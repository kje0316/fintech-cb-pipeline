"""
부도 예측 모델 학습용 데이터 추출 (통계 기반 피처 선택 버전)

BS_DT = '20210801' 데이터에서 **159개 전체 피처** 추출
- 50,000 rows (부도율 1.52%)
- 159 features (모든 원본 컬럼)
- 출력: ml/data/raw_data_full_20210801.parquet

변경 사항:
- 기존: 48개 경험적 선택
- 신규: 159개 전체 추출 (통계적 피처 선택은 다음 단계에서)

실행:
    python ml/scripts/01_extract_training_data.py
"""

import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from shared.config_loader import DB_URL

def extract_all_training_data(bs_dt='20210801', output_path=None):
    """
    PostgreSQL Lake에서 159개 전체 피처 추출 (선택 없이!)

    Args:
        bs_dt: 기준년월 (YYYYMMDD 형식, 예: '20210801')
        output_path: 출력 파일 경로 (기본: ml/data/raw_data_full_{bs_dt}.parquet)

    Returns:
        DataFrame (159개 컬럼 + 타겟)
    """

    # 출력 경로 설정
    if output_path is None:
        output_path = PROJECT_ROOT / f"ml/data/raw_data_full_{bs_dt}.parquet"

    # 출력 디렉토리가 없으면 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f" 부도 예측 모델 학습 데이터 추출 (통계 기반 버전)")
    print(f" BS_DT = {bs_dt}, 159개 전체 피처 추출")
    print("=" * 80)
    print()

    # PostgreSQL 연결
    print(f"✓ PostgreSQL 연결 중... (DB: {DB_URL.split('@')[1]})")
    engine = create_engine(DB_URL)

    # SQL 쿼리 - 159개 전체 선택!
    bs_dt_int = int(bs_dt)

    query = f"""
    SELECT *
    FROM lake.raw_data
    WHERE bs_dt = '{bs_dt}'
      AND perf_12m IS NOT NULL  -- 타겟 변수가 있는 행만
    ORDER BY sic_cd_3
    """

    print(f"✓ 데이터 추출 중... (BS_DT = {bs_dt})")
    print(f"   전체 컬럼 추출 (피처 선택 없음)")
    df = pd.read_sql(query, engine)

    print(f"✓ 데이터 로드 완료: {len(df):,}행 × {len(df.columns)}개 컬럼")
    print()

    # 기본 통계
    print("-" * 80)
    print(" 데이터 요약")
    print("-" * 80)

    # 타겟 변수 분포
    if 'perf_12m' in df.columns:
        # 문자열을 숫자로 변환
        df['perf_12m'] = pd.to_numeric(df['perf_12m'], errors='coerce')
        default_counts = df['perf_12m'].value_counts()
        default_rate = df['perf_12m'].mean() * 100
        print(f"정상 기업: {default_counts.get(0, 0):,}개 ({100 - default_rate:.2f}%)")
        print(f"부도 기업: {default_counts.get(1, 0):,}개 ({default_rate:.2f}%)")
        print(f"클래스 불균형 비율: 1:{int(default_counts.get(0, 0) / max(default_counts.get(1, 1), 1))}")

    # 컬럼 타입 분류
    print(f"\n컬럼 타입 분포:")
    print(f"  - Object (문자열): {(df.dtypes == 'object').sum()}개")
    print(f"  - Int64: {(df.dtypes == 'int64').sum()}개")
    print(f"  - Float64: {(df.dtypes == 'float64').sum()}개")
    print(f"  - 기타: {len(df.columns) - (df.dtypes == 'object').sum() - (df.dtypes == 'int64').sum() - (df.dtypes == 'float64').sum()}개")

    # 결측치 통계
    total_missing = df.isnull().sum().sum()
    total_cells = len(df) * len(df.columns)
    missing_pct = total_missing / total_cells * 100
    print(f"\n전체 결측치: {total_missing:,}개 / {total_cells:,}개 ({missing_pct:.2f}%)")

    # 결측률 높은 컬럼 (70% 이상) - 제거 대상
    high_missing_cols = (df.isnull().sum() / len(df) * 100)[lambda x: x >= 70].sort_values(ascending=False)
    if len(high_missing_cols) > 0:
        print(f"\n⚠️  결측률 70% 이상 컬럼: {len(high_missing_cols)}개 (다음 단계에서 제거 예정)")
        for col, pct in high_missing_cols.head(10).items():
            print(f"  - {col}: {pct:.1f}%")

    # 결측률 10-70% 컬럼
    medium_missing_cols = (df.isnull().sum() / len(df) * 100)[lambda x: (x >= 10) & (x < 70)].sort_values(ascending=False)
    if len(medium_missing_cols) > 0:
        print(f"\n결측률 10-70% 컬럼: {len(medium_missing_cols)}개 (중위값 대체 예정)")
        for col, pct in medium_missing_cols.head(5).items():
            print(f"  - {col}: {pct:.1f}%")

    print("-" * 80)
    print()

    # Parquet 저장
    print(f"✓ Parquet 파일 저장 중... ({output_path})")
    df.to_parquet(output_path, index=False, compression='snappy')

    # 파일 크기 확인
    file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"✓ 저장 완료: {file_size_mb:.2f} MB")
    print()

    print("=" * 80)
    print(" 데이터 추출 완료!")
    print("=" * 80)
    print()
    print(f"출력 파일: {output_path}")
    print(f"행 수: {len(df):,}")
    print(f"컬럼 수: {len(df.columns)}")
    print(f"파일 크기: {file_size_mb:.2f} MB")
    print()
    print("다음 단계:")
    print("  1. 통계적 전처리: python ml/scripts/02a_statistical_preprocessing.py")
    print("  2. 통계적 피처 선택: python ml/scripts/02b_statistical_feature_selection.py")
    print()

    return df


if __name__ == '__main__':
    # 기본 실행: 2021년 8월 데이터 전체 추출
    df = extract_all_training_data(bs_dt='20210801')

    # 샘플 데이터 미리보기
    print("샘플 데이터 (처음 3행, 처음 10개 컬럼):")
    print(df.iloc[:3, :10])
    print()
    print(f"전체 컬럼 목록 ({len(df.columns)}개):")
    print(df.columns.tolist()[:20], "...")
