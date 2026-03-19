# -*- coding: utf-8 -*-
import json
import traceback
import os
import sys
import importlib  # Thêm để hỗ trợ nạp module an toàn
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from app.core.path_manager import PathManager

# FIX LỖI ICON: Xử lý an toàn khi thiếu resources_rc
# Nạp resource tĩnh đã compile (Phase 4.2)
try:
    import app.resources_rc
except ImportError:
    pass

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon as FIF,
    SplashScreen, NavigationAvatarWidget,
    TransparentToolButton, InfoBar, InfoBarPosition,
    RoundMenu, Action, MessageBoxBase, PasswordLineEdit, SubtitleLabel,
    QConfig
)

# Khởi tạo cấu hình hệ thống
QConfig.initialized = True

# Import Services
# [ĐÃ SỬA]: Import SyncManager thay vì AutoSyncWorker cũ
from app.services.sync_manager import SyncManager
from app.core.backup_manager import perform_backup
from app.services.auth_service import AuthService


# ============================================================================
# --- FIX LỖI DATABASE ---
# ============================================================================
def check_database_existence():
    """Đảm bảo tìm đúng file DB để không hiện cảnh báo Demo sai chỗ"""
    db_path = PathManager.get_db_path()
    app_data_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'QCLabManager', db_path)
    local_path = os.path.join(os.getcwd(), db_path)

    target_db = app_data_path if os.path.exists(app_data_path) else local_path

    if os.path.exists(target_db):
        print(f"✅ Database thực tế được xác nhận tại: {target_db}")
        return True

    print(f"⚠️ Cảnh báo: Không thấy file {db_path}. Hệ thống có thể đang chạy với DB giả lập.")
    return False


IS_REAL_DB = check_database_existence()


# ============================================================================
# --- HÀM IMPORT AN TOÀN (NÂNG CẤP) ---
# ============================================================================
def safe_import(module_path, class_name):
    """Sử dụng importlib để nạp module chính xác hơn và bắt lỗi chi tiết"""
    try:
        if not module_path: return None
        # Nạp tươi module bằng importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except ModuleNotFoundError as e:
        print(f"❌ Lỗi Import: Không tìm thấy file tại [{module_path}]. Hãy đảm bảo đã có file __init__.py")
        return None
    except Exception as e:
        print(f"❌ Lỗi Cú Pháp/Logic trong file [{module_path}]: {e}")
        traceback.print_exc()
        return None


# Nạp các trang cơ bản
IQCMainTab = safe_import('app.ui.views.iqc.iqc_main_tab', 'IQCMainTab')
EQAMainTab = safe_import('app.ui.views.eqa.eqa_main_tab', 'EQAMainTab')
EventCalendarPage = safe_import('app.ui.views.calendar.event_calendar_page', 'EventCalendarPage')
CatalogMainPage = safe_import('app.ui.views.catalog.catalog_main_page', 'CatalogMainPage')
DeviceAdminPage = safe_import('app.ui.views.devices.device_admin_page', 'DeviceAdminPage')

# Thử nạp AuditLog
AuditLogViewPage = safe_import('app.ui.views.admin.audit_log_view_page', 'AuditLogViewPage')
if not AuditLogViewPage:
    AuditLogViewPage = safe_import('app.ui.views.admin.audit_log_page', 'AuditLogViewPage')

ReportPage = safe_import('app.ui.views.reports.report_page', 'ReportPage')
AlertsPage = safe_import('app.ui.views.alerts.alerts_page', 'AlertsPage')
OverviewPage = safe_import('app.ui.views.overview.overview_page', 'OverviewPage')
ManagementPage = safe_import('app.ui.views.admin.management_page', 'ManagementPage')
SettingsPage = safe_import('app.ui.views.settings.settings_page', 'SettingsPage')
CapaPage = safe_import('app.ui.views.capa.capa_page', 'CapaPage')


# ============================================================================
# DIALOG ĐỔI MẬT KHẨU
# ============================================================================
class ChangePasswordDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('Đổi mật khẩu', self)
        self.old_pw_input = PasswordLineEdit(self)
        self.old_pw_input.setPlaceholderText("Mật khẩu hiện tại")
        self.new_pw_input = PasswordLineEdit(self)
        self.new_pw_input.setPlaceholderText("Mật khẩu mới")
        self.confirm_pw_input = PasswordLineEdit(self)
        self.confirm_pw_input.setPlaceholderText("Xác nhận mật khẩu mới")

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.old_pw_input)
        self.viewLayout.addWidget(self.new_pw_input)
        self.viewLayout.addWidget(self.confirm_pw_input)
        self.widget.setMinimumWidth(320)

    def validate(self):
        if not self.old_pw_input.text() or not self.new_pw_input.text() or not self.confirm_pw_input.text():
            return (False, "Vui lòng nhập đầy đủ thông tin!")
        if self.new_pw_input.text() != self.confirm_pw_input.text():
            return (False, "Mật khẩu xác nhận không khớp!")
        if len(self.new_pw_input.text()) < 6:
            return (False, "Mật khẩu mới phải từ 6 ký tự trở lên!")
        return (True, "")


# ============================================================================
# MAIN WINDOW CLASS
# ============================================================================
class MainWindow(FluentWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.username = user_data.get('username', 'Admin')
        self.role = str(user_data.get('role', 'VIEWER')).upper()
        self.department = user_data.get('department', '')
        self.fullname = user_data.get('fullname', self.username)

        self.setWindowTitle(f"QC Lab Manager Pro - Xin chào: {self.fullname} ({self.role})")
        self.setMinimumSize(1024, 700)

        # Khởi tạo UI
        self._init_pages()
        self._init_navigation()
        self._setup_sync_ui()

        # [ĐÃ SỬA]: Khởi tạo SyncManager MỚI và bắt các tín hiệu chuẩn
        self.sync_thread = SyncManager(parent=self, interval_seconds=30)
        self.sync_thread.sync_started.connect(self._on_sync_started)
        self.sync_thread.sync_progress.connect(self._on_sync_progress)
        self.sync_thread.sync_finished.connect(self._on_sync_finished)

        # Tương thích ngược với OverviewPage nếu nó cần nhận status
        if hasattr(self, 'home_interface') and hasattr(self.home_interface, 'update_sync_status_ui'):
            self.sync_thread.sync_finished.connect(
                lambda ok, msg: self.home_interface.update_sync_status_ui(2 if ok else 3, msg)
            )

        self.sync_thread.start()
        self.showMaximized()

    def _init_pages(self):
        """Khởi tạo tất cả các trang với xử lý lỗi tập trung"""

        def init_widget(Class, name, *args, **kwargs):
            if not Class:
                return self._create_error_placeholder(f"Không tìm thấy module cho trang: {name}")
            try:
                return Class(*args, **kwargs)
            except Exception as e:
                print(f"❌ Lỗi khi khởi tạo [{name}]: {e}")
                return self._create_error_placeholder(f"Lỗi khởi tạo {name}")

        self.home_interface = init_widget(OverviewPage, "Tổng quan", parent=self)
        self.home_interface.setObjectName("home_interface")
        if hasattr(self.home_interface, 'request_navigation'):
            self.home_interface.request_navigation.connect(self.switch_to_interface_by_key)

        self.calendar_interface = init_widget(EventCalendarPage, "Lịch", parent=self)
        self.calendar_interface.setObjectName("calendar_interface")

        self.iqc_interface = init_widget(IQCMainTab, "IQC", self, self.username, self.role, self.department,
                                         self.fullname)
        self.iqc_interface.setObjectName("iqc_interface")

        self.eqa_interface = init_widget(EQAMainTab, "EQA", self.username, self.role, self.department)
        self.eqa_interface.setObjectName("eqa_interface")

        self.catalog_interface = init_widget(CatalogMainPage, "Danh mục", self.username, self.role, self.department)
        self.catalog_interface.setObjectName("catalog_interface")

        self.device_interface = init_widget(DeviceAdminPage, "Thiết bị", parent=self)
        self._inject_user_data(self.device_interface)
        self.device_interface.setObjectName("device_interface")

        self.capa_interface = init_widget(CapaPage, "CAPA", parent=self)
        self.capa_interface.setObjectName("capa_interface")

        self.alert_interface = init_widget(AlertsPage, "Cảnh báo", parent=self)
        self.alert_interface.setObjectName("alert_interface")

        self.report_interface = init_widget(ReportPage, "Báo cáo", parent=self, username=self.username)
        self.report_interface.setObjectName("report_interface")

        self.log_interface = init_widget(AuditLogViewPage, "Nhật ký", parent=self, username=self.username,
                                         role=self.role)
        self.log_interface.setObjectName("log_interface")

        self.admin_interface = init_widget(ManagementPage, "Quản trị", self.username, self.role, self)
        self.admin_interface.setObjectName("admin_interface")

        self.setting_interface = init_widget(SettingsPage, "Cài đặt", parent=self)
        self.setting_interface.setObjectName("setting_interface")

    def _create_error_placeholder(self, text):
        """Hiển thị thông báo lỗi trực quan trên UI"""
        w = QWidget()
        l = QVBoxLayout(w)
        lbl = QLabel(f"⚠️ {text}\n\n[Hệ thống vẫn chạy nhưng tính năng này tạm thời không khả dụng]")

        lbl.setStyleSheet("""
            QLabel {
                color: #D13438; 
                font-weight: bold; 
                background-color: #FFF4F4; 
                padding: 30px; 
                border: 2px solid #D13438; 
                border-radius: 12px;
                font-size: 14px;
            }
        """)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        l.addWidget(lbl)
        return w

    def _setup_sync_ui(self):
        self.btn_sync_status = TransparentToolButton(FIF.CLOUD, self)
        self.btn_sync_status.setCursor(Qt.PointingHandCursor)
        self.btn_sync_status.clicked.connect(self._force_sync)
        if hasattr(self, 'titleBar') and hasattr(self.titleBar, 'hBoxLayout'):
            self.titleBar.hBoxLayout.insertWidget(self.titleBar.hBoxLayout.count(), self.btn_sync_status, 0,
                                                  Qt.AlignmentFlag.AlignRight)
            self.titleBar.hBoxLayout.insertSpacing(self.titleBar.hBoxLayout.count(), 10)

    # ============================================================================
    # CÁC HÀM LẮNG NGHE TÍN HIỆU TỪ SYNC MANAGER MỚI
    # ============================================================================
    def _on_sync_started(self):
        """Khi bắt đầu chu kỳ đồng bộ"""
        self.btn_sync_status.setIcon(FIF.SYNC)
        self.btn_sync_status.setToolTip("Đang đồng bộ dữ liệu...")

    def _on_sync_progress(self, message):
        """Cập nhật tiến trình thời gian thực"""
        self.btn_sync_status.setToolTip(message)

    def _on_sync_finished(self, success, message):
        """Khi kết thúc một chu kỳ đồng bộ"""
        if success:
            self.btn_sync_status.setIcon(FIF.COMPLETED)
            self.btn_sync_status.setToolTip(message)
        else:
            self.btn_sync_status.setIcon(FIF.INFO)
            self.btn_sync_status.setToolTip(f"Lỗi đồng bộ: {message}")
            # Hiển thị popup báo lỗi mạng cho người dùng
            InfoBar.error("Lỗi đồng bộ ngầm", message, duration=3000, position=InfoBarPosition.TOP_RIGHT, parent=self)

    def _force_sync(self):
        """Xử lý khi người dùng bấm nút đồng bộ trên Title Bar"""
        InfoBar.success("Đồng bộ", "Hệ thống đang chạy đồng bộ ngầm định kỳ 30s an toàn.", duration=2000,
                        position=InfoBarPosition.TOP_RIGHT, parent=self)

    def closeEvent(self, event):
        """Phase 4.1: Xử lý đóng App và ngắt Thread an toàn"""
        try:
            perform_backup()
        except:
            pass

        # [ĐÃ SỬA]: Gọi stop() của SyncManager Mới
        if hasattr(self, 'sync_thread'):
            self.sync_thread.stop()

        super().closeEvent(event)

    def switch_to_interface_by_key(self, key, params=None):
        target = getattr(self, key, None)
        if target:
            self.switchTo(target)
            if params and hasattr(target, 'apply_filter_from_dashboard'):
                try:
                    target.apply_filter_from_dashboard(params)
                except:
                    pass
        else:
            InfoBar.warning("Cảnh báo", f"Trang '{key}' không khả dụng.", duration=2000,
                            position=InfoBarPosition.TOP_RIGHT, parent=self)

    def _inject_user_data(self, page_widget):
        if isinstance(page_widget, QWidget):
            try:
                page_widget.username = self.username
                page_widget.role = self.role
                page_widget.department = self.department
            except:
                pass

    def _check_access(self, key):
        if self.role == "SUPERADMIN": return True
        access = self.user_data.get('access_control')
        try:
            perms = json.loads(access) if isinstance(access, str) else access
            return bool(perms.get(key, 1))
        except:
            return True

    def _init_navigation(self):
        if self._check_access('dashboard'):
            self.addSubInterface(self.home_interface, FIF.HOME, "Tổng quan")
        self.navigationInterface.addSeparator()

        if self._check_access('dashboard') or self._check_access('iqc'):
            self.addSubInterface(self.calendar_interface, FIF.CALENDAR, "Lịch Sự kiện")
        if self._check_access('iqc'):
            self.addSubInterface(self.iqc_interface, FIF.CHECKBOX, "Nội kiểm (IQC)")
        if self._check_access('eqa'):
            self.addSubInterface(self.eqa_interface, FIF.GLOBE, "Ngoại kiểm (EQA)")
        if self._check_access('capa'):
            self.addSubInterface(self.capa_interface, FIF.FEEDBACK, "Quản lý CAPA")
        if self._check_access('alert'):
            self.addSubInterface(self.alert_interface, FIF.RINGER, "Cảnh báo")

        self.navigationInterface.addSeparator()

        if self._check_access('catalog'):
            self.addSubInterface(self.catalog_interface, FIF.FOLDER, "Danh mục QC")
        if self._check_access('device'):
            self.addSubInterface(self.device_interface, FIF.TILES, "Thiết bị")
        if self._check_access('reports'):
            self.addSubInterface(self.report_interface, FIF.PIE_SINGLE, "Báo cáo & Thống kê")

        if self.role in ["SUPERADMIN", "QA", "ADMIN", "TRUONG_KHOA"]:
            self.navigationInterface.addSeparator()
            if self._check_access('user'):
                self.addSubInterface(self.admin_interface, FIF.PEOPLE, "Quản trị", NavigationItemPosition.SCROLL)
            if self._check_access('log'):
                self.addSubInterface(self.log_interface, FIF.HISTORY, "Nhật ký hệ thống", NavigationItemPosition.SCROLL)

        self.addSubInterface(self.setting_interface, FIF.SETTING, "Cài đặt hệ thống", NavigationItemPosition.BOTTOM)
        self.navigationInterface.addWidget(routeKey='avatar', widget=self._create_avatar_widget(),
                                           onClick=self._on_avatar_click, position=NavigationItemPosition.BOTTOM)

    def _create_avatar_widget(self):
        try:
            base_path = sys._MEIPASS
        except:
            base_path = os.path.abspath("")
        logo_path = os.path.join(base_path, "app", "assets", "logo.png").replace("\\", "/")
        return NavigationAvatarWidget(self.fullname, logo_path)

    def _on_avatar_click(self):
        menu = RoundMenu(parent=self)
        if self._check_access('settings'):
            s_act = Action(FIF.SETTING, "Cài đặt")
            s_act.triggered.connect(lambda: self.switchTo(self.setting_interface))
            menu.addAction(s_act)
            menu.addSeparator()
        cp_act = Action(FIF.EDIT, "Đổi mật khẩu")
        cp_act.triggered.connect(self._show_change_password_dialog)
        menu.addAction(cp_act)
        lo_act = Action(FIF.POWER_BUTTON, "Đăng xuất")
        lo_act.triggered.connect(self.close)
        menu.addAction(lo_act)
        menu.exec(QCursor.pos())

    def _show_change_password_dialog(self):
        dialog = ChangePasswordDialog(self)
        if dialog.exec():
            v, m = dialog.validate()
            if not v:
                InfoBar.error("Lỗi", m, parent=self)
                return
            res = AuthService().change_password(self.username, dialog.old_pw_input.text(), dialog.new_pw_input.text())
            if res.get("ok"):
                InfoBar.success("Thành công", "Đã đổi mật khẩu!", parent=self)
            else:
                InfoBar.error("Lỗi", res.get("reason", "Lỗi"), parent=self)