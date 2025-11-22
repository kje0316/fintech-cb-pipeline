# ml/clustering/src/data_loader.py
import pandas as pd
import numpy as np # np.where를 위해 추가
import yaml
import os
import shutil

# 프로젝트 경로 설정
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from etl.lake_to_dwh.scripts.load_to_postgres import get_db_engine

def run(config: dict) -> pd.DataFrame:
    """
    설정 파일에 따라 Feature Store에서 데이터를 로드하고,
    'YYYYMM' 형식의 파티션으로 나누어 Parquet 파일로 저장/로드합니다.
    """
    print("\n--- 1. Data Loading (Partitioned Parquet) ---")
    data_source_config = config['data_source']
    
    # Parquet 데이터를 저장/로드할 디렉토리 경로
    dump_dir = config['paths']['dump_path']
    
    # 필터 정보 가져오기
    filters = data_source_config.get('filters', [])

    # 데이터베이스에서 로드해야 하는 경우
    if data_source_config.get('type') == 'db':
        table_name = data_source_config.get('table_name', 'feature_store.training_dataset')
        
        print(f"Loading data from database table: {table_name}")
        engine = get_db_engine()
        with engine.connect() as connection:
            # 필터를 SQL WHERE 절로 변환
            where_clauses = []
            for col, op, val in filters:
                if col == 'bs_dt': # bs_dt는 날짜형이므로 SQL 문자열 형식으로 변환
                    where_clauses.append(f"{col} {op} '{val}'")
                else:
                    where_clauses.append(f"{col} {op} {val}") # 기타 컬럼은 그대로 사용

            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            query = f"SELECT * FROM {table_name}{where_sql}"
            
            df = pd.read_sql(query, con=connection)
        
        print(f"Data loaded successfully. Shape: {df.shape}")
        
        # 'bs_dt' 컬럼을 datetime으로 변환
        df['bs_dt'] = pd.to_datetime(df['bs_dt'], errors='coerce')
        
        # 파티셔닝을 위한 'yyyymm' 컬럼 생성
        df['yyyymm'] = df['bs_dt'].dt.strftime('%Y%m')
        
        # Parquet 파일로 파티션하여 저장 (기존 디렉토리 삭제 후 새로 쓰기)
        print(f"Saving partitioned data to '{dump_dir}'...")
        if os.path.exists(dump_dir):
            shutil.rmtree(dump_dir)
            
        df.to_parquet(dump_dir, partition_cols=['yyyymm'], index=False)
        # 덤프 후에는 yyyymm 컬럼이 필요 없으므로 제거하고 반환
        df = df.drop(columns=['yyyymm'])
        print("Data saved successfully as partitioned Parquet files.")
    
    # 로컬 Parquet 파티션에서 로드하는 경우
    elif data_source_config.get('type') == 'local_csv': # YAML 호환성을 위해 local_csv로 유지
        print(f"Loading partitioned Parquet data from '{dump_dir}'...")
        if not os.path.exists(dump_dir):
             raise FileNotFoundError(
                f"Parquet dump directory not found: {dump_dir}. "
                "Please run with data_source.type='db' first to create the dump files."
            )
        
        # filters 인자를 pd.Timestamp 객체로 변환 (bs_dt 컬럼인 경우)
        processed_filters = []
        for col, op, val in filters:
            if col == 'bs_dt' and isinstance(val, str):
                processed_filters.append((col, op, pd.Timestamp(val)))
            else:
                processed_filters.append((col, op, val))

        df = pd.read_parquet(dump_dir, filters=processed_filters) # filters 인자 전달
        print("Data loaded successfully from partitioned Parquet files.")
        
    else:
        raise ValueError(f"Unsupported data source type: {data_source_config.get('type')}")
        
    print(f"Final data shape: {df.shape}\n")
    return df

if __name__ == '__main__':
    # 이 스크립트를 직접 실행하여 테스트하기 위한 config 생성
    script_dir = Path(__file__).resolve().parent.parent # ml/clustering/src -> ml/clustering
    
    # base.yaml 로드
    with open(script_dir / 'configs' / 'base.yaml', 'r', encoding='utf-8') as f:
        base_config = yaml.safe_load(f)
        
    # paths 설정 업데이트
    base_config['paths']['dump_path'] = script_dir / base_config['paths']['dump_path']
    base_config['paths']['processed_data_dir'] = script_dir / base_config['paths']['processed_data_dir']
    base_config['paths']['output_dir'] = script_dir / base_config['paths']['output_dir']

    # data_loader.run 실행
    df_loaded = run(base_config)
    print(f"data_loader.py 단독 실행 완료. 로드된 데이터 Shape: {df_loaded.shape}")
