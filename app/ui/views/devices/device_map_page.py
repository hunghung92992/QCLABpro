# app/ui/views/device/device_map_page.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView
from qfluentwidgets import (CardWidget, ComboBox, LineEdit, PrimaryPushButton,
                            TableWidget, InfoBar, SubtitleLabel, CaptionLabel, FluentIcon as FIF)


class DeviceMapPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_service = DeviceService()
        self._init_ui()
        self._load_devices()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- 1. Header & Selector ---
        header_card = CardWidget(self)
        hl = QHBoxLayout(header_card)

        self.cb_device = ComboBox()
        self.cb_device.setPlaceholderText("Chọn máy xét nghiệm...")
        self.cb_device.currentIndexChanged.connect(self._load_maps)

        hl.addWidget(SubtitleLabel("Từ điển Mapping"))
        hl.addStretch(1)
        hl.addWidget(CaptionLabel("Chọn thiết bị:"))
        hl.addWidget(self.cb_device)

        layout.addWidget(header_card)

        # --- 2. Input Area (Add New) ---
        input_card = CardWidget(self)
        il = QHBoxLayout(input_card)

        self.txt_machine = LineEdit()
        self.txt_machine.setPlaceholderText("Mã máy gửi về (vd: 703)")

        self.txt_internal = LineEdit()
        self.txt_internal.setPlaceholderText("Mã hệ thống (vd: GLU)")

        self.btn_add = PrimaryPushButton(FIF.ADD, "Thêm Ánh Xạ")
        self.btn_add.clicked.connect(self._on_add)

        il.addWidget(self.txt_machine)
        il.addWidget(FIF.CHEVRON_RIGHT.icon(), stretch=0)
        il.addWidget(self.txt_internal)
        il.addWidget(self.btn_add)

        layout.addWidget(input_card)

        # --- 3. Table Area ---
        self.table = TableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Mã từ Máy", "Mã Nội Bộ", "Thao tác"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.table)

    def _load_devices(self):
        self.cb_device.clear()
        devices = self.device_service.list_devices(filters={"active": 1})
        for d in devices:
            self.cb_device.addItem(d['name'], userData=d['id'])

    def _load_maps(self):
        self.table.setRowCount(0)
        dev_id = self.cb_device.currentData()
        if not dev_id: return

        maps = self.device_service.get_test_maps(dev_id)
        for m in maps:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(m['machine_code']))
            self.table.setItem(row, 1, QTableWidgetItem(m['internal_code']))

            # Nút xóa (Tạm thời dùng text, bạn có thể thay bằng icon)
            btn_del = PrimaryPushButton("Xóa")
            btn_del.clicked.connect(lambda chk=False, mid=m['id']: self._on_delete(mid))
            self.table.setCellWidget(row, 2, btn_del)

    def _on_add(self):
        dev_id = self.cb_device.currentData()
        m_code = self.txt_machine.text().strip()
        i_code = self.txt_internal.text().strip()

        if not dev_id or not m_code or not i_code:
            InfoBar.warning("Thiếu thông tin", "Vui lòng nhập đủ các mã.", parent=self)
            return

        success, msg = self.device_service.add_test_map(dev_id, m_code, i_code)
        if success:
            InfoBar.success("Thành công", msg, parent=self)
            self.txt_machine.clear()
            self.txt_internal.clear()
            self._load_maps()
        else:
            InfoBar.error("Lỗi", msg, parent=self)

    def _on_delete(self, map_id):
        if self.device_service.delete_test_map(map_id):
            self._load_maps()