# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_schedule_tab.py
Giao diện Lịch phân công EQA.
(CONVERTED TO FLUENT UI - LOGIC PRESERVED)
CẬP NHẬT:
1. Giao diện Fluent UI hiện đại (Card, Table, CalendarPicker).
2. Logic phân quyền ẩn/hiện form được giữ nguyên.
"""
import datetime as dt
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QMessageBox, QHeaderView, QDialog,
    QAbstractItemView, QGridLayout
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

# --- Fluent UI Imports ---
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, ComboBox,
    LineEdit, SpinBox, TableWidget, CalendarPicker,
    FluentIcon as FIF, BodyLabel, InfoBar
)

# Import Service
from app.services.eqa_service import EQAService
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.ui.dialogs.eqa_task_detail_dialog import EQATaskDetailDialog

ALLOWED_EDIT_ROLES = {"SUPERADMIN", "QA", "TRUONG_KHOA"}

VN_STATUS = [
    ("NEW", "Mới tạo"),
    ("RUN", "Đang thực hiện"),
    ("DONE", "Đã nộp"),
    ("LATE", "Quá hạn"),
]


class EqaScheduleTab(QWidget):
    def __init__(self,
                 parent: Optional[QWidget] = None,
                 db_path: Optional[str] = None,
                 username: Optional[str] = None,
                 role: Optional[str] = None,
                 **kwargs):
        super().__init__(parent)

        self.username = username or "user"
        self.role = (role or "user").upper()
        self.can_edit = self.role in ALLOWED_EDIT_ROLES

        self.dao = EQAService()
        self.auth_service = AuthService()
        self.audit_service = AuditService()
        self.input_form_widgets: List[QWidget] = []  # Danh sách các widget form để ẩn/hiện

        self._build_ui()
        self._load_providers()
        self._apply_permissions()  # Áp dụng logic ẩn/hiện
        self._refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # --- Card Nhập liệu ---
        input_card = CardWidget(self)
        grid = QGridLayout(input_card)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(12)

        # 1. Row 1: Year, Round, Provider, Program
        self.sp_year = SpinBox()
        self.sp_year.setRange(2000, 2100)
        self.sp_year.setValue(dt.datetime.now().year)

        self.cb_round = ComboBox()
        self.cb_round.addItems([f"{i:02d}" for i in range(1, 13)])

        self.cb_provider = ComboBox()
        self.cb_provider.setPlaceholderText("Chọn Nhà CC")

        self.cb_program = ComboBox()
        self.cb_program.setPlaceholderText("Chọn Chương trình")

        grid.addWidget(BodyLabel("Năm:", self), 0, 0)
        grid.addWidget(self.sp_year, 0, 1)
        grid.addWidget(BodyLabel("Đợt:", self), 0, 2)
        grid.addWidget(self.cb_round, 0, 3)
        grid.addWidget(BodyLabel("Nhà CC:", self), 0, 4)
        grid.addWidget(self.cb_provider, 0, 5)
        grid.addWidget(BodyLabel("CT:", self), 0, 6)
        grid.addWidget(self.cb_program, 0, 7)

        # Add input widgets to list for permission handling
        self.input_form_widgets.extend([self.sp_year, self.cb_round, self.cb_provider, self.cb_program])

        # 2. Row 2: Sample, Device, Assign, From, To
        self.ed_sample_name = LineEdit()
        self.ed_sample_name.setPlaceholderText("Tên mẫu")

        self.ed_device = LineEdit()
        self.ed_device.setPlaceholderText("Máy thực hiện")

        self.ed_assign = LineEdit()
        self.ed_assign.setPlaceholderText("Nhân viên")

        self.dt_from = CalendarPicker()
        self.dt_from.setDateFormat(Qt.ISODate)
        self.dt_from.setDate(QDate.currentDate())

        self.dt_to = CalendarPicker()
        self.dt_to.setDateFormat(Qt.ISODate)
        self.dt_to.setDate(QDate.currentDate().addDays(7))

        grid.addWidget(BodyLabel("Mẫu:", self), 1, 0)
        grid.addWidget(self.ed_sample_name, 1, 1)
        grid.addWidget(BodyLabel("Máy:", self), 1, 2)
        grid.addWidget(self.ed_device, 1, 3)
        grid.addWidget(BodyLabel("NV:", self), 1, 4)
        grid.addWidget(self.ed_assign, 1, 5)
        grid.addWidget(BodyLabel("Từ:", self), 1, 6)
        grid.addWidget(self.dt_from, 1, 7)
        grid.addWidget(BodyLabel("Đến:", self), 1, 8)  # Chỉnh layout grid
        grid.addWidget(self.dt_to, 1, 9)

        self.input_form_widgets.extend([self.ed_sample_name, self.ed_device, self.ed_assign, self.dt_from, self.dt_to])

        # 3. Row 3: Due, Status, Note
        self.due = CalendarPicker()
        self.due.setDateFormat(Qt.ISODate)
        self.due.setDate(QDate.currentDate().addDays(10))

        self.cb_status = ComboBox()
        for code, label in VN_STATUS:
            self.cb_status.addItem(label, code)

        self.ed_note = LineEdit()
        self.ed_note.setPlaceholderText("Ghi chú")

        grid.addWidget(BodyLabel("Hạn:", self), 2, 0)
        grid.addWidget(self.due, 2, 1)
        grid.addWidget(BodyLabel("Trạng thái:", self), 2, 2)
        grid.addWidget(self.cb_status, 2, 3)
        grid.addWidget(BodyLabel("Ghi chú:", self), 2, 4)
        grid.addWidget(self.ed_note, 2, 5, 1, 2)  # Span 2 cols

        self.input_form_widgets.extend([self.due, self.cb_status, self.ed_note])

        # 4. Buttons Row
        btn_bar = QHBoxLayout()
        self.btn_save = PrimaryPushButton(FIF.SAVE, "Lưu", self)
        self.btn_refresh = PushButton(FIF.SYNC, "Làm mới", self)
        self.btn_delete = PushButton(FIF.DELETE, "Xoá lịch", self)
        self.btn_detail = PushButton(FIF.INFO, "Chi tiết Task & Log", self)

        btn_bar.addWidget(self.btn_save)
        btn_bar.addWidget(self.btn_refresh)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addWidget(self.btn_detail)
        btn_bar.addStretch(1)

        # Add buttons to grid (row 3, col 7, span across)
        grid.addLayout(btn_bar, 2, 7, 1, 3)

        self.input_form_widgets.extend([self.btn_save, self.btn_delete])

        # Add Card to Root
        root.addWidget(input_card)

        # --- Table ---
        self.tbl = TableWidget(self)
        self.tbl.setColumnCount(12)
        self.tbl.setHorizontalHeaderLabels([
            "ID", "Năm", "Đợt", "Nhà cung cấp", "Chương trình", "Tên mẫu",
            "Máy", "Nhân viên", "Thời gian", "Hạn nộp", "Trạng thái", "Ghi chú"
        ])
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setBorderVisible(True)

        root.addWidget(self.tbl, 1)

        # --- Events ---
        self.btn_refresh.clicked.connect(self._refresh)
        self.btn_save.clicked.connect(self._save_task)
        self.btn_delete.clicked.connect(self._delete_task)
        self.tbl.itemDoubleClicked.connect(self._on_row_dbl_click)
        self.cb_provider.currentIndexChanged.connect(self._reload_programs)
        self.sp_year.valueChanged.connect(self._refresh)
        self.btn_detail.clicked.connect(self._open_task_detail)

    def _apply_permissions(self):
        """🟢 Khóa và Ẩn hoàn toàn form nhập liệu nếu không có quyền."""
        # Ẩn toàn bộ form nhập liệu/chỉnh sửa
        for w in self.input_form_widgets:
            w.setVisible(self.can_edit)

        # Nút làm mới và nút chi tiết vẫn luôn hiển thị
        self.btn_refresh.setVisible(True)
        self.btn_detail.setVisible(True)

    def _load_providers(self):
        self.cb_provider.blockSignals(True)
        self.cb_provider.clear()
        self.cb_provider.addItem("— Tất cả —", None)
        for r in self.dao.list_providers():
            self.cb_provider.addItem(r["name"], r["id"])
        self.cb_provider.blockSignals(False)
        self._reload_programs()

    def _reload_programs(self):
        self.cb_program.blockSignals(True)
        self.cb_program.clear()
        self.cb_program.addItem("— Tất cả —", None)
        pid = self.cb_provider.currentData()
        progs = self.dao.list_programs(pid) if pid is not None else self.dao.list_programs()
        for r in progs:
            disp = f"{r['name']} ({r['code']})" if r['code'] else r['name']
            self.cb_program.addItem(disp, r["id"])
        self.cb_program.blockSignals(False)

    def _refresh(self):
        """Tải lại bảng Lịch."""
        year = self.sp_year.value()
        rows = self.dao.list_tasks(year) or []

        self.tbl.setRowCount(0)
        self.tbl.setRowCount(len(rows))

        today = dt.date.today()

        for i, r in enumerate(rows):
            time_range = f"{r.get('start_date') or ''} → {r.get('end_date') or ''}"

            status_label = r.get("status", "NEW")
            for code, label in VN_STATUS:
                if code == status_label:
                    status_label = label
                    break

            cells = [
                r.get("id"), r.get("year"), r.get("round_no"),
                r.get("provider_name"), r.get("program_name"), r.get("sample_plan"),
                r.get("device_name"), r.get("assigned_to"),
                time_range, r.get("due_date"), status_label, r.get("note"),
            ]

            for c, val in enumerate(cells):
                self.tbl.setItem(i, c, QTableWidgetItem("" if val is None else str(val)))

            self._decorate_due(i, r.get("due_date"), today)

        self.tbl.resizeColumnsToContents()

    def _decorate_due(self, row: int, due_date_str: Optional[str], today: dt.date):
        """Tô màu ô 'Hạn nộp'."""
        item = self.tbl.item(row, 9)  # Cột Hạn nộp
        if not item or not due_date_str:
            return

        try:
            d = dt.date.fromisoformat(due_date_str)
            days = (d - today).days

            if days < 0:
                item.setBackground(QColor("#F8C4C4"))  # Đỏ (Quá hạn)
            elif days <= 3:
                item.setBackground(QColor("#FFF2B2"))  # Vàng (Sắp hạn)
            else:
                item.setBackground(QColor("#D6F5D6"))  # Xanh (Còn hạn)
        except Exception:
            pass

    def _save_task(self):
        """Thu thập dữ liệu từ form và gọi Service."""
        # Nếu đang ở chế độ xem, không cho lưu
        if not self.can_edit:
            InfoBar.warning("Truy cập bị từ chối", "Bạn không có quyền lưu/sửa Task EQA.", parent=self)
            return

        data = {
            "year": self.sp_year.value(),
            "round_no": self.cb_round.currentText().strip(),
            "provider_id": self.cb_provider.currentData(),
            "program_id": self.cb_program.currentData(),
            "sample_plan": self.ed_sample_name.text().strip(),
            "device_name": self.ed_device.text().strip(),
            "assigned_to": self.ed_assign.text().strip(),
            # Fluent CalendarPicker uses .date (property) instead of .date() (method)
            "start_date": self.dt_from.date.toString("yyyy-MM-dd"),
            "end_date": self.dt_to.date.toString("yyyy-MM-dd"),
            "due_date": self.due.date.toString("yyyy-MM-dd"),
            "status": self.cb_status.currentData(),
            "note": self.ed_note.text().strip(),
        }

        try:
            tid = self.dao.upsert_task(data, actor=self.username)
            InfoBar.success("Đã lưu", f"Đã lưu lịch (ID: {tid}).", parent=self)
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi lưu lịch", str(e))

    def _delete_task(self):
        row = self.tbl.currentRow()
        if row < 0:
            InfoBar.warning("Chọn dòng", "Chọn một lịch trong bảng để xoá.", parent=self)
            return

        if not self.can_edit:
            InfoBar.warning("Truy cập bị từ chối", "Bạn không có quyền xoá Task EQA.", parent=self)
            return

        tid_item = self.tbl.item(row, 0)
        tid = tid_item.text() if tid_item else None
        if not tid:
            InfoBar.warning("Thiếu ID", "Không xác định được ID lịch.", parent=self)
            return

        if QMessageBox.question(self, "Xác nhận xoá", f"Xoá lịch ID {tid}?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            n = self.dao.delete_task(int(tid))
            InfoBar.success("Kết quả", f"Đã xoá {n} lịch.", parent=self)
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xoá lịch", str(e))

    def _on_row_dbl_click(self, item: QTableWidgetItem):
        """Nạp dữ liệu từ bảng lên form editor (chỉ khi có quyền sửa)."""
        # Note: itemDoubleClicked signal sends item, not (row, col) in TableWidget sometimes,
        # but standard QTableWidget sends item.
        # Fluent TableWidget inherits QTableWidget.
        # But wait, original code connected to (r, c) or item?
        # Standard QTableWidget itemDoubleClicked emits (item). cellDoubleClicked emits (row, col).
        # Original code used: self.tbl.itemDoubleClicked.connect(self._on_row_dbl_click) which expects item.
        # But logic used r, c. This suggests original code might have been using cellDoubleClicked
        # OR the signature in original code was `def _on_row_dbl_click(self, item):` and derived row from item.
        # Looking at original code provided: `def _on_row_dbl_click(self, r: int, c: int):`
        # This implies `cellDoubleClicked` was likely used or intended.
        # However, line 204 in original code: `self.tbl.itemDoubleClicked.connect(self._on_row_dbl_click)`
        # This is a mismatch in original PyQt code (item vs row/col).
        # I will fix it to use `item` to get row.

        r = item.row()

        if not self.can_edit:
            self._open_task_detail()  # Mở chi tiết Task nếu không có quyền sửa form chính
            return

        def val(idx):
            it = self.tbl.item(r, idx)
            return it.text() if it else ""

        try:
            task_id = int(val(0))
        except ValueError:
            return

        task_data = next((t for t in self.dao.list_tasks(self.sp_year.value()) if t['id'] == task_id), None)
        if not task_data:
            return

        self.sp_year.setValue(task_data.get("year") or self.sp_year.value())
        self.cb_round.setCurrentText(task_data.get("round_no") or "")

        idx_p = self.cb_provider.findText(task_data.get("provider_name") or "")
        if idx_p >= 0: self.cb_provider.setCurrentIndex(idx_p)

        idx_prg = self.cb_program.findText(task_data.get("program_name") or "")
        if idx_prg >= 0: self.cb_program.setCurrentIndex(idx_prg)

        self.ed_sample_name.setText(task_data.get("sample_plan") or "")
        self.ed_device.setText(task_data.get("device_name") or "")
        self.ed_assign.setText(task_data.get("assigned_to") or "")

        # Fluent CalendarPicker uses setDate(QDate)
        if task_data.get("start_date"):
            self.dt_from.setDate(QDate.fromString(task_data.get("start_date"), "yyyy-MM-dd"))
        if task_data.get("end_date"):
            self.dt_to.setDate(QDate.fromString(task_data.get("end_date"), "yyyy-MM-dd"))
        if task_data.get("due_date"):
            self.due.setDate(QDate.fromString(task_data.get("due_date"), "yyyy-MM-dd"))

        idx_st = self.cb_status.findData(task_data.get("status") or "NEW")
        if idx_st >= 0: self.cb_status.setCurrentIndex(idx_st)

        self.ed_note.setText(task_data.get("note") or "")

    def _open_task_detail(self):
        """Mở dialog xem chi tiết Task, Log và cập nhật trạng thái."""
        row = self.tbl.currentRow()
        if row < 0:
            InfoBar.warning("Chọn Task", "Vui lòng chọn một Task để xem chi tiết.", parent=self)
            return

        task_id_item = self.tbl.item(row, 0)
        if not task_id_item: return

        try:
            task_id = int(task_id_item.text())
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "ID Task không hợp lệ.")
            return

        # Mở Dialog
        dlg = EQATaskDetailDialog(
            self,
            eqa_service=self.dao,
            auth_service=self.auth_service,
            audit_service=self.audit_service,
            task_id=task_id,
            current_username=self.username
        )

        if dlg.exec() == QDialog.Accepted:
            self._refresh()  # Reload bảng sau khi có cập nhật