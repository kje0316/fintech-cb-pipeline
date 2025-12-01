"""
파생 데이터 변환 및 생성 (Spark 버전)
"""
import os
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from ..config import DM_SCHEMA, PARTITION_CONFIGS


def create_derived_data(spark: SparkSession, fact_df: DataFrame) -> DataFrame:
    """
    Spark SQL로 파생 데이터 직접 계산
    기존 queries.sql 파일의 쿼리를 재사용
    
    Parameters:
    -----------
    spark : SparkSession
        Spark 세션
    fact_df : DataFrame
        fact_financial_statement DataFrame
    
    Returns:
    --------
    DataFrame
        파생 데이터 DataFrame
    """
    print("\n" + "="*70)
    print("STEP 4: 파생 데이터 계산 및 derived_data 생성 (Spark SQL)")
    print("="*70 + "\n")
    
    print("[생성 중] derived_data (Spark SQL 기반)...")
    
    # fact_financial_statement를 임시 뷰로 등록
    fact_df.createOrReplaceTempView("fact_financial_statement")
    
    # 현재 파일의 디렉토리 기준으로 queries.sql 경로 찾기
    current_dir = os.path.dirname(__file__)  # scripts/ 폴더
    parent_dir = os.path.dirname(current_dir)  # main_dm/ 폴더
    sql_file = os.path.join(parent_dir, 'queries.sql')
    
    # queries.sql 파일 읽기
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            query = f.read()
    except FileNotFoundError:
        print(f"⚠️ queries.sql 파일을 찾을 수 없습니다: {sql_file}")
        print("기본 파생 데이터 로직을 사용합니다.")
        return _create_derived_data_fallback(fact_df)
    
    # SQL 쿼리 전처리
    # 1. CREATE TABLE 부분 제거
    query = query.replace(f'CREATE TABLE {{{{DM_SCHEMA}}}}.derived_data AS', '')
    query = query.replace(f'CREATE TABLE {DM_SCHEMA}.derived_data AS', '')
    
    # 2. 스키마 프리픽스 제거
    query = query.replace('{{DM_SCHEMA}}.fact_financial_statement', 'fact_financial_statement')
    query = query.replace(f'{DM_SCHEMA}.fact_financial_statement', 'fact_financial_statement')
    
    # Spark SQL 실행
    derived_df = spark.sql(query)
    
    # 통계 출력
    row_count = derived_df.count()
    col_count = len(derived_df.columns)
    
    print(f"  ✓ derived_data 생성 완료: {row_count:,}행 x {col_count}컬럼")
    
    # 주요 컬럼 확인
    print("\n주요 파생 컬럼 (처음 20개):")
    for i, field in enumerate(derived_df.schema.fields[:20], 1):
        print(f"  {i:2d}. {field.name:15s} : {field.dataType}")
    
    if col_count > 20:
        print(f"  ... 외 {col_count - 20}개 컬럼")
    
    return derived_df


def _create_derived_data_fallback(fact_df: DataFrame) -> DataFrame:
    """
    queries.sql이 없을 때 사용하는 기본 파생 데이터 생성
    (간단한 예시만 포함)
    
    Parameters:
    -----------
    fact_df : DataFrame
        fact_financial_statement DataFrame
    
    Returns:
    --------
    DataFrame
        파생 데이터 DataFrame
    """
    print("  기본 파생 데이터 로직 사용 (간단한 비율만 계산)")
    
    derived_df = fact_df.select(
        'company_sk',
        'time_sk',
        
        # fn1_13: 자산총계
        (F.coalesce('fn1_1', F.lit(0)) + 
         F.coalesce('fn1_2', F.lit(0))).alias('fn1_13'),
        
        # r006: 부채비율
        F.when(
            ((F.coalesce('fn1_1', F.lit(0)) + F.coalesce('fn1_2', F.lit(0))) -
             (F.coalesce('fn1_14', F.lit(0)) + F.coalesce('fn1_18', F.lit(0)))) == 0,
            F.lit(None)
        ).otherwise(
            ((F.coalesce('fn1_14', F.lit(0)) + F.coalesce('fn1_18', F.lit(0))) /
             ((F.coalesce('fn1_1', F.lit(0)) + F.coalesce('fn1_2', F.lit(0))) -
              (F.coalesce('fn1_14', F.lit(0)) + F.coalesce('fn1_18', F.lit(0))))) * 100
        ).alias('r006'),
        
        # r015: 영업이익률
        F.when(
            F.coalesce('fn2_1', F.lit(0)) == 0,
            F.lit(None)
        ).otherwise(
            ((F.coalesce('fn2_1', F.lit(0)) - 
              F.coalesce('fn2_2', F.lit(0)) - 
              F.coalesce('fn2_3', F.lit(0))) /
             F.coalesce('fn2_1', F.lit(0))) * 100
        ).alias('r015')
    )
    
    print("  ⚠️ 전체 파생 컬럼을 위해 queries.sql 파일을 제공해주세요!")
    
    return derived_df


def create_indexes(spark: SparkSession, dataframes: dict):
    """
    성능 최적화를 위한 인덱스 생성
    
    Spark/Delta Lake는 전통적인 인덱스 대신 파티셔닝을 사용합니다.
    이 함수는 호환성을 위해 유지하지만 실제로는 파티셔닝 정보만 출력합니다.
    
    Parameters:
    -----------
    spark : SparkSession
        Spark 세션
    dataframes : dict
        {table_name: DataFrame} 딕셔너리
    """
    print("\n[파티셔닝 정보] 성능 최적화...")
    
    print("\n⚠️ 참고: Spark/Delta Lake는 전통적인 인덱스 대신 파티셔닝을 사용합니다.")
    
    if PARTITION_CONFIGS:
        print("\n설정된 파티셔닝:")
        for table_name, partition_cols in PARTITION_CONFIGS.items():
            if table_name in dataframes:
                print(f"  - {table_name}: {', '.join(partition_cols)}")
    else:
        print("  파티셔닝 설정 없음")
    
    print("\n💡 파티셔닝은 데이터 저장 시(write) 자동으로 적용됩니다.")
    print("  ✓ 성능 최적화 정보 출력 완료")
