"""
파생 데이터 변환 및 생성
"""
import os
from sqlalchemy import text
from ..config import DM_SCHEMA


def create_derived_data(engine):
    """
    SQL로 파생 데이터 직접 계산 및 테이블 생성
    queries.sql 파일의 쿼리를 실행
    """
    print("\n" + "="*70)
    print("STEP 4: 파생 데이터 계산 및 derived_data 테이블 생성")
    print("="*70 + "\n")
    
    print("[생성 중] derived_data 테이블 (SQL 계산)...")
    
    # 현재 파일의 디렉토리 기준으로 queries.sql 경로 찾기
    current_dir = os.path.dirname(__file__)  # scripts/ 폴더
    parent_dir = os.path.dirname(current_dir)  # main_dm/ 폴더
    sql_file = os.path.join(parent_dir, 'queries.sql')
    
    # queries.sql 파일 읽기
    with open(sql_file, 'r', encoding='utf-8') as f:
        query = f.read()
    
    # 스키마 이름 치환
    query = query.replace('{{DM_SCHEMA}}', DM_SCHEMA)
    
    with engine.begin() as conn:
        # 기존 테이블 삭제
        conn.execute(text(f"DROP TABLE IF EXISTS {DM_SCHEMA}.derived_data CASCADE"))
        
        # SQL 실행
        conn.execute(text(query))
        
        # 행 수 확인
        result = conn.execute(text(f"SELECT COUNT(*) FROM {DM_SCHEMA}.derived_data"))
        row_count = result.scalar()
        
        print(f"  ✓ {DM_SCHEMA}.derived_data 생성 완료 ({row_count:,}행)")


def create_indexes(engine):
    """
    성능 최적화를 위한 인덱스 생성
    """
    print("\n[인덱스 생성] 성능 최적화...")
    
    with engine.begin() as conn:
        try:
            # derived_data 인덱스
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_derived_company 
                ON {DM_SCHEMA}.derived_data(company_sk)
            """))
            
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_derived_time 
                ON {DM_SCHEMA}.derived_data(time_sk)
            """))
            
            # 주요 비율 인덱스 (NULL 제외)
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_derived_r015 
                ON {DM_SCHEMA}.derived_data(r015) 
                WHERE r015 IS NOT NULL
            """))
            
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_derived_r006 
                ON {DM_SCHEMA}.derived_data(r006) 
                WHERE r006 IS NOT NULL
            """))
            
            print("  ✓ 인덱스 생성 완료")
            
        except Exception as e:
            print(f"  ⚠️ 인덱스 생성 실패: {e}")