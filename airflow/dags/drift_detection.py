"""
Drift 감지 파이프라인

매주 월요일 02:00 AM에 실행되어:
1. 최근 7일 예측 데이터 vs 기준선(학습 데이터) 비교
2. PSI (Population Stability Index) 계산
3. KS-Test (Kolmogorov-Smirnov Test) 수행
4. Drift 임계값 초과 시 알림 및 재학습 트리거
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np
from scipy import stats


default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'drift_detection',
    default_args=default_args,
    description='모델 Drift 감지 및 재학습 트리거',
    schedule_interval='0 2 * * 1',  # 매주 월요일 02:00 AM
    catchup=False,
    max_active_runs=1,
    tags=['mlops', 'drift-detection', 'monitoring'],
)


def calculate_psi(expected, actual, bins=10):
    """
    Population Stability Index (PSI) 계산
    
    PSI < 0.10: 안정 (No action)
    0.10 < PSI < 0.25: 주의 (Monitoring)
    PSI > 0.25: 불안정 (Retrain recommended)
    
    Args:
        expected: 기준선 데이터 (학습 데이터)
        actual: 현재 데이터 (최근 예측 데이터)
        bins: 구간 수
    
    Returns:
        PSI score
    """
    def psi_score(expected_array, actual_array, buckets):
        """PSI 계산 핵심 함수"""
        breakpoints = np.arange(0, buckets + 1) / buckets * 100
        
        expected_percents = np.histogram(expected_array, np.percentile(expected_array, breakpoints))[0] / len(expected_array)
        actual_percents = np.histogram(actual_array, np.percentile(expected_array, breakpoints))[0] / len(actual_array)
        
        # 0으로 나누는 것 방지
        expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
        actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)
        
        psi_values = (actual_percents - expected_percents) * np.log(actual_percents / expected_percents)
        
        return np.sum(psi_values)
    
    return psi_score(expected, actual, bins)


def calculate_ks_test(expected, actual):
    """
    Kolmogorov-Smirnov Test 수행
    
    p-value < 0.05: 분포가 유의미하게 다름 (Drift 발생)
    p-value >= 0.05: 분포가 비슷함 (안정)
    
    Returns:
        (ks_statistic, p_value)
    """
    return stats.ks_2samp(expected, actual)


def detect_data_drift(**context):
    """
    Task 1: Data Drift 감지 (PSI, KS-Test)
    
    최근 7일 예측 데이터 vs 기준선 데이터 비교
    """
    execution_date = context['execution_date']
    model_version = 'v4'  # TODO: 동적으로 가져오기
    
    logging.info(f"🔍 Detecting data drift for model: {model_version}")
    
    dwh_db = PostgresHook(postgres_conn_id='dwh_db')
    
    # 1. 기준선 데이터 (학습 데이터) 조회
    # TODO: 실제로는 학습 데이터를 별도 테이블에 저장해야 함
    baseline_query = """
        SELECT default_probability
        FROM fact_predictions fp
        JOIN dim_model dm ON fp.model_key = dm.model_key
        WHERE dm.model_version = %s
        AND fp.created_at >= NOW() - INTERVAL '90 days'
        AND fp.created_at < NOW() - INTERVAL '7 days'
        ORDER BY RANDOM()
        LIMIT 1000
    """
    
    baseline_data = dwh_db.get_pandas_df(baseline_query, parameters=(model_version,))
    
    if baseline_data.empty:
        logging.warning("⚠️  No baseline data found")
        return {'drift_detected': False, 'reason': 'No baseline data'}
    
    # 2. 현재 데이터 (최근 7일) 조회
    current_query = """
        SELECT default_probability
        FROM fact_predictions fp
        JOIN dim_model dm ON fp.model_key = dm.model_key
        WHERE dm.model_version = %s
        AND fp.created_at >= NOW() - INTERVAL '7 days'
    """
    
    current_data = dwh_db.get_pandas_df(current_query, parameters=(model_version,))
    
    if current_data.empty:
        logging.warning("⚠️  No current data found")
        return {'drift_detected': False, 'reason': 'No current data'}
    
    logging.info(f"📊 Baseline samples: {len(baseline_data)}, Current samples: {len(current_data)}")
    
    # 3. PSI 계산
    psi_score = calculate_psi(
        baseline_data['default_probability'].values,
        current_data['default_probability'].values
    )
    
    logging.info(f"📈 PSI Score: {psi_score:.6f}")
    
    # PSI 상태 판정
    if psi_score < 0.10:
        psi_status = 'stable'
    elif psi_score < 0.25:
        psi_status = 'warning'
    else:
        psi_status = 'alert'
    
    # 4. KS-Test 수행
    ks_statistic, ks_pvalue = calculate_ks_test(
        baseline_data['default_probability'].values,
        current_data['default_probability'].values
    )
    
    logging.info(f"📈 KS Statistic: {ks_statistic:.6f}, p-value: {ks_pvalue:.6f}")
    
    ks_drift_detected = ks_pvalue < 0.05
    
    # 5. 결과 저장 (dm_model_drift)
    insert_query = """
        INSERT INTO dm_model_drift (
            analysis_date, model_version,
            baseline_start, baseline_end,
            current_start, current_end,
            psi_score, psi_status,
            ks_statistic, ks_pvalue, ks_drift_detected,
            retrain_recommended, alert_triggered
        ) VALUES (
            %s, %s,
            NOW() - INTERVAL '90 days', NOW() - INTERVAL '7 days',
            NOW() - INTERVAL '7 days', NOW(),
            %s, %s,
            %s, %s, %s,
            %s, %s
        )
    """
    
    retrain_recommended = (psi_status == 'alert' or ks_drift_detected)
    alert_triggered = retrain_recommended
    
    dwh_db.run(
        insert_query,
        parameters=(
            execution_date.date(), model_version,
            psi_score, psi_status,
            ks_statistic, ks_pvalue, ks_drift_detected,
            retrain_recommended, alert_triggered
        )
    )
    
    logging.info(f"✅ Drift analysis completed and saved")
    
    # 6. XCom에 결과 저장 (다음 Task에서 사용)
    context['task_instance'].xcom_push(key='drift_detected', value=retrain_recommended)
    context['task_instance'].xcom_push(key='psi_score', value=float(psi_score))
    context['task_instance'].xcom_push(key='ks_pvalue', value=float(ks_pvalue))
    
    return {
        'drift_detected': retrain_recommended,
        'psi_score': float(psi_score),
        'psi_status': psi_status,
        'ks_statistic': float(ks_statistic),
        'ks_pvalue': float(ks_pvalue)
    }


def send_alert_if_needed(**context):
    """
    Task 2: Drift 감지 시 알림 전송
    
    Slack, Email 등으로 알림 전송
    """
    ti = context['task_instance']
    drift_detected = ti.xcom_pull(task_ids='detect_data_drift', key='drift_detected')
    psi_score = ti.xcom_pull(task_ids='detect_data_drift', key='psi_score')
    ks_pvalue = ti.xcom_pull(task_ids='detect_data_drift', key='ks_pvalue')
    
    if not drift_detected:
        logging.info("✅ No drift detected, no alert needed")
        return
    
    logging.warning(f"🚨 DRIFT DETECTED!")
    logging.warning(f"   PSI Score: {psi_score:.6f}")
    logging.warning(f"   KS p-value: {ks_pvalue:.6f}")
    
    # TODO: Slack/Email 알림 전송
    # slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    # requests.post(slack_webhook, json={
    #     'text': f'🚨 Model Drift Detected!\nPSI: {psi_score:.4f}\nKS p-value: {ks_pvalue:.4f}\nRetraining recommended.'
    # })
    
    logging.info("📧 Alert sent (placeholder)")


# ============================================================================
# DAG Tasks
# ============================================================================

detect_drift = PythonOperator(
    task_id='detect_data_drift',
    python_callable=detect_data_drift,
    dag=dag,
)

send_alert = PythonOperator(
    task_id='send_alert_if_needed',
    python_callable=send_alert_if_needed,
    dag=dag,
)

# TODO: 재학습 DAG 트리거 (나중에 구현)
# trigger_retrain = TriggerDagRunOperator(
#     task_id='trigger_retrain',
#     trigger_dag_id='model_retrain',
#     dag=dag,
# )

# Task 의존성
detect_drift >> send_alert
# detect_drift >> trigger_retrain  # (나중에 활성화)
