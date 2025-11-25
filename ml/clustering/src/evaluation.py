# ml/clustering/src/evaluation.py
import pandas as pd
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score

def evaluate(df: pd.DataFrame, features: list, labels: pd.Series, metrics_to_run: list) -> dict:
    """
    클러스터링 결과를 바탕으로 성능 지표를 계산합니다.
    """
    print("--- 4. Evaluation ---")
    
    results = {}
    df_features = df[features]
    
    print("Calculating evaluation metrics...")
    for metric in metrics_to_run:
        try:
            if metric == 'Silhouette':
                score = silhouette_score(df_features, labels)
                results['silhouette_score'] = score
                print(f"  - Silhouette Score: {score:.4f}")
            elif metric == 'CalinskiHarabasz':
                score = calinski_harabasz_score(df_features, labels)
                results['calinski_harabasz_score'] = score
                print(f"  - Calinski-Harabasz Score: {score:.4f}")
            elif metric == 'DaviesBouldin':
                score = davies_bouldin_score(df_features, labels)
                results['davies_bouldin_score'] = score
                print(f"  - Davies-Bouldin Score: {score:.4f}")
        except Exception as e:
            print(f"Could not calculate {metric}. Error: {e}")
            results[metric.lower() + '_score'] = 'N/A'
            
    print("Evaluation finished.")
    return results
