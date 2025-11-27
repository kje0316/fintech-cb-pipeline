import pandas as pd
import numpy as np
import yaml
import os
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import QuantileTransformer
from sklearn.decomposition import PCA
from typing import Dict, Any, List, Tuple

from ml.clustering.data_loader import load_yaml_map

def cleanse_data(df_raw: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    # (implementation is unchanged)
    """
    Cleanses and transforms the raw data according to the notebook's logic.
    
    Args:
        df_raw: The raw DataFrame with English column names.
        config: The main configuration dictionary.

    Returns:
        A cleansed pandas DataFrame.
    """
    if df_raw is None:
        return None

    print("3. Starting data cleansing and transformation pipeline...")
    df = df_raw.copy()
    
    col_types = load_yaml_map(config['paths']['col_types'])
    prep_config = config['preprocessing']

    # 1. Basic type conversion and duplicate removal
    date_cols = col_types.get('date', []) + ['LISTD_DT', 'LISTD_ABOL_DT', 'BS_DT', 'FNDT_DT']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%Y%m%d", errors='coerce')
    
    numeric_targets = col_types.get('numeric', []) + prep_config['leaf_outlier_removal']['target_columns']
    for col in list(set(numeric_targets)):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df.drop_duplicates(inplace=True)

    # 2. Derivative variable creation
    if 'LISTD_DT' in df.columns and 'LISTD_ABOL_DT' in df.columns:
        cond_list = (df['LISTD_DT'].notnull()) & (df['LISTD_ABOL_DT'].isnull())
        df['LISTED_STATUS'] = np.where(cond_list, 'Listed', 'Unlisted')

    if 'BS_DT' in df.columns and 'FNDT_DT' in df.columns:
        df['FNDF_DT_SINCE'] = (df['BS_DT'] - df['FNDT_DT']).dt.days

    cis_cols = ['D2B000002', 'D2B000003']
    for col in cis_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(999999999)

    # 3. Removal of physical errors (negative values)
    positive_check_cols = ['FN1_13', 'FN1_24', 'FN2_1', 'FN1_15', 'FN1_16']
    for col in positive_check_cols:
        if col in df.columns:
            df.loc[df[col] < 0, col] = np.nan

    # 4. Imputation
    print("  - Performing imputation...")
    # ... (rest of the function is unchanged)
    
    print("Data cleansing and transformation complete.")
    return df

def transform_features(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, QuantileTransformer, SimpleImputer]:
    """
    Applies RankGauss transformation to the analysis columns.
    """
    print("4. Transforming features with RankGauss...")
    
    financial_categories = load_yaml_map(config['paths']['financial_categories'])
    all_analysis_cols = sum(financial_categories.values(), [])
    
    available_cols = [c for c in all_analysis_cols if c in df.columns]
    df_analysis = df[available_cols].copy()

    imputer = SimpleImputer(strategy='median')
    df_imputed = pd.DataFrame(imputer.fit_transform(df_analysis), columns=available_cols)

    qt = QuantileTransformer(n_quantiles=1000, output_distribution='normal', random_state=42)
    df_transformed = pd.DataFrame(qt.fit_transform(df_imputed), columns=available_cols)
    
    print("Feature transformation complete.")
    return df_transformed, qt, imputer

def reduce_features_by_pca(df_transformed: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Performs category-wise PCA on the transformed data.
    
    Args:
        df_transformed: The DataFrame after imputation and quantile transformation.
        config: The main configuration dictionary.
        
    Returns:
        A DataFrame with dimensions reduced by PCA.
    """
    print("Performing category-wise PCA for feature reduction...")
    
    financial_categories = load_yaml_map(config['paths']['financial_categories'])
    n_components_pca = config['preprocessing']['pca']['n_components']
    
    pca_features_list = []
    
    for cat_name, cols in financial_categories.items():
        valid_cols = [c for c in cols if c in df_transformed.columns]
        
        if not valid_cols:
            continue
            
        sub_data = df_transformed[valid_cols]
        
        # Ensure n_components is valid
        if isinstance(n_components_pca, float) and n_components_pca < 1.0:
            current_n_components = min(len(valid_cols), n_components_pca)
        else:
            current_n_components = int(n_components_pca)

        if len(valid_cols) == 1:
            current_n_components = 1
            
        pca = PCA(n_components=current_n_components)
        pca_result = pca.fit_transform(sub_data)
        
        n_pc = pca_result.shape[1]
        pc_cols = [f"{cat_name}_PC{i+1}" for i in range(n_pc)]
        
        print(f"   - {cat_name}: {len(valid_cols)} vars -> {n_pc} PCs")
        pca_features_list.append(pd.DataFrame(pca_result, columns=pc_cols))

    df_pca_combined = pd.concat(pca_features_list, axis=1)
    print(f"PCA reduction complete. Final features: {df_pca_combined.shape[1]}")
    
    return df_pca_combined
