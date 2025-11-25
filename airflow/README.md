# Airflow ETL/MLOps Pipeline Setup Guide

## Overview

이 프로젝트는 Apache Airflow를 사용하여 다음 파이프라인을 자동화합니다:

1. **ETL Pipeline** (`etl_log_to_dwh.py`): 로그 DB → DWH → DM 일배치 처리
2. **Drift Detection** (`drift_detection.py`): 모델 드리프트 감지 및 재학습 트리거
3. **Model Retrain** (TODO): 모델 재학습 파이프라인

## Architecture

```
┌─────────────┐     Daily 01:00      ┌─────────────┐     Weekly Mon 02:00    ┌──────────────┐
│  Log DB     │ ──────────────────→  │  DWH/DM     │ ────────────────────→  │ Drift Check  │
│ (Raw Logs)  │   ETL Pipeline       │ (Analytics) │   PSI/KS-Test          │ & Alert      │
└─────────────┘                       └─────────────┘                         └──────────────┘
                                                                                      │
                                                                                      ↓
                                                                              ┌──────────────┐
                                                                              │   Retrain    │
                                                                              │   Pipeline   │
                                                                              └──────────────┘
```

---

## 1. Installation

### Prerequisites

- Python 3.8+
- PostgreSQL (로그 DB, DWH DB 설정 완료)
- pip or uv

### Install Airflow

```bash
# Option 1: pip 사용
pip install "apache-airflow[postgres]==2.8.1" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.11.txt"

# Option 2: uv 사용 (더 빠름)
uv pip install "apache-airflow[postgres]==2.8.1" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.8.1/constraints-3.11.txt"
```

### Install Additional Dependencies

```bash
pip install psycopg2-binary pandas numpy scipy
```

---

## 2. Configuration

### Set Airflow Home

```bash
export AIRFLOW_HOME=/Users/kje/coding/project/fintech-cb-pipeline/airflow
echo 'export AIRFLOW_HOME=/Users/kje/coding/project/fintech-cb-pipeline/airflow' >> ~/.zshrc
source ~/.zshrc
```

### Initialize Airflow Database

```bash
cd /Users/kje/coding/project/fintech-cb-pipeline/airflow
airflow db init
```

### Create Admin User

```bash
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```

---

## 3. Database Connections

Airflow에서 PostgreSQL 연결을 설정해야 합니다.

### Add Connections via CLI

```bash
# 로그 DB 연결
airflow connections add 'log_db' \
    --conn-type 'postgres' \
    --conn-host 'localhost' \
    --conn-schema 'mlops_logs' \
    --conn-login 'mlops_user' \
    --conn-password 'your_password' \
    --conn-port 5432

# DWH DB 연결
airflow connections add 'dwh_db' \
    --conn-type 'postgres' \
    --conn-host 'localhost' \
    --conn-schema 'mlops_dwh' \
    --conn-login 'mlops_user' \
    --conn-password 'your_password' \
    --conn-port 5432
```

### Or Add Connections via Web UI

1. Airflow 웹서버 실행 후 http://localhost:8080 접속
2. Admin → Connections 메뉴
3. `+` 버튼으로 새 Connection 추가

**Connection ID**: `log_db`
- Connection Type: `Postgres`
- Host: `localhost`
- Schema: `mlops_logs`
- Login: `mlops_user`
- Password: `your_password`
- Port: `5432`

**Connection ID**: `dwh_db`
- Connection Type: `Postgres`
- Host: `localhost`
- Schema: `mlops_dwh`
- Login: `mlops_user`
- Password: `your_password`
- Port: `5432`

---

## 4. Start Airflow

### Option 1: Standalone Mode (개발용)

```bash
cd /Users/kje/coding/project/fintech-cb-pipeline/airflow
airflow standalone
```

이 명령은 웹서버, 스케줄러, 메타데이터 DB를 모두 한 번에 실행합니다.

### Option 2: Separate Components (프로덕션용)

**Terminal 1 - Webserver**:
```bash
airflow webserver --port 8080
```

**Terminal 2 - Scheduler**:
```bash
airflow scheduler
```

---

## 5. DAGs Overview

### ETL Pipeline: `etl_log_to_dwh`

**스케줄**: 매일 01:00 AM (KST)

**Tasks**:
1. `extract_predictions_to_dwh`: prediction_logs → fact_predictions
2. `extract_model_performance_to_dwh`: model_performance_logs → fact_model_performance
3. `aggregate_daily_predictions`: DWH → DM 일별 집계
4. `refresh_materialized_views`: Materialized View 갱신

**Task Flow**:
```
extract_predictions ──┐
                      ├──→ aggregate_daily ──→ refresh_views
extract_model_perf ───┘
```

**Manual Trigger**:
```bash
airflow dags trigger etl_log_to_dwh
```

### Drift Detection: `drift_detection`

**스케줄**: 매주 월요일 02:00 AM

**Tasks**:
1. `detect_data_drift`: PSI/KS-Test 계산 및 저장
2. `send_alert_if_needed`: Drift 감지 시 알림

**Drift Metrics**:
- **PSI (Population Stability Index)**:
  - < 0.10: 안정 (No action)
  - 0.10 - 0.25: 주의 (Monitoring)
  - \> 0.25: 불안정 (Retrain recommended)

- **KS-Test (Kolmogorov-Smirnov)**:
  - p-value < 0.05: Drift 발생
  - p-value >= 0.05: 안정

**Manual Trigger**:
```bash
airflow dags trigger drift_detection
```

---

## 6. Testing

### Test ETL Pipeline Manually

```bash
# 특정 날짜로 백필 실행
airflow dags backfill etl_log_to_dwh \
    --start-date 2025-01-20 \
    --end-date 2025-01-21
```

### Test Drift Detection Manually

```bash
airflow dags trigger drift_detection
```

### Check Task Logs

```bash
# 웹 UI에서 확인: http://localhost:8080
# 또는 CLI로 확인
airflow tasks test drift_detection detect_data_drift 2025-01-24
```

---

## 7. Monitoring

### Web UI

- **URL**: http://localhost:8080
- **Username**: `admin`
- **Password**: `admin` (또는 설정한 비밀번호)

### Key Metrics to Monitor

1. **DAG Runs**: 성공/실패 여부
2. **Task Duration**: 각 Task 실행 시간
3. **Logs**: 에러 로그 확인
4. **Connections**: DB 연결 상태

### DM Tables to Check

```sql
-- 일별 예측 집계 확인
SELECT * FROM dm_daily_predictions
ORDER BY date DESC LIMIT 7;

-- Drift 분석 결과 확인
SELECT
    analysis_date,
    model_version,
    psi_score,
    psi_status,
    ks_pvalue,
    ks_drift_detected,
    retrain_recommended
FROM dm_model_drift
ORDER BY analysis_date DESC;
```

---

## 8. Troubleshooting

### DAG Not Appearing in Web UI

```bash
# DAG 파일 구문 오류 확인
python airflow/dags/etl_log_to_dwh.py
python airflow/dags/drift_detection.py

# Airflow DAG 목록 확인
airflow dags list
```

### Connection Error

```bash
# Connection 목록 확인
airflow connections list

# Connection 테스트
airflow connections test log_db
airflow connections test dwh_db
```

### Task Failure

1. Web UI에서 Task 로그 확인
2. 로그에서 에러 메시지 확인
3. DB 연결, 쿼리, 데이터 무결성 검증

### Permission Issues

```bash
# Airflow 디렉토리 권한 확인
ls -la /Users/kje/coding/project/fintech-cb-pipeline/airflow

# 로그 디렉토리 생성
mkdir -p airflow/logs
chmod -R 755 airflow/logs
```

---

## 9. Production Deployment

### Using Docker (권장)

`docker-compose.yaml` 예시:

```yaml
version: '3'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data

  airflow-webserver:
    image: apache/airflow:2.8.1
    depends_on:
      - postgres
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    ports:
      - "8080:8080"
    command: webserver

  airflow-scheduler:
    image: apache/airflow:2.8.1
    depends_on:
      - postgres
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    command: scheduler

volumes:
  postgres-db-volume:
```

### Environment Variables

프로덕션 환경에서는 `.env` 파일 사용:

```bash
# .env
AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
AIRFLOW__CORE__LOAD_EXAMPLES=False
AIRFLOW__WEBSERVER__SECRET_KEY=your_secret_key_here
```

---

## 10. Next Steps

### TODO: Model Retrain DAG

아직 구현되지 않은 재학습 파이프라인:

1. Drift Detection이 재학습 추천 시 자동 트리거
2. Ground Truth 라벨이 있는 데이터 추출
3. 피처 엔지니어링 파이프라인 실행
4. 모델 재학습 및 검증
5. MLflow에 새 모델 등록
6. 성능이 개선되면 프로덕션 배포

### TODO: Alert Integration

현재 placeholder로 구현된 알림 기능:

1. Slack Webhook 연동
2. Email 알림 설정
3. PagerDuty/Opsgenie 연동 (선택)

### TODO: Grafana Dashboard

DM 테이블을 Grafana와 연동하여 시각화:

1. Prediction trends (일별 예측 수, 리스크 분포)
2. Drift scores (PSI, KS-Test 추이)
3. Model performance (AUC, Precision, Recall)
4. API metrics (응답 시간, 에러율)

---

## References

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Airflow PostgreSQL Provider](https://airflow.apache.org/docs/apache-airflow-providers-postgres/)
- [PSI (Population Stability Index)](https://mwburke.github.io/data%20science/2018/04/29/population-stability-index.html)
- [Model Monitoring Best Practices](https://neptune.ai/blog/ml-model-monitoring-best-practices)
