// API Response Types

export interface KPIData {
  bs_dt: string;
  avg_credit_grade: number;
  avg_credit_grade_change: number;
  hhi_index: number;
  hhi_status: 'safe' | 'moderate' | 'high';
  hhi_description: string;
  high_risk_ratio: number;
  high_risk_change: number;
  premium_ratio: number;
  premium_to_risk_ratio: number;
}

export interface IndustryTrendData {
  industry_code: string;
  industry_name: string;
  bs_dt: string;
  default_rate: number;
}

export interface IndustryComposition {
  industry_code: string;
  industry_name: string;
  company_count: number;
  percentage: number;
}

export interface HeatmapData {
  bs_dt: string;
  industry_code: string;
  industry_name: string;
  default_rate: number;
}

export interface IndustryDefaultRate {
  industry_code: string;
  industry_name: string;
  default_rate: number;
  total_companies: number;
}

export interface CreditDistribution {
  credit_grade: number;
  company_count: number;
  percentage: number;
  default_rate: number;
  default_count: number;
}

export interface IndustryRiskRadar {
  industry_code: string;
  industry_name: string;
  credit_health_score: number;
  default_risk_score: number;
  market_presence_score: number;
  financial_stability_score: number;
  overall_health_score: number;
  growth_potential_score: number;
}

export interface BenchmarkStats {
  mean: number;
  median: number;
  p25?: number;
  p75?: number;
}

export interface FinancialBenchmarks {
  leverage: BenchmarkStats;
  liquidity: BenchmarkStats;
  profitability: BenchmarkStats;
  efficiency: BenchmarkStats;
}

// Component Props Types

export interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: number;
  trendLabel?: string;
  status?: 'safe' | 'moderate' | 'high' | 'improving' | 'worsening' | 'neutral';
  description?: string;
}
