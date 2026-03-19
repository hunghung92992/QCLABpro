# -*- coding: utf-8 -*-
"""
app/shared/utils/date_helper.py
(Ported từ date_util.py)
Chuẩn hoá parse/format ngày (ưu tiên YYYY-MM-DD).
"""
from __future__ import annotations
from typing import Optional
import re
import datetime as dt

# Định dạng ngày ISO chuẩn YYYY-MM-DD
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Các định dạng phổ biến khác
COMMON_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
]


def parse_date_str(s: str) -> Optional[str]:
    """
    Parse một chuỗi ngày bất kỳ (vd: 'dd/mm/yyyy', 'yyyy-mm-dd H:M:S')
    và trả về chuỗi chuẩn ISO 'YYYY-MM-DD'.
    """
    if not s:
        return None
    s_date = str(s).strip().split(" ")[0]  # Lấy phần ngày nếu là timestamp

    for fmt in COMMON_FORMATS:
        try:
            d = dt.datetime.strptime(s_date, fmt).date()
            return d.isoformat()  # Trả về 'YYYY-MM-DD'
        except Exception:
            pass

    # Thử ISO (fallback)
    try:
        d = dt.date.fromisoformat(s_date)
        return d.isoformat()
    except Exception:
        pass

    return None  # Không thể parse