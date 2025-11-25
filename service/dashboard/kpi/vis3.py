
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from .kpi_dashboard import load_cleansed_data

def prepare_data_for_vis3(df: pd.DataFrame) -> pd.DataFrame:
    """
    월별/업종별 부도율 히트맵을 그리는 데 필요한 피벗 데이터를 준비합니다.
    """
    # 1. 설정 및 데이터 전처리
    COL_TIME = 'BS_DT'
    COL_MID_INDUSTRY = 'SIC_CD_3'
    COL_INDUSTRY = 'SIC_CD_1'
    COL_DEFAULT = 'PERF_12M'

    df_vis = df.copy()
    df_vis[COL_INDUSTRY] = df_vis[COL_MID_INDUSTRY].apply(
        lambda x: 'Other' if pd.isna(x) or str(x).lower() == 'nan' or str(x)[0] in ['K', 'O', 'T'] else str(x)[0])
    df_vis[COL_DEFAULT] = pd.to_numeric(df_vis[COL_DEFAULT], errors='coerce')
    df_vis.dropna(subset=[COL_TIME, COL_INDUSTRY, COL_DEFAULT], inplace=True)

    # 2. 월별, 업종별 평균 부도율 집계
    df_vis['월별'] = df_vis[COL_TIME].dt.strftime('%Y-%m')
    df_heatmap = df_vis.groupby(['월별', COL_INDUSTRY])[COL_DEFAULT].mean().reset_index()
    df_heatmap.rename(columns={COL_DEFAULT: '부도율'}, inplace=True)

    # 3. 히트맵을 위한 데이터 피벗
    try:
        df_pivot = df_heatmap.pivot(index=COL_INDUSTRY, columns='월별', values='부도율')
        df_pivot = df_pivot.sort_index(axis=1, ascending=True)

        # Y축 순서 정렬 ('Other'를 마지막으로)
        categories = df_pivot.index.tolist()
        if 'Other' in categories:
            categories.remove('Other')
            # 알파벳 오름차순으로 정렬 후, 'Other'를 맨 뒤에 추가
            category_order = sorted(categories, reverse=False)
            category_order.append('Other')
            df_pivot = df_pivot.reindex(category_order)
        else:
            # Other가 없으면 그냥 알파벳 오름차순 정렬
            df_pivot = df_pivot.sort_index(ascending=True)

        print("--- 데이터 준비 완료 ---")
        return df_pivot
    except ValueError as e:
        print(f"피벗 오류 발생 (중복 월-업종 쌍 존재 가능): {e}")
        return None

def create_vis3_figure(pivot_df: pd.DataFrame) -> go.Figure:
    """
    준비된 피벗 데이터를 사용하여 월별/업종별 부도율 히트맵을 생성합니다.
    """
    UPPER_CAP = 0.04  # 색상 스케일의 최대값을 4%로 고정

    fig = px.imshow(
        pivot_df,
        text_auto=".1%",
        aspect="equal",
        color_continuous_scale='Blues',
        # title="<b>월별 & 업종별 부도율 히트맵</b>",
        range_color=[0, UPPER_CAP]
    )

    fig.update_layout(
        xaxis_title='기준년월',
        yaxis_title='업종 (대분류)',
        template='plotly_white',
        title_x=0.5
    )
    
    return fig


def main():
    """
    데이터를 로드하고, 시각화 3을 생성하여 화면에 출력합니다.
    """
    print("--- 시각화 3: 데이터 로딩 및 생성 시작 ---")
    
    # 1. 데이터 로딩
    df = load_cleansed_data()
    if df is None:
        print("✗ 데이터 로딩 실패. 시각화를 중단합니다.")
        return
    
    df_cleansed = df.copy()

    print("✓ 데이터 로딩 성공.")

    # 2. 시각화에 필요한 데이터 준비
    vis3_data = prepare_data_for_vis3(df_cleansed)
    
    # 3. Plotly Figure 생성
    if vis3_data is not None:
        fig = create_vis3_figure(vis3_data)
        
        # 4. 차트 출력 (스크립트 직접 실행 시)
        print("✓ 차트 생성 완료. 브라우저에 차트를 표시합니다.")
        fig.show()
    else:
        print("✗ 시각화 데이터 준비 실패.")


if __name__ == '__main__':
    main()
