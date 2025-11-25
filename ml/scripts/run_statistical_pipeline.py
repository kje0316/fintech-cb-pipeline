"""
통계 기반 ML 파이프라인 통합 실행

전체 프로세스:
1. 데이터 추출 (159개 전체)
2. 통계적 전처리
3. 통계적 피처 선택 (5가지 방법)
4. 도메인 검증
5. 결과 요약

실행:
    python ml/scripts/run_statistical_pipeline.py
"""

import sys
from pathlib import Path
import time

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_full_pipeline():
    """
    전체 통계 기반 ML 파이프라인 실행
    """
    print("\n")
    print("="*80)
    print("  통계 기반 부도예측 ML 파이프라인")
    print("  Statistical Feature Selection for Default Prediction")
    print("="*80)
    print()

    start_time = time.time()

    try:
        # ====================================================================
        # Step 1: 데이터 추출 (159개 전체)
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [1/4] 데이터 추출 (159개 전체 피처)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        from ml.scripts.extract_01_training_data import extract_all_training_data

        step_start = time.time()
        df = extract_all_training_data()
        step_time = time.time() - step_start

        print(f"\n✓ Step 1 완료 ({step_time:.1f}초)")
        print(f"  출력: {df.shape[0]:,}행 × {df.shape[1]}개 컬럼")
        print()

        # ====================================================================
        # Step 2: 통계적 전처리
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [2/4] 통계적 전처리 (결측치, 인코딩)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        from ml.scripts.preprocess_02a_statistical import statistical_preprocessing

        step_start = time.time()
        X, y, metadata = statistical_preprocessing()
        step_time = time.time() - step_start

        print(f"\n✓ Step 2 완료 ({step_time:.1f}초)")
        print(f"  출력: {X.shape[0]:,}행 × {X.shape[1]}개 피처")
        print()

        # ====================================================================
        # Step 3: 통계적 피처 선택 (5가지 방법)
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [3/4] 통계적 피처 선택 (5가지 방법론)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        from ml.scripts.select_02b_statistical_features import statistical_feature_selection

        step_start = time.time()
        selected_features, report = statistical_feature_selection()
        step_time = time.time() - step_start

        print(f"\n✓ Step 3 완료 ({step_time:.1f}초)")
        print(f"  출력: {len(selected_features)}개 피처 선택")
        print()

        # ====================================================================
        # Step 4: 도메인 검증
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [4/4] 도메인 검증 (식별자 제거)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        from ml.scripts.validate_02c_domain import domain_validation

        step_start = time.time()
        validated_features, validation_report = domain_validation()
        step_time = time.time() - step_start

        print(f"\n✓ Step 4 완료 ({step_time:.1f}초)")
        print(f"  출력: {len(validated_features)}개 최종 피처")
        print()

        # ====================================================================
        # 최종 요약
        # ====================================================================
        total_time = time.time() - start_time

        print("\n")
        print("="*80)
        print("  파이프라인 완료!")
        print("="*80)
        print()
        print("  전체 소요 시간: {:.1f}초 ({:.1f}분)".format(total_time, total_time/60))
        print()
        print("  처리 결과:")
        print("  ┌─────────────────────────────────────────────────────────┐")
        print(f"  │  원본 데이터:        {df.shape[1]:3d}개 컬럼                        │")
        print(f"  │  전처리 후:          {X.shape[1]:3d}개 피처                        │")
        print(f"  │  통계적 선택:        {len(selected_features):3d}개 피처                        │")
        print(f"  │  도메인 검증 후:     {len(validated_features):3d}개 피처 (최종)                 │")
        print("  └─────────────────────────────────────────────────────────┘")
        print()
        print("  생성된 파일:")
        print("    ✓ ml/data/raw_data_full_20210801.parquet")
        print("    ✓ ml/data/preprocessed_data_20210801.parquet")
        print("    ✓ ml/data/preprocessing_metadata.pkl")
        print("    ✓ ml/data/feature_selection_report.csv  ← 발표용!")
        print("    ✓ ml/data/selected_features.csv")
        print("    ✓ ml/data/validated_features.csv")
        print("    ✓ ml/data/domain_validation_report.txt")
        print()
        print("  다음 단계:")
        print("    1. 파생 변수 생성: python ml/scripts/03_feature_engineering.py")
        print("    2. 모델 학습: python ml/scripts/04_train_default_model.py")
        print("    3. SHAP 분석: python ml/scripts/03_shap_analysis.py")
        print()

        return {
            'original_features': df.shape[1],
            'preprocessed_features': X.shape[1],
            'selected_features': len(selected_features),
            'validated_features': len(validated_features),
            'total_time': total_time
        }

    except Exception as e:
        print("\n")
        print("="*80)
        print("  ✗ 파이프라인 실행 실패!")
        print("="*80)
        print()
        print(f"오류: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    result = run_full_pipeline()
