"""
조기경보 위험 프로파일 마트 생성
================================

6가지 위험 요소를 0-100 스케일로 정규화하여 레이더 차트에 사용:
1. 신용등급 점수 (낮을수록 위험)
2. 연체 위험도
3. 부채 건전성
4. 유동성 건전성
5. 수익성 건전성
6. 기업 규모 안정성
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from shared.config_loader import DB_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_risk_profile_mart():
    """위험 프로파일 마트 생성"""
    engine = create_engine(DB_URL)

    with engine.connect() as conn:
        # Drop existing mart
        logger.info("Dropping existing mart_company_risk_profile...")
        conn.execute(text("DROP TABLE IF EXISTS marts.mart_company_risk_profile CASCADE"))
        conn.commit()

        # Create new mart with risk scores
        logger.info("Creating mart_company_risk_profile...")

        create_mart_query = text("""
            CREATE TABLE marts.mart_company_risk_profile AS
            WITH base_data AS (
                SELECT
                    fc.company_key,
                    fc.period_key,
                    fc.industry_key,
                    dp.bs_dt,
                    di.industry_code,
                    di.industry_name,

                    -- Raw metrics
                    fc.credit_grade,
                    fc.overdue_days_tax,
                    fc.overdue_days_bill,
                    fc.overdue_days_loan,
                    ffr.debt_ratio,
                    ffr.current_ratio,
                    ffr.roa,
                    ffr.operating_margin,
                    fbs.total_assets,
                    fc.default_yn

                FROM dwh.fact_credit_event fc
                JOIN dwh.dim_period dp ON fc.period_key = dp.period_key
                JOIN dwh.dim_industry di ON fc.industry_key = di.industry_key
                LEFT JOIN dwh.fact_financial_ratios ffr ON
                    fc.company_key = ffr.company_key AND fc.period_key = ffr.period_key
                LEFT JOIN dwh.fact_balance_sheet fbs ON
                    fc.company_key = fbs.company_key AND fc.period_key = fbs.period_key
            ),
            risk_calculations AS (
                SELECT
                    company_key,
                    period_key,
                    industry_key,
                    bs_dt,
                    industry_code,
                    industry_name,
                    default_yn,

                    -- 1. Credit Grade Score (0-100, higher is better)
                    -- Grade 1-3 (excellent): 90-100
                    -- Grade 4-5 (good): 70-89
                    -- Grade 6-7 (fair): 40-69
                    -- Grade 8-10 (poor): 0-39
                    CASE
                        WHEN credit_grade <= 3 THEN 100 - (credit_grade - 1) * 3.33
                        WHEN credit_grade <= 5 THEN 85 - (credit_grade - 4) * 7.5
                        WHEN credit_grade <= 7 THEN 55 - (credit_grade - 6) * 7.5
                        ELSE 35 - (credit_grade - 8) * 11.67
                    END as credit_score,

                    -- 2. Delinquency Risk (0-100, higher is better = less delinquent)
                    CASE
                        WHEN COALESCE(overdue_days_tax, 0) = 0
                         AND COALESCE(overdue_days_bill, 0) = 0
                         AND COALESCE(overdue_days_loan, 0) = 0 THEN 100
                        WHEN COALESCE(overdue_days_tax, 0) + COALESCE(overdue_days_bill, 0) + COALESCE(overdue_days_loan, 0) <= 30 THEN 70
                        WHEN COALESCE(overdue_days_tax, 0) + COALESCE(overdue_days_bill, 0) + COALESCE(overdue_days_loan, 0) <= 90 THEN 40
                        WHEN COALESCE(overdue_days_tax, 0) + COALESCE(overdue_days_bill, 0) + COALESCE(overdue_days_loan, 0) <= 180 THEN 20
                        ELSE 0
                    END as delinquency_score,

                    -- 3. Debt Health (0-100, higher is better = lower debt ratio)
                    CASE
                        WHEN debt_ratio IS NULL THEN 50  -- neutral
                        WHEN debt_ratio <= 50 THEN 100
                        WHEN debt_ratio <= 100 THEN 100 - (debt_ratio - 50)
                        WHEN debt_ratio <= 200 THEN 50 - (debt_ratio - 100) / 2
                        WHEN debt_ratio <= 500 THEN 25 - (debt_ratio - 200) / 12
                        ELSE 0
                    END as debt_health_score,

                    -- 4. Liquidity Health (0-100, higher is better)
                    CASE
                        WHEN current_ratio IS NULL THEN 50
                        WHEN current_ratio >= 200 THEN 100
                        WHEN current_ratio >= 150 THEN 80 + (current_ratio - 150) / 2.5
                        WHEN current_ratio >= 100 THEN 60 + (current_ratio - 100) * 0.4
                        WHEN current_ratio >= 50 THEN 30 + (current_ratio - 50) * 0.6
                        ELSE current_ratio * 0.6
                    END as liquidity_score,

                    -- 5. Profitability Health (0-100, higher is better)
                    CASE
                        WHEN roa IS NULL AND operating_margin IS NULL THEN 50
                        WHEN COALESCE(roa, 0) >= 10 AND COALESCE(operating_margin, 0) >= 10 THEN 100
                        WHEN COALESCE(roa, 0) >= 5 AND COALESCE(operating_margin, 0) >= 5 THEN 80
                        WHEN COALESCE(roa, 0) >= 0 AND COALESCE(operating_margin, 0) >= 0 THEN 60
                        WHEN COALESCE(roa, 0) >= -5 AND COALESCE(operating_margin, 0) >= -5 THEN 40
                        WHEN COALESCE(roa, 0) >= -10 AND COALESCE(operating_margin, 0) >= -10 THEN 20
                        ELSE 0
                    END as profitability_score,

                    -- 6. Size Stability (0-100, medium-large is best)
                    CASE
                        WHEN total_assets IS NULL THEN 50
                        WHEN total_assets BETWEEN 1000000000 AND 50000000000 THEN 100  -- 10억-500억 (sweet spot)
                        WHEN total_assets BETWEEN 100000000 AND 1000000000 THEN 80     -- 1억-10억
                        WHEN total_assets > 50000000000 THEN 70                         -- >500억 (paradox)
                        ELSE 50                                                         -- <1억
                    END as size_stability_score

                FROM base_data
            )
            SELECT
                company_key,
                period_key,
                industry_key,
                bs_dt,
                industry_code,
                industry_name,
                default_yn,

                -- Individual scores
                ROUND(credit_score::numeric, 2) as credit_score,
                ROUND(delinquency_score::numeric, 2) as delinquency_score,
                ROUND(debt_health_score::numeric, 2) as debt_health_score,
                ROUND(liquidity_score::numeric, 2) as liquidity_score,
                ROUND(profitability_score::numeric, 2) as profitability_score,
                ROUND(size_stability_score::numeric, 2) as size_stability_score,

                -- Overall risk score (weighted average)
                ROUND(
                    (credit_score * 0.25 +
                     delinquency_score * 0.25 +
                     debt_health_score * 0.15 +
                     liquidity_score * 0.15 +
                     profitability_score * 0.10 +
                     size_stability_score * 0.10)::numeric, 2
                ) as overall_risk_score,

                -- Risk level category
                CASE
                    WHEN (credit_score * 0.25 + delinquency_score * 0.25 + debt_health_score * 0.15 +
                          liquidity_score * 0.15 + profitability_score * 0.10 + size_stability_score * 0.10) >= 80 THEN 'Low'
                    WHEN (credit_score * 0.25 + delinquency_score * 0.25 + debt_health_score * 0.15 +
                          liquidity_score * 0.15 + profitability_score * 0.10 + size_stability_score * 0.10) >= 60 THEN 'Medium'
                    WHEN (credit_score * 0.25 + delinquency_score * 0.25 + debt_health_score * 0.15 +
                          liquidity_score * 0.15 + profitability_score * 0.10 + size_stability_score * 0.10) >= 40 THEN 'High'
                    ELSE 'Critical'
                END as risk_level,

                NOW() as created_at,
                NOW() as updated_at

            FROM risk_calculations
        """)

        conn.execute(create_mart_query)
        conn.commit()

        # Create indexes
        logger.info("Creating indexes...")
        conn.execute(text("CREATE INDEX idx_risk_profile_period ON marts.mart_company_risk_profile(period_key)"))
        conn.execute(text("CREATE INDEX idx_risk_profile_industry ON marts.mart_company_risk_profile(industry_key)"))
        conn.execute(text("CREATE INDEX idx_risk_profile_risk_level ON marts.mart_company_risk_profile(risk_level)"))
        conn.execute(text("CREATE INDEX idx_risk_profile_default ON marts.mart_company_risk_profile(default_yn)"))
        conn.commit()

        # Get row count
        result = conn.execute(text("SELECT COUNT(*) FROM marts.mart_company_risk_profile"))
        count = result.scalar()
        logger.info(f"✓ Created mart_company_risk_profile with {count:,} rows")

        # Sample statistics
        stats = conn.execute(text("""
            SELECT
                risk_level,
                COUNT(*) as count,
                ROUND(AVG(overall_risk_score), 2) as avg_score,
                ROUND(AVG(CASE WHEN default_yn = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) as default_rate_pct
            FROM marts.mart_company_risk_profile
            GROUP BY risk_level
            ORDER BY
                CASE risk_level
                    WHEN 'Low' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'High' THEN 3
                    WHEN 'Critical' THEN 4
                END
        """)).fetchall()

        logger.info("\nRisk Level Distribution:")
        for row in stats:
            logger.info(f"  {row[0]:8s}: {row[1]:6,} companies | Avg Score: {row[2]:5.1f} | Default Rate: {row[3]:5.2f}%")


if __name__ == "__main__":
    try:
        create_risk_profile_mart()
        logger.info("\n✓ Risk profile mart creation completed successfully!")
    except Exception as e:
        logger.error(f"\n✗ Error creating risk profile mart: {e}")
        raise
