# -*- coding: utf-8 -*-
import sys
import pathlib

# Ép đường dẫn gốc
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.auth_service import AuthService
from app.core.database_orm import SessionLocal
from app.models.core_models import User


def check_db_direct():
    print("--- 1. KIỂM TRA TRỰC TIẾP DATABASE ---")
    db = SessionLocal()
    users = db.query(User).all()
    if not users:
        print("❌ Bảng User trong DB đang trống trơn!")
    else:
        for u in users:
            print(
                f"✅ Tìm thấy User: '{u.username}', active={getattr(u, 'active', getattr(u, 'is_active', 'Không có'))}, sync_flag={u.sync_flag}")
    db.close()


def test_auth_service():
    print("\n--- 2. KIỂM TRA QUA AUTH_SERVICE ---")
    auth = AuthService()

    user_data = auth.get_user_by_username("admin")
    print(f"👉 Dữ liệu lấy lên: {user_data}")

    if user_data:
        res = auth.authenticate_user("admin", "admin123")
        print(f"👉 Kết quả đăng nhập: {res}")
    else:
        print("❌ AuthService không lấy được dữ liệu của admin!")


if __name__ == "__main__":
    check_db_direct()
    test_auth_service()