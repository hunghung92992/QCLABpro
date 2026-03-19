# -*- coding: utf-8 -*-
"""
seed_admin.py
Script chạy MỘT LẦN để khởi tạo tài khoản SUPERADMIN.
"""

import sys
import os
import sqlite3

# Thêm thư mục gốc vào sys.path để có thể import 'app'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from app.services.auth_service import AuthService
    from app.core.constants import DEFAULT_PASSWORD, ROLE_SUPERADMIN
    from app.core.database_orm import get_db_connection
except ImportError as e:
    print(f"LỖI: Không thể import. Hãy đảm bảo bạn chạy file này từ thư mục gốc QC_Manager_v3/")
    print(f"Chi tiết lỗi: {e}")
    sys.exit(1)


def check_database():
    """Kiểm tra xem CSDL và bảng users_ex đã tồn tại chưa."""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1 FROM users_ex LIMIT 1")
        return True
    except sqlite3.OperationalError:
        print("LỖI: Bảng 'users_ex' không tồn tại.")
        print("Vui lòng chạy file migration '001_init_schema.sql' trước.")
        return False
    except Exception as e:
        print(f"LỖI kết nối CSDL: {e}")
        return False


def seed_admin_user():
    """Khởi tạo tài khoản admin."""

    print("Đang kiểm tra CSDL...")
    if not check_database():
        return

    auth_service = AuthService()

    admin_username = "admin"

    # 1. Kiểm tra xem 'admin' đã tồn tại chưa
    print(f"Kiểm tra tài khoản '{admin_username}'...")
    existing_user = auth_service.get_user_by_username(admin_username)

    if existing_user:
        print(f"Tài khoản '{admin_username}' đã tồn tại. Bỏ qua.")
        return

    # 2. Nếu chưa tồn tại, tạo mới
    print(f"Tài khoản '{admin_username}' không tồn tại. Đang tạo...")

    result = auth_service.create_user(
        username=admin_username,
        fullname="Quản trị viên Hệ thống",
        role=ROLE_SUPERADMIN,
        department="IT/Admin",
        is_active=True
    )

    if result["ok"]:
        print("---")
        print("TẠO ADMIN THÀNH CÔNG!")
        print(f"Tài khoản: {admin_username}")
        print(f"Mật khẩu: {DEFAULT_PASSWORD}")
        print("---")
    else:
        print(f"LỖI: Không thể tạo admin: {result['reason']}")


if __name__ == "__main__":
    seed_admin_user()