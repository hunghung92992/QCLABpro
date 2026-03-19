# app/features/catalog/catalog_lot_dialog.py
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QFrame, QGridLayout
)
from qfluentwidgets import (
    MessageBoxBase, LineEdit, ComboBox, CalendarPicker,
    StrongBodyLabel, BodyLabel, SubtitleLabel
)
from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService


class LotBaseDialog(MessageBoxBase):
    def __init__(self,
                 parent: Optional[QWidget] = None,
                 title: str = "Sửa LOT",  # Đổi tiêu đề mặc định
                 defaults: Optional[Dict[str, Any]] = None,
                 dept_service: Optional[DepartmentService] = None,
                 catalog_service: Optional[CatalogService] = None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)

        self._defaults = defaults or {}
        self.dept_service = dept_service or DepartmentService()
        self.catalog_service = catalog_service or CatalogService()

        # --- 1. SETUP UI ---
        self.viewLayout.addWidget(self.titleLabel)

        # A. Group: Thông tin chung
        self.viewLayout.addWidget(StrongBodyLabel("Thông tin chung:", self))

        # Row 1: Mã Lot & Tên (Thứ tự)
        h1 = QHBoxLayout()
        self.txtLotCode = LineEdit(self)
        self.txtLotCode.setPlaceholderText("Mã Lot (VD: 12)")

        self.txtLotName = LineEdit(self)
        self.txtLotName.setPlaceholderText("Tên/Thứ tự (VD: 2)")

        h1.addWidget(self.txtLotCode)
        h1.addWidget(self.txtLotName)
        self.viewLayout.addLayout(h1)

        # Row 2: Mapping ID (Quan trọng)
        h2 = QHBoxLayout()
        h2.addWidget(BodyLabel("Mã mẫu (SID) trên máy:", self))
        self.txtDeviceSampleID = LineEdit(self)
        self.txtDeviceSampleID.setPlaceholderText("Mã mẫu trên máy (VD: QC_L1)")
        h2.addWidget(self.txtDeviceSampleID, 1)  # Stretch factor 1 để ô nhập dài ra
        self.viewLayout.addLayout(h2)

        self.viewLayout.addSpacing(10)  # Khoảng cách

        # B. Group: Phân loại
        self.viewLayout.addWidget(StrongBodyLabel("Phân loại:", self))

        # Row 3: Phòng ban | Level | Trạng thái
        h3 = QHBoxLayout()

        # Cột 1: Phòng ban
        v3_1 = QVBoxLayout()
        v3_1.addWidget(BodyLabel("Phòng ban:", self))
        self.cmbDepartment = ComboBox(self)
        v3_1.addWidget(self.cmbDepartment)

        # Cột 2: Level
        v3_2 = QVBoxLayout()
        v3_2.addWidget(BodyLabel("Mức (Level):", self))
        self.cmbLevel = ComboBox(self)
        self.cmbLevel.addItems(["", "L1", "L2", "L3"])
        v3_2.addWidget(self.cmbLevel)

        # Cột 3: Trạng thái
        v3_3 = QVBoxLayout()
        v3_3.addWidget(BodyLabel("Trạng thái:", self))
        self.cmbStatus = ComboBox(self)
        self.cmbStatus.addItems(["active", "closed"])
        v3_3.addWidget(self.cmbStatus)

        h3.addLayout(v3_1, 3)
        h3.addLayout(v3_2, 2)
        h3.addLayout(v3_3, 2)
        self.viewLayout.addLayout(h3)

        # Row 4: Ngày SX | Hạn SD
        h4 = QHBoxLayout()

        v4_1 = QVBoxLayout()
        v4_1.addWidget(BodyLabel("Ngày SX:", self))
        self.dtMfg = CalendarPicker(self)
        self.dtMfg.setDateFormat(Qt.DateFormat.ISODate)
        v4_1.addWidget(self.dtMfg)

        v4_2 = QVBoxLayout()
        v4_2.addWidget(BodyLabel("Hạn SD:", self))
        self.dtExp = CalendarPicker(self)
        self.dtExp.setDateFormat(Qt.DateFormat.ISODate)
        v4_2.addWidget(self.dtExp)

        h4.addLayout(v4_1)
        h4.addLayout(v4_2)
        self.viewLayout.addLayout(h4)

        # Warning Label
        self.lblDup = BodyLabel("", self)
        self.lblDup.setStyleSheet("color: red")
        self.viewLayout.addWidget(self.lblDup)

        # Config Buttons
        self.yesButton.setText("Lưu")
        self.cancelButton.setText("Hủy")
        self.widget.setMinimumWidth(550)

        # --- 2. LOAD DATA ---
        self._load_departments()
        self._apply_defaults()

        # Event Check trùng
        self.txtLotCode.textChanged.connect(self._check_dup)
        self.cmbDepartment.currentIndexChanged.connect(self._check_dup)

        # Event Save
        try:
            self.yesButton.clicked.disconnect()
        except:
            pass
        self.yesButton.clicked.connect(self._ok)

    def _load_departments(self):
        self.cmbDepartment.clear()
        self.cmbDepartment.addItem("", "")
        try:
            deps = self.dept_service.list_departments(active_only=True)
            for d in deps:
                self.cmbDepartment.addItem(d.name, d.name)
        except:
            pass

    def _apply_defaults(self):
        d = self._defaults
        if not d:
            self.dtMfg.setDate(QDate.currentDate())
            self.dtExp.setDate(QDate.currentDate().addDays(365))
            return

        # 1. Load Text (Dùng .get để an toàn)
        self.txtLotCode.setText(d.get('lot_code') or d.get('lot') or d.get('lot_no') or "")

        # Ưu tiên lấy 'name', nếu không có thì lấy 'lot_name'
        self.txtLotName.setText(d.get('name') or d.get('lot_name') or "")

        # Load Mapping ID
        self.txtDeviceSampleID.setText(d.get('device_sample_id') or "")

        # 2. Load ComboBox (Phòng ban, Level, Status)
        # Phòng ban
        dept_val = d.get('department') or ""
        idx = self.cmbDepartment.findText(dept_val)
        if idx >= 0: self.cmbDepartment.setCurrentIndex(idx)

        # Level (Chuyển đổi số sang chữ nếu cần: 1->L1)
        lvl = str(d.get('level') or "")
        if lvl == "1":
            lvl = "L1"
        elif lvl == "2":
            lvl = "L2"
        elif lvl == "3":
            lvl = "L3"
        idx_lvl = self.cmbLevel.findText(lvl)
        if idx_lvl >= 0: self.cmbLevel.setCurrentIndex(idx_lvl)

        # Status
        status_val = d.get('status') or "active"
        idx_st = self.cmbStatus.findText(status_val)
        if idx_st >= 0: self.cmbStatus.setCurrentIndex(idx_st)

        # 3. Load Ngày tháng (XỬ LÝ AN TOÀN TUYỆT ĐỐI)
        # Hàm con để parse ngày
        def _safe_set_date(picker, val):
            if not val: return
            try:
                # Thử parse ISO format (YYYY-MM-DD)
                qdate = QDate.fromString(str(val), Qt.DateFormat.ISODate)
                if qdate.isValid():
                    picker.setDate(qdate)
            except:
                pass

        # Lấy mfg_date, nếu không có thì thử lấy mfg
        mfg_val = d.get('mfg_date') or d.get('mfg')
        _safe_set_date(self.dtMfg, mfg_val)

        # Lấy exp_date, nếu không có thì thử lấy exp hoặc expiry_date
        exp_val = d.get('exp_date') or d.get('exp') or d.get('expiry_date')
        _safe_set_date(self.dtExp, exp_val)

    def _check_dup(self):
        # (Giữ nguyên logic cũ của bạn, tạm bỏ qua để code gọn)
        pass

    def _ok(self):
        code = self.txtLotCode.text().strip()
        if not code:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chưa nhập Mã Lot")
            return
        self.accept()

    def values(self) -> Dict[str, Any]:
        return {
            # [SỬA LỖI 1] Đổi key 'lot_name' thành 'name' để khớp với logic cũ của bạn
            "name": self.txtLotName.text().strip(),
            "lot_name": self.txtLotName.text().strip(),  # Giữ cả 2 cho chắc chắn

            "lot_code": self.txtLotCode.text().strip(),
            "lot": self.txtLotCode.text().strip(),  # Giữ cả 2 key lot/lot_code

            "level": self.cmbLevel.currentText(),

            # [SỬA LỖI MAPPING] Trả về đúng key device_sample_id
            "device_sample_id": self.txtDeviceSampleID.text().strip(),

            "department": self.cmbDepartment.currentText(),
            "mfg_date": self.dtMfg.date.toString(Qt.DateFormat.ISODate),
            "exp_date": self.dtExp.date.toString(Qt.DateFormat.ISODate),
            "status": self.cmbStatus.currentText(),
        }


# --- FUNCTIONS GỌI TỪ NGOÀI ---
def open_add_lot_dialog(parent=None, dept_service=None, catalog_service=None):
    dlg = LotBaseDialog(parent, "Thêm LOT", dept_service=dept_service, catalog_service=catalog_service)
    return dlg.values() if dlg.exec() else None


def open_edit_lot_dialog(defaults: Dict, parent=None, dept_service=None, catalog_service=None):
    dlg = LotBaseDialog(parent, "Sửa LOT", defaults=defaults, dept_service=dept_service,
                        catalog_service=catalog_service)
    return dlg.values() if dlg.exec() else None