# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any

# Qt Compat
from app.utils.qt_compat import (
    Qt, QAbstractItemView, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QInputDialog, QGroupBox, QFormLayout,
    QComboBox, QDialogButtonBox, QCompleter, QStandardItemModel,
    CaseInsensitive
)

# Services
from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService


# ============================================================================
# DIALOG THÊM/SỬA XÉT NGHIỆM
# ============================================================================
class DeptTestDialog(QDialog):
    def __init__(self, parent: QWidget, dep_name: str, catalog_service: CatalogService, prefill=None):
        super().__init__(parent)
        self.setWindowTitle(f"Chỉ số cho: {dep_name}")
        self.dept_name = dep_name
        self.catalog_service = catalog_service

        self.test_name = QComboBox()
        self.test_name.setEditable(True)
        self.test_name.lineEdit().setPlaceholderText("Gõ để tìm hoặc thêm mới...")

        # --- Completers ---
        self._test_model = QStandardItemModel(self)
        self._test_completer = QCompleter(self._test_model, self)
        self._test_completer.setCaseSensitivity(CaseInsensitive)
        self.test_name.setCompleter(self._test_completer)

        form = QFormLayout()
        form.addRow("Mã xét nghiệm *", self.test_name)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btns)

        self._load_test_suggestions()
        if prefill:
            self.test_name.setEditText(prefill.test_code)

    def _load_test_suggestions(self):
        try:
            # Code cũ dùng list_tests_by_department của catalog, ta tạm bỏ qua nếu chưa có
            pass
        except Exception:
            pass

    def get_values(self) -> Dict[str, Any]:
        return {"test_name": self.test_name.currentText().strip()}


# ============================================================================
# TRANG QUẢN LÝ CHÍNH
# ============================================================================
class DepartmentAdminPage(QDialog):
    def __init__(self, db_path: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quản lý Phòng ban & Xét nghiệm")
        self.resize(1000, 600)

        self.svc = DepartmentService()
        self.catalog_service = CatalogService()

        self._build_ui()
        self._wire_events()
        self.reload_departments()

    def _build_ui(self):
        root = QHBoxLayout(self)

        left_box = QGroupBox("Phòng ban / Nhóm")
        left_layout = QVBoxLayout(left_box)
        self.list_deps = QListWidget()
        self.btn_dep_add = QPushButton("Thêm")
        self.btn_dep_edit = QPushButton("Sửa")
        self.btn_dep_del = QPushButton("Xoá")
        btn_bar_left = QHBoxLayout()
        btn_bar_left.addWidget(self.btn_dep_add)
        btn_bar_left.addWidget(self.btn_dep_edit)
        btn_bar_left.addWidget(self.btn_dep_del)
        left_layout.addWidget(self.list_deps)
        left_layout.addLayout(btn_bar_left)

        right_box = QGroupBox("Chỉ số xét nghiệm của phòng ban")
        right_layout = QVBoxLayout(right_box)

        self.table_tests = QTableWidget(0, 2, self)
        self.table_tests.setHorizontalHeaderLabels(["Mã xét nghiệm", "Trạng thái"])
        self.table_tests.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_tests.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_tests.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_tests.horizontalHeader().setStretchLastSection(True)

        self.btn_test_add = QPushButton("Thêm chỉ số")
        self.btn_test_del = QPushButton("Xoá chỉ số")
        btn_bar_right = QHBoxLayout()
        btn_bar_right.addWidget(self.btn_test_add)
        btn_bar_right.addWidget(self.btn_test_del)
        right_layout.addWidget(self.table_tests)
        right_layout.addLayout(btn_bar_right)

        root.addWidget(left_box, 1)
        root.addWidget(right_box, 2)

    def _wire_events(self):
        self.list_deps.itemSelectionChanged.connect(self._on_dep_changed)
        self.btn_dep_add.clicked.connect(self._add_dep)
        self.btn_dep_edit.clicked.connect(self._edit_dep)
        self.btn_dep_del.clicked.connect(self._del_dep)

        self.btn_test_add.clicked.connect(self._add_test)
        self.btn_test_del.clicked.connect(self._del_test)

    # ---------- Load data ----------
    def reload_departments(self):
        self.list_deps.clear()
        # [NEW] Gọi hàm get_all() của Service mới
        for d in self.svc.get_all():
            item = QListWidgetItem(d.name)
            item.setData(Qt.UserRole, str(d.id))  # UUID
            if not d.active:
                item.setForeground(Qt.gray)
                item.setToolTip("Đã bị khóa")
            self.list_deps.addItem(item)
        if self.list_deps.count() > 0:
            self.list_deps.setCurrentRow(0)

    def _on_dep_changed(self):
        dep_id = self.current_dep_id()
        self.reload_tests(dep_id)

    def reload_tests(self, dep_id: Optional[str]):
        self.table_tests.setRowCount(0)
        if not dep_id: return

        # [NEW] Gọi hàm list_tests_by_department
        rows = self.svc.list_tests_by_department(dep_id)
        self.table_tests.setRowCount(len(rows))
        for r, t in enumerate(rows):
            self.table_tests.setItem(r, 0, QTableWidgetItem(t.test_code))
            status = "Active" if t.active else "Inactive"
            self.table_tests.setItem(r, 1, QTableWidgetItem(status))

            # Lưu ID dòng test để xóa
            self.table_tests.setVerticalHeaderItem(r, QTableWidgetItem(str(t.id)))

    def current_dep_id(self) -> Optional[str]:
        it = self.list_deps.currentItem()
        return str(it.data(Qt.UserRole)) if it else None

    # ---------- Handlers ----------
    def _add_dep(self):
        name, ok = QInputDialog.getText(self, "Thêm phòng ban", "Tên phòng ban:")
        if not ok or not name.strip(): return

        # [NEW] Gọi hàm create()
        success, msg = self.svc.create(name.strip())
        if not success:
            QMessageBox.warning(self, "Lỗi", msg)
        else:
            self.reload_departments()

    def _edit_dep(self):
        dep_id = self.current_dep_id()
        if not dep_id: return
        cur_item = self.list_deps.currentItem()

        name, ok = QInputDialog.getText(self, "Sửa phòng ban", "Tên phòng ban:", text=cur_item.text())
        if not ok or not name.strip(): return

        # [NEW] Gọi hàm update()
        success, msg = self.svc.update(dep_id, name.strip(), "")
        if not success:
            QMessageBox.warning(self, "Lỗi", msg)
        else:
            self.reload_departments()

    def _del_dep(self):
        dep_id = self.current_dep_id()
        if not dep_id: return
        if QMessageBox.question(self, "Xác nhận", "Xoá phòng ban này?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        # [NEW] Gọi hàm delete()
        success, msg = self.svc.delete(dep_id)
        if not success:
            QMessageBox.warning(self, "Lỗi", msg)
        else:
            self.reload_departments()
            self.table_tests.setRowCount(0)

    def _add_test(self):
        dep_id = self.current_dep_id()
        dep_name_item = self.list_deps.currentItem()
        if not dep_id:
            QMessageBox.information(self, "Thông báo", "Hãy chọn phòng ban trước.")
            return

        dlg = DeptTestDialog(self, dep_name=dep_name_item.text(), catalog_service=self.catalog_service)
        if dlg.exec() != QDialog.Accepted: return
        data = dlg.get_values()

        # [NEW] Gọi hàm add_test_to_department
        success, msg = self.svc.add_test_to_department(dep_id, data["test_name"])
        if not success:
            QMessageBox.warning(self, "Lỗi", msg)
        else:
            self.reload_tests(dep_id)

    def _del_test(self):
        dep_id = self.current_dep_id()
        row = self.table_tests.currentRow()
        if row < 0: return

        test_id = self.table_tests.verticalHeaderItem(row).text()

        if QMessageBox.question(self, "Xác nhận", "Xoá chỉ số này?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        # [NEW] Gọi hàm remove_test_from_department
        success, msg = self.svc.remove_test_from_department(test_id)
        if not success:
            QMessageBox.warning(self, "Lỗi", msg)
        else:
            self.reload_tests(dep_id)