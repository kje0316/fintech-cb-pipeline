"""
ML Feature Store 마트 빌더

원본 데이터에서 70개 ML 피처를 생성하여 Feature Store 마트에 적재

Usage:
    # 전체 기준년월 처리
    python etl/dwh_to_mart/build_feature_store.py

    # 특정 기준년월만 처리
    python etl/dwh_to_mart/build_feature_store.py --base-ym 20210801

    # 스키마만 생성
    python etl/dwh_to_mart/build_feature_store.py --schema-only
"""
import sys
import argparse
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import DB_URL

# ML 피처 생성 함수 import
from ml.default_prediction.run_pipeline import (
    INPUT_37_COLUMNS,
    CLUSTERING_70_FEATURES,
    create_derived_features,
    map_to_70_features
)

# 경로 설정
RAW_DATA_PATH = project_root / 'data' / 'raw' / '기업신용평가정보_합성데이터.csv'
COLUMNS_MAP_PATH = project_root / 'config' / 'columns_map.yaml'
SCHEMA_SQL_PATH = project_root / 'etl' / 'dwh_to_mart' / 'feature_store_schema.sql'

# DB 연결
engine = create_engine(DB_URL, echo=False, future=True)

DM_SCHEMA = "marts"
TABLE_NAME = "mart_feature_store_ml"
META_TABLE_NAME = "mart_feature_store_metadata"


def create_schema():
    """Feature Store 스키마 생성 (SQL 파일 실행)"""
    print("\n📦 Feature Store 스키마 생성 중...")

    with open(SCHEMA_SQL_PATH, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # SQL 문을 개별로 분리하여 실행
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]

    # 각 문장을 개별 트랜잭션으로 실행 (오류 격리)
    for stmt in statements:
        if stmt and not stmt.startswith('--'):
            try:
                with engine.begin() as conn:
                    conn.execute(text(stmt))
            except SQLAlchemyError as e:
                # 이미 존재하는 오류는 무시
                if 'already exists' not in str(e):
                    print(f"  ⚠️ SQL 실행 경고: {str(e)[:100]}")

    print("✅ Feature Store 스키마 생성 완료")


def load_columns_map():
    """컬럼명 매핑 로드 (한글 → 영문)"""
    with open(COLUMNS_MAP_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_raw_data(base_ym: int = None) -> pd.DataFrame:
    """
    원본 데이터 로드

    Args:
        base_ym: 특정 기준년월만 로드 (None이면 전체)

    Returns:
        DataFrame
    """
    print(f"\n📂 원본 데이터 로드 중: {RAW_DATA_PATH}")

    df = pd.read_csv(RAW_DATA_PATH, encoding='cp949', low_memory=False)
    print(f"  - 전체 데이터: {len(df):,}건")

    if base_ym:
        df = df[df['기준년월'] == base_ym]
        print(f"  - {base_ym} 필터링: {len(df):,}건")

    return df


def rename_columns(df: pd.DataFrame, columns_map: dict) -> pd.DataFrame:
    """컬럼명 한글 → 영문 변환"""
    rename_dict = {v: k.lower() for k, v in columns_map.items() if v in df.columns}
    return df.rename(columns=rename_dict)


def generate_70_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    70개 ML 피처 생성

    Args:
        df: 원본 데이터 (영문 컬럼명)

    Returns:
        70개 피처가 포함된 DataFrame
    """
    print(f"\n🔧 70개 ML 피처 생성 중...")

    # 필수 컬럼 확인
    available_cols = [col for col in INPUT_37_COLUMNS if col in df.columns]
    missing_cols = [col for col in INPUT_37_COLUMNS if col not in df.columns]

    print(f"  - 입력 컬럼: {len(available_cols)}/{len(INPUT_37_COLUMNS)}")
    if missing_cols:
        print(f"  - 누락 ({len(missing_cols)}개): {missing_cols[:5]}...")
        for col in missing_cols:
            df[col] = 0

    # 70개 피처 생성
    features_list = []
    total = len(df)

    for idx, (_, row) in enumerate(df.iterrows()):
        if idx % 10000 == 0:
            print(f"  - 진행: {idx:,}/{total:,} ({idx/total*100:.1f}%)")

        # 37개 입력 추출
        input_dict = {col: row.get(col, 0) for col in INPUT_37_COLUMNS}

        # 파생 변수 생성
        derived = create_derived_features(input_dict)

        # 70개 피처 매핑
        features_70 = map_to_70_features(derived)

        # 메타 정보 추가
        features_70['base_ym'] = row.get('base_ym', row.get('기준년월', 0))
        features_70['company_id'] = row.get('company_id', row.get('기업고유키', f'COMP_{idx}'))
        features_70['sic_cd_3'] = row.get('sic_cd_3', row.get('업종대분류', ''))

        # 타겟 레이블 (있으면)
        target_col = 'perf_12m'  # 모형개발용Performance(향후1년내부도여부)
        if target_col in row:
            features_70['default_yn'] = int(row[target_col]) if pd.notna(row[target_col]) else None
        else:
            features_70['default_yn'] = None

        features_list.append(features_70)

    df_features = pd.DataFrame(features_list)

    # 무한값/NaN 처리
    df_features = df_features.replace([np.inf, -np.inf], np.nan)

    print(f"✅ 70개 피처 생성 완료: {len(df_features):,}건, {len(CLUSTERING_70_FEATURES)}개 피처")

    return df_features


def insert_to_feature_store(df_features: pd.DataFrame, base_ym: int):
    """
    Feature Store 마트에 적재

    Args:
        df_features: 70개 피처 DataFrame
        base_ym: 기준년월
    """
    # numpy 타입을 Python 기본 타입으로 변환
    base_ym_int = int(base_ym)

    print(f"\n💾 Feature Store 마트 적재 중... (base_ym={base_ym_int})")

    with engine.begin() as conn:
        # 기존 데이터 삭제 (해당 기준년월)
        conn.execute(text(f"""
            DELETE FROM {DM_SCHEMA}.{TABLE_NAME}
            WHERE base_ym = :base_ym
        """), {'base_ym': base_ym_int})

        print(f"  - 기존 데이터 삭제 완료 (base_ym={base_ym_int})")

    # pandas to_sql 사용하여 적재
    # 컬럼명을 소문자로 변환
    df_features.columns = df_features.columns.str.lower()

    # 필요한 컬럼만 선택 (테이블 스키마와 일치)
    expected_cols = [
        'base_ym', 'company_id',
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
        # 타겟 및 메타
        'default_yn', 'sic_cd_3'
    ]

    # 존재하는 컬럼만 선택
    available_cols = [col for col in expected_cols if col in df_features.columns]
    df_to_insert = df_features[available_cols].copy()

    # 적재 (psycopg2 copy_from 사용 - 빠름)
    import io

    # NULL 값 처리 및 타입 변환
    df_to_insert = df_to_insert.fillna('')

    # CSV 형식으로 변환
    output = io.StringIO()
    df_to_insert.to_csv(output, sep='\t', header=False, index=False, na_rep='')
    output.seek(0)

    # raw connection으로 COPY 실행
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        # 스키마 설정
        cursor.execute(f"SET search_path TO {DM_SCHEMA}, public")
        cursor.copy_from(
            output,
            TABLE_NAME,  # search_path 설정 후 테이블명만 사용
            sep='\t',
            null='',
            columns=df_to_insert.columns.tolist()
        )
        raw_conn.commit()
    finally:
        raw_conn.close()

    print(f"✅ Feature Store 적재 완료: {len(df_to_insert):,}건")

    # 메타데이터 업데이트
    update_metadata(base_ym_int, df_features)


def update_metadata(base_ym: int, df_features: pd.DataFrame):
    """메타데이터 테이블 업데이트"""
    # numpy 타입을 Python 기본 타입으로 변환
    base_ym_int = int(base_ym)
    total = int(len(df_features))

    default_col = 'default_yn' if 'default_yn' in df_features.columns else None
    if default_col and df_features[default_col].notna().any():
        default_count = int(df_features[default_col].sum())
    else:
        default_count = 0

    default_rate = float(default_count / total) if total > 0 else 0.0

    # NULL 비율 계산
    null_counts = int(df_features.isnull().sum().sum())
    total_cells = int(df_features.shape[0] * df_features.shape[1])
    null_ratio = float(null_counts / total_cells) if total_cells > 0 else 0.0

    with engine.begin() as conn:
        # UPSERT
        conn.execute(text(f"""
            INSERT INTO {DM_SCHEMA}.{META_TABLE_NAME}
            (base_ym, total_companies, default_count, default_rate, null_ratio, source_table, updated_at)
            VALUES (:base_ym, :total, :default_count, :default_rate, :null_ratio, :source, NOW())
            ON CONFLICT (base_ym) DO UPDATE SET
                total_companies = EXCLUDED.total_companies,
                default_count = EXCLUDED.default_count,
                default_rate = EXCLUDED.default_rate,
                null_ratio = EXCLUDED.null_ratio,
                updated_at = NOW()
        """), {
            'base_ym': base_ym_int,
            'total': total,
            'default_count': default_count,
            'default_rate': default_rate,
            'null_ratio': null_ratio,
            'source': str(RAW_DATA_PATH)
        })

    print(f"  - 메타데이터 업데이트 완료")


def build_feature_store(base_ym: int = None):
    """
    Feature Store 빌드 메인 함수

    Args:
        base_ym: 특정 기준년월 (None이면 전체)
    """
    start_time = datetime.now()

    print("\n" + "=" * 60)
    print("ML Feature Store 빌드")
    print(f"시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 스키마 생성
    create_schema()

    # 2. 컬럼 매핑 로드
    columns_map = load_columns_map()

    # 3. 원본 데이터 로드
    df_raw = load_raw_data(base_ym)

    if len(df_raw) == 0:
        print("⚠️ 처리할 데이터가 없습니다.")
        return

    # 4. 컬럼명 변환
    df_renamed = rename_columns(df_raw, columns_map)

    # 5. 기준년월별 처리
    if base_ym:
        base_yms = [base_ym]
    else:
        base_yms = sorted(df_renamed['base_ym'].unique() if 'base_ym' in df_renamed.columns
                         else df_raw['기준년월'].unique())

    print(f"\n📋 처리할 기준년월: {base_yms}")

    for ym in base_yms:
        print(f"\n{'='*40}")
        print(f"📅 기준년월: {ym}")
        print(f"{'='*40}")

        # 해당 기준년월 데이터 필터링
        if 'base_ym' in df_renamed.columns:
            df_ym = df_renamed[df_renamed['base_ym'] == ym].copy()
        else:
            df_ym = df_renamed[df_raw['기준년월'] == ym].copy()
            df_ym['base_ym'] = ym

        if len(df_ym) == 0:
            print(f"  ⚠️ 데이터 없음, 스킵")
            continue

        # 70개 피처 생성
        df_features = generate_70_features(df_ym)

        # Feature Store 적재
        insert_to_feature_store(df_features, ym)

    # 완료
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 60)
    print("✅ Feature Store 빌드 완료!")
    print(f"소요 시간: {duration}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="ML Feature Store 빌드")
    parser.add_argument(
        '--base-ym',
        type=int,
        default=None,
        help="특정 기준년월만 처리 (예: 20210801)"
    )
    parser.add_argument(
        '--schema-only',
        action='store_true',
        help="스키마만 생성하고 종료"
    )
    args = parser.parse_args()

    if args.schema_only:
        create_schema()
        print("✅ 스키마만 생성 완료")
        return

    build_feature_store(args.base_ym)


if __name__ == "__main__":
    main()
