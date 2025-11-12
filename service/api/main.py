from fastapi import FastAPI
from .routers import metadata, benchmarking

app = FastAPI(
    title="Fintech CB Pipeline API",
    description="데이터 마트 및 메타데이터를 서빙하는 API"
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

@app.get("/")
async def root():
    return {"message": "API is running. Go to /docs for details."}