# -*- coding: utf-8 -*-
"""
app/features/capa/capa_page.py
(WIN11 FLUENT DESIGN - PROFESSIONAL CAPA MANAGEMENT)
FIXED VERSION:
- Đồng bộ hoàn toàn với Database Service (corrective, verify_evidence).
- Tích hợp tính năng Xuất file (Word/Excel/PDF) qua Menu chuột phải VÀ Toolbar.
- Sửa lỗi icon FIF.WORD -> FIF.DOCUMENT.
"""
import shutil
import os
import datetime as dt
from typing import Optional, Dict
import pandas as pd

# --- IMPORTS TỪ THƯ VIỆN BÊN NGOÀI ---
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem,
    QGridLayout, QScrollArea, QMenu, QListWidget, QListWidgetItem, QFileDialog
)
from PySide6.QtGui import QColor

# --- FLUENT UI IMPORTS ---
from qfluentwidgets import (
    TableWidget, PrimaryPushButton, PushButton, ComboBox,
    SearchLineEdit, FluentIcon as FIF, InfoBadge,
    StrongBodyLabel, CardWidget, SubtitleLabel, BodyLabel,
    MessageBoxBase, LineEdit, TextEdit, DateEdit,
    SegmentedWidget, InfoBar, InfoBarPosition, SimpleCardWidget,
    DropDownPushButton, RoundMenu, Action  # <--- Thêm các widget cho nút DropDown
)

# --- IMPORTS TỪ PROJECT ---
from app.services.capa_service import CapaService

# Import Export Service (Xử lý trường hợp chưa có file để tránh crash)
try:
    from app.services.capa_export_service import CapaExportService
except ImportError:
    CapaExportService = None


# =============================================================================
# 1. DIALOG CHI TIẾT CAPA (TABBED FORM)
# =============================================================================
class CapaDetailDialog(MessageBoxBase):
    def __init__(self, parent=None, data: Optional[Dict] = None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Chi tiết CAPA", self)

        # Khởi tạo Service
        self.service = CapaService()

        # Dữ liệu đang sửa (nếu có)
        self.data = data or {}

        # Tăng kích thước dialog
        self.widget.setMinimumWidth(850)
        self.widget.setMinimumHeight(650)

        # Cấu hình nút bấm mặc định của MessageBoxBase
        self.yesButton.setText("Lưu Hồ sơ")
        self.cancelButton.setText("Đóng")

        # Ngắt kết nối mặc định và gán hàm xử lý mới cho nút Lưu
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self._on_save_clicked)

        self._build_ui()
        self._load_data()
        self._refresh_attachments()

    def _build_ui(self):
        # 1. Header & Navigation
        self.viewLayout.addWidget(self.titleLabel)

        # Thanh điều hướng Tab
        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("tab_info", "1. Thông tin chung")
        self.pivot.addItem("tab_root", "2. Phân tích nguyên nhân")
        self.pivot.addItem("tab_action", "3. Kế hoạch hành động")
        self.pivot.addItem("tab_verify", "4. Đánh giá hiệu quả")
        self.pivot.setCurrentItem("tab_info")

        self.viewLayout.addWidget(self.pivot)
        self.viewLayout.addSpacing(10)

        # 2. Stacked Content (Nội dung cuộn)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.content_widget = QWidget()
        self.form_layout = QVBoxLayout(self.content_widget)
        self.form_layout.setSpacing(20)

        self.scroll.setWidget(self.content_widget)
        self.viewLayout.addWidget(self.scroll)

        # Signal chuyển tab
        self.pivot.currentItemChanged.connect(self._on_tab_changed)

        # Khởi tạo các trang con
        self._init_page_info()
        self._init_page_root()
        self._init_page_action()
        self._init_page_verify()

        # Nút Phê duyệt (Chỉ hiện khi chưa khóa)
        self.btn_approve = PushButton(FIF.ACCEPT, "Phê duyệt & Khóa hồ sơ", self)
        self.btn_approve.setStyleSheet("""
            PushButton { color: white; background-color: #28a745; font-weight: bold; border-radius: 4px; padding: 8px; }
            PushButton:hover { background-color: #218838; }
        """)
        self.btn_approve.clicked.connect(self._handle_approve)
        self.viewLayout.addWidget(self.btn_approve)

        # Logic hiển thị trạng thái Khóa
        is_locked = self.data.get("is_locked") == 1
        if is_locked:
            self._set_widgets_enabled(False)
            self.btn_approve.hide()
            self.yesButton.setEnabled(False)  # Khóa nút Lưu
            self.titleLabel.setText(f"📋 HỒ SƠ ĐÃ KHÓA (Duyệt bởi: {self.data.get('approved_by', 'N/A')})")

    def _set_widgets_enabled(self, is_enabled: bool):
        """
        Khóa/Mở form thông minh:
        - is_enabled = False (Khóa): Các ô nhập liệu bị khóa, NHƯNG vẫn xem được file.
        """
        # 1. Danh sách các widget nhập liệu cần khóa
        widgets_to_lock = [
            # Tab 1
            self.txt_title, self.cb_source, self.cb_severity, self.cb_probability, self.txt_desc,
            # Tab 2
            self.cb_method, self.txt_root_cause,
            # Tab 3
            self.txt_correction, self.txt_corrective, self.dt_due, self.txt_owner,
            # Tab 4
            self.txt_verify, self.cb_status
        ]

        for w in widgets_to_lock:
            # Nếu là ô nhập văn bản -> Chuyển sang chế độ "Chỉ đọc" (vẫn copy được text)
            if hasattr(w, 'setReadOnly'):
                w.setReadOnly(not is_enabled)
            # Nếu là ComboBox, DateEdit -> Vô hiệu hóa
            else:
                w.setEnabled(is_enabled)

        # 2. Xử lý riêng phần File đính kèm
        # LUÔN LUÔN CHO PHÉP tương tác với danh sách file (để click đúp xem)
        self.list_attachments.setEnabled(True)

        # Nhưng ẨN nút "Thêm file" đi nếu hồ sơ đã khóa
        self.btn_add_file.setVisible(is_enabled)

    def _create_section(self, title):
        card = SimpleCardWidget(self)
        lay = QVBoxLayout(card)
        lay.addWidget(StrongBodyLabel(title, self))
        return card, lay

    # --- TAB 1: INFO (ĐÃ NÂNG CẤP LOGIC RỦI RO) ---
    def _init_page_info(self):
        self.page_info = QWidget()
        l = QVBoxLayout(self.page_info)
        l.setContentsMargins(0, 0, 0, 0)

        # Row 1: ID & Title
        grid = QGridLayout()
        self.txt_id = LineEdit()
        self.txt_id.setPlaceholderText("Mã CAPA (Tự động)")
        self.txt_id.setReadOnly(True)
        self.txt_title = LineEdit()
        self.txt_title.setPlaceholderText("Tiêu đề sự cố...")

        grid.addWidget(BodyLabel("Mã số:", self), 0, 0)
        grid.addWidget(self.txt_id, 0, 1)
        grid.addWidget(BodyLabel("Tiêu đề:", self), 0, 2)
        grid.addWidget(self.txt_title, 0, 3)

        # Row 2: Source & Risk Inputs
        self.cb_source = ComboBox()
        self.cb_source.addItems(
            ["IQC Failure", "EQA Failure", "Internal Audit", "Customer Complaint", "Risk Assessment"])

        # 1. Severity (Mức độ nghiêm trọng)
        self.cb_severity = ComboBox()
        self.cb_severity.addItems([
            "1 - Không đáng kể",
            "2 - Nhẹ (Ảnh hưởng ít)",
            "3 - Vừa (Ảnh hưởng kết quả)",
            "4 - Nặng (Sai sót lâm sàng)",
            "5 - Thảm họa (Ngừng hoạt động)"
        ])
        self.cb_severity.currentIndexChanged.connect(self._calculate_risk)

        # 2. Probability (Khả năng xảy ra)
        self.cb_probability = ComboBox()
        self.cb_probability.addItems([
            "1 - Hiếm khi (<1 lần/năm)",
            "2 - Ít gặp (1 lần/năm)",
            "3 - Thỉnh thoảng (1 lần/tháng)",
            "4 - Thường xuyên (1 lần/tuần)",
            "5 - Rất thường xuyên (Hàng ngày)"
        ])
        self.cb_probability.currentIndexChanged.connect(self._calculate_risk)

        grid.addWidget(BodyLabel("Nguồn gốc:", self), 1, 0)
        grid.addWidget(self.cb_source, 1, 1)
        grid.addWidget(BodyLabel("Mức độ nghiêm trọng (S):", self), 1, 2)
        grid.addWidget(self.cb_severity, 1, 3)
        grid.addWidget(BodyLabel("Khả năng xảy ra (P):", self), 2, 2)
        grid.addWidget(self.cb_probability, 2, 3)

        # Row 3: Kết quả tính toán (Risk Level)
        # Ô này sẽ bị khóa, máy tự điền kết quả
        self.cb_risk = LineEdit()
        self.cb_risk.setReadOnly(True)
        self.cb_risk.setPlaceholderText("Máy tự tính...")

        grid.addWidget(BodyLabel("==> Mức độ Rủi ro:", self), 3, 2)
        grid.addWidget(self.cb_risk, 3, 3)

        l.addLayout(grid)

        l.addWidget(BodyLabel("Mô tả chi tiết sự cố:", self))
        self.txt_desc = TextEdit()
        self.txt_desc.setPlaceholderText("Mô tả chi tiết...")
        self.txt_desc.setFixedHeight(100)
        l.addWidget(self.txt_desc)

        self.form_layout.addWidget(self.page_info)

        # Chỉ gọi tính toán nếu đang tạo mới, nếu load data thì để load data xử lý
        if not self.data:
            self._calculate_risk()

    def _calculate_risk(self):
        """
        Thuật toán Ma trận rủi ro (Risk Matrix 5x5)
        Score = S * P
        """
        # Lấy giá trị index (0-4) cộng thêm 1 để ra điểm (1-5)
        s_score = self.cb_severity.currentIndex() + 1
        p_score = self.cb_probability.currentIndex() + 1

        total_score = s_score * p_score
        result_text = ""
        color = ""

        if total_score <= 4:
            result_text = "Low"
            color = "#28a745"  # Xanh lá
        elif total_score <= 9:
            result_text = "Medium"
            color = "#ffc107"  # Vàng
        elif total_score <= 16:
            result_text = "High"
            color = "#fd7e14"  # Cam
        else:
            result_text = "Critical"
            color = "#dc3545"  # Đỏ

        # Hiển thị kết quả
        self.cb_risk.setText(result_text)
        # Tô màu chữ để cảnh báo
        self.cb_risk.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")

    # --- TAB 2: ROOT CAUSE ---
    def _init_page_root(self):
        self.page_root = QWidget()
        l = QVBoxLayout(self.page_root)
        self.page_root.hide()

        card, c_lay = self._create_section("Phân tích nguyên nhân (RCA)")

        # Thêm phần chọn phương pháp
        h_method = QHBoxLayout()
        h_method.addWidget(BodyLabel("Phương pháp:", self))
        self.cb_method = ComboBox()
        self.cb_method.addItems(["5 Whys", "Fishbone", "FMEA", "Khác"])
        h_method.addWidget(self.cb_method)
        h_method.addStretch()
        c_lay.addLayout(h_method)

        c_lay.addWidget(BodyLabel("Chi tiết phân tích:", self))
        self.txt_root_cause = TextEdit()
        self.txt_root_cause.setPlaceholderText("Tại sao sự cố xảy ra?...")
        self.txt_root_cause.setFixedHeight(120)
        c_lay.addWidget(self.txt_root_cause)
        l.addWidget(card)
        self.form_layout.addWidget(self.page_root)

    # --- TAB 3: ACTION ---
    def _init_page_action(self):
        self.page_action = QWidget()
        l = QVBoxLayout(self.page_action)
        self.page_action.hide()

        # Khắc phục ngay
        c1, l1 = self._create_section("Hành động Khắc phục (Correction)")
        self.txt_correction = TextEdit()
        self.txt_correction.setPlaceholderText("Xử lý ngay lập tức...")
        self.txt_correction.setFixedHeight(60)
        l1.addWidget(self.txt_correction)
        l.addWidget(c1)

        # Phòng ngừa
        c2, l2 = self._create_section("Hành động Phòng ngừa (Corrective Action)")
        self.txt_corrective = TextEdit()
        self.txt_corrective.setPlaceholderText("Ngăn chặn tái diễn...")
        self.txt_corrective.setFixedHeight(80)
        l2.addWidget(self.txt_corrective)

        h = QHBoxLayout()
        self.dt_due = DateEdit()
        self.dt_due.setDate(QDate.currentDate().addDays(7))
        self.txt_owner = LineEdit()
        self.txt_owner.setPlaceholderText("Người phụ trách")

        h.addWidget(BodyLabel("Hạn chót:", self))
        h.addWidget(self.dt_due)
        h.addWidget(BodyLabel("Phụ trách:", self))
        h.addWidget(self.txt_owner)
        l2.addLayout(h)
        l.addWidget(c2)
        self.form_layout.addWidget(self.page_action)

    # --- TAB 4: VERIFY ---
    def _init_page_verify(self):
        self.page_verify = QWidget()
        l = QVBoxLayout(self.page_verify)
        self.page_verify.hide()

        c, cl = self._create_section("Đánh giá & Đóng hồ sơ")
        self.txt_verify = TextEdit()
        self.txt_verify.setFixedHeight(80)
        self.txt_verify.setPlaceholderText("Minh chứng hiệu quả...")
        cl.addWidget(self.txt_verify)

        h = QHBoxLayout()
        h.addWidget(BodyLabel("Trạng thái:", self))
        self.cb_status = ComboBox()
        self.cb_status.addItems(["Open", "In Progress", "Verification Pending", "Closed"])
        h.addWidget(self.cb_status)
        cl.addLayout(h)
        l.addWidget(c)

        # Phần đính kèm file
        self._init_attachment_ui(l)
        l.addStretch()
        self.form_layout.addWidget(self.page_verify)

    def _on_tab_changed(self, k):
        self.page_info.setVisible(k == "tab_info")
        self.page_root.setVisible(k == "tab_root")
        self.page_action.setVisible(k == "tab_action")
        self.page_verify.setVisible(k == "tab_verify")

    def _init_attachment_ui(self, parent_layout):
        card, lay = self._create_section("📁 Minh chứng đính kèm")
        self.list_attachments = QListWidget()
        self.list_attachments.setFixedHeight(100)
        self.list_attachments.itemDoubleClicked.connect(self._open_file)

        self.btn_add_file = PushButton(FIF.ADD, "Thêm file", self)
        self.btn_add_file.clicked.connect(self._on_add_file_clicked)

        lay.addWidget(self.list_attachments)
        lay.addWidget(self.btn_add_file)
        parent_layout.addWidget(card)

    def _on_add_file_clicked(self):
        capa_id = self.txt_id.text()
        if not capa_id or "Tự động" in capa_id:
            InfoBar.warning("Lỗi", "Cần lưu hồ sơ trước khi đính kèm file.", parent=self)
            return
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file", "", "All Files (*.*)")
        if path:
            if self.service.add_attachment(capa_id, path):
                self._refresh_attachments()
                InfoBar.success("Xong", "Đã tải file lên.", parent=self)

    def _refresh_attachments(self):
        self.list_attachments.clear()
        capa_id = self.txt_id.text()
        if not capa_id or "Tự động" in capa_id: return
        files = self.service.get_attachments(capa_id)
        for f in files:
            icon = FIF.DOCUMENT.icon()
            if f['file_name'].lower().endswith(('.png', '.jpg')): icon = FIF.PHOTO.icon()
            self.list_attachments.addItem(QListWidgetItem(icon, f['file_name']))

    def _open_file(self, item):
        capa_id = self.txt_id.text()
        path = os.path.abspath(os.path.join("data", "attachments", capa_id, item.text()))
        if os.path.exists(path): os.startfile(path)

    # --- QUAN TRỌNG: LOGIC LOAD/SAVE DỮ LIỆU ---

    def _load_data(self):
        """Đổ dữ liệu từ DB vào Form"""
        if not self.data: return

        self.txt_id.setText(str(self.data.get("capa_id", "")))
        self.txt_title.setText(self.data.get("title", ""))
        self.cb_source.setCurrentText(self.data.get("source", "IQC Failure"))

        # Dùng setText cho LineEdit Rủi ro
        risk = self.data.get("risk_level", "Medium")
        self.cb_risk.setText(risk)

        self.txt_desc.setText(self.data.get("description", ""))
        self.txt_root_cause.setText(self.data.get("root_cause", ""))
        self.txt_correction.setText(self.data.get("correction", ""))

        # KEY CHUẨN ĐÂY: Dùng corrective và verify_evidence để khớp với DB
        self.txt_corrective.setText(self.data.get("corrective", ""))
        self.txt_verify.setText(self.data.get("verify_evidence", ""))

        self.txt_owner.setText(self.data.get("owner", ""))
        self.cb_status.setCurrentText(self.data.get("status", "Open"))

        d_str = self.data.get("due_date", "")
        if d_str:
            self.dt_due.setDate(QDate.fromString(d_str, "yyyy-MM-dd"))

    def _get_data(self):
        """Thu thập dữ liệu từ Form"""
        return {
            "capa_id": self.txt_id.text(),
            "title": self.txt_title.text(),
            "source": self.cb_source.currentText(),

            # Dùng text() cho LineEdit Rủi ro
            "risk_level": self.cb_risk.text(),

            "owner": self.txt_owner.text(),
            "due_date": self.dt_due.date().toString("yyyy-MM-dd"),
            "description": self.txt_desc.toPlainText(),
            "root_cause": self.txt_root_cause.toPlainText(),
            "correction": self.txt_correction.toPlainText(),
            "corrective": self.txt_corrective.toPlainText(),
            "verify_evidence": self.txt_verify.toPlainText(),
            "status": self.cb_status.currentText()
        }

    def _on_save_clicked(self):
        """Xử lý sự kiện bấm nút Lưu"""
        data = self._get_data()
        capa_id = data.get("capa_id")

        success = False
        # Nếu có ID thực (bắt đầu bằng CP-) thì là Update
        if capa_id and "CP-" in capa_id:
            success = self.service.update_capa(data)
            action = "Cập nhật"
        else:
            # Ngược lại là Create
            success = self.service.create_capa_entry(**data)
            action = "Tạo mới"

        if success:
            InfoBar.success("Thành công", f"Đã {action} hồ sơ CAPA.", parent=self)
            self.accept()  # Đóng dialog
        else:
            InfoBar.error("Lỗi", f"Không thể {action} hồ sơ. Vui lòng kiểm tra lại.", parent=self)

    def _handle_approve(self):
        capa_id = self.txt_id.text()
        if not capa_id: return
        if self.service.approve_capa(capa_id, "Quản lý Lab"):
            InfoBar.success("Xong", "Hồ sơ đã được duyệt và khóa.", parent=self)
            self.accept()


# =============================================================================
# 2. TRANG QUẢN LÝ CHÍNH (CAPA PAGE)
# =============================================================================
class CapaPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = CapaService()

        # Khởi tạo Service Export
        if CapaExportService:
            self.export_service = CapaExportService()
        else:
            self.export_service = None

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Toolbar
        top_card = CardWidget(self)
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(16, 12, 16, 12)
        top_layout.setSpacing(12)

        self.txt_search = SearchLineEdit(self)
        self.txt_search.setPlaceholderText("Tìm kiếm...")
        self.txt_search.textChanged.connect(self._filter_table)
        top_layout.addWidget(self.txt_search)

        self.cb_filter_status = ComboBox()
        self.cb_filter_status.addItems(["Tất cả trạng thái", "Open", "In Progress", "Closed"])
        self.cb_filter_status.currentIndexChanged.connect(self._filter_table)
        top_layout.addWidget(self.cb_filter_status)

        top_layout.addStretch(1)

        self.btn_refresh = PushButton(FIF.SYNC, "Làm mới", self)
        self.btn_refresh.clicked.connect(self._load_data)
        top_layout.addWidget(self.btn_refresh)

        # --- NÚT XUẤT HỒ SƠ (Dạng DropDown) ---
        self.btn_export = DropDownPushButton(FIF.SHARE, "Xuất Hồ Sơ", self)

        menu = RoundMenu(parent=self)

        # --- SỬA LỖI TẠI ĐÂY: Dùng FIF.DOCUMENT thay vì FIF.WORD ---
        act_word = Action(FIF.DOCUMENT, "Xuất Word (.docx)", self)
        act_word.triggered.connect(lambda: self._export_current_selection("word"))

        # Dùng FIF.FOLDER cho Excel (hoặc icon khác có sẵn)
        act_excel = Action(FIF.FOLDER, "Xuất Excel (.xlsx)", self)
        act_excel.triggered.connect(lambda: self._export_current_selection("excel"))

        # Dùng FIF.PRINT cho PDF
        act_pdf = Action(FIF.PRINT, "Xuất PDF (.pdf)", self)
        act_pdf.triggered.connect(lambda: self._export_current_selection("pdf"))

        menu.addActions([act_word, act_excel, act_pdf])
        self.btn_export.setMenu(menu)
        top_layout.addWidget(self.btn_export)
        # ---------------------------------

        self.btn_export_overdue = PushButton(FIF.DOWNLOAD, "Xuất Quá Hạn", self)
        self.btn_export_overdue.clicked.connect(self._on_export_overdue_clicked)
        top_layout.addWidget(self.btn_export_overdue)

        self.btn_new = PrimaryPushButton(FIF.ADD, "Tạo Mới", self)
        self.btn_new.clicked.connect(self._open_new_capa)
        top_layout.addWidget(self.btn_new)

        layout.addWidget(top_card)

        # Table
        self.table = TableWidget(self)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)

        # Kích hoạt menu chuột phải
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        cols = ["Mã CAPA", "Tiêu đề", "Nguồn", "Rủi ro", "Hạn chót", "Trạng thái", "Phụ trách", ""]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.table.doubleClicked.connect(self._open_edit_capa)

        layout.addWidget(self.table)

    def _load_data(self):
        """Tải dữ liệu lên bảng (Table)"""
        self.table.setRowCount(0)
        status = self.cb_filter_status.currentText()
        if status == "Tất cả trạng thái": status = None

        capas = self.service.get_all_capas(status)

        for i, item in enumerate(capas):
            self.table.insertRow(i)

            # Logic check quá hạn
            is_overdue = False
            if item.get("due_date") and item.get("status") != "Closed":
                try:
                    due = dt.datetime.strptime(item["due_date"], "%Y-%m-%d").date()
                    if due < dt.date.today(): is_overdue = True
                except:
                    pass

            id_item = QTableWidgetItem(str(item["capa_id"]))
            if is_overdue:
                id_item.setForeground(QColor("#e74c3c"))
                id_item.setToolTip("Quá hạn!")

            t_item = QTableWidgetItem(item["title"])
            t_item.setData(Qt.ItemDataRole.UserRole, item)  # Lưu data gốc để dùng khi sửa hoặc xuất file

            self.table.setItem(i, 0, id_item)
            self.table.setItem(i, 1, t_item)
            self.table.setItem(i, 2, QTableWidgetItem(item.get("source", "")))
            self.table.setCellWidget(i, 3, self._create_risk_badge(item.get("risk_level", "")))

            due_item = QTableWidgetItem(item.get("due_date", ""))
            if is_overdue: due_item.setForeground(QColor("#e74c3c"))
            self.table.setItem(i, 4, due_item)

            self.table.setCellWidget(i, 5, self._create_status_badge(item.get("status", "")))
            self.table.setItem(i, 6, QTableWidgetItem(item.get("owner", "")))
            self.table.setItem(i, 7, QTableWidgetItem(FIF.EDIT.icon(), ""))

    def _open_new_capa(self):
        dlg = CapaDetailDialog(self)
        if dlg.exec(): self._load_data()

    def _open_edit_capa(self):
        r = self.table.currentRow()
        if r < 0: return
        data = self.table.item(r, 1).data(Qt.ItemDataRole.UserRole)
        dlg = CapaDetailDialog(self, data)
        if dlg.exec(): self._load_data()

    # --- HÀM XỬ LÝ XUẤT FILE TỪ NÚT BẤM ---
    def _export_current_selection(self, file_type):
        """Xuất file cho dòng đang được chọn"""
        row = self.table.currentRow()
        if row < 0:
            InfoBar.warning("Chưa chọn hồ sơ", "Vui lòng click vào một dòng trong bảng trước.", parent=self)
            return

        # Lấy data từ cột 1 (UserRole)
        data_item = self.table.item(row, 1)
        if not data_item: return
        data = data_item.data(Qt.ItemDataRole.UserRole)

        # Gọi hàm chung
        self._handle_export(data, file_type)

    # --- Context Menu (Chuột phải) ---
    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        r = item.row()
        data = self.table.item(r, 1).data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        # SỬA ICON TẠI ĐÂY NỮA
        act_word = menu.addAction(FIF.DOCUMENT.icon(), "Xuất Word")
        act_xls = menu.addAction(FIF.FOLDER.icon(), "Xuất Excel")
        act_pdf = menu.addAction(FIF.PRINT.icon(), "Xuất PDF")

        res = menu.exec(self.table.viewport().mapToGlobal(pos))
        if res == act_word:
            self._handle_export(data, "word")
        elif res == act_xls:
            self._handle_export(data, "excel")
        elif res == act_pdf:
            self._handle_export(data, "pdf")

    # --- Logic chung xuất file ---
    def _handle_export(self, data, type):
        if not self.export_service:
            InfoBar.error("Lỗi", "Chưa cài đặt module Export.", parent=self)
            return

        if type == "excel":
            ext = ".xlsx"; filter_str = "Excel (*.xlsx)"
        elif type == "pdf":
            ext = ".pdf"; filter_str = "PDF (*.pdf)"
        else:
            ext = ".docx"; filter_str = "Word (*.docx)"

        path, _ = QFileDialog.getSaveFileName(self, "Lưu file", f"{data['capa_id']}{ext}", filter_str)
        if path:
            success, msg = False, ""

            # --- FIX QUAN TRỌNG: Gọi đúng tham số của Service ---
            if type == "excel":
                # Excel service cần output_path
                success, msg = self.export_service.export_excel(data, "template_capa.xlsx", output_path=path)
            elif type == "pdf":
                # PDF service cần output_path
                success, msg = self.export_service.export_pdf(data, output_path=path)
            elif type == "word" and hasattr(self.export_service, 'export_word'):
                # Word service dùng save_path
                success, msg = self.export_service.export_word(data, save_path=path)

            if success:
                InfoBar.success("Thành công", msg, parent=self)
                os.startfile(path)
            else:
                InfoBar.error("Lỗi", msg, parent=self)

    # --- Helpers UI ---
    def _create_status_badge(self, status):
        b = InfoBadge.info(status)
        if status == "Closed":
            b = InfoBadge.success("Closed")
        elif status == "Open":
            b = InfoBadge.error("Open")
        w = QWidget();
        l = QHBoxLayout(w);
        l.setContentsMargins(4, 2, 4, 2);
        l.setAlignment(Qt.AlignCenter);
        l.addWidget(b)
        return w

    def _create_risk_badge(self, risk):
        b = InfoBadge.success(risk)
        if risk == "Critical":
            b = InfoBadge.error("Critical")
        elif risk == "High":
            b = InfoBadge.warning("High")
        w = QWidget();
        l = QHBoxLayout(w);
        l.setContentsMargins(4, 2, 4, 2);
        l.setAlignment(Qt.AlignCenter);
        l.addWidget(b)
        return w

    def _filter_table(self):
        txt = self.txt_search.text().lower()
        st = self.cb_filter_status.currentText()
        if st == "Tất cả trạng thái": st = None
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 1)
            data = item.data(Qt.ItemDataRole.UserRole)
            match_txt = txt in item.text().lower() or txt in str(data["capa_id"]).lower()
            match_st = True if not st else data["status"] == st
            self.table.setRowHidden(r, not (match_txt and match_st))

    def showEvent(self, e):
        super().showEvent(e)
        self._check_and_alert_overdue()

    def _check_and_alert_overdue(self):
        c = self.service.get_overdue_count()
        if c > 0: InfoBar.error("Cảnh báo", f"Có {c} hồ sơ quá hạn!", parent=self, duration=5000)

    def _on_export_overdue_clicked(self):
        # Xuất danh sách quá hạn ra Excel
        all_capas = self.service.get_all_capas(None)
        today = dt.date.today()
        overdue_list = []

        for item in all_capas:
            if item["due_date"] and item["status"] != "Closed":
                try:
                    due_date = dt.datetime.strptime(item["due_date"], "%Y-%m-%d").date()
                    if due_date < today:
                        overdue_list.append({
                            "Mã CAPA": item["capa_id"],
                            "Tiêu đề": item["title"],
                            "Hạn chót": item["due_date"],
                            "Trạng thái": item["status"],
                            "Người phụ trách": item["owner"]
                        })
                except:
                    pass

        if not overdue_list:
            InfoBar.info("Thông báo", "Tuyệt vời! Không có hồ sơ nào bị quá hạn.", parent=self)
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu danh sách quá hạn",
                                                   f"Overdue_{today.strftime('%d%m')}.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            try:
                df = pd.DataFrame(overdue_list)
                df.to_excel(file_path, index=False)
                InfoBar.success("Thành công", f"Đã xuất {len(overdue_list)} hồ sơ ra file Excel.", parent=self)
            except Exception as e:
                InfoBar.error("Lỗi", f"Không thể xuất file: {str(e)}", parent=self)