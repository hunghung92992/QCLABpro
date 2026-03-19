# -*- coding: utf-8 -*-
"""
app/core/config.py
Module quản lý cấu hình tập trung (Core Config) - BL-001 & BL-002.
Đảm bảo mọi đường dẫn đều đi qua Path Manager để tránh lỗi quyền ghi trên Windows.
"""
import json
import os
import logging
from app.core.path_manager import PathManager
# [MỚI] Import Path Manager chuẩn hóa
try:
    from app.core.path_manager import (
        get_config_path,
        get_db_path,
        get_backup_dir,
        get_reports_dir,
        get_attachments_dir
    )
except ImportError:
    # Phòng hờ trường hợp môi trường dev chưa cấu hình đúng path
    def get_config_path():
        return PathManager.get_config_path()


    def get_db_path():
        return PathManager.get_db_path()


    def get_backup_dir():
        return "backups"


    def get_reports_dir():
        return "reports"


    def get_attachments_dir():
        return "attachments"

logger = logging.getLogger(__name__)

# Lấy đường dẫn file config từ AppData chuẩn (Source of Truth)
CONFIG_FILE = get_config_path()

# Cấu hình mặc định chuẩn Enterprise
DEFAULT_CONFIG = {
    # --- Cấu hình Local & Paths (BL-002) ---
    "db_path": PathManager.get_db_path(),
    "auto_backup": True,
    "backup_dir": get_backup_dir(),  # Lưu ở Documents
    "reports_dir": get_reports_dir(),  # Lưu ở Documents
    "attachments_dir": get_attachments_dir(),

    # --- Cấu hình Server (Sync Module) ---
    "server_host": "localhost",
    "server_port": "5432",
    "server_name": "QClab",
    "server_user": "postgres",
    "server_password": "encrypted_password_placeholder",  # Sẽ xử lý ở M3 (Security)

    # --- Cấu hình Thiết bị (LIS - BL-050) ---
    "lis_port": "COM3",
    "protocol": "ASTM 1394",
    "baud_rate": 9600,

    # --- Cấu hình Giao diện & Báo cáo ---
    "lab_name": "TRUNG TÂM Y TẾ KHU VỰC CẦN ĐƯỚC - KHOA XÉT NGHIỆM & CĐHA",
    "theme_mode": "System",  # Light, Dark, System
    "language": "vi_VN"
}


class AppConfig:
    def __init__(self):
        # Khởi tạo dữ liệu từ template mặc định
        self._data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Đọc file config.json và vá lỗi đường dẫn (Fix P0)"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    self._data.update(saved_data)

                # [FIX P0] CỰC KỲ QUAN TRỌNG:
                # Luôn ép buộc db_path và các thư mục hệ thống về đường dẫn chuẩn tuyệt đối.
                # Điều này ngăn lỗi khi user copy file config.json từ máy này sang máy khác
                # hoặc từ phiên bản cũ (vốn lưu đường dẫn tương đối).
                self._data["db_path"] = PathManager.get_db_path()
                self._data["backup_dir"] = get_backup_dir()
                self._data["reports_dir"] = get_reports_dir()
                self._data["attachments_dir"] = get_attachments_dir()

            except Exception as e:
                logger.error(f"⚠️ [CONFIG] Lỗi giải mã file config: {e}")
        else:
            # Lần đầu chạy, tạo file config mẫu tại AppData
            logger.info("🆕 [CONFIG] Khởi tạo file cấu hình lần đầu tại AppData.")
            self.save()

    def save(self):
        """Lưu cấu hình hiện tại xuống file config.json"""
        try:
            # Đảm bảo thư mục chứa file config tồn tại trước khi ghi
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ [CONFIG] Không thể lưu file: {e}")

    # --- Getter / Setter an toàn ---
    def get(self, key, default=None):
        """Truy xuất giá trị cấu hình"""
        return self._data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        """Cập nhật và lưu tự động"""
        self._data[key] = value
        self.save()

    @property
    def db_path(self) -> str:
        """Helper để lấy nhanh db_path dạng chuỗi tuyệt đối"""
        return str(self._data.get("db_path"))


# Khởi tạo instance duy nhất (Singleton)
cfg = AppConfig()