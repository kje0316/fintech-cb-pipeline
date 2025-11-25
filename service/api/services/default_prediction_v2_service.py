"""
부도예측 v2 서비스 (70개 피처 기반)

37개 입력 → 70개 피처 → 부도예측
"""
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import json
from typing import Dict, List, Tuple, Any
import shap
import mlflow
import mlflow.xgboost
import mlflow.lightgbm
import mlflow.catboost
import mlflow.sklearn
import mlflow.pyfunc
from mlflow.tracking import MlflowClient

from .excel_prediction_service import ExcelPredictionService


def convert_numpy_types(obj: Any) -> Any:
    """재귀적으로 numpy 타입을 Python 기본 타입으로 변환"""
    # numpy 타입 체크 (np.integer, np.floating, np.bool_, np.ndarray 등)
    if isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


class DefaultPredictionV2Service:
    """70개 피처 기반 부도예측 서비스"""

    def __init__(self, use_mlflow_registry=True):
        """
        모델 및 관련 파일 로드

        Args:
            use_mlflow_registry: True면 MLflow Registry에서, False면 로컬 파일에서 로드
        """
        self.model_dir = Path("models/default_prediction_v2/models/production")
        self.results_dir = Path("models/default_prediction_v2/results")
        self.use_mlflow_registry = use_mlflow_registry

        if use_mlflow_registry:
            # MLflow Registry에서 Production 모델 로드
            print("📦 MLflow Registry에서 Production 모델 로딩 중...")

            try:
                # MLflow 설정
                mlflow.set_tracking_uri("sqlite:///mlflow_db/mlflow.db")
                client = MlflowClient()

                # Production 스테이지의 최신 모델 가져오기
                model_name = "default_prediction_model"
                prod_versions = client.get_latest_versions(model_name, stages=["Production"])

                if not prod_versions:
                    raise ValueError(f"Production 스테이지에 등록된 모델이 없습니다: {model_name}")

                prod_version = prod_versions[0]
                model_version = prod_version.version

                print(f"  - 모델: {model_name}")
                print(f"  - 버전: {model_version}")
                print(f"  - 스테이지: {prod_version.current_stage}")

                # 모델 로드 (MLflow에서)
                model_uri = f"models:/{model_name}/{model_version}"

                # MLflow Run에서 모델과 스케일러 로드
                run_id = prod_version.run_id

                # 모델 로드 (모델 타입에 맞게)
                model_tags = prod_version.tags  # tags는 이미 dict
                model_type = model_tags.get('model_type', '').lower()

                # 모델 URI 생성
                model_uri = f"models:/{model_name}/{model_version}"

                if 'xgboost' in model_type:
                    self.model = mlflow.xgboost.load_model(model_uri)
                elif 'lightgbm' in model_type or 'lgbm' in model_type:
                    self.model = mlflow.lightgbm.load_model(model_uri)
                elif 'catboost' in model_type:
                    self.model = mlflow.catboost.load_model(model_uri)
                else:
                    # Fallback: pyfunc로 로드
                    self.model = mlflow.pyfunc.load_model(model_uri)

                # 스케일러 로드 (같은 run에서)
                scaler_uri = f"runs:/{run_id}/scaler"
                self.scaler = mlflow.sklearn.load_model(scaler_uri)

                # 메타데이터는 모델 태그에서 가져오기
                self.metadata = {
                    'model_type': model_tags.get('model_type', 'Unknown'),
                    'model_version': f'v{model_version}',
                    'n_features': int(model_tags.get('n_features', 0)),
                    'auc_roc': float(model_tags.get('auc_roc', 0.0)),
                    'source': 'mlflow_registry'
                }

                # Feature names는 로컬 메타데이터에서 로드 (임시)
                local_metadata_path = self.model_dir / "metadata_v1.json"
                if local_metadata_path.exists():
                    with open(local_metadata_path, 'r', encoding='utf-8') as f:
                        local_metadata = json.load(f)
                        self.feature_names = local_metadata['feature_names']
                else:
                    # 기본값 (63개 피처)
                    self.feature_names = [f"feature_{i}" for i in range(63)]

                print(f"✅ MLflow Registry에서 모델 로드 완료")
                print(f"   - 모델 타입: {self.metadata['model_type']}")
                print(f"   - 버전: {model_version}")
                print(f"   - 피처 수: {len(self.feature_names)}")

            except Exception as e:
                print(f"⚠️  MLflow Registry 로드 실패: {e}")
                print("   로컬 파일로 Fallback...")
                use_mlflow_registry = False

        if not use_mlflow_registry:
            # 로컬 파일에서 모델 로드 (기존 방식)
            print("📦 로컬 파일에서 모델 로딩 중...")

            # 모델 로드
            with open(self.model_dir / "model_v1.pkl", 'rb') as f:
                self.model = pickle.load(f)

            # 스케일러 로드
            with open(self.model_dir / "scaler_v1.pkl", 'rb') as f:
                self.scaler = pickle.load(f)

            # 메타데이터 로드
            with open(self.model_dir / "metadata_v1.json", 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)

            # Feature names
            self.feature_names = self.metadata['feature_names']

            print(f"✅ 로컬 파일에서 모델 로드 완료")
            print(f"   - 모델: {self.metadata['model_type']}")
            print(f"   - 피처 수: {len(self.feature_names)}")
            print(f"   - AUC: {self.metadata.get('metrics', {}).get('auc_roc', 'N/A')}")

        # SHAP explainer 로드 (존재하면)
        shap_path = self.results_dir / "shap_values.pkl"
        if shap_path.exists():
            with open(shap_path, 'rb') as f:
                shap_data = pickle.load(f)
                self.shap_base_value = shap_data['base_value']
        else:
            self.shap_base_value = None

        # ExcelPredictionService (피처 생성용)
        self.feature_generator = ExcelPredictionService()

    def predict_from_excel_input(
        self,
        excel_input: Dict
    ) -> Dict:
        """
        37개 엑셀 입력 → 부도예측

        Args:
            excel_input: 37개 필수 컬럼을 포함한 딕셔너리

        Returns:
            prediction: 부도예측 결과
        """
        # 1. 37개 입력 → 파생 변수 생성
        full_features = self.feature_generator.create_derived_features(excel_input)

        # 2. 파생 변수 → 70개 클러스터링 피처
        clustering_features = self.feature_generator.map_to_clustering_features(full_features)

        # 3. clustering_features의 numpy 타입을 Python float로 변환
        clustering_features_serializable = {
            k: float(v) if isinstance(v, (np.floating, np.integer)) else v
            for k, v in clustering_features.items()
        }

        # 4. 70개 피처 → 부도예측
        prediction = self.predict(clustering_features)

        # 5. 추가 정보 포함
        prediction['clustering_features'] = clustering_features_serializable
        prediction['n_features'] = len(self.feature_names)

        # 6. 모든 numpy 타입을 Python 기본 타입으로 변환
        return convert_numpy_types(prediction)

    def predict(self, features: Dict) -> Dict:
        """
        70개 피처로 부도예측

        Args:
            features: 70개 피처 딕셔너리

        Returns:
            prediction: 부도확률, 위험도, SHAP 설명 등
        """
        # 1. 피처 정렬 (학습 시 순서와 동일)
        X = []
        for feature_name in self.feature_names:
            X.append(features.get(feature_name, 0))

        X = np.array(X).reshape(1, -1)

        # 2. 스케일링
        X_scaled = self.scaler.transform(X)

        # 3. 예측
        y_pred_proba = self.model.predict_proba(X_scaled)[0]
        default_probability = float(y_pred_proba[1])

        # 4. 위험도 판정 (임계값 기반)
        if default_probability < 0.3:
            risk_level = "Low"
        elif default_probability < 0.6:
            risk_level = "Medium"
        else:
            risk_level = "High"

        # 5. SHAP 설명 생성
        shap_explanation = self._generate_shap_explanation(X_scaled, default_probability)

        result = {
            'default_probability': float(default_probability),
            'default_prediction': int(default_probability >= 0.5),
            'risk_level': risk_level,
            'confidence': 1.0,  # TODO: 신뢰도 계산 로직 추가
            'shap_values': shap_explanation,
            'model_version': self.metadata['model_version'],
            'model_type': self.metadata['model_type']
        }

        # 6. 모든 numpy 타입을 Python 기본 타입으로 변환
        return convert_numpy_types(result)

    def _generate_shap_explanation(
        self,
        X_scaled: np.ndarray,
        prediction: float
    ) -> Dict:
        """SHAP 설명 생성"""
        try:
            # TreeExplainer 사용
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X_scaled)

            # 피처별 기여도 계산
            contributions = []
            for i, feature_name in enumerate(self.feature_names):
                contributions.append({
                    'feature_name': feature_name,
                    'feature_value': float(X_scaled[0, i]),
                    'shap_value': float(shap_values[0, i]),
                    'contribution_pct': abs(float(shap_values[0, i])) / (abs(shap_values[0]).sum() + 1e-10) * 100
                })

            # 기여도 순으로 정렬
            contributions = sorted(contributions, key=lambda x: abs(x['shap_value']), reverse=True)

            return {
                'base_value': float(explainer.expected_value),
                'expected_value': prediction,
                'contributions': contributions[:20]  # 상위 20개만 반환
            }

        except Exception as e:
            print(f"⚠️  SHAP 설명 생성 실패: {e}")
            return {
                'base_value': 0.0,
                'expected_value': prediction,
                'contributions': []
            }

    def get_feature_importance(self, top_n: int = 20) -> List[Dict]:
        """Feature Importance 반환"""
        importances = self.model.feature_importances_

        fi_list = []
        for i, feature_name in enumerate(self.feature_names):
            fi_list.append({
                'feature_name': feature_name,
                'importance': float(importances[i])
            })

        # 중요도 순 정렬
        fi_list = sorted(fi_list, key=lambda x: x['importance'], reverse=True)

        return fi_list[:top_n]

    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        return {
            'model_version': self.metadata['model_version'],
            'model_type': self.metadata['model_type'],
            'n_features': self.metadata['n_features'],
            'training_date': self.metadata['training_date'],
            'performance': self.metadata['metrics'],
            'description': self.metadata['description']
        }
