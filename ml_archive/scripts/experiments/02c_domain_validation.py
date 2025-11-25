"""
도메인 검증 (통계적으로 선택된 피처 검증)

역할:
- 통계적으로 선택된 피처를 도메인 지식으로 검증
- 명백히 불필요한 피처만 제거 (식별자, 메타데이터)
- 추가 검토가 필요한 경계선 피처 식별

검증 기준:
1. 식별자 제거 (ID, 코드 등)
2. 메타데이터 제거 (날짜, 순번 등)
3. 중복 피처 제거
4. 경계선 피처 (3표) 검토

출력:
- ml/data/validated_features.csv (도메인 검증 완료)
- ml/data/domain_validation_report.txt (검증 리포트)

실행:
    python ml/scripts/02c_domain_validation.py
"""

import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def domain_validation():
    """
    도메인 지식 기반 피처 검증

    Returns:
        validated_features: 도메인 검증 완료된 피처 리스트
        validation_report: 검증 리포트 dict
    """

    print("="*80)
    print(" 도메인 검증 (Domain Validation)")
    print("="*80)
    print()

    # 1. 통계적 선택 결과 로드
    print("✓ 통계적 선택 결과 로드 중...")
    selected_path = PROJECT_ROOT / "ml/data/selected_features.csv"
    report_path = PROJECT_ROOT / "ml/data/feature_selection_report.csv"

    selected_df = pd.read_csv(selected_path)
    report_df = pd.read_csv(report_path)

    selected_features = selected_df['feature'].tolist()
    print(f"  통계적으로 선택된 피처: {len(selected_features)}개")
    print()

    # 2. 제거 규칙 정의
    print("-"*80)
    print(" 도메인 기반 제거 규칙")
    print("-"*80)

    # 규칙 1: 식별자 (명백한 제거 대상)
    identifier_keywords = ['ID', '_ID', 'SK', 'CODE', 'CD']
    # 규칙 2: 메타데이터 (명백한 제거 대상)
    metadata_keywords = ['DT', 'DATE', 'TIME', 'SEQ', 'NO', 'NUM']

    # 제거할 피처 수집
    to_remove = []
    removal_reasons = {}

    for feat in selected_features:
        feat_lower = feat.lower()

        # 식별자 체크
        if any(kw.lower() in feat_lower for kw in identifier_keywords):
            # 예외: corp_grad (신용등급)은 유지
            if feat.lower() == 'corp_grad':
                continue
            to_remove.append(feat)
            removal_reasons[feat] = "식별자"
            continue

        # 메타데이터 체크
        if any(kw.lower() in feat_lower for kw in metadata_keywords):
            # 예외: 중요한 날짜 피처는 유지할 수 있음
            to_remove.append(feat)
            removal_reasons[feat] = "메타데이터"
            continue

    print(f"  식별자 키워드: {identifier_keywords}")
    print(f"  메타데이터 키워드: {metadata_keywords}")
    print()

    # 3. 제거 실행
    print("-"*80)
    print(" 제거 대상 피처")
    print("-"*80)

    if to_remove:
        print(f"  총 {len(to_remove)}개 제거:")
        for feat in to_remove:
            votes = report_df[report_df['feature']==feat]['votes'].values[0]
            reason = removal_reasons[feat]
            print(f"    - {feat:<40} (이유: {reason}, 득표: {votes})")
    else:
        print("  제거할 피처 없음 (모두 유효)")
    print()

    # 4. 경계선 피처 검토 (3표)
    print("-"*80)
    print(" 경계선 피처 검토 (3표)")
    print("-"*80)

    borderline = report_df[
        (report_df['final_selected'] == True) &
        (report_df['votes'] == 3)
    ]['feature'].tolist()

    borderline = [f for f in borderline if f not in to_remove]

    if borderline:
        print(f"  총 {len(borderline)}개 경계선 피처:")
        print("  (추가 검토 권장 - 현재는 모두 유지)")
        print()
        for feat in borderline:
            row = report_df[report_df['feature']==feat].iloc[0]
            print(f"    - {feat:<40}")
            print(f"        득표: {row['votes']}")
            print(f"        상관계수: {row['correlation']:.4f}")
            print(f"        MI 점수: {row['mi_score']:.4f}")
            print(f"        RF 중요도: {row['rf_importance']:.4f}")
            print()
    else:
        print("  경계선 피처 없음 (모두 4표 이상)")
    print()

    # 5. 최종 검증된 피처
    validated_features = [f for f in selected_features if f not in to_remove]

    print("="*80)
    print(" 도메인 검증 완료")
    print("="*80)
    print(f"  통계적 선택: {len(selected_features)}개")
    print(f"  도메인 제거: {len(to_remove)}개")
    print(f"  최종 검증: {len(validated_features)}개")
    print()

    # 6. 검증된 피처 저장
    validated_path = PROJECT_ROOT / "ml/data/validated_features.csv"
    pd.DataFrame({'feature': validated_features}).to_csv(validated_path, index=False)
    print(f"✓ 검증된 피처 저장: {validated_path}")
    print()

    # 7. 검증 리포트 저장
    report_lines = []
    report_lines.append("="*80)
    report_lines.append(" 도메인 검증 리포트")
    report_lines.append("="*80)
    report_lines.append("")
    report_lines.append(f"일시: {pd.Timestamp.now()}")
    report_lines.append("")
    report_lines.append("-"*80)
    report_lines.append(" 요약")
    report_lines.append("-"*80)
    report_lines.append(f"통계적 선택: {len(selected_features)}개")
    report_lines.append(f"도메인 제거: {len(to_remove)}개")
    report_lines.append(f"최종 검증: {len(validated_features)}개")
    report_lines.append("")
    report_lines.append("-"*80)
    report_lines.append(" 제거된 피처")
    report_lines.append("-"*80)
    if to_remove:
        for feat in to_remove:
            report_lines.append(f"  - {feat}: {removal_reasons[feat]}")
    else:
        report_lines.append("  없음")
    report_lines.append("")
    report_lines.append("-"*80)
    report_lines.append(" 경계선 피처 (3표)")
    report_lines.append("-"*80)
    if borderline:
        for feat in borderline:
            row = report_df[report_df['feature']==feat].iloc[0]
            report_lines.append(f"  - {feat}")
            report_lines.append(f"      상관계수: {row['correlation']:.4f}")
            report_lines.append(f"      MI: {row['mi_score']:.4f}, F: {row['f_score']:.2f}, RF: {row['rf_importance']:.4f}")
    else:
        report_lines.append("  없음")
    report_lines.append("")
    report_lines.append("-"*80)
    report_lines.append(" 최종 검증된 피처 목록")
    report_lines.append("-"*80)
    for i, feat in enumerate(sorted(validated_features), 1):
        votes = report_df[report_df['feature']==feat]['votes'].values[0]
        report_lines.append(f"  {i:2d}. {feat:<40} ({votes}표)")
    report_lines.append("")

    report_text = "\n".join(report_lines)
    report_txt_path = PROJECT_ROOT / "ml/data/domain_validation_report.txt"
    with open(report_txt_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"✓ 검증 리포트 저장: {report_txt_path}")
    print()

    # 8. 통계 비교 (기존 48개 vs 새로운 선택)
    print("-"*80)
    print(" 기존 방식과 비교")
    print("-"*80)
    print(f"  기존 (경험적 선택): 48개")
    print(f"  신규 (통계 + 도메인): {len(validated_features)}개")
    print(f"  차이: {len(validated_features) - 48:+d}개")
    print()

    print("다음 단계:")
    print("  python ml/scripts/03_feature_engineering.py")
    print()

    validation_report = {
        'selected_count': len(selected_features),
        'removed_count': len(to_remove),
        'validated_count': len(validated_features),
        'removed_features': to_remove,
        'removal_reasons': removal_reasons,
        'borderline_features': borderline
    }

    return validated_features, validation_report


if __name__ == '__main__':
    validated_features, report = domain_validation()

    print("\n도메인 검증 완료!")
    print(f"최종: {len(validated_features)}개 피처")
    print(f"리포트: ml/data/domain_validation_report.txt")
