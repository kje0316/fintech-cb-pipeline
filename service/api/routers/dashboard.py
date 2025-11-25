"""
대시보드 API 라우터
==================

메인 대시보드에 필요한 5개 엔드포인트 제공:
1. KPI 카드 데이터 (최신 월 기준)
2. 상위 5개 위험 업종의 월별 부도율 추세
3. 대분류 업종 구성비 (파이 차트용)
4. 월별 × 업종별 부도율 히트맵 데이터
5. 대분류 업종별 부도율 (막대 그래프용)
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
from ..database import get_db

router = APIRouter(prefix="/api/v1/dashboard")

DM_SCHEMA = "marts"
DWH_SCHEMA = "dwh"


@router.get("/kpi")
async def get_kpi_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    KPI 카드 데이터 반환 (최신 월 기준)

    Returns:
    --------
    - bs_dt: 기준 년월
    - avg_credit_grade: 평균 신용등급
    - avg_credit_grade_change: 전월 대비 변화
    - hhi_index: HHI (Herfindahl-Hirschman Index) 위험 집중도
    - hhi_status: HHI 상태 (safe/moderate/high)
    - high_risk_ratio: 고위험 기업 비율 (%)
    - high_risk_change: 고위험 비율 전월 대비 변화 (percentage points)
    - premium_ratio: 우량군 기업 비율 (%)
    - premium_to_risk_ratio: 우량군/고위험군 배율
    """

    # 1. 기본 KPI 데이터 가져오기
    kpi_query = text(f"""
        SELECT
            bs_dt,
            avg_credit_grade,
            avg_credit_grade_change,
            high_risk_ratio,
            high_risk_ratio_change
        FROM {DM_SCHEMA}.mart_market_kpi_monthly
        WHERE bs_dt = (SELECT MAX(bs_dt) FROM {DM_SCHEMA}.mart_market_kpi_monthly)
    """)

    kpi_result = db.execute(kpi_query).fetchone()

    if not kpi_result:
        raise HTTPException(status_code=404, detail="KPI 데이터를 찾을 수 없습니다")

    # 2. HHI (Herfindahl-Hirschman Index) 계산
    # HHI = Σ(각 업종의 부도 기업 비중)^2 × 10,000
    hhi_query = text(f"""
        WITH latest_month AS (
            SELECT MAX(bs_dt) as max_dt
            FROM {DM_SCHEMA}.mart_industry_default_trend
        ),
        industry_defaults AS (
            SELECT
                industry_code,
                total_companies,
                default_rate,
                (total_companies * default_rate / 100.0) as default_count
            FROM {DM_SCHEMA}.mart_industry_default_trend
            WHERE bs_dt = (SELECT max_dt FROM latest_month)
        ),
        total_defaults AS (
            SELECT SUM(default_count) as total
            FROM industry_defaults
        )
        SELECT
            ROUND(
                SUM(
                    POWER(
                        (default_count / NULLIF((SELECT total FROM total_defaults), 0)) * 100,
                        2
                    )
                )::NUMERIC,
                2
            ) as hhi
        FROM industry_defaults
        WHERE (SELECT total FROM total_defaults) > 0
    """)

    hhi_result = db.execute(hhi_query).fetchone()
    hhi_value = float(hhi_result[0]) if hhi_result and hhi_result[0] else 0.0

    # HHI 상태 판단
    if hhi_value < 1500:
        hhi_status = "safe"
        hhi_description = "신용 위험이 여러 업종에 분산되어 있습니다"
    elif hhi_value < 2500:
        hhi_status = "moderate"
        hhi_description = "업종별 위험 집중도가 중간 수준입니다"
    else:
        hhi_status = "high"
        hhi_description = "특정 업종에 신용 위험이 집중되어 있습니다"

    # 3. 우량군 비율 계산 (신용등급 1-4)
    premium_query = text(f"""
        WITH latest_month AS (
            SELECT MAX(bs_dt) as max_dt
            FROM {DM_SCHEMA}.mart_credit_grade_distribution_monthly
        )
        SELECT
            ROUND(
                SUM(CASE WHEN credit_grade BETWEEN 1 AND 4 THEN percentage ELSE 0 END)::NUMERIC,
                2
            ) as premium_ratio,
            ROUND(
                SUM(CASE WHEN credit_grade BETWEEN 8 AND 10 THEN percentage ELSE 0 END)::NUMERIC,
                2
            ) as high_risk_ratio_from_dist
        FROM {DM_SCHEMA}.mart_credit_grade_distribution_monthly
        WHERE bs_dt = (SELECT max_dt FROM latest_month)
    """)

    premium_result = db.execute(premium_query).fetchone()
    premium_ratio = float(premium_result[0]) if premium_result and premium_result[0] else 0.0
    high_risk_from_dist = float(premium_result[1]) if premium_result and premium_result[1] else 0.1

    # 우량군/고위험군 배율 계산
    premium_to_risk = round(premium_ratio / max(high_risk_from_dist, 0.01), 2)

    return {
        "bs_dt": kpi_result[0].isoformat() if kpi_result[0] else None,
        "avg_credit_grade": float(kpi_result[1]) if kpi_result[1] else 0.0,
        "avg_credit_grade_change": float(kpi_result[2]) if kpi_result[2] else 0.0,
        "hhi_index": hhi_value,
        "hhi_status": hhi_status,
        "hhi_description": hhi_description,
        "high_risk_ratio": float(kpi_result[3]) if kpi_result[3] else 0.0,
        "high_risk_change": float(kpi_result[4]) if kpi_result[4] else 0.0,
        "premium_ratio": premium_ratio,
        "premium_to_risk_ratio": premium_to_risk,
    }


@router.get("/top-industries-trend")
async def get_top_industries_trend(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    상위 5개 고위험 업종의 월별 부도율 추세

    Returns:
    --------
    List of:
    - industry_code: 업종 코드 (A-U)
    - industry_name: 업종명
    - bs_dt: 기준년월
    - default_rate: 부도율 (%)
    """

    # 1단계: 업종별 평균 부도율 계산하여 상위 5개 선정
    top_industries_query = text(f"""
        SELECT industry_code
        FROM {DM_SCHEMA}.mart_industry_risk_ranking
        ORDER BY risk_score DESC
        LIMIT 5
    """)

    top_industries = [row[0] for row in db.execute(top_industries_query).fetchall()]

    if not top_industries:
        return []

    # 2단계: 상위 5개 업종의 월별 추세 데이터 가져오기
    trend_query = text(f"""
        SELECT
            industry_code,
            industry_name,
            bs_dt,
            default_rate
        FROM {DM_SCHEMA}.mart_industry_default_trend
        WHERE industry_code = ANY(:industry_codes)
        ORDER BY industry_code, bs_dt
    """)

    results = db.execute(trend_query, {"industry_codes": top_industries}).fetchall()

    return [
        {
            "industry_code": row[0],
            "industry_name": row[1],
            "bs_dt": row[2].isoformat() if row[2] else None,
            "default_rate": float(row[3]) if row[3] else 0.0,
        }
        for row in results
    ]


@router.get("/industry-composition")
async def get_industry_composition(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    대분류 업종 구성비 (전체 기간 평균)

    Returns:
    --------
    List of:
    - industry_code: 업종 코드 (A-U)
    - industry_name: 업종명
    - company_count: 평균 기업 수
    - percentage: 구성 비율 (%)
    """

    query = text(f"""
        WITH industry_avg AS (
            SELECT
                industry_code,
                industry_name,
                ROUND(AVG(total_companies)::NUMERIC, 0) as avg_companies
            FROM {DM_SCHEMA}.mart_industry_default_trend
            GROUP BY industry_code, industry_name
        )
        SELECT
            industry_code,
            industry_name,
            avg_companies,
            ROUND((avg_companies::NUMERIC / SUM(avg_companies) OVER ()) * 100, 2) as percentage
        FROM industry_avg
        ORDER BY avg_companies DESC
    """)

    results = db.execute(query).fetchall()

    return [
        {
            "industry_code": row[0],
            "industry_name": row[1],
            "company_count": int(row[2]) if row[2] else 0,
            "percentage": float(row[3]) if row[3] else 0.0,
        }
        for row in results
    ]


@router.get("/heatmap")
async def get_heatmap_data(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    월별 × 업종별 부도율 히트맵 데이터

    Returns:
    --------
    List of:
    - bs_dt: 기준년월
    - industry_code: 업종 코드 (A-U)
    - industry_name: 업종명
    - default_rate: 부도율 (%)
    """

    query = text(f"""
        SELECT
            bs_dt,
            industry_code,
            industry_name,
            default_rate
        FROM {DM_SCHEMA}.mart_industry_default_trend
        ORDER BY bs_dt, industry_code
    """)

    results = db.execute(query).fetchall()

    return [
        {
            "bs_dt": row[0].isoformat() if row[0] else None,
            "industry_code": row[1],
            "industry_name": row[2],
            "default_rate": float(row[3]) if row[3] else 0.0,
        }
        for row in results
    ]


@router.get("/industry-default-rates")
async def get_industry_default_rates(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    대분류 업종별 부도율 (막대 그래프용)

    Returns:
    --------
    List of:
    - industry_code: 업종 코드 (A-U)
    - industry_name: 업종명
    - default_rate: 평균 부도율 (%)
    - total_companies: 평균 기업 수
    """

    query = text(f"""
        SELECT
            industry_code,
            industry_name,
            default_rate,
            total_companies
        FROM {DM_SCHEMA}.mart_industry_risk_ranking
        ORDER BY default_rate DESC
    """)

    results = db.execute(query).fetchall()

    return [
        {
            "industry_code": row[0],
            "industry_name": row[1],
            "default_rate": float(row[2]) if row[2] else 0.0,
            "total_companies": int(row[3]) if row[3] else 0,
        }
        for row in results
    ]


@router.get("/credit-distribution")
async def get_credit_distribution(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    신용등급별 기업 분포 및 부도율

    Returns:
    --------
    List of:
    - credit_grade: 신용등급 (0-10)
    - company_count: 기업 수
    - percentage: 구성 비율 (%)
    - default_rate: 해당 등급 내 부도율 (%)
    - default_count: 부도 기업 수
    """

    query = text(f"""
        SELECT
            credit_grade,
            SUM(company_count) as total_companies,
            AVG(percentage) as avg_percentage,
            AVG(default_rate_in_grade) as avg_default_rate,
            SUM(default_count) as total_defaults
        FROM {DM_SCHEMA}.mart_credit_grade_distribution_monthly
        GROUP BY credit_grade
        ORDER BY credit_grade
    """)

    results = db.execute(query).fetchall()

    return [
        {
            "credit_grade": int(row[0]) if row[0] is not None else 0,
            "company_count": int(row[1]) if row[1] else 0,
            "percentage": float(row[2]) if row[2] else 0.0,
            "default_rate": float(row[3]) if row[3] else 0.0,
            "default_count": int(row[4]) if row[4] else 0,
        }
        for row in results
    ]


@router.get("/industry-risk-radar")
async def get_industry_risk_radar(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    산업별 위험 프로파일 (레이더 차트용)

    Returns:
    --------
    List of:
    - industry_code: 업종 코드 (A-U)
    - industry_name: 업종명
    - credit_health_score: 신용 건전성 (0-100)
    - default_risk_score: 부도 위험도 (0-100, 높을수록 안전)
    - market_presence_score: 시장 점유율 (0-100)
    - financial_stability_score: 재무 안정성 (0-100)
    - overall_health_score: 종합 건전성 (0-100)
    - growth_potential_score: 성장 잠재력 (0-100)
    """

    query = text(f"""
        SELECT
            industry_code,
            industry_name,
            credit_health_score,
            default_risk_score,
            market_presence_score,
            financial_stability_score,
            overall_health_score,
            growth_potential_score
        FROM {DM_SCHEMA}.mart_industry_risk_radar
        ORDER BY industry_code
    """)

    results = db.execute(query).fetchall()

    return [
        {
            "industry_code": row[0],
            "industry_name": row[1],
            "credit_health_score": float(row[2]) if row[2] else 0.0,
            "default_risk_score": float(row[3]) if row[3] else 0.0,
            "market_presence_score": float(row[4]) if row[4] else 0.0,
            "financial_stability_score": float(row[5]) if row[5] else 0.0,
            "overall_health_score": float(row[6]) if row[6] else 0.0,
            "growth_potential_score": float(row[7]) if row[7] else 0.0,
        }
        for row in results
    ]


@router.get("/industry-benchmarks")
async def get_industry_benchmarks(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    전체 시장 재무 건전성 벤치마크 (게이지용)

    Returns:
    --------
    - leverage: 레버리지 (부채비율) 통계
    - liquidity: 유동성 (유동비율) 통계
    - profitability: 수익성 (영업이익률) 통계
    - efficiency: 효율성 통계
    각각 mean, p25, median, p75 포함
    """

    query = text(f"""
        SELECT
            AVG(leverage_mean) as leverage_mean,
            AVG(leverage_median) as leverage_median,
            AVG(leverage_p25) as leverage_p25,
            AVG(leverage_p75) as leverage_p75,

            AVG(liquidity_mean) as liquidity_mean,
            AVG(liquidity_median) as liquidity_median,
            AVG(liquidity_p25) as liquidity_p25,
            AVG(liquidity_p75) as liquidity_p75,

            AVG(profitability_mean) as profitability_mean,
            AVG(profitability_median) as profitability_median,
            AVG(profitability_p25) as profitability_p25,
            AVG(profitability_p75) as profitability_p75,

            AVG(efficiency_mean) as efficiency_mean,
            AVG(efficiency_median) as efficiency_median
        FROM {DM_SCHEMA}.mart_industry_financial_benchmarks
    """)

    result = db.execute(query).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="벤치마크 데이터를 찾을 수 없습니다")

    return {
        "leverage": {
            "mean": float(result[0]) if result[0] else 0.0,
            "median": float(result[1]) if result[1] else 0.0,
            "p25": float(result[2]) if result[2] else 0.0,
            "p75": float(result[3]) if result[3] else 0.0,
        },
        "liquidity": {
            "mean": float(result[4]) if result[4] else 0.0,
            "median": float(result[5]) if result[5] else 0.0,
            "p25": float(result[6]) if result[6] else 0.0,
            "p75": float(result[7]) if result[7] else 0.0,
        },
        "profitability": {
            "mean": float(result[8]) if result[8] else 0.0,
            "median": float(result[9]) if result[9] else 0.0,
            "p25": float(result[10]) if result[10] else 0.0,
            "p75": float(result[11]) if result[11] else 0.0,
        },
        "efficiency": {
            "mean": float(result[12]) if result[12] else 0.0,
            "median": float(result[13]) if result[13] else 0.0,
        },
    }
