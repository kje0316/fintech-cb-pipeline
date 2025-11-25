"""
ETL 파이프라인: 로그 DB → DWH → DM

매일 자정에 실행되어:
1. 로그 DB에서 전날 데이터 추출
2. DWH (Fact/Dimension) 테이블에 적재
3. DM (Data Mart) 테이블 집계
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging


default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'etl_log_to_dwh',
    default_args=default_args,
    description='로그 DB → DWH → DM ETL 파이프라인',
    schedule_interval='0 1 * * *',  # 매일 01:00 AM (KST)
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'dwh', 'dm'],
)


def extract_predictions_to_dwh(**context):
    """
    Task 1: 로그 DB → DWH (fact_predictions)

    전날 prediction_logs에서 데이터를 추출하여 fact_predictions에 적재
    """
    execution_date = context['execution_date']
    # TEMPORARY: 테스트를 위해 -1일 로직 제거
    target_date = execution_date.date()  # (execution_date - timedelta(days=1)).date()

    logging.info(f"📦 Extracting predictions for date: {target_date}")

    # 로그 DB 연결
    log_db = PostgresHook(postgres_conn_id='log_db')
    # DWH DB 연결
    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    # 1. 로그 DB에서 데이터 추출
    extract_query = """
        SELECT
            pl.request_id,
            pl.created_at,
            pl.input_data,
            pl.derived_features,
            pl.prediction_result,
            pl.default_probability,
            pl.risk_level,
            pl.model_version,
            pl.model_type,
            pl.inference_time_ms,
            pl.actual_default,
            pl.actual_default_date
        FROM logs.prediction_logs pl
        WHERE DATE(pl.created_at) = %s
    """

    records = log_db.get_records(extract_query, parameters=(target_date,))
    logging.info(f"✅ Extracted {len(records)} prediction records")

    if not records:
        logging.warning("⚠️  No records to process")
        return

    # 2. DWH에 적재
    insert_query = """
        INSERT INTO dwh.fact_predictions (
            date_key, model_key, request_id,
            default_probability, risk_level,
            current_ratio, debt_ratio, equity_ratio,
            has_delinquency, max_delinquency_days,
            actual_default, actual_default_date,
            inference_time_ms, created_at
        )
        SELECT
            TO_CHAR(%s::DATE, 'YYYYMMDD')::INTEGER,
            dm.model_key,
            %s,
            %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s
        FROM dwh.dim_model dm
        WHERE dm.model_version = %s AND dm.model_type = %s
        ON CONFLICT (request_id) DO NOTHING
    """

    inserted_count = 0
    for record in records:
        request_id = record[0]
        created_at = record[1]
        input_data = record[2]
        derived_features = record[3]
        prediction_result = record[4]
        default_probability = record[5]
        risk_level = record[6]
        model_version = record[7]
        model_type = record[8]
        inference_time_ms = record[9]
        actual_default = record[10]
        actual_default_date = record[11]

        # Fallback: prediction_result에서 값 추출 (컬럼이 NULL인 경우)
        if default_probability is None and prediction_result:
            prob_value = prediction_result.get('default_probability')
            if prob_value is not None:
                default_probability = float(prob_value)  # Convert string to float
        if risk_level is None and prediction_result:
            risk_level = prediction_result.get('risk_level')

        # 여전히 None이면 0으로 기본값 설정 (NOT NULL 제약 회피)
        if default_probability is None:
            logging.warning(f"⚠️  default_probability is NULL for {request_id}, setting to 0")
            default_probability = 0.0
        if risk_level is None:
            logging.warning(f"⚠️  risk_level is NULL for {request_id}, setting to 'Unknown'")
            risk_level = 'Unknown'

        # 재무 비율 추출 (derived_features에서)
        current_ratio = derived_features.get('current_ratio', None) if derived_features else None
        debt_ratio = derived_features.get('debt_ratio', None) if derived_features else None
        equity_ratio = derived_features.get('equity_ratio', None) if derived_features else None

        # 연체 정보 추출
        has_delinquency = input_data.get('da0d00029', 0) > 0 if input_data else False
        max_delinquency_days = max(
            input_data.get('da0d00035_1', 0),
            input_data.get('da0d00035_2', 0),
            input_data.get('da0d00033_1', 0)
        ) if input_data else 0

        dwh_db.run(
            insert_query,
            parameters=(
                target_date, request_id,
                default_probability, risk_level,
                current_ratio, debt_ratio, equity_ratio,
                has_delinquency, max_delinquency_days,
                actual_default, actual_default_date,
                inference_time_ms, created_at,
                model_version, model_type
            )
        )
        inserted_count += 1

    logging.info(f"✅ Inserted {inserted_count} records into fact_predictions")


def extract_model_performance_to_dwh(**context):
    """
    Task 2: 로그 DB → DWH (fact_model_performance)

    전날 model_performance_logs 데이터를 fact_model_performance에 적재
    """
    execution_date = context['execution_date']
    # TEMPORARY: 테스트를 위해 -1일 로직 제거
    target_date = execution_date.date()  # (execution_date - timedelta(days=1)).date()

    logging.info(f"📦 Extracting model performance for date: {target_date}")

    log_db = PostgresHook(postgres_conn_id='log_db')
    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    # 1. 로그 DB에서 데이터 추출
    extract_query = """
        SELECT
            mpl.logged_at,
            mpl.model_version,
            mpl.model_type,
            mpl.auc_roc,
            mpl.precision_score,
            mpl.recall,
            mpl.f1_score,
            mpl.psi_score,
            mpl.ks_statistic,
            mpl.ks_pvalue,
            mpl.avg_prediction,
            mpl.std_prediction,
            mpl.evaluation_period_start,
            mpl.evaluation_period_end,
            mpl.sample_size,
            mpl.notes
        FROM logs.model_performance_logs mpl
        WHERE DATE(mpl.logged_at) = %s
    """

    records = log_db.get_records(extract_query, parameters=(target_date,))
    logging.info(f"✅ Extracted {len(records)} performance records")

    if not records:
        return

    # 2. DWH에 적재
    insert_query = """
        INSERT INTO dwh.fact_model_performance (
            date_key, model_key,
            auc_roc, precision_score, recall, f1_score,
            psi_score, ks_statistic, ks_pvalue,
            avg_prediction, std_prediction,
            evaluation_period_start, evaluation_period_end,
            sample_size, notes, logged_at
        )
        SELECT
            TO_CHAR(%s::DATE, 'YYYYMMDD')::INTEGER,
            dm.model_key,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s
        FROM dwh.dim_model dm
        WHERE dm.model_version = %s AND dm.model_type = %s
    """

    for record in records:
        dwh_db.run(insert_query, parameters=record[1:] + (target_date,))

    logging.info(f"✅ Inserted {len(records)} records into fact_model_performance")


def aggregate_daily_predictions(**context):
    """
    Task 3: DWH → DM (dm_daily_predictions)

    fact_predictions 데이터를 일별로 집계
    """
    execution_date = context['execution_date']
    # TEMPORARY: 테스트를 위해 -1일 로직 제거
    target_date = execution_date.date()  # (execution_date - timedelta(days=1)).date()

    logging.info(f"📊 Aggregating daily predictions for date: {target_date}")

    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    # DM 집계 함수 실행
    dwh_db.run(f"SELECT refresh_dm_daily_predictions('{target_date}')")

    logging.info(f"✅ Aggregated dm_daily_predictions for {target_date}")


def refresh_materialized_views(**context):
    """
    Task 4: Materialized Views 갱신
    """
    logging.info("🔄 Refreshing materialized views...")

    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    views = [
        'mv_recent_predictions',
    ]

    for view in views:
        dwh_db.run(f"REFRESH MATERIALIZED VIEW {view}")
        logging.info(f"✅ Refreshed {view}")


# ============================================================================
# DAG Tasks
# ============================================================================

extract_predictions = PythonOperator(
    task_id='extract_predictions_to_dwh',
    python_callable=extract_predictions_to_dwh,
    dag=dag,
)

extract_model_performance = PythonOperator(
    task_id='extract_model_performance_to_dwh',
    python_callable=extract_model_performance_to_dwh,
    dag=dag,
)

aggregate_daily = PythonOperator(
    task_id='aggregate_daily_predictions',
    python_callable=aggregate_daily_predictions,
    dag=dag,
)

refresh_views = PythonOperator(
    task_id='refresh_materialized_views',
    python_callable=refresh_materialized_views,
    dag=dag,
)

# Task 의존성
extract_predictions >> aggregate_daily
extract_model_performance >> aggregate_daily
aggregate_daily >> refresh_views
