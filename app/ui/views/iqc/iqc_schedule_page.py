# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_schedule_page.py
(WIN11 FLUENT DESIGN - LIGHT/DARK MODE SUPPORT)
- Quản lý lịch chạy mẫu nội kiểm.
- Sử dụng TableWidget, InfoBadge và SearchLineEdit của Fluent UI.
- Giữ nguyên toàn bộ logic nghiệp vụ cũ.
"""

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem
)

# --- FLUENT UI IMPORTS ---
from qfluentwidgets import (
    TableWidget, PrimaryPushButton, PushButton, ComboBox,
    SearchLineEdit, FluentIcon as FIF, InfoBadge,
    StrongBodyLabel, CardWidget, InfoBar
)

# Imports Services
from app.services.department_service import DepartmentService
from app.services.iqc_schedule_service import IQCScheduleService
from app.ui.dialogs.iqc_schedule_dialog import IQCScheduleConfigDialog

# Allowed roles
ALLOWED_ROLES = {"SUPERADMIN", "QA", "TRUONG_KHOA"}


class IQCSchedulePage(QWidget):
    def __init__(self, parent=None, role: str = "VIEWER"):
        super().__init__(parent)

        self.current_role = (role or "").upper()
        self.can_edit = self.current_role in ALLOWED_ROLES

        self.dept_service = DepartmentService()
        self.sched_service = IQCScheduleService()

        self._build_ui()
        self._load_departments()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # --- 1. TOOLBAR (CardWidget) ---
        # Sử dụng CardWidget để tạo khung chứa công cụ đẹp mắt
        top_card = CardWidget(self)
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(20, 10, 20, 10)
        top_layout.setSpacing(12)

        # Label + ComboBox
        top_layout.addWidget(StrongBodyLabel("Phòng ban:", self))
        self.cb_dep = ComboBox()
        self.cb_dep.setMinimumWidth(200)
        self.cb_dep.addItem("— Tất cả —", None)
        top_layout.addWidget(self.cb_dep)

        # Search Bar (Fluent)
        self.txt_search = SearchLineEdit(self)
        self.txt_search.setPlaceholderText("Tìm kiếm xét nghiệm...")
        self.txt_search.setFixedWidth(280)
        self.txt_search.textChanged.connect(self._filter_table_client_side)
        top_layout.addWidget(self.txt_search)

        top_layout.addStretch(1)

        # Buttons
        self.btn_refresh = PushButton(FIF.SYNC, "Làm mới", self)
        self.btn_refresh.clicked.connect(self._load_data)
        top_layout.addWidget(self.btn_refresh)

        if self.can_edit:
            # Sử dụng icon SETTING (số ít) chuẩn xác
            self.btn_config = PrimaryPushButton(FIF.SETTING, "Cấu hình Lịch", self)
            self.btn_config.clicked.connect(self._open_config_dialog)
            top_layout.addWidget(self.btn_config)

        layout.addWidget(top_card)

        # --- 2. TABLE (Fluent TableWidget) ---
        self.table = TableWidget(self)

        # Cấu hình bảng Fluent
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # Ẩn lưới dọc để nhìn thoáng hơn
        self.table.setAlternatingRowColors(True)  # Màu xen kẽ

        # Cấu hình cột
        headers = [
            "Phòng ban", "Xét nghiệm", "Level", "Lần chạy cuối",
            "Hạn kế tiếp", "Trạng thái", "Tần suất", "Khóa nhập"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # Resize mode
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Cột Test Name giãn hết cỡ

        layout.addWidget(self.table)

        # Double click để sửa
        if self.can_edit:
            self.table.doubleClicked.connect(self._open_config_dialog)

        # Connect Filter Signal
        self.cb_dep.currentIndexChanged.connect(self._load_data)

    def _load_departments(self):
        self.cb_dep.blockSignals(True)
        self.cb_dep.clear()
        self.cb_dep.addItem("— Tất cả —", None)
        try:
            deps = self.dept_service.list_departments(active_only=True)
            for d in deps:
                self.cb_dep.addItem(d.name, d.id)
        except:
            pass
        self.cb_dep.blockSignals(False)

    def _load_data(self):
        """Tải dữ liệu và tính toán trạng thái."""
        dep_id = self.cb_dep.currentData()
        self.table.setRowCount(0)

        # Lấy danh sách phòng ban cần load
        if dep_id:
            target_deps = [d for d in self.dept_service.list_departments() if d.id == dep_id]
        else:
            target_deps = self.dept_service.list_departments(active_only=True)

        today = dt.date.today()
        row_idx = 0

        for dep in target_deps:
            try:
                tests = self.dept_service.list_tests_by_department(dep.id)
            except:
                continue

            for test in tests:
                for level in [1, 2, 3]:
                    # Tính toán trạng thái lock/due
                    status, next_due_str, is_locked = self.sched_service.compute_lock_status(
                        department_id=dep.id, device_id=None, test_code=test.test_name, level=level, today=today
                    )

                    # Lấy config hiện tại
                    sched_row = self.sched_service.get_schedule(
                        department_id=dep.id, device_id=None, test_code=test.test_name, level=level
                    )

                    self.table.insertRow(row_idx)

                    # 1. Dept
                    self.table.setItem(row_idx, 0, QTableWidgetItem(dep.name))

                    # 2. Test Name (Lưu data ẩn để dùng cho dialog)
                    item_test = QTableWidgetItem(test.test_name)

                    # [FIX QT6] Sử dụng Qt.ItemDataRole.UserRole
                    item_test.setData(Qt.ItemDataRole.UserRole, {
                        "dep_id": dep.id, "test_code": test.test_name, "level": level,
                        "sched_data": {
                            "freq": sched_row.freq if sched_row else "daily",
                            "every_n": sched_row.every_n if sched_row else 1,
                            "grace_days": sched_row.grace_days if sched_row else 0,
                            "hard_lock": sched_row.hard_lock if sched_row else 0
                        }
                    })
                    self.table.setItem(row_idx, 1, item_test)

                    # 3. Level
                    self.table.setItem(row_idx, 2, QTableWidgetItem(f"L{level}"))

                    # 4. Last Run
                    last_run = sched_row.last_run if sched_row else "Chưa chạy"
                    self.table.setItem(row_idx, 3, QTableWidgetItem(str(last_run)))

                    # 5. Next Due
                    self.table.setItem(row_idx, 4, QTableWidgetItem(str(next_due_str or "Hôm nay")))

                    # 6. Status Badge (Widget) - Giao diện hiện đại
                    # Thay vì tô màu nền, ta dùng Badge (Thẻ)
                    status_widget = self._create_status_badge(status, is_locked)
                    self.table.setCellWidget(row_idx, 5, status_widget)

                    # 7. Frequency
                    freq_vn = {"daily": "Hàng ngày", "weekly": "Hàng tuần", "monthly": "Hàng tháng",
                               "ndays": "Mỗi N ngày"}
                    f_val = sched_row.freq if sched_row else "daily"
                    self.table.setItem(row_idx, 6, QTableWidgetItem(freq_vn.get(f_val, f_val)))

                    # 8. Lock Status
                    # Kiểm tra xem có đang bị khóa thực sự không (do quá hạn + hard_lock)
                    is_effectively_locked = (is_locked or (sched_row and sched_row.hard_lock and status == 'overdue'))

                    if is_effectively_locked:
                        # Dùng icon Close (Đỏ) cho trạng thái Khóa
                        icon = FIF.CLOSE.icon()
                        text = " Đã khóa"
                    else:
                        # Dùng icon Accept (Xanh) cho trạng thái Mở
                        icon = FIF.ACCEPT.icon()
                        text = " Mở"

                    item_lock = QTableWidgetItem(icon, text)
                    self.table.setItem(row_idx, 7, item_lock)

                    row_idx += 1

        self.table.resizeColumnsToContents()
        self._filter_table_client_side()

    def _create_status_badge(self, status, is_locked):
        """Tạo badge trạng thái đẹp mắt thay cho việc tô màu dòng"""
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(5, 2, 5, 2)
        lay.setAlignment(Qt.AlignCenter)

        if status == 'ok':
            # Màu xanh lá
            badge = InfoBadge.success("Còn hạn")
        elif status == 'due':
            # Màu vàng cam
            badge = InfoBadge.warning("Đến hạn")
        elif status == 'overdue':
            # Màu đỏ
            txt = "Đã khóa" if is_locked else "Quá hạn"
            badge = InfoBadge.error(txt)
        else:
            badge = InfoBadge.info("N/A")

        lay.addWidget(badge)
        return container

    def _filter_table_client_side(self):
        term = self.txt_search.text().lower().strip()
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 1)  # Cột Test Name
            if item:
                txt = item.text().lower()
                self.table.setRowHidden(r, term not in txt)

    def _open_config_dialog(self):
        if not self.can_edit: return

        # Lấy dòng đang chọn
        row = self.table.currentRow()
        if row < 0: return

        # Lấy data ẩn từ cột Test Name (cột 1)
        item = self.table.item(row, 1)
        if not item: return

        # [FIX QT6]
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data: return

        # Mở Dialog cấu hình (Fluent Version)
        dlg = IQCScheduleConfigDialog(
            self,
            test_name=data["test_code"],
            level=data["level"],
            current_data=data["sched_data"]
        )

        if dlg.exec():
            cfg = dlg.get_values()

            # Logic Save (Áp dụng cho 1 level hoặc tất cả)
            levels_to_update = [1, 2, 3] if cfg["apply_all_levels"] else [data["level"]]

            try:
                for lvl in levels_to_update:
                    self.sched_service.upsert(
                        department_id=data["dep_id"],
                        device_id=None,
                        test_code=data["test_code"],
                        level=lvl,
                        freq=cfg["freq"],
                        every_n=cfg["every_n"],
                        grace_days=cfg["grace_days"],
                        hard_lock=cfg["hard_lock"],
                        note=f"FluentUpdate: {cfg['apply_all_levels']}"
                    )

                InfoBar.success("Thành công", "Đã cập nhật cấu hình lịch thành công.", parent=self)
                self._load_data()  # Reload table
            except Exception as e:
                InfoBar.error("Lỗi", str(e), parent=self)