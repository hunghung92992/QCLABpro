# -*- coding: utf-8 -*-
"""
app/shared/dialogs/standard_capa_dialog.py
(UNIFIED CAPA DIALOG - ISO 15189 & FLUENT DESIGN)
Giao diện nhập liệu CAPA duy nhất cho toàn hệ thống.
"""

import datetime as dt
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea,QFileDialog

from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, StrongBodyLabel, BodyLabel,
    LineEdit, TextEdit, ComboBox, DateEdit, SegmentedWidget,
    SimpleCardWidget, InfoBar, FluentIcon as FIF, PrimaryPushButton ,PushButton
)

from app.services.capa_service import CapaService

# --- DANH SÁCH GỢI Ý CHUẨN ---
SUGGESTIONS = {
    "IQC": {
        "causes": ["Lỗi ngẫu nhiên", "Lỗi hệ thống", "Hóa chất hỏng/hết hạn", "Calibration sai lệch",
                   "Mẫu QC bị nhiễm bẩn", "Lỗi kim hút/bọt khí"],
        "actions": ["Chạy lại mẫu QC mới", "Hiệu chuẩn lại (Recalibrate)", "Thay hóa chất mới",
                    "Bảo trì bộ phận hút mẫu", "Liên hệ hỗ trợ kỹ thuật hãng"]
    },
    "ALERTS": {
        "causes": ["Lỗi kết nối mạng (LIS/HIS)", "Nhiệt độ tủ bảo quản vượt ngưỡng", "Thiết bị chưa bảo trì định kỳ",
                   "Hết vật tư tiêu hao", "Lỗi phần mềm điều khiển"],
        "actions": ["Kiểm tra hạ tầng mạng", "Điều chỉnh nhiệt độ/Gọi bảo trì", "Thực hiện bảo trì ngay",
                    "Bổ sung vật tư", "Khởi động lại hệ thống"]
    }
}


class StandardCapaDialog(MessageBoxBase):
    def __init__(self, parent=None, source="IQC", title_incident="", initial_desc="", test_info=""):
        super().__init__(parent)
        self.service = CapaService()
        self.source = source

        # Cấu hình Dialog
        self.titleLabel = SubtitleLabel("Hồ sơ Hành động Khắc phục (CAPA)", self)
        self.widget.setMinimumWidth(750)
        self.widget.setMinimumHeight(600)
        self.yesButton.setText("Lưu Hồ sơ")
        self.cancelButton.setText("Hủy bỏ")

        # UI Components
        self._build_ui(title_incident, initial_desc, test_info)
        self._apply_suggestions()

    def _build_ui(self, title_inc, desc_inc, test_info):
        self.viewLayout.addWidget(self.titleLabel)

        # 1. Navigation Tab
        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("tab_1", "1. Thông tin")
        self.pivot.addItem("tab_2", "2. Nguyên nhân")
        self.pivot.addItem("tab_3", "3. Khắc phục")
        self.pivot.addItem("tab_4", "4. Đánh giá")
        self.pivot.setCurrentItem("tab_1")
        self.viewLayout.addWidget(self.pivot)
        self.viewLayout.addSpacing(10)

        # 2. Content Area
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.container = QWidget()
        self.content_lay = QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)
        self.viewLayout.addWidget(self.scroll)

        # Khởi tạo các trang nội dung
        self._init_page_info(title_inc, desc_inc, test_info)
        self._init_page_root_cause()
        self._init_page_actions()
        self._init_page_verify()

        self.pivot.currentItemChanged.connect(self._on_tab_changed)
        # Thêm nút In/Xuất vào thanh nút bấm của Dialog
        self.btn_print = PushButton(FIF.PRINT, "In phiếu nhanh", self)
        self.btn_print.setFixedWidth(150)
        self.btn_print.clicked.connect(self._print_current)

        # Chèn vào layout nút bấm (MessageBoxBase hỗ trợ custom layout)
        self.viewLayout.addWidget(self.btn_print)

    def _print_current(self):
        """Xuất PDF nhanh từ dữ liệu đang nhập trên form"""
        data = self.get_data()  # Lấy dữ liệu từ các ô nhập liệu

        path, _ = QFileDialog.getSaveFileName(
            self, "In nhanh PDF", f"Phieu_CAPA_Nhanh.pdf", "PDF Files (*.pdf)"
        )
        if path:
            from app.services.capa_export_service import CapaExportService
            success, msg = CapaExportService().export_pdf(data, path)
            if success:
                InfoBar.success("Thành công", "Đã in phiếu PDF thành công.", parent=self)

    def _create_card(self, title):
        card = SimpleCardWidget(self)
        lay = QVBoxLayout(card)
        lay.addWidget(StrongBodyLabel(title, self))
        return card, lay

    def _init_page_info(self, title_inc, desc_inc, test_info):
        self.page_info = QWidget()
        l = QVBoxLayout(self.page_info)

        grid = QGridLayout()
        self.txt_title = LineEdit();
        self.txt_title.setText(title_inc)
        self.cb_risk = ComboBox();
        self.cb_risk.addItems(["Low", "Medium", "High", "Critical"])
        self.txt_test_info = LineEdit();
        self.txt_test_info.setText(test_info);
        self.txt_test_info.setReadOnly(True)

        grid.addWidget(BodyLabel("Tiêu đề:"), 0, 0);
        grid.addWidget(self.txt_title, 0, 1)
        grid.addWidget(BodyLabel("Rủi ro:"), 0, 2);
        grid.addWidget(self.cb_risk, 0, 3)
        grid.addWidget(BodyLabel("Đối tượng:"), 1, 0);
        grid.addWidget(self.txt_test_info, 1, 1, 1, 3)

        l.addLayout(grid)
        l.addWidget(BodyLabel("Mô tả sự cố:"))
        self.txt_desc = TextEdit();
        self.txt_desc.setText(desc_inc);
        self.txt_desc.setFixedHeight(100)
        l.addWidget(self.txt_desc)

        self.content_lay.addWidget(self.page_info)

    def _init_page_root_cause(self):
        self.page_root = QWidget();
        self.page_root.hide()
        l = QVBoxLayout(self.page_root)

        card, cl = self._create_card("Phân tích Nguyên nhân gốc rễ (RCA)")
        self.cb_cause_suggest = ComboBox();
        self.cb_cause_suggest.setPlaceholderText("Gợi ý nguyên nhân...")
        self.cb_cause_suggest.currentTextChanged.connect(lambda t: self.txt_root_cause.insertPlainText(t + "\n"))

        self.txt_root_cause = TextEdit();
        self.txt_root_cause.setPlaceholderText("Phân tích chi tiết tại đây...")
        cl.addWidget(BodyLabel("Chọn từ danh mục gợi ý:"))
        cl.addWidget(self.cb_cause_suggest)
        cl.addWidget(self.txt_root_cause)

        l.addWidget(card);
        self.content_lay.addWidget(self.page_root)

    def _init_page_actions(self):
        self.page_action = QWidget();
        self.page_action.hide()
        l = QVBoxLayout(self.page_action)

        c1, l1 = self._create_card("Hành động Khắc phục (Correction)")
        self.cb_act_suggest = ComboBox();
        self.cb_act_suggest.setPlaceholderText("Gợi ý hành động...")
        self.cb_act_suggest.currentTextChanged.connect(lambda t: self.txt_correction.insertPlainText(t + "\n"))
        self.txt_correction = TextEdit();
        self.txt_correction.setFixedHeight(80)
        l1.addWidget(self.cb_act_suggest);
        l1.addWidget(self.txt_correction)

        c2, l2 = self._create_card("Hành động Phòng ngừa (Preventive)")
        self.txt_preventive = TextEdit();
        self.txt_preventive.setFixedHeight(80)
        l2.addWidget(self.txt_preventive)

        # Deadline
        h = QHBoxLayout()
        self.dt_due = DateEdit();
        self.dt_due.setDate(QDate.currentDate().addDays(7))
        self.txt_owner = LineEdit();
        self.txt_owner.setPlaceholderText("Người phụ trách")
        h.addWidget(BodyLabel("Hạn chót:"));
        h.addWidget(self.dt_due)
        h.addWidget(BodyLabel("Chịu trách nhiệm:"));
        h.addWidget(self.txt_owner)
        l2.addLayout(h)

        l.addWidget(c1);
        l.addWidget(c2)
        self.content_lay.addWidget(self.page_action)

    def _init_page_verify(self):
        self.page_verify = QWidget();
        self.page_verify.hide()
        l = QVBoxLayout(self.page_verify)
        c, cl = self._create_card("Đánh giá hiệu quả")
        self.txt_verify = TextEdit();
        self.txt_verify.setPlaceholderText("Bằng chứng/Kết quả sau khi thực hiện...")
        self.cb_status = ComboBox();
        self.cb_status.addItems(["Open", "In-Progress", "Closed"])

        cl.addWidget(self.txt_verify)
        h = QHBoxLayout();
        h.addWidget(BodyLabel("Trạng thái hồ sơ:"));
        h.addWidget(self.cb_status)
        cl.addLayout(h)

        l.addWidget(c);
        self.content_lay.addWidget(self.page_verify)

    def _on_tab_changed(self, k):
        self.page_info.setVisible(k == "tab_1")
        self.page_root.setVisible(k == "tab_2")
        self.page_action.setVisible(k == "tab_3")
        self.page_verify.setVisible(k == "tab_4")

    def _apply_suggestions(self):
        data = SUGGESTIONS.get(self.source, SUGGESTIONS["ALERTS"])
        self.cb_cause_suggest.addItems([""] + data["causes"])
        self.cb_act_suggest.addItems([""] + data["actions"])

    def get_data(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "title": self.txt_title.text(),
            "description": self.txt_desc.toPlainText(),
            "risk_level": self.cb_risk.currentText(),
            "root_cause": self.txt_root_cause.toPlainText(),
            "correction": self.txt_correction.toPlainText(),
            "preventive_action": self.txt_preventive.toPlainText(),
            "due_date": self.dt_due.date().toString("yyyy-MM-dd"),
            "owner": self.txt_owner.text(),
            "status": self.cb_status.currentText(),
            "verify_note": self.txt_verify.toPlainText(),
            "test_info": self.txt_test_info.text()
        }