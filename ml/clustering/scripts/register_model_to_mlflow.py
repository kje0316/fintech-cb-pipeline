"""
기존 클러스터링 모델을 MLflow Model Registry에 등록하는 스크립트

Usage:
    python ml/clustering/scripts/register_model_to_mlflow.py --config final_notebook_model
"""
import sys
import argparse
import tempfile
import json
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

import joblib
import mlflow
from mlflow.tracking import MlflowClient


def register_existing_model(
    config_name: str = 'final_notebook_model',
    model_name: str = 'clustering_model',
    promote_to_production: bool = True
):
    """
    로컬에 저장된 클러스터링 모델을 MLflow Model Registry에 등록

    Args:
        config_name: 설정 파일명
        model_name: MLflow에 등록할 모델명
        promote_to_production: Production 스테이지로 승격 여부
    """
    from ml.clustering.data_loader import load_config

    print(f"\n{'='*60}")
    print(f"클러스터링 모델 MLflow 등록")
    print(f"{'='*60}")

    # MLflow 설정
    mlflow.set_tracking_uri("sqlite:///mlflow_db/mlflow.db")
    mlflow.set_experiment("clustering")
    client = MlflowClient()

    # 설정 로드
    config = load_config(config_name)
    model_dir = Path(config['paths']['model_dir'])
    output_dir = Path(config['paths']['output_dir'])

    print(f"\n📂 모델 디렉토리: {model_dir}")

    # 모델 파일 확인
    required_files = ['vae_model.pkl', 'clusterer.pkl', 'quantile_transformer.pkl', 'imputer.pkl']
    for f in required_files:
        if not (model_dir / f).exists():
            raise FileNotFoundError(f"필수 파일 없음: {model_dir / f}")

    print("✅ 모델 파일 확인 완료")

    # 클러스터 정보 로드 (clustered_data.csv에서)
    import pandas as pd
    clustered_data_path = output_dir / 'final_clustered_data.csv'
    if not clustered_data_path.exists():
        clustered_data_path = output_dir / 'clustered_data.csv'

    if clustered_data_path.exists():
        df = pd.read_csv(clustered_data_path, nrows=100000)
        df.columns = df.columns.str.upper()
        n_clusters = df['CLUSTER'].nunique()
        n_samples = len(df)
        print(f"  - 클러스터 수: {n_clusters}")
        print(f"  - 샘플 수: {n_samples:,}")
    else:
        n_clusters = 10
        n_samples = 50000
        print(f"  ⚠️ clustered_data.csv 없음, 기본값 사용")

    # MLflow Run 시작
    with mlflow.start_run(run_name=f"register_{config_name}") as run:
        run_id = run.info.run_id
        print(f"\n📊 MLflow Run 시작: {run_id[:8]}")

        # 파라미터 로깅
        mlflow.log_param("config_name", config_name)
        mlflow.log_param("n_clusters", n_clusters)
        mlflow.log_param("source", "local_registration")

        # 아티팩트 저장 (임시 디렉토리 사용)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 모델 파일 복사
            for f in required_files:
                src = model_dir / f
                dst = tmpdir / f
                import shutil
                shutil.copy(src, dst)
                print(f"  📦 {f}")

            # UMAP (있으면)
            umap_path = model_dir / 'umap_reducer.pkl'
            if umap_path.exists():
                shutil.copy(umap_path, tmpdir / 'umap_reducer.pkl')
                print(f"  📦 umap_reducer.pkl")

            # 메타데이터 생성
            metadata = {
                'config_name': config_name,
                'n_clusters': n_clusters,
                'n_samples': n_samples,
                'has_umap': umap_path.exists(),
                'registered_from': 'local'
            }
            with open(tmpdir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            # MLflow에 아티팩트 로깅
            mlflow.log_artifacts(str(tmpdir), artifact_path="clustering_model")

        print(f"\n✅ 아티팩트 업로드 완료")

        # Model Registry에 등록
        print(f"\n📋 Model Registry에 등록 중...")

        # artifacts URI 직접 구성
        artifact_uri = mlflow.get_artifact_uri("clustering_model")
        print(f"  Artifact URI: {artifact_uri}")

        # 수동으로 Model Registry에 등록
        try:
            client.create_registered_model(model_name)
            print(f"  ✅ 모델 '{model_name}' 생성됨")
        except Exception:
            print(f"  ℹ️  모델 '{model_name}' 이미 존재")

        # 모델 버전 생성
        model_version = client.create_model_version(
            name=model_name,
            source=artifact_uri,
            run_id=run_id,
            tags={
                "model_type": "CLUSTERING",
                "algorithm": "VAE+HDBSCAN",
                "n_clusters": str(n_clusters)
            }
        )

        version = model_version.version
        print(f"  ✅ 등록 완료: {model_name} v{version}")

        # Production으로 승격
        if promote_to_production:
            print(f"\n🚀 Production 스테이지로 승격 중...")

            # 기존 Production 모델 Archived로 변경
            try:
                existing_prod = client.get_latest_versions(model_name, stages=["Production"])
                for v in existing_prod:
                    client.transition_model_version_stage(
                        name=model_name,
                        version=v.version,
                        stage="Archived"
                    )
                    print(f"  📦 v{v.version} → Archived")
            except Exception:
                pass

            # 새 버전을 Production으로
            client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage="Production"
            )
            print(f"  ✅ v{version} → Production")

    print(f"\n{'='*60}")
    print(f"✅ 클러스터링 모델 MLflow 등록 완료!")
    print(f"  - 모델명: {model_name}")
    print(f"  - 버전: {version}")
    print(f"  - 스테이지: {'Production' if promote_to_production else 'None'}")
    print(f"{'='*60}\n")

    return version


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="클러스터링 모델 MLflow 등록")
    parser.add_argument(
        '--config',
        type=str,
        default='final_notebook_model',
        help="설정 파일명"
    )
    parser.add_argument(
        '--no-production',
        action='store_true',
        help="Production 승격 안함"
    )
    args = parser.parse_args()

    register_existing_model(
        config_name=args.config,
        promote_to_production=not args.no_production
    )
