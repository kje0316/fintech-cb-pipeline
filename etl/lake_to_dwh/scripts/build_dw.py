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
    # company_id를 기준으로 고유 기업 정보를 추출. 중복 시 최신 데이터 유지.
    df.columns = df.columns.str.lower()
    company_cols_config = [col.lower() for col in dw_columns['dims']['dim_company'] if col.upper() != 'COMPANY_SK']
    company_defining_cols = [col for col in company_cols_config if col in df.columns]

    # 수정: 슬라이싱 전에 drop_duplicates를 먼저 수행하여 KeyError 방지
    df_unique_companies = df.copy().drop_duplicates(subset=['company_id'], keep='last')
    dim_company_to_load = df_unique_companies[company_defining_cols].copy()
    dim_company_to_load.columns = dim_company_to_load.columns.str.lower()

    load_data(dim_company_to_load, 'dwh.dim_company')
    print("dim_company 생성 및 저장 완료.")

    dim_company = load_table_from_db('dwh.dim_company', COL_TYPES_PATH)


    # === 2. dim_time 생성 ===
    time_cols = list(dict.fromkeys(dw_columns['dims']['dim_time']))
    time_defining_cols = [col for col in time_cols if col in df.columns and col.upper() != 'TIME_SK']

    if not all(col in df.columns for col in time_defining_cols):
        raise ValueError(f"Time dimension을 정의하는 컬럼이 원본 데이터에 없습니다: {time_defining_cols}")

    dim_time_to_load = df[time_defining_cols].copy().drop_duplicates(
        subset=['bs_dt'],  # dw_columns 설정에 따라 컬럼명 확인 필요 (예: bs_dt)
        keep='last'        # 중복 시 최신 값 유지
    )    
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


    print("팩트 테이블 생성 중...")
    COMPANY_BK = 'company_id' # 기업 식별자
    TIME_BK = 'bs_dt'         # 기준 일자 
    print(f"조인 키 설정: '{COMPANY_BK}', '{TIME_BK}'")


    # 원본과 차원 모두 적용하는 전처리 
    print('원본과 차원 테이블에 모두 전처리 수행 Type Casting & Strip')
    try:
        if COMPANY_BK in df.columns and COMPANY_BK in dim_company.columns:
            df[COMPANY_BK] = df[COMPANY_BK].astype(str).str.strip()
            dim_company[COMPANY_BK] = dim_company[COMPANY_BK].astype(str).str.strip()
        else:
            raise KeyError(f"Company BK 컬럼({COMPANY_BK})이 데이터프레임에 없습니다.")

        # [Time] Datetime 객체로 변환 (날짜 포맷 통일)
        if TIME_BK in df.columns and TIME_BK in dim_time.columns:
            df[TIME_BK] = pd.to_datetime(df[TIME_BK], errors='coerce')
            dim_time[TIME_BK] = pd.to_datetime(dim_time[TIME_BK], errors='coerce')
        else:
            raise KeyError(f"Time BK 컬럼({TIME_BK})이 데이터프레임에 없습니다.")
            
    except Exception as e:
        print(f"🚨 전처리 중 치명적 오류 발생: {e}")
        raise e


    # SK Lookup 
    df_merged = pd.merge(
        df, 
        dim_company[[COMPANY_BK, 'company_sk']], 
        on=COMPANY_BK, 
        how='left'
    )
    df_merged = pd.merge(
        df_merged, 
        dim_time[[TIME_BK, 'time_sk']], 
        on=TIME_BK, 
        how='left'
    )

    # 무결성 처리 필요? -- 추후 확인 
    facts_config = dw_columns['facts']
    
    for fact_name, measure_cols in facts_config.items():
        print(f"\nProcessing Table: {fact_name} ...")
        
        # 5-1. 해당 팩트 테이블에 필요한 컬럼 정의
        required_cols = ['company_sk', 'time_sk'] + [col.lower() for col in measure_cols]
        valid_cols = [c for c in required_cols if c in df_merged.columns]
        
        # 누락된 컬럼 확인 (디버깅용)
        missing_cols = set(required_cols) - set(valid_cols)
        if missing_cols:
            print(f"   (참고) 원천 데이터에 없어 제외된 컬럼 수: {len(missing_cols)}")

        # 5-3. 최종 데이터프레임 생성 및 중복 제거
        fact_df = df_merged[valid_cols].copy().drop_duplicates()
        
        # 5-4. DB 적재
        if not fact_df.empty:
            # load_data 함수는 기 구현된 것으로 가정
            load_data(fact_df, f'dwh.{fact_name}')
            print(f"✅ {fact_name}: {len(fact_df)}건 적재 완료.")
            print(f"   Sample: {fact_df.head(1).values}")
        else:
            print(f"⚠️ {fact_name}: 적재할 데이터가 없습니다.")

    print("\n=== 모든 팩트 테이블 생성 완료 ===")   


