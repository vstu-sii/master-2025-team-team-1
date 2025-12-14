from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, 
    CONTENT_TYPE_LATEST, CollectorRegistry, multiprocess, ProcessCollector
)
from langfuse import Langfuse
from contextvars import ContextVar
import time
import os
import sys
from typing import Optional, Dict, Any
import uuid
import json
import logging
import httpx
import psutil

# ========== НАСТРОЙКА ПУТЕЙ ДЛЯ PROMETHEUS MULTIPROCESS ==========
PROMETHEUS_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus")

# Создаем директорию если её нет и устанавливаем переменную окружения
try:
    os.makedirs(PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
    os.environ['PROMETHEUS_MULTIPROC_DIR'] = PROMETHEUS_MULTIPROC_DIR
except Exception as e:
    print(f"⚠️ Warning: Could not create prometheus directory: {e}")
    PROMETHEUS_MULTIPROC_DIR = None

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO for production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI App", debug=False)

# ========== НАСТРОЙКА METRICS РЕЕСТРА ==========
registry = CollectorRegistry()

# Регистрируем метрики процесса
ProcessCollector(registry=registry)

# Проверяем, доступен ли multiprocess mode
if PROMETHEUS_MULTIPROC_DIR and os.path.exists(PROMETHEUS_MULTIPROC_DIR):
    logger.info(f"✅ Using Prometheus multiprocess dir: {PROMETHEUS_MULTIPROC_DIR}")
    USE_MULTIPROC = True
else:
    logger.warning(f"⚠️ Prometheus multiprocess dir not available: {PROMETHEUS_MULTIPROC_DIR}")
    logger.info("ℹ️ Using single process mode for metrics")
    USE_MULTIPROC = False

# ========== HTTP METRICS ==========
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    registry=registry
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    registry=registry
)

HTTP_REQUESTS_ACTIVE = Gauge(
    'http_requests_active',
    'Active HTTP Requests',
    registry=registry,
    multiprocess_mode='liveall' if USE_MULTIPROC else 'all'
)

HTTP_ERRORS_TOTAL = Counter(
    'http_errors_total',
    'Total HTTP Errors',
    registry=registry
)

# ========== METRICS ==========
CHAT_REQUESTS_TOTAL = Counter(
    'chat_requests_total',
    'Total Chat Requests',
    registry=registry
)

CHAT_RESPONSE_DURATION = Histogram(
    'chat_response_duration_seconds',
    'Chat Response Time',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    registry=registry
)

PROCESS_MEMORY_BYTES = Gauge(
    'process_memory_bytes',
    'Memory usage in bytes',
    registry=registry,
    multiprocess_mode='min' if USE_MULTIPROC else 'all'
)

PROCESS_CPU_PERCENT = Gauge(
    'process_cpu_percent',
    'CPU usage percent',
    registry=registry,
    multiprocess_mode='max' if USE_MULTIPROC else 'all'
)

# ========== НАСТРОЙКА LANGFUSE ==========
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

logger.info("=" * 80)
logger.info("CONFIGURING APPLICATION")
logger.info(f"LANGFUSE_HOST: {LANGFUSE_HOST}")
logger.info(f"PUBLIC_KEY_SET: {bool(LANGFUSE_PUBLIC_KEY)}")
logger.info(f"SECRET_KEY_SET: {bool(LANGFUSE_SECRET_KEY)}")
logger.info(f"PROMETHEUS_MULTIPROC: {'ENABLED' if USE_MULTIPROC else 'DISABLED'}")
logger.info("=" * 80)

# Проверка доступности Langfuse
def check_langfuse_connection() -> bool:
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

# ========== MIDDLEWARE ДЛЯ METRICS ==========
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    trace_id_var.set(trace_id)
    
    start_time = time.time()
    endpoint = request.url.path
    
    # Увеличиваем счетчик активных запросов
    if not USE_MULTIPROC:
        HTTP_REQUESTS_ACTIVE.inc()
    
    # Создаем trace в Langfuse если клиент инициализирован
    trace = None
    if langfuse_client:
        try:
            trace = langfuse_client.trace(
                id=trace_id,
                name=f"{request.method} {endpoint}",
                metadata={
                    "method": request.method,
                    "path": endpoint,
                    "client_ip": request.client.host if request.client else None
                }
            )
            logger.debug(f"Trace created: {trace_id}")
        except Exception as e:
            logger.error(f"Failed to create trace: {e}")
    
    try:
        response = await call_next(request)
        latency = time.time() - start_time
        
        HTTP_REQUESTS_TOTAL.inc()
        HTTP_REQUEST_DURATION.observe(latency)
        
        if response.status_code >= 400:
            HTTP_ERRORS_TOTAL.inc()
        
        # Завершаем trace в Langfuse
        if trace:
            try:
                trace.update(metadata={"status_code": response.status_code, "latency": latency})
                logger.debug(f"Trace updated: {trace_id}")
            except Exception as e:
                logger.error(f"Failed to update trace: {e}")
        
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time"] = f"{latency:.3f}s"
        
        logger.info(f"{request.method} {endpoint} - {response.status_code} ({latency:.3f}s)")
        
        return response
        
    except Exception as e:
        HTTP_ERRORS_TOTAL.inc()
        logger.error(f"Request failed: {e}")
        raise
        
    finally:
        if not USE_MULTIPROC:
            HTTP_REQUESTS_ACTIVE.dec()

# ========== CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== ЭНДПОИНТЫ ==========
@app.get("/")
async def root():
    return {
        "service": "AI App",
        "version": "1.0.0",
        "monitoring": {
            "prometheus_metrics": "/metrics",
            "health": "/api/health",
            "metrics_health": "/api/metrics/health"
        },
        "langfuse": {
            "configured": langfuse_client is not None,
            "host": LANGFUSE_HOST
        }
    }

@app.get("/api/health")
async def health():
    """Проверка здоровья приложения"""
    trace_id = trace_id_var.get()
    
    # Обновляем системные метрики
    try:
        process = psutil.Process()
        PROCESS_MEMORY_BYTES.set(process.memory_info().rss)
        PROCESS_CPU_PERCENT.set(process.cpu_percent())
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "system": {
            "pid": os.getpid(),
            "prometheus_multiproc": USE_MULTIPROC,
            "multiproc_dir": PROMETHEUS_MULTIPROC_DIR
        },
        "langfuse": {
            "client_initialized": langfuse_client is not None,
            "service_reachable": check_langfuse_connection() if langfuse_client else False
        },
        "trace_id": trace_id
    }

@app.get("/metrics")
async def metrics():
    """Эндпоинт для сбора метрик Prometheus"""
    try:
        # Обновляем системные метрики
        process = psutil.Process()
        PROCESS_MEMORY_BYTES.set(process.memory_info().rss)
        PROCESS_CPU_PERCENT.set(process.cpu_percent())
        
        # Генерируем метрики
        if USE_MULTIPROC:
            data = generate_latest(registry)
        else:
            data = generate_latest()
        
        return Response(data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(f"Error: {e}", status_code=500)

@app.get("/api/metrics/summary")
async def metrics_summary():
    """Сводка метрик в JSON формате"""
    return {
        "http": {
            "requests_total": HTTP_REQUESTS_TOTAL._value.get() if not USE_MULTIPROC else "N/A in multiproc",
            "requests_active": HTTP_REQUESTS_ACTIVE._value.get() if not USE_MULTIPROC else "N/A in multiproc",
        },
        "timestamp": time.time(),
        "prometheus_multiproc": USE_MULTIPROC
    }

# Остальные эндпоинты (hello, chat, langfuse-test) остаются без изменений
# ... [ваш существующий код для эндпоинтов] ...

@app.get("/api/hello")
async def hello():
    trace_id = trace_id_var.get()
    
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

@app.post("/api/chat")
async def chat(request: Request):
    start_time = time.time()
    trace_id = trace_id_var.get()
    
    CHAT_REQUESTS_TOTAL.inc()
    
    try:
        data = await request.json()
        message = data.get("message", "")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Имитация обработки
        time.sleep(0.1)
        response_text = f"Echo: {message}"
        
        # Записываем время ответа
        total_time = time.time() - start_time
        CHAT_RESPONSE_DURATION.observe(total_time)
        
        return {
            "response": response_text,
            "trace_id": trace_id,
            "processing_time": total_time
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 80)
    print("🚀 AI App")
    print("=" * 80)
    print(f"🌐 Langfuse: {'✅ READY' if langfuse_client else '❌ NOT CONFIGURED'}")
    print(f"📈 Prometheus Multiprocess: {'✅ ENABLED' if USE_MULTIPROC else '❌ DISABLED'}")
    print(f"📁 Multiproc dir: {PROMETHEUS_MULTIPROC_DIR}")
    print(f"🔗 Health: http://localhost:8000/api/health")
    print(f"📊 Metrics: http://localhost:8000/metrics")
    print(f"💬 Chat: POST http://localhost:8000/api/chat")
    print("=" * 80)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  
        log_level="info"
    )