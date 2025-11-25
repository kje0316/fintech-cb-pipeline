from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import metadata, benchmarking, dashboard, prediction
from .middleware.logging_middleware import APILoggingMiddleware

app = FastAPI(
    title="Fintech CB Pipeline API",
    description="데이터 마트, 메타데이터, 부도 예측을 제공하는 API",
    version="1.0.0"
)

# CORS 설정 (Next.js 대시보드용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 로깅 미들웨어 (모든 API 요청/응답 로깅)
app.add_middleware(APILoggingMiddleware)

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

@app.get("/")
async def root():
    return {
        "message": "Fintech CB Pipeline API is running",
        "endpoints": {
            "docs": "/docs",
            "metadata": "/api/v1/metadata",
            "benchmarking": "/api/v1/benchmarking",
            "dashboard": "/api/v1/dashboard",
            "prediction": "/api/v1/predict"
        }
    }