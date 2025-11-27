"""
클러스터링 API 모델 정의
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class ClusterPredictionResponse(BaseModel):
    """클러스터 예측 결과"""
    success: bool
    cluster_id: int = Field(..., description="클러스터 ID (0-12, -1=노이즈)")
    cluster_name: str = Field(..., description="클러스터 별명")
    cluster_description: str = Field(..., description="클러스터 설명")
    method: Optional[str] = Field(None, description="예측 방법 (model/rule_based)")


class BenchmarkMetric(BaseModel):
    """벤치마크 지표"""
    name: str = Field(..., description="지표명")
    key: str = Field(..., description="피처 키")
    company_value: float = Field(..., description="기업 값")
    cluster_avg: float = Field(..., description="클러스터 평균")
    percentile: int = Field(..., ge=1, le=99, description="백분위수 (1-99)")
    comparison: str = Field(..., description="비교 결과 (above/below/average)")
    unit: str = Field(..., description="단위")


class RadarDataPoint(BaseModel):
    """레이더 차트 데이터 포인트"""
    metric: str
    company: int = Field(..., description="기업 백분위수")
    cluster_avg: int = Field(50, description="클러스터 평균 (항상 50)")


class ClusterBenchmarkResponse(BaseModel):
    """클러스터 벤치마크 결과"""
    cluster_id: int
    cluster_name: str
    metrics: List[BenchmarkMetric] = Field(..., description="지표별 벤치마크")
    radar_data: List[RadarDataPoint] = Field(..., description="레이더 차트 데이터")
    summary: str = Field(..., description="요약 텍스트")


class PartnerCompany(BaseModel):
    """추천 협력사 기업"""
    company_id: str = Field(..., description="기업 ID")
    company_name: str = Field(..., description="기업명")
    default_probability: float = Field(..., description="부도확률 (0-1)")
    risk_level: str = Field(..., description="위험도 (Low/Medium/High)")
    industry: str = Field(..., description="업종")
    similarity_score: float = Field(..., description="유사도 점수 (0-1)")
    key_strengths: List[str] = Field(..., description="핵심 강점")


class PartnerRecommendationResponse(BaseModel):
    """협력사 추천 결과"""
    cluster_id: int
    cluster_name: str
    total_count: int = Field(..., description="추천 기업 수")
    partners: List[PartnerCompany] = Field(..., description="추천 기업 목록")


class FullAnalysisRequest(BaseModel):
    """통합 분석 요청 (JSON 입력용)"""
    clustering_features: Dict = Field(..., description="70개 클러스터링 피처")


class IndustryBenchmark(BaseModel):
    """업종 대비 벤치마크 결과"""
    industry_code: str = Field(..., description="업종 코드")
    industry_name: str = Field(..., description="업종명")
    metrics: List[Dict] = Field(..., description="지표별 업종 대비 벤치마크")
    percentile_rank: int = Field(..., description="업종 내 종합 백분위")
    summary: str = Field(..., description="업종 대비 요약")


class DiagnosisReport(BaseModel):
    """기업 진단 리포트"""
    report_text: str = Field(..., description="LLM 생성 종합 리포트")
    risk_interpretation: str = Field(..., description="위험 요인 해석")
    radar_chart: Optional[str] = Field(None, description="레이더 차트 (base64 이미지)")


class FullAnalysisResponse(BaseModel):
    """통합 분석 결과 (부도예측 + 클러스터링 + 협력사 + 진단)"""
    success: bool

    # 부도 예측 결과
    default_prediction: Dict = Field(..., description="부도 예측 결과")
    shap_values: Optional[Dict] = Field(None, description="SHAP 설명")

    # 클러스터링 결과
    clustering: ClusterPredictionResponse = Field(..., description="클러스터 예측 결과")
    benchmark: ClusterBenchmarkResponse = Field(..., description="클러스터 벤치마크 결과")

    # 업종 대비 분석 (신규)
    industry_benchmark: Optional[IndustryBenchmark] = Field(None, description="업종 대비 벤치마크")

    # 진단 리포트 (신규)
    diagnosis: Optional[DiagnosisReport] = Field(None, description="종합 진단 리포트")

    # 협력사 추천
    partners: List[PartnerCompany] = Field(..., description="추천 협력사 목록")

    # 기타 정보
    clustering_features: Optional[Dict] = Field(None, description="70개 클러스터링 피처")
    derived_ratios: Optional[Dict] = Field(None, description="자동 계산된 재무비율")
    message: Optional[str] = None
