# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QHeaderView, QTableWidgetItem
from qfluentwidgets import (CardWidget, SubtitleLabel, CaptionLabel, StrongBodyLabel,
                            TableWidget, FluentIcon as FIF, InfoBadge)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from app.services.capa_service import CapaService


class CapaDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = CapaService()
        self._build_ui()
        self.refresh_dashboard()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)

        # --- 1. Top Cards: Tổng số liệu ---
        self.top_layout = QHBoxLayout()
        self.card_total = self._create_stat_card("Tổng hồ sơ", "0", "#0078D4")
        self.card_open = self._create_stat_card("Đang mở", "0", "#C50F1F")
        self.card_overdue = self._create_stat_card("Quá hạn", "0", "#D13438")
        self.top_layout.addWidget(self.card_total)
        self.top_layout.addWidget(self.card_open)
        self.top_layout.addWidget(self.card_overdue)
        self.layout.addLayout(self.top_layout)

        # --- 2. Middle Row: Biểu đồ ---
        chart_layout = QHBoxLayout()

        # Biểu đồ Trạng thái (Pie Chart)
        self.fig_status, self.ax_status = plt.subplots(figsize=(4, 4))
        self.canvas_status = FigureCanvas(self.fig_status)
        card_chart_1 = CardWidget()
        l1 = QVBoxLayout(card_chart_1)
        l1.addWidget(StrongBodyLabel("Tỷ lệ Trạng thái"))
        l1.addWidget(self.canvas_status)
        chart_layout.addWidget(card_chart_1)

        # Biểu đồ Nguồn gốc (Bar Chart)
        self.fig_source, self.ax_source = plt.subplots(figsize=(4, 4))
        self.canvas_source = FigureCanvas(self.fig_source)
        card_chart_2 = CardWidget()
        l2 = QVBoxLayout(card_chart_2)
        l2.addWidget(StrongBodyLabel("Nguồn gốc Sự cố"))
        l2.addWidget(self.canvas_source)
        chart_layout.addWidget(card_chart_2)

        self.layout.addLayout(chart_layout)

        # --- 3. Bottom Row: Danh sách quá hạn ---
        overdue_card = CardWidget()
        low_lay = QVBoxLayout(overdue_card)
        low_lay.addWidget(StrongBodyLabel("⚠️ Danh sách hồ sơ cần xử lý gấp (Quá hạn)"))
        self.table_overdue = TableWidget()
        self.table_overdue.setColumnCount(4)
        self.table_overdue.setHorizontalHeaderLabels(["Mã số", "Tiêu đề", "Hạn chót", "Phụ trách"])
        self.table_overdue.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        low_lay.addWidget(self.table_overdue)
        self.layout.addWidget(overdue_card)

    def _create_stat_card(self, title, val, color):
        card = CardWidget()
        l = QVBoxLayout(card)
        l.addWidget(CaptionLabel(title))
        v = SubtitleLabel(val)
        v.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        l.addWidget(v)
        return card

    def refresh_dashboard(self):
        data = self.service.get_detailed_stats()

        # Cập nhật Cards
        total = sum(data['status'].values())
        self.card_total.findChild(SubtitleLabel).setText(str(total))
        self.card_open.findChild(SubtitleLabel).setText(str(data['status'].get('Open', 0)))
        self.card_overdue.findChild(SubtitleLabel).setText(str(len(data['overdue'])))

        # Vẽ Pie Chart Status
        self.ax_status.clear()
        labels = list(data['status'].keys())
        values = list(data['status'].values())
        if values:
            self.ax_status.pie(values, labels=labels, autopct='%1.1f%%', colors=['#FF9999', '#66B3FF', '#99FF99'])
        self.canvas_status.draw()

        # Vẽ Bar Chart Source
        self.ax_source.clear()
        src_labels = list(data['source'].keys())
        src_values = list(data['source'].values())
        if src_values:
            self.ax_source.bar(src_labels, src_values, color='#0078D4')
        self.canvas_source.draw()

        # Cập nhật bảng quá hạn
        self.table_overdue.setRowCount(0)
        for i, item in enumerate(data['overdue']):
            self.table_overdue.insertRow(i)
            self.table_overdue.setItem(i, 0, QTableWidgetItem(item['capa_id']))
            self.table_overdue.setItem(i, 1, QTableWidgetItem(item['title']))
            self.table_overdue.setItem(i, 2, QTableWidgetItem(item['due_date']))
            self.table_overdue.setItem(i, 3, QTableWidgetItem(item['owner']))