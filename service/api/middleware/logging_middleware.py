"""
API 로깅 미들웨어

모든 API 요청/응답을 로깅합니다.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import traceback
from service.api.services.logging_service import get_logging_service


class APILoggingMiddleware(BaseHTTPMiddleware):
    """
    모든 API 요청/응답 로깅 미들웨어

    로깅 대상:
    - /api/** (모든 API 엔드포인트)

    제외:
    - /health (헬스체크, 너무 많음)
    - /docs, /openapi.json (문서)
    """

    async def dispatch(self, request: Request, call_next):
        # 제외 경로 체크
        excluded_paths = ['/health', '/docs', '/openapi.json', '/redoc']
        if any(request.url.path.startswith(path) for path in excluded_paths):
            return await call_next(request)

        # 시작 시간
        start_time = time.time()

        # 요청 정보 추출
        method = request.method
        endpoint = request.url.path
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')

        # 사용자 정보 (인증 구현 시)
        user_id = request.state.user_id if hasattr(request.state, 'user_id') else None
        session_id = request.cookies.get('session_id')

        # 요청 처리
        status_code = 500  # 기본값 (에러 발생 시)
        error_message = None
        error_traceback = None

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            # 에러 발생
            status_code = 500
            error_message = str(e)
            error_traceback = traceback.format_exc()

            # 에러 응답 생성
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )

        # 응답 시간 계산
        response_time_ms = int((time.time() - start_time) * 1000)

        # DB에 로깅 (비동기, 백그라운드)
        try:
            logging_service = get_logging_service()
            logging_service.log_api_request(
                method=method,
                endpoint=endpoint,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=error_message,
                error_traceback=error_traceback,
                user_agent=user_agent
            )
        except Exception as log_error:
            # 로깅 실패는 무시 (메인 요청에 영향 없도록)
            print(f"Failed to log API request: {log_error}")

        return response
