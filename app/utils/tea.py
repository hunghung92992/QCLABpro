# -*- coding: utf-8 -*-
"""
app/shared/logic/tea.py
(Ported từ tea.py)
Logic tính toán liên quan đến TEa (Total Error Allowable).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, Any
import math


@dataclass(frozen=True)
class TeaMetrics:
    """Lớp chứa các chỉ số đã tính toán."""
    bias_percent: Optional[float]
    cv_percent: Optional[float]
    sigma: Optional[float]


def _safe_div(n: Optional[float], d: Optional[float]) -> Optional[float]:
    """Phép chia an toàn, trả về None nếu mẫu số là 0 hoặc None."""
    if n is None or d is None:
        return None
    try:
        if d == 0:
            return None
        return n / d
    except Exception:
        return None


def calc_bias_percent(target: float, mean: float) -> Optional[float]:
    """Tính % Sai số (Bias)."""
    if target == 0 or math.isnan(target) or math.isnan(mean):
        return None
    return abs(mean - target) / abs(target) * 100.0


def calc_cv_percent(std: float, mean: float) -> Optional[float]:
    """Tính % Hệ số biến thiên (CV)."""
    if mean == 0 or math.isnan(mean) or math.isnan(std):
        return None
    ratio = _safe_div(std, mean)
    # CV luôn là số dương
    return None if ratio is None else abs(ratio * 100.0)


def calc_sigma(tea_percent: float, bias_percent: Optional[float], cv_percent: Optional[float]) -> Optional[float]:
    """Tính Sigma Metric theo công thức (TEa% - |Bias%|) / CV%."""
    if tea_percent <= 0:
        return None
    if bias_percent is None or cv_percent is None or cv_percent == 0:
        return None

    return (tea_percent - abs(bias_percent)) / cv_percent


def evaluate_tea_metrics(
        mean: float,
        std: float,
        target: float,
        tea_percent: float
) -> TeaMetrics:
    """Tính toán bộ chỉ số (Bias, CV, Sigma) từ dữ liệu thống kê."""
    bias = calc_bias_percent(target, mean)
    cv = calc_cv_percent(std, mean)
    sigma = calc_sigma(tea_percent, bias, cv)

    return TeaMetrics(bias_percent=bias, cv_percent=cv, sigma=sigma)


def check_single_point(result: float, target: float, tea_percent: float) -> bool:
    """Kiểm tra 1 điểm có nằm trong ngưỡng TEa hay không."""
    single_bias = calc_bias_percent(target, result)
    if single_bias is None:
        return False  # Không thể xác định (ví dụ target = 0)
    return abs(single_bias) <= tea_percent