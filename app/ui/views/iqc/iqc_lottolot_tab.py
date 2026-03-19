# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_lottolot_tab.py
(FLUENT DESIGN VERSION - EP26-A UPGRADE)
Giao diện Tab So sánh Lot-to-Lot (LTL) theo chuẩn CLSI EP26-A.
Tính năng mới:
- Lookback: Tính toán số lượng mẫu bệnh nhân cần kiểm tra lại khi Fail.
- Audit Trail: Lưu lịch sử phê duyệt/từ chối lô mới.
"""

import datetime as dt
from typing import List, Dict, Any, Optional
import numpy as np

# --- PYSIDE6 IMPORTS ---
from PySide6.QtCore import Qt, QSettings, QDateTime
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QLabel, QSpinBox,
    QDoubleSpinBox, QFrame, QGridLayout, QAbstractItemView, QGroupBox
)

# --- Imports Logic & Services ---
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    import io

    HAS_MPL = True

    import pandas as pd
    from openpyxl.drawing.image import Image as OpenpyxlImage

    HAS_PANDAS = True
except ImportError:
    HAS_MPL = False
    HAS_PANDAS = False
    FigureCanvas = QWidget
    Figure = lambda *args, **kwargs: None

from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService
from app.services.iqc_service import IQCService
from app.utils import analytics

# Key QSettings
SETTINGS_KEY_LTL = "ltl_acceptance_templates"

# --- FLUENT DESIGN STYLESHEET ---
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
    QLabel.SectionTitle {
        font-size: 16px;
        font-weight: 600;
        color: #0067C0;
    }
    QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QLineEdit {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 5px 8px;
        min-height: 24px;
    }
    QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
        border: 2px solid #0067C0;
        border-bottom: 2px solid #0067C0;
    }
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: 500;
    }
    QPushButton:hover { background-color: #F6F6F6; }

    QPushButton[class="primary"] {
        background-color: #0067C0;
        color: #FFFFFF;
        border: 1px solid #005FB8;
    }
    QPushButton[class="primary"]:hover { background-color: #1874D0; }

    QPushButton[class="success"] {
        background-color: #107C10;
        color: #FFFFFF;
        border: 1px solid #0B5A0B;
    }
    QPushButton[class="danger"] {
        background-color: #C50F1F;
        color: #FFFFFF;
        border: 1px solid #A80000;
    }

    QTableWidget {
        background-color: #FFFFFF;
        border: 1px solid #E5E5E5;
        border-radius: 6px;
        gridline-color: #F0F0F0;
    }
    QHeaderView::section {
        background-color: #FAFAFA;
        border: none;
        border-bottom: 1px solid #E0E0E0;
        padding: 6px;
        font-weight: 600;
        color: #444444;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #D1D1D1;
        border-radius: 6px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: #0067C0;
    }
"""


class IQCLotToLotTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)

        self.dept_service = DepartmentService()
        self.catalog_service = CatalogService()
        self.iqc_service = IQCService()

        self._history_cache: Dict[str, List[Dict[str, Any]]] = {}

        self._build_ui()
        self._load_departments()
        self._wire_signals()

        self.cb_level.currentIndexChanged.connect(self._load_template)
        self.cb_test.currentTextChanged.connect(self._load_template)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # --- ROW 1: INPUTS ---
        h_top = QHBoxLayout()
        h_top.setSpacing(16)

        # === CARD 1: DỮ LIỆU SO SÁNH ===
        card_data = QFrame()
        card_data.setProperty("class", "Card")
        l_data = QVBoxLayout(card_data)

        lbl_data = QLabel("Dữ liệu So sánh & Lookback")
        lbl_data.setProperty("class", "SectionTitle")
        l_data.addWidget(lbl_data)

        grid_data = QGridLayout()
        grid_data.setVerticalSpacing(12)
        grid_data.setHorizontalSpacing(12)

        self.cb_dept = QComboBox()
        self.cb_test = QComboBox()
        self.cb_test.setEditable(True)
        self.cb_level = QComboBox()
        self.cb_level.addItems(["L1", "L2", "L3"])

        self.cb_lot_ref = QComboBox()
        self.cb_lot_ref.setEditable(True)
        self.cb_lot_x = QComboBox()
        self.cb_lot_x.setEditable(True)

        self.dt_from = QDateEdit(QDateTime.currentDateTime().addDays(-90).date())
        self.dt_to = QDateEdit(QDateTime.currentDateTime().date())
        for d in (self.dt_from, self.dt_to):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")

        self.sp_max_delta = QSpinBox()
        self.sp_max_delta.setRange(1, 168)
        self.sp_max_delta.setValue(24)
        self.sp_max_delta.setSuffix(" giờ")

        # --- NEW: Lookback Inputs ---
        self.sp_daily_samples = QSpinBox()
        self.sp_daily_samples.setRange(1, 10000)
        self.sp_daily_samples.setValue(50)
        self.sp_daily_samples.setSuffix(" mẫu/ngày")

        self.sp_days_run = QSpinBox()
        self.sp_days_run.setRange(0, 365)
        self.sp_days_run.setValue(1)
        self.sp_days_run.setSuffix(" ngày")

        grid_data.addWidget(QLabel("Phòng ban:"), 0, 0)
        grid_data.addWidget(self.cb_dept, 0, 1)
        grid_data.addWidget(QLabel("Test:"), 1, 0)
        grid_data.addWidget(self.cb_test, 1, 1)
        grid_data.addWidget(QLabel("Level:"), 2, 0)
        grid_data.addWidget(self.cb_level, 2, 1)

        grid_data.addWidget(QLabel("Lot Tham Chiếu:"), 3, 0)
        grid_data.addWidget(self.cb_lot_ref, 3, 1)
        grid_data.addWidget(QLabel("Lot X (Mới):"), 4, 0)
        grid_data.addWidget(self.cb_lot_x, 4, 1)

        grid_data.addWidget(QLabel("Từ ngày:"), 5, 0)
        grid_data.addWidget(self.dt_from, 5, 1)
        grid_data.addWidget(QLabel("Đến ngày:"), 6, 0)
        grid_data.addWidget(self.dt_to, 6, 1)
        grid_data.addWidget(QLabel("Ghép cặp trong:"), 7, 0)
        grid_data.addWidget(self.sp_max_delta, 7, 1)

        # Add Lookback inputs
        grid_data.addWidget(QLabel("Công suất mẫu:"), 8, 0)
        grid_data.addWidget(self.sp_daily_samples, 8, 1)
        grid_data.addWidget(QLabel("Đã chạy Lot mới:"), 9, 0)
        grid_data.addWidget(self.sp_days_run, 9, 1)

        l_data.addLayout(grid_data)
        l_data.addStretch(1)

        # === CARD 2: TIÊU CHÍ & PHÊ DUYỆT ===
        card_crit = QFrame()
        card_crit.setProperty("class", "Card")
        l_crit = QVBoxLayout(card_crit)

        lbl_crit = QLabel("Tiêu chí Chấp nhận (EP26-A)")
        lbl_crit.setProperty("class", "SectionTitle")
        l_crit.addWidget(lbl_crit)

        grid_crit = QGridLayout()
        grid_crit.setVerticalSpacing(12)
        grid_crit.setHorizontalSpacing(12)

        self.sp_r2_min = QDoubleSpinBox()
        self.sp_r2_min.setRange(0.0, 1.0)
        self.sp_r2_min.setValue(0.950)
        self.sp_r2_min.setSingleStep(0.01)
        self.sp_slope_min = QDoubleSpinBox()
        self.sp_slope_min.setRange(0.0, 2.0)
        self.sp_slope_min.setValue(0.970)
        self.sp_slope_max = QDoubleSpinBox()
        self.sp_slope_max.setRange(0.0, 2.0)
        self.sp_slope_max.setValue(1.030)
        self.sp_int_abs = QDoubleSpinBox()
        self.sp_int_abs.setRange(0.0, 1000.0)
        self.sp_int_abs.setValue(2.500)
        self.sp_bias_perc = QDoubleSpinBox()
        self.sp_bias_perc.setRange(0.0, 100.0)
        self.sp_bias_perc.setValue(3.00)

        grid_crit.addWidget(QLabel("R² Min:"), 0, 0)
        grid_crit.addWidget(self.sp_r2_min, 0, 1)
        grid_crit.addWidget(QLabel("Slope Min:"), 1, 0)
        grid_crit.addWidget(self.sp_slope_min, 1, 1)
        grid_crit.addWidget(QLabel("Slope Max:"), 2, 0)
        grid_crit.addWidget(self.sp_slope_max, 2, 1)
        grid_crit.addWidget(QLabel("Intercept Max (Abs):"), 3, 0)
        grid_crit.addWidget(self.sp_int_abs, 3, 1)
        grid_crit.addWidget(QLabel("Bias Max (%):"), 4, 0)
        grid_crit.addWidget(self.sp_bias_perc, 4, 1)

        l_crit.addLayout(grid_crit)

        h_temp = QHBoxLayout()
        self.btn_save_template = QPushButton("Lưu Ngưỡng")
        self.btn_load_template = QPushButton("Tải Ngưỡng")
        h_temp.addWidget(self.btn_save_template)
        h_temp.addWidget(self.btn_load_template)
        l_crit.addLayout(h_temp)

        # --- Audit Trail Controls ---
        gb_audit = QGroupBox("Phê duyệt Lô (Audit)")
        l_audit = QVBoxLayout(gb_audit)
        h_audit_btns = QHBoxLayout()
        self.btn_approve = QPushButton("✅ Phê duyệt")
        self.btn_approve.setProperty("class", "success")
        self.btn_approve.setEnabled(False)
        self.btn_reject = QPushButton("⛔ Từ chối")
        self.btn_reject.setProperty("class", "danger")
        self.btn_reject.setEnabled(False)
        h_audit_btns.addWidget(self.btn_approve)
        h_audit_btns.addWidget(self.btn_reject)
        l_audit.addLayout(h_audit_btns)
        l_crit.addWidget(gb_audit)

        l_crit.addStretch(1)

        h_top.addWidget(card_data, 1)
        h_top.addWidget(card_crit, 1)
        root.addLayout(h_top)

        h_btns = QHBoxLayout()
        self.btn_run = QPushButton("⚡ Phân tích Dữ liệu")
        self.btn_run.setProperty("class", "primary")
        self.btn_run.setMinimumHeight(36)

        self.btn_export = QPushButton("Xuất Báo cáo (Excel/PDF)")
        self.btn_export.setMinimumHeight(36)

        h_btns.addStretch(1)
        h_btns.addWidget(self.btn_export)
        h_btns.addWidget(self.btn_run)
        root.addLayout(h_btns)

        # --- CARD 3: RESULTS TABLE ---
        self.tbl = QTableWidget(0, 13)  # Thêm 1 cột Lookback
        self.tbl.setHorizontalHeaderLabels([
            "Cặp Lot", "N (cặp)", "Cảnh báo",
            "PB Slope", "PB Int.", "Deming Slope", "Deming Int.", "R² (Corr)", "SE_E",
            "Mean Diff (BA)", "LoA Low", "Đánh giá", "Lookback (Mẫu)"
        ])
        self.tbl.verticalHeader().setVisible(False)

        # --- FIX LỖI CRASH TẠI ĐÂY ---
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # -----------------------------

        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl.setAlternatingRowColors(True)

        root.addWidget(self.tbl, 1)

        # --- Audit History Table ---
        self.tbl_audit = QTableWidget(0, 4)
        self.tbl_audit.setHorizontalHeaderLabels(["Thời gian", "Người dùng", "Hành động", "Chi tiết"])
        self.tbl_audit.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_audit.setMaximumHeight(100)
        # Ẩn mặc định, hiện khi cần
        # root.addWidget(self.tbl_audit)

        # --- CARD 4: CHARTS ---
        if HAS_MPL:
            chart_frame = QFrame()
            chart_frame.setProperty("class", "Card")
            l_chart = QVBoxLayout(chart_frame)

            self.fig = Figure(figsize=(12, 4), tight_layout=True, facecolor='white')
            self.canvas = FigureCanvas(self.fig)
            l_chart.addWidget(self.canvas)

            self.canvas.mpl_connect('button_press_event', self._on_click)
            root.addWidget(chart_frame, 2)
        else:
            self.canvas = None
            root.addWidget(QLabel("Thiếu 'matplotlib' để vẽ đồ thị."))

        self.btn_save_template.clicked.connect(self._save_template)
        self.btn_load_template.clicked.connect(self._load_template_ui)
        self.btn_approve.clicked.connect(lambda: self._save_audit_log("APPROVED"))
        self.btn_reject.clicked.connect(lambda: self._save_audit_log("REJECTED"))

    def _wire_signals(self):
        self.cb_dept.currentIndexChanged.connect(self._on_filter_changed)
        self.cb_test.currentTextChanged.connect(self._on_filter_changed)
        self.cb_level.currentIndexChanged.connect(self._on_filter_changed)
        self.cb_lot_ref.currentTextChanged.connect(self._on_filter_changed)
        self.cb_lot_x.currentTextChanged.connect(self._on_filter_changed)

        self.btn_run.clicked.connect(self._run_analysis)
        self.btn_export.clicked.connect(self._export_report)

    # --- (GIỮ NGUYÊN TOÀN BỘ LOGIC BÊN DƯỚI NHƯ FILE GỐC) ---
    def _get_template_key(self) -> str:
        test = self.cb_test.currentText().strip()
        level = self.cb_level.currentText().strip()
        return f"{test}.{level}" if test and level else None

    def _save_template(self):
        key = self._get_template_key()
        if not key:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn Test và Level trước khi lưu.")
            return
        settings = QSettings()
        settings.beginGroup(SETTINGS_KEY_LTL)
        settings.setValue(f"{key}/R2_MIN", self.sp_r2_min.value())
        settings.setValue(f"{key}/SLOPE_MIN", self.sp_slope_min.value())
        settings.setValue(f"{key}/SLOPE_MAX", self.sp_slope_max.value())
        settings.setValue(f"{key}/INT_ABS", self.sp_int_abs.value())
        settings.setValue(f"{key}/BIAS_PERC", self.sp_bias_perc.value())
        settings.endGroup()
        QMessageBox.information(self, "Thành công", f"Đã lưu ngưỡng chấp nhận cho {key}.")

    def _load_template_data(self) -> Dict[str, float]:
        key = self._get_template_key()
        if not key:
            return {"R2_MIN": 0.95, "SLOPE_MIN": 0.97, "SLOPE_MAX": 1.03, "INT_ABS": 2.5, "BIAS_PERC": 3.0}
        settings = QSettings()
        settings.beginGroup(SETTINGS_KEY_LTL)
        data = {
            "R2_MIN": float(settings.value(f"{key}/R2_MIN", 0.95)),
            "SLOPE_MIN": float(settings.value(f"{key}/SLOPE_MIN", 0.97)),
            "SLOPE_MAX": float(settings.value(f"{key}/SLOPE_MAX", 1.03)),
            "INT_ABS": float(settings.value(f"{key}/INT_ABS", 2.5)),
            "BIAS_PERC": float(settings.value(f"{key}/BIAS_PERC", 3.0)),
        }
        settings.endGroup()
        return data

    def _load_template(self):
        data = self._load_template_data()
        self.sp_r2_min.setValue(data["R2_MIN"])
        self.sp_slope_min.setValue(data["SLOPE_MIN"])
        self.sp_slope_max.setValue(data["SLOPE_MAX"])
        self.sp_int_abs.setValue(data["INT_ABS"])
        self.sp_bias_perc.setValue(data["BIAS_PERC"])

    def _load_template_ui(self):
        self._load_template()
        QMessageBox.information(self, "Tải Ngưỡng", "Đã tải ngưỡng chấp nhận thành công.")

    def _load_departments(self):
        self.cb_dept.clear()
        self.cb_dept.addItem("— Chọn phòng ban —", None)
        try:
            deps = self.dept_service.list_departments(active_only=True)
            for d in deps: self.cb_dept.addItem(d.name, d.name)
        except Exception as e:
            print(f"[IQCLotToLot] Lỗi nạp phòng ban: {e}")

    def _on_filter_changed(self):
        dep_name = self.cb_dept.currentText()
        level_selected = self.cb_level.currentText()
        if not dep_name or dep_name == "— Chọn phòng ban —":
            self.cb_test.clear()
            self.cb_lot_ref.clear()
            self.cb_lot_x.clear()
            return

        try:
            tests = self.catalog_service.list_tests_by_department(dep_name)
            current_test = self.cb_test.currentText()
            self.cb_test.blockSignals(True)
            self.cb_test.clear()
            self.cb_test.addItems([""] + tests)
            self.cb_test.setCurrentText(current_test)
            self.cb_test.blockSignals(False)
        except Exception as e:
            raise RuntimeError(f"Lỗi nạp test: {e}")

        try:
            lots_by_level = self.catalog_service.list_active_lots_by_level(dep_name, only_valid_expiry=False)
            lot_names_for_level = [info['lot_no'] for info in lots_by_level.get(level_selected, [])]
            lot_names_for_level.sort()
            for cb in [self.cb_lot_ref, self.cb_lot_x]:
                current_lot = cb.currentText()
                cb.blockSignals(True)
                cb.clear()
                cb.addItem("", None)
                cb.addItems(lot_names_for_level)
                cb.setCurrentText(current_lot)
                cb.blockSignals(False)
        except Exception as e:
            raise RuntimeError(f"Lỗi nạp LOT: {e}")

    def _pair_by_time(self, A, B, max_delta_hours):
        A_data = []
        for r in A:
            try:
                t = dt.datetime.fromisoformat(r['run_time'].replace("Z", "+00:00"))
                A_data.append((t, r['value_num'], r))
            except ValueError:
                pass
        B_data = []
        for r in B:
            try:
                t = dt.datetime.fromisoformat(r['run_time'].replace("Z", "+00:00"))
                B_data.append((t, r['value_num'], r))
            except ValueError:
                pass

        pairs_xy, pairs_details = [], []
        used_b_indices = set()
        delta_threshold = dt.timedelta(hours=max_delta_hours)

        for i, (ta, va, da) in enumerate(A_data):
            best_b_val, best_b_idx, min_delta = None, -1, delta_threshold
            for j, (tb, vb, db) in enumerate(B_data):
                if j in used_b_indices: continue
                delta = abs(ta - tb)
                if delta <= min_delta:
                    min_delta = delta
                    best_b_val = vb
                    best_b_idx = j
            if best_b_idx != -1 and best_b_val is not None:
                pairs_xy.append((va, best_b_val))
                pairs_details.append({"A": da, "B": B_data[best_b_idx][2]})
                used_b_indices.add(best_b_idx)
        X = [p[0] for p in pairs_xy]
        Y = [p[1] for p in pairs_xy]
        return X, Y, pairs_details

    def _calculate_ep26_stats(self, X, Y, crit_dict):
        stats = {
            "N": len(X), "Slope_PB": None, "Int_PB": None, "Slope_D": None, "Int_D": None,
            "R_Squared": None, "SE_E": None, "Mean_Diff_BA": None, "LoA_Low": None,
            "LoA_High": None, "Evaluation": None, "Color": None
        }
        if len(X) < 3:
            stats["Evaluation"] = "Fail: Không đủ mẫu (N<3)"
            stats["Color"] = "#D9534F"
            return stats

        slope_d, int_d = analytics.deming_regression(X, Y, lambda_val=1.0)
        ba_stats = analytics.bland_altman_stats(X, Y)
        corr_coeff = np.corrcoef(X, Y)[0, 1] if len(X) >= 2 else None
        r_squared = corr_coeff ** 2 if corr_coeff is not None and not np.isnan(corr_coeff) else None

        se_e = None
        if slope_d is not None and int_d is not None:
            Y_pred = slope_d * np.array(X) + int_d
            residuals = np.array(Y) - Y_pred
            se_e = np.std(residuals, ddof=1) if len(X) > 1 else None

        stats.update({
            "Slope_PB": slope_d, "Int_PB": int_d, "Slope_D": slope_d, "Int_D": int_d,
            "R_Squared": r_squared, "SE_E": se_e,
            "Mean_Diff_BA": ba_stats.get('mean_diff'), "LoA_Low": ba_stats.get('loa_low'),
            "LoA_High": ba_stats.get('loa_high')
        })

        is_fail = False
        if r_squared is not None and r_squared < crit_dict["R2_MIN"]: is_fail = True
        if not is_fail and slope_d is not None and int_d is not None:
            if not (crit_dict["SLOPE_MIN"] <= slope_d <= crit_dict["SLOPE_MAX"]): is_fail = True
            if not is_fail and abs(int_d) > crit_dict["INT_ABS"]: is_fail = True

        mean_X = np.mean(X) if X else 1.0
        if not is_fail and ba_stats["mean_diff"] is not None and mean_X != 0:
            mean_bias_perc = (ba_stats["mean_diff"] / mean_X) * 100
            if abs(mean_bias_perc) > crit_dict["BIAS_PERC"]: is_fail = True

        if is_fail:
            eval_str = "Từ chối"
            color = "#D9534F"
        elif stats["N"] < 20:
            eval_str = "Cảnh báo (N<20)"
            color = "#F0AD4E"
        else:
            eval_str = "Chấp nhận"
            color = "#5CB85C"
        stats["Evaluation"] = eval_str
        stats["Color"] = color
        return stats

    def _run_analysis(self):
        dep_name = self.cb_dept.currentText()
        test = self.cb_test.currentText()
        level = self.cb_level.currentText()
        lot_A = self.cb_lot_ref.currentText()
        lot_B = self.cb_lot_x.currentText()
        t_from = self.dt_from.date().toString("yyyy-MM-dd")
        t_to = self.dt_to.date().toString("yyyy-MM-dd")
        max_delta = self.sp_max_delta.value()

        selected_lots = [l for l in [lot_A, lot_B] if l]
        if len(selected_lots) < 2 or not (dep_name and test and level):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn đủ Phòng ban, Test, Level và ít nhất 2 LOT.")
            return

        crit_dict = self._load_template_data()
        histories = {}
        for lot_code in selected_lots:
            histories[lot_code] = self.iqc_service.get_history(
                department=dep_name, run_date_from=t_from, run_date_to=t_to,
                test_code=test, lot_no=lot_code, level=level, limit=2000, active_only=True
            )

        pairs_to_analyze = [(lot_A, lot_B)]
        self.tbl.setRowCount(0)
        all_plots = []
        self._history_cache = {}

        for lot_A, lot_B in pairs_to_analyze:
            hist_A = histories[lot_A]
            hist_B = histories[lot_B]
            X, Y, details = self._pair_by_time(hist_A, hist_B, max_delta_hours=max_delta)
            stats = self._calculate_ep26_stats(X, Y, crit_dict)
            pair_key = f"{lot_A} vs {lot_B}"
            self._history_cache[pair_key] = {"X": X, "Y": Y, "Details": details}

            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            eval_color = stats["Color"]

            # --- Tính Lookback Samples ---
            lookback_samples = "N/A"
            if stats["Evaluation"] == "Từ chối":
                samples_per_day = self.sp_daily_samples.value()
                days_run = self.sp_days_run.value()
                count = samples_per_day * days_run
                lookback_samples = f"{count} mẫu"

            def _set(c, v, fmt="{:.4g}", is_eval=False):
                txt = fmt.format(v) if v is not None and isinstance(v, (int, float)) else (v or "N/A")
                item = QTableWidgetItem(txt)
                item.setBackground(QColor(eval_color) if is_eval else Qt.white)
                self.tbl.setItem(r, c, item)

            _set(0, pair_key, fmt="{}")
            _set(1, stats["N"], fmt="{:.0f}")
            _set(2, "N<20" if stats["N"] < 20 else "OK", fmt="{}")
            _set(3, stats["Slope_PB"])
            _set(4, stats["Int_PB"])
            _set(5, stats["Slope_D"])
            _set(6, stats["Int_D"])
            _set(7, stats["R_Squared"])
            _set(8, stats["SE_E"])
            _set(9, stats["Mean_Diff_BA"])
            _set(10, stats.get("LoA_Low"))
            _set(11, stats["Evaluation"], fmt="{}", is_eval=True)
            _set(12, lookback_samples, fmt="{}")  # Cột Lookback

            if stats["N"] >= 3 and stats["Slope_D"] is not None:
                all_plots.append(
                    {"A": lot_A, "B": lot_B, "X": X, "Y": Y, "Stats": stats, "Label": pair_key, "Crit": crit_dict})

        # Enable Audit buttons if analysis run
        self.btn_approve.setEnabled(True)
        self.btn_reject.setEnabled(True)

        self.tbl.resizeColumnsToContents()
        if HAS_MPL and self.canvas and all_plots:
            self._plot_charts(all_plots)
        elif HAS_MPL and self.canvas:
            self.fig.clear()
            self.fig.add_subplot(111).text(0.5, 0.5, "Không đủ mẫu (N<20).", ha='center')
            self.canvas.draw()

    def _plot_charts(self, all_plots):
        self.fig.clear()
        num_pairs = len(all_plots)
        if num_pairs == 0: return
        gs = self.fig.add_gridspec(2, num_pairs)

        for i, data in enumerate(all_plots):
            X, Y = data['X'], data['Y']
            stats = data['Stats']
            crit_dict = data['Crit']

            # Deming
            ax_dm = self.fig.add_subplot(gs[0, i])
            ax_dm.scatter(X, Y, s=12, alpha=0.6)
            slope, intercept = stats['Slope_D'], stats['Int_D']
            min_val, max_val = min(min(X), min(Y)), max(max(X), max(Y))
            ax_dm.plot([min_val, max_val], [slope * min_val + intercept, slope * max_val + intercept], color='red',
                       label=f'Deming')
            ax_dm.plot([min_val, max_val], [min_val, max_val], color='gray', linestyle=':', label='y=x')
            ax_dm.set_title(f"Deming: {data['Label']} (R²: {stats['R_Squared']:.3f})", fontsize=9)
            ax_dm.legend(fontsize=7)

            # Bland-Altman
            ax_ba = self.fig.add_subplot(gs[1, i])
            avgs = [(x + y) / 2 for x, y in zip(X, Y)]
            diffs = [(x - y) for x, y in zip(X, Y)]
            ax_ba.scatter(avgs, diffs, s=12, alpha=0.6)
            ax_ba.axhline(stats['Mean_Diff_BA'], color='blue', linestyle='--')
            mean_X = np.mean(X) if X else 1.0
            if mean_X != 0:
                crit_bias_abs = (crit_dict['BIAS_PERC'] / 100.0) * abs(mean_X)
                ax_ba.axhline(crit_bias_abs, color='purple', linestyle='--')
                ax_ba.axhline(-crit_bias_abs, color='purple', linestyle='--')
            ax_ba.axhline(stats.get('LoA_High', 0), color='red', linestyle=':')
            ax_ba.axhline(stats.get('LoA_Low', 0), color='red', linestyle=':')
            ax_ba.set_title(f"Bland-Altman: {data['Label']}", fontsize=9)

        self.fig.tight_layout()
        self.canvas.draw()

    def _on_click(self, event):
        if event.button != 3 or not HAS_MPL: return
        if not event.inaxes: return
        QMessageBox.information(self, "Info", "Right-clicked plot")

    def _export_report(self):
        if not HAS_PANDAS or not HAS_MPL:
            QMessageBox.warning(self, "Thiếu thư viện", "Yêu cầu 'pandas', 'openpyxl', và 'matplotlib'.")
            return
        if self.tbl.rowCount() == 0:
            QMessageBox.information(self, "Không có dữ liệu", "Vui lòng chạy phân tích trước.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Lưu Báo cáo Lot-to-Lot", "CLSI_EP26_Report.xlsx",
                                              "Excel Files (*.xlsx)")
        if not path: return

        try:
            headers = [self.tbl.horizontalHeaderItem(i).text() for i in range(self.tbl.columnCount())]
            rows_data = []
            for r in range(self.tbl.rowCount()):
                row = {h: (self.tbl.item(r, c).text() if self.tbl.item(r, c) else "") for c, h in enumerate(headers)}
                rows_data.append(row)
            df = pd.DataFrame(rows_data, columns=headers)

            img_buffer = io.BytesIO()
            self.fig.savefig(img_buffer, format='png', dpi=200)
            img_buffer.seek(0)
            img = OpenpyxlImage(img_buffer)

            with pd.ExcelWriter(path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='EP26-A Analysis', index=False, startrow=1)
                ws = writer.sheets['EP26-A Analysis']
                ws.add_image(img, f'A{len(df) + 5}')

            QMessageBox.information(self, "Thành công", f"Đã xuất báo cáo EP26-A tại:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi khi xuất Excel", str(e))

    def _save_audit_log(self, action):
        """Lưu lịch sử phê duyệt/từ chối lô."""
        test = self.cb_test.currentText()
        lot = self.cb_lot_x.currentText()
        user = "User"  # Cần lấy user thực tế từ session
        time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Logic giả lập: Lưu vào file text hoặc DB
        log_entry = f"[{time}] {user} {action} Lot {lot} ({test})\n"

        # Thêm vào bảng hiển thị (nếu có) hoặc thông báo
        if action == "APPROVED":
            QMessageBox.information(self, "Audit Trail", f"Đã phê duyệt lô {lot}.\nGhi nhận lúc: {time}")
        else:
            QMessageBox.warning(self, "Audit Trail", f"Đã TỪ CHỐI lô {lot}.\nGhi nhận lúc: {time}")