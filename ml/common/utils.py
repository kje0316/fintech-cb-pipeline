"""
Common utilities for all ML models

공통 유틸리티 함수들
"""
import numpy as np
from typing import Any, Union


def safe_divide(
    numerator: Union[int, float],
    denominator: Union[int, float],
    default: float = 0.0
) -> float:
    """
    안전한 나눗셈 (0으로 나누기 방지)

    Args:
        numerator: 분자
        denominator: 분모
        default: 나눗셈 불가능 시 반환값

    Returns:
        나눗셈 결과 또는 default 값
    """
    if denominator == 0 or np.isnan(denominator) or np.isinf(denominator):
        return default

    if np.isnan(numerator) or np.isinf(numerator):
        return default

    result = numerator / denominator

    if np.isnan(result) or np.isinf(result):
        return default

    return result


def handle_missing(value: Any, default: Any = 0.0) -> Any:
    """
    결측치 처리

    Args:
        value: 입력 값
        default: 결측 시 기본값

    Returns:
        처리된 값
    """
    if value is None:
        return default

    if isinstance(value, (int, float)):
        if np.isnan(value) or np.isinf(value):
            return default

    return value
