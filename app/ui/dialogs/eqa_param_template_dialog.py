# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_param_template_dialog.py
Dialog quản lý Thông số Mẫu (Template) cho Chương trình EQA.
(CONVERTED TO FLUENT UI - LOGIC PRESERVED)
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidgetItem, QMessageBox, QHeaderView,
    QAbstractItemView
)

# --- Fluent UI Imports ---
from qfluentwidgets import (
    LineEdit, PushButton, PrimaryPushButton, TableWidget,
    StrongBodyLabel, CardWidget, FluentIcon as FIF, InfoBar
)

# Imports Services
from app.services.eqa_service import EQAService
from app.services.catalog_service import CatalogService


class EQAParamTemplateDialog(QDialog):
    """
    Quản lý danh sách Thông số (Analyte) cho một Chương trình EQA cụ thể.
    """

    def __init__(self, parent: QWidget, program_id: int, program_name: str):
        super().__init__(parent)
        self.setWindowTitle(f"Quản lý Thông số Mẫu cho: {program_name}")
        self.resize(850, 600)

        self.program_id = program_id
        self.eqa_service = EQAService()
        self.catalog_service = CatalogService()

        self._templates_cache: List[Dict[str, Any]] = []

        self._build_ui()
        self._wire_events()
        self._load_templates()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # --- Toolbar Nhập nhanh (CardWidget) ---
        input_card = CardWidget(self)
        h_input_layout = QVBoxLayout(input_card)

        h_input_layout.addWidget(StrongBodyLabel("Thêm nhanh Thông số", self))

        h_form = QHBoxLayout()

        self.txt_analyte = LineEdit()
        self.txt_analyte.setPlaceholderText("Tên xét nghiệm (ví dụ: GLU, CHOL)")

        self.txt_unit = LineEdit()
        self.txt_unit.setPlaceholderText("Đơn vị (ví dụ: mg/dL)")

        self.btn_add_param = PrimaryPushButton(FIF.ADD, "Thêm", self)

        h_form.addWidget(self.txt_analyte, 2)
        h_form.addWidget(self.txt_unit, 1)
        h_form.addWidget(self.btn_add_param)

        h_input_layout.addLayout(h_form)
        root.addWidget(input_card)

        # --- Bảng Template ---
        # Card bao quanh bảng để đồng bộ style
        table_card = CardWidget(self)
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)  # Bảng tràn viền card

        self.table = TableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Thông số (Analyte)*", "Đơn vị"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        # Cho phép sửa trực tiếp (editing)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setBorderVisible(True)

        table_layout.addWidget(self.table)
        root.addWidget(table_card, 1)

        # --- Nút chức năng cuối ---
        h_buttons = QHBoxLayout()
        self.btn_delete_row = PushButton(FIF.DELETE, "Xoá dòng đã chọn", self)
        self.btn_save_all = PrimaryPushButton(FIF.SAVE, "Lưu Thay đổi", self)

        h_buttons.addWidget(self.btn_delete_row)
        h_buttons.addStretch(1)
        h_buttons.addWidget(self.btn_save_all)

        root.addLayout(h_buttons)

    def _wire_events(self):
        self.btn_add_param.clicked.connect(self._add_param_row)
        self.table.itemChanged.connect(self._on_item_modified)
        self.btn_delete_row.clicked.connect(self._delete_selected_row)
        self.btn_save_all.clicked.connect(self._save_all_changes)

        # Gợi ý Đơn vị
        self.txt_analyte.textChanged.connect(self._auto_fill_unit)

    # ============================================================================
    # DATA LOGIC (Giữ nguyên 100%)
    # ============================================================================

    def _load_templates(self):
        """Tải các mẫu đã lưu từ EQA Service."""
        self._templates_cache = self.eqa_service.get_param_templates(self.program_id)
        self.table.setRowCount(0)
        self.table.setRowCount(len(self._templates_cache))

        for r, t in enumerate(self._templates_cache):
            self.table.setItem(r, 0, QTableWidgetItem(str(t.get("id", ""))))
            self.table.setItem(r, 1, QTableWidgetItem(t.get("analyte", "")))
            self.table.setItem(r, 2, QTableWidgetItem(t.get("unit", "")))

            # Đánh dấu cột ID là không sửa được
            self.table.item(r, 0).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

    def _add_param_row(self):
        """Thêm một hàng mới (từ form nhập nhanh)."""
        analyte = self.txt_analyte.text().strip()
        unit = self.txt_unit.text().strip() or None

        if not analyte:
            InfoBar.warning("Thiếu thông tin", "Thông số (Analyte) là bắt buộc.", parent=self)
            return

        r = self.table.rowCount()
        self.table.insertRow(r)

        # ID trống (bản ghi mới)
        self.table.setItem(r, 0, QTableWidgetItem(""))
        self.table.item(r, 0).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        # Nội dung
        self.table.setItem(r, 1, QTableWidgetItem(analyte))
        self.table.setItem(r, 2, QTableWidgetItem(unit or ""))

        # Đánh dấu hàng mới
        self._on_item_modified(self.table.item(r, 1))

        self.txt_analyte.clear()
        self.txt_unit.clear()
        self.txt_analyte.setFocus()

    def _auto_fill_unit(self, analyte_name: str):
        """Sử dụng CatalogService để gợi ý đơn vị."""
        if not analyte_name or len(analyte_name) < 3:
            return

        # Logic cũ: tìm unit dựa trên tên xét nghiệm
        try:
            meta = self.catalog_service.get_test_meta(department="", test_name=analyte_name)
            unit = meta.get("unit")
            if unit:
                self.txt_unit.setText(unit)
        except Exception:
            pass

    def _on_item_modified(self, item: QTableWidgetItem):
        """Đánh dấu hàng đã sửa bằng màu vàng nhạt."""
        if item.row() < 0: return

        # Chỉ đánh dấu nếu không phải cột ID
        if item.column() > 0:
            for c in range(self.table.columnCount()):
                i = self.table.item(item.row(), c)
                if i:
                    i.setBackground(QColor("#FFFDD0"))  # Màu kem/vàng nhạt
                    i.setToolTip("Chưa lưu")

    def _delete_selected_row(self):
        """Xóa dòng khỏi bảng (dòng đã lưu hoặc dòng mới)."""
        row = self.table.currentRow()
        if row < 0:
            InfoBar.warning("Xoá", "Vui lòng chọn dòng muốn xoá.", parent=self)
            return

        if QMessageBox.question(self, "Xác nhận",
                                "Bạn có muốn xoá dòng này không? (Việc xoá sẽ được lưu khi bấm 'Lưu Thay đổi')",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        # Xoá dòng trên UI
        self.table.removeRow(row)

    def _save_all_changes(self):
        """Thu thập tất cả các thay đổi và gửi đến EQA Service."""
        items_to_save = []
        for r in range(self.table.rowCount()):
            analyte = self.table.item(r, 1).text().strip()
            unit = self.table.item(r, 2).text().strip()

            if not analyte: continue  # Bỏ qua dòng trống

            items_to_save.append({
                "analyte": analyte,
                "unit": unit or None,
                "id": self.table.item(r, 0).text()  # ID có thể trống
            })

        if not items_to_save:
            InfoBar.warning("Lưu", "Không có thông số nào để lưu.", parent=self)
            return

        try:
            # Gọi service ghi đè
            self.eqa_service.save_param_templates_overwrite(self.program_id, items_to_save)
            InfoBar.success("Thành công", f"Đã lưu {len(items_to_save)} thông số mẫu.", parent=self)
            self._load_templates()  # Tải lại để loại bỏ màu vàng

        except Exception as e:
            QMessageBox.critical(self, "Lỗi lưu", f"Không thể lưu thông số mẫu: {e}")