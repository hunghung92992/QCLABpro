# -*- coding: utf-8 -*-
"""
app/services/sync_manager.py
Orchestration: Quản lý luồng chạy ngầm (QThread) và điều phối SyncService.
Hoàn thiện Phase 2.3 (Phân vai) & Phase 4.1 (Dừng Thread an toàn tuyệt đối).
"""
import logging
from PySide6.QtCore import QThread, Signal

from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)


class SyncManager(QThread):
    # Các tín hiệu (Signals) bắn ra để UI cập nhật
    sync_started = Signal()
    sync_finished = Signal(bool, str)  # (Success, Message)
    sync_progress = Signal(str)  # Log realtime cho giao diện
    sync_stats = Signal(int, int)  # (Pushed Count, Pulled Count)

    def __init__(self, parent=None, interval_seconds=30):
        super().__init__(parent)
        self.interval = interval_seconds
        self._is_running = False
        self.sync_service = SyncService()

    def run(self):
        """Vòng lặp vĩnh cửu chạy ngầm, gọi mỗi X giây."""
        self._is_running = True
        logger.info(f"🔄 [SyncManager] Thread đã khởi động (Chu kỳ {self.interval}s).")

        # [PHASE 4.1]: Dùng isInterruptionRequested() chuẩn của QThread
        while self._is_running and not self.isInterruptionRequested():
            self.sync_started.emit()
            self.sync_progress.emit("Đang kiểm tra kết nối API Server...")

            try:
                # 1. Thực hiện PUSH
                self.sync_progress.emit("Đang đẩy dữ liệu lên Server...")
                push_ok, push_count, push_errors = self.sync_service.push_changes()

                if self.isInterruptionRequested():
                    break  # Thoát ngay lập tức nếu có lệnh tắt App

                # 2. Thực hiện PULL
                self.sync_progress.emit("Đang lấy dữ liệu mới từ Server...")
                pull_ok, pull_count, pull_errors = self.sync_service.pull_changes()

                if self.isInterruptionRequested():
                    break  # Thoát ngay lập tức nếu có lệnh tắt App

                # Emit thống kê cho UI
                self.sync_stats.emit(push_count, pull_count)

                # Đánh giá tổng thể
                if push_ok and pull_ok:
                    msg = f"Hoàn tất! Đẩy: {push_count} | Kéo: {pull_count}"
                    self.sync_finished.emit(True, msg)
                else:
                    err_msg = "Lỗi "
                    if not push_ok: err_msg += f"Push: {push_errors} "
                    if not pull_ok: err_msg += f"Pull: {pull_errors}"
                    self.sync_finished.emit(False, err_msg)

            except Exception as e:
                logger.error(f"❌ [SyncManager] Crash Exception: {e}")
                self.sync_finished.emit(False, f"Lỗi nghiêm trọng: {e}")

            # Nghỉ ngơi chờ chu kỳ tiếp theo (Chia nhỏ thời gian ngủ)
            for _ in range(self.interval):
                if (not self._is_running) or self.isInterruptionRequested():
                    break
                # [PHASE 4.1]: Dùng msleep của Qt thay vì time.sleep để không bị block event loop
                self.msleep(1000)

        logger.info("🛑 [SyncManager] Thread đã dừng hoàn toàn.")

    def stop(self, timeout_ms: int = 2500):
        """Phase 4.1: Dừng QThread an toàn chuẩn mực."""
        logger.info("⏳ [SyncManager] Nhận lệnh dừng. Đang đợi luồng đồng bộ kết thúc...")
        self._is_running = False

        # 1. Bật cờ ngắt luồng nội bộ của Qt
        self.requestInterruption()
        # 2. Ngừng event loop (nếu có)
        self.quit()

        # 3. Chờ tối đa timeout_ms (VD: 2.5 giây) để luồng tự thoát
        if not self.wait(timeout_ms):
            # Nếu hết 2.5 giây mà API vẫn đang treo, buộc phải tiêu diệt (Last resort)
            logger.warning("⚠️ [SyncManager] Luồng không tự dừng kịp, tiến hành terminate() (Last resort).")
            self.terminate()
            self.wait(1000)