# ml/clustering/src/preprocessor.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, PowerTransformer
from sklearn.decomposition import PCA
import joblib
import os
from typing import List
from statsmodels.stats.outliers_influence import variance_inflation_factor

# --- 유틸리티 함수 추가 ---
def find_highly_correlated_features(df: pd.DataFrame, threshold: float = 0.9) -> List[str]:
    """상관계수가 임계치 이상인 피처 쌍 중 하나를 찾아 제거할 목록을 반환합니다."""
    corr_matrix = df.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
    print(f"  - Found {len(to_drop)} features to drop due to high correlation (> {threshold}): {to_drop}")
    return to_drop

def find_high_vif_features(df: pd.DataFrame, threshold: float = 5.0) -> List[str]:
    """VIF(분산 팽창 지수)가 임계치 이상인 피처를 찾아 제거할 목록을 반환합니다."""
    vif_data = pd.DataFrame()
    vif_data["feature"] = df.columns
    vif_data["VIF"] = [variance_inflation_factor(df.values, i) for i in range(df.shape[1])]
    to_drop = vif_data[vif_data['VIF'] > threshold]['feature'].tolist()
    print(f"  - Found {len(to_drop)} features to drop due to high VIF (> {threshold}): {to_drop}")
    return to_drop

def apply_preprocessing(df: pd.DataFrame, steps: list, output_dir: str) -> pd.DataFrame:
    """
    설정 파일에 명시된 전처리 단계를 순서대로 데이터에 적용합니다.
    """
    print("--- Applying Preprocessing Steps ---")
    df_processed = df.copy()
    
    # 출력 디렉토리가 없으면 생성 (스케일러, PCA 모델 저장용)
    os.makedirs(output_dir, exist_ok=True)

    for step in steps:
        method = step.get('method')
        params = step.get('params', {})
        print(f"Applying step: {method} with params: {params}")

        if method == 'fillna':
            if params.get('strategy') == 'median':
                df_processed.fillna(df_processed.median(numeric_only=True), inplace=True)
            else:
                df_processed.fillna(0, inplace=True)
        
        elif method == 'feature_selection':
            # 다중공선성 기반 피처 선택
            corr_threshold = params.get('correlation_threshold', 0.9)
            vif_threshold = params.get('vif_threshold', 5.0)
            
            # 상관관계
            to_drop_corr = find_highly_correlated_features(df_processed, threshold=corr_threshold)
            df_processed.drop(columns=to_drop_corr, inplace=True)
            
            # VIF
            to_drop_vif = find_high_vif_features(df_processed, threshold=vif_threshold)
            df_processed.drop(columns=to_drop_vif, inplace=True)
            
            print(f"  - Feature selection complete. Kept {len(df_processed.columns)} features.")

        elif method == 'scale':
            scaler_name = params.get('scaler', 'StandardScaler')
            if scaler_name == 'StandardScaler':
                scaler = StandardScaler()
            elif scaler_name == 'MinMaxScaler':
                scaler = MinMaxScaler()
            elif scaler_name == 'PowerTransformer':
                scaler = PowerTransformer(method='yeo-johnson', standardize=True)
            else:
                raise ValueError(f"Unsupported scaler: {scaler_name}")
            
            df_processed = pd.DataFrame(scaler.fit_transform(df_processed), columns=df_processed.columns)
            
            # 스케일러 저장
            scaler_path = os.path.join(output_dir, "scaler.pkl")
            joblib.dump(scaler, scaler_path)
            print(f"Scaler saved to {scaler_path}")

        elif method == 'pca':
            pca = PCA(**params)
            df_processed = pd.DataFrame(
                pca.fit_transform(df_processed),
                columns=[f'PC_{i+1}' for i in range(params['n_components'])]
            )
            
            # PCA 모델 저장
            pca_path = os.path.join(output_dir, "pca_model.pkl")
            joblib.dump(pca, pca_path)
            print(f"PCA model saved to {pca_path}")
            
    print(f"Preprocessing finished. Processed data shape: {df_processed.shape}")
    return df_processed

def run(df_raw: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    전체 전처리 파이프라인을 실행합니다.
    """
    print("\n--- 2. Preprocessing ---")
    if df_raw.empty:
        print("Warning: Input data is empty. Skipping preprocessing.")
        return pd.DataFrame()

    # 1. 학습에 사용할 피처 선택
    drop_cols = config.get('drop_cols', [])
    target_col = config.get('target_col', '')
    
    # 식별자 컬럼과 타겟 컬럼을 제외한 모든 컬럼을 피처로 간주
    features_to_use = [col for col in df_raw.columns if col not in drop_cols + [target_col]]
    df_features = df_raw[features_to_use].copy()
    
    # 숫자형이 아닌 컬럼은 일단 제외 (실제로는 인코딩 등 처리 필요)
    numeric_cols = df_features.select_dtypes(include=np.number).columns.tolist()
    df_numeric_features = df_features[numeric_cols]
    
    # 2. 설정에 정의된 전처리 단계 적용
    preprocessing_steps = config.get('preprocessing', [])
    output_dir = config['paths']['output_dir']
    
    df_processed = apply_preprocessing(df_numeric_features, preprocessing_steps, output_dir)
    
    # 3. 원본 데이터의 식별자 컬럼들을 다시 붙여서 반환
    # drop=True로 인덱스를 초기화하여 concat 시 인덱스 정렬 오류 방지
    # 식별자/타겟 컬럼은 drop_cols와 target_col을 합쳐서 가져온다
    identifier_cols = [c for c in drop_cols + [target_col] if c in df_raw.columns]
    identifiers_df = df_raw[identifier_cols].reset_index(drop=True)
    processed_features_df = df_processed.reset_index(drop=True)
    
    final_df = pd.concat([identifiers_df, processed_features_df], axis=1)
    
    return final_df
