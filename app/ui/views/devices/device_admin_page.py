# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem,
    QAbstractItemView, QFrame, QGridLayout, QLabel, QStackedWidget, QFileDialog
)

from qfluentwidgets import (
    TableWidget, PrimaryPushButton, PushButton,
    LineEdit, ComboBox, FluentIcon as FIF, InfoBar,
    CardWidget, StrongBodyLabel, BodyLabel,
    InfoBadge, MessageBoxBase, SubtitleLabel, CheckBox, SpinBox,
    DatePicker  # [NEW]
)

from app.services.device_service import DeviceService


class DeviceDialog(MessageBoxBase):
    def __init__(self, parent=None, device_data=None):
        super().__init__(parent)
        self.device_data = device_data or {}
        self.service = DeviceService()

        self.titleLabel = SubtitleLabel("Cấu hình thiết bị & Bảo trì", self)
        self.viewLayout.addWidget(self.titleLabel)

        self._init_form()
        self._load_departments_to_combo()
        self._load_data()

        # Nút Test giữ nguyên
        self.btn_test = PushButton(FIF.SPEED_OFF, "Test Kết nối", self)
        self.btn_test.clicked.connect(self._on_test_connection)
        self.buttonLayout.insertWidget(0, self.btn_test)

        self.yesButton.setText("Lưu")
        self.cancelButton.setText("Hủy")
        self.widget.setMinimumWidth(650)  # Tăng chiều rộng chút

    def _init_form(self):
        # --- PHẦN 1: THÔNG TIN CŨ (GIỮ NGUYÊN) ---
        self.grp_info = QFrame(self)
        layout_info = QGridLayout(self.grp_info)

        self.txt_code = LineEdit(self);
        self.txt_code.setPlaceholderText("Mã máy (VD: XP-100)")
        self.txt_name = LineEdit(self);
        self.txt_name.setPlaceholderText("Tên hiển thị")
        self.txt_model = LineEdit(self);
        self.txt_model.setPlaceholderText("Model máy")
        self.cb_dept = ComboBox(self);
        self.cb_dept.setPlaceholderText("Chọn phòng ban")
        self.cb_protocol = ComboBox(self);
        self.cb_protocol.addItems(["ASTM 1394", "HL7 v2.x", "Custom/Plain Text", "Serial Raw"])

        layout_info.addWidget(BodyLabel("Mã máy:"), 0, 0);
        layout_info.addWidget(self.txt_code, 0, 1)
        layout_info.addWidget(BodyLabel("Tên máy:"), 1, 0);
        layout_info.addWidget(self.txt_name, 1, 1)
        layout_info.addWidget(BodyLabel("Phòng ban:"), 2, 0);
        layout_info.addWidget(self.cb_dept, 2, 1)
        layout_info.addWidget(BodyLabel("Model:"), 3, 0);
        layout_info.addWidget(self.txt_model, 3, 1)
        layout_info.addWidget(BodyLabel("Giao thức:"), 4, 0);
        layout_info.addWidget(self.cb_protocol, 4, 1)

        self.viewLayout.addWidget(self.grp_info)
        self.viewLayout.addSpacing(10)

        hbox_conn = QHBoxLayout()
        hbox_conn.addWidget(StrongBodyLabel("Kiểu kết nối:", self))
        self.cb_conn_type = ComboBox(self)
        self.cb_conn_type.addItems(["TCP/IP (LAN)", "RS232 (Serial/COM)", "FILE (Folder/ASTM)", "Không kết nối"])
        self.cb_conn_type.currentIndexChanged.connect(self._on_conn_type_changed)
        hbox_conn.addWidget(self.cb_conn_type, 1)
        self.viewLayout.addLayout(hbox_conn)

        self.stack_settings = QStackedWidget(self)

        # 1. TCP
        self.page_tcp = QWidget();
        tcp_layout = QGridLayout(self.page_tcp)
        self.txt_ip = LineEdit(self);
        self.txt_ip.setPlaceholderText("192.168.1.xxx")
        self.txt_port = SpinBox(self);
        self.txt_port.setRange(1, 65535);
        self.txt_port.setValue(5000)
        tcp_layout.addWidget(BodyLabel("IP Address:"), 0, 0);
        tcp_layout.addWidget(self.txt_ip, 0, 1)
        tcp_layout.addWidget(BodyLabel("Port:"), 1, 0);
        tcp_layout.addWidget(self.txt_port, 1, 1)

        # 2. Serial
        self.page_serial = QWidget();
        ser_layout = QGridLayout(self.page_serial)
        self.txt_com = LineEdit(self);
        self.txt_com.setPlaceholderText("COM1")
        self.cb_baud = ComboBox(self);
        self.cb_baud.addItems(["9600", "19200", "38400", "115200"])
        self.cb_parity = ComboBox(self);
        self.cb_parity.addItems(["None", "Odd", "Even"])
        ser_layout.addWidget(BodyLabel("Cổng COM:"), 0, 0);
        ser_layout.addWidget(self.txt_com, 0, 1)
        ser_layout.addWidget(BodyLabel("Baudrate:"), 1, 0);
        ser_layout.addWidget(self.cb_baud, 1, 1)
        ser_layout.addWidget(BodyLabel("Parity:"), 2, 0);
        ser_layout.addWidget(self.cb_parity, 2, 1)

        # 3. File
        self.page_file = QWidget();
        file_layout = QHBoxLayout(self.page_file)
        self.txt_file_path = LineEdit(self);
        self.txt_file_path.setPlaceholderText("D:/LIS_DATA")
        self.btn_browse = PushButton("Chọn...", self);
        self.btn_browse.clicked.connect(self._browse_folder)
        file_layout.addWidget(BodyLabel("Thư mục:"));
        file_layout.addWidget(self.txt_file_path, 1);
        file_layout.addWidget(self.btn_browse)

        # 4. None
        self.page_none = QWidget()

        self.stack_settings.addWidget(self.page_tcp)
        self.stack_settings.addWidget(self.page_serial)
        self.stack_settings.addWidget(self.page_file)
        self.stack_settings.addWidget(self.page_none)

        self.viewLayout.addWidget(self.stack_settings)

        self.txt_note = LineEdit(self);
        self.txt_note.setPlaceholderText("Ghi chú thêm...")
        self.viewLayout.addWidget(self.txt_note)

        # --- [NEW] PHẦN 2: CẤU HÌNH BẢO TRÌ ---
        self.viewLayout.addSpacing(15)
        self.viewLayout.addWidget(StrongBodyLabel("Cấu hình Bảo trì Định kỳ", self))

        grp_maint = QFrame();
        maint_layout = QGridLayout(grp_maint)
        self.sp_cycle = SpinBox();
        self.sp_cycle.setRange(0, 3650);
        self.sp_cycle.setSuffix(" ngày");
        self.sp_cycle.setToolTip("0 = Không nhắc")
        self.dp_last = DatePicker();
        self.dp_last.setDate(QDate.currentDate())

        maint_layout.addWidget(BodyLabel("Chu kỳ lặp lại:"), 0, 0);
        maint_layout.addWidget(self.sp_cycle, 0, 1)
        maint_layout.addWidget(BodyLabel("Lần cuối bảo trì:"), 1, 0);
        maint_layout.addWidget(self.dp_last, 1, 1)

        self.viewLayout.addWidget(grp_maint)

    def _browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if d: self.txt_file_path.setText(d)

    def _load_departments_to_combo(self):
        self.cb_dept.clear()
        self.cb_dept.addItem("", userData=None)
        depts = self.service.get_departments()
        for d in depts:
            self.cb_dept.addItem(d['name'], userData=d['id'])

    def _load_data(self):
        d = self.device_data
        if not d: return

        # Load thông tin cơ bản
        self.txt_code.setText(d.get('code', ''))
        self.txt_name.setText(d.get('name', ''))
        self.txt_model.setText(d.get('model', ''))
        self.txt_note.setText(d.get('note', ''))
        self.cb_protocol.setCurrentText(d.get('protocol', 'ASTM 1394'))

        if d.get('department_id'):
            idx = self.cb_dept.findData(d.get('department_id'))
            if idx >= 0: self.cb_dept.setCurrentIndex(idx)

        # Load Conn Type
        ctype = d.get('conn_type', 'none')
        idx_stack = 3
        if ctype == 'tcp':
            idx_stack = 0
            self.txt_ip.setText(d.get('ip', ''))
            self.txt_port.setValue(int(d.get('port') or 5000))
        elif ctype == 'serial':
            idx_stack = 1
            self.txt_com.setText(d.get('serial_port', ''))
            self.cb_baud.setCurrentText(str(d.get('baudrate', '9600')))
        elif ctype == 'file':
            idx_stack = 2
            self.txt_file_path.setText(d.get('file_path', ''))

        self.cb_conn_type.setCurrentIndex(idx_stack)
        self.stack_settings.setCurrentIndex(idx_stack)

        # [NEW] Load Maintenance
        self.sp_cycle.setValue(int(d.get('maintenance_cycle') or 0))
        if d.get('last_maintenance_date'):
            try:
                # Xử lý format ngày
                val = d.get('last_maintenance_date')
                if "-" in val:
                    qd = QDate.fromString(val, "yyyy-MM-dd")
                else:
                    qd = QDate.fromString(val, "d/M/yyyy")

                if qd.isValid(): self.dp_last.setDate(qd)
            except:
                pass

    def _on_conn_type_changed(self, index):
        self.stack_settings.setCurrentIndex(index)

    def get_data(self):
        idx = self.cb_conn_type.currentIndex()
        ctype_map = {0: "tcp", 1: "serial", 2: "file", 3: "none"}
        conn_type = ctype_map.get(idx, "none")

        data = {
            "code": self.txt_code.text(),
            "name": self.txt_name.text(),
            "model": self.txt_model.text(),
            "protocol": self.cb_protocol.currentText(),
            "department_id": self.cb_dept.currentData(),
            "conn_type": conn_type,
            "note": self.txt_note.text(),
            # [NEW] Maintenance Fields
            "maintenance_cycle": self.sp_cycle.value(),
            "last_maintenance_date": self.dp_last.date.toString("yyyy-MM-dd")
        }

        if conn_type == "tcp":
            data["ip"] = self.txt_ip.text()
            data["port"] = self.txt_port.value()
        elif conn_type == "serial":
            data["serial_port"] = self.txt_com.text()
            data["baudrate"] = self.cb_baud.currentText()
            data["parity"] = self.cb_parity.currentText()
            data["stopbits"] = 1
        elif conn_type == "file":
            data["file_path"] = self.txt_file_path.text()

        return data

    def _on_test_connection(self):
        config = self.get_data()
        self.btn_test.setEnabled(False);
        self.btn_test.setText("Đang thử...")
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        ok, msg = self.service.test_connection(config)
        self.btn_test.setEnabled(True);
        self.btn_test.setText("Test Kết nối")
        if ok:
            InfoBar.success("Thành công", msg, parent=self)
        else:
            InfoBar.error("Thất bại", msg, parent=self)


class DeviceAdminPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = DeviceService()
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)

        header_card = CardWidget(self)
        header_layout = QVBoxLayout(header_card)
        title = StrongBodyLabel("Danh sách Thiết bị Xét nghiệm & Bảo trì", self)

        toolbar = QHBoxLayout()
        self.txt_search = LineEdit(self)
        self.txt_search.setPlaceholderText("Tìm kiếm thiết bị...")
        self.txt_search.setFixedWidth(250)
        self.txt_search.textChanged.connect(self._load_data)

        self.btn_add = PrimaryPushButton(FIF.ADD, "Thêm mới", self)
        self.btn_edit = PushButton(FIF.EDIT, "Sửa", self)
        self.btn_del = PushButton(FIF.DELETE, "Xóa", self)
        self.btn_ping = PushButton(FIF.SPEED_HIGH, "Kiểm tra Kết nối", self)

        toolbar.addWidget(self.txt_search);
        toolbar.addStretch(1)
        toolbar.addWidget(self.btn_add);
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_ping);
        toolbar.addWidget(self.btn_del)

        header_layout.addWidget(title);
        header_layout.addLayout(toolbar)
        layout.addWidget(header_card)

        self.table = TableWidget(self)
        # [NEW] Thêm cột Bảo trì
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Mã máy", "Tên thiết bị", "Phòng ban", "Loại kết nối", "Thông số", "Bảo trì", "Trạng thái"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_del.clicked.connect(self._on_delete)
        self.btn_ping.clicked.connect(self._on_quick_test)

    def _load_data(self):
        search = self.txt_search.text().lower()
        devices = self.service.list_devices()
        filtered = [d for d in devices if search in d['name'].lower() or search in d.get('code', '').lower()]

        self.table.setRowCount(0)
        for i, d in enumerate(filtered):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(d['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(d.get('code', '')))
            self.table.setItem(i, 2, QTableWidgetItem(d['name']))
            self.table.setItem(i, 3, QTableWidgetItem(d.get('department_name') or "---"))

            ctype = d.get('conn_type', 'none')
            bg_color = '#9d5d00'
            if ctype == 'tcp':
                bg_color = '#005fb8'
            elif ctype == 'file':
                bg_color = '#107c10'

            self._set_badge(i, 4, ctype.upper(), bg_color)

            # Set thông tin kết nối
            info = "---"
            if ctype == 'tcp':
                info = f"{d.get('ip')}:{d.get('port')}"
            elif ctype == 'serial':
                info = f"{d.get('serial_port')} ({d.get('baudrate')})"
            elif ctype == 'file':
                info = d.get('file_path')
            self.table.setItem(i, 5, QTableWidgetItem(info))

            # [NEW] Set thông tin bảo trì
            cycle = d.get('maintenance_cycle', 0)
            last = d.get('last_maintenance_date') or "-"
            maint_info = f"Định kỳ {cycle} ngày\nCuối: {last}" if cycle > 0 else "Không nhắc"
            self.table.setItem(i, 6, QTableWidgetItem(maint_info))

            self._set_badge(i, 7, "Active", '#0f7b0f')
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, d)

        self.table.resizeRowsToContents()

    def _set_badge(self, row, col, text, bg_color):
        container = QWidget();
        layout = QHBoxLayout(container);
        layout.setContentsMargins(5, 5, 5, 5);
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        badge = InfoBadge(text)
        badge.setStyleSheet(
            f"InfoBadge {{ background-color: {bg_color}; color: white; border-radius: 4px; padding: 2px 8px; }}")
        layout.addWidget(badge)
        self.table.setCellWidget(row, col, container)

    def _on_add(self):
        dlg = DeviceDialog(self)
        if dlg.exec():
            ok, msg = self.service.create_device(dlg.get_data())
            if ok:
                self._load_data();
                InfoBar.success("Thành công", msg, parent=self)
            else:
                InfoBar.error("Lỗi", msg, parent=self)

    def _on_edit(self):
        row = self.table.currentRow()
        if row < 0: return
        data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        dlg = DeviceDialog(self, device_data=data)
        if dlg.exec():
            ok, msg = self.service.update_device(data['id'], dlg.get_data())
            if ok:
                self._load_data();
                InfoBar.success("Cập nhật", msg, parent=self)
            else:
                InfoBar.error("Lỗi", msg, parent=self)

    def _on_delete(self):
        """Xử lý sự kiện khi nhấn nút Xóa"""
        # 1. Lấy dòng đang chọn (SỬA LỖI: dùng self.table thay vì self.tableView)
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            InfoBar.warning("Cảnh báo", "Vui lòng chọn thiết bị cần xóa!", parent=self)
            return

        # Lấy index của dòng đầu tiên được chọn
        row_index = selected_rows[0].row()

        # Lấy dữ liệu thiết bị đã lưu trong item (cột 0)
        device_data = self.table.item(row_index, 0).data(Qt.ItemDataRole.UserRole)
        device_id = device_data['id']
        device_name = device_data['name']

        # 2. HIỆN HỘP THOẠI XÁC NHẬN
        from qfluentwidgets import MessageBox

        title = "Xác nhận xóa"
        content = f"Bạn có chắc chắn muốn xóa thiết bị '{device_name}' không?\nHành động này không thể hoàn tác."

        # Tạo MessageBox chuẩn
        w = MessageBox(title, content, self.window())

        # 3. Xử lý kết quả
        if w.exec():
            # --- GỌI SERVICE ĐỂ XÓA ---
            # Giả định service của bạn có hàm delete_device(id)
            # Nếu hàm tên khác, hãy sửa lại (ví dụ: delete, remove_device...)
            try:
                ok, msg = self.service.delete_device(device_id)

                if ok:
                    self._load_data()  # Load lại bảng
                    InfoBar.success("Thành công", "Đã xóa thiết bị thành công", parent=self)
                else:
                    InfoBar.error("Lỗi", f"Không thể xóa: {msg}", parent=self)
            except AttributeError:
                InfoBar.error("Lỗi Code", "Chưa có hàm delete_device trong Service!", parent=self)
            except Exception as e:
                InfoBar.error("Lỗi hệ thống", str(e), parent=self)

    def _on_quick_test(self):
        row = self.table.currentRow()
        if row < 0: return
        data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        InfoBar.info("Test", f"Đang kiểm tra {data['name']}...", parent=self)
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        ok, msg = self.service.test_connection(data)
        if ok:
            InfoBar.success("OK", msg, parent=self)
        else:
            InfoBar.error("Lỗi", msg, parent=self)