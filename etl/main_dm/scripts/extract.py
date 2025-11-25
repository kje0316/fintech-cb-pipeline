"""
DWH 테이블 추출 및 DM으로 복사
"""
from sqlalchemy import text
from ..config import DWH_SCHEMA, DM_SCHEMA, TABLES_TO_COPY


def copy_dwh_tables_to_dm(engine):
    """
    DWH의 모든 테이블을 DM 스키마로 그대로 복사 (SQL 직접 실행 - 고속)
    """
    print("\n" + "="*70)
    print("STEP 1: DWH 테이블 → DM 스키마 복사")
    print("="*70 + "\n")
    
    # DM 스키마 생성
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DM_SCHEMA}"))
        print(f"✓ {DM_SCHEMA} 스키마 생성 완료")
    
    with engine.begin() as conn:
        for table_name in TABLES_TO_COPY:
            print(f"\n[복사 중] {table_name}...")
            
            # 기존 테이블 삭제
            conn.execute(text(f"DROP TABLE IF EXISTS {DM_SCHEMA}.{table_name} CASCADE"))
            
            # SQL로 직접 복사 (매우 빠름!)
            conn.execute(text(f"""
                CREATE TABLE {DM_SCHEMA}.{table_name} AS 
                SELECT * FROM {DWH_SCHEMA}.{table_name}
            """))
            
            # 행 수 확인
            result = conn.execute(text(f"SELECT COUNT(*) FROM {DM_SCHEMA}.{table_name}"))
            row_count = result.scalar()
            
            print(f"  ✓ {DM_SCHEMA}.{table_name} 생성 완료 ({row_count:,}행)")
    
    print("\n" + "="*70)
    print("✓ 모든 DWH 테이블 복사 완료")
    print("="*70)
