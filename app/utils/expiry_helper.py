# -*- coding: utf-8 -*-
"""
app/shared/utils/expiry_helper.py
(Ported từ qc_expiry.py)
Tiện ích kiểm tra trạng thái Hạn sử dụng.
"""

from __future__ import annotations
import datetime as _dt
from typing import Optional, Tuple, Union

# Số ngày cảnh báo mặc định
DEFAULT_WARN_DAYS = 30


def parse_date(s: Optional[Union[str, _dt.date, _dt.datetime]]) -> Optional[_dt.date]:
    """Parse nhiều định dạng ngày/chuỗi ngày một cách an toàn."""
    if not s: return None
    if isinstance(s, _dt.datetime): return s.date()
    if isinstance(s, _dt.date): return s

    s_date = str(s).strip().split(" ")[0]  # Lấy phần ngày nếu là timestamp

    # Ưu tiên ISO
    try:
        return _dt.date.fromisoformat(s_date)
    except (ValueError, TypeError):
        pass

    # Thử các định dạng phổ biến khác
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return _dt.datetime.strptime(s_date, fmt).date()
        except Exception:
            continue

    return None


def evaluate_expiry(
        expiry_date: Optional[Union[str, _dt.date]],
        warn_days: Optional[int] = None,
        today: Optional[_dt.date] = None
) -> Tuple[str, Optional[int]]:
    """
    Đánh giá trạng thái HSD.
    Trả về (status, days_left)
      - status: "expired", "near_expiry", "ok", hoặc "unknown"
      - days_left: Số ngày còn lại (có thể âm)
    """
    warn = int(warn_days if warn_days is not None else DEFAULT_WARN_DAYS)
    exp = parse_date(expiry_date)
    if not exp:
        return "unknown", None

    d0 = today or _dt.date.today()
    delta_days = (exp - d0).days

    if delta_days < 0:
        return "expired", delta_days
    if delta_days <= warn:
        return "near_expiry", delta_days

    return "ok", delta_days