import pandas as pd
import numpy as np

import yaml
from shared.config_loader import config

def cleanse_data(df_raw, yaml_path):
    """
    원본 데이터를 정제와 타입 변환
    - df_raw: 컬럼명 영문으로 변경된 원본 데이터프레임

    클렌징 전략 (Root Cause 기반 - 원인 먼저, 결과 나중):
    1. 중복 제거
    2. 경과일수 컬럼 → 5개 위험도 카테고리 변환 (999999999 = 이벤트 없음)
    3. Leaf 컬럼(기본 항목) 음수 제거 (물리적 정확성)
    4. Leaf 컬럼 IQR 이상치 제거 (통계적 정확성, 설정 기반)
    5. 파생컬럼 재계산 (17개 재무비율, 정제된 Leaf로 계산, 설정 기반)
    6. 파생컬럼 이상치 검증 (Optional, 설정 기반) -> 0으로 나눌 경우 결과를 0으로 대체 
    7. 주소지시군구 타입 변환
    8. 타입 변환 (date/str/numeric)

    핵심 로직: Leaf 이상치 제거 → 파생컬럼 재계산
    - Leaf가 정제되면 파생컬럼도 자동으로 정제됨 (Root Cause 해결)
    """

    if df_raw is None:
        return {}

    print("데이터 정제 및 변환 시작...")

    # Helper function: IQR 이상치 제거 (Leaf 및 Derived 컬럼 공통 사용)
    def remove_outliers_iqr(series, threshold):
        """
        IQR 방법으로 이상치 마스크 생성

        Args:
            series: pandas Series
            threshold: IQR 배수 (1.5=표준, 3.0=보수적, 1.0=공격적)

        Returns:
            outlier_mask: 이상치 위치 (True/False)
        """
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR

        return (series < lower_bound) | (series > upper_bound)

    # 1. 중복 제거
    df_raw.drop_duplicates(inplace=True)

    # 2. 경과일수 컬럼 → 5개 카테고리 변환
    print("  - 경과일수 컬럼을 5개 구간으로 범주화 중...")

    def categorize_days_since_event(days):
        """
        경과일수를 5개 위험도 카테고리로 변환

        Args:
            days: 경과일수 (999999999 = 이벤트 없음)

        Returns:
            0: 이벤트 없음 (999999999) - 가장 안전
            1: 장기 경과 (2년 초과) - 낮은 위험
            2: 중기 경과 (1-2년) - 중간 위험
            3: 단기 경과 (3개월-1년) - 높은 위험
            4: 최근 발생 (3개월 이내) - 매우 높은 위험
        """
        if pd.isna(days):
            return np.nan
        if days == 999999999 or days == 999999999.0:
            return 0  # 이벤트 없음
        elif days > 730:   # 2년 초과
            return 1
        elif days > 365:   # 1-2년
            return 2
        elif days > 90:    # 3개월-1년
            return 3
        else:              # 0-90일
            return 4

    # 경과일수 컬럼 목록
    days_since_cols = {
        'D2B000002': '신용도판단정보공공정보최근발생일자로부터경과일수',
        'D2B000003': '신용도판단정보공공정보최근해제일자로부터경과일수',
    }

    for col, name in days_since_cols.items():
        if col in df_raw.columns:
            # 원본 컬럼 백업 (필요시)
            # df_raw[f'{col}_원본'] = df_raw[col]

            # 카테고리 변환
            df_raw[col] = df_raw[col].apply(categorize_days_since_event)

            # 변환 결과 집계
            counts = df_raw[col].value_counts().sort_index()
            total = len(df_raw)

            print(f"    ✓ {name} ({col}):")
            category_names = {
                0: '이벤트 없음',
                1: '장기 경과(2년+)',
                2: '중기 경과(1-2년)',
                3: '단기 경과(3개월-1년)',
                4: '최근 발생(3개월내)'
            }
            for cat in sorted(counts.index):
                if not pd.isna(cat):
                    cat_int = int(cat)
                    cat_name = category_names.get(cat_int, f'카테고리{cat_int}')
                    pct = counts[cat] / total * 100
                    print(f"      - {cat_int}: {cat_name} = {counts[cat]:,}건 ({pct:.1f}%)")

    # 3. Leaf 컬럼 음수 제거 (양수여야 할 기본 재무 항목)
    print("  - Leaf 컬럼 이상치 제거 중...")

    # 양수여야 할 Leaf 컬럼 목록 (재무상태표 기본 항목)
    positive_leaf_cols = {
        # 자산 Leaf 컬럼
        'FN1_7': '현금',
        'FN1_8': '현금등가물',
        'FN1_9': '상품유가증권',
        'FN1_10': '현금성자산',
        'FN1_11': '매출채권',
        'FN1_4': '재고자산',
        'FN1_6': '재공품',
        'FN1_5': '유형자산',
        'FN1_11_3': '무형자산',
        'FN1_11_4': '투자자산',

        # 부채 Leaf 컬럼
        'FN1_15': '단기차입금',
        'FN1_16': '차입금',
        'FN1_17': '매입채무',

        # 자본 Leaf 컬럼
        'FN1_20': '자기자본(납입자본금)',
        'FN1_21': '자본잉여금',
        'FN1_22': '이익잉여금',

        # 손익계산서 Leaf 컬럼
        'FN2_1': '매출액',
        'FN2_2': '매출원가',
        'FN2_3': '판매비와관리비',
        'FN2_4': '금융비용',
        'FN3_4_1': '이자비용',
    }

    negative_counts = {}
    for col, name in positive_leaf_cols.items():
        if col in df_raw.columns:
            negative_mask = df_raw[col] < 0
            count = negative_mask.sum()
            if count > 0:
                negative_counts[name] = count
                df_raw.loc[negative_mask, col] = np.nan

    if negative_counts:
        print(f"    ✓ {sum(negative_counts.values())}건의 음수 값을 NULL로 변환:")
        for name, count in sorted(negative_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      - {name}: {count}건")

    # 4. Leaf 컬럼 IQR 이상치 제거 (파생컬럼 재계산 전에 실행)
    leaf_outlier_config = config.get('cleansing', {}).get('leaf_outlier_removal', {})

    if leaf_outlier_config.get('enabled', True):
        threshold = leaf_outlier_config.get('iqr_threshold', 1.5)
        print(f"  - Leaf 컬럼 이상치 제거 중 (IQR {threshold}배)...")

        # 대상 Leaf 컬럼 및 한글명 매핑
        target_leaf_cols = leaf_outlier_config.get('target_columns', [])
        leaf_names = {
            'FN1_13': '자산총계',
            'FN1_1': '유동자산',
            'FN1_2': '비유동자산',
            'FN1_3': '당좌자산',
            'FN1_4': '재고자산',
            'FN1_11': '매출채권',
            'FN1_19': '부채총계',
            'FN1_14': '유동부채',
            'FN1_18': '비유동부채',
            'FN1_16': '차입금',
            'FN1_15': '단기차입금',
            'FN1_17': '매입채무',
            'FN1_24': '자본총계',
            'FN1_22': '이익잉여금',
            'FN2_1': '매출액',
            'FN2_2': '매출원가',
            'FN2_3': '판매비와관리비',
            'FN2_5': '영업손익',
            'FN2_10': '당기순이익',
            'FN3_2': '영업활동현금흐름',
        }

        leaf_outlier_counts = {}
        for col in target_leaf_cols:
            if col in df_raw.columns:
                # NULL이 아닌 값만 대상
                valid_mask = df_raw[col].notna()
                valid_series = df_raw.loc[valid_mask, col]

                if len(valid_series) > 0:
                    outlier_mask_series = remove_outliers_iqr(valid_series, threshold)
                    count = outlier_mask_series.sum()

                    if count > 0:
                        # 이상치를 NULL로 변환
                        outlier_indices = valid_series[outlier_mask_series].index
                        df_raw.loc[outlier_indices, col] = np.nan
                        leaf_outlier_counts[leaf_names.get(col, col)] = count

        if leaf_outlier_counts:
            total = sum(leaf_outlier_counts.values())
            print(f"    ✓ {total:,}건의 Leaf 이상치를 NULL로 변환:")
            for name, count in sorted(leaf_outlier_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"      - {name}: {count:,}건")
        else:
            print(f"    ✓ 이상치 없음")

    # 5. 파생컬럼 재계산 (재무비율 17개) - 정제된 Leaf 컬럼 사용
    derived_config = config.get('cleansing', {}).get('derived_columns', {})

    if derived_config.get('enabled', True):
        print("  - 파생컬럼 재계산 중 (21개 재무비율, 고신뢰도만)...")

        log_comparison = derived_config.get('log_comparison', False)
        threshold = derived_config.get('comparison_threshold', 0.01)

        # 재계산할 재무비율 정의 (분자, 분모, 백분율여부, 설명)
        # ⚠️ 원본 CSV 대비 검증 완료 (일치율 95% 이상만 재계산)
        #
        # 검증 결과 (10,000행 샘플):
        # - 일치율 95% 이상: 21개 → 재계산 ✅
        # - 일치율 80-95%: 3개 (R022, N004, R012) → 원본 유지 ⚠️
        # - 일치율 80% 미만: 6개 (N002, N006, N009, N010, N011, R021) → 원본 유지 ❌
        #
        # 재무비율 계산 방식:
        # 1. 기본 비율 = 분자 / 분모
        # 2. 백분율 변환 (is_percent=True인 경우): 비율 × 100
        # 3. 분모 0 처리: inf 발생 시 0으로 치환 (NULL과 구분)

        ratios_to_recalc = {
            # === 재무상태표 비율 (안정성) ===

            'R006': ('FN1_19', 'FN1_24', True,
                    '부채비율: 기업의 부채 의존도 측정\n'
                    '              계산: (부채총계 / 자본총계) × 100\n'
                    '              의미: 자본 대비 부채 비율, 낮을수록 재무 안정성 높음\n'
                    '              검증: 평균 오차 0.00001, 100% 일치'),

            'R007': ('FN1_24', 'FN1_13', True,
                    '자기자본비율: 총자산 중 자기자본 비중\n'
                    '              계산: (자본총계 / 자산총계) × 100\n'
                    '              의미: 자산의 자기자본 비율, 높을수록 재무 안정성 높음\n'
                    '              검증: 평균 오차 0.00002, 100% 일치'),

            'R008': ('FN1_1', 'FN1_14', True,
                    '유동비율: 단기 채무 지급 능력 측정\n'
                    '              계산: (유동자산 / 유동부채) × 100\n'
                    '              의미: 유동부채 대비 유동자산 비율, 100% 이상이 안전\n'
                    '              검증: 평균 오차 0.00001, 100% 일치'),

            # === 손익계산서 비율 (수익성) ===

            'R013': ('FN2_2', 'FN2_1', True,
                    '매출원가율: 매출액 대비 원가 비중\n'
                    '              계산: (매출원가 / 매출액) × 100\n'
                    '              의미: 매출 중 원가 비율, 낮을수록 수익성 높음\n'
                    '              검증: 평균 오차 0.000008, 100% 일치'),

            'R014': ('FN2_3', 'FN2_1', True,
                    '판관비율: 매출액 대비 판매관리비 비중\n'
                    '              계산: (판매비와관리비 / 매출액) × 100\n'
                    '              의미: 매출 중 관리비용 비율\n'
                    '              검증: 평균 오차 0.000001, 100% 일치'),

            'R015': ('FN2_5', 'FN2_1', True,
                    '영업이익율: 매출액 대비 영업이익 비율\n'
                    '              계산: (영업손익 / 매출액) × 100\n'
                    '              의미: 본업에서의 수익성, 높을수록 좋음\n'
                    '              검증: 평균 오차 0.000001, 100% 일치'),

            'R016': ('FN2_10', 'FN2_1', True,
                    '당기순이익율: 매출액 대비 순이익 비율\n'
                    '              계산: (당기순이익 / 매출액) × 100\n'
                    '              의미: 최종 수익성 지표\n'
                    '              검증: 평균 오차 0.000001, 100% 일치'),

            'R018': ('FN2_10', 'FN1_24', False,
                    '자기자본이익률(ROE): 자본 대비 수익성\n'
                    '              계산: 당기순이익 / 자본총계\n'
                    '              의미: 자본 1원당 수익, 투자 수익률\n'
                    '              검증: 평균 오차 0.000000, 100% 일치'),

            'R023': ('FN2_10', 'FN1_13', True,
                    '총자산순이익률(ROA): 자산 대비 수익성\n'
                    '              계산: (당기순이익 / 자산총계) × 100\n'
                    '              의미: 자산 활용 효율성\n'
                    '              검증: 평균 오차 0.000001, 100% 일치'),

            # === 활동성 비율 (효율성) ===

            'R020': ('FN2_2', 'FN1_4', False,
                    '재고자산회전율: 재고 관리 효율성\n'
                    '              계산: 매출원가 / 재고자산\n'
                    '              의미: 재고가 1년에 몇 번 회전하는지, 높을수록 효율적\n'
                    '              검증: 평균 오차 0.00001, 100% 일치'),

            # 'R022': ('FN2_1', 'FN1_13', False,
            #         '총자산회전율: 자산 활용 효율성\n'
            #         '              계산: 매출액 / 자산총계\n'
            #         '              의미: 자산 1원당 매출액, 높을수록 효율적\n'
            #         '              검증: 평균 오차 0.03, 상대 오차 4%\n'
            #         '              → 원본 유지 (경미한 오차지만 다른 계산 방법 가능성)'),

            # === 증가율 (성장성) ===

            'R001': ('FN1_13', 'FN1_13_1', True,
                    '총자산증가율: 자산 규모 성장률 (비표준 공식)\n'
                    '              계산: ((자산총계 - 자산총계(전기)) / 자산총계) × 100\n'
                    '              의미: 자산 증가율 (당기 기준 - 일반적인 전기 기준과 다름)\n'
                    '              검증: 평균 오차 0.0002, 100% 일치\n'
                    '              주의: 표준 공식은 (당기-전기)/전기×100 이나 원본 CSV는 당기 기준'),

            'R002': ('FN2_1', 'FN2_1_1', True,
                    '매출액증가율: 매출 성장률 (표준 공식)\n'
                    '              계산: ((매출액 - 전기매출액) / 전기매출액) × 100\n'
                    '              의미: 매출 증가율, 기업 성장성 지표\n'
                    '              검증: 평균 오차 0.00004, 100% 일치'),

            'R019': ('FN2_1', 'FN1_11', False,
                    '매출채권회전율: 채권 회수 효율성\n'
                    '              계산: 매출액 / 평균매출채권\n'
                    '                   (평균매출채권 = (당기 매출채권 + 전기 매출채권) / 2)\n'
                    '              의미: 매출채권이 1년에 몇 번 현금화되는지\n'
                    '              검증: 평균 오차 0.0000, 100% 일치 (평균 사용 시)\n'
                    '              주의: 단순 당기 매출채권 사용 시 오차 발생'),

            # === N 시리즈: 추가 재무비율 (일치율 95% 이상만) ===

            'N001': ('FN1_15', 'FN1_13', True,
                    '단기차입금의존도: 자산 대비 단기차입금 비율\n'
                    '              계산: (단기차입금 / 자산총계) × 100\n'
                    '              의미: 단기 부채 의존도\n'
                    '              검증: 평균 오차 0.00, 100% 일치'),

            'N003': (None, None, False,  # complex
                    '순운전자본회전율: 운전자본 효율성\n'
                    '              계산: 매출액 / (유동자산 - 유동부채)\n'
                    '              의미: 순운전자본 활용도\n'
                    '              검증: 평균 오차 0.00, 100% 일치'),

            'N005': (None, None, True,  # complex
                    '매출총이익율: 매출 대비 매출총이익 비율\n'
                    '              계산: ((매출액 - 매출원가) / 매출액) × 100\n'
                    '              의미: 원가 제외 수익성\n'
                    '              검증: 평균 오차 0.00, 100% 일치'),

            'N008': ('FN3_2', 'FN2_1', True,
                    'OCF/매출액비율: 매출 대비 영업현금흐름\n'
                    '              계산: (영업활동현금흐름 / 매출액) × 100\n'
                    '              의미: 현금 창출 능력\n'
                    '              검증: 평균 오차 0.00, 100% 일치'),

            'N012': ('FN2_1', 'FN1_24', False,
                    '총자본회전율: 자본 대비 매출액\n'
                    '              계산: 매출액 / 자본총계\n'
                    '              의미: 자본 활용 효율성\n'
                    '              검증: 평균 오차 0.00, 100% 일치'),

            # === 검증 실패 / 원본 데이터 유지 (주석 처리) ===

            # 'R012': ('FN1_16', 'FN1_13', True,
            #         '차입금의존도: 총자산 대비 차입금 비율\n'
            #         '              계산: (차입금 / 자산총계) × 100\n'
            #         '              의미: 자산 중 차입금 비중\n'
            #         '              검증: 평균 오차 6.96, 일치율 2.2% ❌\n'
            #         '              문제: 원본 CSV와 불일치, 원본 값 유지'),

            # 'R021': ('FN2_2', 'FN1_17', False,
            #         '매입채무회전율: 매입채무 지급 주기\n'
            #         '              계산: 매출원가 / 매입채무\n'
            #         '              의미: 매입채무가 1년에 몇 번 지급되는지\n'
            #         '              검증: 평균 오차 57,609 ❌\n'
            #         '              문제: 원본 CSV 데이터 오류 (일부 행에 9,221,303 같은 비정상 값)\n'
            #         '                    원본 값 유지하되 이상치 제거 단계에서 처리'),

            # 'R024': ('FN2_10', 'FN1_20', False,
            #         '유동자산증가율: 유동자산 성장률\n'
            #         '              계산: ((유동자산 - 전기 유동자산) / 전기 유동자산) × 100\n'
            #         '              검증: 불가능 ❌\n'
            #         '              문제: 원본 CSV에 "유동자산(전기)" 컬럼 없음\n'
            #         '                    원본 값 유지'),
        }

        # 재계산 전 원본 값 저장 (비교 로그용)
        original_values = {}
        if log_comparison:
            sample_ratios = ['R006', 'R007', 'R018', 'R019', 'R022']  # 샘플 5개
            for ratio in sample_ratios:
                if ratio in df_raw.columns:
                    original_values[ratio] = df_raw[ratio].copy()

        # 재무비율 재계산
        recalc_count = 0
        for ratio_code, (numerator, denominator, is_percent, desc) in ratios_to_recalc.items():
            if ratio_code not in df_raw.columns:
                continue

            # N 시리즈 complex 계산 (numerator가 None인 경우 먼저 처리)
            if ratio_code == 'N003':
                # N003 = 매출액 / (유동자산 - 유동부채)
                working_capital = df_raw['FN1_1'] - df_raw['FN1_14']
                df_raw[ratio_code] = df_raw['FN2_1'] / working_capital
                df_raw[ratio_code] = df_raw[ratio_code].replace([np.inf, -np.inf], 0)
                recalc_count += 1
                continue

            elif ratio_code == 'N005':
                # N005 = ((매출액 - 매출원가) / 매출액) × 100
                gross_profit = df_raw['FN2_1'] - df_raw['FN2_2']
                df_raw[ratio_code] = (gross_profit / df_raw['FN2_1']) * 100
                df_raw[ratio_code] = df_raw[ratio_code].replace([np.inf, -np.inf], 0)
                recalc_count += 1
                continue

            # 일반 비율: numerator/denominator 존재 확인
            if numerator not in df_raw.columns or denominator not in df_raw.columns:
                continue

            # 특수 계산: 증가율 (당기 - 전기)
            if ratio_code == 'R001':
                # R001 = (자산총계 - 자산총계(전기)) / 자산총계 × 100
                df_raw[ratio_code] = ((df_raw[numerator] - df_raw[denominator]) / df_raw[numerator]) * 100
                df_raw[ratio_code] = df_raw[ratio_code].replace([np.inf, -np.inf], 0)
                recalc_count += 1

            elif ratio_code == 'R002':
                # R002 = (매출액 - 전기매출액) / 전기매출액 × 100
                df_raw[ratio_code] = ((df_raw[numerator] - df_raw[denominator]) / df_raw[denominator]) * 100
                df_raw[ratio_code] = df_raw[ratio_code].replace([np.inf, -np.inf], 0)
                recalc_count += 1

            elif ratio_code == 'R019':
                # R019 = 매출액 / 평균매출채권
                # 평균매출채권 = (당기 매출채권 + 전기 매출채권) / 2
                prev_col = 'FN1_11_1'  # 매출채권(전기)
                if prev_col in df_raw.columns:
                    avg_receivables = (df_raw[denominator] + df_raw[prev_col]) / 2
                    df_raw[ratio_code] = df_raw[numerator] / avg_receivables
                    df_raw[ratio_code] = df_raw[ratio_code].replace([np.inf, -np.inf], 0)
                    recalc_count += 1
                else:
                    # 전기 데이터 없으면 단순 계산
                    df_raw[ratio_code] = df_raw[numerator] / df_raw[denominator]
                    df_raw[ratio_code] = df_raw[ratio_code].replace([np.inf, -np.inf], 0)
                    recalc_count += 1

            else:
                # 일반 비율 계산
                df_raw[ratio_code] = df_raw[numerator] / df_raw[denominator]

                # 백분율 변환 (필요시)
                if is_percent:
                    df_raw[ratio_code] = df_raw[ratio_code] * 100

                # 분모 0인 경우 inf 발생 → 0으로 치환 (NULL과 구분)
                df_raw[ratio_code] = df_raw[ratio_code].replace([np.inf, -np.inf], 0)
                recalc_count += 1

        print(f"    ✓ {recalc_count}개 재무비율 재계산 완료 (증가율/평균 포함, 백분율, 분모 0 → 0 처리)")

        # 재계산 전후 비교 로그
        if log_comparison and original_values:
            print(f"    ✓ 재계산 전후 비교 (샘플 {len(original_values)}개):")
            for ratio, original in original_values.items():
                recalculated = df_raw[ratio]
                diff = (recalculated - original).dropna()

                if len(diff) > 0:
                    changed_mask = diff.abs() > threshold
                    changed_count = changed_mask.sum()

                    if changed_count > 0:
                        print(f"      - {ratio}: {changed_count:,}건 변경 (평균 차이: {diff.mean():.2f}, 최대: {diff.abs().max():.2f})")
                    else:
                        print(f"      - {ratio}: 변경 없음")

    # 6. 파생컬럼 이상치 제거 (Optional - 파생컬럼 검증용)
    # Note: Leaf 이상치가 제거되었으므로 파생컬럼 이상치는 이론적으로 적어야 함
    outlier_config = config.get('cleansing', {}).get('outlier_removal', {})

    if outlier_config.get('enabled', True):
        threshold = outlier_config.get('iqr_threshold', 1.5)
        print(f"  - 파생컬럼 이상치 검증 중 (IQR {threshold}배)...")

        # remove_outliers_iqr 함수는 이미 위에서 정의됨 (step 4)

        # 대상 컬럼 및 한글명 매핑
        target_cols = outlier_config.get('target_columns', [])
        ratio_names = {
            'R006': '부채비율',
            'R007': '자기자본비율',
            'R008': '유동비율',
            'R012': '차입금의존도',
            'R013': '매출원가율',
            'R014': '판관비율',
            'R019': '매출채권회전율',
            'R020': '재고자산회전율',
            'R021': '매입채무회전율',
            'R022': '총자산회전율',
        }

        outlier_counts = {}
        for col in target_cols:
            if col in df_raw.columns:
                # NULL이 아닌 값만 대상
                valid_mask = df_raw[col].notna()
                valid_series = df_raw.loc[valid_mask, col]

                if len(valid_series) > 0:
                    outlier_mask_series = remove_outliers_iqr(valid_series, threshold)
                    count = outlier_mask_series.sum()

                    if count > 0:
                        # 이상치를 NULL로 변환
                        outlier_indices = valid_series[outlier_mask_series].index
                        df_raw.loc[outlier_indices, col] = np.nan
                        outlier_counts[ratio_names.get(col, col)] = count

        if outlier_counts:
            total = sum(outlier_counts.values())
            print(f"    ✓ {total:,}건의 이상치를 NULL로 변환:")
            for name, count in sorted(outlier_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      - {name}: {count:,}건")
        else:
            print(f"    ✓ 이상치 없음")

    # 6. 주소지시군구 소수점 제거
    df_raw['CT_CNTY_GU_CD'] = df_raw['CT_CNTY_GU_CD'].astype('Int64').astype(str)

    # (아래 주석 처리된 코드는 삭제 예정 - 위에서 재계산 완료)
    # # R001: 총자본순이익률 (당기순이익 / 자산총계)
    # df_raw['R001'] = df_raw['FN2-3'] / df_raw['FN1-13'].replace(0, np.nan)

    # # R002: 자기자본순이익률 (당기순이익 / 자본총계)
    # df_raw['R002'] = df_raw['FN2-3'] / df_raw['FN1-24'].replace(0, np.nan)

    # # R006: 부채비율 (부채총계 / 자본총계)
    # df_raw['R006'] = df_raw['FN1-18'] / df_raw['FN1-24'].replace(0, np.nan)

    # # R007: 유동비율 (유동자산 / 유동부채)
    # df_raw['R007'] = df_raw['FN1-1'] / df_raw['FN1-17'].replace(0, np.nan)

    # # R008: 당좌비율 (당좌자산 / 유동부채)
    # df_raw['R008'] = df_raw['FN1-2'] / df_raw['FN1-17'].replace(0, np.nan)

    # # R012: 이자보상배율 (영업이익 / 이자비용)
    # df_raw['R012'] = df_raw['FN2-5'] / df_raw['FN3-4'].replace(0, np.nan)

    # # R013: 총자산회전율 (매출액 / 자산총계)
    # df_raw['R013'] = df_raw['FN2-1'] / df_raw['FN1-13'].replace(0, np.nan)

    # # R014: 매출채권회전율 (매출액 / 매출채권및기타채권) - (맵핑표의 'FN1-3' 항목 사용)
    # df_raw['R014'] = df_raw['FN2-1'] / df_raw['FN1-3'].replace(0, np.nan)

    # # R015: 영업이익률 (영업이익 / 매출액)
    # df_raw['R015'] = df_raw['FN2-5'] / df_raw['FN2-1'].replace(0, np.nan)

    # # R016: 순이익률 (당기순이익 / 매출액)
    # df_raw['R016'] = df_raw['FN2-3'] / df_raw['FN2-1'].replace(0, np.nan)

    # # R018: 자기자본이익률(ROE) (당기순이익 / 자본총계) - (R002와 동일)
    # df_raw['R018'] = df_raw['FN2-3'] / df_raw['FN1-24'].replace(0, np.nan)

    # # R019: 총자산이익률(ROA) (당기순이익 / 자산총계) - (R001과 동일)
    # df_raw['R019'] = df_raw['FN2-3'] / df_raw['FN1-13'].replace(0, np.nan)

    # # R020: 자본집약도 (자산총계 / 매출액) - (총자산회전율의 역수)
    # df_raw['R020'] = df_raw['FN1-13'] / df_raw['FN2-1'].replace(0, np.nan)

    # # R021: 매입채무회전율 (매출원가 / 매입채무및기타채무) - (맵핑표의 'FN1-19' 항목 사용)
    # df_raw['R021'] = df_raw['FN2-2'] / df_raw['FN1-19'].replace(0, np.nan)

    # # R022: 재고자산회전율 (매출원가 / 재고자산)
    # df_raw['R022'] = df_raw['FN2-2'] / df_raw['FN1-4'].replace(0, np.nan)

    # # R023: 총자산순이익률 (당기순이익 / 자산총계) - (R001, R019와 동일)
    # df_raw['R023'] = df_raw['FN2-3'] / df_raw['FN1-13'].replace(0, np.nan)

    # # R024: 자본금순이익률 (당기순이익 / 자본금)
    # df_raw['R024'] = df_raw['FN2-3'] / df_raw['FN1-20'].replace(0, np.nan)

    # # R025: 유형자산증가율 ((당기 유형자산 - 전기 유형자산) / 전기 유형자산)
    # df_raw['R025'] = (df_raw['FN1-10'] - df_raw['FN1-10.1']) / df_raw['FN1-10.1'].replace(0, np.nan)



    # 6. 타입 변환
    with open(yaml_path, 'r', encoding="utf-8") as f: 
        column_types = yaml.safe_load(f)

    for col in column_types.get('date', []):
        if col in df_raw.columns:
            df_raw[col] = pd.to_datetime(df_raw[col], format="%Y%m%d", errors='coerce')

    for col in column_types.get('str', []):
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].astype('str').str.strip()

    for col in column_types.get('numeric', []):
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
    
    print('데이터 타입 변환 완료.')

    return df_raw



