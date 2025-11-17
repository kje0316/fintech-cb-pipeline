"""
DWH → DM 파이프라인 (테이블 복사 + 파생 데이터)

목표:
1. DWH 테이블들을 DM으로 그대로 복사
   - dim_company
   - dim_industry
   - dim_time
   - fact_credit_behavior
   - fact_financial_statement
   
2. 파생 데이터는 derived_data 테이블에만 저장 (SQL로 직접 계산 - 초고속)
   - company_sk, time_sk (FK)
   - 파생 금액: fn1_13, fn1_24, fn2_5, fn2_10, ...
   - 파생 비율: r001, r006, r015, ...
   - 파생 지표: n001, n003, n005, ...
"""

from sqlalchemy import create_engine, text
from shared.config_loader import DB_URL


engine = create_engine(DB_URL, echo=False, future=True)

DWH_SCHEMA = "dwh2"
DM_SCHEMA = "dm"


# =============================================================
# STEP 1: DWH 테이블들을 DM으로 복사
# =============================================================

def copy_dwh_tables_to_dm():
    """
    DWH의 모든 테이블을 DM 스키마로 그대로 복사 (SQL 직접 실행 - 고속)
    """
    print("\n" + "="*70)
    print("STEP 1: DWH 테이블 → DM 스키마 복사 (고속 모드)")
    print("="*70 + "\n")
    
    # DM 스키마 생성
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DM_SCHEMA}"))
        print(f"✓ {DM_SCHEMA} 스키마 생성 완료")
    
    # 복사할 테이블 목록
    tables_to_copy = [
        'dim_company',
        'dim_industry',
        'dim_time',
        'fact_credit_behavior',
        'fact_financial_statement'
    ]
    
    with engine.begin() as conn:
        for table_name in tables_to_copy:
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


# =============================================================
# STEP 2: SQL로 파생 데이터 직접 계산 (초고속)
# =============================================================

def create_derived_data_in_sql():
    """
    SQL로 파생 데이터 직접 계산 및 테이블 생성 (Python 메모리 사용 없음, 초고속)
    """
    print("\n" + "="*70)
    print("STEP 2: 파생 데이터 계산 및 derived_data 테이블 생성 (SQL 직접 계산)")
    print("="*70 + "\n")
    
    print("[1/3] derived_data 테이블 생성 중 (SQL 계산)...")
    
    with engine.begin() as conn:
        # 기존 테이블 삭제
        conn.execute(text(f"DROP TABLE IF EXISTS {DM_SCHEMA}.derived_data CASCADE"))
        
        # SQL로 파생 데이터 직접 계산하여 테이블 생성
        conn.execute(text(f"""
        CREATE TABLE {DM_SCHEMA}.derived_data AS
        SELECT
            fs.company_sk,
            fs.time_sk,
            
            -- =============================
            -- 금액·규모 파생
            -- =============================
            
            -- fn1_10: 유동자산 합계
            (COALESCE(fs.fn1_7, 0) + COALESCE(fs.fn1_8, 0) + COALESCE(fs.fn1_9, 0)) AS fn1_10,
            
            -- fn1_13: 자산총계
            (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) AS fn1_13,
            
            -- fn1_19: 부채총계
            (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0)) AS fn1_19,
            
            -- fn1_24: 자본총계 = 자산총계 - 부채총계
            (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
            (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0)) AS fn1_24,
            
            -- fn2_2_1: 매출총이익 = 매출액 - 매출원가
            (COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0)) AS fn2_2_1,
            
            -- fn2_5: 영업이익 = 매출총이익 - 판관비
            (COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) AS fn2_5,
            
            -- fn2_3_1: 법인세차감전순이익
            ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
             COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) AS fn2_3_1,
            
            -- fn2_10: 당기순이익
            (((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
              COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) AS fn2_10,
            
            -- fn2_3_4: 당기순이익(계속사업)
            ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
               COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) - 
             COALESCE(fs.fn2_3_5, 0)) AS fn2_3_4,
            
            -- fn3_1: 감가상각비 총합
            (COALESCE(fs.fn3_2, 0) + COALESCE(fs.fn3_2_1, 0) + COALESCE(fs.fn3_2_2, 0)) AS fn3_1,
            
            -- fn3_11: 운전자본 = 유동자산 - 유동부채
            (COALESCE(fs.fn1_1, 0) - COALESCE(fs.fn1_14, 0)) AS fn3_11,
            
            -- fn3_11_1: 순운전자본 = 자기자본 - fn1_10
            (COALESCE(fs.fn1_16, 0) - 
             (COALESCE(fs.fn1_7, 0) + COALESCE(fs.fn1_8, 0) + COALESCE(fs.fn1_9, 0))) AS fn3_11_1,
            
            -- fn3_7: EBIT
            ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
             COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0) + COALESCE(fs.fn2_4, 0)) AS fn3_7,
            
            -- fn3_3: 자기자본회전율
            CASE 
                WHEN COALESCE(fs.fn3_2, 0) = 0 THEN NULL
                ELSE COALESCE(fs.fn1_16, 0) / NULLIF(fs.fn3_2, 0)
            END AS fn3_3,
            
            -- fn3_4: 영업이익률
            CASE 
                WHEN COALESCE(fs.fn2_4, 0) = 0 THEN NULL
                ELSE (COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) / NULLIF(fs.fn2_4, 0)
            END AS fn3_4,
            
            -- fn3_5: EBIT마진
            CASE 
                WHEN COALESCE(fs.fn2_4, 0) = 0 THEN NULL
                ELSE ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                      COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0) + COALESCE(fs.fn2_4, 0)) / NULLIF(fs.fn2_4, 0)
            END AS fn3_5,
            
            -- fn3_10: 이자보상배율
            CASE 
                WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
                ELSE (COALESCE(fs.fn3_10_1, 0) / NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
            END AS fn3_10,
            
            -- =============================
            -- 재무비율 (R 계열)
            -- =============================
            
            -- 성장성 비율
            -- r001: 자산증가율
            CASE 
                WHEN COALESCE(fs.fn1_13_1, 0) = 0 THEN NULL
                ELSE (((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - COALESCE(fs.fn1_13_1, 0)) / 
                      NULLIF(fs.fn1_13_1, 0)) * 100
            END AS r001,
            
            -- r002: 매출액증가율
            CASE 
                WHEN COALESCE(fs.fn2_1_1, 0) = 0 THEN NULL
                ELSE ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_1_1, 0)) / NULLIF(fs.fn2_1_1, 0)) * 100
            END AS r002,
            
            -- r003: 영업이익증가율
            CASE 
                WHEN COALESCE(fs.fn2_5_1, 0) = 0 THEN NULL
                ELSE (((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) - 
                       COALESCE(fs.fn2_5_1, 0)) / NULLIF(fs.fn2_5_1, 0)) * 100
            END AS r003,
            
            -- r004: 당기순이익증가율
            CASE 
                WHEN COALESCE(fs.fn2_10_1, 0) = 0 THEN NULL
                ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                        COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0) - 
                       COALESCE(fs.fn2_10_1, 0)) / NULLIF(fs.fn2_10_1, 0)) * 100
            END AS r004,
            
            -- 안정성 비율
            -- r006: 부채비율
            CASE 
                WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
                ELSE ((COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0)) / 
                      NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)) * 100
            END AS r006,
            
            -- r007: 자기자본비율
            CASE 
                WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
                ELSE (((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                       (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) / 
                      NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
            END AS r007,
            
            -- r008: 유동비율
            CASE 
                WHEN COALESCE(fs.fn1_14, 0) = 0 THEN NULL
                ELSE (COALESCE(fs.fn1_1, 0) / NULLIF(fs.fn1_14, 0)) * 100
            END AS r008,
            
            -- r009: 당좌비율
            CASE 
                WHEN COALESCE(fs.fn1_14, 0) = 0 THEN NULL
                ELSE (COALESCE(fs.fn1_3, 0) / NULLIF(fs.fn1_14, 0)) * 100
            END AS r009,
            
            -- r012: 자기자본순이익률
            CASE 
                WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
                ELSE (COALESCE(fs.fn1_16, 0) / NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
            END AS r012,
            
            -- 수익성 비율
            -- r013: 매출원가율
            CASE 
                WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
                ELSE (COALESCE(fs.fn2_2, 0) / NULLIF(fs.fn2_1, 0)) * 100
            END AS r013,
            
            -- r014: 판관비율
            CASE 
                WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
                ELSE (COALESCE(fs.fn2_3, 0) / NULLIF(fs.fn2_1, 0)) * 100
            END AS r014,
            
            -- r015: 영업이익률
            CASE 
                WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
                ELSE ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) / 
                      NULLIF(fs.fn2_1, 0)) * 100
            END AS r015,
            
            -- r016: 순이익률
            CASE 
                WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
                ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                        COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) / 
                      NULLIF(fs.fn2_1, 0)) * 100
            END AS r016,
            
            -- r018: ROE (자기자본순이익률)
            CASE 
                WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
                ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                        COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) / 
                      NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)) * 100
            END AS r018,
            
            -- r023: ROA (총자산순이익률)
            CASE 
                WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
                ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                        COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) / 
                      NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
            END AS r023,
            
            -- 활동성 비율
            -- r019: 총자산회전율
            CASE 
                WHEN COALESCE(fs.fn1_11, 0) = 0 THEN NULL
                ELSE COALESCE(fs.fn2_1, 0) / NULLIF(fs.fn1_11, 0)
            END AS r019,
            
            -- r020: 매출채권회전율
            CASE 
                WHEN COALESCE(fs.fn1_4, 0) = 0 THEN NULL
                ELSE COALESCE(fs.fn2_2, 0) / NULLIF(fs.fn1_4, 0)
            END AS r020,
            
            -- r021: 재고자산회전율
            CASE 
                WHEN COALESCE(fs.fn1_17, 0) = 0 THEN NULL
                ELSE COALESCE(fs.fn2_2, 0) / NULLIF(fs.fn1_17, 0)
            END AS r021,
            
            -- r022: 자기자본회전율
            CASE 
                WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
                ELSE COALESCE(fs.fn2_1, 0) / NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)
            END AS r022,
            
            -- =============================
            -- 추가 지표 (N 계열)
            -- =============================
            
            -- n001: 차입금의존도
            CASE 
                WHEN (COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) = 0 THEN NULL
                ELSE (COALESCE(fs.fn1_15, 0) / NULLIF((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)), 0)) * 100
            END AS n001,
            
            -- n002: 순운전자본비율
            CASE 
                WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
                ELSE ((COALESCE(fs.fn1_16, 0) - 
                       (COALESCE(fs.fn1_7, 0) + COALESCE(fs.fn1_8, 0) + COALESCE(fs.fn1_9, 0))) / 
                      NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)) * 100
            END AS n002,
            
            -- n003: 운전자본회전율
            CASE 
                WHEN (COALESCE(fs.fn1_1, 0) - COALESCE(fs.fn1_14, 0)) = 0 THEN NULL
                ELSE COALESCE(fs.fn2_1, 0) / NULLIF((COALESCE(fs.fn1_1, 0) - COALESCE(fs.fn1_14, 0)), 0)
            END AS n003,
            
            -- n004: 매출액순이익률
            CASE 
                WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
                ELSE ((((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0) - COALESCE(fs.fn2_3, 0)) + 
                        COALESCE(fs.fn2_7, 0) - COALESCE(fs.fn2_8, 0)) - COALESCE(fs.fn2_3_3, 0)) / 
                      NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                              (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)) * 100
            END AS n004,
            
            -- n005: 매출총이익률
            CASE 
                WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
                ELSE ((COALESCE(fs.fn2_1, 0) - COALESCE(fs.fn2_2, 0)) / NULLIF(fs.fn2_1, 0)) * 100
            END AS n005,
            
            -- n006: EBITDA마진
            CASE 
                WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
                ELSE (COALESCE(fs.fn3_8, 0) / NULLIF(fs.fn2_1, 0)) * 100
            END AS n006,
            
            -- n008: 감가상각비율
            CASE 
                WHEN COALESCE(fs.fn2_1, 0) = 0 THEN NULL
                ELSE COALESCE(fs.fn3_2, 0) / NULLIF(fs.fn2_1, 0)
            END AS n008,
            
            -- n010: EBITDA배수
            CASE 
                WHEN COALESCE(fs.fn3_8, 0) = 0 THEN NULL
                ELSE COALESCE(fs.fn1_16, 0) / NULLIF(fs.fn3_8, 0)
            END AS n010,
            
            -- n011: 이자비용비율
            CASE 
                WHEN COALESCE(fs.fn2_4, 0) = 0 THEN NULL
                ELSE COALESCE(fs.fn3_8, 0) / NULLIF(fs.fn2_4, 0)
            END AS n011,
            
            -- n012: 자기자본회전율2
            CASE 
                WHEN ((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                      (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))) = 0 THEN NULL
                ELSE COALESCE(fs.fn2_1, 0) / 
                     NULLIF(((COALESCE(fs.fn1_1, 0) + COALESCE(fs.fn1_2, 0)) - 
                             (COALESCE(fs.fn1_14, 0) + COALESCE(fs.fn1_18, 0))), 0)
            END AS n012
            
        FROM {DM_SCHEMA}.fact_financial_statement fs
        """))
        
        # 행 수 확인
        result = conn.execute(text(f"SELECT COUNT(*) FROM {DM_SCHEMA}.derived_data"))
        row_count = result.scalar()
        
        print(f"  ✓ {DM_SCHEMA}.derived_data 생성 완료 ({row_count:,}행)")


def create_foreign_keys():
    """
    derived_data 테이블에 외래키 제약 추가
    """
    print("\n[2/3] 외래키 제약 추가 중...")
    
    with engine.begin() as conn:
        try:
            # 기본키 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.derived_data 
                ADD PRIMARY KEY (company_sk, time_sk)
            """))
            print("  ✓ 기본키 추가 완료")
            
            # 외래키 추가
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.derived_data
                ADD CONSTRAINT fk_derived_company
                FOREIGN KEY (company_sk) REFERENCES {DM_SCHEMA}.dim_company(company_sk)
            """))
            print("  ✓ company_sk 외래키 추가 완료")
            
            conn.execute(text(f"""
                ALTER TABLE {DM_SCHEMA}.derived_data
                ADD CONSTRAINT fk_derived_time
                FOREIGN KEY (time_sk) REFERENCES {DM_SCHEMA}.dim_time(time_sk)
            """))
            print("  ✓ time_sk 외래키 추가 완료")
            
        except Exception as e:
            print(f"  ⚠ 외래키 추가 실패 (이미 존재할 수 있음): {e}")


def create_indexes():
    """
    성능 최적화를 위한 인덱스 생성
    """
    print("\n[3/3] 인덱스 생성 중...")
    
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
            print(f"  ⚠ 인덱스 생성 실패: {e}")


# =============================================================
# MAIN
# =============================================================

def main():
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*20 + "DWH → DM 구축 시작" + " "*28 + "║")
    print("║" + " "*18 + "(SQL 직접 계산 모드)" + " "*28 + "║")
    print("╚" + "="*68 + "╝")
    
    
    # ===== STEP 1: DWH 테이블 복사 =====
    copy_dwh_tables_to_dm()
    
    
    # ===== STEP 2: SQL로 파생 데이터 직접 생성 =====
    create_derived_data_in_sql()
    
    
    # ===== STEP 3: 제약/인덱스 추가 =====
    create_foreign_keys()
    create_indexes()
    
    
    # ===== 완료 =====
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*20 + "✓ DM 구축 완료!" + " "*30 + "║")
    print("╚" + "="*68 + "╝")
    
    print("\n생성된 테이블:")
    print(f"  - {DM_SCHEMA}.dim_company")
    print(f"  - {DM_SCHEMA}.dim_industry")
    print(f"  - {DM_SCHEMA}.dim_time")
    print(f"  - {DM_SCHEMA}.fact_credit_behavior")
    print(f"  - {DM_SCHEMA}.fact_financial_statement")
    print(f"  - {DM_SCHEMA}.derived_data ⭐ (파생 데이터 - SQL 직접 계산)")
    
    print("\n조회 예시:")
    print(f"""
    -- 파생 데이터 조회
    SELECT * FROM {DM_SCHEMA}.derived_data LIMIT 10;
    
    -- 원시 + 파생 조인
    SELECT 
        fs.fn1_1, fs.fn2_1,  -- 원시 데이터
        dd.fn1_13, dd.r015   -- 파생 데이터
    FROM {DM_SCHEMA}.fact_financial_statement fs
    JOIN {DM_SCHEMA}.derived_data dd 
        ON fs.company_sk = dd.company_sk 
        AND fs.time_sk = dd.time_sk
    LIMIT 10;
    """)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()