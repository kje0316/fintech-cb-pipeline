"""
부도 예측 API 모델 정의
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class PredictionRequest(BaseModel):
    """예측 요청 모델 (사업자번호 조회용)"""
    business_number: str = Field(..., description="사업자번호 (10자리)")
    bs_dt: Optional[str] = Field(None, description="회계연도 (YYYYMMDD), 미입력 시 최신")


class PredictionResponse(BaseModel):
    """예측 결과 응답 모델"""
    success: bool
    business_number: str
    company_info: Optional[Dict] = Field(None, description="기업 기본 정보")
    prediction: Dict = Field(..., description="예측 결과")
    shap_values: Optional[Dict] = Field(None, description="SHAP 설명")
    message: Optional[str] = None


class CompanyInfo(BaseModel):
    """기업 기본 정보"""
    business_number: str
    bs_dt: str
    sic_cd_3: Optional[str] = Field(None, description="업종 코드")
    wg_gb: Optional[str] = Field(None, description="임금 구분")
    empe_cnt: Optional[str] = Field(None, description="종업원 수")


class DefaultPrediction(BaseModel):
    """부도 예측 결과"""
    default_probability: float = Field(..., description="부도 확률 (0-1)")
    default_prediction: int = Field(..., description="부도 예측 (0: 정상, 1: 부도)")
    risk_level: str = Field(..., description="위험도 (Low/Medium/High)")
    confidence: float = Field(1.0, description="예측 신뢰도 (0-1)")


class ShapExplanation(BaseModel):
    """SHAP 설명"""
    base_value: float = Field(..., description="기준값 (평균 예측)")
    expected_value: float = Field(..., description="예측값")
    contributions: List[Dict] = Field(..., description="피처별 기여도")


class FeatureContribution(BaseModel):
    """피처 기여도"""
    feature_name: str
    feature_value: float
    shap_value: float
    contribution_pct: float


# Phase 2: 경량 모델 입력 모델 (13개 필수 컬럼)
class LightweightPredictionRequest(BaseModel):
    """경량 모델 예측 요청 (13개 DWH 컬럼)"""
    # 연체 정보 (8개)
    da0d00029: float = Field(..., description="연체과목수(1년내발생)")
    da0d00029_1: float = Field(..., description="연체과목수(1년내발생)_1")
    da0d00026_1: float = Field(..., description="연체과목수(1년내유지)_1")
    da0d00035_2: float = Field(..., description="최장연체일수(1년)_2")
    da0d00035_3_2: float = Field(..., description="최장연체일수(1년)_3_2")
    da0d00035_4_1: float = Field(..., description="최장연체일수(1년)_4_1")
    da0d00035_4_2: float = Field(..., description="최장연체일수(1년)_4_2")

    # 신용사건 (2개)
    d2b000002: float = Field(..., description="공공신용정보(유형2)")
    d2b000003: float = Field(..., description="공공신용정보(유형3)")

    # 재무 정보 (3개)
    fn1_1: float = Field(..., description="유동자산 (천원)")
    fn1_4: float = Field(..., description="재고자산 (천원)")
    fn3_11_1: float = Field(..., description="순차입금_1 (천원)")

    # 재무 비율 (1개)
    r007: float = Field(..., description="자기자본비율 (%)")


# Phase 3: 사용자 친화 모델 입력 (19개)
class UserFriendlyPredictionRequest(BaseModel):
    """사용자 친화 모델 예측 요청 (19개 입력)"""

    # 재무상태표 (7개)
    fn1_13: float = Field(..., ge=0, description="자산총계 (천원)")
    fn1_1: float = Field(..., ge=0, description="유동자산 (천원)")
    fn1_4: float = Field(..., ge=0, description="재고자산 (천원)")
    fn1_19: float = Field(..., ge=0, description="부채총계 (천원)")
    fn1_24: float = Field(..., gt=0, description="자본총계 (천원)")
    fn1_14: float = Field(..., ge=0, description="유동부채 (천원)")
    fn1_15: float = Field(..., ge=0, description="단기차입금 (천원)")

    # 손익계산서 (6개)
    fn2_1: float = Field(..., description="매출액 (천원)")
    fn2_5: float = Field(..., description="영업이익 당기 (천원)")
    fn2_5_1: float = Field(..., description="영업이익 전기 (천원)")
    fn2_10: float = Field(..., description="당기순이익 당기 (천원)")
    fn2_10_1: float = Field(..., description="당기순이익 전기 (천원)")
    fn2_3: float = Field(..., ge=0, description="판매비와관리비 (천원)")

    # 현금흐름 (1개)
    fn3_2: float = Field(..., description="영업활동현금흐름 (천원)")

    # 기업정보 (2개)
    empe_cnt: float = Field(..., ge=0, description="종업원수 (명)")
    wg_gb: str = Field(..., description="외감여부 (Y/N)")

    # 간소화 연체/신용 정보 (3개)
    has_delinquency: bool = Field(False, description="현재 연체 여부")
    delinquency_days: float = Field(0, ge=0, description="최장 연체일수 (없으면 0)")
    has_tax_delinquency: bool = Field(False, description="세금 체납 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "fn1_13": 150000,
                "fn1_1": 50000,
                "fn1_4": 20000,
                "fn1_19": 80000,
                "fn1_24": 70000,
                "fn1_14": 30000,
                "fn1_15": 10000,
                "fn2_1": 200000,
                "fn2_5": 15000,
                "fn2_5_1": 12000,
                "fn2_10": 10000,
                "fn2_10_1": 8000,
                "fn2_3": 25000,
                "fn3_2": 12000,
                "empe_cnt": 50,
                "wg_gb": "Y",
                "has_delinquency": False,
                "delinquency_days": 0,
                "has_tax_delinquency": False
            }
        }


# Phase 4: 엑셀 업로드 모델 입력 (37개)
class ExcelPredictionRequest(BaseModel):
    """엑셀 업로드 예측 요청 (37개 입력)"""

    # 재무상태표 (12개)
    fn1_13: float = Field(..., ge=0, description="자산총계(당기) (천원)")
    fn1_1: float = Field(..., ge=0, description="유동자산(당기) (천원)")
    fn1_4: float = Field(..., ge=0, description="재고자산 (천원)")
    fn1_11: float = Field(..., ge=0, description="매출채권 (천원)")
    fn1_19: float = Field(..., ge=0, description="부채총계 (천원)")
    fn1_24: float = Field(..., gt=0, description="자본총계 (천원)")
    fn1_14: float = Field(..., ge=0, description="유동부채 (천원)")
    fn1_15: float = Field(..., ge=0, description="단기차입금 (천원)")
    fn1_16: float = Field(..., ge=0, description="차입금 (천원)")
    fn1_유형자산: float = Field(..., ge=0, description="유형자산(당기) (천원)")
    fn1_매입채무: float = Field(..., ge=0, description="매입채무 (천원)")
    fn3_적립금: float = Field(..., ge=0, description="적립금 (천원)")

    # 손익계산서 (8개)
    fn2_1: float = Field(..., description="매출액(당기) (천원)")
    fn2_2: float = Field(..., ge=0, description="매출원가 (천원)")
    fn2_2_1: float = Field(..., description="매출총이익 (천원)")
    fn2_3: float = Field(..., ge=0, description="판매비와관리비 (천원)")
    fn2_5: float = Field(..., description="영업이익(당기) (천원)")
    fn2_5_1: float = Field(..., description="영업이익(전기) (천원)")
    fn2_10: float = Field(..., description="당기순이익(당기) (천원)")
    fn2_10_1: float = Field(..., description="당기순이익(전기) (천원)")

    # 현금흐름/기타 (6개)
    fn3_1: float = Field(..., description="현금흐름 (천원)")
    fn3_2: float = Field(..., description="영업활동현금흐름 (천원)")
    fn3_7: float = Field(..., description="EBIT (천원)")
    fn3_8: float = Field(..., description="EBITDA(당기) (천원)")
    fn3_11_1: float = Field(..., description="순차입금 (천원)")
    fn2_4: float = Field(0, ge=0, description="이자비용 (천원) - 선택적")

    # 전년도 데이터 (4개) - 성장성 계산용
    fn1_13_전기: float = Field(..., ge=0, description="자산총계(전기) (천원)")
    fn2_1_전기: float = Field(..., description="매출액(전기) (천원)")
    fn1_1_전기: float = Field(..., ge=0, description="유동자산(전기) (천원)")
    fn3_8_전기: float = Field(..., description="EBITDA(전기) (천원)")

    # 기업정보 (2개)
    empe_cnt: float = Field(..., ge=0, description="종업원수 (명)")
    wg_gb: str = Field(..., description="외감여부 (Y/N)")

    # 연체정보 (7개)
    da0d00029: float = Field(0, ge=0, description="연체과목수(1년내발생)")
    da0d00026: float = Field(0, ge=0, description="연체과목수(1년내유지)")
    da0d00035_1: float = Field(0, ge=0, description="최장연체일수(1년)")
    da0d00035_2: float = Field(0, ge=0, description="최장연체일수(기타)")
    da0d00033_1: float = Field(0, ge=0, description="최장연체일수(3개월)")
    db0d00006: float = Field(0, ge=0, description="30일이상연체(미해제)")
    d2b000002: float = Field(999999999, description="공공정보 (세금체납) - 999999999는 체납 없음")

    class Config:
        json_schema_extra = {
            "example": {
                # 재무상태표 (12개)
                "fn1_13": 100000,
                "fn1_1": 60000,
                "fn1_4": 15000,
                "fn1_11": 20000,
                "fn1_19": 60000,
                "fn1_24": 40000,
                "fn1_14": 30000,
                "fn1_15": 10000,
                "fn1_16": 25000,
                "fn1_유형자산": 35000,
                "fn1_매입채무": 12000,
                "fn3_적립금": 8000,
                # 손익계산서 (8개)
                "fn2_1": 500000,
                "fn2_2": 350000,
                "fn2_2_1": 150000,
                "fn2_3": 80000,
                "fn2_5": 30000,
                "fn2_5_1": 25000,
                "fn2_10": 20000,
                "fn2_10_1": 15000,
                # 현금흐름/기타 (6개)
                "fn3_1": 22000,
                "fn3_2": 25000,
                "fn3_7": 32000,
                "fn3_8": 38000,
                "fn3_11_1": 15000,
                "fn2_4": 2000,
                # 전년도 데이터 (4개)
                "fn1_13_전기": 90000,
                "fn2_1_전기": 450000,
                "fn1_1_전기": 55000,
                "fn3_8_전기": 35000,
                # 기업정보 (2개)
                "empe_cnt": 50,
                "wg_gb": "Y",
                # 연체정보 (7개 - 정상 기업 예시)
                "da0d00029": 0,
                "da0d00026": 0,
                "da0d00035_1": 0,
                "da0d00035_2": 0,
                "da0d00033_1": 0,
                "db0d00006": 0,
                "d2b000002": 999999999
            }
        }


class ExcelPredictionResponse(BaseModel):
    """엑셀 업로드 예측 결과"""
    success: bool
    n_features: int = Field(..., description="생성된 피처 개수")
    prediction: Dict = Field(..., description="부도 예측 결과")
    shap_values: Optional[Dict] = Field(None, description="SHAP 설명")
    clustering_features: Optional[Dict] = Field(None, description="클러스터링용 70개 피처")
    derived_ratios: Optional[Dict] = Field(None, description="자동 계산된 재무비율")
    message: Optional[str] = None
