from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Response
import time

app = FastAPI()

# Метрики Prometheus
REQUEST_COUNT = Counter('requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.middleware("http")
async def monitor_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    request_latency = time.time() - start_time
    
    REQUEST_COUNT.inc()
    REQUEST_LATENCY.observe(request_latency)
    
    return response

@app.get("/api/hello")
def read_root():
    return {"message": "Hello from FastAPI!"}