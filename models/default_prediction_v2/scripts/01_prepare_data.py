"""
70개 피처 학습 데이터 준비 스크립트

37개 입력 컬럼 → 70개 피처 생성 및 Train/Test 분리
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from service.api.services.excel_prediction_service import ExcelPredictionService


def load_raw_data():
    """원본 데이터 로드"""
    print("📂 원본 데이터 로딩 중...")

    # preprocessed_data 사용 (원본 컬럼 + default_yn 타겟)
    data_path = Path("ml/data/preprocessed_data_20210801.parquet")

    if not data_path.exists():
        raise FileNotFoundError(f"학습 데이터를 찾을 수 없습니다: {data_path}")

    df = pd.read_parquet(data_path)
    print(f"✅ 데이터 로드 완료: {len(df):,}건, {len(df.columns)}개 컬럼")

    # 타겟 변수 확인
    if 'default_yn' in df.columns:
        print(f"  - 타겟 변수: default_yn")
        print(f"  - 부도율: {df['default_yn'].mean()*100:.2f}%")

    return df


def extract_37_input_features(df):
    """원본 데이터에서 37개 입력 컬럼 추출"""
    print("\n🔍 37개 입력 컬럼 추출 중...")

    # ExcelPredictionService의 37개 필수 컬럼
    required_cols = [
        # 재무상태표 (12개)
        'fn1_13', 'fn1_1', 'fn1_4', 'fn1_11', 'fn1_19', 'fn1_24',
        'fn1_14', 'fn1_15', 'fn1_16', 'fn1_유형자산', 'fn1_매입채무', 'fn3_적립금',

        # 손익계산서 (8개)
        'fn2_1', 'fn2_2', 'fn2_2_1', 'fn2_3', 'fn2_5', 'fn2_5_1',
        'fn2_10', 'fn2_10_1',

        # 현금흐름/기타 (6개)
        'fn3_1', 'fn3_2', 'fn3_7', 'fn3_8', 'fn3_11_1', 'fn2_4',

        # 전년도 데이터 (4개)
        'fn1_13_전기', 'fn2_1_전기', 'fn1_1_전기', 'fn3_8_전기',

        # 기업정보 (2개)
        'empe_cnt', 'wg_gb',

        # 연체정보 (7개)
        'da0d00029', 'da0d00026', 'da0d00035_1', 'da0d00035_2',
        'da0d00033_1', 'db0d00006', 'd2b000002',
    ]

    # 타겟 변수
    if 'default_yn' in df.columns:
        target_col = 'default_yn'
    elif 'default' in df.columns:
        target_col = 'default'
    elif 'def_yn' in df.columns:
        target_col = 'def_yn'
    else:
        raise ValueError("타겟 변수를 찾을 수 없습니다. (default_yn, default, def_yn 중 하나 필요)")

    # 사용 가능한 컬럼만 추출
    available_cols = [col for col in required_cols if col in df.columns]
    missing_cols = [col for col in required_cols if col not in df.columns]

    print(f"  - 사용 가능 컬럼: {len(available_cols)}/37")

    if missing_cols:
        print(f"  ⚠️  누락된 컬럼 ({len(missing_cols)}개):")
        for col in missing_cols[:10]:
            print(f"     - {col}")
        if len(missing_cols) > 10:
            print(f"     ... 외 {len(missing_cols)-10}개")

        # 누락된 컬럼을 0으로 채움
        for col in missing_cols:
            df[col] = 0
            print(f"  📝 {col} → 0으로 채움")

    # 37개 입력 + 타겟
    df_37 = df[available_cols + missing_cols + [target_col]].copy()

    # 결측치 처리
    df_37 = df_37.fillna(0)

    print(f"✅ 37개 입력 컬럼 추출 완료: {df_37.shape}")

    return df_37, target_col


def generate_70_features(df_37, target_col):
    """37개 입력 → 70개 피처 생성"""
    print("\n🔧 70개 피처 생성 중...")

    service = ExcelPredictionService()

    features_70_list = []

    for idx, row in df_37.iterrows():
        if idx % 10000 == 0:
            print(f"  진행률: {idx}/{len(df_37)} ({idx/len(df_37)*100:.1f}%)")

        # 37개 입력을 딕셔너리로 변환
        input_dict = row.drop(target_col).to_dict()

        # 파생 변수 생성 (70개)
        full_features = service.create_derived_features(input_dict)

        # 클러스터링 피처 매핑 (70개)
        clustering_features = service.map_to_clustering_features(full_features)

        features_70_list.append(clustering_features)

    df_70 = pd.DataFrame(features_70_list)

    # 타겟 변수 추가
    df_70[target_col] = df_37[target_col].values

    print(f"✅ 70개 피처 생성 완료: {df_70.shape}")
    print(f"  - 피처 수: {len(df_70.columns) - 1}")
    print(f"  - 샘플 수: {len(df_70)}")

    return df_70


def split_train_test(df_70, target_col, test_size=0.2, random_state=42):
    """Train/Test 분리"""
    print(f"\n✂️  Train/Test 분리 중 (test_size={test_size})...")

    from sklearn.model_selection import train_test_split

    # 타겟 분포 확인
    target_dist = df_70[target_col].value_counts(normalize=True)
    print(f"  타겟 분포:")
    print(f"    - 정상: {target_dist.get(0, 0)*100:.2f}%")
    print(f"    - 부도: {target_dist.get(1, 0)*100:.2f}%")

    # Stratified split
    train_df, test_df = train_test_split(
        df_70,
        test_size=test_size,
        stratify=df_70[target_col],
        random_state=random_state
    )

    print(f"✅ 분리 완료:")
    print(f"  - Train: {len(train_df):,}건 ({len(train_df)/len(df_70)*100:.1f}%)")
    print(f"  - Test:  {len(test_df):,}건 ({len(test_df)/len(df_70)*100:.1f}%)")

    return train_df, test_df


def save_data(train_df, test_df, target_col):
    """데이터 저장"""
    print("\n💾 데이터 저장 중...")

    output_dir = Path("data/processed")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Parquet 저장
    train_path = output_dir / "train_70features.parquet"
    test_path = output_dir / "test_70features.parquet"

    train_df.to_parquet(train_path, index=False)
    test_df.to_parquet(test_path, index=False)

    print(f"✅ Train 데이터 저장: {train_path}")
    print(f"✅ Test 데이터 저장: {test_path}")

    # 피처 메타데이터 저장
    feature_list = [col for col in train_df.columns if col != target_col]

    metadata = {
        "n_features": len(feature_list),
        "features": feature_list,
        "target": target_col,
        "train_size": len(train_df),
        "test_size": len(test_df),
        "train_default_rate": float(train_df[target_col].mean()),
        "test_default_rate": float(test_df[target_col].mean())
    }

    metadata_path = output_dir / "feature_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"✅ 메타데이터 저장: {metadata_path}")

    return train_path, test_path


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("70개 피처 학습 데이터 준비 시작")
    print("=" * 60)

    try:
        # 1. 원본 데이터 로드
        df = load_raw_data()

        # 2. 37개 입력 컬럼 추출
        df_37, target_col = extract_37_input_features(df)

        # 3. 70개 피처 생성 (전체 데이터 사용)
        print("\n📊 전체 데이터로 70개 피처 생성 시작...")
        use_full = True  # 전체 데이터 사용

        df_70 = generate_70_features(df_37, target_col)

        # 4. Train/Test 분리
        train_df, test_df = split_train_test(df_70, target_col)

        # 5. 저장
        train_path, test_path = save_data(train_df, test_df, target_col)

        print("\n" + "=" * 60)
        print("✅ 데이터 준비 완료!")
        print("=" * 60)
        print(f"다음 단계: python models/default_prediction_v2/scripts/02_train_model.py")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
