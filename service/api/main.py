from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from .routers import metadata, benchmarking, dashboard, prediction, clustering
from .middleware.logging_middleware import APILoggingMiddleware
from .middleware.prometheus_middleware import PrometheusMiddleware, get_metrics

app = FastAPI(
    title="Fintech CB Pipeline API",
    description="데이터 마트, 메타데이터, 부도 예측을 제공하는 API",
    version="1.0.0"
)

# CORS 설정 (Next.js 대시보드용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js 대시보드
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 로깅 미들웨어 (모든 API 요청/응답 로깅)
app.add_middleware(APILoggingMiddleware)

# Prometheus 메트릭 미들웨어
app.add_middleware(PrometheusMiddleware)

# 메타데이터 라우터 등록
app.include_router(
    metadata.router,
    prefix="/api/v1/metadata",
    tags=["Metadata"]
)

# 벤치마킹 라우터 등록
app.include_router(
    benchmarking.router,
    tags=["Benchmarking"]
)

# 대시보드 라우터 등록
app.include_router(
    dashboard.router,
    tags=["Dashboard"]
)

# 부도 예측 라우터 등록
app.include_router(
    prediction.router,
    tags=["Prediction"]
)

# 클러스터링 라우터 등록
app.include_router(
    clustering.router,
    tags=["Clustering"]
)

@app.get("/")
async def root():
    return {
        "message": "Fintech CB Pipeline API is running",
        "endpoints": {
            "docs": "/docs",
            "metadata": "/api/v1/metadata",
            "benchmarking": "/api/v1/benchmarking",
            "dashboard": "/api/v1/dashboard",
            "prediction": "/api/v1/predict",
            "clustering": "/api/v1/clustering",
            "metrics": "/metrics"
        }
    }


@app.get("/metrics", response_class=PlainTextResponse, tags=["Monitoring"])
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    return get_metrics().get_metrics()


@app.get("/health", tags=["Monitoring"])
async def health():
    """헬스체크 엔드포인트"""
    return {"status": "healthy"}