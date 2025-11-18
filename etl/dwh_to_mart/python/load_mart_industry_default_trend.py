"""
업종별 월별 부도 추세 마트 적재 스크립트
=====================================

mart_industry_default_trend 테이블에 데이터를 적재합니다.

계산 항목:
- 업종별 × 월별 부도율 추세 (73개 업종 × 12개월)
- 신용등급 분포 (1-3, 4-5, 6-7, 8-10)
- 주요 재무지표 중앙값 (차트 hover용)

실행 방법:
  python etl/dwh_to_mart/python/load_mart_industry_default_trend.py
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


def load_industry_default_trend():
    """대분류 업종별 월별 부도 추세 데이터 적재 (A, B, C 등)"""
    print("\n대분류 업종별 월별 부도 추세 데이터 적재 중...")
    print(f"DWH ({DWH_SCHEMA}) → DM ({DM_SCHEMA})")

    with engine.begin() as conn:
        query = text(f"""
            INSERT INTO {DM_SCHEMA}.mart_industry_default_trend (
                industry_code,
                industry_name,
                bs_dt,
                total_companies,
                default_companies,
                default_rate,
                grade_1_3_count,
                grade_4_5_count,
                grade_6_7_count,
                grade_8_10_count,
                grade_0_count,
                median_debt_ratio,
                median_current_ratio,
                median_operating_margin,
                median_roe,
                median_z_score,
                created_at,
                updated_at
            )
            SELECT
                LEFT(c.sic_cd_3, 1) as industry_code,  -- 대분류 (A, B, C 등)
                mc.major_category_name as industry_name,  -- 대분류명
                t.bs_dt,

                -- 기업 수 및 부도율
                COUNT(DISTINCT c.company_sk) as total_companies,
                SUM(CASE WHEN cb.perf_12m::INTEGER = 1 THEN 1 ELSE 0 END) as default_companies,
                ROUND((SUM(CASE WHEN cb.perf_12m::INTEGER = 1 THEN 1 ELSE 0 END)::NUMERIC /
                       NULLIF(COUNT(DISTINCT c.company_sk), 0)) * 100, 2) as default_rate,

                -- 신용등급 분포
                SUM(CASE WHEN cb.corp_grad::INTEGER BETWEEN 1 AND 3 THEN 1 ELSE 0 END) as grade_1_3_count,
                SUM(CASE WHEN cb.corp_grad::INTEGER BETWEEN 4 AND 5 THEN 1 ELSE 0 END) as grade_4_5_count,
                SUM(CASE WHEN cb.corp_grad::INTEGER BETWEEN 6 AND 7 THEN 1 ELSE 0 END) as grade_6_7_count,
                SUM(CASE WHEN cb.corp_grad::INTEGER BETWEEN 8 AND 10 THEN 1 ELSE 0 END) as grade_8_10_count,
                SUM(CASE WHEN cb.corp_grad::INTEGER = 0 THEN 1 ELSE 0 END) as grade_0_count,

                -- 재무지표 중앙값 (hover details용)
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.r006)::NUMERIC, 2) as median_debt_ratio,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.r008)::NUMERIC, 2) as median_current_ratio,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.r015)::NUMERIC, 2) as median_operating_margin,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.r018)::NUMERIC, 2) as median_roe,

                -- Z-Score 중앙값 (Python에서 계산하지 않고 여기서는 NULL로 설정, 향후 업데이트)
                NULL::NUMERIC as median_z_score,

                NOW() as created_at,
                NOW() as updated_at

            FROM {DWH_SCHEMA}.dim_time t
            CROSS JOIN {DWH_SCHEMA}.dim_company c
            LEFT JOIN {DWH_SCHEMA}.dim_major_category mc ON mc.major_category = LEFT(c.sic_cd_3, 1)
            LEFT JOIN {DWH_SCHEMA}.fact_credit_behavior cb ON cb.company_sk = c.company_sk AND cb.time_sk = t.time_sk
            LEFT JOIN {DWH_SCHEMA}.fact_financial_ratios fr ON fr.company_sk = c.company_sk AND fr.time_sk = t.time_sk

            WHERE c.sic_cd_3 IS NOT NULL
              AND c.company_sk IS NOT NULL

            GROUP BY LEFT(c.sic_cd_3, 1), mc.major_category_name, t.bs_dt

            HAVING COUNT(DISTINCT c.company_sk) >= 10  -- 최소 10개 이상 기업이 있는 경우만

            ON CONFLICT (industry_code, bs_dt) DO UPDATE SET
                industry_name = EXCLUDED.industry_name,
                total_companies = EXCLUDED.total_companies,
                default_companies = EXCLUDED.default_companies,
                default_rate = EXCLUDED.default_rate,
                grade_1_3_count = EXCLUDED.grade_1_3_count,
                grade_4_5_count = EXCLUDED.grade_4_5_count,
                grade_6_7_count = EXCLUDED.grade_6_7_count,
                grade_8_10_count = EXCLUDED.grade_8_10_count,
                grade_0_count = EXCLUDED.grade_0_count,
                median_debt_ratio = EXCLUDED.median_debt_ratio,
                median_current_ratio = EXCLUDED.median_current_ratio,
                median_operating_margin = EXCLUDED.median_operating_margin,
                median_roe = EXCLUDED.median_roe,
                median_z_score = EXCLUDED.median_z_score,
                updated_at = NOW()
        """)

        result = conn.execute(query)
        count = result.rowcount
        print(f"  ✓ {count}개 레코드 적재 완료")


def verify_data():
    """데이터 적재 확인"""
    print("\n" + "="*80)
    print("마트 데이터 확인")
    print("="*80)

    with engine.begin() as conn:
        # 총 레코드 수
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM {DM_SCHEMA}.mart_industry_default_trend
        """))
        total_count = result.scalar()
        print(f"\n총 레코드 수: {total_count:,}개 (업종 × 월)\n")

        # 업종 수 및 월 수
        result = conn.execute(text(f"""
            SELECT
                COUNT(DISTINCT industry_code) as industry_count,
                COUNT(DISTINCT bs_dt) as month_count
            FROM {DM_SCHEMA}.mart_industry_default_trend
        """))
        row = result.fetchone()
        print(f"업종 수: {row[0]}개")
        print(f"월 수: {row[1]}개월")

        # 부도율 상위 10개 업종 (전체 기간 평균)
        print("\n부도율 상위 10개 업종 (전체 기간 평균):")
        print("-" * 80)
        result = conn.execute(text(f"""
            SELECT
                industry_code,
                industry_name,
                COUNT(*) as month_count,
                ROUND(AVG(default_rate)::NUMERIC, 2) as avg_default_rate,
                ROUND(AVG(total_companies)::NUMERIC, 0) as avg_companies
            FROM {DM_SCHEMA}.mart_industry_default_trend
            GROUP BY industry_code, industry_name
            ORDER BY avg_default_rate DESC
            LIMIT 10
        """))

        print(f"{'업종코드':<10} {'업종명':<40} {'월수':<6} {'평균부도율%':<12} {'평균기업수':<10}")
        print("-" * 80)
        for row in result:
            print(f"{row[0]:<10} {row[1]:<40} {row[2]:<6} {row[3]:<12} {int(row[4]):<10}")

        # 샘플 데이터 (G46 업종)
        print("\n샘플 데이터 (G46: 도매 및 상품 중개업):")
        print("-" * 100)
        result = conn.execute(text(f"""
            SELECT
                TO_CHAR(bs_dt, 'YYYY-MM') as year_month,
                total_companies,
                default_companies,
                default_rate,
                grade_1_3_count,
                grade_4_5_count,
                grade_6_7_count,
                grade_8_10_count
            FROM {DM_SCHEMA}.mart_industry_default_trend
            WHERE industry_code = 'G46'
            ORDER BY bs_dt
        """))

        print(f"{'월':<10} {'기업수':<8} {'부도수':<8} {'부도율%':<10} {'1-3':<6} {'4-5':<6} {'6-7':<6} {'8-10':<6}")
        print("-" * 100)
        for row in result:
            print(f"{row[0]:<10} {row[1]:<8} {row[2]:<8} {row[3]:<10} {row[4]:<6} {row[5]:<6} {row[6]:<6} {row[7]:<6}")


def main():
    try:
        print("\n" + "="*80)
        print("업종별 월별 부도 추세 마트 적재 시작")
        print("="*80)

        # 데이터 적재
        load_industry_default_trend()

        # 결과 확인
        verify_data()

        print("\n" + "="*80)
        print("✓ 업종별 월별 부도 추세 마트 적재 완료!")
        print("="*80)

    except Exception as e:
        print(f"\n✗ 마트 적재 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
