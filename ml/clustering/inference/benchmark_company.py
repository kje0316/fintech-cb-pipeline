import pandas as pd
import numpy as np
import os
import argparse

from ml.clustering.data_loader import load_config
from ml.clustering.inference.predictor import Predictor
from ml.clustering.results.visualization import plot_benchmark_radar_chart

def main():
    """
    Main function to generate a benchmark radar chart for an input company.
    """
    parser = argparse.ArgumentParser(description="Generate a financial positioning benchmark for an input company.")
    parser.add_argument('input_csv', type=str, help="Path to the input CSV file with a single company's data.")
    parser.add_argument('--experiment', type=str, default='final_notebook_model', help="Name of the trained experiment model to use.")
    args = parser.parse_args()

    if not os.path.exists(args.input_csv):
        print(f"Error: Input file not found at {args.input_csv}")
        return

    print(f"--- Generating benchmark report for '{args.input_csv}' using '{args.experiment}' model ---")
    
    config = load_config(args.experiment)
    predictor = Predictor(args.experiment)
    
    full_data_path = os.path.join(config['paths']['output_dir'], args.experiment, 'final_clustered_data.csv')
    try:
        df_full = pd.read_csv(full_data_path)
    except FileNotFoundError:
        print(f"Error: Full clustered data not found for experiment '{args.experiment}'. Please run the training first.")
        return
        
    df_input = pd.read_csv(args.input_csv)
    if len(df_input) > 1:
        print("Warning: Input CSV contains more than one row. Using the first row for benchmarking.")
        df_input = df_input.head(1)

    df_predicted = predictor.predict(df_input.copy())
    predicted_cluster = df_predicted['predicted_cluster'].iloc[0]
    
    print(f"\nInput company assigned to: Cluster {predicted_cluster}")
    if predicted_cluster == -1:
        print("Company was classified as noise. Cannot generate benchmark against a specific cluster.")
        return

    # 3. Calculate Profiles
    key_metrics_map = config['profiling']['key_metrics']
    key_metrics = list(key_metrics_map.keys())
    df_non_noise = df_full[df_full['Cluster'] != -1]
    
    # Pre-calculate all cluster averages
    all_cluster_means = df_non_noise.groupby('Cluster')[key_metrics].mean()

    # Profile 1: Input Company
    profile_input = df_predicted[key_metrics].iloc[0]
    profile_input.name = "Input Company"

    # Profile 2: Cluster Average
    profile_cluster_avg = all_cluster_means.loc[predicted_cluster]
    profile_cluster_avg.name = "Cluster Average"

    # Profile 3: Overall Average
    profile_overall_avg = df_non_noise[key_metrics].mean()
    profile_overall_avg.name = "Overall Average"

    # 4. Scale profiles for radar chart
    # Combine the three specific profiles
    profiles_of_interest = pd.concat([profile_input, profile_cluster_avg, profile_overall_avg], axis=1).T

    # To rank them fairly, add them to the full distribution of cluster averages
    distribution_df = pd.concat([all_cluster_means, profiles_of_interest])
    
    # Rank everything together, dropping duplicates from the index to keep only the benchmark profiles
    ranked_distribution = distribution_df.rank(pct=True, axis=0)
    plot_data = ranked_distribution.loc[['Input Company', 'Cluster Average', 'Overall Average']]
    
    # Rename columns for plotting
    plot_data.columns = [key_metrics_map.get(c, c) for c in plot_data.columns]

    # 5. Generate and save the plot
    input_filename_base = os.path.splitext(os.path.basename(args.input_csv))[0]
    plot_benchmark_radar_chart(plot_data, config, input_filename_base)

if __name__ == '__main__':
    main()
