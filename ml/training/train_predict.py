"""
부도예측 모델 다중 알고리즘 실험 스크립트

XGBoost, LightGBM, CatBoost 모델을 학습하고
MLflow에 자동 등록하여 성능을 비교합니다.
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
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from imblearn.over_sampling import SMOTE

import mlflow
import mlflow.xgboost
import mlflow.lightgbm
import mlflow.catboost
import mlflow.sklearn
from mlflow.tracking import MlflowClient


def load_training_data():
    """학습 데이터 로드"""
    print("📂 학습 데이터 로딩 중...")

    train_path = Path("ml/data/processed/train_70features.parquet")
    test_path = Path("ml/data/processed/test_70features.parquet")

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

    X_train = train_df.drop(columns=[target_col])
    y_train = train_df[target_col]
    X_test = test_df.drop(columns=[target_col])
    y_test = test_df[target_col]

    print(f"  - Train 피처: {X_train.shape}")
    print(f"  - Test 피처:  {X_test.shape}")
    print(f"  - Train 부도율: {y_train.mean()*100:.2f}%")
    print(f"  - Test 부도율:  {y_test.mean()*100:.2f}%")

    feature_names = list(X_train.columns)

    return X_train, X_test, y_train, y_test, feature_names


def apply_smote(X_train, y_train, random_state=42):
    """SMOTE 오버샘플링 적용"""
    print(f"\n⚖️  SMOTE 오버샘플링 적용 중...")

    original_dist = y_train.value_counts()
    print(f"  원본 분포:")
    print(f"    - 정상: {original_dist.get(0, 0):,}건 ({original_dist.get(0, 0)/len(y_train)*100:.1f}%)")
    print(f"    - 부도: {original_dist.get(1, 0):,}건 ({original_dist.get(1, 0)/len(y_train)*100:.1f}%)")

    smote = SMOTE(random_state=random_state)
    X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

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


def get_model_configs():
    """실험할 모델 설정"""
    return {
        'xgboost': {
            'model': XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric='logloss',
                use_label_encoder=False
            ),
            'params': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8
            },
            'log_func': mlflow.xgboost.log_model
        },
        'lightgbm': {
            'model': LGBMClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbose=-1
            ),
            'params': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8
            },
            'log_func': mlflow.lightgbm.log_model
        },
        'catboost': {
            'model': CatBoostClassifier(
                iterations=100,
                depth=6,
                learning_rate=0.1,
                random_state=42,
                verbose=False
            ),
            'params': {
                'iterations': 100,
                'depth': 6,
                'learning_rate': 0.1
            },
            'log_func': mlflow.catboost.log_model
        }
    }


def train_model(model, X_train, y_train, model_name):
    """모델 학습"""
    print(f"\n🤖 {model_name.upper()} 모델 학습 중...")

    model.fit(X_train, y_train)

    print(f"✅ {model_name.upper()} 학습 완료")

    return model


def evaluate_model(model, X_test, y_test, model_name):
    """모델 평가"""
    print(f"\n📊 {model_name.upper()} 모델 평가 중...")

    # 예측
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)

    # 메트릭 계산
    auc = roc_auc_score(y_test, y_pred_proba)
    f1 = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    print(f"\n📈 {model_name.upper()} 성능 지표:")
    print(f"  - AUC-ROC:   {auc:.4f}")
    print(f"  - F1-Score:  {f1:.4f}")
    print(f"  - Precision: {precision:.4f}")
    print(f"  - Recall:    {recall:.4f}")

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    print(f"\n혼동 행렬:")
    print(f"  [[TN: {cm[0,0]:4d}, FP: {cm[0,1]:4d}]")
    print(f"   [FN: {cm[1,0]:4d}, TP: {cm[1,1]:4d}]]")

    metrics = {
        'auc_roc': float(auc),
        'f1_score': float(f1),
        'precision': float(precision),
        'recall': float(recall),
        'confusion_matrix': cm.tolist()
    }

    return metrics


def register_model_to_registry(model_uri, model_name, model_type, metrics, feature_names):
    """MLflow Model Registry에 모델 등록"""
    print(f"\n📋 Model Registry에 {model_type.upper()} 등록 중...")

    try:
        client = MlflowClient()

        # 모델 등록
        model_version = mlflow.register_model(
            model_uri=model_uri,
            name=model_name,
            tags={
                "model_type": model_type.upper(),
                "n_features": len(feature_names),
                "auc_roc": metrics['auc_roc']
            }
        )

        print(f"  ✅ 모델 등록 완료: {model_name} (버전 {model_version.version})")
        print(f"     타입: {model_type.upper()}, AUC: {metrics['auc_roc']:.4f}")

        # 모델 버전에 설명 추가
        client.update_model_version(
            name=model_name,
            version=model_version.version,
            description=f"{model_type.upper()} model with {len(feature_names)} features. "
                        f"AUC-ROC: {metrics['auc_roc']:.4f}, "
                        f"F1: {metrics['f1_score']:.4f}"
        )

        return model_version

    except Exception as e:
        print(f"  ⚠️  Model Registry 등록 중 오류: {e}")
        return None


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("부도예측 모델 다중 알고리즘 실험")
    print("=" * 60)

    # MLflow 설정
    mlflow.set_tracking_uri("sqlite:///mlflow_db/mlflow.db")
    experiment = mlflow.set_experiment("default_prediction_v2")
    print(f"📊 MLflow 실험: {experiment.name} (ID: {experiment.experiment_id})")

    try:
        # 1. 데이터 로드
        train_df, test_df = load_training_data()

        # 2. 피처 준비
        X_train, X_test, y_train, y_test, feature_names = prepare_features(
            train_df, test_df
        )

        # 3. SMOTE 오버샘플링
        X_train_resampled, y_train_resampled = apply_smote(X_train, y_train)

        # 4. 스케일링
        X_train_scaled, X_test_scaled, scaler = scale_features(
            X_train_resampled, X_test
        )

        # 5. 모델 설정
        model_configs = get_model_configs()

        # 6. 각 모델 학습 및 평가
        results = []

        for model_type, config in model_configs.items():
            print("\n" + "=" * 60)
            print(f"🔬 {model_type.upper()} 실험 시작")
            print("=" * 60)

            with mlflow.start_run(run_name=f"{model_type}_baseline"):
                # 데이터 정보 로깅
                mlflow.log_param("model_type", model_type)
                mlflow.log_param("n_train_samples", len(X_train))
                mlflow.log_param("n_test_samples", len(X_test))
                mlflow.log_param("n_features", len(feature_names))
                mlflow.log_param("train_default_rate", y_train.mean())
                mlflow.log_param("use_smote", True)
                mlflow.log_param("n_resampled", len(X_train_resampled))

                # 하이퍼파라미터 로깅
                mlflow.log_params(config['params'])

                # 모델 학습
                model = train_model(
                    config['model'],
                    X_train_scaled,
                    y_train_resampled,
                    model_type
                )

                # 모델 평가
                metrics = evaluate_model(model, X_test_scaled, y_test, model_type)

                # 성능 지표 로깅
                mlflow.log_metrics({
                    "auc_roc": metrics['auc_roc'],
                    "f1_score": metrics['f1_score'],
                    "precision": metrics['precision'],
                    "recall": metrics['recall']
                })

                # 모델 저장
                model_uri = config['log_func'](model, "model").model_uri
                scaler_uri = mlflow.sklearn.log_model(scaler, "scaler").model_uri

                print(f"\n📦 {model_type.upper()} 모델 저장:")
                print(f"  - 모델 URI: {model_uri}")
                print(f"  - 스케일러 URI: {scaler_uri}")

                # Model Registry에 등록
                model_version = register_model_to_registry(
                    model_uri=model_uri,
                    model_name="default_prediction_model",
                    model_type=model_type,
                    metrics=metrics,
                    feature_names=feature_names
                )

                # 결과 저장
                results.append({
                    'model_type': model_type,
                    'version': model_version.version if model_version else None,
                    'auc_roc': metrics['auc_roc'],
                    'f1_score': metrics['f1_score'],
                    'precision': metrics['precision'],
                    'recall': metrics['recall']
                })

        # 7. 결과 요약
        print("\n" + "=" * 60)
        print("📊 전체 모델 성능 비교")
        print("=" * 60)

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('auc_roc', ascending=False)

        print(results_df.to_string(index=False))

        # 최고 성능 모델
        best_model = results_df.iloc[0]
        print(f"\n🏆 최고 성능 모델:")
        print(f"  - 타입: {best_model['model_type'].upper()}")
        print(f"  - 버전: {best_model['version']}")
        print(f"  - AUC-ROC: {best_model['auc_roc']:.4f}")

        # 결과 저장
        results_dir = Path("ml/results")
        results_dir.mkdir(exist_ok=True, parents=True)

        results_path = results_dir / "model_comparison.csv"
        results_df.to_csv(results_path, index=False)
        print(f"\n💾 비교 결과 저장: {results_path}")

        print("\n" + "=" * 60)
        print("✅ 모든 모델 실험 완료!")
        print("=" * 60)
        print(f"\n📊 MLflow UI 확인: http://localhost:5000")
        print(f"📋 Models 탭에서 등록된 모델들을 확인하세요.")
        print(f"\n다음 단계:")
        print(f"  1. MLflow UI에서 최고 성능 모델을 Production으로 승격")
        print(f"  2. API를 MLflow Registry와 연동")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
