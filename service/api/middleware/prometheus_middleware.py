"""
Prometheus 메트릭 미들웨어

FastAPI 애플리케이션의 메트릭을 Prometheus 포맷으로 노출합니다.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict
from collections import defaultdict
import threading


class PrometheusMetrics:
    """Prometheus 메트릭 수집기"""

    def __init__(self):
        self._lock = threading.Lock()

        # 요청 카운터
        self.request_count: Dict[str, int] = defaultdict(int)

        # 에러 카운터
        self.error_count: Dict[str, int] = defaultdict(int)

        # 응답 시간 (합계, 개수)
        self.response_time_sum: Dict[str, float] = defaultdict(float)
        self.response_time_count: Dict[str, int] = defaultdict(int)

        # 예측 관련 메트릭
        self.prediction_count = 0
        self.prediction_latency_sum = 0.0
        self.prediction_latency_count = 0

        # 업로드 관련 메트릭
        self.upload_count = 0
        self.upload_success = 0
        self.upload_failed = 0

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """요청 메트릭 기록"""
        with self._lock:
            key = f"{method}_{endpoint}"
            self.request_count[key] += 1
            self.response_time_sum[key] += duration
            self.response_time_count[key] += 1

            if status_code >= 400:
                error_key = f"{method}_{endpoint}_{status_code}"
                self.error_count[error_key] += 1

    def record_prediction(self, latency_ms: float):
        """예측 메트릭 기록"""
        with self._lock:
            self.prediction_count += 1
            self.prediction_latency_sum += latency_ms
            self.prediction_latency_count += 1

    def record_upload(self, success: bool):
        """업로드 메트릭 기록"""
        with self._lock:
            self.upload_count += 1
            if success:
                self.upload_success += 1
            else:
                self.upload_failed += 1

    def get_metrics(self) -> str:
        """Prometheus 포맷으로 메트릭 반환"""
        lines = []

        # HELP 및 TYPE 정의
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")

        with self._lock:
            # 요청 카운터
            for key, count in self.request_count.items():
                parts = key.split("_", 1)
                method = parts[0]
                endpoint = parts[1] if len(parts) > 1 else "unknown"
                lines.append(f'http_requests_total{{method="{method}",endpoint="{endpoint}"}} {count}')

            # 에러 카운터
            lines.append("")
            lines.append("# HELP http_errors_total Total HTTP errors")
            lines.append("# TYPE http_errors_total counter")
            for key, count in self.error_count.items():
                parts = key.rsplit("_", 1)
                method_endpoint = parts[0]
                status = parts[1] if len(parts) > 1 else "unknown"
                me_parts = method_endpoint.split("_", 1)
                method = me_parts[0]
                endpoint = me_parts[1] if len(me_parts) > 1 else "unknown"
                lines.append(f'http_errors_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}')

            # 응답 시간
            lines.append("")
            lines.append("# HELP http_request_duration_seconds HTTP request duration in seconds")
            lines.append("# TYPE http_request_duration_seconds summary")
            for key, total in self.response_time_sum.items():
                count = self.response_time_count.get(key, 1)
                parts = key.split("_", 1)
                method = parts[0]
                endpoint = parts[1] if len(parts) > 1 else "unknown"
                avg = total / count if count > 0 else 0
                lines.append(f'http_request_duration_seconds_sum{{method="{method}",endpoint="{endpoint}"}} {total:.4f}')
                lines.append(f'http_request_duration_seconds_count{{method="{method}",endpoint="{endpoint}"}} {count}')

            # 예측 메트릭
            lines.append("")
            lines.append("# HELP ml_predictions_total Total ML predictions")
            lines.append("# TYPE ml_predictions_total counter")
            lines.append(f"ml_predictions_total {self.prediction_count}")

            lines.append("")
            lines.append("# HELP ml_prediction_latency_ms ML prediction latency in milliseconds")
            lines.append("# TYPE ml_prediction_latency_ms summary")
            lines.append(f"ml_prediction_latency_ms_sum {self.prediction_latency_sum:.2f}")
            lines.append(f"ml_prediction_latency_ms_count {self.prediction_latency_count}")

            # 업로드 메트릭
            lines.append("")
            lines.append("# HELP file_uploads_total Total file uploads")
            lines.append("# TYPE file_uploads_total counter")
            lines.append(f'file_uploads_total{{status="success"}} {self.upload_success}')
            lines.append(f'file_uploads_total{{status="failed"}} {self.upload_failed}')

        return "\n".join(lines)


# 싱글톤 인스턴스
_metrics_instance = None


def get_metrics() -> PrometheusMetrics:
    """메트릭 싱글톤 인스턴스 가져오기"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PrometheusMetrics()
    return _metrics_instance


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Prometheus 메트릭 수집 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        # /metrics 엔드포인트는 측정하지 않음
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            metrics = get_metrics()
            metrics.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=status_code,
                duration=duration
            )

        return response
