# service/api/services/benchmarking_service.py

from typing import Optional
from sqlalchemy import text
from ..database import engine

def get_benchmark_stats(industry: str, metric: str) -> Optional[dict]:
    """
    PostgreSQL marts.dm_industry_benchmark_v0 테이블에서 벤치마크 통계 조회

    Args:
        industry: 업종 코드 (예: "G46")
        metric: 지표 코드 (예: "debt_ratio")

    Returns:
        dict: 벤치마크 통계 또는 None
    """
    try:
        query = text("""
            SELECT
                industry_code,
                metric_code,
                count,
                avg_value,
                median_value,
                std_value,
                min_value,
                max_value,
                p10,
                p25,
                p50,
                p75,
                p90
            FROM marts.dm_industry_financial_ratios_stats
            WHERE industry_code = :industry
              AND metric_code = :metric
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"industry": industry, "metric": metric})
            row = result.fetchone()

            if row is None:
                return None

            # 결과를 dict로 변환
            return {
                "industry_code": row[0],
                "metric_code": row[1],
                "count": int(row[2]),
                "avg_value": float(row[3]) if row[3] is not None else None,
                "median_value": float(row[4]) if row[4] is not None else None,
                "std_value": float(row[5]) if row[5] is not None else None,
                "min_value": float(row[6]) if row[6] is not None else None,
                "max_value": float(row[7]) if row[7] is not None else None,
                "p10": float(row[8]) if row[8] is not None else None,
                "p25": float(row[9]) if row[9] is not None else None,
                "p50": float(row[10]) if row[10] is not None else None,
                "p75": float(row[11]) if row[11] is not None else None,
                "p90": float(row[12]) if row[12] is not None else None,
            }

    except Exception as e:
        print(f"❌ 벤치마크 데이터 조회 실패: {e}")
        return None
