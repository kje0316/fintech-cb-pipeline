-- ============================================================================
-- Data Mart (DM) Schema
--
-- 목적: DWH 데이터를 집계하여 분석 및 모니터링 최적화
-- ============================================================================

-- ============================================================================
-- 일별 예측 집계
-- ============================================================================

CREATE TABLE dm_daily_predictions (
    date DATE PRIMARY KEY,
    model_version VARCHAR(50),

    -- 예측 수
    total_predictions INTEGER,
    low_risk_count INTEGER,
    medium_risk_count INTEGER,
    high_risk_count INTEGER,

    -- 예측 분포
    avg_default_probability DECIMAL(5, 4),
    median_default_probability DECIMAL(5, 4),
    std_default_probability DECIMAL(5, 4),
    min_default_probability DECIMAL(5, 4),
    max_default_probability DECIMAL(5, 4),

    -- 실제 부도 (Ground Truth 있을 때)
    labeled_count INTEGER,
    actual_default_count INTEGER,
    actual_default_rate DECIMAL(5, 4),

    -- 성능 메트릭 (라벨이 있는 경우)
    accuracy DECIMAL(5, 4),
    precision_score DECIMAL(5, 4),
    recall DECIMAL(5, 4),
    f1_score DECIMAL(5, 4),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dm_daily_date ON dm_daily_predictions(date);
CREATE INDEX idx_dm_daily_model ON dm_daily_predictions(model_version);

-- ============================================================================
-- 모델 드리프트 분석
-- ============================================================================

CREATE TABLE dm_model_drift (
    drift_id SERIAL PRIMARY KEY,
    analysis_date DATE NOT NULL,
    model_version VARCHAR(50) NOT NULL,

    -- 분석 기간
    baseline_start DATE NOT NULL,
    baseline_end DATE NOT NULL,
    current_start DATE NOT NULL,
    current_end DATE NOT NULL,

    -- Data Drift (PSI, KS-Test)
    psi_score DECIMAL(10, 6),
    psi_status VARCHAR(20),  -- stable, warning, alert
    ks_statistic DECIMAL(10, 6),
    ks_pvalue DECIMAL(10, 6),
    ks_drift_detected BOOLEAN,

    -- Concept Drift (예측 vs 실제)
    predicted_default_rate DECIMAL(5, 4),
    actual_default_rate DECIMAL(5, 4),
    concept_drift_score DECIMAL(10, 6),
    concept_drift_detected BOOLEAN,

    -- 피처별 Drift (JSON)
    feature_drift_scores JSONB,

    -- 액션
    retrain_recommended BOOLEAN DEFAULT FALSE,
    alert_triggered BOOLEAN DEFAULT FALSE,

    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dm_drift_date ON dm_model_drift(analysis_date);
CREATE INDEX idx_dm_drift_model ON dm_model_drift(model_version);
CREATE INDEX idx_dm_drift_detected ON dm_model_drift(ks_drift_detected, concept_drift_detected);

-- ============================================================================
-- 업종별 위험도 분석
-- ============================================================================

CREATE TABLE dm_industry_risk (
    industry_code VARCHAR(20),
    analysis_date DATE,
    model_version VARCHAR(50),

    -- 예측 수
    total_predictions INTEGER,

    -- 위험도 분포
    low_risk_count INTEGER,
    low_risk_pct DECIMAL(5, 2),
    medium_risk_count INTEGER,
    medium_risk_pct DECIMAL(5, 2),
    high_risk_count INTEGER,
    high_risk_pct DECIMAL(5, 2),

    -- 평균 부도 확률
    avg_default_probability DECIMAL(5, 4),
    median_default_probability DECIMAL(5, 4),

    -- 재무 비율 평균
    avg_current_ratio DECIMAL(10, 4),
    avg_debt_ratio DECIMAL(10, 4),
    avg_equity_ratio DECIMAL(10, 4),
    avg_roa DECIMAL(10, 4),
    avg_roe DECIMAL(10, 4),

    -- 실제 부도율 (Ground Truth)
    actual_default_rate DECIMAL(5, 4),

    created_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (industry_code, analysis_date, model_version)
);

CREATE INDEX idx_dm_industry_date ON dm_industry_risk(analysis_date);
CREATE INDEX idx_dm_industry_code ON dm_industry_risk(industry_code);

-- ============================================================================
-- 피처 분포 모니터링
-- ============================================================================

CREATE TABLE dm_feature_distribution (
    feature_name VARCHAR(100),
    analysis_date DATE,
    model_version VARCHAR(50),

    -- 통계량
    mean_value DECIMAL(20, 6),
    median_value DECIMAL(20, 6),
    std_value DECIMAL(20, 6),
    min_value DECIMAL(20, 6),
    max_value DECIMAL(20, 6),

    -- 분위수
    p25 DECIMAL(20, 6),
    p50 DECIMAL(20, 6),
    p75 DECIMAL(20, 6),
    p90 DECIMAL(20, 6),
    p95 DECIMAL(20, 6),
    p99 DECIMAL(20, 6),

    -- 결측/이상치
    missing_count INTEGER,
    missing_rate DECIMAL(5, 4),
    outlier_count INTEGER,
    outlier_rate DECIMAL(5, 4),

    -- 샘플 수
    sample_size INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (feature_name, analysis_date, model_version)
);

CREATE INDEX idx_dm_feature_date ON dm_feature_distribution(analysis_date);
CREATE INDEX idx_dm_feature_name ON dm_feature_distribution(feature_name);

-- ============================================================================
-- Materialized Views (물리적 뷰 - 성능 최적화)
-- ============================================================================

-- 최근 7일 예측 트렌드
CREATE MATERIALIZED VIEW mv_recent_predictions AS
SELECT
    DATE(fp.created_at) as prediction_date,
    dm.model_version,
    COUNT(*) as total_predictions,
    AVG(fp.default_probability) as avg_default_prob,
    COUNT(CASE WHEN fp.risk_level = 'Low' THEN 1 END) as low_risk_count,
    COUNT(CASE WHEN fp.risk_level = 'Medium' THEN 1 END) as medium_risk_count,
    COUNT(CASE WHEN fp.risk_level = 'High' THEN 1 END) as high_risk_count,
    COUNT(CASE WHEN fp.actual_default IS NOT NULL THEN 1 END) as labeled_count,
    COUNT(CASE WHEN fp.actual_default = TRUE THEN 1 END) as actual_default_count
FROM fact_predictions fp
JOIN dim_model dm ON fp.model_key = dm.model_key
WHERE fp.created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(fp.created_at), dm.model_version;

CREATE INDEX idx_mv_recent_date ON mv_recent_predictions(prediction_date);

-- 일별로 갱신 (Airflow에서 실행)
-- REFRESH MATERIALIZED VIEW mv_recent_predictions;

-- ============================================================================
-- DM 테이블 채우기 함수 (Airflow에서 호출)
-- ============================================================================

-- 일별 예측 집계 채우기
CREATE OR REPLACE FUNCTION refresh_dm_daily_predictions(target_date DATE)
RETURNS VOID AS $$
BEGIN
    INSERT INTO dm_daily_predictions (
        date, model_version,
        total_predictions, low_risk_count, medium_risk_count, high_risk_count,
        avg_default_probability, median_default_probability,
        std_default_probability, min_default_probability, max_default_probability,
        labeled_count, actual_default_count, actual_default_rate,
        updated_at
    )
    SELECT
        target_date,
        dm.model_version,
        COUNT(*) as total_predictions,
        COUNT(CASE WHEN fp.risk_level = 'Low' THEN 1 END) as low_risk_count,
        COUNT(CASE WHEN fp.risk_level = 'Medium' THEN 1 END) as medium_risk_count,
        COUNT(CASE WHEN fp.risk_level = 'High' THEN 1 END) as high_risk_count,
        AVG(fp.default_probability) as avg_default_probability,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fp.default_probability) as median_default_probability,
        STDDEV(fp.default_probability) as std_default_probability,
        MIN(fp.default_probability) as min_default_probability,
        MAX(fp.default_probability) as max_default_probability,
        COUNT(CASE WHEN fp.actual_default IS NOT NULL THEN 1 END) as labeled_count,
        COUNT(CASE WHEN fp.actual_default = TRUE THEN 1 END) as actual_default_count,
        CASE
            WHEN COUNT(CASE WHEN fp.actual_default IS NOT NULL THEN 1 END) > 0
            THEN COUNT(CASE WHEN fp.actual_default = TRUE THEN 1 END)::DECIMAL /
                 COUNT(CASE WHEN fp.actual_default IS NOT NULL THEN 1 END)
            ELSE NULL
        END as actual_default_rate,
        NOW()
    FROM fact_predictions fp
    JOIN dim_model dm ON fp.model_key = dm.model_key
    JOIN dim_date dd ON fp.date_key = dd.date_key
    WHERE dd.date = target_date
    GROUP BY dm.model_version
    ON CONFLICT (date) DO UPDATE SET
        total_predictions = EXCLUDED.total_predictions,
        low_risk_count = EXCLUDED.low_risk_count,
        medium_risk_count = EXCLUDED.medium_risk_count,
        high_risk_count = EXCLUDED.high_risk_count,
        avg_default_probability = EXCLUDED.avg_default_probability,
        median_default_probability = EXCLUDED.median_default_probability,
        std_default_probability = EXCLUDED.std_default_probability,
        min_default_probability = EXCLUDED.min_default_probability,
        max_default_probability = EXCLUDED.max_default_probability,
        labeled_count = EXCLUDED.labeled_count,
        actual_default_count = EXCLUDED.actual_default_count,
        actual_default_rate = EXCLUDED.actual_default_rate,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;
