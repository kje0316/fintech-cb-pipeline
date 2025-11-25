"""
제약조건 추가
"""
from sqlalchemy import text
from ..config import DM_SCHEMA


def add_constraints_to_dm(engine):
    """
    DM 테이블들에 제약조건 추가 (DWH와 동일한 구조)
    - PK: Primary Key
    - FK: Foreign Key
    - NOT NULL: 필수 컬럼
    - UNIQUE: 비즈니스 키
    """
    print("\n" + "="*70)
    print("STEP 3: DM 테이블 제약조건 추가")
    print("="*70 + "\n")
    
    with engine.begin() as conn:
        try:
            print("[Dimension 테이블 제약조건 추가]")
            
            # ============================================
            # 1. dim_company 제약조건
            # ============================================
            print("\n[1/5] dim_company...")
            
            # PK 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.dim_company 
                ADD CONSTRAINT pk_dim_company PRIMARY KEY (company_sk)
            """))
            
            # UNIQUE 제약 (비즈니스 키)
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.dim_company 
                ADD CONSTRAINT uq_company_id UNIQUE (company_id)
            """))
            
            # NOT NULL 제약
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.dim_company 
                ALTER COLUMN company_sk SET NOT NULL,
                ALTER COLUMN company_id SET NOT NULL
            """))
            
            print("  ✓ PK, UNIQUE, NOT NULL 추가 완료")
            
            # ============================================
            # 2. dim_time 제약조건
            # ============================================
            print("\n[2/5] dim_time...")
            
            # PK 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.dim_time 
                ADD CONSTRAINT pk_dim_time PRIMARY KEY (time_sk)
            """))
            
            # NOT NULL 제약
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.dim_time 
                ALTER COLUMN time_sk SET NOT NULL,
                ALTER COLUMN bs_dt SET NOT NULL
            """))
            
            print("  ✓ PK, NOT NULL 추가 완료")
            
            # ============================================
            # 3. dim_industry 제약조건
            # ============================================
            print("\n[3/5] dim_industry...")
            
            # PK 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.dim_industry 
                ADD CONSTRAINT pk_dim_industry PRIMARY KEY (industry_sk)
            """))
            
            # UNIQUE 제약
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.dim_industry 
                ADD CONSTRAINT uq_industry_code UNIQUE (industry_code)
            """))
            
            # NOT NULL 제약
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.dim_industry 
                ALTER COLUMN industry_sk SET NOT NULL,
                ALTER COLUMN industry_code SET NOT NULL,
                ALTER COLUMN industry_name SET NOT NULL
            """))
            
            print("  ✓ PK, UNIQUE, NOT NULL 추가 완료")
            
            print("\n[Fact 테이블 제약조건 추가]")
            
            # ============================================
            # 4. fact_financial_statement 제약조건
            # ============================================
            print("\n[4/5] fact_financial_statement...")
            
            # PK 추가 (복합키)
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.fact_financial_statement 
                ADD CONSTRAINT pk_fact_financial PRIMARY KEY (company_sk, time_sk)
            """))
            
            # NOT NULL 제약
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.fact_financial_statement 
                ALTER COLUMN company_sk SET NOT NULL,
                ALTER COLUMN time_sk SET NOT NULL
            """))
            
            # FK 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.fact_financial_statement
                ADD CONSTRAINT fk_financial_company
                FOREIGN KEY (company_sk) REFERENCES {DM_SCHEMA}.dim_company(company_sk)
            """))
            
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.fact_financial_statement
                ADD CONSTRAINT fk_financial_time
                FOREIGN KEY (time_sk) REFERENCES {DM_SCHEMA}.dim_time(time_sk)
            """))
            
            print("  ✓ PK, FK, NOT NULL 추가 완료")
            
            # ============================================
            # 5. fact_credit_behavior 제약조건
            # ============================================
            print("\n[5/5] fact_credit_behavior...")
            
            # PK 추가 (복합키)
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.fact_credit_behavior 
                ADD CONSTRAINT pk_fact_credit PRIMARY KEY (company_sk, time_sk)
            """))
            
            # NOT NULL 제약
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.fact_credit_behavior 
                ALTER COLUMN company_sk SET NOT NULL,
                ALTER COLUMN time_sk SET NOT NULL
            """))
            
            # FK 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.fact_credit_behavior
                ADD CONSTRAINT fk_credit_company
                FOREIGN KEY (company_sk) REFERENCES {DM_SCHEMA}.dim_company(company_sk)
            """))
            
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.fact_credit_behavior
                ADD CONSTRAINT fk_credit_time
                FOREIGN KEY (time_sk) REFERENCES {DM_SCHEMA}.dim_time(time_sk)
            """))
            
            print("  ✓ PK, FK, NOT NULL 추가 완료")
            
            print("\n" + "="*70)
            print("✅ 모든 DM 테이블 제약조건 추가 완료")
            print("="*70)
            
        except Exception as e:
            print(f"\n❌ 제약조건 추가 중 오류: {e}")
            print("💡 팁: 데이터 품질 문제가 있을 수 있습니다. STEP 2 검증 결과를 확인하세요.")
            raise


def add_derived_data_constraints(engine):
    """
    derived_data 테이블에 제약조건 추가
    """
    print("\n[제약조건 추가] derived_data...")
    
    with engine.begin() as conn:
        try:
            # PK 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.derived_data 
                ADD CONSTRAINT pk_derived_data PRIMARY KEY (company_sk, time_sk)
            """))
            print("  ✓ PK 추가 완료")
            
            # NOT NULL 제약
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.derived_data 
                ALTER COLUMN company_sk SET NOT NULL,
                ALTER COLUMN time_sk SET NOT NULL
            """))
            print("  ✓ NOT NULL 추가 완료")
            
            # FK 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.derived_data
                ADD CONSTRAINT fk_derived_company
                FOREIGN KEY (company_sk) REFERENCES {DM_SCHEMA}.dim_company(company_sk)
            """))
            
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.derived_data
                ADD CONSTRAINT fk_derived_time
                FOREIGN KEY (time_sk) REFERENCES {DM_SCHEMA}.dim_time(time_sk)
            """))
            print("  ✓ FK 추가 완료")
            
        except Exception as e:
            print(f"  ⚠️ derived_data 제약조건 추가 실패: {e}")
            raise
