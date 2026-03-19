# -*- coding: utf-8 -*-
"""
app/core/updater.py
Lõi kiểm tra và tải bản cập nhật ngầm bằng QThread (Bản có Áo giáp chống File rác)
"""
import os
import sys
import subprocess
import requests
from packaging import version
from PySide6.QtCore import QThread, Signal
from app.core.path_manager import PathManager

# ⚠️ LINK ĐẾN FILE version.json CỦA BẠN (Phải là link RAW)
UPDATE_URL = "https://raw.githubusercontent.com/hunghung92992/update-QC/refs/heads/main/version.json"
CURRENT_VERSION = "1.0.0"


class UpdateCheckerThread(QThread):
    result_ready = Signal(dict)
    error_occurred = Signal(str)

    def run(self):
        try:
            response = requests.get(UPDATE_URL, timeout=5)
            response.raise_for_status()
            data = response.json()

            latest_version = data.get("version", "1.0.0")

            if version.parse(latest_version) > version.parse(CURRENT_VERSION):
                self.result_ready.emit(data)
            else:
                self.result_ready.emit({})

        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadUpdateThread(QThread):
    progress_updated = Signal(int)
    download_complete = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

        # Mượn thư mục gốc từ đường dẫn Database để lưu file
        app_dir = os.path.dirname(PathManager.get_db_path())
        self.save_path = os.path.join(app_dir, "QCLabManager_Update.exe")

    def run(self):
        try:
            # allow_redirects=True giúp đi theo link ẩn của GitHub/Drive
            response = requests.get(self.download_url, stream=True, timeout=15, allow_redirects=True)
            response.raise_for_status()

            # 🛡️ ÁO GIÁP 1: KIỂM TRA XEM CÓ PHẢI ĐANG TẢI TRANG WEB KHÔNG?
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                raise Exception(
                    "Đường link tải về là một trang web, KHÔNG PHẢI file cài đặt .exe! Hãy kiểm tra lại link.")

            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024  # 1MB
            downloaded = 0

            with open(self.save_path, 'wb') as file:
                for data in response.iter_content(block_size):
                    file.write(data)
                    downloaded += len(data)
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        self.progress_updated.emit(progress)

            # 🛡️ ÁO GIÁP 2: KIỂM TRA DUNG LƯỢNG FILE SAU KHI TẢI
            file_size = os.path.getsize(self.save_path)
            if file_size < 2000000:  # Nếu file nhỏ hơn 2MB
                os.remove(self.save_path)  # Xóa ngay file rác
                raise Exception(f"File tải về quá nhỏ ({file_size / 1024:.0f} KB). Đây là file rác/hỏng do link sai!")

            # Nếu qua được 2 ải trên, file chắc chắn là phần mềm thật!
            self.download_complete.emit(self.save_path)

        except Exception as e:
            self.error_occurred.emit(str(e))


def execute_installer(installer_path):
    """Mở file cài đặt và thoát phần mềm hiện tại"""
    if os.path.exists(installer_path):
        try:
            # Tạm thời TẮT chế độ /SILENT để bạn nhìn thấy giao diện Setup bằng mắt thường
            subprocess.Popen([installer_path])
            sys.exit(0)
        except Exception as e:
            print(f"❌ Không thể khởi chạy file Setup: {e}")