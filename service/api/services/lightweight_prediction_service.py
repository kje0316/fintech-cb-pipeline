"""
경량 모델 예측 서비스 (13개 입력 컬럼)
- 사용자 입력 데이터로 부도 예측
- 12개 피처 사용 (1개 파생 변수 포함)
"""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from typing import Dict, Tuple

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent.parent


class LightweightPredictionService:
    """경량 모델 예측 서비스"""

    def __init__(self):
        """초기화 - 경량 모델 및 설정 로드"""
        self.project_root = project_root
        self.model_path = self.project_root / "ml/models/lightweight_model_best.pkl"
        self.scaler_path = self.project_root / "ml/models/lightweight_scaler.pkl"
        self.features_path = self.project_root / "ml/models/lightweight_features.json"

        # 모델 및 스케일러 로드
        self._load_model()
        self._load_scaler()
        self._load_features()

    def _load_model(self):
        """모델 로드"""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"✓ 경량 모델 로드 완료: {self.model_path}")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"경량 모델 파일을 찾을 수 없습니다: {self.model_path}\n"
                "먼저 경량 모델을 학습하세요: python ml/scripts/04_train_lightweight_model.py"
            )

    def _load_scaler(self):
        """스케일러 로드"""
        try:
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            print(f"✓ 경량 스케일러 로드 완료: {self.scaler_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"스케일러 파일을 찾을 수 없습니다: {self.scaler_path}")

    def _load_features(self):
        """피처 리스트 로드"""
        try:
            with open(self.features_path, 'r') as f:
                data = json.load(f)
            self.model_features = data['features']
            print(f"✓ 피처 리스트 로드 완료: {len(self.model_features)}개 피처")
        except FileNotFoundError:
            raise FileNotFoundError(f"피처 리스트 파일을 찾을 수 없습니다: {self.features_path}")

    def create_derived_features(self, input_data: Dict) -> Dict:
        """
        파생 변수 생성

        Args:
            input_data: 사용자 입력 데이터 (13개 DWH 컬럼)

        Returns:
            파생 변수가 추가된 데이터
        """
        data = input_data.copy()

        # inventory_to_current_asset = fn1_4 / fn1_1
        if 'fn1_4' in data and 'fn1_1' in data:
            fn1_4 = data['fn1_4']
            fn1_1 = data['fn1_1']
            data['inventory_to_current_asset'] = fn1_4 / (fn1_1 + 1e-6) if fn1_1 != 0 else 0.0
        else:
            data['inventory_to_current_asset'] = 0.0

        return data

    def prepare_features(self, input_data: Dict) -> pd.DataFrame:
        """
        모델 입력용 피처 준비

        Args:
            input_data: 사용자 입력 데이터

        Returns:
            모델 입력용 피처 데이터프레임 (12개 컬럼)
        """
        # 1. 파생 변수 생성
        data_with_derived = self.create_derived_features(input_data)

        # 2. 모델이 요구하는 12개 피처만 선택
        feature_data = {}
        for feat in self.model_features:
            if feat in data_with_derived:
                feature_data[feat] = float(data_with_derived[feat])
            else:
                # 피처가 없으면 0으로 채움
                feature_data[feat] = 0.0
                print(f"⚠️  누락된 피처: {feat} (0으로 대체)")

        # DataFrame 생성
        X = pd.DataFrame([feature_data])

        # 3. 무한대/NaN 처리
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(0)

        return X

    def predict(self, X: pd.DataFrame) -> Tuple[float, int, str]:
        """
        부도 예측

        Args:
            X: 피처 데이터프레임

        Returns:
            (부도확률, 부도예측, 위험도)
        """
        # 스케일링
        X_scaled = self.scaler.transform(X)

        # 예측 (DataFrame으로 전달하여 feature names 유지)
        X_scaled_df = pd.DataFrame(X_scaled, columns=self.model_features)
        proba = self.model.predict_proba(X_scaled_df)[0, 1]  # 부도 확률
        pred = int(proba >= 0.5)  # 0.5 threshold

        # 위험도 판정
        if proba >= 0.3:
            risk_level = "High"
        elif proba >= 0.1:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return float(proba), pred, risk_level

    def explain_prediction(self, X: pd.DataFrame) -> Dict:
        """
        SHAP 설명 생성

        Args:
            X: 피처 데이터프레임

        Returns:
            SHAP 설명 딕셔너리
        """
        try:
            import shap

            # 스케일링
            X_scaled = self.scaler.transform(X)
            X_scaled_df = pd.DataFrame(X_scaled, columns=self.model_features)

            # SHAP explainer 생성
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X_scaled_df)

            # SHAP 값 추출
            # RandomForest는 리스트 또는 3D array로 반환
            if isinstance(shap_values, list):
                shap_values_class1 = shap_values[1]  # 부도 클래스
                base_value = explainer.expected_value[1]
            elif len(shap_values.shape) == 3:
                shap_values_class1 = shap_values[:, :, 1]  # 부도 클래스
                base_value = explainer.expected_value[1] if hasattr(explainer.expected_value, '__len__') else explainer.expected_value
            else:
                shap_values_class1 = shap_values
                base_value = explainer.expected_value

            # 단일 샘플이므로 첫 번째 행만 사용
            shap_values_sample = shap_values_class1[0]  # shape: (12,)

            # 기여도 계산
            contributions = []
            for i, feat in enumerate(self.model_features):
                contributions.append({
                    'feature_name': feat,
                    'feature_value': float(X[feat].iloc[0]),
                    'shap_value': float(shap_values_sample[i]),
                    'contribution_pct': float(abs(shap_values_sample[i]) / (abs(shap_values_sample).sum() + 1e-10) * 100)
                })

            # 기여도 순으로 정렬
            contributions.sort(key=lambda x: abs(x['shap_value']), reverse=True)

            return {
                'base_value': float(base_value),
                'expected_value': float(shap_values_sample.sum() + base_value),
                'contributions': contributions  # 전체 12개 기여도 반환
            }

        except ImportError:
            return {
                'error': 'SHAP 라이브러리가 설치되지 않았습니다.',
                'contributions': []
            }
        except Exception as e:
            import traceback
            print(f"SHAP Error: {str(e)}")
            print(traceback.format_exc())
            return {
                'error': f'SHAP 계산 실패: {str(e)}',
                'contributions': []
            }

    def predict_from_input(self, input_data: Dict) -> Dict:
        """
        사용자 입력으로부터 부도 예측 (경량 모델 전체 프로세스)

        Args:
            input_data: 13개 DWH 컬럼 딕셔너리

        Returns:
            예측 결과 딕셔너리
        """
        try:
            # 1. 피처 준비
            X = self.prepare_features(input_data)

            # 2. 예측
            proba, pred, risk_level = self.predict(X)

            # 3. SHAP 설명
            shap_explanation = self.explain_prediction(X)

            return {
                'success': True,
                'model_type': 'lightweight',
                'n_features': len(self.model_features),
                'prediction': {
                    'default_probability': proba,
                    'default_prediction': pred,
                    'risk_level': risk_level,
                    'confidence': 1.0  # 입력 데이터는 신뢰도 100%
                },
                'shap_values': shap_explanation,
                'input_summary': {
                    'total_columns': len(input_data),
                    'derived_features': 1  # inventory_to_current_asset
                }
            }

        except Exception as e:
            import traceback
            print(f"Prediction Error: {str(e)}")
            print(traceback.format_exc())
            return {
                'success': False,
                'error': f'예측 중 오류 발생: {str(e)}'
            }


# 싱글톤 인스턴스
_lightweight_service = None

def get_lightweight_service() -> LightweightPredictionService:
    """경량 예측 서비스 싱글톤 인스턴스 반환"""
    global _lightweight_service
    if _lightweight_service is None:
        _lightweight_service = LightweightPredictionService()
    return _lightweight_service
