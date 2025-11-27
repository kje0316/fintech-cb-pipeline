import pandas as pd
from typing import Dict, Any, Tuple

def create_cluster_profiles(df_full: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Creates cluster profiles by calculating and ranking the mean of key business metrics.

    Args:
        df_full: The full DataFrame containing the original data and 'Cluster' assignments.
        config: The main configuration dictionary.

    Returns:
        A tuple containing:
        - raw_means: DataFrame of the actual mean values for each cluster's key metrics.
        - rank_profiles: DataFrame of the ranked (0-1) profiles for each cluster.
    """
    print("11. Creating cluster profiles...")

    profiling_config = config['profiling']
    key_metrics = profiling_config['key_metrics']
    
    # Filter out noise cluster (-1) for profiling
    analysis_df = df_full[df_full['Cluster'] != -1].copy()

    # Check if there are any non-noise clusters left
    if analysis_df.empty:
        print("Warning: No data left after filtering out noise. Cannot create profiles.")
        return pd.DataFrame(), pd.DataFrame()

    # A. Calculate the mean of key metrics for each cluster (Raw Data)
    raw_means = analysis_df.groupby('Cluster')[list(key_metrics.keys())].mean()
    
    # B. Rank the means to get a relative profile (0 to 1)
    # pct=True converts the rank to a percentile, making it a relative score.
    rank_profiles = raw_means.rank(pct=True, axis=0)

    # Rename columns to be more descriptive for the final report
    raw_means.columns = [key_metrics.get(c, c) for c in raw_means.columns]
    rank_profiles.columns = [key_metrics.get(c, c) for c in rank_profiles.columns]
    
    print("Cluster profiling complete.")
    
    # Display the results
    print("\n" + "="*60)
    print(" [Cluster Profiles - Raw Average Values]")
    print("="*60)
    display(raw_means.style.format("{:,.2f}").background_gradient(cmap='Blues', axis=0))
    
    print("\n" + "="*60)
    print(" [Cluster Profiles - Relative Rank (0 to 1)]")
    print("="*60)
    display(rank_profiles.style.format("{:.2%}").background_gradient(cmap='Greens', axis=0))
    
    return raw_means, rank_profiles

def display(df_styler):
    """
    A helper to render styled pandas DataFrames, as the default display
    might not work in all environments when running from a script.
    In a real script, you would save this to HTML or print the raw data.
    """
    try:
        from IPython.display import display as ipy_display
        ipy_display(df_styler)
    except ImportError:
        print("IPython not found. Printing raw DataFrame instead.")
        print(df_styler.data)
