import pandas as pd
import yaml
import os
from typing import Dict, Any
import collections.abc
import sys
from pathlib import Path

# Add project root to sys.path to allow importing from etl
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the extraction functions from the etl module
from etl.lake_to_dwh.scripts.extract import extract_from_lake, extract_data

def deep_merge(d1, d2):
    """
    Recursively merges two dictionaries.
    Keys from d2 will overwrite keys from d1.
    """
    for k, v in d2.items():
        if k in d1 and isinstance(d1[k], dict) and isinstance(v, collections.abc.Mapping):
            d1[k] = deep_merge(d1[k], v)
        else:
            d1[k] = v
    return d1

def load_config(config_name: str = 'final_notebook_model') -> Dict[str, Any]:
    """
    Loads the base configuration and merges it with a specific experiment
    configuration.

    Args:
        config_name: The name of the experiment config file (without .yaml).

    Returns:
        A dictionary containing the merged configuration.
    """
    config_dir = 'ml/clustering/configs'
    base_config_path = os.path.join(config_dir, 'base.yaml')
    exp_config_path = os.path.join(config_dir, f"{config_name}.yaml")

    if not os.path.exists(base_config_path):
        raise FileNotFoundError(f"Base configuration file not found at: {base_config_path}")
    if not os.path.exists(exp_config_path):
        raise FileNotFoundError(f"Experiment configuration file not found at: {exp_config_path}")
    
    with open(base_config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    with open(exp_config_path, 'r', encoding='utf-8') as f:
        exp_config = yaml.safe_load(f)

    # Merge the base config with the experiment-specific one
    merged_config = deep_merge(config, exp_config)
    
    # Store the experiment name for saving outputs in dedicated folders
    merged_config['experiment_name'] = config_name
    
    return merged_config

def load_raw_data(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Loads the raw dataset based on the source provided in the config.
    Source can be 'csv', 'lake', or 'feature_store'.

    Args:
        config: The main configuration dictionary.

    Returns:
        A pandas DataFrame with the raw data.
    """
    etl_source = config.get('etl', {}).get('source', 'csv')
    base_ym = config.get('data', {}).get('base_ym')

    print(f"1. Loading raw data from: {etl_source}...")

    df_raw = None

    if etl_source == 'feature_store':
        # Feature Store에서 직접 로드 (70개 피처 + 메타데이터)
        from ml.common.feature_store import load_from_feature_store
        df_raw = load_from_feature_store(base_ym=base_ym, include_target=True)

        # 컬럼명 대문자로 변환 (기존 파이프라인 호환성)
        df_raw.columns = df_raw.columns.str.upper()

        print(f"✓ Data loaded from Feature Store. {len(df_raw):,} rows, {len(df_raw.columns)} columns.")
        return df_raw

    elif etl_source == 'lake':
        column_map_path = os.path.join(project_root, config['paths']['col_map'])
        df_raw = extract_from_lake(column_map_path)

    elif etl_source == 'csv':
        column_map_path = os.path.join(project_root, config['paths']['col_map'])
        file_path = os.path.join(project_root, config['paths']['raw_data'])
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Raw data file not found at: {file_path}")
        df_raw = extract_data(file_path, column_map_path)

    else:
        raise ValueError(f"Unsupported ETL source: {etl_source}. Must be 'csv', 'lake', or 'feature_store'.")

    if df_raw is None:
        raise RuntimeError("Data loading failed.")

    # 기준년월 필터링 (feature_store가 아닌 경우에만)
    if base_ym:
        # 기준년월 컬럼 찾기 (한글 또는 영문)
        ym_col = None
        for col in ['기준년월', 'BS_DT', 'bs_dt']:
            if col in df_raw.columns:
                ym_col = col
                break

        if ym_col:
            original_count = len(df_raw)
            df_raw = df_raw[df_raw[ym_col] == base_ym].copy()
            print(f"  - 기준년월 {base_ym} 필터링: {original_count:,}건 → {len(df_raw):,}건")
        else:
            print(f"  - Warning: 기준년월 컬럼을 찾을 수 없습니다. 필터링 없이 진행.")

    print(f"✓ Data loaded successfully. {len(df_raw):,} rows, {len(df_raw.columns)} columns.")
    return df_raw

def load_yaml_map(yaml_path: str) -> Dict[str, Any]:
    """
    Loads a generic YAML file and returns its content as a dictionary.

    Args:
        yaml_path: The path to the YAML file.

    Returns:
        A dictionary with the content of the YAML file.
    """
    if not os.path.exists(yaml_path):
        print(f"Warning: YAML file not found at: {yaml_path}. Returning empty dictionary.")
        return {}
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data_map = yaml.safe_load(f)
        return data_map
    except Exception as e:
        print(f"Error loading YAML file at {yaml_path}: {e}")
        return {}

def rename_columns(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Renames DataFrame columns from Korean to English using the mapping file.

    Args:
        df: The input DataFrame with Korean column names.
        config: The main configuration dictionary.

    Returns:
        A DataFrame with English column names.
    """
    col_map_path = os.path.join(project_root, config['paths']['col_map'])
    eng_to_kor_map = load_yaml_map(col_map_path)
    
    if not eng_to_kor_map:
        print("Warning: Column map is empty. Skipping column renaming.")
        return df

    kor_to_eng_map = {v: k for k, v in eng_to_kor_map.items()}
    df_renamed = df.rename(columns=kor_to_eng_map)
    
    print("2. Renamed columns from Korean to English.")
    return df_renamed
