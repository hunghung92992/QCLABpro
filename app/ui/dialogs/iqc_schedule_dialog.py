# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_schedule_dialog.py
(WIN11 FLUENT DESIGN - LIGHT/DARK MODE SUPPORT)
- Dialog cấu hình lịch chạy mẫu nội kiểm.
- Hỗ trợ tùy chọn "Áp dụng cho tất cả Level".
"""
from typing import Dict, Any, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QWidget

# --- FLUENT UI IMPORTS ---
from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, StrongBodyLabel, BodyLabel,
    ComboBox, SpinBox, CheckBox, PrimaryPushButton, PushButton,
    InfoBar, SwitchButton
)


class IQCScheduleConfigDialog(MessageBoxBase):
    """
    Sử dụng MessageBoxBase của FluentWidgets để có dialog chuẩn Win11
    (Bo góc, bóng đổ, tự động Dark Mode).
    """

    def __init__(self, parent=None, test_name: str = "", level: int = 1, current_data: Optional[Dict] = None):
        super().__init__(parent)

        self.test_info = f"{test_name} - Level {level}"
        self._data = current_data or {}

        # Tiêu đề Dialog
        self.titleLabel = SubtitleLabel(f"Cấu hình Lịch: {test_name} (L{level})", self)

        # Nội dung chính
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(10)

        self._build_ui()
        self._load_data()

        # Cấu hình nút bấm (Yes/Cancel) -> Lưu/Hủy
        self.yesButton.setText("Lưu Cấu hình")
        self.cancelButton.setText("Hủy bỏ")

        # Tăng kích thước mặc định
        self.widget.setMinimumWidth(450)

    def _build_ui(self):
        # 1. Tần suất (Frequency)
        self.viewLayout.addWidget(StrongBodyLabel("Tần suất lặp lại", self))
        self.cb_freq = ComboBox(self)
        self.cb_freq.addItems(
            ["Hàng ngày (Daily)", "Hàng tuần (Weekly)", "Hàng tháng (Monthly)", "Tùy chỉnh (Mỗi N ngày)"])
        # Map text -> key
        self._freq_map = ["daily", "weekly", "monthly", "ndays"]
        self.viewLayout.addWidget(self.cb_freq)
        self.viewLayout.addSpacing(10)

        # 2. Chi tiết (Every N Days)
        h_every = QHBoxLayout()
        h_every.addWidget(BodyLabel("Lặp lại mỗi:", self))
        self.sp_every = SpinBox(self)
        self.sp_every.setRange(1, 365)
        h_every.addWidget(self.sp_every)
        h_every.addWidget(BodyLabel("ngày/tuần", self))
        self.viewLayout.addLayout(h_every)

        # 3. Ân hạn (Grace Period)
        h_grace = QHBoxLayout()
        h_grace.addWidget(BodyLabel("Thời gian ân hạn:", self))
        self.sp_grace = SpinBox(self)
        self.sp_grace.setRange(0, 10)
        h_grace.addWidget(self.sp_grace)
        h_grace.addWidget(BodyLabel("ngày", self))
        self.viewLayout.addLayout(h_grace)
        self.viewLayout.addSpacing(10)

        # 4. Tùy chọn nâng cao (Switch & Checkbox)
        self.chk_hard_lock = SwitchButton(self)
        self.chk_hard_lock.setText("Khóa nhập liệu nếu Quá hạn")
        self.chk_hard_lock.setOnText("Đang Bật")
        self.chk_hard_lock.setOffText("Đang Tắt")
        self.viewLayout.addWidget(self.chk_hard_lock)
        self.viewLayout.addSpacing(5)

        # [NEW] Áp dụng hàng loạt
        self.chk_apply_all = CheckBox("Áp dụng cho TẤT CẢ Level của xét nghiệm này", self)
        self.viewLayout.addWidget(self.chk_apply_all)

        # Info Label (Hint)
        self.viewLayout.addSpacing(10)
        self.lbl_info = BodyLabel("Gợi ý: Chọn tần suất để xem hướng dẫn.", self)
        self.lbl_info.setTextColor("#666666", "#aaaaaa")  # Màu xám cho text phụ
        self.lbl_info.setWordWrap(True)
        self.viewLayout.addWidget(self.lbl_info)

        # Connect signals
        self.cb_freq.currentIndexChanged.connect(self._update_hint)

    def _load_data(self):
        freq = self._data.get("freq", "daily")

        # Map key -> index
        if freq in self._freq_map:
            idx = self._freq_map.index(freq)
            self.cb_freq.setCurrentIndex(idx)

        self.sp_every.setValue(int(self._data.get("every_n", 1)))
        self.sp_grace.setValue(int(self._data.get("grace_days", 0)))

        is_locked = bool(self._data.get("hard_lock", 0))
        self.chk_hard_lock.setChecked(is_locked)

        self._update_hint()

    def _update_hint(self):
        idx = self.cb_freq.currentIndex()
        freq_key = self._freq_map[idx]

        if freq_key == "daily":
            self.lbl_info.setText("Hệ thống sẽ nhắc chạy mẫu mỗi ngày.")
            self.sp_every.setEnabled(False)
            self.sp_every.setValue(1)
        elif freq_key == "weekly":
            self.lbl_info.setText("Nhắc chạy 1 lần/tuần (Reset chu kỳ vào Thứ 2).")
            self.sp_every.setEnabled(True)
        elif freq_key == "monthly":
            self.lbl_info.setText("Nhắc chạy 1 lần/tháng (Reset vào ngày 1).")
            self.sp_every.setEnabled(True)
        else:
            self.lbl_info.setText(f"Nhắc chạy sau mỗi {self.sp_every.value()} ngày tính từ lần chạy cuối.")
            self.sp_every.setEnabled(True)

    def get_values(self) -> Dict[str, Any]:
        """Trả về dữ liệu cấu hình khi user bấm Lưu"""
        idx = self.cb_freq.currentIndex()
        return {
            "freq": self._freq_map[idx],
            "every_n": self.sp_every.value(),
            "grace_days": self.sp_grace.value(),
            "hard_lock": 1 if self.chk_hard_lock.isChecked() else 0,
            "apply_all_levels": self.chk_apply_all.isChecked()
        }