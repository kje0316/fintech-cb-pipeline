# ml/feature_engineering/build_training_dataset.py
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np # np.where를 위해 추가
import yaml
from sqlalchemy import create_engine, text 
from shared.config_loader import config
from etl.lake_to_dwh.scripts.load_to_postgres import get_db_engine

def get_column_to_alias_map():
    """
    dw_columns.yaml을 읽어 각 컬럼이 어떤 테이블 별칭에 속하는지 맵을 생성합니다.
    (e.g., {'company_id': 'dc', 'r001': 'ffr'})
    """
    with open('config/dw_columns.yaml', 'r', encoding='utf-8') as f:
        dw_columns = yaml.safe_load(f)

    col_to_alias = {}
    aliases = {'dim_company': 'dc', 'dim_time': 'dt', 'fact_financial_statement': 'ffs', 
               'fact_financial_ratios': 'ffr', 'fact_credit_behavior': 'fcb'}

    for table_type, tables in dw_columns.items():
        for table_name, columns in tables.items():
            alias = aliases.get(table_name)
            if alias and columns:
                for col in columns:
                    col_to_alias[col.lower()] = alias
    
    if 'perf_12m' not in col_to_alias:
        col_to_alias['perf_12m'] = 'fcb'
        
    return col_to_alias

def build_training_dataset(test_run: bool = False):
    """
    DWH의 테이블을 조인하고 파생 변수를 추가하여, 모델 학습용 데이터셋을 생성합니다.
    test_run=True일 경우, 10개 행만 샘플링하여 빠르게 테스트합니다.
    """
    run_mode = "테스트" if test_run else "전체"
    print(f"피처 스토어 구축 ({run_mode} 모드)을 시작합니다...")
    
    try:
        # --- 1. 설정 파일 로드 및 쿼리 생성 ---
        with open('config/feature_store.yaml', 'r', encoding='utf-8') as f:
            feature_store_config = yaml.safe_load(f)
        
        source_features = feature_store_config.get('source_features', [])
        col_to_alias = get_column_to_alias_map()
        
        select_expressions = []
        for col in source_features:
            alias = col_to_alias.get(col.lower())
            if alias:
                select_expressions.append(f"{alias}.{col.lower()}")
            else:
                print(f"  - 경고: '{col}' 컬럼의 소스 테이블을 찾을 수 없습니다. 쿼리에서 제외됩니다.")

        select_clause = ",\n                    ".join(select_expressions)
        
        query = f"""
            SELECT
                {select_clause}
            FROM dwh.fact_financial_statement AS ffs
            LEFT JOIN dwh.dim_company AS dc ON ffs.company_sk = dc.company_sk
            LEFT JOIN dwh.dim_time AS dt ON ffs.time_sk = dt.time_sk
            LEFT JOIN dwh.fact_financial_ratios AS ffr ON ffs.company_sk = ffr.company_sk AND ffs.time_sk = ffr.time_sk
            LEFT JOIN dwh.fact_credit_behavior AS fcb ON ffs.company_sk = fcb.company_sk AND ffs.time_sk = fcb.time_sk
        """

        if test_run:
            query += " LIMIT 10;"
            print("\n*** 테스트 실행: 쿼리 결과가 10개 행으로 제한됩니다. ***\n")
        
        # --- 2. 데이터 로딩 및 파생 변수 생성 ---
        engine = get_db_engine()
        with engine.connect() as connection:
            print("  - 'feature_store' 스키마 생성 중...")
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS feature_store"))
            connection.commit()
            
            print("  - DWH 테이블 조인하여 학습용 데이터셋 생성 중...")
            df_training = pd.read_sql(query, con=connection)
            print(f"  - 학습용 데이터셋 생성 완료. (Shape: {df_training.shape})")

            print("  - 파생 변수 생성 중...")
            # df_training['debt_to_equity_ratio'] = df_training['fn1_16'] / df_training['fn1_17'].replace(0, 1e-9)
            current_date = pd.to_datetime(df_training['bs_dt'], errors='coerce')
            foundation_date = pd.to_datetime(df_training['fndt_dt'], errors='coerce')
            df_training['company_age_years'] = (current_date - foundation_date).dt.days / 365.25
            cond_listed = (df_training['listd_dt'].notnull()) & (df_training['listd_abol_dt'].isnull())
            df_training['listed_status'] = np.where(cond_listed, 'Listed', 'Unlisted')
            print("  - 파생 변수 생성 완료.")
            
            # --- 3. 최종 컬럼 검증 및 저장 ---
            final_feature_list = feature_store_config.get('final_features', [])
            df_final = df_training[[col for col in final_feature_list if col in df_training.columns]]
            
            target_table = 'feature_store.training_dataset_test' if test_run else 'feature_store.training_dataset'
            print(f"  - '{target_table}' 테이블에 데이터 적재 중...")
            
            df_final.to_sql(
                name=target_table.split('.')[-1],
                con=engine, 
                schema='feature_store', 
                if_exists='replace', 
                index=False
            )
            print(f"✓ '{target_table}' 테이블 적재 완료.")
            
    except Exception as e:
        print(f"✗ 피처 스토어 구축 실패: {e}")
        raise e

if __name__ == '__main__':
    # 빠른 테스트를 위해 test_run=True로 설정. 
    # 전체 데이터를 실행하려면 test_run=False로 변경하거나, build_training_dataset()으로 호출하세요.
    build_training_dataset(test_run=)

