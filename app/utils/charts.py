# -*- coding: utf-8 -*-
"""
app/shared/logic/charts.py
(ĐÃ CẬP NHẬT GĐ 8)
Logic tính toán thống kê cho biểu đồ.
Sửa lỗi: Dùng statistics.stdev (n-1) thay vì pstdev (n).
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import statistics
import math


def basic_stats(values: List[float]) -> Dict[str, float]:
    """Tính toán N, Mean, SD (stdev, n-1), CV%."""
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return {"n": 0, "mean": float("nan"), "sd": float("nan"), "cv": float("nan")}

    n = len(vals)
    mean = statistics.fmean(vals)

    if n < 2:
        # Không thể tính SD và CV nếu chỉ có 1 điểm
        return {"n": n, "mean": mean, "sd": float("nan"), "cv": float("nan")}

    # SỬA LỖI: Dùng stdev (SD của mẫu, n-1)
    sd = statistics.stdev(vals)

    cv = (sd / mean * 100.0) if (mean != 0.0 and not math.isnan(mean)) else float("nan")

    return {"n": n, "mean": mean, "sd": sd, "cv": cv}