"""
부도예측 모델 학습 스크립트 (70개 피처 기반)

XGBoost 베이스라인 모델 학습 및 저장
"""
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import json
from datetime import datetime

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    confusion_matrix, classification_report
)
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

# MLflow 추가
import mlflow
import mlflow.xgboost
import mlflow.sklearn


def load_training_data():
    """학습 데이터 로드"""
    print("📂 학습 데이터 로딩 중...")

    train_path = Path("data/processed/train_70features.parquet")
    test_path = Path("data/processed/test_70features.parquet")

    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(
            "학습 데이터를 찾을 수 없습니다.\n"
            "먼저 01_prepare_data.py를 실행하세요."
        )

    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)

    print(f"✅ 데이터 로드 완료:")
    print(f"  - Train: {len(train_df):,}건")
    print(f"  - Test:  {len(test_df):,}건")

    return train_df, test_df


def prepare_features(train_df, test_df, target_col='default_yn'):
    """피처 준비 (X, y 분리)"""
    print(f"\n🔧 피처 준비 중...")

    # X, y 분리
    X_train = train_df.drop(columns=[target_col])
    y_train = train_df[target_col]
    X_test = test_df.drop(columns=[target_col])
    y_test = test_df[target_col]

    print(f"  - Train 피처: {X_train.shape}")
    print(f"  - Test 피처:  {X_test.shape}")
    print(f"  - Train 부도율: {y_train.mean()*100:.2f}%")
    print(f"  - Test 부도율:  {y_test.mean()*100:.2f}%")

    # 피처 이름 저장
    feature_names = list(X_train.columns)

    return X_train, X_test, y_train, y_test, feature_names


def apply_smote(X_train, y_train, random_state=42):
    """SMOTE 오버샘플링 적용"""
    print(f"\n⚖️  SMOTE 오버샘플링 적용 중...")

    # 원본 분포
    original_dist = y_train.value_counts()
    print(f"  원본 분포:")
    print(f"    - 정상: {original_dist.get(0, 0):,}건 ({original_dist.get(0, 0)/len(y_train)*100:.1f}%)")
    print(f"    - 부도: {original_dist.get(1, 0):,}건 ({original_dist.get(1, 0)/len(y_train)*100:.1f}%)")

    # SMOTE 적용
    smote = SMOTE(random_state=random_state)
    X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

    # 리샘플링 후 분포
    resampled_dist = pd.Series(y_resampled).value_counts()
    print(f"  리샘플링 후:")
    print(f"    - 정상: {resampled_dist.get(0, 0):,}건 ({resampled_dist.get(0, 0)/len(y_resampled)*100:.1f}%)")
    print(f"    - 부도: {resampled_dist.get(1, 0):,}건 ({resampled_dist.get(1, 0)/len(y_resampled)*100:.1f}%)")

    print(f"✅ SMOTE 완료: {len(X_train):,}건 → {len(X_resampled):,}건")

    return X_resampled, y_resampled


def scale_features(X_train, X_test):
    """피처 스케일링"""
    print(f"\n📏 피처 스케일링 중...")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print(f"✅ 스케일링 완료")

    return X_train_scaled, X_test_scaled, scaler


def train_xgboost_baseline(X_train, y_train, random_state=42):
    """XGBoost 베이스라인 모델 학습"""
    print(f"\n🤖 XGBoost 모델 학습 중...")
    print(f"  하이퍼파라미터:")

    params = {
        'n_estimators': 100,
        'max_depth': 6,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': random_state,
        'eval_metric': 'logloss',
        'use_label_encoder': False
    }

    for key, value in params.items():
        print(f"    - {key}: {value}")

    model = XGBClassifier(**params)
    model.fit(X_train, y_train)

    print(f"✅ 모델 학습 완료")

    return model


def evaluate_model(model, X_test, y_test, scaler):
    """모델 평가"""
    print(f"\n📊 모델 평가 중...")

    # 예측
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)

    # 메트릭 계산
    auc = roc_auc_score(y_test, y_pred_proba)
    f1 = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    print(f"\n📈 성능 지표:")
    print(f"  - AUC-ROC:   {auc:.4f}")
    print(f"  - F1-Score:  {f1:.4f}")
    print(f"  - Precision: {precision:.4f}")
    print(f"  - Recall:    {recall:.4f}")

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    print(f"\n혼동 행렬:")
    print(f"  [[TN: {cm[0,0]:4d}, FP: {cm[0,1]:4d}]")
    print(f"   [FN: {cm[1,0]:4d}, TP: {cm[1,1]:4d}]]")

    # Classification Report
    print(f"\n상세 리포트:")
    print(classification_report(y_test, y_pred, target_names=['정상', '부도']))

    metrics = {
        'auc_roc': float(auc),
        'f1_score': float(f1),
        'precision': float(precision),
        'recall': float(recall),
        'confusion_matrix': cm.tolist()
    }

    return metrics


def save_model_and_results(model, scaler, feature_names, metrics):
    """모델 및 결과 저장"""
    print(f"\n💾 모델 저장 중...")

    output_dir = Path("models/default_prediction_v2/models/production")
    output_dir.mkdir(exist_ok=True, parents=True)

    # 모델 저장
    model_path = output_dir / "model_v1.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"  ✅ 모델 저장: {model_path}")

    # 스케일러 저장
    scaler_path = output_dir / "scaler_v1.pkl"
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"  ✅ 스케일러 저장: {scaler_path}")

    # 메타데이터 저장
    metadata = {
        'model_version': 'v1',
        'model_type': 'XGBoost',
        'n_features': len(feature_names),
        'feature_names': feature_names,
        'metrics': metrics,
        'training_date': datetime.now().isoformat(),
        'description': '70개 피처 기반 부도예측 베이스라인 모델'
    }

    metadata_path = output_dir / "metadata_v1.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"  ✅ 메타데이터 저장: {metadata_path}")

    # 실험 로그 저장
    results_dir = Path("models/default_prediction_v2/results")
    results_dir.mkdir(exist_ok=True, parents=True)

    experiment_log = {
        'exp_id': 'exp001',
        'model_type': 'xgboost_baseline',
        'n_features': len(feature_names),
        'auc': metrics['auc_roc'],
        'f1': metrics['f1_score'],
        'precision': metrics['precision'],
        'recall': metrics['recall'],
        'notes': 'Initial baseline with 70 features'
    }

    log_path = results_dir / "experiment_log.csv"
    log_df = pd.DataFrame([experiment_log])
    log_df.to_csv(log_path, index=False)
    print(f"  ✅ 실험 로그 저장: {log_path}")

    return model_path, scaler_path, metadata_path


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("부도예측 모델 학습 시작 (70개 피처)")
    print("=" * 60)

    # MLflow 실험 설정 (데이터베이스 백엔드 사용)
    mlflow.set_tracking_uri("sqlite:///mlflow_db/mlflow.db")  # SQLite 데이터베이스

    # 실험 설정 (없으면 자동 생성)
    experiment = mlflow.set_experiment("default_prediction_v2")
    print(f"📊 MLflow 실험: {experiment.name} (ID: {experiment.experiment_id})")

    try:
        # MLflow Run 시작
        with mlflow.start_run(run_name="xgboost_baseline"):
            # 1. 데이터 로드
            train_df, test_df = load_training_data()

            # 2. 피처 준비
            X_train, X_test, y_train, y_test, feature_names = prepare_features(
                train_df, test_df
            )

            # MLflow: 데이터 정보 로깅
            mlflow.log_param("n_train_samples", len(X_train))
            mlflow.log_param("n_test_samples", len(X_test))
            mlflow.log_param("n_features", len(feature_names))
            mlflow.log_param("train_default_rate", y_train.mean())

            # 3. SMOTE 오버샘플링
            X_train_resampled, y_train_resampled = apply_smote(X_train, y_train)
            mlflow.log_param("use_smote", True)
            mlflow.log_param("n_resampled", len(X_train_resampled))

            # 4. 스케일링
            X_train_scaled, X_test_scaled, scaler = scale_features(
                X_train_resampled, X_test
            )

            # 5. 모델 학습
            model = train_xgboost_baseline(X_train_scaled, y_train_resampled)

            # MLflow: 하이퍼파라미터 로깅
            mlflow.log_params({
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.1,
                "subsample": 0.8,
                "colsample_bytree": 0.8
            })

            # 6. 모델 평가
            metrics = evaluate_model(model, X_test_scaled, y_test, scaler)

            # MLflow: 성능 지표 로깅
            mlflow.log_metrics({
                "auc_roc": metrics['auc_roc'],
                "f1_score": metrics['f1_score'],
                "precision": metrics['precision'],
                "recall": metrics['recall']
            })

            # MLflow: 모델 저장 및 Registry 등록
            print("\n📦 MLflow에 모델 저장 중...")

            # 모델 아티팩트 저장
            model_uri = mlflow.xgboost.log_model(model, "model").model_uri
            scaler_uri = mlflow.sklearn.log_model(scaler, "scaler").model_uri

            print(f"  ✅ 모델 URI: {model_uri}")
            print(f"  ✅ 스케일러 URI: {scaler_uri}")

            # Model Registry에 등록
            print("\n📋 Model Registry에 등록 중...")
            model_name = "default_prediction_model"

            try:
                # 모델 등록
                model_version = mlflow.register_model(
                    model_uri=model_uri,
                    name=model_name,
                    tags={
                        "model_type": "XGBoost",
                        "n_features": len(feature_names),
                        "auc_roc": metrics['auc_roc']
                    }
                )

                print(f"  ✅ 모델 등록 완료: {model_name} (버전 {model_version.version})")
                print(f"     AUC: {metrics['auc_roc']:.4f}")

                # 모델 버전에 설명 추가
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                client.update_model_version(
                    name=model_name,
                    version=model_version.version,
                    description=f"XGBoost baseline model with {len(feature_names)} features. "
                                f"AUC-ROC: {metrics['auc_roc']:.4f}, "
                                f"F1: {metrics['f1_score']:.4f}"
                )

                # 첫 번째 모델이면 자동으로 Production으로 승격
                if model_version.version == 1:
                    client.transition_model_version_stage(
                        name=model_name,
                        version=model_version.version,
                        stage="Production",
                        archive_existing_versions=False
                    )
                    print(f"  ✅ 첫 번째 모델 - 자동으로 Production 스테이지로 승격")
                else:
                    print(f"  ℹ️  새 버전 등록됨. Production 승격은 수동으로 진행하세요.")
                    print(f"     명령어: mlflow models transition-model-version-stage {model_name} {model_version.version} Production")

            except Exception as e:
                print(f"  ⚠️  Model Registry 등록 중 오류: {e}")
                print(f"     모델은 MLflow 실험에 저장되었습니다.")

            # 7. 로컬 파일 저장 (기존 방식 유지)
            model_path, scaler_path, metadata_path = save_model_and_results(
                model, scaler, feature_names, metrics
            )

            print("\n" + "=" * 60)
            print("✅ 모델 학습 완료!")
            print("=" * 60)
            print(f"모델 파일: {model_path}")
            print(f"성능 (AUC): {metrics['auc_roc']:.4f}")
            print(f"\n📊 MLflow UI 실행: mlflow ui --backend-store-uri sqlite:///mlflow_db/mlflow.db")
            print(f"   브라우저: http://localhost:5000")
            print(f"\n📋 Model Registry에서 모델 확인:")
            print(f"   - 모델명: {model_name}")
            print(f"   - 등록된 버전 확인 가능")
            print(f"\n다음 단계: python models/default_prediction_v2/scripts/03_evaluate_model.py")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        mlflow.end_run(status="FAILED")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
