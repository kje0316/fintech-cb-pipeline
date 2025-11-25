"""
파생 변수 생성 (통계적으로 선택된 피처 기반)

입력: ml/data/validated_features.csv (도메인 검증 완료)
출력: ml/data/engineered_features_20210801.parquet

작업:
1. 검증된 피처 로드
2. 파생 변수 생성 (10개)
3. 최종 스케일링
4. 저장

실행:
    python ml/scripts/03_feature_engineering.py
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import pickle

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.preprocessing import StandardScaler


def create_derived_features(df, validated_features):
    """
    파생 변수 생성

    Args:
        df: 전처리된 데이터프레임
        validated_features: 검증된 피처 리스트

    Returns:
        df_engineered: 파생 변수가 추가된 데이터프레임
    """
    print("="*80)
    print(" 파생 변수 생성")
    print("="*80)
    print()

    df_engineered = df[validated_features].copy()

    derived_count = 0

    # 파생 변수 생성 (필요한 원본 피처가 있을 때만) - 소문자 컬럼명 사용
    # 1. cash_to_debt
    if 'fn3_2' in df.columns and 'fn1_19' in df.columns:
        df_engineered['cash_to_debt'] = df['fn3_2'] / (df['fn1_19'] + 1e-6)
        derived_count += 1
        print(f"  ✓ cash_to_debt 생성 (영업현금흐름/부채)")

    # 2. debt_to_equity
    if 'fn1_19' in df.columns and 'fn1_24' in df.columns:
        df_engineered['debt_to_equity'] = df['fn1_19'] / (df['fn1_24'] + 1e-6)
        derived_count += 1
        print(f"  ✓ debt_to_equity 생성 (부채/자본)")

    # 3. interest_coverage
    if 'fn2_5' in df.columns and 'fn2_4' in df.columns:
        df_engineered['interest_coverage'] = df['fn2_5'] / (df['fn2_4'] + 1e-6)
        derived_count += 1
        print(f"  ✓ interest_coverage 생성 (영업이익/이자비용)")

    # 4. net_working_capital
    if 'fn1_1' in df.columns and 'fn1_14' in df.columns:
        df_engineered['net_working_capital'] = df['fn1_1'] - df['fn1_14']
        derived_count += 1
        print(f"  ✓ net_working_capital 생성 (유동자산-유동부채)")

    # 5. nwc_to_total_asset
    if 'net_working_capital' in df_engineered.columns and 'fn1_13' in df.columns:
        df_engineered['nwc_to_total_asset'] = df_engineered['net_working_capital'] / (df['fn1_13'] + 1e-6)
        derived_count += 1
        print(f"  ✓ nwc_to_total_asset 생성 (순운전자본/총자산)")

    # 6. composite_growth
    if 'r001' in df.columns and 'r002' in df.columns:
        df_engineered['composite_growth'] = (df['r001'] + df['r002']) / 2
        derived_count += 1
        print(f"  ✓ composite_growth 생성 (자산+매출 증가율)")

    # 7. borrowing_ratio
    if 'fn1_16' in df.columns and 'fn1_13' in df.columns:
        df_engineered['borrowing_ratio'] = df['fn1_16'] / (df['fn1_13'] + 1e-6)
        derived_count += 1
        print(f"  ✓ borrowing_ratio 생성 (차입금/총자산)")

    # 8-9. has_credit_event
    if 'd2b000002' in df.columns:
        df_engineered['has_credit_event_1'] = (df['d2b000002'] != 999999999).astype(int)
        derived_count += 1
        print(f"  ✓ has_credit_event_1 생성 (공공신용이벤트)")

    if 'd2b000003' in df.columns:
        df_engineered['has_credit_event_2'] = (df['d2b000003'] != 999999999).astype(int)
        derived_count += 1
        print(f"  ✓ has_credit_event_2 생성 (공공신용이벤트)")

    # 10. inventory_to_current_asset
    if 'fn1_4' in df.columns and 'fn1_1' in df.columns:
        df_engineered['inventory_to_current_asset'] = df['fn1_4'] / (df['fn1_1'] + 1e-6)
        derived_count += 1
        print(f"  ✓ inventory_to_current_asset 생성 (재고/유동자산)")

    print()
    print(f"  총 {derived_count}개 파생 변수 생성")
    print(f"  최종 피처 개수: {df_engineered.shape[1]}개")
    print()

    # 무한대/NaN 처리
    df_engineered = df_engineered.replace([np.inf, -np.inf], np.nan)
    nan_count = df_engineered.isnull().sum().sum()
    if nan_count > 0:
        print(f"  ⚠️  파생 변수 생성 중 NaN 발생: {nan_count}개")
        print(f"     중위값으로 대체 중...")
        for col in df_engineered.columns:
            if df_engineered[col].isnull().sum() > 0:
                df_engineered[col] = df_engineered[col].fillna(df_engineered[col].median())
        print(f"  ✓ 대체 완료")
        print()

    return df_engineered


def scale_features(df, target_col='default_yn'):
    """
    피처 스케일링 (StandardScaler)

    Args:
        df: 피처 데이터프레임
        target_col: 타겟 변수 컬럼명

    Returns:
        df_scaled: 스케일링된 데이터프레임
        scaler: 학습된 스케일러 객체
    """
    print("="*80)
    print(" 피처 스케일링 (StandardScaler)")
    print("="*80)
    print()

    # 타겟 분리
    if target_col in df.columns:
        y = df[target_col].copy()
        X = df.drop(columns=[target_col])
    else:
        y = None
        X = df.copy()

    # 스케일링 (수치형만)
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()

    print(f"  수치형 피처: {len(numeric_cols)}개")

    scaler = StandardScaler()
    X_scaled = X.copy()
    X_scaled[numeric_cols] = scaler.fit_transform(X[numeric_cols])

    print(f"  ✓ StandardScaler 적용 완료")
    print(f"     평균: 0, 표준편차: 1로 변환")
    print()

    # 타겟 다시 추가
    if y is not None:
        X_scaled[target_col] = y

    return X_scaled, scaler


def feature_engineering_pipeline():
    """
    전체 피처 엔지니어링 파이프라인
    """
    print("\n")
    print("="*80)
    print("  파생 변수 생성 및 스케일링")
    print("="*80)
    print()

    # 1. 검증된 피처 로드
    print("✓ 검증된 피처 로드 중...")
    validated_path = PROJECT_ROOT / "ml/data/validated_features.csv"
    validated_df = pd.read_csv(validated_path)
    validated_features = validated_df['feature'].tolist()
    print(f"  검증된 피처: {len(validated_features)}개")
    print()

    # 2. 전처리된 데이터 로드
    print("✓ 전처리 데이터 로드 중...")
    preprocessed_path = PROJECT_ROOT / "ml/data/preprocessed_data_20210801.parquet"
    df = pd.read_parquet(preprocessed_path)
    print(f"  데이터: {df.shape[0]:,}행 × {df.shape[1]}개 컬럼")
    print()

    # 3. 타겟 변수 확인
    target_col = 'default_yn'
    if target_col in df.columns:
        y = df[target_col].copy()
        print(f"  타겟 변수: {target_col}")
        print(f"  부도율: {y.mean()*100:.2f}%")
    else:
        raise ValueError(f"타겟 변수 '{target_col}'가 없습니다!")

    # 신용등급도 보존
    credit_grade = df['credit_grade'].copy() if 'credit_grade' in df.columns else None

    print()

    # 4. 파생 변수 생성
    df_engineered = create_derived_features(df, validated_features)

    # 타겟 추가
    df_engineered[target_col] = y
    if credit_grade is not None:
        df_engineered['credit_grade'] = credit_grade

    # 5. 스케일링
    df_scaled, scaler = scale_features(df_engineered, target_col=target_col)

    # 6. 저장
    print("="*80)
    print(" 저장")
    print("="*80)
    print()

    # 6-1. 엔지니어링된 데이터 저장
    output_path = PROJECT_ROOT / "ml/data/engineered_features_20210801.parquet"
    df_scaled.to_parquet(output_path, index=False, compression='snappy')
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ 피처 데이터 저장: {output_path}")
    print(f"     크기: {file_size_mb:.2f} MB")
    print(f"     Shape: {df_scaled.shape}")
    print()

    # 6-2. Scaler 저장
    scaler_path = PROJECT_ROOT / "ml/data/feature_scaler.pkl"
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"  ✓ Scaler 저장: {scaler_path}")
    print()

    # 7. 최종 요약
    print("="*80)
    print(" 완료!")
    print("="*80)
    print()
    print(f"  입력: {len(validated_features)}개 검증된 피처")
    print(f"  출력: {df_scaled.shape[1]-1}개 피처 (타겟 제외)")
    print(f"     - 원본: {len(validated_features)}개")
    print(f"     - 파생: {df_scaled.shape[1]-1-len(validated_features)}개")
    print()
    print("  생성 파일:")
    print("    ✓ ml/data/engineered_features_20210801.parquet")
    print("    ✓ ml/data/feature_scaler.pkl")
    print()
    print("  다음 단계:")
    print("    python ml/scripts/04_train_default_model.py")
    print()

    return df_scaled, scaler


if __name__ == '__main__':
    df_scaled, scaler = feature_engineering_pipeline()

    print("\n피처 엔지니어링 결과:")
    print(f"  최종 shape: {df_scaled.shape}")
    print(f"  컬럼 목록 (처음 10개):")
    for i, col in enumerate(df_scaled.columns[:10], 1):
        print(f"    {i:2d}. {col}")
    if len(df_scaled.columns) > 10:
        print(f"    ... 외 {len(df_scaled.columns)-10}개")
