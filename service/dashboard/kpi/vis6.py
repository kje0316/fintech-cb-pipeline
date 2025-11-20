
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from .kpi_dashboard import load_cleansed_data
from .kpi import calculate_portfolio_hhi_components # kpi.py에서 HHI 구성요소 계산 함수 임포트

def prepare_data_for_vis6(df: pd.DataFrame) -> pd.DataFrame:
    """
    HHI 구성요소(업종별 집계) 데이터를 준비합니다.
    kpi.py의 함수를 재사용하여 코드 중복을 방지합니다.
    """
    print("--- HHI 구성요소 데이터 계산 시작 ---")
    industry_summary_df = calculate_portfolio_hhi_components(df)
    print("✓ HHI 구성요소 데이터 계산 완료")
    return industry_summary_df

def create_vis6_figure(industry_summary_df: pd.DataFrame) -> go.Figure:
    """
    준비된 HHI 구성요소 데이터를 사용하여 트리맵을 생성합니다.
    """
    if industry_summary_df is None or industry_summary_df.empty:
        print("⚠️ HHI 구성요소 데이터가 없어 트리맵을 생성할 수 없습니다.")
        return go.Figure()

    def format_number_korean(x):
        """숫자를 소수점 없는 한글 단위로 변환합니다."""
        x = int(x)
        if x >= 1_0000_0000_0000_0000: return f"{x/1_0000_0000_0000_0000:.0f}경"
        elif x >= 1_0000_0000_0000: return f"{x/1_0000_0000_0000:.0f}조"
        elif x >= 1_0000_0000: return f"{x/1_0000_0000:.0f}억"
        elif x >= 1_0000: return f"{x/1_0000:.0f}만"
        elif x >= 1_000: return f"{x/1_000:.0f}천"
        else: return str(x)

    COL_INDUSTRY_LARGE = 'SIC_CD_1'
    COL_VALUE_TO_USE = 'FN1_16'
    color_scale_reds = ["#fde8e7", "#f5968c", "#e67c73", "#c00000"]

    fig = px.treemap(
        industry_summary_df,
        path=[COL_INDUSTRY_LARGE],
        values=COL_VALUE_TO_USE,
        color=COL_VALUE_TO_USE,
        color_continuous_scale=color_scale_reds,
        # title="<b>업종별 위험 기여도 (HHI 구성요소)</b>"
    )

    fig.update_traces(
        texttemplate="%{label}<br>%{customdata[0]}<br><b>%{percentRoot:.1%}</b>",
        textfont=dict(size=14),
        customdata=industry_summary_df[COL_VALUE_TO_USE].map(format_number_korean).to_frame().values,
        hovertemplate=(
            "<b>%{label}</b><br>" + 
            "합산값: %{value:,d}<br>" +
            "<b>비중: %{percentRoot:.1%}</b>" +
            "<extra></extra>"
        ),
        root_color="#f0f0f0"
    )

    max_val = industry_summary_df[COL_VALUE_TO_USE].max()
    max_val_rounded = np.ceil(max_val / 1e11) * 1e11
    tickvals = np.linspace(0, max_val_rounded, 5)
    ticktext = [format_number_korean(x) for x in tickvals]
    
    fig.update_layout(
        margin=dict(t=50, l=10, r=10, b=10),
        paper_bgcolor='white',
        plot_bgcolor='white',
        coloraxis_colorbar=dict(title="차입금", tickvals=tickvals, ticktext=ticktext),
        title_x=0.5
    )
    
    return fig


def main():
    """
    데이터를 로드하고, 시각화 6을 생성하여 화면에 출력합니다.
    """
    print("--- 시각화 6: 데이터 로딩 및 생성 시작 ---")
    
    # 1. 데이터 로딩 및 전처리
    df = load_cleansed_data()
    if df is None:
        print("✗ 데이터 로딩 실패. 시각화를 중단합니다.")
        return
    df_cleansed = df.copy()
    df_cleansed['SIC_CD_1'] = df_cleansed['SIC_CD_3'].apply(
        lambda x: 'Other' if pd.isna(x) or str(x).lower() == 'nan' or str(x)[0] in ['K', 'O', 'T'] else str(x)[0])

    target_date = pd.to_datetime('2021-08-01')
    df_snapshot = df_cleansed[df_cleansed['BS_DT'] == target_date].copy()

    if df_snapshot.empty:
        print(f"✗ 해당 날짜({target_date.date()})의 데이터가 없습니다. 시각화를 중단합니다.")
        return

    print("✓ 데이터 로딩 및 전처리 성공.")

    # 2. 시각화에 필요한 데이터 준비
    vis6_data = prepare_data_for_vis6(df_snapshot)
    
    # 3. Plotly Figure 생성
    if vis6_data is not None:
        fig = create_vis6_figure(vis6_data)
        
        # 4. 차트 출력 (스크립트 직접 실행 시)
        print("✓ 차트 생성 완료. 브라우저에 차트를 표시합니다.")
        fig.show()
    else:
        print("✗ 시각화 데이터 준비 실패.")


if __name__ == '__main__':
    main()