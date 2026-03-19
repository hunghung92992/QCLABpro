# -*- coding: utf-8 -*-
"""
app/shared/utils/validators.py
(Ported từ validators.py)
Các hàm kiểm tra và ép kiểu an toàn.
"""
from __future__ import annotations
from typing import Optional, Any

def to_float_safe(x: Any) -> Optional[float]:
    """Ép kiểu sang float an toàn, chấp nhận None, "" và dấu phẩy."""
    try:
        if x is None: return None
        s = str(x).strip().replace(",", ".")
        if s == "": return None
        return float(s)
    except (ValueError, TypeError):
        return None

def to_bool_safe(x: Any) -> Optional[int]:
    """
    Ép kiểu sang 0/1 an toàn (cho POS/NEG/Dương/Âm).
    Trả về 1 (True), 0 (False), hoặc None (Không xác định).
    """
    if x is None: return None
    s = str(x).strip().lower()
    if s in ("1", "true", "yes", "pos", "+", "positive", "dương", "duong"):
        return 1
    if s in ("0", "false", "no", "neg", "-", "negative", "âm", "am"):
        return 0
    return None

def clamp_float(v: Any, lo: Optional[float] = None, hi: Optional[float] = None) -> Optional[float]:
    """Ép kiểu float và giới hạn trong khoảng [lo, hi]."""
    x = to_float_safe(v)
    if x is None:
        return None
    if lo is not None and x < lo:
        return lo
    if hi is not None and x > hi:
        return hi
    return x
def to_bool_safe(value):
    """
    Chuyển đổi an toàn giá trị sang boolean.
    Xử lý string như 'true'/'false', số, v.v.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ('true', '1', 'yes', 'on'):
            return True
        elif value_lower in ('false', '0', 'no', 'off'):
            return False
    return bool(value)  # Fallback sang chuyển đổi bool của Python
def to_float_safe(value):
    """
    Chuyển đổi an toàn giá trị sang float.
    Trả về 0.0 nếu thất bại.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0