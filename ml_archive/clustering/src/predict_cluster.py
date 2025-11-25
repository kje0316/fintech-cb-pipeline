import pandas as pd
import numpy as np
from typing import Any
from .util import save_data, load_data, load_model
from pathlib import Path
import os
import yaml


def predict_clusters(model: Any, df: pd.DataFrame) -> np.ndarray:
    """
    학습된 클러스터링 모델을 사용하여 새로운 데이터의 군집을 예측합니다.
    
    :param model: 학습된 K-Means 모델 객체
    :param df: 스케일링 및 차원 축소가 완료된 데이터
    :return: 군집 예측 결과 (numpy array)
    """
    print("Predicting clusters for new data...")
    predictions = model.predict(df)
    print(f"Prediction complete. Found clusters: {predictions}")
    return predictions


def prediction_pipeline(data_path: str, scaler_path: str, pca_path: str, model_path: str, output_path: str) -> None:
    """
    전체 예측 파이프라인을 실행합니다.
    1. 새로운 데이터 로드
    2. 저장된 모델(스케일러, PCA, K-Means) 로드
    3. 데이터 변환 (스케일링, PCA)
    4. 군집 예측
    5. 결과 저장
    
    :param data_path: 예측할 새로운 데이터 경로
    :param scaler_path: 저장된 스케일러 모델 경로
    :param pca_path: 저장된 PCA 모델 경로
    :param model_path: 저장된 K-Means 모델 경로
    :param output_path: 예측 결과 저장 경로
    """
    print("Prediction pipeline started.")
    
    try:
        # 1. 모델 로드
        scaler_loaded = load_model(scaler_path)
        pca_loaded = load_model(pca_path)
        kmeans_loaded = load_model(model_path)
        print("Models (scaler, PCA, k-means) loaded successfully.")
        print("-" * 30)

        # 2. 새 데이터 로드
        new_data = load_data(data_path)
        print(f"New data loaded from {data_path}. Shape: {new_data.shape}")

        # 스케일러가 학습된 피처 순서와 이름을 기준으로 컬럼을 맞춤
        feature_cols = scaler_loaded.feature_names_in_
        new_data_raw = new_data[feature_cols].copy()

        # 3. 새 데이터에 변환 적용
        # (1) 스케일러 적용
        new_data_scaled = scaler_loaded.transform(new_data_raw)
        print(f"(1) Scaler applied. Shape: {new_data_scaled.shape}")
        
        # (2) PCA 적용
        new_data_pca = pca_loaded.transform(new_data_scaled)
        print(f"(2) PCA applied. Shape: {new_data_pca.shape}")
        
        # 4. K-Means로 예측
        new_clusters = predict_clusters(kmeans_loaded, new_data_pca)
        
        # 5. 결과 저장
        new_data['cluster'] = new_clusters
        save_data(new_data, output_path)
        
        print("-" * 30)
        print("✅ Final prediction result:")
        print(f"Predictions saved to {output_path}")
        print(f"Example predictions: {new_clusters[:5]}")

    except FileNotFoundError as e:
        print(f"Error: A model or data file was not found. {e}")
    except Exception as e:
        print(f"An error occurred during prediction: {e}")
        
    print("Prediction pipeline finished.")


def main():
    """
    예측 파이프라인을 실행하는 메인 함수.
    이 파이프라인을 실행하기 전에, train_cluster.py 등을 통해
    모델 파일들(scaler, pca, kmeans)이 생성되어 있어야 합니다.
    """
    project_root = Path(__file__).resolve().parents[3]

    # config/local_settings.yaml에서 경로 설정 로드
    config_path = project_root / 'config' / 'local_settings.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    paths_config = config['paths']

    # 가상의 모델 및 데이터 경로
    # build_features.py에서 저장된 스케일러 모델
    SCALER_PATH = project_root / 'ml' / 'clustering' / 'models' / 'scaler_model.pkl'
    # train_cluster.py에서 저장된 PCA 모델
    PCA_PATH = project_root / 'ml' / 'clustering' / 'models' / 'pca_model.pkl'
    # train_cluster.py에서 저장된 K-Means 모델
    KMEANS_PATH = project_root / 'ml' / 'clustering' / 'models' / 'kmeans_model.pkl'
    # 예측 결과 저장 경로
    OUTPUT_DATA_PATH = project_root / "predictions.csv"

    # --- 테스트용 더미 데이터 생성 ---
    # 실제로는 이 부분을 사용하지 않고, 예측할 데이터 경로를 `data_path`에 지정합니다.
    try:
        # 스케일러 모델을 로드하여 피처 이름을 가져옵니다.
        # 이 스케일러는 build_features.py에서 생성된 것입니다.
        scaler_for_cols = load_model(str(SCALER_PATH))
        feature_names = scaler_for_cols.feature_names_in_
        
        dummy_df = pd.DataFrame(np.random.rand(5, len(feature_names)), columns=feature_names)
        dummy_input_path = project_root / "dummy_new_data.csv"
        dummy_df.to_csv(dummy_input_path, index=False)
        print(f"Created '{dummy_input_path}' for demonstration.")
        
        # 파이프라인 실행
        prediction_pipeline(
            data_path=str(dummy_input_path),
            scaler_path=str(SCALER_PATH),
            pca_path=str(PCA_PATH),
            model_path=str(KMEANS_PATH),
            output_path=str(OUTPUT_DATA_PATH)
        )
        # 더미 데이터 삭제: 불필요하게 디스크 공간을 차지하며, 나중에 실행할 때 혼동이나 충돌을 일으킬 수 있음
        os.remove(dummy_input_path)
        print(f"Removed '{dummy_input_path}'.") 

    except FileNotFoundError:
         print("-" * 30)
         print("WARNING: Could not create dummy data because a model is not found.")
         print("Please run the training pipeline first to generate the models.")
         print("Skipping __main__ block execution.")
    except Exception as e:
        print(f"An error occurred in main: {e}")


if __name__ == '__main__':
    main()