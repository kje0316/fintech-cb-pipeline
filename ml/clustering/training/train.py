import pandas as pd
import numpy as np
import joblib
import os
import argparse
import tempfile
from pathlib import Path

import mlflow
import mlflow.pyfunc
import mlflow.sklearn
from mlflow.tracking import MlflowClient

# Import all necessary modules
from ml.clustering.data_loader import load_config, load_raw_data, rename_columns
from ml.clustering.features.build_features import cleanse_data, transform_features, reduce_features_by_pca
from ml.clustering.training.models.vae import get_model
from ml.clustering.training.clustering import reduce_dimensions_umap, perform_clustering, refine_clusters_by_probability
from ml.clustering.training.evaluate import evaluate_clustering
from ml.clustering.inference.profiling import create_cluster_profiles


def register_clustering_model(
    run_id: str,
    model_name: str,
    metrics: dict,
    n_clusters: int,
    promote_to_production: bool = True
) -> mlflow.entities.model_registry.ModelVersion:
    """MLflow Model Registry에 클러스터링 모델 등록 및 Production 승격"""
    print(f"\n📋 Model Registry에 클러스터링 모델 등록 중...")

    try:
        client = MlflowClient()

        # artifacts URI 구성
        artifact_uri = mlflow.get_artifact_uri("clustering_model")
        print(f"  Artifact URI: {artifact_uri}")

        # Model Registry에 등록 (없으면 생성)
        try:
            client.create_registered_model(model_name)
            print(f"  ✅ 모델 '{model_name}' 생성됨")
        except Exception:
            print(f"  ℹ️  모델 '{model_name}' 이미 존재")

        # 모델 버전 생성
        model_version = client.create_model_version(
            name=model_name,
            source=artifact_uri,
            run_id=run_id,
            tags={
                "model_type": "CLUSTERING",
                "algorithm": "VAE+HDBSCAN",
                "n_clusters": str(n_clusters),
                "silhouette_score": str(metrics.get('silhouette_score', 0))
            }
        )

        version = model_version.version
        print(f"  ✅ 모델 등록 완료: {model_name} (버전 {version})")

        # 모델 버전에 설명 추가
        client.update_model_version(
            name=model_name,
            version=version,
            description=f"Clustering model with {n_clusters} clusters. "
                        f"Silhouette: {metrics.get('silhouette_score', 0):.4f}"
        )

        # Production 스테이지로 승격
        if promote_to_production:
            print(f"  🚀 Production 스테이지로 승격 중...")

            # 기존 Production 모델을 Archived로
            try:
                existing_prod = client.get_latest_versions(model_name, stages=["Production"])
                for v in existing_prod:
                    client.transition_model_version_stage(
                        name=model_name,
                        version=v.version,
                        stage="Archived"
                    )
                    print(f"     v{v.version} → Archived")
            except Exception:
                pass

            # 새 버전을 Production으로
            client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage="Production"
            )
            print(f"  ✅ v{version} → Production")

        return model_version

    except Exception as e:
        print(f"  ⚠️  Model Registry 등록 중 오류: {e}")
        return None


def run_clustering_pipeline(
    config_name: str = 'final_notebook_model',
    data_path: str = None,
    save_models: bool = True,
    experiment_name: str = 'clustering',
    register_to_mlflow: bool = True
) -> dict:
    """
    클러스터링 파이프라인 실행 함수 (프로그램적 호출용)

    Args:
        config_name: 설정 파일 이름 (예: 'hdbscan_betavae')
        data_path: 데이터 경로 (None이면 config에서 지정된 경로 사용)
        save_models: 모델 저장 여부
        experiment_name: MLflow 실험 이름
        register_to_mlflow: MLflow Registry에 등록 여부

    Returns:
        dict: 학습 결과 (클러스터 수, 평가 지표 등)
    """
    print(f"\n{'='*60}")
    print(f"클러스터링 파이프라인 시작: {config_name}")
    print(f"{'='*60}")

    # MLflow 설정
    mlflow.set_tracking_uri("sqlite:///mlflow_db/mlflow.db")
    mlflow.set_experiment(experiment_name)

    # 1. Load Configuration
    config = load_config(config_name)

    # Override data path if provided
    if data_path:
        config['data']['raw_path'] = data_path

    # 2. Load and Prepare Data
    print("\n📂 데이터 로딩 중...")
    df_raw = load_raw_data(config)
    df_renamed = rename_columns(df_raw, config)
    print(f"  - 원본 데이터: {len(df_raw):,}건")

    # 3. Preprocess Data
    print("\n🔧 전처리 중...")
    df_clean = cleanse_data(df_renamed, config)
    df_transformed, qt, imputer = transform_features(df_clean, config)
    print(f"  - 전처리 후: {len(df_clean):,}건")

    # 3.5 (Optional) Reduce features with PCA
    if config['preprocessing'].get('use_pca', False):
        vae_input_features = reduce_features_by_pca(df_transformed, config)
    else:
        vae_input_features = df_transformed

    # 4. Train VAE Model and get Latent Vectors
    print("\n🧠 VAE 모델 학습 중...")
    input_dim = vae_input_features.shape[1]
    vae_model = get_model(config, input_dim=input_dim)
    vae_model.fit(vae_input_features.values)
    financial_dna = vae_model.transform(vae_input_features.values)
    print(f"  - Latent dimension: {financial_dna.shape[1]}")

    # 5. Perform Clustering
    print("\n📊 클러스터링 수행 중...")
    umap_reducer = None
    if config['modeling']['umap_for_clustering'].get('enabled', True):
        umap_embedding, umap_reducer = reduce_dimensions_umap(financial_dna, config)
        cluster_input = umap_embedding
    else:
        cluster_input = financial_dna

    clusterer, labels, probabilities = perform_clustering(cluster_input, config)

    # 6. Refine clusters if enabled
    final_labels = refine_clusters_by_probability(labels, probabilities, config)
    df_clean['Cluster'] = final_labels

    n_clusters = len(set(final_labels)) - (1 if -1 in final_labels else 0)
    n_noise = np.sum(final_labels == -1)
    print(f"  - 클러스터 수: {n_clusters}")
    print(f"  - 노이즈: {n_noise:,}건 ({n_noise/len(final_labels)*100:.1f}%)")

    # 7. Evaluate and Profile
    evaluation_metrics = {}
    valid_data_mask = final_labels != -1
    if np.sum(valid_data_mask) > 0:
        print("\n📈 클러스터 평가 중...")
        evaluation_metrics = evaluate_clustering(cluster_input[valid_data_mask], final_labels[valid_data_mask])
        if config['pipeline_params'].get('run_profiling', False):
            create_cluster_profiles(df_clean, config)

    # 8. Save Models and Results
    model_dir = Path(config['paths']['model_dir'])
    output_dir = Path(config['paths']['output_dir'])

    # ============================================================
    # MLflow 로깅 시작
    # ============================================================
    model_version = None
    run_id = None

    with mlflow.start_run(run_name=f"clustering_{config_name}") as run:
        run_id = run.info.run_id
        print(f"\n📊 MLflow 로깅 중... (Run ID: {run_id[:8]})")

        # 파라미터 로깅
        mlflow.log_param("config_name", config_name)
        mlflow.log_param("n_samples", len(df_clean))
        mlflow.log_param("n_features", vae_input_features.shape[1])
        mlflow.log_param("latent_dim", financial_dna.shape[1])

        # VAE 파라미터
        vae_config = config.get('modeling', {}).get('vae', {})
        mlflow.log_param("vae_latent_dim", vae_config.get('latent_dim', 16))
        mlflow.log_param("vae_epochs", vae_config.get('epochs', 100))

        # HDBSCAN 파라미터
        hdbscan_config = config.get('modeling', {}).get('hdbscan', {})
        mlflow.log_param("hdbscan_min_cluster_size", hdbscan_config.get('min_cluster_size', 50))
        mlflow.log_param("hdbscan_min_samples", hdbscan_config.get('min_samples', 10))

        # 메트릭 로깅
        mlflow.log_metric("n_clusters", n_clusters)
        mlflow.log_metric("n_noise", n_noise)
        mlflow.log_metric("noise_ratio", n_noise / len(final_labels))

        if evaluation_metrics:
            if evaluation_metrics.get('silhouette_score') is not None:
                mlflow.log_metric("silhouette_score", evaluation_metrics['silhouette_score'])
            if evaluation_metrics.get('calinski_harabasz_score') is not None:
                mlflow.log_metric("calinski_harabasz_score", evaluation_metrics['calinski_harabasz_score'])
            if evaluation_metrics.get('davies_bouldin_score') is not None:
                mlflow.log_metric("davies_bouldin_score", evaluation_metrics['davies_bouldin_score'])

        # 모델 아티팩트 저장 (임시 디렉토리 사용)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 각 모델 컴포넌트 저장
            joblib.dump(vae_model, tmpdir / 'vae_model.pkl')
            joblib.dump(clusterer, tmpdir / 'clusterer.pkl')
            joblib.dump(qt, tmpdir / 'quantile_transformer.pkl')
            joblib.dump(imputer, tmpdir / 'imputer.pkl')
            if umap_reducer:
                joblib.dump(umap_reducer, tmpdir / 'umap_reducer.pkl')

            # 메타데이터 저장
            import json
            metadata = {
                'config_name': config_name,
                'n_clusters': n_clusters,
                'n_features': vae_input_features.shape[1],
                'latent_dim': financial_dna.shape[1],
                'has_umap': umap_reducer is not None,
                'feature_names': list(vae_input_features.columns) if hasattr(vae_input_features, 'columns') else [],
                'metrics': evaluation_metrics
            }
            with open(tmpdir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            # MLflow에 아티팩트 로깅
            mlflow.log_artifacts(str(tmpdir), artifact_path="clustering_model")

        print(f"  ✅ MLflow 아티팩트 저장 완료")

        # Model Registry에 등록
        if register_to_mlflow:
            model_version = register_clustering_model(
                run_id=run_id,
                model_name="clustering_model",
                metrics=evaluation_metrics,
                n_clusters=n_clusters
            )

    # ============================================================
    # 로컬 저장 (fallback용)
    # ============================================================
    if save_models and config['pipeline_params'].get('save_models', True):
        print("\n💾 로컬에 모델 저장 중 (fallback용)...")
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(vae_model, model_dir / 'vae_model.pkl')
        joblib.dump(clusterer, model_dir / 'clusterer.pkl')
        joblib.dump(qt, model_dir / 'quantile_transformer.pkl')
        joblib.dump(imputer, model_dir / 'imputer.pkl')
        if umap_reducer:
            joblib.dump(umap_reducer, model_dir / 'umap_reducer.pkl')
        print(f"  - 모델 저장 위치: {model_dir}")

    # Save output data
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / 'financial_dna.npy', financial_dna)
    np.save(output_dir / 'cluster_embedding.npy', cluster_input)
    df_clean.to_csv(output_dir / 'clustered_data.csv', index=False, encoding='utf-8-sig')
    print(f"  - 결과 저장 위치: {output_dir}")

    print(f"\n{'='*60}")
    print(f"✅ 클러스터링 파이프라인 완료!")
    print(f"{'='*60}")

    return {
        'n_clusters': n_clusters,
        'n_noise': n_noise,
        'n_samples': len(df_clean),
        'silhouette_score': evaluation_metrics.get('silhouette_score'),
        'calinski_harabasz_score': evaluation_metrics.get('calinski_harabasz_score'),
        'davies_bouldin_score': evaluation_metrics.get('davies_bouldin_score'),
        'model_dir': str(model_dir),
        'output_dir': str(output_dir),
        'config_name': config_name,
        'mlflow_run_id': run_id,
        'model_version': model_version.version if model_version else None
    }


def main():
    """
    Main function to run the complete financial clustering training pipeline.
    """
    parser = argparse.ArgumentParser(description="Run a training experiment for financial clustering.")
    parser.add_argument(
        '--config',
        type=str,
        default='final_notebook_model',
        help="Name of the experiment config file (e.g., 'final_notebook_model')."
    )
    args = parser.parse_args()

    # 1. Load Configuration
    print(f"--- Running Experiment: {args.config} ---")
    config = load_config(args.config)

    # 2. Load and Prepare Data
    df_raw = load_raw_data(config)
    df_renamed = rename_columns(df_raw, config)

    # 3. Preprocess Data
    df_clean = cleanse_data(df_renamed, config)
    df_transformed, qt, imputer = transform_features(df_clean, config)

    # 3.5 (Optional) Reduce features with PCA
    if config['preprocessing'].get('use_pca', False):
        vae_input_features = reduce_features_by_pca(df_transformed, config)
    else:
        vae_input_features = df_transformed

    # 4. Train VAE Model and get Latent Vectors
    input_dim = vae_input_features.shape[1]
    vae_model = get_model(config, input_dim=input_dim)
    vae_model.fit(vae_input_features.values)
    financial_dna = vae_model.transform(vae_input_features.values)

    # 5. Perform Clustering
    umap_reducer = None
    if config['modeling']['umap_for_clustering'].get('enabled', True):
        umap_embedding, umap_reducer = reduce_dimensions_umap(financial_dna, config)
        cluster_input = umap_embedding
    else:
        print("Skipping UMAP for clustering as per config.")
        cluster_input = financial_dna

    clusterer, labels, probabilities = perform_clustering(cluster_input, config)
    
    # 6. Refine clusters if enabled
    final_labels = refine_clusters_by_probability(labels, probabilities, config)

    # Add cluster labels to the original cleaned dataframe
    df_clean['Cluster'] = final_labels

    # 7. Evaluate and Profile
    valid_data_mask = final_labels != -1
    if np.sum(valid_data_mask) > 0:
        evaluation_metrics = evaluate_clustering(cluster_input[valid_data_mask], final_labels[valid_data_mask])
        if config['pipeline_params']['run_profiling']:
            create_cluster_profiles(df_clean, config)
    else:
        print("All data points were classified as noise. Skipping evaluation and profiling.")

    # --- Output Directories ---
    model_dir = config['paths']['model_dir']
    output_dir = config['paths']['output_dir']

    # 8. Save Models and Results
    if config['pipeline_params']['save_models']:
        os.makedirs(model_dir, exist_ok=True)
        joblib.dump(vae_model, os.path.join(model_dir, 'vae_model.pkl'))
        joblib.dump(clusterer, os.path.join(model_dir, 'clusterer.pkl'))
        joblib.dump(qt, os.path.join(model_dir, 'quantile_transformer.pkl'))
        joblib.dump(imputer, os.path.join(model_dir, 'imputer.pkl'))
        if umap_reducer:
            joblib.dump(umap_reducer, os.path.join(model_dir, 'umap_reducer.pkl'))
        
        print(f"Models saved to: {model_dir}")

    # Save data required for analysis
    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, 'financial_dna.npy'), financial_dna)
    np.save(os.path.join(output_dir, 'cluster_embedding.npy'), cluster_input)
    df_clean.to_csv(os.path.join(output_dir, 'clustered_data.csv'), index=False, encoding='utf-8-sig')
    print(f"Processed data and artifacts saved to: {output_dir}")

    print(f"\n--- Clustering training finished successfully! ---")


if __name__ == '__main__':
    main()

