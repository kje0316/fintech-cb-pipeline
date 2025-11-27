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

// Prediction API Types

export interface CompanyInfo {
  bs_dt: string;
  sic_cd_3: string | null;
  wg_gb: string | null;
  empe_cnt: string | null;
}

export interface DefaultPrediction {
  default_probability: number;
  default_prediction: number;
  risk_level: 'Low' | 'Medium' | 'High';
  confidence: number;
}

export interface FeatureContribution {
  feature_name: string;
  feature_value: number;
  shap_value: number;
  contribution_pct: number;
}

export interface ShapExplanation {
  base_value: number;
  expected_value: number;
  contributions: FeatureContribution[];
  error?: string;
}

export interface PredictionResponse {
  success: boolean;
  business_number: string;
  company_info: CompanyInfo | null;
  prediction: DefaultPrediction;
  shap_values: ShapExplanation | null;
  message?: string;
}

export interface PredictionRequest {
  business_number: string;
  bs_dt?: string;
}

// Full Analysis API Types

export interface BenchmarkMetric {
  name: string;
  key: string;
  company_value: number;
  cluster_avg: number;
  percentile: number;
  comparison: 'above' | 'below' | 'average';
  unit: string;
}

export interface RadarDataPoint {
  metric: string;
  company: number;
  cluster_avg: number;
}

export interface ClusterPrediction {
  success: boolean;
  cluster_id: number;
  cluster_name: string;
  cluster_description: string;
  method?: string;
}

export interface ClusterBenchmark {
  cluster_id: number;
  cluster_name: string;
  metrics: BenchmarkMetric[];
  radar_data: RadarDataPoint[];
  summary: string;
}

export interface PartnerCompany {
  company_id: string;
  company_name: string;
  default_probability: number;
  risk_level: string;
  industry: string;
  similarity_score: number;
  key_strengths: string[];
}

// 업종 대비 벤치마크
export interface IndustryBenchmarkMetric {
  name: string;
  key: string;
  company_value: number;
  industry_avg: number;
  percentile: number;
  unit: string;
}

export interface IndustryBenchmark {
  industry_code: string;
  industry_name: string;
  metrics: IndustryBenchmarkMetric[];
  percentile_rank: number;
  summary: string;
}

// 진단 리포트
export interface DiagnosisReport {
  report_text: string;
  risk_interpretation: string;
  radar_chart?: string;  // base64 이미지
}

export interface FullAnalysisResponse {
  success: boolean;
  default_prediction: DefaultPrediction;
  shap_values: ShapExplanation | null;
  clustering: ClusterPrediction;
  benchmark: ClusterBenchmark;
  industry_benchmark?: IndustryBenchmark;  // 신규
  diagnosis?: DiagnosisReport;  // 신규
  partners: PartnerCompany[];
  clustering_features?: Record<string, number>;
  derived_ratios?: Record<string, number>;
  message?: string;
}

// Lightweight Prediction Request (13개 필수 입력)
export interface LightweightPredictionRequest {
  // 연체 정보 (7개)
  da0d00029: number;
  da0d00029_1: number;
  da0d00026_1: number;
  da0d00035_2: number;
  da0d00035_3_2: number;
  da0d00035_4_1: number;
  da0d00035_4_2: number;
  // 신용사건 (2개)
  d2b000002: number;
  d2b000003: number;
  // 재무 정보 (3개)
  fn1_1: number;
  fn1_4: number;
  fn3_11_1: number;
  // 재무 비율 (1개)
  r007: number;
}

// User-Friendly Prediction Request (19개 입력)
export interface UserFriendlyPredictionRequest {
  // 재무상태표 (7개)
  fn1_13: number;  // 자산총계
  fn1_1: number;   // 유동자산
  fn1_4: number;   // 재고자산
  fn1_19: number;  // 부채총계
  fn1_24: number;  // 자본총계
  fn1_14: number;  // 유동부채
  fn1_15: number;  // 단기차입금
  // 손익계산서 (6개)
  fn2_1: number;    // 매출액
  fn2_5: number;    // 영업이익 당기
  fn2_5_1: number;  // 영업이익 전기
  fn2_10: number;   // 당기순이익 당기
  fn2_10_1: number; // 당기순이익 전기
  fn2_3: number;    // 판매비와관리비
  // 현금흐름 (1개)
  fn3_2: number;    // 영업활동현금흐름
  // 기업정보 (2개)
  empe_cnt: number; // 종업원수
  wg_gb: string;    // 외감여부 (Y/N)
  // 간소화 연체 (3개)
  has_delinquency: boolean;      // 연체 여부
  delinquency_days: number;      // 연체일수
  has_tax_delinquency: boolean;  // 세금 체납 여부
}
