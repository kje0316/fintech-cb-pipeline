# build_dw.py

import os
import yaml
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from etl.lake_to_dwh.scripts.extract import extract_data
from etl.lake_to_dwh.scripts.cleansing import cleanse_data
from etl.lake_to_dwh.scripts.load_to_postgres import load_data, create_schema, load_table_from_db

RAW_DATA_PATH = './data/기업신용평가정보_합성데이터.csv'
COLUMN_REFERENCE_PATH = './data/202109_기업CB.csv'
COL_TYPES_PATH = './config/col_types.yaml'
DW_COLUMNS_PATH = './config/dw_columns.yaml'
SCHEMA_SQL_PATH = './etl/lake_to_dwh/schema.sql'

def create_dims(df, dw_columns):
    """
    데이터프레임에서 차원 테이블들을 생성하고 DB에 저장
    """
    print("차원 테이블 생성 중...")

    # === 1. dim_company 생성 ===
    company_cols = list(dict.fromkeys(dw_columns['dims']['dim_company']))
    # 원본 데이터에 없는 컬럼은 제외, COMPANY_SK는 DB에서 생성되므로 제외
    company_defining_cols = [col for col in company_cols if col in df.columns and col.upper() != 'COMPANY_SK']
    dim_company_to_load = df[company_defining_cols].copy().drop_duplicates()
    dim_company_to_load.columns = dim_company_to_load.columns.str.lower()

    load_data(dim_company_to_load, 'dwh.dim_company')
    print("dim_company 생성 및 저장 완료.")

    dim_company = load_table_from_db('dwh.dim_company', COL_TYPES_PATH)


    # === 2. dim_time 생성 ===
    time_cols = list(dict.fromkeys(dw_columns['dims']['dim_time']))
    time_defining_cols = [col for col in time_cols if col in df.columns and col.upper() != 'TIME_SK']

    if not all(col in df.columns for col in time_defining_cols):
        raise ValueError(f"Time dimension을 정의하는 컬럼이 원본 데이터에 없습니다: {time_defining_cols}")

    dim_time_to_load = df[time_defining_cols].copy().drop_duplicates()
    dim_time_to_load.columns = dim_time_to_load.columns.str.lower()

    load_data(dim_time_to_load, 'dwh.dim_time')
    print("dim_time 생성 및 저장 완료.")

    dim_time = load_table_from_db('dwh.dim_time', COL_TYPES_PATH)


    # === 3. dim_industry 생성 ===
    print("dim_industry 생성 중...")

    # shared/config_loader에서 industry_codes 경로 가져오기
    from shared.config_loader import config
    industry_csv_path = config['paths']['industry_codes']

    # CSV 파일 읽기
    industry_df = pd.read_csv(industry_csv_path, encoding='utf-8')
    industry_df.columns = industry_df.columns.str.lower()  # 컬럼명 소문자로 통일

    # industry_sk는 DB에서 자동 생성되므로 제외
    dim_industry_to_load = industry_df[['industry_code', 'industry_name']].copy()

    load_data(dim_industry_to_load, 'dwh.dim_industry')
    print("dim_industry 생성 및 저장 완료.")

    dim_industry = load_table_from_db('dwh.dim_industry', COL_TYPES_PATH)

    print("차원 테이블 생성 완료.")
    return dim_company, dim_time, dim_industry
    







def create_facts(df, dim_company, dim_time, dw_columns):
    """
    데이터프레임과 차원 테이블들을 이용해 팩트 테이블들을 생성하고 DB에 저장
    """
    try:    
        df.columns = df.columns.str.lower()
        dim_company.columns = dim_company.columns.str.lower()
        dim_time.columns = dim_time.columns.str.lower()
    except AttributeError as e:
        print(f"경고: DataFrame 컬럼명 변경 중 오류 발생 (이미 소문자일 수 있음): {e}")
        # 컬럼이 없는 빈 DataFrame 등이 전달될 경우를 대비한 예외 처리
        pass

    print("팩트 테이블 생성 중...")

    date_cols = ['fndt_dt', 'listd_dt', 'listd_abol_dt']
    for col in date_cols:
        if col in dim_company.columns:
            dim_company[col] = pd.to_datetime(dim_company[col], errors='coerce')
            
    common_cols = df.columns.intersection(dim_company.columns)
    company_defining_cols = [col for col in common_cols if col.upper() != 'COMPANY_SK']

    common_time_cols = df.columns.intersection(dim_time.columns)
    time_defining_cols = [col for col in common_time_cols if col.upper() != 'TIME_SK']

    print(f"Company Merge Keys: {company_defining_cols}")
    print(f"Time Merge Keys: {time_defining_cols}")
    
    
    df_merged = pd.merge(df, dim_company, on=company_defining_cols, how='left', suffixes=("", "_dim"))

    # (아마도 다음 오류는 'time' merge에서 발생할 수 있으니 'bs_dt'도 확인 필요)
    if 'bs_dt' in df.columns and 'bs_dt' in dim_time.columns:
        df['bs_dt'] = pd.to_datetime(df['bs_dt'], errors='coerce')
        dim_time['bs_dt'] = pd.to_datetime(dim_time['bs_dt'], errors='coerce')

    df_merged = pd.merge(df_merged, dim_time, on=time_defining_cols, how='left', suffixes=("", "_dim"))


    for fact_name, fact_cols in dw_columns['facts'].items():
        fact_cols_lower = [col.lower() for col in fact_cols]
        cols_to_select = ['company_sk', 'time_sk'] + fact_cols_lower
        existing_cols = [col for col in cols_to_select if col in df_merged.columns]

        fact_df = df_merged[existing_cols].copy().drop_duplicates()

        load_data(fact_df, f'dwh.{fact_name}')

        print(f"{fact_name} 생성 및 저장 완료.")
        print(fact_df.head(3))
        print(fact_df.shape)
    print("팩트 테이블 생성 완료.")



