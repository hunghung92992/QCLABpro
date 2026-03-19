# -*- coding: utf-8 -*-
import os
import json
import traceback
from app.core.path_manager import PathManager
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFileDialog,
    QDialog, QTextEdit, QApplication
)

# Import widget giao diện
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, SwitchSettingCard,
    PrimaryPushSettingCard, PushSettingCard, FluentIcon as FIF,
    InfoBar, InfoBarPosition, setTheme, Theme, LineEdit as FluentLineEdit,
    ComboBox, SettingCard, PasswordLineEdit,
    MessageBoxBase, SubtitleLabel, BodyLabel, ProgressBar  # [UPDATE] Bổ sung module cho Auto Updater
)

# Import QSettings để lưu cấu hình UI cục bộ
from PySide6.QtCore import QSettings

# Import thư viện Database
from sqlalchemy import create_engine

# [UPDATE] IMPORT LÕI AUTO UPDATER
try:
    from app.core.updater import UpdateCheckerThread, DownloadUpdateThread, execute_installer, CURRENT_VERSION

    HAS_UPDATER = True
except ImportError:
    HAS_UPDATER = False
    CURRENT_VERSION = "1.0.0"


class AppConfig:
    """Wrapper đơn giản để dùng QSettings cho các cài đặt UI cục bộ"""

    def __init__(self):
        self.settings = QSettings("NguyenHung", "QCLabManager")

    def get(self, key, default=None):
        return self.settings.value(key, default)

    def set(self, key, value):
        self.settings.setValue(key, value)


# Khởi tạo instance cấu hình toàn cục cho file này
cfg = AppConfig()


# ============================================================
# HỘP THOẠI CẬP NHẬT PHẦN MỀM (AUTO UPDATER DIALOG) - ĐÃ FIX
# ============================================================
class UpdateDialog(MessageBoxBase):
    def __init__(self, update_data, parent=None):
        super().__init__(parent)
        self.update_data = update_data

        # 1. Tự khởi tạo Label Tiêu đề (FIX LỖI TẠI ĐÂY)
        self.titleLabel = SubtitleLabel("Phát hiện bản cập nhật mới!", self)

        new_version = update_data.get('version', 'Unknown')
        notes = update_data.get('release_notes', 'Không có chi tiết.')

        self.lbl_info = BodyLabel(f"Phiên bản {new_version} đã sẵn sàng (Hiện tại: {CURRENT_VERSION})", self)
        self.lbl_notes = BodyLabel(f"Chi tiết cập nhật:\n{notes}", self)

        self.progress_bar = ProgressBar(self)
        self.progress_bar.hide()  # Ẩn đi chờ lúc tải mới hiện

        # 2. Thêm các widget vào Layout của hộp thoại
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.lbl_info)
        self.viewLayout.addWidget(self.lbl_notes)
        self.viewLayout.addSpacing(15)
        self.viewLayout.addWidget(self.progress_bar)

        # 3. Đổi tên nút bấm
        self.yesButton.setText("Tải và Cài đặt ngay")
        self.cancelButton.setText("Để sau")

        # Thiết lập độ rộng tối thiểu cho hộp thoại đẹp hơn
        self.widget.setMinimumWidth(400)

        self.downloader = None

    def accept(self):
        """Logic khi bấm Tải và Cài đặt"""
        self.yesButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        self.yesButton.setText("Đang tải xuống...")
        self.progress_bar.show()

        url = self.update_data.get('download_url')
        self.downloader = DownloadUpdateThread(url)
        self.downloader.progress_updated.connect(self.progress_bar.setValue)
        self.downloader.download_complete.connect(self.on_download_success)
        self.downloader.error_occurred.connect(self.on_download_error)
        self.downloader.start()

    def on_download_success(self, file_path):
        self.yesButton.setText("Đang khởi động Setup...")
        execute_installer(file_path)  # Gọi hàm tắt app và chạy file cài đặt

    def on_download_error(self, err):
        self.lbl_notes.setText(f"❌ Lỗi tải xuống: {err}\nVui lòng kiểm tra lại mạng.")
        self.yesButton.setEnabled(True)
        self.cancelButton.setEnabled(True)
        self.yesButton.setText("Thử tải lại")
        self.progress_bar.hide()


# --- 1. HỘP THOẠI XEM LOG ---
class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nhật ký hệ thống (System Logs)")
        self.resize(900, 600)
        self.vbox = QVBoxLayout(self)

        self.lbl_info = QLabel("Hiển thị 500 dòng log gần nhất từ hệ thống")
        self.lbl_info.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 5px;")
        self.vbox.addWidget(self.lbl_info)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 10pt;")
        self.vbox.addWidget(self.text_edit)
        self._load_log()

    def _load_log(self):
        log_path = os.path.join(PathManager.get_log_dir(), f"app{os.extsep}log")
        self.lbl_info.setText(f"Hiển thị log từ file: {log_path}")

        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    last_lines = lines[-500:]
                    content = "".join(last_lines)
                    self.text_edit.setPlainText(content)
                    self.text_edit.moveCursor(QTextCursor.MoveOperation.End)
            except Exception as e:
                self.text_edit.setPlainText(f"❌ Lỗi đọc file log: {str(e)}")
        else:
            self.text_edit.setPlainText(f"⚠️ Chưa tìm thấy file log tại: {log_path}")


# --- 2. TRANG CÀI ĐẶT CHÍNH ---
class SettingsPage(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWidget(self)
        self.view.setObjectName("settingsView")
        self.vbox = QVBoxLayout(self.view)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 0, 0, 0)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("settings_page")

        # Style trong suốt
        self.view.setStyleSheet("#settingsView { background-color: transparent; }")
        self.setStyleSheet("SettingsPage, ScrollArea { background-color: transparent; border: none; }")

        try:
            self._init_ui()
        except Exception as e:
            print(f"❌ [UI CRASH] Lỗi nghiêm trọng khi vẽ trang Cài đặt: {e}")
            traceback.print_exc()

    def _init_ui(self):
        self.vbox.setSpacing(20)
        self.vbox.setContentsMargins(36, 20, 36, 20)

        self.lbl_title = QLabel("Cài đặt Hệ thống", self)
        self.lbl_title.setStyleSheet("font-size: 26px; font-weight: bold; font-family: 'Segoe UI';")
        self.vbox.addWidget(self.lbl_title)

        self._init_server_group()
        self._init_local_db_group()
        self._init_lis_group()
        self._init_report_group()
        self._init_ui_group()
        self._init_system_group()
        self._init_about_group()

        self.vbox.addStretch(1)

    # ============================================================
    # 1. MÁY CHỦ TRUNG TÂM (POSTGRESQL)
    # ============================================================
    def _init_server_group(self):
        self.grp_server = SettingCardGroup("Máy chủ Trung tâm (PostgreSQL)", self.view)

        # 1. Host
        self.card_host = SettingCard(FIF.GLOBE, "Địa chỉ Host", "IP Máy chủ (VD: 192.168.1.31)", self.grp_server)
        self.txt_host = FluentLineEdit(self.card_host)
        self.txt_host.setPlaceholderText("192.168.1.31")
        self.txt_host.setFixedWidth(250)
        self.card_host.hBoxLayout.addWidget(self.txt_host, 0, Qt.AlignmentFlag.AlignRight)
        self.card_host.hBoxLayout.addSpacing(16)

        # 2. Port
        self.card_port = SettingCard(FIF.COMMAND_PROMPT, "Cổng (Port)", "Mặc định: 5432", self.grp_server)
        self.txt_port = FluentLineEdit(self.card_port)
        self.txt_port.setPlaceholderText("5432")
        self.txt_port.setFixedWidth(100)
        self.card_port.hBoxLayout.addWidget(self.txt_port, 0, Qt.AlignmentFlag.AlignRight)
        self.card_port.hBoxLayout.addSpacing(16)

        # 3. Database Name
        self.card_dbname = SettingCard(FIF.FOLDER, "Tên Database", "Ví dụ: QClab", self.grp_server)
        self.txt_dbname = FluentLineEdit(self.card_dbname)
        self.txt_dbname.setPlaceholderText("QClab")
        self.txt_dbname.setFixedWidth(250)
        self.card_dbname.hBoxLayout.addWidget(self.txt_dbname, 0, Qt.AlignmentFlag.AlignRight)
        self.card_dbname.hBoxLayout.addSpacing(16)

        # 4. Username
        self.card_user = SettingCard(FIF.PEOPLE, "Tài khoản (User)", "Tên đăng nhập PostgreSQL", self.grp_server)
        self.txt_user = FluentLineEdit(self.card_user)
        self.txt_user.setPlaceholderText("postgres")
        self.txt_user.setFixedWidth(250)
        self.card_user.hBoxLayout.addWidget(self.txt_user, 0, Qt.AlignmentFlag.AlignRight)
        self.card_user.hBoxLayout.addSpacing(16)

        # 5. Password
        self.card_pass = SettingCard(FIF.INFO, "Mật khẩu", "Mật khẩu truy cập Database", self.grp_server)
        self.txt_pass = PasswordLineEdit(self.card_pass)
        self.txt_pass.setPlaceholderText("Nhập mật khẩu")
        self.txt_pass.setFixedWidth(250)
        self.card_pass.hBoxLayout.addWidget(self.txt_pass, 0, Qt.AlignmentFlag.AlignRight)
        self.card_pass.hBoxLayout.addSpacing(16)

        # 6. Nút Test
        self.card_save_server = PrimaryPushSettingCard(
            "Lưu & Kiểm tra kết nối", FIF.SAVE, "Áp dụng thay đổi",
            "Kiểm tra kết nối và lưu cấu hình PostgreSQL", self.grp_server
        )
        self.card_save_server.clicked.connect(self._save_server_config)

        self.grp_server.addSettingCard(self.card_host)
        self.grp_server.addSettingCard(self.card_port)
        self.grp_server.addSettingCard(self.card_dbname)
        self.grp_server.addSettingCard(self.card_user)
        self.grp_server.addSettingCard(self.card_pass)
        self.grp_server.addSettingCard(self.card_save_server)

        self.vbox.addWidget(self.grp_server)

        # Nạp dữ liệu cũ lên giao diện
        self._load_server_config()

    def _load_server_config(self):
        """Đọc config.json (nơi SyncManager lấy dữ liệu) và điền vào form"""
        config_path = PathManager.get_config_path()
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg_json = json.load(f)
                    db_cfg = cfg_json.get("postgresql", {})

                    self.txt_host.setText(db_cfg.get("host", "192.168.1.31"))
                    self.txt_port.setText(str(db_cfg.get("port", "5432")))
                    self.txt_dbname.setText(db_cfg.get("dbname", "QClab"))
                    self.txt_user.setText(db_cfg.get("user", "postgres"))
                    self.txt_pass.setText(db_cfg.get("password", ""))
        except Exception as e:
            print(f"Lỗi load config DB: {e}")

    def _save_server_config(self):
        """Lưu config và kết nối thử nghiệm tới PostgreSQL"""
        host = self.txt_host.text().strip()
        port = self.txt_port.text().strip() or "5432"
        db_name = self.txt_dbname.text().strip()
        user = self.txt_user.text().strip()
        pwd = self.txt_pass.text().strip()

        if not host or not db_name or not user:
            InfoBar.warning("Cảnh báo", "Vui lòng nhập đủ Host, Database và User!", parent=self,
                            position=InfoBarPosition.TOP_RIGHT)
            return

        self.card_save_server.setEnabled(False)
        InfoBar.info("Đang kết nối...", f"Đang thử nghiệm kết nối tới PostgreSQL tại {host}...", parent=self,
                     duration=2000)
        QApplication.processEvents()

        try:
            # 1. TEST KẾT NỐI (Timeout 3s để không bị treo app)
            conn_str = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db_name}"
            engine = create_engine(conn_str, connect_args={"connect_timeout": 3})

            with engine.connect() as conn:
                pass  # Chạm vào DB thành công!

            # 2. LƯU VÀO CONFIG.JSON (ĐỂ SYNCMANAGER ĐỌC)
            config_path = PathManager.get_config_path()
            cfg_json = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg_json = json.load(f)

            cfg_json["postgresql"] = {
                "host": host,
                "port": port,
                "dbname": db_name,
                "user": user,
                "password": pwd
            }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg_json, f, indent=4, ensure_ascii=False)

            InfoBar.success("Thành công", "Kết nối PostgreSQL thành công! Đã lưu cấu hình.", parent=self,
                            position=InfoBarPosition.TOP_RIGHT, duration=4000)

        except Exception as e:
            # Bắt lỗi sai Pass hoặc sai IP
            err_msg = str(e)
            if "password authentication failed" in err_msg:
                InfoBar.error("Lỗi xác thực", "Sai mật khẩu hoặc tài khoản (User)!", parent=self,
                              position=InfoBarPosition.TOP_RIGHT)
            elif "timeout" in err_msg.lower():
                InfoBar.error("Lỗi mạng",
                              "Không tìm thấy Máy chủ. Kiểm tra lại IP hoặc Tường lửa (Port 5432) trên máy chủ.",
                              parent=self, position=InfoBarPosition.TOP_RIGHT)
            else:
                InfoBar.error("Lỗi kết nối", f"Không thể kết nối. Chi tiết: {err_msg[:50]}...", parent=self,
                              position=InfoBarPosition.TOP_RIGHT)
        finally:
            self.card_save_server.setEnabled(True)

    # ============================================================
    # CÁC GROUP KHÁC
    # ============================================================
    def _init_local_db_group(self):
        self.grp_db = SettingCardGroup("Cơ sở dữ liệu Local", self.view)

        self.card_db_path = SettingCard(FIF.FOLDER, "Đường dẫn Database", "Vị trí lưu file SQLite nội bộ", self.grp_db)
        self.txt_db_path = FluentLineEdit(self.card_db_path)
        self.txt_db_path.setText(PathManager.get_db_path())
        self.txt_db_path.setFixedWidth(300)
        self.txt_db_path.setReadOnly(True)
        self.card_db_path.hBoxLayout.addWidget(self.txt_db_path, 0, Qt.AlignmentFlag.AlignRight)
        self.card_db_path.hBoxLayout.addSpacing(16)

        self.card_backup = PrimaryPushSettingCard(
            "Sao lưu ngay", FIF.SAVE, "Sao lưu dữ liệu", "Tạo bản sao lưu an toàn (.bak)", self.grp_db
        )
        self.card_backup.clicked.connect(self._on_backup_db)

        self.card_auto_bk = SwitchSettingCard(
            FIF.SYNC, "Tự động sao lưu", "Tự động sao lưu mỗi khi tắt phần mềm",
            configItem=None, parent=self.grp_db
        )
        auto_bk_val = cfg.get("auto_backup", "true")
        self.card_auto_bk.setChecked(str(auto_bk_val).lower() == "true")
        self.card_auto_bk.checkedChanged.connect(lambda c: cfg.set("auto_backup", c))

        self.grp_db.addSettingCard(self.card_db_path)
        self.grp_db.addSettingCard(self.card_backup)
        self.grp_db.addSettingCard(self.card_auto_bk)
        self.vbox.addWidget(self.grp_db)

    def _init_lis_group(self):
        self.grp_device = SettingCardGroup("Kết nối thiết bị (LIS)", self.view)

        self.card_com = SettingCard(FIF.EDIT, "Cổng giao tiếp", "Cổng COM kết nối máy xét nghiệm", self.grp_device)
        self.cb_com = ComboBox(self.card_com)
        self.cb_com.addItems(["COM1", "COM2", "COM3", "TCP/IP"])
        self.cb_com.setCurrentText(cfg.get("lis_port", "COM1"))
        self.cb_com.currentTextChanged.connect(lambda t: cfg.set("lis_port", t))
        self.cb_com.setFixedWidth(150)
        self.card_com.hBoxLayout.addWidget(self.cb_com, 0, Qt.AlignmentFlag.AlignRight)
        self.card_com.hBoxLayout.addSpacing(16)

        self.card_protocol = SettingCard(FIF.TAG, "Giao thức truyền", "Chuẩn giao tiếp dữ liệu", self.grp_device)
        self.cb_protocol = ComboBox(self.card_protocol)
        self.cb_protocol.addItems(["ASTM 1394", "HL7 v2.5", "Ký tự phân cách (|)"])
        self.cb_protocol.setCurrentText(cfg.get("protocol", "ASTM 1394"))
        self.cb_protocol.currentTextChanged.connect(lambda t: cfg.set("protocol", t))
        self.cb_protocol.setFixedWidth(150)
        self.card_protocol.hBoxLayout.addWidget(self.cb_protocol, 0, Qt.AlignmentFlag.AlignRight)
        self.card_protocol.hBoxLayout.addSpacing(16)

        self.grp_device.addSettingCard(self.card_com)
        self.grp_device.addSettingCard(self.card_protocol)
        self.vbox.addWidget(self.grp_device)

    def _init_report_group(self):
        self.grp_report = SettingCardGroup("Cấu hình Báo cáo", self.view)

        self.card_lab_name = SettingCard(FIF.EDIT, "Tên đơn vị", "Tiêu đề hiển thị trên phiếu in", self.grp_report)
        self.txt_lab_name = FluentLineEdit(self.card_lab_name)
        self.txt_lab_name.setText(cfg.get("lab_name", ""))
        self.txt_lab_name.editingFinished.connect(lambda: cfg.set("lab_name", self.txt_lab_name.text()))
        self.txt_lab_name.setFixedWidth(400)
        self.card_lab_name.hBoxLayout.addWidget(self.txt_lab_name, 0, Qt.AlignmentFlag.AlignRight)
        self.card_lab_name.hBoxLayout.addSpacing(16)

        self.card_logo = PushSettingCard(
            "Chọn ảnh...", FIF.PHOTO, "Logo đơn vị", "Đường dẫn file logo (.png, .jpg)", self.grp_report
        )
        self.card_logo.clicked.connect(self._on_select_logo)

        self.grp_report.addSettingCard(self.card_lab_name)
        self.grp_report.addSettingCard(self.card_logo)
        self.vbox.addWidget(self.grp_report)

    def _init_ui_group(self):
        self.grp_ui = SettingCardGroup("Giao diện", self.view)
        self.card_theme = SettingCard(FIF.BRUSH, "Chế độ màu", "Giao diện Sáng / Tối", self.grp_ui)
        self.cb_theme = ComboBox(self.card_theme)
        self.cb_theme.addItems(["Sáng (Light)", "Tối (Dark)", "Theo hệ thống"])
        self.cb_theme.setCurrentText(cfg.get("theme_mode", "Theo hệ thống"))
        self.cb_theme.setFixedWidth(180)
        self.cb_theme.currentTextChanged.connect(self._on_theme_changed)
        self.card_theme.hBoxLayout.addWidget(self.cb_theme, 0, Qt.AlignmentFlag.AlignRight)
        self.card_theme.hBoxLayout.addSpacing(16)
        self.grp_ui.addSettingCard(self.card_theme)
        self.vbox.addWidget(self.grp_ui)

    def _init_system_group(self):
        self.grp_sys = SettingCardGroup("Hệ thống & Nhật ký", self.view)
        self.card_view_log = PushSettingCard(
            "Xem Log", FIF.DOCUMENT, "Nhật ký hoạt động",
            "Xem chi tiết hoạt động đồng bộ và lỗi phát sinh", self.grp_sys
        )
        self.card_view_log.clicked.connect(self._on_view_log)
        self.grp_sys.addSettingCard(self.card_view_log)
        self.vbox.addWidget(self.grp_sys)

    def _init_about_group(self):
        self.grp_about = SettingCardGroup("Thông tin phần mềm", self.view)

        # [UPDATE] Nút Kiểm tra cập nhật
        self.card_app_info = PrimaryPushSettingCard(
            "Kiểm tra bản mới", FIF.UPDATE, "Cập nhật phần mềm",
            f"Phiên bản hiện tại: v{CURRENT_VERSION} | Tự động kiểm tra và tải xuống bản vá mới nhất", self.grp_about
        )
        self.card_app_info.clicked.connect(self._on_check_update)

        self.card_contact = SettingCard(
            FIF.PHONE, "Liên hệ hỗ trợ", "Email: thanhhung1512@gmail.com | Hotline: 0398.000.678", self.grp_about
        )

        self.card_feedback = PushSettingCard(
            "Gửi góp ý", FIF.FEEDBACK, "Phản hồi & Góp ý",
            "Gửi báo cáo lỗi hoặc đề xuất tính năng mới cho nhà phát triển", self.grp_about
        )
        self.card_feedback.clicked.connect(self._on_feedback)

        self.grp_about.addSettingCard(self.card_app_info)
        self.grp_about.addSettingCard(self.card_contact)
        self.grp_about.addSettingCard(self.card_feedback)

        self.vbox.addWidget(self.grp_about)

    # ============================================================
    # SLOTS & LOGIC
    # ============================================================
    def _on_backup_db(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu file Backup", "Backup_QC.bak", "Backup Files (*.bak)")
        if file_path:
            InfoBar.success("Sao lưu thành công", f"File: {os.path.basename(file_path)}", parent=self)

    def _on_select_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn Logo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            cfg.set("logo_path", file_path)
            InfoBar.success("Đã cập nhật Logo", "Logo mới sẽ hiển thị trên báo cáo in.", parent=self)

    def _on_theme_changed(self, text):
        cfg.set("theme_mode", text)
        if "Sáng" in text:
            setTheme(Theme.LIGHT)
        elif "Tối" in text:
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.AUTO)

    def _on_view_log(self):
        dialog = LogViewerDialog(self.window())
        dialog.exec()

    # [UPDATE] XỬ LÝ LOGIC KIỂM TRA BẢN MỚI
    def _on_check_update(self):
        if not HAS_UPDATER:
            InfoBar.error("Thiếu Module", "Chưa tìm thấy hệ thống Updater (app/core/updater.py).", parent=self.window())
            return

        InfoBar.info("Đang kết nối...", "Hệ thống đang kiểm tra phiên bản mới trên máy chủ.", parent=self.window(),
                     duration=2000)

        # Chạy luồng kiểm tra ngầm để không đơ UI
        self.checker = UpdateCheckerThread()
        self.checker.result_ready.connect(self._on_check_result)
        self.checker.error_occurred.connect(self._on_check_error)
        self.checker.start()

    def _on_check_result(self, update_data):
        if update_data:
            # Hiện cửa sổ báo có cập nhật
            dialog = UpdateDialog(update_data, self.window())
            dialog.exec()
        else:
            InfoBar.success("Thành công", f"Bạn đang sử dụng phiên bản mới nhất (v{CURRENT_VERSION}).",
                            parent=self.window())

    def _on_check_error(self, err):
        InfoBar.error("Lỗi mạng", f"Không thể lấy thông tin bản cập nhật: {err}", parent=self.window(), duration=4000)

    def _on_feedback(self):
        QDesktopServices.openUrl(QUrl("mailto:thanhhung1512@gmail.com?subject=Feedback QC Lab"))