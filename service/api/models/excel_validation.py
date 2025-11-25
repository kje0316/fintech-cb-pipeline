"""
엑셀 데이터 검증 모델 (Pydantic v2)

37개 필수 컬럼에 대한 강력한 타입 체크 및 비즈니스 규칙 검증
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from decimal import Decimal


class ExcelInputValidation(BaseModel):
    """
    37개 필수 컬럼 검증

    비즈니스 규칙:
    - 금액은 음수 불가 (일부 손익 항목 제외)
    - 자산 = 부채 + 자본 (오차 5% 허용)
    - 매출총이익 = 매출액 - 매출원가
    - 영업이익 = 매출총이익 - 판관비
    """

    # ========================================================================
    # 재무상태표 (12개)
    # ========================================================================

    fn1_13: float = Field(..., description="자산총계(당기)", ge=0)
    fn1_1: float = Field(..., description="유동자산(당기)", ge=0)
    fn1_4: float = Field(0.0, description="재고자산", ge=0)
    fn1_11: float = Field(0.0, description="매출채권", ge=0)
    fn1_19: float = Field(..., description="부채총계", ge=0)
    fn1_24: float = Field(..., description="자본총계")  # 음수 가능 (자본잠식)
    fn1_14: float = Field(0.0, description="유동부채", ge=0)
    fn1_15: float = Field(0.0, description="단기차입금", ge=0)
    fn1_16: float = Field(0.0, description="차입금", ge=0)
    fn1_유형자산: float = Field(0.0, description="유형자산(당기)", ge=0)
    fn1_매입채무: float = Field(0.0, description="매입채무", ge=0)
    fn3_적립금: float = Field(0.0, description="적립금", ge=0)

    # ========================================================================
    # 손익계산서 (8개)
    # ========================================================================

    fn2_1: float = Field(..., description="매출액(당기)", ge=0)
    fn2_2: float = Field(0.0, description="매출원가", ge=0)
    fn2_2_1: float = Field(..., description="매출총이익")  # 음수 가능
    fn2_3: float = Field(0.0, description="판매비와관리비", ge=0)
    fn2_5: float = Field(..., description="영업이익 당기")  # 음수 가능
    fn2_5_1: float = Field(0.0, description="영업이익 전기")  # 음수 가능
    fn2_10: float = Field(..., description="당기순이익 당기")  # 음수 가능
    fn2_10_1: float = Field(0.0, description="당기순이익 전기")  # 음수 가능

    # ========================================================================
    # 현금흐름/기타 (6개)
    # ========================================================================

    fn3_1: float = Field(0.0, description="현금흐름")  # 음수 가능
    fn3_2: float = Field(0.0, description="영업활동현금흐름")  # 음수 가능
    fn3_7: float = Field(0.0, description="EBIT")  # 음수 가능
    fn3_8: float = Field(0.0, description="EBITDA(당기)")  # 음수 가능
    fn3_11_1: float = Field(0.0, description="순차입금")  # 음수 가능
    fn2_4: float = Field(0.0, description="이자비용", ge=0)

    # ========================================================================
    # 전년도 데이터 (4개)
    # ========================================================================

    fn1_13_전기: float = Field(0.0, description="자산총계(전기)", ge=0)
    fn2_1_전기: float = Field(0.0, description="매출액(전기)", ge=0)
    fn1_1_전기: float = Field(0.0, description="유동자산(전기)", ge=0)
    fn3_8_전기: float = Field(0.0, description="EBITDA(전기)")  # 음수 가능

    # ========================================================================
    # 기업정보 (2개)
    # ========================================================================

    empe_cnt: int = Field(0, description="종업원수", ge=0)
    wg_gb: Literal['Y', 'N', 1, 0] = Field('N', description="외감여부")

    # ========================================================================
    # 연체정보 (7개)
    # ========================================================================

    da0d00029: float = Field(0.0, description="연체과목수(1년내발생)", ge=0)
    da0d00026: float = Field(0.0, description="연체과목수(1년내유지)", ge=0)
    da0d00035_1: float = Field(0.0, description="최장연체일수(1년)", ge=0)
    da0d00035_2: float = Field(0.0, description="최장연체일수(기타)", ge=0)
    da0d00033_1: float = Field(0.0, description="최장연체일수(3개월)", ge=0)
    db0d00006: float = Field(0.0, description="부도/화의/워크아웃정보", ge=0)
    d2b000002: float = Field(0.0, description="연체정보", ge=0)

    # ========================================================================
    # Field Validators (개별 필드 검증)
    # ========================================================================

    @field_validator('wg_gb')
    @classmethod
    def validate_wg_gb(cls, v):
        """외감여부를 Y/N 또는 1/0 → 1/0으로 통일"""
        if isinstance(v, str):
            v = v.upper()
            if v == 'Y':
                return 1
            elif v == 'N':
                return 0
            else:
                raise ValueError("wg_gb는 'Y', 'N', 0, 1 중 하나여야 합니다")
        elif v in [0, 1]:
            return v
        else:
            raise ValueError("wg_gb는 'Y', 'N', 0, 1 중 하나여야 합니다")

    @field_validator('fn1_13', 'fn2_1')
    @classmethod
    def validate_required_positive(cls, v, info):
        """필수 항목은 0보다 커야 함"""
        if v <= 0:
            raise ValueError(f"{info.field_name}은(는) 0보다 큰 값이어야 합니다 (입력값: {v})")
        return v

    # ========================================================================
    # Model Validators (전체 모델 검증 - 비즈니스 규칙)
    # ========================================================================

    @model_validator(mode='after')
    def validate_balance_sheet(self):
        """재무상태표 항등식: 자산 = 부채 + 자본 (오차 5% 허용)"""
        assets = self.fn1_13
        liabilities = self.fn1_19
        equity = self.fn1_24

        expected_assets = liabilities + equity

        if assets > 0:
            error_rate = abs(assets - expected_assets) / assets
            if error_rate > 0.05:  # 5% 오차 허용
                raise ValueError(
                    f"재무상태표 검증 실패: 자산({assets:,.0f}) ≠ 부채({liabilities:,.0f}) + 자본({equity:,.0f}) "
                    f"(오차율: {error_rate*100:.1f}%, 허용: 5%)"
                )

        return self

    @model_validator(mode='after')
    def validate_income_statement(self):
        """손익계산서 검증: 매출총이익 = 매출액 - 매출원가 (오차 허용)"""
        revenue = self.fn2_1
        cogs = self.fn2_2
        gross_profit = self.fn2_2_1

        expected_gross_profit = revenue - cogs

        # 5% 오차 허용
        if revenue > 0:
            error = abs(gross_profit - expected_gross_profit)
            error_rate = error / revenue

            if error_rate > 0.05:
                raise ValueError(
                    f"매출총이익 검증 실패: 입력값({gross_profit:,.0f}) ≠ 매출액({revenue:,.0f}) - 매출원가({cogs:,.0f}) = {expected_gross_profit:,.0f} "
                    f"(오차율: {error_rate*100:.1f}%, 허용: 5%)"
                )

        return self

    @model_validator(mode='after')
    def validate_operating_income(self):
        """영업이익 검증: 영업이익 ≈ 매출총이익 - 판관비 (근사치)"""
        gross_profit = self.fn2_2_1
        sga = self.fn2_3
        operating_income = self.fn2_5

        expected_operating_income = gross_profit - sga

        # 영업이익은 다른 영업외 손익이 포함될 수 있으므로 경고만
        if self.fn2_1 > 0:
            error = abs(operating_income - expected_operating_income)
            error_rate = error / self.fn2_1

            if error_rate > 0.10:  # 10% 오차 경고
                import warnings
                warnings.warn(
                    f"영업이익 불일치 경고: 입력값({operating_income:,.0f}) vs 예상값({expected_operating_income:,.0f}) "
                    f"(오차율: {error_rate*100:.1f}%)"
                )

        return self

    @model_validator(mode='after')
    def validate_current_ratio(self):
        """유동자산 ≤ 자산총계"""
        if self.fn1_1 > self.fn1_13 * 1.01:  # 1% 오차 허용
            raise ValueError(
                f"유동자산({self.fn1_1:,.0f})이 자산총계({self.fn1_13:,.0f})보다 클 수 없습니다"
            )
        return self

    @model_validator(mode='after')
    def validate_current_liabilities(self):
        """유동부채 ≤ 부채총계"""
        if self.fn1_14 > self.fn1_19 * 1.01:  # 1% 오차 허용
            raise ValueError(
                f"유동부채({self.fn1_14:,.0f})가 부채총계({self.fn1_19:,.0f})보다 클 수 없습니다"
            )
        return self

    @model_validator(mode='after')
    def validate_inventory(self):
        """재고자산 ≤ 유동자산"""
        if self.fn1_4 > self.fn1_1 * 1.01:  # 1% 오차 허용
            raise ValueError(
                f"재고자산({self.fn1_4:,.0f})이 유동자산({self.fn1_1:,.0f})보다 클 수 없습니다"
            )
        return self

    @model_validator(mode='after')
    def validate_short_term_debt(self):
        """단기차입금 ≤ 유동부채"""
        if self.fn1_15 > self.fn1_14 * 1.01 and self.fn1_14 > 0:  # 1% 오차 허용
            raise ValueError(
                f"단기차입금({self.fn1_15:,.0f})이 유동부채({self.fn1_14:,.0f})보다 클 수 없습니다"
            )
        return self

    @model_validator(mode='after')
    def validate_reasonable_ranges(self):
        """합리적 범위 검증 (비정상적으로 큰 값 감지)"""
        # 자산총계가 100조 이상이면 경고 (재벌급 대기업)
        if self.fn1_13 > 100_000_000_000:
            import warnings
            warnings.warn(f"자산총계가 매우 큽니다: {self.fn1_13:,.0f}천원 (확인 필요)")

        # 종업원수가 10만명 이상이면 경고
        if self.empe_cnt > 100_000:
            import warnings
            warnings.warn(f"종업원수가 매우 많습니다: {self.empe_cnt:,}명 (확인 필요)")

        return self

    class Config:
        str_strip_whitespace = True
        json_schema_extra = {
            "example": {
                "fn1_13": 150000000,
                "fn1_1": 50000000,
                "fn2_1": 200000000,
                "fn1_19": 80000000,
                "fn1_24": 70000000,
                "fn2_2_1": 50000000,
                "fn2_5": 15000000,
                "fn2_10": 10000000,
                "wg_gb": "Y",
                "empe_cnt": 50
            }
        }


class ExcelValidationResult(BaseModel):
    """검증 결과"""
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    validated_data: Optional[dict] = None
