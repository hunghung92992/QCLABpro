# -*- coding: utf-8 -*-
"""
app/features/calendar/event_calendar_page.py
(WIN11 FLUENT DESIGN - LIGHT/DARK MODE SUPPORT - BUG FIXED)
"""
import datetime as dt
from typing import List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCalendarWidget,
    QFrame, QScrollArea, QDialog, QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt, QDate, QPoint, Signal
from PySide6.QtGui import QColor, QPainter, QFont

# --- FLUENT UI IMPORTS ---
from qfluentwidgets import (
    CardWidget, SimpleCardWidget, PrimaryPushButton, PushButton,
    FluentIcon as FIF, StrongBodyLabel, BodyLabel, CaptionLabel,
    SubtitleLabel, InfoBar, CheckBox, ComboBox, LineEdit,
    TextEdit, TimeEdit, qconfig, isDarkTheme, themeColor
)

from app.services.calendar_service import CalendarService, EVENT_TYPES


# --- 1. WIDGET LỊCH TÙY BIẾN (Adaptive Theme) ---
class MasterCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.events_map = {}  # {QDate: [list of colors]}

        # Cấu hình cơ bản
        self.setGridVisible(False)
        self.setNavigationBarVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)

        # Áp dụng style lần đầu
        self.updateStyle()

        # Lắng nghe sự kiện đổi theme từ hệ thống (nếu qfluentwidgets được cấu hình đúng)
        qconfig.themeChanged.connect(self.updateStyle)

    def updateStyle(self):
        """Cập nhật CSS dựa trên chế độ Sáng/Tối"""
        if isDarkTheme():
            bg_color = "#202020"  # Màu nền tối (Mica)
            alt_bg = "#2d2d2d"  # Màu nền ô ngày
            text_color = "#ffffff"
            hover_bg = "#3e3e3e"
            select_bg = themeColor().name()  # Lấy màu chủ đạo của hệ thống
            nav_color = "#ffffff"
        else:
            bg_color = "#ffffff"
            alt_bg = "#f9f9f9"
            text_color = "#000000"
            hover_bg = "#e0e0e0"
            select_bg = "#e3f2fd"
            nav_color = "#333333"

        # CSS Tinh chỉnh cho giống Win11 Calendar
        # LƯU Ý: Đã bỏ đi đường dẫn file SVG ảo để tránh rác log (Phase 4.2)
        self.setStyleSheet(f"""
            QCalendarWidget QWidget {{ 
                background-color: {bg_color}; 
                alternate-background-color: {alt_bg}; 
                color: {text_color};
            }}
            QAbstractItemView:enabled {{ 
                font-family: 'Segoe UI'; font-size: 14px; color: {text_color};  
                selection-background-color: {select_bg}; 
                selection-color: {text_color if not isDarkTheme() else '#ffffff'};
                border-radius: 6px;
                outline: none;
            }}
            QAbstractItemView:disabled {{ color: #888888; }}
            QToolButton {{ 
                color: {nav_color}; font-weight: bold; icon-size: 24px; 
                background: transparent; border: none; padding: 5px;
                border-radius: 4px;
            }}
            QToolButton:hover {{ background-color: {hover_bg}; }}
            QSpinBox {{ 
                background: transparent; color: {text_color}; 
                font-size: 16px; font-weight: bold; border: none; selection-background-color: transparent;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 0; }} /* Ẩn nút spin */
        """)

    def update_events(self, events: List[Dict]):
        self.events_map = {}
        for e in events:
            d = e['date']
            qd = QDate(d.year, d.month, d.day)
            if qd not in self.events_map: self.events_map[qd] = []
            if e['color'] not in self.events_map[qd]:
                self.events_map[qd].append(e['color'])

        # [PHASE 4.3 KHẮC PHỤC LỖI QCalendarWidget::updateCell: Invalid date]
        # Xóa dòng self.updateCell(QDate()) gây lỗi, thay bằng update() để vẽ lại toàn bộ widget
        self.update()

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        if date in self.events_map:
            colors = self.events_map[date]
            dot_size = 6
            spacing = 4
            total_width = (len(colors) * dot_size) + ((len(colors) - 1) * spacing)
            start_x = rect.center().x() - (total_width / 2)
            y = rect.bottom() - 10

            painter.setPen(Qt.NoPen)
            for i, col in enumerate(colors[:4]):  # Max 4 dots
                painter.setBrush(QColor(col))
                painter.drawEllipse(QPoint(int(start_x + i * (dot_size + spacing) + dot_size / 2), y), 3, 3)


# --- 2. WIDGET SỰ KIỆN (Fluent Card) ---
class EventCardItem(SimpleCardWidget):
    """Sử dụng SimpleCardWidget để tự động có border/shadow/color chuẩn Win11"""

    def __init__(self, event: Dict):
        super().__init__()
        self.event = event
        self._setup_ui()

    def _setup_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Thanh màu trạng thái bên trái
        color_strip = QFrame()
        color_strip.setFixedWidth(4)
        color_strip.setStyleSheet(
            f"background-color: {self.event.get('color', '#0078D7')}; border-top-left-radius: 4px; border-bottom-left-radius: 4px;")
        lay.addWidget(color_strip)

        # Nội dung chính
        content_widget = QWidget()
        v_lay = QVBoxLayout(content_widget)
        v_lay.setContentsMargins(12, 10, 12, 10)
        v_lay.setSpacing(4)

        # Row 1: Time + Status Badge
        h1 = QHBoxLayout()

        # Icon + Time
        icon_char = self.event.get('icon', '📅')
        time_lbl = CaptionLabel(f"{icon_char} {self.event.get('time_str', '--:--')}", self)
        time_lbl.setTextColor(QColor("#666666") if not isDarkTheme() else QColor("#aaaaaa"), QColor("#aaaaaa"))
        h1.addWidget(time_lbl)
        h1.addStretch()

        # Status Logic
        today = dt.date.today()
        # [SỬA LỖI TIỀM ẨN]: Đảm bảo event['date'] luôn là kiểu dt.date trước khi trừ
        event_date = self.event.get('date', today)
        if isinstance(event_date, str):
            try:
                event_date = dt.date.fromisoformat(event_date)
            except:
                event_date = today

        days = (event_date - today).days
        status_text, bg_col, txt_col = "", "", "#ffffff"

        if self.event.get('status') == 'DONE':
            status_text, bg_col = "ĐÃ XONG", "#107C10"
        elif days < 0:
            status_text, bg_col = "QUÁ HẠN", "#C50F1F"
        elif 0 <= days <= 3:
            status_text, bg_col, txt_col = f"CÒN {days} NGÀY", "#FFD700", "#000000"

        # [PHASE 4.4 KHẮC PHỤC LỖI Parse Stylesheet]: Viết CSS chuẩn trên 1 dòng an toàn
        if status_text and bg_col:
            badge = QLabel(status_text)
            badge.setStyleSheet(
                f"background-color: {bg_col}; color: {txt_col}; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            h1.addWidget(badge)

        v_lay.addLayout(h1)

        # Row 2: Title
        title = StrongBodyLabel(self.event.get('title', 'Không có tiêu đề'), self)
        title.setWordWrap(True)
        v_lay.addWidget(title)

        # Row 3: Description
        if self.event.get('desc'):
            desc = BodyLabel(self.event['desc'], self)
            desc.setTextColor(QColor("#555555") if not isDarkTheme() else QColor("#cccccc"), QColor("#cccccc"))
            desc.setWordWrap(True)
            v_lay.addWidget(desc)

        lay.addWidget(content_widget)


# --- 3. DIALOG THÊM SỰ KIỆN (Fluent Dialog) ---
class AddEventDialog(QDialog):
    def __init__(self, date, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm Sự kiện Mới")
        self.resize(450, 400)
        self.date = date

        # Set màu nền dialog theo theme
        bg = "#ffffff" if not isDarkTheme() else "#2b2b2b"
        self.setStyleSheet(f"QDialog {{ background-color: {bg}; }}")

        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)

        # Header
        lay.addWidget(SubtitleLabel(f"Ngày: {self.date.toString('dd/MM/yyyy')}", self))

        # Form
        self.txt_title = LineEdit(self)
        self.txt_title.setPlaceholderText("Tiêu đề (VD: Họp giao ban, Nhập hóa chất...)")

        self.cb_type = ComboBox(self)
        for k, v in EVENT_TYPES.items():
            if k not in ["EQA", "MAINTENANCE"]:
                self.cb_type.addItem(f"{v['icon']} {v['label']}", k)

        self.tm_start = TimeEdit(self)
        self.tm_start.setTime(dt.datetime.now().time())
        self.tm_end = TimeEdit(self)
        self.tm_end.setTime(dt.datetime.now().time().replace(minute=30))

        self.txt_desc = TextEdit(self)
        self.txt_desc.setPlaceholderText("Nội dung chi tiết...")
        self.txt_desc.setFixedHeight(100)

        # Layout Inputs
        lay.addWidget(StrongBodyLabel("Thông tin chính", self))
        lay.addWidget(self.txt_title)
        lay.addWidget(self.cb_type)

        h_tm = QHBoxLayout()
        h_tm.addWidget(BodyLabel("Từ:", self))
        h_tm.addWidget(self.tm_start)
        h_tm.addSpacing(10)
        h_tm.addWidget(BodyLabel("Đến:", self))
        h_tm.addWidget(self.tm_end)
        lay.addLayout(h_tm)

        lay.addWidget(StrongBodyLabel("Ghi chú", self))
        lay.addWidget(self.txt_desc)

        # Buttons
        h_btn = QHBoxLayout()
        self.btn_save = PrimaryPushButton("Lưu", self)
        self.btn_save.clicked.connect(self.accept)

        self.btn_cancel = PushButton("Hủy", self)
        self.btn_cancel.clicked.connect(self.reject)

        h_btn.addStretch()
        h_btn.addWidget(self.btn_cancel)
        h_btn.addWidget(self.btn_save)
        lay.addLayout(h_btn)

    def get_data(self):
        return {
            "title": self.txt_title.text(),
            "type": self.cb_type.currentData(),
            "date": self.date.toString("yyyy-MM-dd"),
            "start": self.tm_start.text(),
            "end": self.tm_end.text(),
            "desc": self.txt_desc.toPlainText()
        }


# --- 4. PAGE CHÍNH ---
class EventCalendarPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = CalendarService()
        self.active_events = []

        self._build_ui()
        self._refresh_calendar()

        # Kết nối sự kiện đổi theme để refresh lại màu các Checkbox/Lịch
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # === CỘT TRÁI: BỘ LỌC + LỊCH ===
        # Sử dụng SimpleCardWidget làm container để có bo góc và màu nền chuẩn
        left_panel = SimpleCardWidget(self)
        v_left = QVBoxLayout(left_panel)
        v_left.setContentsMargins(12, 12, 12, 12)

        # 1. Bộ lọc (Filter)
        lbl_filter = StrongBodyLabel("Bộ lọc hiển thị", self)
        v_left.addWidget(lbl_filter)

        # Grid filter
        self.filter_container = QFrame()
        grid_filt = QGridLayout(self.filter_container)
        grid_filt.setContentsMargins(0, 5, 0, 10)

        self.chk_filters = {}
        row, col = 0, 0
        for k, v in EVENT_TYPES.items():
            chk = CheckBox(v['label'], self)
            chk.setChecked(True)
            chk.stateChanged.connect(self._refresh_calendar)

            # Lưu màu gốc để xử lý theme sau này
            chk.setProperty("base_color", v['color'])

            self.chk_filters[k] = chk
            grid_filt.addWidget(chk, row, col)

            col += 1
            if col > 1:  # 2 cột
                col = 0
                row += 1

        v_left.addWidget(self.filter_container)

        # Cập nhật màu text cho checkbox lần đầu
        self._update_filter_styles()

        # 2. Calendar Widget
        self.calendar = MasterCalendarWidget()
        v_left.addWidget(self.calendar)

        root.addWidget(left_panel, 4)

        # === CỘT PHẢI: CHI TIẾT SỰ KIỆN ===
        # CardWidget (lớn hơn SimpleCardWidget) cho vùng chi tiết
        right_panel = CardWidget(self)
        v_right = QVBoxLayout(right_panel)
        v_right.setContentsMargins(16, 16, 16, 16)

        # Header
        self.lbl_header = SubtitleLabel("Chi tiết sự kiện", self)
        v_right.addWidget(self.lbl_header)

        # Danh sách (Scroll)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")  # Trong suốt để lộ màu Card

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")

        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setContentsMargins(0, 0, 10, 0)  # Padding phải cho scrollbar
        self.scroll.setWidget(self.scroll_content)

        v_right.addWidget(self.scroll)

        # Nút chức năng
        h_act = QHBoxLayout()
        self.btn_add = PrimaryPushButton(FIF.ADD, "Thêm Sự kiện", self)
        self.btn_del = PushButton(FIF.DELETE, "Xoá Sự kiện", self)
        h_act.addWidget(self.btn_add)
        h_act.addWidget(self.btn_del)
        v_right.addLayout(h_act)

        root.addWidget(right_panel, 6)

        # --- SIGNALS ---
        self.calendar.selectionChanged.connect(self._on_date_selected)
        self.calendar.currentPageChanged.connect(lambda y, m: self._refresh_calendar())
        self.btn_add.clicked.connect(self._add_event)
        self.btn_del.clicked.connect(self._delete_event)

    def _on_theme_changed(self):
        """Callback khi hệ thống đổi chế độ Sáng/Tối"""
        self._update_filter_styles()
        self._on_date_selected()  # Refresh lại list event để cập nhật màu text trong card

    def _update_filter_styles(self):
        """Cập nhật màu chữ checkbox để dễ nhìn trên nền tối/sáng"""
        is_dark = isDarkTheme()
        for k, chk in self.chk_filters.items():
            base_col = chk.property("base_color")
            # Ở dark mode, làm sáng màu text lên một chút nếu màu gốc quá tối
            # Ở đây ta giữ nguyên màu gốc vì các màu sự kiện thường khá tươi (cam, xanh, đỏ)
            # Hoặc force trắng nếu muốn đồng bộ
            chk.setStyleSheet(f"color: {base_col if not is_dark else '#ffffff'}; font-weight: 500;")

    def _get_active_filters(self) -> List[str]:
        return [k for k, chk in self.chk_filters.items() if chk.isChecked()]

    def _refresh_calendar(self):
        y, m = self.calendar.yearShown(), self.calendar.monthShown()
        start = dt.date(y, m, 1) - dt.timedelta(days=7)
        end = dt.date(y, m, 28) + dt.timedelta(days=40)

        filters = self._get_active_filters()
        self.active_events = self.service.get_all_events(start, end, filters)
        self.calendar.update_events(self.active_events)
        self._on_date_selected()

    def _on_date_selected(self):
        qd = self.calendar.selectedDate()
        py_date = dt.date(qd.year(), qd.month(), qd.day())
        self.lbl_header.setText(f"Sự kiện ngày {qd.toString('dd/MM/yyyy')}")

        # Clear layout
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        daily_events = [e for e in self.active_events if e['date'] == py_date]

        if not daily_events:
            empty = BodyLabel("Không có sự kiện nào.", self)
            empty.setTextColor(QColor("#888888"), QColor("#888888"))
            empty.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(empty)
        else:
            for e in daily_events:
                # Dùng Custom Card Widget
                card = EventCardItem(e)
                card.setProperty("event_id", e['id'])
                card.setProperty("source", e['source'])
                self.scroll_layout.addWidget(card)

    def _add_event(self):
        date = self.calendar.selectedDate()
        dlg = AddEventDialog(date, self)
        if dlg.exec():
            try:
                self.service.add_event(dlg.get_data())
                self._refresh_calendar()
                InfoBar.success("Thành công", "Đã thêm sự kiện vào lịch.", parent=self, duration=2000)
            except Exception as e:
                InfoBar.error("Lỗi", str(e), parent=self)

    def _delete_event(self):
        qd = self.calendar.selectedDate()
        py_date = dt.date(qd.year(), qd.month(), qd.day())
        manuals = [e for e in self.active_events if e['date'] == py_date and e['source'] == 'MANUAL']

        if not manuals:
            InfoBar.warning("Chú ý", "Không có sự kiện thủ công nào để xóa ngày này.", parent=self)
            return

        target = manuals[0]  # Xóa cái đầu tiên (Logic đơn giản hóa)

        from qfluentwidgets import MessageDialog
        w = MessageDialog("Xác nhận", f"Bạn có chắc muốn xóa sự kiện:\n'{target['title']}'?", self)
        if w.exec():
            self.service.delete_event(target['id'])
            self._refresh_calendar()
            InfoBar.success("Đã xóa", "Sự kiện đã được gỡ bỏ.", parent=self)