"""
부도 예측 API 라우터

최종 버전: 엑셀 업로드 기반 부도예측
- 37개 입력 컬럼 → 70개 파생 피처 생성 → 부도 예측
- MLflow Registry의 Production 모델 사용
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import pandas as pd
import io
import time
from pathlib import Path

from service.api.models.prediction import ExcelPredictionResponse
from service.api.services.default_prediction_v2_service import DefaultPredictionV2Service
from service.api.services.logging_service import get_logging_service

router = APIRouter(prefix="/api/v1/predict")


# ============================================================================
# 모델 캐싱 (성능 최적화)
# ============================================================================
_v2_service_cache = None


def get_v2_service(force_reload: bool = False):
    """
    DefaultPredictionV2Service 가져오기 (캐싱)

    매번 MLflow에서 모델을 로드하는 대신, 메모리에 캐싱하여 재사용합니다.

    Args:
        force_reload: True면 캐시를 무시하고 새로 로드

    Returns:
        DefaultPredictionV2Service 인스턴스
    """
    global _v2_service_cache

    if _v2_service_cache is None or force_reload:
        print(f"🔄 모델 {'재' if force_reload else ''}로드 중...")
        _v2_service_cache = DefaultPredictionV2Service()
        print(f"✅ 모델 로드 완료: {_v2_service_cache.metadata['model_type']} {_v2_service_cache.metadata['model_version']}")

    return _v2_service_cache


# ============================================================================
# 헬스 체크
# ============================================================================

@router.get("/health")
def health_check():
    """API 헬스 체크"""
    return {
        "status": "healthy",
        "service": "default-prediction-v2",
        "version": "2.0.0"
    }


# ============================================================================
# 부도 예측 API (엑셀 업로드)
# ============================================================================

@router.post("/upload/excel", response_model=ExcelPredictionResponse)
async def predict_from_excel(file: UploadFile = File(...)):
    """
    엑셀 파일 업로드 기반 부도 예측 (최종 버전)

    **입력**:
    - 엑셀 파일 (.xlsx, .xls)
    - 37개 필수 컬럼 포함
    - '데이터입력' 또는 '샘플데이터' 시트 사용

    **출력**:
    - 부도 확률
    - 위험도 (Low/Medium/High)
    - SHAP 설명
    - 70개 클러스터링 피처
    - 자동 계산된 재무비율

    **사용 예시**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/predict/upload/excel" \\
         -F "file=@재무데이터.xlsx"
    ```
    """
    start_time = time.time()

    try:
        # 1. 파일 확장자 검증
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="엑셀 파일(.xlsx, .xls)만 업로드 가능합니다."
            )

        # 2. 파일 읽기
        contents = await file.read()

        # "데이터입력" 시트 또는 "샘플데이터" 시트를 찾아서 읽기
        # 1행: 컬럼명, 2행: 항목명, 3행: 단위, 4행부터: 데이터
        try:
            df = pd.read_excel(io.BytesIO(contents), sheet_name='데이터입력', header=0, skiprows=[1, 2])

            # 데이터입력 시트에 데이터가 없거나 모든 값이 NaN이면 샘플데이터 시트 사용
            if len(df) == 0 or df.iloc[0].isna().all():
                df = pd.read_excel(io.BytesIO(contents), sheet_name='샘플데이터', header=0, skiprows=[1, 2])
        except ValueError:
            # "데이터입력" 시트가 없으면 "샘플데이터" 시트 시도
            try:
                df = pd.read_excel(io.BytesIO(contents), sheet_name='샘플데이터', header=0, skiprows=[1, 2])
            except ValueError:
                # 둘 다 없으면 첫 번째 시트 사용
                df = pd.read_excel(io.BytesIO(contents), header=0)

        # 3. v2 모델 서비스 가져오기 (캐시된 모델 사용)
        v2_service = get_v2_service()

        # 4. 필수 컬럼 검증 (37개)
        required_cols = v2_service.feature_generator.EXCEL_INPUT_FEATURES
        missing_cols = [col for col in required_cols if col not in df.columns and col != 'fn2_4']  # 이자비용은 선택적

        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"필수 컬럼이 누락되었습니다: {missing_cols}\n템플릿 파일을 다운로드하여 사용하세요."
            )

        # 5. 첫 번째 행 데이터 추출 (1개 기업만 처리)
        if len(df) == 0:
            raise HTTPException(
                status_code=400,
                detail="엑셀 파일에 데이터가 없습니다. '데이터입력' 또는 '샘플데이터' 시트를 확인하세요."
            )

        first_row = df.iloc[0]

        # 6. 딕셔너리로 변환 (NaN은 0으로 처리)
        excel_input = {}
        for col in required_cols:
            value = first_row.get(col, 0)
            if pd.isna(value):
                value = 0

            # wg_gb (외감여부)는 Y/N → 1/0 변환
            if col == 'wg_gb':
                if isinstance(value, str):
                    value = 1 if value.upper() == 'Y' else 0
                excel_input[col] = float(value)
            else:
                # 나머지는 숫자로 변환
                try:
                    excel_input[col] = float(value)
                except (ValueError, TypeError):
                    excel_input[col] = 0.0

        # 7. 부도 예측 수행 (37개 → 70개 피처 → 예측)
        result = v2_service.predict_from_excel_input(excel_input)

        # 8. 추론 시간 계산
        inference_time_ms = int((time.time() - start_time) * 1000)

        # 9. 예측 로그 DB에 저장 (PostgreSQL)
        try:
            logging_service = get_logging_service()
            request_id = logging_service.log_prediction(
                input_data=excel_input,
                derived_features=result.get('clustering_features', {}),
                prediction_result=result,
                model_version=result.get('model_version', 'unknown'),
                model_type=result.get('model_type', 'unknown'),
                inference_time_ms=inference_time_ms
            )
            print(f"✅ 예측 로그 저장 완료: request_id={request_id}")
        except Exception as log_error:
            # 로깅 실패는 무시 (예측 결과에 영향 없도록)
            print(f"⚠️ 로깅 실패 (무시): {log_error}")

        # 10. 응답 생성
        return ExcelPredictionResponse(
            success=True,
            prediction={
                'default_probability': result['default_probability'],
                'default_prediction': result['default_prediction'],
                'risk_level': result['risk_level'],
                'confidence': result.get('confidence', 1.0),
                'model_version': result.get('model_version', 'unknown'),
                'model_type': result.get('model_type', 'unknown')
            },
            shap_values=result.get('shap_values', {}),
            clustering_features=result.get('clustering_features', {}),
            n_features=result.get('n_features', 70),
            message=None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"예측 처리 중 오류가 발생했습니다: {str(e)}"
        )


# ============================================================================
# 템플릿 다운로드
# ============================================================================

@router.get("/download/excel/template")
def download_excel_template():
    """
    재무 정보 입력 템플릿 다운로드

    37개 필수 컬럼이 포함된 엑셀 템플릿 파일을 제공합니다.

    **사용 예시**:
    ```bash
    curl -O "http://localhost:8000/api/v1/predict/download/excel/template"
    ```
    """
    # 템플릿 파일 경로
    template_path = Path("ml/templates/재무정보_입력템플릿.xlsx")

    if not template_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"템플릿 파일을 찾을 수 없습니다: {template_path}\n먼저 템플릿을 생성하세요: python ml/scripts/07_generate_excel_template.py"
        )

    return FileResponse(
        path=str(template_path),
        filename="재무정보_입력템플릿.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================================
# 관리자 API - 모델 관리
# ============================================================================

@router.post("/admin/reload-model")
async def reload_model():
    """
    Production 모델을 다시 로드합니다 (서버 재시작 없이)

    **사용 시점**:
    - MLflow Registry에서 새 모델을 Production으로 승격한 후
    - API 서버를 재시작하지 않고 새 모델을 적용하고 싶을 때

    **사용법**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/predict/admin/reload-model
    ```

    **Returns**:
        모델 갱신 결과 (이전 버전 → 새 버전)
    """
    try:
        old_service = _v2_service_cache
        old_info = {
            "version": old_service.metadata.get('model_version', 'Unknown') if old_service else None,
            "type": old_service.metadata.get('model_type', 'Unknown') if old_service else None,
            "auc": old_service.metadata.get('auc_roc', 'N/A') if old_service else None
        }

        # 새 모델 강제 로드
        new_service = get_v2_service(force_reload=True)
        new_info = {
            "version": new_service.metadata.get('model_version', 'Unknown'),
            "type": new_service.metadata.get('model_type', 'Unknown'),
            "auc": new_service.metadata.get('auc_roc', 'N/A')
        }

        return {
            "status": "success",
            "message": "모델이 성공적으로 갱신되었습니다",
            "old_model": old_info,
            "new_model": new_info,
            "changed": old_info['version'] != new_info['version']
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"모델 갱신 실패: {str(e)}"
        )


@router.get("/admin/model-info")
async def get_model_info():
    """
    현재 로드된 모델 정보를 조회합니다

    **사용법**:
    ```bash
    curl http://localhost:8000/api/v1/predict/admin/model-info
    ```

    **Returns**:
        현재 사용 중인 모델의 버전, 타입, 성능 정보
    """
    try:
        service = get_v2_service()

        return {
            "status": "success",
            "model_info": {
                "version": service.metadata.get('model_version', 'Unknown'),
                "type": service.metadata.get('model_type', 'Unknown'),
                "auc_roc": service.metadata.get('auc_roc', 'N/A'),
                "n_features": service.metadata.get('n_features', len(service.feature_names)),
                "source": service.metadata.get('source', 'unknown')
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"모델 정보 조회 실패: {str(e)}"
        )
