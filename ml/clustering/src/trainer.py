# ml/clustering/src/trainer.py
import pandas as pd
import numpy as np

def train(model, df: pd.DataFrame, config: dict):
    """
    주어진 모델과 데이터로 클러스터링을 수행하고,
    결과(라벨)를 원본 데이터프레임에 추가하여 반환합니다.
    """
    print("--- 3. Model Training ---")
    
    # config를 참조하여 학습에 사용할 피처 선택
    drop_cols = config.get('drop_cols', [])
    target_col = config.get('target_col', '')
    features = [col for col in df.columns if col not in drop_cols + [target_col]]
    
    print(f"Training model on {len(features)} features...")
    df_features = df[features]
    
    # 모델 학습 및 예측 (클러스터링은 fit_predict 사용)
    labels = model.fit_predict(df_features)
    
    # 결과 데이터프레임에 라벨 추가
    df_results = df.copy()
    df_results['cluster_label'] = labels
    
    print(f"Training finished. Number of clusters found: {len(np.unique(labels))}")
    return df_results, model
