import pandas as pd
import yaml
from typing import List, Dict
from sqlalchemy import create_engine, text

from shared.config_loader import DB_URL

# 프로젝트 루트 폴더 기준의 파일 경로
COLUMNS_YAML_PATH = "config/columns_map.yaml"

def get_industry_mappings() -> List[Dict[str, str]]:
    """
    dwh.dim_industry 테이블에서 업종 정보를 조회하여 리스트로 반환
    """
    try:
        engine = create_engine(DB_URL)
        query = text("SELECT industry_code, industry_name FROM dwh.dim_industry ORDER BY industry_code")

        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

            return [
                {"industry_code": row[0], "industry_name": row[1]}
                for row in rows
            ]
    except Exception as e:
        print(f"Error loading industry mappings from DWH: {e}")
        return [{"industry_code": "ERROR", "industry_name": f"Database error: {str(e)}"}]

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