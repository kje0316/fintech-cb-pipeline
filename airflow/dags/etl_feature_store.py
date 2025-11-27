"""
Feature Store ETL 파이프라인

ML 모델 학습/추론용 70개 피처를 생성하여 Feature Store 마트에 적재

실행 조건:
1. 새로운 기준년월 데이터가 추가되었을 때
2. 모델 재학습 전 최신 피처 준비

Flow:
CSV 원본 → 70개 피처 변환 → Feature Store 마트 (marts.mart_feature_store_ml)
"""
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import sys
import os
import yaml

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
    'etl_feature_store',
    default_args=default_args,
    description='ML Feature Store ETL 파이프라인',
    schedule_interval=None,  # 수동 트리거 또는 다른 DAG에서 호출
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'feature-store', 'ml'],
)


def check_new_data(**context):
    """
    Step 1: 새로운 데이터 확인

    Feature Store에 없는 기준년월이 있는지 확인

    Returns:
        'build_feature_store' or 'skip_build'
    """
    logging.info("=" * 60)
    logging.info("📊 Step 1: Checking for new data...")
    logging.info("=" * 60)

    # 원본 CSV에서 사용 가능한 기준년월 목록
    csv_path = os.path.join(PROJECT_ROOT, 'data/raw/기업신용평가정보_합성데이터.csv')

    try:
        df_base_ym = pd.read_csv(csv_path, encoding='cp949', usecols=['기준년월'])
        available_base_yms = sorted(df_base_ym['기준년월'].unique().tolist())
        logging.info(f"📋 CSV 기준년월: {available_base_yms}")

    except Exception as e:
        logging.error(f"❌ CSV 로드 실패: {e}")
        return 'skip_build'

    # Feature Store에 있는 기준년월 목록
    try:
        dwh_db = PostgresHook(postgres_conn_id='dwh_db')
        existing_query = """
            SELECT DISTINCT base_ym
            FROM marts.mart_feature_store_ml
            ORDER BY base_ym
        """
        existing_df = dwh_db.get_pandas_df(existing_query)
        existing_base_yms = existing_df['base_ym'].tolist() if len(existing_df) > 0 else []
        logging.info(f"📋 Feature Store 기준년월: {existing_base_yms}")

    except Exception as e:
        logging.warning(f"⚠️ Feature Store 조회 실패 (테이블 없을 수 있음): {e}")
        existing_base_yms = []

    # 새로운 기준년월 확인
    new_base_yms = [ym for ym in available_base_yms if ym not in existing_base_yms]

    if new_base_yms:
        logging.info(f"🆕 새로운 기준년월 발견: {new_base_yms}")
        context['ti'].xcom_push(key='new_base_yms', value=new_base_yms)
        return 'build_feature_store'
    else:
        logging.info("✅ 모든 데이터가 이미 Feature Store에 있습니다.")
        return 'skip_build'


def build_feature_store(**context):
    """
    Step 2: Feature Store 빌드

    새로운 기준년월 데이터에 대해 70개 피처 생성 및 적재
    """
    logging.info("=" * 60)
    logging.info("🔧 Step 2: Building Feature Store...")
    logging.info("=" * 60)

    ti = context['ti']
    new_base_yms = ti.xcom_pull(key='new_base_yms', task_ids='check_new_data')

    if not new_base_yms:
        logging.warning("⚠️ 처리할 기준년월이 없습니다.")
        return

    # Feature Store 빌드 스크립트 import
    from etl.dwh_to_mart.build_feature_store import (
        create_schema,
        load_columns_map,
        load_raw_data,
        rename_columns,
        generate_70_features,
        insert_to_feature_store
    )

    # 스키마 생성
    create_schema()

    # 컬럼 매핑 로드
    columns_map = load_columns_map()

    total_inserted = 0

    for base_ym in new_base_yms:
        logging.info(f"\n{'='*40}")
        logging.info(f"📅 Processing base_ym: {base_ym}")
        logging.info(f"{'='*40}")

        try:
            # 원본 데이터 로드
            df_raw = load_raw_data(base_ym)

            if len(df_raw) == 0:
                logging.warning(f"⚠️ {base_ym}: 데이터 없음")
                continue

            # 컬럼명 변환
            df_renamed = rename_columns(df_raw, columns_map)
            df_renamed['base_ym'] = base_ym

            # 70개 피처 생성
            df_features = generate_70_features(df_renamed)

            # Feature Store 적재
            insert_to_feature_store(df_features, base_ym)

            total_inserted += len(df_features)
            logging.info(f"✅ {base_ym}: {len(df_features):,}건 적재 완료")

        except Exception as e:
            logging.error(f"❌ {base_ym} 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            continue

    logging.info(f"\n✅ Feature Store 빌드 완료: 총 {total_inserted:,}건")

    # XCom에 결과 저장
    context['ti'].xcom_push(key='total_inserted', value=total_inserted)
    context['ti'].xcom_push(key='processed_base_yms', value=new_base_yms)


def update_feature_store_stats(**context):
    """
    Step 3: Feature Store 통계 업데이트
    """
    logging.info("=" * 60)
    logging.info("📊 Step 3: Updating Feature Store statistics...")
    logging.info("=" * 60)

    dwh_db = PostgresHook(postgres_conn_id='dwh_db')

    # 전체 통계 조회
    stats_query = """
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT base_ym) as total_base_yms,
            COUNT(DISTINCT company_id) as total_companies,
            SUM(CASE WHEN default_yn = 1 THEN 1 ELSE 0 END) as default_count,
            AVG(CASE WHEN default_yn IS NOT NULL THEN default_yn ELSE NULL END) as default_rate
        FROM marts.mart_feature_store_ml
    """

    try:
        stats = dwh_db.get_first(stats_query)

        logging.info(f"📈 Feature Store 현황:")
        logging.info(f"   - 총 레코드: {stats[0]:,}")
        logging.info(f"   - 기준년월 수: {stats[1]}")
        logging.info(f"   - 고유 기업 수: {stats[2]:,}")
        logging.info(f"   - 부도 기업: {stats[3]:,}" if stats[3] else "   - 부도 기업: N/A")
        logging.info(f"   - 부도율: {stats[4]:.4f}" if stats[4] else "   - 부도율: N/A")

    except Exception as e:
        logging.error(f"❌ 통계 조회 실패: {e}")


def skip_build(**context):
    """빌드 스킵"""
    logging.info("=" * 60)
    logging.info("✅ Feature Store 빌드 스킵 - 모든 데이터가 최신 상태입니다.")
    logging.info("=" * 60)


# ============================================================================
# DAG Tasks
# ============================================================================

check_data = BranchPythonOperator(
    task_id='check_new_data',
    python_callable=check_new_data,
    dag=dag,
)

build_store = PythonOperator(
    task_id='build_feature_store',
    python_callable=build_feature_store,
    dag=dag,
)

update_stats = PythonOperator(
    task_id='update_feature_store_stats',
    python_callable=update_feature_store_stats,
    dag=dag,
)

skip = PythonOperator(
    task_id='skip_build',
    python_callable=skip_build,
    dag=dag,
)

# 완료 태스크 (모든 브랜치 합류점)
complete = EmptyOperator(
    task_id='complete',
    dag=dag,
    trigger_rule='none_failed_min_one_success',
)

# Task 의존성
check_data >> [build_store, skip]
build_store >> update_stats >> complete
skip >> complete
