# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_main_tab.py
(FINAL FIX: Robust Import & Safe Pivot Navigation)
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QMessageBox
)
from PySide6.QtCore import Qt

# --- Fluent UI Imports ---
from qfluentwidgets import (
    Pivot, PushButton, FluentIcon as FIF
)

# --- GRANULAR IMPORTS (Import lẻ để tránh lỗi dây chuyền) ---
EqaScheduleTab = None
EqaWizardTab = None
EqaCompareTab = None
EQAMasterDataDialog = None

# 1. Import Schedule
try:
    from .eqa_schedule_tab import EqaScheduleTab
except ImportError as e:
    print(f"⚠️ EQA Import Error (Schedule): {e}")

# 2. Import Wizard
try:
    from .eqa_wizard_tab import EqaWizardTab
except ImportError as e:
    print(f"⚠️ EQA Import Error (Wizard): {e}")

# 3. Import Compare
try:
    from .eqa_compare_tab import EqaCompareTab
except ImportError as e:
    print(f"⚠️ EQA Import Error (Compare): {e}")

# 4. Import Dialog
try:
    from app.ui.dialogs.eqa_master_data_dialog import EQAMasterDataDialog
except ImportError as e:
    print(f"⚠️ EQA Import Error (Dialog): {e}")

# Các vai trò được phép xem tab nâng cao và tab lịch
ELEVATED_ROLES = {"SUPERADMIN", "QA", "TRUONG_KHOA"}
SCHEDULE_ALLOWED_ROLES = {"SUPERADMIN", "QA"}


class EQAMainTab(QWidget):
    def __init__(self,
                 username: Optional[str] = None,
                 role: Optional[str] = None,
                 department: Optional[str] = None,
                 parent: Optional[QWidget] = None,
                 **kwargs):

        super().__init__(parent)

        # Xử lý tham số linh hoạt (ưu tiên tham số truyền vào, sau đó đến kwargs)
        self.props = {
            "db_path": kwargs.get("db_path"),
            "username": str(username or kwargs.get("current_username") or "user"),
            "role": str(role or kwargs.get("current_role") or "").upper(),
            "department": str(department or kwargs.get("current_department") or ""),
            "fullname": kwargs.get("fullname", "")
        }

        # Fallback username
        if self.props["username"] == "user" and kwargs.get("username"):
            self.props["username"] = kwargs.get("username")

        self.pivot: Optional[Pivot] = None
        self.stackedWidget: Optional[QStackedWidget] = None
        self.page_schedule: Optional[EqaScheduleTab] = None

        # Danh sách này dùng để theo dõi các tab đã add, tránh lỗi KeyError của Pivot
        self.added_route_keys: List[str] = []

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # --- Toolbar (Chỉ hiện nếu có quyền) ---
        if self.props["role"] in SCHEDULE_ALLOWED_ROLES:
            h_toolbar = QHBoxLayout()
            self.btn_master_data = PushButton(FIF.IOT, "Quản lý Danh mục EQA", self)
            self.btn_master_data.clicked.connect(self._open_master_data)

            h_toolbar.addWidget(self.btn_master_data)
            h_toolbar.addStretch(1)
            layout.addLayout(h_toolbar)

        # --- Cấu trúc Tabs ---
        self.pivot = Pivot(self)
        self.stackedWidget = QStackedWidget(self)

        layout.addWidget(self.pivot)
        layout.addWidget(self.stackedWidget)

        # ===== Tab 1: Lịch phân công =====
        if EqaScheduleTab:
            try:
                self.page_schedule = EqaScheduleTab(**self.props)
                self._add_tab(self.page_schedule, "schedule", "Lịch phân công")
            except Exception as e:
                self._add_error_tab("Lỗi Lịch", str(e), "schedule")
        else:
            self._add_error_tab("Lịch (Thiếu File)", "Không tìm thấy class EqaScheduleTab", "schedule")

        # ===== Tab 2: Nhập kết quả =====
        if EqaWizardTab:
            try:
                wizard_tab = EqaWizardTab(**self.props)
                self._add_tab(wizard_tab, "wizard", "Nhập kết quả")
            except Exception as e:
                self._add_error_tab("Lỗi Nhập", str(e), "wizard")
        else:
            self._add_error_tab("Nhập (Thiếu File)", "Không tìm thấy class EqaWizardTab", "wizard")

        # ===== Tab 3: So sánh kết quả =====
        if EqaCompareTab:
            try:
                compare_tab = EqaCompareTab(**self.props)
                self._add_tab(compare_tab, "compare", "Phân tích & So sánh")
            except Exception as e:
                self._add_error_tab("Lỗi So sánh", str(e), "compare")
        else:
            self._add_error_tab("So sánh (Thiếu File)", "Không tìm thấy class EqaCompareTab", "compare")

        # [FIX TIỆT ĐỂ] Sử dụng list self.added_route_keys để set tab
        # Không truy cập self.pivot.items[0] nữa vì nó gây lỗi KeyError trên một số version
        if self.added_route_keys:
            first_key = self.added_route_keys[0]
            self.pivot.setCurrentItem(first_key)
            self.stackedWidget.setCurrentIndex(0)
        else:
            # Fallback nếu không có tab nào (tránh trắng trang)
            lbl_empty = QLabel("Không có Module EQA nào được tải.")
            lbl_empty.setAlignment(Qt.AlignCenter)
            self.stackedWidget.addWidget(lbl_empty)

        # Kết nối sự kiện chuyển tab
        self.pivot.currentItemChanged.connect(self._on_pivot_changed)

    def _add_tab(self, widget: QWidget, route_key: str, title: str):
        """Helper thêm tab thành công."""
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(routeKey=route_key, text=title)
        self.added_route_keys.append(route_key)

    def _add_error_tab(self, title, error_msg, route_key):
        """Helper hiển thị tab lỗi thay vì crash."""
        print(f"⚠️ EQA Tab Error [{title}]: {error_msg}")
        lbl = QLabel(f"<b>{title}:</b><br>{error_msg}")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: red; font-size: 14px; background: #FFF0F0; border: 1px dashed red;")

        self.stackedWidget.addWidget(lbl)
        self.pivot.addItem(routeKey=route_key, text=f"⚠️ {title}")
        self.added_route_keys.append(route_key)

    def _on_pivot_changed(self, route_key: str):
        """Đồng bộ Pivot và StackedWidget."""
        # Tìm index trong danh sách key của mình quản lý
        try:
            index = self.added_route_keys.index(route_key)
            self.stackedWidget.setCurrentIndex(index)
        except ValueError:
            pass

    def _open_master_data(self):
        """Mở dialog Master Data."""
        try:
            if not EQAMasterDataDialog:
                QMessageBox.warning(self, "Lỗi", "Chưa import được Dialog Master Data.")
                return

            from app.services.eqa_service import EQAService
            dlg = EQAMasterDataDialog(self, eqa_service=EQAService())
            dlg.exec()

            # Reload dữ liệu cho tab Lịch nếu cần
            if self.page_schedule and hasattr(self.page_schedule, '_load_providers'):
                self.page_schedule._load_providers()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Quản lý Danh mục: {e}")