"""
경량 모델 학습 스크립트
- Top 12 SHAP 피처만 사용
- 전체 모델과 성능 비교
"""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    classification_report
)

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent
data_dir = project_root / "ml/data"
model_dir = project_root / "ml/models"

print("=" * 80)
print("경량 모델 학습 (Top 12 SHAP Features)")
print("=" * 80)

# Top 12 피처 (모델 Gini importance 기준)
# SHAP importance와 Gini importance는 다를 수 있음
# 여기서는 모델의 Gini importance 사용
TOP_12_FEATURES = [
    'da0d00029',
    'da0d00029_1',
    'da0d00035_2',
    'da0d00035_4_2',
    'da0d00035_4_1',
    'inventory_to_current_asset',
    'da0d00035_3_2',
    'd2b000003',
    'd2b000002',
    'r007',
    'fn3_11_1',
    'da0d00026_1'
]

print(f"\n✓ Top 12 피처 선택 완료:")
for i, feat in enumerate(TOP_12_FEATURES, 1):
    print(f"  {i}. {feat}")

# 1. 데이터 로드
print("\n[1/7] 데이터 로드...")
from sklearn.model_selection import train_test_split

# 엔지니어링된 전체 데이터 로드
df = pd.read_parquet(data_dir / "engineered_features_20210801.parquet")
print(f"  - 전체 데이터: {df.shape}")

# 타겟 변수 분리
# 타겟 변수는 default_yn 또는 perf_12m
target_col = 'default_yn' if 'default_yn' in df.columns else 'perf_12m'
X = df.drop(target_col, axis=1)
y = df[target_col]

print(f"  - 부도율: {y.mean():.4f}")

# 학습/테스트 분할 (80/20, stratify로 부도율 유지)
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print(f"  - 학습 데이터: {X_train.shape}")
print(f"  - 테스트 데이터: {X_test.shape}")
print(f"  - 부도율 (학습): {y_train.mean():.4f}")
print(f"  - 부도율 (테스트): {y_test.mean():.4f}")

# 2. Top 12 피처만 선택
print("\n[2/6] Top 12 피처 추출...")
X_train_light = X_train[TOP_12_FEATURES].copy()
X_test_light = X_test[TOP_12_FEATURES].copy()

print(f"  - 원본 피처 수: {X_train.shape[1]}개")
print(f"  - 경량 피처 수: {X_train_light.shape[1]}개")
print(f"  - 피처 감소율: {(1 - X_train_light.shape[1]/X_train.shape[1])*100:.1f}%")

# NaN 및 무한대 처리
X_train_light = X_train_light.replace([np.inf, -np.inf], np.nan)
X_test_light = X_test_light.replace([np.inf, -np.inf], np.nan)
X_train_light = X_train_light.fillna(0)
X_test_light = X_test_light.fillna(0)

# 3. 스케일링
print("\n[3/6] 피처 스케일링...")
scaler_light = StandardScaler()
X_train_scaled = scaler_light.fit_transform(X_train_light)
X_test_scaled = scaler_light.transform(X_test_light)

# DataFrame으로 다시 변환 (feature names 유지)
X_train_scaled = pd.DataFrame(X_train_scaled, columns=TOP_12_FEATURES, index=X_train_light.index)
X_test_scaled = pd.DataFrame(X_test_scaled, columns=TOP_12_FEATURES, index=X_test_light.index)

print("  ✓ 스케일링 완료")

# 4. 모델 학습 (전체 모델과 동일한 하이퍼파라미터)
print("\n[4/6] RandomForest 경량 모델 학습...")
model_light = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=20,
    min_samples_leaf=10,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)

model_light.fit(X_train_scaled, y_train)
print("  ✓ 학습 완료")

# 5. 예측 및 평가
print("\n[5/6] 모델 평가...")
y_pred_light = model_light.predict(X_test_scaled)
y_proba_light = model_light.predict_proba(X_test_scaled)[:, 1]

# 메트릭 계산
metrics_light = {
    'accuracy': accuracy_score(y_test, y_pred_light),
    'precision': precision_score(y_test, y_pred_light),
    'recall': recall_score(y_test, y_pred_light),
    'f1': f1_score(y_test, y_pred_light),
    'roc_auc': roc_auc_score(y_test, y_proba_light),
    'pr_auc': average_precision_score(y_test, y_proba_light)
}

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred_light)
tn, fp, fn, tp = cm.ravel()

print("\n" + "=" * 60)
print("경량 모델 성능 (Top 12 Features)")
print("=" * 60)
print(f"  Accuracy:  {metrics_light['accuracy']:.4f} ({metrics_light['accuracy']*100:.2f}%)")
print(f"  Precision: {metrics_light['precision']:.4f} ({metrics_light['precision']*100:.2f}%)")
print(f"  Recall:    {metrics_light['recall']:.4f} ({metrics_light['recall']*100:.2f}%)")
print(f"  F1-Score:  {metrics_light['f1']:.4f} ({metrics_light['f1']*100:.2f}%)")
print(f"  AUC-ROC:   {metrics_light['roc_auc']:.4f} ({metrics_light['roc_auc']*100:.2f}%)")
print(f"  AUC-PR:    {metrics_light['pr_auc']:.4f} ({metrics_light['pr_auc']*100:.2f}%)")
print("\nConfusion Matrix:")
print(f"  TN: {tn:5d}  |  FP: {fp:5d}")
print(f"  FN: {fn:5d}  |  TP: {tp:5d}")
print("=" * 60)

# 6. 전체 모델과 비교
print("\n[6/7] 전체 모델과 성능 비교...")
try:
    with open(model_dir / "evaluation_results.json", 'r') as f:
        eval_data = json.load(f)

    # Random Forest 결과 가져오기
    metrics_full_raw = eval_data['all_results']['Random Forest']

    # 키 이름 매핑
    metrics_full = {
        'accuracy': metrics_full_raw['accuracy'],
        'precision': metrics_full_raw['precision'],
        'recall': metrics_full_raw['recall'],
        'f1': metrics_full_raw['f1_score'],
        'roc_auc': metrics_full_raw['auc_roc'],
        'pr_auc': metrics_full_raw['auc_pr']
    }

    print("\n" + "=" * 80)
    print("성능 비교: 전체 모델 (79 features) vs 경량 모델 (12 features)")
    print("=" * 80)
    print(f"{'Metric':<15} {'Full Model':<15} {'Light Model':<15} {'Change':<15} {'Retention'}")
    print("-" * 80)

    for metric in ['accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'pr_auc']:
        full_val = metrics_full[metric]
        light_val = metrics_light[metric]
        change = light_val - full_val
        retention = (light_val / full_val * 100) if full_val > 0 else 0

        change_str = f"{change:+.4f}" if abs(change) >= 0.0001 else "±0.0000"
        print(f"{metric:<15} {full_val:<15.4f} {light_val:<15.4f} {change_str:<15} {retention:>6.2f}%")

    print("=" * 80)

    # 성능 유지율 계산 (AUC-ROC 기준)
    retention_pct = (metrics_light['roc_auc'] / metrics_full['roc_auc'] * 100)
    print(f"\n✓ AUC-ROC 성능 유지율: {retention_pct:.2f}%")

    if retention_pct >= 93:
        print("  → 우수: 예상(88-95%) 범위 내 상위권")
    elif retention_pct >= 88:
        print("  → 양호: 예상(88-95%) 범위 내")
    else:
        print("  → 주의: 예상 범위 미달, 피처 추가 검토 필요")

except FileNotFoundError:
    print("  ⚠️  전체 모델 평가 결과를 찾을 수 없습니다.")
    metrics_full = None

# 7. 모델 및 결과 저장
print("\n[7/7] 모델 및 결과 저장...")

# 경량 모델 저장
model_path = model_dir / "lightweight_model_best.pkl"
with open(model_path, 'wb') as f:
    pickle.dump(model_light, f)
print(f"  ✓ 모델 저장: {model_path}")

# 스케일러 저장
scaler_path = model_dir / "lightweight_scaler.pkl"
with open(scaler_path, 'wb') as f:
    pickle.dump(scaler_light, f)
print(f"  ✓ 스케일러 저장: {scaler_path}")

# 피처 리스트 저장
features_path = model_dir / "lightweight_features.json"
with open(features_path, 'w') as f:
    json.dump({'features': TOP_12_FEATURES}, f, indent=2)
print(f"  ✓ 피처 리스트 저장: {features_path}")

# 평가 결과 저장
eval_path = model_dir / "lightweight_evaluation.json"
eval_results = {
    'model_type': 'RandomForestClassifier',
    'n_features': len(TOP_12_FEATURES),
    'features': TOP_12_FEATURES,
    'metrics': metrics_light,
    'confusion_matrix': {
        'tn': int(tn), 'fp': int(fp),
        'fn': int(fn), 'tp': int(tp)
    },
    'comparison_with_full_model': {
        'full_model_metrics': metrics_full if metrics_full else {},
        'retention_pct': retention_pct if metrics_full else None
    }
}

with open(eval_path, 'w') as f:
    json.dump(eval_results, f, indent=2)
print(f"  ✓ 평가 결과 저장: {eval_path}")

# 피처 중요도 저장
feature_importance_light = pd.DataFrame({
    'feature': TOP_12_FEATURES,
    'importance': model_light.feature_importances_
}).sort_values('importance', ascending=False)

importance_path = model_dir / "lightweight_feature_importance.csv"
feature_importance_light.to_csv(importance_path, index=False)
print(f"  ✓ 피처 중요도 저장: {importance_path}")

print("\n" + "=" * 80)
print("경량 모델 학습 완료!")
print("=" * 80)
print(f"\n생성된 파일:")
print(f"  1. {model_path}")
print(f"  2. {scaler_path}")
print(f"  3. {features_path}")
print(f"  4. {eval_path}")
print(f"  5. {importance_path}")
print(f"\n다음 단계: API 엔드포인트 구현 (/api/v1/predict/quick)")
