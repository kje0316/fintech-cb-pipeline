"""
부도예측 모델 평가 스크립트

학습된 모델의 성능을 다각도로 분석:
- ROC/PR 커브
- Feature Importance
- SHAP 분석
- 임계값별 성능
"""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_curve, auc, precision_recall_curve,
    confusion_matrix, classification_report
)
import shap

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False


def load_model_and_data():
    """모델 및 테스트 데이터 로드"""
    print("📂 모델 및 데이터 로딩 중...")

    model_dir = Path("models/default_prediction_v2/models/production")

    # 모델 로드
    with open(model_dir / "model_v1.pkl", 'rb') as f:
        model = pickle.load(f)

    # 스케일러 로드
    with open(model_dir / "scaler_v1.pkl", 'rb') as f:
        scaler = pickle.load(f)

    # 메타데이터 로드
    with open(model_dir / "metadata_v1.json", 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # 테스트 데이터 로드
    test_df = pd.read_parquet("data/processed/test_70features.parquet")

    # X, y 분리
    X_test = test_df.drop(columns=['default_yn'])
    y_test = test_df['default_yn']

    # 스케일링
    X_test_scaled = scaler.transform(X_test)

    print(f"✅ 로드 완료:")
    print(f"  - 모델: {metadata['model_type']}")
    print(f"  - 피처 수: {len(metadata['feature_names'])}")
    print(f"  - 테스트 샘플: {len(X_test):,}건")

    return model, scaler, metadata, X_test, X_test_scaled, y_test


def plot_roc_pr_curves(model, X_test_scaled, y_test, output_dir):
    """ROC 커브 및 PR 커브 시각화"""
    print("\n📊 ROC/PR 커브 생성 중...")

    # 예측 확률
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

    # ROC 커브
    fpr, tpr, thresholds_roc = roc_curve(y_test, y_pred_proba)
    roc_auc = auc(fpr, tpr)

    # PR 커브
    precision, recall, thresholds_pr = precision_recall_curve(y_test, y_pred_proba)

    # 시각화
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # ROC 커브
    axes[0].plot(fpr, tpr, color='darkorange', lw=2,
                 label=f'ROC curve (AUC = {roc_auc:.4f})')
    axes[0].plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
    axes[0].set_xlim([0.0, 1.0])
    axes[0].set_ylim([0.0, 1.05])
    axes[0].set_xlabel('False Positive Rate')
    axes[0].set_ylabel('True Positive Rate')
    axes[0].set_title('ROC Curve')
    axes[0].legend(loc="lower right")
    axes[0].grid(True, alpha=0.3)

    # PR 커브
    axes[1].plot(recall, precision, color='green', lw=2, label='PR curve')
    axes[1].axhline(y=y_test.mean(), color='navy', linestyle='--',
                    label=f'Baseline ({y_test.mean():.4f})')
    axes[1].set_xlim([0.0, 1.0])
    axes[1].set_ylim([0.0, 1.05])
    axes[1].set_xlabel('Recall')
    axes[1].set_ylabel('Precision')
    axes[1].set_title('Precision-Recall Curve')
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    plot_path = output_dir / "roc_pr_curves.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✅ ROC/PR 커브 저장: {plot_path}")

    return roc_auc


def plot_feature_importance(model, feature_names, output_dir, top_n=20):
    """Feature Importance 시각화"""
    print(f"\n📊 Feature Importance (상위 {top_n}개) 생성 중...")

    # Feature importance 추출
    importances = model.feature_importances_

    # DataFrame 생성
    fi_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values('importance', ascending=False)

    # 상위 N개
    top_features = fi_df.head(top_n)

    # 시각화
    plt.figure(figsize=(10, 8))
    sns.barplot(data=top_features, y='feature', x='importance', palette='viridis')
    plt.title(f'Top {top_n} Feature Importance (XGBoost)')
    plt.xlabel('Importance Score')
    plt.ylabel('Feature')
    plt.tight_layout()

    plot_path = output_dir / "feature_importance.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    # CSV 저장
    csv_path = output_dir / "feature_importance.csv"
    fi_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    print(f"  ✅ Feature Importance 저장: {plot_path}")
    print(f"  ✅ CSV 저장: {csv_path}")

    print(f"\n  상위 10개 피처:")
    for idx, row in fi_df.head(10).iterrows():
        print(f"    {row['feature']:15s}: {row['importance']:.4f}")

    return fi_df


def analyze_shap_values(model, X_test_scaled, feature_names, output_dir, max_samples=500):
    """SHAP 분석 및 시각화"""
    print(f"\n📊 SHAP 분석 중 (샘플 {max_samples}개)...")

    # 샘플링 (SHAP 계산 시간 단축)
    if len(X_test_scaled) > max_samples:
        indices = np.random.choice(len(X_test_scaled), max_samples, replace=False)
        X_sample = X_test_scaled[indices]
    else:
        X_sample = X_test_scaled

    # SHAP Explainer 생성
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # Summary Plot (Feature Importance)
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_sample, feature_names=feature_names,
                      show=False, max_display=20)
    plot_path = output_dir / "shap_summary_plot.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✅ SHAP Summary Plot 저장: {plot_path}")

    # Bar Plot (Mean Absolute SHAP)
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_sample, feature_names=feature_names,
                      plot_type="bar", show=False, max_display=20)
    bar_path = output_dir / "shap_bar_plot.png"
    plt.savefig(bar_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✅ SHAP Bar Plot 저장: {bar_path}")

    # SHAP values 저장 (API에서 사용 가능)
    shap_data = {
        'feature_names': feature_names,
        'shap_values': shap_values.tolist() if isinstance(shap_values, np.ndarray) else shap_values,
        'base_value': float(explainer.expected_value)
    }

    shap_path = output_dir / "shap_values.pkl"
    with open(shap_path, 'wb') as f:
        pickle.dump(shap_data, f)
    print(f"  ✅ SHAP 값 저장: {shap_path}")

    return shap_values, explainer


def analyze_threshold_performance(model, X_test_scaled, y_test, output_dir):
    """임계값별 성능 분석"""
    print("\n📊 임계값별 성능 분석 중...")

    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

    thresholds = np.arange(0.1, 0.9, 0.05)
    results = []

    for threshold in thresholds:
        y_pred = (y_pred_proba >= threshold).astype(int)
        cm = confusion_matrix(y_test, y_pred)

        tn, fp, fn, tp = cm.ravel()

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        results.append({
            'threshold': threshold,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'tp': tp,
            'fp': fp,
            'tn': tn,
            'fn': fn
        })

    df_threshold = pd.DataFrame(results)

    # 시각화
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Precision/Recall/F1
    axes[0].plot(df_threshold['threshold'], df_threshold['precision'],
                 label='Precision', marker='o')
    axes[0].plot(df_threshold['threshold'], df_threshold['recall'],
                 label='Recall', marker='s')
    axes[0].plot(df_threshold['threshold'], df_threshold['f1_score'],
                 label='F1-Score', marker='^')
    axes[0].set_xlabel('Threshold')
    axes[0].set_ylabel('Score')
    axes[0].set_title('Precision/Recall/F1 vs Threshold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # TP/FP/FN
    axes[1].plot(df_threshold['threshold'], df_threshold['tp'],
                 label='True Positives', marker='o')
    axes[1].plot(df_threshold['threshold'], df_threshold['fp'],
                 label='False Positives', marker='s')
    axes[1].plot(df_threshold['threshold'], df_threshold['fn'],
                 label='False Negatives', marker='^')
    axes[1].set_xlabel('Threshold')
    axes[1].set_ylabel('Count')
    axes[1].set_title('TP/FP/FN vs Threshold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    plot_path = output_dir / "threshold_analysis.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    # CSV 저장
    csv_path = output_dir / "threshold_performance.csv"
    df_threshold.to_csv(csv_path, index=False)

    print(f"  ✅ 임계값 분석 저장: {plot_path}")
    print(f"  ✅ CSV 저장: {csv_path}")

    # 최적 F1 임계값
    best_idx = df_threshold['f1_score'].idxmax()
    best_threshold = df_threshold.loc[best_idx]

    print(f"\n  최적 F1 임계값: {best_threshold['threshold']:.2f}")
    print(f"    - Precision: {best_threshold['precision']:.4f}")
    print(f"    - Recall:    {best_threshold['recall']:.4f}")
    print(f"    - F1-Score:  {best_threshold['f1_score']:.4f}")

    return df_threshold


def generate_evaluation_report(metadata, roc_auc, fi_df, output_dir):
    """평가 리포트 생성"""
    print("\n📝 평가 리포트 생성 중...")

    report = {
        'model_info': {
            'model_version': metadata['model_version'],
            'model_type': metadata['model_type'],
            'n_features': metadata['n_features'],
            'training_date': metadata['training_date']
        },
        'performance': {
            'auc_roc': roc_auc,
            'original_metrics': metadata['metrics']
        },
        'top_10_features': fi_df.head(10).to_dict('records')
    }

    report_path = output_dir / "evaluation_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  ✅ 평가 리포트 저장: {report_path}")

    return report


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("부도예측 모델 평가 시작")
    print("=" * 60)

    try:
        # 출력 디렉토리 생성
        output_dir = Path("models/default_prediction_v2/results")
        output_dir.mkdir(exist_ok=True, parents=True)

        # 1. 모델 및 데이터 로드
        model, scaler, metadata, X_test, X_test_scaled, y_test = load_model_and_data()

        # 2. ROC/PR 커브
        roc_auc = plot_roc_pr_curves(model, X_test_scaled, y_test, output_dir)

        # 3. Feature Importance
        fi_df = plot_feature_importance(model, metadata['feature_names'], output_dir)

        # 4. SHAP 분석
        shap_values, explainer = analyze_shap_values(
            model, X_test_scaled, metadata['feature_names'], output_dir
        )

        # 5. 임계값별 성능
        threshold_df = analyze_threshold_performance(model, X_test_scaled, y_test, output_dir)

        # 6. 평가 리포트 생성
        report = generate_evaluation_report(metadata, roc_auc, fi_df, output_dir)

        print("\n" + "=" * 60)
        print("✅ 모델 평가 완료!")
        print("=" * 60)
        print(f"결과 디렉토리: {output_dir}")
        print(f"\n생성된 파일:")
        print(f"  - roc_pr_curves.png")
        print(f"  - feature_importance.png")
        print(f"  - feature_importance.csv")
        print(f"  - shap_summary_plot.png")
        print(f"  - shap_bar_plot.png")
        print(f"  - shap_values.pkl")
        print(f"  - threshold_analysis.png")
        print(f"  - threshold_performance.csv")
        print(f"  - evaluation_report.json")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
