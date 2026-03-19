# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QTableWidgetItem,
    QListWidgetItem, QAbstractItemView
)
from qfluentwidgets import (
    Pivot, TableWidget, PrimaryPushButton, PushButton,
    InfoBar, LineEdit, ComboBox,
    CardWidget, ListWidget, StrongBodyLabel, MessageBoxBase, SubtitleLabel
)

from app.ui.views.auth.user_admin_page import UserAdminPage
from app.services.department_service import DepartmentService


# --- DIALOGS ---

class DepartmentDialog(MessageBoxBase):
    def __init__(self, parent=None, name="", note=""):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Thông tin Phòng ban", self)
        self.txt_name = LineEdit(self)
        self.txt_name.setPlaceholderText("Tên phòng ban")
        self.txt_name.setText(name)
        self.txt_note = LineEdit(self)
        self.txt_note.setPlaceholderText("Ghi chú")
        self.txt_note.setText(note)
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.txt_name)
        self.viewLayout.addWidget(self.txt_note)
        self.yesButton.setText("Lưu")
        self.cancelButton.setText("Hủy")

    def get_data(self):
        return self.txt_name.text().strip(), self.txt_note.text().strip()


class TestIndexDialog(MessageBoxBase):
    def __init__(self, parent=None, code="", name="", unit="", dtype="Quant", method=""):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Thông tin Chỉ số", self)

        # 1. Mã code
        self.txt_code = LineEdit(self)
        self.txt_code.setPlaceholderText("Mã xét nghiệm (VD: GLU)")
        self.txt_code.setText(code)

        # 2. Tên hiển thị
        self.txt_name = LineEdit(self)
        self.txt_name.setPlaceholderText("Tên hiển thị (VD: Glucose)")
        self.txt_name.setText(name)

        # 3. Đơn vị
        self.txt_unit = LineEdit(self)
        self.txt_unit.setPlaceholderText("Đơn vị (VD: mmol/L)")
        self.txt_unit.setText(unit)

        # 4. Kiểu dữ liệu
        self.cb_type = ComboBox(self)
        self.cb_type.addItems(["Quant", "Qual", "Semi"])
        self.cb_type.setCurrentText(dtype)

        # 5. Phương pháp
        self.txt_method = LineEdit(self)
        self.txt_method.setPlaceholderText("Phương pháp")
        self.txt_method.setText(method)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.txt_code)
        self.viewLayout.addWidget(self.txt_name)
        self.viewLayout.addWidget(self.txt_unit)
        self.viewLayout.addWidget(self.cb_type)
        self.viewLayout.addWidget(self.txt_method)

        self.yesButton.setText("Lưu")
        self.cancelButton.setText("Hủy")

    def get_data(self):
        return {
            "test_code": self.txt_code.text().strip(),
            "test_name": self.txt_name.text().strip(),
            "unit": self.txt_unit.text().strip(),
            "data_type": self.cb_type.currentText(),
            "method": self.txt_method.text().strip()
        }


# --- TAB QUẢN LÝ ---

class DepartmentTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dept_id = None
        self.service = DepartmentService()
        self._init_ui()
        self._load_departments()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(20)

        # LEFT
        left_panel = CardWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(StrongBodyLabel("Phòng ban / Nhóm", self))
        self.list_dept = ListWidget(self)
        self.list_dept.itemClicked.connect(self._on_dept_selected)
        left_layout.addWidget(self.list_dept)

        hbox_left = QHBoxLayout()
        self.btn_add_dept = PrimaryPushButton("Thêm", self)
        self.btn_edit_dept = PushButton("Sửa", self)
        self.btn_del_dept = PushButton("Xóa", self)
        for btn in [self.btn_add_dept, self.btn_edit_dept, self.btn_del_dept]:
            btn.setFixedHeight(32)
            hbox_left.addWidget(btn)
        left_layout.addLayout(hbox_left)

        # RIGHT
        right_panel = CardWidget(self)
        right_layout = QVBoxLayout(right_panel)
        self.lbl_right = StrongBodyLabel("Chỉ số xét nghiệm", self)
        right_layout.addWidget(self.lbl_right)

        # Full 4 cột như cũ
        self.tbl_indices = TableWidget(self)
        self.tbl_indices.setColumnCount(4)
        self.tbl_indices.setHorizontalHeaderLabels(["Mã/Tên", "Đơn vị", "Kiểu", "Phương pháp"])
        self.tbl_indices.verticalHeader().hide()
        self.tbl_indices.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_indices.horizontalHeader().setStretchLastSection(True)
        self.tbl_indices.setEditTriggers(QAbstractItemView.NoEditTriggers)
        right_layout.addWidget(self.tbl_indices)

        hbox_right = QHBoxLayout()
        self.btn_add_idx = PrimaryPushButton("Thêm chỉ số", self)
        self.btn_edit_idx = PushButton("Sửa chỉ số", self)  # Nút Sửa
        self.btn_del_idx = PushButton("Xóa chỉ số", self)

        self.btn_add_idx.setEnabled(False)
        self.btn_edit_idx.setEnabled(False)
        self.btn_del_idx.setEnabled(False)

        for btn in [self.btn_add_idx, self.btn_edit_idx, self.btn_del_idx]:
            btn.setFixedHeight(32)
            hbox_right.addWidget(btn)
        right_layout.addLayout(hbox_right)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

        # Events
        self.btn_add_dept.clicked.connect(self._action_add_dept)
        self.btn_edit_dept.clicked.connect(self._action_edit_dept)
        self.btn_del_dept.clicked.connect(self._action_del_dept)
        self.btn_add_idx.clicked.connect(self._action_add_index)
        self.btn_edit_idx.clicked.connect(self._action_edit_index)
        self.btn_del_idx.clicked.connect(self._action_del_index)

    # --- LOGIC ---
    def _load_departments(self):
        self.list_dept.clear()
        for d in self.service.get_all():
            item = QListWidgetItem(d.name)
            item.setData(Qt.UserRole, str(d.id))
            item.setData(Qt.UserRole + 1, d.note or "")
            self.list_dept.addItem(item)

    def _on_dept_selected(self, item):
        self.current_dept_id = item.data(Qt.UserRole)
        self.lbl_right.setText(f"Chỉ số của: {item.text()}")
        self.btn_add_idx.setEnabled(True)
        self.btn_edit_idx.setEnabled(True)
        self.btn_del_idx.setEnabled(True)
        self._load_indices(self.current_dept_id)

    def _load_indices(self, dept_id):
        self.tbl_indices.setRowCount(0)
        tests = self.service.list_tests_by_department(dept_id)
        self.tbl_indices.setRowCount(len(tests))
        for r, t in enumerate(tests):
            # Hiển thị Mã + Tên
            display_name = f"{t.test_code}"
            if t.test_name: display_name += f" ({t.test_name})"

            self.tbl_indices.setItem(r, 0, QTableWidgetItem(display_name))
            self.tbl_indices.setItem(r, 1, QTableWidgetItem(t.unit or ""))
            self.tbl_indices.setItem(r, 2, QTableWidgetItem(t.data_type or ""))
            self.tbl_indices.setItem(r, 3, QTableWidgetItem(t.method or ""))

            # Lưu Data ẩn để dùng khi Sửa
            item = self.tbl_indices.item(r, 0)
            item.setData(Qt.UserRole, str(t.id))  # ID
            item.setData(Qt.UserRole + 1, t.test_code)  # Code
            item.setData(Qt.UserRole + 2, t.test_name)  # Name
            item.setData(Qt.UserRole + 3, t.unit)  # Unit
            item.setData(Qt.UserRole + 4, t.data_type)  # Type
            item.setData(Qt.UserRole + 5, t.method)  # Method

    # --- ACTIONS ---
    def _action_add_dept(self):
        dlg = DepartmentDialog(self)
        if dlg.exec():
            name, note = dlg.get_data()
            ok, msg = self.service.create(name, note)
            if ok:
                self._load_departments()
                InfoBar.success("Thành công", msg, parent=self)
            else:
                InfoBar.error("Lỗi", msg, parent=self)

    def _action_edit_dept(self):
        row = self.list_dept.currentRow()
        if row < 0: return
        item = self.list_dept.item(row)
        dlg = DepartmentDialog(self, name=item.text(), note=item.data(Qt.UserRole + 1))
        if dlg.exec():
            name, note = dlg.get_data()
            ok, msg = self.service.update(item.data(Qt.UserRole), name, note)
            if ok:
                self._load_departments()
                InfoBar.success("Thành công", msg, parent=self)
            else:
                InfoBar.error("Lỗi", msg, parent=self)

    def _action_del_dept(self):
        row = self.list_dept.currentRow()
        if row < 0: return
        item = self.list_dept.item(row)
        ok, msg = self.service.delete(item.data(Qt.UserRole))
        if ok:
            self.list_dept.takeItem(row)
            self.tbl_indices.setRowCount(0)
            self.current_dept_id = None
            InfoBar.success("Đã xóa", msg, parent=self)
        else:
            InfoBar.error("Lỗi", msg, parent=self)

    def _action_add_index(self):
        if not self.current_dept_id: return
        dlg = TestIndexDialog(self)
        if dlg.exec():
            d = dlg.get_data()
            ok, msg = self.service.add_test_to_department(
                self.current_dept_id, d['test_code'], d['test_name'], d['unit'], d['data_type'], d['method']
            )
            if ok:
                self._load_indices(self.current_dept_id)
                InfoBar.success("Thành công", msg, parent=self)
            else:
                InfoBar.error("Lỗi", msg, parent=self)

    def _action_edit_index(self):
        row = self.tbl_indices.currentRow()
        if row < 0: return

        # Lấy data cũ từ UserRole
        item = self.tbl_indices.item(row, 0)
        idx_id = item.data(Qt.UserRole)
        code = item.data(Qt.UserRole + 1)
        name = item.data(Qt.UserRole + 2)
        unit = item.data(Qt.UserRole + 3)
        dtype = item.data(Qt.UserRole + 4)
        meth = item.data(Qt.UserRole + 5)

        dlg = TestIndexDialog(self, code=code, name=name, unit=unit, dtype=dtype, method=meth)
        if dlg.exec():
            d = dlg.get_data()
            ok, msg = self.service.update_test_in_department(
                idx_id, d['test_code'], d['test_name'], d['unit'], d['data_type'], d['method']
            )
            if ok:
                self._load_indices(self.current_dept_id)
                InfoBar.success("Thành công", msg, parent=self)
            else:
                InfoBar.error("Lỗi", msg, parent=self)

    def _action_del_index(self):
        row = self.tbl_indices.currentRow()
        if row < 0: return
        idx_id = self.tbl_indices.item(row, 0).data(Qt.UserRole)
        ok, msg = self.service.remove_test_from_department(idx_id)
        if ok:
            self.tbl_indices.removeRow(row)
            InfoBar.success("Đã xóa", msg, parent=self)
        else:
            InfoBar.error("Lỗi", msg, parent=self)


class ManagementPage(QWidget):
    def __init__(self, username, role, parent=None):
        super().__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(30, 10, 30, 10)
        self.pivot = Pivot(self)
        self.pivot.addItem(routeKey="users", text="Người dùng")
        self.pivot.addItem(routeKey="depts", text="Phòng ban & Xét nghiệm")
        self.pivot.setCurrentItem("users")
        self.vbox.addWidget(self.pivot)
        self.vbox.addSpacing(10)
        self.stacked = QStackedWidget(self)
        self.page_users = UserAdminPage(username, role)
        self.page_depts = DepartmentTab()
        self.stacked.addWidget(self.page_users)
        self.stacked.addWidget(self.page_depts)
        self.vbox.addWidget(self.stacked)
        self.pivot.currentItemChanged.connect(lambda k: self.stacked.setCurrentIndex(0 if k == "users" else 1))