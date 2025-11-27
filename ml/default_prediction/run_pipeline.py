"""
부도예측 모델 학습 파이프라인

원본 데이터 → 37개 입력 컬럼 추출 → 70개 피처 생성 → 모델 학습 → MLflow 등록

피처 구조:
- 37개 입력 컬럼: 유저가 실제로 입력하는 데이터
- 70개 피처: 파생 변수 포함, 클러스터링 팀과 동일한 피처셋
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np
import yaml
from sklearn.model_selection import train_test_split

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# ============================================================================
# 37개 입력 컬럼 정의 (columns_map.yaml 기준, 소문자)
# ============================================================================
INPUT_37_COLUMNS = [
    # 재무상태표 (12개)
    'fn1_13',      # 자산총계
    'fn1_1',       # 유동자산
    'fn1_4',       # 재고자산
    'fn1_11',      # 매출채권
    'fn1_19',      # 부채총계
    'fn1_24',      # 자본총계
    'fn1_14',      # 유동부채
    'fn1_15',      # 단기차입금
    'fn1_16',      # 차입금
    'fn1_5',       # 유형자산 (기존 fn1_유형자산 → fn1_5)
    'fn1_17',      # 매입채무 (기존 fn1_매입채무 → fn1_17)
    'fn3_6',       # 적립금비율 (기존 fn3_적립금 → fn3_6)

    # 손익계산서 (8개)
    'fn2_1',       # 매출액
    'fn2_2',       # 매출원가
    'fn2_2_1',     # 매출총이익
    'fn2_3',       # 판매비와관리비
    'fn2_5',       # 영업손익
    'fn2_5_1',     # 전기영업이익
    'fn2_10',      # 당기순이익
    'fn2_10_1',    # 당기순이익(전기)

    # 현금흐름/기타 (6개)
    'fn3_1',       # 현금흐름
    'fn3_2',       # 영업활동현금흐름
    'fn3_7',       # EBIT
    'fn3_8',       # EBITDA
    'fn3_11_1',    # 순차입금
    'fn2_4',       # 이자비용

    # 전년도 데이터 (4개)
    'fn1_13_1',    # 자산총계(전기) (기존 fn1_13_전기 → fn1_13_1)
    'fn2_1_1',     # 전기매출액 (기존 fn2_1_전기 → fn2_1_1)
    'fn1_11_1',    # 매출채권(전기) (기존 fn1_1_전기 → fn1_11_1)
    'fn1_24_1',    # 전기자본총계 (추가)

    # 기업정보 (2개)
    'empe_cnt',    # 종업원수
    'wg_gb',       # 외감구분

    # 연체정보 (7개)
    'da0d00029', 'da0d00026', 'da0d00035_1', 'da0d00035_2',
    'da0d00033_1', 'db0d00006', 'd2b000002',
]


# ============================================================================
# 70개 피처 목록 (클러스터링 팀과 동일)
# ============================================================================
CLUSTERING_70_FEATURES = [
    # 재무상태표 기본 (10개)
    'FN1_13', 'FN1_1', 'FN1_4', 'FN1_11', 'FN1_14', 'FN1_15',
    'FN1_16', 'FN1_19', 'FN1_20', 'FN1_24',

    # 손익계산서 기본 (4개)
    'FN2_1', 'FN2_2_1', 'FN2_5', 'FN2_10',

    # 현금흐름/기타 기본 (10개)
    'FN3_1', 'FN3_2', 'FN3_3', 'FN3_4', 'FN3_6', 'FN3_7',
    'FN3_8', 'FN3_10', 'FN3_11', 'FN3_11_1',

    # 연체정보 (7개)
    'DA0D00021', 'DA0D00026', 'DA0D00029', 'DA0D00033_1',
    'DA0D00035_1', 'DB0D00006', 'D2B000012',

    # 안정성 비율 (7개)
    'R006', 'R007', 'R008', 'R009', 'R012', 'N001', 'N002',

    # 수익성 비율 (7개)
    'R013', 'R015', 'R016', 'R018', 'R023', 'N004', 'N005',

    # 활동성 비율 (6개)
    'R019', 'R020', 'R021', 'R022', 'N003', 'N012',

    # 성장성 비율 (8개)
    'R001', 'R002', 'R003', 'R004', 'R024', 'R025', 'N007',

    # 현금흐름/생산성 비율 (5개)
    'N006', 'N008', 'N009', 'N010', 'N011',
]


def create_derived_features(row: Dict) -> Dict:
    """
    37개 입력으로 파생 변수 생성

    Args:
        row: 37개 입력값 딕셔너리

    Returns:
        파생 변수 포함된 딕셔너리
    """
    data = dict(row)

    # 0 나누기 방지용 상수
    eps = 1e-6

    # 기본값 설정
    fn1_13 = data.get('fn1_13', 0) or 0  # 자산총계
    fn1_1 = data.get('fn1_1', 0) or 0    # 유동자산
    fn1_4 = data.get('fn1_4', 0) or 0    # 재고자산
    fn1_11 = data.get('fn1_11', 0) or 0  # 매출채권
    fn1_14 = data.get('fn1_14', 0) or 0  # 유동부채
    fn1_15 = data.get('fn1_15', 0) or 0  # 단기차입금
    fn1_16 = data.get('fn1_16', 0) or 0  # 차입금
    fn1_19 = data.get('fn1_19', 0) or 0  # 부채총계
    fn1_24 = data.get('fn1_24', 0) or 0  # 자본총계
    fn2_1 = data.get('fn2_1', 0) or 0    # 매출액
    fn2_2 = data.get('fn2_2', 0) or 0    # 매출원가
    fn2_2_1 = data.get('fn2_2_1', 0) or 0  # 매출총이익
    fn2_5 = data.get('fn2_5', 0) or 0    # 영업손익
    fn2_10 = data.get('fn2_10', 0) or 0  # 당기순이익
    fn2_4 = data.get('fn2_4', 0) or 0    # 이자비용
    fn3_1 = data.get('fn3_1', 0) or 0    # 현금흐름
    fn3_2 = data.get('fn3_2', 0) or 0    # 영업활동현금흐름
    fn3_7 = data.get('fn3_7', 0) or 0    # EBIT
    fn3_8 = data.get('fn3_8', 0) or 0    # EBITDA
    fn3_11_1 = data.get('fn3_11_1', 0) or 0  # 순차입금
    fn1_매입채무 = data.get('fn1_17', 0) or 0      # 매입채무
    fn3_적립금비율 = data.get('fn3_6', 0) or 0     # 적립금비율
    fn1_유형자산 = data.get('fn1_5', 0) or 0       # 유형자산

    # 전기 데이터
    fn1_13_전기 = data.get('fn1_13_1', 0) or 0     # 자산총계(전기)
    fn2_1_전기 = data.get('fn2_1_1', 0) or 0       # 전기매출액
    fn1_24_전기 = data.get('fn1_24_1', 0) or 0     # 전기자본총계
    fn2_5_전기 = data.get('fn2_5_1', 0) or 0       # 전기영업이익
    fn2_10_전기 = data.get('fn2_10_1', 0) or 0     # 당기순이익(전기)

    # ========== 안정성 비율 ==========
    # 부채비율 = 부채총계 / 자본총계
    data['debt_ratio'] = fn1_19 / (fn1_24 + eps) if fn1_24 > 0 else 0

    # 자기자본비율 = 자본총계 / 자산총계
    data['equity_ratio'] = fn1_24 / (fn1_13 + eps) if fn1_13 > 0 else 0

    # 유동비율 = 유동자산 / 유동부채
    data['current_ratio'] = fn1_1 / (fn1_14 + eps) if fn1_14 > 0 else 0

    # 당좌비율 = (유동자산 - 재고자산) / 유동부채
    data['quick_ratio'] = (fn1_1 - fn1_4) / (fn1_14 + eps) if fn1_14 > 0 else 0

    # 차입금의존도 = 차입금 / 자산총계
    data['borrowing_dependency'] = fn1_16 / (fn1_13 + eps) if fn1_13 > 0 else 0

    # 단기차입금의존도 = 단기차입금 / 자산총계
    data['short_term_borrowing_dependency'] = fn1_15 / (fn1_13 + eps) if fn1_13 > 0 else 0

    # ========== 수익성 비율 ==========
    # 영업이익률 = 영업손익 / 매출액
    data['operating_margin'] = fn2_5 / (fn2_1 + eps) if fn2_1 > 0 else 0

    # ROE = 당기순이익 / 자본총계
    data['roe'] = fn2_10 / (fn1_24 + eps) if fn1_24 > 0 else 0

    # 매출총이익률
    if fn2_2_1 > 0 and fn2_1 > 0:
        data['gross_margin'] = fn2_2_1 / fn2_1
    elif fn2_1 > 0:
        data['gross_margin'] = (fn2_1 - fn2_2) / fn2_1
    else:
        data['gross_margin'] = 0

    # ========== 활동성 비율 ==========
    # 매출채권회전율 = 매출액 / 매출채권
    data['receivable_turnover'] = fn2_1 / (fn1_11 + eps) if fn1_11 > 0 else 0

    # 재고자산회전율 = 매출원가 / 재고자산
    data['inventory_turnover'] = fn2_2 / (fn1_4 + eps) if fn1_4 > 0 else 0

    # 총자산회전율 = 매출액 / 자산총계
    data['total_capital_turnover'] = fn2_1 / (fn1_13 + eps) if fn1_13 > 0 else 0

    # 순운전자본회전율
    net_working_capital = fn1_1 - fn1_14
    data['net_working_capital'] = net_working_capital
    data['nwc_turnover'] = fn2_1 / (net_working_capital + eps) if net_working_capital > 0 else 0

    # ========== 현금흐름 비율 ==========
    # EBITDA마진율 = EBITDA / 매출액
    data['ebitda_margin'] = fn3_8 / (fn2_1 + eps) if fn2_1 > 0 else 0

    # OCF마진율 = 영업활동현금흐름 / 매출액
    data['ocf_margin'] = fn3_2 / (fn2_1 + eps) if fn2_1 > 0 else 0

    # 차입금/EBITDA
    data['debt_to_ebitda'] = fn1_16 / (fn3_8 + eps) if fn3_8 > 0 else 999

    # 이자보상배율 = EBIT / 이자비용
    data['interest_coverage_ebit'] = fn3_7 / (fn2_4 + eps) if fn2_4 > 0 else 0

    # ========== 성장성 비율 ==========
    # 총자산증가율
    data['asset_growth'] = (fn1_13 - fn1_13_전기) / (fn1_13_전기 + eps) if fn1_13_전기 > 0 else 0

    # 매출액증가율
    data['revenue_growth'] = (fn2_1 - fn2_1_전기) / (fn2_1_전기 + eps) if fn2_1_전기 > 0 else 0

    # 자본총계증가율
    data['equity_growth'] = (fn1_24 - fn1_24_전기) / (fn1_24_전기 + eps) if fn1_24_전기 > 0 else 0

    # 영업이익증가율
    data['operating_income_growth'] = (fn2_5 - fn2_5_전기) / (abs(fn2_5_전기) + eps) if fn2_5_전기 != 0 else 0

    # 당기순이익증가율
    data['net_income_growth'] = (fn2_10 - fn2_10_전기) / (abs(fn2_10_전기) + eps) if fn2_10_전기 != 0 else 0

    # 유형자산 저장 (R025 계산용)
    data['fn1_5'] = fn1_유형자산

    return data


def map_to_70_features(data: Dict) -> Dict:
    """
    파생 변수 포함 데이터를 70개 클러스터링 피처로 매핑

    Args:
        data: 파생 변수 포함 딕셔너리

    Returns:
        70개 피처 딕셔너리 (대문자 컬럼명)
    """
    eps = 1e-6
    features = {}

    # ========== 재무상태표 기본 ==========
    features['FN1_13'] = data.get('fn1_13', 0) or 0
    features['FN1_1'] = data.get('fn1_1', 0) or 0
    features['FN1_4'] = data.get('fn1_4', 0) or 0
    features['FN1_11'] = data.get('fn1_11', 0) or 0
    features['FN1_14'] = data.get('fn1_14', 0) or 0
    features['FN1_15'] = data.get('fn1_15', 0) or 0
    features['FN1_16'] = data.get('fn1_16', 0) or 0
    features['FN1_19'] = data.get('fn1_19', 0) or 0
    features['FN1_20'] = data.get('fn1_24', 0) or 0  # 자기자본 = 자본총계
    features['FN1_24'] = data.get('fn1_24', 0) or 0

    # ========== 손익계산서 기본 ==========
    features['FN2_1'] = data.get('fn2_1', 0) or 0
    features['FN2_2_1'] = data.get('fn2_2_1', 0) or 0
    features['FN2_5'] = data.get('fn2_5', 0) or 0
    features['FN2_10'] = data.get('fn2_10', 0) or 0

    # ========== 현금흐름/기타 기본 ==========
    features['FN3_1'] = data.get('fn3_1', 0) or 0
    features['FN3_2'] = data.get('fn3_2', 0) or 0
    features['FN3_7'] = data.get('fn3_7', 0) or 0
    features['FN3_8'] = data.get('fn3_8', 0) or 0
    features['FN3_11_1'] = data.get('fn3_11_1', 0) or 0

    # FN3_3: 부채상환계수 = 부채총계 / 영업활동현금흐름
    fn3_2 = data.get('fn3_2', 0) or 0
    fn1_19 = data.get('fn1_19', 0) or 0
    features['FN3_3'] = fn1_19 / (fn3_2 + eps) if fn3_2 > 0 else 0

    # FN3_4: 이자보상배율
    features['FN3_4'] = data.get('interest_coverage_ebit', 0)

    # FN3_6: 적립금비율 (이미 계산된 값 사용)
    features['FN3_6'] = data.get('fn3_6', 0) or 0

    features['FN3_10'] = 0  # 청산가치율 (계산 불가)
    features['FN3_11'] = data.get('net_working_capital', 0)

    # 변수 정의 (아래에서 사용)
    fn1_24 = data.get('fn1_24', 0) or 0

    # ========== 연체정보 ==========
    features['DA0D00021'] = data.get('da0d00029', 0) or 0
    features['DA0D00026'] = data.get('da0d00026', 0) or 0
    features['DA0D00029'] = data.get('da0d00029', 0) or 0
    features['DA0D00033_1'] = data.get('da0d00033_1', 0) or 0
    features['DA0D00035_1'] = data.get('da0d00035_1', 0) or 0
    features['DB0D00006'] = data.get('db0d00006', 0) or 0
    features['D2B000012'] = data.get('d2b000002', 0) or 0

    # ========== 안정성 비율 ==========
    features['R006'] = data.get('debt_ratio', 0)
    features['R007'] = data.get('equity_ratio', 0)
    features['R008'] = data.get('current_ratio', 0)
    features['R009'] = data.get('quick_ratio', 0)
    features['R012'] = data.get('borrowing_dependency', 0)
    features['N001'] = data.get('short_term_borrowing_dependency', 0)
    features['N002'] = features['FN3_11_1'] / (features['FN1_24'] + eps) if features['FN1_24'] > 0 else 0

    # ========== 수익성 비율 ==========
    fn2_1 = data.get('fn2_1', 0) or 0
    fn2_2 = data.get('fn2_2', 0) or 0
    fn2_10 = data.get('fn2_10', 0) or 0
    fn1_13 = data.get('fn1_13', 0) or 0

    features['R013'] = fn2_2 / (fn2_1 + eps) if fn2_1 > 0 else 0  # 매출원가율
    features['R015'] = data.get('operating_margin', 0)
    features['R016'] = fn2_10 / (fn2_1 + eps) if fn2_1 > 0 else 0  # 당기순이익률
    features['R018'] = data.get('roe', 0)
    features['R023'] = fn2_10 / (fn1_13 + eps) if fn1_13 > 0 else 0  # 총자산순이익률
    features['N004'] = data.get('roe', 0)  # 자기자본순이익률 = ROE
    features['N005'] = data.get('gross_margin', 0)

    # ========== 활동성 비율 ==========
    features['R019'] = data.get('receivable_turnover', 0)
    features['R020'] = data.get('inventory_turnover', 0)

    # 매입채무회전율 = 매출원가 / 매입채무
    fn1_17 = data.get('fn1_17', 0) or 0  # 매입채무
    features['R021'] = fn2_2 / (fn1_17 + eps) if fn1_17 > 0 else 0

    features['R022'] = data.get('total_capital_turnover', 0)
    features['N003'] = data.get('nwc_turnover', 0)
    features['N012'] = fn2_1 / (fn1_24 + eps) if fn1_24 > 0 else 0  # 총자본회전율

    # ========== 성장성 비율 ==========
    features['R001'] = data.get('asset_growth', 0)      # 총자산증가율
    features['R002'] = data.get('revenue_growth', 0)    # 매출액증가율
    features['R003'] = data.get('operating_income_growth', 0)  # 영업이익증가율
    features['R004'] = data.get('net_income_growth', 0)  # 당기순이익증가율
    features['R024'] = data.get('equity_growth', 0)      # 자본총계증가율 (유동자산 전기 없으므로 대체)
    features['R025'] = 0  # 유형자산증가율 (전기 데이터 없음)
    features['N007'] = 0  # EBITDA증가율 (전기 데이터 없음)

    # ========== 현금흐름/생산성 비율 ==========
    features['N006'] = data.get('ebitda_margin', 0)
    features['N008'] = data.get('ocf_margin', 0)
    features['N009'] = features['FN3_3']  # 부채상환계수
    features['N010'] = data.get('debt_to_ebitda', 0)
    features['N011'] = data.get('interest_coverage_ebit', 0)

    return features


def prepare_training_data(base_ym: int = 20210801) -> Tuple[str, str]:
    """
    원본 데이터 → 37개 입력 추출 → 70개 피처 생성 → Train/Test 분리

    Args:
        base_ym: 기준년월

    Returns:
        (train_path, test_path) 튜플
    """
    print("\n" + "=" * 60)
    print("STEP 1: 학습 데이터 준비 (70개 피처)")
    print("=" * 60)

    # 컬럼 매핑 로드
    with open(project_root / 'config' / 'columns_map.yaml', 'r', encoding='utf-8') as f:
        columns_map = yaml.safe_load(f)

    # 원본 데이터 로드
    raw_path = project_root / 'data' / 'raw' / '기업신용평가정보_합성데이터.csv'
    print(f"\n📂 원본 데이터 로딩: {raw_path.name}")

    try:
        df_raw = pd.read_csv(raw_path, encoding='cp949')
    except UnicodeDecodeError:
        df_raw = pd.read_csv(raw_path, encoding='utf-8')

    print(f"  - 전체 데이터: {len(df_raw):,}건")

    # 기준년월 필터링
    df_filtered = df_raw[df_raw['기준년월'] == base_ym].copy()
    print(f"  - 기준년월 {base_ym}: {len(df_filtered):,}건")

    # 타겟 컬럼 처리
    target_col_kr = '모형개발용Performance(향후1년내부도여부)'
    if target_col_kr not in df_filtered.columns:
        raise ValueError(f"타겟 컬럼 '{target_col_kr}'를 찾을 수 없습니다.")

    target_values = df_filtered[target_col_kr].values

    # 컬럼명 영문 변환 (소문자로 통일)
    rename_dict = {v: k.lower() for k, v in columns_map.items() if v in df_filtered.columns}
    df_renamed = df_filtered.rename(columns=rename_dict)

    print(f"  - 부도율: {np.mean(target_values)*100:.2f}%")

    # 37개 입력 컬럼 추출 (없는 컬럼은 0으로)
    print(f"\n🔍 37개 입력 컬럼 추출...")
    available_cols = [col for col in INPUT_37_COLUMNS if col in df_renamed.columns]
    missing_cols = [col for col in INPUT_37_COLUMNS if col not in df_renamed.columns]

    print(f"  - 사용 가능: {len(available_cols)}/{len(INPUT_37_COLUMNS)}")
    if missing_cols:
        print(f"  - 누락 ({len(missing_cols)}개): {missing_cols[:5]}...")
        for col in missing_cols:
            df_renamed[col] = 0

    # 70개 피처 생성
    print(f"\n🔧 70개 피처 생성 중...")
    features_list = []

    for idx, row in df_renamed.iterrows():
        if idx % 10000 == 0 and idx > 0:
            print(f"  - 진행: {idx:,}건 처리됨")

        # 37개 입력 추출
        input_dict = {col: row.get(col, 0) for col in INPUT_37_COLUMNS}

        # 파생 변수 생성
        derived = create_derived_features(input_dict)

        # 70개 피처 매핑
        features_70 = map_to_70_features(derived)
        features_list.append(features_70)

    df_70 = pd.DataFrame(features_list)
    df_70['default_yn'] = target_values

    # 결측치/무한값 처리
    df_70 = df_70.replace([np.inf, -np.inf], 0)
    df_70 = df_70.fillna(0)

    print(f"  ✅ 70개 피처 생성 완료: {df_70.shape}")

    # Train/Test 분리
    print(f"\n✂️ Train/Test 분리 (80:20)...")
    train_df, test_df = train_test_split(
        df_70,
        test_size=0.2,
        random_state=42,
        stratify=df_70['default_yn']
    )

    # 저장
    output_dir = project_root / 'data' / 'processed'
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / f'train_70features_{base_ym}.parquet'
    test_path = output_dir / f'test_70features_{base_ym}.parquet'

    train_df.to_parquet(train_path, index=False)
    test_df.to_parquet(test_path, index=False)

    print(f"\n✅ 데이터 준비 완료:")
    print(f"  - Train: {len(train_df):,}건 → {train_path.name}")
    print(f"  - Test:  {len(test_df):,}건 → {test_path.name}")
    print(f"  - 피처 수: {len(df_70.columns) - 1}개 (+ target)")

    return str(train_path), str(test_path)


def train_model(
    base_ym: int,
    train_path: str,
    model_type: str = 'catboost'
) -> dict:
    """모델 학습"""
    print("\n" + "=" * 60)
    print("STEP 2: 모델 학습")
    print("=" * 60)

    from ml.default_prediction.training.train import run_training_pipeline

    result = run_training_pipeline(
        base_ym=base_ym,
        data_path=train_path,
        model_type=model_type,
        experiment_name='default_prediction'
    )

    print(f"\n✅ 모델 학습 완료:")
    print(f"  - 모델: {result['model_type']}")
    print(f"  - AUC-ROC: {result['auc_roc']:.4f}")
    print(f"  - MLflow 버전: {result.get('model_version', 'N/A')}")

    return result


def main():
    """부도예측 모델 학습 파이프라인 실행"""
    parser = argparse.ArgumentParser(
        description="부도예측 모델 학습 파이프라인 (70개 피처)"
    )
    parser.add_argument(
        '--base-ym',
        type=int,
        default=20210801,
        help="학습에 사용할 기준년월 (예: 20210801)"
    )
    parser.add_argument(
        '--model-type',
        type=str,
        default='catboost',
        choices=['catboost', 'xgboost', 'lightgbm'],
        help="모델 타입"
    )
    parser.add_argument(
        '--skip-data-prep',
        action='store_true',
        help="데이터 준비 단계 건너뛰기 (이미 준비된 경우)"
    )
    args = parser.parse_args()

    start_time = datetime.now()

    try:
        print("\n" + "=" * 60)
        print("부도예측 모델 학습 파이프라인 (70개 피처)")
        print(f"시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Step 1: 데이터 준비
        if not args.skip_data_prep:
            train_path, test_path = prepare_training_data(args.base_ym)
        else:
            train_path = str(project_root / 'data' / 'processed' / f'train_70features_{args.base_ym}.parquet')
            print(f"\n⏭️ 데이터 준비 건너뜀 (--skip-data-prep)")

        # Step 2: 모델 학습
        result = train_model(
            base_ym=args.base_ym,
            train_path=train_path,
            model_type=args.model_type
        )

        # 완료
        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "=" * 60)
        print("✅ 파이프라인 완료!")
        print("=" * 60)
        print(f"\n소요 시간: {duration}")
        print(f"\n결과:")
        print(f"  - 피처 수: 70개")
        print(f"  - 모델: {result['model_type']}")
        print(f"  - AUC-ROC: {result['auc_roc']:.4f}")
        print(f"  - F1-Score: {result['f1_score']:.4f}")
        print(f"  - MLflow 버전: {result.get('model_version', 'N/A')}")

        return result

    except Exception as e:
        print(f"\n❌ 파이프라인 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
