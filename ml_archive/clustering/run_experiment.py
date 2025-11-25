# ml/clustering/run_experiment.py
import yaml
from datetime import datetime
import os
import sys
import argparse
import json
import pandas as pd
from pathlib import Path
import joblib

# --- 프로젝트 루트 및 src 디렉토리를 Python 경로에 추가 ---
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parents[1]
src_dir = script_dir / 'src'

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# --- 소스 모듈 임포트 ---
import data_loader
import preprocessor
import models
import trainer
import evaluation

def load_and_merge_configs(base_config_path, exp_config_path):
    """기본 설정과 실험 설정을 로드하고 병합합니다."""
    with open(base_config_path, 'r', encoding='utf-8') as f:
        base_config = yaml.safe_load(f)
    with open(exp_config_path, 'r', encoding='utf-8') as f:
        exp_config = yaml.safe_load(f)
    
    # base_config에 exp_config를 덮어쓰기
    base_config.update(exp_config)
    return base_config

def save_artifacts(output_dir, model, df_with_labels, metrics, config):
    """실험 결과물들을 지정된 디렉토리에 저장합니다."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 설정 파일 저장 (Path 객체를 문자열로 변환 후 저장)
    config_to_save = config.copy()
    config_to_save['paths'] = {k: str(v) for k, v in config['paths'].items()} # 경로를 문자열로 변환
    
    config_path = os.path.join(output_dir, 'config.yaml')
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_to_save, f)
    print(f"  - Config saved to: {config_path}")
    
    # 2. 모델 저장
    model_path = os.path.join(output_dir, 'model.pkl')
    joblib.dump(model, model_path)
    print(f"  - Model saved to: {model_path}")
    
    # 3. 클러스터링 결과 저장
    clusters_path = os.path.join(output_dir, 'clusters.csv')
    df_with_labels.to_csv(clusters_path, index=False)
    print(f"  - Labeled data saved to: {clusters_path}")
    
    # 4. 평가 지표 저장
    metrics_path = os.path.join(output_dir, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=4)
    print(f"  - Metrics saved to: {metrics_path}")

def run_experiment(config_name: str):
    """
    주어진 실험 설정에 따라 전체 파이프라인을 실행합니다.
    """
    # 1. 설정 로드 및 경로 준비
    base_config_path = script_dir / 'configs' / 'base.yaml'
    exp_config_path = script_dir / 'configs' / 'experiments' / config_name
    config = load_and_merge_configs(base_config_path, exp_config_path)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = script_dir / 'outputs' / f"{timestamp}_{config['experiment_name']}"
    
    # config의 경로들을 절대 경로로 변환
    config['paths']['dump_path'] = script_dir / config['paths']['dump_path']
    config['paths']['output_dir'] = str(output_dir)
    
    # --- 파이프라인 실행 ---
    # 1. 데이터 로드
    df_raw = data_loader.run(config)
    
    # 2. 전처리
    df_processed = preprocessor.run(df_raw, config)

    # 3. 모델 초기화
    model = models.get_model(config)
    
    # 4. 학습
    df_results, trained_model = trainer.train(model, df_processed, config)

    # 5. 평가
    # 전처리 단계(예: PCA) 후의 실제 피처 목록을 사용
    processed_features = [col for col in df_processed.columns if col not in config.get('drop_cols', []) + [config.get('target_col', '')]]
    eval_metrics = config.get('evaluation', {}).get('metrics', [])
    metrics = evaluation.evaluate(df_processed, processed_features, df_results['cluster_label'], eval_metrics)
    
    # 6. 결과 저장
    print("\n--- 5. Saving Artifacts ---")
    save_artifacts(output_dir, trained_model, df_results, metrics, config)

    print("\n" + "="*50)
    print("Clustering Pipeline Finished Successfully")
    print(f"All artifacts saved in: {output_dir}")
    print("="*50)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config', 
        type=str, 
        default='exp001_kmeans_5_clusters.yaml',
        help='Name of the experiment config file in configs/experiments/'
    )
    args = parser.parse_args()
    
    run_experiment(args.config)
