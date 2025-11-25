import pandas as pd
import numpy as np
from typing import Any, Tuple, Dict
import os
import yaml
from pathlib import Path
from .util import load_data, save_model
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.utils import resample


def apply_dimensionality_reduction(df: pd.DataFrame, n_components: int) -> Tuple[pd.DataFrame, PCA]:
    """
    PCA를 사용하여 차원 축소를 수행하고, 학습된 PCA 모델을 반환합니다.
    
    :param df: 스케일링된 데이터프레임
    :param n_components: 축소할 차원의 수
    :return: 차원이 축소된 데이터프레임과 학습된 PCA 모델 객체
    """
    print(f"Applying PCA for dimensionality reduction to {n_components} components...")

    pca = PCA(n_components=n_components, random_state=42)
    df_pca = pca.fit_transform(df)
    
    print(f"PCA complete. Explained variance ratio of {n_components} components: {sum(pca.explained_variance_ratio_):.4f}")

    return pd.DataFrame(df_pca), pca


def train_clustering_model(df: pd.DataFrame, n_clusters: int) -> KMeans:
    """
    클러스터링 모델(K-Means)을 학습하고, 학습된 모델을 반환합니다.
    
    :param df: 차원 축소된 데이터프레임
    :param n_clusters: 군집의 수
    :return: 학습된 K-Means 모델 객체
    """
    print(f"Training clustering model with {n_clusters} clusters...")
    
    kmeans = KMeans(
        n_clusters=n_clusters, 
        n_init="auto",
        random_state=42
    )
    kmeans.fit(df)
    print("Standard KMeans clustering finished.")

    return kmeans


def evaluate_clustering_model(df_pca: pd.DataFrame, kmeans_model: KMeans, n_clusters: int, sample_size: int = 10000) -> Dict[str, float]:
    """
    클러스터링 모델의 성능을 실루엣 계수, 데이비스-불딘 인덱스, 칼린스키-하라바스 인덱스로 평가합니다.
    메모리 효율성을 위해 데이터를 샘플링하여 계산합니다.
    
    :param df_pca: PCA가 적용된 데이터프레임
    :param kmeans_model: 학습된 K-Means 모델
    :param n_clusters: 군집의 수
    :param sample_size: 평가를 위해 샘플링할 데이터 포인트 수
    :return: 각 평가 지표를 포함하는 딕셔너리
    """
    print(f"Evaluating clustering model with {n_clusters} clusters using {sample_size} samples...")
    
    # 클러스터 예측
    kmeans_clusters = kmeans_model.predict(df_pca)

    # 메모리 부족을 피하기 위해 샘플링
    if len(df_pca) > sample_size:
        sample_indices = resample(range(len(df_pca)), n_samples=sample_size, random_state=42)
        X_sample = df_pca.iloc[sample_indices]
        labels_sample = kmeans_clusters[sample_indices]
    else:
        X_sample = df_pca
        labels_sample = kmeans_clusters

    # NumPy 배열로 변환 (scikit-learn 함수 입력 요구사항)
    X_sample_np = X_sample.values
    labels_sample_np = labels_sample

    # 점수 계산
    s_score = silhouette_score(X_sample_np, labels_sample_np)
    db_score = davies_bouldin_score(X_sample_np, labels_sample_np)
    ch_score = calinski_harabasz_score(X_sample_np, labels_sample_np)

    print(f"--- K={n_clusters}일 때의 점수 ---")
    print(f"실루엣 계수 (높을수록 좋음): {s_score:.3f}")
    print(f"데이비스-불딘 인덱스 (낮을수록 좋음): {db_score:.3f}")
    print(f"칼린스키-하라바스 인덱스 (높을수록 좋음): {ch_score:.3f}")
    
    return {
        "silhouette_score": s_score,
        "davies_bouldin_score": db_score,
        "calinski_harabasz_score": ch_score
    }


def train_pipeline(data_path: str, output_dir: str) -> None:
    """
    전체 모델 학습 파이프라인을 실행합니다.
    1. 피처 데이터 로드 (스케일링 완료된 데이터)
    2. 차원 축소 (PCA)
    3. 클러스터링 모델 학습
    4. 클러스터링 모델 평가
    5. 학습된 모델(PCA, K-Means) 저장
    
    :param data_path: 피처 엔지니어링 및 스케일링이 완료된 데이터 경로
    :param output_dir: 학습된 모델들을 저장할 디렉토리 경로
    """
    print("Model training pipeline started.")
    
    # config.py 등에서 파라미터 로드
    N_COMPONENTS = 8
    N_CLUSTERS = 7
    SAMPLE_SIZE_FOR_EVAL = 10000 # 평가를 위한 샘플 크기
    
    # 1. 데이터 로드 (이미 스케일링 되었다고 가정)
    df = load_data(data_path)
    
    # 2. 차원 축소
    df_pca, pca_model = apply_dimensionality_reduction(df, n_components=N_COMPONENTS)
    
    # 3. 클러스터링 모델 학습
    kmeans_model = train_clustering_model(df_pca, n_clusters=N_CLUSTERS)
    
    # 4. 클러스터링 모델 평가
    evaluation_scores = evaluate_clustering_model(df_pca, kmeans_model, N_CLUSTERS, SAMPLE_SIZE_FOR_EVAL)
    print(f"Model evaluation completed: {evaluation_scores}")

    # 5. 모델 저장
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    save_model(pca_model, os.path.join(output_dir, "pca_model.pkl"))
    save_model(kmeans_model, os.path.join(output_dir, "kmeans_model.pkl"))
    
    print("Model training pipeline finished.")


def main():
    """
    모델 학습 파이프라인을 실행하는 메인 함수.
    이 스크립트는 build_features.py가 실행된 후에 실행되어야 합니다.
    """
    project_root = Path(__file__).resolve().parents[3]

    # config/local_settings.yaml에서 경로 설정 로드
    config_path = project_root / 'config' / 'local_settings.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    paths_config = config['paths']

    # 입력 데이터 경로 (build_features.py의 출력)
    DATA_PATH = project_root / paths_config.get('processed_data_path', 'data/processed/clustering_features.csv')
    
    # 모델 출력 디렉토리
    OUTPUT_DIR = project_root / 'ml' / 'clustering' / 'models'

    train_pipeline(data_path=str(DATA_PATH), output_dir=str(OUTPUT_DIR))


if __name__ == '__main__':
    main()

