"""
산업별 위험 프로파일 마트 생성 (간소화 버전)
===========================================

기존 마트 데이터를 활용하여 산업별 6가지 위험 지표 계산:
1. 신용 건전성 (평균 신용등급)
2. 부도 위험도 (부도율)
3. 재무 안정성 (부채비율, 유동비율)
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


def create_industry_risk_radar_mart():
    """산업별 위험 프로파일 레이더 차트용 마트 생성"""
    engine = create_engine(DB_URL)

    with engine.connect() as conn:
        logger.info("Dropping existing mart_industry_risk_radar...")
        conn.execute(text("DROP TABLE IF EXISTS marts.mart_industry_risk_radar CASCADE"))
        conn.commit()

        logger.info("Creating mart_industry_risk_radar...")

        # 산업별 평균 지표를 6가지 위험 점수로 변환
        create_mart_query = text("""
            CREATE TABLE marts.mart_industry_risk_radar AS
            WITH industry_metrics AS (
                SELECT
                    industry_code,
                    industry_name,
                    AVG(default_rate) as avg_default_rate,
                    AVG(total_companies) as avg_companies,

                    -- From credit grade distribution
                    (SELECT AVG(credit_grade * company_count) / NULLIF(SUM(company_count), 0)
                     FROM marts.mart_credit_grade_distribution_monthly cgd
                     JOIN marts.mart_industry_default_trend idt ON cgd.bs_dt = idt.bs_dt
                     WHERE idt.industry_code = trend.industry_code
                    ) as weighted_avg_grade

                FROM marts.mart_industry_default_trend trend
                GROUP BY industry_code, industry_name
            )
            SELECT
                industry_code,
                industry_name,

                -- 1. Credit Health Score (0-100, higher is better)
                -- Lower credit grade = better (1 is best, 10 is worst)
                ROUND((100 - (COALESCE(weighted_avg_grade, 5.5) - 1) * 11.11)::numeric, 2) as credit_health_score,

                -- 2. Default Risk Score (0-100, higher is better = lower default)
                ROUND(GREATEST(0, 100 - (avg_default_rate * 20))::numeric, 2) as default_risk_score,

                -- 3. Market Presence Score (0-100, based on company count)
                ROUND(LEAST(100, (avg_companies / 100) * 100)::numeric, 2) as market_presence_score,

                -- 4-6: Financial metrics (using industry risk ranking mart)
                COALESCE(
                    (SELECT ROUND(GREATEST(0, 100 - LEAST(100, default_rate * 15))::numeric, 2)
                     FROM marts.mart_industry_risk_ranking
                     WHERE industry_code = industry_metrics.industry_code
                    ), 50
                ) as financial_stability_score,

                COALESCE(
                    (SELECT ROUND((100 - risk_score)::numeric, 2)
                     FROM marts.mart_industry_risk_ranking
                     WHERE industry_code = industry_metrics.industry_code
                    ), 50
                ) as overall_health_score,

                -- Growth potential (inverse of default rate)
                ROUND(GREATEST(0, 100 - (avg_default_rate * 25))::numeric, 2) as growth_potential_score,

                -- Raw metrics for reference
                ROUND(avg_default_rate::numeric, 2) as raw_default_rate,
                ROUND(avg_companies::numeric, 0) as raw_company_count,
                ROUND(COALESCE(weighted_avg_grade, 5.5)::numeric, 2) as raw_avg_credit_grade,

                NOW() as created_at,
                NOW() as updated_at

            FROM industry_metrics
            ORDER BY industry_code
        """)

        conn.execute(create_mart_query)
        conn.commit()

        # Create index
        logger.info("Creating index...")
        conn.execute(text("CREATE INDEX idx_industry_risk_radar_code ON marts.mart_industry_risk_radar(industry_code)"))
        conn.commit()

        # Get row count
        result = conn.execute(text("SELECT COUNT(*) FROM marts.mart_industry_risk_radar"))
        count = result.scalar()
        logger.info(f"✓ Created mart_industry_risk_radar with {count:,} rows")

        # Sample data
        sample = conn.execute(text("""
            SELECT
                industry_code,
                industry_name,
                credit_health_score,
                default_risk_score,
                market_presence_score,
                financial_stability_score,
                overall_health_score,
                growth_potential_score
            FROM marts.mart_industry_risk_radar
            ORDER BY default_risk_score DESC
            LIMIT 5
        """)).fetchall()

        logger.info("\nTop 5 Industries by Default Risk Score (Higher = Better):")
        logger.info(f"{'Code':<4} {'Name':<30} {'Credit':>6} {'Default':>7} {'Market':>7} {'Financial':>9} {'Overall':>8} {'Growth':>7}")
        logger.info("-" * 85)
        for row in sample:
            logger.info(f"{row[0]:<4} {row[1]:<30} {row[2]:>6.1f} {row[3]:>7.1f} {row[4]:>7.1f} {row[5]:>9.1f} {row[6]:>8.1f} {row[7]:>7.1f}")


if __name__ == "__main__":
    try:
        create_industry_risk_radar_mart()
        logger.info("\n✓ Industry risk radar mart creation completed successfully!")
    except Exception as e:
        logger.error(f"\n✗ Error creating industry risk radar mart: {e}")
        raise
