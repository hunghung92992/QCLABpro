# -*- coding: utf-8 -*-
"""
main.py (Win 11 Fluent Version)
M6 FINALIZED: Integrated LIS Workers, Parsers, Auto-Services, Bootstrap & Compiled Resources
Phase 9: Tích hợp hệ thống khóa bản quyền theo phần cứng (Hardware-based License Key)
"""
import sys
import os
import traceback
import ctypes
import datetime as dt
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QIcon

# [PHASE 4.2 KHẮC PHỤC LỖI ICON] Nạp file resources đã được biên dịch từ resources.qrc
try:
    import app.resources_rc
except ImportError:
    pass

# Tắt mọi cảnh báo rác của Qt
os.environ[
    "QT_LOGGING_RULES"] = "qt.qpa.drawing=false;qt.stylesheet=false;qt.styleSheet.warning=false;qt.svg.warning=false"

# 1. IMPORT THEO CẤU TRÚC PATH MANAGER MỚI
from app.core.path_manager import PathManager
from app.core.logger import setup_logger
from app.core.backup_manager import perform_backup

# Khởi tạo thư mục và Logger
PathManager.ensure_structure()
logger = setup_logger()

# Import giao diện từ qfluentwidgets
from qfluentwidgets import (
    setTheme, Theme, SubtitleLabel, LineEdit, BodyLabel,
    InfoBar, InfoBarPosition, PushButton, PrimaryPushButton
)

# 🌟 IMPORT MODULE BẢO MẬT (Chắc chắn bạn đã tạo file app/core/security.py)
try:
    from app.core.security import get_hardware_id, load_saved_key, verify_license, save_key
except ImportError:
    logger.warning("⚠️ Không tìm thấy app.core.security. Bỏ qua kiểm tra bản quyền.")


    def verify_license(k):
        return True


    def load_saved_key():
        return ""


    def get_hardware_id():
        return "UNKNOWN"


    def save_key(k):
        pass

# Khai báo App ID để Windows không gom nhóm Icon
try:
    myappid = 'nguyenhung.qclabmanager.pro.1.0.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


def resource_path(relative_path):
    """ Lấy đường dẫn tuyệt đối cho assets """
    base_path = str(PathManager.get_project_root())
    return os.path.join(base_path, relative_path)


def exception_hook(exctype, value, tb):
    """ Bắt lỗi crash toàn cục và ghi log """
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"CRITICAL ERROR: {value}\n{error_msg}")

    if QApplication.instance():
        QMessageBox.critical(None, "Lỗi Hệ Thống", f"Ứng dụng đã dừng đột ngột:\n{value}")
    sys.exit(1)


# =====================================================================
# HỘP THOẠI YÊU CẦU KÍCH HOẠT (BẢN QUYỀN) - ĐÃ FIX LỖI NONE TYPE
# =====================================================================
class LicenseDialog(QDialog):
    def __init__(self, hwid, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kích hoạt bản quyền phần mềm")
        self.setFixedSize(450, 280)  # Kích thước cửa sổ độc lập
        self.hwid = hwid

        # Nạp Icon ứng dụng cho cửa sổ cấp quyền
        app_icon_path = resource_path(os.path.join("app", "assets", "logo.ico"))
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))

        # Layout chính
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(24, 24, 24, 24)
        self.vbox.setSpacing(15)

        # Tiêu đề
        self.lbl_title = SubtitleLabel("Khóa Bản Quyền (License Key)", self)
        self.vbox.addWidget(self.lbl_title)

        # Hiển thị Mã Máy
        self.lbl_hwid = BodyLabel("Mã máy của bạn (Hãy copy và gửi cho Nhà cung cấp):")
        self.txt_hwid = LineEdit()
        self.txt_hwid.setText(self.hwid)
        self.txt_hwid.setReadOnly(True)
        self.vbox.addWidget(self.lbl_hwid)
        self.vbox.addWidget(self.txt_hwid)

        # Ô nhập Key
        self.lbl_key = BodyLabel("Nhập Mã Kích Hoạt:")
        self.txt_key = LineEdit()
        self.txt_key.setPlaceholderText("VD: A1B2C-D3E4F-G5H6I-J7K8L")
        self.vbox.addWidget(self.lbl_key)
        self.vbox.addWidget(self.txt_key)

        self.vbox.addStretch(1)

        # Nút bấm (Nằm ngang dưới cùng)
        self.hbox = QHBoxLayout()
        self.btn_ok = PrimaryPushButton("Kích hoạt ngay")
        self.btn_cancel = PushButton("Thoát phần mềm")

        self.hbox.addStretch(1)
        self.hbox.addWidget(self.btn_ok)
        self.hbox.addWidget(self.btn_cancel)
        self.vbox.addLayout(self.hbox)

        # Kết nối sự kiện click
        self.btn_ok.clicked.connect(self.validate)
        self.btn_cancel.clicked.connect(self.reject)  # Reject sẽ trả về False cho dialog.exec()

    def validate(self):
        """Kiểm tra key khi khách hàng bấm nút Kích hoạt"""
        input_key = self.txt_key.text().strip()
        if verify_license(input_key):
            save_key(input_key)
            InfoBar.success("Thành công", "Cảm ơn bạn đã sử dụng phiên bản bản quyền!", parent=self, duration=3000)
            self.accept()  # Chấp nhận và đóng hộp thoại (trả về True)
        else:
            self.txt_key.setError(True)
            InfoBar.error("Lỗi kích hoạt", "Mã kích hoạt không hợp lệ cho máy tính này!", parent=self,
                          position=InfoBarPosition.TOP)


def main():
    sys.excepthook = exception_hook

    # Cấu hình DPI cho màn hình độ phân giải cao
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("QC Lab Manager")

    # Nạp Icon ứng dụng chính
    app_icon_path = resource_path(os.path.join("app", "assets", "logo.ico"))
    app.setWindowIcon(QIcon(app_icon_path))

    # Áp dụng Fluent Theme
    setTheme(Theme.AUTO)

    # 🛑 KIỂM TRA BẢN QUYỀN TRƯỚC KHI CHẠY APP
    saved_key = load_saved_key()
    if not verify_license(saved_key):
        hwid = get_hardware_id()
        dialog = LicenseDialog(hwid)
        if not dialog.exec():
            # Nếu người dùng bấm "Thoát" hoặc đóng cửa sổ -> Tắt luôn ứng dụng
            logger.warning("Thoát ứng dụng do không kích hoạt bản quyền.")
            sys.exit(0)

    # --- PHẦN IMPORT TRỄ (Lazy Import) ---
    from app.ui.views.auth.login_page import FluentLoginWindow
    from app.ui.main_window import MainWindow

    # Import các Service lõi của LIS M6
    from app.services.iqc_service import IQCService
    from app.services.device_service import DeviceService
    from app.integration.device_worker_service import DeviceWorkerService
    from app.integration.parsers.lis_parser_service import LisParserService

    # 3. GỌI BOOTSTRAP TẠO DB/SEED DỮ LIỆU
    from app.core.bootstrap import run_bootstrap
    try:
        run_bootstrap()
    except Exception as e:
        logger.error(f"Bootstrap failed: {e}")
        QMessageBox.critical(None, "Lỗi Database", "Không thể khởi tạo cơ sở dữ liệu.")
        return 1

    # 4. Khởi tạo Login và Quản lý Service
    login_window = FluentLoginWindow()
    windows = {"main": None}

    lis_services = {
        "worker_manager": None,
        "parser_manager": None
    }

    def show_main_window(user_data):
        try:
            # A. Khởi tạo Giao diện chính
            mw = MainWindow(user_data)
            windows["main"] = mw
            mw.show()

            # 5. FIX LỖI THOÁT APP: Dùng .hide() thay vì .close()
            login_window.hide()

            # B. Kích hoạt Hệ thống LIS M6
            logger.info("🤖 Đang khởi động hệ thống tự động hóa LIS...")

            try:
                # Khởi tạo các Service phụ thuộc
                iqc_svc = IQCService()
                dev_svc = DeviceService()

                # Chạy LisParser
                parser = LisParserService(iqc_svc, dev_svc)
                parser.start(poll_interval=10)
                lis_services["parser_manager"] = parser

                # Chạy DeviceWorkers
                worker_manager = DeviceWorkerService(dev_svc)
                worker_manager.start_workers()
                lis_services["worker_manager"] = worker_manager

                logger.info("✅ LIS Workers & Parser đã sẵn sàng!")

            except Exception as lis_err:
                logger.error(f"LIS Startup Error: {lis_err}")

        except Exception as e:
            logger.error(f"Main Window Init Error: {e}")
            QMessageBox.critical(None, "Lỗi Giao Diện", f"Không thể mở trang chủ: {e}")

    login_window.loginSuccess.connect(show_main_window)
    login_window.show()

    # --- BẢO HIỂM MỨC APP: CHẶN MỌI QTHREAD TREO ---
    def on_about_to_quit():
        logger.info("🧹 Đang dọn dẹp bộ nhớ và các luồng UI con...")
        mw = windows.get("main")
        if mw:
            for attr_name in dir(mw):
                try:
                    attr = getattr(mw, attr_name)
                    # Ép tắt nếu là QThread đang chạy ngầm
                    if isinstance(attr, QThread) and attr.isRunning():
                        logger.info(f"⏳ Ép dừng luồng mồ côi: {attr_name}")
                        attr.requestInterruption()
                        attr.quit()
                        attr.wait(1500)
                except Exception:
                    pass

    app.aboutToQuit.connect(on_about_to_quit)

    # --- THỰC THI VÒNG LẶP SỰ KIỆN ---
    exit_code = app.exec()

    # --- DỌN DẸP KHI THOÁT ---
    try:
        logger.info("Đang dừng các dịch vụ LIS...")
        if lis_services["worker_manager"]:
            lis_services["worker_manager"].stop_workers()

        if lis_services["parser_manager"]:
            lis_services["parser_manager"].stop()

        logger.info("Ứng dụng đang đóng... Bắt đầu tiến trình Auto-Backup.")
        perform_backup()
    except Exception as e:
        logger.error(f"Cleanup/Backup failed during exit: {e}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()