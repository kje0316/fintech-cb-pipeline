"""
클러스터링 API 라우터

기업 클러스터 예측, 벤치마크, 협력사 추천 엔드포인트 제공
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict

from service.api.models.clustering import (
    ClusterPredictionResponse,
    ClusterBenchmarkResponse,
    PartnerRecommendationResponse,
    FullAnalysisRequest,
    FullAnalysisResponse
)
from service.api.services.clustering_service import get_clustering_service

router = APIRouter(prefix="/api/v1/clustering")


@router.get("/health")
def health_check():
    """클러스터링 API 헬스 체크"""
    return {
        "status": "healthy",
        "service": "clustering",
        "version": "1.0.0"
    }


@router.post("/predict", response_model=ClusterPredictionResponse)
async def predict_cluster(features: Dict):
    """
    70개 클러스터링 피처로 클러스터 예측

    **입력**:
    - 70개 클러스터링 피처 딕셔너리 (FN1_13, R006, ... 등)

    **출력**:
    - cluster_id: 클러스터 ID (0-12)
    - cluster_name: 클러스터 별명 (예: "안정형 중소기업")
    - cluster_description: 클러스터 특성 설명

    **사용 예시**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/clustering/predict" \\
         -H "Content-Type: application/json" \\
         -d '{"FN2_1": 50000000, "R006": 120, "R015": 5, ...}'
    ```
    """
    try:
        service = get_clustering_service()
        result = service.predict_cluster(features)

        return ClusterPredictionResponse(
            success=result['success'],
            cluster_id=result['cluster_id'],
            cluster_name=result['cluster_name'],
            cluster_description=result.get('cluster_description', ''),
            method=result.get('method')
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"클러스터 예측 실패: {str(e)}"
        )


@router.get("/benchmark/{cluster_id}", response_model=ClusterBenchmarkResponse)
async def get_cluster_benchmark(
    cluster_id: int,
    features: str = Query(None, description="기업 피처 (JSON 문자열)")
):
    """
    클러스터 평균 대비 벤치마크 조회

    **입력**:
    - cluster_id: 클러스터 ID (path parameter)
    - features: 기업의 70개 피처 (query parameter, JSON 문자열)

    **출력**:
    - metrics: 지표별 벤치마크 비교 (매출액, 부채비율, 영업이익률 등)
    - radar_data: 레이더 차트용 정규화 데이터
    - summary: 요약 텍스트

    **사용 예시**:
    ```bash
    curl "http://localhost:8000/api/v1/clustering/benchmark/2?features=%7B%22FN2_1%22%3A50000000%7D"
    ```
    """
    import json

    try:
        service = get_clustering_service()

        # features 파싱
        company_features = {}
        if features:
            try:
                company_features = json.loads(features)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="features 파라미터가 유효한 JSON 형식이 아닙니다."
                )

        result = service.get_benchmark(cluster_id, company_features)

        return ClusterBenchmarkResponse(
            cluster_id=result['cluster_id'],
            cluster_name=result['cluster_name'],
            metrics=result['metrics'],
            radar_data=result['radar_data'],
            summary=result['summary']
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"벤치마크 조회 실패: {str(e)}"
        )


@router.post("/benchmark", response_model=ClusterBenchmarkResponse)
async def post_cluster_benchmark(request: FullAnalysisRequest):
    """
    클러스터 평균 대비 벤치마크 조회 (POST 방식)

    **입력**:
    - clustering_features: 70개 클러스터링 피처 딕셔너리

    먼저 클러스터를 예측한 후, 해당 클러스터 평균과 비교합니다.
    """
    try:
        service = get_clustering_service()

        # 클러스터 예측
        cluster_result = service.predict_cluster(request.clustering_features)
        cluster_id = cluster_result['cluster_id']

        # 벤치마크 계산
        result = service.get_benchmark(cluster_id, request.clustering_features)

        return ClusterBenchmarkResponse(
            cluster_id=result['cluster_id'],
            cluster_name=result['cluster_name'],
            metrics=result['metrics'],
            radar_data=result['radar_data'],
            summary=result['summary']
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"벤치마크 조회 실패: {str(e)}"
        )


@router.get("/partners/{cluster_id}", response_model=PartnerRecommendationResponse)
async def get_partner_recommendations(
    cluster_id: int,
    limit: int = Query(10, ge=1, le=50, description="추천 기업 수 (1-50)")
):
    """
    같은 클러스터 내 우량 협력사 추천

    **입력**:
    - cluster_id: 클러스터 ID (path parameter)
    - limit: 추천 기업 수 (기본값: 10)

    **출력**:
    - partners: 추천 기업 목록
        - company_name: 기업명
        - default_probability: 부도확률
        - risk_level: 위험도
        - similarity_score: 유사도 점수
        - key_strengths: 핵심 강점

    **로직**:
    - 같은 클러스터 내 기업 중 부도확률이 낮은 기업 추천
    - 유사도 점수 기반 정렬

    **사용 예시**:
    ```bash
    curl "http://localhost:8000/api/v1/clustering/partners/2?limit=10"
    ```
    """
    try:
        service = get_clustering_service()

        partners = service.get_partner_recommendations(
            cluster_id=cluster_id,
            company_features={},  # 향후 유사도 계산에 사용
            limit=limit
        )

        return PartnerRecommendationResponse(
            cluster_id=cluster_id,
            cluster_name=service.CLUSTER_ALIASES.get(cluster_id, f"클러스터 {cluster_id}"),
            total_count=len(partners),
            partners=partners
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"협력사 추천 실패: {str(e)}"
        )


@router.get("/clusters")
async def list_clusters():
    """
    전체 클러스터 목록 및 설명 조회

    **출력**:
    - clusters: 13개 클러스터 정보 목록
        - cluster_id: 클러스터 ID
        - cluster_name: 클러스터 별명
        - description: 클러스터 설명

    **사용 예시**:
    ```bash
    curl "http://localhost:8000/api/v1/clustering/clusters"
    ```
    """
    try:
        service = get_clustering_service()

        clusters = []
        for cluster_id in range(-1, 13):
            clusters.append({
                'cluster_id': cluster_id,
                'cluster_name': service.CLUSTER_ALIASES.get(cluster_id, f"클러스터 {cluster_id}"),
                'description': service.CLUSTER_DESCRIPTIONS.get(cluster_id, "")
            })

        return {
            'total_clusters': len(clusters),
            'clusters': clusters
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"클러스터 목록 조회 실패: {str(e)}"
        )


@router.post("/admin/reload-model")
async def reload_clustering_model():
    """
    클러스터링 모델 수동 리로드 (관리자 전용)

    MLflow Registry에서 최신 Production 모델을 다시 로드합니다.
    모델이 업데이트되었을 때 서버 재시작 없이 새 모델을 적용할 수 있습니다.

    **사용 예시**:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/clustering/admin/reload-model"
    ```
    """
    try:
        from service.api.services.clustering_service import reload_clustering_service

        # 서비스 리로드
        reload_clustering_service()

        return {
            'success': True,
            'message': '클러스터링 모델이 성공적으로 리로드되었습니다.',
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"모델 리로드 실패: {str(e)}"
        )
