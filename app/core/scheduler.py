# -*- coding: utf-8 -*-
import threading
import time
from app.services.sync_service import SyncService
from app.core.logger import logger


class AutoSyncWorker(threading.Thread):
    def __init__(self, interval_seconds=180):  # Đã chỉnh mặc định thành 180s (3 phút)
        super().__init__()
        self.interval = interval_seconds
        self.sync_service = SyncService()
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        """Dừng worker an toàn"""
        self._stop_event.set()

    def run(self):
        logger.info(f"🤖 AutoSyncWorker khởi động. Chu kỳ: {self.interval // 60} phút/lần.")

        # Đợi 10 giây ban đầu để hệ thống chính ổn định trước khi sync phát đầu tiên
        time.sleep(10)

        while not self._stop_event.is_set():
            try:
                # Kiểm tra kết nối Internet/Server
                if self.sync_service.check_connection():
                    logger.info("🔄 [AUTO] Đang thực hiện đồng bộ định kỳ (3 phút)...")

                    # Ưu tiên đẩy dữ liệu Local lên trước
                    success, pushed, push_errs = self.sync_service.push_changes()
                    if pushed > 0:
                        logger.info(f"✅ [AUTO] Đã đẩy {pushed} bản ghi lên.")

                    # Sau đó cập nhật dữ liệu mới từ Server về
                    pulled, pull_errs = self.sync_service.pull_changes()
                    if pulled > 0:
                        logger.info(f"✅ [AUTO] Đã tải {pulled} bản ghi về.")
                else:
                    logger.warning("⚠️ [AUTO] Không có kết nối tới Server. Sẽ thử lại sau.")

            except Exception as e:
                logger.error(f"❌ [AUTO SYNC ERROR] {e}")

            # Cơ chế ngủ thông minh: Ngủ từng giây một để có thể thoát ngay lập tức nếu App đóng
            for _ in range(self.interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

        logger.info("🛑 AutoSyncWorker đã dừng hẳn.")