-- ========================================
-- ML Feature Store Schema Definitions
-- ========================================
-- ML 모델 학습/추론용 피처 스토어 마트
--
-- 마트 목록:
-- 1. mart_feature_store_ml - 70개 ML 피처 (부도예측 + 클러스터링 공통)
--
-- 실행 방법:
--   psql -h localhost -U [username] -d fintech_cb_pipeline -f etl/dwh_to_mart/feature_store_schema.sql
-- ========================================

-- Marts 스키마 (이미 존재할 수 있음)
CREATE SCHEMA IF NOT EXISTS marts;

-- ========================================
-- 1. mart_feature_store_ml
-- ========================================
-- ML 모델 학습/추론용 70개 피처 스토어
-- 부도예측 모델과 클러스터링 모델이 공통으로 사용

-- 주의: DROP TABLE은 데이터 손실을 유발합니다. 스키마 재생성 시에만 사용하세요.
-- DROP TABLE IF EXISTS marts.mart_feature_store_ml CASCADE;

CREATE TABLE IF NOT EXISTS marts.mart_feature_store_ml (
    -- Primary Key
    feature_id SERIAL,
    base_ym INTEGER NOT NULL,                    -- 기준년월 (YYYYMM)
    company_id VARCHAR(50) NOT NULL,             -- 기업 ID

    -- ========================================
    -- 재무상태표 기본 (10개)
    -- ========================================
    fn1_13 NUMERIC(20, 2),                       -- 자산총계
    fn1_1 NUMERIC(20, 2),                        -- 유동자산
    fn1_4 NUMERIC(20, 2),                        -- 재고자산
    fn1_11 NUMERIC(20, 2),                       -- 비유동자산
    fn1_14 NUMERIC(20, 2),                       -- 유동부채
    fn1_15 NUMERIC(20, 2),                       -- 단기차입금
    fn1_16 NUMERIC(20, 2),                       -- 비유동부채
    fn1_19 NUMERIC(20, 2),                       -- 부채총계
    fn1_20 NUMERIC(20, 2),                       -- 자본금
    fn1_24 NUMERIC(20, 2),                       -- 자본총계

    -- ========================================
    -- 손익계산서 기본 (4개)
    -- ========================================
    fn2_1 NUMERIC(20, 2),                        -- 매출액
    fn2_2_1 NUMERIC(20, 2),                      -- 매출원가
    fn2_5 NUMERIC(20, 2),                        -- 영업이익
    fn2_10 NUMERIC(20, 2),                       -- 당기순이익

    -- ========================================
    -- 현금흐름/기타 기본 (10개)
    -- ========================================
    fn3_1 NUMERIC(20, 2),                        -- 영업활동현금흐름
    fn3_2 NUMERIC(20, 2),                        -- 투자활동현금흐름
    fn3_3 NUMERIC(20, 2),                        -- 재무활동현금흐름
    fn3_4 NUMERIC(20, 2),                        -- 현금및현금성자산증가
    fn3_6 NUMERIC(20, 2),                        -- 기초현금
    fn3_7 NUMERIC(20, 2),                        -- 기말현금
    fn3_8 NUMERIC(20, 2),                        -- EBITDA
    fn3_10 NUMERIC(20, 2),                       -- 잉여현금흐름
    fn3_11 NUMERIC(20, 2),                       -- 순운전자본증감
    fn3_11_1 NUMERIC(20, 4),                     -- 이자보상배율

    -- ========================================
    -- 연체정보 (7개)
    -- ========================================
    da0d00021 NUMERIC(10, 0),                    -- 연체건수
    da0d00026 NUMERIC(20, 2),                    -- 연체금액
    da0d00029 NUMERIC(10, 0),                    -- 최장연체일수
    da0d00033_1 NUMERIC(20, 2),                  -- 세금체납금액
    da0d00035_1 NUMERIC(20, 2),                  -- 연체발생금액
    db0d00006 NUMERIC(10, 0),                    -- 신용사건건수
    d2b000012 NUMERIC(10, 0),                    -- 부도이력

    -- ========================================
    -- 안정성 비율 (7개)
    -- ========================================
    r006 NUMERIC(20, 4),                         -- 부채비율
    r007 NUMERIC(20, 4),                         -- 유동부채비율
    r008 NUMERIC(20, 4),                         -- 유동비율
    r009 NUMERIC(20, 4),                         -- 당좌비율
    r012 NUMERIC(20, 4),                         -- 차입금의존도
    n001 NUMERIC(20, 4),                         -- 매출액대비영업이익
    n002 NUMERIC(20, 4),                         -- 매출액대비순이익

    -- ========================================
    -- 수익성 비율 (7개)
    -- ========================================
    r013 NUMERIC(20, 4),                         -- 매출총이익률
    r015 NUMERIC(20, 4),                         -- 영업이익률
    r016 NUMERIC(20, 4),                         -- 순이익률
    r018 NUMERIC(20, 4),                         -- ROE
    r023 NUMERIC(20, 4),                         -- ROA
    n004 NUMERIC(20, 4),                         -- 비유동비율
    n005 NUMERIC(20, 4),                         -- 비유동장기적합률

    -- ========================================
    -- 활동성 비율 (6개)
    -- ========================================
    r019 NUMERIC(20, 4),                         -- 총자산회전율
    r020 NUMERIC(20, 4),                         -- 매출채권회전율
    r021 NUMERIC(20, 4),                         -- 재고자산회전율
    r022 NUMERIC(20, 4),                         -- 매입채무회전율
    n003 NUMERIC(20, 4),                         -- 자기자본비율
    n012 NUMERIC(20, 4),                         -- 자산효율성

    -- ========================================
    -- 성장성 비율 (8개)
    -- ========================================
    r001 NUMERIC(20, 4),                         -- 총자산증가율
    r002 NUMERIC(20, 4),                         -- 매출증가율
    r003 NUMERIC(20, 4),                         -- 순이익증가율
    r004 NUMERIC(20, 4),                         -- 자기자본증가율
    r024 NUMERIC(20, 4),                         -- 현금흐름부채비율
    r025 NUMERIC(20, 4),                         -- 이자보상배율
    n007 NUMERIC(20, 4),                         -- 현금흐름이자보상배율

    -- ========================================
    -- 현금흐름/생산성 비율 (5개)
    -- ========================================
    n006 NUMERIC(20, 4),                         -- EBITDA마진율
    n008 NUMERIC(20, 4),                         -- 영업현금흐름비율
    n009 NUMERIC(20, 4),                         -- 투자현금흐름비율
    n010 NUMERIC(20, 4),                         -- 순운전자본비율
    n011 NUMERIC(20, 4),                         -- 현금전환주기

    -- ========================================
    -- 타겟 레이블 (학습용)
    -- ========================================
    default_yn INTEGER,                          -- 부도여부 (0/1)
    cluster_id INTEGER,                          -- 클러스터 ID (학습 후 매핑)

    -- ========================================
    -- 메타데이터
    -- ========================================
    sic_cd_3 VARCHAR(10),                        -- 업종코드 (3자리)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (base_ym, company_id)
);

-- 인덱스 생성
CREATE INDEX idx_fs_ml_base_ym ON marts.mart_feature_store_ml(base_ym);
CREATE INDEX idx_fs_ml_company ON marts.mart_feature_store_ml(company_id);
CREATE INDEX idx_fs_ml_default ON marts.mart_feature_store_ml(default_yn);
CREATE INDEX idx_fs_ml_cluster ON marts.mart_feature_store_ml(cluster_id);
CREATE INDEX idx_fs_ml_sic ON marts.mart_feature_store_ml(sic_cd_3);

-- 코멘트
COMMENT ON TABLE marts.mart_feature_store_ml IS 'ML 모델 학습/추론용 70개 피처 스토어 (부도예측 + 클러스터링 공통)';
COMMENT ON COLUMN marts.mart_feature_store_ml.base_ym IS '기준년월 (YYYYMM 형식)';
COMMENT ON COLUMN marts.mart_feature_store_ml.default_yn IS '부도여부: 향후 1년 내 부도 발생 여부 (1=부도, 0=정상)';
COMMENT ON COLUMN marts.mart_feature_store_ml.cluster_id IS '클러스터 ID: 클러스터링 모델로 예측된 그룹 (-1=노이즈)';


-- ========================================
-- 2. mart_feature_store_metadata
-- ========================================
-- Feature Store 메타데이터 (버전 관리용)

-- DROP TABLE IF EXISTS marts.mart_feature_store_metadata CASCADE;

CREATE TABLE IF NOT EXISTS marts.mart_feature_store_metadata (
    metadata_id SERIAL PRIMARY KEY,
    base_ym INTEGER NOT NULL UNIQUE,             -- 기준년월

    -- 데이터 정보
    total_companies INTEGER NOT NULL,            -- 전체 기업 수
    default_count INTEGER,                       -- 부도 기업 수
    default_rate NUMERIC(5, 4),                  -- 부도율

    -- 피처 통계
    feature_count INTEGER DEFAULT 70,            -- 피처 수
    null_ratio NUMERIC(5, 4),                    -- 전체 NULL 비율

    -- 모델 사용 이력
    used_for_training BOOLEAN DEFAULT FALSE,     -- 학습에 사용됨
    used_for_inference BOOLEAN DEFAULT FALSE,    -- 추론에 사용됨
    model_version VARCHAR(20),                   -- 사용된 모델 버전

    -- 메타데이터
    source_table VARCHAR(100),                   -- 원본 테이블
    etl_version VARCHAR(20),                     -- ETL 버전
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fs_meta_base_ym ON marts.mart_feature_store_metadata(base_ym);

COMMENT ON TABLE marts.mart_feature_store_metadata IS 'Feature Store 메타데이터 (버전 관리, 데이터 품질 추적용)';


-- ========================================
-- 테이블 생성 확인 쿼리
-- ========================================
-- SELECT table_name, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
-- FROM pg_tables
-- WHERE schemaname = 'marts' AND tablename LIKE 'mart_feature%';
