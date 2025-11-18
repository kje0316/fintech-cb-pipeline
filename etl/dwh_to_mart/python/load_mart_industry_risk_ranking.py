"""
대분류 업종별 리스크 랭킹 마트 적재 스크립트
============================================

mart_industry_risk_ranking 테이블에 데이터를 적재합니다.

계산 항목:
- 대분류 업종별 (A~U) 리스크 지표
- 부도율, 평균 신용등급, 고위험 기업 비율
- 재무 건전성 지표 (부채비율, 유동비율, 영업이익률)
- 종합 리스크 점수 = 0.4×부도율 + 0.3×평균신용등급 + 0.2×고위험비율
- 리스크 순위 (1=가장 위험)

실행 방법:
  python etl/dwh_to_mart/python/load_mart_industry_risk_ranking.py
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import DB_URL

# DB 연결
engine = create_engine(DB_URL, echo=False, future=True)

DWH_SCHEMA = "dwh"
DM_SCHEMA = "marts"


def load_industry_risk_ranking():
    """대분류 업종별 리스크 랭킹 데이터 적재"""
    print("\n대분류 업종별 리스크 랭킹 데이터 적재 중...")
    print(f"DWH ({DWH_SCHEMA}) → DM ({DM_SCHEMA})")

    with engine.begin() as conn:
        # 1단계: CTE로 업종별 리스크 지표 계산
        query = text(f"""
            WITH industry_risk_metrics AS (
                SELECT
                    LEFT(c.sic_cd_3, 1) as industry_code,  -- 대분류
                    mc.major_category_name as industry_name,

                    -- 리스크 지표
                    COUNT(DISTINCT c.company_sk) as total_companies,
                    SUM(CASE WHEN cb.perf_12m::INTEGER = 1 THEN 1 ELSE 0 END) as default_companies,
                    ROUND((SUM(CASE WHEN cb.perf_12m::INTEGER = 1 THEN 1 ELSE 0 END)::NUMERIC /
                           NULLIF(COUNT(DISTINCT c.company_sk), 0)) * 100, 2) as default_rate,

                    -- 신용 프로파일
                    ROUND(AVG(cb.corp_grad::NUMERIC), 2) as avg_credit_grade,
                    SUM(CASE WHEN cb.corp_grad::INTEGER >= 8 THEN 1 ELSE 0 END) as high_risk_count,
                    ROUND((SUM(CASE WHEN cb.corp_grad::INTEGER >= 8 THEN 1 ELSE 0 END)::NUMERIC /
                           NULLIF(COUNT(DISTINCT c.company_sk), 0)) * 100, 2) as high_risk_ratio,

                    -- 재무 건전성 지표 (중앙값)
                    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.r006)::NUMERIC, 2) as median_debt_ratio,
                    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.r008)::NUMERIC, 2) as median_current_ratio,
                    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.r015)::NUMERIC, 2) as median_operating_margin,

                    -- 집계 기간
                    MIN(t.bs_dt) as data_period_start,
                    MAX(t.bs_dt) as data_period_end

                FROM {DWH_SCHEMA}.dim_company c
                LEFT JOIN {DWH_SCHEMA}.dim_major_category mc ON mc.major_category = LEFT(c.sic_cd_3, 1)
                LEFT JOIN {DWH_SCHEMA}.fact_credit_behavior cb ON cb.company_sk = c.company_sk
                LEFT JOIN {DWH_SCHEMA}.fact_financial_ratios fr ON fr.company_sk = c.company_sk AND fr.time_sk = cb.time_sk
                LEFT JOIN {DWH_SCHEMA}.dim_time t ON t.time_sk = cb.time_sk

                WHERE c.sic_cd_3 IS NOT NULL
                  AND cb.corp_grad IS NOT NULL

                GROUP BY LEFT(c.sic_cd_3, 1), mc.major_category_name

                HAVING COUNT(DISTINCT c.company_sk) >= 10  -- 최소 10개 이상 기업
            ),
            risk_score_calculated AS (
                SELECT
                    *,
                    -- Z-Score는 NULL로 설정 (향후 업데이트)
                    NULL::NUMERIC as avg_z_score,

                    -- 종합 리스크 점수 계산
                    -- 높을수록 위험: 부도율, 신용등급, 고위험비율
                    -- 낮을수록 위험: Z-Score (현재는 제외)
                    ROUND((
                        0.4 * COALESCE(default_rate, 0) +
                        0.3 * COALESCE(avg_credit_grade, 5) +
                        0.2 * COALESCE(high_risk_ratio, 0)
                    ), 4) as risk_score

                FROM industry_risk_metrics
            )
            INSERT INTO {DM_SCHEMA}.mart_industry_risk_ranking (
                industry_code,
                industry_name,
                total_companies,
                default_companies,
                default_rate,
                avg_credit_grade,
                high_risk_count,
                high_risk_ratio,
                avg_z_score,
                median_debt_ratio,
                median_current_ratio,
                median_operating_margin,
                risk_score,
                risk_rank,
                data_period_start,
                data_period_end,
                created_at,
                updated_at
            )
            SELECT
                industry_code,
                industry_name,
                total_companies,
                default_companies,
                default_rate,
                avg_credit_grade,
                high_risk_count,
                high_risk_ratio,
                avg_z_score,
                median_debt_ratio,
                median_current_ratio,
                median_operating_margin,
                risk_score,
                RANK() OVER (ORDER BY risk_score DESC) as risk_rank,  -- 순위 (높은 점수 = 위험)
                data_period_start,
                data_period_end,
                NOW() as created_at,
                NOW() as updated_at
            FROM risk_score_calculated
            ORDER BY risk_score DESC

            ON CONFLICT (industry_code) DO UPDATE SET
                industry_name = EXCLUDED.industry_name,
                total_companies = EXCLUDED.total_companies,
                default_companies = EXCLUDED.default_companies,
                default_rate = EXCLUDED.default_rate,
                avg_credit_grade = EXCLUDED.avg_credit_grade,
                high_risk_count = EXCLUDED.high_risk_count,
                high_risk_ratio = EXCLUDED.high_risk_ratio,
                avg_z_score = EXCLUDED.avg_z_score,
                median_debt_ratio = EXCLUDED.median_debt_ratio,
                median_current_ratio = EXCLUDED.median_current_ratio,
                median_operating_margin = EXCLUDED.median_operating_margin,
                risk_score = EXCLUDED.risk_score,
                risk_rank = EXCLUDED.risk_rank,
                data_period_start = EXCLUDED.data_period_start,
                data_period_end = EXCLUDED.data_period_end,
                updated_at = NOW()
        """)

        result = conn.execute(query)
        count = result.rowcount
        print(f"  ✓ {count}개 대분류 업종 리스크 데이터 적재 완료")


def verify_data():
    """데이터 적재 확인"""
    print("\n" + "="*80)
    print("마트 데이터 확인")
    print("="*80)

    with engine.begin() as conn:
        # 총 레코드 수
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM {DM_SCHEMA}.mart_industry_risk_ranking
        """))
        total_count = result.scalar()
        print(f"\n총 대분류 업종 수: {total_count}개\n")

        # 위험 업종 TOP 5
        print("🔴 위험 업종 TOP 5 (리스크 점수 높은 순):")
        print("-" * 120)
        result = conn.execute(text(f"""
            SELECT
                risk_rank,
                industry_code,
                industry_name,
                total_companies,
                ROUND(default_rate::NUMERIC, 2) as default_rate,
                ROUND(avg_credit_grade::NUMERIC, 2) as avg_grade,
                ROUND(high_risk_ratio::NUMERIC, 2) as high_risk_ratio,
                ROUND(risk_score::NUMERIC, 4) as risk_score
            FROM {DM_SCHEMA}.mart_industry_risk_ranking
            ORDER BY risk_score DESC
            LIMIT 5
        """))

        print(f"{'순위':<6} {'코드':<6} {'업종명':<45} {'기업수':<10} {'부도율%':<10} {'평균등급':<10} {'고위험%':<10} {'리스크점수':<12}")
        print("-" * 120)
        for row in result:
            print(f"{row[0]:<6} {row[1]:<6} {row[2]:<45} {row[3]:<10} {row[4]:<10} {row[5]:<10} {row[6]:<10} {row[7]:<12}")

        # 안전 업종 TOP 5
        print("\n🟢 안전 업종 TOP 5 (리스크 점수 낮은 순):")
        print("-" * 120)
        result = conn.execute(text(f"""
            SELECT
                risk_rank,
                industry_code,
                industry_name,
                total_companies,
                ROUND(default_rate::NUMERIC, 2) as default_rate,
                ROUND(avg_credit_grade::NUMERIC, 2) as avg_grade,
                ROUND(high_risk_ratio::NUMERIC, 2) as high_risk_ratio,
                ROUND(risk_score::NUMERIC, 4) as risk_score
            FROM {DM_SCHEMA}.mart_industry_risk_ranking
            ORDER BY risk_score ASC
            LIMIT 5
        """))

        print(f"{'순위':<6} {'코드':<6} {'업종명':<45} {'기업수':<10} {'부도율%':<10} {'평균등급':<10} {'고위험%':<10} {'리스크점수':<12}")
        print("-" * 120)
        for row in result:
            print(f"{row[0]:<6} {row[1]:<6} {row[2]:<45} {row[3]:<10} {row[4]:<10} {row[5]:<10} {row[6]:<10} {row[7]:<12}")

        # 전체 업종 리스크 분포
        print("\n전체 대분류 업종 리스크 분포:")
        print("-" * 120)
        result = conn.execute(text(f"""
            SELECT
                risk_rank,
                industry_code,
                industry_name,
                ROUND(risk_score::NUMERIC, 4) as risk_score
            FROM {DM_SCHEMA}.mart_industry_risk_ranking
            ORDER BY risk_score DESC
        """))

        print(f"{'순위':<6} {'코드':<6} {'업종명':<45} {'리스크점수':<12}")
        print("-" * 120)
        for row in result:
            print(f"{row[0]:<6} {row[1]:<6} {row[2]:<45} {row[3]:<12}")


def main():
    try:
        print("\n" + "="*80)
        print("대분류 업종별 리스크 랭킹 마트 적재 시작")
        print("="*80)

        # 데이터 적재
        load_industry_risk_ranking()

        # 결과 확인
        verify_data()

        print("\n" + "="*80)
        print("✓ 대분류 업종별 리스크 랭킹 마트 적재 완료!")
        print("="*80)

    except Exception as e:
        print(f"\n✗ 마트 적재 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
