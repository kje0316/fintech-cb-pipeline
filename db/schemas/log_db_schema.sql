-- ============================================================================
-- 로그 DB 스키마 (Raw Layer)
--
-- 목적: 모든 예측 요청, 업로드, 모델 성능을 원시 형태로 저장
-- 데이터베이스: fintech_cb_pipeline
-- 스키마: logs
-- ============================================================================

-- logs 스키마 생성
CREATE SCHEMA IF NOT EXISTS logs;

-- ============================================================================
-- 예측 로그 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs.prediction_logs (
    -- 기본 정보
    id BIGSERIAL PRIMARY KEY,
    request_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 사용자 정보
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    ip_address INET,

    -- 입력 데이터 (37개 필수 컬럼) - JSONB로 저장
    input_data JSONB NOT NULL,

    -- 파생 피처 (70개) - JSONB로 저장
    derived_features JSONB,

    -- 예측 결과
    prediction_result JSONB NOT NULL,
    default_probability DECIMAL(5, 4),  -- 부도 확률
    risk_level VARCHAR(20),              -- Low/Medium/High

    -- 모델 정보
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,

    -- 성능 추적
    inference_time_ms INTEGER,

    -- 실제 라벨 (나중에 업데이트)
    actual_default BOOLEAN,
    actual_default_date DATE,
    label_updated_at TIMESTAMP,

    -- 메타데이터
    validation_errors JSONB,
    notes TEXT
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_prediction_logs_created_at ON logs.prediction_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_user_id ON logs.prediction_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_model_version ON logs.prediction_logs(model_version);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_risk_level ON logs.prediction_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_input_data ON logs.prediction_logs USING GIN (input_data);

-- 파티셔닝 (월별) - 대량 데이터 처리 최적화
-- CREATE TABLE prediction_logs_2025_01 PARTITION OF prediction_logs
-- FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

COMMENT ON TABLE logs.prediction_logs IS '예측 요청 및 결과 로그';
COMMENT ON COLUMN logs.prediction_logs.input_data IS '37개 입력 컬럼 (JSONB)';
COMMENT ON COLUMN logs.prediction_logs.derived_features IS '70개 파생 피처 (JSONB)';
COMMENT ON COLUMN logs.prediction_logs.actual_default IS 'Ground Truth (나중에 업데이트)';

-- ============================================================================
-- 업로드 로그 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs.upload_logs (
    id BIGSERIAL PRIMARY KEY,
    upload_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 사용자 정보
    user_id VARCHAR(100),
    ip_address INET,

    -- 파일 정보
    file_name VARCHAR(500),
    file_size INTEGER,
    file_hash VARCHAR(64),  -- MD5/SHA256

    -- 처리 상태
    status VARCHAR(20) NOT NULL,  -- success, failed, pending
    error_message TEXT,
    validation_errors JSONB,

    -- 처리 결과
    rows_processed INTEGER,
    rows_valid INTEGER,
    rows_invalid INTEGER,

    -- 연결된 예측 ID들
    prediction_ids UUID[],

    processing_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_upload_logs_created_at ON logs.upload_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_upload_logs_status ON logs.upload_logs(status);
CREATE INDEX IF NOT EXISTS idx_upload_logs_user_id ON logs.upload_logs(user_id);

COMMENT ON TABLE logs.upload_logs IS '엑셀 파일 업로드 로그';
COMMENT ON COLUMN logs.upload_logs.file_hash IS '파일 중복 체크용 해시';
COMMENT ON COLUMN logs.upload_logs.prediction_ids IS '생성된 예측 request_id 배열';

-- ============================================================================
-- 모델 성능 로그 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs.model_performance_logs (
    id BIGSERIAL PRIMARY KEY,
    logged_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 모델 정보
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50),

    -- 성능 메트릭
    auc_roc DECIMAL(5, 4),
    precision_score DECIMAL(5, 4),
    recall DECIMAL(5, 4),
    f1_score DECIMAL(5, 4),

    -- Drift 메트릭
    psi_score DECIMAL(10, 6),
    ks_statistic DECIMAL(10, 6),
    ks_pvalue DECIMAL(10, 6),

    -- 예측 분포
    avg_prediction DECIMAL(5, 4),
    std_prediction DECIMAL(5, 4),

    -- 평가 데이터
    evaluation_period_start TIMESTAMP,
    evaluation_period_end TIMESTAMP,
    sample_size INTEGER,

    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_model_perf_logged_at ON logs.model_performance_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_model_perf_version ON logs.model_performance_logs(model_version);

COMMENT ON TABLE logs.model_performance_logs IS '모델 성능 및 Drift 추적 로그';
COMMENT ON COLUMN logs.model_performance_logs.psi_score IS 'Population Stability Index';
COMMENT ON COLUMN logs.model_performance_logs.ks_statistic IS 'Kolmogorov-Smirnov 통계량';

-- ============================================================================
-- 샘플 데이터 조회 뷰
-- ============================================================================

CREATE OR REPLACE VIEW v_recent_predictions AS
SELECT
    pl.request_id,
    pl.created_at,
    pl.model_version,
    pl.model_type,
    pl.default_probability,
    pl.risk_level,
    pl.inference_time_ms,
    pl.input_data->>'fn1_13' as total_assets,
    pl.input_data->>'fn2_1' as revenue,
    pl.actual_default
FROM logs.prediction_logs pl
WHERE pl.created_at >= NOW() - INTERVAL '7 days'
ORDER BY pl.created_at DESC;

COMMENT ON VIEW v_recent_predictions IS '최근 7일 예측 로그 요약';

-- ============================================================================
-- 통계 조회 함수
-- ============================================================================

CREATE OR REPLACE FUNCTION get_daily_prediction_stats(target_date DATE)
RETURNS TABLE (
    total_predictions BIGINT,
    avg_default_prob DECIMAL(5, 4),
    low_risk_count BIGINT,
    medium_risk_count BIGINT,
    high_risk_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_predictions,
        AVG(default_probability)::DECIMAL(5, 4) as avg_default_prob,
        COUNT(CASE WHEN risk_level = 'Low' THEN 1 END) as low_risk_count,
        COUNT(CASE WHEN risk_level = 'Medium' THEN 1 END) as medium_risk_count,
        COUNT(CASE WHEN risk_level = 'High' THEN 1 END) as high_risk_count
    FROM logs.prediction_logs
    WHERE DATE(created_at) = target_date;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_daily_prediction_stats IS '일별 예측 통계 조회';

-- 사용 예시:
-- SELECT * FROM get_daily_prediction_stats('2025-01-24');

-- ============================================================================
-- API 로그 테이블
-- ============================================================================

CREATE TABLE IF NOT EXISTS logs.api_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 요청 정보
    method VARCHAR(10) NOT NULL,
    endpoint VARCHAR(500) NOT NULL,
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    ip_address INET,

    -- 응답 정보
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL,

    -- 에러 정보
    error_message TEXT,
    error_traceback TEXT,

    -- 메타데이터
    user_agent TEXT,
    request_body_size INTEGER,
    response_body_size INTEGER
);

CREATE INDEX IF NOT EXISTS idx_api_logs_timestamp ON logs.api_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_logs_endpoint ON logs.api_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_logs_status_code ON logs.api_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_api_logs_user_id ON logs.api_logs(user_id);

COMMENT ON TABLE logs.api_logs IS 'API 요청/응답 로그 (미들웨어 자동 생성)';
COMMENT ON COLUMN logs.api_logs.response_time_ms IS 'API 응답 시간 (밀리초)';
