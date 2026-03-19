# -*- coding: utf-8 -*-
"""
app/core/path_manager.py
Quản lý đường dẫn tập trung chuẩn Enterprise (BL-001).
Đảm bảo tuân thủ cơ chế Sandbox: Tách biệt mã nguồn (Read-only) và Dữ liệu (Writable).
"""
import sys
import os
import shutil
import logging
from pathlib import Path

# Cấu hình logger cơ bản cho path_manager
logger = logging.getLogger(__name__)

# Tên ứng dụng đồng nhất cho toàn hệ thống
APP_NAME = "QCLabManager"

class PathManager:
    @classmethod
    def get_project_root(cls) -> Path:
        """
        Xác định thư mục gốc chứa mã nguồn hoặc tài nguyên đóng gói.
        [QUAN TRỌNG]: Xử lý chuẩn xác cơ chế _MEIPASS của PyInstaller.
        """
        if getattr(sys, 'frozen', False):
            # Chạy từ PyInstaller .exe -> Tài nguyên nằm trong _MEIPASS
            return Path(sys._MEIPASS)
        else:
            # Chạy từ mã nguồn .py: app/core/path_manager.py -> lùi 3 cấp
            return Path(__file__).resolve().parent.parent.parent

    @classmethod
    def get_app_data_dir(cls) -> Path:
        """
        Vùng lưu trữ dữ liệu hệ thống (AppData/Local).
        Không bị xóa khi user dọn dẹp Document, tránh lỗi quyền ghi.
        """
        if sys.platform == "win32":
            base = os.getenv('LOCALAPPDATA')
            if not base:
                base = str(Path.home() / 'AppData' / 'Local')
            app_dir = Path(base) / APP_NAME
        else:
            app_dir = Path.home() / '.local' / 'share' / APP_NAME

        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir

    @classmethod
    def get_user_documents_dir(cls) -> Path:
        """
        Vùng lưu trữ dữ liệu người dùng có thể tương tác (PDF, Backup, Excel).
        """
        doc_dir = Path.home() / 'Documents' / APP_NAME
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir

    @classmethod
    def _migrate_file(cls, filename: str) -> str:
        """
        Logic BL-002: Hợp nhất đường dẫn và tự động di trú file mẫu.
        Nếu file chưa tồn tại ở AppData, copy từ thư mục gốc cài đặt sang.
        """
        target_path = cls.get_app_data_dir() / filename

        # Nếu file chưa có trong AppData (lần đầu chạy hoặc bị xóa)
        if not target_path.exists():
            source_path = cls.get_project_root() / filename

            if source_path.exists():
                try:
                    # Copy kèm metadata để giữ nguyên timestamp
                    shutil.copy2(source_path, target_path)
                    logger.info(f"📦 [MIGRATION] Đã chuyển file mẫu {filename} vào AppData.")
                except Exception as e:
                    logger.error(f"⚠️ [MIGRATION ERROR] Lỗi copy {filename}: {e}")
            else:
                pass # Để SQLAlchemy/Config tự khởi tạo nếu không có file mẫu

        return str(target_path)

    # ==========================================
    # PUBLIC API: TRUY XUẤT ĐƯỜNG DẪN (BL-001 & BL-002)
    # ==========================================


    @classmethod
    def get_db_path(cls) -> str:
        db_name = f"Datauser{os.extsep}db"
        return cls._migrate_file(db_name)

    @classmethod

    def get_config_path(cls) -> str:
        return cls._migrate_file(f"config{os.extsep}json")

    @classmethod
    def get_sync_state_path(cls) -> str:
        """File trạng thái đồng bộ (Internal data)"""
        return str(cls.get_app_data_dir() / "sync_state.json")

    @classmethod
    def get_log_dir(cls) -> str:
        """Thư mục Logs (AppData/Local)"""
        log_dir = cls.get_app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return str(log_dir)

    @classmethod
    def get_backup_dir(cls) -> str:
        """Thư mục Backups (Documents)"""
        backup_dir = cls.get_user_documents_dir() / "Backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return str(backup_dir)

    @classmethod
    def get_reports_dir(cls) -> str:
        """Thư mục xuất báo cáo (Documents)"""
        reports_dir = cls.get_user_documents_dir() / "Reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        return str(reports_dir)

    @classmethod
    def get_attachments_dir(cls) -> str:
        """Thư mục file đính kèm (Documents)"""
        attachments_dir = cls.get_user_documents_dir() / "Attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)
        return str(attachments_dir)

    @classmethod
    def get_asset_path(cls, filename: str) -> str:
        """Đường dẫn an toàn để lấy Icon, Ảnh, Font chữ từ thư mục assets"""
        return str(cls.get_project_root() / "app" / "assets" / filename)

    @classmethod
    def ensure_structure(cls):
        """Hàm khởi tạo toàn bộ cấu trúc thư mục khi App bắt đầu chạy."""
        cls.get_app_data_dir()
        cls.get_user_documents_dir()
        cls.get_log_dir()
        cls.get_backup_dir()
        cls.get_reports_dir()
        cls.get_attachments_dir()