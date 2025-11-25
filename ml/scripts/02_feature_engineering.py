"""
부도 예측 모델 - 피처 엔지니어링 스크립트

EDA 결과를 바탕으로 모델 학습에 사용할 피처 준비:
1. 결측치 처리
2. 이상치 처리
3. 파생 피처 생성
4. 범주형 피처 인코딩
5. 피처 선택
6. 피처 스케일링

입력: ml/data/raw_data_20210801.parquet
출력: ml/data/processed_data_20210801.parquet

실행:
    python ml/scripts/02_feature_engineering.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.preprocessing import StandardScaler, LabelEncoder


def load_data(data_path):
    """데이터 로드"""
    print("="*80)
    print(" 데이터 로드")
    print("="*80)

    df = pd.read_parquet(data_path)
    print(f"✓ 데이터 로드 완료: {len(df):,}행 × {len(df.columns)}열")
    print(f"✓ 부도율: {df['default_yn'].mean() * 100:.2f}%")

    return df


def handle_missing_values(df):
    """결측치 처리"""
    print("\n" + "="*80)
    print(" 결측치 처리")
    print("="*80)

    # 결측치 분석
    missing_stats = pd.DataFrame({
        '결측수': df.isnull().sum(),
        '결측률(%)': df.isnull().sum() / len(df) * 100
    }).sort_values('결측률(%)', ascending=False)

    print("결측치 통계 (결측률 > 0):")
    high_missing = missing_stats[missing_stats['결측률(%)'] > 0]
    if len(high_missing) > 0:
        print(high_missing)
    else:
        print("✓ 결측치 없음")

    # 결측률 70% 이상 컬럼 삭제
    high_missing_cols = missing_stats[missing_stats['결측률(%)'] >= 70].index.tolist()
    if len(high_missing_cols) > 0:
        print(f"\n결측률 70% 이상 컬럼 삭제: {high_missing_cols}")
        df = df.drop(columns=high_missing_cols)

    # 나머지 결측치: 중위값으로 대체
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    missing_count = 0
    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            missing_count += 1

    print(f"\n✓ {missing_count}개 컬럼 결측치 중위값 대체 완료")
    print(f"✓ 전체 결측치: {df.isnull().sum().sum()}개")

    return df


def handle_outliers(df):
    """이상치 처리"""
    print("\n" + "="*80)
    print(" 이상치 처리 (IQR 기반)")
    print("="*80)

    # 재무비율 컬럼 선택
    ratio_cols = [col for col in df.columns if any(x in col for x in
                  ['ratio', 'margin', 'roe', 'roa', 'turnover', 'growth', 'dependency'])]

    outlier_counts = {}

    for col in ratio_cols:
        if col in df.columns and df[col].dtype in [np.float64, np.int64]:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
            outlier_count = outliers.sum()

            if outlier_count > 0:
                outlier_counts[col] = outlier_count
                # 이상치를 중위값으로 대체
                median_val = df[col].median()
                df.loc[outliers, col] = median_val

    print(f"이상치 처리 결과 (Top 10):")
    for col, count in sorted(outlier_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {col}: {count:,}개")

    print(f"\n✓ 총 {sum(outlier_counts.values()):,}개 이상치 처리 완료")

    return df


def create_derived_features(df):
    """파생 피처 생성"""
    print("\n" + "="*80)
    print(" 파생 피처 생성")
    print("="*80)

    # 1. 현금/부채 비율
    df['cash_to_debt'] = df['operating_cashflow'] / (df['total_debt'] + 1e-6)
    df['cash_to_debt'] = df['cash_to_debt'].replace([np.inf, -np.inf], 0)

    # 2. EBITDA (영업이익)
    df['ebitda'] = df['operating_income']

    # 3. 이자보상배율
    df['interest_coverage'] = df['operating_income'] / (df['interest_expense'] + 1e-6)
    df['interest_coverage'] = df['interest_coverage'].replace([np.inf, -np.inf], 0)

    # 4. 순운전자본
    df['net_working_capital'] = df['current_asset'] - df['current_liability']

    # 5. 순운전자본/총자산
    df['nwc_to_total_asset'] = df['net_working_capital'] / (df['total_asset'] + 1e-6)
    df['nwc_to_total_asset'] = df['nwc_to_total_asset'].replace([np.inf, -np.inf], 0)

    # 6. 복합 성장률
    df['composite_growth'] = (df['total_asset_growth'] + df['revenue_growth']) / 2

    # 7. 차입금 의존도
    df['borrowing_ratio'] = df['borrowings'] / (df['total_asset'] + 1e-6)
    df['borrowing_ratio'] = df['borrowing_ratio'].replace([np.inf, -np.inf], 0)

    # 8. 공공신용정보 이벤트 여부
    df['has_credit_event_1'] = (df['public_credit_event_1'] != 999999999).astype(int)
    df['has_credit_event_2'] = (df['public_credit_event_2'] != 999999999).astype(int)

    # 9. 재고자산/유동자산 비율
    df['inventory_to_current_asset'] = df['inventory'] / (df['current_asset'] + 1e-6)
    df['inventory_to_current_asset'] = df['inventory_to_current_asset'].replace([np.inf, -np.inf], 0)

    # 10. 부채/자본 비율
    df['debt_to_equity'] = df['total_debt'] / (df['total_equity'] + 1e-6)
    df['debt_to_equity'] = df['debt_to_equity'].replace([np.inf, -np.inf], 0)

    print("생성된 파생 피처:")
    print("  1. cash_to_debt - 현금/부채 비율")
    print("  2. ebitda - 영업이익")
    print("  3. interest_coverage - 이자보상배율")
    print("  4. net_working_capital - 순운전자본")
    print("  5. nwc_to_total_asset - 순운전자본/총자산")
    print("  6. composite_growth - 복합 성장률")
    print("  7. borrowing_ratio - 차입금 의존도")
    print("  8. has_credit_event_1/2 - 공공신용이벤트 여부")
    print("  9. inventory_to_current_asset - 재고/유동자산")
    print(" 10. debt_to_equity - 부채/자본")

    print(f"\n✓ 총 {len(df.columns)}개 컬럼 (원본 대비 +10개)")

    return df


def encode_categorical_features(df):
    """범주형 피처 인코딩"""
    print("\n" + "="*80)
    print(" 범주형 피처 인코딩")
    print("="*80)

    categorical_cols = ['industry_code', 'audit_status', 'region']

    # LabelEncoder 사용
    for col in categorical_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            print(f"✓ {col} 인코딩 완료: {len(le.classes_)}개 클래스")

    return df


def select_features(df):
    """피처 선택"""
    print("\n" + "="*80)
    print(" 피처 선택")
    print("="*80)

    # 피처와 타겟 분리
    X = df.drop(columns=['default_yn', 'base_date', 'public_credit_event_1', 'public_credit_event_2'])
    y = df['default_yn']

    print(f"초기 피처 개수: {X.shape[1]}개")

    # 1. 분산이 거의 없는 피처 제거
    low_var_cols = []
    for col in X.columns:
        if X[col].std() < 0.01:
            low_var_cols.append(col)

    if len(low_var_cols) > 0:
        print(f"\n분산 낮은 피처 제거 ({len(low_var_cols)}개): {low_var_cols}")
        X = X.drop(columns=low_var_cols)

    # 2. 타겟과 상관관계 분석
    correlations = X.corrwith(y).abs().sort_values(ascending=False)

    print("\n타겟과 상관관계 Top 15:")
    for feature, corr in correlations.head(15).items():
        print(f"  {feature}: {corr:.4f}")

    # 상관관계 낮은 피처 제거 (|corr| < 0.005)
    low_corr_cols = correlations[correlations < 0.005].index.tolist()
    if len(low_corr_cols) > 0:
        print(f"\n상관관계 낮은 피처 제거 ({len(low_corr_cols)}개)")
        X = X.drop(columns=low_corr_cols)

    print(f"\n✓ 최종 피처 개수: {X.shape[1]}개")

    # 타겟 변수 다시 추가
    X['default_yn'] = y

    return X


def scale_features(df):
    """피처 스케일링"""
    print("\n" + "="*80)
    print(" 피처 스케일링 (StandardScaler)")
    print("="*80)

    # 피처와 타겟 분리
    X = df.drop(columns=['default_yn'])
    y = df['default_yn']

    # StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

    print(f"✓ 피처 스케일링 완료")
    print(f"  평균: {X_scaled.mean().mean():.6f}")
    print(f"  표준편차: {X_scaled.std().mean():.6f}")

    # 타겟 변수 다시 추가
    X_scaled['default_yn'] = y

    return X_scaled


def save_processed_data(df, output_path):
    """전처리된 데이터 저장"""
    print("\n" + "="*80)
    print(" 전처리 데이터 저장")
    print("="*80)

    # Parquet 저장
    df.to_parquet(output_path, index=False, compression='snappy')

    # 파일 크기 확인
    file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)

    print(f"✓ 저장 완료: {output_path}")
    print(f"  - 행 수: {len(df):,}")
    print(f"  - 피처 개수: {len(df.columns) - 1}")
    print(f"  - 파일 크기: {file_size_mb:.2f} MB")
    print(f"  - 부도율: {df['default_yn'].mean() * 100:.2f}%")


def main():
    """메인 실행 함수"""

    print("="*80)
    print(" 부도 예측 모델 - 피처 엔지니어링")
    print("="*80)
    print()

    # 입출력 경로
    input_path = PROJECT_ROOT / 'ml/data/raw_data_20210801.parquet'
    output_path = PROJECT_ROOT / 'ml/data/processed_data_20210801.parquet'

    # 1. 데이터 로드
    df = load_data(input_path)

    # 2. 결측치 처리
    df = handle_missing_values(df)

    # 3. 이상치 처리
    df = handle_outliers(df)

    # 4. 파생 피처 생성
    df = create_derived_features(df)

    # 5. 범주형 피처 인코딩
    df = encode_categorical_features(df)

    # 6. 피처 선택
    df = select_features(df)

    # 7. 피처 스케일링
    df = scale_features(df)

    # 8. 저장
    save_processed_data(df, output_path)

    print("\n" + "="*80)
    print(" 피처 엔지니어링 완료!")
    print("="*80)
    print(f"\n다음 단계:")
    print(f"  python ml/scripts/02_train_default_model.py")
    print()


if __name__ == '__main__':
    main()
