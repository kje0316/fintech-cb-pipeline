
import pandas as pd
import plotly.graph_objects as go
from .kpi_dashboard import load_cleansed_data
from .kpi import calc_kpi4 # kpi.py에서 HHI 계산 함수 임포트

def prepare_data_for_vis5(df: pd.DataFrame) -> float:
    """
    HHI 지수를 계산하여 시각화에 필요한 데이터를 준비합니다.
    kpi.py의 calc_kpi4 함수를 재사용하여 코드 중복을 방지합니다.
    """
    print("--- HHI 지수 계산 시작 ---")
    hhi_score = calc_kpi4(df)
    print(f"✓ HHI 지수 계산 완료: {hhi_score:.2f}")
    return hhi_score

def create_vis5_figure(hhi_score: float) -> go.Figure:
    """
    준비된 HHI 지수를 사용하여 게이지 차트를 생성합니다.
    """
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = hhi_score,
        # title = {'text': f"<b>포트폴리오 위험 집중도 (HHI)</b>"},
        number = {'valueformat': ',.0f'},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, 10000], 'tickwidth': 1, 'tickcolor': "darkgray", 'tickvals': [0, 1500, 2500, 10000]},
            'bar': {'color': "#595959", 'thickness': 0.2},
            'bgcolor': "white",
            'steps': [ 
                {'range': [0, 1500], 'color': '#a9d18e'},
                {'range': [1500, 2500], 'color': '#fde291'},
                {'range': [2500, 10000], 'color': '#e67c73'}
            ],
            'threshold': {
                'line': {'color': "#c00000", 'width': 3},
                'thickness': 0.75,
                'value': 2500 
            }
        }
    ))
    
    # 레이블 추가
    # fig.add_annotation(text="✅ 분산됨", x=0.18, y=0.15, font=dict(size=12, color="#5a8236"), showarrow=False)
    # fig.add_annotation(text="⚠️ 다소 집중", x=0.5, y=0.15, font=dict(size=12, color="#b08520"), showarrow=False)
    # fig.add_annotation(text="🚨 고도 집중", x=0.82, y=0.15, font=dict(size=12, color="#c00000"), showarrow=False)

    return fig


def main():
    """
    데이터를 로드하고, 시각화 5를 생성하여 화면에 출력합니다.
    """
    print("--- 시각화 5: 데이터 로딩 및 생성 시작 ---")
    
    # 1. 데이터 로딩 및 전처리
    df = load_cleansed_data()
    if df is None:
        print("✗ 데이터 로딩 실패. 시각화를 중단합니다.")
        return
        
    target_date = pd.to_datetime('2021-08-01')
    df_cleansed = df.copy()
    df_cleansed['SIC_CD_1'] = df_cleansed['SIC_CD_3'].apply(
        lambda x: 'Other' if pd.isna(x) or str(x).lower() == 'nan' or str(x)[0] in ['K', 'O', 'T'] else str(x)[0])
    df_snapshot = df_cleansed[df_cleansed['BS_DT'] == target_date].copy()

    if df_snapshot.empty:
        print(f"✗ 해당 날짜({target_date.date()})의 데이터가 없습니다. 시각화를 중단합니다.")
        return

    print("✓ 데이터 로딩 및 전처리 성공.")

    # 2. 시각화에 필요한 데이터 준비 (HHI 점수 계산)
    hhi_score = prepare_data_for_vis5(df_snapshot)
    
    # 3. Plotly Figure 생성
    if hhi_score is not None:
        fig = create_vis5_figure(hhi_score)
        
        # 4. 차트 출력 (스크립트 직접 실행 시)
        print("✓ 차트 생성 완료. 브라우저에 차트를 표시합니다.")
        fig.show()
    else:
        print("✗ 시각화 데이터 준비 실패.")


if __name__ == '__main__':
    main()