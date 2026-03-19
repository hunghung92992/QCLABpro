# -*- coding: utf-8 -*-
"""
app/shared/widgets/expiry_banner_widget.py
(Ported từ qc_expiry_banner.py)
Widget (UI) hiển thị cảnh báo Sắp hết hạn / Đã hết hạn.
"""

from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from typing import Optional, Union
import datetime as _dt

# Import helper mới từ utils
from app.utils.expiry_helper import evaluate_expiry, DEFAULT_WARN_DAYS


class QCExpiryBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lbl = QLabel()
        self._lbl.setWordWrap(True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.addWidget(self._lbl, 1, Qt.AlignCenter)

        self.setVisible(False)
        self.setObjectName("QCExpiryBanner")  # Thêm ID để CSS (styles.qss)

    def set_expiry(self,
                   expiry: Optional[Union[str, _dt.date]],
                   warn_days: int = DEFAULT_WARN_DAYS):
        """
        Cập nhật trạng thái HSD và tự động Ẩn/Hiện/Đổi màu.
        """
        status, days_left = evaluate_expiry(expiry, warn_days)

        if status == "expired":
            self._lbl.setText(f"⚠️ ĐÃ HẾT HẠN. (HSD: {expiry})")
            # CSS (styles.qss) sẽ xử lý màu đỏ
            self.setProperty("status", "expired")
            self.setVisible(True)
        elif status == "near_expiry":
            d = days_left if days_left is not None else "?"
            self._lbl.setText(f"⚠️ Sắp hết hạn trong {d} ngày. (HSD: {expiry})")
            # CSS (styles.qss) sẽ xử lý màu vàng
            self.setProperty("status", "near_expiry")
            self.setVisible(True)
        else:
            # status == "ok" hoặc "unknown"
            self.setProperty("status", "ok")
            self.setVisible(False)

        # Cập nhật style (để QSS nhận diện thay đổi property)
        self.style().unpolish(self);
        self.style().polish(self)