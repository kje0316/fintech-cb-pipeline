"""
부도 예측 모델 학습 스크립트

여러 ML 모델을 학습하고 성능을 비교하여 최적 모델 선택:
- Logistic Regression (Baseline)
- Random Forest
- XGBoost
- LightGBM

클래스 불균형 처리:
- SMOTE (Synthetic Minority Over-sampling Technique)
- class_weight 조정

평가 지표:
- Accuracy, Precision, Recall, F1-Score
- AUC-ROC, AUC-PR
- Confusion Matrix

출력:
- ml/models/default_model_best.pkl
- ml/models/feature_importance.csv
- ml/models/evaluation_results.json

실행:
    python ml/scripts/02_train_default_model.py
"""

import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ML 라이브러리
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    classification_report
)
from imblearn.over_sampling import SMOTE
import xgboost as xgb
import lightgbm as lgb


def load_data(data_path):
    """
    전처리된 데이터 로드

    Args:
        data_path: Parquet 파일 경로

    Returns:
        X, y, feature_names
    """
    print("="*80)
    print(" 데이터 로드")
    print("="*80)

    df = pd.read_parquet(data_path)
    print(f"✓ 데이터 로드 완료: {len(df):,}행 × {len(df.columns)}열")

    # 피처와 타겟 분리
    X = df.drop(columns=['default_yn'])
    y = df['default_yn']
    feature_names = X.columns.tolist()

    print(f"✓ 피처 개수: {len(feature_names)}")
    print(f"✓ 부도율: {y.mean() * 100:.2f}%")
    print(f"  - 정상: {(y == 0).sum():,}개")
    print(f"  - 부도: {(y == 1).sum():,}개")

    return X, y, feature_names


def split_data(X, y, test_size=0.2, random_state=42):
    """
    Train/Test 분리

    Args:
        X: 피처
        y: 타겟
        test_size: 테스트 비율
        random_state: 랜덤 시드

    Returns:
        X_train, X_test, y_train, y_test
    """
    print("\n" + "="*80)
    print(" Train/Test 분리")
    print("="*80)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    print(f"✓ Train: {len(X_train):,}행 ({len(X_train) / len(X) * 100:.1f}%)")
    print(f"✓ Test:  {len(X_test):,}행 ({len(X_test) / len(X) * 100:.1f}%)")
    print(f"\nTrain 부도율: {y_train.mean() * 100:.2f}%")
    print(f"Test  부도율: {y_test.mean() * 100:.2f}%")

    return X_train, X_test, y_train, y_test


def apply_smote(X_train, y_train, random_state=42):
    """
    SMOTE 적용 (클래스 불균형 해소)

    Args:
        X_train: Train 피처
        y_train: Train 타겟
        random_state: 랜덤 시드

    Returns:
        X_train_resampled, y_train_resampled
    """
    print("\n" + "="*80)
    print(" SMOTE 적용 (클래스 불균형 해소)")
    print("="*80)

    print(f"적용 전 - 정상: {(y_train == 0).sum():,}개, 부도: {(y_train == 1).sum():,}개")

    smote = SMOTE(random_state=random_state)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

    print(f"적용 후 - 정상: {(y_train_resampled == 0).sum():,}개, 부도: {(y_train_resampled == 1).sum():,}개")
    print(f"✓ 부도 샘플 증가: {(y_train == 1).sum():,} → {(y_train_resampled == 1).sum():,}")

    return X_train_resampled, y_train_resampled


def train_models(X_train, y_train, X_test, y_test, feature_names):
    """
    여러 모델 학습 및 평가

    Args:
        X_train, y_train: Train 데이터
        X_test, y_test: Test 데이터
        feature_names: 피처 이름

    Returns:
        models, results
    """
    print("\n" + "="*80)
    print(" 모델 학습 및 평가")
    print("="*80)

    models = {}
    results = {}

    # 1. Logistic Regression (Baseline)
    print("\n[1/4] Logistic Regression 학습 중...")
    lr = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
    lr.fit(X_train, y_train)
    models['Logistic Regression'] = lr
    results['Logistic Regression'] = evaluate_model(lr, X_test, y_test, "Logistic Regression")

    # 2. Random Forest
    print("\n[2/4] Random Forest 학습 중...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42,
                                 class_weight='balanced', n_jobs=-1)
    rf.fit(X_train, y_train)
    models['Random Forest'] = rf
    results['Random Forest'] = evaluate_model(rf, X_test, y_test, "Random Forest")

    # 3. XGBoost
    print("\n[3/4] XGBoost 학습 중...")
    # 클래스 불균형 비율 계산
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    xgb_model = xgb.XGBClassifier(
        n_estimators=100, max_depth=6, learning_rate=0.1,
        scale_pos_weight=scale_pos_weight, random_state=42,
        use_label_encoder=False, eval_metric='logloss', n_jobs=-1,
        base_score=0.5  # SHAP 호환성을 위해 명시적으로 설정
    )
    xgb_model.fit(X_train, y_train)
    models['XGBoost'] = xgb_model
    results['XGBoost'] = evaluate_model(xgb_model, X_test, y_test, "XGBoost")

    # 4. LightGBM
    print("\n[4/4] LightGBM 학습 중...")
    lgb_model = lgb.LGBMClassifier(
        n_estimators=100, max_depth=6, learning_rate=0.1,
        class_weight='balanced', random_state=42, n_jobs=-1, verbose=-1
    )
    lgb_model.fit(X_train, y_train)
    models['LightGBM'] = lgb_model
    results['LightGBM'] = evaluate_model(lgb_model, X_test, y_test, "LightGBM")

    # 결과 비교
    print("\n" + "="*80)
    print(" 모델 성능 비교")
    print("="*80)
    comparison_df = pd.DataFrame(results).T
    print(comparison_df.to_string())
    print("="*80)

    # 최적 모델 선택 (F1-Score 기준)
    best_model_name = comparison_df['f1_score'].idxmax()
    best_model = models[best_model_name]

    print(f"\n✓ 최적 모델: {best_model_name}")
    print(f"  - F1-Score: {comparison_df.loc[best_model_name, 'f1_score']:.4f}")
    print(f"  - AUC-ROC: {comparison_df.loc[best_model_name, 'auc_roc']:.4f}")

    return models, results, best_model_name, best_model


def evaluate_model(model, X_test, y_test, model_name):
    """
    모델 평가

    Args:
        model: 학습된 모델
        X_test, y_test: Test 데이터
        model_name: 모델 이름

    Returns:
        평가 지표 dict
    """
    # 예측
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # 평가 지표 계산
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1_score': f1_score(y_test, y_pred),
        'auc_roc': roc_auc_score(y_test, y_pred_proba),
        'auc_pr': average_precision_score(y_test, y_pred_proba)
    }

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    print(f"\n{model_name} 평가 결과:")
    print(f"  - Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  - Precision: {metrics['precision']:.4f}")
    print(f"  - Recall:    {metrics['recall']:.4f}")
    print(f"  - F1-Score:  {metrics['f1_score']:.4f}")
    print(f"  - AUC-ROC:   {metrics['auc_roc']:.4f}")
    print(f"  - AUC-PR:    {metrics['auc_pr']:.4f}")
    print(f"\n  Confusion Matrix:")
    print(f"    TN: {tn:5d}  FP: {fp:5d}")
    print(f"    FN: {fn:5d}  TP: {tp:5d}")

    return metrics


def extract_feature_importance(model, feature_names, model_name):
    """
    피처 중요도 추출

    Args:
        model: 학습된 모델
        feature_names: 피처 이름
        model_name: 모델 이름

    Returns:
        DataFrame (feature, importance)
    """
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importance = np.abs(model.coef_[0])
    else:
        return None

    feature_importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)

    return feature_importance_df


def save_results(best_model, best_model_name, results, feature_importance_df):
    """
    모델 및 결과 저장

    Args:
        best_model: 최적 모델
        best_model_name: 최적 모델 이름
        results: 평가 결과
        feature_importance_df: 피처 중요도
    """
    print("\n" + "="*80)
    print(" 결과 저장")
    print("="*80)

    # 출력 디렉토리 생성
    model_dir = PROJECT_ROOT / 'ml/models'
    model_dir.mkdir(parents=True, exist_ok=True)

    # 1. 최적 모델 저장
    model_path = model_dir / 'default_model_best.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(best_model, f)
    print(f"✓ 모델 저장: {model_path}")

    # 2. 평가 결과 저장
    results_path = model_dir / 'evaluation_results.json'
    with open(results_path, 'w') as f:
        json.dump({
            'best_model': best_model_name,
            'all_results': results
        }, f, indent=2)
    print(f"✓ 평가 결과 저장: {results_path}")

    # 3. 피처 중요도 저장
    if feature_importance_df is not None:
        importance_path = model_dir / 'feature_importance.csv'
        feature_importance_df.to_csv(importance_path, index=False)
        print(f"✓ 피처 중요도 저장: {importance_path}")

        print("\n피처 중요도 Top 10:")
        print(feature_importance_df.head(10).to_string(index=False))

    print("="*80)


def main():
    """메인 실행 함수"""

    # 1. 데이터 로드 (전처리된 데이터 사용)
    data_path = PROJECT_ROOT / 'ml/data/processed_data_20210801.parquet'
    X, y, feature_names = load_data(data_path)

    # 2. Train/Test 분리
    X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.2, random_state=42)

    # 3. SMOTE 적용
    X_train_resampled, y_train_resampled = apply_smote(X_train, y_train, random_state=42)

    # 4. 모델 학습 및 평가
    models, results, best_model_name, best_model = train_models(
        X_train_resampled, y_train_resampled, X_test, y_test, feature_names
    )

    # 5. 피처 중요도 추출
    feature_importance_df = extract_feature_importance(best_model, feature_names, best_model_name)

    # 6. 결과 저장
    save_results(best_model, best_model_name, results, feature_importance_df)

    print("\n" + "="*80)
    print(" 모델 학습 완료!")
    print("="*80)
    print(f"\n다음 단계:")
    print(f"  1. SHAP 분석 노트북 실행: ml/notebooks/03_model_interpretation.ipynb")
    print(f"  2. 모델 배포: service/api/에 통합")
    print()


if __name__ == '__main__':
    main()
