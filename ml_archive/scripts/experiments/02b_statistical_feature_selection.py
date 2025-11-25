"""
통계적 피처 선택 (5가지 방법론 조합)

변경 사항:
- 기존: 경험적으로 48개 선택
- 신규: 5가지 통계 방법으로 객관적 선택

방법론:
1. 분산 기반 (VarianceThreshold)
2. 상호정보량 (Mutual Information)
3. F-통계량 (ANOVA F-test)
4. 트리 모델 피처 중요도 (RandomForest)
5. 타겟 상관관계 (Correlation)

선택 기준:
- 3개 이상 방법에서 선택된 피처만 최종 선택
- 발표용 리포트 생성 (feature_selection_report.csv)

출력:
- ml/data/selected_features.csv (선택된 피처 목록)
- ml/data/feature_selection_report.csv (발표용 상세 리포트)

실행:
    python ml/scripts/02b_statistical_feature_selection.py
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.feature_selection import (
    VarianceThreshold,
    SelectKBest,
    mutual_info_classif,
    f_classif
)
from sklearn.ensemble import RandomForestClassifier
import warnings
warnings.filterwarnings('ignore')


def statistical_feature_selection(input_path=None, n_features=50):
    """
    5가지 통계 방법으로 피처 선택

    Args:
        input_path: 입력 파일 경로 (기본: ml/data/preprocessed_data_20210801.parquet)
        n_features: 각 방법에서 선택할 피처 개수 (기본: 50)

    Returns:
        selected_features: 최종 선택된 피처 리스트
        report: 발표용 상세 리포트 DataFrame
    """

    # 경로 설정
    if input_path is None:
        input_path = PROJECT_ROOT / "ml/data/preprocessed_data_20210801.parquet"

    print("="*80)
    print(" 통계적 피처 선택 (5가지 방법론)")
    print("="*80)
    print()

    # 1. 데이터 로드
    print(f"✓ 데이터 로드 중... ({input_path})")
    df = pd.read_parquet(input_path)

    # 타겟 분리
    y = df['default_yn'].copy()
    X = df.drop(columns=['default_yn', 'credit_grade'], errors='ignore')

    print(f"  피처: {X.shape[1]}개")
    print(f"  샘플: {X.shape[0]:,}개")
    print(f"  부도율: {y.mean()*100:.2f}%")
    print()

    # 선택된 피처를 저장할 딕셔너리
    method_features = {}

    # ========================================================================
    # 방법 1: 분산 기반 (VarianceThreshold)
    # ========================================================================
    print("-"*80)
    print(" [방법 1] 분산 기반 선택 (VarianceThreshold)")
    print("-"*80)

    var_threshold = VarianceThreshold(threshold=0.01)
    var_threshold.fit(X)
    var_features = X.columns[var_threshold.get_support()].tolist()

    print(f"  분산 > 0.01: {len(var_features)}개 선택")
    print(f"  제거됨: {X.shape[1] - len(var_features)}개 (저분산)")
    method_features['variance'] = set(var_features)
    print()

    # ========================================================================
    # 방법 2: 상호정보량 (Mutual Information)
    # ========================================================================
    print("-"*80)
    print(" [방법 2] 상호정보량 기반 선택 (Mutual Information)")
    print("-"*80)

    k = min(n_features, len(X.columns))
    mi_selector = SelectKBest(mutual_info_classif, k=k)
    mi_selector.fit(X, y)
    mi_features = X.columns[mi_selector.get_support()].tolist()
    mi_scores = pd.DataFrame({
        'feature': X.columns,
        'mi_score': mi_selector.scores_
    }).sort_values('mi_score', ascending=False)

    print(f"  상위 {k}개 선택")
    print(f"\n  Top 10 피처 (상호정보량):")
    for idx, row in mi_scores.head(10).iterrows():
        print(f"    {row['feature']:<40} {row['mi_score']:.4f}")

    method_features['mutual_info'] = set(mi_features)
    print()

    # ========================================================================
    # 방법 3: F-통계량 (ANOVA F-test)
    # ========================================================================
    print("-"*80)
    print(" [방법 3] F-통계량 기반 선택 (ANOVA)")
    print("-"*80)

    f_selector = SelectKBest(f_classif, k=k)
    f_selector.fit(X, y)
    f_features = X.columns[f_selector.get_support()].tolist()
    f_scores = pd.DataFrame({
        'feature': X.columns,
        'f_score': f_selector.scores_,
        'p_value': f_selector.pvalues_
    }).sort_values('f_score', ascending=False)

    print(f"  상위 {k}개 선택")
    print(f"\n  Top 10 피처 (F-통계량):")
    for idx, row in f_scores.head(10).iterrows():
        print(f"    {row['feature']:<40} F={row['f_score']:.2f}, p={row['p_value']:.6f}")

    method_features['f_stat'] = set(f_features)
    print()

    # ========================================================================
    # 방법 4: Random Forest 피처 중요도
    # ========================================================================
    print("-"*80)
    print(" [방법 4] Random Forest 피처 중요도")
    print("-"*80)

    print("  모델 학습 중... (100 trees)")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced'  # 클래스 불균형 처리
    )
    rf.fit(X, y)

    rf_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)

    rf_features = rf_importance.head(k)['feature'].tolist()

    print(f"  상위 {k}개 선택")
    print(f"\n  Top 10 피처 (Random Forest):")
    for idx, row in rf_importance.head(10).iterrows():
        print(f"    {row['feature']:<40} {row['importance']:.4f}")

    method_features['random_forest'] = set(rf_features)
    print()

    # ========================================================================
    # 방법 5: 타겟 상관관계
    # ========================================================================
    print("-"*80)
    print(" [방법 5] 타겟 상관관계")
    print("-"*80)

    correlations = X.corrwith(y).abs().sort_values(ascending=False)
    corr_features = correlations[correlations > 0.01].index.tolist()

    print(f"  상관계수 > 0.01: {len(corr_features)}개 선택")
    print(f"\n  Top 10 피처 (상관관계):")
    for feat in correlations.head(10).index:
        print(f"    {feat:<40} {correlations[feat]:.4f}")

    method_features['correlation'] = set(corr_features)
    print()

    # ========================================================================
    # 통합 선택 (3개 이상 방법에서 선택된 피처)
    # ========================================================================
    print("="*80)
    print(" 통합 선택 결과")
    print("="*80)

    # 모든 피처 수집
    all_features = set()
    for features in method_features.values():
        all_features.update(features)

    # 각 피처별 득표수 계산
    feature_votes = {}
    for feat in all_features:
        votes = sum(1 for method_feats in method_features.values() if feat in method_feats)
        feature_votes[feat] = votes

    # 득표수별 분류
    vote_counts = pd.Series(feature_votes).value_counts().sort_index(ascending=False)
    print("\n득표수별 피처 개수:")
    for votes, count in vote_counts.items():
        print(f"  {votes}표: {count}개")

    # 3표 이상 피처만 최종 선택
    final_features = [f for f, v in feature_votes.items() if v >= 3]
    print(f"\n✓ 최종 선택 (3표 이상): {len(final_features)}개 피처")
    print()

    # ========================================================================
    # 상세 리포트 생성 (발표용)
    # ========================================================================
    print("-"*80)
    print(" 상세 리포트 생성")
    print("-"*80)

    # 각 피처의 모든 점수 수집
    report_data = []
    for feat in all_features:
        row = {
            'feature': feat,
            'votes': feature_votes[feat],
            'mi_score': mi_scores[mi_scores['feature']==feat]['mi_score'].values[0]
                        if feat in mi_scores['feature'].values else 0,
            'f_score': f_scores[f_scores['feature']==feat]['f_score'].values[0]
                       if feat in f_scores['feature'].values else 0,
            'p_value': f_scores[f_scores['feature']==feat]['p_value'].values[0]
                       if feat in f_scores['feature'].values else 1,
            'rf_importance': rf_importance[rf_importance['feature']==feat]['importance'].values[0]
                            if feat in rf_importance['feature'].values else 0,
            'correlation': correlations.get(feat, 0),
            'variance_selected': feat in method_features['variance'],
            'mi_selected': feat in method_features['mutual_info'],
            'f_selected': feat in method_features['f_stat'],
            'rf_selected': feat in method_features['random_forest'],
            'corr_selected': feat in method_features['correlation'],
            'final_selected': feat in final_features
        }
        report_data.append(row)

    report = pd.DataFrame(report_data).sort_values('votes', ascending=False)

    # 리포트 저장
    report_path = PROJECT_ROOT / "ml/data/feature_selection_report.csv"
    report.to_csv(report_path, index=False)
    print(f"  ✓ 상세 리포트 저장: {report_path}")

    # 선택된 피처 목록 저장
    selected_path = PROJECT_ROOT / "ml/data/selected_features.csv"
    pd.DataFrame({'feature': final_features}).to_csv(selected_path, index=False)
    print(f"  ✓ 선택된 피처 저장: {selected_path}")
    print()

    # ========================================================================
    # 최종 요약
    # ========================================================================
    print("="*80)
    print(" 최종 요약")
    print("="*80)
    print(f"  원본 피처: {X.shape[1]}개")
    print(f"  최종 선택: {len(final_features)}개")
    print(f"  제거율: {(1 - len(final_features)/X.shape[1])*100:.1f}%")
    print()
    print("  득표수 분포:")
    for votes in sorted(vote_counts.index, reverse=True):
        count = vote_counts[votes]
        pct = count / len(all_features) * 100
        status = "✓ 선택" if votes >= 3 else "✗ 제외"
        print(f"    {votes}표: {count:3d}개 ({pct:5.1f}%) {status}")
    print()

    print("  방법별 선택 피처:")
    for method, features in method_features.items():
        print(f"    {method:<20}: {len(features):3d}개")
    print()

    print("  최종 선택된 피처 (알파벳 순):")
    for i, feat in enumerate(sorted(final_features), 1):
        votes = feature_votes[feat]
        print(f"    {i:2d}. {feat:<40} ({votes}표)")
    print()

    print("다음 단계:")
    print("  python ml/scripts/02c_domain_validation.py")
    print()

    return final_features, report


if __name__ == '__main__':
    final_features, report = statistical_feature_selection()

    print("\n피처 선택 완료!")
    print(f"최종 선택: {len(final_features)}개")
    print(f"리포트: ml/data/feature_selection_report.csv")
