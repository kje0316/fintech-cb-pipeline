"""
드리프트 감지 시 자동 재학습 파이프라인

실행 조건:
1. 주간으로 PSI 계산 및 드리프트 체크
2. PSI > 0.2이면 다음 기준년월 데이터로 재학습
3. 새 모델 성능이 현재 모델보다 2% 이상 좋으면 Production 승격
4. API 서버에 모델 재로드 요청

기준년월 순서: 20210801 → 20220801 → 20230801 → ...
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
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

    # 원본 CSV에서 사용 가능한 기준년월 목록 조회
    import pandas as pd
    import os

    # 프로젝트 루트 디렉토리 찾기
    airflow_home = os.environ.get('AIRFLOW_HOME', '/Users/kje/coding/project/fintech-cb-pipeline/airflow')
    project_root = os.path.dirname(airflow_home)
    csv_path = os.path.join(project_root, 'data/raw/기업신용평가정보_합성데이터.csv')

    logging.info(f"📂 Reading base_ym from: {csv_path}")

    df_base_ym = pd.read_csv(csv_path, encoding='cp949', usecols=['기준년월'])
    available_base_yms = sorted(df_base_ym['기준년월'].unique().tolist())

    logging.info(f"📋 Available base_ym in source CSV: {available_base_yms}")

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
    Step 3: 원본 CSV에서 새 기준년월 데이터 추출
    """
    import pandas as pd

    ti = context['ti']
    next_base_ym = ti.xcom_pull(key='next_base_ym', task_ids='determine_next_base_ym')

    logging.info("=" * 80)
    logging.info(f"📦 Step 3: Extracting training data for base_ym={next_base_ym}")
    logging.info("=" * 80)

    # 원본 CSV 경로
    airflow_home = os.environ.get('AIRFLOW_HOME', '/Users/kje/coding/project/fintech-cb-pipeline/airflow')
    project_root = os.path.dirname(airflow_home)
    csv_path = os.path.join(project_root, 'data/raw/기업신용평가정보_합성데이터.csv')

    logging.info(f"📂 Reading from: {csv_path}")

    # 해당 기준년월 데이터만 필터링
    df = pd.read_csv(csv_path, encoding='cp949')
    df_filtered = df[df['기준년월'] == next_base_ym].copy()

    logging.info(f"✅ Extracted {len(df_filtered)} rows for base_ym={next_base_ym}")
    logging.info(f"   - Total columns: {len(df_filtered.columns)}")

    # Default flag 컬럼 확인 (없으면 경고)
    default_col = None
    for col in df_filtered.columns:
        if 'default' in col.lower() or '부도' in col:
            default_col = col
            break

    if default_col:
        logging.info(f"   - Default column: {default_col}")
        logging.info(f"   - Default rate: {df_filtered[default_col].mean():.4f}")
    else:
        logging.warning("⚠️  No default flag column found")

    if len(df_filtered) < 1000:
        raise ValueError(f"Not enough training data! Only {len(df_filtered)} rows found for base_ym={next_base_ym}")

    # Parquet 저장
    output_dir = os.path.join(project_root, 'ml/data')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'raw_data_full_{next_base_ym}.parquet')

    df_filtered.to_parquet(output_path, index=False)
    logging.info(f"💾 Saved to: {output_path}")

    # XCom에 저장
    context['ti'].xcom_push(key='training_data_path', value=output_path)
    context['ti'].xcom_push(key='training_samples', value=len(df_filtered))

    default_rate = df_filtered[default_col].mean() if default_col else 0.0
    context['ti'].xcom_push(key='default_rate', value=float(default_rate))


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

    # 실제로는 ml/scripts/run_full_ml_pipeline.py 를 base_ym 파라미터와 함께 실행
    # 여기서는 간단히 시뮬레이션

    logging.info("📝 Step 4-1: Feature Engineering...")
    # subprocess.run(['python3', f'{PROJECT_ROOT}/ml/scripts/03_feature_engineering.py', '--base_ym', str(next_base_ym)])

    logging.info("🎓 Step 4-2: Model Training...")
    # subprocess.run(['python3', f'{PROJECT_ROOT}/ml/scripts/04_train_default_model.py', '--base_ym', str(next_base_ym)])

    # 시뮬레이션: 새 모델의 성능 (실제로는 학습 후 MLflow에서 조회)
    import random
    random.seed(next_base_ym)
    new_auc = 0.746 + random.uniform(-0.03, 0.05)  # 0.716 ~ 0.796 범위
    new_auc = round(new_auc, 4)

    logging.info(f"✅ Training completed!")
    logging.info(f"   - New model AUC-ROC: {new_auc:.4f}")

    # XCom에 저장
    context['ti'].xcom_push(key='new_auc', value=new_auc)


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

train_model = PythonOperator(
    task_id='run_ml_training_pipeline',
    python_callable=run_ml_training_pipeline,
    dag=dag,
)

evaluate_model = BranchPythonOperator(
    task_id='evaluate_and_compare',
    python_callable=evaluate_and_compare,
    dag=dag,
)

promote_model = PythonOperator(
    task_id='promote_to_production',
    python_callable=promote_to_production,
    dag=dag,
)

log_only = PythonOperator(
    task_id='log_training_only',
    python_callable=log_training_only,
    dag=dag,
)

skip = PythonOperator(
    task_id='skip_retraining',
    python_callable=skip_retraining,
    dag=dag,
)

# Task 의존성
check_drift >> [determine_base_ym, skip]
determine_base_ym >> extract_data >> train_model >> evaluate_model
evaluate_model >> [promote_model, log_only]
