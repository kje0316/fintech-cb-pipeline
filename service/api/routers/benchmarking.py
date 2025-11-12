from fastapi import APIRouter, HTTPException, Query
from ..models.benchmark import BenchmarkResponse
from ..services import benchmarking_service

router = APIRouter()

@router.get(
    "/benchmark",
    response_model = BenchmarkResponse,
    summary="업종별 벤치마킹 통계 조회"
)
async def read_benchmark(
    industry: str = Query(..., example="G46"),
    metric: str =Query(..., example="debt_ratio")
):
    stats = benchmarking_service.get_benchmark_stats(industry, metric)
    if stats is None:
        raise HTTPException(status_code=404, detail="data not found")
    return stats

