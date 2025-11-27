"""
클러스터링 서비스

기업의 클러스터 예측, 벤치마크 계산, 협력사 추천, 업종 대비 분석, LLM 리포트 기능 제공
"""
import pandas as pd
import numpy as np
import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Any
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import yaml

# LLM 및 시각화 모듈 (lazy import)
_llm_config = None
_genai_client = None


class ClusteringService:
    """클러스터링 기반 분석 서비스"""

    # 15개 클러스터 별명 (실제 모델 분석 결과 기반)
    CLUSTER_ALIASES = {
        -1: "분류 불가",
        0: "자본잠식 위험 기업",
        1: "일반 중소기업",
        2: "고위험 부도우려 기업",
        3: "초우량 재무안정 기업",
        4: "유동성 풍부 기업",
        5: "자본잠식 소규모 기업",
        6: "안정형 중소기업",
        7: "저위험 우량 기업",
        8: "현금부자 안정 기업",
        9: "성장잠재력 기업",
        10: "안정성장 기업",
        11: "중간위험 기업",
        12: "성숙안정 기업",
        13: "신규진입 기업",
    }

    # 클러스터 데이터 경로 (CLUSTER 컬럼이 있는 파일 사용)
    CLUSTER_DATA_PATH = project_root / 'ml' / 'outputs' / 'clustering' / 'clustered_data.csv'

    # 클러스터별 특성 설명 (실제 모델 분석 결과 기반)
    CLUSTER_DESCRIPTIONS = {
        -1: "클러스터 분류가 어려운 이상치 또는 데이터 부족 기업입니다.",
        0: "자본잠식(부채비율 음수) 상태로 재무 위험이 높습니다. 자본 확충이 시급합니다.",
        1: "전체의 48%를 차지하는 일반적인 중소기업군입니다. 평균적인 재무 특성을 보입니다.",
        2: "부도율 21.6%로 가장 위험한 기업군입니다. 즉각적인 재무 개선이 필요합니다.",
        3: "저부채(26%), 고유동성(408%)의 초우량 기업군입니다. 부도율 0.4%로 매우 안정적입니다.",
        4: "유동비율 378%로 현금 유동성이 풍부한 기업군입니다.",
        5: "소규모 자본잠식 기업군입니다. 규모 확대와 자본 확충이 필요합니다.",
        6: "평균적인 재무지표를 보이는 안정형 중소기업군입니다.",
        7: "저부채(28%), 고유동성(395%)으로 재무 위험이 낮은 우량 기업군입니다.",
        8: "유동비율 435%로 현금 보유가 풍부하고 부채비율이 낮은 안정적인 기업군입니다.",
        9: "성장 잠재력이 높은 기업군입니다. 투자 확대를 통한 성장이 기대됩니다.",
        10: "안정적인 성장세를 보이는 기업군입니다. 균형 잡힌 재무구조를 갖추고 있습니다.",
        11: "중간 수준의 위험을 가진 기업군입니다. 재무 개선 여지가 있습니다.",
        12: "성숙기에 접어든 안정적인 기업군입니다. 수익성이 양호합니다.",
        13: "시장에 신규 진입한 기업군입니다. 성장 초기 단계의 특성을 보입니다.",
    }

    # 벤치마크에 사용할 주요 지표
    BENCHMARK_METRICS = [
        {'key': 'FN2_1', 'name': '매출액', 'unit': '천원', 'higher_better': True},
        {'key': 'R006', 'name': '부채비율', 'unit': '%', 'higher_better': False},
        {'key': 'R015', 'name': '영업이익률', 'unit': '%', 'higher_better': True},
        {'key': 'R018', 'name': 'ROE', 'unit': '%', 'higher_better': True},
        {'key': 'R008', 'name': '유동비율', 'unit': '%', 'higher_better': True},
        {'key': 'N006', 'name': 'EBITDA마진율', 'unit': '%', 'higher_better': True},
    ]

    def __init__(self, use_mlflow_registry: bool = True):
        """
        초기화 - Predictor는 lazy loading

        Args:
            use_mlflow_registry: True면 MLflow Registry에서 모델 로드
        """
        self._predictor = None
        self._cluster_data = None
        self._cluster_stats = None  # 클러스터별 통계
        self._industry_stats = None  # 업종별 통계
        self._use_mlflow_registry = use_mlflow_registry
        self._load_cluster_aliases()
        self._load_cluster_data()  # 실제 클러스터 데이터 로드

    def _load_cluster_aliases(self):
        """cluster_aliases.yaml 로드"""
        try:
            aliases_path = project_root / 'ml' / 'clustering' / 'configs' / 'cluster_aliases.yaml'
            if aliases_path.exists():
                with open(aliases_path, 'r', encoding='utf-8') as f:
                    loaded_aliases = yaml.safe_load(f)
                    if loaded_aliases:
                        self.CLUSTER_ALIASES.update({int(k): v for k, v in loaded_aliases.items()})
                print(f"✅ 클러스터 별명 로드 완료: {len(self.CLUSTER_ALIASES)}개")
        except Exception as e:
            print(f"⚠️ cluster_aliases.yaml 로드 실패, 기본값 사용: {e}")

    def _load_cluster_data(self):
        """실제 클러스터링 결과 데이터 로드 및 통계 계산"""
        try:
            if not self.CLUSTER_DATA_PATH.exists():
                print(f"⚠️ 클러스터 데이터 파일 없음: {self.CLUSTER_DATA_PATH}")
                return

            # 필요한 컬럼만 로드 (메모리 최적화)
            use_cols = [
                'COMPANY_ID', 'SIC_CD_3', 'Cluster',
                'FN2_1', 'R006', 'R015', 'R018', 'R008', 'N006',
                'R002', 'R012', 'DA0D00021', 'DEFAULT_YN'
            ]

            print(f"📊 클러스터 데이터 로드 중: {self.CLUSTER_DATA_PATH}")
            self._cluster_data = pd.read_csv(
                self.CLUSTER_DATA_PATH,
                usecols=lambda x: x.upper() in [c.upper() for c in use_cols],
                low_memory=False
            )

            # 컬럼명 대문자로 통일
            self._cluster_data.columns = self._cluster_data.columns.str.upper()

            # 클러스터별 통계 계산
            metric_cols = ['FN2_1', 'R006', 'R015', 'R018', 'R008', 'N006']
            self._cluster_stats = self._cluster_data.groupby('CLUSTER')[metric_cols].agg(['mean', 'std', 'median']).to_dict()

            # 업종별 통계 계산
            self._industry_stats = self._cluster_data.groupby('SIC_CD_3')[metric_cols].agg(['mean', 'std', 'median']).to_dict()

            # 전체 평균
            self._overall_stats = self._cluster_data[metric_cols].agg(['mean', 'std', 'median']).to_dict()

            n_companies = len(self._cluster_data)
            n_clusters = self._cluster_data['CLUSTER'].nunique()
            print(f"✅ 클러스터 데이터 로드 완료: {n_companies:,}개 기업, {n_clusters}개 클러스터")

        except Exception as e:
            print(f"⚠️ 클러스터 데이터 로드 실패: {e}")
            self._cluster_data = None
            self._cluster_stats = None
            self._industry_stats = None

    @property
    def predictor(self):
        """Predictor lazy loading - MLflow Registry 우선"""
        if self._predictor is None:
            try:
                from ml.clustering.inference.predictor import Predictor
                self._predictor = Predictor(
                    experiment_name='final_notebook_model',
                    use_mlflow_registry=self._use_mlflow_registry,
                    model_stage="Production"
                )
                source = self._predictor.metadata.get('source', 'unknown')
                version = self._predictor.metadata.get('model_version', 'N/A')
                print(f"✅ 클러스터링 Predictor 로드 완료 (source: {source}, version: {version})")
            except Exception as e:
                print(f"⚠️ Predictor 로드 실패: {e}")
                self._predictor = None
        return self._predictor

    def reload_predictor(self):
        """Predictor 재로드 (새 모델 적용 시)"""
        self._predictor = None
        return self.predictor is not None

    def predict_cluster(self, clustering_features: Dict) -> Dict:
        """
        70개 클러스터링 피처로 클러스터 예측

        Args:
            clustering_features: 70개 클러스터링 피처 딕셔너리

        Returns:
            {
                'cluster_id': int,
                'cluster_name': str,
                'cluster_description': str,
                'success': bool
            }
        """
        try:
            if self.predictor is None:
                # Predictor 로드 실패 시 규칙 기반 분류
                return self._rule_based_clustering(clustering_features)

            # DataFrame 형식으로 변환
            df = pd.DataFrame([clustering_features])

            # 클러스터 예측
            result_df = self.predictor.predict(df)
            cluster_id = int(result_df['predicted_cluster'].iloc[0])

            return {
                'success': True,
                'cluster_id': cluster_id,
                'cluster_name': self.CLUSTER_ALIASES.get(cluster_id, f"클러스터 {cluster_id}"),
                'cluster_description': self.CLUSTER_DESCRIPTIONS.get(cluster_id, "")
            }

        except Exception as e:
            print(f"⚠️ 클러스터 예측 실패, 규칙 기반 분류 사용: {e}")
            return self._rule_based_clustering(clustering_features)

    def _rule_based_clustering(self, features: Dict) -> Dict:
        """
        규칙 기반 클러스터 분류 (Predictor 실패 시 폴백)

        재무 지표 기반 간단한 분류 로직
        """
        try:
            # 주요 지표 추출
            debt_ratio = features.get('R006', 100)  # 부채비율
            roe = features.get('R018', 0)  # ROE
            current_ratio = features.get('R008', 100)  # 유동비율
            revenue = features.get('FN2_1', 0)  # 매출액
            operating_margin = features.get('R015', 0)  # 영업이익률

            # 규칙 기반 분류
            if debt_ratio > 300 or current_ratio < 50:
                cluster_id = 11  # 고부채 고위험
            elif debt_ratio < 50 and current_ratio > 200:
                cluster_id = 7  # 재무안정성 특화
            elif revenue > 100000000 and roe > 10:  # 매출 1000억 이상, ROE 10% 이상
                cluster_id = 6  # 초우량 대기업
            elif roe > 15 and operating_margin > 10:
                cluster_id = 4  # 고수익 잠재
            elif operating_margin > 5 and debt_ratio < 150:
                cluster_id = 9  # 균형잡힌 우량
            elif debt_ratio < 100 and current_ratio > 150:
                cluster_id = 2  # 안정형 중소기업
            elif revenue < 10000000:  # 매출 100억 미만
                cluster_id = 0  # 고위험 소규모
            else:
                cluster_id = 3  # 평균 수준

            return {
                'success': True,
                'cluster_id': cluster_id,
                'cluster_name': self.CLUSTER_ALIASES.get(cluster_id, f"클러스터 {cluster_id}"),
                'cluster_description': self.CLUSTER_DESCRIPTIONS.get(cluster_id, ""),
                'method': 'rule_based'
            }

        except Exception as e:
            return {
                'success': False,
                'cluster_id': -1,
                'cluster_name': "분류 불가",
                'cluster_description': "클러스터 분류 중 오류가 발생했습니다.",
                'error': str(e)
            }

    def get_benchmark(self, cluster_id: int, company_features: Dict) -> Dict:
        """
        클러스터 평균 대비 벤치마크 계산

        Args:
            cluster_id: 클러스터 ID
            company_features: 기업의 70개 피처

        Returns:
            {
                'cluster_name': str,
                'metrics': [
                    {
                        'name': str,
                        'company_value': float,
                        'cluster_avg': float,
                        'percentile': int,
                        'comparison': str  # 'above', 'below', 'average'
                    }
                ],
                'radar_data': [...],  # 레이더 차트용 정규화 데이터
                'summary': str
            }
        """
        # 클러스터별 평균값
        cluster_averages = self._get_cluster_averages(cluster_id)

        # 클러스터 내 min/max 범위 가져오기 (정규화용)
        cluster_ranges = self._get_cluster_ranges(cluster_id)

        metrics = []
        radar_data = []

        for metric_info in self.BENCHMARK_METRICS:
            key = metric_info['key']
            name = metric_info['name']
            higher_better = metric_info['higher_better']

            company_value = company_features.get(key, 0)
            cluster_avg = cluster_averages.get(key, 0)

            # 백분위수 계산 (개선된 로직)
            percentile = self._calculate_percentile(
                company_value, cluster_avg, higher_better
            )

            # 비교 결과
            if percentile > 60:
                comparison = 'above'
            elif percentile < 40:
                comparison = 'below'
            else:
                comparison = 'average'

            metrics.append({
                'name': name,
                'key': key,
                'company_value': round(company_value, 2),
                'cluster_avg': round(cluster_avg, 2),
                'percentile': percentile,
                'comparison': comparison,
                'unit': metric_info['unit']
            })

            # 레이더 차트용 데이터 (0-100 스케일로 정규화)
            # 기업과 클러스터 평균 모두 실제 정규화된 값으로 표시
            min_val, max_val = cluster_ranges.get(key, (0, 100))

            # 매출액처럼 편차가 큰 지표는 로그 스케일 적용
            use_log_scale = key == 'FN2_1'  # 매출액

            company_normalized = self._normalize_for_radar(
                company_value, min_val, max_val, higher_better, use_log_scale
            )
            cluster_normalized = self._normalize_for_radar(
                cluster_avg, min_val, max_val, higher_better, use_log_scale
            )

            radar_data.append({
                'metric': name,
                'company': company_normalized,
                'cluster_avg': cluster_normalized
            })

        # 요약 텍스트 생성
        above_metrics = [m['name'] for m in metrics if m['comparison'] == 'above']
        below_metrics = [m['name'] for m in metrics if m['comparison'] == 'below']

        summary_parts = []
        if above_metrics:
            summary_parts.append(f"**{', '.join(above_metrics[:2])}** 지표가 우수합니다")
        if below_metrics:
            summary_parts.append(f"**{', '.join(below_metrics[:2])}** 지표는 개선이 필요합니다")

        summary = ". ".join(summary_parts) if summary_parts else "전반적으로 클러스터 평균 수준입니다."

        return {
            'cluster_id': cluster_id,
            'cluster_name': self.CLUSTER_ALIASES.get(cluster_id, f"클러스터 {cluster_id}"),
            'metrics': metrics,
            'radar_data': radar_data,
            'summary': summary
        }

    def _get_cluster_ranges(self, cluster_id: int) -> Dict[str, tuple]:
        """
        레이더 차트 정규화용 범위 반환

        글로벌 데이터셋의 5~95 백분위수 사용 (클러스터 간 비교를 위해)
        데이터 없으면 합리적인 기본 범위 사용
        """
        # 기본 범위 (합리적인 재무 지표 범위)
        default_ranges = {
            'FN2_1': (0, 100000000),      # 매출액: 0 ~ 1000억
            'R006': (0, 400),              # 부채비율: 0 ~ 400%
            'R015': (-20, 30),             # 영업이익률: -20% ~ 30%
            'R018': (-30, 50),             # ROE: -30% ~ 50%
            'R008': (50, 300),             # 유동비율: 50% ~ 300%
            'N006': (-10, 40),             # EBITDA마진율: -10% ~ 40%
        }

        # 전체 데이터에서 글로벌 범위 계산 (클러스터별이 아닌 전체)
        if self._cluster_data is not None:
            ranges = {}
            for metric_info in self.BENCHMARK_METRICS:
                key = metric_info['key']
                if key in self._cluster_data.columns:
                    values = self._cluster_data[key].dropna()
                    if len(values) > 0:
                        # 5~95 백분위수 (극단값 제외)
                        min_val = float(values.quantile(0.05))
                        max_val = float(values.quantile(0.95))

                        # 범위가 너무 이상하면 (음수만 있거나) 기본값 사용
                        if max_val <= min_val or (max_val < 0 and key in ['R006', 'R008']):
                            ranges[key] = default_ranges.get(key, (0, 100))
                        else:
                            ranges[key] = (min_val, max_val)
                    else:
                        ranges[key] = default_ranges.get(key, (0, 100))
                else:
                    ranges[key] = default_ranges.get(key, (0, 100))

            return ranges

        return default_ranges

    def _normalize_for_radar(
        self,
        value: float,
        min_val: float,
        max_val: float,
        higher_better: bool,
        use_log_scale: bool = False
    ) -> int:
        """
        레이더 차트용 0-100 정규화

        Args:
            value: 원본 값
            min_val: 최소값
            max_val: 최대값
            higher_better: True면 높을수록 좋음
            use_log_scale: True면 로그 스케일 적용 (매출액 등 편차 큰 지표용)

        Returns:
            0-100 범위의 정규화된 값
        """
        import math

        # 범위가 없으면 50 반환
        if max_val == min_val:
            return 50

        # 로그 스케일 적용 (매출액 등 편차가 큰 지표)
        if use_log_scale:
            # 0 이하 값 처리 (로그 불가)
            log_value = math.log10(max(1, value))
            log_min = math.log10(max(1, min_val))
            log_max = math.log10(max(1, max_val))

            if log_max == log_min:
                return 50

            normalized = (log_value - log_min) / (log_max - log_min) * 100
        else:
            # 범위 내로 클리핑
            clipped_value = max(min_val, min(max_val, value))
            # 0-100 정규화
            normalized = (clipped_value - min_val) / (max_val - min_val) * 100

        # higher_better가 False면 반전 (낮을수록 좋으면 높은 점수)
        if not higher_better:
            normalized = 100 - normalized

        return int(max(0, min(100, normalized)))

    def _calculate_percentile(
        self,
        company_value: float,
        cluster_avg: float,
        higher_better: bool
    ) -> int:
        """
        백분위수 계산 (음수 및 극단값 처리)

        Args:
            company_value: 기업 값
            cluster_avg: 클러스터 평균
            higher_better: True면 높을수록 좋음, False면 낮을수록 좋음

        Returns:
            1-99 범위의 백분위수 (50이 평균, 높을수록 좋음)
        """
        # 평균이 0에 가까우면 직접 비교
        if abs(cluster_avg) < 0.001:
            if higher_better:
                return 75 if company_value > 0 else (25 if company_value < 0 else 50)
            else:
                return 75 if company_value < 0 else (25 if company_value > 0 else 50)

        # 차이 기반 계산 (음수 평균도 처리)
        diff = company_value - cluster_avg

        # 스케일 정규화 (평균의 절대값 기준)
        scale = abs(cluster_avg) if abs(cluster_avg) > 1 else 1
        normalized_diff = diff / scale

        # higher_better에 따라 방향 조정
        if not higher_better:
            normalized_diff = -normalized_diff  # 낮을수록 좋으면 부호 반전

        # sigmoid 형태로 변환하여 극단값 방지
        # normalized_diff가 0이면 50, 양수면 50-99, 음수면 1-50
        import math
        sigmoid = 1 / (1 + math.exp(-normalized_diff * 2))  # 0~1 범위
        percentile = int(sigmoid * 98) + 1  # 1~99 범위

        return min(99, max(1, percentile))

    def _get_cluster_averages(self, cluster_id: int) -> Dict:
        """
        클러스터별 실제 중앙값 반환 (이상치 영향 최소화)

        mean 대신 median 사용 - 재무 데이터의 극단값 영향 제거
        """
        # 기본값 (데이터 없을 때 폴백)
        default_averages = {
            'FN2_1': 50000000,   # 매출액 5천만
            'R006': 120,         # 부채비율 120%
            'R015': 5,           # 영업이익률 5%
            'R018': 8,           # ROE 8%
            'R008': 150,         # 유동비율 150%
            'N006': 10,          # EBITDA마진율 10%
        }

        if self._cluster_stats is None:
            return default_averages

        try:
            averages = {}
            for metric in ['FN2_1', 'R006', 'R015', 'R018', 'R008', 'N006']:
                # median 사용 (이상치 영향 최소화)
                key = (metric, 'median')
                if key in self._cluster_stats:
                    cluster_medians = self._cluster_stats[key]
                    if cluster_id in cluster_medians:
                        value = cluster_medians[cluster_id]
                        if pd.notna(value):
                            averages[metric] = float(value)
                            continue
                # 폴백
                averages[metric] = default_averages.get(metric, 0)

            return averages

        except Exception as e:
            print(f"⚠️ 클러스터 중앙값 조회 실패: {e}")
            return default_averages

    def get_partner_recommendations(
        self,
        cluster_id: int,
        company_features: Dict,
        limit: int = 10
    ) -> List[Dict]:
        """
        같은 클러스터 내 우량 기업 추천 (실제 데이터 기반)

        Args:
            cluster_id: 현재 기업의 클러스터 ID
            company_features: 기업의 피처 (유사도 계산용)
            limit: 추천 기업 수

        Returns:
            추천 기업 목록
        """
        # 업종명 매핑
        industry_names = {
            'C': '제조업', 'G': '도소매업', 'F': '건설업',
            'H': '운수창고업', 'J': '정보통신업', 'K': '금융보험업',
            'L': '부동산업', 'M': '전문서비스업', 'N': '사업시설관리업',
            'A': '농림어업', 'B': '광업', 'D': '전기가스업',
            'E': '수도하수폐기물', 'I': '숙박음식점업', 'P': '교육서비스업',
            'Q': '보건사회복지', 'R': '예술스포츠', 'S': '기타서비스업',
        }

        if self._cluster_data is None:
            # 데이터 없으면 빈 리스트
            return []

        try:
            # 같은 클러스터의 기업들 필터링
            cluster_companies = self._cluster_data[
                self._cluster_data['CLUSTER'] == cluster_id
            ].copy()

            if len(cluster_companies) == 0:
                return []

            # 부도 기업 제외
            cluster_companies = cluster_companies[
                cluster_companies['DEFAULT_YN'] != 1
            ]

            # 재무 건전성 점수 계산
            cluster_companies['health_score'] = (
                cluster_companies['R018'].fillna(0).clip(-50, 50) * 0.3 +  # ROE
                cluster_companies['R015'].fillna(0).clip(-50, 50) * 0.3 +  # 영업이익률
                (200 - cluster_companies['R006'].fillna(200).clip(0, 400)) / 4 * 0.2 +  # 부채비율 역수
                cluster_companies['R008'].fillna(100).clip(0, 300) / 3 * 0.2  # 유동비율
            )

            # 재무 건전성 하위 50% 제외 (우량 기업만)
            health_median = cluster_companies['health_score'].median()
            healthy_companies = cluster_companies[
                cluster_companies['health_score'] >= health_median
            ]

            # 유사도 계산 (샘플링으로 성능 최적화 - 최대 500개)
            if len(healthy_companies) > 500:
                healthy_companies = healthy_companies.sample(n=500, random_state=42)

            # 각 기업의 유사도 계산
            similarities = []
            for idx, row in healthy_companies.iterrows():
                sim = self._calculate_similarity(company_features, row)
                similarities.append((idx, sim))

            # 유사도 높은 순 정렬
            similarities.sort(key=lambda x: -x[1])

            partners = []
            for idx, similarity in similarities[:limit * 2]:
                row = healthy_companies.loc[idx]

                # 업종 코드에서 업종명 추출
                sic_code = str(row.get('SIC_CD_3', ''))
                industry_prefix = sic_code[:1] if sic_code else ''
                industry_name = industry_names.get(industry_prefix, '기타')

                # 재무지표 기반 부도확률 추정
                debt_ratio = float(row.get('R006', 100) or 100)
                op_margin = float(row.get('R015', 0) or 0)
                roe = float(row.get('R018', 0) or 0)

                # 부도확률 추정 (클리핑 적용)
                debt_ratio = max(0, min(500, debt_ratio))
                op_margin = max(-50, min(50, op_margin))
                roe = max(-50, min(50, roe))

                default_prob = max(0.01, min(0.5,
                    0.1 + (debt_ratio - 100) / 500 - op_margin / 50 - roe / 50
                ))

                # 위험도 결정
                if default_prob < 0.1:
                    risk_level = 'Low'
                elif default_prob < 0.2:
                    risk_level = 'Medium'
                else:
                    risk_level = 'High'

                # 강점 분석
                strengths = []
                if debt_ratio < 100:
                    strengths.append('재무안정성')
                if op_margin > 5:
                    strengths.append('수익성')
                growth = float(row.get('R002', 0) or 0)
                if growth > 10:
                    strengths.append('성장성')
                liquidity = float(row.get('R008', 0) or 0)
                if liquidity > 150:
                    strengths.append('유동성')
                if roe > 10:
                    strengths.append('효율성')

                if not strengths:
                    strengths = ['안정적 운영']

                company_id = str(row.get('COMPANY_ID', ''))
                partners.append({
                    'company_id': company_id,
                    'company_name': f"ID-{company_id[-8:]}" if company_id else f"기업-{len(partners)+1:03d}",
                    'default_probability': round(default_prob, 4),
                    'risk_level': risk_level,
                    'industry': industry_name,
                    'similarity_score': similarity,  # 이미 계산됨
                    'key_strengths': strengths[:3]
                })

                if len(partners) >= limit:
                    break

            return partners[:limit]

        except Exception as e:
            print(f"⚠️ 협력사 추천 실패: {e}")
            return []

    def _calculate_similarity(self, features1: Dict, features2) -> float:
        """
        두 기업 간 유사도 계산 (IQR 기반 정규화)

        이상치에 강건한 IQR(사분위범위)를 사용하여 정규화합니다.
        """
        try:
            metrics = ['FN2_1', 'R006', 'R015', 'R018', 'R008', 'N006']
            differences = []

            for m in metrics:
                v1 = features1.get(m, 0) or 0
                v2 = features2.get(m, 0) if isinstance(features2, dict) else features2.get(m, 0)
                if pd.isna(v2):
                    v2 = 0

                # IQR 기반 스케일 계산 (캐시된 데이터 사용)
                if self._cluster_data is not None and m in self._cluster_data.columns:
                    col_data = self._cluster_data[m].dropna()
                    q1, q3 = col_data.quantile(0.25), col_data.quantile(0.75)
                    iqr = q3 - q1
                    scale = iqr if iqr > 0 else col_data.std()
                    if scale == 0 or pd.isna(scale):
                        scale = 1
                else:
                    scale = 1

                # 정규화된 차이 계산
                diff = abs(float(v1) - float(v2)) / scale
                differences.append(min(diff, 5))  # 최대 5 표준편차로 클리핑

            # 평균 차이 계산
            avg_diff = np.mean(differences)

            # 거리를 유사도로 변환 (0~1 범위)
            # avg_diff가 0이면 1, avg_diff가 2면 약 0.5, avg_diff가 5면 약 0.1
            similarity = 1 / (1 + avg_diff)

            return round(max(0.01, min(0.99, similarity)), 2)

        except Exception as e:
            print(f"유사도 계산 오류: {e}")
            return 0.5

    # ========================================================================
    # 업종 대비 분석
    # ========================================================================

    def get_industry_benchmark(
        self,
        industry_code: str,
        company_features: Dict
    ) -> Dict:
        """
        업종 대비 위치 분석

        Args:
            industry_code: 업종 코드 (SIC_CD_3)
            company_features: 기업의 70개 피처

        Returns:
            {
                'industry_code': str,
                'industry_name': str,
                'metrics': [...],  # 벤치마크 지표
                'percentile_rank': int,  # 업종 내 종합 순위
                'summary': str
            }
        """
        # 업종명 매핑 (주요 업종)
        industry_names = {
            'C': '제조업',
            'G': '도소매업',
            'F': '건설업',
            'H': '운수창고업',
            'J': '정보통신업',
            'K': '금융보험업',
            'L': '부동산업',
            'M': '전문과학기술서비스업',
            'N': '사업시설관리업',
        }

        industry_name = industry_names.get(
            industry_code[:1] if industry_code else '',
            f"업종코드 {industry_code}"
        )

        # 업종별 평균값 (실제로는 DB에서 조회)
        industry_averages = self._get_industry_averages(industry_code)

        metrics = []
        total_score = 0

        for metric_info in self.BENCHMARK_METRICS:
            key = metric_info['key']
            name = metric_info['name']
            higher_better = metric_info['higher_better']

            company_value = company_features.get(key, 0)
            industry_avg = industry_averages.get(key, 0)

            # 백분위수 계산
            if industry_avg != 0:
                ratio = company_value / industry_avg
                if higher_better:
                    percentile = min(99, max(1, int(50 + (ratio - 1) * 50)))
                else:
                    percentile = min(99, max(1, int(50 - (ratio - 1) * 50)))
            else:
                percentile = 50

            total_score += percentile

            metrics.append({
                'name': name,
                'key': key,
                'company_value': round(company_value, 2),
                'industry_avg': round(industry_avg, 2),
                'percentile': percentile,
                'unit': metric_info['unit']
            })

        # 종합 백분위
        avg_percentile = int(total_score / len(self.BENCHMARK_METRICS))

        # 요약 생성
        if avg_percentile >= 70:
            summary = f"{industry_name} 내에서 상위 {100-avg_percentile}%에 해당하는 우수한 재무 상태입니다."
        elif avg_percentile >= 40:
            summary = f"{industry_name} 내에서 평균 수준의 재무 상태를 보이고 있습니다."
        else:
            summary = f"{industry_name} 내에서 하위 {avg_percentile}%에 해당하며 재무 개선이 필요합니다."

        return {
            'industry_code': industry_code,
            'industry_name': industry_name,
            'metrics': metrics,
            'percentile_rank': avg_percentile,
            'summary': summary
        }

    def _get_industry_averages(self, industry_code: str) -> Dict:
        """업종별 실제 평균값 반환"""
        # 기본값 (데이터 없을 때 폴백)
        base_averages = {
            'FN2_1': 30000000,
            'R006': 130,
            'R015': 4,
            'R018': 6,
            'R008': 140,
            'N006': 8,
        }

        if self._industry_stats is None or not industry_code:
            return base_averages

        try:
            averages = {}
            for metric in ['FN2_1', 'R006', 'R015', 'R018', 'R008', 'N006']:
                key = (metric, 'mean')
                if key in self._industry_stats:
                    industry_means = self._industry_stats[key]
                    if industry_code in industry_means:
                        value = industry_means[industry_code]
                        if pd.notna(value):
                            averages[metric] = float(value)
                            continue
                # 폴백
                averages[metric] = base_averages.get(metric, 0)

            return averages

        except Exception as e:
            print(f"⚠️ 업종 평균 조회 실패: {e}")
            return base_averages

    # ========================================================================
    # LLM 기반 분석 리포트
    # ========================================================================

    def _get_llm_client(self):
        """LLM 클라이언트 lazy loading"""
        global _llm_config, _genai_client

        if _genai_client is not None:
            return _genai_client, _llm_config

        try:
            # 설정 파일 로드
            config_path = project_root / 'config' / 'local_settings.yaml'
            if not config_path.exists():
                print("⚠️ local_settings.yaml 없음, LLM 기능 비활성화")
                return None, None

            with open(config_path, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)

            google_config = settings.get('GOOGLE', {})
            api_key = google_config.get('API_KEY')
            model_id = google_config.get('MODEL_ID', 'gemini-2.0-flash')

            if not api_key:
                print("⚠️ GOOGLE.API_KEY 없음, LLM 기능 비활성화")
                return None, None

            from google import genai
            _genai_client = genai.Client(api_key=api_key)
            _llm_config = {'model_id': model_id}

            print(f"✅ LLM 클라이언트 초기화 완료: {model_id}")
            return _genai_client, _llm_config

        except Exception as e:
            print(f"⚠️ LLM 클라이언트 초기화 실패: {e}")
            return None, None

    def generate_diagnosis_report(
        self,
        company_features: Dict,
        default_prediction: Dict,
        cluster_info: Dict,
        benchmark: Dict,
        industry_benchmark: Optional[Dict] = None
    ) -> str:
        """
        LLM 기반 종합 진단 리포트 생성

        Args:
            company_features: 기업 재무 피처
            default_prediction: 부도예측 결과
            cluster_info: 클러스터 정보
            benchmark: 클러스터 벤치마크
            industry_benchmark: 업종 벤치마크 (선택)

        Returns:
            종합 진단 리포트 문자열
        """
        client, config = self._get_llm_client()

        if client is None:
            return self._generate_rule_based_report(
                company_features, default_prediction, cluster_info, benchmark
            )

        try:
            # 데이터 준비
            data = {
                '부도예측': {
                    '부도확률': f"{default_prediction.get('default_probability', 0)*100:.1f}%",
                    '위험등급': default_prediction.get('risk_level', 'Unknown'),
                },
                '클러스터분석': {
                    '소속군집': cluster_info.get('cluster_name', ''),
                    '군집특성': cluster_info.get('cluster_description', ''),
                },
                '벤치마크': {m['name']: f"기업 {m['company_value']}{m['unit']} vs 평균 {m['cluster_avg']}{m['unit']} (상위 {100-m['percentile']}%)"
                           for m in benchmark.get('metrics', [])},
            }

            if industry_benchmark:
                data['업종대비'] = {
                    '업종': industry_benchmark.get('industry_name', ''),
                    '업종내순위': f"상위 {100-industry_benchmark.get('percentile_rank', 50)}%",
                }

            prompt = f"""
당신은 20년 경력의 기업 신용 분석 전문가입니다. 아래 데이터를 바탕으로 경영진에게 제출할 수준의 상세한 기업 진단 리포트를 작성하세요.

[분석 데이터]
{json.dumps(data, ensure_ascii=False, indent=2)}

[리포트 구조 - 반드시 아래 7개 섹션을 모두 포함하세요]

## 1. 경영진단 요약 (Executive Summary)
- 기업의 전반적인 재무 건전성 평가 (2-3문장)
- 핵심 위험/기회 요인 요약
- 즉각적인 조치 필요 여부 및 긴급도 판단

## 2. 재무 건전성 분석
- 부채비율, 유동비율 등 안정성 지표 상세 분석
- 동종 업계 평균 대비 위치 해석
- 재무 구조의 강점과 취약점
- 단기/장기 지급 능력 평가

## 3. 수익성 심층 분석
- 영업이익률, ROE, EBITDA 마진율 상세 분석
- 수익성 저하/개선의 원인 추정
- 업계 경쟁사 대비 수익 창출 능력 평가
- 수익성이 기업 가치에 미치는 영향

## 4. 성장성 및 시장 포지션
- 매출 규모와 성장 잠재력 분석
- 클러스터 내 위치와 의미 해석
- 시장 점유율 확대 가능성
- 경쟁 우위 요소 및 차별화 포인트

## 5. 리스크 요인 상세 분석
- 식별된 주요 위험 요인 3-5개 상세 설명
- 각 위험 요인의 심각도와 발생 가능성
- 위험 요인 간 상호 연관성
- 방치 시 예상되는 시나리오

## 6. 단기 개선 권고안 (3-6개월)
- 즉시 실행 가능한 구체적 조치 3-5개
- 각 조치의 예상 효과와 우선순위
- 필요 자원 및 실행 방안
- KPI 및 성과 측정 방법

## 7. 중장기 전략 제언 (6개월-2년)
- 구조적 개선을 위한 전략 방향
- 재무 목표 설정 권고
- 사업 포트폴리오 조정 방안
- 모니터링 및 재평가 주기

[작성 가이드라인]
- 톤앤매너: 전문적이고 객관적인 어조, 실무자가 바로 활용 가능한 수준
- 수치 해석: 단순 수치 나열이 아닌 경영적 의미와 시사점 설명
- 분량: 각 섹션별 3-5문장 이상, 전체 2000자 이상의 충실한 리포트
- 마크다운 형식으로 작성 (##, **, - 등 활용)

리포트를 작성하세요:
"""

            response = client.models.generate_content(
                model=config['model_id'],
                contents=prompt
            )
            return response.text

        except Exception as e:
            print(f"⚠️ LLM 리포트 생성 실패: {e}")
            return self._generate_rule_based_report(
                company_features, default_prediction, cluster_info, benchmark
            )

    def _generate_rule_based_report(
        self,
        company_features: Dict,
        default_prediction: Dict,
        cluster_info: Dict,
        benchmark: Dict
    ) -> str:
        """규칙 기반 리포트 생성 (LLM 폴백)"""
        prob = default_prediction.get('default_probability', 0)
        risk = default_prediction.get('risk_level', 'Unknown')
        cluster_name = cluster_info.get('cluster_name', '')

        # 강점/약점 분석
        metrics = benchmark.get('metrics', [])
        strengths = [m['name'] for m in metrics if m.get('percentile', 50) >= 60]
        weaknesses = [m['name'] for m in metrics if m.get('percentile', 50) < 40]

        report = f"""## 종합 진단 요약

**소속 군집**: {cluster_name}
**부도 위험도**: {risk} ({prob*100:.1f}%)

### 강점
{', '.join(strengths) if strengths else '특별히 두드러진 강점 없음'}

### 개선 필요 영역
{', '.join(weaknesses) if weaknesses else '전반적으로 양호'}

### 제언
"""
        if risk == 'High':
            report += "부채 관리와 유동성 확보에 즉각적인 조치가 필요합니다."
        elif risk == 'Medium':
            report += "현재 수준을 유지하면서 약점 영역 개선에 집중하세요."
        else:
            report += "현재 재무 상태가 양호합니다. 지속적인 모니터링을 권장합니다."

        return report

    def interpret_shap_values(
        self,
        shap_values: Dict,
        default_prediction: Dict
    ) -> str:
        """
        SHAP 값을 LLM으로 해석하여 위험 요인 설명

        Args:
            shap_values: SHAP 값 딕셔너리 {'contributions': [...], ...}
            default_prediction: 부도예측 결과

        Returns:
            위험 요인 해석 문자열
        """
        client, config = self._get_llm_client()

        # contributions 리스트 추출
        contributions = shap_values.get('contributions', []) if shap_values else []

        if client is None or not contributions:
            return self._rule_based_shap_interpretation(shap_values, default_prediction)

        try:
            # 상위 5개 영향 요인 추출 (이미 정렬되어 있음)
            top_contributions = contributions[:5]

            # 피처명 한글 매핑
            feature_names = {
                'R006': '부채비율', 'R008': '유동비율', 'R015': '영업이익률',
                'R018': 'ROE', 'FN2_1': '매출액', 'R012': '차입금의존도',
                'DA0D00021': '연체건수', 'N006': 'EBITDA마진율', 'R002': '매출증가율'
            }

            factors = []
            for contrib in top_contributions:
                feature = contrib.get('feature_name', '')
                value = contrib.get('shap_value', 0)
                name = feature_names.get(feature.upper(), feature)
                direction = "위험 증가" if value > 0 else "위험 감소"
                factors.append(f"- {name}: {direction} (영향도: {abs(value):.3f})")

            prompt = f"""
기업의 부도확률이 {default_prediction.get('default_probability', 0)*100:.1f}%로 예측되었습니다.
다음은 부도 위험에 가장 큰 영향을 미친 요인들입니다:

{chr(10).join(factors)}

이 기업의 위험 요인을 2-3문장으로 간결하게 설명해주세요.
왜 위험한지, 어떤 지표가 문제인지 구체적으로 설명하세요.
"""

            response = client.models.generate_content(
                model=config['model_id'],
                contents=prompt
            )
            return response.text

        except Exception as e:
            print(f"⚠️ SHAP 해석 실패: {e}")
            return self._rule_based_shap_interpretation(shap_values, default_prediction)

    def _rule_based_shap_interpretation(
        self,
        shap_values: Dict,
        default_prediction: Dict
    ) -> str:
        """규칙 기반 SHAP 해석 (LLM 폴백)"""
        if not shap_values:
            return "위험 요인 분석 데이터가 없습니다."

        # contributions 리스트에서 추출
        contributions = shap_values.get('contributions', [])
        if not contributions:
            return "위험 요인 분석 데이터가 없습니다."

        # 상위 5개 요인 추출 (이미 정렬되어 있음)
        top_contributions = contributions[:5]

        risk_increase = []  # 위험 증가 요인
        risk_decrease = []  # 위험 감소 요인

        for contrib in top_contributions:
            # feature_name은 이미 한글로 변환되어 있음
            name = contrib.get('feature_name', '')
            value = contrib.get('shap_value', 0)
            pct = contrib.get('contribution_pct', 0)

            if value > 0:
                risk_increase.append(f"{name}({pct:.1f}%)")
            else:
                risk_decrease.append(f"{name}({pct:.1f}%)")

        # 결과 생성
        parts = []
        if risk_increase:
            parts.append(f"**위험 증가 요인**: {', '.join(risk_increase[:3])}")
        if risk_decrease:
            parts.append(f"**위험 감소 요인**: {', '.join(risk_decrease[:2])}")

        prob = default_prediction.get('default_probability', 0)
        risk = default_prediction.get('risk_level', 'Unknown')

        if risk == 'High':
            parts.append("현재 부도 위험이 높은 상태이며, 즉각적인 재무 개선이 필요합니다.")
        elif risk == 'Medium':
            parts.append("주의가 필요한 수준입니다. 위험 증가 요인에 대한 관리가 권장됩니다.")
        else:
            parts.append("현재 재무 상태가 비교적 안정적입니다.")

        return " ".join(parts) if parts else "위험 요인 분석을 수행할 수 없습니다."

    # ========================================================================
    # 레이더 차트 생성
    # ========================================================================

    def generate_radar_chart(
        self,
        company_features: Dict,
        benchmark: Dict,
        output_format: str = 'base64'
    ) -> Optional[str]:
        """
        레이더 차트 이미지 생성

        Args:
            company_features: 기업 피처
            benchmark: 벤치마크 결과
            output_format: 'base64' 또는 'file_path'

        Returns:
            base64 인코딩된 이미지 또는 파일 경로
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # 백엔드 설정
            import matplotlib.pyplot as plt
            import numpy as np

            # 한글 폰트 설정
            try:
                plt.rcParams['font.family'] = 'AppleGothic'
                plt.rcParams['axes.unicode_minus'] = False
            except:
                pass

            radar_data = benchmark.get('radar_data', [])
            if not radar_data:
                return None

            # 데이터 준비
            labels = [d['metric'] for d in radar_data]
            company_values = [d['company'] for d in radar_data]
            cluster_avg = [d['cluster_avg'] for d in radar_data]

            num_vars = len(labels)
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            angles += angles[:1]

            company_values += company_values[:1]
            cluster_avg += cluster_avg[:1]

            # 차트 생성
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

            ax.plot(angles, company_values, 'o-', linewidth=2, label='입력 기업', color='#e74c3c')
            ax.fill(angles, company_values, alpha=0.25, color='#e74c3c')

            ax.plot(angles, cluster_avg, 'o-', linewidth=2, label='클러스터 평균', color='#3498db')
            ax.fill(angles, cluster_avg, alpha=0.1, color='#3498db')

            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels, size=10)
            ax.set_ylim(0, 100)
            ax.set_yticklabels([])

            plt.title('기업 재무 포지션 분석', size=14, y=1.08)
            plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
            plt.tight_layout()

            if output_format == 'base64':
                # base64로 인코딩
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close(fig)
                return f"data:image/png;base64,{image_base64}"
            else:
                # 파일로 저장
                output_dir = project_root / 'ml' / 'outputs' / 'clustering'
                output_dir.mkdir(parents=True, exist_ok=True)
                file_path = output_dir / 'radar_chart_latest.png'
                plt.savefig(file_path, dpi=100, bbox_inches='tight')
                plt.close(fig)
                return str(file_path)

        except Exception as e:
            print(f"⚠️ 레이더 차트 생성 실패: {e}")
            return None


# 싱글톤 인스턴스
_clustering_service = None


def get_clustering_service() -> ClusteringService:
    """클러스터링 서비스 싱글톤 인스턴스 반환"""
    global _clustering_service
    if _clustering_service is None:
        _clustering_service = ClusteringService()
    return _clustering_service


def reload_clustering_service() -> ClusteringService:
    """
    클러스터링 서비스 리로드 (새 모델 로드)

    MLflow Registry에서 최신 Production 모델을 다시 로드합니다.

    Returns:
        ClusteringService: 새로 로드된 서비스 인스턴스
    """
    global _clustering_service
    print("🔄 클러스터링 서비스 리로드 중...")

    # 기존 인스턴스 삭제
    _clustering_service = None

    # 새 인스턴스 생성 (최신 모델 로드)
    _clustering_service = ClusteringService()

    print("✅ 클러스터링 서비스 리로드 완료")
    return _clustering_service
