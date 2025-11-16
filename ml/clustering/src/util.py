import pandas as pd
import numpy as np 
import pickle
from typing import Any, Dict, List
from statsmodels.stats.outliers_influence import variance_inflation_factor
# from statsmodels.tools.sm_utils import dmatrices  # (참고) dmatrices를 사용하면 더 안정적일 수 있음



def load_data(path: str) -> pd.DataFrame:
    """
    지정된 경로에서 데이터를 로드합니다. 파일 확장자에 따라 다른 라이브러리를 사용합니다.
    
    :param path: 데이터 파일의 경로 (e.g., 'data.csv', 'data.pkl')
    :return: 로드된 pandas DataFrame
    """
    print(f"Attempting to load data from {path}...")
    if path.endswith('.csv'):
        return pd.read_csv(path)
    elif path.endswith('.pkl'):
        with open(path, 'rb') as f:
            return pickle.load(f)
    else:
        raise ValueError(f"Unsupported file format: {path}")

def save_data(df: pd.DataFrame, path: str) -> None:
    """
    DataFrame을 지정된 경로에 저장합니다.
    
    :param df: 저장할 pandas DataFrame
    :param path: 저장할 파일 경로
    """
    print(f"Attempting to save data to {path}...")
    if path.endswith('.csv'):
        df.to_csv(path, index=False)
    elif path.endswith('.pkl'):
        with open(path, 'wb') as f:
            pickle.dump(df, f)
    else:
        raise ValueError(f"Unsupported file format: {path}")
    print(f"Data successfully saved to {path}")

def load_model(path: str) -> Any:
    """
    지정된 경로에서 직렬화된 모델(.pkl)을 로드합니다.
    
    :param path: 모델 파일 경로
    :return: 로드된 모델 객체
    """
    print(f"Attempting to load model from {path}...")
    with open(path, 'rb') as f:
        model = pickle.load(f)
    print(f"Model successfully loaded from {path}")
    return model

def save_model(model: Any, path: str) -> None:
    """
    모델 객체를 지정된 경로에 .pkl 파일로 저장합니다.
    
    :param model: 저장할 모델 객체
    :param path: 저장할 파일 경로
    """
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model successfully saved to {path}")




# 수치형 변수 간 상관관계
 
def find_highly_correlated_features(df_numeric, threshold=0.9, verbose=True):
    """
    수치형 데이터프레임에서 높은 상관관계(절대값 기준)를 가진 피처를 식별합니다.

    상관관계 행렬의 상삼각행렬(upper triangle)만 검사하여 중복을 피하고,
    임계값(threshold)을 초과하는 상관관계를 가진 컬럼의 리스트를 반환합니다.

    Parameters
    ----------
    df_numeric : pd.DataFrame
        수치형 변수로만 구성된 입력 데이터프레임.
    threshold : float, optional
        삭제 대상으로 간주할 상관관계 임계값. (기본값: 0.9)
    verbose : bool, optional
        True일 경우, 원본 컬럼 수와 삭제 대상 컬럼 리스트를 출력합니다. (기본값: True)

    Returns
    -------
    list
        임계값을 초과하는 상관관계를 가진 컬럼 이름들의 리스트.
        (상관관계가 높은 쌍 중 '뒤쪽' 컬럼이 리스트에 포함됩니다.)
    """
    
    # 1. 상관관계 행렬 계산 (절대값)
    corr_matrix = df_numeric.corr().abs()

    # 2. 상삼각행렬 마스크 생성 (k=1로 대각선 제외)
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

    # 3. 임계값을 초과하는 컬럼 식별
    # any(upper_tri[column] > threshold) : 
    #   각 컬럼(세로)을 기준으로 임계값을 넘는 값이 '하나라도' 있으면 True
    to_drop = [column for column in upper_tri.columns if any(upper_tri[column] > threshold)]

    # 4. (선택적) 결과 출력
    if verbose:
        print(f"--- 상관관계 높은 피처 탐색 ---")
        print(f"원본 컬럼 개수: {df_numeric.shape[1]}")
        print(f"상관관계 임계값: {threshold}")
        print(f"삭제 대상 컬럼 ({len(to_drop)}개):")
        print(to_drop)
        print("-" * 30)

    return to_drop






# 분산 팽창 지수 
def find_high_vif_features(df_numeric, threshold=5, verbose=True):
    """
    수치형 데이터프레임의 모든 피처에 대해 VIF(분산 팽창 지수)를 계산합니다.
    
    VIF는 다중공선성(Multicollinearity)의 심각성을 측정하는 지표입니다.
    VIF가 5 또는 10을 초과하는 피처는 다른 피처에 의해 강하게 설명되므로
    모델에서 제외하는 것을 고려할 수 있습니다.

    Parameters
    ----------
    df_numeric : pd.DataFrame
        수치형 변수로만 구성된 입력 데이터프레임.
        (주의: 내부에 결측치(NaN)가 없어야 합니다. VIF 계산 시 오류 발생)
    threshold : float or int, optional
        제거 대상으로 간주할 VIF 임계값. (기본값: 5)
    verbose : bool, optional
        True일 경우, 각 피처의 VIF 값을 출력하고 제거 대상 목록을 요약합니다.
        (기본값: True)

    Returns
    -------
    list
        VIF가 임계값(threshold)을 초과하는 컬럼 이름들의 리스트.
    """
    
    if df_numeric.isnull().any().any():
        print("!! 경고: 데이터에 결측치가 포함되어 있습니다.")
        print("VIF 계산 전에 .fillna() 등으로 결측치를 처리해야 합니다.")
        # 결측치가 있으면 정상 작동 불가 -> 결측치를 평균으로 임시 대체하고 경고
        df_numeric = df_numeric.fillna(df_numeric.mean())
        print("임시로 결측치를 평균값으로 대체하여 VIF를 계산합니다.")

    vif_data = []
    values = df_numeric.values
    columns = df_numeric.columns
    
    if verbose:
        print("--- VIF (분산 팽창 지수) 계산 ---")
        print(f"VIF 임계값: {threshold}")
        print("-" * 30)

    for i, col in enumerate(columns):
        try:
            vif_value = variance_inflation_factor(values, i)
        except Exception as e:
            # 오류(inf)
            # - 완벽한 선형 관계(e.g., A = B * 2)
            # - 상수로만 이루어진 컬럼
            vif_value = np.inf
            
        vif_data.append((col, vif_value))
        
        if verbose:
            print(f"{col:<30}  VIF = {vif_value:.3f}")

    # VIF가 임계값을 초과하는 컬럼 리스트 필터링
    to_drop = [col for col, vif in vif_data if vif > threshold]
    
    if verbose:
        print("-" * 30)
        print(f"제거 대상 컬럼 ({len(to_drop)}개):")
        print(to_drop)
        print("--- VIF 계산 완료 ---")

    return to_drop