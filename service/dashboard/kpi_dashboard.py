import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


def load_cleansed_data():
    """
    데이터 추출 및 정제 파이프라인을 실행하여 정제된 데이터프레임을 반환합니다.
    """
    # --- 프로젝트 루트 경로 설정 ---
    # 이 스크립트의 위치: /service/dashboard/
    # 프로젝트 루트는 2단계 상위
    try:
        project_root = Path(__file__).resolve().parents[2]
    except IndexError:
        project_root = Path.cwd()

    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))

    # --- 필요한 함수 임포트 ---
    from etl.lake_to_dwh.scripts.extract import extract_data
    from etl.lake_to_dwh.scripts.cleansing import cleanse_data

    # --- 경로 설정 ---
    raw_data_path = project_root / 'data' / 'raw' / '기업신용평가정보_합성데이터.csv'
    column_map_path = project_root / 'config' / 'columns_map.yaml'
    col_types_path = project_root / 'config' / 'col_types.yaml'

    # --- 데이터 로드 및 정제 파이프라인 실행 ---
    print("--- 1. 데이터 추출 시작 ---")
    df_raw = extract_data(str(raw_data_path), str(column_map_path))

    if df_raw is None:
        print("✗ 데이터 추출 실패.")
        return None
    
    print(f"✓ 데이터 추출 성공. Shape: {df_raw.shape}")
    
    print("\\n--- 2. 데이터 정제 시작 ---")
    df_cleansed = cleanse_data(df_raw, str(col_types_path))
    
    if df_cleansed is None:
        print("✗ 데이터 정제 실패.")
        return None

    print(f"✓ 데이터 정제 성공. Shape: {df_cleansed.shape}")
    return df_cleansed





if __name__ == '__main__':
    print("대시보드용 데이터 로딩 스크립트")
    df_cleansed = load_cleansed_data()
    
    if df_cleansed is not None:
        print("\\n--- 정제된 데이터 샘플 (상위 5개) ---")
        print(df_cleansed.head())
