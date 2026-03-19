# app/services/backup_service.py
import sqlite3
import shutil
import datetime as dt
import os
from app.core.database_orm import DB_PATH, get_db_connection


class BackupService:
    def create_backup(self, backup_dir="backups"):
        """
        Sao lưu nóng (Hot Backup) database ra file .bak
        """
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"qc_manager_backup_{timestamp}.sqlite"
        backup_path = os.path.join(backup_dir, filename)

        try:
            # Cách 1: Dùng API backup của SQLite (An toàn nhất)
            dest_conn = sqlite3.connect(backup_path)
            with get_db_connection() as source_conn:
                source_conn.backup(dest_conn)
            dest_conn.close()

            return True, backup_path

        except Exception as e:
            print(f"Lỗi backup: {e}")
            return False, str(e)

    def restore_backup(self, backup_path):
        """
        Khôi phục dữ liệu từ file backup.
        CẢNH BÁO: Hành động này sẽ ghi đè dữ liệu hiện tại.
        """
        try:
            # 1. Đóng mọi kết nối (Thực tế cần restart app)
            # 2. Copy file backup đè lên file chính
            shutil.copy2(backup_path, DB_PATH)
            return True, "Khôi phục thành công. Vui lòng khởi động lại ứng dụng."
        except Exception as e:
            return False, str(e)
