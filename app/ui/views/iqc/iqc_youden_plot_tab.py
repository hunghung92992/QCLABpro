# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_youden_plot_tab.py
(FLUENT DESIGN - EXPERT UPGRADE - VIETNAMESE VERSION)
Tính năng:
- Biểu đồ Youden (Twin Plot) cho 3 cặp (L1vL2, L1vL3, L2vL3).
- Tự động phân loại lỗi (Hệ thống vs Ngẫu nhiên).
- Trực quan hóa rủi ro (Khoảng cách từ tâm & Vùng SDI).
"""
from __future__ import annotations
from typing import Optional, List, Dict

# --- PYSIDE6 IMPORTS ---
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QDateEdit, QPushButton, QLabel, QFrame, QGridLayout, QMessageBox
)

from app.utils.qt_compat import (
    fill_combo_from_list, get_combo_id, add_combo_item
)

# Services
from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService
from app.services.iqc_service import IQCService
from app.utils.validators import to_float_safe as _to_float

# Matplotlib
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches  # Cần thiết để vẽ hình tròn/hộp

    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = QWidget
    Figure = lambda *args, **kwargs: None
    np = None

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
"""


class IQCYoudenPlotTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)

        self.dept_service = DepartmentService()
        self.catalog_service = CatalogService()
        self.iqc_service = IQCService()

        self._lots_cache: Dict[str, List[Dict[str, str]]] = {'L1': [], 'L2': [], 'L3': []}
        self._test_cache: List[str] = []

        # Tạo Figure
        if HAS_MPL:
            self.fig_12 = Figure(figsize=(4, 4), tight_layout=True, facecolor='white')
            self.fig_13 = Figure(figsize=(4, 4), tight_layout=True, facecolor='white')
            self.fig_23 = Figure(figsize=(4, 4), tight_layout=True, facecolor='white')
        else:
            self.fig_12 = None
            self.fig_13 = None
            self.fig_23 = None

        self._build_ui()
        self._load_deps()
        self._on_dep_changed()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # --- Card 1: Bộ lọc (Filters) ---
        filter_card = QFrame()
        filter_card.setProperty("class", "Card")
        lay_filter = QVBoxLayout(filter_card)

        lbl_title = QLabel("Bộ lọc dữ liệu & Phân tích")
        lbl_title.setProperty("class", "SectionTitle")
        lay_filter.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(16)

        # Hàng 1
        self.cb_dep = QComboBox()
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd")
        self.dt_from.setDate(QDate.currentDate().addMonths(-3))
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd")
        self.dt_to.setDate(QDate.currentDate())

        grid.addWidget(QLabel("Phòng ban:"), 0, 0)
        grid.addWidget(self.cb_dep, 0, 1)
        grid.addWidget(QLabel("Từ ngày:"), 0, 2)
        grid.addWidget(self.dt_from, 0, 3)
        grid.addWidget(QLabel("Đến ngày:"), 0, 4)
        grid.addWidget(self.dt_to, 0, 5)

        # Hàng 2
        self.cb_test = QComboBox()
        self.cb_test.setEditable(True)
        self.cb_lot_l1 = QComboBox()
        self.cb_lot_l1.setEditable(True)
        self.cb_lot_l2 = QComboBox()
        self.cb_lot_l2.setEditable(True)
        self.cb_lot_l3 = QComboBox()
        self.cb_lot_l3.setEditable(True)

        grid.addWidget(QLabel("Mã xét nghiệm:"), 1, 0)
        grid.addWidget(self.cb_test, 1, 1)
        grid.addWidget(QLabel("Lô QC L1:"), 1, 2)
        grid.addWidget(self.cb_lot_l1, 1, 3)
        grid.addWidget(QLabel("Lô QC L2:"), 1, 4)
        grid.addWidget(self.cb_lot_l2, 1, 5)

        # Hàng 3
        grid.addWidget(QLabel("Lô QC L3:"), 2, 2)
        grid.addWidget(self.cb_lot_l3, 2, 3)

        self.b_analyze = QPushButton("Vẽ Biểu đồ Youden (Chuyên sâu)")
        self.b_analyze.setProperty("class", "primary")
        self.b_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_analyze.setMinimumHeight(32)
        grid.addWidget(self.b_analyze, 2, 4, 1, 2)

        lay_filter.addLayout(grid)
        root.addWidget(filter_card)

        # --- Card 2: Biểu đồ (Charts) ---
        plot_card = QFrame()
        plot_card.setProperty("class", "Card")
        plot_layout_main = QVBoxLayout(plot_card)

        lbl_plot_title = QLabel("Kết quả Phân tích Tương quan & Phân loại Lỗi")
        lbl_plot_title.setProperty("class", "SectionTitle")
        plot_layout_main.addWidget(lbl_plot_title)

        h_plots = QHBoxLayout()
        if HAS_MPL:
            self.canvas_12 = FigureCanvas(self.fig_12)
            self.canvas_13 = FigureCanvas(self.fig_13)
            self.canvas_23 = FigureCanvas(self.fig_23)
            h_plots.addWidget(self.canvas_12, 1)
            h_plots.addWidget(self.canvas_13, 1)
            h_plots.addWidget(self.canvas_23, 1)
        else:
            lbl_err = QLabel("Thiếu thư viện 'matplotlib'.")
            lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h_plots.addWidget(lbl_err)

        plot_layout_main.addLayout(h_plots)
        root.addWidget(plot_card, 1)

        # Signals
        self.cb_dep.currentIndexChanged.connect(self._on_dep_changed)
        self.b_analyze.clicked.connect(self._on_analyze)

    # --- LOGIC ---
    def _load_deps(self):
        try:
            deps = self.dept_service.list_departments(active_only=True)
            fill_combo_from_list(self.cb_dep, [{"id": d.name, "name": d.name} for d in deps], text_key="name",
                                 id_key="id")
        except:
            pass

    def _on_dep_changed(self):
        dep_name = self.cb_dep.currentText()
        try:
            self._test_cache = self.catalog_service.list_tests_by_department(dep_name)
            self.cb_test.clear()
            self.cb_test.addItems([""] + self._test_cache)
        except:
            pass

        try:
            self._lots_cache = self.catalog_service.list_active_lots_by_level(dep_name)
            for cb, lvl in zip([self.cb_lot_l1, self.cb_lot_l2, self.cb_lot_l3], ['L1', 'L2', 'L3']):
                cb.clear()
                add_combo_item(cb, f"— Chọn Lô {lvl} —", None)
                for l in self._lots_cache.get(lvl, []):
                    add_combo_item(cb, l["lot_no"], l["lot_no"])
        except:
            pass

    def _get_data(self, dep, test, lot, level, frm, to) -> Dict[str, float]:
        history = self.iqc_service.get_history(dep, frm, to, test, lot, level, limit=5000, active_only=True)
        data_by_date = {}
        for r in history:
            val, date = r.get('value_num'), r.get('run_date')
            if val is not None and date:
                data_by_date[date] = val
        return data_by_date

    # --- ADVANCED PLOTTING LOGIC ---
    def _plot_youden(self, fig, canvas, x_vals, y_vals, tgt_x, tgt_y, title):
        """
        Vẽ Youden Plot Nâng cao:
        1. Tính Z-Score.
        2. Vẽ vòng tròn 2SD, 3SD.
        3. Phân loại lỗi Hệ thống (trong dải chéo) vs Ngẫu nhiên (ngoài dải).
        4. Tô màu điểm dữ liệu theo mức rủi ro.
        """
        fig.clear()
        ax = fig.add_subplot(111)

        # Lấy Target
        mx = _to_float(tgt_x.get("mean"))
        sx = _to_float(tgt_x.get("sd"))
        my = _to_float(tgt_y.get("mean"))
        sy = _to_float(tgt_y.get("sd"))

        if not (mx and sx and my and sy):
            ax.text(0.5, 0.5, "Thiếu Target Mean/SD", ha='center', va='center')
            canvas.draw()
            return

        # 1. Chuyển đổi sang Z-Score (Standardized Difference Index - SDI)
        # Z = (Value - Mean) / SD
        z_x = np.array([(v - mx) / sx for v in x_vals])
        z_y = np.array([(v - my) / sy for v in y_vals])
        N = len(z_x)

        if N == 0:
            ax.text(0.5, 0.5, "Không có dữ liệu chung", ha='center')
            canvas.draw()
            return

        # 2. Tính toán Khoảng cách & Phân loại
        # - Khoảng cách đến tâm (0,0): Đánh giá rủi ro tổng thể
        dist_center = np.sqrt(z_x ** 2 + z_y ** 2)

        # - Khoảng cách đến đường chéo y=x: Đánh giá Lỗi Hệ thống vs Ngẫu nhiên
        # Công thức khoảng cách từ điểm (x0, y0) đến đường ax + by + c = 0 (ở đây x - y = 0)
        # d = |x0 - y0| / sqrt(1^2 + (-1)^2) = |x0 - y0| / sqrt(2)
        dist_diag = np.abs(z_x - z_y) / np.sqrt(2)

        # Ngưỡng phân loại: Điểm nằm trong vòng 1SD quanh đường chéo là "Hệ thống"
        THRESHOLD_SYS = 0.8
        is_systematic = dist_diag <= THRESHOLD_SYS
        is_random = ~is_systematic

        # Thống kê
        count_sys = np.sum(is_systematic)
        perc_sys = (count_sys / N) * 100
        perc_rnd = 100 - perc_sys
        avg_dist = np.mean(dist_center)

        # 3. Vẽ Vùng Rủi Ro (Visual Zones)
        # Vòng tròn 2SD (An toàn)
        circle_2sd = patches.Circle((0, 0), 2, fill=False, edgecolor='#2E7D32', linestyle='--', linewidth=1.5,
                                    label='Giới hạn 2SD')
        ax.add_patch(circle_2sd)
        # Vòng tròn 3SD (Nguy hiểm)
        circle_3sd = patches.Circle((0, 0), 3, fill=False, edgecolor='#C62828', linestyle='-', linewidth=1.5,
                                    label='Giới hạn 3SD')
        ax.add_patch(circle_3sd)

        # Vùng Lỗi Hệ thống (Dải màu dọc đường chéo)
        diag_range = np.linspace(-5, 5, 100)
        # Vẽ dải bao quanh đường y=x với độ rộng THRESHOLD_SYS * sqrt(2) theo chiều y
        offset_y = THRESHOLD_SYS * np.sqrt(2)
        # Thực tế đơn giản hơn: y_upper = x + offset, y_lower = x - offset
        # Vì dist_diag = |x-y|/sqrt(2) <= T  => |x-y| <= T*sqrt(2) => y thuộc [x - T*sqrt(2), x + T*sqrt(2)]
        offset = THRESHOLD_SYS * 1.414
        ax.fill_between(diag_range, diag_range - offset, diag_range + offset, color='#FFF3E0', alpha=0.5,
                        label='Vùng Lỗi Hệ thống')
        ax.plot(diag_range, diag_range, color='gray', linestyle=':', alpha=0.5)  # Đường tâm y=x

        # 4. Tô màu Điểm dữ liệu (Color Logic)
        colors = []
        for i in range(N):
            d = dist_center[i]
            if d > 3.0:
                colors.append('#D32F2F')  # Đỏ (Vi phạm 3SD)
            elif d > 2.0:
                # Cảnh báo: Phân loại màu theo loại lỗi
                if is_systematic[i]:
                    colors.append('#EF6C00')  # Cam (Cảnh báo Hệ thống)
                else:
                    colors.append('#9C27B0')  # Tím (Cảnh báo Ngẫu nhiên)
            else:
                colors.append('#388E3C')  # Xanh (Tốt)

        ax.scatter(z_x, z_y, c=colors, s=45, alpha=0.8, edgecolors='white', zorder=5)

        # 5. Hộp Thống kê (Stats Box)
        stats_msg = (
            f"N = {N}\n"
            f"Hệ thống: {perc_sys:.1f}%\n"
            f"Ngẫu nhiên: {perc_rnd:.1f}%\n"
            f"K/c TB: {avg_dist:.2f}σ"
        )
        props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='#BDBDBD')
        ax.text(0.05, 0.95, stats_msg, transform=ax.transAxes, fontsize=8,
                verticalalignment='top', bbox=props, zorder=6)

        # 6. Thiết lập Trục & Nhãn
        ax.axhline(0, color='gray', linestyle='-', linewidth=0.8, alpha=0.3)
        ax.axvline(0, color='gray', linestyle='-', linewidth=0.8, alpha=0.3)

        limit = 4.5
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect('equal', adjustable='box')  # Đảm bảo hình tròn không bị méo

        ax.set_xlabel("Mức X (Z-Score)", fontsize=9)
        ax.set_ylabel("Mức Y (Z-Score)", fontsize=9)
        ax.set_title(title, fontsize=10, fontweight='bold')
        ax.grid(True, linestyle=':', alpha=0.4)

        # Legend nhỏ gọn
        ax.legend(loc='lower right', fontsize=7, framealpha=0.8)

        canvas.draw()

    def _on_analyze(self):
        if not HAS_MPL:
            QMessageBox.warning(self, "Lỗi", "Thiếu thư viện matplotlib.")
            return

        dep = self.cb_dep.currentText()
        test = self.cb_test.currentText()
        frm = self.dt_from.date().toString("yyyy-MM-dd")
        to = self.dt_to.date().toString("yyyy-MM-dd")

        l1 = get_combo_id(self.cb_lot_l1)
        l2 = get_combo_id(self.cb_lot_l2)
        l3 = get_combo_id(self.cb_lot_l3)

        if not (test and l1 and (l2 or l3)):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn Xét nghiệm, Lô L1 và ít nhất Lô L2 hoặc L3.")
            return

        # Clear cũ
        if HAS_MPL:
            self.fig_12.clear()
            self.fig_13.clear()
            self.fig_23.clear()
            self.canvas_12.draw()
            self.canvas_13.draw()
            self.canvas_23.draw()

        # Lấy dữ liệu L1 (Base)
        d1 = self._get_data(dep, test, l1, "L1", frm, to)
        t1 = self.catalog_service.get_target_by_lot(test, "L1", l1)

        # Helper vẽ cặp
        def process_pair(la, lb, da, db, ta, tb, fig, cv, title):
            # Tìm ngày chung
            common_dates = sorted(list(set(da.keys()) & set(db.keys())))
            if common_dates:
                xa = [da[d] for d in common_dates]
                yb = [db[d] for d in common_dates]
                self._plot_youden(fig, cv, xa, yb, ta, tb, title)
            else:
                self._draw_empty_msg(fig, cv, "Không có dữ liệu chung theo ngày")

        # Cặp L1-L2
        if l2:
            d2 = self._get_data(dep, test, l2, "L2", frm, to)
            t2 = self.catalog_service.get_target_by_lot(test, "L2", l2)
            process_pair(l1, l2, d1, d2, t1, t2, self.fig_12, self.canvas_12, "L1 vs L2")

        # Cặp L1-L3
        if l3:
            d3 = self._get_data(dep, test, l3, "L3", frm, to)
            t3 = self.catalog_service.get_target_by_lot(test, "L3", l3)
            process_pair(l1, l3, d1, d3, t1, t3, self.fig_13, self.canvas_13, "L1 vs L3")

        # Cặp L2-L3
        if l2 and l3:
            # d2, t2, d3, t3 đã có ở trên
            process_pair(l2, l3, d2, d3, t2, t3, self.fig_23, self.canvas_23, "L2 vs L3")

    def _draw_empty_msg(self, fig, canvas, msg):
        fig.clear()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, msg, ha='center', va='center', fontsize=9, color='gray')
        ax.set_axis_off()
        canvas.draw()