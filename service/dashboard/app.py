import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide")
st.title("중소기업 재무 벤치마킹")

# --- FastAPI 서버 주소 ---
API_BASE_URL = "http://127.0.0.1:8000"

# --- 18개 재무지표 매핑 (R코드 → metric_code) ---
METRICS = {
    'R001': ('total_asset_growth', '총자산증가율'),
    'R002': ('revenue_growth', '매출액증가율'),
    'R006': ('debt_ratio', '부채비율'),
    'R007': ('equity_ratio', '자기자본비율'),
    'R008': ('current_ratio', '유동비율'),
    'R012': ('borrowing_dependency', '차입금의존도'),
    'R013': ('cogs_ratio', '매출원가율'),
    'R014': ('sga_ratio', '판관비율'),
    'R015': ('operating_margin', '영업이익률'),
    'R016': ('net_margin', '당기순이익률'),
    'R018': ('roe', '자기자본이익률(ROE)'),
    'R019': ('receivable_turnover', '매출채권회전율'),
    'R020': ('inventory_turnover', '재고자산회전율'),
    'R021': ('payable_turnover', '매입채무회전율'),
    'R022': ('total_asset_turnover', '총자산회전율'),
    'R023': ('roa', '총자산순이익률(ROA)'),
    'R024': ('current_asset_growth', '유동자산증가율'),
    'R025': ('tangible_asset_growth', '유형자산증가율'),
}

# --- 메타데이터 로드 (업종 정보) ---
@st.cache_data
def load_metadata():
    """FastAPI의 메타데이터 API를 호출하여 업종 정보를 가져옵니다."""
    try:
        # 업종 코드 불러오기
        industry_resp = requests.get(f"{API_BASE_URL}/api/v1/metadata/industries")
        industry_data = industry_resp.json()
        industry_map = {item['industry_code']: item['industry_name'] for item in industry_data}

        return industry_map

    except requests.exceptions.ConnectionError:
        st.error(f"백엔드 API 서버({API_BASE_URL})에 연결할 수 없습니다.")
        st.error("터미널에서 'uvicorn service.api.main:app --reload'가 실행 중인지 확인하세요.")
        return None
    except Exception as e:
        st.error(f"메타데이터 로드 실패: {e}")
        return None

# --- 벤치마크 데이터 조회 ---
def get_benchmark_data(industry_code, metric_code):
    """FastAPI의 벤치마킹 API를 호출합니다."""
    try:
        benchmark_url = f"{API_BASE_URL}/benchmark"
        params = {
            "industry": industry_code,
            "metric": metric_code
        }

        response = requests.get(benchmark_url, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"분석 실패 (API Error {response.status_code}): {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(f"백엔드 API 서버({API_BASE_URL})에 연결할 수 없습니다.")
        return None
    except Exception as e:
        st.error(f"API 호출 실패: {e}")
        return None

# --- 백분위 계산 ---
def calculate_percentile(my_value, benchmark_data):
    """사용자 값이 어느 백분위에 속하는지 계산합니다."""
    p10 = benchmark_data['p10']
    p25 = benchmark_data['p25']
    p50 = benchmark_data['p50']
    p75 = benchmark_data['p75']
    p90 = benchmark_data['p90']

    if my_value <= p10:
        return 10, "하위 10% 이하"
    elif my_value <= p25:
        # 10~25 사이 선형 보간
        percentile = 10 + ((my_value - p10) / (p25 - p10)) * 15
        return percentile, "하위 10~25%"
    elif my_value <= p50:
        # 25~50 사이 선형 보간
        percentile = 25 + ((my_value - p25) / (p50 - p25)) * 25
        return percentile, "하위 25~50%"
    elif my_value <= p75:
        # 50~75 사이 선형 보간
        percentile = 50 + ((my_value - p50) / (p75 - p50)) * 25
        return percentile, "상위 25~50%"
    elif my_value <= p90:
        # 75~90 사이 선형 보간
        percentile = 75 + ((my_value - p75) / (p90 - p75)) * 15
        return percentile, "상위 10~25%"
    else:
        return 90, "상위 10% 이상"

# --- 메인 UI ---
industry_map = load_metadata()

if industry_map:

    st.header("1. 내 정보 입력하기")

    # 업종 선택
    industry_names = list(industry_map.values())
    col1, col2 = st.columns(2)

    with col1:
        selected_industry_name = st.selectbox("업종을 선택하세요:", industry_names)

    with col2:
        # 재무지표 선택 (18개만)
        metric_names = [korean_name for _, (_, korean_name) in METRICS.items()]
        selected_metric_name = st.selectbox("분석할 재무 지표를 선택하세요:", metric_names)

    # 값 입력
    my_value = st.number_input(
        f"나의 '{selected_metric_name}' 값 입력:",
        value=100.0,
        format="%.2f"
    )

    # 한글 이름을 코드로 변환
    industry_code_map_rev = {v: k for k, v in industry_map.items()}
    selected_industry_code = industry_code_map_rev[selected_industry_name]

    # metric 이름으로 metric_code 찾기
    selected_metric_code = None
    for r_code, (metric_code, korean_name) in METRICS.items():
        if korean_name == selected_metric_name:
            selected_metric_code = r_code  # DB에 저장된 R001, R006 등의 코드 사용
            break

    # 분석 버튼
    if st.button("결과 분석하기", type="primary"):

        with st.spinner("데이터를 분석 중입니다..."):
            # API 호출
            data = get_benchmark_data(selected_industry_code, selected_metric_code)

            if data:
                st.header("2. 분석 결과")
                st.subheader(f"'{selected_industry_name}' 업종 내 '{selected_metric_name}' 비교")

                # 기본 통계
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        label="나의 값",
                        value=f"{my_value:.2f}"
                    )

                with col2:
                    avg = data['avg_value']
                    delta = my_value - avg
                    st.metric(
                        label="업종 평균",
                        value=f"{avg:.2f}",
                        delta=f"{delta:+.2f}"
                    )

                with col3:
                    median = data['median_value']
                    st.metric(
                        label="업종 중앙값",
                        value=f"{median:.2f}"
                    )

                with col4:
                    st.metric(
                        label="표본 수",
                        value=f"{data['count']:,}개 기업"
                    )

                # 백분위 분석
                percentile, range_text = calculate_percentile(my_value, data)

                st.divider()
                st.subheader("📊 백분위 분석")

                col1, col2 = st.columns([2, 1])

                with col1:
                    # 백분위 진행바
                    st.progress(percentile / 100)
                    st.write(f"귀하의 값은 **{range_text}**에 속합니다. (백분위: {percentile:.1f}%)")

                    # 백분위 분포 표시
                    st.write("#### 백분위 분포")
                    percentile_df = pd.DataFrame({
                        '백분위': ['10%', '25%', '50% (중앙값)', '75%', '90%'],
                        '값': [
                            f"{data['p10']:.2f}",
                            f"{data['p25']:.2f}",
                            f"{data['p50']:.2f}",
                            f"{data['p75']:.2f}",
                            f"{data['p90']:.2f}"
                        ]
                    })
                    st.dataframe(percentile_df, hide_index=True, use_container_width=True)

                with col2:
                    # 통계 요약
                    st.write("#### 기타 통계")
                    st.write(f"**최소값**: {data['min_value']:.2f}")
                    st.write(f"**최대값**: {data['max_value']:.2f}")
                    st.write(f"**표준편차**: {data['std_value']:.2f}")

                # 해석 도움말
                st.divider()
                st.subheader("💡 결과 해석")

                if percentile < 25:
                    st.info(
                        f"귀하의 '{selected_metric_name}'은(는) 업종 내에서 **낮은 편**입니다. "
                        f"업종 평균({avg:.2f})과 비교하여 개선이 필요할 수 있습니다."
                    )
                elif percentile < 50:
                    st.info(
                        f"귀하의 '{selected_metric_name}'은(는) 업종 내에서 **평균 이하**입니다. "
                        f"중앙값({median:.2f})을 목표로 개선을 고려해보세요."
                    )
                elif percentile < 75:
                    st.success(
                        f"귀하의 '{selected_metric_name}'은(는) 업종 내에서 **평균 이상**입니다. "
                        f"안정적인 수준을 유지하고 있습니다."
                    )
                else:
                    st.success(
                        f"귀하의 '{selected_metric_name}'은(는) 업종 내에서 **우수한 편**입니다. "
                        f"상위권을 유지하고 계십니다!"
                    )

else:
    st.error("메타데이터를 불러올 수 없습니다. API 서버를 확인해주세요.")
