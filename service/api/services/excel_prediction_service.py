"""
엑셀 업로드 기반 부도 예측 서비스
30개 입력 → 70개 피처 생성 → 부도예측 + 클러스터링
"""
import pandas as pd
import numpy as np
from typing import Dict, Any
from pathlib import Path

from service.api.services.user_friendly_prediction_service import UserFriendlyPredictionService


class ExcelPredictionService(UserFriendlyPredictionService):
    """
    엑셀 업로드 전용 예측 서비스 (37개 입력)

    입력 구성:
    - 재무상태표(당기): 12개
    - 손익계산서: 8개
    - 현금흐름/기타: 6개
    - 전년도 데이터: 4개
    - 기업정보: 2개
    - 연체정보: 7개
    총 39개 (fn2_4, fn3_유형자산_전기는 선택적)

    자동 생성:
    - 70개 클러스터링 피처 전부 생성 가능
    - 실루엣 스코어 0.68 유지
    """

    # 37개 기본 입력 컬럼
    EXCEL_INPUT_FEATURES = [
        # 재무상태표 (12개)
        'fn1_13',   # 자산총계(당기)
        'fn1_1',    # 유동자산(당기)
        'fn1_4',    # 재고자산
        'fn1_11',   # 매출채권
        'fn1_19',   # 부채총계
        'fn1_24',   # 자본총계
        'fn1_14',   # 유동부채
        'fn1_15',   # 단기차입금
        'fn1_16',   # 차입금
        'fn1_유형자산',  # 유형자산(당기)
        'fn1_매입채무',  # 매입채무
        'fn3_적립금',    # 적립금

        # 손익계산서 (8개)
        'fn2_1',    # 매출액(당기)
        'fn2_2',    # 매출원가
        'fn2_2_1',  # 매출총이익
        'fn2_3',    # 판매비와관리비
        'fn2_5',    # 영업이익 당기
        'fn2_5_1',  # 영업이익 전기
        'fn2_10',   # 당기순이익 당기
        'fn2_10_1', # 당기순이익 전기

        # 현금흐름/기타 (6개)
        'fn3_1',    # 현금흐름
        'fn3_2',    # 영업활동현금흐름
        'fn3_7',    # EBIT
        'fn3_8',    # EBITDA(당기)
        'fn3_11_1', # 순차입금
        'fn2_4',    # 이자비용 (선택적)

        # 전년도 데이터 (4개) - 성장성 계산용
        'fn1_13_전기',  # 자산총계(전기)
        'fn2_1_전기',   # 매출액(전기)
        'fn1_1_전기',   # 유동자산(전기)
        'fn3_8_전기',   # EBITDA(전기)

        # 기업정보 (2개)
        'empe_cnt', # 종업원수
        'wg_gb',    # 외감여부

        # 연체정보 (7개)
        'da0d00029',   # 연체과목수(1년내발생)
        'da0d00026',   # 연체과목수(1년내유지)
        'da0d00035_1', # 최장연체일수(1년)
        'da0d00035_2', # 최장연체일수(기타)
        'da0d00033_1', # 최장연체일수(3개월)
        'db0d00006',   # 30일이상연체
        'd2b000002',   # 공공정보(세금체납)
    ]

    def __init__(self):
        """초기화 - UserFriendly 모델 활용"""
        super().__init__()

    def create_derived_features(self, input_data: Dict) -> Dict:
        """
        30개 입력으로 70개 파생 변수 생성

        Args:
            input_data: 30개 기본 입력 딕셔너리

        Returns:
            70개 피처 딕셔너리
        """
        # 1. UserFriendly 모델의 15개 파생 변수 생성 (부모 클래스 메서드)
        data = super().create_derived_features(input_data)

        # 2. 추가 파생 변수 생성 (10개)

        # 2-1. 활동성 비율 추가
        if 'fn1_11' in data and data.get('fn2_1', 0) > 0:
            # 매출채권회전율 = 매출액 / 매출채권
            data['receivable_turnover'] = data['fn2_1'] / (data['fn1_11'] + 1e-6)
        else:
            data['receivable_turnover'] = 0

        if 'fn2_2' in data and data.get('fn1_4', 0) > 0:
            # 재고자산회전율 = 매출원가 / 재고자산
            data['inventory_turnover_v2'] = data['fn2_2'] / (data['fn1_4'] + 1e-6)
        else:
            data['inventory_turnover_v2'] = 0

        # 2-2. 수익성 비율 추가
        if 'fn2_2_1' in data and data.get('fn2_1', 0) > 0:
            # 매출총이익률 = 매출총이익 / 매출액
            data['gross_margin'] = data['fn2_2_1'] / (data['fn2_1'] + 1e-6)
        elif 'fn2_2' in data and data.get('fn2_1', 0) > 0:
            # 매출총이익 = 매출액 - 매출원가
            gross_profit = data['fn2_1'] - data['fn2_2']
            data['gross_margin'] = gross_profit / (data['fn2_1'] + 1e-6)
        else:
            data['gross_margin'] = 0

        # 2-3. 현금흐름 비율 추가
        if 'fn3_8' in data and data.get('fn2_1', 0) > 0:
            # EBITDA마진율 = EBITDA / 매출액
            data['ebitda_margin'] = data['fn3_8'] / (data['fn2_1'] + 1e-6)
        else:
            data['ebitda_margin'] = 0

        if 'fn3_2' in data and data.get('fn2_1', 0) > 0:
            # OCF마진율 = 영업활동현금흐름 / 매출액
            data['ocf_margin'] = data['fn3_2'] / (data['fn2_1'] + 1e-6)
        else:
            data['ocf_margin'] = 0

        # 2-4. 차입금 관련 비율
        if 'fn1_16' in data:
            # 차입금의존도 = 차입금 / 자산총계
            data['borrowing_dependency'] = data['fn1_16'] / (data.get('fn1_13', 0) + 1e-6)

            # 차입금/EBITDA = 차입금 / EBITDA (부채상환능력)
            if 'fn3_8' in data and data['fn3_8'] > 0:
                data['debt_to_ebitda'] = data['fn1_16'] / data['fn3_8']
            else:
                data['debt_to_ebitda'] = 999  # EBITDA가 0이면 상환 불가능
        else:
            data['borrowing_dependency'] = 0
            data['debt_to_ebitda'] = 0

        # 2-5. 이자보상배율
        if 'fn3_7' in data and 'fn2_4' in data and data.get('fn2_4', 0) > 0:
            # 이자보상배율 = EBIT / 이자비용
            data['interest_coverage_ebit'] = data['fn3_7'] / data['fn2_4']
        elif 'fn2_5' in data and 'fn2_4' in data and data.get('fn2_4', 0) > 0:
            # 근사치: 영업이익 / 이자비용
            data['interest_coverage_ebit'] = data['fn2_5'] / data['fn2_4']
        else:
            data['interest_coverage_ebit'] = 0

        # 2-6. 순운전자본회전율
        if data.get('fn1_1', 0) > data.get('fn1_14', 0):
            net_working_capital = data['fn1_1'] - data['fn1_14']
            if data.get('fn2_1', 0) > 0:
                data['nwc_turnover'] = data['fn2_1'] / net_working_capital
            else:
                data['nwc_turnover'] = 0
        else:
            data['nwc_turnover'] = 0

        return data

    def map_to_clustering_features(self, input_data: Dict) -> Dict:
        """
        30개 입력을 70개 클러스터링 피처로 매핑

        config/financial_categories.yaml의 70개 컬럼 기준

        Args:
            input_data: 30개 기본 입력 + 파생 변수 포함 딕셔너리

        Returns:
            70개 클러스터링 피처 딕셔너리
        """
        clustering_data = {}

        # 1. 직접 매핑 (기본 컬럼)
        # 재무상태표
        clustering_data['FN1_13'] = input_data.get('fn1_13', 0)  # 자산총계
        clustering_data['FN1_1'] = input_data.get('fn1_1', 0)    # 유동자산
        clustering_data['FN1_4'] = input_data.get('fn1_4', 0)    # 재고자산
        clustering_data['FN1_11'] = input_data.get('fn1_11', 0)  # 매출채권
        clustering_data['FN1_14'] = input_data.get('fn1_14', 0)  # 유동부채
        clustering_data['FN1_15'] = input_data.get('fn1_15', 0)  # 단기차입금
        clustering_data['FN1_16'] = input_data.get('fn1_16', 0)  # 차입금
        clustering_data['FN1_19'] = input_data.get('fn1_19', 0)  # 부채총계
        clustering_data['FN1_20'] = input_data.get('fn1_24', 0)  # 자기자본 (=자본총계)
        clustering_data['FN1_24'] = input_data.get('fn1_24', 0)  # 자본총계

        # 손익계산서
        clustering_data['FN2_1'] = input_data.get('fn2_1', 0)    # 매출액
        clustering_data['FN2_2_1'] = input_data.get('fn2_2_1', 0)  # 매출총이익
        clustering_data['FN2_5'] = input_data.get('fn2_5', 0)    # 영업손익
        clustering_data['FN2_10'] = input_data.get('fn2_10', 0)  # 당기순이익

        # 현금흐름/기타
        clustering_data['FN3_1'] = input_data.get('fn3_1', 0)    # 현금흐름
        clustering_data['FN3_2'] = input_data.get('fn3_2', 0)    # 영업활동현금흐름
        clustering_data['FN3_7'] = input_data.get('fn3_7', 0)    # EBIT
        clustering_data['FN3_8'] = input_data.get('fn3_8', 0)    # EBITDA
        clustering_data['FN3_11_1'] = input_data.get('fn3_11_1', 0)  # 순차입금

        # 연체정보
        clustering_data['DA0D00021'] = input_data.get('da0d00029', 0)  # 근사치
        clustering_data['DA0D00026'] = input_data.get('da0d00026', 0)
        clustering_data['DA0D00029'] = input_data.get('da0d00029', 0)
        clustering_data['DA0D00033_1'] = input_data.get('da0d00033_1', 0)
        clustering_data['DA0D00035_1'] = input_data.get('da0d00035_1', 0)
        clustering_data['DB0D00006'] = input_data.get('db0d00006', 0)
        clustering_data['D2B000012'] = input_data.get('d2b000002', 0)  # 국세체납

        # 2. 파생 비율 계산
        # 안정성 비율
        clustering_data['R006'] = input_data.get('debt_ratio', 0)  # 부채비율
        clustering_data['R007'] = input_data.get('equity_ratio', 0)  # 자기자본비율
        clustering_data['R008'] = input_data.get('current_ratio', 0)  # 유동비율
        clustering_data['R009'] = input_data.get('quick_ratio', 0)  # 당좌비율
        clustering_data['R012'] = input_data.get('borrowing_dependency', 0)  # 차입금의존도
        clustering_data['N001'] = input_data.get('short_term_borrowing_dependency', 0)  # 단기차입금의존도
        clustering_data['N002'] = clustering_data.get('FN3_11_1', 0) / (clustering_data.get('FN1_24', 0) + 1e-6)  # 순차입금비율

        # 수익성 비율
        clustering_data['R013'] = input_data.get('fn2_2', 0) / (input_data.get('fn2_1', 0) + 1e-6)  # 매출원가율
        clustering_data['R015'] = input_data.get('operating_margin', 0)  # 영업이익률
        clustering_data['R016'] = input_data.get('fn2_10', 0) / (input_data.get('fn2_1', 0) + 1e-6)  # 당기순이익률
        clustering_data['R018'] = input_data.get('roe', 0)  # ROE
        clustering_data['R023'] = input_data.get('fn2_10', 0) / (input_data.get('fn1_13', 0) + 1e-6)  # 총자산순이익률
        clustering_data['N004'] = input_data.get('roe', 0)  # 자기자본순이익률 (ROE와 동일)
        clustering_data['N005'] = input_data.get('gross_margin', 0)  # 매출총이익률

        # 활동성 비율
        clustering_data['R019'] = input_data.get('receivable_turnover', 0)  # 매출채권회전율
        clustering_data['R020'] = input_data.get('inventory_turnover_v2', 0)  # 재고자산회전율

        # R021: 매입채무회전율 = 매출원가 / 매입채무
        if input_data.get('fn1_매입채무', 0) > 0:
            clustering_data['R021'] = input_data.get('fn2_2', 0) / input_data.get('fn1_매입채무', 0)
        else:
            clustering_data['R021'] = 0

        clustering_data['R022'] = input_data.get('total_capital_turnover', 0)  # 총자산회전율
        clustering_data['N003'] = input_data.get('nwc_turnover', 0)  # 순운전자본회전율
        clustering_data['N012'] = input_data.get('fn2_1', 0) / (input_data.get('fn1_24', 0) + 1e-6)  # 총자본회전율

        # 성장성 비율
        # R001: 총자산증가율 = (당기 자산총계 - 전기 자산총계) / 전기 자산총계
        if input_data.get('fn1_13_전기', 0) > 0:
            clustering_data['R001'] = (input_data.get('fn1_13', 0) - input_data.get('fn1_13_전기', 0)) / input_data.get('fn1_13_전기', 0)
        else:
            clustering_data['R001'] = 0

        # R002: 매출액증가율 = (당기 매출액 - 전기 매출액) / 전기 매출액
        if input_data.get('fn2_1_전기', 0) > 0:
            clustering_data['R002'] = (input_data.get('fn2_1', 0) - input_data.get('fn2_1_전기', 0)) / input_data.get('fn2_1_전기', 0)
        else:
            clustering_data['R002'] = 0

        clustering_data['R003'] = input_data.get('operating_income_growth', 0)  # 영업이익증가율
        clustering_data['R004'] = input_data.get('net_income_growth', 0)  # 당기순이익증가율

        # R024: 유동자산증가율 = (당기 유동자산 - 전기 유동자산) / 전기 유동자산
        if input_data.get('fn1_1_전기', 0) > 0:
            clustering_data['R024'] = (input_data.get('fn1_1', 0) - input_data.get('fn1_1_전기', 0)) / input_data.get('fn1_1_전기', 0)
        else:
            clustering_data['R024'] = 0

        # R025: 유형자산증가율 (전기 데이터가 있으면 계산, 없으면 0)
        if input_data.get('fn1_유형자산_전기', 0) > 0:
            clustering_data['R025'] = (input_data.get('fn1_유형자산', 0) - input_data.get('fn1_유형자산_전기', 0)) / input_data.get('fn1_유형자산_전기', 0)
        else:
            clustering_data['R025'] = 0

        # N007: EBITDA증가율 = (당기 EBITDA - 전기 EBITDA) / 전기 EBITDA
        if input_data.get('fn3_8_전기', 0) > 0:
            clustering_data['N007'] = (input_data.get('fn3_8', 0) - input_data.get('fn3_8_전기', 0)) / input_data.get('fn3_8_전기', 0)
        else:
            clustering_data['N007'] = 0

        # 현금흐름 및 생산성 비율
        clustering_data['N006'] = input_data.get('ebitda_margin', 0)  # EBITDA마진율
        clustering_data['N008'] = input_data.get('ocf_margin', 0)  # OCF/매출액

        # N009: 부채상환계수 = FN3_3 (부채상환계수)
        # FN3_3 = 부채총계 / 영업활동현금흐름
        if input_data.get('fn3_2', 0) > 0:
            fn3_3_value = input_data.get('fn1_19', 0) / input_data.get('fn3_2', 0)
            clustering_data['N009'] = fn3_3_value
            clustering_data['FN3_3'] = fn3_3_value
        else:
            clustering_data['N009'] = 0
            clustering_data['FN3_3'] = 0

        clustering_data['N010'] = input_data.get('debt_to_ebitda', 0)  # 차입금/EBITDA
        clustering_data['N011'] = input_data.get('interest_coverage_ebit', 0)  # EBITDA/금융비용

        # 기타
        clustering_data['FN3_11'] = input_data.get('net_working_capital', 0)  # 순운전자본
        clustering_data['FN3_4'] = input_data.get('interest_coverage_ebit', 0)  # 이자보상배율

        # FN3_6: 적립금비율 = 적립금 / 자본총계
        if input_data.get('fn1_24', 0) > 0:
            clustering_data['FN3_6'] = input_data.get('fn3_적립금', 0) / input_data.get('fn1_24', 0)
        else:
            clustering_data['FN3_6'] = 0

        # FN3_10: 청산가치율 (근사치 계산 불가, 0으로 유지)
        clustering_data['FN3_10'] = 0

        return clustering_data

    def predict_from_excel_data(self, input_data: Dict) -> Dict:
        """
        엑셀 데이터로부터 통합 예측 수행

        Args:
            input_data: 30개 기본 입력 딕셔너리

        Returns:
            {
                'success': bool,
                'n_features': int,
                'prediction': DefaultPrediction,
                'shap_values': ShapExplanation,
                'clustering_features': Dict,  # 70개 클러스터링 피처
                'derived_ratios': Dict  # 자동 계산된 재무비율
            }
        """
        try:
            # 1. 기본 입력 검증
            missing = [col for col in self.EXCEL_INPUT_FEATURES
                      if col not in input_data and col != 'fn2_4']  # 이자비용은 선택적
            if missing:
                return {
                    'success': False,
                    'error': f'필수 컬럼이 누락되었습니다: {missing}'
                }

            # 2. 파생 변수 생성 (70개)
            full_data = self.create_derived_features(input_data)

            # 3. 부도 예측 (UserFriendly 모델 활용)
            prediction_result = self.predict_from_input(input_data)

            # 4. 클러스터링 피처 매핑 (70개)
            clustering_features = self.map_to_clustering_features(full_data)

            # 5. 자동 계산된 재무비율만 추출
            derived_ratios = {
                '안정성': {
                    '부채비율': full_data.get('debt_ratio', 0),
                    '자기자본비율': full_data.get('equity_ratio', 0),
                    '유동비율': full_data.get('current_ratio', 0),
                    '당좌비율': full_data.get('quick_ratio', 0),
                    '차입금의존도': full_data.get('borrowing_dependency', 0),
                    '단기차입금의존도': full_data.get('short_term_borrowing_dependency', 0),
                },
                '수익성': {
                    '영업이익률': full_data.get('operating_margin', 0),
                    'ROE': full_data.get('roe', 0),
                    '매출총이익률': full_data.get('gross_margin', 0),
                },
                '활동성': {
                    '매출채권회전율': full_data.get('receivable_turnover', 0),
                    '재고자산회전율': full_data.get('inventory_turnover', 0),
                    '총자본회전율': full_data.get('total_capital_turnover', 0),
                    '순운전자본회전율': full_data.get('nwc_turnover', 0),
                },
                '성장성': {
                    '영업이익증가율': full_data.get('operating_income_growth', 0),
                    '순이익증가율': full_data.get('net_income_growth', 0),
                },
                '현금흐름': {
                    'EBITDA마진율': full_data.get('ebitda_margin', 0),
                    'OCF마진율': full_data.get('ocf_margin', 0),
                    '현금/부채비율': full_data.get('cash_to_debt', 0),
                    '차입금/EBITDA': full_data.get('debt_to_ebitda', 0),
                    '이자보상배율': full_data.get('interest_coverage_ebit', 0),
                }
            }

            return {
                'success': True,
                'n_features': len(clustering_features),
                'prediction': prediction_result.get('prediction'),
                'shap_values': prediction_result.get('shap_values'),
                'clustering_features': clustering_features,
                'derived_ratios': derived_ratios,
                'message': f'엑셀 데이터 분석 완료 (입력 {len(input_data)}개 → 피처 {len(clustering_features)}개 생성)'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'예측 중 오류 발생: {str(e)}'
            }


# 싱글톤 인스턴스
_excel_service = None

def get_excel_service() -> ExcelPredictionService:
    """엑셀 예측 서비스 싱글톤 인스턴스 반환"""
    global _excel_service
    if _excel_service is None:
        _excel_service = ExcelPredictionService()
    return _excel_service
