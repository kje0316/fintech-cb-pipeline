
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .kpi_dashboard import load_cleansed_data

def prepare_data_for_vis2(df: pd.DataFrame) -> dict:
    """
    업종별 위험-수익성 포트폴리오 분석에 필요한 데이터를 준비합니다.
    """
    # 0. 컬럼명 정의 (실제 영문 컬럼명)
    COL_INDUSTRY = 'SIC_CD_1'
    COL_RISK = 'R006'       # 부채비율
    COL_PROFIT = 'R015'     # 영업이익율
    COL_SIZE = 'FN2_1'      # 매출액

    # 1. 필요한 컬럼만 선택하고 결측치 처리
    cols_to_use = [COL_INDUSTRY, COL_RISK, COL_PROFIT, COL_SIZE]
    df_vis = df[cols_to_use].copy()
    df_vis.dropna(inplace=True)

    # 2. 업종별 데이터 집계
    # X축 (위험): 부채비율의 '중앙값'
    # Y축 (수익성): 영업이익율의 '중앙값'
    # 버블크기 (규모): 매출액의 '총합'
    industry_df = df_vis.groupby(COL_INDUSTRY).agg(
        risk=(COL_RISK, 'median'),
        profit=(COL_PROFIT, 'median'),
        size=(COL_SIZE, 'sum')
    ).reset_index()

    # 3. 4분면 기준선 계산 (시장 전체의 중앙값)
    median_risk = industry_df['risk'].median()
    median_profit = industry_df['profit'].median()
    
    print("--- 데이터 준비 완료 ---")
    return {
        "industry_df": industry_df,
        "median_risk": median_risk,
        "median_profit": median_profit
    }

def create_vis2_figure(data_dict: dict) -> go.Figure:
    """
    준비된 데이터를 사용하여 업종별 위험-수익성 포트폴리오 버블 차트를 생성합니다.
    """
    # 데이터 언패킹
    industry_df = data_dict["industry_df"]
    median_risk = data_dict["median_risk"]
    median_profit = data_dict["median_profit"]
    
    COL_INDUSTRY = 'SIC_CD_1'

    # 1. 버블 차트 생성
    fig = px.scatter(
        industry_df,
        x='risk',
        y='profit',
        size='size',
        color=COL_INDUSTRY,
        hover_name=COL_INDUSTRY,
        text=COL_INDUSTRY,
        size_max=60,
        # title='<b>업종별 위험-수익성 포트폴리오</b>',
        labels={
            "risk": "<b>재무 위험 (업종별 부채비율 중앙값) </b>",
            "profit": "<b>수익성 (업종별 영업이익율 중앙값) </b>",
            "size": "시장 규모 (매출액 총합)"
        },
        template='plotly_white'
    )

    # 2. 4분면 참조선 및 레이블 추가
    fig.add_hline(y=median_profit, line_dash="dash", line_color="gray", 
                  annotation_text=f"수익성 중앙값({median_profit:.1f}%)", 
                  annotation_position="bottom right")
    fig.add_vline(x=median_risk, line_dash="dash", line_color="gray",
                  annotation_text=f"위험 중앙값({median_risk:.1f}%)", 
                  annotation_position="top left")

    # 3. 4분면 설명 추가
    max_x = industry_df['risk'].max() * 1.05
    max_y = industry_df['profit'].max() * 1.05
    min_x = industry_df['risk'].min() * 0.95
    min_y = industry_df['profit'].min() * 0.95

    # fig.add_annotation(text="<b>⭐ 저위험-고수익</b><br>(알짜 업종)", x=min_x, y=max_y, showarrow=False, xanchor='left', yanchor='top', font=dict(color="green", size=12))
    # fig.add_annotation(text="<b>고위험-고수익</b><br>(성장 주도 업종)", x=max_x, y=max_y, showarrow=False, xanchor='right', yanchor='top', font=dict(color="blue", size=12))
    # fig.add_annotation(text="<b>⚠️ 고위험-저수익</b><br>(한계/위험 업종)", x=max_x, y=min_y, showarrow=False, xanchor='right', yanchor='bottom', font=dict(color="red", size=12))
    # fig.add_annotation(text="<b>저위험-저수익</b><br>(성숙/안정 업종)", x=min_x, y=min_y, showarrow=False, xanchor='left', yanchor='bottom', font=dict(color="orange", size=12))

    # 4. 레이아웃 최종 업데이트
    x_padding = (industry_df['risk'].max() - industry_df['risk'].min()) * 0.1
    y_padding = (industry_df['profit'].max() - industry_df['profit'].min()) * 0.1
    
    fig.update_layout(
        title_font_size=20,
        title_x=0.5,
        xaxis=dict(gridcolor='lightgray', range=[industry_df['risk'].min() - x_padding, industry_df['risk'].max() + x_padding]),
        yaxis=dict(gridcolor='lightgray', range=[industry_df['profit'].min() - y_padding, industry_df['profit'].max() + y_padding]),
        showlegend=False
    )
    fig.update_traces(textposition='top center')

    return fig


def main():
    """
    데이터를 로드하고, 시각화 2를 생성하여 화면에 출력합니다.
    """
    print("--- 시각화 2: 데이터 로딩 및 생성 시작 ---")
    
    # 1. 데이터 로딩 및 전처리
    df = load_cleansed_data()
    if df is None:
        print("✗ 데이터 로딩 실패. 시각화를 중단합니다.")
        return
    
    df_cleansed = df.copy()
        
    df_cleansed['SIC_CD_1'] = df_cleansed['SIC_CD_3'].apply(
        lambda x: 'Other' if pd.isna(x) or str(x).lower() == 'nan' or str(x)[0] in ['K', 'O', 'T'] else str(x)[0])
    df_snapshot = df_cleansed[df_cleansed['BS_DT']=="2021-08-01"].copy()

    if df_snapshot.empty:
        print("✗ 해당 날짜(2021-08-01)의 데이터가 없습니다. 시각화를 중단합니다.")
        return

    print("✓ 데이터 로딩 및 전처리 성공.")

    # 2. 시각화에 필요한 데이터 준비
    vis2_data = prepare_data_for_vis2(df_snapshot)
    
    # 3. Plotly Figure 생성
    if vis2_data:
        fig = create_vis2_figure(vis2_data)
        
        # 4. 차트 출력 (스크립트 직접 실행 시)
        print("✓ 차트 생성 완료. 브라우저에 차트를 표시합니다.")
        fig.show()
    else:
        print("✗ 시각화 데이터 준비 실패.")


if __name__ == '__main__':
    main()

