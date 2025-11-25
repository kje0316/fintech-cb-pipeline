"""
SHAP 분석 스크립트 (LightGBM/XGBoost 호환)

부도 예측 모델의 설명 가능성 분석:
- 피처 중요도
- 개별 예측 설명
- What-if 시뮬레이션

실행:
    python ml/scripts/03_shap_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import shap
import warnings
from pathlib import Path
import sys

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

warnings.filterwarnings('ignore')

# 시각화 설정
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False
sns.set_style('whitegrid')


def load_model_and_data():
    """모델 및 데이터 로드"""
    print("="*80)
    print(" 모델 및 데이터 로드")
    print("="*80)

    # 모델 로드
    model_path = PROJECT_ROOT / 'ml/models/default_model_best.pkl'
    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    print(f"✓ 모델 로드 완료: {type(model).__name__}")

    # 데이터 로드
    data_path = PROJECT_ROOT / 'ml/data/processed_data_20210801.parquet'
    df = pd.read_parquet(data_path)

    X = df.drop(columns=['default_yn'])
    y = df['default_yn']
    feature_names = X.columns.tolist()

    print(f"✓ 데이터 로드 완료: {len(df):,}행 × {len(df.columns)}열")
    print(f"✓ 피처 개수: {len(feature_names)}")
    print(f"✓ 부도율: {y.mean() * 100:.2f}%")

    return model, X, y, feature_names


def calculate_shap_values(model, X, sample_size=5000):
    """SHAP values 계산"""
    print("\n" + "="*80)
    print(" SHAP values 계산")
    print("="*80)

    # 샘플링
    sample_size = min(sample_size, len(X))
    X_sample = X.sample(n=sample_size, random_state=42)

    print(f"샘플 크기: {sample_size:,}개")

    # SHAP Explainer 생성
    print("\n1. TreeExplainer 생성 중...")
    explainer = shap.TreeExplainer(model)
    print("✓ Explainer 생성 완료")

    # Expected value 처리
    if isinstance(explainer.expected_value, (list, np.ndarray)):
        expected_value = explainer.expected_value[0]
    else:
        expected_value = explainer.expected_value

    print(f"  Expected value: {expected_value:.4f}")

    # SHAP values 계산
    print("\n2. SHAP values 계산 중...")
    shap_values = explainer.shap_values(X_sample)

    # LightGBM 다중 클래스 형식 처리
    if isinstance(shap_values, list):
        print(f"  다중 클래스 형식 ({len(shap_values)}개 클래스)")
        shap_values = shap_values[0]

    print(f"✓ SHAP values 계산 완료")
    print(f"  Shape: {shap_values.shape}")
    print(f"  평균 절대값: {abs(shap_values).mean():.4f}")

    return explainer, shap_values, expected_value, X_sample


def plot_summary(shap_values, X_sample, output_dir):
    """Summary Plot"""
    print("\n" + "="*80)
    print(" Summary Plot 생성")
    print("="*80)

    # Bee swarm plot
    plt.figure(figsize=(12, 10))
    shap.summary_plot(shap_values, X_sample, plot_type="dot", show=False)
    plt.title('SHAP Summary Plot - 피처 중요도', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()

    summary_path = output_dir / 'shap_summary_plot.png'
    plt.savefig(summary_path, dpi=150, bbox_inches='tight')
    print(f"✓ Summary plot 저장: {summary_path}")
    plt.close()

    # Bar plot
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False)
    plt.title('SHAP Feature Importance', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()

    bar_path = output_dir / 'shap_bar_plot.png'
    plt.savefig(bar_path, dpi=150, bbox_inches='tight')
    print(f"✓ Bar plot 저장: {bar_path}")
    plt.close()

    # 피처 중요도 DataFrame
    feature_importance = pd.DataFrame({
        'feature': X_sample.columns.tolist(),
        'importance': np.abs(shap_values).mean(axis=0)
    }).sort_values('importance', ascending=False)

    print("\nSHAP 기반 피처 중요도 Top 15:")
    print(feature_importance.head(15).to_string(index=False))

    return feature_importance


def analyze_individual_prediction(model, explainer, shap_values, expected_value, X_sample, y_sample, output_dir):
    """개별 예측 분석"""
    print("\n" + "="*80)
    print(" 개별 예측 분석 - 부도 기업 샘플")
    print("="*80)

    # 부도 기업 중 하나 선택
    default_indices = y_sample[y_sample == 1].index

    if len(default_indices) == 0:
        print("⚠️  샘플에 부도 기업 없음")
        return

    default_idx = default_indices[0]
    sample_loc = X_sample.index.get_loc(default_idx)
    default_sample = X_sample.iloc[sample_loc]

    # 예측 확률
    pred_proba = model.predict_proba(default_sample.values.reshape(1, -1))[0, 1]

    print(f"실제 레이블: 부도")
    print(f"예측 부도 확률: {pred_proba * 100:.2f}%")
    print(f"예측 결과: {'부도' if pred_proba >= 0.5 else '정상'}")

    # Waterfall plot
    try:
        plt.figure(figsize=(12, 8))
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_values[sample_loc],
                base_values=expected_value,
                data=X_sample.iloc[sample_loc],
                feature_names=X_sample.columns.tolist()
            ),
            max_display=15,
            show=False
        )
        plt.tight_layout()

        waterfall_path = output_dir / 'shap_waterfall_default.png'
        plt.savefig(waterfall_path, dpi=150, bbox_inches='tight')
        print(f"\n✓ Waterfall plot 저장: {waterfall_path}")
        plt.close()
    except Exception as e:
        print(f"⚠️  Waterfall plot 생성 실패: {e}")


def save_results(shap_values, expected_value, X_sample, y_sample, feature_importance, output_dir):
    """결과 저장"""
    print("\n" + "="*80)
    print(" 결과 저장")
    print("="*80)

    # SHAP values 저장
    shap_data = {
        'shap_values': shap_values,
        'expected_value': expected_value,
        'X_sample': X_sample,
        'y_sample': y_sample,
        'feature_names': X_sample.columns.tolist()
    }

    shap_path = output_dir / 'shap_values.pkl'
    with open(shap_path, 'wb') as f:
        pickle.dump(shap_data, f)
    print(f"✓ SHAP values 저장: {shap_path}")

    # 피처 중요도 저장
    importance_path = output_dir / 'feature_importance_shap.csv'
    feature_importance.to_csv(importance_path, index=False)
    print(f"✓ 피처 중요도 저장: {importance_path}")


def main():
    """메인 실행 함수"""

    print("="*80)
    print(" SHAP 분석 - 부도 예측 모델 설명")
    print("="*80)
    print()

    # 출력 디렉토리 생성
    model_dir = PROJECT_ROOT / 'ml/models'
    plot_dir = model_dir / 'shap_plots'
    plot_dir.mkdir(parents=True, exist_ok=True)

    # 1. 모델 및 데이터 로드
    model, X, y, feature_names = load_model_and_data()

    # 2. SHAP values 계산
    explainer, shap_values, expected_value, X_sample = calculate_shap_values(model, X, sample_size=5000)
    y_sample = y.loc[X_sample.index]

    # 3. Summary Plot
    feature_importance = plot_summary(shap_values, X_sample, plot_dir)

    # 4. 개별 예측 분석
    analyze_individual_prediction(model, explainer, shap_values, expected_value, X_sample, y_sample, plot_dir)

    # 5. 결과 저장
    save_results(shap_values, expected_value, X_sample, y_sample, feature_importance, model_dir)

    print("\n" + "="*80)
    print(" SHAP 분석 완료!")
    print("="*80)
    print(f"\n출력 디렉토리: {plot_dir}")
    print("\n생성된 파일:")
    print("  - shap_summary_plot.png - 전체 피처 중요도")
    print("  - shap_bar_plot.png - 피처 중요도 막대그래프")
    print("  - shap_waterfall_default.png - 부도 기업 예측 설명")
    print("  - shap_values.pkl - SHAP values 데이터")
    print("  - feature_importance_shap.csv - 피처 중요도 CSV")
    print()


if __name__ == '__main__':
    main()
