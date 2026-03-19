# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_task_dialog.py
Dialog thêm/sửa Task EQA (Phân công nhiệm vụ, Deadline).
(CONVERTED TO FLUENT UI - LOGIC PRESERVED)
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QGridLayout
)

# --- Fluent UI Imports ---
from qfluentwidgets import (
    MessageBoxBase, CardWidget, PrimaryPushButton, PushButton,
    ComboBox, EditableComboBox, LineEdit, SpinBox, CalendarPicker,
    StrongBodyLabel, BodyLabel, SubtitleLabel, InfoBar
)

# Imports Services
from app.services.eqa_service import EQAService
from app.services.auth_service import AuthService


class EQATaskDialog(MessageBoxBase):
    """Dialog Thêm/Sửa Task EQA."""

    def __init__(self, parent: QWidget, eqa_service: EQAService, auth_service: AuthService,
                 task_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)

        self.eqa_service = eqa_service
        self.auth_service = auth_service
        self._data = task_data or {}
        self.is_edit_mode = bool(task_data and task_data.get('id'))

        title = f"Sửa Tác vụ EQA ID: {self._data.get('id')}" if self.is_edit_mode else "Thêm Tác vụ EQA"
        self.titleLabel = SubtitleLabel(title, self)

        self._build_ui()
        self._load_master_data()
        self._load_task_data()

        # Override buttons
        self.yesButton.setText("Lưu")
        self.cancelButton.setText("Hủy")

        # Connect validation
        try:
            self.yesButton.clicked.disconnect()
        except:
            pass
        self.yesButton.clicked.connect(self._check_and_save)

    def _build_ui(self):
        # Header
        self.viewLayout.addWidget(self.titleLabel)

        # --- Card 1: Thông tin Round ---
        round_card = CardWidget(self)
        grid1 = QGridLayout(round_card)
        grid1.setSpacing(10)
        grid1.setContentsMargins(16, 16, 16, 16)

        self.sp_year = SpinBox()
        self.sp_year.setRange(2000, 2100)
        self.sp_year.setValue(QDate.currentDate().year())

        self.cb_round = ComboBox()
        self.cb_round.addItems([f"{i:02d}" for i in range(1, 13)])

        self.cb_provider = ComboBox()
        self.cb_provider.setPlaceholderText("Chọn Provider")

        self.cb_program = ComboBox()
        self.cb_program.setPlaceholderText("Chọn Program")

        grid1.addWidget(BodyLabel("Năm:", self), 0, 0)
        grid1.addWidget(self.sp_year, 0, 1)
        grid1.addWidget(BodyLabel("Đợt:", self), 0, 2)
        grid1.addWidget(self.cb_round, 0, 3)
        grid1.addWidget(BodyLabel("Provider:", self), 1, 0)
        grid1.addWidget(self.cb_provider, 1, 1)
        grid1.addWidget(BodyLabel("Program:", self), 1, 2)
        grid1.addWidget(self.cb_program, 1, 3)

        self.viewLayout.addWidget(round_card)

        # --- Card 2: Chi tiết Tác vụ ---
        task_card = CardWidget(self)
        grid2 = QGridLayout(task_card)
        grid2.setSpacing(10)
        grid2.setContentsMargins(16, 16, 16, 16)

        self.txt_sample_plan = LineEdit()
        self.txt_sample_plan.setPlaceholderText("Ví dụ: Mẫu A, Mẫu B")

        self.cb_device_name = EditableComboBox()
        self.cb_device_name.setPlaceholderText("Chọn hoặc nhập máy")

        self.cb_assigned_to = ComboBox()
        self.cb_assigned_to.setPlaceholderText("Chọn KTV")

        self.dt_start = CalendarPicker()
        self.dt_start.setDateFormat(Qt.ISODate)

        self.dt_end = CalendarPicker()
        self.dt_end.setDateFormat(Qt.ISODate)

        self.dt_due = CalendarPicker()
        self.dt_due.setDateFormat(Qt.ISODate)

        self.cb_status = ComboBox()
        self.cb_status.addItems(["NEW", "RUN", "DONE", "LATE"])

        self.txt_note = LineEdit()
        self.txt_note.setPlaceholderText("Ghi chú")

        # Row 0
        grid2.addWidget(BodyLabel("Tên Mẫu*", self), 0, 0)
        grid2.addWidget(self.txt_sample_plan, 0, 1)
        grid2.addWidget(BodyLabel("Thiết bị*", self), 0, 2)
        grid2.addWidget(self.cb_device_name, 0, 3)

        # Row 1
        grid2.addWidget(BodyLabel("Giao cho*", self), 1, 0)
        grid2.addWidget(self.cb_assigned_to, 1, 1)
        grid2.addWidget(BodyLabel("Trạng thái", self), 1, 2)
        grid2.addWidget(self.cb_status, 1, 3)

        # Row 2 (Dates)
        grid2.addWidget(BodyLabel("Start:", self), 2, 0)
        grid2.addWidget(self.dt_start, 2, 1)
        grid2.addWidget(BodyLabel("End:", self), 2, 2)
        grid2.addWidget(self.dt_end, 2, 3)

        # Row 3
        grid2.addWidget(BodyLabel("Hạn nộp*", self), 3, 0)
        grid2.addWidget(self.dt_due, 3, 1)
        grid2.addWidget(BodyLabel("Ghi chú", self), 3, 2)
        grid2.addWidget(self.txt_note, 3, 3)

        self.viewLayout.addWidget(task_card)
        self.widget.setMinimumWidth(750)

        # --- Wire Events ---
        self.cb_provider.currentIndexChanged.connect(self._on_provider_changed)
        # EditableComboBox dùng textChanged
        self.cb_program.currentTextChanged.connect(self._reload_device_suggestions)
        self.cb_assigned_to.currentTextChanged.connect(self._reload_device_suggestions)

    # --- Helper fill combo ---
    def _fill_combo(self, combo, items, text_key, id_key, empty_text=None):
        combo.clear()
        if empty_text:
            combo.addItem(empty_text, None)
        for item in items:
            combo.addItem(str(item.get(text_key)), item.get(id_key))

    def _load_master_data(self):
        """Tải Providers, Programs và Users."""
        # Providers
        providers = self.eqa_service.list_providers()
        self._fill_combo(self.cb_provider, providers, "name", "id", "— Chọn Provider —")

        # Users (KTV)
        users = self.auth_service.list_users(search_term=None)
        ktv_list = [{"username": u["username"], "fullname": u["fullname"] or u["username"]}
                    for u in users if u["role"] in ["KTV", "QA", "TRUONG_KHOA", "SUPERADMIN"]]
        self._fill_combo(self.cb_assigned_to, ktv_list, "fullname", "username", "— Chọn KTV —")

    def _on_provider_changed(self):
        """Tải Programs khi Provider thay đổi."""
        provider_id = self.cb_provider.currentData()
        programs = self.eqa_service.list_programs(provider_id) if provider_id else []
        self._fill_combo(self.cb_program, programs, "name", "id", "— Chọn Program —")
        self._reload_device_suggestions()

    def _reload_device_suggestions(self):
        """Tải gợi ý tên thiết bị EQA."""
        program_id = self.cb_program.currentData()
        self.cb_device_name.clear()
        self.cb_device_name.addItem("")

        if program_id:
            devices = self.eqa_service.list_eqa_devices(program_id)
            for d in devices:
                self.cb_device_name.addItem(d["name"])

    def _load_task_data(self):
        """Nạp dữ liệu task hiện tại."""
        if not self.is_edit_mode:
            current = QDate.currentDate()
            self.dt_start.setDate(current)
            self.dt_end.setDate(current.addDays(7))
            self.dt_due.setDate(current.addDays(10))
            return

        data = self._data
        self.sp_year.setValue(data.get("year", QDate.currentDate().year()))
        self.cb_round.setCurrentText(data.get("round_no", "01"))
        self.txt_sample_plan.setText(data.get("sample_plan", ""))
        self.txt_note.setText(data.get("note", ""))
        self.cb_status.setCurrentText(data.get("status", "NEW"))

        # Provider/Program
        idx_prov = self.cb_provider.findText(data.get("provider_name") or "")
        if idx_prov >= 0: self.cb_provider.setCurrentIndex(idx_prov)

        # Trigger load program
        self._on_provider_changed()

        idx_prog = self.cb_program.findText(data.get("program_name") or "")
        if idx_prog >= 0: self.cb_program.setCurrentIndex(idx_prog)

        self._reload_device_suggestions()
        self.cb_device_name.setText(data.get("device_name", ""))  # EditableComboBox

        # KTV
        idx_ktv = self.cb_assigned_to.findData(data.get("assigned_to"))
        if idx_ktv >= 0: self.cb_assigned_to.setCurrentIndex(idx_ktv)

        # Dates
        def _set(w, s):
            if s: w.setDate(QDate.fromString(s, "yyyy-MM-dd"))

        _set(self.dt_start, data.get("start_date"))
        _set(self.dt_end, data.get("end_date"))
        _set(self.dt_due, data.get("due_date"))

    def _check_and_save(self):
        """Validation và Lưu."""
        prog_id = self.cb_program.currentData()
        assigned_to = self.cb_assigned_to.currentData()

        if not prog_id or not assigned_to:
            InfoBar.warning("Thiếu dữ liệu", "Vui lòng chọn Chương trình và KTV.", parent=self)
            return

        if not self.txt_sample_plan.text().strip():
            InfoBar.warning("Thiếu dữ liệu", "Vui lòng nhập Tên Mẫu EQA.", parent=self)
            return

        data = {
            "id": self._data.get('id'),
            "year": self.sp_year.value(),
            "round_no": self.cb_round.currentText().strip(),
            "provider_id": self.cb_provider.currentData(),
            "program_id": prog_id,
            "sample_plan": self.txt_sample_plan.text().strip(),
            "device_name": self.cb_device_name.text().strip(),  # EditableCombo
            "assigned_to": assigned_to,
            "start_date": self.dt_start.date.toString("yyyy-MM-dd"),
            "end_date": self.dt_end.date.toString("yyyy-MM-dd"),
            "due_date": self.dt_due.date.toString("yyyy-MM-dd"),
            "status": self.cb_status.currentText().strip(),
            "note": self.txt_note.text().strip()
        }

        try:
            task_id = self.eqa_service.upsert_task(data)
            # MessageBoxBase return 1 on accept
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi lưu dữ liệu", f"Không thể lưu Tác vụ: {e}")