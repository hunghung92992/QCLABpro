# -*- coding: utf-8 -*-
import sys
import pathlib

# Ép đường dẫn gốc
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.auth_service import AuthService


def fix_admin_password():
    auth = AuthService()
    user = auth.get_user_by_username("admin")

    if user:
        # Tự động tạo mã Hash mới chuẩn 100% với máy tính của bạn
        res = auth.reset_password(user['id'], "admin")
        if res['ok']:
            print("✅ BÙM! Đã reset mật khẩu admin thành chữ: admin")

            # Test thử luôn cho chắc ăn
            test_login = auth.authenticate_user("admin", "admin")
            print(f"👉 Test đăng nhập lại: {test_login['reason']}")
        else:
            print(f"❌ Lỗi khi reset: {res}")
    else:
        print("❌ Không tìm thấy tài khoản admin")


if __name__ == "__main__":
    fix_admin_password()