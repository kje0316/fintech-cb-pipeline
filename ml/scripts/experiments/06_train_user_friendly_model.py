"""
사용자 친화 모델 학습 스크립트
- 재무제표 중심 (16개) + 간소화된 연체 정보 (3개)
- 총 19개 입력 → 25개 피처 (파생 변수 자동 생성)
- 목표: AUC-ROC 78% 이상
"""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent
data_dir = project_root / "ml/data"
model_dir = project_root / "ml/models"

print("=" * 80)
print("사용자 친화 모델 학습 (19개 입력 → 25개 피처)")
print("=" * 80)

# ============================================================================
# 1. 피처 정의
# ============================================================================

# 재무 기본 피처 (16개)
FINANCIAL_BASE_FEATURES = [
    # 재무상태표 (7개)
    'fn1_13',   # 자산총계
    'fn1_1',    # 유동자산
    'fn1_4',    # 재고자산
    'fn1_19',   # 부채총계
    'fn1_24',   # 자본총계
    'fn1_14',   # 유동부채
    'fn1_15',   # 단기차입금
    # 손익계산서 (6개)
    'fn2_1',    # 매출액
    'fn2_5',    # 영업이익 (당기)
    'fn2_5_1',  # 영업이익 (전기)
    'fn2_10',   # 당기순이익 (당기)
    'fn2_10_1', # 당기순이익 (전기)
    'fn2_3',    # 판매비와관리비
    # 현금흐름 (1개)
    'fn3_2',    # 영업활동현금흐름
    # 기업정보 (2개)
    'empe_cnt', # 종업원수
    'wg_gb'     # 외감여부
]

# 간소화 연체 피처 (3개 원본 매핑)
# 이 피처들은 간소화된 입력을 위한 것
SIMPLE_DELINQUENCY_FEATURES = {
    'has_delinquency': 'da0d00029',      # 현재 연체 여부 (연체과목수 > 0이면 True)
    'delinquency_days': 'da0d00035_2',   # 연체일수 (최장연체일수)
    'has_tax_delinquency': 'd2b000002'   # 세금 체납 여부 (공공정보 존재 여부)
}

# 전체 입력 피처 리스트
BASE_INPUT_FEATURES = FINANCIAL_BASE_FEATURES + list(SIMPLE_DELINQUENCY_FEATURES.values())

print(f"\n✓ 기본 입력 피처: {len(BASE_INPUT_FEATURES)}개")
print("  - 재무 피처: 16개")
print("  - 간소화 연체 피처: 3개")

# ============================================================================
# 2. 데이터 로드 및 전처리
# ============================================================================

print("\n[1/8] 데이터 로드...")
df = pd.read_parquet(data_dir / "preprocessed_data_20210801.parquet")
print(f"  - 전체 데이터: {df.shape}")

# 타겟 변수 분리
target_col = 'default_yn' if 'default_yn' in df.columns else 'perf_12m'
y = df[target_col]
print(f"  - 부도율: {y.mean():.4f}")

# 필요한 피처만 선택
# wg_gb는 대소문자 확인
if 'wg_gb' not in df.columns and 'WG_GB' in df.columns:
    df['wg_gb'] = df['WG_GB']
if 'empe_cnt' not in df.columns and 'EMPE_CNT' in df.columns:
    df['empe_cnt'] = df['EMPE_CNT']

# 누락된 컬럼 확인
missing_cols = [col for col in BASE_INPUT_FEATURES if col not in df.columns]
if missing_cols:
    print(f"  ⚠️  누락된 컬럼: {missing_cols}")
    print(f"  → 사용 가능한 컬럼: {[c for c in df.columns if c.startswith(('fn', 'da', 'd2b', 'empe', 'wg'))][:20]}")
    raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_cols}")

X_base = df[BASE_INPUT_FEATURES].copy()

# ============================================================================
# 3. 파생 변수 생성
# ============================================================================

print("\n[2/8] 파생 변수 생성...")

def create_derived_features(df_input):
    """19개 입력으로 파생 변수 생성"""
    df = df_input.copy()

    # 안정성 비율 (4개)
    df['debt_ratio'] = df['fn1_19'] / (df['fn1_24'] + 1e-6)
    df['equity_ratio'] = df['fn1_24'] / (df['fn1_13'] + 1e-6)
    df['debt_to_equity'] = df['fn1_19'] / (df['fn1_24'] + 1e-6)
    df['short_term_borrowing_dependency'] = df['fn1_15'] / (df['fn1_13'] + 1e-6)

    # 유동성 비율 (4개)
    df['current_ratio'] = df['fn1_1'] / (df['fn1_14'] + 1e-6)
    df['quick_ratio'] = (df['fn1_1'] - df['fn1_4']) / (df['fn1_14'] + 1e-6)
    df['inventory_to_current_asset'] = df['fn1_4'] / (df['fn1_1'] + 1e-6)
    df['net_working_capital'] = df['fn1_1'] - df['fn1_14']

    # 수익성 비율 (2개)
    df['operating_margin'] = df['fn2_5'] / (df['fn2_1'] + 1e-6)
    df['roe'] = df['fn2_10'] / (df['fn1_24'] + 1e-6)

    # 활동성 비율 (2개)
    df['inventory_turnover'] = df['fn2_1'] / (df['fn1_4'] + 1e-6)
    df['total_capital_turnover'] = df['fn2_1'] / (df['fn1_13'] + 1e-6)

    # 성장성 비율 (2개)
    df['operating_income_growth'] = (df['fn2_5'] - df['fn2_5_1']) / (df['fn2_5_1'].abs() + 1e-6)
    df['net_income_growth'] = (df['fn2_10'] - df['fn2_10_1']) / (df['fn2_10_1'].abs() + 1e-6)

    # 현금흐름 비율 (1개)
    df['cash_to_debt'] = df['fn3_2'] / (df['fn1_19'] + 1e-6)

    # 무한대 및 NaN 처리
    df = df.replace([np.inf, -np.inf], 0)
    df = df.fillna(0)

    return df

X_with_derived = create_derived_features(X_base)

# 파생 변수 목록
DERIVED_FEATURES = [
    'debt_ratio', 'equity_ratio', 'debt_to_equity', 'short_term_borrowing_dependency',
    'current_ratio', 'quick_ratio', 'inventory_to_current_asset', 'net_working_capital',
    'operating_margin', 'roe',
    'inventory_turnover', 'total_capital_turnover',
    'operating_income_growth', 'net_income_growth',
    'cash_to_debt'
]

print(f"  - 파생 변수 생성: {len(DERIVED_FEATURES)}개")
print(f"  - 총 피처 수: {len(BASE_INPUT_FEATURES) + len(DERIVED_FEATURES)}개")

# ============================================================================
# 4. 최종 피처 선택 및 인코딩
# ============================================================================

print("\n[3/8] 피처 선택 및 인코딩...")

# wg_gb 인코딩 (Y/N → 1/0)
if X_with_derived['wg_gb'].dtype == 'object':
    X_with_derived['wg_gb_encoded'] = LabelEncoder().fit_transform(X_with_derived['wg_gb'].fillna('N'))
else:
    X_with_derived['wg_gb_encoded'] = X_with_derived['wg_gb']

# 최종 피처 리스트 (wg_gb 제외, wg_gb_encoded 포함)
FINAL_FEATURES = [f for f in BASE_INPUT_FEATURES if f != 'wg_gb'] + ['wg_gb_encoded'] + DERIVED_FEATURES

X_final = X_with_derived[FINAL_FEATURES].copy()

print(f"  - 최종 피처 수: {len(FINAL_FEATURES)}개")
print(f"  - 데이터 shape: {X_final.shape}")

# ============================================================================
# 5. 학습/테스트 분할
# ============================================================================

print("\n[4/8] 학습/테스트 분할...")
X_train, X_test, y_train, y_test = train_test_split(
    X_final, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print(f"  - 학습 데이터: {X_train.shape}")
print(f"  - 테스트 데이터: {X_test.shape}")
print(f"  - 부도율 (학습): {y_train.mean():.4f}")
print(f"  - 부도율 (테스트): {y_test.mean():.4f}")

# ============================================================================
# 6. 스케일링
# ============================================================================

print("\n[5/8] 피처 스케일링...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# DataFrame으로 다시 변환
X_train_scaled = pd.DataFrame(X_train_scaled, columns=FINAL_FEATURES, index=X_train.index)
X_test_scaled = pd.DataFrame(X_test_scaled, columns=FINAL_FEATURES, index=X_test.index)

print("  ✓ 스케일링 완료")

# ============================================================================
# 7. 모델 학습
# ============================================================================

print("\n[6/8] RandomForest 모델 학습...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=20,
    min_samples_leaf=10,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)

model.fit(X_train_scaled, y_train)
print("  ✓ 학습 완료")

# ============================================================================
# 8. 예측 및 평가
# ============================================================================

print("\n[7/8] 모델 평가...")
y_pred = model.predict(X_test_scaled)
y_proba = model.predict_proba(X_test_scaled)[:, 1]

# 메트릭 계산
metrics = {
    'accuracy': accuracy_score(y_test, y_pred),
    'precision': precision_score(y_test, y_pred),
    'recall': recall_score(y_test, y_pred),
    'f1': f1_score(y_test, y_pred),
    'roc_auc': roc_auc_score(y_test, y_proba),
    'pr_auc': average_precision_score(y_test, y_proba)
}

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()

print("\n" + "=" * 60)
print("사용자 친화 모델 성능 (19개 입력 → 25개 피처)")
print("=" * 60)
print(f"  Accuracy:  {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
print(f"  Precision: {metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)")
print(f"  Recall:    {metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)")
print(f"  F1-Score:  {metrics['f1']:.4f} ({metrics['f1']*100:.2f}%)")
print(f"  AUC-ROC:   {metrics['roc_auc']:.4f} ({metrics['roc_auc']*100:.2f}%)")
print(f"  AUC-PR:    {metrics['pr_auc']:.4f} ({metrics['pr_auc']*100:.2f}%)")
print("\nConfusion Matrix:")
print(f"  TN: {tn:5d}  |  FP: {fp:5d}")
print(f"  FN: {fn:5d}  |  TP: {tp:5d}")
print("=" * 60)

# ============================================================================
# 9. 성능 비교
# ============================================================================

print("\n[8/8] 전체 모델과 성능 비교...")
try:
    with open(model_dir / "evaluation_results.json", 'r') as f:
        eval_data = json.load(f)

    metrics_full_raw = eval_data['all_results']['Random Forest']
    metrics_full = {
        'accuracy': metrics_full_raw['accuracy'],
        'precision': metrics_full_raw['precision'],
        'recall': metrics_full_raw['recall'],
        'f1': metrics_full_raw['f1_score'],
        'roc_auc': metrics_full_raw['auc_roc'],
        'pr_auc': metrics_full_raw['auc_pr']
    }

    print("\n" + "=" * 80)
    print("성능 비교: 전체 모델 (79 features) vs 사용자 친화 모델 (25 features)")
    print("=" * 80)
    print(f"{'Metric':<15} {'Full Model':<15} {'User-Friendly':<15} {'Change':<15} {'Retention'}")
    print("-" * 80)

    for metric in ['accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'pr_auc']:
        full_val = metrics_full[metric]
        user_val = metrics[metric]
        change = user_val - full_val
        retention = (user_val / full_val * 100) if full_val > 0 else 0

        change_str = f"{change:+.4f}" if abs(change) >= 0.0001 else "±0.0000"
        print(f"{metric:<15} {full_val:<15.4f} {user_val:<15.4f} {change_str:<15} {retention:>6.2f}%")

    print("=" * 80)

    retention_pct = (metrics['roc_auc'] / metrics_full['roc_auc'] * 100)
    print(f"\n✓ AUC-ROC 성능 유지율: {retention_pct:.2f}%")

    if metrics['roc_auc'] >= 0.78:
        print("  → 목표 달성! AUC-ROC ≥ 78%")
    elif metrics['roc_auc'] >= 0.75:
        print("  → 양호: AUC-ROC ≥ 75%")
    else:
        print("  → 주의: 목표 미달, 피처 추가 검토 필요")

except FileNotFoundError:
    print("  ⚠️  전체 모델 평가 결과를 찾을 수 없습니다.")
    metrics_full = None
    retention_pct = None

# ============================================================================
# 10. 모델 및 결과 저장
# ============================================================================

print("\n[9/9] 모델 및 결과 저장...")

# 모델 저장
model_path = model_dir / "user_friendly_model_best.pkl"
with open(model_path, 'wb') as f:
    pickle.dump(model, f)
print(f"  ✓ 모델 저장: {model_path}")

# 스케일러 저장
scaler_path = model_dir / "user_friendly_scaler.pkl"
with open(scaler_path, 'wb') as f:
    pickle.dump(scaler, f)
print(f"  ✓ 스케일러 저장: {scaler_path}")

# 피처 리스트 및 매핑 저장
features_info = {
    'base_input_features': BASE_INPUT_FEATURES,
    'derived_features': DERIVED_FEATURES,
    'final_features': FINAL_FEATURES,
    'n_features': len(FINAL_FEATURES),
    'feature_groups': {
        '재무상태표': ['fn1_13', 'fn1_1', 'fn1_4', 'fn1_19', 'fn1_24', 'fn1_14', 'fn1_15'],
        '손익계산서': ['fn2_1', 'fn2_5', 'fn2_5_1', 'fn2_10', 'fn2_10_1', 'fn2_3'],
        '현금흐름': ['fn3_2'],
        '기업정보': ['empe_cnt', 'wg_gb_encoded'],
        '간소화_연체': list(SIMPLE_DELINQUENCY_FEATURES.values()),
        '파생_변수': DERIVED_FEATURES
    }
}

features_path = model_dir / "user_friendly_features.json"
with open(features_path, 'w', encoding='utf-8') as f:
    json.dump(features_info, f, indent=2, ensure_ascii=False)
print(f"  ✓ 피처 정보 저장: {features_path}")

# 평가 결과 저장
eval_results = {
    'model_type': 'RandomForestClassifier',
    'model_name': 'User-Friendly Model',
    'n_input_features': len(BASE_INPUT_FEATURES),
    'n_total_features': len(FINAL_FEATURES),
    'metrics': metrics,
    'confusion_matrix': {
        'tn': int(tn), 'fp': int(fp),
        'fn': int(fn), 'tp': int(tp)
    },
    'comparison_with_full_model': {
        'full_model_metrics': metrics_full if metrics_full else {},
        'retention_pct': retention_pct if retention_pct else None
    }
}

eval_path = model_dir / "user_friendly_evaluation.json"
with open(eval_path, 'w') as f:
    json.dump(eval_results, f, indent=2)
print(f"  ✓ 평가 결과 저장: {eval_path}")

# 피처 중요도 저장
feature_importance = pd.DataFrame({
    'feature': FINAL_FEATURES,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

importance_path = model_dir / "user_friendly_feature_importance.csv"
feature_importance.to_csv(importance_path, index=False)
print(f"  ✓ 피처 중요도 저장: {importance_path}")

print("\n" + "=" * 80)
print("사용자 친화 모델 학습 완료!")
print("=" * 80)
print(f"\n생성된 파일:")
print(f"  1. {model_path}")
print(f"  2. {scaler_path}")
print(f"  3. {features_path}")
print(f"  4. {eval_path}")
print(f"  5. {importance_path}")
print(f"\n다음 단계:")
print(f"  1. API 서비스 구현 (UserFriendlyPredictionService)")
print(f"  2. 엔드포인트 추가 (/api/v1/predict/user-friendly)")
print(f"  3. 프론트엔드 구현 (/predict)")
