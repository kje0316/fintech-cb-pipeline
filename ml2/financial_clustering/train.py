import pandas as pd
import numpy as np
import joblib
import os
import argparse

# Import all necessary modules from the src folder
from ml2.financial_clustering.src.data_loader import load_config, load_raw_data, rename_columns
from ml2.financial_clustering.src.preprocessing import cleanse_data, transform_features, reduce_features_by_pca
from ml2.financial_clustering.src.models import get_model
from ml2.financial_clustering.src.clustering import reduce_dimensions_umap, perform_clustering, refine_clusters_by_probability
from ml2.financial_clustering.src.evaluation import evaluate_clustering
from ml2.financial_clustering.src.profiling import create_cluster_profiles

def main():
    """
    Main function to run the complete financial clustering training pipeline.
    """
    parser = argparse.ArgumentParser(description="Run a training experiment for financial clustering.")
    parser.add_argument(
        '--config', 
        type=str, 
        default='hdbscan_betavae', 
        help="Name of the experiment config file (e.g., 'hdbscan_betavae')."
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

    # --- Create Experiment-Specific Output Directories ---
    exp_name = config['experiment_name']
    model_dir = os.path.join(config['paths']['model_dir'], exp_name)
    output_dir = os.path.join(config['paths']['output_dir'], exp_name)

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
    np.save(os.path.join(output_dir, 'cluster_input_embedding.npy'), cluster_input)
    df_clean.to_csv(os.path.join(output_dir, 'final_clustered_data.csv'), index=False, encoding='utf-8-sig')
    print(f"Processed data and artifacts saved to: {output_dir}")

    print(f"\n--- Experiment '{args.config}' finished successfully! ---")


if __name__ == '__main__':
    main()

