import pandas as pd
import numpy as np
from typing import List, Tuple
from sklearn.preprocessing import OneHotEncoder, PowerTransformer
import os
from pathlib import Path
import yaml

from .util import find_highly_correlated_features, find_high_vif_features, load_data, save_data, save_model
from etl.lake_to_dwh.scripts.extract import extract_data
from etl.lake_to_dwh.scripts.cleansing import cleanse_data


def select_features_for_multicollinearity(df: pd.DataFrame, numeric_cols: List[str]) -> List[str]:
    """
    다중공선성 분석을 통해 최종 사용할 수치형 피처 리스트를 반환합니다.
    
    :param df: 전처리된 데이터프레임
    :param numeric_cols: 분석할 수치형 변수 리스트
    :return: 선택된 최종 수치형 피처 이름 리스트
    """
    print("Starting feature selection for multicollinearity...")
    df_numeric = df[numeric_cols].copy()

    # 결측치 처리 (VIF 계산 전 필수)
    if df_numeric.isnull().any().any():
        print("NaNs found in numeric columns, filling with median...")
        df_numeric = df_numeric.fillna(df_numeric.median())

    # 1. 수치형 변수 간 상관관계 분석 (0.9 이상이면 삭제)
    to_drop_corr = find_highly_correlated_features(
        df_numeric,
        threshold=0.9,
        verbose=True
    )
    numeric_cols_after_corr = [col for col in numeric_cols if col not in to_drop_corr]
    df_numeric_after_corr = df_numeric[numeric_cols_after_corr]
    print(f"상관관계 제거 후 수치형 피처: {len(numeric_cols_after_corr)}개 (제거: {len(to_drop_corr)}개)")

    # 2. VIF(분산 팽창 지수) 분석 (5 이상이면 삭제)
    to_drop_vif = find_high_vif_features(
        df_numeric_after_corr,
        threshold=5,
        verbose=True
    )
    final_numeric_cols = [col for col in numeric_cols_after_corr if col not in to_drop_vif]
    print(f"VIF 제거 후 최종 수치형 피처: {len(final_numeric_cols)}개 (제거: {len(to_drop_vif)}개)")

    return final_numeric_cols


def encode_categorical_features(df: pd.DataFrame, categorical_cols: List[str]) -> pd.DataFrame:
    """
    scikit-learn의 OneHotEncoder를 사용하여 범주형 변수를 원-핫 인코딩합니다.
    
    :param df: 원본 데이터프레임
    :param categorical_cols: 인코딩할 범주형 변수 리스트
    :return: 인코딩된 컬럼으로 구성된 데이터프레임
    """
    print("Encoding categorical features using sklearn.OneHotEncoder...")
    
    df_categorical = df[categorical_cols].copy()
    
    # 결측치를 별도의 카테고리로 취급
    df_categorical.fillna('missing', inplace=True)

    encoder = OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore')
    encoded_array = encoder.fit_transform(df_categorical)
    encoded_col_names = encoder.get_feature_names_out(categorical_cols)

    encoded_df = pd.DataFrame(
        encoded_array,
        columns=encoded_col_names,
        index=df.index
    )
    return encoded_df


def scale_numerical_features(df: pd.DataFrame, numeric_cols: List[str]) -> Tuple[pd.DataFrame, PowerTransformer]:
    """
    수치형 변수를 PowerTransformer (Yeo-Johnson)를 사용하여 스케일링합니다.
    
    이 변환은 데이터의 왜곡(skewness)을 줄여 정규분포에 가깝게 만들고,
    'standardize=True' 옵션을 통해 표준 스케일링(평균 0, 분산 1)을 동시에 수행합니다.
    
    :param df: 데이터프레임
    :param numeric_cols: 스케일링할 수치형 변수 리스트
    :return: 스케일링된 데이터프레임과 학습된 PowerTransformer 객체
    """
    print("Scaling numerical features using PowerTransformer (Yeo-Johnson)...")
    
    df_numeric = df[numeric_cols].copy()

    # 결측치 처리
    if df_numeric.isnull().any().any():
        print("NaNs found, filling with median before scaling...")
        df_numeric = df_numeric.fillna(df_numeric.median())

    pt = PowerTransformer(method='yeo-johnson', standardize=True)
    pt_scaled_array = pt.fit_transform(df_numeric)

    scaled_numeric_df = pd.DataFrame(
        pt_scaled_array,
        columns=numeric_cols,
        index=df_numeric.index
    )
    return scaled_numeric_df, pt


def create_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    기존 변수를 조합하여 모델링에 유용한 새로운 파생변수를 생성합니다.

    :param df: 정제된(cleansed) 데이터프레임
    :return: 파생변수가 추가된 데이터프레임
    """
    # 상장여부, 설립~기준년도 경과일수 
    cond_list = (df['LISTD_DT'].notnull()) & (df['LISTD_ABOL_DT'].isnull()) 
    new_cols = pd.DataFrame({
        'LISTED_STATUS': np.where(cond_list, 'Listed', 'Unlisted'),
        'FNDF_DT_SINCE': (df['BS_DT'] - df['FNDT_DT']).dt.days
    }, index=df.index) 

    df = pd.concat([df, new_cols], axis=1)    
    return df 

def build_features(df: pd.DataFrame, processed_data_path: str, model_path: str) -> None:
    """
    전체 피처 엔지니어링 파이프라인을 실행합니다.
    입력으로 **정제된(cleansed)** 데이터프레임을 받습니다.
    
    :param df: 정제된 데이터프레임
    :param processed_data_path: 처리된 데이터를 저장할 경로 (.csv)
    :param model_path: 학습된 스케일러 모델을 저장할 경로 (.pkl)
    """
    print("Feature engineering pipeline started.")
    
    # --- 메모리 문제 해결을 위한 임시 샘플링 ---
    print("Temporarily sampling 5000 rows to avoid memory issues...")
    # 원본 데이터프레임을 그대로 사용하려면 아래 라인의 주석을 해제하고 샘플링 라인을 주석 처리하세요.
    df_to_process = df.copy() 
    # df_to_process = df.sample(n=5000, random_state=42)
    
    # 1. 파생변수 생성
    df_processed = create_derived_features(df_to_process)
    
    # 2. 컬럼 타입 정의
    categorical_cols = [col for col in df_processed.columns if df_processed[col].dtype == 'object'] # 범주형 변수 처리 비활성화
    numeric_cols = [col for col in df_processed.columns if pd.api.types.is_numeric_dtype(df_processed[col]) and col not in ['COMPANY_ID']]
    
    print(f"Identified {len(numeric_cols)} numeric columns for processing.")

    # 3. 다중공선성 기반 피처 선택
    final_numeric_cols = select_features_for_multicollinearity(df_processed, numeric_cols)
    
    # 4. 범주형 변수 인코딩 (비활성화)
    # df_encoded = encode_categorical_features(df_processed, categorical_cols)
    
    # 5. 수치형 변수 스케일링
    df_scaled_numeric, scaler_model = scale_numerical_features(df_processed, final_numeric_cols)
    
    # 6. 최종 데이터는 스케일링된 수치형 데이터만 포함
    # final_df = pd.concat([df_scaled_numeric, df_encoded], axis=1) # 원본
    final_df = df_scaled_numeric
    print(f"Final feature-engineered data shape: {final_df.shape}")
    
    # 7. 최종 데이터 및 스케일러 저장
    data_dir = os.path.dirname(processed_data_path)
    model_dir = os.path.dirname(model_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        
    save_data(final_df, processed_data_path)
    save_model(scaler_model, model_path)
    
    print("Feature engineering pipeline finished.")


def main():
    """
    데이터 추출, 정제, 피처 엔지니어링까지 전체 프로세스를 실행하는 메인 함수
    """
    # 프로젝트 루트 경로 설정
    project_root = Path(__file__).resolve().parents[3]

    # config/local_settings.yaml에서 경로 설정 로드
    config_path = project_root / 'config' / 'local_settings.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    paths_config = config['paths']
    
    raw_data_path = project_root / paths_config['raw_data']
    column_map_path = project_root / paths_config['columns_map']
    col_types_path = project_root / paths_config['col_types']
    cleansed_data_path = project_root / paths_config['cleansed_data_path']

    # 추천 경로(방법 1)에 따라 저장 경로를 설정
    processed_data_path = project_root / 'data' / 'processed' / 'clustering_features.csv'
    model_path = project_root / 'ml' / 'clustering' / 'models' / 'scaler_model.pkl'

    # 1. 데이터 추출
    print("--- 1. Starting Data Extraction ---")
    raw_df = extract_data(str(raw_data_path), str(column_map_path))
    
    if raw_df is None:
        print("Data extraction failed. Exiting.")
        return
    
    print(f"Data extracted successfully. Shape: {raw_df.shape}")
    print(raw_df.head(3))

    # 2. 데이터 정제
    print("\n--- 2. Starting Data Cleansing ---")
    cleansed_df = cleanse_data(raw_df, str(col_types_path))

    if cleansed_df is None:
        print("Data cleansing failed. Exiting.")
        return
    
    print(f"Data cleansed successfully. Shape: {cleansed_df.shape}")
    
    # 정제된 데이터 저장 (분석 단계에서 사용)
    print(f"Saving cleansed data to {cleansed_data_path}...")
    save_data(cleansed_df, str(cleansed_data_path))
    print("✓ Cleansed data saved.")
    
    # 3. 피처 엔지니어링 실행
    print("\n--- 3. Starting Feature Engineering ---")
    build_features(cleansed_df, str(processed_data_path), str(model_path))
    
    print("\n--- All processes finished ---")


if __name__ == '__main__':
    main()

