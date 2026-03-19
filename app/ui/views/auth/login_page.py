# -*- coding: utf-8 -*-
import sys
import base64  # Thêm thư viện mã hóa
from PySide6.QtCore import Qt, Signal, QSettings  # Thêm QSettings
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon

# --- IMPORT FLUENT WIDGETS ---
from qfluentwidgets import (
    LineEdit, PasswordLineEdit, PrimaryPushButton,
    CheckBox, TitleLabel, BodyLabel, InfoBar, InfoBarPosition,
    FluentIcon as FIF, Action
)

# --- IMPORT AN TOÀN CHO LineEditButtonPosition ---
try:
    from qfluentwidgets import LineEditButtonPosition
except ImportError:
    try:
        from qfluentwidgets.components.widgets.line_edit import LineEditButtonPosition
    except ImportError:
        LineEditButtonPosition = None  # Fallback: Nếu không tìm thấy thì bỏ qua icon

from app.services.auth_service import AuthService
from app.services.audit_service import AuditService


class FluentLoginWindow(QWidget):
    loginSuccess = Signal(dict)  # Signal bắn ra khi login thành công

    def __init__(self):
        super().__init__()
        self.auth_service = AuthService()
        self.audit_service = AuditService()
        self.user_data = None

        self.setWindowTitle("Đăng nhập - Lab Manager")
        self.resize(400, 550)

        # Khởi tạo bộ nhớ tạm của hệ thống
        self.settings = QSettings("NguyenHung", "QCLabManager")

        # Setup UI
        self._init_ui()

        # Center window
        self._center()

        # Nạp thông tin tài khoản nếu người dùng đã chọn Ghi nhớ trước đó
        self._load_saved_credentials()

    def _init_ui(self):
        # Layout chính
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(40, 60, 40, 40)
        self.vbox.setSpacing(20)

        # 1. Header (Tiêu đề)
        self.lbl_title = TitleLabel("Xin chào!", self)
        self.lbl_sub = BodyLabel("Vui lòng đăng nhập để tiếp tục.", self)
        self.lbl_sub.setTextColor("#606060", "#d0d0d0")  # Màu xám nhạt

        self.vbox.addWidget(self.lbl_title, 0, Qt.AlignmentFlag.AlignHCenter)
        self.vbox.addWidget(self.lbl_sub, 0, Qt.AlignmentFlag.AlignHCenter)
        self.vbox.addSpacing(20)

        # 2. Form nhập liệu (Fluent Style)

        # --- Username ---
        self.txt_user = LineEdit(self)
        self.txt_user.setPlaceholderText("Tên đăng nhập")
        self.txt_user.setClearButtonEnabled(True)

        # Thêm Icon an toàn
        if LineEditButtonPosition:
            self.txt_user.addAction(Action(FIF.PEOPLE), LineEditButtonPosition.LEFT)

        # --- Password ---
        self.txt_pass = PasswordLineEdit(self)
        self.txt_pass.setPlaceholderText("Mật khẩu")

        # Thêm Icon an toàn
        if LineEditButtonPosition:
            self.txt_pass.addAction(Action(FIF.LOCK), LineEditButtonPosition.LEFT)

        self.vbox.addWidget(self.txt_user)
        self.vbox.addWidget(self.txt_pass)

        # 3. Tùy chọn (Remember me)
        self.chk_remember = CheckBox("Ghi nhớ đăng nhập", self)
        self.vbox.addWidget(self.chk_remember)

        self.vbox.addSpacing(10)

        # 4. Nút bấm (Primary = Màu xanh Win 11)
        self.btn_login = PrimaryPushButton("Đăng nhập", self)
        self.btn_login.clicked.connect(self._on_login)
        self.vbox.addWidget(self.btn_login)

        # Spacer để đẩy mọi thứ lên trên một chút
        self.vbox.addStretch(1)

        # 5. Footer
        self.lbl_ver = BodyLabel("QC Manager | @NguyễnHùng", self)
        self.lbl_ver.setTextColor("#909090", "#707070")
        self.vbox.addWidget(self.lbl_ver, 0, Qt.AlignmentFlag.AlignHCenter)

        # Sự kiện Enter
        self.txt_user.returnPressed.connect(self._on_login)
        self.txt_pass.returnPressed.connect(self._on_login)

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2,
                  (screen.height() - size.height()) // 2)

    # --- CÁC HÀM XỬ LÝ GHI NHỚ ĐĂNG NHẬP ---
    def _load_saved_credentials(self):
        """Đọc thông tin từ QSettings và điền vào UI"""
        remember = self.settings.value("login/remember", False, type=bool)
        self.chk_remember.setChecked(remember)

        if remember:
            saved_user = self.settings.value("login/username", "")
            saved_pass_b64 = self.settings.value("login/password", "")

            # Giải mã mật khẩu từ base64
            try:
                if saved_pass_b64:
                    saved_pass = base64.b64decode(saved_pass_b64.encode('utf-8')).decode('utf-8')
                else:
                    saved_pass = ""
            except Exception:
                saved_pass = ""

            self.txt_user.setText(saved_user)
            self.txt_pass.setText(saved_pass)

    def _save_credentials(self, username, password, remember):
        """Lưu hoặc xóa thông tin tùy thuộc vào CheckBox"""
        self.settings.setValue("login/remember", remember)
        if remember:
            self.settings.setValue("login/username", username)
            # Mã hóa base64 trước khi lưu
            pass_b64 = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            self.settings.setValue("login/password", pass_b64)
        else:
            # Xóa sạch nếu người dùng bỏ tick
            self.settings.remove("login/username")
            self.settings.remove("login/password")

    # ----------------------------------------

    def _on_login(self):
        username = self.txt_user.text().strip()
        password = self.txt_pass.text()
        remember = self.chk_remember.isChecked()

        if not username or not password:
            self._show_error("Vui lòng nhập đầy đủ thông tin.")
            return

        # Gọi Service kiểm tra xác thực
        res = self.auth_service.authenticate_user(username, password)

        if res["ok"]:
            self.user_data = res["user_data"]
            self.audit_service.log_action(username, "LOGIN_SUCCESS", "Win11_UI")

            # Lưu thông tin nếu đăng nhập thành công
            self._save_credentials(username, password, remember)

            # Emit signal để main.py mở giao diện chính
            self.loginSuccess.emit(self.user_data)
            self.close()
        else:
            self._show_error(f"Đăng nhập thất bại: {res['reason']}")
            self.audit_service.log_action(username, "LOGIN_FAIL", res['reason'])

    def _show_error(self, msg):
        InfoBar.error(
            title='Lỗi',
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )