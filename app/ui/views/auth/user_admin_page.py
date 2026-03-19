# -*- coding: utf-8 -*-
"""
app/features/auth/user_admin_page.py
(FIXED: Sửa lỗi load danh sách phòng ban & Thay Icon LOCK bị lỗi)
"""

from typing import Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDialog, QDialogButtonBox, QHeaderView, QAbstractItemView,
    QTableWidgetItem
)

# --- IMPORT FLUENT WIDGETS ---
from qfluentwidgets import (
    PrimaryPushButton, PushButton, LineEdit, ComboBox, CheckBox,
    TableWidget, PasswordLineEdit, InfoBar, FluentIcon as FIF
)

# Imports Services
from app.services.auth_service import AuthService
from app.services.department_service import DepartmentService
from app.services.audit_service import AuditService
from app.core.constants import ALL_ROLES, DEFAULT_PASSWORD

# Import Dialog Phân quyền
try:
    from app.ui.dialogs.permission_dialog import MenuPermissionDialog
except ImportError:
    MenuPermissionDialog = None


# --- Dialog Thêm/Sửa User ---
class UserDialog(QDialog):
    def __init__(self, title: str, dept_service: DepartmentService, parent=None, is_edit=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(450)

        self.is_edit = is_edit
        self.vbox = QVBoxLayout(self)

        # Form Layout
        self.form = QFormLayout()
        self.form.setSpacing(15)

        # 1. Username
        self.username = LineEdit()
        self.username.setPlaceholderText("Nhập tên đăng nhập")

        # 2. Password
        self.password = PasswordLineEdit()
        self.password.setText(DEFAULT_PASSWORD)

        # 3. Fullname
        self.fullname = LineEdit()
        self.fullname.setPlaceholderText("Họ và tên nhân viên")

        # 4. Role
        self.role = ComboBox()
        self.role.addItems(ALL_ROLES)

        # 5. Department [ĐÃ SỬA LỖI LOAD]
        self.department = ComboBox()
        try:
            # Kiểm tra xem Service đang dùng hàm mới (get_all) hay hàm cũ (list_departments)
            # để đảm bảo luôn lấy được dữ liệu dù Service thay đổi.
            if hasattr(dept_service, 'get_all'):
                deps = dept_service.get_all()
            else:
                deps = dept_service.list_departments(active_only=True)

            self.department.addItem("--- Chọn phòng ban ---", "")

            for d in deps:
                # Lấy tên phòng ban an toàn (dù d là Object hay Dict)
                name = getattr(d, 'name', None) or d.get('name')

                # Logic cũ của bạn: Text = Name, Data = Name
                if name:
                    self.department.addItem(name, name)

        except Exception as e:
            print(f"UserDialog Error: Không thể load phòng ban - {e}")
            self.department.addItem("Lỗi tải dữ liệu", "")

        # 6. Active
        self.active = CheckBox("Kích hoạt tài khoản")
        self.active.setChecked(True)

        # Add rows
        self.form.addRow("Tên đăng nhập (*):", self.username)
        if not is_edit:
            self.form.addRow("Mật khẩu (*):", self.password)
        self.form.addRow("Họ và tên:", self.fullname)
        self.form.addRow("Vai trò:", self.role)
        self.form.addRow("Phòng ban:", self.department)
        self.form.addRow("", self.active)

        self.vbox.addLayout(self.form)
        self.vbox.addSpacing(20)

        # Buttons
        self.btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)
        self.vbox.addWidget(self.btns)

    def get_data(self) -> Dict[str, Any]:
        # Dùng currentText() để lấy tên phòng ban (Logic cũ)
        dept_val = self.department.currentText()
        if dept_val == "--- Chọn phòng ban ---" or "Lỗi" in dept_val:
            dept_val = ""

        data = {
            "username": self.username.text().strip(),
            "fullname": self.fullname.text().strip(),
            "role": self.role.currentText(),
            "department": dept_val,
            "is_active": 1 if self.active.isChecked() else 0
        }
        if not self.is_edit:
            data["password"] = self.password.text()
        return data

    def load_data(self, user_data):
        self.username.setText(user_data['username'])
        self.username.setEnabled(False)
        self.fullname.setText(user_data['fullname'] or "")
        self.role.setCurrentText(user_data['role'])

        # Tìm và set index cho Department dựa trên Text
        current_dept = user_data.get('department') or ""
        idx = self.department.findText(current_dept)
        if idx >= 0:
            self.department.setCurrentIndex(idx)
        else:
            # Nếu không tìm thấy (do tên phòng bị đổi), thêm tạm vào để hiển thị
            if current_dept:
                self.department.addItem(current_dept, current_dept)
                self.department.setCurrentText(current_dept)

        self.active.setChecked(bool(user_data['is_active']))


# --- Trang Quản lý User ---
class UserAdminPage(QWidget):
    def __init__(self, current_username: str, current_role: str, parent=None):
        super().__init__(parent)
        self.current_username = current_username
        self.current_role = current_role

        self.auth_service = AuthService()
        self.dept_service = DepartmentService()
        self.audit_service = AuditService()

        self._build_ui()
        self._load_users()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Toolbar
        toolbar = QHBoxLayout()

        self.btn_add = PrimaryPushButton(FIF.ADD, "Thêm User", self)
        self.btn_edit = PushButton(FIF.EDIT, "Sửa", self)
        self.btn_perm = PushButton(FIF.MENU, "Phân quyền Menu", self)

        # [SỬA] Đổi Icon LOCK -> PASSWORD để tránh lỗi thư viện cũ
        self.btn_lock = PushButton(FIF.FOLDER_ADD, "Khóa/Mở", self)

        self.btn_reset = PushButton(FIF.SYNC, "Reset Pass", self)
        self.btn_delete = PushButton(FIF.DELETE, "Xóa", self)

        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_perm)
        toolbar.addWidget(self.btn_lock)
        toolbar.addWidget(self.btn_reset)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch(1)

        layout.addLayout(toolbar)

        # 2. Table
        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Họ tên", "Vai trò", "Phòng ban", "Trạng thái"])
        self.table.verticalHeader().hide()

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setBorderVisible(True)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

        # Events
        self.btn_add.clicked.connect(self._on_add_user)
        self.btn_edit.clicked.connect(self._on_edit_user)
        self.btn_perm.clicked.connect(self._on_permission_click)
        self.btn_lock.clicked.connect(self._on_toggle_active)
        self.btn_reset.clicked.connect(self._on_reset_password)
        self.btn_delete.clicked.connect(self._on_delete_user)

    def _load_users(self):
        try:
            users = self.auth_service.list_users()
            self.table.setRowCount(0)
            for u in users:
                row = self.table.rowCount()
                self.table.insertRow(row)

                # [QUAN TRỌNG] ID là UUID (String), không ép kiểu int()
                # Lưu toàn bộ object User vào UserRole
                item_id = QTableWidgetItem(str(u["id"]))
                item_id.setData(Qt.UserRole, u)

                self.table.setItem(row, 0, item_id)
                self.table.setItem(row, 1, QTableWidgetItem(u["username"]))
                self.table.setItem(row, 2, QTableWidgetItem(u["fullname"] or ""))
                self.table.setItem(row, 3, QTableWidgetItem(u["role"]))
                self.table.setItem(row, 4, QTableWidgetItem(u["department"] or ""))

                status = "Active" if u["is_active"] else "Locked"
                item_status = QTableWidgetItem(status)
                if not u["is_active"]:
                    item_status.setForeground(Qt.red)
                else:
                    item_status.setForeground(Qt.darkGreen)
                self.table.setItem(row, 5, item_status)
        except Exception as e:
            print(f"Lỗi load users: {e}")
            InfoBar.error("Lỗi", f"Không thể tải danh sách user: {e}", parent=self)

    def _get_selected_user(self):
        row = self.table.currentRow()
        if row < 0: return None

        item = self.table.item(row, 0)
        if not item: return None

        return item.data(Qt.UserRole)

    # --- Actions ---

    def _on_add_user(self):
        dlg = UserDialog("Thêm người dùng mới", self.dept_service, self, is_edit=False)
        if dlg.exec():
            data = dlg.get_data()
            res = self.auth_service.create_user(
                data["username"], data["password"], data["role"],
                data["department"], data["fullname"], data["is_active"]
            )
            if res["ok"]:
                InfoBar.success("Thành công", f"Đã tạo user {data['username']}", parent=self)
                self.audit_service.log_action(self.current_username, "CREATE_USER", data["username"])
                self._load_users()
            else:
                InfoBar.error("Lỗi", res["reason"], parent=self)

    def _on_edit_user(self):
        user = self._get_selected_user()
        if not user:
            InfoBar.warning("Chú ý", "Vui lòng chọn user cần sửa", parent=self)
            return

        dlg = UserDialog(f"Sửa: {user['username']}", self.dept_service, self, is_edit=True)
        dlg.load_data(user)

        if dlg.exec():
            data = dlg.get_data()
            res = self.auth_service.update_user(
                user["id"], role=data["role"], department=data["department"],
                fullname=data["fullname"], is_active=data["is_active"]
            )
            if res["ok"]:
                self.audit_service.log_action(self.current_username, "UPDATE_USER", user["username"])
                self._load_users()
                InfoBar.success("Cập nhật", "Đã lưu thông tin người dùng", parent=self)
            else:
                InfoBar.error("Lỗi", res["reason"], parent=self)

    def _on_permission_click(self):
        if not MenuPermissionDialog:
            InfoBar.error("Lỗi", "Chưa tìm thấy file permission_dialog.py", parent=self)
            return

        user = self._get_selected_user()
        if not user:
            InfoBar.warning("Chọn tài khoản", "Vui lòng chọn user để phân quyền.", parent=self)
            return

        dlg = MenuPermissionDialog(user, self.auth_service, self)
        if dlg.exec():
            InfoBar.success("Thành công", f"Đã cập nhật quyền cho {user['username']}", parent=self)

    def _on_toggle_active(self):
        user = self._get_selected_user()
        if not user: return
        res = self.auth_service.toggle_active(user["id"])
        if res["ok"]:
            action = "UNLOCK_USER" if not user["is_active"] else "LOCK_USER"
            self.audit_service.log_action(self.current_username, action, user["username"])
            self._load_users()
            InfoBar.success("Thành công", f"Đã đổi trạng thái {user['username']}", parent=self)
        else:
            InfoBar.error("Lỗi", res.get("reason", "Unknown"), parent=self)

    def _on_reset_password(self):
        user = self._get_selected_user()
        if not user: return

        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "Xác nhận",
                                f"Reset mật khẩu {user['username']} về mặc định ({DEFAULT_PASSWORD})?") == QMessageBox.Yes:
            res = self.auth_service.reset_password(user["id"], DEFAULT_PASSWORD)
            if res["ok"]:
                InfoBar.success("Đã Reset", f"Mật khẩu mới: {DEFAULT_PASSWORD}", parent=self)
                self.audit_service.log_action(self.current_username, "RESET_PASSWORD", user["username"])
            else:
                InfoBar.error("Lỗi", res.get("reason", "Unknown"), parent=self)

    def _on_delete_user(self):
        user = self._get_selected_user()
        if not user: return

        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "Cảnh báo", f"Xóa vĩnh viễn user {user['username']}?") == QMessageBox.Yes:
            res = self.auth_service.delete_user(user["id"], user["username"])
            if res["ok"]:
                self.audit_service.log_action(self.current_username, "DELETE_USER", user["username"])
                self._load_users()
                InfoBar.success("Đã xóa", f"User {user['username']} đã bị xóa khỏi hệ thống", parent=self)
            else:
                InfoBar.error("Lỗi", res["reason"], parent=self)