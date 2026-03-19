# -*- coding: utf-8 -*-
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel

from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, CheckBox, ComboBox, LineEdit
)

# Danh sách các quyền tương ứng với Key hệ thống
# (Label hiển thị, Key định danh)
PERMISSIONS_MAP = [
    ("Tổng quan", "dashboard"),
    ("Kết quả nội kiểm (IQC)", "iqc"),
    ("Quản lý thiết bị", "device"),
    ("Nhật ký (Audit Log)", "log"),
    ("Quản lý người dùng", "user"),
    ("Quản lý mẫu QC (Catalog)", "catalog"),
    ("Chương trình ngoại kiểm (EQA)", "eqa"),
    ("Phân tích thống kê", "reports"),
    ("Cảnh báo", "alert"),
    ("Cài đặt", "settings"),
    ("Quản trị (Admin)", "admin_tab")  # Thêm cái này cho tab quản trị mới
]


class MenuPermissionDialog(MessageBoxBase):
    def __init__(self, user_data, auth_service, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.auth_service = auth_service
        self.user_id = user_data['id']

        # Tiêu đề
        self.titleLabel = SubtitleLabel("Tùy biến menu theo người dùng", self)

        # Setup UI
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(10)

        self._init_ui()
        self._load_current_permissions()

        # Cấu hình nút (Lưu / Đóng)
        self.yesButton.setText("Lưu")
        self.cancelButton.setText("Đóng")

        # Tăng độ rộng dialog
        self.widget.setMinimumWidth(500)

    def _init_ui(self):
        # 1. Hiển thị tên tài khoản đang sửa
        self.lbl_user = QLabel(f"Tài khoản đang chọn: {self.user_data.get('username')} ({self.user_data.get('role')})",
                               self)
        self.lbl_user.setStyleSheet("color: #666; font-weight: bold;")
        self.viewLayout.addWidget(self.lbl_user)
        self.viewLayout.addSpacing(15)

        # 2. Grid chứa các Checkbox
        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(15)
        self.grid.setHorizontalSpacing(30)

        self.checks = {}  # Lưu tham chiếu các checkbox

        # Tạo Checkbox theo map (2 cột)
        for idx, (label_text, key) in enumerate(PERMISSIONS_MAP):
            chk = CheckBox(label_text, self)
            row = idx // 2
            col = idx % 2
            self.grid.addWidget(chk, row, col)
            self.checks[key] = chk

        self.viewLayout.addLayout(self.grid)

    def _load_current_permissions(self):
        # Lấy chuỗi JSON từ DB (Giả sử key là 'access_control')
        access_str = self.user_data.get('access_control')

        if not access_str:
            # Mặc định chọn hết nếu chưa thiết lập
            for chk in self.checks.values():
                chk.setChecked(True)
            return

        try:
            perms = json.loads(access_str)
            for key, chk in self.checks.items():
                # Nếu key có trong json và là True -> check
                # Nếu key không có trong json -> mặc định True (cho an toàn)
                is_allowed = perms.get(key, True)
                chk.setChecked(bool(is_allowed))
        except:
            # Lỗi parse JSON -> Chọn hết
            for chk in self.checks.values():
                chk.setChecked(True)

    def validate(self):
        # Hàm này chạy khi bấm nút Lưu (Yes)
        # Gom dữ liệu từ checkbox thành dict
        new_perms = {}
        for key, chk in self.checks.items():
            new_perms[key] = 1 if chk.isChecked() else 0

        # Chuyển thành chuỗi JSON
        json_str = json.dumps(new_perms)

        # Gọi Service lưu vào DB
        # (Lưu ý: Bạn cần thêm hàm update_access_control vào AuthService)
        res = self.auth_service.update_user_access(self.user_id, json_str)

        if res:
            return True  # Đóng dialog
        else:
            return False  # Giữ dialog nếu lỗi