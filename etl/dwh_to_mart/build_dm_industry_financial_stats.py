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

RAW_DATA_PATH = './data/기업신용평가정보_합성데이터.csv'
COLUMN_REFERENCE_PATH = './data/202109_기업CB.csv'
COL_TYPES_PATH = './config/col_types.yaml'
DW_COLUMNS_PATH = './config/dw_columns.yaml'
SCHEMA_SQL_PATH = './etl/lake_to_dwh/schema.sql'

# --------------------
# DB 연결 (shared/config_loader.py 사용)
engine = create_engine(
    DB_URL,
    echo=True,
    future=True
)

# 스키마 이름
DM_SCHEMA = "marts"


def create_schema():
    """DM 스키마 생성"""
    with engine.begin() as conn:
        try:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DM_SCHEMA}"))
            print(f"✓ 스키마 '{DM_SCHEMA}' 생성 완료")
        except SQLAlchemyError as e:
            print(f"✗ 스키마 생성 실패: {e}")
            raise


def drop_table():
    """기존 DM 테이블 삭제"""
    with engine.begin() as conn:
        try:
            conn.execute(text(f"DROP TABLE IF EXISTS {DM_SCHEMA}.dm_industry_financial_ratios_stats CASCADE"))
            print("✓ 기존 DM 테이블 삭제 완료")
        except SQLAlchemyError as e:
            print(f"✗ 테이블 삭제 실패: {e}")
            raise


def create_dm_table():
    """업종별 재무비율 통계 테이블 생성"""
    print("\ndm_industry_financial_ratios_stats 테이블 생성 중...")

    with engine.begin() as conn:
        # 테이블 생성
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DM_SCHEMA}.dm_industry_financial_ratios_stats (
                stat_sk SERIAL PRIMARY KEY,
                industry_code VARCHAR(10) NOT NULL,
                metric_code VARCHAR(10) NOT NULL,
                
                -- 통계값
                count INTEGER,
                avg_value FLOAT,
                median_value FLOAT,
                std_value FLOAT,
                min_value FLOAT,
                max_value FLOAT,
                
                -- 백분위수
                p10 FLOAT,
                p25 FLOAT,
                p50 FLOAT,
                p75 FLOAT,
                p90 FLOAT,
                
                created_at TIMESTAMP DEFAULT NOW(),
                
                CONSTRAINT uk_industry_metric UNIQUE(industry_code, metric_code)
            )
        """))
        
        # 인덱스 생성
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_dmifrs_industry
            ON {DM_SCHEMA}.dm_industry_financial_ratios_stats(industry_code)
        """))

        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_dmifrs_metric
            ON {DM_SCHEMA}.dm_industry_financial_ratios_stats(metric_code)
        """))
        
        print("✓ dm_industry_financial_ratios_stats 테이블 생성 완료")


def verify_table():
    """테이블 생성 확인"""
    with engine.begin() as conn:
        result = conn.execute(text(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{DM_SCHEMA}'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        
        print("\n" + "="*60)
        print(f"생성된 DM 테이블 목록 (스키마: {DM_SCHEMA})")
        print("="*60)
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table}")
        print("="*60)
        
        # 컬럼 정보 조회
        result = conn.execute(text(f"""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = '{DM_SCHEMA}' 
            AND table_name = 'dm_industry_financial_ratios_stats'
            ORDER BY ordinal_position
        """))
        
        print(f"\n테이블 컬럼 정보:")
        print("-" * 80)
        print(f"{'컬럼명':<30} {'타입':<20} {'NULL허용':<10}")
        print("-" * 80)
        
        for row in result:
            col_name = row[0]
            data_type = row[1]
            if row[2]:
                data_type += f"({row[2]})"
            is_null = row[3]
            
            print(f"{col_name:<30} {data_type:<20} {is_null:<10}")


def main():
    parser = argparse.ArgumentParser(description='업종별 재무비율 통계 DM 구축')
    parser.add_argument('--rebuild', action='store_true', help='기존 테이블을 삭제하고 재생성')
    args = parser.parse_args()
    
    try:
        print("\n" + "="*60)
        print("업종별 재무비율 통계 DM 구축 시작")
        print("="*60 + "\n")
        
        # 스키마 생성
        create_schema()
        
        # 테이블 재생성 옵션
        if args.rebuild:
            print("\n[재구축 모드] 기존 테이블 삭제 중...")
            drop_table()
        
        # DM 테이블 생성
        create_dm_table()
        
        # 생성 확인
        verify_table()
        
        print("\n" + "="*60)
        print("✓ DM 구축 완료!")
        print("="*60)
        print(f"\n사용 예시:")
        print(f"  python {sys.argv[0]} --rebuild  # 테이블 재생성")
        
    except Exception as e:
        print(f"\n✗ DM 구축 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()