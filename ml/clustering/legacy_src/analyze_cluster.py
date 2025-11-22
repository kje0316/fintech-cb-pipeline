import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Optional
import umap.umap_ as umap # Add import
from .util import load_data # Add import
from pathlib import Path
import yaml


def visualize_clusters_umap(
    df_scaled: pd.DataFrame,
    cluster_labels: pd.Series,
    n_neighbors: int = 30,
    min_dist: float = 0.1,
    n_components: int = 2,
    random_state: int = 42,
    title: str = 'UMAP Visualization of Clusters'
) -> pd.DataFrame:
    """
    UMAP을 사용하여 클러스터링 결과를 시각화합니다.
    
    :param df_scaled: 스케일링된 원본 데이터 (범주형 OHE + 수치형 스케일링)
    :param cluster_labels: 클러스터 라벨 (예: K-Means 결과)
    :param n_neighbors: UMAP 이웃 개수 (낮으면 로컬, 높으면 글로벌 구조)
    :param min_dist: UMAP 점들이 얼마나 빽빽하게 뭉칠지
    :param n_components: UMAP 차원 (2D로 시각화)
    :param random_state: UMAP 랜덤 시드
    :param title: 시각화 제목
    :return: UMAP 임베딩과 클러스터 라벨이 포함된 DataFrame
    """
    print("Starting UMAP visualization...")

    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        n_components=n_components,
        random_state=random_state,
        verbose=True # Suppress UMAP verbose output for cleaner logs
    )

    embedding = reducer.fit_transform(df_scaled)

    umap_df = pd.DataFrame(embedding, columns=[f'UMAP {i+1}' for i in range(n_components)])
    umap_df['cluster'] = cluster_labels.reset_index(drop=True) # Ensure index alignment

    plt.figure(figsize=(12, 8))
    sns.scatterplot(
        data=umap_df,
        x='UMAP 1',
        y='UMAP 2',
        hue='cluster',
        palette='tab20',
        legend='full',
        s=10,
        alpha=0.5
    )
    plt.title(title)
    plt.xlabel('UMAP Component 1')
    plt.ylabel('UMAP Component 2')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    # plt.savefig('path/to/umap_cluster_visualization.png')
    plt.show()
    
    print("UMAP visualization finished.")
    return umap_df


def profile_clusters(df: pd.DataFrame, cluster_col: str, numeric_cols: List[str]) -> pd.DataFrame:
    """
    각 군집의 특성을 분석하고 프로파일링합니다.
    (수치형 변수의 .describe() 통계량 비교)
    """
    print("Profiling clusters using detailed statistics...")
    
    # .mean() 대신 .describe()를 사용
    profile = df.groupby(cluster_col)[numeric_cols].describe()
    
    # 멀티인덱스를 보기 쉽게 T (Transpose)를 두 번 사용
    profile_transposed = profile.T.reset_index().rename(columns={'level_0': 'Feature', 'level_1': 'Statistic'})
    print(profile_transposed)
    
    # (팁) 특정 통계량(e.g., median)만 볼 수도 있습니다.
    # median_profile = df.groupby(cluster_col)[numeric_cols].median()
    # print("\n--- Median Profile ---")
    # print(median_profile)
    
    return profile


def profile_categorical_clusters(df: pd.DataFrame, cluster_col: str, categorical_cols: List[str]):
    """
    범주형 변수의 분포를 통해 군집의 '구성비'를 프로파일링합니다.
    """
    print("\nProfiling categorical features (Composition)...")
    
    for col in categorical_cols:
        # 'index' 기준 정규화: 각 클러스터(index)의 합이 1(100%)이 되도록 비율 계산
        crosstab_profile = pd.crosstab(df[cluster_col], df[col], normalize='index')
        
        # (선택) 상위 5개 항목만 출력
        print(f"\n--- Profile for '{col}' (Top 5 categories per cluster) ---")
        for cluster_id in crosstab_profile.index:
            top_categories = crosstab_profile.loc[cluster_id].nlargest(5)
            print(f"Cluster {cluster_id}:")
            print(top_categories[top_categories > 0]) # 0%인 항목은 제외



def profile_clusters_with_index(df: pd.DataFrame, cluster_col: str, numeric_cols: List[str]):
    """
    전체 평균과 대비하여 각 군집의 '상대적 위치(Index)'를 프로파일링합니다.
    """
    print("\nProfiling clusters relative to overall mean (Index)...")
    
    # 1. 전체 평균
    overall_mean = df[numeric_cols].mean()
    
    # 2. 군집별 평균
    cluster_mean = df.groupby(cluster_col)[numeric_cols].mean()
    
    # 3. Index 계산 (Cluster Mean / Overall Mean)
    # (broadcasting을 이용해 각 행(군집)에 overall_mean을 나눔)
    relative_profile = cluster_mean / overall_mean
    
    print(relative_profile)
    return relative_profile


def analysis_pipeline(prediction_path: str, cleansed_data_path: str, scaled_data_path: str, skip_visualization: bool = True) -> None:
    """
    전체 클러스터 분석 파이프라인을 실행합니다.
    1. 예측 결과와 정제된 데이터 로드 및 병합
    2. UMAP 기반 클러스터 시각화 (skip_visualization이 False일 경우)
    3. 클러스터 프로파일링 (수치형/범주형)
    
    :param prediction_path: 군집 예측 결과 파일 경로 (클러스터 라벨 포함)
    :param cleansed_data_path: 정제된 데이터 파일 경로 (프로파일링용)
    :param scaled_data_path: 스케일링된 데이터 파일 경로 (UMAP 시각화용)
    :param skip_visualization: 시각화 단계를 건너뛸지 여부 (기본값: False)
    """
    print("Cluster analysis pipeline started.")
    
    df_predictions = load_data(prediction_path)
    df_cleansed = load_data(cleansed_data_path)
    df_scaled = load_data(scaled_data_path)
    
    # 분석을 위해 예측 결과와 원본 데이터를 병합 (공통 key 필요)
    # 여기서는 df_cleansed의 인덱스를 기준으로 병합한다고 가정
    df_merged = df_cleansed.copy()
    df_merged['cluster'] = df_predictions['cluster']

    # 2. UMAP 기반 클러스터 시각화
    if not skip_visualization:
        visualize_clusters_umap(
            df_scaled=df_scaled,
            cluster_labels=df_merged['cluster'],
            n_neighbors=30,
            min_dist=0.1,
            n_components=2,
            title='UMAP Visualization of K-Means Clusters'
        )
    else:
        print("UMAP visualization skipped as requested.")
    
    # 3. 클러스터 프로파일링
    print("\n--- Starting Cluster Profiling ---")
    numeric_cols = [col for col in df_cleansed.columns if pd.api.types.is_numeric_dtype(df_cleansed[col])]
    categorical_cols = [col for col in df_cleansed.columns if df_cleansed[col].dtype == 'object']
    
    # 3-1. 수치형 변수 상세 통계 프로파일링
    profile_clusters(df_merged, 'cluster', numeric_cols)
    
    # 3-2. 범주형 변수 구성비 프로파일링
    profile_categorical_clusters(df_merged, 'cluster', categorical_cols)
    
    # 3-3. 수치형 변수 상대 위치 프로파일링
    profile_clusters_with_index(df_merged, 'cluster', numeric_cols)
    
    print("\n--- Cluster Profiling Finished ---")
    print("Cluster analysis pipeline finished.")


def main():
    """
    클러스터 분석 파이프라인을 실행하는 메인 함수.
    이 파이프라인을 실행하기 전에, build_features.py, train_cluster.py, predict_cluster.py를 통해
    필요한 데이터와 모델이 생성되어 있어야 합니다.
    """
    project_root = Path(__file__).resolve().parents[3]

    # config/local_settings.yaml에서 경로 설정 로드
    config_path = project_root / 'config' / 'local_settings.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    paths_config = config['paths']

    # 분석에 필요한 파일 경로 정의
    PREDICTION_PATH = project_root / "predictions.csv" # predict_cluster.py의 결과
    CLEANSED_DATA_PATH = project_root / paths_config['cleansed_data_path'] # build_features.py에서 저장
    SCALED_DATA_PATH = project_root / "data" / "processed" / "clustering_features.csv" # build_features.py의 결과

    # 시각화 건너뛰기 옵션 (기본값: True)
    SKIP_VISUALIZATION = True

    analysis_pipeline(
        prediction_path=str(PREDICTION_PATH),
        cleansed_data_path=str(CLEANSED_DATA_PATH),
        scaled_data_path=str(SCALED_DATA_PATH),
        skip_visualization=SKIP_VISUALIZATION,
    )


if __name__ == '__main__':
    main()




