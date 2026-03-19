from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QWidget, QMessageBox)
from PySide6.QtCore import Qt
from qfluentwidgets import PrimaryPushButton, PushButton, SubtitleLabel, LineEdit


class CatalogMappingDialog(QDialog):
    def __init__(self, parent=None, data_list=None, service=None):
        super().__init__(parent)
        self.setWindowTitle("Mapping Code LIMS/Excel")
        self.resize(700, 500)

        self.data_list = data_list or []  # Danh sách các analytes từ màn hình chính
        self.service = service

        # UI Setup
        layout = QVBoxLayout(self)

        # Tiêu đề
        layout.addWidget(SubtitleLabel("Ánh xạ mã xét nghiệm (LIMS/Excel Mapping)", self))

        # Bảng Mapping
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setHorizontalHeaderLabels(["ID (Ẩn)", "Tên Xét Nghiệm", "Đơn Vị", "Mã LIMS / Header Excel"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.NoSelection)  # Không cần chọn dòng

        # Style bảng
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.setColumnHidden(0, True)  # Ẩn cột ID

        layout.addWidget(self.tbl)

        # Load dữ liệu
        self._load_data()

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = PrimaryPushButton("Lưu Mapping", self)
        self.btn_cancel = PushButton("Đóng", self)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        # Events
        self.btn_save.clicked.connect(self._on_save)
        self.btn_cancel.clicked.connect(self.reject)

    def _load_data(self):
        self.tbl.setRowCount(len(self.data_list))

        for r, d in enumerate(self.data_list):
            # Cột ID (Ẩn)
            self.tbl.setItem(r, 0, QTableWidgetItem(str(d.get("id"))))

            # Cột Tên (Read only)
            name_item = QTableWidgetItem(str(d.get("test_name")))
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Không cho sửa tên
            self.tbl.setItem(r, 1, name_item)

            # Cột Đơn vị (Read only)
            unit_item = QTableWidgetItem(str(d.get("unit") or ""))
            unit_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.tbl.setItem(r, 2, unit_item)

            # Cột Mapping Code (Cho phép sửa)
            current_code = d.get("lims_code") or ""
            # Dùng ô nhập liệu trực tiếp hoặc TableItem edit
            # Ở đây dùng TableItem cho đơn giản
            code_item = QTableWidgetItem(str(current_code))
            code_item.setBackground(Qt.GlobalColor.white)  # Đánh dấu màu để biết ô này nhập được
            self.tbl.setItem(r, 3, code_item)

    def _on_save(self):
        """Lưu toàn bộ mapping xuống DB"""
        count = 0
        try:
            for r in range(self.tbl.rowCount()):
                item_id = self.tbl.item(r, 0).text()
                # Lấy text từ cột Mapping (cột 3)
                lims_code = self.tbl.item(r, 3).text().strip()

                # Gọi service update
                self.service.update_analyte_mapping(item_id, lims_code)
                count += 1

            QMessageBox.information(self, "Thành công", f"Đã cập nhật mapping cho {count} chỉ số.")
            self.accept()  # Đóng dialog

        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu mapping: {e}")