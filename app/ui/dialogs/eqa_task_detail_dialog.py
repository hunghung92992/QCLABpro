# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_task_detail_dialog.py
Dialog quản lý chi tiết Task EQA (Task Log, Notes, Status updates).
(CONVERTED TO FLUENT UI - LOGIC PRESERVED)
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView
)

# --- Fluent UI Imports ---
from qfluentwidgets import (
    MessageBoxBase, CardWidget, PrimaryPushButton, ComboBox,
    LineEdit, TableWidget, StrongBodyLabel, BodyLabel,
    SubtitleLabel, FluentIcon as FIF, InfoBar
)

# Imports Services
from app.services.eqa_service import EQAService
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService

# Trạng thái chuẩn
VN_STATUS = [
    ("NEW", "Mới tạo"),
    ("RUN", "Đang thực hiện"),
    ("DONE", "Đã nộp"),
    ("LATE", "Quá hạn"),
    ("CANCELED", "Đã hủy")
]


class EQATaskDetailDialog(QDialog):
    """
    Quản lý chi tiết của một Task EQA (hiển thị thông tin tổng quan, log, và update nhanh).
    """

    def __init__(self, parent: QWidget, eqa_service: EQAService, auth_service: AuthService, audit_service: AuditService,
                 task_id: int, current_username: str):
        super().__init__(parent)
        self.setWindowTitle(f"Chi tiết Task EQA ID: {task_id}")
        self.resize(1000, 700)  # Tăng size chút để hiển thị đẹp hơn

        self.eqa_service = eqa_service
        self.auth_service = auth_service
        self.audit_service = audit_service
        self.task_id = task_id
        self.current_username = current_username

        self._task_data: Optional[Dict[str, Any]] = None

        self._build_ui()
        self._wire_events()
        self._load_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # --- Card 1: Thông tin Tổng quan (Task Summary) ---
        summary_card = CardWidget(self)
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.addWidget(StrongBodyLabel("Thông tin Task", self))

        self.lbl_summary = BodyLabel("Đang tải thông tin Task...", self)
        self.lbl_summary.setWordWrap(True)
        summary_layout.addWidget(self.lbl_summary)

        root.addWidget(summary_card)

        # --- Card 2: Cập nhật Trạng thái Nhanh ---
        update_card = CardWidget(self)
        update_layout = QVBoxLayout(update_card)
        update_layout.addWidget(StrongBodyLabel("Cập nhật Nhanh & Ghi Log", self))

        h_update = QHBoxLayout()

        self.cb_status_update = ComboBox()
        for code, label in VN_STATUS:
            self.cb_status_update.addItem(label, code)

        self.txt_log_note = LineEdit()
        self.txt_log_note.setPlaceholderText("Ghi chú/Lý do cập nhật trạng thái...")

        self.btn_log_update = PrimaryPushButton(FIF.SAVE, "Lưu Log & Update", self)

        h_update.addWidget(BodyLabel("Trạng thái mới:", self))
        h_update.addWidget(self.cb_status_update)
        h_update.addWidget(BodyLabel("Ghi chú Log:", self))
        h_update.addWidget(self.txt_log_note, 1)
        h_update.addWidget(self.btn_log_update)

        update_layout.addLayout(h_update)
        root.addWidget(update_card)

        # --- Card 3: Nhật ký Hoạt động (Task Log) ---
        log_card = CardWidget(self)
        log_layout = QVBoxLayout(log_card)
        log_layout.addWidget(StrongBodyLabel("Nhật ký Hoạt động (Task Log)", self))

        self.table_log = TableWidget(self)
        self.table_log.setColumnCount(4)
        self.table_log.setHorizontalHeaderLabels(["Thời gian (TS)", "Người thực hiện", "Hành động", "Ghi chú"])
        self.table_log.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_log.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_log.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_log.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_log.verticalHeader().hide()
        self.table_log.setBorderVisible(True)

        log_layout.addWidget(self.table_log, 1)
        root.addWidget(log_card, 1)

    def _wire_events(self):
        self.btn_log_update.clicked.connect(self._log_and_update_status)

    def _load_data(self):
        """Tải thông tin Task tổng quan và Log."""

        # 1. Tải Task Summary
        try:
            self._task_data = self.eqa_service.get_task(self.task_id)
            if not self._task_data:
                self.lbl_summary.setText("Lỗi: Không tìm thấy Task.")
                return

            data = self._task_data
            # Dùng HTML basic cho BodyLabel (nếu hỗ trợ) hoặc text thường
            # BodyLabel hỗ trợ RichText cơ bản
            summary_text = (
                f"Chương trình: {data.get('provider_name')} - {data.get('program_name')}\n"
                f"Đợt: {data.get('year')}-{data.get('round_no')} | Mẫu: {data.get('sample_plan')}\n"
                f"Giao cho: {data.get('assigned_to')} | Hạn nộp: {data.get('due_date')}\n"
                f"Trạng thái hiện tại: {data.get('status')}"
            )
            self.lbl_summary.setText(summary_text)

            # Đồng bộ ComboBox với trạng thái hiện tại
            current_status_code = data.get('status')
            idx = self.cb_status_update.findData(current_status_code)
            if idx >= 0: self.cb_status_update.setCurrentIndex(idx)

        except Exception as e:
            self.lbl_summary.setText(f"Lỗi tải Task Summary: {e}")
            return

        # 2. Tải Task Log
        self._load_task_log()

    def _load_task_log(self):
        """Tải các log liên quan đến Task EQA."""
        try:
            logs = self.eqa_service.list_task_logs(self.task_id)
            self.table_log.setRowCount(0)
            self.table_log.setRowCount(len(logs))

            for r, log in enumerate(logs):
                self.table_log.setItem(r, 0, QTableWidgetItem(str(log.get('ts'))))
                self.table_log.setItem(r, 1, QTableWidgetItem(str(log.get('actor'))))
                self.table_log.setItem(r, 2, QTableWidgetItem(str(log.get('action'))))
                self.table_log.setItem(r, 3, QTableWidgetItem(str(log.get('note'))))

        except Exception as e:
            self.table_log.setRowCount(1)
            self.table_log.setItem(0, 3, QTableWidgetItem(f"Lỗi tải Log: {e}"))

    def _log_and_update_status(self):
        """Ghi Log và cập nhật trạng thái Task."""
        if not self._task_data: return

        new_status_code = self.cb_status_update.currentData()
        note = self.txt_log_note.text().strip()

        if not note and new_status_code != self._task_data.get('status'):
            InfoBar.warning("Thiếu ghi chú", "Vui lòng nhập lý do khi thay đổi trạng thái.", parent=self)
            return

        try:
            old_status = self._task_data.get('status')

            # 1. Ghi Log Hành động
            self.eqa_service.log_task_action(
                task_id=self.task_id,
                actor=self.current_username,
                action=f"STATUS_CHANGE_FROM_{old_status}_TO_{new_status_code}",
                note=note
            )

            # 2. Cập nhật Trạng thái trong bảng eqa_task
            self.eqa_service.update_task_status(
                task_id=self.task_id,
                new_status=new_status_code
            )

            InfoBar.success("Thành công", f"Đã cập nhật trạng thái Task ID {self.task_id} thành {new_status_code}.",
                            parent=self)

            # Tải lại để cập nhật summary và log
            self._load_data()
            self.txt_log_note.clear()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi cập nhật", f"Không thể cập nhật trạng thái Task: {e}")