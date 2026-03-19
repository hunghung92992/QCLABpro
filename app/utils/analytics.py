# -*- coding: utf-8 -*-
"""
app/shared/logic/analytics.py
(Hoàn thiện - Lượt 137)
Logic tính toán cho Phân tích Nâng cao (Sigma, Lot-to-Lot).
"""

import math
from typing import List, Tuple, Optional, Dict, Any


# --- Logic tính toán chung ---

def _to_float(x: Any) -> Optional[float]:
    """Helper nội bộ để ép kiểu an toàn."""
    try:
        if x is None: return None
        s = str(x).strip().replace(",", ".")
        if s == "": return None
        return float(s)
    except Exception:
        return None


def compute_stats(values: List[float]) -> Dict[str, Any]:
    """Tính toán thống kê cơ bản từ một danh sách các giá trị."""
    if not values:
        return {"n": 0, "mean": None, "sd": None, "cv": None}

    try:
        n = len(values)
        mean = sum(values) / n

        if n > 1:
            variance = sum((x - mean) ** 2 for x in values) / (n - 1)
            sd = math.sqrt(variance)
        else:
            sd = None  # Không thể tính SD nếu chỉ có 1 điểm

        cv = safe_cv_percent(mean, sd)

        return {"n": n, "mean": mean, "sd": sd, "cv": cv}

    except Exception as e:
        print(f"Lỗi compute_stats: {e}")
        return {"n": 0, "mean": None, "sd": None, "cv": None}


def safe_cv_percent(mean: Optional[float], sd: Optional[float]) -> Optional[float]:
    """Tính CV% an toàn (tránh chia cho 0)."""
    if mean is None or sd is None or mean == 0:
        return None
    return abs((sd / mean) * 100.0)


def calculate_bias_percent(lab_mean: Optional[float], target_mean: Optional[float]) -> Optional[float]:
    """
    (MỚI) Tính Độ chệch (Bias) theo phần trăm.
    Bias % = ((Lab Mean - Target Mean) / Target Mean) * 100
    """
    if lab_mean is None or target_mean is None:
        return None

    # (MỚI) Xử lý chia cho 0
    if target_mean == 0:
        if lab_mean == 0:
            return 0.0  # Nếu cả hai là 0, bias là 0%
        else:
            return None  # Không thể tính % bias nếu target là 0

    bias = lab_mean - target_mean
    return (bias / target_mean) * 100.0
# --- Logic cho Phân tích Sigma ---

def calculate_sigma(lab_mean: float, lab_sd: float,
                    target_mean: float, tea_abs: float) -> Optional[float]:
    """
    Tính Sigma Metric (6-Sigma).
    Sigma = (TEa - |Bias|) / SD
    """
    if lab_sd == 0:
        return None  # Không thể tính nếu SD=0

    bias_abs = abs(lab_mean - target_mean)

    sigma = (tea_abs - bias_abs) / lab_sd

    # Sigma có thể là số âm nếu Bias > TEa
    return sigma


# --- Logic cho So sánh Lot-to-Lot ---

def deming_regression(x: List[float], y: List[float], lambda_val: float = 1.0) -> Tuple[
    Optional[float], Optional[float]]:
    """
    Tính toán Hồi quy Deming (Deming Regression).
    Trả về (slope, intercept).
    """
    n = len(x)
    if n < 2 or n != len(y):
        return None, None

    xm = sum(x) / n
    ym = sum(y) / n

    try:
        Sxx = sum((xi - xm) ** 2 for xi in x) / (n - 1)
        Syy = sum((yi - ym) ** 2 for yi in y) / (n - 1)
        Sxy = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y)) / (n - 1)

        if abs(Sxy) < 1e-12:
            return None, None  # Không có tương quan

        b = (Syy - lambda_val * Sxx + math.sqrt((Syy - lambda_val * Sxx) ** 2 + 4 * lambda_val * Sxy ** 2)) / (2 * Sxy)
        a = ym - b * xm
        return b, a
    except (ValueError, OverflowError, ZeroDivisionError):
        return None, None


def bland_altman_stats(x: List[float], y: List[float]) -> Dict[str, Optional[float]]:
    """
    Tính toán Thống kê Bland-Altman.
    Trả về: {mean_diff, sd_diff, loa_low, loa_high}
    """
    if len(x) < 2 or len(x) != len(y):
        return {"mean_diff": None, "sd_diff": None, "loa_low": None, "loa_high": None}

    diffs = [(xi - yi) for xi, yi in zip(x, y)]
    n = len(diffs)

    mean_diff = sum(diffs) / n
    sd_diff = (sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)) ** 0.5

    loa_low = mean_diff - 1.96 * sd_diff
    loa_high = mean_diff + 1.96 * sd_diff

    return {
        "mean_diff": mean_diff,
        "sd_diff": sd_diff,
        "loa_low": loa_low,
        "loa_high": loa_high
    }


# --- Thêm vào cuối file app/shared/logic/analytics.py ---

def calculate_measurement_uncertainty(lab_sd: float, bias_abs: float, k: float = 2.0) -> Dict[str, Any]:
    """
    Tính độ không đảm bảo đo (MU) theo mô hình Nordtest (đơn giản hóa).
    u_c = sqrt(u_Rw^2 + u_bias^2)
    Trong đó:
      - u_Rw = Lab SD (Độ lệch chuẩn nội kiểm dài hạn)
      - u_bias = RMSE hoặc Bias tuyệt đối (để an toàn, ta dùng Bias tuyệt đối)
    """
    try:
        # 1. Độ không đảm bảo đo chuẩn tổng hợp (Combined Standard Uncertainty)
        # u_c = sqrt(SD^2 + Bias^2)
        u_c = math.sqrt(lab_sd ** 2 + bias_abs ** 2)

        # 2. Độ không đảm bảo đo mở rộng (Expanded Uncertainty)
        U_expanded = u_c * k

        return {
            "u_c": u_c,
            "U_expanded": U_expanded,
            "k": k
        }
    except Exception:
        return {"u_c": 0, "U_expanded": 0, "k": k}