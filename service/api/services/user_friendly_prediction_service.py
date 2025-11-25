"""
사용자 친화 모델 예측 서비스 (19개 입력)
- 재무제표 중심 (16개) + 간소화 연체 정보 (3개)
- 34개 피처 사용 (15개 파생 변수 자동 생성)
"""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from typing import Dict, Tuple
from sklearn.preprocessing import LabelEncoder

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent.parent


class UserFriendlyPredictionService:
    """사용자 친화 모델 예측 서비스"""

    def __init__(self):
        """초기화 - 사용자 친화 모델 및 설정 로드"""
        self.project_root = project_root
        self.model_path = self.project_root / "ml/models/user_friendly_model_best.pkl"
        self.scaler_path = self.project_root / "ml/models/user_friendly_scaler.pkl"
        self.features_path = self.project_root / "ml/models/user_friendly_features.json"

        # 모델 및 스케일러 로드
        self._load_model()
        self._load_scaler()
        self._load_features()

    def _load_model(self):
        """모델 로드"""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"✓ 사용자 친화 모델 로드 완료: {self.model_path}")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"사용자 친화 모델 파일을 찾을 수 없습니다: {self.model_path}\n"
                "먼저 모델을 학습하세요: python ml/scripts/06_train_user_friendly_model.py"
            )

    def _load_scaler(self):
        """스케일러 로드"""
        try:
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            print(f"✓ 사용자 친화 스케일러 로드 완료: {self.scaler_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"스케일러 파일을 찾을 수 없습니다: {self.scaler_path}")

    def _load_features(self):
        """피처 정보 로드"""
        try:
            with open(self.features_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.base_input_features = data['base_input_features']
            self.derived_features = data['derived_features']
            self.final_features = data['final_features']
            print(f"✓ 피처 정보 로드 완료: {len(self.final_features)}개 피처")
        except FileNotFoundError:
            raise FileNotFoundError(f"피처 정보 파일을 찾을 수 없습니다: {self.features_path}")

    def create_derived_features(self, input_data: Dict) -> Dict:
        """
        파생 변수 생성

        Args:
            input_data: 사용자 입력 데이터 (19개)

        Returns:
            파생 변수가 추가된 데이터
        """
        data = input_data.copy()

        # 안정성 비율 (4개)
        if 'fn1_19' in data and 'fn1_24' in data:
            data['debt_ratio'] = data['fn1_19'] / (data['fn1_24'] + 1e-6)
            data['equity_ratio'] = data['fn1_24'] / (data.get('fn1_13', 0) + 1e-6)
            data['debt_to_equity'] = data['fn1_19'] / (data['fn1_24'] + 1e-6)

        if 'fn1_15' in data and 'fn1_13' in data:
            data['short_term_borrowing_dependency'] = data['fn1_15'] / (data['fn1_13'] + 1e-6)

        # 유동성 비율 (4개)
        if 'fn1_1' in data and 'fn1_14' in data:
            data['current_ratio'] = data['fn1_1'] / (data['fn1_14'] + 1e-6)

        if 'fn1_1' in data and 'fn1_4' in data and 'fn1_14' in data:
            data['quick_ratio'] = (data['fn1_1'] - data['fn1_4']) / (data['fn1_14'] + 1e-6)
            data['inventory_to_current_asset'] = data['fn1_4'] / (data['fn1_1'] + 1e-6)
            data['net_working_capital'] = data['fn1_1'] - data['fn1_14']

        # 수익성 비율 (2개)
        if 'fn2_5' in data and 'fn2_1' in data:
            data['operating_margin'] = data['fn2_5'] / (data['fn2_1'] + 1e-6)

        if 'fn2_10' in data and 'fn1_24' in data:
            data['roe'] = data['fn2_10'] / (data['fn1_24'] + 1e-6)

        # 활동성 비율 (2개)
        if 'fn2_1' in data:
            if 'fn1_4' in data:
                data['inventory_turnover'] = data['fn2_1'] / (data['fn1_4'] + 1e-6)
            if 'fn1_13' in data:
                data['total_capital_turnover'] = data['fn2_1'] / (data['fn1_13'] + 1e-6)

        # 성장성 비율 (2개)
        if 'fn2_5' in data and 'fn2_5_1' in data:
            fn2_5_1_abs = abs(data['fn2_5_1']) + 1e-6
            data['operating_income_growth'] = (data['fn2_5'] - data['fn2_5_1']) / fn2_5_1_abs

        if 'fn2_10' in data and 'fn2_10_1' in data:
            fn2_10_1_abs = abs(data['fn2_10_1']) + 1e-6
            data['net_income_growth'] = (data['fn2_10'] - data['fn2_10_1']) / fn2_10_1_abs

        # 현금흐름 비율 (1개)
        if 'fn3_2' in data and 'fn1_19' in data:
            data['cash_to_debt'] = data['fn3_2'] / (data['fn1_19'] + 1e-6)

        # 무한대 처리
        for key in data:
            if isinstance(data[key], (int, float)):
                if np.isinf(data[key]) or np.isnan(data[key]):
                    data[key] = 0.0

        return data

    def prepare_features(self, input_data: Dict) -> pd.DataFrame:
        """
        모델 입력용 피처 준비

        Args:
            input_data: 사용자 입력 데이터

        Returns:
            모델 입력용 피처 데이터프레임 (34개 컬럼)
        """
        # 1. wg_gb 인코딩 (Y/N → 1/0)
        if 'wg_gb' in input_data:
            if isinstance(input_data['wg_gb'], str):
                input_data['wg_gb_encoded'] = 1 if input_data['wg_gb'].upper() == 'Y' else 0
            else:
                input_data['wg_gb_encoded'] = input_data['wg_gb']

        # 2. 파생 변수 생성
        data_with_derived = self.create_derived_features(input_data)

        # 3. 최종 피처 준비
        feature_data = {}
        for feat in self.final_features:
            feature_data[feat] = data_with_derived.get(feat, 0.0)

        # DataFrame 생성 (1 row)
        df = pd.DataFrame([feature_data], columns=self.final_features)

        return df

    def predict(self, X: pd.DataFrame) -> Tuple[float, int, str]:
        """
        부도 예측

        Args:
            X: 피처 데이터프레임

        Returns:
            (부도 확률, 부도 예측, 위험도)
        """
        # 스케일링
        X_scaled = self.scaler.transform(X)

        # 예측
        proba = self.model.predict_proba(X_scaled)[0][1]
        pred = 1 if proba >= 0.5 else 0

        # 위험도 분류
        if proba < 0.3:
            risk_level = "Low"
        elif proba < 0.6:
            risk_level = "Medium"
        else:
            risk_level = "High"

        return proba, pred, risk_level

    def explain_prediction(self, X: pd.DataFrame, proba: float) -> Dict:
        """
        SHAP 값을 이용한 예측 설명 (간단한 feature importance 사용)

        Args:
            X: 피처 데이터프레임
            proba: 부도 확률

        Returns:
            SHAP 설명 딕셔너리
        """
        try:
            # Feature importance 사용
            feature_importances = self.model.feature_importances_

            # 피처 값과 importance 결합
            contributions = []
            for i, feat in enumerate(self.final_features):
                contributions.append({
                    'feature_name': feat,
                    'feature_value': float(X.iloc[0, i]),
                    'importance': float(feature_importances[i]),
                    'contribution_pct': float(feature_importances[i] * 100)
                })

            # importance 순으로 정렬
            contributions.sort(key=lambda x: x['importance'], reverse=True)

            # Top 10만 반환
            top_contributions = contributions[:10]

            return {
                'base_value': 0.0152,  # 전체 부도율
                'expected_value': proba,
                'contributions': top_contributions,
                'n_features': len(self.final_features)
            }

        except Exception as e:
            print(f"SHAP 설명 생성 실패: {str(e)}")
            return {
                'base_value': 0.0152,
                'expected_value': proba,
                'contributions': [],
                'error': str(e)
            }

    def predict_from_input(self, input_data: Dict) -> Dict:
        """
        사용자 입력으로 부도 예측

        Args:
            input_data: 사용자 입력 데이터 (19개)

        Returns:
            예측 결과 딕셔너리
        """
        try:
            # 1. 피처 준비
            X = self.prepare_features(input_data)

            # 2. 예측
            proba, pred, risk_level = self.predict(X)

            # 3. SHAP 설명
            shap_explanation = self.explain_prediction(X, proba)

            # 4. 결과 반환
            return {
                'success': True,
                'prediction': {
                    'default_probability': float(proba),
                    'default_prediction': int(pred),
                    'risk_level': risk_level,
                    'confidence': float(max(proba, 1 - proba))
                },
                'shap_values': shap_explanation,
                'n_features': len(self.final_features)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# 싱글톤 인스턴스
_service_instance = None


def get_user_friendly_service() -> UserFriendlyPredictionService:
    """
    사용자 친화 예측 서비스 인스턴스 가져오기 (싱글톤)
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = UserFriendlyPredictionService()
    return _service_instance
