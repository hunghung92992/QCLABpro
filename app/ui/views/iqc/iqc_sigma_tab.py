# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_sigma_tab.py
(FLUENT DESIGN VERSION)
Giao diện Tab Phân tích Sigma.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
import numpy as np

# --- PYSIDE6 IMPORTS ---
from PySide6.QtCore import Qt, QDate, QDateTime, QSettings
from PySide6.QtGui import QFont, QColor, QPainter, QPdfWriter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QLabel, QDateEdit, QSpinBox, QDoubleSpinBox,
    QFrame, QGridLayout, QAbstractItemView  # <--- THÊM IMPORT
)
from PySide6.QtPrintSupport import QPrinter

# Helper functions
from app.utils.qt_compat import (
    combo_find_text_ci
)

# --- MATPLOTLIB ---
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.colors import ListedColormap, BoundaryNorm
    import matplotlib.pyplot as plt

    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = QWidget


    # Placeholder classes
    class Figure:
        def clear(self): pass

        def add_subplot(self, *args, **kwargs): return plt.gca()

        def colorbar(self, *args, **kwargs): pass

        def tight_layout(self): pass


    class BoundaryNorm:
        def __init__(self, *args, **kwargs): pass


    class ListedColormap:
        def __init__(self, *args, **kwargs): pass

        def set_bad(self, *args, **kwargs): pass

from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService
from app.services.iqc_service import IQCService
from app.utils import analytics
from app.utils.validators import to_float_safe as _to_float

# Key lưu cài đặt
SETTINGS_KEY_SIGMA = "iqc_sigma_filter"

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
    QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 5px 8px;
        min-height: 24px;
    }
    QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
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
    QPushButton:pressed { background-color: #F0F0F0; border-color: #B0B0B0; }

    QPushButton[class="primary"] {
        background-color: #0067C0;
        color: #FFFFFF;
        border: 1px solid #005FB8;
    }
    QPushButton[class="primary"]:hover { background-color: #1874D0; }

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
"""


class IQCSigmaTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)  # Apply Style

        # Khởi tạo Services
        self.dept_service = DepartmentService()
        self.catalog_service = CatalogService()
        self.iqc_service = IQCService()

        # Cache
        self._lots_cache: Dict[str, List[Dict[str, str]]] = {'L1': [], 'L2': [], 'L3': []}
        self._test_cache: List[str] = []

        # --- Init Logic ---
        self._build_ui()
        self._load_departments()
        self._load_filters()
        self._on_dep_changed()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # --- Card 1: Bộ lọc (Filter) ---
        filter_card = QFrame()
        filter_card.setProperty("class", "Card")
        lay_filter = QVBoxLayout(filter_card)

        # Title
        lbl_title = QLabel("Bộ lọc Phân tích Sigma")
        lbl_title.setProperty("class", "SectionTitle")
        lay_filter.addWidget(lbl_title)

        # Grid Inputs
        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(16)

        # Row 1
        self.cb_dept = QComboBox()
        self.cb_test = QComboBox()
        self.cb_test.setEditable(True)
        self.cb_level = QComboBox()
        self.cb_level.addItems(["— Tất cả Level —", "L1", "L2", "L3"])

        grid.addWidget(QLabel("Phòng ban:"), 0, 0)
        grid.addWidget(self.cb_dept, 0, 1)
        grid.addWidget(QLabel("Test Code:"), 0, 2)
        grid.addWidget(self.cb_test, 0, 3)
        grid.addWidget(QLabel("Level:"), 0, 4)
        grid.addWidget(self.cb_level, 0, 5)

        # Row 2
        self.dt_from = QDateEdit(QDateTime.currentDateTime().addDays(-90).date())
        self.dt_to = QDateEdit(QDateTime.currentDateTime().date())
        for d in (self.dt_from, self.dt_to):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")

        self.cb_lot = QComboBox()
        self.cb_lot.setEditable(True)
        self.cb_lot.addItem("— Tất cả Lot —", None)

        grid.addWidget(QLabel("Từ ngày:"), 1, 0)
        grid.addWidget(self.dt_from, 1, 1)
        grid.addWidget(QLabel("Đến ngày:"), 1, 2)
        grid.addWidget(self.dt_to, 1, 3)
        grid.addWidget(QLabel("Lot:"), 1, 4)
        grid.addWidget(self.cb_lot, 1, 5)

        # Row 3 (Min Settings)
        self.sb_sigma_min = QDoubleSpinBox()
        self.sb_sigma_min.setRange(0, 10)
        self.sb_sigma_min.setValue(0)
        self.sb_sigma_min.setSingleStep(0.5)

        self.sb_n_min = QSpinBox()
        self.sb_n_min.setRange(1, 100)
        self.sb_n_min.setValue(5)

        grid.addWidget(QLabel("Sigma Min:"), 2, 0)
        grid.addWidget(self.sb_sigma_min, 2, 1)
        grid.addWidget(QLabel("N Min:"), 2, 2)
        grid.addWidget(self.sb_n_min, 2, 3)

        lay_filter.addLayout(grid)
        lay_filter.addSpacing(10)

        # Action Buttons
        h_btns = QHBoxLayout()
        self.btn_run = QPushButton("Tính toán Sigma")
        self.btn_run.setProperty("class", "primary")
        self.btn_run.setMinimumHeight(32)

        self.btn_export_csv = QPushButton("Xuất CSV")
        self.btn_export_pdf = QPushButton("Xuất PDF")

        h_btns.addWidget(self.btn_run)
        h_btns.addWidget(self.btn_export_csv)
        h_btns.addWidget(self.btn_export_pdf)
        h_btns.addStretch(1)

        lay_filter.addLayout(h_btns)
        root.addWidget(filter_card)

        # --- Card 2: Table ---
        # Table Stats
        self.tbl_stats = QTableWidget(0, 16)
        self.tbl_stats.setHorizontalHeaderLabels([
            "Test", "Level", "Lot", "N", "Mean (Lab)", "SD (Lab)", "CV% (Lab)",
            "Target (Catalog)", "SD (Target)", "Unit", "TEa (%)", "TEa (abs)",
            "Bias (abs)", "Bias (%)", "Sigma (calc)", "Đánh giá"
        ])
        self.tbl_stats.verticalHeader().setVisible(False)

        # --- FIX LỖI TẠI ĐÂY ---
        self.tbl_stats.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # -----------------------

        self.tbl_stats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl_stats.horizontalHeader().setStretchLastSection(True)
        self.tbl_stats.setAlternatingRowColors(True)

        root.addWidget(self.tbl_stats, 1)  # Stretch factor 1

        # --- Card 3: Chart (Heatmap) ---
        if HAS_MPL:
            chart_card = QFrame()
            chart_card.setProperty("class", "Card")
            lay_chart = QVBoxLayout(chart_card)

            # Title for Chart
            lbl_chart = QLabel("Heatmap Sigma")
            lbl_chart.setProperty("class", "SectionTitle")
            lay_chart.addWidget(lbl_chart)

            self.fig_sigma = Figure(figsize=(6, 4), tight_layout=True, facecolor='white')
            self.canvas_sigma = FigureCanvas(self.fig_sigma)
            lay_chart.addWidget(self.canvas_sigma)

            root.addWidget(chart_card, 1)
        else:
            self.canvas_sigma = None
            lbl_err = QLabel("Thiếu 'matplotlib' để vẽ heatmap.")
            lbl_err.setAlignment(Qt.AlignCenter)
            root.addWidget(lbl_err)

        # --- Connect Signals ---
        self.btn_run.clicked.connect(self._run_analysis)
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_export_pdf.clicked.connect(self._export_pdf)
        self.cb_dept.currentIndexChanged.connect(self._on_dep_changed)
        self.cb_level.currentIndexChanged.connect(self._on_level_filter_changed)

    # --- LOGIC GIỮ NGUYÊN (Copy từ file gốc) ---

    def _load_departments(self):
        self.cb_dept.clear()
        self.cb_dept.addItem("— Tất cả —", None)
        try:
            deps = self.dept_service.list_departments(active_only=True)
            for d in deps:
                self.cb_dept.addItem(d.name, d.id)
        except Exception as e:
            print(f"[IQCSigmaTab] Lỗi nạp phòng ban: {e}")

    def _on_dep_changed(self):
        dep_name = self.cb_dept.currentText()
        if self.cb_dept.currentIndex() == 0: dep_name = ""

        try:
            self._test_cache = self.catalog_service.list_tests_by_department(dep_name)
            current_test = self.cb_test.currentText()
            self.cb_test.clear()
            self.cb_test.addItem("— Tất cả Test —", None)
            self.cb_test.addItems(self._test_cache)
            self.cb_test.setCurrentText(current_test)
        except Exception as e:
            print(f"[IQCSigmaTab] Lỗi nạp test: {e}")
            self._test_cache = []

        try:
            self._lots_cache = self.catalog_service.list_active_lots_by_level(dep_name)
        except Exception as e:
            print(f"[IQCSigmaTab] Lỗi nạp Lô (Lot): {e}")
            self._lots_cache = {'L1': [], 'L2': [], 'L3': []}

        self._on_level_filter_changed()

    def _on_level_filter_changed(self):
        selected_level = self.cb_level.currentText()
        current_lot_text = self.cb_lot.currentText()

        self.cb_lot.clear()
        self.cb_lot.addItem("— Tất cả Lot —", None)

        all_lots_set = set()
        if selected_level == "— Tất cả Level —":
            for key in ['L1', 'L2', 'L3']:
                for lot_info in self._lots_cache.get(key, []):
                    all_lots_set.add(lot_info["lot_no"])
        else:
            for lot_info in self._lots_cache.get(selected_level, []):
                all_lots_set.add(lot_info["lot_no"])

        self.cb_lot.addItems(sorted(list(all_lots_set)))
        self.cb_lot.setCurrentText(current_lot_text)

    def _save_filters(self):
        try:
            settings = QSettings()
            settings.beginGroup(SETTINGS_KEY_SIGMA)
            settings.setValue("department", self.cb_dept.currentText())
            settings.setValue("test_code", self.cb_test.currentText())
            settings.setValue("level", self.cb_level.currentText())
            settings.setValue("lot", self.cb_lot.currentText())
            settings.setValue("date_from", self.dt_from.date())
            settings.setValue("date_to", self.dt_to.date())
            settings.setValue("sigma_min", self.sb_sigma_min.value())
            settings.setValue("n_min", self.sb_n_min.value())
            settings.endGroup()
        except Exception as e:
            print(f"[IQCSigmaTab] Lỗi lưu settings: {e}")

    def _load_filters(self):
        try:
            settings = QSettings()
            settings.beginGroup(SETTINGS_KEY_SIGMA)

            dep_name = settings.value("department", self.cb_dept.currentText())
            idx = combo_find_text_ci(self.cb_dept, dep_name)
            if idx >= 0: self.cb_dept.setCurrentIndex(idx)

            self.cb_test.setCurrentText(settings.value("test_code", "— Tất cả Test —"))
            self.cb_level.setCurrentText(settings.value("level", "— Tất cả Level —"))
            self.cb_lot.setCurrentText(settings.value("lot", "— Tất cả Lot —"))

            date_from = settings.value("date_from", self.dt_from.date())
            date_to = settings.value("date_to", self.dt_to.date())

            if isinstance(date_from, QDate): self.dt_from.setDate(date_from)
            if isinstance(date_to, QDate): self.dt_to.setDate(date_to)

            self.sb_sigma_min.setValue(float(settings.value("sigma_min", 0.0)))
            self.sb_n_min.setValue(int(settings.value("n_min", 5)))
            settings.endGroup()
        except Exception as e:
            print(f"[IQCSigmaTab] Lỗi tải settings: {e}")

    def _get_target_and_tea(self, test_code: str, level: str, lot_no: str) -> Tuple[
        Optional[float], Optional[float], Optional[float], Optional[str]]:
        try:
            detail_row = self.catalog_service.get_target_by_lot(test_code, level, lot_no)
            if not detail_row: return None, None, None, None

            target_mean = _to_float(detail_row.get("mean"))
            target_sd = _to_float(detail_row.get("sd"))
            target_tea_percent = _to_float(detail_row.get("tea"))
            unit = detail_row.get("unit")
            return target_mean, target_sd, target_tea_percent, unit
        except Exception as e:
            print(f"[IQCSigmaTab] Lỗi lấy target/tea/sd: {e}")
        return None, None, None, None

    def _run_analysis(self):
        dep_id = self.cb_dept.currentData()
        dep_name = self.cb_dept.currentText() if dep_id is not None else None
        t_from = self.dt_from.date().toString("yyyy-MM-dd")
        t_to = self.dt_to.date().toString("yyyy-MM-dd")

        selected_test = self.cb_test.currentText()
        if self.cb_test.currentIndex() <= 0: selected_test = None

        selected_level = self.cb_level.currentText()
        if self.cb_level.currentIndex() <= 0: selected_level = None

        selected_lot = self.cb_lot.currentText()
        if self.cb_lot.currentIndex() <= 0: selected_lot = None

        n_min = self.sb_n_min.value()
        sigma_min = self.sb_sigma_min.value()

        self._save_filters()

        try:
            history = self.iqc_service.get_history(
                department=dep_name,
                run_date_from=t_from,
                run_date_to=t_to,
                test_code=selected_test,
                level=selected_level,
                lot_no=selected_lot,
                limit=10000,
                active_only=True
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải lịch sử IQC: {e}");
            return

        history = [r for r in history if r.get('result_type') == 'quant' and r.get('value_num') is not None]

        if not history:
            QMessageBox.information(self, "Thông báo", "Không tìm thấy dữ liệu Quant trong khoảng thời gian đã chọn.")
            self.tbl_stats.setRowCount(0)
            if self.canvas_sigma: self.fig_sigma.clear(); self.canvas_sigma.draw()
            return

        from collections import defaultdict
        grouped_data = defaultdict(list)
        for r in history:
            key = (r['test_code'], r['level'], r['lot'])
            grouped_data[key].append(r['value_num'])

        self.tbl_stats.setRowCount(0)
        heatmap_data = []
        failed_sigma_count = 0

        for (test, level, lot), values in grouped_data.items():
            if not test or not level or not lot: continue

            lab_mean, lab_sd, n = analytics.compute_stats(values)
            if lab_mean is None or lab_sd is None or n < n_min: continue

            lab_cv = analytics.safe_cv_percent(lab_mean, lab_sd)
            target_mean, target_sd, target_tea_percent, unit = self._get_target_and_tea(test, level, lot)

            eff_mean = target_mean if target_mean is not None else lab_mean
            eff_sd = target_sd if target_sd is not None else lab_sd
            eff_tea_percent = target_tea_percent if target_tea_percent is not None else 10.0

            bias_abs = abs(lab_mean - eff_mean) if eff_mean is not None else None
            bias_percent = analytics.calculate_bias_percent(lab_mean, eff_mean) if eff_mean is not None else None
            tea_abs = (eff_tea_percent / 100.0) * abs(eff_mean) if eff_mean != 0 else eff_tea_percent
            sigma = analytics.calculate_sigma(lab_mean, lab_sd, eff_mean, tea_abs) if bias_abs is not None else None

            if sigma is not None and sigma < sigma_min: continue

            eval_str = "Kém (<3)"
            if sigma is not None:
                if sigma >= 6:
                    eval_str = "Tốt (>=6)"
                elif sigma >= 4:
                    eval_str = "Khá (4-6)"
                elif sigma >= 3:
                    eval_str = "Đạt (3-4)"
                else:
                    failed_sigma_count += 1

            if target_sd is not None and lab_sd > target_sd * 1.5:
                eval_str += " (Cảnh báo: SD Lab cao)"

            r = self.tbl_stats.rowCount()
            self.tbl_stats.insertRow(r)

            def _set(c, v, is_num=False):
                txt = "N/A"
                if v is not None and not (isinstance(v, float) and math.isnan(v)):
                    if is_num:
                        txt = f"{v:.2f}"
                    elif isinstance(v, float):
                        txt = f"{v:.4g}"
                    else:
                        txt = str(v)
                self.tbl_stats.setItem(r, c, QTableWidgetItem(txt))

            _set(0, test);
            _set(1, level);
            _set(2, lot);
            _set(3, n)
            _set(4, lab_mean);
            _set(5, lab_sd);
            _set(6, lab_cv, True)
            _set(7, target_mean);
            _set(8, target_sd);
            _set(9, unit)
            _set(10, target_tea_percent, True);
            _set(11, tea_abs)
            _set(12, bias_abs);
            _set(13, bias_percent, True);
            _set(14, sigma, True)

            item_sigma = self.tbl_stats.item(r, 14)
            item_eval = QTableWidgetItem(eval_str)

            if sigma is not None:
                if sigma < 3:
                    color = QColor("#F8C4C4")
                elif sigma < 4:
                    color = QColor("#FFF2B2")
                else:
                    color = QColor("#D6F5D6")
                item_sigma.setBackground(color)
                item_eval.setBackground(color)

            if "Cảnh báo" in eval_str and (sigma is None or sigma >= 3):
                item_eval.setBackground(QColor("#FFF2B2"))

            self.tbl_stats.setItem(r, 15, item_eval)
            heatmap_data.append({"test": test, "level": level, "lot": lot, "sigma": sigma})

        self.tbl_stats.resizeColumnsToContents()
        if self.canvas_sigma: self._plot_heatmap(heatmap_data)

        if failed_sigma_count > 0:
            QMessageBox.warning(self, "Cảnh báo Sigma", f"Phát hiện {failed_sigma_count} quy trình có Sigma < 3.")
        else:
            QMessageBox.information(self, "Hoàn thành", f"Đã phân tích {len(heatmap_data)} quy trình.")

    def _plot_heatmap(self, rows: List[Dict[str, Any]]):
        if not HAS_MPL: return
        self.fig_sigma.clear()
        ax = self.fig_sigma.add_subplot(111)

        y_labels = sorted(list(set(r["test"] for r in rows)))
        x_labels = sorted(list(set(f"{r['level']}|{r['lot']}" for r in rows)))
        if not y_labels or not x_labels: self.canvas_sigma.draw(); return

        mat = np.full((len(y_labels), len(x_labels)), np.nan)
        for r in rows:
            try:
                iy = y_labels.index(r["test"])
                ix = x_labels.index(f"{r['level']}|{r['lot']}")
                mat[iy, ix] = r["sigma"]
            except ValueError:
                pass

        M = np.ma.masked_invalid(mat)
        bounds = [0, 2, 3, 4, 6, 100]
        colors = ["#D9534F", "#F0AD4E", "#FFFFB2", "#90EE90", "#006400"]
        cmap = ListedColormap(colors)
        cmap.set_bad(color="#E0E0E0")
        norm = BoundaryNorm(bounds, cmap.N)

        im = ax.imshow(M, aspect="auto", cmap=cmap, norm=norm)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if not np.ma.is_masked(M[i, j]):
                    ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=8, color="black")

        ax.set_yticks(range(len(y_labels)));
        ax.set_yticklabels(y_labels, fontsize=9)
        ax.set_xticks(range(len(x_labels)));
        ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=9)
        ax.set_title("Heatmap Sigma (Cao hơn = Tốt hơn)")
        cbar = self.fig_sigma.colorbar(im, ax=ax, ticks=[1, 2.5, 3.5, 5, 50], boundaries=bounds)
        cbar.ax.set_yticklabels(["<2", "2-3", "3-4", "4-6", ">=6"])
        self.canvas_sigma.draw()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu CSV", "sigma_dashboard.csv", "CSV Files (*.csv)")
        if not path: return
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                headers = [self.tbl_stats.horizontalHeaderItem(i).text() for i in range(self.tbl_stats.columnCount())]
                w.writerow(headers)
                for r in range(self.tbl_stats.rowCount()):
                    row = [self.tbl_stats.item(r, c).text() if self.tbl_stats.item(r, c) else "" for c in
                           range(self.tbl_stats.columnCount())]
                    w.writerow(row)
            QMessageBox.information(self, "Xuất CSV", f"Đã lưu: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu CSV: {e}")

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Lưu Báo cáo PDF", "sigma_report.pdf", "PDF Files (*.pdf)")
        if not path: return
        try:
            pdf_writer = QPdfWriter(path)
            pdf_writer.setPageSize(QPrinter.A4)
            pdf_writer.setPageOrientation(QPrinter.Landscape)
            painter = QPainter(pdf_writer)

            painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
            painter.drawText(50, 100, f"Báo cáo Phân tích Sigma - {self.cb_dept.currentText()}")
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(50, 130, f"Từ ngày: {self.dt_from.text()} Đến ngày: {self.dt_to.text()}")

            table = self.tbl_stats
            table.resizeColumnsToContents()
            x_start, y_start = 50, 200
            painter.save()
            painter.translate(x_start, y_start)

            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            for j in range(table.columnCount()):
                header_text = table.horizontalHeaderItem(j).text()
                width = table.columnWidth(j)
                painter.drawText(0, 0, width, 30, Qt.AlignCenter | Qt.AlignVCenter, header_text)
                painter.drawRect(0, 0, width, 30)
                painter.translate(width, 0)
            painter.translate(-table.viewport().width(), 30)

            painter.setFont(QFont("Segoe UI", 9))
            for i in range(table.rowCount()):
                height = table.rowHeight(i)
                for j in range(table.columnCount()):
                    width = table.columnWidth(j)
                    item = table.item(i, j)
                    if item:
                        bg_color = item.background().color()
                        if bg_color.isValid() and bg_color != Qt.white:
                            painter.fillRect(0, 0, width, height, bg_color)
                        painter.drawText(5, 0, width - 10, height, Qt.AlignLeft | Qt.AlignVCenter, item.text())
                    painter.drawRect(0, 0, width, height)
                    painter.translate(width, 0)
                painter.translate(-table.viewport().width(), height)
            painter.restore()

            if self.canvas_sigma:
                pdf_writer.newPage()
                page_rect = pdf_writer.pageRect()
                img = self.canvas_sigma.grab()
                target_rect = img.rect()
                target_rect.moveCenter(page_rect.center())
                target_rect.moveTop(100)
                target_rect.setSize(
                    img.size().scaled(page_rect.width() - 200, page_rect.height() - 200, Qt.KeepAspectRatio))
                painter.drawImage(target_rect, img)

            painter.end()
            QMessageBox.information(self, "Xuất PDF", f"Đã lưu: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Xuất PDF", f"Lỗi: {e}")