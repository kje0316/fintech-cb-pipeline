
import pandas as pd
import plotly.graph_objects as go
from .kpi_dashboard import load_cleansed_data

def prepare_data_for_vis1(df: pd.DataFrame) -> dict:
    """
    월별 전체/업종별 부도율 및 Top 5 업종을 계산하여 시각화에 필요한 데이터를 준비합니다.
    """
    # 1. 데이터 전처리
    COL_TIME = 'BS_DT'
    COL_INDUSTRY = 'SIC_CD_1'
    COL_DEFAULT = 'PERF_12M'

    df_vis = df[[COL_TIME, COL_INDUSTRY, COL_DEFAULT]].copy()
    # load_cleansed_data에서 이미 datetime으로 변환되었으므로 추가 변환 불필요
    df_vis[COL_DEFAULT] = pd.to_numeric(df_vis[COL_DEFAULT], errors='coerce')
    df_vis.dropna(subset=[COL_TIME, COL_INDUSTRY, COL_DEFAULT], inplace=True)

    # 2. 부도율 집계
    # 2.1. 전체 월별 부도율
    df_monthly_total = df_vis.groupby(COL_TIME)[COL_DEFAULT].mean().reset_index()
    df_monthly_total.rename(columns={COL_DEFAULT: '부도율'}, inplace=True)

    # 2.2. 월별 업종별 부도율
    df_monthly_industry = df_vis.groupby([COL_TIME, COL_INDUSTRY])[COL_DEFAULT].mean().reset_index()
    df_monthly_industry.rename(columns={COL_DEFAULT: '부도율'}, inplace=True)

    # 3. Top 5 업종 선정
    avg_default_rates = df_monthly_industry.groupby(COL_INDUSTRY)['부도율'].mean()
    top_5_industries = avg_default_rates.nlargest(5).index.tolist()

    print("--- 데이터 준비 완료 ---")
    print(f"Top 5 업종: {top_5_industries}")

    return {
        "monthly_total": df_monthly_total,
        "monthly_industry": df_monthly_industry,
        "top_5": top_5_industries
    }

def create_vis1_figure(data_dict: dict) -> go.Figure:
    """
    준비된 부도율 데이터를 사용하여 드롭다운이 포함된 시계열 차트를 생성합니다.
    """
    # 데이터 언패킹
    df_monthly_total = data_dict["monthly_total"]
    df_monthly_industry = data_dict["monthly_industry"]
    top_5_industries = data_dict["top_5"]
    
    COL_TIME = 'BS_DT'
    COL_INDUSTRY = 'SIC_CD_1'

    # 스타일 정의
    HIGHLIGHT_COLOR = '#E06666'
    HIGHLIGHT_WIDTH = 2.5
    HIGHLIGHT_DASH = 'solid'
    FADED_COLOR = 'lightgray'
    FADED_WIDTH = 1.5
    FADED_DASH = 'dot'

    # 빈 Figure 생성
    fig = go.Figure()

    # 전체 부도율 선 추가
    fig.add_trace(go.Scatter(
        x=df_monthly_total[COL_TIME],
        y=df_monthly_total['부도율'],
        mode='lines',
        name='전체 부도율',
        line=dict(color='#6FA8DC', width=2)
    ))

    # Top 5 업종 부도율 선 추가
    for i, industry in enumerate(top_5_industries):
        industry_data = df_monthly_industry[df_monthly_industry[COL_INDUSTRY] == industry]
        is_highlighted = (i == 0)
        fig.add_trace(go.Scatter(
            x=industry_data[COL_TIME],
            y=industry_data['부도율'],
            mode='lines',
            name=str(industry),
            line=dict(
                color=HIGHLIGHT_COLOR if is_highlighted else FADED_COLOR,
                width=HIGHLIGHT_WIDTH if is_highlighted else FADED_WIDTH,
                dash=HIGHLIGHT_DASH if is_highlighted else FADED_DASH
            )
        ))

    # 드롭다운 버튼 생성
    buttons = []
    num_industries = len(top_5_industries)
    industry_trace_indices = list(range(1, num_industries + 1))

    for i, industry_name in enumerate(top_5_industries):
        colors = [FADED_COLOR] * num_industries
        widths = [FADED_WIDTH] * num_industries
        dashes = [FADED_DASH] * num_industries
        
        colors[i] = HIGHLIGHT_COLOR
        widths[i] = HIGHLIGHT_WIDTH
        dashes[i] = HIGHLIGHT_DASH
        
        buttons.append(dict(
            method='restyle',
            label=str(industry_name),
            args=[
                {'line.color': colors, 'line.width': widths, 'line.dash': dashes},
                industry_trace_indices
            ]
        ))

    # 레이아웃 업데이트
    fig.update_layout(
        # title=f"<b>업종별(Top 5) 및 전체 부도율 추이</b><br>(초기 선택: {top_5_industries[0]})",
        xaxis_title='기준년월',
        yaxis_title='월별 부도율',
        yaxis_tickformat='.1%',
        hovermode="x unified",
        template='plotly_white',
        # legend_title_text='범례',
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.15,
                yanchor="top"
            )
        ],
        title_y=0.9,
        title_x=0.5,
        title_font_size=16
    )

    return fig


def main():
    """
    데이터를 로드하고, 시각화 1을 생성하여 화면에 출력합니다.
    이 함수는 스크립트를 직접 실행할 때 사용하기 위한 것입니다.
    """
    print("--- 시각화 1: 데이터 로딩 및 생성 시작 ---")
    
    # 1. 데이터 로딩 및 전처리; 나중에 api를 통한 연결로 변경 
    df = load_cleansed_data()
    if df is None:
        print("✗ 데이터 로딩 실패. 시각화를 중단합니다.")
        return
    
    df_cleansed = df.copy()
    df_cleansed['SIC_CD_1'] = df_cleansed['SIC_CD_3'].apply(
        lambda x: 'Other' if pd.isna(x) or str(x).lower() == 'nan' or str(x)[0] in ['K', 'O', 'T'] else str(x)[0])
    
    # 시각화에는 전체 기간 데이터 사용 (df_snapshot 대신 df_cleansed)
    print("✓ 데이터 로딩 및 전처리 성공.")

    # 2. 시각화에 필요한 데이터 준비
    vis1_data = prepare_data_for_vis1(df_cleansed)
    
    # 3. Plotly Figure 생성
    if vis1_data:
        fig = create_vis1_figure(vis1_data)
        
        # 4. 차트 출력 (스크립트 직접 실행 시)
        print("✓ 차트 생성 완료. 브라우저에 차트를 표시합니다.")
        fig.show()
    else:
        print("✗ 시각화 데이터 준비 실패.")


if __name__ == '__main__':
    main()