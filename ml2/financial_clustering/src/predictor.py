import pandas as pd
import numpy as np
import joblib
import os
import hdbscan
from typing import Dict, Any

from .data_loader import load_config, load_yaml_map
from .preprocessing import cleanse_data

class Predictor:
    """
    A class to handle prediction for new companies based on a specific trained clustering experiment.
    """
    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.config = load_config(experiment_name)
        
        model_dir = os.path.join(self.config['paths']['model_dir'], self.experiment_name)
        
        print(f"Loading models and preprocessors from: {model_dir}")
        self.vae_model = joblib.load(os.path.join(model_dir, 'vae_model.pkl'))
        self.clusterer = joblib.load(os.path.join(model_dir, 'clusterer.pkl'))
        self.qt = joblib.load(os.path.join(model_dir, 'quantile_transformer.pkl'))
        self.imputer = joblib.load(os.path.join(model_dir, 'imputer.pkl'))
        
        # Load UMAP reducer if it was used in the experiment
        self.umap_reducer = None
        umap_path = os.path.join(model_dir, 'umap_reducer.pkl')
        if os.path.exists(umap_path):
            self.umap_reducer = joblib.load(umap_path)
            print("Loaded UMAP reducer.")

        financial_categories = load_yaml_map(self.config['paths']['financial_categories'])
        self.analysis_cols = [col for col in sum(financial_categories.values(), []) if col in self.qt.feature_names_in_]
        
        print("Predictor initialized successfully.")

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
