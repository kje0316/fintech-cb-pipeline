-- ============================================================================
-- Data Warehouse (DWH) Schema
--
-- 목적: 로그 DB에서 정규화된 데이터를 추출하여 분석 최적화
-- ============================================================================

-- ============================================================================
-- Dimension Tables (차원 테이블)
-- ============================================================================

-- 날짜 차원 (Date Dimension)
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,  -- YYYYMMDD
    date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    week INTEGER NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(10) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN DEFAULT FALSE,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER
);

CREATE INDEX idx_dim_date_date ON dim_date(date);
CREATE INDEX idx_dim_date_year_month ON dim_date(year, month);

-- 모델 차원 (Model Dimension)
CREATE TABLE dim_model (
    model_key SERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    model_algorithm VARCHAR(100),
    n_features INTEGER,
    training_date DATE,
    auc_roc DECIMAL(5, 4),
    precision_score DECIMAL(5, 4),
    recall DECIMAL(5, 4),
    f1_score DECIMAL(5, 4),
    is_production BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(model_version, model_type)
);

CREATE INDEX idx_dim_model_version ON dim_model(model_version);
CREATE INDEX idx_dim_model_production ON dim_model(is_production);

-- 기업 차원 (Company Dimension) - SCD Type 2
CREATE TABLE dim_company (
    company_key SERIAL PRIMARY KEY,
    business_id VARCHAR(100),  -- 사업자번호 (해시)
    company_name VARCHAR(500),
    industry_code VARCHAR(20),
    industry_name VARCHAR(200),
    company_size VARCHAR(20),  -- 대기업, 중소기업, 스타트업
    employee_count_range VARCHAR(50),  -- 1-10, 11-50, 51-200, ...
    is_audited BOOLEAN,  -- 외감여부

    -- SCD Type 2 (천천히 변하는 차원)
    valid_from TIMESTAMP NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMP DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dim_company_business_id ON dim_company(business_id);
CREATE INDEX idx_dim_company_current ON dim_company(is_current);
CREATE INDEX idx_dim_company_industry ON dim_company(industry_code);

-- ============================================================================
-- Fact Tables (사실 테이블)
-- ============================================================================

-- 예측 사실 테이블
CREATE TABLE fact_predictions (
    prediction_key BIGSERIAL PRIMARY KEY,

    -- Foreign Keys
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    model_key INTEGER NOT NULL REFERENCES dim_model(model_key),
    company_key INTEGER REFERENCES dim_company(company_key),

    -- 측정값 (Measures)
    default_probability DECIMAL(5, 4) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    confidence DECIMAL(5, 4),

    -- 재무 비율 (집계용)
    current_ratio DECIMAL(10, 4),
    debt_ratio DECIMAL(10, 4),
    equity_ratio DECIMAL(10, 4),
    roa DECIMAL(10, 4),
    roe DECIMAL(10, 4),
    operating_margin DECIMAL(10, 4),
    net_margin DECIMAL(10, 4),

    -- 연체 정보
    has_delinquency BOOLEAN,
    max_delinquency_days INTEGER,

    -- 실제 라벨 (Ground Truth)
    actual_default BOOLEAN,
    actual_default_date DATE,
    label_lag_days INTEGER,  -- 예측과 실제 부도 사이 일수

    -- 메타데이터
    request_id UUID NOT NULL,
    inference_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fact_pred_date ON fact_predictions(date_key);
CREATE INDEX idx_fact_pred_model ON fact_predictions(model_key);
CREATE INDEX idx_fact_pred_company ON fact_predictions(company_key);
CREATE INDEX idx_fact_pred_risk ON fact_predictions(risk_level);
CREATE INDEX idx_fact_pred_actual ON fact_predictions(actual_default);
CREATE INDEX idx_fact_pred_request_id ON fact_predictions(request_id);

-- 모델 성능 사실 테이블
CREATE TABLE fact_model_performance (
    performance_key BIGSERIAL PRIMARY KEY,

    -- Foreign Keys
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    model_key INTEGER NOT NULL REFERENCES dim_model(model_key),

    -- 측정값
    auc_roc DECIMAL(5, 4),
    precision_score DECIMAL(5, 4),
    recall DECIMAL(5, 4),
    f1_score DECIMAL(5, 4),

    -- Drift 메트릭
    psi_score DECIMAL(10, 6),
    ks_statistic DECIMAL(10, 6),
    ks_pvalue DECIMAL(10, 6),
    data_drift_detected BOOLEAN,
    concept_drift_detected BOOLEAN,

    -- 예측 분포
    avg_prediction DECIMAL(5, 4),
    std_prediction DECIMAL(5, 4),
    median_prediction DECIMAL(5, 4),

    -- 평가 기간
    evaluation_period_start TIMESTAMP,
    evaluation_period_end TIMESTAMP,
    sample_size INTEGER,

    notes TEXT,
    logged_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fact_perf_date ON fact_model_performance(date_key);
CREATE INDEX idx_fact_perf_model ON fact_model_performance(model_key);
CREATE INDEX idx_fact_perf_drift ON fact_model_performance(data_drift_detected);

-- ============================================================================
-- 날짜 차원 자동 채우기 함수
-- ============================================================================

CREATE OR REPLACE FUNCTION populate_dim_date(start_date DATE, end_date DATE)
RETURNS VOID AS $$
DECLARE
    iter_date DATE := start_date;
BEGIN
    WHILE iter_date <= end_date LOOP
        INSERT INTO dim_date (
            date_key, date, year, quarter, month, week,
            day_of_month, day_of_week, day_name, is_weekend
        ) VALUES (
            TO_CHAR(iter_date, 'YYYYMMDD')::INTEGER,
            iter_date,
            EXTRACT(YEAR FROM iter_date),
            EXTRACT(QUARTER FROM iter_date),
            EXTRACT(MONTH FROM iter_date),
            EXTRACT(WEEK FROM iter_date),
            EXTRACT(DAY FROM iter_date),
            EXTRACT(DOW FROM iter_date),
            TO_CHAR(iter_date, 'Day'),
            EXTRACT(DOW FROM iter_date) IN (0, 6)
        )
        ON CONFLICT (date) DO NOTHING;

        iter_date := iter_date + INTERVAL '1 day';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 2020-01-01 부터 2030-12-31까지 채우기
SELECT populate_dim_date('2020-01-01'::DATE, '2030-12-31'::DATE);
