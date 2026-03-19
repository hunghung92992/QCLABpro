# -*- coding: utf-8 -*-
"""
app/core/logger.py
Hệ thống Logging tập trung chuẩn Enterprise (BL-005).
Hỗ trợ Rotating Logs, Bảo mật dữ liệu nhạy cảm và truy vết lỗi chi tiết.
"""
import logging
import os
import re
from logging.handlers import RotatingFileHandler

from app.core.path_manager import PathManager
# Import Path Manager để lấy đường dẫn log chuẩn (BL-001)
try:
    from app.core.path_manager import get_log_dir
except ImportError:
    def get_log_dir():
        d = os.path.join(os.getcwd(), "logs")
        os.makedirs(d, exist_ok=True)
        return d

# --- CẤU HÌNH ---

LOG_DIR = PathManager.get_log_dir()
LOG_FILE_PATH = os.path.join(LOG_DIR, f"app{os.extsep}log")
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5  # Giữ lại 5 file cũ (tăng từ 3 lên 5 để an toàn hơn)


class SensitiveDataFilter(logging.Filter):
    """
    Bộ lọc bảo mật: Tự động ẩn mật khẩu/token trong log trước khi ghi xuống đĩa.
    """

    def filter(self, record):
        msg = str(record.msg)
        # Regex tìm các cụm nhạy cảm như password, token, secret
        patterns = [
            r"(password['\"]?\s*[:=]\s*['\"]?)([^'\",\s]+)",
            r"(token['\"]?\s*[:=]\s*['\"]?)([^'\",\s]+)",
            r"(server_password['\"]?\s*[:=]\s*['\"]?)([^'\",\s]+)"
        ]
        for pattern in patterns:
            msg = re.sub(pattern, r"\1******", msg, flags=re.IGNORECASE)
        record.msg = msg
        return True


def setup_logger():
    """Thiết lập cấu hình logging toàn cục cho Root Logger."""

    # Sử dụng Root Logger để bắt được log từ các thư viện khác (SQLAlchemy, Requests...)
    root_logger = logging.getLogger()

    # Nếu đã cấu hình rồi thì bỏ qua (tránh lặp log)
    if root_logger.hasHandlers():
        return root_logger

    root_logger.setLevel(logging.DEBUG)

    # 1. Handler ghi file (Xoay vòng + UTF-8)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        # Định dạng chi tiết cho file: [Thời gian] [Level] [Module:Dòng] Nội dung
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)-8s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ [LOGGER] Lỗi khởi tạo file log tại {LOG_FILE_PATH}: {e}")

    # 2. Handler Console (Dành cho Dev)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Màu sắc hoặc định dạng đơn giản cho Console
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)

    logging.info(f"🚀 LOGGING START | PATH: {LOG_FILE_PATH}")
    return root_logger


# Khởi tạo instance duy nhất
logger = setup_logger()