# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_master_data_dialog.py
Dialog quản lý Master Data cho EQA: Nhà cung cấp (Provider) và Chương trình (Program).
(CONVERTED TO FLUENT UI - LOGIC PRESERVED)
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QMessageBox, QInputDialog, QHeaderView, QAbstractItemView,
    QTableWidgetItem, QListWidgetItem
)

# --- Fluent UI Imports ---
from qfluentwidgets import (
    MessageBoxBase, LineEdit, PushButton, PrimaryPushButton,
    ListWidget, TableWidget, FluentIcon as FIF,
    StrongBodyLabel, SubtitleLabel, CardWidget, InfoBar
)

# Import Service
from app.services.eqa_service import EQAService


class EQAProgramDialog(MessageBoxBase):
    """Dialog thêm/sửa Chương trình (Program) - Fluent UI."""

    def __init__(self, parent: QWidget, provider_id: int, program_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Thêm/Sửa Chương trình EQA", self)

        self.provider_id = provider_id
        self._data = program_data or {}

        # UI Components
        self.viewLayout.addWidget(self.titleLabel)

        self.txt_name = LineEdit()
        self.txt_name.setText(self._data.get("name", ""))
        self.txt_name.setPlaceholderText("Tên Chương trình")

        self.txt_code = LineEdit()
        self.txt_code.setText(self._data.get("code", ""))
        self.txt_code.setPlaceholderText("Mã chương trình (Ví dụ: VEQAS-CHEM)")

        # Layout
        form = QFormLayout()
        form.addRow("Tên Chương trình*", self.txt_name)
        form.addRow("Mã (Code)", self.txt_code)
        self.viewLayout.addLayout(form)

        # Buttons configuration
        self.yesButton.setText("Lưu")
        self.cancelButton.setText("Hủy")

        # Custom validation logic
        try:
            self.yesButton.clicked.disconnect()
        except:
            pass
        self.yesButton.clicked.connect(self._check_and_accept)

    def _check_and_accept(self):
        if not self.txt_name.text().strip():
            # Dùng QMessageBox chuẩn để chặn modal
            QMessageBox.warning(self, "Thiếu thông tin", "Tên chương trình là bắt buộc.")
            return
        self.accept()

    def get_values(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.txt_name.text().strip(),
            "code": self.txt_code.text().strip() or None,
            "id": self._data.get("id")
        }


# ============================================================================
# DIALOG CHÍNH (MASTER DATA)
# ============================================================================

class EQAMasterDataDialog(QDialog):
    """
    Quản lý danh mục EQA (Provider & Program).
    """

    def __init__(self, parent=None, eqa_service: Optional[EQAService] = None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý Danh mục EQA (Provider & Program)")
        self.resize(1000, 650)  # Tăng kích thước chút để đẹp hơn với CardWidget

        # Service
        self.eqa_service = eqa_service or EQAService()
        self.current_provider_id: Optional[int] = None

        self._build_ui()
        self._wire_events()
        self.reload_providers()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ========== LEFT: Providers (Master) ==========
        left_card = CardWidget(self)
        left_layout = QVBoxLayout(left_card)

        left_layout.addWidget(StrongBodyLabel("Nhà cung cấp (Provider)", self))

        self.list_providers = ListWidget(self)
        self.list_providers.setSelectionMode(QAbstractItemView.SingleSelection)
        left_layout.addWidget(self.list_providers)

        btn_bar_left = QHBoxLayout()
        self.btn_prov_add = PrimaryPushButton(FIF.ADD, "Thêm", self)
        self.btn_prov_edit = PushButton(FIF.EDIT, "Sửa", self)
        self.btn_prov_del = PushButton(FIF.DELETE, "Xoá", self)

        btn_bar_left.addWidget(self.btn_prov_add)
        btn_bar_left.addWidget(self.btn_prov_edit)
        btn_bar_left.addWidget(self.btn_prov_del)

        left_layout.addLayout(btn_bar_left)

        # ========== RIGHT: Programs (Detail) ==========
        right_card = CardWidget(self)
        right_layout = QVBoxLayout(right_card)

        right_layout.addWidget(StrongBodyLabel("Chương trình EQA của Provider", self))

        # Bảng Programs
        self.table_programs = TableWidget(self)
        self.table_programs.setColumnCount(3)
        self.table_programs.setHorizontalHeaderLabels(["ID", "Tên Chương trình", "Mã Code"])
        self.table_programs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_programs.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_programs.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_programs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_programs.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_programs.verticalHeader().hide()
        self.table_programs.setBorderVisible(True)

        right_layout.addWidget(self.table_programs)

        # Nút Programs
        btn_bar_right = QHBoxLayout()
        self.btn_prog_add = PrimaryPushButton(FIF.ADD, "Thêm CT", self)
        self.btn_prog_edit = PushButton(FIF.EDIT, "Sửa CT", self)
        self.btn_prog_del = PushButton(FIF.DELETE, "Xoá CT", self)

        btn_bar_right.addWidget(self.btn_prog_add)
        btn_bar_right.addWidget(self.btn_prog_edit)
        btn_bar_right.addWidget(self.btn_prog_del)

        right_layout.addLayout(btn_bar_right)

        # --- Kết thúc Layout ---
        root.addWidget(left_card, 1)
        root.addWidget(right_card, 2)

    def _wire_events(self):
        # Providers
        self.list_providers.itemSelectionChanged.connect(self._on_provider_changed)
        self.btn_prov_add.clicked.connect(self._add_provider)
        self.btn_prov_edit.clicked.connect(self._edit_provider)
        self.btn_prov_del.clicked.connect(self._delete_provider)

        # Programs
        self.btn_prog_add.clicked.connect(self._add_program)
        self.btn_prog_edit.clicked.connect(self._edit_program)
        self.table_programs.doubleClicked.connect(lambda: self._edit_program())
        self.btn_prog_del.clicked.connect(self._delete_program)

    # ============================================================================
    # PROVIDER LOGIC (Master)
    # ============================================================================

    def reload_providers(self):
        """Tải lại danh sách Provider."""
        self.list_providers.clear()
        providers = self.eqa_service.list_providers()
        for p in providers:
            item = QListWidgetItem(p["name"])
            item.setData(Qt.UserRole, p["id"])
            self.list_providers.addItem(item)

        self.table_programs.setRowCount(0)
        self.current_provider_id = None
        if self.list_providers.count() > 0:
            self.list_providers.setCurrentRow(0)

    def _on_provider_changed(self):
        """Cập nhật ID và tải Programs khi Provider thay đổi."""
        selected_items = self.list_providers.selectedItems()
        if selected_items:
            self.current_provider_id = selected_items[0].data(Qt.UserRole)
            self._reload_programs()
        else:
            self.current_provider_id = None
            self.table_programs.setRowCount(0)

    def _add_provider(self):
        name, ok = QInputDialog.getText(self, "Thêm Provider", "Tên Nhà cung cấp:")
        if not ok or not name.strip(): return

        result = self.eqa_service.upsert_provider(name.strip())
        if result:
            InfoBar.success("Thành công", f"Đã thêm Provider: {name.strip()}", parent=self)
            self.reload_providers()
        else:
            InfoBar.error("Lỗi", "Không thể thêm Provider (Có thể tên đã tồn tại).", parent=self)

    def _edit_provider(self):
        prov_id = self.current_provider_id
        if not prov_id:
            InfoBar.warning("Chú ý", "Vui lòng chọn Provider để sửa.", parent=self)
            return

        current_name = self.list_providers.selectedItems()[0].text()
        name, ok = QInputDialog.getText(self, "Sửa Provider", "Tên Nhà cung cấp:", text=current_name)
        if not ok or not name.strip(): return

        result = self.eqa_service.upsert_provider(name.strip(), prov_id)
        if result:
            InfoBar.success("Thành công", "Đã cập nhật Provider.", parent=self)
            self.reload_providers()
        else:
            InfoBar.error("Lỗi", "Không thể cập nhật Provider (Có thể tên đã tồn tại).", parent=self)

    def _delete_provider(self):
        prov_id = self.current_provider_id
        if not prov_id: return

        if QMessageBox.question(self, "Xác nhận Xóa", "Xóa Provider này và toàn bộ Chương trình liên quan?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        if self.eqa_service.delete_provider(prov_id):
            InfoBar.success("Thành công", "Đã xóa Provider.", parent=self)
            self.reload_providers()
        else:
            InfoBar.error("Lỗi", "Không thể xóa Provider.", parent=self)

    # ============================================================================
    # PROGRAM LOGIC (Detail)
    # ============================================================================

    def _reload_programs(self):
        """Tải lại danh sách Programs cho Provider hiện tại."""
        self.table_programs.setRowCount(0)
        if not self.current_provider_id: return

        programs = self.eqa_service.list_programs(self.current_provider_id)
        self.table_programs.setRowCount(len(programs))

        for r, p in enumerate(programs):
            self.table_programs.setItem(r, 0, QTableWidgetItem(str(p["id"])))
            self.table_programs.setItem(r, 1, QTableWidgetItem(p["name"]))
            self.table_programs.setItem(r, 2, QTableWidgetItem(p["code"] or ""))

            # Lưu ID vào Item 0 (ẩn nếu cần) hoặc dùng data để an toàn
            self.table_programs.item(r, 0).setData(Qt.UserRole, p["id"])

        self.table_programs.resizeColumnsToContents()

    def _add_program(self):
        prov_id = self.current_provider_id
        if not prov_id:
            InfoBar.warning("Chú ý", "Vui lòng chọn Provider trước.", parent=self)
            return

        dlg = EQAProgramDialog(self, prov_id)
        if dlg.exec() != 1: return  # MessageBoxBase returns 1

        data = dlg.get_values()

        result = self.eqa_service.upsert_program(
            data["provider_id"], data["name"], data["code"]
        )
        if result:
            InfoBar.success("Thành công", "Đã thêm Chương trình.", parent=self)
            self._reload_programs()
        else:
            InfoBar.error("Lỗi", "Không thể thêm Chương trình (Có thể tên đã tồn tại).", parent=self)

    def _edit_program(self):
        prov_id = self.current_provider_id
        row = self.table_programs.currentRow()
        if not prov_id or row < 0:
            InfoBar.warning("Chú ý", "Vui lòng chọn Chương trình để sửa.", parent=self)
            return

        # Lấy ID từ data đã lưu ở cột 0
        item0 = self.table_programs.item(row, 0)
        if item0 and item0.data(Qt.UserRole):
            prog_id = item0.data(Qt.UserRole)
        else:
            # Fallback
            try:
                prog_id = int(item0.text())
            except:
                return

        program_data = {
            "id": prog_id,
            "name": self.table_programs.item(row, 1).text(),
            "code": self.table_programs.item(row, 2).text()
        }

        dlg = EQAProgramDialog(self, prov_id, program_data)
        if dlg.exec() != 1: return

        data = dlg.get_values()

        result = self.eqa_service.upsert_program(
            data["provider_id"], data["name"], data["code"], data["id"]
        )
        if result:
            InfoBar.success("Thành công", "Đã cập nhật Chương trình.", parent=self)
            self._reload_programs()
        else:
            InfoBar.error("Lỗi", "Không thể cập nhật Chương trình.", parent=self)

    def _delete_program(self):
        row = self.table_programs.currentRow()
        if row < 0: return

        item0 = self.table_programs.item(row, 0)
        if item0 and item0.data(Qt.UserRole):
            prog_id = item0.data(Qt.UserRole)
        else:
            try:
                prog_id = int(item0.text())
            except:
                return

        if QMessageBox.question(self, "Xác nhận Xóa", "Xóa Chương trình này?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        if self.eqa_service.delete_program(prog_id):
            InfoBar.success("Thành công", "Đã xóa Chương trình.", parent=self)
            self._reload_programs()
        else:
            InfoBar.error("Lỗi", "Không thể xóa Chương trình.", parent=self)