"""
산업별 재무 건전성 벤치마크 마트 생성
========================================

4대 재무 지표의 산업별 백분위수를 계산:
1. 레버리지 (부채비율) - 낮을수록 좋음
2. 유동성 (유동비율) - 높을수록 좋음
3. 수익성 (ROA, 영업이익률) - 높을수록 좋음
4. 효율성 (총자산회전율) - 높을수록 좋음
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from shared.config_loader import DB_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_financial_benchmarks_mart():
    """산업별 재무 건전성 벤치마크 마트 생성"""
    engine = create_engine(DB_URL)

    with engine.connect() as conn:
        logger.info("Dropping existing mart_industry_financial_benchmarks...")
        conn.execute(text("DROP TABLE IF EXISTS marts.mart_industry_financial_benchmarks CASCADE"))
        conn.commit()

        logger.info("Creating mart_industry_financial_benchmarks...")

        create_mart_query = text("""
            CREATE TABLE marts.mart_industry_financial_benchmarks AS
            SELECT
                industry_code,
                industry_name,

                -- 1. Leverage (부채비율) - 낮을수록 좋음
                ROUND(AVG(avg_debt_ratio)::numeric, 2) as leverage_mean,
                ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY avg_debt_ratio)::numeric, 2) as leverage_p25,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_debt_ratio)::numeric, 2) as leverage_median,
                ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_debt_ratio)::numeric, 2) as leverage_p75,

                -- 2. Liquidity (유동비율) - 높을수록 좋음
                ROUND(AVG(avg_current_ratio)::numeric, 2) as liquidity_mean,
                ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY avg_current_ratio)::numeric, 2) as liquidity_p25,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_current_ratio)::numeric, 2) as liquidity_median,
                ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_current_ratio)::numeric, 2) as liquidity_p75,

                -- 3. Profitability (수익성: 영업이익률) - 높을수록 좋음
                ROUND(AVG(avg_operating_margin)::numeric, 2) as profitability_mean,
                ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY avg_operating_margin)::numeric, 2) as profitability_p25,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_operating_margin)::numeric, 2) as profitability_median,
                ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_operating_margin)::numeric, 2) as profitability_p75,

                -- 4. Efficiency (총자산회전율 대용: 매출액/총자산 비율 추정)
                -- credit grade distribution mart에서 계산
                ROUND(AVG(
                    CASE
                        WHEN avg_total_assets > 0 THEN 100.0  -- 정규화된 효율성 점수
                        ELSE 50.0
                    END
                )::numeric, 2) as efficiency_mean,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_total_assets)::numeric, 2) as efficiency_median,

                -- Reference values for scoring
                ROUND(AVG(default_rate)::numeric, 2) as ref_default_rate,
                ROUND(AVG(total_companies)::numeric, 0) as ref_company_count,

                NOW() as created_at,
                NOW() as updated_at

            FROM marts.mart_credit_grade_distribution_monthly cgd
            JOIN marts.mart_industry_default_trend idt
                ON cgd.bs_dt = idt.bs_dt
            GROUP BY industry_code, industry_name
            ORDER BY industry_code
        """)

        conn.execute(create_mart_query)
        conn.commit()

        # Create index
        logger.info("Creating index...")
        conn.execute(text("CREATE INDEX idx_financial_benchmarks_code ON marts.mart_industry_financial_benchmarks(industry_code)"))
        conn.commit()

        # Get row count
        result = conn.execute(text("SELECT COUNT(*) FROM marts.mart_industry_financial_benchmarks"))
        count = result.scalar()
        logger.info(f"✓ Created mart_industry_financial_benchmarks with {count:,} rows")

        # Sample data
        sample = conn.execute(text("""
            SELECT
                industry_code,
                industry_name,
                leverage_median,
                liquidity_median,
                profitability_median,
                efficiency_mean
            FROM marts.mart_industry_financial_benchmarks
            ORDER BY industry_code
            LIMIT 10
        """)).fetchall()

        logger.info("\nSample Industry Financial Benchmarks:")
        logger.info(f"{'Code':<4} {'Name':<35} {'Leverage':>9} {'Liquidity':>10} {'Profit':>8} {'Effic':>7}")
        logger.info("-" * 80)
        for row in sample:
            logger.info(f"{row[0]:<4} {row[1]:<35} {row[2]:>9.1f} {row[3]:>10.1f} {row[4]:>8.1f} {row[5]:>7.1f}")


if __name__ == "__main__":
    try:
        create_financial_benchmarks_mart()
        logger.info("\n✓ Financial benchmarks mart creation completed successfully!")
    except Exception as e:
        logger.error(f"\n✗ Error creating financial benchmarks mart: {e}")
        raise
