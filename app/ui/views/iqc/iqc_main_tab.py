# -*- coding: utf-8 -*-
"""

(FIXED: Tham số khởi tạo + PySide6 Alignment Flags)
Container chính chứa các Tab: Nhập liệu, Biểu đồ, Nâng cao...
"""

from __future__ import annotations
from typing import Optional, Union, Dict, Any, List

# --- PySide6 Imports ---
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QLabel
)
from PySide6.QtCore import Qt

# --- Fluent UI Imports ---
from qfluentwidgets import (
    Pivot, FluentIcon as FIF
)

# --- Import Sub-pages ---
# Sử dụng try/except để tránh crash app nếu thiếu file con
try:
    from .iqc_input_page import IQCInputPage
except ImportError:
    IQCInputPage = None

try:
    from .iqc_chart_page import IQCChartPage
except ImportError:
    IQCChartPage = None

try:
    from .iqc_advanced_page import IQCAdvancedPage
except ImportError:
    IQCAdvancedPage = None

try:
    from .iqc_schedule_page import IQCSchedulePage
except ImportError:
    IQCSchedulePage = None

# Phân quyền
ELEVATED_ROLES = {"SUPERADMIN", "QA", "TRUONG_KHOA"}
SCHEDULE_ALLOWED_ROLES = {"SUPERADMIN", "QA"}


class IQCMainTab(QWidget):
    def __init__(self,
                 parent: Optional[QWidget] = None,
                 username: Optional[str] = None,
                 role: Optional[str] = None,
                 department: Optional[str] = None,
                 fullname: Optional[str] = None,
                 db_path: Optional[str] = None,
                 **kwargs):
        """
        Khởi tạo nhận đủ 6 tham số từ MainWindowFluent.
        Thứ tự: self, parent, username, role, department, fullname + các tham số mở rộng.
        """
        super().__init__(parent)

        # Chuẩn hóa dữ liệu truyền vào (Props) - Giữ nguyên logic xử lý của bạn
        self.props = {
            "db_path": db_path,
            "username": username or "",
            "role": (role or "VIEWER").upper(),
            "department": department or "",
            "fullname": fullname or username or ""
        }

        # Khởi tạo các biến chứa trang
        self.page_input: Optional[QWidget] = None
        self.page_chart: Optional[QWidget] = None
        self.page_adv: Optional[QWidget] = None
        self.page_schedule: Optional[QWidget] = None

        self.tab_map: List[Dict[str, Any]] = []

        # Xây dựng giao diện
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Thanh điều hướng (Pivot)
        self.pivot = Pivot(self)
        layout.addWidget(self.pivot)

        # 2. Khu vực hiển thị trang (StackedWidget)
        self.stackedWidget = QStackedWidget(self)
        layout.addWidget(self.stackedWidget)

        # ===== TAB 1: NHẬP LIỆU =====
        if IQCInputPage:
            try:
                self.page_input = IQCInputPage(parent=self, **self.props)
                self._add_tab("input", "Nhập liệu", FIF.EDIT, self.page_input)
            except Exception as e:
                self._add_error_tab("input", "Lỗi Nhập liệu", str(e))
        else:
            self._add_error_tab("input", "Thiếu File Nhập", "IQCInputPage not found")

        # ===== TAB 2: BIỂU ĐỒ =====
        if IQCChartPage:
            try:
                self.page_chart = IQCChartPage(parent=self, **self.props)
                chart_icon = getattr(FIF, 'CHART', FIF.TILES)
                self._add_tab("chart", "Biểu đồ L-J", chart_icon, self.page_chart)
            except Exception as e:
                self._add_error_tab("chart", "Lỗi Biểu đồ", str(e))
        else:
            self._add_error_tab("chart", "Thiếu File Biểu đồ", "IQCChartPage not found")

        # ===== TAB 3: NÂNG CAO (Check quyền) =====
        if self.props["role"] in ELEVATED_ROLES:
            if IQCAdvancedPage:
                try:
                    self.page_adv = IQCAdvancedPage(parent=self, **self.props)
                    self._add_tab("advanced", "Phân tích Nâng cao", FIF.SEARCH, self.page_adv)
                except Exception as e:
                    self._add_error_tab("advanced", "Lỗi Nâng cao", str(e))
            else:
                self._add_placeholder_tab("advanced", "Phân tích Nâng cao", FIF.SEARCH)

        # ===== TAB 4: QUẢN LÝ LỊCH (Check quyền) =====
        if self.props["role"] in SCHEDULE_ALLOWED_ROLES:
            if IQCSchedulePage:
                try:
                    self.page_schedule = IQCSchedulePage(parent=self, role=self.props["role"])
                    self._add_tab("schedule", "Lịch & Sự kiện", FIF.CALENDAR, self.page_schedule)
                except Exception as e:
                    self._add_error_tab("schedule", "Lỗi Lịch", str(e))
            else:
                self._add_placeholder_tab("schedule", "Lịch & Sự kiện", FIF.CALENDAR)

        # Mặc định chọn tab đầu
        if self.tab_map:
            self.pivot.setCurrentItem(self.tab_map[0]['key'])
            self.stackedWidget.setCurrentIndex(0)

        # Kết nối sự kiện chuyển tab
        self.pivot.currentItemChanged.connect(self._on_pivot_changed)

    def _add_tab(self, key, text, icon, widget):
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(routeKey=key, text=text, icon=icon)
        self.tab_map.append({'key': key, 'widget': widget})

    def _add_error_tab(self, key, text, error_msg):
        """Hiển thị tab báo lỗi nếu module bị crash hoặc thiếu file"""
        container = QWidget()
        v = QVBoxLayout(container)
        lbl = QLabel(f"⚠️ <b>{text}</b><br>{error_msg}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("""
            color: #D13438; 
            font-size: 14px; 
            background: #FFF4F4; 
            border: 1px dashed #D13438; 
            border-radius: 8px;
            padding: 20px;
        """)
        v.addWidget(lbl)
        self.stackedWidget.addWidget(container)
        self.pivot.addItem(routeKey=key, text=text, icon=FIF.INFO)
        self.tab_map.append({'key': key, 'widget': container})

    def _add_placeholder_tab(self, key, text, icon):
        """Hiển thị tab cho các tính năng chưa hoàn thiện"""
        container = QWidget()
        v = QVBoxLayout(container)
        lbl = QLabel(f"🚧 <b>Module {text}</b><br>Chức năng đang được phát triển.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #666; font-size: 14px; padding: 20px;")
        v.addWidget(lbl)
        self.stackedWidget.addWidget(container)
        self.pivot.addItem(routeKey=key, text=text, icon=icon)
        self.tab_map.append({'key': key, 'widget': container})

    def _on_pivot_changed(self, route_key: str):
        """Xử lý khi người dùng click chuyển tab"""
        found_index = -1
        for i, item in enumerate(self.tab_map):
            if item['key'] == route_key:
                found_index = i
                break

        if found_index >= 0:
            self.stackedWidget.setCurrentIndex(found_index)

        # --- ĐỒNG BỘ DỮ LIỆU GIỮA CÁC TAB ---
        if route_key == "chart" and self.page_chart and self.page_input:
            try:
                if hasattr(self.page_input, 'get_current_context') and hasattr(self.page_chart, 'sync_from_context'):
                    context = self.page_input.get_current_context()
                    self.page_chart.sync_from_context(context)
            except Exception as e:
                print(f"[IQCMainTab] Sync Error: {e}")

    def apply_filter_from_dashboard(self, params: Dict[str, Any]):
        """
        Nhận tín hiệu điều hướng từ Dashboard (OverviewPage).
        Ví dụ: params = {'status': 'warning', 'target_tab': 'chart'}
        """
        target_tab = params.get('target_tab', 'input')
        self.pivot.setCurrentItem(target_tab)

        # Nếu có trang đích, truyền tham số lọc sâu hơn
        active_page = None
        for item in self.tab_map:
            if item['key'] == target_tab:
                active_page = item['widget']
                break

        if active_page and hasattr(active_page, 'apply_filter'):
            active_page.apply_filter(params)