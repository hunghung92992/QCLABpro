# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_advanced_page.py
(FINAL CLEAN VERSION)
Container chính: Tích hợp tất cả các module phân tích nâng cao và cấu hình.
"""

from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
import traceback

# --- Import Tabs Con ---
# Import an toàn để tránh crash app nếu file con bị lỗi
try:
    from .iqc_opspecs_tab import IQCOpspecsTab
except ImportError: IQCOpspecsTab = None

try:
    from .iqc_lottolot_tab import IQCLotToLotTab
except ImportError: IQCLotToLotTab = None

try:
    from .iqc_youden_plot_tab import IQCYoudenPlotTab
except ImportError: IQCYoudenPlotTab = None

try:
    from .iqc_monitoring_chart_tab import IQCMonitoringChartTab
except ImportError: IQCMonitoringChartTab = None

try:
    from .iqc_predictive_tab import IQCPredictiveTab
except ImportError: IQCPredictiveTab = None

try:
    from .iqc_rules_config_tab import IQCRulesConfigTab
except ImportError as e:
    print(f"Import RulesConfig Error: {e}")
    IQCRulesConfigTab = None

try:
    from .iqc_system_ops_tab import IQCSystemOpsTab
except ImportError: IQCSystemOpsTab = None

class IQCAdvancedPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        tabs = QTabWidget()
        root.addWidget(tabs)

        def add_safe(TabClass, title):
            if TabClass is None:
                tabs.addTab(QLabel(f"Không tìm thấy module: {title}"), title)
                return
            try:
                widget = TabClass(self)
                tabs.addTab(widget, title)
            except Exception as e:
                # Hiện lỗi chi tiết ra màn hình để debug
                err_msg = f"Lỗi khởi tạo {title}:\n{str(e)}\n\n{traceback.format_exc()}"
                tabs.addTab(QLabel(err_msg), title)
                print(err_msg)

        add_safe(IQCOpspecsTab, "Biểu đồ OPSpecs")
        add_safe(IQCYoudenPlotTab, "Biểu đồ Youden")
        add_safe(IQCMonitoringChartTab, "Theo dõi (CV, Bias)")
        add_safe(IQCLotToLotTab, "So sánh Lot-to-Lot")
        add_safe(IQCPredictiveTab, "Dự đoán Trend AI")
        add_safe(IQCRulesConfigTab, "Cấu hình Quy tắc")
        add_safe(IQCSystemOpsTab, "Tác vụ Hệ thống")