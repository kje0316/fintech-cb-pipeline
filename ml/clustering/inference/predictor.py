import pandas as pd
import numpy as np
import joblib
import os
import json
import hdbscan
from typing import Dict, Any, Optional
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

from ml.clustering.data_loader import load_config, load_yaml_map
from ml.clustering.features.build_features import cleanse_data


class Predictor:
    """
    A class to handle prediction for new companies based on a specific trained clustering experiment.
    Supports loading from MLflow Registry or local files.
    """
    def __init__(
        self,
        experiment_name: str = 'final_notebook_model',
        use_mlflow_registry: bool = True,
        model_stage: str = "Production"
    ):
        """
        Initialize Predictor.

        Args:
            experiment_name: Config name for local loading fallback
            use_mlflow_registry: If True, try MLflow Registry first
            model_stage: MLflow model stage ("Production", "Staging", etc.)
        """
        self.experiment_name = experiment_name
        self.config = load_config(experiment_name)
        self.use_mlflow_registry = use_mlflow_registry
        self.metadata = {}

        if use_mlflow_registry:
            try:
                self._load_from_mlflow(model_stage)
            except Exception as e:
                print(f"⚠️ MLflow 로드 실패: {e}")
                print("   로컬 파일로 fallback...")
                self._load_from_local()
        else:
            self._load_from_local()

        # Load analysis columns
        financial_categories = load_yaml_map(self.config['paths']['financial_categories'])
        self.analysis_cols = [col for col in sum(financial_categories.values(), []) if col in self.qt.feature_names_in_]

        print("✅ Predictor initialized successfully.")

    def _load_from_mlflow(self, model_stage: str = "Production"):
        """MLflow Registry에서 모델 로드"""
        print(f"📦 MLflow Registry에서 클러스터링 모델 로딩 중 ({model_stage})...")

        mlflow.set_tracking_uri("sqlite:///mlflow_db/mlflow.db")
        client = MlflowClient()

        model_name = "clustering_model"
        versions = client.get_latest_versions(model_name, stages=[model_stage])

        if not versions:
            raise ValueError(f"{model_stage} 스테이지에 등록된 클러스터링 모델이 없습니다.")

        version = versions[0]
        model_version = version.version
        run_id = version.run_id

        print(f"  - 모델: {model_name}")
        print(f"  - 버전: {model_version}")
        print(f"  - 스테이지: {version.current_stage}")

        # 아티팩트 경로
        artifact_path = client.download_artifacts(run_id, "clustering_model")
        artifact_dir = Path(artifact_path)

        # 모델 컴포넌트 로드
        self.vae_model = joblib.load(artifact_dir / 'vae_model.pkl')
        self.clusterer = joblib.load(artifact_dir / 'clusterer.pkl')
        self.qt = joblib.load(artifact_dir / 'quantile_transformer.pkl')
        self.imputer = joblib.load(artifact_dir / 'imputer.pkl')

        # UMAP 로드 (존재하면)
        self.umap_reducer = None
        umap_path = artifact_dir / 'umap_reducer.pkl'
        if umap_path.exists():
            self.umap_reducer = joblib.load(umap_path)
            print("  - UMAP reducer 로드됨")

        # 메타데이터 로드
        metadata_path = artifact_dir / 'metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)

        print(f"  ✅ MLflow에서 모델 로드 완료 (버전 {model_version})")
        self.metadata['source'] = 'mlflow_registry'
        self.metadata['model_version'] = model_version

    def _load_from_local(self):
        """로컬 파일에서 모델 로드"""
        model_dir = self.config['paths']['model_dir']

        print(f"📦 로컬에서 모델 로딩 중: {model_dir}")

        self.vae_model = joblib.load(os.path.join(model_dir, 'vae_model.pkl'))
        self.clusterer = joblib.load(os.path.join(model_dir, 'clusterer.pkl'))
        self.qt = joblib.load(os.path.join(model_dir, 'quantile_transformer.pkl'))
        self.imputer = joblib.load(os.path.join(model_dir, 'imputer.pkl'))

        # UMAP 로드 (존재하면)
        self.umap_reducer = None
        umap_path = os.path.join(model_dir, 'umap_reducer.pkl')
        if os.path.exists(umap_path):
            self.umap_reducer = joblib.load(umap_path)
            print("  - UMAP reducer 로드됨")

        print(f"  ✅ 로컬에서 모델 로드 완료")
        self.metadata['source'] = 'local'

    def predict(self, df_new: pd.DataFrame) -> pd.DataFrame:
        """
        Predicts the cluster for a new batch of companies in a DataFrame.
        """
        print(f"\nStarting prediction for {len(df_new)} new companies using '{self.experiment_name}' model...")
        
        df_clean = cleanse_data(df_new, self.config)
        
        for col in self.analysis_cols:
            if col not in df_clean.columns:
                df_clean[col] = np.nan
        
        df_analysis = df_clean[self.analysis_cols].copy()
        df_imputed = self.imputer.transform(df_analysis)
        df_transformed = self.qt.transform(df_imputed)

        if self.config['preprocessing'].get('use_pca', False):
            print("Warning: Prediction for PCA-based models is not fully implemented.")
            vae_input_features = df_transformed 
        else:
             vae_input_features = df_transformed
        
        new_dna = self.vae_model.transform(vae_input_features)
        
        # If UMAP was used during training, apply it to the new data
        if self.umap_reducer:
            print("Applying UMAP transformation to new data...")
            cluster_input = self.umap_reducer.transform(new_dna)
        else:
            cluster_input = new_dna

        # Predict cluster
        print("Predicting clusters...")
        if isinstance(self.clusterer, hdbscan.HDBSCAN):
             predicted_clusters, _ = hdbscan.approximate_predict(self.clusterer, cluster_input)
        else: 
             predicted_clusters = self.clusterer.predict(cluster_input)

        df_clean['predicted_cluster'] = predicted_clusters
        
        print("Prediction complete.")
        return df_clean
