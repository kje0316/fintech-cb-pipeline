
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .kpi_dashboard import load_cleansed_data

def prepare_data_for_vis4(df: pd.DataFrame) -> dict:
    """
    특정 날짜 기준, 업종(대분류)별 평균 부도율 및 전체 평균 부도율 데이터를 준비합니다.
    """

    # 1. 설정 및 데이터 전처리
    COL_INDUSTRY = 'SIC_CD_1'
    COL_DEFAULT = 'PERF_12M'

    df_vis = df.copy()
    df_vis[COL_DEFAULT] = pd.to_numeric(df_vis[COL_DEFAULT], errors='coerce')
    df_vis.dropna(subset=[COL_INDUSTRY, COL_DEFAULT], inplace=True)

    # 2. 업종별 평균 부도율 집계
    df_industry_default = df_vis.groupby(COL_INDUSTRY)[COL_DEFAULT].mean().reset_index()
    df_industry_default.rename(columns={COL_DEFAULT: '부도율'}, inplace=True)
    
    # 3. x축 순서 정렬 ('Other'를 마지막으로)
    categories = df_industry_default[COL_INDUSTRY].unique().tolist()
    if 'Other' in categories:
        categories.remove('Other')
        category_order = sorted(categories) + ['Other']
    else:
        category_order = sorted(categories)

    # 4. 전체 평균 부도율 계산
    overall_avg_default = df_vis[COL_DEFAULT].mean()
    print(f"--- 전체 평균 부도율 계산 완료: {overall_avg_default:.2%} ---")
    print("--- 데이터 준비 완료 ---")
    return {
        "industry_default": df_industry_default,
        "overall_avg_default": overall_avg_default,
        "category_order": category_order
    }


def create_vis4_figure(data_dict: dict, target_date: pd.Timestamp) -> go.Figure:
    """
    준비된 데이터를 사용하여 업종별 평균 부도율 막대 그래프를 생성합니다.
    """
    # 데이터 언패킹
    data_df = data_dict["industry_default"]
    overall_avg_default = data_dict["overall_avg_default"]
    category_order = data_dict["category_order"]

    COL_INDUSTRY = 'SIC_CD_1'

    fig = px.bar(
        data_df,
        x=COL_INDUSTRY,
        y='부도율',
        text='부도율',
        # title=f"<b>업종(대분류)별 평균 부도율 ({target_date.strftime('%Y-%m-%d')} 기준)</b>"
    )

    # 전체 평균 참조선 추가
    fig.add_hline(
        y=overall_avg_default,
        line_dash="dash",
        line_color="#003173",
        annotation_text=f"전체 평균({overall_avg_default:.2%})",
        annotation_position="bottom right"
    )


    # 레이아웃 및 스타일 업데이트
    fig.update_layout(
        xaxis_title='업종(대분류)',
        yaxis_title='평균 부도율',
        yaxis_tickformat='.2%',
        template='plotly_white',
        showlegend=False,
        title_x=0.5,
        # x축 순서 지정
        xaxis=dict(
            categoryorder='array',
            categoryarray=category_order
        )
    )

    fig.update_traces(
        marker_color='skyblue',
        texttemplate='%{y:.2%}',
        textposition='outside'
    )
    return fig





def main():
    """
    데이터를 로드하고, 시각화 4를 생성하여 화면에 출력합니다.
    """
    print("--- 시각화 4: 데이터 로딩 및 생성 시작 ---")

    # 1. 데이터 로딩 및 전처리
    df = load_cleansed_data()
    if df is None:
        print("✗ 데이터 로딩 실패. 시각화를 중단합니다.")
        return

    target_date = pd.to_datetime('2021-08-01')
    df_cleansed = df.copy()
    # 'Other' 카테고리 생성
    df_cleansed['SIC_CD_1'] = df_cleansed['SIC_CD_3'].apply(
        lambda x: 'Other' if pd.isna(x) or str(x).lower() == 'nan' or str(x)[0] in ['K', 'O', 'T'] else str(x)[0])

    df_snapshot = df_cleansed[df_cleansed['BS_DT'] == target_date].copy()

    if df_snapshot.empty:
        print(f"✗ 해당 날짜({target_date.date()})의 데이터가 없습니다. 시각화를 중단합니다.")
        return
    
    print("✓ 데이터 로딩 및 전처리 성공.")
    # 2. 시각화에 필요한 데이터 준비
    vis4_data = prepare_data_for_vis4(df_snapshot)
    

    # 3. Plotly Figure 생성
    if vis4_data:
        fig = create_vis4_figure(vis4_data, target_date)
        # 4. 차트 출력 (스크립트 직접 실행 시)
        print("✓ 차트 생성 완료. 브라우저에 차트를 표시합니다.")
        fig.show()
    else:
        print("✗ 시각화 데이터 준비 실패.")





if __name__ == '__main__':

    main()