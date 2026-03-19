# -*- coding: utf-8 -*-
"""
app/core/constants.py
(Ported từ constants.py)
Các hằng số dùng chung trong hệ thống.
"""

# Mật khẩu mặc định cho user mới và khi đặt lại mật khẩu
DEFAULT_PASSWORD = "XN123456@"

# Tên role chuẩn
ROLE_SUPERADMIN = "SUPERADMIN"
ROLE_QA = "QA"
ROLE_TRUONG_KHOA = "TRUONG_KHOA"
ROLE_KTV = "KTV"
ROLE_VIEWER = "VIEWER"

# Danh sách roles hiển thị trong combobox UI
ALL_ROLES = [
    ROLE_SUPERADMIN,
    ROLE_QA,
    ROLE_TRUONG_KHOA,
    ROLE_KTV,
    ROLE_VIEWER
]