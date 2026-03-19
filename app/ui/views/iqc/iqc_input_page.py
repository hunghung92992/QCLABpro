# -*- coding: utf-8 -*-
"""
/iqc/iqc_input_page.py
(FULL MERGED VERSION: PySide6 + Windows 11 Fluent Design + Caching + Pre-Westgard + Delta Check)
[UPDATED]:
- Fix target_mean -> mean
- Add Import Excel Button
- Fix UUID handling in Edit/Delete
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple
import getpass
import json ,os
from app.services.capa_service import CapaService
# --- PYSIDE6 IMPORTS ---
from PySide6.QtCore import (
    Qt, QTimer, QDate, QPointF, QModelIndex, QEvent
)
from PySide6.QtGui import (
    QColor, QKeySequence, QBrush, QFont, QPainter, QPen
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLabel,
    QPushButton, QCheckBox, QMessageBox, QDialog,
    QDateEdit, QTabWidget, QDialogButtonBox, QHeaderView,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QStyledItemDelegate, QMenu, QStyleOptionViewItem,
    QAbstractItemView, QFrame, QStyle, QFileDialog
)
import xlsxwriter
from app.ui.dialogs.standard_capa_dialog import StandardCapaDialog
# Imports helper functions from qt_compat
from app.utils.qt_compat import (
    set_combo_by_id, add_combo_item, get_combo_id, fill_combo_from_list,
    combo_find_text_ci, clear_combo
)

from app.core.database_orm import get_db_connection
from qfluentwidgets import (
    InfoBar,           # <--- THÊM DÒNG NÀY
    # <--- (Nên thêm cái này để chỉnh vị trí thông báo)

)
# Services
from app.services.iqc_service import IQCService
from app.services.catalog_service import CatalogService
from app.services.department_service import DepartmentService
from app.services.iqc_schedule_service import IQCScheduleService
from app.services.iqc_rule_service import IQCRuleService
from app.services.device_service import DeviceService

# Helpers
from app.utils.validators import to_float_safe as _to_float, to_bool_safe as _to_bool

# Note: Ensure check_westgard_multilevel is available in westgard module
try:
    from app.utils.westgard import check_westgard_multilevel
except ImportError:
    def check_westgard_multilevel(current, history, rules):
        return {}

# Import CAPA Dialog (Optional)
try:
    from app.ui.dialogs.iqc_capa_dialog import CapaDialog

    HAS_CAPA = True
except ImportError:
    HAS_CAPA = False

# ============================================================================
# FLUENT DESIGN STYLESHEET (WINDOWS 11 STYLE)
# ============================================================================
FLUENT_QSS = """
    QWidget {
        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
        font-size: 14px;
        color: #1A1A1A;
        background-color: #F3F3F3;
    }
    QFrame.Card {
        background-color: #FFFFFF;
        border: 1px solid #E5E5E5;
        border-radius: 8px;
    }
    QGroupBox {
        font-weight: 600;
        border: none;
        margin-top: 10px;
        background-color: transparent;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        color: #0067C0;
    }
    QTabWidget::pane {
        border: 1px solid #E5E5E5;
        border-radius: 8px;
        background: #FFFFFF;
        top: -1px; 
    }
    QTabBar::tab {
        background: transparent;
        border: none;
        padding: 8px 16px;
        margin-right: 4px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 500;
        color: #5C5C5C;
    }
    QTabBar::tab:selected {
        background: #FFFFFF;
        color: #0067C0;
        border-bottom: 2px solid #0067C0;
    }
    QTabBar::tab:hover {
        background: #EAEAEA;
    }
    QLineEdit, QDateEdit, QComboBox {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 24px;
    }
    QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
        border: 2px solid #0067C0;
        border-bottom: 2px solid #0067C0;
    }
    QLineEdit:hover, QDateEdit:hover, QComboBox:hover {
        background-color: #FDFDFD;
        border: 1px solid #888888;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #F6F6F6;
    }
    QPushButton:pressed {
        background-color: #F0F0F0;
        border-color: #B0B0B0;
    }
    QPushButton[class="primary"] {
        background-color: #0067C0;
        color: #FFFFFF;
        border: 1px solid #005FB8;
    }
    QPushButton[class="primary"]:hover {
        background-color: #1874D0;
    }
    QPushButton[class="primary"]:pressed {
        background-color: #005299;
    }
    QTableWidget {
        background-color: #FFFFFF;
        border: 1px solid #E5E5E5;
        border-radius: 6px;
        gridline-color: #F0F0F0;
        selection-background-color: #E3F2FD;
        selection-color: #000000;
        outline: none;
    }
    QHeaderView::section {
        background-color: #FAFAFA;
        border: none;
        border-bottom: 1px solid #E0E0E0;
        padding: 6px;
        font-weight: 600;
        color: #444444;
    }
    QTableWidget QLineEdit {
        background-color: #FEFEFE; 
        border: 1px solid transparent;
    }
    QTableWidget QLineEdit:focus {
        border: 1px solid #0067C0;
        background-color: #FFFFFF;
    }
    QTableWidget::item {
        padding: 2px;
    }
    QScrollBar:vertical {
        background: #F3F3F3;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #CCCCCC;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #999999;
    }
    QLabel {
        color: #333333;
    }
"""

# ============================================================================
# CONSTANTS & RULES MAP
# ============================================================================
STANDARD_ACTIONS = [
    "Đã chạy lại (Rerun) - Kết quả đạt", "Đã chạy lại (Rerun) - Vẫn lỗi",
    "Hiệu chuẩn lại (Recalibration)", "Thay hóa chất mới (New Reagent)",
    "Thay lô QC mới (New Lot QC)", "Bảo trì thiết bị (Maintenance)",
    "Lỗi ngẫu nhiên (Random Error)", "Kiểm tra lại mẫu (Check Sample)"
]

COLOR_PASS_OK_BG = QBrush(QColor("#DFF6DD"))
COLOR_WARN_BG = QBrush(QColor("#FFF4CE"))
COLOR_ERR_RANDOM = QBrush(QColor("#FFE0B2"))
COLOR_ERR_SYSTEM = QBrush(QColor("#FFCDD2"))
COLOR_ERR_GROSS = QBrush(QColor("#E1BEE7"))
COLOR_NA_BG = QBrush(QColor("#F5F5F5"))
COLOR_INPUT_BG = QBrush(QColor("#FFFEF0"))
COLOR_FAIL_BG = QBrush(QColor("#FFCDD2"))

WESTGARD_RULES_MAP = {
    "OK": {"msg": "Đạt", "color": COLOR_PASS_OK_BG, "desc": "Kết quả nằm trong giới hạn kiểm soát.", "action": ""},
    "1_2s": {"msg": "Cảnh báo 1-2s", "color": COLOR_WARN_BG, "desc": "⚠️ Cảnh báo: Vượt quá 2SD.",
             "action": "Theo dõi."},
    "1_3s": {"msg": "Lỗi 1-3s", "color": COLOR_ERR_RANDOM, "desc": "🚫 Lỗi Ngẫu nhiên (3SD).",
             "action": "Rửa kim, Chạy lại."},
    "R_4s": {"msg": "Lỗi R-4s", "color": COLOR_ERR_RANDOM, "desc": "🚫 Lỗi Ngẫu nhiên (>4SD).",
             "action": "Kiểm tra bọt khí, Chạy lại."},
    "2_2s": {"msg": "Lỗi 2-2s", "color": COLOR_ERR_SYSTEM, "desc": "❌ Lỗi Hệ thống (2 điểm > 2SD).",
             "action": "Kiểm tra Calib, Hóa chất."},
    "4_1s": {"msg": "Lỗi 4-1s", "color": COLOR_ERR_SYSTEM, "desc": "❌ Lỗi Hệ thống (4 điểm > 1SD).",
             "action": "Bảo trì/Calib lại."},
    "10_x": {"msg": "Lỗi 10x", "color": COLOR_ERR_SYSTEM, "desc": "❌ Lỗi Hệ thống (Shift trend).",
             "action": "Kiểm tra toàn hệ thống."},
    "ERR_NEG": {"msg": "Lỗi Âm", "color": COLOR_ERR_GROSS, "desc": "⛔ Lỗi Thô: Kết quả âm.",
                "action": "Kiểm tra nhập liệu/Blank."},
    "ERR_EXTREME": {"msg": "Lỗi Cực đại", "color": COLOR_ERR_GROSS, "desc": "⛔ Lỗi Thô: Sai lệch > 4.5 SD.",
                    "action": "Kiểm tra mẫu/thiết bị."},
    "ERR_EXPIRED": {"msg": "Hết hạn", "color": COLOR_ERR_GROSS, "desc": "⛔ Quy chế: LOT QC hết hạn.",
                    "action": "Thay lô QC mới."},
    "ERR_ZERO": {"msg": "Lỗi = 0", "color": COLOR_ERR_GROSS, "desc": "⛔ Lỗi Thô: Kết quả bằng 0.",
                 "action": "Kiểm tra lại mẫu."},
    "Unknown": {"msg": "Lỗi QC", "color": COLOR_ERR_SYSTEM, "desc": "Lỗi không xác định.", "action": ""}
}

SEMI_RANGE_LIST = (
        ['neg', 'negative', 'âm tính', 'âm', '-', 'norm', 'normal', 'bình thường', '0', '0.0']
        + ['+-', 'trace', 'tr', 'vết', '±']
        + ['0.5', '5', '0.15']
        + ['1+', '+1', 'pos', 'positive', 'dương tính', 'dương']
        + ['10', '15', '2.8', '0.3', '8.8', '3.2']
        + ['2+', '+2']
        + ['25', '5.5', '1.0', '1', '17', '1.5', '16', '70']
        + ['3+', '+3']
        + ['80', '14', '3.0', '3', '33', '4.0', '4', '125']
        + ['4+', '+4']
        + ['200', '28', '100', '8.0', '8', '500']
        + ['5+', '+5', '55', '6+', '+6']
        + [f"{x:.1f}" for x in
           [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0]]
        + ['1.000', '1.005', '1.010', '1.015', '1.020', '1.025', '1.030', '1.035']
)
SEMI_CAT_DEFAULT_LIST = list(dict.fromkeys(SEMI_RANGE_LIST))
SEMI_TYPES = {
    "Loại 1 (POS/NEG)": ['NEG', 'POS'],
    "Loại 2 (0+, 1+, trace...)": ['0+', '+-', 'trace', '1+', '2+', '3+', '4+', '5+'],
    "Loại 3 (Số 0-9)": [str(round(i * 0.5, 1)) for i in range(0, 19)],
    "Loại 4 (Tỷ trọng 1.000-1.035)": ['1.000', '1.005', '1.010', '1.015', '1.020', '1.025', '1.030', '1.035']
}


# ============================================================================
# SPARKLINE DELEGATE
# ============================================================================
class SparklineDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        data = index.data(Qt.ItemDataRole.UserRole)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, QColor("#E3F2FD"))
        else:
            painter.fillRect(rect, QColor("#FFFFFF"))

        if not data or not isinstance(data, list) or len(data) == 0:
            painter.restore()
            return

        margin = 6
        w = rect.width() - 2 * margin
        h = rect.height() - 2 * margin
        min_val, max_val = min(data), max(data)
        range_val = max_val - min_val if max_val != min_val else 1.0
        points = []

        if len(data) == 1:
            x = rect.left() + margin + (w / 2)
            y = rect.bottom() - margin - (0.5 * h)
            points.append(QPointF(x, y))
        else:
            step_x = w / (len(data) - 1)
            for i, val in enumerate(data):
                x = rect.left() + margin + i * step_x
                normalized_h = (val - min_val) / range_val
                y = rect.bottom() - margin - (normalized_h * h)
                points.append(QPointF(x, y))

        pen = QPen(QColor("#0067C0"), 1.8)
        painter.setPen(pen)
        if len(points) > 1: painter.drawPolyline(points)

        painter.setBrush(QColor("#D9534F"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(points[-1], 3.5, 3.5)

        if len(points) > 1:
            painter.setBrush(QColor("#9E9E9E"))
            painter.drawEllipse(points[0], 2.5, 2.5)
        painter.restore()


# ============================================================================
# HELPERS
# ============================================================================
def _parse_meta_from_note(note: Optional[str]) -> Dict[str, Any]:
    if not note or not str(note).strip().startswith("{"): return {}
    try:
        return json.loads(note)
    except Exception:
        return {}


def _convert_value(value: float, from_unit: str, to_unit: str, test_code: str) -> float:
    if not from_unit or not to_unit or from_unit.strip().lower() == to_unit.strip().lower():
        return value
    fu, tu, tc = from_unit.strip(), to_unit.strip(), (test_code or "").strip().upper()
    factors = {
        ("mg/dL", "mmol/L", "GLU"): 1 / 18.016, ("mmol/L", "mg/dL", "GLU"): 18.016,
        ("mg/dL", "mmol/L", "CHOL"): 0.02586, ("mmol/L", "mg/dL", "CHOL"): 38.67,
        ("mg/dL", "mmol/L", "TG"): 0.01129, ("mmol/L", "mg/dL", "TG"): 88.57,
        ("mg/dL", "µmol/L", "UA"): 59.48, ("µmol/L", "mg/dL", "UA"): 1 / 59.48,
        ("mg/dL", "µmol/L", "CRE"): 88.4, ("µmol/L", "mg/dL", "CRE"): 1 / 88.4,
    }
    key = (fu, tu, tc)
    return value * factors[key] if key in factors else value


def _make_ro_item(text: str = "") -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    return it


class IQCEditDialog(QDialog):
    def __init__(self, parent=None, *, run_type: str, value: str, unit: str):
        super().__init__(parent)
        self.setWindowTitle("Sửa kết quả")
        self.setStyleSheet(FLUENT_QSS)
        self.run_type = (run_type or "quant").lower()

        self.resize(350, 200)
        lay = QVBoxLayout(self)

        container = QFrame()
        container.setProperty("class", "Card")
        lay_c = QVBoxLayout(container)

        form = QFormLayout()
        form.setSpacing(15)
        self.ed_value = QLineEdit(value or "")
        self.ed_unit = QLineEdit(unit or "")
        if self.run_type == "semi":
            self.ed_value.setPlaceholderText("cat (score)")
        elif self.run_type == "qual":
            self.ed_value.setPlaceholderText("POS/NEG")
        form.addRow("Giá trị:", self.ed_value)
        form.addRow("Đơn vị:", self.ed_unit)
        lay_c.addLayout(form)
        lay.addWidget(container)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setProperty("class", "primary")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_values(self):
        return self.ed_value.text().strip(), self.ed_unit.text().strip()


# ============================================================================
# CLASS CHÍNH: IQCInputPage
# ============================================================================
class IQCInputPage(QWidget):
    INPUT_FONT_SIZE = 13
    INPUT_ROW_HEIGHT = 42

    def __init__(self, parent: Optional[QWidget] = None, username: Optional[str] = None,
                 role: Optional[str] = None, department: Optional[str] = None,
                 fullname: Optional[str] = None, **kwargs):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)

        self.username = username or getpass.getuser()
        self.fullname = fullname or self.username
        self.role = (role or "user").upper()
        self.current_department_name = department or ""
        self.input_font = QFont("Segoe UI", IQCInputPage.INPUT_FONT_SIZE)

        self.iqc_service = IQCService()
        self.catalog_service = CatalogService()
        self.dept_service = DepartmentService()
        # BẠN PHẢI THÊM VÀO ĐÂY:
        self.capa_service = CapaService()
        self.schedule_service = IQCScheduleService()
        self.rule_service = IQCRuleService()
        self.device_service = DeviceService()

        self._lots_cache: Dict[str, List[Dict[str, str]]] = {'L1': [], 'L2': [], 'L3': []}
        self._history_cache: Dict[Tuple[str, str, str], List[Any]] = {}

        self._build_ui()
        self._wire_signals()
        self._load_departments()
        self._apply_type_layout()

        self.timer_validation = QTimer(self)
        self.timer_validation.timeout.connect(self._update_live_validation)
        self.timer_validation.start(1500)
        self._reload_history()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.tab_widget = QTabWidget()
        root.addWidget(self.tab_widget)

        # --- TAB 1: NHẬP LIỆU ---
        input_tab = QWidget()
        input_layout = QVBoxLayout(input_tab)
        input_layout.setContentsMargins(16, 16, 16, 16)

        header_card = QFrame()
        header_card.setProperty("class", "Card")
        header_layout = QVBoxLayout(header_card)

        header_grp = QGroupBox("Thông tin nhập liệu")
        hf = QFormLayout(header_grp)
        hf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        hf.setSpacing(12)

        row1 = QHBoxLayout()
        self.cb_dep = QComboBox()
        self.cb_dep.setMinimumWidth(150)
        self.ed_date = QDateEdit()
        self.ed_date.setCalendarPopup(True)
        self.ed_date.setDate(QDate.currentDate())
        self.ed_date.setDisplayFormat("yyyy-MM-dd")
        self.ed_user = QLineEdit(self.fullname)
        self.ed_user.setReadOnly(True)
        self.ed_user.setStyleSheet("background-color: #F9F9F9; color: #555;")
        row1.addWidget(QLabel("Phòng ban:"))
        row1.addWidget(self.cb_dep, 1)
        row1.addSpacing(12)
        row1.addWidget(QLabel("Ngày:"))
        row1.addWidget(self.ed_date)
        row1.addSpacing(12)
        row1.addWidget(QLabel("Người nhập:"))
        row1.addWidget(self.ed_user, 1)
        hf.addRow(row1)

        row2 = QHBoxLayout()
        self.cb_device = QComboBox()
        self.cb_type = QComboBox()
        self.cb_type.addItems(["Quant", "Semi", "Qual"])
        self.cb_type.setFixedWidth(100)
        self.chk_only_valid = QCheckBox("Chỉ LOT còn hạn")
        self.chk_only_valid.setChecked(True)
        row2.addWidget(QLabel("Thiết bị:"))
        row2.addWidget(self.cb_device, 1)
        row2.addSpacing(12)
        row2.addWidget(QLabel("Loại nội kiểm:"))
        row2.addWidget(self.cb_type)
        row2.addSpacing(12)
        row2.addWidget(self.chk_only_valid)
        hf.addRow(row2)

        row3 = QHBoxLayout()
        self.cb_l1 = QComboBox()
        self.cb_l1.setEditable(True)
        self.lbl_l1_exp = QLabel("HSD: —")
        self.lbl_l1_exp.setStyleSheet("color: #777; font-size: 11px;")
        self.cb_l2 = QComboBox()
        self.cb_l2.setEditable(True)
        self.lbl_l2_exp = QLabel("HSD: —")
        self.lbl_l2_exp.setStyleSheet("color: #777; font-size: 11px;")
        self.cb_l3 = QComboBox()
        self.cb_l3.setEditable(True)
        self.lbl_l3_exp = QLabel("HSD: —")
        self.lbl_l3_exp.setStyleSheet("color: #777; font-size: 11px;")

        row3.addWidget(QLabel("LOT L1:"))
        row3.addWidget(self.cb_l1, 1)
        row3.addWidget(self.lbl_l1_exp)
        row3.addSpacing(15)
        row3.addWidget(QLabel("LOT L2:"))
        row3.addWidget(self.cb_l2, 1)
        row3.addWidget(self.lbl_l2_exp)
        row3.addSpacing(15)
        row3.addWidget(QLabel("LOT L3:"))
        row3.addWidget(self.cb_l3, 1)
        row3.addWidget(self.lbl_l3_exp)
        hf.addRow(row3)

        row4 = QHBoxLayout()
        row4.addStretch(1)

        self.b_get_device = QPushButton("📥 Lấy từ Máy")
        self.b_get_device.setMinimumHeight(32)

        self.b_import_excel = QPushButton("📗 Nhập Excel")
        self.b_import_excel.setMinimumHeight(32)
        self.b_import_excel.setStyleSheet("color: #2E7D32; border: 1px solid #2E7D32;")
        self.b_import_excel.clicked.connect(self._on_import_excel_clicked)

        self.b_load_test = QPushButton("Tải Test theo LOT")
        self.b_load_test.setMinimumHeight(32)

        self.b_save = QPushButton("💾 Lưu (Ctrl+S)")
        self.b_save.setMinimumHeight(32)
        self.b_save.setProperty("class", "primary")

        row4.addWidget(self.b_get_device)
        row4.addWidget(self.b_import_excel)
        row4.addWidget(self.b_load_test)
        row4.addWidget(self.b_save)

        header_layout.addWidget(header_grp)
        header_layout.addLayout(row4)
        input_layout.addWidget(header_card)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setShowGrid(True)
        self.tbl.setAlternatingRowColors(True)
        input_layout.addWidget(self.tbl, 1)

        self.lbl_summary = QLabel("Sẵn sàng")
        self.lbl_summary.setStyleSheet("""
            background-color: #E3F2FD; 
            padding: 8px 12px; font-weight: 600; border-radius: 4px;
            color: #005FB8; border: 1px solid #BBDEFB;
        """)
        input_layout.addWidget(self.lbl_summary)

        self.tab_widget.addTab(input_tab, "Nhập liệu")

        # --- TAB 2: LỊCH SỬ ---
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(16, 16, 16, 16)

        btns_hist = QHBoxLayout()

        filter_card = QFrame()
        filter_card.setProperty("class", "Card")
        filter_layout_box = QVBoxLayout(filter_card)
        filter_layout = QHBoxLayout()

        self.b_export_excel_hist = QPushButton("Xuất Excel")
        self.b_export_excel_hist.setStyleSheet("color: #2E7D32; border: 1px solid #2E7D32;")
        self.b_export_excel_hist.clicked.connect(self._on_export_excel)

        self.ed_filter_date_from = QDateEdit()
        self.ed_filter_date_from.setCalendarPopup(True)
        self.ed_filter_date_from.setDate(QDate.currentDate().addDays(-7))
        self.ed_filter_date_from.setDisplayFormat("yyyy-MM-dd")

        self.ed_filter_date_to = QDateEdit()
        self.ed_filter_date_to.setCalendarPopup(True)
        self.ed_filter_date_to.setDate(QDate.currentDate())
        self.ed_filter_date_to.setDisplayFormat("yyyy-MM-dd")

        self.cb_filter_dep = QComboBox()
        self.cb_filter_dep.addItem("Tất cả", None)
        self.ed_filter_lot = QLineEdit()
        self.ed_filter_lot.setPlaceholderText("Lọc theo LOT...")
        self.ed_search_hist = QLineEdit()
        self.ed_search_hist.setPlaceholderText("Tìm kiếm...")

        # [BỔ SUNG] ComboBox lọc trạng thái (Đạt/Cảnh báo/Lỗi)
        self.cb_filter_status = QComboBox()
        self.cb_filter_status.addItems(["Tất cả", "Đạt (OK)", "Cảnh báo/Lỗi"])
        self.cb_filter_status.setFixedWidth(130)

        self.b_filter_hist = QPushButton("Lọc")
        self.b_filter_hist.setProperty("class", "primary")

        filter_layout.addWidget(QLabel("Từ:"))
        filter_layout.addWidget(self.ed_filter_date_from)
        filter_layout.addWidget(QLabel("Đến:"))
        filter_layout.addWidget(self.ed_filter_date_to)
        filter_layout.addSpacing(12)
        filter_layout.addWidget(QLabel("Phòng ban:"))
        filter_layout.addWidget(self.cb_filter_dep)

        # [BỔ SUNG] Thêm widget lọc trạng thái vào layout
        filter_layout.addSpacing(12)
        filter_layout.addWidget(QLabel("Trạng thái:"))
        filter_layout.addWidget(self.cb_filter_status)

        filter_layout.addSpacing(12)
        filter_layout.addWidget(QLabel("LOT:"))
        filter_layout.addWidget(self.ed_filter_lot)
        filter_layout.addSpacing(12)
        filter_layout.addWidget(QLabel("Tìm kiếm:"))
        filter_layout.addWidget(self.ed_search_hist)
        filter_layout.addWidget(self.b_filter_hist)

        filter_layout_box.addLayout(filter_layout)
        history_layout.addWidget(filter_card)

        # [CẬP NHẬT] Tăng cột lên 14 và thêm header "Cảnh báo"
        self.tbl_hist = QTableWidget(0, 14)
        self.tbl_hist.setHorizontalHeaderLabels(
            ["ID", "Active", "Xu hướng", "Test Code", "Run Time", "User", "Run Type", "Device", "Department", "LOT",
             "Value", "Unit", "Cảnh báo", "Note"])

        self.tbl_hist.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_hist.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_hist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_hist.itemDoubleClicked.connect(self._on_hist_edit_dialog)
        self.tbl_hist.setItemDelegateForColumn(2, SparklineDelegate(self.tbl_hist))
        self.tbl_hist.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl_hist.customContextMenuRequested.connect(self._show_context_menu)
        self.tbl_hist.verticalHeader().setVisible(False)
        self.tbl_hist.setAlternatingRowColors(True)
        history_layout.addWidget(self.tbl_hist, 1)

        btns_hist = QHBoxLayout()
        if self.role in ("SUPERADMIN", "QA"):
            self.b_edit_hist = QPushButton("Chỉnh sửa (Admin)")
            self.b_delete_hist = QPushButton("Xoá (Admin)")
            btns_hist.addWidget(self.b_edit_hist)
            btns_hist.addWidget(self.b_delete_hist)
        else:
            self.b_edit_hist = None
            self.b_delete_hist = None

        self.b_refresh_hist = QPushButton("Tải lại")
        btns_hist.addWidget(self.b_refresh_hist)
        btns_hist.addWidget(self.b_export_excel_hist)
        btns_hist.addStretch(1)

        history_layout.addLayout(btns_hist)
        self.tab_widget.addTab(history_tab, "Lịch sử Nhập")

    # --- [MỚI] LOGIC NHẬP EXCEL ---
    def _on_import_excel_clicked(self):
        """Mở dialog nhập Excel dựa trên Mapping"""
        # 1. Chọn Lot hiện tại
        current_lot = get_combo_id(self.cb_l1) or get_combo_id(self.cb_l2) or get_combo_id(self.cb_l3)
        if not current_lot:
            QMessageBox.warning(self, "Chú ý", "Vui lòng chọn ít nhất một LOT ở phần L1/L2/L3 để nhập liệu vào.")
            return

        # 2. Tìm ID của Lot đó trong DB
        # Logic: lấy ID từ cache _lots_cache hoặc query lại
        lot_id = None
        # ... (Cần logic lấy lot_id chính xác, tạm thời giả sử người dùng chọn L1)
        # Để đơn giản, ta tìm trong cache
        found = False
        for lvl in ['L1', 'L2', 'L3']:
            for l_info in self._lots_cache.get(lvl, []):
                if l_info['lot_no'] == current_lot:
                    lot_id = l_info['id']  # Cache đã có ID
                    found = True
                    break
            if found: break

        if not lot_id:
            # Fallback tìm trong DB
            l_obj = self.catalog_service.search_lots(lot=current_lot)
            if l_obj: lot_id = l_obj[0]['id']

        if not lot_id:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy thông tin LOT trong hệ thống.")
            return

        # 3. Mở File Dialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file QC Excel", "", "Excel Files (*.xlsx *.xls)")
        if not file_path: return

        # 4. Gọi Service nhập
        # Lưu ý: Hàm này cần được thêm vào iqc_service (tôi sẽ gửi ở bước tiếp theo)
        # Tạm thời gọi placeholder hoặc nếu bạn đã thêm thì dùng luôn
        try:
            res = self.iqc_service.import_qc_from_excel(file_path, lot_id)
            if res.get("success"):
                QMessageBox.information(self, "Thành công", res.get("msg"))
                self._reload_history()
            else:
                QMessageBox.warning(self, "Thất bại", res.get("msg"))
        except AttributeError:
            QMessageBox.warning(self, "Chưa cập nhật",
                                "Service chưa có hàm import_qc_from_excel. Hãy cập nhật iqc_service.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))

    def _on_export_excel(self):
        if self.tbl_hist.rowCount() == 0:
            QMessageBox.warning(self, "Trống", "Không có dữ liệu để xuất.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu báo cáo QC",
                                                   f"QC_Report_{QDate.currentDate().toString('yyyyMMdd')}.xlsx",
                                                   "Excel Files (*.xlsx)")
        if not file_path: return

        try:
            workbook = xlsxwriter.Workbook(file_path)
            worksheet = workbook.add_worksheet("QC History")

            fmt_header = workbook.add_format(
                {'bold': True, 'bg_color': '#0067C0', 'font_color': 'white', 'border': 1, 'align': 'center',
                 'valign': 'vcenter'})
            fmt_cell = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
            fmt_fail = workbook.add_format({'bg_color': '#FFCDD2', 'border': 1, 'align': 'center'})
            fmt_warn = workbook.add_format({'bg_color': '#FFF4CE', 'border': 1, 'align': 'center'})

            headers = ["ID", "Test Code", "Run Time", "User", "Run Type", "Device", "Dept", "LOT", "Value", "Unit",
                       "Note", "Status"]
            for col, h in enumerate(headers):
                worksheet.write(0, col, h, fmt_header)
                worksheet.set_column(col, col, 15)

            row_idx = 1
            for r in range(self.tbl_hist.rowCount()):
                item_val = self.tbl_hist.item(r, 10)
                bg_color = item_val.background().color().name().upper() if item_val else "#FFFFFF"

                current_fmt = fmt_cell
                status_text = "OK"
                if bg_color.startswith("#FFC") or bg_color.startswith("#D95"):
                    current_fmt = fmt_fail
                    status_text = "FAIL"
                elif bg_color.startswith("#FFF"):
                    current_fmt = fmt_warn
                    status_text = "WARN"

                worksheet.write(row_idx, 0, self.tbl_hist.item(r, 0).text(), fmt_cell)
                for c_tbl in range(3, 12):
                    val = self.tbl_hist.item(r, c_tbl).text()
                    worksheet.write(row_idx, c_tbl - 2, val, current_fmt)

                note_item = self.tbl_hist.item(r, 12)
                note_text = note_item.text() if note_item else ""
                if note_text.startswith("{"):
                    try:
                        d = json.loads(note_text)
                        if "capa" in d:
                            c = d["capa"]
                            note_text = f"CAPA: {c.get('action')} - {c.get('root_cause')}"
                    except:
                        pass
                worksheet.write(row_idx, 10, note_text, current_fmt)
                worksheet.write(row_idx, 11, status_text, current_fmt)
                row_idx += 1

            workbook.close()
            QMessageBox.information(self, "Thành công", f"Đã xuất file: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Xuất File", str(e))

    def _wire_signals(self):
        self.cb_dep.currentIndexChanged.connect(self._on_dep_changed)
        self.chk_only_valid.stateChanged.connect(self._reload_lot_lists)
        self.cb_type.currentIndexChanged.connect(self._on_run_type_changed)
        self.cb_l1.currentIndexChanged.connect(lambda: self._on_header_lot_changed(1))
        self.cb_l2.currentIndexChanged.connect(lambda: self._on_header_lot_changed(2))
        self.cb_l3.currentIndexChanged.connect(lambda: self._on_header_lot_changed(3))
        self.b_load_test.clicked.connect(self._load_test_data_by_lot)
        self.b_get_device.clicked.connect(self._on_load_from_device)
        self.b_save.clicked.connect(self._on_save)
        self.b_save.setShortcut(QKeySequence("Ctrl+S"))
        self.tbl.itemChanged.connect(self._on_item_changed)
        self.b_filter_hist.clicked.connect(self._reload_history)
        self.b_refresh_hist.clicked.connect(self._reload_history)
        self.ed_search_hist.returnPressed.connect(self._reload_history)
        self.ed_filter_lot.returnPressed.connect(self._reload_history)
        if self.b_edit_hist: self.b_edit_hist.clicked.connect(self._edit_selected_history)
        if self.b_delete_hist: self.b_delete_hist.clicked.connect(self._delete_selected_history)
        self.tbl.installEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.tbl and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                self._move_to_next_editable_cell()
                return True
        return super().eventFilter(source, event)

    def _move_to_next_editable_cell(self):
        r = self.tbl.currentRow()
        c = self.tbl.currentColumn()
        if r < 0 or c < 0: return

        curr_r, curr_c = r, c + 1
        max_r, max_c = self.tbl.rowCount(), self.tbl.columnCount()

        while curr_r < max_r:
            while curr_c < max_c:
                if not self.tbl.isColumnHidden(curr_c):
                    item = self.tbl.item(curr_r, curr_c)
                    widget = self.tbl.cellWidget(curr_r, curr_c)
                    is_editable = False
                    if widget and (isinstance(widget, QComboBox) or isinstance(widget, QLineEdit)):
                        is_editable = True
                    elif item and (item.flags() & Qt.ItemFlag.ItemIsEditable):
                        is_editable = True

                    if is_editable:
                        self.tbl.setCurrentCell(curr_r, curr_c)
                        if widget:
                            widget.setFocus()
                            if isinstance(widget, QComboBox): widget.showPopup()
                        else:
                            self.tbl.editItem(item)
                        return
                curr_c += 1
            curr_c = 0
            curr_r += 1

    def _load_departments(self):
        deps = []
        try:
            deps = self.dept_service.list_departments(active_only=True)
        except Exception:
            pass
        fill_combo_from_list(self.cb_dep, [{"id": d.id, "name": d.name} for d in deps], text_key="name", id_key="id",
                             add_empty=None)
        fill_combo_from_list(self.cb_filter_dep, [{"id": d.id, "name": d.name} for d in deps], text_key="name",
                             id_key="id", add_empty="Tất cả")
        if self.current_department_name:
            idx = combo_find_text_ci(self.cb_dep, self.current_department_name)
            if idx >= 0: self.cb_dep.setCurrentIndex(idx)
        self._on_dep_changed()

    def _on_dep_changed(self):
        dep_name = self.cb_dep.currentText()
        self._clear_table_rows()
        self.cb_device.clear()
        try:
            # [FIX] Hàm service giờ trả về list dict [{'id':..., 'name':...}]
            devs = self.catalog_service.list_devices_by_department(dep_name)

            # Dùng helper fill_combo_from_list để điền đúng ID và Name
            fill_combo_from_list(
                self.cb_device,
                devs,
                text_key="name",
                id_key="id",
                add_empty="— Chọn thiết bị —"
            )
        except Exception as e:
            print(f"Lỗi load thiết bị: {e}")

        self._reload_lot_lists()

    def _reload_lot_lists(self):
        dep_name = self.cb_dep.currentText()
        only_valid = self.chk_only_valid.isChecked()
        try:
            # Sẽ trả về list dict có key: lot_no, expiry_date, và ID (nếu service update)
            self._lots_cache = self.catalog_service.list_active_lots_by_level(dep_name, only_valid_expiry=only_valid)
        except Exception:
            self._lots_cache = {'L1': [], 'L2': [], 'L3': []}

        combos = [self.cb_l1, self.cb_l2, self.cb_l3]
        level_keys = ['L1', 'L2', 'L3']
        old_selections = [get_combo_id(cb) for cb in combos]
        for i, (cb, key) in enumerate(zip(combos, level_keys)):
            cb.blockSignals(True)
            clear_combo(cb)
            lot_list = self._lots_cache.get(key, [])
            add_combo_item(cb, f"— Chọn LOT {key} —", None)
            for lot_info in lot_list:
                # Lưu ý: Nếu lot_info có 'id', nên dùng nó làm userData. Nếu không, dùng lot_no
                val = lot_info.get("lot_no")
                add_combo_item(cb, val, val)
            set_combo_by_id(cb, old_selections[i])
            cb.blockSignals(False)
        for i in range(1, 4): self._on_header_lot_changed(i)

    def _on_header_lot_changed(self, level_index: int):
        combos = [self.cb_l1, self.cb_l2, self.cb_l3]
        labels = [self.lbl_l1_exp, self.lbl_l2_exp, self.lbl_l3_exp]
        key = ['L1', 'L2', 'L3'][level_index - 1]
        cb = combos[level_index - 1]
        lbl = labels[level_index - 1]
        lot_no = get_combo_id(cb)
        exp = ""
        if lot_no:
            found = next((l["expiry_date"] for l in self._lots_cache.get(key, []) if l["lot_no"] == lot_no), "")
            exp = found or ""
        lbl.setText(f"HSD: {exp or '—'}")
        for r in range(self.tbl.rowCount()): self._update_row_lot_display(r)
        self._update_column_visibility()
        self._update_live_validation()

    def _clear_table_rows(self):
        self.tbl.setRowCount(0)
        self._history_cache.clear()
        self.lbl_summary.setText("Sẵn sàng")

    def _on_run_type_changed(self):
        self._apply_type_layout()
        self._clear_table_rows()

    def _apply_type_layout(self):
        run_type = self.cb_type.currentText().strip().lower()
        headers = ["Test code", "Unit", "LOT L1", "LOT L2", "LOT L3"]
        col_count = 5
        for i in range(1, 4):
            if run_type == "quant":
                headers.extend([f"KQ L{i}", f"SDI L{i}", f"Cảnh báo L{i}"])
                col_count += 3
            elif run_type == "semi":
                headers.extend([f"Cat L{i}", f"Score L{i}", f"Cảnh báo L{i}"])
                col_count += 3
            else:
                headers.extend([f"KQ L{i}", f"Pass/Fail L{i}"])
                col_count += 2
        self.tbl.setColumnCount(col_count)
        self.tbl.setHorizontalHeaderLabels(headers)
        self._update_column_visibility()
        for r in range(self.tbl.rowCount()): self._configure_row_widgets(r)

    def _update_column_visibility(self):
        run_type = self.cb_type.currentText().strip().lower()
        active_map = {1: bool(get_combo_id(self.cb_l1)), 2: bool(get_combo_id(self.cb_l2)),
                      3: bool(get_combo_id(self.cb_l3))}
        col_step = 3 if run_type in ("quant", "semi") else 2
        col_base = 5
        for i in range(1, 4):
            self.tbl.setColumnHidden(2 + (i - 1), not active_map[i])
            for j in range(col_step): self.tbl.setColumnHidden(col_base + j, not active_map[i])
            col_base += col_step

    def _add_row(self, test_code: str = "", unit: str = "", level_map: Optional[Dict[str, Any]] = None):
        """
        Thêm một dòng mới vào bảng nhập liệu.
        - test_code: Mã xét nghiệm (VD: GLU)
        - unit: Đơn vị (VD: mmol/L)
        - level_map: Dictionary chứa giá trị các mức (VD: {'L1': 5.5, 'L2': 10.2})
        """
        # Lưu ý: Kiểm tra biến bảng của bạn là self.tbl hay self.table để sửa cho khớp
        # Ở đây tôi dùng self.table theo quy chuẩn chung, nếu code cũ là self.tbl thì bạn sửa lại nhé.
        table_widget = getattr(self, 'tbl', getattr(self, 'table', None))
        if not table_widget:
            print("Lỗi: Không tìm thấy biến bảng (self.tbl hoặc self.table)")
            return

        r = table_widget.rowCount()
        table_widget.insertRow(r)

        # Set chiều cao dòng (nếu class có định nghĩa hằng số)
        if hasattr(IQCInputPage, 'INPUT_ROW_HEIGHT'):
            table_widget.setRowHeight(r, IQCInputPage.INPUT_ROW_HEIGHT)

        # Cột 0: Test Code (Ép kiểu str để tránh lỗi nếu None)
        table_widget.setItem(r, 0, QTableWidgetItem(str(test_code) if test_code else ""))

        # Cột 1: Unit (Hiển thị đơn vị lấy từ máy)
        table_widget.setItem(r, 1, QTableWidgetItem(str(unit) if unit else ""))

        # Cấu hình các ô nhập liệu (L1, L2, L3...)
        self._configure_row_widgets(r, level_map=level_map)

        # Validate lại dòng vừa thêm (sau 50ms để UI kịp render)
        QTimer.singleShot(50, lambda row=r: self._update_live_validation(specific_row=row))

    def _configure_row_widgets(self, r: int, level_map: Optional[Dict[str, Any]] = None):
        run_type = self.cb_type.currentText().strip().lower()
        level_map = level_map or {}
        test_code = self.tbl.item(r, 0).text()
        col_base = 5

        for i in range(1, 4):
            self.tbl.setItem(r, 1 + i, _make_ro_item(""))
            self._update_row_lot_display(r)

        for i in range(1, 4):
            level_str = f"L{i}"
            if run_type == "quant":
                val = level_map.get(level_str, "")
                item = QTableWidgetItem(str(val))
                item.setFont(self.input_font)
                item.setBackground(COLOR_INPUT_BG)
                self.tbl.setItem(r, col_base, item)
                self.tbl.setItem(r, col_base + 1, _make_ro_item(""))
                self.tbl.setItem(r, col_base + 2, _make_ro_item(""))
                col_base += 3
            elif run_type == "semi":
                cat = level_map.get(f"cat_{level_str}", "")
                lot, _ = self._get_selected_header_lot(i)
                target_data = self.catalog_service.get_target_by_lot(test_code, level_str, lot)
                self._ensure_semi_row_widgets(r, i, test_code, cat_value=str(cat), target_data=target_data)
                self.tbl.setItem(r, col_base + 1, _make_ro_item(""))
                self.tbl.setItem(r, col_base + 2, _make_ro_item(""))
                col_base += 3
            else:
                val = level_map.get(f"qual_{level_str}", "")
                self._ensure_qual_row_widgets(r, i, val_data=_to_bool(val))
                self.tbl.setItem(r, col_base + 1, _make_ro_item(""))
                col_base += 2
        for c in [0, 1] + [c for c in range(5, self.tbl.columnCount())]:
            item = self.tbl.item(r, c)
            if item: item.setFont(self.input_font)

    def _update_row_lot_display(self, r: int):
        for i in range(1, 4):
            lot_no, _ = self._get_selected_header_lot(i)
            col_lot = 2 + (i - 1)
            item = self.tbl.item(r, col_lot)
            if not item: item = _make_ro_item(""); self.tbl.setItem(r, col_lot, item)
            item.setText(lot_no or "")

    def _get_test_code_at_row(self, row: int) -> str:
        item = self.tbl.item(row, 0)
        return item.text().strip() if item else ""

    def _get_selected_header_lot(self, level: int) -> tuple[str, str]:
        cb = [self.cb_l1, self.cb_l2, self.cb_l3][level - 1]
        lot_no = get_combo_id(cb)
        if lot_no:
            found = next((l["expiry_date"] for l in self._lots_cache.get(f"L{level}", []) if l["lot_no"] == lot_no), "")
            return lot_no, found or ""
        return "", ""

    def _semi_cat_options_for_test(self, test_code: str, target_data: Optional[Dict[str, Any]] = None):
        meta = _parse_meta_from_note((target_data or {}).get("note"))
        semi_type = meta.get("semi_type", "Loại 2 (0+, 1+, trace...)")
        if semi_type == "Loại 4 (Tỷ trọng 1.000-1.035)": return [""] + SEMI_TYPES[semi_type], True
        options = SEMI_CAT_DEFAULT_LIST[:]
        if semi_type == "Loại 1 (POS/NEG)":
            options = ["", "NEG", "POS"]
        elif semi_type == "Loại 2 (0+, 1+, trace...)":
            options = ["", "neg", "pos", "trace", "+-"] + [f"{i}+" for i in range(0, 6)]
        elif semi_type == "Loại 3 (Số 0-9)":
            options = [""] + [str(round(i * 0.5, 1)) for i in range(0, 19)]
        return options, True

    def _make_semi_cat_widget(self, test_code, target_data):
        options, editable = self._semi_cat_options_for_test(test_code, target_data)
        cb = QComboBox()
        cb.setEditable(editable)
        cb.addItems(options)
        cb.setFont(self.input_font)
        cb.setStyleSheet(f"background-color: {COLOR_INPUT_BG.color().name()}; border: none;")
        return cb

    def _ensure_semi_row_widgets(self, row, level_index, test_code, cat_value="", target_data=None):
        col_base = 5 + (level_index - 1) * 3
        w = self.tbl.cellWidget(row, col_base)
        if not isinstance(w, QComboBox):
            w = self._make_semi_cat_widget(test_code, target_data)
            self.tbl.setCellWidget(row, col_base, w)
        if isinstance(w, QComboBox):
            options, editable = self._semi_cat_options_for_test(test_code, target_data)
            w.blockSignals(True)
            w.clear()
            w.addItems(options)
            w.setEditable(editable)
            if cat_value: w.setCurrentText(cat_value)
            w.blockSignals(False)
            try:
                w.currentTextChanged.disconnect()
            except:
                pass
            w.currentTextChanged.connect(lambda txt, cb=w: self._on_semi_cat_changed(cb, txt))

    def _on_semi_cat_changed(self, cat_widget, cat_txt):
        try:
            for r in range(self.tbl.rowCount()):
                for c in range(self.tbl.columnCount()):
                    if self.tbl.cellWidget(r, c) == cat_widget:
                        self._update_live_validation(specific_row=r)
                        return
        except Exception:
            pass

    def _make_qual_combo(self, data_val: Optional[int] = None) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(False)
        add_combo_item(cb, "", None)
        add_combo_item(cb, "POS", 1)
        add_combo_item(cb, "NEG", 0)
        if data_val is not None: set_combo_by_id(cb, data_val)
        cb.setFont(self.input_font)
        cb.setStyleSheet(f"background-color: {COLOR_INPUT_BG.color().name()}; border: none;")
        return cb

    def _ensure_qual_row_widgets(self, row: int, level_index: int, val_data: Optional[int] = None):
        col_base = 5 + (level_index - 1) * 2
        w = self.tbl.cellWidget(row, col_base)
        cb = None
        if not isinstance(w, QComboBox):
            cb = self._make_qual_combo(val_data)
            self.tbl.setCellWidget(row, col_base, cb)
        else:
            cb = w
            if val_data is not None: set_combo_by_id(w, val_data)
        try:
            cb.currentIndexChanged.disconnect()
        except:
            pass
        cb.currentIndexChanged.connect(lambda idx, r=row: self._update_live_validation(specific_row=r))

    def _update_live_validation(self, specific_row: Optional[int] = None):
        run_type = (self.cb_type.currentText() or "").strip().lower()
        rows = [specific_row] if specific_row is not None else range(self.tbl.rowCount())
        dep_name = self.cb_dep.currentText()
        current_run_date = self.ed_date.date()

        total_checks = 0
        count_pass = 0
        count_warn = 0
        count_fail = 0

        for r in rows:
            test_code = self._get_test_code_at_row(r)
            if not test_code: continue

            row_unit = self.tbl.item(r, 1).text().strip() if self.tbl.item(r, 1) else ""
            current_z_scores = {}
            targets_map = {}
            col_indices_map = {}
            violations_map = {}

            col_step = 3 if run_type in ("quant", "semi") else 2
            col_base = 5

            # 1. Thu thập dữ liệu và tính toán sơ bộ
            for i in range(1, 4):
                level_str = f"L{i}"
                if self.tbl.isColumnHidden(col_base):
                    col_base += col_step
                    continue

                col_indices_map[level_str] = col_base
                col_result = col_base
                result_item = self.tbl.item(r, col_result)
                val_text = result_item.text().strip() if result_item else ""
                if val_text: total_checks += 1

                lot_no, lot_exp_str = self._get_selected_header_lot(i)
                target_data = self.catalog_service.get_target_by_lot(test_code, level_str, lot_no)
                targets_map[level_str] = target_data

                pre_error_code = None
                if self.chk_only_valid.isChecked() and lot_exp_str:
                    exp_date = QDate.fromString(lot_exp_str, "yyyy-MM-dd")
                    if exp_date.isValid() and exp_date < current_run_date: pre_error_code = "ERR_EXPIRED"

                if run_type == "quant" and val_text and lot_no and target_data and not pre_error_code:
                    try:
                        val = _to_float(val_text)
                        if val is not None:
                            if val < 0:
                                pre_error_code = "ERR_NEG"
                            elif val == 0:
                                pre_error_code = "ERR_ZERO"
                            else:
                                t_mean = _to_float(target_data.get("mean")) or _to_float(target_data.get("target_mean"))
                                t_sd = _to_float(target_data.get("sd")) or _to_float(target_data.get("target_sd"))
                                t_unit = target_data.get("unit")

                                if t_mean is not None and t_sd and t_sd > 0:
                                    if row_unit and t_unit and row_unit.lower() != t_unit.lower():
                                        val = _convert_value(val, row_unit, t_unit, test_code)
                                    z = (val - t_mean) / t_sd
                                    if abs(z) > 4.5:
                                        pre_error_code = "ERR_EXTREME"
                                    else:
                                        current_z_scores[level_str] = z
                    except Exception:
                        pass

                if pre_error_code: violations_map[level_str] = pre_error_code
                col_base += col_step

            # 2. Kiểm tra Westgard đa mức (cho Quant)
            if run_type == "quant" and current_z_scores:
                history_z_map = {}
                valid_levels = list(current_z_scores.keys())
                for lvl in valid_levels:
                    lot = self._get_selected_header_lot(int(lvl[1]))[0]
                    cache_key = (test_code, lvl, lot)
                    hist_rows = self._history_cache.get(cache_key, [])
                    if not hist_rows:
                        try:
                            hist_rows = self.iqc_service.get_history(department=dep_name, test_code=test_code,
                                                                     level=lvl, lot_no=lot, limit=15, sort_order="DESC",
                                                                     active_only=True)
                            self._history_cache[cache_key] = hist_rows
                        except:
                            pass

                    if hist_rows:
                        last_rec = hist_rows[0]
                        h_val = _to_float(last_rec.get('value_num'))
                        t_data = targets_map[lvl]
                        if h_val is not None and t_data:
                            tm = _to_float(t_data.get("mean"))
                            tsd = _to_float(t_data.get("sd"))
                            if tm and tsd: history_z_map[lvl] = [(h_val - tm) / tsd]

                rule_cfg = self.rule_service.get_rule(dep_name, test_code, "L1")
                rules_list = rule_cfg['rules'].split(',') if rule_cfg else None
                wg_results = check_westgard_multilevel(current_z_scores, history_z_map, rules_list)
                for lvl, code in wg_results.items():
                    if lvl not in violations_map: violations_map[lvl] = code

            # 3. Cập nhật giao diện từng ô
            for i in range(1, 4):
                level_str = f"L{i}"
                if level_str not in col_indices_map: continue

                col_base = col_indices_map[level_str]
                col_result = col_base
                col_sdi = col_base + 1
                col_warn = col_base + (col_step - 1)

                target_data = targets_map.get(level_str)
                result_widget = self.tbl.cellWidget(r, col_result)
                val_text = ""
                if isinstance(result_widget, QComboBox):
                    val_text = result_widget.currentText()
                elif self.tbl.item(r, col_result):
                    val_text = self.tbl.item(r, col_result).text()

                status_msg = ""
                bg_color = COLOR_INPUT_BG
                pass_fail_code = None
                sdi_text = ""
                tooltip_text = ""
                action_text = ""

                # Biến lưu mã lỗi để gửi xuống DB (Quan trọng)
                final_violation_code = "OK"

                if not target_data:
                    status_msg = "Thiếu Target"
                    bg_color = COLOR_NA_BG
                elif run_type == "quant":
                    vio_code = violations_map.get(level_str, "OK")
                    final_violation_code = vio_code  # Lưu mã lỗi (VD: "1_3s")

                    is_delta_warning = False
                    if vio_code == "OK" and level_str in current_z_scores and val_text:
                        lot = self._get_selected_header_lot(i)[0]
                        cache_key = (test_code, level_str, lot)
                        hist = self._history_cache.get(cache_key, [])
                        if hist:
                            last_val = _to_float(hist[0].get('value_num'))
                            curr_val = _to_float(val_text)
                            t_sd = _to_float(target_data.get("sd"))
                            if last_val is not None and t_sd and abs(curr_val - last_val) > (3 * t_sd):
                                is_delta_warning = True

                    rule_info = WESTGARD_RULES_MAP.get(vio_code, WESTGARD_RULES_MAP["Unknown"])
                    if vio_code not in WESTGARD_RULES_MAP and vio_code != "OK":
                        status_msg = f"Lỗi {vio_code.replace('_', '-')}"
                    else:
                        status_msg = rule_info["msg"]
                    bg_color = rule_info["color"]
                    tooltip_text = rule_info["desc"]
                    action_text = rule_info.get("action", "")

                    if vio_code == "OK":
                        pass_fail_code = 1
                        if is_delta_warning:
                            tooltip_text += "\n⚠️ Delta Check: Thay đổi đột ngột (>3SD)."
                            count_warn += 1
                        else:
                            count_pass += 1
                    elif vio_code == "1_2s":
                        pass_fail_code = 2
                        count_warn += 1
                    else:
                        pass_fail_code = 0
                        count_fail += 1

                    if level_str in current_z_scores:
                        sdi_text = f"{current_z_scores[level_str]:.2f}"
                    elif vio_code in ("ERR_NEG", "ERR_ZERO", "ERR_EXTREME"):
                        sdi_text = "---"

                    if not val_text:
                        status_msg, bg_color, sdi_text, pass_fail_code = "", COLOR_INPUT_BG, "", None
                        final_violation_code = ""  # Không có dữ liệu thì không có lỗi

                elif run_type == "semi":
                    status_msg, bg_color = self._get_semi_validation(val_text, target_data)
                    pass_fail_code = 0 if bg_color == COLOR_FAIL_BG else 1
                    final_violation_code = "FAIL" if pass_fail_code == 0 else "OK"

                    if val_text:
                        if pass_fail_code == 0:
                            tooltip_text = "Kết quả không khớp Target."
                            count_fail += 1
                        else:
                            count_pass += 1
                elif run_type == "qual":
                    val = get_combo_id(result_widget) if isinstance(result_widget, QComboBox) else None
                    if val is not None:
                        status_msg, bg_color = self._get_qual_validation(val, target_data)
                        pass_fail_code = 0 if bg_color == COLOR_FAIL_BG else 1
                        final_violation_code = "FAIL" if pass_fail_code == 0 else "OK"

                        if pass_fail_code == 0:
                            tooltip_text = "Kết quả định tính sai."
                            count_fail += 1
                        else:
                            count_pass += 1
                    else:
                        bg_color = COLOR_INPUT_BG

                # --- CẬP NHẬT UI ITEM ---
                item_warn = self.tbl.item(r, col_warn)
                if item_warn:
                    item_warn.setText(status_msg)
                    if pass_fail_code is not None:
                        # Lưu Pass/Fail (0, 1, 2)
                        item_warn.setData(Qt.ItemDataRole.UserRole, pass_fail_code)
                        # [QUAN TRỌNG] Lưu mã lỗi Westgard (VD: "1_3s") vào UserRole + 1
                        item_warn.setData(Qt.ItemDataRole.UserRole + 1, final_violation_code)

                    item_warn.setBackground(bg_color)
                    full_tt = tooltip_text
                    if action_text: full_tt += f"\n💡 {action_text}"
                    item_warn.setToolTip(full_tt)

                if run_type == "quant":
                    item_sdi = self.tbl.item(r, col_sdi)
                    if item_sdi: item_sdi.setText(sdi_text); item_sdi.setBackground(bg_color)

                item_res = self.tbl.item(r, col_result)
                if item_res: item_res.setBackground(bg_color)
                if result_widget:
                    css = f"background-color: {bg_color.color().name()}; border: none;"
                    if isinstance(result_widget, QComboBox): css += " QAbstractItemView { background-color: white; }"
                    result_widget.setStyleSheet(css)

        if total_checks > 0:
            self.lbl_summary.setText(
                f"Tổng: {total_checks} | ✅ Đạt: {count_pass} | ⚠️ Cảnh báo: {count_warn} | ❌ Lỗi: {count_fail}")
            if count_fail > 0:
                self.lbl_summary.setText(self.lbl_summary.text() + " - Click để lập phiếu CAPA!")
                self.lbl_summary.setStyleSheet(
                    "background-color: #FFEBEE; padding: 8px 12px; font-weight: 600; border-radius: 4px; color: #D32F2F; border: 1px solid #FFCDD2;")
            elif count_warn > 0:
                self.lbl_summary.setStyleSheet(
                    "background-color: #FFF8E1; padding: 8px 12px; font-weight: 600; border-radius: 4px; color: #F57C00; border: 1px solid #FFE0B2;")
            else:
                self.lbl_summary.setStyleSheet(
                    "background-color: #E8F5E9; padding: 8px 12px; font-weight: 600; border-radius: 4px; color: #2E7D32; border: 1px solid #C8E6C9;")
        else:
            self.lbl_summary.setText("Sẵn sàng")
            self.lbl_summary.setStyleSheet(
                "background-color: #F5F5F5; padding: 8px 12px; font-weight: 600; border-radius: 4px; color: #616161; border: 1px solid #E0E0E0;")

    def _get_semi_validation(self, result_val: str, target_data: Dict[str, Any]) -> Tuple[str, QBrush]:
        res_str = str(result_val or "").strip().lower()
        if not res_str: return "", COLOR_INPUT_BG
        meta = _parse_meta_from_note(target_data.get("note"))
        target_str = (target_data.get("reference_range") or meta.get("target") or "").lower().strip()
        if not target_str: return "Thiếu Target", COLOR_NA_BG

        try:
            v_num = float(res_str)
            clean_target = target_str.replace(" to ", "-")
            if "-" in clean_target:
                parts = clean_target.split("-")
                if len(parts) == 2:
                    min_v, max_v = float(parts[0]), float(parts[1])
                    if min_v > max_v: min_v, max_v = max_v, min_v
                    if min_v <= v_num <= max_v: return "Đạt", COLOR_PASS_OK_BG
            else:
                if abs(v_num - float(target_str)) < 0.000001: return "Đạt", COLOR_PASS_OK_BG
            return f"K.Đạt (Chờ {target_str})", COLOR_FAIL_BG
        except ValueError:
            pass

        if res_str == target_str: return "Đạt", COLOR_PASS_OK_BG
        if "to" in target_str or "-" in target_str:
            try:
                valid_list = self._expand_semi_range(target_str)
                if res_str in [x.lower() for x in valid_list]: return "Đạt", COLOR_PASS_OK_BG
            except:
                pass
        return f"K.Đạt (Chờ {target_str})", COLOR_FAIL_BG

    def _expand_semi_range(self, range_str: str) -> List[str]:
        s = range_str.lower().replace(" to ", "-")
        parts = s.split("-")
        if len(parts) != 2: return [s]
        start, end = parts[0].strip(), parts[1].strip()
        try:
            s_idx = SEMI_RANGE_LIST.index(start)
            e_idx = SEMI_RANGE_LIST.index(end)
            if s_idx > e_idx: s_idx, e_idx = e_idx, s_idx
            return SEMI_RANGE_LIST[s_idx: e_idx + 1]
        except:
            return [start, end]

    def _get_qual_validation(self, result_val: int, target_data: Dict[str, Any]) -> Tuple[str, QBrush]:
        ref = target_data.get("reference_range", "") or "NEG"
        expected = 1 if ref.upper() == "POS" else 0
        return ("Đạt", COLOR_PASS_OK_BG) if result_val == expected else (f"K.Đạt (Chờ {ref})", COLOR_FAIL_BG)

    def _on_load_from_device(self):
        """
        Logic lấy kết quả (Hỗ trợ FILE, TCP/IP và RS232) - Đã sửa lỗi Unit và Mapping.
        """
        # 1. LẤY THÔNG TIN THIẾT BỊ
        device_id = get_combo_id(self.cb_device)
        if not device_id:
            QMessageBox.warning(self, "Chưa chọn thiết bị", "Vui lòng chọn Thiết bị trước.")
            return

        device_info = self.device_service.get_device(device_id)
        if not device_info: return

        # Lấy kiểu kết nối
        conn_type = getattr(device_info, 'connection_type', 'file').lower()

        # 2. CHUẨN BỊ MAPPING (SMART MAPPING)
        target_date = self.ed_date.date().toPython()
        selected_lots = {}
        if get_combo_id(self.cb_l1): selected_lots[1] = get_combo_id(self.cb_l1)
        if get_combo_id(self.cb_l2): selected_lots[2] = get_combo_id(self.cb_l2)
        if get_combo_id(self.cb_l3): selected_lots[3] = get_combo_id(self.cb_l3)

        if not selected_lots:
            QMessageBox.warning(self, "Chú ý", "Hãy chọn ít nhất 1 Lot.")
            return

        # Tạo map chuẩn (Test chuẩn trong DB)
        standard_tests_map = {}
        try:
            # Quét tất cả các Lot đang chọn để lấy danh sách Test đầy đủ nhất
            active_lot_ids = []
            for lot_code in selected_lots.values():
                found = self.catalog_service.search_lots(lot=lot_code)
                if found:
                    active_lot_ids.append(found[0]['id'])

            # Lấy chi tiết từng Lot để xây dựng từ điển Mapping
            seen_ids = set()
            for l_id in active_lot_ids:
                if l_id in seen_ids: continue
                seen_ids.add(l_id)

                details = self.catalog_service.get_details_by_lot(l_id)
                for d in details:
                    std_name = d.get("test_name", "").strip()
                    if not std_name: continue

                    # 1. Map chính tên: "AST (GOT)" -> "AST (GOT)"
                    standard_tests_map[std_name.upper()] = std_name

                    # 2. Map từ khóa: "GOT" -> "AST (GOT)"
                    parts = std_name.replace("(", " ").replace(")", " ").split()
                    for p in parts:
                        if len(p) >= 2: standard_tests_map[p.upper()] = std_name

                    # 3. Map mã Code (nếu có): "GOT" -> "AST (GOT)"
                    if d.get('test_code'):
                        standard_tests_map[d.get('test_code').upper()] = std_name
        except Exception as e:
            print(f"Lỗi Mapping: {e}")

        self._clear_table_rows()
        total_found = 0
        merged_data = {}

        # --- Hàm nội bộ để xử lý và gộp dữ liệu ---
        def process_and_merge(res_item, level_index):
            raw_code = res_item['test_code'].strip().upper()
            val = res_item['value']
            unit = res_item.get('unit', '')  # Lấy đơn vị

            # Mapping: Tìm tên chuẩn trong từ điển
            final_name = standard_tests_map.get(raw_code, res_item['test_code'])

            if final_name not in merged_data:
                merged_data[final_name] = {
                    "test_code": final_name,
                    "unit": unit
                }
            # Cập nhật Unit nếu chưa có (ưu tiên lấy unit từ lần đọc đầu tiên có unit)
            if unit and not merged_data[final_name].get("unit"):
                merged_data[final_name]["unit"] = unit

            # Gán giá trị vào Level tương ứng (L1, L2, L3)
            merged_data[final_name][f"L{level_index}"] = val

        # =========================================================
        # TRƯỜNG HỢP 1: KẾT NỐI FILE
        # =========================================================
        if conn_type == 'file':
            folder_path = getattr(device_info, 'file_path', '')
            if not folder_path or not os.path.exists(folder_path):
                QMessageBox.warning(self, "Lỗi đường dẫn", f"Thư mục không tồn tại: {folder_path}")
                return

            for level_idx, lot_code in selected_lots.items():
                results = self.iqc_service.read_machine_file_by_lot(folder_path, lot_code, target_date)
                for res in results:
                    process_and_merge(res, level_idx)
                    total_found += 1

        # =========================================================
        # TRƯỜNG HỢP 2: KẾT NỐI TCP/IP (LAN)
        # =========================================================
        elif conn_type == 'tcp':
            ip = getattr(device_info, 'ip_address', '')
            port = getattr(device_info, 'ip_port', '')

            if not ip or not port:
                QMessageBox.warning(self, "Thiếu cấu hình mạng", "Vui lòng nhập IP và Port trong Cấu hình thiết bị.")
                return

            QMessageBox.information(self, "Đang kết nối", f"Đang kết nối tới {ip}:{port}...\nVui lòng đợi giây lát.")

            # Gọi service TCP
            results = self.iqc_service.receive_data_via_tcp(ip, int(port))

            if not results:
                QMessageBox.warning(self, "Không có dữ liệu",
                                    f"Kết nối thành công tới {ip}:{port} nhưng không nhận được dữ liệu nào.\n(Có thể máy chưa gửi kết quả)")
                return

            # Map dữ liệu TCP vào TẤT CẢ các Lot đang chọn
            for res in results:
                for level_idx in selected_lots.keys():
                    process_and_merge(res, level_idx)
                    total_found += 1

        # =========================================================
        # TRƯỜNG HỢP 3: KẾT NỐI SERIAL (RS232) [MỚI THÊM]
        # =========================================================
        elif conn_type in ['serial', 'rs232']:
            # Lấy tham số cấu hình từ DB
            port = getattr(device_info, 'com_port', '')
            baud = getattr(device_info, 'baudrate', 9600)
            parity = getattr(device_info, 'parity', 'N')
            stopbits = getattr(device_info, 'stop_bits', 1)
            databits = getattr(device_info, 'data_bits', 8)

            if not port:
                QMessageBox.warning(self, "Thiếu cấu hình", "Vui lòng nhập Cổng COM (VD: COM1) trong Cài đặt thiết bị.")
                return

            QMessageBox.information(self, "Đang đọc", f"Đang lắng nghe cổng {port} (Baud {baud})...\nVui lòng đợi 5 giây.")

            # Gọi Service RS232
            results = self.iqc_service.receive_data_via_serial(
                port=port,
                baudrate=baud,
                parity=parity,
                stopbits=stopbits,
                bytesize=databits
            )

            if not results:
                QMessageBox.warning(self, "Không có dữ liệu",
                                    f"Đã mở cổng {port} nhưng không nhận được tín hiệu.\n"
                                    "(Kiểm tra cáp kết nối hoặc bấm gửi lại từ máy)")
                return

            # Xử lý kết quả (Mapping & Merge)
            for res in results:
                for level_idx in selected_lots.keys():
                    process_and_merge(res, level_idx)
                    total_found += 1

        else:
            QMessageBox.warning(self, "Chưa hỗ trợ", f"Kiểu kết nối '{conn_type}' chưa được hỗ trợ lấy dữ liệu.")
            return

        # 4. HIỂN THỊ LÊN BẢNG
        if total_found == 0:
            QMessageBox.warning(self, "Không có dữ liệu", "Không tìm thấy kết quả phù hợp.")
            return

        for t_code, val_map in merged_data.items():
            # [QUAN TRỌNG] Lấy Unit từ val_map để hiển thị đúng
            row_unit = val_map.get("unit", "")
            self._add_row(t_code, row_unit, level_map=val_map)

        QMessageBox.information(self, "Thành công", f"Đã tải dữ liệu thành công ({total_found} điểm).")

    def _process_result_item(self, res_item, mapping_map, merged_data, level_idx):
        """Helper để gom logic mapping và merge data"""
        raw_code = res_item['test_code'].strip()
        val = res_item['value']

        # Smart Mapping
        final_code = mapping_map.get(raw_code.upper(), raw_code)

        if final_code not in merged_data:
            merged_data[final_code] = {"test_code": final_code}

        # Ghi đè giá trị nếu chưa có (hoặc ghi đè luôn)
        merged_data[final_code][f"L{level_idx}"] = val

    def _load_test_data_by_lot(self):
        dep_name = self.cb_dep.currentText()
        selected_lots = [get_combo_id(cb) for cb in [self.cb_l1, self.cb_l2, self.cb_l3] if get_combo_id(cb)]
        if not selected_lots:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn ít nhất 1 LOT ở header trước.")
            return

        self._clear_table_rows()
        existing = set()
        new_rows = 0
        quant_count = 0
        non_quant_count = 0
        tests_to_fetch_history = []

        try:
            for lot_no in selected_lots:
                lot_id = None

                def find_lot(lst, lot_no):
                    for l in lst:
                        if l.get('lot_no') == lot_no or l.get('lot') == lot_no: return l
                    return None

                lots_list = self.catalog_service.search_lots(department=dep_name, lot=lot_no, status=None)
                found_lot = find_lot(lots_list, lot_no)
                if not found_lot:
                    lots_list = self.catalog_service.search_lots(department=None, lot=lot_no, status=None)
                    found_lot = find_lot(lots_list, lot_no)
                if found_lot: lot_id = found_lot.get('id')
                if not lot_id: continue

                details = self.catalog_service.get_details_by_lot(lot_id)
                if not details: continue

                for d in details:
                    test_name = (d.get("test_name") or "").strip()
                    if not test_name or test_name.lower() in existing: continue
                    meta = _parse_meta_from_note(d.get("note"))
                    unit = d.get("unit") or meta.get("unit", "")
                    data_type = (d.get("data_type") or meta.get("data_type") or "Quant").lower()
                    level_str = (d.get("level") or "L1").upper()
                    level_map = {}

                    if data_type == "quant":
                        level_map[level_str] = ""
                        quant_count += 1
                        tests_to_fetch_history.append(test_name)
                    elif data_type == "semi":
                        level_map[f"cat_{level_str}"] = meta.get("target", "")
                        non_quant_count += 1
                    elif data_type == "qual":
                        level_map[f"qual_{level_str}"] = meta.get("target", "")
                        non_quant_count += 1

                    current_type = self.cb_type.currentText().strip().lower()
                    if data_type != current_type:
                        idx_type = combo_find_text_ci(self.cb_type, data_type.capitalize())
                        if idx_type >= 0:
                            self.cb_type.setCurrentIndex(idx_type)
                            self._apply_type_layout()

                    self._add_row(test_name, unit, level_map=level_map)
                    new_rows += 1
                    existing.add(test_name.lower())

            self._update_column_visibility()

            if tests_to_fetch_history and self.cb_type.currentText() == "Quant":
                active_lots = []
                for i in range(1, 4):
                    l_lot, _ = self._get_selected_header_lot(i)
                    if l_lot: active_lots.append((f"L{i}", l_lot))
                for t_name in tests_to_fetch_history:
                    for lvl, lot in active_lots:
                        try:
                            hist = self.iqc_service.get_history(department=dep_name, test_code=t_name, level=lvl,
                                                                lot_no=lot, limit=15, sort_order="DESC",
                                                                active_only=True)
                            self._history_cache[(t_name, lvl, lot)] = hist
                        except:
                            pass

            if self.tbl.rowCount() > 0:
                self.tbl.setCurrentCell(0, 0)
                self._move_to_next_editable_cell()

            msg = f"Đã nạp {new_rows} xét nghiệm."
            if quant_count and non_quant_count: msg += f"\n({quant_count} Quant, {non_quant_count} Qual/Semi)"
            QMessageBox.information(self, "Thành công", msg)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải test: {e}")

    def _on_item_changed(self, item: QTableWidgetItem):
        if item is None: return
        if item.column() >= 5: self._update_live_validation(specific_row=item.row())

    def _collect_rows_for_save(self) -> List[Dict[str, Any]]:
        run_type = self.cb_type.currentText().strip().lower()
        out = []
        for r in range(self.tbl.rowCount()):
            test_code = self.tbl.item(r, 0).text()
            if not test_code: continue
            unit = self.tbl.item(r, 1).text()
            row_payload = {"test_code": test_code, "unit": unit}
            has_data = False
            col_base = 5
            for i in range(1, 4):
                level_str = f"L{i}"
                if self.tbl.isColumnHidden(col_base):
                    col_base += 3 if run_type != "qual" else 2
                    continue
                lot, exp = self._get_selected_header_lot(i)
                row_payload[f"lot_{level_str}"] = lot
                row_payload[f"lot_expiry_{level_str}"] = exp

                warn_item = None  # Biến tạm để lấy item cảnh báo

                if run_type == "quant":
                    val_item, sdi_item, warn_item = self.tbl.item(r, col_base), self.tbl.item(r,
                                                                                              col_base + 1), self.tbl.item(
                        r, col_base + 2)
                    if val_item and val_item.text().strip():
                        row_payload[level_str] = val_item.text().strip()
                        row_payload[f"sdi_{level_str}"] = sdi_item.text() if sdi_item else None
                        has_data = True
                    col_base += 3
                elif run_type == "semi":
                    cat_widget = self.tbl.cellWidget(r, col_base)
                    warn_item = self.tbl.item(r, col_base + 2)
                    cat = ""
                    if isinstance(cat_widget, QComboBox):
                        cat = cat_widget.currentText().strip()
                    elif isinstance(cat_widget, QLineEdit):
                        cat = cat_widget.text().strip()
                    if cat:
                        row_payload[f"cat_{level_str}"] = cat
                        has_data = True
                    col_base += 3
                else:
                    qual_widget = self.tbl.cellWidget(r, col_base)
                    warn_item = self.tbl.item(r, col_base + 1)
                    qual_data = get_combo_id(qual_widget) if isinstance(qual_widget, QComboBox) else None
                    if qual_data is not None:
                        row_payload[f"qual_{level_str}"] = "POS" if qual_data == 1 else "NEG"
                        has_data = True
                    col_base += 2

                # [QUAN TRỌNG] Lấy mã lỗi từ UserRole + 1 để gửi đi
                if warn_item:
                    row_payload[f"pass_fail_{level_str}"] = warn_item.data(Qt.ItemDataRole.UserRole)
                    row_payload[f"violation_{level_str}"] = warn_item.data(Qt.ItemDataRole.UserRole + 1)

            if has_data: out.append(row_payload)
        return out

    def _on_save(self):
        dep = self.cb_dep.currentText()

        # [FIX] Lấy Tên thiết bị để lưu vào lịch sử (cho dễ đọc)
        # ID thiết bị vẫn được dùng ngầm ở nút "Lấy từ máy"
        device = self.cb_device.currentText()
        if not device or device == "— Chọn thiết bị —":
            device = ""

        run_date = self.ed_date.date().toString("yyyy-MM-dd")
        run_type = self.cb_type.currentText().strip().lower()

        rows_to_save = self._collect_rows_for_save()
        if not rows_to_save:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa có kết quả.")
            return

        if QMessageBox.question(self, "Lưu", f"Lưu {len(rows_to_save)} kết quả?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return

        try:
            run_id = self.iqc_service.create_run(run_date, self.username, device, dep, levels_count=3,
                                                 run_type=run_type)
            count = self.iqc_service.upsert_results(run_id, rows_to_save, department=dep)

            # ... (Phần logic đánh dấu lịch còn lại giữ nguyên) ...
            dep_id = get_combo_id(self.cb_dep)
            if dep_id:
                for r in rows_to_save:
                    for i in range(1, 4):
                        self.schedule_service.mark_run_today(department_id=dep_id, device_id=None,
                                                             test_code=r["test_code"], level=i, date=run_date)

            QMessageBox.information(self, "OK", f"Đã lưu {count} kết quả.")
            self._reload_history()
            self._clear_table_rows()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))

    def _reload_history(self):
        dep = self.cb_filter_dep.currentText() if self.cb_filter_dep.currentData() else None
        f_d = self.ed_filter_date_from.date().toString("yyyy-MM-dd")
        t_d = self.ed_filter_date_to.date().toString("yyyy-MM-dd")

        # 1. Lấy dữ liệu thô
        rows = self.iqc_service.get_history(department=dep, run_date_from=f_d, run_date_to=t_d,
                                            lot_no=self.ed_filter_lot.text().strip(), limit=500, sort_order="DESC")

        # 2. Lọc theo từ khóa tìm kiếm
        st = self.ed_search_hist.text().strip().lower()
        if st:
            rows = [r for r in rows if
                    any(st in str(r.get(k, "")).lower() for k in ("test_code", "user", "device", "value"))]

        # 3. [CẬP NHẬT] Lọc theo Trạng thái (Logic khớp hoàn toàn với cột Cảnh báo)
        status_mode = self.cb_filter_status.currentIndex()  # 0: Tất cả, 1: Đạt, 2: Cảnh báo/Lỗi

        if status_mode != 0:
            filtered_rows = []
            for r in rows:
                # Phân tích Note để lấy violation
                note_raw = r.get("note", "")
                violation = ""
                if note_raw and str(note_raw).strip().startswith("{"):
                    try:
                        extra = json.loads(note_raw)
                        violation = extra.get("violation", "")
                    except:
                        pass

                pass_fail = r.get("pass_fail")

                # Logic xác định Đạt hay Lỗi (Giống hệt logic hiển thị cột 12)
                is_ok = (pass_fail == 1) or (violation == "OK")

                if status_mode == 1:  # Muốn lấy Đạt
                    if is_ok: filtered_rows.append(r)
                elif status_mode == 2:  # Muốn lấy Lỗi/Cảnh báo
                    if not is_ok: filtered_rows.append(r)

            rows = filtered_rows

        # 4. Hiển thị lên bảng
        self.tbl_hist.setRowCount(len(rows))
        for i, r in enumerate(rows):
            # ID & Checkbox
            self.tbl_hist.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            chk = QCheckBox()
            chk.setChecked(r.get("is_active", 1) == 1)
            chk.setProperty("result_id", r.get("id"))
            chk.stateChanged.connect(self._on_history_active_changed)
            w = QWidget()
            l = QHBoxLayout(w)
            l.addWidget(chk)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setContentsMargins(0, 0, 0, 0)
            self.tbl_hist.setCellWidget(i, 1, w)

            # Sparkline
            item_trend = QTableWidgetItem()
            trend_data = [ro['value_num'] for ro in rows
                          if ro['test_code'] == r['test_code'] and ro['level'] == r['level'] and ro[
                              'value_num'] is not None][:10][::-1]
            item_trend.setData(Qt.ItemDataRole.UserRole, trend_data)
            self.tbl_hist.setItem(i, 2, item_trend)

            # Các cột thông tin
            cols_val = ["test_code", "run_time", "user", "run_type", "device", "department", "lot", "value", "unit"]
            for idx, k in enumerate(cols_val, 3):
                self.tbl_hist.setItem(i, idx, QTableWidgetItem(str(r.get(k) or "")))

            # --- CỘT CẢNH BÁO (Cột 12) ---
            # Parse lại note để hiển thị (hoặc có thể tối ưu bằng cách lưu biến tạm ở vòng lặp trên)
            note_raw = r.get("note", "")
            violation = ""
            if note_raw and str(note_raw).strip().startswith("{"):
                try:
                    extra = json.loads(note_raw)
                    violation = extra.get("violation", "")
                except:
                    pass

            pass_fail = r.get("pass_fail")
            status_text = ""
            bg_color = QBrush(QColor("transparent"))
            fg_color = QColor("black")

            # Logic hiển thị (Đồng nhất với logic lọc ở trên)
            if pass_fail == 1 or violation == "OK":
                status_text = "Đạt"
                fg_color = QColor("#2E7D32")
            else:
                if violation and violation != "OK":
                    rule_info = WESTGARD_RULES_MAP.get(violation, WESTGARD_RULES_MAP["Unknown"])
                    status_text = rule_info["msg"]
                    bg_color = rule_info["color"]
                elif pass_fail == 0:
                    status_text = "Lỗi"
                    bg_color = COLOR_FAIL_BG
                elif pass_fail == 2:
                    status_text = "Cảnh báo"
                    bg_color = COLOR_WARN_BG

            item_status = QTableWidgetItem(status_text)
            item_status.setBackground(bg_color)
            item_status.setForeground(fg_color)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_hist.setItem(i, 12, item_status)

            # Cột Note (Cột 13)
            self.tbl_hist.setItem(i, 13, QTableWidgetItem(str(note_raw)))

        self.tbl_hist.resizeColumnsToContents()
        self.tbl_hist.setColumnWidth(2, 80)

    def _show_context_menu(self, pos):
        item = self.tbl_hist.itemAt(pos)
        if not item: return
        rid = self.tbl_hist.item(item.row(), 0).text()
        menu = QMenu(self)
        if HAS_CAPA:
            menu.addAction("📝 Tạo/Sửa Phiếu CAPA").triggered.connect(lambda: self._open_capa_dialog(rid, ""))
            menu.addSeparator()
        for act in STANDARD_ACTIONS: menu.addAction(act).triggered.connect(
            lambda _, a=act: self._update_note_quick(rid, a, ""))
        menu.exec(self.tbl_hist.viewport().mapToGlobal(pos))

    def _update_note_quick(self, rid, new_text, old_text):
        try:
            self.iqc_service.add_note_to_result(rid, new_text)
            self._reload_history()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))

    def _open_capa_dialog(self, rid, info):
        # rid là ID kết quả IQC, info là thông tin Test
        row = self.tbl_hist.currentRow()
        violation = self.tbl_hist.item(row, 12).text()  # Cột Cảnh báo

        dlg = StandardCapaDialog(
            parent=self,
            source="IQC",
            title_incident=f"Lỗi Westgard: {violation}",
            initial_desc=f"Kết quả IQC vi phạm quy tắc {violation} tại mã kết quả {rid}.",
            test_info=info
        )

        if dlg.exec():
            data = dlg.get_data()
            # SỬA: Thay self.service bằng self.capa_service
            self.capa_service.create_capa_entry(**data)
            InfoBar.success("Thành công", "Đã lưu CAPA", parent=self)

    def _on_hist_edit_dialog(self, item):
        if not self.b_edit_hist: return
        self._edit_history_row(self.tbl_hist.item(item.row(), 6).text(), self.tbl_hist.item(item.row(), 10).text(),
                               self.tbl_hist.item(item.row(), 11).text())

    def _edit_selected_history(self):
        r = self.tbl_hist.currentRow()
        if r >= 0: self._edit_history_row(self.tbl_hist.item(r, 6).text(), self.tbl_hist.item(r, 10).text(),
                                          self.tbl_hist.item(r, 11).text())

    def _edit_history_row(self, run_type, val, unit):
        """Hàm xử lý logic khi bấm nút Chỉnh sửa (Admin)"""
        # Lấy ID kết quả đang chọn
        r = self.tbl_hist.currentRow()
        if r < 0: return
        rid = self.tbl_hist.item(r, 0).text()

        # Hiển thị hộp thoại sửa
        dlg = IQCEditDialog(self, run_type=run_type, value=val, unit=unit)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_val, new_unit = dlg.get_values()

            # Gọi Service để lưu vào Database
            success = self.iqc_service.update_result_value(
                result_id=rid,
                new_val=new_val,
                new_unit=new_unit,
                run_type=run_type
            )

            if success:
                QMessageBox.information(self, "Thành công", "Đã cập nhật kết quả.")
                self._reload_history()  # Tải lại bảng để thấy số mới
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể cập nhật dữ liệu (Lỗi Database).")

    def _delete_selected_history(self):
        """Xử lý sự kiện nút Xóa (Admin) - CHẾ ĐỘ XÓA VĨNH VIỄN"""
        r = self.tbl_hist.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn dòng cần xóa.")
            return

        # Lấy ID kết quả từ cột 0
        rid = self.tbl_hist.item(r, 0).text()

        # Hỏi xác nhận (Cảnh báo kỹ vì xóa vĩnh viễn không khôi phục được)
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa vĩnh viễn",
            "⚠️ CẢNH BÁO: Bạn có chắc chắn muốn xóa VĨNH VIỄN kết quả này không?\n\n"
            "Dữ liệu sẽ bị xóa hoàn toàn khỏi cơ sở dữ liệu và KHÔNG THỂ khôi phục.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            try:
                # Gọi hàm delete_result (Xóa cứng) thay vì set_result_active_status (Xóa mềm)
                success = self.iqc_service.delete_result(rid)

                if success:
                    QMessageBox.information(self, "Thành công", "Đã xóa dữ liệu vĩnh viễn.")
                    self._reload_history()  # Tải lại bảng để cập nhật
                else:
                    QMessageBox.critical(self, "Lỗi", "Không thể xóa dữ liệu (Lỗi Database hoặc ID không tồn tại).")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi ngoại lệ", str(e))


    def _on_history_active_changed(self, state):
        try:
            self.iqc_service.set_result_active_status(self.sender().property("result_id"), state == 2)
        except:
            pass

    def get_current_context(self):
        return {"department": self.cb_dep.currentText(),
                "test_code": self.tbl.item(self.tbl.currentRow(), 0).text() if self.tbl.currentRow() >= 0 else ""}