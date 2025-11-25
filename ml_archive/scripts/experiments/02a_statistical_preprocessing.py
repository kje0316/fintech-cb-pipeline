"""
통계적 전처리 (159개 전체 피처 대상)

변경 사항:
- 기존: 48개 경험적 선택 후 전처리
- 신규: 159개 전체를 통계적으로 전처리

작업 내용:
1. 타겟 변수 분리
2. 컬럼 타입 분류 (식별자, 범주형, 수치형)
3. 결측치 처리
   - NULL 70% 이상: 제거
   - 수치형: 중위값 대체
   - 범주형: 최빈값 대체
4. 범주형 인코딩 (LabelEncoder)
5. 무한대/NaN 처리

출력:
- ml/data/preprocessed_data_20210801.parquet
- ml/data/preprocessing_metadata.pkl (인코더, 통계)

실행:
    python ml/scripts/02a_statistical_preprocessing.py
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import pickle

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.preprocessing import LabelEncoder


def statistical_preprocessing(input_path=None, output_path=None):
    """
    통계적 전처리 (159개 전체 대상)

    Args:
        input_path: 입력 파일 경로 (기본: ml/data/raw_data_full_20210801.parquet)
        output_path: 출력 파일 경로 (기본: ml/data/preprocessed_data_20210801.parquet)

    Returns:
        X: 전처리된 피처 DataFrame
        y: 타겟 Series
        metadata: 전처리 메타데이터 dict
    """

    # 경로 설정
    if input_path is None:
        input_path = PROJECT_ROOT / "ml/data/raw_data_full_20210801.parquet"
    if output_path is None:
        output_path = PROJECT_ROOT / "ml/data/preprocessed_data_20210801.parquet"

    print("="*80)
    print(" 통계적 전처리 시작 (159개 전체 피처)")
    print("="*80)
    print()

    # 1. 데이터 로드
    print(f"✓ 데이터 로드 중... ({input_path})")
    df = pd.read_parquet(input_path)
    print(f"  원본 데이터: {df.shape[0]:,}행 × {df.shape[1]}개 컬럼")
    print()

    # 2. 타겟 변수 분리
    print("-"*80)
    print(" [1/5] 타겟 변수 분리")
    print("-"*80)

    target_col = 'perf_12m'  # 부도 여부 (0/1)
    additional_target = 'corp_grad'  # 신용등급 (보조 타겟)

    if target_col not in df.columns:
        raise ValueError(f"타겟 변수 '{target_col}'가 없습니다!")

    # 문자열 타입이면 숫자로 변환
    if df[target_col].dtype == 'object':
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce')

    y = df[target_col].copy()

    if additional_target in df.columns:
        if df[additional_target].dtype == 'object':
            df[additional_target] = pd.to_numeric(df[additional_target], errors='coerce')
        credit_grade = df[additional_target].copy()
    else:
        credit_grade = None

    # 타겟 제외
    X = df.drop(columns=[col for col in [target_col, additional_target] if col in df.columns])

    print(f"  타겟 변수: {target_col}")
    print(f"  부도율: {y.mean()*100:.2f}%")
    print(f"  피처 개수: {X.shape[1]}개")
    print()

    # 3. 컬럼 타입 분류
    print("-"*80)
    print(" [2/5] 컬럼 타입 분류")
    print("-"*80)

    # 식별자 컬럼 (제거 대상) - 소문자로 비교
    id_cols = []
    for col in X.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['id', '_id', 'company_sk', 'time_sk']):
            id_cols.append(col)

    # 날짜 컬럼 (제거 대상) - 소문자로 비교
    date_cols = []
    for col in X.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['_dt', 'bs_dt', 'date']):
            date_cols.append(col)

    # 범주형 컬럼
    categorical_cols = []
    for col in X.columns:
        if X[col].dtype == 'object':
            categorical_cols.append(col)
        elif col.lower() in ['sic_cd_3', 'wg_gb', 'ct_cnty_gu_cd']:
            categorical_cols.append(col)

    # 수치형 컬럼
    exclude_cols = id_cols + date_cols + categorical_cols
    numeric_cols = [col for col in X.columns if col not in exclude_cols]

    print(f"  식별자 컬럼: {len(id_cols)}개 (제거 예정)")
    if id_cols:
        print(f"    {id_cols[:5]}")
    print(f"  날짜 컬럼: {len(date_cols)}개 (제거 예정)")
    if date_cols:
        print(f"    {date_cols[:5]}")
    print(f"  범주형 컬럼: {len(categorical_cols)}개")
    if categorical_cols:
        print(f"    {categorical_cols}")
    print(f"  수치형 컬럼: {len(numeric_cols)}개")
    print()

    # 식별자/날짜 컬럼 제거
    X = X.drop(columns=id_cols + date_cols)
    numeric_cols = [c for c in numeric_cols if c not in id_cols + date_cols]

    print(f"  제거 후: {X.shape[1]}개 컬럼")
    print()

    # 4. 결측치 처리
    print("-"*80)
    print(" [3/5] 결측치 처리")
    print("-"*80)

    # 4-1. NULL 70% 이상 컬럼 제거
    null_ratio = X.isnull().mean()
    high_null_cols = null_ratio[null_ratio >= 0.7].index.tolist()

    if high_null_cols:
        print(f"  NULL 70% 이상 컬럼 ({len(high_null_cols)}개 제거):")
        for col in high_null_cols[:10]:
            print(f"    - {col}: {null_ratio[col]*100:.1f}%")
        if len(high_null_cols) > 10:
            print(f"    ... 외 {len(high_null_cols)-10}개")

        X = X.drop(columns=high_null_cols)
        numeric_cols = [c for c in numeric_cols if c not in high_null_cols]
        categorical_cols = [c for c in categorical_cols if c not in high_null_cols]
        print()

    # 4-2. 수치형: 중위값 대체
    imputed_count = 0
    for col in numeric_cols:
        if col in X.columns and X[col].isnull().sum() > 0:
            median_val = X[col].median()
            null_count = X[col].isnull().sum()
            X[col] = X[col].fillna(median_val)
            imputed_count += 1
            if imputed_count <= 5:  # 처음 5개만 출력
                print(f"  {col}: {null_count}개 중위값({median_val:.2f}) 대체")

    if imputed_count > 5:
        print(f"  ... 외 {imputed_count-5}개 컬럼")
    print()

    # 4-3. 범주형: 최빈값 대체
    for col in categorical_cols:
        if col in X.columns and X[col].isnull().sum() > 0:
            mode_val = X[col].mode()[0] if len(X[col].mode()) > 0 else 'UNKNOWN'
            null_count = X[col].isnull().sum()
            X[col] = X[col].fillna(mode_val)
            print(f"  {col}: {null_count}개 최빈값({mode_val}) 대체")
    print()

    # 5. 범주형 인코딩
    print("-"*80)
    print(" [4/5] 범주형 인코딩 (LabelEncoder)")
    print("-"*80)

    le_dict = {}
    for col in categorical_cols:
        if col in X.columns:
            le = LabelEncoder()
            # 문자열로 변환 후 인코딩
            X[col] = X[col].astype(str)
            X[col] = le.fit_transform(X[col])
            le_dict[col] = le

            print(f"  {col}: {len(le.classes_)}개 클래스 → 0-{len(le.classes_)-1}")
            if len(le.classes_) <= 10:
                print(f"    클래스: {le.classes_[:10].tolist()}")
    print()

    # 6. 무한대/NaN 최종 처리
    print("-"*80)
    print(" [5/5] 무한대/NaN 최종 처리")
    print("-"*80)

    # 무한대를 NaN으로 변환
    inf_count = np.isinf(X.select_dtypes(include=[np.number])).sum().sum()
    if inf_count > 0:
        print(f"  무한대 값 발견: {inf_count}개")
        X = X.replace([np.inf, -np.inf], np.nan)

    # 남은 NaN을 중위값으로 대체
    remaining_nan = X.isnull().sum().sum()
    if remaining_nan > 0:
        print(f"  남은 NaN: {remaining_nan}개 → 중위값 대체")
        for col in X.columns:
            if X[col].isnull().sum() > 0:
                X[col] = X[col].fillna(X[col].median())

    final_nan = X.isnull().sum().sum()
    print(f"  최종 결측치: {final_nan}개")
    print()

    # 7. 최종 요약
    print("="*80)
    print(" 전처리 완료")
    print("="*80)
    print(f"  입력: {df.shape}")
    print(f"  출력: {X.shape} (피처) + {y.shape} (타겟)")
    print(f"  제거된 컬럼: {df.shape[1] - X.shape[1] - 1}개")  # -1 for target
    print(f"  범주형 인코딩: {len(le_dict)}개")
    print(f"  결측치: {final_nan}개 (0개 달성)")
    print()

    # 8. 저장
    # 8-1. 데이터 저장
    output_df = X.copy()
    output_df['default_yn'] = y  # 타겟 추가
    if credit_grade is not None:
        output_df['credit_grade'] = credit_grade

    print(f"✓ 전처리 데이터 저장 중... ({output_path})")
    output_df.to_parquet(output_path, index=False, compression='snappy')
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  저장 완료: {file_size_mb:.2f} MB")
    print()

    # 8-2. 메타데이터 저장
    metadata = {
        'label_encoders': le_dict,
        'numeric_cols': numeric_cols,
        'categorical_cols': categorical_cols,
        'removed_cols': id_cols + date_cols + high_null_cols,
        'shape': X.shape,
        'target_col': target_col,
        'default_rate': y.mean()
    }

    metadata_path = PROJECT_ROOT / "ml/data/preprocessing_metadata.pkl"
    print(f"✓ 메타데이터 저장 중... ({metadata_path})")
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    print("  저장 완료")
    print()

    print("다음 단계:")
    print("  python ml/scripts/02b_statistical_feature_selection.py")
    print()

    return X, y, metadata


if __name__ == '__main__':
    X, y, metadata = statistical_preprocessing()

    print("전처리 결과 미리보기:")
    print(f"  피처 shape: {X.shape}")
    print(f"  타겟 shape: {y.shape}")
    print(f"  수치형 컬럼: {len(metadata['numeric_cols'])}개")
    print(f"  범주형 컬럼: {len(metadata['categorical_cols'])}개")
