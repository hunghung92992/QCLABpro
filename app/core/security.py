# -*- coding: utf-8 -*-
import subprocess
import hashlib
import os
from app.core.path_manager import PathManager

# ⚠️ QUAN TRỌNG: Đây là "Chìa khóa sinh tử" của bạn.
# Tuyệt đối không tiết lộ chuỗi này cho ai. Nếu họ biết, họ có thể tự tạo Key!
SECRET_SALT = "QCLabManager_Pro_2026_@NguyenHung_!#$"

def get_hardware_id():
    """Lấy mã Serial Number vật lý của ổ cứng (Không bị thay đổi khi cài lại Win)"""
    try:
        # Chạy lệnh wmic của Windows để lấy Serial ổ cứng
        output = subprocess.check_output("wmic diskdrive get serialnumber", shell=True).decode()
        # Bóc tách dữ liệu
        lines = [line.strip() for line in output.strip().split('\n') if line.strip()]
        if len(lines) > 1:
            serial = lines[1] # Lấy serial của ổ đĩa đầu tiên
            return serial
    except Exception:
        pass
    return "UNKNOWN_HWID_12345"

def generate_license_key(hwid):
    """Tạo mã bản quyền (Key) dựa trên Mã máy (HWID) và Secret Salt"""
    raw_key = f"{hwid}_{SECRET_SALT}"
    # Băm SHA-256 mã này ra thành chuỗi dài
    full_hash = hashlib.sha256(raw_key.encode()).hexdigest().upper()
    # Cắt lấy 20 ký tự, định dạng thành xxxx-xxxx-xxxx-xxxx cho đẹp mắt
    key = f"{full_hash[:5]}-{full_hash[5:10]}-{full_hash[10:15]}-{full_hash[15:20]}"
    return key

def verify_license(input_key):
    """Kiểm tra Key nhập vào có khớp với máy hiện tại không"""
    if not input_key:
        return False
    hwid = get_hardware_id()
    expected_key = generate_license_key(hwid)
    return input_key.strip() == expected_key

# --- Quản lý File lưu Key ---
def get_key_file_path():
    """Lưu file key vào thư mục Local AppData để không bị mất khi Update App"""
    # Lấy thư mục gốc (AppData/Local/QCLabManager) từ đường dẫn Database
    app_dir = os.path.dirname(PathManager.get_db_path())
    return os.path.join(app_dir, "license.key")

def load_saved_key():
    """Đọc key đã lưu trong máy"""
    path = get_key_file_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_key(key):
    """Lưu key xuống máy tính khách hàng sau khi kích hoạt thành công"""
    path = get_key_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(key.strip())