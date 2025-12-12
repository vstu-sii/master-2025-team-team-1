from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from langfuse import Langfuse
from contextvars import ContextVar
import time
import os
from typing import Optional
import uuid

app = FastAPI(title="AI App")

# ========== 1. НАСТРОЙКА LANGFUSE ==========
# Получаем ключи из переменных окружения
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3002")

# Инициализируем Langfuse клиент
langfuse = Langfuse(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_HOST
)

# ContextVar для хранения trace_id в рамках запроса
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

# ========== 2. МЕТРИКИ PROMETHEUS ==========
REQUEST_COUNT = Counter('fastapi_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('fastapi_request_latency_seconds', 'Request latency', ['method', 'endpoint'])
LANGFUSE_TRACES = Counter('langfuse_traces_total', 'Total traces sent to Langfuse')
ERROR_COUNT = Counter('fastapi_errors_total', 'Total errors', ['method', 'endpoint', 'error_type'])

# ========== 3. MIDDLEWARE ДЛЯ ТРАССИРОВКИ ==========
@app.middleware("http")
async def langfuse_tracing_middleware(request: Request, call_next):
    # Генерируем уникальный ID для трассировки
    trace_id = f"trace_{uuid.uuid4().hex[:16]}"
    trace_id_var.set(trace_id)
    
    start_time = time.time()
    
    try:
        # Создаем трассировку в Langfuse
        trace = langfuse.trace(
            id=trace_id,
            name=f"{request.method} {request.url.path}",
            metadata={
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        # Логируем начало обработки запроса
        span = trace.span(
            name="request_processing",
            input={
                "headers": dict(request.headers),
                "body": await request.body() if request.method in ["POST", "PUT", "PATCH"] else None,
            }
        )
        
        # Выполняем запрос
        response = await call_next(request)
        request_latency = time.time() - start_time
        
        # Завершаем span
        span.end(
            output={
                "status_code": response.status_code,
                "headers": dict(response.headers),
            },
            metadata={
                "latency_seconds": round(request_latency, 4),
                "response_size": len(response.body) if hasattr(response, 'body') else 0,
            }
        )
        
        # Обновляем метрики Prometheus
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(request_latency)
        LANGFUSE_TRACES.inc()
        
        # Добавляем trace_id в заголовки ответа для отладки
        response.headers["X-Trace-ID"] = trace_id
        
        return response
        
    except Exception as e:
        request_latency = time.time() - start_time
        error_type = type(e).__name__
        
        # Логируем ошибку в Langfuse
        if 'trace' in locals():
            trace.event(
                name="request_error",
                metadata={
                    "error": str(e),
                    "error_type": error_type,
                    "latency_seconds": round(request_latency, 4),
                }
            )
        
        # Обновляем метрики ошибок
        ERROR_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            error_type=error_type
        ).inc()
        
        raise

# ========== 4. CORS MIDDLEWARE ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Настройте под свои нужды
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 5. ЭНДПОИНТЫ ==========
@app.get("/metrics")
async def metrics():
    """Эндпоинт для Prometheus метрик"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/hello")
async def read_root():
    """Простой тестовый эндпоинт"""
    # Получаем trace_id для текущего запроса
    trace_id = trace_id_var.get()
    
    # Можно добавить дополнительную трассировку
    if trace_id:
        trace = langfuse.trace(id=trace_id)
        trace.span(
            name="hello_endpoint_logic",
            metadata={"custom_logic": "executed"}
        )
    
    return {
        "message": "Hello from FastAPI!",
        "trace_id": trace_id,
        "langfuse_url": f"{LANGFUSE_HOST}/traces/{trace_id}" if trace_id else None
    }

@app.get("/api/health")
async def health_check():
    """Проверка здоровья с трассировкой"""
    trace_id = trace_id_var.get()
    
    # Логируем проверку здоровья
    if trace_id:
        trace = langfuse.trace(id=trace_id)
        trace.generation(
            name="health_check",
            input={"endpoint": "/api/health"},
            output={"status": "healthy"},
            metadata={"timestamp": time.time()}
        )
    
    return {
        "status": "healthy",
        "service": "fastapi-langfuse",
        "langfuse_connected": bool(LANGFUSE_SECRET_KEY),
        "trace_id": trace_id
    }

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Пример эндпоинта для чата с трассировкой"""
    trace_id = trace_id_var.get()
    
    try:
        data = await request.json()
        message = data.get("message", "")
        user_id = data.get("user_id", "anonymous")
        
        if trace_id:
            trace = langfuse.trace(id=trace_id)
            
            # Обновляем информацию о пользователе
            trace.update(user_id=user_id)
            
            # Логируем входные данные
            trace.span(
                name="chat_input_processing",
                input={"message": message, "user_id": user_id}
            )
            
            # Имитируем обработку LLM (в реальности здесь будет вызов к OpenAI и т.д.)
            # Пример с использованием CallbackHandler для OpenAI:
            # handler = CallbackHandler(trace_id=trace_id)
            # response = openai.chat.completions.create(..., callbacks=[handler])
            
            response_text = f"Echo: {message}"
            
            # Логируем ответ
            trace.generation(
                name="chat_response",
                input={"message": message},
                output=response_text,
                metadata={"model": "echo", "user_id": user_id}
            )
        
        return {
            "response": response_text,
            "user_id": user_id,
            "trace_id": trace_id,
            "langfuse_url": f"{LANGFUSE_HOST}/traces/{trace_id}" if trace_id else None
        }
        
    except Exception as e:
        if trace_id:
            trace = langfuse.trace(id=trace_id)
            trace.event(
                name="chat_error",
                metadata={"error": str(e), "error_type": type(e).__name__}
            )
        raise

# ========== 6. ЭНДПОИНТ ДЛЯ РУЧНОГО ТЕСТИРОВАНИЯ LANGFUSE ==========
@app.get("/api/test-trace")
async def test_trace():
    """Эндпоинт для ручного тестирования трассировки"""
    # Создаем отдельную трассировку для теста
    test_trace_id = f"test_{uuid.uuid4().hex[:8]}"
    
    trace = langfuse.trace(
        id=test_trace_id,
        name="manual_test_trace",
        user_id="test_user",
        metadata={"source": "test_endpoint"}
    )
    
    # Логируем несколько этапов
    with trace.span(name="step_1") as span:
        span.input = {"test": "data"}
        # Имитация работы
        time.sleep(0.1)
        span.output = {"processed": True}
    
    trace.span(name="step_2", metadata={"custom": "metadata"})
    
    trace.generation(
        name="test_generation",
        input={"prompt": "Test input"},
        output="Test output",
        metadata={"model": "test-model", "temperature": 0.7}
    )
    
    # Добавляем оценку (score)
    trace.score(
        name="test_score",
        value=4.5,
        comment="Good test response"
    )
    
    return {
        "message": "Test trace created",
        "trace_id": test_trace_id,
        "view_url": f"{LANGFUSE_HOST}/traces/{test_trace_id}"
    }

# ========== 7. ЗАПУСК ПРИЛОЖЕНИЯ ==========
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("FastAPI + Langfuse + Prometheus")
    print("=" * 50)
    print(f"Langfuse Host: {LANGFUSE_HOST}")
    print(f"Langfuse Connected: {bool(LANGFUSE_SECRET_KEY)}")
    print(f"Prometheus Metrics: http://localhost:8000/metrics")
    print(f"API Documentation: http://localhost:8000/docs")
    print(f"Langfuse Dashboard: {LANGFUSE_HOST}")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)