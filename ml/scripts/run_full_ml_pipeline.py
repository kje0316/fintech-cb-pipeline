"""
완전한 ML 파이프라인 실행 (데이터 → 모델 학습까지)

전체 프로세스:
1. 데이터 추출 (159개 전체)
2. 통계적 전처리
3. 통계적 피처 선택 (5가지 방법)
4. 도메인 검증
5. 파생 변수 생성
6. 모델 학습 및 평가

실행:
    python ml/scripts/run_full_ml_pipeline.py
"""

import sys
from pathlib import Path
import time

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_full_ml_pipeline():
    """
    데이터 추출부터 모델 학습까지 전체 파이프라인 실행
    """
    print("\n")
    print("="*80)
    print("  완전한 ML 파이프라인 (End-to-End)")
    print("  Statistical Feature Selection → Model Training")
    print("="*80)
    print()

    start_time = time.time()

    try:
        # ====================================================================
        # Step 1: 데이터 추출 (159개 전체)
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [1/6] 데이터 추출 (159개 전체 피처)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        # Step 1 import는 실제 파일명에 맞춰 수정 필요
        # 파일명 확인 후 적절히 수정
        import importlib.util

        # 01_extract_training_data.py 동적 로드
        spec = importlib.util.spec_from_file_location(
            "extract_module",
            PROJECT_ROOT / "ml/scripts/01_extract_training_data.py"
        )
        extract_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extract_module)

        step_start = time.time()
        df = extract_module.extract_all_training_data()
        step_time = time.time() - step_start

        print(f"\n✓ Step 1 완료 ({step_time:.1f}초)")
        print(f"  출력: {df.shape[0]:,}행 × {df.shape[1]}개 컬럼")
        print()

        # ====================================================================
        # Step 2: 통계적 전처리
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [2/6] 통계적 전처리 (결측치, 인코딩)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        # 02a_statistical_preprocessing.py 동적 로드
        spec = importlib.util.spec_from_file_location(
            "preprocess_module",
            PROJECT_ROOT / "ml/scripts/02a_statistical_preprocessing.py"
        )
        preprocess_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preprocess_module)

        step_start = time.time()
        X, y, metadata = preprocess_module.statistical_preprocessing()
        step_time = time.time() - step_start

        print(f"\n✓ Step 2 완료 ({step_time:.1f}초)")
        print(f"  출력: {X.shape[0]:,}행 × {X.shape[1]}개 피처")
        print()

        # ====================================================================
        # Step 3: 통계적 피처 선택 (5가지 방법)
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [3/6] 통계적 피처 선택 (5가지 방법론)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        # 02b_statistical_feature_selection.py 동적 로드
        spec = importlib.util.spec_from_file_location(
            "select_module",
            PROJECT_ROOT / "ml/scripts/02b_statistical_feature_selection.py"
        )
        select_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(select_module)

        step_start = time.time()
        selected_features, report = select_module.statistical_feature_selection()
        step_time = time.time() - step_start

        print(f"\n✓ Step 3 완료 ({step_time:.1f}초)")
        print(f"  출력: {len(selected_features)}개 피처 선택")
        print()

        # ====================================================================
        # Step 4: 도메인 검증
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [4/6] 도메인 검증 (식별자 제거)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        # 02c_domain_validation.py 동적 로드
        spec = importlib.util.spec_from_file_location(
            "validate_module",
            PROJECT_ROOT / "ml/scripts/02c_domain_validation.py"
        )
        validate_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validate_module)

        step_start = time.time()
        validated_features, validation_report = validate_module.domain_validation()
        step_time = time.time() - step_start

        print(f"\n✓ Step 4 완료 ({step_time:.1f}초)")
        print(f"  출력: {len(validated_features)}개 최종 피처")
        print()

        # ====================================================================
        # Step 5: 파생 변수 생성
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [5/6] 파생 변수 생성 및 스케일링".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        # 03_feature_engineering.py 동적 로드
        spec = importlib.util.spec_from_file_location(
            "engineer_module",
            PROJECT_ROOT / "ml/scripts/03_feature_engineering.py"
        )
        engineer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engineer_module)

        step_start = time.time()
        df_scaled, scaler = engineer_module.feature_engineering_pipeline()
        step_time = time.time() - step_start

        print(f"\n✓ Step 5 완료 ({step_time:.1f}초)")
        print(f"  출력: {df_scaled.shape[1]-1}개 피처 (타겟 제외)")
        print()

        # ====================================================================
        # Step 6: 모델 학습 및 평가
        # ====================================================================
        print("\n")
        print("┌" + "─"*78 + "┐")
        print("│" + " [6/6] 모델 학습 및 평가 (4가지 모델)".ljust(78) + "│")
        print("└" + "─"*78 + "┘")
        print()

        # 04_train_default_model.py 동적 로드
        spec = importlib.util.spec_from_file_location(
            "train_module",
            PROJECT_ROOT / "ml/scripts/04_train_default_model.py"
        )
        train_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(train_module)

        step_start = time.time()

        # 데이터 로드
        data_path = PROJECT_ROOT / 'ml/data/engineered_features_20210801.parquet'
        X, y, credit_grade, feature_names = train_module.load_data(data_path)

        # Train/Test 분리
        X_train, X_test, y_train, y_test = train_module.split_data(X, y, test_size=0.2, random_state=42)

        # SMOTE 적용
        X_train_resampled, y_train_resampled = train_module.apply_smote(X_train, y_train, random_state=42)

        # 모델 학습 및 평가
        models, results, best_model_name, best_model = train_module.train_models(
            X_train_resampled, y_train_resampled, X_test, y_test, feature_names
        )

        # 피처 중요도 추출
        feature_importance_df = train_module.extract_feature_importance(best_model, feature_names, best_model_name)

        # 결과 저장
        train_module.save_results(best_model, best_model_name, results, feature_importance_df, feature_names)

        step_time = time.time() - step_start

        print(f"\n✓ Step 6 완료 ({step_time:.1f}초)")
        print(f"  최적 모델: {best_model_name}")
        print(f"  F1-Score: {results[best_model_name]['f1_score']:.4f}")
        print(f"  AUC-ROC: {results[best_model_name]['auc_roc']:.4f}")
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
        print(f"  │  도메인 검증:        {len(validated_features):3d}개 피처                        │")
        print(f"  │  파생 변수 추가:     {df_scaled.shape[1]-1:3d}개 피처 (최종)                 │")
        print(f"  │  최적 모델:          {best_model_name:<30}│")
        print(f"  │  F1-Score:           {results[best_model_name]['f1_score']:.4f}                                  │")
        print(f"  │  AUC-ROC:            {results[best_model_name]['auc_roc']:.4f}                                  │")
        print("  └─────────────────────────────────────────────────────────┘")
        print()
        print("  생성된 파일:")
        print("    데이터:")
        print("      ✓ ml/data/raw_data_full_20210801.parquet")
        print("      ✓ ml/data/preprocessed_data_20210801.parquet")
        print("      ✓ ml/data/engineered_features_20210801.parquet")
        print("      ✓ ml/data/feature_selection_report.csv  ← 발표용!")
        print("      ✓ ml/data/validated_features.csv")
        print()
        print("    모델:")
        print("      ✓ ml/models/default_model_best.pkl")
        if best_model_name == 'XGBoost':
            print("      ✓ ml/models/default_model_xgb.json")
        print("      ✓ ml/models/evaluation_results.json")
        print("      ✓ ml/models/feature_importance.csv")
        print("      ✓ ml/models/training_summary.txt")
        print()
        print("  다음 단계:")
        print("    1. SHAP 분석: python ml/scripts/03_shap_analysis.py")
        print("    2. 리포트 확인:")
        print("       - ml/data/feature_selection_report.csv (피처 선택 근거)")
        print("       - ml/models/training_summary.txt (모델 성능)")
        print()

        return {
            'original_features': df.shape[1],
            'preprocessed_features': X.shape[1],
            'selected_features': len(selected_features),
            'validated_features': len(validated_features),
            'final_features': df_scaled.shape[1] - 1,
            'best_model': best_model_name,
            'f1_score': results[best_model_name]['f1_score'],
            'auc_roc': results[best_model_name]['auc_roc'],
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
    result = run_full_ml_pipeline()
