"""
부도 예측 서비스
- DWH에서 기업 데이터 조회
- 피처 매핑 및 변환
- 모델 추론
- SHAP 설명 생성
"""
import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from sqlalchemy import text
from typing import Optional, Dict, Tuple
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from service.api.database import engine


class PredictionService:
    """부도 예측 서비스"""

    def __init__(self):
        """초기화 - 모델 및 설정 로드"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.model_path = self.project_root / "ml/models/default_model_best.pkl"
        self.scaler_path = self.project_root / "ml/data/feature_scaler.pkl"
        self.mapping_path = self.project_root / "ml/config/feature_mapping.json"

        # 모델 및 스케일러 로드
        self._load_model()
        self._load_scaler()
        self._load_feature_mapping()

    def _load_model(self):
        """모델 로드"""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"✓ 모델 로드 완료: {self.model_path}")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"모델 파일을 찾을 수 없습니다: {self.model_path}\n"
                "먼저 ML 파이프라인을 실행하세요: python ml/scripts/run_full_ml_pipeline.py"
            )

    def _load_scaler(self):
        """스케일러 로드"""
        try:
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            print(f"✓ 스케일러 로드 완료: {self.scaler_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"스케일러 파일을 찾을 수 없습니다: {self.scaler_path}")

    def _load_feature_mapping(self):
        """피처 매핑 로드"""
        try:
            with open(self.mapping_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            self.model_features = mapping['model_features']
            self.derived_features = mapping.get('derived_features', [])
            print(f"✓ 피처 매핑 로드 완료: {len(self.model_features)}개 피처")
        except FileNotFoundError:
            raise FileNotFoundError(f"피처 매핑 파일을 찾을 수 없습니다: {self.mapping_path}")

    def get_company_data(self, business_number: str = None, bs_dt: str = None) -> Optional[pd.DataFrame]:
        """
        DWH에서 기업 데이터 조회

        Args:
            business_number: 사업자번호 (미사용 - lake.raw_data에는 식별자 없음)
            bs_dt: 회계연도 (YYYYMMDD), None이면 최신

        Returns:
            DataFrame (1행) 또는 None
        """
        # lake.raw_data에는 기업 식별자가 없으므로
        # 현재는 bs_dt로만 조회 (샘플 데이터 1개 반환)
        # 실무에서는 사업자번호로 조회 가능하도록 데이터 구조 개선 필요

        if bs_dt is None:
            bs_dt = '20210801'  # 기본값

        query = text("""
            SELECT *
            FROM lake.raw_data
            WHERE bs_dt = :bs_dt
              AND perf_12m IS NOT NULL
            LIMIT 1
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"bs_dt": bs_dt})
            columns = result.keys()
            row = result.fetchone()

            if row is None:
                return None

            # DataFrame으로 변환
            df = pd.DataFrame([dict(zip(columns, row))])
            return df

    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        파생 변수 생성

        Args:
            df: 원본 데이터프레임

        Returns:
            파생 변수가 추가된 데이터프레임
        """
        df_copy = df.copy()

        # 1. cash_to_debt
        if 'fn3_2' in df.columns and 'fn1_19' in df.columns:
            df_copy['cash_to_debt'] = pd.to_numeric(df['fn3_2'], errors='coerce') / (pd.to_numeric(df['fn1_19'], errors='coerce') + 1e-6)

        # 2. debt_to_equity
        if 'fn1_19' in df.columns and 'fn1_24' in df.columns:
            df_copy['debt_to_equity'] = pd.to_numeric(df['fn1_19'], errors='coerce') / (pd.to_numeric(df['fn1_24'], errors='coerce') + 1e-6)

        # 3. interest_coverage
        if 'fn2_5' in df.columns and 'fn2_4' in df.columns:
            df_copy['interest_coverage'] = pd.to_numeric(df['fn2_5'], errors='coerce') / (pd.to_numeric(df['fn2_4'], errors='coerce') + 1e-6)

        # 4. net_working_capital
        if 'fn1_1' in df.columns and 'fn1_14' in df.columns:
            df_copy['net_working_capital'] = pd.to_numeric(df['fn1_1'], errors='coerce') - pd.to_numeric(df['fn1_14'], errors='coerce')

        # 5. nwc_to_total_asset
        if 'net_working_capital' in df_copy.columns and 'fn1_13' in df.columns:
            df_copy['nwc_to_total_asset'] = df_copy['net_working_capital'] / (pd.to_numeric(df['fn1_13'], errors='coerce') + 1e-6)

        # 6. composite_growth
        if 'r001' in df.columns and 'r002' in df.columns:
            df_copy['composite_growth'] = (pd.to_numeric(df['r001'], errors='coerce') + pd.to_numeric(df['r002'], errors='coerce')) / 2

        # 7. borrowing_ratio
        if 'fn1_16' in df.columns and 'fn1_13' in df.columns:
            df_copy['borrowing_ratio'] = pd.to_numeric(df['fn1_16'], errors='coerce') / (pd.to_numeric(df['fn1_13'], errors='coerce') + 1e-6)

        # 8-9. has_credit_event
        if 'd2b000002' in df.columns:
            val = pd.to_numeric(df['d2b000002'], errors='coerce')
            df_copy['has_credit_event_1'] = (val != 999999999).astype(int)

        if 'd2b000003' in df.columns:
            val = pd.to_numeric(df['d2b000003'], errors='coerce')
            df_copy['has_credit_event_2'] = (val != 999999999).astype(int)

        # 10. inventory_to_current_asset
        if 'fn1_4' in df.columns and 'fn1_1' in df.columns:
            df_copy['inventory_to_current_asset'] = pd.to_numeric(df['fn1_4'], errors='coerce') / (pd.to_numeric(df['fn1_1'], errors='coerce') + 1e-6)

        return df_copy

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        모델 입력용 피처 준비

        Args:
            df: DWH에서 조회한 데이터프레임

        Returns:
            모델 입력용 피처 데이터프레임 (79개 컬럼)
        """
        # 1. 파생 변수 생성
        df_engineered = self.create_derived_features(df)

        # 2. 모델이 요구하는 79개 피처만 선택
        missing_features = []
        feature_data = {}

        for feat in self.model_features:
            if feat in df_engineered.columns:
                # 문자열이면 숫자로 변환
                val = df_engineered[feat].iloc[0]
                if isinstance(val, str):
                    val = pd.to_numeric(val, errors='coerce')
                feature_data[feat] = val
            else:
                # 피처가 없으면 0으로 채움 (또는 median)
                feature_data[feat] = 0.0
                missing_features.append(feat)

        if missing_features:
            print(f"⚠️  누락된 피처 {len(missing_features)}개를 0으로 채웠습니다")

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
        # 스케일러가 credit_grade를 포함하므로 임시로 추가
        X_with_grade = X.copy()
        if 'credit_grade' not in X_with_grade.columns:
            X_with_grade['credit_grade'] = 0  # 예측 시에는 모르므로 0

        # 스케일러와 동일한 컬럼 순서로 정렬
        scaler_columns = self.scaler.feature_names_in_
        X_with_grade = X_with_grade[scaler_columns]

        # 스케일링
        X_scaled = self.scaler.transform(X_with_grade)

        # credit_grade 제거 (모델은 이 컬럼 없이 학습됨)
        X_scaled_df = pd.DataFrame(X_scaled, columns=scaler_columns)
        X_scaled_df = X_scaled_df.drop('credit_grade', axis=1)

        # 예측 (DataFrame으로 전달하여 feature names 유지)
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

            # 스케일러가 credit_grade를 포함하므로 임시로 추가
            X_with_grade = X.copy()
            if 'credit_grade' not in X_with_grade.columns:
                X_with_grade['credit_grade'] = 0

            # 스케일러와 동일한 컬럼 순서로 정렬
            scaler_columns = self.scaler.feature_names_in_
            X_with_grade = X_with_grade[scaler_columns]

            # 스케일링
            X_scaled = self.scaler.transform(X_with_grade)

            # credit_grade 제거 (모델은 이 컬럼 없이 학습됨)
            X_scaled_df = pd.DataFrame(X_scaled, columns=scaler_columns)
            X_scaled_df = X_scaled_df.drop('credit_grade', axis=1)

            # SHAP explainer 생성 (DataFrame으로 전달하여 feature names 유지)
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X_scaled_df)

            # SHAP 값 추출
            # RandomForest는 리스트 또는 3D array로 반환
            if isinstance(shap_values, list):
                # 리스트 형태: [class_0_values, class_1_values]
                shap_values_class1 = shap_values[1]  # 부도 클래스 (class=1)
                base_value = explainer.expected_value[1]
            elif len(shap_values.shape) == 3:
                # 3D array 형태: (n_samples, n_features, n_classes)
                shap_values_class1 = shap_values[:, :, 1]  # 부도 클래스 (class=1)
                base_value = explainer.expected_value[1] if hasattr(explainer.expected_value, '__len__') else explainer.expected_value
            else:
                # 2D array 형태 (단일 클래스)
                shap_values_class1 = shap_values
                base_value = explainer.expected_value

            # 단일 샘플이므로 첫 번째 행만 사용
            shap_values_sample = shap_values_class1[0]  # shape: (79,)

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
                'contributions': contributions[:20]  # Top 20만
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

    def predict_company(self, business_number: str = None, bs_dt: str = None) -> Dict:
        """
        기업 부도 예측 (전체 프로세스)

        Args:
            business_number: 사업자번호
            bs_dt: 회계연도

        Returns:
            예측 결과 딕셔너리
        """
        # 1. DWH 조회
        df = self.get_company_data(business_number, bs_dt)
        if df is None:
            return {
                'success': False,
                'message': f'해당 기업 정보를 찾을 수 없습니다. (bs_dt: {bs_dt or "최신"})'
            }

        # 2. 기업 기본 정보
        company_info = {
            'bs_dt': df['bs_dt'].iloc[0] if 'bs_dt' in df.columns else None,
            'sic_cd_3': df['sic_cd_3'].iloc[0] if 'sic_cd_3' in df.columns else None,
            'wg_gb': df['wg_gb'].iloc[0] if 'wg_gb' in df.columns else None,
            'empe_cnt': df['empe_cnt'].iloc[0] if 'empe_cnt' in df.columns else None,
        }

        # 3. 피처 준비
        X = self.prepare_features(df)

        # 4. 예측
        proba, pred, risk_level = self.predict(X)

        # 5. SHAP 설명
        shap_explanation = self.explain_prediction(X)

        return {
            'success': True,
            'business_number': business_number or 'N/A',
            'company_info': company_info,
            'prediction': {
                'default_probability': proba,
                'default_prediction': pred,
                'risk_level': risk_level,
                'confidence': 1.0  # DWH 조회는 신뢰도 100%
            },
            'shap_values': shap_explanation
        }


# 싱글톤 인스턴스
_prediction_service = None

def get_prediction_service() -> PredictionService:
    """예측 서비스 싱글톤 인스턴스 반환"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service
