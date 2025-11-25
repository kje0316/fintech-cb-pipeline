"""
로그 DB 저장 서비스

PostgreSQL에 예측 로그, 업로드 로그, 성능 로그 저장
"""
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import Dict, Optional, List
import uuid
from datetime import datetime
from contextlib import contextmanager
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config_loader import config


class LoggingService:
    """로그 DB 저장 서비스"""

    def __init__(self):
        """PostgreSQL 연결 설정 (config/local_settings.yaml에서 로드)"""
        db_cfg = config['db']
        self.db_config = {
            'host': db_cfg['host'],
            'port': int(db_cfg['port']),
            'database': db_cfg['db_name'],
            'user': db_cfg['user'],
            'password': db_cfg.get('password', ''),
        }

    @contextmanager
    def get_connection(self):
        """DB 연결 컨텍스트 매니저"""
        conn = psycopg2.connect(**self.db_config)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def log_prediction(
        self,
        input_data: Dict,
        derived_features: Dict,
        prediction_result: Dict,
        model_version: str,
        model_type: str,
        inference_time_ms: int,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        validation_errors: Optional[Dict] = None
    ) -> str:
        """
        예측 로그 저장

        Returns:
            request_id (UUID)
        """
        request_id = str(uuid.uuid4())

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO logs.prediction_logs (
                        request_id, user_id, session_id, ip_address,
                        input_data, derived_features, prediction_result,
                        default_probability, risk_level,
                        model_version, model_type,
                        inference_time_ms, validation_errors
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s
                    )
                """, (
                    request_id, user_id, session_id, ip_address,
                    Json(input_data), Json(derived_features), Json(prediction_result),
                    prediction_result.get('default_probability'),
                    prediction_result.get('risk_level'),
                    model_version, model_type,
                    inference_time_ms, Json(validation_errors) if validation_errors else None
                ))

        return request_id

    def log_upload(
        self,
        file_name: str,
        file_size: int,
        file_hash: str,
        status: str,
        rows_processed: int,
        rows_valid: int,
        rows_invalid: int,
        prediction_ids: List[str],
        processing_time_ms: int,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        error_message: Optional[str] = None,
        validation_errors: Optional[Dict] = None
    ) -> str:
        """
        업로드 로그 저장

        Returns:
            upload_id (UUID)
        """
        upload_id = str(uuid.uuid4())

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO logs.upload_logs (
                        upload_id, user_id, ip_address,
                        file_name, file_size, file_hash,
                        status, error_message, validation_errors,
                        rows_processed, rows_valid, rows_invalid,
                        prediction_ids, processing_time_ms
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s
                    )
                """, (
                    upload_id, user_id, ip_address,
                    file_name, file_size, file_hash,
                    status, error_message, Json(validation_errors) if validation_errors else None,
                    rows_processed, rows_valid, rows_invalid,
                    prediction_ids, processing_time_ms
                ))

        return upload_id

    def log_model_performance(
        self,
        model_version: str,
        model_type: str,
        auc_roc: float,
        precision_score: Optional[float] = None,
        recall: Optional[float] = None,
        f1_score: Optional[float] = None,
        psi_score: Optional[float] = None,
        ks_statistic: Optional[float] = None,
        ks_pvalue: Optional[float] = None,
        avg_prediction: Optional[float] = None,
        std_prediction: Optional[float] = None,
        evaluation_period_start: Optional[datetime] = None,
        evaluation_period_end: Optional[datetime] = None,
        sample_size: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        모델 성능 로그 저장

        Returns:
            log_id
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO logs.model_performance_logs (
                        model_version, model_type,
                        auc_roc, precision_score, recall, f1_score,
                        psi_score, ks_statistic, ks_pvalue,
                        avg_prediction, std_prediction,
                        evaluation_period_start, evaluation_period_end,
                        sample_size, notes
                    ) VALUES (
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s
                    ) RETURNING id
                """, (
                    model_version, model_type,
                    auc_roc, precision_score, recall, f1_score,
                    psi_score, ks_statistic, ks_pvalue,
                    avg_prediction, std_prediction,
                    evaluation_period_start, evaluation_period_end,
                    sample_size, notes
                ))

                log_id = cur.fetchone()[0]

        return log_id

    def update_actual_label(
        self,
        request_id: str,
        actual_default: bool,
        actual_default_date: Optional[datetime] = None
    ):
        """실제 라벨 업데이트 (Ground Truth)"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE logs.prediction_logs
                    SET actual_default = %s,
                        actual_default_date = %s,
                        label_updated_at = NOW()
                    WHERE request_id = %s
                """, (actual_default, actual_default_date, request_id))

    def get_predictions_for_drift_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
        model_version: Optional[str] = None
    ) -> List[Dict]:
        """Drift 분석용 예측 데이터 조회"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        request_id,
                        created_at,
                        input_data,
                        derived_features,
                        default_probability,
                        risk_level,
                        model_version,
                        actual_default
                    FROM logs.prediction_logs
                    WHERE created_at BETWEEN %s AND %s
                """
                params = [start_date, end_date]

                if model_version:
                    query += " AND model_version = %s"
                    params.append(model_version)

                query += " ORDER BY created_at"

                cur.execute(query, params)
                return cur.fetchall()

    def get_model_performance_history(
        self,
        model_version: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """모델 성능 히스토리 조회"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT *
                    FROM logs.model_performance_logs
                """
                params = []

                if model_version:
                    query += " WHERE model_version = %s"
                    params.append(model_version)

                query += " ORDER BY logged_at DESC LIMIT %s"
                params.append(limit)

                cur.execute(query, params)
                return cur.fetchall()

    def log_api_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        response_time_ms: int,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        error_message: Optional[str] = None,
        error_traceback: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_body_size: Optional[int] = None,
        response_body_size: Optional[int] = None
    ):
        """API 요청/응답 로그 저장"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO logs.api_logs (
                        method, endpoint, user_id, session_id, ip_address,
                        status_code, response_time_ms,
                        error_message, error_traceback,
                        user_agent, request_body_size, response_body_size
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s
                    )
                """, (
                    method, endpoint, user_id, session_id, ip_address,
                    status_code, response_time_ms,
                    error_message, error_traceback,
                    user_agent, request_body_size, response_body_size
                ))


# Singleton 인스턴스
_logging_service_instance = None


def get_logging_service() -> LoggingService:
    """로깅 서비스 싱글톤 인스턴스 가져오기"""
    global _logging_service_instance
    if _logging_service_instance is None:
        _logging_service_instance = LoggingService()
    return _logging_service_instance
