# -*- coding: utf-8 -*-
"""
app/features/alerts/alerts_page.py
TRANG CẢNH BÁO & GIÁM SÁT TRUNG TÂM
(Giao diện Dashboard kết hợp Cảnh báo + CAPA)
FIXED: Sửa lỗi Icon (PROCESSING -> SYNC) và đảm bảo import QSize
"""
import datetime as dt
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QTableWidgetItem, QAbstractItemView
)
from PySide6.QtGui import QColor

# --- SERVICES ---
from app.services.alert_service import AlertService
from app.services.capa_service import CapaService

# --- DIALOGS ---
from app.ui.views.capa.capa_page import CapaDetailDialog

# --- FLUENT WIDGETS ---
from qfluentwidgets import (
    PrimaryPushButton, PushButton, FluentIcon as FIF,
    CardWidget, TableWidget, ComboBox,
    StrongBodyLabel, TitleLabel, BodyLabel, CaptionLabel,
    InfoBar, ToolButton
)


# --- HELPER: Tính thời gian ---
def time_ago(date_obj):
    if not date_obj: return ""
    if isinstance(date_obj, str):
        try:
            date_obj = dt.datetime.fromisoformat(date_obj)
        except:
            try:
                date_obj = dt.datetime.strptime(date_obj, "%Y-%m-%d")
            except:
                return str(date_obj)

    if isinstance(date_obj, dt.date) and not isinstance(date_obj, dt.datetime):
        date_obj = dt.datetime.combine(date_obj, dt.datetime.min.time())

    now = dt.datetime.now()
    diff = now - date_obj
    seconds = diff.total_seconds()

    if seconds < 60: return "Vừa xong"
    if seconds < 3600: return f"{int(seconds // 60)} phút trước"
    if seconds < 86400: return f"{int(seconds // 3600)} giờ trước"
    days = int(seconds // 86400)
    if days < 7: return f"{days} ngày trước"
    return date_obj.strftime("%d/%m/%Y")


# --- WIDGET: THẺ THỐNG KÊ (STAT CARD) ---
class StatCard(CardWidget):
    clicked = Signal()

    def __init__(self, icon, title, value, color, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setCursor(Qt.PointingHandCursor)

        h = QHBoxLayout(self)
        h.setContentsMargins(24, 0, 24, 0)
        h.setSpacing(20)

        # Icon tròn đẹp mắt
        btn_icon = PushButton(icon, "", self)
        btn_icon.setFixedSize(48, 48)
        btn_icon.setIconSize(QSize(24, 24))

        # Style màu nền nhạt + icon đậm
        btn_icon.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {color}1A; /* Màu nhạt 10% */
                color: {color}; 
                border: none; 
                border-radius: 24px; 
            }}
        """)
        btn_icon.clicked.connect(self.clicked.emit)

        # Text Info
        v = QVBoxLayout()
        v.setSpacing(2)
        v.setAlignment(Qt.AlignVCenter)

        self.lbl_val = TitleLabel(str(value), self)
        self.lbl_val.setStyleSheet(f"color: {color}; font-family: 'Segoe UI Variable Display'; font-size: 28px;")

        self.lbl_title = BodyLabel(title, self)
        self.lbl_title.setTextColor(QColor("#606060"), QColor("#d0d0d0"))

        v.addWidget(self.lbl_val)
        v.addWidget(self.lbl_title)

        h.addWidget(btn_icon)
        h.addLayout(v)
        h.addStretch(1)

    def set_value(self, value):
        self.lbl_val.setText(str(value))

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.clicked.emit()


# --- TRANG CHÍNH: ALERTS PAGE ---
class AlertsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alerts_page")

        # Khởi tạo Services
        self.alert_service = AlertService()
        self.capa_service = CapaService()

        self.dismissed_ids = set()  # Lưu các alert đã ẩn

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(30, 30, 30, 30)
        main.setSpacing(24)

        # 1. Header: Chào mừng & Date
        header = QHBoxLayout()
        v_head = QVBoxLayout()
        v_head.setSpacing(4)
        v_head.addWidget(TitleLabel("Trung tâm Cảnh báo & Giám sát", self))
        v_head.addWidget(CaptionLabel(f"Hôm nay: {dt.date.today().strftime('%d tháng %m, %Y')}", self))

        self.btn_refresh = PrimaryPushButton(FIF.SYNC, "Cập nhật dữ liệu", self)
        self.btn_refresh.clicked.connect(self._reload_full)

        header.addLayout(v_head)
        header.addStretch(1)
        header.addWidget(self.btn_refresh)
        main.addLayout(header)

        # 2. Bốn Thẻ Chỉ Số Quan Trọng (Cards)
        cards = QHBoxLayout()
        cards.setSpacing(16)

        # --- FIX ICON: Dùng icon an toàn (Folder, Sync, Calendar, Info) ---
        self.card_total = StatCard(FIF.FOLDER, "Tổng Hồ sơ CAPA", "0", "#0078d4")
        self.card_open = StatCard(FIF.SYNC, "Đang xử lý", "0", "#ffaa00")  # Thay PROCESSING -> SYNC
        self.card_overdue = StatCard(FIF.CALENDAR, "Đã quá hạn", "0", "#d13438")  # Thay HISTORY -> CALENDAR
        self.card_risk = StatCard(FIF.INFO, "Rủi ro Cao", "0", "#ea4300")  # Thay WARNING -> INFO (Màu cam đậm)

        # Click thẻ để lọc nhanh
        self.card_total.clicked.connect(lambda: self._quick_filter("Tất cả"))
        self.card_overdue.clicked.connect(lambda: self._quick_filter("Hồ sơ tồn (CAPA)"))

        cards.addWidget(self.card_total)
        cards.addWidget(self.card_open)
        cards.addWidget(self.card_overdue)
        cards.addWidget(self.card_risk)
        main.addLayout(cards)

        # 3. Bảng "Cảnh báo Nóng" (Hot Alerts)
        v_table = QVBoxLayout()
        v_table.setSpacing(10)

        h_tbl = QHBoxLayout()
        h_tbl.addWidget(StrongBodyLabel("🔥 Tiêu điểm cần xử lý gấp (Cảnh báo & Hồ sơ)", self))
        h_tbl.addStretch()

        self.cb_filter = ComboBox(self)
        self.cb_filter.addItems(["Tất cả", "Sự cố mới (Alerts)", "Hồ sơ tồn (CAPA)"])
        self.cb_filter.currentIndexChanged.connect(self._load_data)
        h_tbl.addWidget(BodyLabel("Lọc:", self))
        h_tbl.addWidget(self.cb_filter)

        v_table.addLayout(h_tbl)

        self.table = TableWidget(self)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Mức độ", "Loại", "Nội dung / Tiêu đề", "Đối tượng / Phụ trách", "Thời gian", "Hành động"])

        # Style Table
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table.setColumnWidth(0, 110)  # Mức độ
        self.table.setColumnWidth(1, 140)  # Loại
        self.table.setColumnWidth(2, 400)  # Nội dung (Rộng nhất)
        self.table.setColumnWidth(3, 200)  # Đối tượng
        self.table.setColumnWidth(4, 120)  # Thời gian
        self.table.horizontalHeader().setStretchLastSection(True)  # Hành động

        v_table.addWidget(self.table)
        main.addLayout(v_table)

    def _reload_full(self):
        self.dismissed_ids.clear()
        self._load_data()
        InfoBar.success("Đã làm mới", "Dữ liệu Dashboard đã được cập nhật.", parent=self)

    def _quick_filter(self, mode):
        self.cb_filter.setCurrentText(mode)

    def _load_data(self):
        # A. Lấy số liệu thống kê CAPA (Cho 4 Cards)
        all_capas = self.capa_service.get_all_capas(None)

        count_total = len(all_capas)
        count_open = 0
        count_overdue = 0
        count_high_risk = 0

        today = dt.date.today()

        urgent_capas = []  # List hồ sơ cần xử lý

        for c in all_capas:
            st = c.get("status", "Open")
            risk = c.get("risk_level", "Medium")
            due_str = c.get("due_date", "")

            # 1. Đếm Open
            if st != "Closed": count_open += 1

            # 2. Đếm Rủi ro cao (Chỉ tính cái chưa đóng)
            if risk in ["Critical", "High"] and st != "Closed":
                count_high_risk += 1

            # 3. Đếm Quá hạn
            is_overdue = False
            if due_str and st != "Closed":
                try:
                    if dt.datetime.strptime(due_str, "%Y-%m-%d").date() < today:
                        count_overdue += 1
                        is_overdue = True
                except:
                    pass

            # Lọc hồ sơ gấp (Quá hạn HOẶC Rủi ro cao)
            if is_overdue or (risk == "Critical" and st != "Closed"):
                c['source_type'] = 'CAPA'
                c['sort_date'] = due_str
                c['is_overdue'] = is_overdue
                urgent_capas.append(c)

        # Update UI Cards
        self.card_total.set_value(count_total)
        self.card_open.set_value(count_open)
        self.card_overdue.set_value(count_overdue)
        self.card_risk.set_value(count_high_risk)

        # B. Lấy dữ liệu Cảnh báo (Alerts) từ Service
        raw_alerts = self.alert_service.get_all_alerts()
        active_alerts = []
        for a in raw_alerts:
            uid = f"{a.get('result_id')}_{a.get('name')}"
            if uid not in self.dismissed_ids:
                a['source_type'] = 'ALERT'
                a['sort_date'] = a.get('date', '')
                active_alerts.append(a)

        # C. Gộp danh sách hiển thị
        final_list = []
        mode = self.cb_filter.currentText()

        if mode == "Tất cả" or mode == "Sự cố mới (Alerts)":
            final_list.extend(active_alerts)
        if mode == "Tất cả" or mode == "Hồ sơ tồn (CAPA)":
            final_list.extend(urgent_capas)

        # Sắp xếp: Ưu tiên Critical trước, sau đó đến ngày
        final_list.sort(key=lambda x: (
            0 if x.get('level') == 'critical' or x.get('risk_level') == 'Critical' else 1,
            x.get('sort_date', '')
        ))

        # Render Table
        self.table.setRowCount(0)
        for i, item in enumerate(final_list):
            self.table.insertRow(i)
            self._render_row(i, item)

    def _render_row(self, row, item):
        source = item.get('source_type')

        # 1. Badge Mức độ
        is_crit = False
        level_text = "Trung bình"

        if source == 'ALERT':
            is_crit = (item.get('level') == 'critical')
            level_text = "Nghiêm trọng" if is_crit else "Cảnh báo"
        else:  # CAPA
            is_crit = (item.get('risk_level') == 'Critical' or item.get('is_overdue'))
            level_text = "Quá hạn" if item.get('is_overdue') else item.get('risk_level')

        bg = "#f8d7da" if is_crit else "#fff3cd"
        fg = "#721c24" if is_crit else "#856404"
        self._set_badge(row, 0, level_text, bg, fg)

        # 2. Loại
        type_str = item.get('type') if source == 'ALERT' else "Hồ sơ CAPA"
        self.table.setItem(row, 1, QTableWidgetItem(type_str))

        # 3. Nội dung
        msg = item.get('message') if source == 'ALERT' else item.get('title')
        self.table.setItem(row, 2, QTableWidgetItem(msg))

        # 4. Đối tượng
        target = item.get('name') if source == 'ALERT' else item.get('owner')
        self.table.setItem(row, 3, QTableWidgetItem(target))

        # 5. Thời gian
        date_val = item.get('date') if source == 'ALERT' else item.get('due_date')
        self.table.setItem(row, 4, QTableWidgetItem(time_ago(date_val)))

        # 6. Hành động
        self._set_action_buttons(row, 5, item, source)

    def _set_badge(self, row, col, text, bg, fg):
        container = QWidget()
        l = QHBoxLayout(container)
        l.setContentsMargins(5, 5, 5, 5)
        l.setAlignment(Qt.AlignLeft)
        lbl = PushButton(text, self)
        lbl.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: none; border-radius: 4px; padding: 4px 8px; font-weight: bold;")
        lbl.setFixedHeight(26)
        l.addWidget(lbl)
        self.table.setCellWidget(row, col, container)

    def _set_action_buttons(self, row, col, item, source):
        container = QWidget()
        l = QHBoxLayout(container)
        l.setContentsMargins(0, 2, 0, 2)
        l.setSpacing(8)
        l.setAlignment(Qt.AlignLeft)

        if source == 'ALERT':
            # Nút Ghi CAPA (Xanh)
            btn1 = PrimaryPushButton(FIF.EDIT, "Ghi CAPA", self)
            btn1.setFixedWidth(110)
            btn1.clicked.connect(lambda: self._open_create_capa(item))
            l.addWidget(btn1)

            # Nút Ẩn (Xám)
            btn2 = ToolButton(FIF.CLOSE, self)
            btn2.setToolTip("Bỏ qua cảnh báo này")
            btn2.clicked.connect(lambda: self._dismiss_alert(item))
            l.addWidget(btn2)

        else:  # CAPA Record
            # Nút Xem/Xử lý (Cam)
            btn1 = PushButton(FIF.VIEW, "Xử lý ngay", self)
            btn1.setFixedWidth(110)
            btn1.clicked.connect(lambda: self._open_edit_capa(item))
            l.addWidget(btn1)

        self.table.setCellWidget(row, col, container)

    # --- ACTIONS ---
    def _open_create_capa(self, alert_item):
        """Mở form tạo mới CAPA với dữ liệu điền sẵn từ Alert"""
        prefill = {
            "title": f"Sự cố: {alert_item.get('name')}",
            "source": "IQC Failure" if "Westgard" in alert_item.get('type', '') else "Risk Assessment",
            "description": f"Cảnh báo hệ thống:\n- {alert_item.get('message', '')}\n- Thời gian: {alert_item.get('date')}",
            "risk_level": "Critical" if alert_item.get('level') == 'critical' else "High",
            "owner": "Administrator",
            "status": "Open",
            "due_date": dt.date.today().strftime("%Y-%m-%d")
        }

        dlg = CapaDetailDialog(self, prefill)
        if dlg.exec():
            InfoBar.success("Đã ghi nhận", "Hồ sơ CAPA mới đã được tạo từ cảnh báo.", parent=self)
            self._dismiss_alert(alert_item)  # Tự động ẩn alert sau khi xử lý xong
            self._load_data()  # Reload để cập nhật số liệu Cards

    def _open_edit_capa(self, capa_item):
        """Mở form sửa hồ sơ CAPA có sẵn"""
        dlg = CapaDetailDialog(self, capa_item)
        if dlg.exec():
            self._load_data()  # Cập nhật lại nếu có thay đổi trạng thái

    def _dismiss_alert(self, item):
        uid = f"{item.get('result_id')}_{item.get('name')}"
        self.dismissed_ids.add(uid)
        self._load_data()