# -*- coding: utf-8 -*-
"""
app/features/auth/menu_visibility_dialog.py
(Ported từ admin_menu_visibility.py)
CẢI TIẾN: Chỉ gọi AuthService và MenuService.
(MỚI) Sửa lỗi NameError: QMessageBox và chuẩn hóa import.
"""

from __future__ import annotations

# (MỚI) Sửa lỗi: Import từ qt_compat và thêm QMessageBox
from app.utils.qt_compat import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QGridLayout, QMessageBox
)

from app.services.menu_service import MenuService, MENU_KEYS
from app.services.auth_service import AuthService

# Nhãn (labels) cho các khóa menu
LABELS = {
    "overview": "Tổng quan", "qc_sample": "Quản lý mẫu QC (Catalog)",
    "qc_result": "Kết quả nội kiểm (IQC)", "eqa": "Chương trình ngoại kiểm (EQA)",
    "devices": "Quản lý thiết bị", "reports": "Phân tích thống kê",
    "reports": "Nhật ký (Audit Log)", "alerts": "Cảnh báo",
    "users": "Quản lý người dùng", "settings": "Cài đặt"
}


class AdminMenuVisibilityDialog(QDialog):

    def __init__(self, parent=None, current_role: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Tùy biến menu theo người dùng (Admin)")

        self.auth_service = AuthService()
        self.menu_service = MenuService()

        v = QVBoxLayout(self)
        self.user_cb = QComboBox()
        v.addWidget(QLabel("Chọn tài khoản:"))
        v.addWidget(self.user_cb)

        grid = QGridLayout()
        self.checks = {}
        for i, key in enumerate(MENU_KEYS):
            cb = QCheckBox(LABELS.get(key, key))
            self.checks[key] = cb
            grid.addWidget(cb, i // 2, i % 2)
        v.addLayout(grid)

        btns = QHBoxLayout()
        bsave = QPushButton("Lưu")
        bclose = QPushButton("Đóng")
        bsave.clicked.connect(self.save)
        bclose.clicked.connect(self.close)
        btns.addWidget(bsave)
        btns.addWidget(bclose)
        v.addLayout(btns)

        self._load_users()
        self.user_cb.currentIndexChanged.connect(self._load_vis_for_user)

        # Tải lần đầu
        if self.user_cb.count():
            self._load_vis_for_user()

    def _load_users(self):
        # Gọi AuthService
        users = self.auth_service.list_users()

        self.user_cb.clear()
        for user in users:
            uname = user.get('username')
            role = user.get('role')
            self.user_cb.addItem(f"{uname} ({role or ''})", (uname, role))

    def _load_vis_for_user(self):
        data = self.user_cb.currentData()
        if not data: return

        uname, role = data

        # Gọi MenuService
        vis = self.menu_service.get_visibility_map(uname, role=role)

        for k, cb in self.checks.items():
            cb.setChecked(bool(vis.get(k, 1)))

    def save(self):
        data = self.user_cb.currentData()
        if not data: return

        uname, role = data
        vis = {k: (1 if cb.isChecked() else 0) for k, cb in self.checks.items()}

        # Gọi MenuService
        if self.menu_service.set_visibility(uname, vis):
            QMessageBox.information(self, "Thành công", f"Đã lưu phân quyền cho {uname}.")
        else:
            QMessageBox.warning(self, "Lỗi", "Không thể lưu phân quyền.")