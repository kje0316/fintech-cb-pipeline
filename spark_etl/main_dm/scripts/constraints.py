"""
제약조건 추가 (Spark 버전)
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from typing import Dict
from ..config import EXECUTION_MODE, DM_SCHEMA


def add_constraints_to_dm(spark: SparkSession, dataframes: Dict[str, DataFrame]):
    """
    DM 테이블들에 제약조건 추가
    
    Spark/Delta Lake는 PK, FK, UNIQUE를 직접 지원하지 않으므로
    검증 로직으로 대체
    
    Parameters:
    -----------
    spark : SparkSession
        Spark 세션
    dataframes : dict
        {table_name: DataFrame} 딕셔너리
    """
    print("\n" + "="*70)
    print("STEP 3: DM 테이블 제약조건 검증")
    print("="*70 + "\n")
    
    print("⚠️ 참고: Spark/Delta Lake는 PK, FK, UNIQUE 제약을 직접 지원하지 않습니다.")
    print("대신 데이터 쓰기 전 검증 로직으로 제약조건을 보장합니다.\n")
    
    # EXECUTION_MODE가 'hybrid'인 경우 PostgreSQL에 제약조건 추가 가능
    if EXECUTION_MODE == "hybrid":
        print("💡 Hybrid 모드: PostgreSQL에 저장 후 ALTER TABLE로 제약조건 추가 가능")
        print("   (run_pipeline.py에서 처리)\n")
    
    # ============================================
    # 1. dim_company 검증
    # ============================================
    print("[1/5] dim_company 제약조건 검증...")
    
    if 'dim_company' in dataframes:
        df = dataframes['dim_company']
        
        # PK 검증 (NOT NULL + UNIQUE)
        pk_validation = _validate_primary_key(df, ['company_sk'])
        
        # UNIQUE 검증 (company_id)
        unique_validation = _validate_unique(df, 'company_id')
        
        if pk_validation and unique_validation:
            print("  ✓ PK, UNIQUE 검증 통과")
        else:
            raise ValueError("dim_company 제약조건 검증 실패")
    
    # ============================================
    # 2. dim_time 검증
    # ============================================
    print("\n[2/5] dim_time 제약조건 검증...")
    
    if 'dim_time' in dataframes:
        df = dataframes['dim_time']
        
        pk_validation = _validate_primary_key(df, ['time_sk'])
        
        if pk_validation:
            print("  ✓ PK 검증 통과")
        else:
            raise ValueError("dim_time 제약조건 검증 실패")
    
    # ============================================
    # 3. dim_industry 검증
    # ============================================
    print("\n[3/5] dim_industry 제약조건 검증...")
    
    if 'dim_industry' in dataframes:
        df = dataframes['dim_industry']
        
        pk_validation = _validate_primary_key(df, ['industry_sk'])
        unique_validation = _validate_unique(df, 'industry_code')
        
        if pk_validation and unique_validation:
            print("  ✓ PK, UNIQUE 검증 통과")
        else:
            raise ValueError("dim_industry 제약조건 검증 실패")
    
    # ============================================
    # 4. fact_financial_statement 검증
    # ============================================
    print("\n[4/5] fact_financial_statement 제약조건 검증...")
    
    if 'fact_financial_statement' in dataframes:
        df = dataframes['fact_financial_statement']
        
        # 복합 PK 검증
        pk_validation = _validate_primary_key(df, ['company_sk', 'time_sk'])
        
        if pk_validation:
            print("  ✓ PK 검증 통과")
        else:
            raise ValueError("fact_financial_statement 제약조건 검증 실패")
    
    # ============================================
    # 5. fact_credit_behavior 검증
    # ============================================
    print("\n[5/5] fact_credit_behavior 제약조건 검증...")
    
    if 'fact_credit_behavior' in dataframes:
        df = dataframes['fact_credit_behavior']
        
        pk_validation = _validate_primary_key(df, ['company_sk', 'time_sk'])
        
        if pk_validation:
            print("  ✓ PK 검증 통과")
        else:
            raise ValueError("fact_credit_behavior 제약조건 검증 실패")
    
    print("\n" + "="*70)
    print("✅ 모든 DM 테이블 제약조건 검증 완료")
    print("="*70)


def add_derived_data_constraints(spark: SparkSession, derived_df: DataFrame):
    """
    derived_data 테이블에 제약조건 검증
    
    Parameters:
    -----------
    spark : SparkSession
        Spark 세션
    derived_df : DataFrame
        derived_data DataFrame
    """
    print("\n[제약조건 검증] derived_data...")
    
    # PK 검증 (복합키)
    pk_validation = _validate_primary_key(derived_df, ['company_sk', 'time_sk'])
    
    if pk_validation:
        print("  ✓ PK 검증 통과")
    else:
        raise ValueError("derived_data 제약조건 검증 실패")


def _validate_primary_key(df: DataFrame, pk_columns: list) -> bool:
    """
    Primary Key 검증 (NOT NULL + UNIQUE)
    
    Parameters:
    -----------
    df : DataFrame
        검증할 DataFrame
    pk_columns : list
        PK 컬럼 목록
    
    Returns:
    --------
    bool
        검증 통과 시 True
    """
    # 1. NOT NULL 체크
    null_condition = F.lit(False)
    for col in pk_columns:
        null_condition = null_condition | F.col(col).isNull()
    
    null_count = df.filter(null_condition).count()
    
    if null_count > 0:
        print(f"    ❌ PK NULL 발견: {null_count}건")
        return False
    
    # 2. UNIQUE 체크 (중복 체크)
    duplicates = df.groupBy(*pk_columns).count().filter(F.col('count') > 1)
    dup_count = duplicates.count()
    
    if dup_count > 0:
        print(f"    ❌ PK 중복 발견: {dup_count}건")
        return False
    
    return True


def _validate_unique(df: DataFrame, column: str) -> bool:
    """
    UNIQUE 제약 검증
    
    Parameters:
    -----------
    df : DataFrame
        검증할 DataFrame
    column : str
        UNIQUE 컬럼
    
    Returns:
    --------
    bool
        검증 통과 시 True
    """
    # NULL 제외하고 중복 체크
    duplicates = (
        df.filter(F.col(column).isNotNull())
          .groupBy(column)
          .count()
          .filter(F.col('count') > 1)
    )
    
    dup_count = duplicates.count()
    
    if dup_count > 0:
        print(f"    ❌ UNIQUE 제약 위반 ({column}): {dup_count}건")
        return False
    
    return True
