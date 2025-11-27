"""
클러스터링 모델 학습 파이프라인

원본 데이터 → 전처리 → VAE 피처 추출 → UMAP → HDBSCAN 클러스터링
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    """클러스터링 모델 학습 파이프라인 실행"""
    parser = argparse.ArgumentParser(
        description="클러스터링 모델 학습 파이프라인"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='final_notebook_model',
        help="설정 파일명 (예: final_notebook_model)"
    )
    parser.add_argument(
        '--save-models',
        action='store_true',
        default=True,
        help="모델 저장 여부"
    )
    args = parser.parse_args()

    start_time = datetime.now()

    try:
        print("\n" + "=" * 60)
        print("클러스터링 모델 학습 파이프라인")
        print(f"시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"설정: {args.config}")
        print("=" * 60)

        from ml.clustering.training.train import run_clustering_pipeline

        result = run_clustering_pipeline(
            config_name=args.config,
            save_models=args.save_models
        )

        # 완료
        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "=" * 60)
        print("✅ 파이프라인 완료!")
        print("=" * 60)
        print(f"\n소요 시간: {duration}")
        print(f"\n결과:")
        print(f"  - 클러스터 수: {result['n_clusters']}")
        print(f"  - 샘플 수: {result['n_samples']:,}건")
        print(f"  - 노이즈: {result['n_noise']:,}건")
        if result.get('silhouette_score'):
            print(f"  - Silhouette Score: {result['silhouette_score']:.4f}")
        print(f"  - 모델 저장 위치: {result['model_dir']}")

        return result

    except Exception as e:
        print(f"\n❌ 파이프라인 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
