import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import argparse
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import DB_URL

# --------------------
# DB 연결 (shared/config_loader.py 사용)
engine = create_engine(
    DB_URL,
    echo=False,
    future=True
)

# 스키마 이름
DWH_SCHEMA = "dwh"
DM_SCHEMA = "marts"

# 재무비율 메트릭 정의
METRICS = {
    'r001': '총자산증가율',
    'r006': '부채비율',
    'r007': '자기자본비율',
    'r008': '유동비율',
    'r012': '차입금의존도',
    'r002': '매출액증가율',
    'r015': '영업이익률',
    'r016': '당기순이익률',
    'r013': '매출원가율',
    'r014': '판관비율',
    'r018': '자기자본이익률_ROE',
    'r019': '매출채권회전율',
    'r020': '재고자산회전율',
    'r021': '매입채무회전율',
    'r022': '총자산회전율',
    'r023': '총자산순이익률',
    'r024': '유동자산증가율',
    'r025': '유형자산증가율'
}


def load_industry_financial_ratios_stats():
    """업종별 재무비율 통계 적재"""
    print("\n업종별 재무비율 통계 데이터 적재 중...")
    print(f"DWH ({DWH_SCHEMA}) → DM ({DM_SCHEMA})")
    print(f"총 {len(METRICS)}개 메트릭 처리\n")
    
    total_inserted = 0
    
    with engine.begin() as conn:
        for metric_code, metric_name in METRICS.items():
            print(f"처리중: {metric_code.upper()} - {metric_name}")
            
            # 각 메트릭별로 업종별 통계 계산
            query = text(f"""
                INSERT INTO {DM_SCHEMA}.dm_industry_financial_ratios_stats
                    (industry_code, metric_code, count, avg_value, median_value, 
                     std_value, min_value, max_value, p10, p25, p50, p75, p90, created_at)
                SELECT 
                    dc.sic_cd_3 as industry_code,
                    '{metric_code.upper()}' as metric_code,
                    
                    -- 통계값
                    COUNT(fr.{metric_code}) as count,
                    AVG(fr.{metric_code})::FLOAT as avg_value,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fr.{metric_code})::FLOAT as median_value,
                    STDDEV(fr.{metric_code})::FLOAT as std_value,
                    MIN(fr.{metric_code})::FLOAT as min_value,
                    MAX(fr.{metric_code})::FLOAT as max_value,
                    
                    -- 백분위수
                    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY fr.{metric_code})::FLOAT as p10,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY fr.{metric_code})::FLOAT as p25,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY fr.{metric_code})::FLOAT as p50,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY fr.{metric_code})::FLOAT as p75,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY fr.{metric_code})::FLOAT as p90,
                    
                    NOW() as created_at
                    
                FROM {DWH_SCHEMA}.dim_company dc
                JOIN {DWH_SCHEMA}.fact_financial_ratios fr 
                    ON dc.company_sk = fr.company_sk
                
                WHERE dc.sic_cd_3 IS NOT NULL
                  AND fr.{metric_code} IS NOT NULL
                
                GROUP BY dc.sic_cd_3
                HAVING COUNT(fr.{metric_code}) >= 5  -- 최소 5개 이상 데이터가 있는 업종만
                
                ON CONFLICT (industry_code, metric_code) DO UPDATE SET
                    count = EXCLUDED.count,
                    avg_value = EXCLUDED.avg_value,
                    median_value = EXCLUDED.median_value,
                    std_value = EXCLUDED.std_value,
                    min_value = EXCLUDED.min_value,
                    max_value = EXCLUDED.max_value,
                    p10 = EXCLUDED.p10,
                    p25 = EXCLUDED.p25,
                    p50 = EXCLUDED.p50,
                    p75 = EXCLUDED.p75,
                    p90 = EXCLUDED.p90,
                    created_at = NOW()
            """)
            
            result = conn.execute(query)
            count = result.rowcount
            total_inserted += count
            print(f"  ✓ {count}개 업종 데이터 적재 완료")
    
    print(f"\n총 {total_inserted}개 레코드 적재 완료")


def verify_data():
    """데이터 적재 확인"""
    print("\n" + "="*80)
    print("DM 데이터 적재 결과 확인")
    print("="*80)
    
    with engine.begin() as conn:
        # 총 레코드 수
        result = conn.execute(text(f"""
            SELECT COUNT(*) 
            FROM {DM_SCHEMA}.dm_industry_financial_ratios_stats
        """))
        total_count = result.scalar()
        print(f"\n총 레코드 수: {total_count:,}개")
        
        # 업종별 레코드 수
        result = conn.execute(text(f"""
            SELECT 
                industry_code,
                COUNT(*) as metric_count
            FROM {DM_SCHEMA}.dm_industry_financial_ratios_stats
            GROUP BY industry_code
            ORDER BY industry_code
            LIMIT 10
        """))
        
        print(f"\n업종별 메트릭 수 (상위 10개):")
        print("-" * 40)
        print(f"{'업종코드':<15} {'메트릭 수':<10}")
        print("-" * 40)
        for row in result:
            print(f"{row[0]:<15} {row[1]:<10}")
        
        # 메트릭별 업종 수
        result = conn.execute(text(f"""
            SELECT 
                metric_code,
                COUNT(*) as industry_count
            FROM {DM_SCHEMA}.dm_industry_financial_ratios_stats
            GROUP BY metric_code
            ORDER BY metric_code
        """))
        
        print(f"\n메트릭별 업종 수:")
        print("-" * 40)
        print(f"{'메트릭코드':<15} {'업종 수':<10}")
        print("-" * 40)
        for row in result:
            print(f"{row[0]:<15} {row[1]:<10}")


def show_sample_data():
    """샘플 데이터 조회"""
    print("\n" + "="*80)
    print("샘플 데이터 조회")
    print("="*80)
    
    with engine.begin() as conn:
        # G46 업종의 영업이익률(operating_margin) 샘플
        result = conn.execute(text(f"""
            SELECT 
                industry_code,
                metric_code,
                count,
                ROUND(avg_value::numeric, 2) as avg_value,
                ROUND(median_value::numeric, 2) as median_value,
                ROUND(std_value::numeric, 2) as std_value,
                ROUND(min_value::numeric, 2) as min_value,
                ROUND(max_value::numeric, 2) as max_value,
                ROUND(p10::numeric, 2) as p10,
                ROUND(p25::numeric, 2) as p25,
                ROUND(p50::numeric, 2) as p50,
                ROUND(p75::numeric, 2) as p75,
                ROUND(p90::numeric, 2) as p90
            FROM {DM_SCHEMA}.dm_industry_financial_ratios_stats
            WHERE industry_code = 'G46' 
              AND metric_code IN ('R015', 'R016', 'R018')
            ORDER BY metric_code
        """))
        
        print("\n[샘플] G46 업종의 주요 수익성 지표:")
        print("-" * 140)
        print(f"{'업종':<6} {'메트릭':<8} {'건수':<6} {'평균':<8} {'중앙값':<8} {'표준편차':<8} {'최소':<8} {'최대':<8} {'P10':<6} {'P25':<6} {'P50':<6} {'P75':<6} {'P90':<6}")
        print("-" * 140)
        
        for row in result:
            print(f"{row[0]:<6} {row[1]:<8} {row[2]:<6} {row[3]:<8} {row[4]:<8} {row[5]:<8} {row[6]:<8} {row[7]:<8} {row[8]:<6} {row[9]:<6} {row[10]:<6} {row[11]:<6} {row[12]:<6}")


def show_comparison():
    """업종 간 비교"""
    print("\n" + "="*80)
    print("업종 간 영업이익률(R015) 비교")
    print("="*80)
    
    with engine.begin() as conn:
        result = conn.execute(text(f"""
            SELECT 
                industry_code,
                count,
                ROUND(avg_value::numeric, 2) as avg_value,
                ROUND(median_value::numeric, 2) as median_value,
                ROUND(p25::numeric, 2) as p25,
                ROUND(p75::numeric, 2) as p75
            FROM {DM_SCHEMA}.dm_industry_financial_ratios_stats
            WHERE metric_code = 'R015'
            ORDER BY avg_value DESC
            LIMIT 15
        """))
        
        print("\n영업이익률 상위 15개 업종:")
        print("-" * 80)
        print(f"{'순위':<6} {'업종코드':<10} {'건수':<8} {'평균':<10} {'중앙값':<10} {'P25':<10} {'P75':<10}")
        print("-" * 80)
        
        for idx, row in enumerate(result, 1):
            print(f"{idx:<6} {row[0]:<10} {row[1]:<8} {row[2]:<10} {row[3]:<10} {row[4]:<10} {row[5]:<10}")


def main():
    parser = argparse.ArgumentParser(description='DWH에서 DM으로 데이터 적재')
    parser.add_argument('--sample', action='store_true', help='샘플 데이터 조회')
    parser.add_argument('--compare', action='store_true', help='업종 간 비교 조회')
    args = parser.parse_args()
    
    try:
        print("\n" + "="*80)
        print("업종별 재무비율 통계 DM 데이터 적재 시작")
        print("="*80)
        
        # ETL 실행
        load_industry_financial_ratios_stats()
        
        # 결과 확인
        verify_data()
        
        # 샘플 데이터 조회
        if args.sample:
            show_sample_data()
        
        # 업종 간 비교
        if args.compare:
            show_comparison()
        
        print("\n" + "="*80)
        print("✓ DM 데이터 적재 완료!")
        print("="*80)
        print(f"\n사용 예시:")
        print(f"  python {sys.argv[0]}            # 데이터 적재")
        print(f"  python {sys.argv[0]} --sample   # 샘플 데이터 조회")
        print(f"  python {sys.argv[0]} --compare  # 업종 간 비교")
        
    except Exception as e:
        print(f"\n✗ 데이터 적재 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()