# -*- coding: utf-8 -*-
"""
app/core/migration_manager.py
Quản lý nâng cấp cấu trúc Database tự động.
"""
import sqlite3
import logging
from app.core.database_orm import get_db_connection

logger = logging.getLogger("QCManager")

# --- DANH SÁCH MIGRATION ---
# Key: Version ID (tăng dần)
# Value: List các câu lệnh SQL cần chạy
MIGRATIONS = {
    1: [
        """CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);""",
        """CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, fullname TEXT, department TEXT);""",
        """CREATE TABLE IF NOT EXISTS departments (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, code TEXT);""",
        # ... Thêm các bảng cơ bản khác nếu chưa có ...
    ],
    2: [
        # Ví dụ: Thêm bảng iqc_schedule_config (đã làm ở các bước trước, nhưng giờ chuẩn hóa vào đây)
        """CREATE TABLE IF NOT EXISTS iqc_schedule_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER, device_id INTEGER, test_code TEXT, level INTEGER,
            freq TEXT, every_n INTEGER, grace_days INTEGER, hard_lock INTEGER,
            last_run TEXT, start_date TEXT, end_date TEXT, due_date TEXT,
            lock_input INTEGER DEFAULT 0, note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"""
    ],
    # Sau này muốn thêm cột 'email' vào bảng users, chỉ cần thêm version 3:
    # 3: ["ALTER TABLE users ADD COLUMN email TEXT;"]
}

CURRENT_APP_VERSION = max(MIGRATIONS.keys())


class MigrationManager:
    def __init__(self):
        pass

    def _get_current_db_version(self, conn) -> int:
        """Lấy version hiện tại của file DB."""
        try:
            # Kiểm tra bảng schema_version có tồn tại không
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version';")
            if not cursor.fetchone():
                return 0  # Chưa có bảng version -> Database mới tinh hoặc rất cũ

            cursor = conn.execute("SELECT MAX(version) FROM schema_version;")
            row = cursor.fetchone()
            return row[0] if row[0] is not None else 0
        except Exception as e:
            logger.error(f"Lỗi kiểm tra version DB: {e}")
            return 0

    def run_migrations(self):
        """Chạy quy trình kiểm tra và nâng cấp DB."""
        logger.info("Đang kiểm tra Schema Database...")

        try:
            with get_db_connection() as conn:
                current_ver = self._get_current_db_version(conn)
                logger.info(f"Version DB hiện tại: {current_ver}. Version App: {CURRENT_APP_VERSION}")

                if current_ver < CURRENT_APP_VERSION:
                    for ver in range(current_ver + 1, CURRENT_APP_VERSION + 1):
                        logger.info(f"-> Đang nâng cấp lên Version {ver}...")
                        sqls = MIGRATIONS.get(ver, [])
                        for sql in sqls:
                            conn.execute(sql)

                        # Cập nhật version mới vào bảng
                        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (ver,))
                        conn.commit()
                        logger.info(f"-> Đã nâng cấp xong Version {ver}.")
                else:
                    logger.info("Database đã ở phiên bản mới nhất.")

        except sqlite3.Error as e:
            logger.critical(f"LỖI NGHIÊM TRỌNG KHI MIGRATION: {e}")
            # Trong thực tế có thể cần popup thông báo lỗi fatal
            raise e