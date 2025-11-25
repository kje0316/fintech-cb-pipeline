"""
통합 ETL 파이프라인 실행 스크립트

CSV 원본 데이터 → Lake → DWH → DM(파생 데이터 포함) 전체 과정을 순차 실행합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def run_lake_to_dwh2():
    """Phase 1: Lake → DWH2 (CSV 데이터를 차원 및 사실 테이블로 적재)"""
    print("\n" + "="*80)
    print("PHASE 1: Lake → DWH2 Pipeline")
    print("="*80)

    from spark_etl.lake_to_dwh2.run_pipe_spark import run_pipeline
    run_pipeline()

    print("\n✓ Phase 1 완료: DWH2 테이블 생성 및 데이터 적재 완료\n")


# def run_dwh_to_dm():
#     """Phase 2: DWH2 → DM (파생 데이터 포함한 Data Mart 생성)"""
#     print("\n" + "="*80)
#     print("PHASE 2: DWH2 → DM Pipeline (파생 데이터 포함)")
#     print("="*80)

#     # derived_dm.py의 main 함수 실행
#     from etl.main_dm.scripts.derived_dm import main as build_dm
    
#     print("\nStep 2: DWH2 → DM 데이터 복사 및 파생 데이터 생성 중...")
#     build_dm()

#     print("\n✓ Phase 2 완료: Data Mart 및 파생 데이터 생성 완료\n")
def run_dwh_to_dm():
    """Phase 2: DWH2 → DM (테이블 복사 + 파생 데이터 생성)"""
    print("\n" + "="*80)
    print("    PHASE 2: DWH2 → DM Pipeline")
    print("="*80)

    from spark_etl.main_dm.run_pipeline import main
    main()

def main():
    """전체 파이프라인 실행"""
    try:
        print("\n" + "="*80)
        print("통합 ETL 파이프라인 시작 (DM 버전)")
        print("="*80)
        print("\n데이터 흐름: CSV → Lake → DWH2 (Dimensions + Facts) → DM (원본 + 파생)\n")

        # Phase 1: Lake → DWH2
        run_lake_to_dwh2()

        # Phase 2: DWH2 → DM (파생 데이터 포함)
        run_dwh_to_dm()

        print("\n" + "="*80)
        print("✓ 전체 파이프라인 완료!")
        # print("="*80)
        # print("\n생성된 데이터베이스 구조:")
        # print("\n[Lake Layer]")
        # print("  lake.raw_data                            - 원본 CSV 데이터")
        
        # print("\n[DWH Layer]")
        # print("  dwh2.dim_company                         - 기업 차원 테이블")
        # print("  dwh2.dim_industry                        - 업종 차원 테이블")
        # print("  dwh2.dim_time                            - 시간 차원 테이블")
        # print("  dwh2.fact_financial_statement            - 재무제표 사실 테이블")
        # print("  dwh2.fact_credit_behavior                - 신용행동 사실 테이블")
        
        # print("\n[DM Layer]")
        # print("  dm.dim_company                           - 기업 차원 (복사)")
        # print("  dm.dim_industry                          - 업종 차원 (복사)")
        # print("  dm.dim_time                              - 시간 차원 (복사)")
        # print("  dm.fact_financial_statement              - 재무제표 사실 (복사)")
        # print("  dm.fact_credit_behavior                  - 신용행동 사실 (복사)")
        # print("  dm.derived_data ⭐                       - 파생 데이터 (SQL 직접 계산)")
        
        # print("\n다음 단계:")
        # print("  1. 데이터 확인:")
        # print("     SELECT * FROM dm.derived_data LIMIT 10;")
        # print("\n  2. 원시 + 파생 조인 조회:")
        # print("     SELECT fs.fn1_1, fs.fn2_1, dd.fn1_13, dd.r015")
        # print("     FROM dm.fact_financial_statement fs")
        # print("     JOIN dm.derived_data dd")
        # print("       ON fs.company_sk = dd.company_sk AND fs.time_sk = dd.time_sk")
        # print("     LIMIT 10;")
        # print("\n  3. API 서버 실행: uvicorn service.api.main:app --reload")
        # print("  4. 대시보드 실행: streamlit run service/dashboard/app.py")

    except Exception as e:
        print(f"\n✗ 파이프라인 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()