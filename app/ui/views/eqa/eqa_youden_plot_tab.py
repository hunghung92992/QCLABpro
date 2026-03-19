# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_youden_plot_tab.py
(UPGRADED - CORRELATION PLOT: LAB vs TARGET)
Vẽ biểu đồ tương quan giữa Kết quả Lab và Giá trị Target (Mean Group).
Giúp phát hiện Lỗi hệ thống (Systematic Error) và Độ chệch (Bias).
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple
import datetime as dt

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox,
    QTableWidgetItem, QHeaderView, QLabel
)
from PySide6.QtCore import Qt

# --- Fluent UI Imports ---
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, ComboBox, SpinBox,
    TableWidget, StrongBodyLabel, BodyLabel, FluentIcon as FIF
)

# Services
from app.services.eqa_service import EQAService

# Matplotlib
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    import numpy as np  # Needed for regression line

    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = QWidget
    Figure = lambda *args, **kwargs: None
    np = None


class EQAYoudenPlotTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        super().__init__(parent)
        self.dao = EQAService()

        # Init Chart
        if HAS_MPL:
            self.fig = Figure(figsize=(8, 6), tight_layout=True)
            self.canvas = FigureCanvas(self.fig)
        else:
            self.fig = None
            self.canvas = QLabel("Thiếu thư viện 'matplotlib' hoặc 'numpy'.")
            self.canvas.setAlignment(Qt.AlignCenter)
            self.canvas.setStyleSheet("font-size: 14px; color: #666;")

        self._build_ui()
        self._load_master_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # --- 1. Filter Card ---
        filter_card = CardWidget(self)
        h_layout = QHBoxLayout(filter_card)
        h_layout.setContentsMargins(12, 12, 12, 12)
        h_layout.setSpacing(12)

        self.cb_provider = ComboBox()
        self.cb_provider.setPlaceholderText("Chọn Provider")

        self.cb_program = ComboBox()
        self.cb_program.setPlaceholderText("Chọn Program")

        self.cb_analyte = ComboBox()
        self.cb_analyte.setPlaceholderText("Chọn Xét nghiệm")

        self.btn_plot = PrimaryPushButton(FIF.TILES, "Vẽ Biểu đồ", self)

        # Add widgets
        h_layout.addWidget(BodyLabel("Provider:", self))
        h_layout.addWidget(self.cb_provider, 1)
        h_layout.addWidget(BodyLabel("Program:", self))
        h_layout.addWidget(self.cb_program, 1)
        h_layout.addWidget(BodyLabel("Analyte:", self))
        h_layout.addWidget(self.cb_analyte, 1)
        h_layout.addWidget(self.btn_plot)

        root.addWidget(filter_card)

        # --- 2. Chart Area ---
        chart_card = CardWidget(self)
        v_chart = QVBoxLayout(chart_card)
        v_chart.addWidget(self.canvas)
        root.addWidget(chart_card, 2)  # Stretch factor 2

        # --- 3. Stats Table ---
        stats_card = CardWidget(self)
        v_stats = QVBoxLayout(stats_card)
        v_stats.addWidget(StrongBodyLabel("Thống kê Hồi quy (Regression Stats)", self))

        self.tbl_stats = TableWidget(self)
        self.tbl_stats.setColumnCount(6)
        self.tbl_stats.setHorizontalHeaderLabels([
            "Slope (Độ dốc)", "Intercept (Giao điểm)", "R² (Hệ số KD)",
            "N (Điểm)", "Bias TB", "Đánh giá"
        ])
        self.tbl_stats.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_stats.verticalHeader().hide()
        self.tbl_stats.setBorderVisible(True)
        self.tbl_stats.setFixedHeight(80)  # Compact height

        v_stats.addWidget(self.tbl_stats)
        root.addWidget(stats_card)

        # --- Events ---
        self.cb_provider.currentIndexChanged.connect(self._on_provider_changed)
        self.cb_program.currentIndexChanged.connect(self._on_program_changed)
        self.btn_plot.clicked.connect(self._plot_chart)

    # --- Data Loading ---
    def _load_master_data(self):
        self.cb_provider.addItem("Chọn...", None)
        for p in self.dao.list_providers():
            self.cb_provider.addItem(p['name'], p['id'])

    def _on_provider_changed(self):
        self.cb_program.clear();
        self.cb_program.addItem("Chọn...", None)
        pid = self.cb_provider.currentData()
        if pid:
            for p in self.dao.list_programs(pid):
                self.cb_program.addItem(p['name'], p['id'])

    def _on_program_changed(self):
        self.cb_analyte.clear()
        pid = self.cb_program.currentData()
        if pid:
            temps = self.dao.get_param_templates(pid)
            for t in temps:
                self.cb_analyte.addItem(t['analyte'])

    # --- Plotting Logic ---
    def _plot_chart(self):
        if not HAS_MPL: return

        prog_id = self.cb_program.currentData()
        analyte = self.cb_analyte.currentText()

        if not prog_id or not analyte:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn Chương trình và Xét nghiệm.")
            return

        # 1. Get Data from Service
        # Data format: [{'round': '01', 'x': target, 'y': lab, 'unit': 'mg/dL'}, ...]
        data = self.dao.get_youden_data(prog_id, analyte)

        if not data or len(data) < 2:
            QMessageBox.information(self, "Thiếu dữ liệu", "Cần ít nhất 2 điểm dữ liệu để vẽ biểu đồ tương quan.")
            self.fig.clear()
            self.canvas.draw()
            return

        x = np.array([d['x'] for d in data])  # Target
        y = np.array([d['y'] for d in data])  # Lab Result
        rounds = [str(d['round']) for d in data]
        unit = data[0].get('unit', '')

        # 2. Draw Plot
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        # Scatter points
        ax.scatter(x, y, color='#0067C0', zorder=3, label='Dữ liệu Lab')

        # Ideal Line (y=x)
        min_val = min(x.min(), y.min()) * 0.95
        max_val = max(x.max(), y.max()) * 1.05
        ax.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.5, label='Lý tưởng (y=x)')

        # Regression Line (Hồi quy tuyến tính)
        # y = mx + c
        A = np.vstack([x, np.ones(len(x))]).T
        m, c = np.linalg.lstsq(A, y, rcond=None)[0]

        reg_line = m * x + c
        ax.plot(x, reg_line, 'r-', alpha=0.8, label=f'Hồi quy (y={m:.2f}x + {c:.2f})')

        # Annotate points
        for i, txt in enumerate(rounds):
            ax.annotate(txt, (x[i], y[i]), xytext=(3, 3), textcoords='offset points', fontsize=8)

        # Labels & Style
        ax.set_title(f"Tương quan EQA: {analyte} ({unit})", fontsize=10, fontweight='bold')
        ax.set_xlabel("Giá trị Đích (Target Mean)", fontsize=9)
        ax.set_ylabel("Kết quả Phòng Lab (Your Result)", fontsize=9)
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, linestyle=':', alpha=0.6)

        # Calculate R-squared
        correlation_matrix = np.corrcoef(x, y)
        correlation_xy = correlation_matrix[0, 1]
        r_squared = correlation_xy ** 2

        # 3. Update Stats Table
        avg_bias = np.mean(y - x)

        self.tbl_stats.setRowCount(1)
        self.tbl_stats.setItem(0, 0, QTableWidgetItem(f"{m:.3f}"))
        self.tbl_stats.setItem(0, 1, QTableWidgetItem(f"{c:.3f}"))
        self.tbl_stats.setItem(0, 2, QTableWidgetItem(f"{r_squared:.4f}"))
        self.tbl_stats.setItem(0, 3, QTableWidgetItem(str(len(x))))
        self.tbl_stats.setItem(0, 4, QTableWidgetItem(f"{avg_bias:.3f}"))

        eval_str = "Tốt" if r_squared > 0.95 else ("Khá" if r_squared > 0.9 else "Cần xem xét")
        self.tbl_stats.setItem(0, 5, QTableWidgetItem(eval_str))

        self.fig.tight_layout()
        self.canvas.draw()