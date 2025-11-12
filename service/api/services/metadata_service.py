import pandas as pd
import yaml 
from typing import List, Dict
from sqlalchemy import create_engine, text

from shared.config_loader import DB_URL

# 프로젝트 루트 폴더 기준의 파일 경로
INDUSTRY_CSV_PATH = "data/fake/industry_codes.csv"
COLUMNS_YAML_PATH = "config/columns_map.yaml"

def get_industry_mappings() -> List[Dict[str, str]]:
    """
    industry_codes.csv 파일을 읽어 [ {code: ..., name: ...} ] 리스트로 반환
    """
    try:
        # P1의 DWH가 준비되기 전, mock csv를 읽습니다.
        df = pd.read_csv(INDUSTRY_CSV_PATH)
        return df.to_dict('records')
    except FileNotFoundError:
        # 파일이 없을 경우 빈 리스트나 에러 메시지를 반환할 수 있습니다.
        return [{"code": "ERROR", "name": f"File not found: {INDUSTRY_CSV_PATH}"}]

def get_column_mappings() -> List[Dict[str, str]]:
    """
    columns_map.yaml 파일을 읽어 [ {code: ..., name: ...} ] 리스트로 반환
    """
    try:
        with open(COLUMNS_YAML_PATH, 'r') as f:
            data = yaml.safe_load(f)
        
        # YAML의 {key: value} 딕셔너리를 리스트로 변환
        return [{"code": k, "name": v} for k, v in data.items()]
    except FileNotFoundError:
        return [{"code": "ERROR", "name": f"File not found: {COLUMNS_YAML_PATH}"}]