import pandas as pd
# kpi-dashboard.py에서 데이터 로딩 함수를 임포트
from .kpi_dashboard import load_cleansed_data

def calc_kpi1(df: pd.DataFrame) -> int:
    """전체 평균 신용등급을 계산합니다."""
    # 신용등급 0은 등급이 부여되지 않은 기업으로 계산에서 제외
    kpi1 = pd.to_numeric(df['CORP_GRAD'])
    kpi1 = kpi1[kpi1 != 0].mean()
    return kpi1

def calc_kpi2(df):
    """고위험군, 우량주 기업수를 계산합니다"""
    good = df[pd.to_numeric(df['CORP_GRAD']).isin([1, 2, 3])].shape[0]
    bad = df[pd.to_numeric(df['CORP_GRAD']).isin([8, 9, 10])].shape[0]
    return good, bad

def calc_kpi3(df):
    """유효기업수를 계산합니다."""
    return df.shape[0]

def calculate_portfolio_hhi_components(df: pd.DataFrame) -> pd.DataFrame:
    """
    HHI 계산에 필요한 업종별 구성요소 데이터프레임을 생성합니다.
    이 함수는 vis6.py에서도 재사용됩니다.
    """
    industry_mid_col = 'SIC_CD_3'
    value_col = 'FN1_16'  # '차입금'을 기준으로 HHI 계산

    try:
        df_hhi = df[[industry_mid_col, value_col]].copy()
    except KeyError:
        print(f"오류: DataFrame에 '{industry_mid_col}' 또는 '{value_col}' 컬럼이 없습니다.")
        return None

    df_hhi[value_col] = pd.to_numeric(df_hhi[value_col], errors='coerce').fillna(0)
    df_hhi[value_col] = df_hhi[value_col].apply(lambda x: x if x > 0 else 0)

    COL_INDUSTRY_LARGE = 'SIC_CD_1'
    df_hhi[COL_INDUSTRY_LARGE] = df_hhi[industry_mid_col].astype(str).str[0]

    industry_exposure = df_hhi.groupby(COL_INDUSTRY_LARGE)[value_col].sum()
    
    return industry_exposure.reset_index()


def calc_kpi4(df: pd.DataFrame) -> float:
    """
    위험 분산도 지수(HHI)를 '차입금' 기준으로 계산합니다.
    HHI는 0에 가까울수록 분산이 잘 되어 있고, 10,000에 가까울수록 집중도가 높음을 의미합니다.
    """
    # HHI 계산에 필요한 구성 요소들을 가져옴
    industry_summary_df = calculate_portfolio_hhi_components(df)
    if industry_summary_df is None:
        return None

    value_col = 'FN1_16'
    total_exposure = industry_summary_df[value_col].sum()

    if total_exposure == 0:
        print("경고: 전체 포트폴리오 규모가 0입니다.")
        return 0

    share_percent = (industry_summary_df[value_col] / total_exposure) * 100
    hhi = (share_percent ** 2).sum()
    
    return hhi


def cal_all_kpis(df: pd.DataFrame) -> dict:
    """
    정의된 모든 KPI를 계산하고 딕셔너리 형태로 반환합니다.
    웹 API 등에서 이 함수를 호출하여 KPI 데이터를 가져갈 수 있습니다.
    
    :param df: 정제된 데이터프레임
    :return: KPI 이름과 계산된 값을 담은 딕셔너리
    """
    kpi2_results = calc_kpi2(df) # (good_companies, bad_companies) 튜플이 반환됨
    
    kpis = {
        "average_credit_grade": calc_kpi1(df),
        "company_risk_counts": {
            "good_companies": kpi2_results[0],
            "bad_companies": kpi2_results[1],
        },
        "total_companies": calc_kpi3(df),
        "hhi_index": calc_kpi4(df),
    }
    return kpis


def main():
    """
    데이터를 로드하고, 모든 KPI를 계산한 후, 콘솔에 결과를 출력합니다.
    이 함수는 스크립트를 직접 실행할 때 사용하기 위한 것입니다.
    """
    print("--- KPI 대시보드 데이터 계산 시작 ---")
    
    # 1. 데이터 로딩
    df_cleansed = load_cleansed_data()
    if df_cleansed is None:
        print("✗ 데이터 로딩 실패. KPI 계산을 중단합니다.")
        return
        
    df_cleansed['SIC_CD_1'] = df_cleansed['SIC_CD_3'].apply(
        lambda x: 'Other' if pd.isna(x) or str(x).lower() == 'nan' or str(x)[0] in ['K', 'O', 'T'] else str(x)[0])
    df_snapshot = df_cleansed[df_cleansed['BS_DT']=="2021-08-01"].copy()

    if df_snapshot.empty:
        print("✗ 해당 날짜(2021-08-01)의 데이터가 없습니다. KPI 계산을 중단합니다.")
        return

    print("✓ 데이터 로딩 및 전처리 성공.")
    
    # 2. KPI 계산 (스냅샷 기준으로 계산)
    kpi_results = cal_all_kpis(df_snapshot)

    # 3. 결과 출력
    print(f"\\n--- KPI 요약 (기준일: 2021-08-01) ---")
    print(f"총 기업 수: {kpi_results.get('total_companies', 'N/A'):,} 개")
    print(f"평균 신용 등급: {kpi_results.get('average_credit_grade', 0.0):.2f} 등급")
    print(f"우량 기업 수 (1-3등급): {kpi_results.get('company_risk_counts', {}).get('good_companies', 'N/A'):,} 개")
    print(f"부실 기업 수 (8-10등급): {kpi_results.get('company_risk_counts', {}).get('bad_companies', 'N/A'):,} 개")
    print(f"산업별 분산도 (HHI): {kpi_results.get('hhi_index', 0.0):.2f}")


if __name__ == '__main__':
    main()
