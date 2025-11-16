import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가하여 다른 모듈을 임포트할 수 있도록 함
# 이 스크립트의 위치: /ml/clustering/src/run_pipeline.py
# 프로젝트 루트: 3단계 상위
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root))

from ml.clustering.src.build_features import main as build_features_main
from ml.clustering.src.train_cluster import main as train_cluster_main
from ml.clustering.src.predict_cluster import main as predict_cluster_main
from ml.clustering.src.analyze_cluster import main as analyze_cluster_main

def run_full_pipeline():
    """
    전체 클러스터링 파이프라인을 순차적으로 실행합니다.
    1. build_features: 피처 생성
    2. train_cluster: 모델 학습
    3. predict_cluster: 예측 (더미 데이터)
    4. analyze_cluster: 결과 분석
    """
    print("=================================================")
    print("====== Starting Full Clustering Pipeline ======")
    print("=================================================\n")

    try:
        print("\n--- [Step 1/4] Running build_features ---")
        build_features_main()
        print("--- [Step 1/4] build_features finished successfully. ---\n")
    except Exception as e:
        print(f"--- [Step 1/4] build_features failed: {e} ---")
        return

    try:
        print("\n--- [Step 2/4] Running train_cluster ---")
        train_cluster_main()
        print("--- [Step 2/4] train_cluster finished successfully. ---\n")
    except Exception as e:
        print(f"--- [Step 2/4] train_cluster failed: {e} ---")
        return

    try:
        print("\n--- [Step 3/4] Running predict_cluster ---")
        predict_cluster_main()
        print("--- [Step 3/4] predict_cluster finished successfully. ---\n")
    except Exception as e:
        print(f"--- [Step 3/4] predict_cluster failed: {e} ---")
        return

    try:
        print("\n--- [Step 4/4] Running analyze_cluster ---")
        analyze_cluster_main()
        print("--- [Step 4/4] analyze_cluster finished successfully. ---\n")
    except Exception as e:
        print(f"--- [Step 4/4] analyze_cluster failed: {e} ---")
        return

    print("\n=================================================")
    print("====== Full Clustering Pipeline Finished ======")
    print("=================================================")

if __name__ == '__main__':
    run_full_pipeline()
