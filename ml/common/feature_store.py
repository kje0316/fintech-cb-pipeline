"""
Feature Store 데이터 로더

ML 모델 학습/추론용 Feature Store에서 데이터를 로드하는 공통 모듈

Usage:
    from ml.common.feature_store import load_from_feature_store

    # 전체 데이터 로드
    df = load_from_feature_store()

    # 특정 기준년월만 로드
    df = load_from_feature_store(base_ym=20210801)

    # 여러 기준년월 로드
    df = load_from_feature_store(base_ym=[20210801, 20210901])
"""
import sys
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import DB_URL
from sqlalchemy import create_engine, text


# Feature Store 테이블 정보
FEATURE_STORE_SCHEMA = "marts"
FEATURE_STORE_TABLE = "mart_feature_store_ml"
METADATA_TABLE = "mart_feature_store_metadata"

# 70개 ML 피처 컬럼 (부도예측 + 클러스터링 공통)
FEATURE_COLUMNS = [
    # 재무상태표 (10개)
    'fn1_13', 'fn1_1', 'fn1_4', 'fn1_11', 'fn1_14', 'fn1_15',
    'fn1_16', 'fn1_19', 'fn1_20', 'fn1_24',
    # 손익계산서 (4개)
    'fn2_1', 'fn2_2_1', 'fn2_5', 'fn2_10',
    # 현금흐름 (10개)
    'fn3_1', 'fn3_2', 'fn3_3', 'fn3_4', 'fn3_6', 'fn3_7',
    'fn3_8', 'fn3_10', 'fn3_11', 'fn3_11_1',
    # 연체정보 (7개)
    'da0d00021', 'da0d00026', 'da0d00029', 'da0d00033_1',
    'da0d00035_1', 'db0d00006', 'd2b000012',
    # 안정성 비율 (7개)
    'r006', 'r007', 'r008', 'r009', 'r012', 'n001', 'n002',
    # 수익성 비율 (7개)
    'r013', 'r015', 'r016', 'r018', 'r023', 'n004', 'n005',
    # 활동성 비율 (6개)
    'r019', 'r020', 'r021', 'r022', 'n003', 'n012',
    # 성장성 비율 (8개)
    'r001', 'r002', 'r003', 'r004', 'r024', 'r025', 'n007',
    # 현금흐름 비율 (5개)
    'n006', 'n008', 'n009', 'n010', 'n011',
]

# 메타 컬럼
META_COLUMNS = ['base_ym', 'company_id', 'sic_cd_3']
TARGET_COLUMNS = ['default_yn', 'cluster_id']


def get_engine():
    """SQLAlchemy 엔진 생성"""
    return create_engine(DB_URL, echo=False, future=True)


def load_from_feature_store(
    base_ym: Optional[Union[int, List[int]]] = None,
    include_target: bool = True,
    features_only: bool = False,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """
    Feature Store에서 ML 학습/추론용 데이터 로드

    Args:
        base_ym: 기준년월 필터 (단일 값 또는 리스트). None이면 전체 로드
        include_target: 타겟 컬럼(default_yn, cluster_id) 포함 여부
        features_only: True면 피처 컬럼만 반환 (메타 제외)
        limit: 로드할 최대 행 수 (테스트/디버깅용)

    Returns:
        DataFrame with ML features
    """
    print(f"📂 Feature Store에서 데이터 로드 중...")

    engine = get_engine()

    # 컬럼 선택
    if features_only:
        columns = FEATURE_COLUMNS
    else:
        columns = META_COLUMNS + FEATURE_COLUMNS
        if include_target:
            columns = columns + TARGET_COLUMNS

    columns_str = ', '.join(columns)

    # 쿼리 생성
    query = f"SELECT {columns_str} FROM {FEATURE_STORE_SCHEMA}.{FEATURE_STORE_TABLE}"

    # 기준년월 필터
    params = {}
    if base_ym is not None:
        if isinstance(base_ym, (list, tuple)):
            placeholders = ', '.join([f':ym{i}' for i in range(len(base_ym))])
            query += f" WHERE base_ym IN ({placeholders})"
            for i, ym in enumerate(base_ym):
                params[f'ym{i}'] = int(ym)
        else:
            query += " WHERE base_ym = :base_ym"
            params['base_ym'] = int(base_ym)

    # 정렬
    query += " ORDER BY base_ym, company_id"

    # 제한
    if limit:
        query += f" LIMIT {int(limit)}"

    # 파라미터 바인딩 (직접 치환)
    for key, value in params.items():
        query = query.replace(f':{key}', str(value))

    # 데이터 로드 (raw connection 사용)
    raw_conn = engine.raw_connection()
    try:
        df = pd.read_sql(query, raw_conn)
    finally:
        raw_conn.close()

    print(f"✅ 데이터 로드 완료: {len(df):,}건, {len(df.columns)}개 컬럼")

    if base_ym is not None:
        if isinstance(base_ym, (list, tuple)):
            print(f"   - 기준년월: {base_ym}")
        else:
            print(f"   - 기준년월: {base_ym}")

    return df


def get_available_base_yms() -> List[int]:
    """Feature Store에서 사용 가능한 기준년월 목록 조회"""
    engine = get_engine()

    query = f"""
        SELECT DISTINCT base_ym
        FROM {FEATURE_STORE_SCHEMA}.{FEATURE_STORE_TABLE}
        ORDER BY base_ym
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [row[0] for row in result]


def get_feature_store_stats() -> pd.DataFrame:
    """Feature Store 메타데이터 통계 조회"""
    engine = get_engine()

    query = f"""
        SELECT
            base_ym,
            total_companies,
            default_count,
            default_rate,
            null_ratio,
            used_for_training,
            updated_at
        FROM {FEATURE_STORE_SCHEMA}.{METADATA_TABLE}
        ORDER BY base_ym
    """

    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def load_train_test_split(
    train_base_yms: List[int],
    test_base_yms: List[int],
    target_col: str = 'default_yn'
) -> tuple:
    """
    기준년월 기반 Train/Test 분할 데이터 로드

    Args:
        train_base_yms: 학습용 기준년월 리스트
        test_base_yms: 테스트용 기준년월 리스트
        target_col: 타겟 컬럼명

    Returns:
        (X_train, X_test, y_train, y_test) 튜플
    """
    print(f"\n📊 Train/Test 데이터 분할 로드")
    print(f"   - Train 기준년월: {train_base_yms}")
    print(f"   - Test 기준년월: {test_base_yms}")

    # 데이터 로드
    train_df = load_from_feature_store(base_ym=train_base_yms, include_target=True)
    test_df = load_from_feature_store(base_ym=test_base_yms, include_target=True)

    # X, y 분리
    X_train = train_df[FEATURE_COLUMNS].copy()
    X_test = test_df[FEATURE_COLUMNS].copy()
    y_train = train_df[target_col].copy()
    y_test = test_df[target_col].copy()

    print(f"\n✅ 분할 완료:")
    print(f"   - Train: {len(X_train):,}건 (부도율: {y_train.mean():.4f})")
    print(f"   - Test:  {len(X_test):,}건 (부도율: {y_test.mean():.4f})")

    return X_train, X_test, y_train, y_test


def mark_as_used_for_training(base_yms: List[int], model_version: str = None):
    """학습에 사용된 기준년월 표시"""
    engine = get_engine()

    with engine.begin() as conn:
        for ym in base_yms:
            conn.execute(text(f"""
                UPDATE {FEATURE_STORE_SCHEMA}.{METADATA_TABLE}
                SET used_for_training = TRUE,
                    model_version = :version,
                    updated_at = NOW()
                WHERE base_ym = :base_ym
            """), {'base_ym': int(ym), 'version': model_version})

    print(f"✅ 학습 사용 기록 완료: {base_yms}")


if __name__ == "__main__":
    # 테스트
    print("=" * 60)
    print("Feature Store 데이터 로더 테스트")
    print("=" * 60)

    # 사용 가능한 기준년월 조회
    base_yms = get_available_base_yms()
    print(f"\n사용 가능한 기준년월: {base_yms}")

    # 메타데이터 조회
    stats = get_feature_store_stats()
    print(f"\nFeature Store 통계:")
    print(stats)

    # 샘플 데이터 로드
    df = load_from_feature_store(base_ym=base_yms[0], limit=100)
    print(f"\n샘플 데이터 (처음 5행):")
    print(df.head())
