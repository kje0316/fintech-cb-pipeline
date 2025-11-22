# ml/clustering/predict.py
import pandas as pd
import numpy as np
import yaml
import os
import sys
import argparse
import joblib
from pathlib import Path

def load_artifacts(experiment_dir: str) -> dict:
    """
    지정된 실험 결과 폴더에서 모델, 설정 등 모든 결과물을 로드합니다.
    """
    print(f"--- Loading artifacts from: {experiment_dir} ---")
    artifacts = {}
    
    # 1. 설정 파일 로드
    config_path = os.path.join(experiment_dir, 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        artifacts['config'] = yaml.safe_load(f)
    print("  - Loaded config.yaml")

    # 2. 메인 모델 로드
    model_path = os.path.join(experiment_dir, 'model.pkl')
    artifacts['model'] = joblib.load(model_path)
    print("  - Loaded model.pkl")

    # 3. 스케일러 로드 (선택적)
    scaler_path = os.path.join(experiment_dir, 'scaler.pkl')
    if os.path.exists(scaler_path):
        artifacts['scaler'] = joblib.load(scaler_path)
        print("  - Loaded scaler.pkl")

    # 4. PCA 모델 로드 (선택적)
    pca_path = os.path.join(experiment_dir, 'pca_model.pkl')
    if os.path.exists(pca_path):
        artifacts['pca'] = joblib.load(pca_path)
        print("  - Loaded pca_model.pkl")
        
    return artifacts

def predict(artifacts: dict, df_new: pd.DataFrame) -> pd.DataFrame:
    """
    새로운 데이터에 대해 전처리 및 클러스터 예측을 수행합니다.
    """
    print("\n--- Prediction Pipeline Started ---")
    config = artifacts['config']
    
    # 1. 학습에 사용된 피처 목록 추출
    # (PCA 적용 시와 아닐 시를 모두 고려)
    if 'pca' in artifacts: # PCA가 적용된 경우
        # 스케일러가 학습된 원본 피처 목록을 가져옴
        original_features = artifacts['scaler'].feature_names_in_
    else: # PCA가 적용되지 않은 경우
        # 모델이 학습한 피처 목록을 가져옴
        original_features = artifacts['model'].feature_names_in_
    
    print(f"Model was trained on {len(original_features)} features.")
    df_features = df_new[original_features].copy()

    # 2. 전처리 적용 (학습 시와 동일한 순서)
    # 2-1. 결측치 처리
    if config['preprocessing'][0]['method'] == 'fillna':
        print("Applying step: fillna")
        df_features.fillna(df_features.median(), inplace=True)
    
    # 2-2. 스케일링 (transform 사용)
    if 'scaler' in artifacts:
        print("Applying step: scale")
        scaled_features = artifacts['scaler'].transform(df_features)
        df_processed = pd.DataFrame(scaled_features, columns=original_features)
    else:
        df_processed = df_features

    # 2-3. PCA 변환 (transform 사용)
    if 'pca' in artifacts:
        print("Applying step: pca")
        pca_features = artifacts['pca'].transform(df_processed)
        df_processed = pd.DataFrame(pca_features, columns=[f'PC_{i+1}' for i in range(artifacts['pca'].n_components_)])
        
    # 3. 예측
    print("Predicting clusters...")
    model = artifacts['model']
    predictions = model.predict(df_processed)
    
    # 4. 결과 종합
    df_new['predicted_cluster'] = predictions
    print("--- Prediction Finished ---")
    
    return df_new

def main(args):
    # 1. 학습된 모델 및 설정 로드
    artifacts = load_artifacts(args.experiment_dir)
    
    # 2. 예측할 데이터 로드
    print(f"\nLoading new data from: {args.input_data}")
    df_new = pd.read_csv(args.input_data)
    
    # 3. 예측 실행
    df_predictions = predict(artifacts, df_new)
    
    # 4. 결과 저장
    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, 'predictions.csv')
    df_predictions.to_csv(output_path, index=False)
    print(f"\nPrediction results saved to: {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--experiment_dir', 
        type=str, 
        required=True,
        help='Path to the experiment output directory (e.g., outputs/20251121_202114_/)'
    )
    parser.add_argument(
        '--input_data',
        type=str,
        required=True,
        help='Path to the new data CSV file for prediction'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default='predictions',
        help='Directory to save the prediction results'
    )
    args = parser.parse_args()
    
    main(args)
