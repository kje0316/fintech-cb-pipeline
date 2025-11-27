import pandas as pd
import numpy as np
import umap.umap_ as umap
import hdbscan
from sklearn.mixture import GaussianMixture
from typing import Dict, Any, Tuple, Union

def reduce_dimensions_umap(data: np.ndarray, config: Dict[str, Any]) -> Tuple[np.ndarray, umap.UMAP]:
    """
    Reduces the dimensionality of the data using UMAP.

    Args:
        data: The high-dimensional data (e.g., VAE latent vectors).
        config: The main configuration dictionary.

    Returns:
        A tuple containing:
        - The low-dimensional embedding of the data.
        - The fitted UMAP reducer object.
    """
    umap_params = config['modeling']['umap_for_clustering']
    print(f"6. Reducing dimensions with UMAP (n_components={umap_params['n_components']})...")
    
    reducer = umap.UMAP(
        n_neighbors=umap_params['n_neighbors'],
        min_dist=umap_params['min_dist'],
        n_components=umap_params['n_components'],
        random_state=42,
        n_jobs=-1,
        verbose=False
    )
    embedding = reducer.fit_transform(data)
    print("Dimensionality reduction complete.")
    return embedding, reducer

def get_clusterer(config: Dict[str, Any]) -> Union[hdbscan.HDBSCAN, GaussianMixture]:
    """
    Factory function to get the specified clustering model from the config.
    """
    algo = config['modeling']['clustering_algo']
    
    if algo == 'hdbscan':
        params = config['modeling']['hdbscan']
        return hdbscan.HDBSCAN(**params)
    elif algo == 'gmm':
        params = config['modeling']['gmm']
        return GaussianMixture(**params)
    else:
        raise ValueError(f"Unknown clustering algorithm specified: {algo}")

def perform_clustering(data: np.ndarray, config: Dict[str, Any]) -> Tuple[Any, np.ndarray, np.ndarray]:
    """
    Performs clustering on the data using the algorithm specified in the config.

    Args:
        data: The data to be clustered (e.g., UMAP embedding or latent vectors).
        config: The main configuration dictionary.

    Returns:
        A tuple containing:
        - The fitted clusterer object.
        - An array of cluster labels.
        - An array of cluster membership probabilities.
    """
    algo = config['modeling']['clustering_algo']
    print(f"7. Performing clustering with {algo}...")
    
    clusterer = get_clusterer(config)
    
    if algo == 'hdbscan':
        clusterer.fit(data)
        labels = clusterer.labels_
        probabilities = clusterer.probabilities_
    elif algo == 'gmm':
        labels = clusterer.fit_predict(data)
        # GMM's predict_proba gives probability for each cluster, so we take the max
        # This is analogous to HDBSCAN's probability for the assigned cluster
        probabilities = clusterer.predict_proba(data).max(axis=1)
    else:
        raise NotImplementedError(f"Clustering algorithm '{algo}' is not implemented.")

    print(f"Clustering complete. Found {len(np.unique(labels))} clusters (including noise if any).")
    return clusterer, labels, probabilities

def refine_clusters_by_probability(labels: np.ndarray, probabilities: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
    """
    Refines cluster labels by converting low-probability members to noise (-1).
    This is primarily designed for HDBSCAN outputs.

    Args:
        labels: The original cluster labels.
        probabilities: The membership probabilities.
        config: The main configuration dictionary.

    Returns:
        An array of refined cluster labels.
    """
    if not config['soft_clustering']['enabled']:
        print("Soft clustering refinement is disabled. Skipping.")
        return labels

    threshold = config['soft_clustering']['probability_threshold']
    print(f"8. Refining clusters with probability threshold > {threshold}...")

    refined_labels = labels.copy()
    refined_labels[probabilities < threshold] = -1
    
    original_noise = np.sum(labels == -1) / len(labels) if len(labels) > 0 else 0
    new_noise = np.sum(refined_labels == -1) / len(refined_labels) if len(refined_labels) > 0 else 0
    
    print(f"Noise ratio changed from {original_noise:.2%} to {new_noise:.2%}.")
    return refined_labels
