-- ========================================
-- Data Mart Schema Definitions
-- ========================================
-- 대시보드 메인 화면을 위한 데이터 마트 DDL
--
-- 마트 목록:
-- 1. mart_market_kpi_monthly - 월별 시장 KPI 지표
-- 2. mart_industry_default_trend - 업종별 월별 부도 추세
-- 3. mart_credit_grade_distribution_monthly - 월별 신용등급 분포
-- 4. mart_industry_risk_ranking - 업종별 리스크 랭킹
-- 5. dm_industry_financial_ratios_stats - 업종별 재무비율 통계 (이미 존재)
--
-- 실행 방법:
--   psql -h localhost -U [username] -d fintech_cb_pipeline -f etl/dwh_to_mart/schema.sql
-- ========================================

-- Marts 스키마 생성 (이미 존재할 수 있음)
CREATE SCHEMA IF NOT EXISTS marts;

-- ========================================
-- 1. mart_market_kpi_monthly
-- ========================================
-- 월별 전체 시장 KPI 지표
-- 대시보드 상단 KPI 카드에 표시할 메트릭

DROP TABLE IF EXISTS marts.mart_market_kpi_monthly CASCADE;

CREATE TABLE marts.mart_market_kpi_monthly (
    bs_dt DATE PRIMARY KEY,

    -- KPI 지표
    total_companies INTEGER NOT NULL,                 -- 전체 기업 수
    avg_credit_grade NUMERIC(4, 2),                   -- 평균 신용등급
    default_rate NUMERIC(5, 2),                       -- 부도율 (%)
    high_risk_ratio NUMERIC(5, 2),                    -- 고위험 기업 비율 (%)
    avg_z_score NUMERIC(10, 4),                       -- 평균 Altman Z-Score

    -- 전월 대비 변화 (MoM)
    total_companies_prev INTEGER,                     -- 전월 기업 수
    avg_credit_grade_prev NUMERIC(4, 2),              -- 전월 평균 신용등급
    default_rate_prev NUMERIC(5, 2),                  -- 전월 부도율
    high_risk_ratio_prev NUMERIC(5, 2),               -- 전월 고위험 비율
    avg_z_score_prev NUMERIC(10, 4),                  -- 전월 평균 Z-Score

    -- 변화량 및 변화율
    total_companies_change INTEGER,                   -- 기업 수 변화
    avg_credit_grade_change NUMERIC(4, 2),            -- 신용등급 변화
    default_rate_change NUMERIC(5, 2),                -- 부도율 변화 (pp)
    high_risk_ratio_change NUMERIC(5, 2),             -- 고위험 비율 변화 (pp)
    avg_z_score_change NUMERIC(10, 4),                -- Z-Score 변화

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mkt_kpi_bs_dt ON marts.mart_market_kpi_monthly(bs_dt);

COMMENT ON TABLE marts.mart_market_kpi_monthly IS '월별 전체 시장 KPI 지표 (대시보드 상단 카드용)';
COMMENT ON COLUMN marts.mart_market_kpi_monthly.high_risk_ratio IS '신용등급 8-10 기업 비율';
COMMENT ON COLUMN marts.mart_market_kpi_monthly.avg_z_score IS 'Altman Z-Score Modified 평균 (< 1.23 위험, 1.23-2.9 회색지대, > 2.9 안전)';


-- ========================================
-- 2. mart_industry_default_trend
-- ========================================
-- 업종별 월별 부도 추세
-- 선택한 5개 업종의 월별 부도율 시계열 차트용

DROP TABLE IF EXISTS marts.mart_industry_default_trend CASCADE;

CREATE TABLE marts.mart_industry_default_trend (
    industry_code VARCHAR(10) NOT NULL,
    industry_name VARCHAR(255) NOT NULL,
    bs_dt DATE NOT NULL,

    -- 부도 관련
    total_companies INTEGER NOT NULL,                 -- 전체 기업 수
    default_companies INTEGER NOT NULL,               -- 부도 기업 수
    default_rate NUMERIC(5, 2) NOT NULL,              -- 부도율 (%)

    -- 신용등급 분포
    grade_1_3_count INTEGER,                          -- 우수 등급 (1-3) 기업 수
    grade_4_5_count INTEGER,                          -- 양호 등급 (4-5) 기업 수
    grade_6_7_count INTEGER,                          -- 보통 등급 (6-7) 기업 수
    grade_8_10_count INTEGER,                         -- 위험 등급 (8-10) 기업 수
    grade_0_count INTEGER,                            -- 등급 0 (특수 케이스)

    -- 주요 재무지표 중앙값 (차트 hover시 표시)
    median_debt_ratio NUMERIC(10, 2),                 -- 부채비율 중앙값
    median_current_ratio NUMERIC(10, 2),              -- 유동비율 중앙값
    median_operating_margin NUMERIC(10, 2),           -- 영업이익률 중앙값
    median_roe NUMERIC(10, 2),                        -- ROE 중앙값
    median_z_score NUMERIC(10, 4),                    -- Z-Score 중앙값

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (industry_code, bs_dt)
);

CREATE INDEX idx_ind_trend_industry ON marts.mart_industry_default_trend(industry_code);
CREATE INDEX idx_ind_trend_bs_dt ON marts.mart_industry_default_trend(bs_dt);
CREATE INDEX idx_ind_trend_default_rate ON marts.mart_industry_default_trend(default_rate DESC);

COMMENT ON TABLE marts.mart_industry_default_trend IS '업종별 월별 부도 추세 (시계열 차트용, 73개 업종 × 12개월)';
COMMENT ON COLUMN marts.mart_industry_default_trend.default_rate IS '월별 부도율 (%) = (부도기업수 / 전체기업수) × 100';


-- ========================================
-- 3. mart_credit_grade_distribution_monthly
-- ========================================
-- 월별 신용등급 분포
-- 신용등급 분포 변화 추이 차트용

DROP TABLE IF EXISTS marts.mart_credit_grade_distribution_monthly CASCADE;

CREATE TABLE marts.mart_credit_grade_distribution_monthly (
    bs_dt DATE NOT NULL,
    credit_grade INTEGER NOT NULL,                    -- 신용등급 (0-10)

    -- 집계 데이터
    company_count INTEGER NOT NULL,                   -- 해당 등급 기업 수
    percentage NUMERIC(5, 2) NOT NULL,                -- 비율 (%)

    -- 해당 등급 기업들의 평균 재무지표
    avg_total_assets NUMERIC(15, 2),                  -- 평균 총자산
    avg_debt_ratio NUMERIC(10, 2),                    -- 평균 부채비율
    avg_current_ratio NUMERIC(10, 2),                 -- 평균 유동비율
    avg_operating_margin NUMERIC(10, 2),              -- 평균 영업이익률
    avg_z_score NUMERIC(10, 4),                       -- 평균 Z-Score

    -- 부도 정보
    default_count INTEGER,                            -- 해당 등급 내 부도 기업 수
    default_rate_in_grade NUMERIC(5, 2),              -- 등급 내 부도율 (%)

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (bs_dt, credit_grade)
);

CREATE INDEX idx_grade_dist_bs_dt ON marts.mart_credit_grade_distribution_monthly(bs_dt);
CREATE INDEX idx_grade_dist_grade ON marts.mart_credit_grade_distribution_monthly(credit_grade);

COMMENT ON TABLE marts.mart_credit_grade_distribution_monthly IS '월별 신용등급 분포 (0-10 등급별 기업 수 및 재무 프로파일)';
COMMENT ON COLUMN marts.mart_credit_grade_distribution_monthly.default_rate_in_grade IS '등급 내 부도율: 특정 등급 내에서 부도 기업 비율';


-- ========================================
-- 4. mart_industry_risk_ranking
-- ========================================
-- 업종별 리스크 랭킹
-- 위험 업종 TOP 5, 안전 업종 TOP 5 표시용

DROP TABLE IF EXISTS marts.mart_industry_risk_ranking CASCADE;

CREATE TABLE marts.mart_industry_risk_ranking (
    ranking_id SERIAL PRIMARY KEY,
    industry_code VARCHAR(10) NOT NULL UNIQUE,
    industry_name VARCHAR(255) NOT NULL,

    -- 리스크 지표
    total_companies INTEGER NOT NULL,                 -- 전체 기업 수
    default_companies INTEGER NOT NULL,               -- 부도 기업 수 (12개월 누적)
    default_rate NUMERIC(5, 2) NOT NULL,              -- 평균 부도율 (%)

    -- 신용 프로파일
    avg_credit_grade NUMERIC(4, 2),                   -- 평균 신용등급
    high_risk_count INTEGER,                          -- 고위험(8-10) 기업 수
    high_risk_ratio NUMERIC(5, 2),                    -- 고위험 기업 비율 (%)

    -- 재무 건전성 지표
    avg_z_score NUMERIC(10, 4),                       -- 평균 Altman Z-Score
    median_debt_ratio NUMERIC(10, 2),                 -- 중앙 부채비율
    median_current_ratio NUMERIC(10, 2),              -- 중앙 유동비율
    median_operating_margin NUMERIC(10, 2),           -- 중앙 영업이익률

    -- 종합 리스크 점수 (가중 평균)
    risk_score NUMERIC(10, 4),                        -- 리스크 점수 (높을수록 위험)
    risk_rank INTEGER,                                -- 리스크 순위 (1=가장 위험)

    -- 메타데이터
    data_period_start DATE,                           -- 집계 기간 시작
    data_period_end DATE,                             -- 집계 기간 종료
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_risk_rank_industry ON marts.mart_industry_risk_ranking(industry_code);
CREATE INDEX idx_risk_rank_score ON marts.mart_industry_risk_ranking(risk_score DESC);
CREATE INDEX idx_risk_rank_default_rate ON marts.mart_industry_risk_ranking(default_rate DESC);

COMMENT ON TABLE marts.mart_industry_risk_ranking IS '업종별 리스크 랭킹 (전체 기간 집계, 위험/안전 TOP 5용)';
COMMENT ON COLUMN marts.mart_industry_risk_ranking.risk_score IS '종합 리스크 점수 = 0.4×부도율 + 0.3×평균신용등급 + 0.2×고위험비율 - 0.1×Z-Score (예시 가중치)';


-- ========================================
-- 5. dm_industry_financial_ratios_stats (이미 존재)
-- ========================================
-- 업종별 재무비율 통계
-- 기존 스크립트로 생성됨: build_dm_industry_financial_stats.py
--
-- 구조:
--   - industry_code, metric_code (PK)
--   - count, avg, median, std, min, max
--   - p10, p25, p50, p75, p90
--
-- 18개 메트릭 × 74개 업종 = 1,323개 레코드
-- 이미 존재하므로 여기서는 생성하지 않음


-- ========================================
-- 권한 설정 (필요시)
-- ========================================
-- GRANT SELECT ON ALL TABLES IN SCHEMA marts TO dashboard_user;


-- ========================================
-- 테이블 생성 확인 쿼리
-- ========================================
-- 생성된 마트 목록 확인:
-- SELECT table_name
-- FROM information_schema.tables
-- WHERE table_schema = 'marts'
-- ORDER BY table_name;

-- 각 마트 행 수 확인:
-- SELECT
--     'mart_market_kpi_monthly' as table_name,
--     COUNT(*) as row_count
-- FROM marts.mart_market_kpi_monthly
-- UNION ALL
-- SELECT
--     'mart_industry_default_trend',
--     COUNT(*)
-- FROM marts.mart_industry_default_trend
-- UNION ALL
-- SELECT
--     'mart_credit_grade_distribution_monthly',
--     COUNT(*)
-- FROM marts.mart_credit_grade_distribution_monthly
-- UNION ALL
-- SELECT
--     'mart_industry_risk_ranking',
--     COUNT(*)
-- FROM marts.mart_industry_risk_ranking
-- UNION ALL
-- SELECT
--     'dm_industry_financial_ratios_stats',
--     COUNT(*)
-- FROM marts.dm_industry_financial_ratios_stats;
