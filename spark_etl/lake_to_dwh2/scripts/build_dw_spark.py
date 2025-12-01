# build_dw_spark.py

import os
import yaml
from pyspark.sql.functions import col, to_date, lower as spark_lower
from spark_etl.lake_to_dwh2.scripts.extract_spark import extract_data, extract_from_lake
from spark_etl.lake_to_dwh2.scripts.cleansing_spark import cleanse_data
from spark_etl.lake_to_dwh2.scripts.load_to_postgres_spark import (
    load_data, create_schema, load_table_from_db, get_spark_session
)
from spark_etl.lake_to_dwh2.scripts.load_to_postgres_spark import get_spark_session

RAW_DATA_PATH = './data/기업신용평가정보_합성데이터.csv'
COLUMN_REFERENCE_PATH = './data/202109_기업CB.csv'
COL_TYPES_PATH = './config/col_types.yaml'
DW_COLUMNS_PATH = './config/dw_columns2.yaml'
SCHEMA_SQL_PATH = './etl/lake_to_dwh2/schema_dwh2.sql'


def create_dims(df, dw_columns):
    """
    Spark DataFrame에서 차원 테이블들을 생성하고 DB에 저장
    """
    print("차원 테이블 생성 중...")
    

    spark = get_spark_session()

    # === 1. dim_company 생성 ===
    company_cols = list(dict.fromkeys(dw_columns['dims']['dim_company']))
    
    # 원본 데이터에 없는 컬럼은 제외, COMPANY_SK는 DB에서 생성되므로 제외
    company_defining_cols = [
        c for c in company_cols 
        if c in df.columns and c.upper() != 'COMPANY_SK'
    ]
    
    # 컬럼 선택 및 중복 제거
    dim_company_to_load = df.select(*company_defining_cols).dropDuplicates()
    
    # 컬럼명 소문자로 변경
    for column in dim_company_to_load.columns:
        dim_company_to_load = dim_company_to_load.withColumnRenamed(
            column, column.lower()
        )

    load_data(dim_company_to_load, 'dwh2.dim_company')
    print("dim_company 생성 및 저장 완료.")

    dim_company = load_table_from_db('dwh2.dim_company', COL_TYPES_PATH)

    # === 2. dim_time 생성 ===
    time_cols = list(dict.fromkeys(dw_columns['dims']['dim_time']))
    time_defining_cols = [
        c for c in time_cols 
        if c in df.columns and c.upper() != 'TIME_SK'
    ]

    if not all(c in df.columns for c in time_defining_cols):
        raise ValueError(f"Time dimension을 정의하는 컬럼이 원본 데이터에 없습니다: {time_defining_cols}")

    dim_time_to_load = df.select(*time_defining_cols).dropDuplicates()
    
    # 컬럼명 소문자로 변경
    for column in dim_time_to_load.columns:
        dim_time_to_load = dim_time_to_load.withColumnRenamed(
            column, column.lower()
        )

    load_data(dim_time_to_load, 'dwh2.dim_time')
    print("dim_time 생성 및 저장 완료.")

    dim_time = load_table_from_db('dwh2.dim_time', COL_TYPES_PATH)

    # === 3. dim_industry 생성 ===
    print("dim_industry 생성 중...")

    # shared/config_loader에서 industry_codes 경로 가져오기
    from shared.config_loader import config
    industry_csv_path = config['paths']['industry_codes']

    # CSV 파일 읽기
    industry_df = spark.read \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .option("encoding", "UTF-8") \
        .csv(industry_csv_path)
    
    # 컬럼명 소문자로 변경
    for column in industry_df.columns:
        industry_df = industry_df.withColumnRenamed(column, column.lower())

    # industry_sk는 DB에서 자동 생성되므로 제외
    dim_industry_to_load = industry_df.select('industry_code', 'industry_name')

    load_data(dim_industry_to_load, 'dwh2.dim_industry')
    print("dim_industry 생성 및 저장 완료.")

    dim_industry = load_table_from_db('dwh2.dim_industry', COL_TYPES_PATH)

    print("차원 테이블 생성 완료.")
    return dim_company, dim_time, dim_industry


def create_facts(df, dim_company, dim_time, dw_columns):
    """
    Spark DataFrame과 차원 테이블들을 이용해 팩트 테이블들을 생성하고 DB에 저장
    """
    
    # 컬럼명 소문자로 통일
    for column in df.columns:
        df = df.withColumnRenamed(column, column.lower())
    
    for column in dim_company.columns:
        dim_company = dim_company.withColumnRenamed(column, column.lower())
    
    for column in dim_time.columns:
        dim_time = dim_time.withColumnRenamed(column, column.lower())

    print("팩트 테이블 생성 중...")

    # 날짜 컬럼 변환
    date_cols = ['fndt_dt', 'listd_dt', 'listd_abol_dt']
    for col_name in date_cols:
        if col_name in dim_company.columns:
            dim_company = dim_company.withColumn(
                col_name,
                to_date(col(col_name))
            )

   # Company merge keys - COMPANY_ID만 사용
    company_defining_cols = ['company_id']

    # Time merge keys
    time_defining_cols = ['bs_dt']

    # Time merge keys
    common_time_cols = list(set(df.columns) & set(dim_time.columns))
    time_defining_cols = [c for c in common_time_cols if c.upper() != 'TIME_SK']

    print(f"Company Merge Keys: {company_defining_cols}")
    print(f"Time Merge Keys: {time_defining_cols}")

    # bs_dt 날짜 변환
    if 'bs_dt' in df.columns and 'bs_dt' in dim_time.columns:
        df = df.withColumn('bs_dt', to_date(col('bs_dt')))
        dim_time = dim_time.withColumn('bs_dt', to_date(col('bs_dt')))

    # Company dimension과 조인
    df_merged = df.join(
        dim_company.select('company_id', 'company_sk'),
        on='company_id',
        how='left'
    )

    # Time dimension과 조인
    df_merged = df_merged.join(
        dim_time.select('bs_dt', 'time_sk'),
        on='bs_dt',
        how='left'
    )

    # NULL 체크 및 필터링
    null_company = df_merged.filter(col('company_sk').isNull()).count()
    null_time = df_merged.filter(col('time_sk').isNull()).count()

    if null_company > 0:
        print(f"  ⚠️ 경고: {null_company}개 행의 company_sk가 NULL입니다. 제거...")
        df_merged = df_merged.filter(col('company_sk').isNotNull())

    if null_time > 0:
        print(f"  ⚠️ 경고: {null_time}개 행의 time_sk가 NULL입니다. 제거...")
        df_merged = df_merged.filter(col('time_sk').isNotNull())

    # 팩트 테이블 생성
    for fact_name, fact_cols in dw_columns['facts'].items():
        fact_cols_lower = [c.lower() for c in fact_cols]
        cols_to_select = ['company_sk', 'time_sk'] + fact_cols_lower
        
        # 존재하는 컬럼만 선택
        existing_cols = [c for c in cols_to_select if c in df_merged.columns]

        fact_df = df_merged.select(*existing_cols).dropDuplicates()

        load_data(fact_df, f'dwh2.{fact_name}')

        print(f"{fact_name} 생성 및 저장 완료.")
        fact_df.show(3)
        print(f"Shape: ({fact_df.count()}, {len(fact_df.columns)})")
    
    print("팩트 테이블 생성 완료.")
