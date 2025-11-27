import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import umap.umap_ as umap
from typing import Dict, Any
import os
import math

# Set Korean font for macOS
try:
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False
except Exception as e:
    print(f"Could not set Korean font: {e}")
    print("Please install 'AppleGothic' font or modify the font setting in 'src/visualization.py'")


def plot_umap_clusters(embedding: np.ndarray, labels: np.ndarray, config: Dict[str, Any]):
    """
    Generates and saves a scatter plot of a 2D UMAP projection, colored by cluster label.
    """
    print("10. Generating UMAP cluster visualization...")
    
    if embedding.shape[1] != 2:
        raise ValueError("Input embedding must be 2-dimensional for plotting.")

    plot_df = pd.DataFrame(embedding, columns=['UMAP_1', 'UMAP_2'])
    plot_df['Cluster'] = labels
    clean_mask = labels != -1
    
    plt.figure(figsize=(14, 10))
    
    sns.scatterplot(
        data=plot_df[clean_mask], 
        x='UMAP_1', 
        y='UMAP_2', 
        hue='Cluster', 
        palette='viridis',
        s=10, alpha=0.7, edgecolor=None
    )
    
    if np.sum(~clean_mask) > 0:
        sns.scatterplot(
            data=plot_df[~clean_mask],
            x='UMAP_1', y='UMAP_2',
            color='lightgrey', s=5, alpha=0.2, label='Noise'
        )

    plt.title(f"Clustering Result ({config['experiment_name']})", fontsize=16)
    plt.xlabel('UMAP Dimension 1')
    plt.ylabel('UMAP Dimension 2')
    plt.legend(title='Cluster Group', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    
    report_dir = os.path.join(config['paths']['report_dir'], config['experiment_name'])
    os.makedirs(report_dir, exist_ok=True)
    save_path = os.path.join(report_dir, 'umap_cluster_visualization.png')
    plt.savefig(save_path)
    print(f"UMAP plot saved to {save_path}")
    plt.show()

def plot_radar_profiles(rank_data: pd.DataFrame, config: Dict[str, Any]):
    """
    Generates and saves a radar chart for all cluster profiles overlaid.
    """
    print("Generating overlaid radar chart of cluster profiles...")
    
    labels = rank_data.columns.tolist()
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(polar=True))
    
    for i, (cid, row) in enumerate(rank_data.iterrows()):
        values = row.tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=2, linestyle='solid', label=f'Cluster {cid}')
        ax.fill(angles, values, alpha=0.1)
        
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=11)
    
    plt.title('All Cluster Profiles (Relative Rank)', size=16, y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    report_dir = os.path.join(config['paths']['report_dir'], config['experiment_name'])
    os.makedirs(report_dir, exist_ok=True)
    save_path = os.path.join(report_dir, 'cluster_profile_radar_chart_overlaid.png')
    plt.savefig(save_path)
    print(f"Overlaid radar chart saved to {save_path}")
    plt.show()

def plot_individual_radar_profiles_grid(rank_data: pd.DataFrame, config: Dict[str, Any]):
    """
    Generates and saves a grid of radar charts, one for each cluster profile.
    """
    print("Generating grid of individual radar charts...")
    
    labels = rank_data.columns.tolist()
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    n_clusters = rank_data.shape[0]
    n_cols = 3
    n_rows = math.ceil(n_clusters / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 5, n_rows * 5), subplot_kw=dict(polar=True))
    axes = axes.flatten()

    for i, (cid, row) in enumerate(rank_data.iterrows()):
        ax = axes[i]
        values = row.tolist()
        values += values[:1]

        ax.plot(angles, values, linewidth=2, linestyle='solid', label=f'Cluster {cid}')
        ax.fill(angles, values, alpha=0.2)
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, size=8)
        ax.set_title(f'Cluster {cid}', size=12, y=1.1)
        ax.set_yticklabels([])

    for i in range(n_clusters, len(axes)):
        axes[i].set_visible(False)

    plt.suptitle('Individual Cluster Profiles (Relative Rank)', size=20, y=1.02)
    plt.tight_layout()

    report_dir = os.path.join(config['paths']['report_dir'], config['experiment_name'])
    os.makedirs(report_dir, exist_ok=True)
    save_path = os.path.join(report_dir, 'cluster_profiles_grid.png')
    plt.savefig(save_path)
    print(f"Grid of radar charts saved to {save_path}")
    plt.show()

def plot_benchmark_radar_chart(ranked_profiles: pd.DataFrame, config: Dict[str, Any], input_filename: str):
    """
    Generates a radar chart comparing an input company to its cluster and the overall average.
    """
    print("Generating benchmark radar chart...")
    
    labels = ranked_profiles.columns.tolist()
    num_vars = len(labels)
    
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(polar=True))
    
    colors = {'Input Company': 'red', 'Cluster Average': 'blue', 'Overall Average': 'grey'}
    
    for i, (profile_name, row) in enumerate(ranked_profiles.iterrows()):
        values = row.tolist()
        values += values[:1]
        
        color = colors.get(profile_name, 'black')
        zorder = 3 if profile_name == 'Input Company' else 2
        linewidth = 2.5 if profile_name == 'Input Company' else 2.0
        alpha = 0.2 if profile_name == 'Input Company' else 0.1

        ax.plot(angles, values, linewidth=linewidth, linestyle='solid', label=profile_name, color=color, zorder=zorder)
        ax.fill(angles, values, alpha=alpha, color=color)
        
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=11)
    
    plt.title('Company Financial Positioning Benchmark', size=16, y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    report_dir = os.path.join(config['paths']['report_dir'], config['experiment_name'])
    os.makedirs(report_dir, exist_ok=True)
    
    save_path = os.path.join(report_dir, f'benchmark_{input_filename}.png')
    plt.savefig(save_path)
    print(f"Benchmark radar chart saved to {save_path}")
    plt.show()
