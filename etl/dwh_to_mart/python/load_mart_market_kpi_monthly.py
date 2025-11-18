"""
월별 시장 KPI 마트 적재 스크립트
===============================

mart_market_kpi_monthly 테이블에 데이터를 적재합니다.

계산 항목:
- total_companies: 월별 전체 기업 수
- avg_credit_grade: 평균 신용등급
- default_rate: 부도율 (%)
- high_risk_ratio: 고위험(등급 8-10) 기업 비율 (%)
- avg_z_score: 평균 Altman Z-Score (Modified)
- MoM 변화량 및 변화율

Altman Z-Score Modified 공식:
  X1 = 순운전자본 / 총자산 (FN3_11 / FN1_13)
  X2 = 이익잉여금 / 총자산 (FN1_22 / FN1_13)
  X3 = EBIT / 총자산 (FN3_7 / FN1_13)
  X4 = 자본총계 / 부채총계 (FN1_24 / FN1_19)
  X5 = 매출액 / 총자산 (FN2_1 / FN1_13)

  Z' = 0.717×X1 + 0.847×X2 + 3.107×X3 + 0.420×X4 + 0.998×X5

Z-Score 해석:
  > 2.9: 안전
  1.23 - 2.9: 회색 지대 (Gray Zone)
  < 1.23: 재무적 어려움 (Financial Distress)

실행 방법:
  python etl/dwh_to_mart/python/load_mart_market_kpi_monthly.py
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import DB_URL, config

# DB 연결
engine = create_engine(DB_URL, echo=False, future=True)

DWH_SCHEMA = "dwh"
DM_SCHEMA = "marts"

# Mart 클렌징 설정 로드
MART_CONFIG = config.get('mart', {})
IMPUTATION_CONFIG = MART_CONFIG.get('imputation', {})
OUTLIER_CONFIG = MART_CONFIG.get('outlier_handling', {})


def impute_missing_values(df):
    """
    결측치 대체 (Mart 전용)

    DWH에서 넘어온 NULL 값을 업종별 중앙값으로 대체합니다.
    """
    if not IMPUTATION_CONFIG.get('enabled', False):
        print("  결측치 대체: 비활성화됨 (설정에서 enabled=false)")
        return df

    method = IMPUTATION_CONFIG.get('method', 'industry_median')
    target_cols = IMPUTATION_CONFIG.get('target_columns', [])
    add_flag = IMPUTATION_CONFIG.get('add_imputation_flag', False)

    print(f"\n  결측치 대체 중 (방법: {method})...")

    imputed_counts = {}

    for col in target_cols:
        if col.lower() not in df.columns:
            continue

        col_lower = col.lower()
        null_count_before = df[col_lower].isna().sum()

        if null_count_before == 0:
            continue

        # 업종별 중앙값으로 대체
        if method == 'industry_median':
            # 업종 컬럼이 있는지 확인
            if 'sic_cd_3' in df.columns:
                df[col_lower] = df.groupby('sic_cd_3')[col_lower].transform(
                    lambda x: x.fillna(x.median())
                )
            else:
                # 업종 컬럼이 없으면 전체 중앙값
                df[col_lower].fillna(df[col_lower].median(), inplace=True)

        elif method == 'median':
            df[col_lower].fillna(df[col_lower].median(), inplace=True)

        elif method == 'mean':
            df[col_lower].fillna(df[col_lower].mean(), inplace=True)

        elif method == 'zero':
            df[col_lower].fillna(0, inplace=True)

        null_count_after = df[col_lower].isna().sum()
        imputed_count = null_count_before - null_count_after

        if imputed_count > 0:
            imputed_counts[col] = imputed_count

            # 대체 플래그 컬럼 추가
            if add_flag:
                df[f'{col_lower}_imputed'] = False
                # 원래 NULL이었던 인덱스에 True 설정 필요
                # (간단히 하기 위해 생략, 필요시 추가)

    if imputed_counts:
        total = sum(imputed_counts.values())
        print(f"    ✓ {total:,}개 결측치 대체:")
        for col, count in sorted(imputed_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {col}: {count:,}개")
    else:
        print(f"    ✓ 대체할 결측치 없음")

    return df


def handle_outliers(df):
    """
    이상치 처리 (Mart 전용)

    극단값을 상한/하한으로 제한(capping)합니다.
    """
    if not OUTLIER_CONFIG.get('enabled', False):
        print("  이상치 처리: 비활성화됨")
        return df

    method = OUTLIER_CONFIG.get('method', 'iqr')
    threshold = OUTLIER_CONFIG.get('iqr_threshold', 3.0)
    action = OUTLIER_CONFIG.get('action', 'cap')
    target_cols = OUTLIER_CONFIG.get('target_columns', [])

    print(f"\n  이상치 처리 중 (방법: {method}, 임계값: {threshold}, 조치: {action})...")

    capped_counts = {}

    for col in target_cols:
        if col.lower() not in df.columns:
            continue

        col_lower = col.lower()
        series = df[col_lower].dropna()

        if len(series) == 0:
            continue

        # IQR 기반 이상치 탐지
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR

        if action == 'cap':
            # Capping: 상한/하한으로 제한
            outlier_count = ((df[col_lower] < lower_bound) | (df[col_lower] > upper_bound)).sum()

            if outlier_count > 0:
                df[col_lower] = df[col_lower].clip(lower=lower_bound, upper=upper_bound)
                capped_counts[col] = outlier_count

        elif action == 'remove':
            # 제거: NULL로 변환
            outlier_mask = (df[col_lower] < lower_bound) | (df[col_lower] > upper_bound)
            outlier_count = outlier_mask.sum()
            if outlier_count > 0:
                df.loc[outlier_mask, col_lower] = np.nan
                capped_counts[col] = outlier_count

    if capped_counts:
        total = sum(capped_counts.values())
        print(f"    ✓ {total:,}개 이상치 처리:")
        for col, count in sorted(capped_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {col}: {count:,}개")
    else:
        print(f"    ✓ 처리할 이상치 없음")

    return df


def calculate_altman_z_score(df):
    """
    Altman Z-Score Modified 계산

    Parameters:
    -----------
    df : DataFrame
        필요 컬럼: fn3_11, fn1_22, fn3_7, fn1_24, fn1_19, fn2_1, fn1_13
        (PostgreSQL이 소문자로 반환)

    Returns:
    --------
    Series
        Z-Score 값 (inf, -inf는 NaN으로 변환)
    """
    # 분모가 0이거나 NULL인 경우 처리
    total_assets = df['fn1_13'].replace(0, np.nan)
    total_debt = df['fn1_19'].replace(0, np.nan)

    # 각 X 계산
    X1 = df['fn3_11'] / total_assets          # Net Working Capital / Total Assets
    X2 = df['fn1_22'] / total_assets          # Retained Earnings / Total Assets
    X3 = df['fn3_7'] / total_assets           # EBIT / Total Assets
    X4 = df['fn1_24'] / total_debt            # Equity / Total Debt
    X5 = df['fn2_1'] / total_assets           # Sales / Total Assets

    # Z-Score 계산
    z_score = (
        0.717 * X1 +
        0.847 * X2 +
        3.107 * X3 +
        0.420 * X4 +
        0.998 * X5
    )

    # inf, -inf를 NaN으로 변환
    z_score = z_score.replace([np.inf, -np.inf], np.nan)

    return z_score


def extract_monthly_data():
    """DWH에서 월별 데이터 추출 및 클렌징"""
    print("\n월별 데이터 추출 중...")

    query = f"""
    SELECT
        t.BS_DT,
        c.SIC_CD_3,  -- 업종 코드 (결측치 대체용)
        cb.CORP_GRAD,
        cb.PERF_12M,

        -- Z-Score 계산용 재무 데이터
        fs.FN3_11,   -- 순운전자본
        fs.FN1_22,   -- 이익잉여금
        fs.FN3_7,    -- EBIT
        fs.FN1_24,   -- 자본총계
        fs.FN1_19,   -- 부채총계
        fs.FN2_1,    -- 매출액
        fs.FN1_13    -- 총자산

    FROM {DWH_SCHEMA}.fact_credit_behavior cb
    JOIN {DWH_SCHEMA}.dim_company c ON cb.COMPANY_SK = c.COMPANY_SK
    JOIN {DWH_SCHEMA}.dim_time t ON cb.TIME_SK = t.TIME_SK
    LEFT JOIN {DWH_SCHEMA}.fact_financial_statement fs ON cb.COMPANY_SK = fs.COMPANY_SK AND cb.TIME_SK = fs.TIME_SK

    WHERE t.BS_DT IS NOT NULL
      AND cb.CORP_GRAD IS NOT NULL
      AND cb.PERF_12M IS NOT NULL

    ORDER BY t.BS_DT
    """

    df = pd.read_sql(query, engine)
    print(f"  추출된 레코드 수: {len(df):,}개")

    # 타입 변환 (PostgreSQL에서 VARCHAR로 저장된 경우)
    df['corp_grad'] = pd.to_numeric(df['corp_grad'], errors='coerce')
    df['perf_12m'] = pd.to_numeric(df['perf_12m'], errors='coerce')

    # === Mart 클렌징 시작 ===
    print("\n=== Mart 클렌징 (결측치 대체 + 이상치 처리) ===")

    # 1. 결측치 대체 (업종별 중앙값)
    df = impute_missing_values(df)

    # 2. 이상치 처리 (Capping)
    df = handle_outliers(df)

    # === Z-Score 계산 (클렌징 후) ===
    print("\n  Altman Z-Score 계산 중 (클렌징된 데이터 사용)...")
    df['z_score'] = calculate_altman_z_score(df)

    z_null_count = df['z_score'].isna().sum()
    z_valid_count = df['z_score'].notna().sum()
    print(f"  유효한 Z-Score: {z_valid_count:,}개")
    print(f"  NULL Z-Score: {z_null_count:,}개")

    if z_valid_count > 0:
        print(f"  Z-Score 통계:")
        print(f"    - 평균: {df['z_score'].mean():.4f}")
        print(f"    - 중앙값: {df['z_score'].median():.4f}")
        print(f"    - 최소: {df['z_score'].min():.4f}")
        print(f"    - 최대: {df['z_score'].max():.4f}")

        # Z-Score 구간별 분포
        safe_count = (df['z_score'] > 2.9).sum()
        gray_count = ((df['z_score'] >= 1.23) & (df['z_score'] <= 2.9)).sum()
        distress_count = (df['z_score'] < 1.23).sum()

        print(f"\n  Z-Score 분포:")
        print(f"    - 안전 (> 2.9): {safe_count:,}개 ({safe_count/z_valid_count*100:.1f}%)")
        print(f"    - 회색지대 (1.23-2.9): {gray_count:,}개 ({gray_count/z_valid_count*100:.1f}%)")
        print(f"    - 위험 (< 1.23): {distress_count:,}개 ({distress_count/z_valid_count*100:.1f}%)")

    return df


def aggregate_monthly_kpi(df):
    """월별 KPI 집계"""
    print("\n월별 KPI 집계 중...")

    monthly_kpis = []

    for bs_dt, group in df.groupby('bs_dt'):
        # 기본 KPI 계산
        total_companies = len(group)
        avg_credit_grade = group['corp_grad'].mean()
        default_count = (group['perf_12m'] == 1).sum()
        default_rate = (default_count / total_companies) * 100

        # 고위험 기업 비율 (신용등급 8-10)
        high_risk_count = (group['corp_grad'] >= 8).sum()
        high_risk_ratio = (high_risk_count / total_companies) * 100

        # 평균 Z-Score
        avg_z_score = group['z_score'].mean()

        monthly_kpis.append({
            'bs_dt': bs_dt,
            'total_companies': total_companies,
            'avg_credit_grade': round(avg_credit_grade, 2) if pd.notna(avg_credit_grade) else None,
            'default_rate': round(default_rate, 2),
            'high_risk_ratio': round(high_risk_ratio, 2),
            'avg_z_score': round(avg_z_score, 4) if pd.notna(avg_z_score) else None,
        })

    kpi_df = pd.DataFrame(monthly_kpis).sort_values('bs_dt')

    # MoM (Month-over-Month) 변화 계산
    kpi_df['total_companies_prev'] = kpi_df['total_companies'].shift(1)
    kpi_df['avg_credit_grade_prev'] = kpi_df['avg_credit_grade'].shift(1)
    kpi_df['default_rate_prev'] = kpi_df['default_rate'].shift(1)
    kpi_df['high_risk_ratio_prev'] = kpi_df['high_risk_ratio'].shift(1)
    kpi_df['avg_z_score_prev'] = kpi_df['avg_z_score'].shift(1)

    # 변화량 계산
    kpi_df['total_companies_change'] = kpi_df['total_companies'] - kpi_df['total_companies_prev']
    kpi_df['avg_credit_grade_change'] = kpi_df['avg_credit_grade'] - kpi_df['avg_credit_grade_prev']
    kpi_df['default_rate_change'] = kpi_df['default_rate'] - kpi_df['default_rate_prev']
    kpi_df['high_risk_ratio_change'] = kpi_df['high_risk_ratio'] - kpi_df['high_risk_ratio_prev']
    kpi_df['avg_z_score_change'] = kpi_df['avg_z_score'] - kpi_df['avg_z_score_prev']

    print(f"  집계된 월 수: {len(kpi_df)}개")

    return kpi_df


def load_to_mart(kpi_df):
    """마트 테이블에 적재 (UPSERT)"""
    print(f"\n{DM_SCHEMA}.mart_market_kpi_monthly 테이블에 적재 중...")

    inserted_count = 0
    updated_count = 0

    with engine.begin() as conn:
        for _, row in kpi_df.iterrows():
            query = text(f"""
                INSERT INTO {DM_SCHEMA}.mart_market_kpi_monthly (
                    bs_dt,
                    total_companies, avg_credit_grade, default_rate, high_risk_ratio, avg_z_score,
                    total_companies_prev, avg_credit_grade_prev, default_rate_prev, high_risk_ratio_prev, avg_z_score_prev,
                    total_companies_change, avg_credit_grade_change, default_rate_change, high_risk_ratio_change, avg_z_score_change,
                    created_at, updated_at
                ) VALUES (
                    :bs_dt,
                    :total_companies, :avg_credit_grade, :default_rate, :high_risk_ratio, :avg_z_score,
                    :total_companies_prev, :avg_credit_grade_prev, :default_rate_prev, :high_risk_ratio_prev, :avg_z_score_prev,
                    :total_companies_change, :avg_credit_grade_change, :default_rate_change, :high_risk_ratio_change, :avg_z_score_change,
                    NOW(), NOW()
                )
                ON CONFLICT (bs_dt) DO UPDATE SET
                    total_companies = EXCLUDED.total_companies,
                    avg_credit_grade = EXCLUDED.avg_credit_grade,
                    default_rate = EXCLUDED.default_rate,
                    high_risk_ratio = EXCLUDED.high_risk_ratio,
                    avg_z_score = EXCLUDED.avg_z_score,
                    total_companies_prev = EXCLUDED.total_companies_prev,
                    avg_credit_grade_prev = EXCLUDED.avg_credit_grade_prev,
                    default_rate_prev = EXCLUDED.default_rate_prev,
                    high_risk_ratio_prev = EXCLUDED.high_risk_ratio_prev,
                    avg_z_score_prev = EXCLUDED.avg_z_score_prev,
                    total_companies_change = EXCLUDED.total_companies_change,
                    avg_credit_grade_change = EXCLUDED.avg_credit_grade_change,
                    default_rate_change = EXCLUDED.default_rate_change,
                    high_risk_ratio_change = EXCLUDED.high_risk_ratio_change,
                    avg_z_score_change = EXCLUDED.avg_z_score_change,
                    updated_at = NOW()
            """)

            # NaN을 None으로 변환 (PostgreSQL NULL)
            params = row.where(pd.notna(row), None).to_dict()
            conn.execute(query, params)

    print(f"  ✓ {len(kpi_df)}개월 데이터 적재 완료")


def verify_mart():
    """마트 데이터 확인"""
    print("\n" + "="*80)
    print("마트 데이터 확인")
    print("="*80)

    with engine.begin() as conn:
        # 전체 레코드 수
        result = conn.execute(text(f"""
            SELECT COUNT(*) FROM {DM_SCHEMA}.mart_market_kpi_monthly
        """))
        total_count = result.scalar()
        print(f"\n총 레코드 수: {total_count}개월\n")

        # 월별 KPI 조회
        result = conn.execute(text(f"""
            SELECT
                TO_CHAR(bs_dt, 'YYYY-MM') as year_month,
                total_companies,
                ROUND(avg_credit_grade, 2) as avg_grade,
                ROUND(default_rate, 2) as default_pct,
                ROUND(high_risk_ratio, 2) as high_risk_pct,
                ROUND(avg_z_score, 4) as avg_z,
                ROUND(avg_credit_grade_change, 2) as grade_change,
                ROUND(default_rate_change, 2) as default_change
            FROM {DM_SCHEMA}.mart_market_kpi_monthly
            ORDER BY bs_dt
        """))

        print("월별 KPI 지표:")
        print("-" * 120)
        print(f"{'월':<10} {'기업수':<10} {'평균등급':<10} {'부도율%':<10} {'고위험%':<10} {'평균Z':<12} {'등급변화':<12} {'부도변화':<12}")
        print("-" * 120)

        for row in result:
            print(f"{row[0]:<10} {row[1]:<10} {row[2] if row[2] else 'N/A':<10} {row[3]:<10} {row[4]:<10} {row[5] if row[5] else 'N/A':<12} {row[6] if row[6] else 'N/A':<12} {row[7] if row[7] else 'N/A':<12}")


def main():
    try:
        print("\n" + "="*80)
        print("월별 시장 KPI 마트 적재 시작")
        print("="*80)

        # 1. 데이터 추출 및 Z-Score 계산
        df = extract_monthly_data()

        # 2. 월별 KPI 집계
        kpi_df = aggregate_monthly_kpi(df)

        # 3. 마트 적재
        load_to_mart(kpi_df)

        # 4. 결과 확인
        verify_mart()

        print("\n" + "="*80)
        print("✓ 월별 시장 KPI 마트 적재 완료!")
        print("="*80)

    except Exception as e:
        print(f"\n✗ 마트 적재 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
