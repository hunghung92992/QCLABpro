# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_opspecs_tab.py
(EXPERT VERSION - BUG FIX)
Biểu đồ OPSpecs chuẩn hóa với phân vùng màu và Westgard Advisor.
Đã sửa lỗi cú pháp khởi tạo QLabel.
"""

from typing import Optional
import numpy as np

# --- PYSIDE6 IMPORTS ---
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox,
    QPushButton, QDateEdit, QMessageBox, QLabel, QFrame,
    QGridLayout, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView
)

from app.utils.qt_compat import (
    fill_combo_from_list
)

from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService
from app.services.iqc_service import IQCService
from app.utils.charts import basic_stats
from app.utils.validators import to_float_safe as _to_float

# Matplotlib
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt

    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = QWidget
    Figure = lambda *args, **kwargs: None

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
    QComboBox, QDateEdit {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 5px 8px;
        min-height: 24px;
    }
    QComboBox:focus, QDateEdit:focus {
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

    /* Table Styling */
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


class IQCOpspecsTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)

        self.dept_service = DepartmentService()
        self.catalog_service = CatalogService()
        self.iqc_service = IQCService()

        # Cache để load nhanh hơn
        self._lots_cache = {'L1': [], 'L2': [], 'L3': []}

        self._build_ui()
        self._load_deps()
        self._on_dep_changed()  # Tải data ban đầu

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # --- Card 1: Bộ lọc (Filter) ---
        filter_card = QFrame()
        filter_card.setProperty("class", "Card")
        lay_filter = QVBoxLayout(filter_card)

        # [FIXED] Sửa lỗi khởi tạo Label
        lbl_title = QLabel("Bộ lọc OPSpecs")
        lbl_title.setProperty("class", "SectionTitle")
        lay_filter.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(16)

        # Row 1
        self.cb_dep = QComboBox()
        self.cb_test = QComboBox()
        self.cb_test.setEditable(True)
        self.cb_lot = QComboBox()
        self.cb_lot.setEditable(True)

        grid.addWidget(QLabel("Phòng ban:"), 0, 0)
        grid.addWidget(self.cb_dep, 0, 1)
        grid.addWidget(QLabel("Test Code:"), 0, 2)
        grid.addWidget(self.cb_test, 0, 3)
        grid.addWidget(QLabel("Lot QC:"), 0, 4)
        grid.addWidget(self.cb_lot, 0, 5)

        # Row 2
        self.dt_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd")

        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd")

        grid.addWidget(QLabel("Từ ngày:"), 1, 0)
        grid.addWidget(self.dt_from, 1, 1)
        grid.addWidget(QLabel("Đến ngày:"), 1, 2)
        grid.addWidget(self.dt_to, 1, 3)

        # Button
        self.btn_draw = QPushButton("📊 Phân tích OPSpecs & Advisor")
        self.btn_draw.setProperty("class", "primary")
        self.btn_draw.setMinimumHeight(32)
        grid.addWidget(self.btn_draw, 1, 4, 1, 2)

        lay_filter.addLayout(grid)
        root.addWidget(filter_card)

        # --- SPLITTER: Chart (Trái) & Advisor (Phải) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Chart Area
        chart_card = QFrame()
        chart_card.setProperty("class", "Card")
        lay_chart = QVBoxLayout(chart_card)

        # [FIXED] Sửa lỗi khởi tạo Label
        lbl_chart_title = QLabel("Biểu đồ Phân vùng Sigma")
        lbl_chart_title.setProperty("class", "SectionTitle")
        lay_chart.addWidget(lbl_chart_title)

        if HAS_MPL:
            self.fig = Figure(figsize=(6, 6), tight_layout=True, facecolor='white')
            self.canvas = FigureCanvas(self.fig)
            lay_chart.addWidget(self.canvas)
        else:
            self.canvas = None
            lay_chart.addWidget(QLabel("Thiếu thư viện 'matplotlib'."))

        splitter.addWidget(chart_card)

        # 2. Advisor Table Area
        advisor_card = QFrame()
        advisor_card.setProperty("class", "Card")
        lay_advisor = QVBoxLayout(advisor_card)

        # [FIXED] Sửa lỗi khởi tạo Label
        lbl_adv_title = QLabel("Westgard Advisor (Gợi ý QC)")
        lbl_adv_title.setProperty("class", "SectionTitle")
        lay_advisor.addWidget(lbl_adv_title)

        self.tbl_advisor = QTableWidget(0, 5)
        self.tbl_advisor.setHorizontalHeaderLabels(["Test", "Level", "Sigma", "Xếp hạng", "Gợi ý QC"])
        self.tbl_advisor.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tbl_advisor.horizontalHeader().setStretchLastSection(True)
        self.tbl_advisor.verticalHeader().setVisible(False)
        self.tbl_advisor.setAlternatingRowColors(True)

        lay_advisor.addWidget(self.tbl_advisor)
        splitter.addWidget(advisor_card)

        # Tỷ lệ hiển thị 60% - 40%
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root.addWidget(splitter, 1)

        # Events
        self.cb_dep.currentIndexChanged.connect(self._on_dep_changed)
        self.btn_draw.clicked.connect(self._draw_chart)

    # --- LOGIC LOAD DATA ---
    def _load_deps(self):
        self.cb_dep.clear()
        try:
            deps = self.dept_service.list_departments(active_only=True)
            fill_combo_from_list(self.cb_dep, [{"id": d.name, "name": d.name} for d in deps], text_key="name",
                                 id_key="id", add_empty=None)
        except Exception:
            pass

    def _on_dep_changed(self):
        """Khi đổi phòng ban -> Tải lại Test và Lot."""
        dep_name = self.cb_dep.currentText()

        # Load Test
        self.cb_test.blockSignals(True)
        self.cb_test.clear()
        self.cb_test.addItem("— Tất cả Test —", None)
        try:
            tests = self.catalog_service.list_tests_by_department(dep_name)
            self.cb_test.addItems(tests)
        except:
            pass
        self.cb_test.blockSignals(False)

        # Load Lot (có cache)
        self.cb_lot.blockSignals(True)
        self.cb_lot.clear()
        self.cb_lot.addItem("— Tất cả Lot —", None)
        try:
            self._lots_cache = self.catalog_service.list_active_lots_by_level(dep_name)
            all_lots = set()
            for lvl in ['L1', 'L2', 'L3']:
                for l in self._lots_cache.get(lvl, []):
                    all_lots.add(l['lot_no'])
            self.cb_lot.addItems(sorted(list(all_lots)))
        except:
            pass
        self.cb_lot.blockSignals(False)

    # --- LOGIC WESTGARD ADVISOR ---
    def _get_westgard_advice(self, sigma: float) -> tuple[str, str, str]:
        """Trả về: (Xếp hạng, Mã màu Hex, Gợi ý QC)"""
        if sigma >= 6.0:
            return ("World Class", "#C8E6C9", "1_3s (N=2). Kiểm tra tối thiểu.")
        elif sigma >= 5.0:
            return ("Excellent", "#DCEDC8", "1_3s/2_2s/R_4s (N=2).")
        elif sigma >= 4.0:
            return ("Good", "#FFF9C4", "1_3s/2_2s/R_4s/4_1s (N=2 hoặc N=4).")
        elif sigma >= 3.0:
            return ("Marginal", "#FFE0B2", "Cần N=4 hoặc N=6. Full Westgard.")
        else:
            return ("Poor", "#FFCDD2", "KHÔNG ĐẠT. Cần cải tiến phương pháp.")

    def _draw_chart(self):
        if not HAS_MPL:
            QMessageBox.warning(self, "Lỗi", "Không có thư viện Matplotlib")
            return

        dep_name = self.cb_dep.currentText()
        f_d = self.dt_from.date().toString("yyyy-MM-dd")
        t_d = self.dt_to.date().toString("yyyy-MM-dd")

        selected_test = self.cb_test.currentText()
        if "Tất cả" in selected_test or not selected_test: selected_test = None
        selected_lot = self.cb_lot.currentText()
        if "Tất cả" in selected_lot or not selected_lot: selected_lot = None

        # Xác định danh sách Test cần chạy
        tests_to_run = [selected_test] if selected_test else self.catalog_service.list_tests_by_department(dep_name)

        if not tests_to_run:
            QMessageBox.warning(self, "Trống", "Không có xét nghiệm nào.")
            return

        print(f"--- BẮT ĐẦU VẼ CHART (EXPERT) ---")
        points = []
        self.tbl_advisor.setRowCount(0)  # Reset bảng

        for test_code in tests_to_run:
            for level in ['L1', 'L2', 'L3']:
                lot_list = self._lots_cache.get(level, [])

                for lot_info in lot_list:
                    lot_no = lot_info['lot_no']
                    if selected_lot and lot_no != selected_lot: continue

                    # 1. Lấy Target
                    target = self.catalog_service.get_target_by_lot(test_code, level, lot_no)
                    if not target: continue

                    t_mean = _to_float(target.get('mean'))
                    t_tea_perc = _to_float(target.get('tea'))

                    if not t_mean or not t_tea_perc:
                        print(f"Skipping {test_code}-{level}: Thiếu Mean/TEa")
                        continue

                    # 2. Lấy Dữ liệu chạy máy
                    history = self.iqc_service.get_history(
                        department=dep_name, run_date_from=f_d, run_date_to=t_d,
                        test_code=test_code, level=level, lot_no=lot_no,
                        limit=500, active_only=True
                    )
                    vals = [r['value_num'] for r in history if r.get('value_num') is not None]

                    if len(vals) < 3: continue  # Bỏ qua nếu ít dữ liệu

                    # 3. Tính toán Thống kê & Sigma
                    stats = basic_stats(vals)
                    lab_mean = stats['mean']
                    lab_sd = stats['sd']

                    if lab_mean and lab_sd:
                        cv = abs(lab_sd / lab_mean * 100.0)
                        bias = abs((lab_mean - t_mean) / t_mean * 100.0)

                        # Tọa độ chuẩn hóa
                        norm_cv = (cv / t_tea_perc) * 100.0
                        norm_bias = (bias / t_tea_perc) * 100.0

                        # Sigma Metric: (TEa - Bias) / CV
                        sigma = (t_tea_perc - bias) / cv if cv > 0 else 0

                        # Thêm vào danh sách vẽ
                        points.append({
                            "label": f"{test_code} {level}",
                            "x": norm_cv,
                            "y": norm_bias,
                            "sigma": sigma
                        })

                        # --- CẬP NHẬT BẢNG ADVISOR ---
                        rating, bg_color, advice = self._get_westgard_advice(sigma)
                        r = self.tbl_advisor.rowCount()
                        self.tbl_advisor.insertRow(r)
                        self.tbl_advisor.setItem(r, 0, QTableWidgetItem(test_code))
                        self.tbl_advisor.setItem(r, 1, QTableWidgetItem(level))

                        item_sigma = QTableWidgetItem(f"{sigma:.2f}σ")
                        item_sigma.setTextAlignment(Qt.AlignCenter)
                        item_sigma.setBackground(QColor(bg_color))
                        item_sigma.setForeground(Qt.black)
                        self.tbl_advisor.setItem(r, 2, item_sigma)

                        self.tbl_advisor.setItem(r, 3, QTableWidgetItem(rating))
                        self.tbl_advisor.setItem(r, 4, QTableWidgetItem(advice))

        if not points:
            QMessageBox.information(self, "Thông báo", "Không có dữ liệu đủ điều kiện để vẽ (Cần Mean, SD và TEa).")
            return

        # --- VẼ BIỂU ĐỒ NÂNG CAO ---
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        # Tạo dải X từ 0 đến 100 (tương ứng Normalized CV)
        x_range = np.linspace(0, 100, 400)

        # Các đường giới hạn Sigma (Y = 100 - Sigma * X)
        y_6s = 100 - 6 * x_range
        y_5s = 100 - 5 * x_range
        y_4s = 100 - 4 * x_range
        y_3s = 100 - 3 * x_range
        y_2s = 100 - 2 * x_range

        # --- TÔ MÀU PHÂN VÙNG (ZONES) ---
        # World Class (>6s) - Xanh đậm
        ax.fill_between(x_range, 0, y_6s, where=(y_6s >= 0), color='#C8E6C9', alpha=0.6, label='World Class (>6σ)')
        # Excellent (5-6s) - Xanh nhạt
        ax.fill_between(x_range, y_6s, y_5s, where=(y_5s >= 0) & (y_5s > y_6s), color='#DCEDC8', alpha=0.6,
                        label='Excellent (5-6σ)')
        # Good (4-5s) - Vàng
        ax.fill_between(x_range, y_5s, y_4s, where=(y_4s >= 0) & (y_4s > y_5s), color='#FFF9C4', alpha=0.6,
                        label='Good (4-5σ)')
        # Marginal (3-4s) - Cam
        ax.fill_between(x_range, y_4s, y_3s, where=(y_3s >= 0) & (y_3s > y_4s), color='#FFE0B2', alpha=0.6,
                        label='Marginal (3-4σ)')
        # Poor (<3s) - Đỏ
        ax.fill_between(x_range, y_3s, y_2s, where=(y_2s >= 0) & (y_2s > y_3s), color='#FFCDD2', alpha=0.6,
                        label='Poor (<3σ)')

        # Vẽ đường ranh giới
        for y_line in [y_6s, y_5s, y_4s, y_3s]:
            ax.plot(x_range, y_line, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)

        # Vẽ điểm dữ liệu
        for p in points:
            # Màu điểm dựa trên Sigma
            c = 'black'
            if p['sigma'] < 3:
                c = 'red'
            elif p['sigma'] < 4:
                c = '#E65100'  # Dark Orange

            ax.plot(p['x'], p['y'], marker='o', color=c, markeredgecolor='white', markersize=8)

            # Chỉ hiện nhãn nếu ít điểm hoặc điểm kém
            if len(points) < 15 or p['sigma'] < 4:
                ax.text(p['x'] + 1, p['y'], p['label'], fontsize=8, fontweight='bold', alpha=0.9)

        ax.set_xlim(0, 60)  # Normalized Imprecision
        ax.set_ylim(0, 120)  # Normalized Bias
        ax.set_xlabel("Normalized Imprecision (CV / TEa) %")
        ax.set_ylabel("Normalized Inaccuracy (Bias / TEa) %")
        ax.set_title(f"Method Decision Chart (Expert)", fontsize=10, fontweight='bold')
        ax.legend(fontsize='small', loc='upper right')
        ax.grid(True, linestyle=':', alpha=0.3)

        self.canvas.draw()
        print("--- VẼ THÀNH CÔNG ---")