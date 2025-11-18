"""
월별 신용등급 분포 마트 적재 스크립트
=======================================

mart_credit_grade_distribution_monthly 테이블에 데이터를 적재합니다.

계산 항목:
- 월별 × 신용등급(0-10) 집계
- 등급별 기업 수 및 비율
- 등급별 평균 재무지표
- 등급 내 부도율

실행 방법:
  python etl/dwh_to_mart/python/load_mart_credit_grade_distribution.py
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


def load_credit_grade_distribution():
    """월별 신용등급 분포 데이터 적재"""
    print("\n월별 신용등급 분포 데이터 적재 중...")
    print(f"DWH ({DWH_SCHEMA}) → DM ({DM_SCHEMA})")

    with engine.begin() as conn:
        query = text(f"""
            INSERT INTO {DM_SCHEMA}.mart_credit_grade_distribution_monthly (
                bs_dt,
                credit_grade,
                company_count,
                percentage,
                avg_total_assets,
                avg_debt_ratio,
                avg_current_ratio,
                avg_operating_margin,
                avg_z_score,
                default_count,
                default_rate_in_grade,
                created_at,
                updated_at
            )
            SELECT
                t.bs_dt,
                cb.corp_grad::INTEGER as credit_grade,

                -- 집계 데이터
                COUNT(DISTINCT c.company_sk) as company_count,
                ROUND((COUNT(DISTINCT c.company_sk)::NUMERIC /
                       NULLIF(SUM(COUNT(DISTINCT c.company_sk)) OVER (PARTITION BY t.bs_dt), 0)) * 100, 2) as percentage,

                -- 평균 재무지표
                ROUND(AVG(fs.fn1_13)::NUMERIC, 2) as avg_total_assets,
                ROUND(AVG(fr.r006)::NUMERIC, 2) as avg_debt_ratio,
                ROUND(AVG(fr.r008)::NUMERIC, 2) as avg_current_ratio,
                ROUND(AVG(fr.r015)::NUMERIC, 2) as avg_operating_margin,

                -- Z-Score (NULL로 설정, 향후 업데이트)
                NULL::NUMERIC as avg_z_score,

                -- 부도 정보
                SUM(CASE WHEN cb.perf_12m::INTEGER = 1 THEN 1 ELSE 0 END) as default_count,
                ROUND((SUM(CASE WHEN cb.perf_12m::INTEGER = 1 THEN 1 ELSE 0 END)::NUMERIC /
                       NULLIF(COUNT(DISTINCT c.company_sk), 0)) * 100, 2) as default_rate_in_grade,

                NOW() as created_at,
                NOW() as updated_at

            FROM {DWH_SCHEMA}.dim_time t
            JOIN {DWH_SCHEMA}.fact_credit_behavior cb ON cb.time_sk = t.time_sk
            JOIN {DWH_SCHEMA}.dim_company c ON c.company_sk = cb.company_sk
            LEFT JOIN {DWH_SCHEMA}.fact_financial_statement fs ON fs.company_sk = c.company_sk AND fs.time_sk = t.time_sk
            LEFT JOIN {DWH_SCHEMA}.fact_financial_ratios fr ON fr.company_sk = c.company_sk AND fr.time_sk = t.time_sk

            WHERE cb.corp_grad IS NOT NULL
              AND cb.corp_grad::INTEGER BETWEEN 0 AND 10

            GROUP BY t.bs_dt, cb.corp_grad::INTEGER

            HAVING COUNT(DISTINCT c.company_sk) >= 5  -- 최소 5개 이상 기업이 있는 경우만

            ON CONFLICT (bs_dt, credit_grade) DO UPDATE SET
                company_count = EXCLUDED.company_count,
                percentage = EXCLUDED.percentage,
                avg_total_assets = EXCLUDED.avg_total_assets,
                avg_debt_ratio = EXCLUDED.avg_debt_ratio,
                avg_current_ratio = EXCLUDED.avg_current_ratio,
                avg_operating_margin = EXCLUDED.avg_operating_margin,
                avg_z_score = EXCLUDED.avg_z_score,
                default_count = EXCLUDED.default_count,
                default_rate_in_grade = EXCLUDED.default_rate_in_grade,
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
            SELECT COUNT(*) FROM {DM_SCHEMA}.mart_credit_grade_distribution_monthly
        """))
        total_count = result.scalar()
        print(f"\n총 레코드 수: {total_count:,}개 (월 × 등급)\n")

        # 월 수 및 등급 수
        result = conn.execute(text(f"""
            SELECT
                COUNT(DISTINCT bs_dt) as month_count,
                COUNT(DISTINCT credit_grade) as grade_count
            FROM {DM_SCHEMA}.mart_credit_grade_distribution_monthly
        """))
        row = result.fetchone()
        print(f"월 수: {row[0]}개월")
        print(f"신용등급 수: {row[1]}개 (0-10)")

        # 최근 월 등급 분포
        print("\n최근 월 신용등급 분포:")
        print("-" * 100)
        result = conn.execute(text(f"""
            SELECT
                TO_CHAR(bs_dt, 'YYYY-MM') as year_month,
                credit_grade,
                company_count,
                percentage,
                default_count,
                default_rate_in_grade
            FROM {DM_SCHEMA}.mart_credit_grade_distribution_monthly
            WHERE bs_dt = (SELECT MAX(bs_dt) FROM {DM_SCHEMA}.mart_credit_grade_distribution_monthly)
            ORDER BY credit_grade
        """))

        print(f"{'월':<10} {'등급':<6} {'기업수':<10} {'비율%':<8} {'부도수':<8} {'등급내부도율%':<12}")
        print("-" * 100)
        for row in result:
            print(f"{row[0]:<10} {row[1]:<6} {row[2]:<10} {row[3]:<8} {row[4]:<8} {row[5] if row[5] else 'N/A':<12}")

        # 등급별 평균 부도율 (전체 기간)
        print("\n등급별 평균 부도율 (전체 기간):")
        print("-" * 80)
        result = conn.execute(text(f"""
            SELECT
                credit_grade,
                SUM(company_count) as total_companies,
                SUM(default_count) as total_defaults,
                ROUND(AVG(default_rate_in_grade)::NUMERIC, 2) as avg_default_rate
            FROM {DM_SCHEMA}.mart_credit_grade_distribution_monthly
            GROUP BY credit_grade
            ORDER BY credit_grade
        """))

        print(f"{'등급':<6} {'총기업수':<12} {'총부도수':<10} {'평균부도율%':<12}")
        print("-" * 80)
        for row in result:
            print(f"{row[0]:<6} {row[1]:<12} {row[2]:<10} {row[3] if row[3] else 'N/A':<12}")


def main():
    try:
        print("\n" + "="*80)
        print("월별 신용등급 분포 마트 적재 시작")
        print("="*80)

        # 데이터 적재
        load_credit_grade_distribution()

        # 결과 확인
        verify_data()

        print("\n" + "="*80)
        print("✓ 월별 신용등급 분포 마트 적재 완료!")
        print("="*80)

    except Exception as e:
        print(f"\n✗ 마트 적재 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
