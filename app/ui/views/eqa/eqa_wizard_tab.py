# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_wizard_tab.py
Giao diện Nhập kết quả EQA.
(CONVERTED TO FLUENT UI - LOGIC PRESERVED)
CẬP NHẬT: Thêm cột U_lab và En-Score (Phân tích MU).
"""
import datetime as dt
import json
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
    QTableWidgetItem, QHeaderView, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# --- Fluent UI Imports ---
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, ComboBox,
    LineEdit, SpinBox, TableWidget, FluentIcon as FIF,
    StrongBodyLabel, BodyLabel, InfoBar
)

# Import Service
from app.services.eqa_service import EQAService


# Logic helper
def _to_float(value):
    try:
        return float(str(value).replace(',', '.'))
    except (ValueError, TypeError):
        return None


# Hằng số màu sắc (sử dụng trong Logic)
COLOR_FAIL_BG = QColor("#F8C4C4")  # Đỏ nhạt (Fail)
COLOR_WARN_BG = QColor("#FFF2B2")  # Vàng nhạt (Warning)
COLOR_PASS_BG = QColor("#D6F5D6")  # Xanh nhạt (Pass)


class EqaWizardTab(QWidget):
    def __init__(self,
                 parent: Optional[QWidget] = None,
                 db_path: Optional[str] = None,
                 username: Optional[str] = None,
                 role: Optional[str] = None,
                 **kwargs):
        super().__init__(parent)

        self.username = username or "user"
        self.role = role or ""
        self.dao = EQAService()

        self._provider_id = None
        self._program_id = None
        self._round_id = None

        self._build_ui()
        self._load_providers()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # --- Card Nhập liệu ---
        input_card = CardWidget(self)
        grid = QGridLayout(input_card)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(12)

        # Row 1: Provider, Program
        self.cb_provider = ComboBox()
        self.cb_provider.setPlaceholderText("Chọn Nhà CC")

        self.cb_program = ComboBox()
        self.cb_program.setPlaceholderText("Chọn Chương trình")

        grid.addWidget(BodyLabel("Nhà cung cấp:", self), 0, 0)
        grid.addWidget(self.cb_provider, 0, 1)
        grid.addWidget(BodyLabel("Chương trình:", self), 0, 2)
        grid.addWidget(self.cb_program, 0, 3)

        # Row 2: Year, Round, Device
        self.sp_year = SpinBox()
        self.sp_year.setRange(2000, 2100)
        self.sp_year.setValue(dt.datetime.now().year)

        self.cb_round = ComboBox()
        self.cb_round.addItems([f"{i:02d}" for i in range(1, 13)])

        self.ed_device = LineEdit()
        self.ed_device.setPlaceholderText("Tên máy/thiết bị")

        grid.addWidget(BodyLabel("Năm:", self), 1, 0)
        grid.addWidget(self.sp_year, 1, 1)
        grid.addWidget(BodyLabel("Đợt:", self), 1, 2)
        grid.addWidget(self.cb_round, 1, 3)
        grid.addWidget(BodyLabel("Thiết bị:", self), 1, 4)
        grid.addWidget(self.ed_device, 1, 5)

        root.addWidget(input_card)

        # --- Toolbar Buttons ---
        btn_layout = QHBoxLayout()

        self.btn_load = PushButton(FIF.SYNC, "Tải thông số", self)
        self.btn_calc = PushButton(FIF.EDIT, "Tính Toán (SDI/En)", self)  # Updated label

        self.btn_add = PushButton(FIF.ADD, "Thêm dòng", self)
        self.btn_del = PushButton(FIF.DELETE, "Xoá dòng", self)
        self.btn_save = PrimaryPushButton(FIF.SAVE, "Lưu kết quả", self)

        btn_layout.addWidget(self.btn_load)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_calc)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addWidget(self.btn_save)

        root.addLayout(btn_layout)

        # --- Bảng nhập ---
        # Columns: Analyte, Unit, Lab Result, Group Mean, Group SD, U_lab, En Score, Eval, Note
        self.COL_ANALYTE = 0
        self.COL_UNIT = 1
        self.COL_SITE = 2
        self.COL_CENTER = 3
        self.COL_SD = 4  # New: Group SD column for Z-score
        self.COL_ULAB = 5
        self.COL_EN_SCORE = 6  # Display both Z and En
        self.COL_EVAL = 7  # Pass/Fail
        self.COL_NOTE = 8

        self.tbl = TableWidget(self)
        self.tbl.setColumnCount(9)
        self.tbl.setHorizontalHeaderLabels([
            "Thông số*", "Đơn vị", "KQ Lab*", "Target Mean*", "Target SD",
            "U_Lab (k=2)", "Scores (Z | En)", "Đánh giá", "Ghi chú"
        ])

        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_ANALYTE, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(self.COL_EN_SCORE, QHeaderView.ResizeToContents)
        self.tbl.verticalHeader().hide()
        self.tbl.setBorderVisible(True)

        root.addWidget(self.tbl, 1)

        # --- Kết nối sự kiện ---
        self.cb_provider.currentIndexChanged.connect(self._on_provider_changed)
        self.cb_program.currentIndexChanged.connect(self._on_program_changed)
        self.sp_year.valueChanged.connect(self._on_round_changed)
        self.cb_round.currentIndexChanged.connect(self._on_round_changed)
        self.ed_device.textChanged.connect(self._on_round_changed)

        self.btn_load.clicked.connect(self._load_params_to_table)
        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._del_selected)
        self.btn_save.clicked.connect(self._save_results)
        self.btn_calc.clicked.connect(self._calculate_all)

        self.tbl.cellChanged.connect(self._on_cell_changed)
        self._on_program_changed()

    def _on_cell_changed(self, row: int, column: int):
        # Auto-calculate when inputs change
        if column in [self.COL_SITE, self.COL_CENTER, self.COL_SD, self.COL_ULAB]:
            self._calculate_row(row)

    # --- HÀM TÍNH TOÁN (CORE) ---
    def _calculate_row(self, row: int):
        try:
            # 1. Get raw values
            lab_val = _to_float(self._get_text(row, self.COL_SITE))
            mean_val = _to_float(self._get_text(row, self.COL_CENTER))
            sd_val = _to_float(self._get_text(row, self.COL_SD))
            u_lab = _to_float(self._get_text(row, self.COL_ULAB))

            if lab_val is None or mean_val is None:
                return  # Not enough data

            # 2. Calculate Z-Score
            z_score = None
            if sd_val and sd_val != 0:
                z_score = self.dao.calculate_z_score(lab_val, mean_val, sd_val)

            # 3. Calculate En-Score
            en_score = None
            if u_lab and u_lab > 0:
                # Estimate U_ref if not provided.
                # Standard practice: U_ref is often approximated as 0 if Group N is large,
                # or derived from Group SD / sqrt(N).
                # Here we assume U_ref ~ 0 for simplicity if not in DB,
                # OR we could add a column for U_ref. Let's use 0.
                u_ref = 0.0
                en_score = self.dao.calculate_en_score(lab_val, mean_val, u_lab, u_ref)

            # 4. Evaluate & Display
            score_text = ""
            eval_text = "---"
            bg_color = QColor(Qt.white)

            # Logic đánh giá tổng hợp
            is_fail = False
            is_warn = False

            if z_score is not None:
                score_text += f"Z={z_score:.2f}"
                if abs(z_score) > 3.0:
                    is_fail = True
                elif abs(z_score) > 2.0:
                    is_warn = True

            if en_score is not None:
                score_text += f" | En={en_score:.2f}"
                if abs(en_score) > 1.0: is_fail = True  # ISO 13528 criteria

            if is_fail:
                eval_text = "KHÔNG ĐẠT"
                bg_color = COLOR_FAIL_BG
            elif is_warn:
                eval_text = "CẢNH BÁO"
                bg_color = COLOR_WARN_BG
            elif z_score is not None or en_score is not None:
                eval_text = "ĐẠT"
                bg_color = COLOR_PASS_BG

            # Update UI (Blocked signals to prevent recursion)
            self.tbl.blockSignals(True)

            item_score = QTableWidgetItem(score_text)
            item_score.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(row, self.COL_EN_SCORE, item_score)

            item_eval = QTableWidgetItem(eval_text)
            item_eval.setTextAlignment(Qt.AlignCenter)
            item_eval.setBackground(bg_color)
            item_eval.setFlags(Qt.ItemIsEnabled)  # Read-only
            self.tbl.setItem(row, self.COL_EVAL, item_eval)

            self.tbl.blockSignals(False)

        except Exception as e:
            print(f"Calc Error Row {row}: {e}")

    def _calculate_all(self):
        for r in range(self.tbl.rowCount()):
            self._calculate_row(r)
        InfoBar.success("Hoàn tất", "Đã cập nhật kết quả tính toán.", parent=self)
        self.tbl.resizeColumnsToContents()

    def _get_text(self, row, col):
        item = self.tbl.item(row, col)
        return item.text() if item else ""

    # --- DATA LOADING ---

    def _load_providers(self):
        self.cb_provider.blockSignals(True)
        self.cb_provider.clear()
        self.cb_provider.addItem("— Chọn nhà CC —", None)
        for r in self.dao.list_providers():
            self.cb_provider.addItem(r["name"], r["id"])
        self.cb_provider.blockSignals(False)

    def _on_provider_changed(self):
        self._provider_id = self.cb_provider.currentData()
        self.cb_program.blockSignals(True)
        self.cb_program.clear()
        self.cb_program.addItem("— Chọn chương trình —", None)
        if self._provider_id:
            for r in self.dao.list_programs(self._provider_id):
                disp = f"{r['name']} ({r['code']})" if r['code'] else r['name']
                self.cb_program.addItem(disp, r["id"])
        self.cb_program.blockSignals(False)
        self._on_program_changed()

    def _on_program_changed(self):
        self._program_id = self.cb_program.currentData()
        self._on_round_changed()

    def _on_round_changed(self, *args):
        if self._program_id is None:
            self._round_id = None
            return

        year = self.sp_year.value()
        rnd = self.cb_round.currentText()
        dev = self.ed_device.text().strip() or None

        try:
            self._round_id = self.dao.get_or_create_round(self._program_id, year, rnd, dev)
            self._load_existing_results()
        except Exception as e:
            self._round_id = None
            self.tbl.setRowCount(0)

    def _load_params_to_table(self):
        if self._program_id is None:
            InfoBar.warning("Chọn chương trình", "Vui lòng chọn chương trình trước.", parent=self)
            return

        params = self.dao.get_param_templates(self._program_id) or []
        self.tbl.setRowCount(0)

        if not params:
            for _ in range(5): self._add_row()
            return

        for p in params:
            i = self.tbl.rowCount()
            self.tbl.insertRow(i)
            self.tbl.setItem(i, self.COL_ANALYTE, QTableWidgetItem(p.get("analyte") or ""))
            self.tbl.setItem(i, self.COL_UNIT, QTableWidgetItem(p.get("unit") or ""))
            # Init empty cells
            for c in [self.COL_SITE, self.COL_CENTER, self.COL_SD, self.COL_ULAB, self.COL_NOTE]:
                self.tbl.setItem(i, c, QTableWidgetItem(""))
            self.tbl.setItem(i, self.COL_EN_SCORE, QTableWidgetItem("---"))
            self.tbl.setItem(i, self.COL_EVAL, QTableWidgetItem("---"))

    def _load_existing_results(self):
        if not self._round_id:
            self.tbl.setRowCount(0)
            return

        rows = self.dao.get_results(self._round_id) or []
        self.tbl.setRowCount(0)
        for r in rows:
            i = self.tbl.rowCount()
            self.tbl.insertRow(i)

            # Metadata parsing logic moved to Service, here we just use what Service returns
            # Service returns dict with 'u_lab' key extracted
            u_lab = str(r.get("u_lab") or "")

            # Note might contain JSON, show raw text or parsed text?
            # Ideally show clean note. For simplicity, we show raw note but user can edit.
            # Or better: Extract simple note if JSON structure exists.
            note_raw = r.get("note") or ""
            note_display = note_raw
            try:
                if note_raw.startswith("{"):
                    meta = json.loads(note_raw)
                    note_display = meta.get("text", "")  # Display only text part
            except:
                pass

            self.tbl.setItem(i, self.COL_ANALYTE, QTableWidgetItem(r.get("analyte") or ""))
            self.tbl.setItem(i, self.COL_UNIT, QTableWidgetItem(r.get("unit") or ""))
            self.tbl.setItem(i, self.COL_SITE, QTableWidgetItem(str(r.get("result_site") or "")))
            self.tbl.setItem(i, self.COL_CENTER, QTableWidgetItem(str(r.get("result_center") or "")))

            # SD isn't explicitly in DB result schema yet, assume user inputs it or it's part of 'result_center' logic
            # For now, leave blank or load if you add an SD column to DB
            self.tbl.setItem(i, self.COL_SD, QTableWidgetItem(""))

            self.tbl.setItem(i, self.COL_ULAB, QTableWidgetItem(u_lab))
            self.tbl.setItem(i, self.COL_NOTE, QTableWidgetItem(note_display))

            # Calc
            self._calculate_row(i)

    def _add_row(self):
        self.tbl.insertRow(self.tbl.rowCount())

    def _del_selected(self):
        i = self.tbl.currentRow()
        if i >= 0: self.tbl.removeRow(i)

    def _save_results(self):
        if not self._round_id:
            InfoBar.warning("Lỗi", "Chưa có thông tin đợt (Round).", parent=self)
            return

        items = []
        for i in range(self.tbl.rowCount()):
            analyte_item = self.tbl.item(i, self.COL_ANALYTE)
            analyte = analyte_item.text().strip() if analyte_item else ""
            if not analyte: continue

            # Get raw values
            unit = self._get_text(i, self.COL_UNIT)
            site = self._get_text(i, self.COL_SITE)
            center = self._get_text(i, self.COL_CENTER)
            note_text = self._get_text(i, self.COL_NOTE)
            u_lab = self._get_text(i, self.COL_ULAB)  # Only store U_lab, SD is usually ephemeral or config

            # Note handling: Service expects 'u_lab' key in item dict to pack into JSON
            item_data = {
                "analyte": analyte,
                "unit": unit,
                "result_site": site,
                "result_center": center,
                "note": note_text,
                "u_lab": _to_float(u_lab)  # Pass float to service
            }
            items.append(item_data)

        if not items:
            InfoBar.warning("Trống", "Không có dữ liệu để lưu.", parent=self)
            return

        try:
            self.dao.save_results(self._round_id, items, actor=self.username)
            InfoBar.success("Đã lưu", f"Đã lưu {len(items)} kết quả vào CSDL.", parent=self)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi lưu", str(e))