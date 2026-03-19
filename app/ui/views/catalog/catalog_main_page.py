# -*- coding: utf-8 -*-
"""
app/features/catalog/catalog_main_page.py
(FIXED: Solved 'KeyError: mfg' and 'name' completely)
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, NamedTuple
import json

# --- PySide6 Standard Imports ---
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QInputDialog, QMessageBox, QSplitter, QFrame,
    QDialog
)

# --- Fluent UI Imports ---
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, ComboBox,
    TableWidget, ListWidget, FluentIcon as FIF,
    StrongBodyLabel, BodyLabel, TitleLabel,
    CalendarPicker, InfoBar
)

# Import Services
from app.services.catalog_service import CatalogService
from app.services.department_service import DepartmentService
from app.services.audit_service import AuditService

# --- Import Dialogs ---
from app.ui.dialogs.catalog_lot_dialog import open_add_lot_dialog, open_edit_lot_dialog
from app.ui.dialogs.catalog_detail_dialog import CatalogDetailDialog
from app.ui.dialogs.catalog_mapping_dialog import CatalogMappingDialog

# Vai trò được phép sửa
ELEVATED_ROLES = {"SUPERADMIN", "QA", "TRUONG_KHOA"}


# --- DTOs ---
class _UILot(NamedTuple):
    id: str
    name: str
    lot: str
    mfg_date: Optional[str]
    exp_date: Optional[str]
    department: Optional[str]
    status: Optional[str]
    level: Optional[str]


class CatalogMainPage(QWidget):
    # ĐỊNH NGHĨA CỘT CHO BẢNG ANALYTES
    COLS = [
        "Phòng ban", "Tên xét nghiệm", "Level", "Thứ tự", "Phân loại", "Kiểu dữ liệu",
        "Đơn vị", "Giá trị đích / Mean", "SD / Khoảng tham chiếu", "TEa", "Ghi chú"
    ]

    def __init__(self, current_username: str, current_role: str, current_department: str, parent=None):
        super().__init__(parent)
        self.setObjectName("CatalogMainPage")

        self.username = current_username
        self.role = (current_role or "").upper()
        self.department = current_department or ""
        self.is_elevated = self.role in ELEVATED_ROLES

        # Khởi tạo Services
        self.catalog_service = CatalogService()
        self.dept_service = DepartmentService()
        self.audit_service = AuditService()

        self.current_lot_id: Optional[str] = None
        self._lots_cache: List[_UILot] = []
        self._details_cache: List[Dict] = []

        self._build_ui()
        self._load_departments_filter()
        self._load_lots()
        self._apply_permissions()

        # Log truy cập
        try:
            self.audit_service.log_action(self.username, "OPEN_PAGE", target="catalog_main_page")
        except:
            pass

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ==================================================
        # LEFT PANEL: DANH SÁCH LOT & BỘ LỌC
        # ==================================================
        left_container = CardWidget(self)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        left_layout.addWidget(StrongBodyLabel("Danh sách LOT", self))

        self.list_lots = ListWidget(self)
        self.list_lots.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        left_layout.addWidget(self.list_lots, 1)

        btn_bar_lot = QHBoxLayout()
        btn_bar_lot.setSpacing(8)
        self.b_add_lot = PrimaryPushButton(FIF.ADD, "Thêm", self)
        self.b_edit_lot = PushButton(FIF.EDIT, "Sửa", self)
        self.b_del_lot_multi = PushButton(FIF.DELETE, "Xoá", self)
        self.b_clone = PushButton(FIF.COPY, "Clone", self)
        self.btn_mapping = PushButton(FIF.IOT, "Mapping", self)

        # Kết nối nút Mapping
        self.btn_mapping.clicked.connect(self._open_mapping_dialog)

        for btn in [self.b_add_lot, self.b_edit_lot, self.b_del_lot_multi, self.b_clone, self.btn_mapping]:
            btn.setFixedHeight(32)
            btn_bar_lot.addWidget(btn)

        left_layout.addLayout(btn_bar_lot)

        # Filter Section
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(sep)
        left_layout.addWidget(StrongBodyLabel("Bộ lọc", self))

        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(10)

        h_dep = QHBoxLayout()
        h_dep.addWidget(BodyLabel("Phòng ban:", self))
        self.f_dep = ComboBox(self)
        self.f_dep.addItem("— Tất cả —", "")
        h_dep.addWidget(self.f_dep, 1)
        filter_layout.addLayout(h_dep)

        h_stat = QHBoxLayout()
        h_stat.addWidget(BodyLabel("Trạng thái:", self))
        self.f_status = ComboBox(self)
        self.f_status.addItems(["— Tất cả —", "active", "dis"])
        h_stat.addWidget(self.f_status, 1)
        filter_layout.addLayout(h_stat)

        h_date = QHBoxLayout()
        self.f_exp_from = CalendarPicker(self)
        self.f_exp_from.setDateFormat(Qt.DateFormat.ISODate)
        self.f_exp_to = CalendarPicker(self)
        self.f_exp_to.setDateFormat(Qt.DateFormat.ISODate)

        h_date.addWidget(BodyLabel("HSD Từ:", self))
        h_date.addWidget(self.f_exp_from)
        h_date.addSpacing(5)
        h_date.addWidget(BodyLabel("Đến:", self))
        h_date.addWidget(self.f_exp_to)
        filter_layout.addLayout(h_date)

        self.b_apply_filter = PushButton(FIF.FILTER, "Áp dụng", self)
        filter_layout.addWidget(self.b_apply_filter)
        left_layout.addLayout(filter_layout)

        # Excel Import/Export
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(sep2)
        exim_layout = QHBoxLayout()
        self.b_export_xl = PushButton(FIF.SAVE, "Xuất Excel", self)
        self.b_import_xl = PushButton(FIF.FOLDER, "Nhập Excel", self)
        exim_layout.addWidget(self.b_export_xl)
        exim_layout.addWidget(self.b_import_xl)
        left_layout.addLayout(exim_layout)

        splitter.addWidget(left_container)

        # ==================================================
        # RIGHT PANEL: ANALYTES
        # ==================================================
        right_container = CardWidget(self)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        right_header = QHBoxLayout()
        right_header.addWidget(TitleLabel("Chi tiết Analytes (Chỉ số)", self))
        right_header.addStretch(1)

        right_header.addWidget(BodyLabel("Loại XN:", self))
        self.f_type = ComboBox(self)
        self.f_type.addItems(["— Tất cả —", "Quant", "Semi", "Qual"])
        self.f_type.setFixedWidth(150)
        right_header.addWidget(self.f_type)

        right_layout.addLayout(right_header)

        self.tbl = TableWidget(self)
        self.tbl.setColumnCount(len(self.COLS))
        self.tbl.setHorizontalHeaderLabels(self.COLS)
        self.tbl.verticalHeader().hide()
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setBorderVisible(True)
        self.tbl.setWordWrap(False)
        right_layout.addWidget(self.tbl, 1)

        ana_btn_layout = QHBoxLayout()
        self.b_add_analyte = PrimaryPushButton(FIF.ADD, "Thêm", self)
        self.b_edit_analyte = PushButton(FIF.EDIT, "Sửa", self)
        self.b_del_analyte_multi = PushButton(FIF.DELETE, "Xoá (nhiều)", self)

        ana_btn_layout.addWidget(self.b_add_analyte)
        ana_btn_layout.addWidget(self.b_edit_analyte)
        ana_btn_layout.addWidget(self.b_del_analyte_multi)
        ana_btn_layout.addStretch(1)
        right_layout.addLayout(ana_btn_layout)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

        # Connect Events
        self.list_lots.itemSelectionChanged.connect(self._on_select_lot)
        self.b_add_lot.clicked.connect(self._on_add_lot)
        self.b_edit_lot.clicked.connect(self._on_edit_lot)
        self.b_del_lot_multi.clicked.connect(self._on_del_lot_multi)
        self.b_clone.clicked.connect(self._on_clone_from)

        self.b_add_analyte.clicked.connect(self._on_add_detail)
        self.b_edit_analyte.clicked.connect(self._on_edit_detail)
        self.b_del_analyte_multi.clicked.connect(self._on_del_detail_multi)
        self.tbl.doubleClicked.connect(lambda: self._on_edit_detail())

        self.f_type.currentIndexChanged.connect(self._refresh_details_table)
        self.b_apply_filter.clicked.connect(self._apply_filters)

        self.b_export_xl.clicked.connect(self._export_excel_ui)
        self.b_import_xl.clicked.connect(self._import_excel_service)

    def _apply_permissions(self):
        if self.role in ELEVATED_ROLES:
            return
        for b in [self.b_add_lot, self.b_edit_lot, self.b_del_lot_multi, self.b_clone,
                  self.b_import_xl, self.b_add_analyte, self.b_edit_analyte,
                  self.b_del_analyte_multi, self.btn_mapping]:
            b.setEnabled(False)
            b.setToolTip("Yêu cầu quyền QA hoặc Trưởng khoa")

    # ---------------- LOAD DATA ----------------
    def _load_departments_filter(self):
        try:
            deps = self.dept_service.list_departments(active_only=False)
            self.f_dep.clear()
            self.f_dep.addItem("— Tất cả —", "")
            for d in deps:
                name = getattr(d, 'name', "") or d.get('name', "")
                if name:
                    self.f_dep.addItem(str(name), str(name))
        except Exception as e:
            print(f"[Catalog UI] Lỗi nạp phòng ban: {e}")

    @staticmethod
    def _to_ui_lot(r: Dict[str, Any]) -> _UILot:
        return _UILot(
            id=str(r.get("id", "")),
            name=str(r.get("lot_name") or r.get("name") or ""),
            lot=str(r.get("lot_no") or r.get("lot") or ""),
            mfg_date=r.get("mfg_date"),
            exp_date=r.get("expiry_date") or r.get("exp_date"),
            department=r.get("department"),
            status=r.get("status"),
            level=r.get("level")
        )

    def _render_lot_list(self, lots: List[Dict]):
        self.list_lots.clear()
        self._lots_cache = [self._to_ui_lot(r) for r in lots]

        for lt in self._lots_cache:
            level_tag = f"[{lt.level}] " if lt.level else ""
            text = f"{level_tag}{lt.name} — Lot: {lt.lot}"

            if lt.department:
                text = f"[{lt.department}] {text}"
            if lt.status != 'active':
                text += f" ({lt.status or 'dis'})"

            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, lt.id)

            try:
                if lt.exp_date:
                    exp_dt = QDate.fromString(str(lt.exp_date), Qt.DateFormat.ISODate)
                    if exp_dt.isValid() and exp_dt.daysTo(QDate.currentDate()) > -30:
                        it.setForeground(QColor("#D9534F"))
            except:
                pass

            if lt.status != 'active':
                it.setForeground(QColor("#7F8C8D"))

            self.list_lots.addItem(it)

        if self.list_lots.count() > 0:
            self.list_lots.setCurrentRow(0)

    def _load_lots(self):
        status_filter = self.f_status.currentData()
        lots = self.catalog_service.search_lots(
            status="active" if status_filter == "active" else None
        )
        self._render_lot_list(lots)

    def _apply_filters(self):
        dep = self.f_dep.currentData() or None
        st = self.f_status.currentData() or None
        d_from = self.f_exp_from.date.toString(Qt.DateFormat.ISODate) if self.f_exp_from.date.isValid() else None
        d_to = self.f_exp_to.date.toString(Qt.DateFormat.ISODate) if self.f_exp_to.date.isValid() else None

        lots = self.catalog_service.search_lots(
            department=dep, status=st,
            exp_from=d_from, exp_to=d_to
        )
        self._render_lot_list(lots)

    def _on_select_lot(self):
        items = self.list_lots.selectedItems()
        self.current_lot_id = (items[0].data(Qt.ItemDataRole.UserRole) if items else None)

        if self.current_lot_id:
            self._details_cache = self.catalog_service.list_details(self.current_lot_id)
        else:
            self._details_cache = []
        self._refresh_details_table()

    # ---------------- LOT CRUD (FIXED HERE) ----------------
    def _on_add_lot(self):
        data = open_add_lot_dialog(
            self,
            dept_service=self.dept_service,
            catalog_service=self.catalog_service
        )
        if not data: return

        try:
            # [FIXED] Dùng .get() để lấy mfg_date/exp_date tránh lỗi KeyError 'mfg'
            lot_id = self.catalog_service.create_lot(
                name=data.get("name"),
                lot=data.get("lot") or data.get("lot_code"),

                # Sửa lỗi chính tại đây:
                mfg_date=data.get("mfg_date") or data.get("mfg"),
                exp_date=data.get("exp_date") or data.get("exp"),

                department=data.get("department"),
                status=data.get("status"),
                level=data.get("level"),
                device_sample_id=data.get("device_sample_id")  # Mapping ID
            )
            self.audit_service.log_action(self.username, "CREATE_LOT", f"lot:{lot_id}", after=data)
            InfoBar.success("Thành công", "Đã thêm Lot mới", parent=self)
            self._load_lots()
        except Exception as e:
            QMessageBox.critical(self, "Thêm Lot", f"Lỗi: {e}")

    def _on_edit_lot(self):
        if not self.current_lot_id:
            InfoBar.warning("Chú ý", "Hãy chọn LOT trước.", parent=self)
            return

        defaults = self.catalog_service.get_lot(self.current_lot_id)
        if not defaults: return

        data = open_edit_lot_dialog(
            defaults, self,
            dept_service=self.dept_service,
            catalog_service=self.catalog_service
        )
        if not data: return

        try:
            # [FIXED] Dùng .get() để lấy mfg_date/exp_date tránh lỗi KeyError 'mfg'
            self.catalog_service.update_lot(
                self.current_lot_id,
                name=data.get("name"),
                lot=data.get("lot") or data.get("lot_code"),

                # Sửa lỗi chính tại đây:
                mfg_date=data.get("mfg_date") or data.get("mfg"),
                exp_date=data.get("exp_date") or data.get("exp"),

                department=data.get("department"),
                status=data.get("status"),
                level=data.get("level"),
                device_sample_id=data.get("device_sample_id")  # Mapping ID
            )
            self.audit_service.log_action(self.username, "UPDATE_LOT", f"lot:{self.current_lot_id}", before=defaults,
                                          after=data)
            InfoBar.success("Thành công", "Cập nhật Lot thành công", parent=self)
            self._load_lots()
            self._refresh_details_table()
        except Exception as e:
            QMessageBox.critical(self, "Sửa Lot", f"Lỗi: {e}")

    def _on_del_lot_multi(self):
        items = self.list_lots.selectedItems()
        if not items: return
        ids = [it.data(Qt.ItemDataRole.UserRole) for it in items]

        if QMessageBox.question(self, "Xác nhận", f"Xoá {len(ids)} LOT đã chọn?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.catalog_service.delete_lots(ids)
            self.audit_service.log_action(self.username, "DELETE_LOTS", f"count:{len(ids)}", before={"ids": ids})
            InfoBar.success("Thành công", f"Đã xóa {len(ids)} Lot", parent=self)
            self._load_lots()
        except Exception as e:
            QMessageBox.critical(self, "Xoá nhiều LOT", f"Lỗi: {e}")

    def _on_clone_from(self):
        dst = self.current_lot_id
        if not dst:
            InfoBar.warning("Clone", "Hãy chọn LOT đích trước.", parent=self)
            return

        src_str, ok = QInputDialog.getText(self, "Clone từ LOT", "Nhập ID LOT nguồn:")
        if not ok or not src_str.strip(): return
        src = str(src_str.strip())

        overwrite = (QMessageBox.question(self, "Ghi đè?", "Xoá analytes cũ?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes)
        try:
            n = self.catalog_service.clone_details(src, dst, overwrite=overwrite)
            self.audit_service.log_action(self.username, "CLONE_LOT_DETAILS", f"from:{src}_to:{dst}",
                                          note=f"copied:{n}")
            InfoBar.success("Clone", f"Đã copy {n} analyte.", parent=self)
            self._on_select_lot()
        except Exception as e:
            QMessageBox.critical(self, "Clone", f"Lỗi: {e}")

    # ---------------- DETAIL CRUD ----------------
    def _current_detail_ids(self) -> List[str]:
        ids = []
        sel = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() else []
        for idx in sel:
            it = self.tbl.item(idx.row(), 0)
            if it and it.data(Qt.ItemDataRole.UserRole):
                ids.append(str(it.data(Qt.ItemDataRole.UserRole)))
        return ids

    def _refresh_details_table(self):
        self.tbl.setRowCount(0)
        if not self._details_cache: return

        self.tbl.setRowCount(len(self._details_cache))

        # Filter type
        current_type_filter = self.f_type.currentText()
        if current_type_filter == "— Tất cả —": current_type_filter = None

        r_idx = 0
        for d in self._details_cache:
            meta = {}
            note_str = d.get("note")
            if note_str and isinstance(note_str, str) and "{" in note_str:
                try:
                    meta = json.loads(note_str)
                except:
                    meta = {}

            dtype = d.get("data_type", "Quant")

            # Client-side filter (nếu muốn)
            if current_type_filter and dtype != current_type_filter:
                continue

            display_target = d.get("mean") if dtype == "Quant" else (meta.get("target") or d.get("mean") or "")
            display_ref = d.get("sd") if dtype == "Quant" else (
                    meta.get("reference_range") or d.get("reference_range") or d.get("sd") or "")
            is_numeric = (dtype == "Quant")

            def _set(col, text, is_num=False):
                val_str = str(text) if text is not None else ""
                if val_str == "0.0" and not is_num: val_str = ""
                it = QTableWidgetItem(val_str)
                align = Qt.AlignmentFlag.AlignRight if is_num else Qt.AlignmentFlag.AlignLeft
                it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                if col == 0: it.setData(Qt.ItemDataRole.UserRole, d.get("id"))
                self.tbl.setItem(r_idx, col, it)

            _set(0, d.get("department"))
            _set(1, d.get("test_name"))
            _set(2, d.get("level"))
            _set(3, d.get("sort_order"))
            _set(4, d.get("category"))
            _set(5, dtype)
            _set(6, d.get("unit") or meta.get("unit") or "")
            _set(7, display_target, is_num=is_numeric)
            _set(8, display_ref, is_num=is_numeric)
            _set(9, d.get("tea"), is_num=True)
            _set(10, note_str)

            r_idx += 1

        self.tbl.setRowCount(r_idx)

    def _on_add_detail(self):
        if not self.current_lot_id:
            InfoBar.warning("Thông báo", "Hãy chọn một LOT trước khi thêm chỉ số.", parent=self)
            return

        lot_data = self.catalog_service.get_lot(self.current_lot_id)
        if not lot_data:
            InfoBar.error("Lỗi", "Không tìm thấy dữ liệu của Lot này.", parent=self)
            return

        dlg = CatalogDetailDialog(
            self,
            dept_name=lot_data.get("department") or "",
            dept_service=self.dept_service,
            catalog_service=self.catalog_service,
            prefill_lot_data=lot_data,
            prefill=None
        )

        if dlg.exec() != QDialog.DialogCode.Accepted: return

        try:
            data = dlg.values()
            self.catalog_service.create_detail(
                lot_id=self.current_lot_id,
                department=data["department"],
                test_name=data["test_name"],
                mean=data.get("mean"), sd=data.get("sd"), tea=data.get("tea"),
                note=data["note"], level=data.get("level"),
                data_type=data.get("data_type"), unit=data.get("unit"),
                reference_range=data.get("reference_range"), category=data.get("category"),
                sort_order=data.get("sort_order")
            )
            # Sync Catalog
            self.catalog_service.upsert_catalog(
                data["department"], data["test_name"],
                data_type=data.get("data_type"), default_unit=data.get("unit")
            )

            InfoBar.success("Thành công", f"Đã thêm '{data['test_name']}'", parent=self)
            self._details_cache = self.catalog_service.list_details(self.current_lot_id)
            self._refresh_details_table()
        except Exception as ex:
            QMessageBox.critical(self, "Lỗi thực thi", f"Không thể lưu: {ex}")

    def _on_edit_detail(self):
        ids = self._current_detail_ids()
        if len(ids) != 1:
            InfoBar.warning("Sửa chỉ số", "Hãy chọn đúng 1 dòng.", parent=self)
            return

        detail_id = ids[0]
        old_data = self.catalog_service.get_detail(detail_id)
        lot_data = self.catalog_service.get_lot(self.current_lot_id)
        dep_name = lot_data.get("department", "")

        dlg = CatalogDetailDialog(
            self,
            dept_name=dep_name,
            dept_service=self.dept_service,
            catalog_service=self.catalog_service,
            prefill_lot_data=lot_data,
            prefill=old_data
        )
        if dlg.exec() != QDialog.DialogCode.Accepted: return

        try:
            data = dlg.values()
            self.catalog_service.update_detail(
                detail_id,
                test_name=data["test_name"], level=data.get("level"),
                mean=data.get("mean"), sd=data.get("sd"), tea=data.get("tea"),
                note=data["note"], data_type=data.get("data_type"),
                unit=data.get("unit"), reference_range=data.get("reference_range"),
                category=data.get("category"), sort_order=data.get("sort_order")
            )
            self.catalog_service.upsert_catalog(
                data["department"], data["test_name"],
                data_type=data.get("data_type"), default_unit=data.get("unit")
            )
            InfoBar.success("Thành công", "Cập nhật thành công", parent=self)
            self._details_cache = self.catalog_service.list_details(self.current_lot_id)
            self._refresh_details_table()
        except Exception as ex:
            QMessageBox.critical(self, "Lỗi", f"{ex}")

    def _on_del_detail_multi(self):
        ids = self._current_detail_ids()
        if not ids: return
        if QMessageBox.question(self, "Xác nhận", f"Xoá {len(ids)} dòng?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.catalog_service.delete_details(ids)
            InfoBar.success("Thành công", f"Đã xóa {len(ids)} dòng", parent=self)
            self._details_cache = self.catalog_service.list_details(self.current_lot_id)
            self._refresh_details_table()

    # ---------------- Import/Export ----------------
    def _export_excel_ui(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu Excel", "qc_catalog.xlsx", "Excel (*.xlsx)")
        if path:
            try:
                self.catalog_service.export_excel(path, lot_id=self.current_lot_id)
                InfoBar.success("Excel", f"Xuất thành công: {path}", parent=self)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))

    def _import_excel_service(self):
        path, _ = QFileDialog.getOpenFileName(self, "Mở Excel", "", "Excel (*.xlsx)")
        if path:
            try:
                res = self.catalog_service.import_excel(path, default_lot_id=self.current_lot_id)
                QMessageBox.information(self, "Kết quả", f"Lots: {res.get('lots')}, Analytes: {res.get('analytes')}")
                self._load_lots()
                self._on_select_lot()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))

    def _open_mapping_dialog(self):
        """Mở dialog mapping cho danh sách hiện tại"""
        if not self._details_cache:
            InfoBar.warning("Chú ý", "Hãy chọn một LOT và đảm bảo có danh sách xét nghiệm.", parent=self)
            return

        dlg = CatalogMappingDialog(self, data_list=self._details_cache, service=self.catalog_service)
        if dlg.exec():
            self._details_cache = self.catalog_service.list_details(self.current_lot_id)
            self._refresh_details_table()
            InfoBar.success("Thành công", "Đã cập nhật mapping", parent=self)