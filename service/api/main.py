from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import metadata, benchmarking, dashboard

app = FastAPI(
    title="Fintech CB Pipeline API",
    description="데이터 마트 및 메타데이터를 서빙하는 API"
)

# CORS 설정 (Next.js 대시보드용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/")
async def root():
    return {"message": "API is running. Go to /docs for details."}