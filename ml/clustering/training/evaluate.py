import numpy as np
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from typing import Dict

def evaluate_clustering(X: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
    """
    Calculates and prints key performance metrics for a clustering result.
    Assumes that noise points (-1) have already been filtered out.

    Args:
        X: The data used for clustering (e.g., UMAP embedding or latent vectors).
        labels: The cluster labels for each data point.

    Returns:
        A dictionary containing the calculated metrics.
    """
    print("9. Evaluating clustering performance...")
    
    # Ensure there's more than one cluster to evaluate
    if len(np.unique(labels)) < 2:
        print("Cannot evaluate with less than 2 clusters.")
        return {}

    # 1. Silhouette Score
    # Using a sample to speed up calculation for large datasets.
    sample_size = 10000 if len(X) > 10000 else len(X)
    sil_score = silhouette_score(X, labels, metric='euclidean', sample_size=sample_size)
    
    # 2. Davies-Bouldin Index
    db_score = davies_bouldin_score(X, labels)
    
    # 3. Calinski-Harabasz Index
    ch_score = calinski_harabasz_score(X, labels)
    
    print("="*40)
    print(" [Clustering Performance Metrics]")
    print("="*40)
    print(f"1. Silhouette Score (High is good): {sil_score:.4f}")
    print(f"2. Davies-Bouldin Index (Low is good): {db_score:.4f}")
    print(f"3. Calinski-Harabasz Index (High is good): {ch_score:.4f}")
    print("="*40)
    
    metrics = {
        'silhouette': sil_score,
        'davies_bouldin': db_score,
        'calinski_harabasz': ch_score
    }
    
    return metrics
