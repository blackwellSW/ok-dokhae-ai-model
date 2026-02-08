"""
Google Cloud Logging 통합
역할: 프로덕션 환경에서 Cloud Logging으로 로그 전송

Cloud Run에서 실행 시:
- 자동으로 Cloud Logging에 구조화된 로그 전송
- 로컬 환경에서는 표준 Python 로깅 사용

로그 레벨:
- DEBUG: 디버그 정보
- INFO: 일반 정보 (API 호출, 성공 등)
- WARNING: 경고 (fallback 사용 등)
- ERROR: 오류 (실패 등)
"""

import os
import logging
import sys
from typing import Optional
from functools import lru_cache

# Cloud Logging 사용 여부 (Cloud Run 환경에서 자동 감지)
_USE_CLOUD_LOGGING = os.getenv("K_SERVICE") is not None  # Cloud Run 환경 변수

# Cloud Logging 클라이언트 (lazy init)
_cloud_logging_client = None
_cloud_handler = None


def _init_cloud_logging():
    """Cloud Logging 초기화"""
    global _cloud_logging_client, _cloud_handler

    if _cloud_handler is not None:
        return _cloud_handler

    try:
        from google.cloud import logging as cloud_logging

        _cloud_logging_client = cloud_logging.Client()

        # Cloud Logging 핸들러 생성
        _cloud_handler = cloud_logging.handlers.CloudLoggingHandler(
            _cloud_logging_client,
            name="ok-dokhae-backend"
        )
        _cloud_handler.setLevel(logging.DEBUG)

        # 구조화된 로그 포맷
        formatter = logging.Formatter(
            '%(levelname)s - %(name)s - %(message)s'
        )
        _cloud_handler.setFormatter(formatter)

        return _cloud_handler

    except Exception as e:
        print(f"Cloud Logging 초기화 실패 (로컬 로깅 사용): {e}")
        return None


def _init_local_logging() -> logging.Handler:
    """로컬 로깅 핸들러 초기화"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # 컬러풀한 로컬 로그 포맷
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    return handler


@lru_cache(maxsize=100)
def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    로거 인스턴스 반환

    Args:
        name: 로거 이름 (보통 __name__ 사용)
        level: 로그 레벨

    Returns:
        설정된 Logger 인스턴스

    사용 예:
        logger = get_logger(__name__)
        logger.info("세션 생성 성공")
        logger.error("오류 발생", exc_info=True)
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 이미 핸들러가 있으면 재사용
    if logger.handlers:
        return logger

    # Cloud Run 환경이면 Cloud Logging 사용
    if _USE_CLOUD_LOGGING:
        handler = _init_cloud_logging()
        if handler:
            logger.addHandler(handler)
            return logger

    # 로컬 환경이면 표준 로깅 사용
    handler = _init_local_logging()
    logger.addHandler(handler)

    return logger


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    user_id: Optional[str] = None,
    extra: Optional[dict] = None
):
    """
    API 요청 로깅 헬퍼

    Args:
        logger: 로거 인스턴스
        method: HTTP 메소드
        path: 요청 경로
        user_id: 사용자 ID (인증된 경우)
        extra: 추가 정보
    """
    msg = f"API Request: {method} {path}"
    if user_id:
        msg += f" | user={user_id}"
    if extra:
        msg += f" | {extra}"
    logger.info(msg)


def log_api_response(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    extra: Optional[dict] = None
):
    """
    API 응답 로깅 헬퍼

    Args:
        logger: 로거 인스턴스
        method: HTTP 메소드
        path: 요청 경로
        status_code: 응답 상태 코드
        duration_ms: 처리 시간 (밀리초)
        extra: 추가 정보
    """
    msg = f"API Response: {method} {path} | status={status_code} | {duration_ms:.2f}ms"
    if extra:
        msg += f" | {extra}"

    if status_code >= 500:
        logger.error(msg)
    elif status_code >= 400:
        logger.warning(msg)
    else:
        logger.info(msg)


def log_model_call(
    logger: logging.Logger,
    model: str,
    success: bool,
    latency_ms: Optional[float] = None,
    tokens: Optional[int] = None,
    error: Optional[str] = None
):
    """
    AI 모델 호출 로깅 헬퍼

    Args:
        logger: 로거 인스턴스
        model: 모델 이름 (vertex-ai/classical-lit, gemini-pro)
        success: 성공 여부
        latency_ms: 응답 시간 (밀리초)
        tokens: 사용된 토큰 수
        error: 오류 메시지
    """
    status = "SUCCESS" if success else "FAILED"
    msg = f"Model Call: {model} | {status}"

    if latency_ms:
        msg += f" | {latency_ms:.2f}ms"
    if tokens:
        msg += f" | tokens={tokens}"
    if error:
        msg += f" | error={error}"

    if success:
        logger.info(msg)
    else:
        logger.error(msg)


def log_session_event(
    logger: logging.Logger,
    event: str,
    session_id: str,
    user_id: Optional[str] = None,
    extra: Optional[dict] = None
):
    """
    세션 이벤트 로깅 헬퍼

    Args:
        logger: 로거 인스턴스
        event: 이벤트 유형 (created, message, ended)
        session_id: 세션 ID
        user_id: 사용자 ID
        extra: 추가 정보
    """
    msg = f"Session Event: {event} | session={session_id}"
    if user_id:
        msg += f" | user={user_id}"
    if extra:
        msg += f" | {extra}"
    logger.info(msg)
