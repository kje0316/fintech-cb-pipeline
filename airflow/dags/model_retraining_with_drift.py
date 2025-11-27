"""
드리프트 감지 시 자동 재학습 파이프라인 (누적 방식)

실행 조건:
1. 주간으로 PSI 계산 및 드리프트 체크
2. PSI > 0.2이면 재학습 트리거
3. 기존 데이터 + 새 기준년월 데이터를 **누적**하여 학습
4. 새 모델 성능이 현재 모델보다 좋으면 Production 승격
   - 부도예측: AUC 2% 이상 개선
   - 클러스터링: Silhouette Score 개선
5. API 서버에 모델 재로드 요청

누적 학습 방식:
- 초기: 20210801만 사용
- 1차 재학습: 20210801 + 20210901
- 2차 재학습: 20210801 + 20210901 + 20211001
- ... (정답 레이블이 있는 과거 데이터를 누적)

모델 종류:
- default_prediction: XGBoost/CatBoost 기반 부도예측 모델
- clustering: VAE + HDBSCAN 기반 기업 클러스터링 모델
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import subprocess
import sys
import os
import requests

# Python 경로 설정
PROJECT_ROOT = '/Users/kje/coding/project/fintech-cb-pipeline'
sys.path.insert(0, PROJECT_ROOT)

# ML 모듈 import (70개 피처 파이프라인 - 부도예측)
from ml.default_prediction.run_pipeline import (
    INPUT_37_COLUMNS,
    create_derived_features,
    map_to_70_features
)
from ml.default_prediction.training.train import run_training_pipeline

# 클러스터링 파이프라인 import
from ml.clustering.training.train import run_clustering_pipeline

default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    'model_retraining_with_drift',
    default_args=default_args,
    description='드리프트 감지 시 자동 재학습 파이프라인',
    schedule_interval='0 3 * * 0',  # 매주 일요일 03:00 AM
    catchup=False,
    max_active_runs=1,
    tags=['mlops', 'retraining', 'drift'],
)


def calculate_psi(expected, actual, buckets=10):
    """
    PSI (Population Stability Index) 계산

    Args:
        expected: 기준 분포 (학습 데이터)
        actual: 현재 분포 (최근 예측 데이터)
        buckets: 구간 수

    Returns:
        PSI 값
    """
    def scale_range(input_data, min_val, max_val):
        input_data = np.array(input_data)
        input_data[input_data < min_val] = min_val
        input_data[input_data > max_val] = max_val
        return input_data

    # 데이터 전처리
    expected = np.array(expected).flatten()
    actual = np.array(actual).flatten()

    # 범위 스케일링
    min_val = min(expected.min(), actual.min())
    max_val = max(expected.max(), actual.max())

    expected = scale_range(expected, min_val, max_val)
    actual = scale_range(actual, min_val, max_val)

    # 구간 생성
    breakpoints = np.linspace(min_val, max_val, buckets + 1)

    # 각 구간별 비율 계산
    expected_percents = np.histogram(expected, breakpoints)[0] / len(expected)
    actual_percents = np.histogram(actual, breakpoints)[0] / len(actual)

    # 0으로 나누기 방지
    expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
    actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)

    # PSI 계산
    psi_values = (actual_percents - expected_percents) * np.log(actual_percents / expected_percents)
    psi = np.sum(psi_values)

    return psi


def check_drift_and_decide(**context):
    """
    Step 1: PSI 계산 및 드리프트 체크

    Returns:
        'determine_next_base_ym' or 'skip_retraining'
    """
    logging.info("=" * 80)
    logging.info("📊 Step 1: Checking for model drift...")
    logging.info("=" * 80)

    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    try:
        # 최근 30일간의 예측 데이터 분포 추출
        recent_query = """
            SELECT default_probability
            FROM fact_predictions
            WHERE created_at >= NOW() - INTERVAL '30 days'
            AND default_probability IS NOT NULL
        """
        recent_df = dwh_db.get_pandas_df(recent_query)

        if len(recent_df) < 100:
            logging.warning(f"⚠️  Not enough recent predictions ({len(recent_df)} rows). Skipping drift check.")
            return 'skip_retraining'

        recent_predictions = recent_df['default_probability'].values

        # 학습 데이터 분포 (20210801 기준) - 임시로 0.01~0.99 범위의 정규분포 가정
        # 실제로는 학습 데이터의 예측 분포를 별도로 저장해두고 사용해야 함
        np.random.seed(42)
        training_predictions = np.random.beta(2, 10, size=10000)  # 낮은 확률에 치우친 분포 (부도율이 낮으므로)

        # PSI 계산
        psi_score = calculate_psi(training_predictions, recent_predictions)

        logging.info(f"✅ PSI Score calculated: {psi_score:.4f}")
        logging.info(f"   - Baseline distribution: {len(training_predictions)} samples")
        logging.info(f"   - Recent distribution: {len(recent_predictions)} samples")

        # XCom에 저장
        context['ti'].xcom_push(key='psi_score', value=float(psi_score))

        # 드리프트 판단
        threshold = 0.2
        if psi_score > threshold:
            logging.warning(f"🚨 DRIFT DETECTED! PSI = {psi_score:.4f} > {threshold}")
            logging.warning(f"   → Triggering model retraining...")
            return 'determine_next_base_ym'
        else:
            logging.info(f"✅ No significant drift detected. PSI = {psi_score:.4f} < {threshold}")
            logging.info(f"   → Skipping retraining.")
            return 'skip_retraining'

    except Exception as e:
        logging.error(f"❌ Error during drift check: {str(e)}")
        return 'skip_retraining'


def determine_next_base_ym(**context):
    """
    Step 2: 다음 학습할 기준년월 결정
    """
    logging.info("=" * 80)
    logging.info("📅 Step 2: Determining next base_ym for retraining...")
    logging.info("=" * 80)

    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    # 현재 Production 모델의 기준년월 조회
    query = """
        SELECT base_ym, model_version, auc_roc
        FROM model_training_history
        WHERE is_production = TRUE
        ORDER BY trained_at DESC
        LIMIT 1
    """

    result = dwh_db.get_first(query)

    if not result:
        logging.error("❌ No production model found in model_training_history!")
        raise ValueError("No production model found")

    current_base_ym = result[0]
    current_version = result[1]
    current_auc = result[2]

    logging.info(f"📌 Current Production Model:")
    logging.info(f"   - base_ym: {current_base_ym}")
    logging.info(f"   - model_version: {current_version}")
    logging.info(f"   - AUC-ROC: {current_auc:.4f}")

    # Feature Store에서 사용 가능한 기준년월 목록 조회
    from ml.common.feature_store import get_available_base_yms

    available_base_yms = get_available_base_yms()
    logging.info(f"📋 Available base_ym in Feature Store: {available_base_yms}")

    # 다음 기준년월 결정
    try:
        current_index = available_base_yms.index(current_base_ym)

        if current_index + 1 < len(available_base_yms):
            next_base_ym = available_base_yms[current_index + 1]
            logging.info(f"✅ Next base_ym selected: {next_base_ym}")
        else:
            # 마지막 기준년월이면 가장 최신 것 사용
            next_base_ym = available_base_yms[-1]
            logging.warning(f"⚠️  Current base_ym is already the latest! Using: {next_base_ym}")

    except ValueError:
        # 현재 base_ym이 목록에 없으면 첫 번째 것 사용
        next_base_ym = available_base_yms[0] if available_base_yms else 20210801
        logging.warning(f"⚠️  Current base_ym not found in DWH. Using first available: {next_base_ym}")

    # 새 모델 버전 생성
    version_num = int(current_version.replace('v', '')) + 1
    new_version = f"v{version_num}"

    logging.info(f"🆕 New model version will be: {new_version}")

    # XCom에 저장
    context['ti'].xcom_push(key='next_base_ym', value=next_base_ym)
    context['ti'].xcom_push(key='new_model_version', value=new_version)
    context['ti'].xcom_push(key='current_auc', value=float(current_auc))


def extract_training_data(**context):
    """
    Step 3: Feature Store에서 누적 학습 데이터 추출

    Feature Store 마트에서 직접 로드 (70개 피처 이미 생성됨)
    누적 방식: 시작(20210801)부터 next_base_ym까지의 모든 데이터
    """
    ti = context['ti']
    next_base_ym = ti.xcom_pull(key='next_base_ym', task_ids='determine_next_base_ym')

    logging.info("=" * 80)
    logging.info(f"📦 Step 3: Loading CUMULATIVE training data from Feature Store (up to base_ym={next_base_ym})")
    logging.info("=" * 80)

    # Feature Store에서 데이터 로드
    from ml.common.feature_store import load_from_feature_store, get_available_base_yms

    # 사용 가능한 기준년월 목록
    available_base_yms = get_available_base_yms()
    logging.info(f"📋 Available base_ym in Feature Store: {available_base_yms}")

    # 누적 방식: 시작(20210801)부터 next_base_ym까지의 모든 데이터
    base_yms_to_use = [ym for ym in available_base_yms if ym <= next_base_ym]
    logging.info(f"📊 Cumulative base_ym to use: {base_yms_to_use}")

    if not base_yms_to_use:
        raise ValueError(f"No training data found for base_ym <= {next_base_ym}")

    # Feature Store에서 누적 데이터 로드
    df_70 = load_from_feature_store(base_ym=base_yms_to_use, include_target=True)

    logging.info(f"✅ Loaded CUMULATIVE data from Feature Store:")
    logging.info(f"   - Total rows: {len(df_70):,}")
    logging.info(f"   - Base months included: {len(base_yms_to_use)}")
    logging.info(f"   - Columns: {len(df_70.columns)}")

    # 각 기준년월별 데이터 수 로깅
    if 'base_ym' in df_70.columns:
        for ym in base_yms_to_use:
            ym_count = len(df_70[df_70['base_ym'] == ym])
            logging.info(f"   - {ym}: {ym_count:,} rows")

    # 타겟 컬럼 확인
    if 'default_yn' not in df_70.columns:
        raise ValueError("타겟 컬럼 'default_yn'을 찾을 수 없습니다.")

    target_values = df_70['default_yn'].values
    default_rate = float(np.nanmean(target_values))
    logging.info(f"   - Default rate: {default_rate:.4f}")

    if len(df_70) < 1000:
        raise ValueError(f"Not enough training data! Only {len(df_70)} rows found")

    # 결측치/무한값 처리
    df_70 = df_70.replace([np.inf, -np.inf], 0)
    df_70 = df_70.fillna(0)

    logging.info(f"   ✅ Data ready: {df_70.shape}")

    # Parquet 저장 (캐싱용)
    airflow_home = os.environ.get('AIRFLOW_HOME', '/Users/kje/coding/project/fintech-cb-pipeline/airflow')
    project_root = os.path.dirname(airflow_home)
    output_dir = os.path.join(project_root, 'data/processed')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'train_70features_cumulative_upto_{next_base_ym}.parquet')

    df_70.to_parquet(output_path, index=False)
    logging.info(f"💾 Cached training data to: {output_path}")

    # XCom에 저장
    context['ti'].xcom_push(key='training_data_path', value=output_path)
    context['ti'].xcom_push(key='training_samples', value=len(df_70))
    context['ti'].xcom_push(key='base_yms_used', value=base_yms_to_use)
    context['ti'].xcom_push(key='default_rate', value=default_rate)


def run_ml_training_pipeline(**context):
    """
    Step 4: ML 학습 파이프라인 실행

    피처 엔지니어링 → 모델 학습 → MLflow 등록
    """
    ti = context['ti']
    next_base_ym = ti.xcom_pull(key='next_base_ym', task_ids='determine_next_base_ym')
    new_version = ti.xcom_pull(key='new_model_version', task_ids='determine_next_base_ym')
    training_data_path = ti.xcom_pull(key='training_data_path', task_ids='extract_training_data')

    logging.info("=" * 80)
    logging.info(f"🤖 Step 4: Running ML training pipeline")
    logging.info(f"   - base_ym: {next_base_ym}")
    logging.info(f"   - new_version: {new_version}")
    logging.info(f"   - training_data: {training_data_path}")
    logging.info("=" * 80)

    # 실제 ML 학습 파이프라인 실행
    try:
        result = run_training_pipeline(
            base_ym=next_base_ym,
            data_path=training_data_path,
            model_version=new_version,
            model_type='catboost',
            experiment_name='default_prediction_retraining'
        )

        new_auc = result['auc_roc']

        logging.info(f"✅ Training completed!")
        logging.info(f"   - Model type: {result['model_type']}")
        logging.info(f"   - AUC-ROC: {new_auc:.4f}")
        logging.info(f"   - F1-Score: {result['f1_score']:.4f}")
        logging.info(f"   - Train samples: {result['n_train_samples']:,}")

    except Exception as e:
        logging.error(f"❌ Training failed: {str(e)}")
        raise

    # XCom에 저장
    context['ti'].xcom_push(key='new_auc', value=new_auc)
    context['ti'].xcom_push(key='training_result', value=result)


def evaluate_and_compare(**context):
    """
    Step 5: 성능 비교 및 승격 결정

    Returns:
        'promote_to_production' or 'log_training_only'
    """
    ti = context['ti']
    current_auc = ti.xcom_pull(key='current_auc', task_ids='determine_next_base_ym')
    new_auc = ti.xcom_pull(key='new_auc', task_ids='run_ml_training_pipeline')
    new_version = ti.xcom_pull(key='new_model_version', task_ids='determine_next_base_ym')

    logging.info("=" * 80)
    logging.info(f"📊 Step 5: Evaluating model performance")
    logging.info("=" * 80)

    improvement = new_auc - current_auc
    improvement_pct = (improvement / current_auc) * 100

    logging.info(f"📈 Performance Comparison:")
    logging.info(f"   - Current model AUC: {current_auc:.4f}")
    logging.info(f"   - New model AUC:     {new_auc:.4f}")
    logging.info(f"   - Improvement:       {improvement:+.4f} ({improvement_pct:+.2f}%)")

    # 승격 기준: 2% 이상 개선
    threshold_improvement = 0.02

    if improvement >= threshold_improvement:
        logging.info(f"✅ New model is significantly better! (improvement >= {threshold_improvement})")
        logging.info(f"   → Promoting {new_version} to Production")
        return 'promote_to_production'
    else:
        logging.warning(f"⚠️  New model improvement is insufficient (improvement < {threshold_improvement})")
        logging.warning(f"   → Keeping current model in Production")
        logging.warning(f"   → {new_version} will be logged but not promoted")
        return 'log_training_only'


def promote_to_production(**context):
    """
    Step 6: 모델 Production 승격
    """
    ti = context['ti']
    next_base_ym = ti.xcom_pull(key='next_base_ym', task_ids='determine_next_base_ym')
    new_version = ti.xcom_pull(key='new_model_version', task_ids='determine_next_base_ym')
    new_auc = ti.xcom_pull(key='new_auc', task_ids='run_ml_training_pipeline')
    training_samples = ti.xcom_pull(key='training_samples', task_ids='extract_training_data')

    logging.info("=" * 80)
    logging.info(f"🚀 Step 6: Promoting {new_version} to Production")
    logging.info("=" * 80)

    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    # 1. 현재 Production 모델을 is_production=FALSE로 변경
    logging.info("📝 Step 6-1: Demoting current production model...")
    dwh_db.run("UPDATE model_training_history SET is_production = FALSE WHERE is_production = TRUE")

    # 2. 새 모델 등록
    logging.info(f"📝 Step 6-2: Registering {new_version} as production model...")
    insert_query = f"""
        INSERT INTO model_training_history
        (base_ym, model_version, model_type, auc_roc, training_samples, is_production, notes)
        VALUES
        ({next_base_ym}, '{new_version}', 'CATBOOST', {new_auc}, {training_samples}, TRUE,
         'Auto-promoted by drift detection pipeline')
    """
    dwh_db.run(insert_query)

    # 3. dim_model 테이블 업데이트
    logging.info("📝 Step 6-3: Updating dim_model table...")
    update_query = f"""
        UPDATE dim_model
        SET model_version = '{new_version}',
            updated_at = NOW()
        WHERE model_type = 'CATBOOST'
    """
    dwh_db.run(update_query)

    logging.info(f"✅ {new_version} successfully promoted to Production!")

    # 4. API 서버에 모델 재로드 요청
    logging.info("🔄 Step 6-4: Reloading model in API server...")
    try:
        response = requests.post(
            'http://localhost:8000/api/v1/predict/admin/reload-model',
            timeout=30
        )
        if response.status_code == 200:
            logging.info(f"✅ API reload successful: {response.json()}")
        else:
            logging.warning(f"⚠️  API reload returned status {response.status_code}: {response.text}")
    except Exception as e:
        logging.error(f"❌ API reload failed: {str(e)}")
        logging.error("   → Please reload manually: POST /api/v1/predict/admin/reload-model")


def log_training_only(**context):
    """
    Step 6-B: 모델이 승격되지 않았을 때 로그만 남김
    """
    ti = context['ti']
    next_base_ym = ti.xcom_pull(key='next_base_ym', task_ids='determine_next_base_ym')
    new_version = ti.xcom_pull(key='new_model_version', task_ids='determine_next_base_ym')
    new_auc = ti.xcom_pull(key='new_auc', task_ids='run_ml_training_pipeline')
    training_samples = ti.xcom_pull(key='training_samples', task_ids='extract_training_data')

    logging.info("=" * 80)
    logging.info(f"📝 Step 6-B: Logging {new_version} without promotion")
    logging.info("=" * 80)

    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    insert_query = f"""
        INSERT INTO model_training_history
        (base_ym, model_version, model_type, auc_roc, training_samples, is_production, notes)
        VALUES
        ({next_base_ym}, '{new_version}', 'CATBOOST', {new_auc}, {training_samples}, FALSE,
         'Trained but not promoted - insufficient improvement')
    """
    dwh_db.run(insert_query)

    logging.info(f"✅ {new_version} training logged successfully")
    logging.info(f"   → Current production model remains unchanged")


def skip_retraining(**context):
    """No-op when no drift detected"""
    logging.info("=" * 80)
    logging.info("✅ No retraining needed - drift is within acceptable range")
    logging.info("=" * 80)


# ============================================================================
# 클러스터링 모델 재학습 함수들
# ============================================================================

def run_clustering_training(**context):
    """
    Step 4-B: 클러스터링 모델 학습 파이프라인 실행

    VAE 피처 추출 → UMAP → HDBSCAN 클러스터링 → MLflow 등록
    """
    ti = context['ti']
    next_base_ym = ti.xcom_pull(key='next_base_ym', task_ids='determine_next_base_ym')

    logging.info("=" * 80)
    logging.info(f"🧠 Step 4-B: Running Clustering training pipeline")
    logging.info(f"   - base_ym: {next_base_ym}")
    logging.info("=" * 80)

    try:
        # 클러스터링 학습 파이프라인 실행
        result = run_clustering_pipeline(
            config_name='final_notebook_model',
            save_models=True,
            experiment_name='clustering_retraining',
            register_to_mlflow=True  # MLflow에 등록하되, Production 승격은 별도로
        )

        new_silhouette = result.get('silhouette_score', 0)
        n_clusters = result.get('n_clusters', 0)

        logging.info(f"✅ Clustering training completed!")
        logging.info(f"   - Clusters: {n_clusters}")
        logging.info(f"   - Silhouette Score: {new_silhouette:.4f}")
        logging.info(f"   - Samples: {result['n_samples']:,}")
        logging.info(f"   - Noise: {result['n_noise']:,}")

    except Exception as e:
        logging.error(f"❌ Clustering training failed: {str(e)}")
        raise

    # XCom에 저장
    context['ti'].xcom_push(key='clustering_silhouette', value=new_silhouette)
    context['ti'].xcom_push(key='clustering_n_clusters', value=n_clusters)
    context['ti'].xcom_push(key='clustering_result', value=result)


def evaluate_clustering_model(**context):
    """
    Step 5-B: 클러스터링 모델 성능 비교 및 승격 결정

    Returns:
        'promote_clustering' or 'log_clustering_only'
    """
    ti = context['ti']
    new_silhouette = ti.xcom_pull(key='clustering_silhouette', task_ids='run_clustering_training')

    logging.info("=" * 80)
    logging.info(f"📊 Step 5-B: Evaluating clustering model performance")
    logging.info("=" * 80)

    # 현재 Production 클러스터링 모델의 성능 조회
    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri("sqlite:///mlflow_db/mlflow.db")
        client = MlflowClient()

        # Production 모델 조회
        prod_versions = client.get_latest_versions("clustering_model", stages=["Production"])
        if prod_versions:
            prod_version = prod_versions[0]
            current_silhouette = float(prod_version.tags.get('silhouette_score', 0))
            logging.info(f"📌 Current Production Clustering Model:")
            logging.info(f"   - Version: {prod_version.version}")
            logging.info(f"   - Silhouette Score: {current_silhouette:.4f}")
        else:
            # Production 모델이 없으면 0으로 설정 (새 모델이 항상 승격됨)
            current_silhouette = 0
            logging.warning("⚠️  No Production clustering model found. New model will be promoted.")

    except Exception as e:
        logging.warning(f"⚠️  Failed to get current model: {e}")
        current_silhouette = 0

    # XCom에 저장
    context['ti'].xcom_push(key='current_clustering_silhouette', value=current_silhouette)

    improvement = new_silhouette - current_silhouette

    logging.info(f"📈 Clustering Performance Comparison:")
    logging.info(f"   - Current Silhouette: {current_silhouette:.4f}")
    logging.info(f"   - New Silhouette:     {new_silhouette:.4f}")
    logging.info(f"   - Improvement:        {improvement:+.4f}")

    # 승격 기준: Silhouette Score가 개선되었거나, Production 모델이 없을 때
    if new_silhouette > current_silhouette or current_silhouette == 0:
        logging.info(f"✅ New clustering model is better!")
        logging.info(f"   → Promoting to Production")
        return 'promote_clustering'
    else:
        logging.warning(f"⚠️  New clustering model is not better")
        logging.warning(f"   → Keeping current model in Production")
        return 'log_clustering_only'


def promote_clustering_to_production(**context):
    """
    Step 6-B: 클러스터링 모델 Production 승격
    """
    ti = context['ti']
    clustering_result = ti.xcom_pull(key='clustering_result', task_ids='run_clustering_training')

    logging.info("=" * 80)
    logging.info(f"🚀 Step 6-B: Promoting clustering model to Production")
    logging.info("=" * 80)

    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri("sqlite:///mlflow_db/mlflow.db")
        client = MlflowClient()

        model_name = "clustering_model"

        # 최신 모델 버전 가져오기 (방금 학습한 모델)
        versions = client.search_model_versions(f"name='{model_name}'")
        if not versions:
            raise ValueError("No clustering model versions found")

        latest_version = max(versions, key=lambda v: int(v.version))
        version = latest_version.version

        logging.info(f"📝 Promoting v{version} to Production...")

        # 기존 Production 모델 Archive
        try:
            existing_prod = client.get_latest_versions(model_name, stages=["Production"])
            for v in existing_prod:
                if v.version != version:  # 방금 승격한 모델이 아닌 경우만
                    client.transition_model_version_stage(
                        name=model_name,
                        version=v.version,
                        stage="Archived"
                    )
                    logging.info(f"   📦 v{v.version} → Archived")
        except Exception:
            pass

        # 새 버전을 Production으로
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Production"
        )
        logging.info(f"   ✅ v{version} → Production")

    except Exception as e:
        logging.error(f"❌ Clustering promotion failed: {str(e)}")
        raise

    # API 서버에 클러스터링 모델 재로드 요청
    logging.info("🔄 Reloading clustering model in API server...")
    try:
        response = requests.post(
            'http://localhost:8000/api/v1/clustering/admin/reload-model',
            timeout=30
        )
        if response.status_code == 200:
            logging.info(f"✅ Clustering API reload successful: {response.json()}")
        else:
            logging.warning(f"⚠️  Clustering API reload returned status {response.status_code}")
    except Exception as e:
        logging.error(f"❌ Clustering API reload failed: {str(e)}")
        logging.error("   → Please reload manually")


def log_clustering_only(**context):
    """
    Step 6-B-Alt: 클러스터링 모델이 승격되지 않았을 때 로그만 남김
    """
    ti = context['ti']
    clustering_result = ti.xcom_pull(key='clustering_result', task_ids='run_clustering_training')

    logging.info("=" * 80)
    logging.info(f"📝 Step 6-B-Alt: Logging clustering model without promotion")
    logging.info("=" * 80)

    logging.info(f"✅ Clustering training logged successfully")
    logging.info(f"   - Silhouette Score: {clustering_result.get('silhouette_score', 'N/A')}")
    logging.info(f"   - Clusters: {clustering_result.get('n_clusters', 'N/A')}")
    logging.info(f"   → Current production model remains unchanged")


def training_complete(**context):
    """
    모든 모델 학습 완료 후 실행되는 더미 태스크
    """
    logging.info("=" * 80)
    logging.info("✅ All model training pipelines completed!")
    logging.info("=" * 80)


# ============================================================================
# DAG Tasks
# ============================================================================

check_drift = BranchPythonOperator(
    task_id='check_drift_and_decide',
    python_callable=check_drift_and_decide,
    dag=dag,
)

determine_base_ym = PythonOperator(
    task_id='determine_next_base_ym',
    python_callable=determine_next_base_ym,
    dag=dag,
)

extract_data = PythonOperator(
    task_id='extract_training_data',
    python_callable=extract_training_data,
    dag=dag,
)

# ============================================================================
# 부도예측 모델 (Default Prediction) Tasks
# ============================================================================
train_default_model = PythonOperator(
    task_id='run_ml_training_pipeline',
    python_callable=run_ml_training_pipeline,
    dag=dag,
)

evaluate_default_model = BranchPythonOperator(
    task_id='evaluate_and_compare',
    python_callable=evaluate_and_compare,
    dag=dag,
)

promote_default_model = PythonOperator(
    task_id='promote_to_production',
    python_callable=promote_to_production,
    dag=dag,
)

log_default_only = PythonOperator(
    task_id='log_training_only',
    python_callable=log_training_only,
    dag=dag,
)

# ============================================================================
# 클러스터링 모델 (Clustering) Tasks
# ============================================================================
train_clustering_model = PythonOperator(
    task_id='run_clustering_training',
    python_callable=run_clustering_training,
    dag=dag,
)

evaluate_clustering = BranchPythonOperator(
    task_id='evaluate_clustering_model',
    python_callable=evaluate_clustering_model,
    dag=dag,
)

promote_clustering = PythonOperator(
    task_id='promote_clustering',
    python_callable=promote_clustering_to_production,
    dag=dag,
)

log_clustering = PythonOperator(
    task_id='log_clustering_only',
    python_callable=log_clustering_only,
    dag=dag,
)

# ============================================================================
# 공통 Tasks
# ============================================================================
skip = PythonOperator(
    task_id='skip_retraining',
    python_callable=skip_retraining,
    dag=dag,
)

# 모든 모델 학습 완료 후 실행되는 더미 태스크 (TriggerRule.ALL_DONE)
complete = EmptyOperator(
    task_id='training_complete',
    dag=dag,
    trigger_rule='none_failed_min_one_success',  # 하나 이상 성공하면 실행
)

# ============================================================================
# Task 의존성
# ============================================================================
# 1. 드리프트 체크 → 재학습 여부 결정
check_drift >> [determine_base_ym, skip]

# 2. 데이터 추출 (부도예측용)
determine_base_ym >> extract_data

# 3. 두 모델 학습 (병렬 실행)
#    - 부도예측 모델: extract_data 이후 실행
#    - 클러스터링 모델: determine_base_ym 이후 바로 실행 (별도 데이터 사용)
extract_data >> train_default_model
determine_base_ym >> train_clustering_model

# 4. 각 모델 평가 및 승격
train_default_model >> evaluate_default_model
evaluate_default_model >> [promote_default_model, log_default_only]

train_clustering_model >> evaluate_clustering
evaluate_clustering >> [promote_clustering, log_clustering]

# 5. 모든 브랜치가 완료되면 complete 태스크 실행
[promote_default_model, log_default_only, promote_clustering, log_clustering] >> complete
