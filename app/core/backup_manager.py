# -*- coding: utf-8 -*-
"""
app/core/backup_manager.py
Tự động sao lưu Database SQLite (BL-006).
Tích hợp kiểm tra tính toàn vẹn và dọn dẹp định kỳ.
"""
import os
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from app.core.config import cfg
from app.core.path_manager import PathManager

# Sử dụng logger đã thiết lập ở BL-005
logger = logging.getLogger(__name__)


def validate_db_integrity(db_path: str) -> bool:
    """Kiểm tra file SQLite có hợp lệ không trước khi backup"""
    if not os.path.exists(db_path):
        return False
    try:
        # Kiểm tra nhanh bằng PRAGMA integrity_check
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        return result[0] == "ok"
    except Exception as e:
        logger.error(f"⚠️ [INTEGRITY] File DB có dấu hiệu hỏng: {e}")
        return False


def perform_backup():
    """Thực hiện quy trình sao lưu Database"""

    # 1. Kiểm tra cấu hình auto_backup
    if not cfg.get("auto_backup", True):
        logger.info("ℹ️ [BACKUP] Tự động sao lưu đang tắt trong cấu hình.")
        return

    # 2. Xác định file nguồn (Sử dụng Path Manager làm Source of Truth)
    # Lấy từ Config trước, nếu không có thì lấy mặc định từ AppData
    source_path = cfg.get("db_path") or PathManager.get_db_path()

    if not os.path.exists(source_path):
        logger.error(f"❌ [BACKUP] Thất bại: Không tìm thấy DB tại {source_path}")
        return

    # 3. Kiểm tra tính toàn vẹn trước khi backup
    if not validate_db_integrity(source_path):
        logger.warning("⚠️ [BACKUP] Hủy sao lưu do file DB nguồn không vượt qua bài kiểm tra toàn vẹn.")
        return

    # 4. Xác định thư mục đích (Documents/QCLabManager/Backups)
    backup_folder = PathManager.get_backup_dir()

    # 5. Tạo tên file kèm timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_filename = f"Datauser_{timestamp}.bak"
    target_path = os.path.join(backup_folder, target_filename)

    try:
        # Copy file kèm metadata (shutil.copy2)
        shutil.copy2(source_path, target_path)

        logger.info(f"✅ [BACKUP] Thành công: {target_filename}")

        # 6. Dọn dẹp các bản sao lưu cũ (Giữ lại 10 bản gần nhất)
        _cleanup_old_backups(backup_folder, max_files=10)

    except Exception as e:
        logger.error(f"❌ [BACKUP] Lỗi hệ thống khi copy: {e}")


def _cleanup_old_backups(backup_dir, max_files=10):
    """Xóa bỏ các file backup cũ để tiết kiệm dung lượng ổ cứng"""
    try:
        # Lấy danh sách các file .bak
        path = Path(backup_dir)
        files = list(path.glob("*.bak"))

        # Sắp xếp theo thời gian sửa đổi (cũ nhất đứng đầu)
        files.sort(key=os.path.getmtime)

        if len(files) > max_files:
            files_to_delete = files[:-max_files]
            for f in files_to_delete:
                f.unlink()  # Xóa file
                logger.debug(f"🧹 [CLEANUP] Đã xóa bản sao lưu cũ: {f.name}")

    except Exception as e:
        logger.error(f"⚠️ [CLEANUP] Lỗi khi dọn dẹp backup: {e}")