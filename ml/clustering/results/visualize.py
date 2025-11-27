import pandas as pd
import numpy as np
import os
import argparse
import umap

from ml.clustering.data_loader import load_config
from ml.clustering.inference.profiling import create_cluster_profiles
from ml.clustering.results.visualization import plot_umap_clusters, plot_radar_profiles as plot_overlaid_radar_profiles, plot_individual_radar_profiles_grid

def main():
    """
    Main function to run the visualization part of the pipeline for a specific experiment.
    Loads trained model outputs and generates reports.
    """
    parser = argparse.ArgumentParser(description="Visualize the results of a clustering experiment.")
    parser.add_argument(
        '--experiment', 
        type=str, 
        default='hdbscan_betavae', 
        help="Name of the experiment to visualize (e.g., 'gmm_vae')."
    )
    args = parser.parse_args()

    print(f"--- Starting visualization for experiment: {args.experiment} ---")
    
    config = load_config(args.experiment)
    
    exp_output_dir = os.path.join(config['paths']['output_dir'], args.experiment)
    final_data_path = os.path.join(exp_output_dir, 'final_clustered_data.csv')
    embedding_path = os.path.join(exp_output_dir, 'cluster_input_embedding.npy')
    
    print(f"Loading processed data from: {exp_output_dir}")
    try:
        df_final = pd.read_csv(final_data_path)
        cluster_embedding = np.load(embedding_path)
    except FileNotFoundError as e:
        print(f"Error: Required file not found. {e}")
        print(f"Please run the training pipeline for the '{args.experiment}' experiment first.")
        return

    raw_means, rank_profiles = create_cluster_profiles(df_final, config)

    config['paths']['report_dir'] = os.path.join(config['paths']['report_dir'], args.experiment)

    # --- UMAP Visualization Logic ---
    if cluster_embedding.shape[1] == 2:
        print("Embedding is 2D. Plotting directly.")
        embedding_for_plot = cluster_embedding
    else:
        print(f"Embedding is {cluster_embedding.shape[1]}D. Running a new 2D UMAP for visualization.")
        plot_umap_params = config['visualization']['umap_for_plot']
        reducer = umap.UMAP(
            n_neighbors=plot_umap_params['n_neighbors'],
            min_dist=plot_umap_params['min_dist'],
            n_components=2,
            random_state=42
        )
        embedding_for_plot = reducer.fit_transform(cluster_embedding)
        
    plot_umap_clusters(embedding_for_plot, df_final['Cluster'].values, config)
    
    if not rank_profiles.empty:
        plot_overlaid_radar_profiles(rank_profiles, config)
        plot_individual_radar_profiles_grid(rank_profiles, config)
    
    print(f"\n--- Visualization for '{args.experiment}' finished successfully! ---")
    print(f"Reports saved to: {config['paths']['report_dir']}")

if __name__ == '__main__':
    main()
