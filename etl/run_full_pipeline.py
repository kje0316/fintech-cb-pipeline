"""
통합 ETL 파이프라인 실행 스크립트

CSV 원본 데이터 → Lake → DWH → Data Mart 전체 과정을 순차 실행합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def run_lake_to_dwh():
    """Phase 1: Lake → DWH (CSV 데이터를 차원 및 사실 테이블로 적재)"""
    print("\n" + "="*80)
    print("PHASE 1: Lake → DWH Pipeline")
    print("="*80)

    from etl.lake_to_dwh.run_pipe import run_pipeline
    run_pipeline()

    print("\n✓ Phase 1 완료: DWH 테이블 생성 및 데이터 적재 완료\n")


def run_dwh_to_mart():
    """Phase 2: DWH → Mart (업종별 재무비율 통계 집계)"""
    print("\n" + "="*80)
    print("PHASE 2: DWH → Mart Pipeline")
    print("="*80)

    from etl.dwh_to_mart.build_dm_industry_financial_stats import (
        create_schema, create_dm_table
    )
    from etl.dwh_to_mart.load_dm_industry_financial_ratios_stats import (
        load_industry_financial_ratios_stats
    )

    # Step 2a: Mart 스키마 및 테이블 생성
    print("\nStep 2a: Mart 스키마 및 테이블 생성 중...")
    create_schema()
    create_dm_table()

    # Step 2b: DWH에서 Mart로 데이터 집계 및 적재
    print("\nStep 2b: DWH → Mart 데이터 적재 중...")
    load_industry_financial_ratios_stats()

    print("\n✓ Phase 2 완료: Data Mart 생성 및 집계 완료\n")


def main():
    """전체 파이프라인 실행"""
    try:
        print("\n" + "="*80)
        print("통합 ETL 파이프라인 시작")
        print("="*80)
        print("\n데이터 흐름: CSV → Lake → DWH (Dimensions + Facts) → Mart (Aggregated)\n")

        # Phase 1: Lake → DWH
        run_lake_to_dwh()

        # Phase 2: DWH → Mart
        run_dwh_to_mart()

        print("\n" + "="*80)
        print("✓ 전체 파이프라인 완료!")
        print("="*80)
        print("\n생성된 데이터베이스 구조:")
        print("  lake.raw_data                            - 원본 CSV 데이터 (사용 안함)")
        print("  dwh.dim_company                          - 기업 차원 테이블")
        print("  dwh.dim_time                             - 시간 차원 테이블")
        print("  dwh.fact_financial_statement             - 재무제표 사실 테이블")
        print("  dwh.fact_financial_ratios                - 재무비율 사실 테이블")
        print("  dwh.fact_credit_behavior                 - 신용행동 사실 테이블")
        print("  marts.dm_industry_financial_ratios_stats - 업종별 재무비율 통계 마트")
        print("\n다음 단계:")
        print("  1. API 서버 실행: uvicorn service.api.main:app --reload")
        print("  2. 대시보드 실행: streamlit run service/dashboard/app.py")

    except Exception as e:
        print(f"\n✗ 파이프라인 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
