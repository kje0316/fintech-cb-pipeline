# 데이터 파이프라인 아키텍처

## 📊 전체 구조

```
┌──────────────────────────────────────────────────────────────┐
│                     Application Layer                         │
│              FastAPI + Pydantic Validation                    │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                   Raw Layer (로그 DB)                         │
│  - prediction_logs (예측 로그)                                │
│  - upload_logs (업로드 로그)                                  │
│  - model_performance_logs (성능 로그)                         │
│                                                               │
│  목적: 원시 데이터 저장, 감사 추적                             │
└──────────────────────────────────────────────────────────────┘
                              ↓
                        ETL (Airflow)
                    매일 01:00 AM 실행
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                DWH Layer (Data Warehouse)                     │
│                                                               │
│  Fact Tables:                                                 │
│  - fact_predictions (예측 사실)                               │
│  - fact_model_performance (모델 성능 사실)                    │
│                                                               │
│  Dimension Tables:                                            │
│  - dim_date (날짜 차원)                                       │
│  - dim_model (모델 차원)                                      │
│  - dim_company (기업 차원)                                    │
│                                                               │
│  목적: 정규화, 분석 최적화                                     │
└──────────────────────────────────────────────────────────────┘
                              ↓
                  Aggregation (Airflow)
                    일별 집계 실행
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                   DM Layer (Data Mart)                        │
│  - dm_daily_predictions (일별 예측 집계)                      │
│  - dm_model_drift (모델 드리프트 분석)                        │
│  - dm_industry_risk (업종별 위험도)                           │
│  - dm_feature_distribution (피처 분포)                        │
│                                                               │
│  목적: 빠른 분석/대시보드, Drift 감지                          │
└──────────────────────────────────────────────────────────────┘
                              ↓
                      ┌───────────────┐
                      │   Monitoring   │
                      │  (Evidently)   │
                      └───────────────┘
```

---

## 🗄️ 데이터베이스 설정

### 1. PostgreSQL 설치 및 설정

```bash
# Docker로 PostgreSQL 실행
docker run -d \
  --name prediction-logs-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=prediction_logs \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:15

# 또는 로컬 설치
brew install postgresql@15
brew services start postgresql@15
```

### 2. 데이터베이스 생성

```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE prediction_logs;
CREATE DATABASE prediction_dwh;

# 연결
\c prediction_logs
```

### 3. 스키마 생성

```bash
# 로그 DB 스키마
psql -U postgres -d prediction_logs -f db/schemas/log_db_schema.sql

# DWH 스키마
psql -U postgres -d prediction_dwh -f db/schemas/dwh_schema.sql

# DM 스키마
psql -U postgres -d prediction_dwh -f db/schemas/dm_schema.sql
```

---

## 🔧 환경 변수 설정

`.env` 파일 생성:

```bash
# 로그 DB
LOG_DB_HOST=localhost
LOG_DB_PORT=5432
LOG_DB_NAME=prediction_logs
LOG_DB_USER=postgres
LOG_DB_PASSWORD=your_password

# DWH DB
DWH_DB_HOST=localhost
DWH_DB_PORT=5432
DWH_DB_NAME=prediction_dwh
DWH_DB_USER=postgres
DWH_DB_PASSWORD=your_password
```

---

## 📝 로그 DB 스키마 (Raw Layer)

### `prediction_logs` 테이블

예측 요청 및 결과를 저장합니다.

```sql
CREATE TABLE prediction_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id UUID UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 입력 데이터 (37개 컬럼) - JSONB
    input_data JSONB NOT NULL,

    -- 파생 피처 (70개) - JSONB
    derived_features JSONB,

    -- 예측 결과
    prediction_result JSONB NOT NULL,
    default_probability DECIMAL(5, 4),
    risk_level VARCHAR(20),

    -- 모델 정보
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,

    -- 실제 라벨 (나중에 업데이트)
    actual_default BOOLEAN,
    actual_default_date DATE,

    ...
);
```

**주요 필드**:
- `input_data`: 37개 입력 컬럼 (JSONB)
- `derived_features`: 70개 파생 피처 (JSONB)
- `prediction_result`: 예측 결과 전체 (JSONB)
- `actual_default`: Ground Truth (나중에 업데이트)

### `upload_logs` 테이블

엑셀 파일 업로드 로그를 저장합니다.

```sql
CREATE TABLE upload_logs (
    id BIGSERIAL PRIMARY KEY,
    upload_id UUID UNIQUE NOT NULL,
    file_name VARCHAR(500),
    status VARCHAR(20) NOT NULL,  -- success, failed, pending
    error_message TEXT,
    validation_errors JSONB,
    rows_processed INTEGER,
    ...
);
```

### `model_performance_logs` 테이블

모델 성능 및 Drift 메트릭을 저장합니다.

```sql
CREATE TABLE model_performance_logs (
    id BIGSERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    auc_roc DECIMAL(5, 4),
    psi_score DECIMAL(10, 6),
    ks_statistic DECIMAL(10, 6),
    ...
);
```

---

## 🏢 DWH 스키마 (Data Warehouse Layer)

### Fact Tables

#### `fact_predictions`

```sql
CREATE TABLE fact_predictions (
    prediction_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    model_key INTEGER NOT NULL REFERENCES dim_model(model_key),
    company_key INTEGER REFERENCES dim_company(company_key),

    default_probability DECIMAL(5, 4) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    current_ratio DECIMAL(10, 4),
    debt_ratio DECIMAL(10, 4),
    ...
);
```

### Dimension Tables

#### `dim_date` (날짜 차원)

```sql
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,  -- YYYYMMDD
    date DATE NOT NULL UNIQUE,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    is_weekend BOOLEAN,
    ...
);
```

#### `dim_model` (모델 차원)

```sql
CREATE TABLE dim_model (
    model_key SERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    auc_roc DECIMAL(5, 4),
    is_production BOOLEAN,
    ...
);
```

---

## 📈 DM 스키마 (Data Mart Layer)

### `dm_daily_predictions`

일별 예측 집계:

```sql
CREATE TABLE dm_daily_predictions (
    date DATE PRIMARY KEY,
    total_predictions INTEGER,
    low_risk_count INTEGER,
    medium_risk_count INTEGER,
    high_risk_count INTEGER,
    avg_default_probability DECIMAL(5, 4),
    actual_default_rate DECIMAL(5, 4),
    ...
);
```

### `dm_model_drift`

Drift 감지 결과:

```sql
CREATE TABLE dm_model_drift (
    analysis_date DATE NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    psi_score DECIMAL(10, 6),
    ks_drift_detected BOOLEAN,
    concept_drift_detected BOOLEAN,
    retrain_recommended BOOLEAN,
    ...
);
```

---

## 🔄 ETL 파이프라인 (Airflow)

### DAG: `etl_log_to_dwh`

**실행 주기**: 매일 01:00 AM

**Tasks**:
1. `extract_predictions_to_dwh` - 로그 DB → DWH (fact_predictions)
2. `extract_model_performance_to_dwh` - 로그 DB → DWH (fact_model_performance)
3. `aggregate_daily_predictions` - DWH → DM (dm_daily_predictions)
4. `refresh_materialized_views` - Materialized Views 갱신

**실행 방법**:

```bash
# Airflow 시작
cd airflow
airflow db init
airflow webserver -p 8080
airflow scheduler

# DAG 수동 실행 (테스트)
airflow dags trigger etl_log_to_dwh
```

---

## 🧪 테스트 및 검증

### 1. 로그 DB 데이터 확인

```sql
-- 오늘 예측 건수
SELECT COUNT(*) FROM prediction_logs WHERE DATE(created_at) = CURRENT_DATE;

-- 모델별 예측 분포
SELECT model_version, risk_level, COUNT(*)
FROM prediction_logs
WHERE DATE(created_at) = CURRENT_DATE
GROUP BY model_version, risk_level;
```

### 2. DWH 데이터 확인

```sql
-- Fact 테이블 건수
SELECT COUNT(*) FROM fact_predictions;

-- 모델별 평균 부도 확률
SELECT dm.model_version, AVG(fp.default_probability)
FROM fact_predictions fp
JOIN dim_model dm ON fp.model_key = dm.model_key
GROUP BY dm.model_version;
```

### 3. DM 데이터 확인

```sql
-- 최근 7일 트렌드
SELECT * FROM dm_daily_predictions
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC;

-- Drift 감지 이력
SELECT * FROM dm_model_drift
WHERE ks_drift_detected = TRUE OR concept_drift_detected = TRUE
ORDER BY analysis_date DESC;
```

---

## 🔍 모니터링 쿼리

### 일별 예측 트렌드

```sql
SELECT
    date,
    total_predictions,
    avg_default_probability,
    ROUND(low_risk_count::DECIMAL / total_predictions * 100, 2) as low_risk_pct,
    ROUND(medium_risk_count::DECIMAL / total_predictions * 100, 2) as medium_risk_pct,
    ROUND(high_risk_count::DECIMAL / total_predictions * 100, 2) as high_risk_pct
FROM dm_daily_predictions
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date;
```

### Drift 감지 알림

```sql
SELECT
    analysis_date,
    model_version,
    psi_score,
    ks_statistic,
    CASE
        WHEN psi_score > 0.25 THEN 'CRITICAL'
        WHEN psi_score > 0.10 THEN 'WARNING'
        ELSE 'STABLE'
    END as drift_status
FROM dm_model_drift
WHERE analysis_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY psi_score DESC;
```

---

## 🚀 다음 단계

1. **Evidently AI 통합** - Drift 자동 감지
2. **Airflow DAG 확장** - Drift 감지 → 재학습 트리거
3. **Grafana 대시보드** - 실시간 모니터링
4. **Slack 알림** - Drift 감지 시 자동 알림
5. **A/B 테스트** - Champion-Challenger 패턴

---

## 📚 참고 자료

- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)
- [Airflow 공식 문서](https://airflow.apache.org/docs/)
- [Evidently AI 가이드](https://docs.evidentlyai.com/)
- [Star Schema 설계 가이드](https://www.kimballgroup.com/)
