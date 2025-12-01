"""
PostgreSQL 제약조건 추가
DM 스키마에 PRIMARY KEY, FOREIGN KEY 추가
"""
from shared.config_loader import DB_URL
from urllib.parse import urlparse
import psycopg2


def add_constraints():
    """
    DM 테이블들에 제약조건 추가
    - PK: Primary Key
    - FK: Foreign Key
    - NOT NULL: 필수 컬럼
    - UNIQUE: 비즈니스 키
    """
    print("\n" + "="*70)
    print("PostgreSQL 제약조건 추가")
    print("="*70 + "\n")
    
    # DB 연결
    result = urlparse(DB_URL)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    
    cursor = conn.cursor()
    
    try:
        print("[Dimension 테이블 제약조건 추가]")
        
        # ============================================
        # 1. dim_company 제약조건
        # ============================================
        print("\n[1/5] dim_company...")
        
        try:
            # PK 추가
            cursor.execute("""
                ALTER TABLE dm.dim_company 
                ADD CONSTRAINT pk_dim_company PRIMARY KEY (company_sk);
            """)
            print("  ✓ PK 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ PK (이미 존재)")
            else:
                raise
        
        try:
            # UNIQUE 제약 (비즈니스 키)
            cursor.execute("""
                ALTER TABLE dm.dim_company 
                ADD CONSTRAINT uq_company_id UNIQUE (company_id);
            """)
            print("  ✓ UNIQUE 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ UNIQUE (이미 존재)")
            else:
                raise
        
        try:
            # NOT NULL 제약
            cursor.execute("""
                ALTER TABLE dm.dim_company 
                ALTER COLUMN company_sk SET NOT NULL,
                ALTER COLUMN company_id SET NOT NULL;
            """)
            print("  ✓ NOT NULL 추가")
        except Exception as e:
            if "not-null constraint" in str(e).lower():
                print("  ℹ NOT NULL (이미 존재)")
            else:
                raise
        
        conn.commit()
        
        # ============================================
        # 2. dim_time 제약조건
        # ============================================
        print("\n[2/5] dim_time...")
        
        try:
            cursor.execute("""
                ALTER TABLE dm.dim_time 
                ADD CONSTRAINT pk_dim_time PRIMARY KEY (time_sk);
            """)
            print("  ✓ PK 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ PK (이미 존재)")
            else:
                raise
        
        try:
            # NOT NULL 제약
            cursor.execute("""
                ALTER TABLE dm.dim_time 
                ALTER COLUMN time_sk SET NOT NULL,
                ALTER COLUMN bs_dt SET NOT NULL;
            """)
            print("  ✓ NOT NULL 추가")
        except Exception as e:
            if "not-null constraint" in str(e).lower():
                print("  ℹ NOT NULL (이미 존재)")
            else:
                raise
        
        conn.commit()
        
        # ============================================
        # 3. dim_industry 제약조건
        # ============================================
        print("\n[3/5] dim_industry...")
        
        try:
            cursor.execute("""
                ALTER TABLE dm.dim_industry 
                ADD CONSTRAINT pk_dim_industry PRIMARY KEY (industry_sk);
            """)
            print("  ✓ PK 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ PK (이미 존재)")
            else:
                raise
        
        try:
            cursor.execute("""
                ALTER TABLE dm.dim_industry 
                ADD CONSTRAINT uq_industry_code UNIQUE (industry_code);
            """)
            print("  ✓ UNIQUE 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ UNIQUE (이미 존재)")
            else:
                raise
        
        try:
            # NOT NULL 제약
            cursor.execute("""
                ALTER TABLE dm.dim_industry 
                ALTER COLUMN industry_sk SET NOT NULL,
                ALTER COLUMN industry_code SET NOT NULL,
                ALTER COLUMN industry_name SET NOT NULL;
            """)
            print("  ✓ NOT NULL 추가")
        except Exception as e:
            if "not-null constraint" in str(e).lower():
                print("  ℹ NOT NULL (이미 존재)")
            else:
                raise
        
        conn.commit()
        
        print("\n[Fact 테이블 제약조건 추가]")
        
        # ============================================
        # 4. fact_financial_statement 제약조건
        # ============================================
        print("\n[4/5] fact_financial_statement...")
        
        try:
            # PK 추가 (복합키)
            cursor.execute("""
                ALTER TABLE dm.fact_financial_statement 
                ADD CONSTRAINT pk_fact_financial PRIMARY KEY (company_sk, time_sk);
            """)
            print("  ✓ PK 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ PK (이미 존재)")
            else:
                raise
        
        try:
            # NOT NULL 제약
            cursor.execute("""
                ALTER TABLE dm.fact_financial_statement 
                ALTER COLUMN company_sk SET NOT NULL,
                ALTER COLUMN time_sk SET NOT NULL;
            """)
            print("  ✓ NOT NULL 추가")
        except Exception as e:
            if "not-null constraint" in str(e).lower():
                print("  ℹ NOT NULL (이미 존재)")
            else:
                raise
        
        try:
            # FK 추가
            cursor.execute("""
                ALTER TABLE dm.fact_financial_statement
                ADD CONSTRAINT fk_financial_company
                FOREIGN KEY (company_sk) REFERENCES dm.dim_company(company_sk);
            """)
            print("  ✓ FK company 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ FK company (이미 존재)")
            else:
                raise
        
        try:
            cursor.execute("""
                ALTER TABLE dm.fact_financial_statement
                ADD CONSTRAINT fk_financial_time
                FOREIGN KEY (time_sk) REFERENCES dm.dim_time(time_sk);
            """)
            print("  ✓ FK time 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ FK time (이미 존재)")
            else:
                raise
        
        conn.commit()
        
        # ============================================
        # 5. fact_credit_behavior 제약조건
        # ============================================
        print("\n[5/5] fact_credit_behavior...")
        
        try:
            cursor.execute("""
                ALTER TABLE dm.fact_credit_behavior 
                ADD CONSTRAINT pk_fact_credit PRIMARY KEY (company_sk, time_sk);
            """)
            print("  ✓ PK 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ PK (이미 존재)")
            else:
                raise
        
        try:
            # NOT NULL 제약
            cursor.execute("""
                ALTER TABLE dm.fact_credit_behavior 
                ALTER COLUMN company_sk SET NOT NULL,
                ALTER COLUMN time_sk SET NOT NULL;
            """)
            print("  ✓ NOT NULL 추가")
        except Exception as e:
            if "not-null constraint" in str(e).lower():
                print("  ℹ NOT NULL (이미 존재)")
            else:
                raise
        
        try:
            cursor.execute("""
                ALTER TABLE dm.fact_credit_behavior
                ADD CONSTRAINT fk_credit_company
                FOREIGN KEY (company_sk) REFERENCES dm.dim_company(company_sk);
            """)
            print("  ✓ FK company 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ FK company (이미 존재)")
            else:
                raise
        
        try:
            cursor.execute("""
                ALTER TABLE dm.fact_credit_behavior
                ADD CONSTRAINT fk_credit_time
                FOREIGN KEY (time_sk) REFERENCES dm.dim_time(time_sk);
            """)
            print("  ✓ FK time 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ FK time (이미 존재)")
            else:
                raise
        
        conn.commit()
        
        # ============================================
        # 6. derived_data 제약조건
        # ============================================
        print("\n[6/6] derived_data...")
        
        try:
            cursor.execute("""
                ALTER TABLE dm.derived_data 
                ADD CONSTRAINT pk_derived_data PRIMARY KEY (company_sk, time_sk);
            """)
            print("  ✓ PK 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ PK (이미 존재)")
            else:
                raise
        
        try:
            # NOT NULL 제약
            cursor.execute("""
                ALTER TABLE dm.derived_data 
                ALTER COLUMN company_sk SET NOT NULL,
                ALTER COLUMN time_sk SET NOT NULL;
            """)
            print("  ✓ NOT NULL 추가")
        except Exception as e:
            if "not-null constraint" in str(e).lower():
                print("  ℹ NOT NULL (이미 존재)")
            else:
                raise
        
        try:
            cursor.execute("""
                ALTER TABLE dm.derived_data
                ADD CONSTRAINT fk_derived_company
                FOREIGN KEY (company_sk) REFERENCES dm.dim_company(company_sk);
            """)
            print("  ✓ FK company 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ FK company (이미 존재)")
            else:
                raise
        
        try:
            cursor.execute("""
                ALTER TABLE dm.derived_data
                ADD CONSTRAINT fk_derived_time
                FOREIGN KEY (time_sk) REFERENCES dm.dim_time(time_sk);
            """)
            print("  ✓ FK time 추가")
        except Exception as e:
            if "already exists" in str(e):
                print("  ℹ FK time (이미 존재)")
            else:
                raise
        
        conn.commit()
        
        print("\n" + "="*70)
        print("✅ 모든 DM 테이블 제약조건 추가 완료")
        print("="*70)
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 제약조건 추가 중 오류: {e}")
        print("💡 팁: 데이터 품질 문제가 있을 수 있습니다.")
        raise
    
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # 직접 실행 시
    add_constraints()