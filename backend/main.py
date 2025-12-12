from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from langfuse import Langfuse
from contextvars import ContextVar
import time
import os
import sys
from typing import Optional
import uuid
import json
import logging
import httpx

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/app_debug.log')
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI App", debug=True)

# ========== 1. НАСТРОЙКА LANGFUSE ==========
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

logger.info("=" * 80)
logger.info("CONFIGURING APPLICATION")
logger.info(f"LANGFUSE_HOST: {LANGFUSE_HOST}")
logger.info(f"PUBLIC_KEY_SET: {bool(LANGFUSE_PUBLIC_KEY)}")
logger.info(f"SECRET_KEY_SET: {bool(LANGFUSE_SECRET_KEY)}")
logger.info("=" * 80)

# Проверка доступности Langfuse
def check_langfuse_connection():
    """Проверяет, доступен ли Langfuse"""
    try:
        response = httpx.get(f"{LANGFUSE_HOST}/api/public/health", timeout=5.0)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Langfuse connection check failed: {e}")
        return False

# Инициализация Langfuse
langfuse_client = None
if all([LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST]):
    try:
        langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
            flush_interval=2,
            flush_at=5,
            timeout=10
        )
        logger.info("✅ Langfuse client initialized")
        
        # Тестовое подключение
        if check_langfuse_connection():
            logger.info("✅ Langfuse service is reachable")
        else:
            logger.warning("⚠️ Langfuse service is not reachable, but client initialized")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize Langfuse: {e}")
        langfuse_client = None
else:
    logger.warning("⚠️ Langfuse credentials not fully configured")

# ContextVar для хранения trace_id
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

# ========== 2. MIDDLEWARE ==========
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    
    start_time = time.time()
    
    try:
        # Создаем trace в Langfuse если клиент инициализирован
        trace = None
        if langfuse_client:
            try:
                trace = langfuse_client.trace(
                    id=trace_id,
                    name=f"{request.method} {request.url.path}",
                    metadata={
                        "method": request.method,
                        "path": request.url.path,
                        "client_ip": request.client.host if request.client else None
                    }
                )
                logger.debug(f"Trace created: {trace_id}")
            except Exception as e:
                logger.error(f"Failed to create trace: {e}")
        
        response = await call_next(request)
        latency = time.time() - start_time
        
        # Завершаем trace
        if trace:
            try:
                trace.update(metadata={"status_code": response.status_code, "latency": latency})
                logger.debug(f"Trace updated: {trace_id}")
            except Exception as e:
                logger.error(f"Failed to update trace: {e}")
        
        # Добавляем заголовки
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time"] = f"{latency:.3f}s"
        
        logger.info(f"{request.method} {request.url.path} - {response.status_code} ({latency:.3f}s)")
        
        return response
        
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise

# ========== 3. CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 4. ЭНДПОИНТЫ ==========
@app.get("/")
async def root():
    return {
        "service": "AI App",
        "langfuse": {
            "configured": langfuse_client is not None,
            "host": LANGFUSE_HOST,
            "test_endpoint": "/api/langfuse-test"
        }
    }

@app.get("/api/health")
async def health():
    trace_id = trace_id_var.get()
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "langfuse": {
            "client_initialized": langfuse_client is not None,
            "service_reachable": check_langfuse_connection() if langfuse_client else False,
            "host": LANGFUSE_HOST
        },
        "trace_id": trace_id
    }

@app.get("/api/langfuse-test")
async def langfuse_test():
    """Тестовый эндпоинт для Langfuse"""
    if not langfuse_client:
        return {
            "error": "Langfuse client not initialized",
            "check": "Verify LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST env vars"
        }
    
    # Создаем тестовую трассировку
    test_trace_id = f"test_{uuid.uuid4().hex[:8]}"
    
    try:
        trace = langfuse_client.trace(
            id=test_trace_id,
            name="test_trace",
            metadata={"source": "test_endpoint"}
        )
        
        trace.span(name="test_span_1", metadata={"step": 1})
        
        span = trace.span(name="test_span_2")
        span.input = {"message": "Hello"}
        time.sleep(0.1)
        span.output = {"response": "World"}
        span.end()  
        
        trace.generation(
            name="test_generation",
            input={"prompt": "Test"},
            output="Test output",
            metadata={"model": "test"}
        )
        
        # Принудительно отправляем
        langfuse_client.flush()
        
        return {
            "success": True,
            "trace_id": test_trace_id,
            "view_url": f"{LANGFUSE_HOST}/traces/{test_trace_id}",
            "message": "Test trace created and sent to Langfuse"
        }
        
    except Exception as e:
        logger.error(f"Langfuse test failed: {e}")
        return {
            "error": "Failed to create test trace",
            "details": str(e),
            "trace_id": test_trace_id
        }

@app.get("/api/hello")
async def hello():
    trace_id = trace_id_var.get()
    
    # Добавляем span если Langfuse доступен
    if langfuse_client:
        try:
            trace = langfuse_client.trace(id=trace_id)
            trace.span(name="hello_processing")
            langfuse_client.flush()
        except Exception as e:
            logger.error(f"Failed to add span: {e}")
    
    return {
        "message": "Hello from FastAPI",
        "trace_id": trace_id,
        "langfuse_enabled": langfuse_client is not None
    }

@app.post("/api/chat")
async def chat(request: Request):
    trace_id = trace_id_var.get()
    
    try:
        data = await request.json()
        message = data.get("message", "")
        
        if langfuse_client:
            try:
                trace = langfuse_client.trace(id=trace_id)
                trace.span(
                    name="chat_input",
                    input={"message": message}
                )
                
                response_text = f"Echo: {message}"
                
                trace.generation(
                    name="chat_response",
                    input={"message": message},
                    output=response_text,
                    metadata={"model": "echo"}
                )
                
                langfuse_client.flush()
                
            except Exception as e:
                logger.error(f"Langfuse error in chat: {e}")
                response_text = f"Echo (langfuse error): {message}"
        else:
            response_text = f"Echo: {message}"
        
        return {
            "response": response_text,
            "trace_id": trace_id
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ========== 5. ЗАПУСК ==========
if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 80)
    print("🚀 FASTAPI APPLICATION")
    print("=" * 80)
    print(f"🌐 Langfuse: {'✅ READY' if langfuse_client else '❌ NOT CONFIGURED'}")
    print(f"📊 Host: {LANGFUSE_HOST}")
    print(f"🔗 Health: http://localhost:8000/api/health")
    print(f"🧪 Test: http://localhost:8000/api/langfuse-test")
    print(f"📈 Metrics: http://localhost:8000/metrics")
    print(f"📚 Docs: http://localhost:8000/docs")
    print("=" * 80)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )