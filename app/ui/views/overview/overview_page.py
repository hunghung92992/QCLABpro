# -*- coding: utf-8 -*-
import datetime as dt
import time
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QHeaderView, QTableWidgetItem, QAbstractItemView, QApplication
)
from PySide6.QtGui import QColor, QCursor

# --- MATPLOTLIB SETUP ---
import matplotlib
matplotlib.use('QtAgg')  # Bắt buộc dùng QtAgg cho PySide6
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- FLUENT WIDGETS ---
from qfluentwidgets import (
    FluentIcon as FIF, CardWidget, TitleLabel, CaptionLabel,
    StrongBodyLabel, IconWidget, PrimaryPushButton, TransparentPushButton,
    TableWidget, InfoBadge, BodyLabel, SimpleCardWidget, ComboBox
)

try:
    from app.services.overview_service import OverviewService
except ImportError:
    OverviewService = None


# ============================================================================
# COMPONENT: CLICKABLE KPI CARD (Thẻ KPI bấm được)
# ============================================================================
class ClickableCard(CardWidget):
    clicked = Signal()

    def __init__(self, icon, title, value, unit="", color="#0078d4", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)  # Con trỏ tay chỉ
        self.setFixedHeight(100)

        h = QHBoxLayout(self)
        h.setContentsMargins(20, 20, 20, 20)

        # Icon tròn
        iw = IconWidget(icon, self)
        iw.setFixedSize(48, 48)
        iw.setStyleSheet(f"background-color: {color}; border-radius: 24px; padding: 10px; color: white;")

        # Nội dung text
        v = QVBoxLayout()
        v.setAlignment(Qt.AlignVCenter)
        v.setSpacing(2)

        h_val = QHBoxLayout()
        h_val.setAlignment(Qt.AlignLeft)
        h_val.setSpacing(5)
        self.lbl_val = TitleLabel(str(value), self)
        self.lbl_unit = StrongBodyLabel(unit, self)
        h_val.addWidget(self.lbl_val)
        h_val.addWidget(self.lbl_unit)

        self.lbl_title = CaptionLabel(title, self)
        # Bỏ setStyleSheet vì FluentUI tự quản lý màu chữ

        v.addLayout(h_val)
        v.addWidget(self.lbl_title)

        h.addWidget(iw)
        h.addSpacing(15)
        h.addLayout(v)
        h.addStretch(1)

    def set_value(self, value):
        self.lbl_val.setText(str(value))

    # Bắt sự kiện thả chuột (Mouse Release) để tính là Click
    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


# ============================================================================
# COMPONENT: SIMPLE CHART (Biểu đồ đơn giản)
# ============================================================================
class SimpleTrendChart(SimpleCardWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(15, 15, 15, 15)
        v.addWidget(StrongBodyLabel(title, self))

        self.fig = Figure(figsize=(5, 3), dpi=72)
        self.fig.patch.set_facecolor('none')
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background: transparent;")
        v.addWidget(self.canvas)

    def plot(self, x, y):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        # Vẽ vùng màu dưới line
        ax.fill_between(x, y, color="#0078d4", alpha=0.1)
        # Vẽ line
        ax.plot(x, y, color="#0078d4", marker="o", markersize=4)

        # Style tối giản
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#aaa')
        ax.spines['left'].set_color('#aaa')

        self.fig.tight_layout()
        self.canvas.draw()


# ============================================================================
# MAIN OVERVIEW PAGE
# ============================================================================
class OverviewPage(QWidget):
    # Signal điều hướng: (Key của trang đích, Dữ liệu truyền đi)
    request_navigation = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("overview_page")
        self.service = OverviewService() if OverviewService else None

        self._init_ui()

        # Timer 1: Refresh dữ liệu Biểu đồ/KPI mỗi 60s
        self.data_timer = QTimer(self)
        self.data_timer.timeout.connect(self._update_data)
        self.data_timer.start(60000)

        # Load dữ liệu lần đầu (Delay nhẹ để UI render xong)
        QTimer.singleShot(100, self._first_load)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area (để tránh vỡ layout trên màn hình nhỏ)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content = QWidget()
        self.vbox = QVBoxLayout(self.content)
        self.vbox.setContentsMargins(30, 20, 30, 30)
        self.vbox.setSpacing(20)

        # --- 1. HEADER (Title + Status Bar + Filter) ---
        header = QHBoxLayout()

        # Left: Title & Status Bar
        hl = QVBoxLayout()
        hl.addWidget(TitleLabel("Tổng quan", self.content))

        # Thanh trạng thái (Status Bar) dưới Tiêu đề
        self.status_layout = QHBoxLayout()
        self.status_layout.setSpacing(15)

        # ĐÃ XÓA TẤT CẢ setStyleSheet Ở ĐÂY để chặn thông báo lỗi UI rác
        self.lbl_local_db = CaptionLabel("🟢 DB: Checking...", self.content)
        self.lbl_server = CaptionLabel("☁️ Server: Đang kiểm tra...", self.content)
        self.lbl_sync = CaptionLabel("🔄 Đồng bộ: Đang chờ...", self.content)
        self.lbl_countdown = CaptionLabel("", self.content)

        self.status_layout.addWidget(self.lbl_local_db)
        self.status_layout.addWidget(self.lbl_server)
        self.status_layout.addWidget(self.lbl_sync)
        self.status_layout.addWidget(self.lbl_countdown)
        self.status_layout.addStretch(1)

        hl.addLayout(self.status_layout)
        header.addLayout(hl)

        header.addStretch(1)

        # Right: Filter ComboBox
        header.addWidget(BodyLabel("Khoa/Phòng:", self.content))
        self.cb_dept = ComboBox(self.content)
        self.cb_dept.addItem("Tất cả")
        self.cb_dept.setFixedWidth(180)
        self.cb_dept.currentTextChanged.connect(self._update_data)  # Reload khi đổi khoa
        header.addWidget(self.cb_dept)

        self.vbox.addLayout(header)

        # --- 2. KPI CARDS ---
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)

        self.card_1 = ClickableCard(FIF.CALENDAR, "Mẫu hôm nay", "0", "", "#0078d4")
        self.card_2 = ClickableCard(FIF.COMPLETED, "Tỷ lệ Đạt", "0", "%", "#107c10")
        self.card_3 = ClickableCard(FIF.TILES, "Thiết bị Hỏng/Tổng", "0/0", "", "#605e5c")
        self.card_4 = ClickableCard(FIF.INFO, "CAPA Quá hạn/Mở", "0/0", "", "#d13438")

        # --- NAVIGATION LOGIC ---
        self.card_1.clicked.connect(lambda: self.request_navigation.emit("iqc_interface", {}))
        self.card_2.clicked.connect(lambda: self.request_navigation.emit("report_interface", {}))
        self.card_3.clicked.connect(lambda: self.request_navigation.emit("device_interface", {}))
        self.card_4.clicked.connect(lambda: self.request_navigation.emit("capa_interface", {"filter": "overdue"}))

        kpi_layout.addWidget(self.card_1)
        kpi_layout.addWidget(self.card_2)
        kpi_layout.addWidget(self.card_3)
        kpi_layout.addWidget(self.card_4)
        self.vbox.addLayout(kpi_layout)

        # --- 3. CHART & ACTIONS ---
        mid_layout = QHBoxLayout()

        # Chart (70%)
        self.chart = SimpleTrendChart("Xu hướng mẫu (7 ngày)")
        mid_layout.addWidget(self.chart, 7)

        # Quick Actions (30%)
        action_card = CardWidget()
        v_act = QVBoxLayout(action_card)
        v_act.setContentsMargins(15, 15, 15, 15)
        v_act.addWidget(StrongBodyLabel("Thao tác nhanh", action_card))
        v_act.addSpacing(10)

        b1 = PrimaryPushButton(FIF.ADD, "Nhập IQC")
        b1.clicked.connect(lambda: self.request_navigation.emit("iqc_interface", {}))
        b2 = TransparentPushButton(FIF.FEEDBACK, "Tạo CAPA")
        b2.clicked.connect(lambda: self.request_navigation.emit("capa_interface", {"action": "new"}))
        b3 = TransparentPushButton(FIF.GLOBE, "Kết quả EQA")
        b3.clicked.connect(lambda: self.request_navigation.emit("eqa_interface", {}))

        v_act.addWidget(b1)
        v_act.addWidget(b2)
        v_act.addWidget(b3)
        v_act.addStretch(1)
        mid_layout.addWidget(action_card, 3)

        self.vbox.addLayout(mid_layout)

        # --- 4. TABLE ---
        self.vbox.addWidget(StrongBodyLabel("Hoạt động gần nhất"))
        self.table = TableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Thời gian", "Khoa", "Test", "Level", "KQ", "Trạng thái"])
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setFixedHeight(300)
        self.vbox.addWidget(self.table)

        scroll.setWidget(self.content)
        main_layout.addWidget(scroll)

    # ========================================================================
    # LOGIC NHẬN TRẠNG THÁI ĐỒNG BỘ TỪ MAIN WINDOW (THẬT 100%)
    # ========================================================================
    def update_sync_status_ui(self, status_code, message):
        """Hàm này nhận tín hiệu từ MainWindow để cập nhật thanh trạng thái"""
        if status_code == 0:  # Dừng
            self.lbl_server.setText("⚪ Server: Ngừng hoạt động")
            self.lbl_sync.setText(f"Trạng thái: {message}")
            self.lbl_countdown.setText("")

        elif status_code == 1:  # Đang đồng bộ
            self.lbl_server.setText("🟢 Server: Connected")
            self.lbl_sync.setText("🔄 Đang đồng bộ...")
            self.lbl_countdown.setText("")

        elif status_code == 2:  # Đồng bộ OK
            self.lbl_server.setText("🟢 Server: Connected")
            self.lbl_sync.setText(f"✅ {message}")
            self.lbl_countdown.setText("⏳ Hệ thống tự động đồng bộ ngầm")

        elif status_code == 3:  # Lỗi / Mất mạng / Offline
            self.lbl_server.setText("🔴 Server: Disconnected (Offline)")
            self.lbl_sync.setText(f"⚠️ {message}")
            self.lbl_countdown.setText("Lưu tạm Local. Sẽ đẩy khi có mạng.")

    # ========================================================================
    # LOGIC DATA LOCAL
    # ========================================================================
    def _first_load(self):
        """Load danh sách khoa trước, rồi mới load data."""
        if self.service:
            depts = self.service.get_departments()
            self.cb_dept.blockSignals(True)
            for d in depts:
                self.cb_dept.addItem(d)
            self.cb_dept.blockSignals(False)
        self._update_data()

    def _update_data(self):
        if not self.service: return

        # 1. Update Health
        health = self.service.check_system_health()
        db_txt = "🟢 DB: Connected" if health['db'] else "🔴 DB: Error"
        bk_txt = "🟢 Backup: OK" if health['backup'] else "⚪ Backup: None (24h)"
        self.lbl_local_db.setText(f"{db_txt}  |  {bk_txt}")

        # 2. Get Filter
        dept = self.cb_dept.currentText()

        # 3. KPI
        k = self.service.get_kpi_data(dept)
        self.card_1.set_value(k['total_samples'])
        self.card_2.set_value(k['pass_rate'])
        self.card_3.set_value(k['device_status'])
        self.card_4.set_value(k['capa_status'])

        # 4. Chart
        dates, counts = self.service.get_chart_data(dept)
        safe_counts = []
        for c in counts:
            try:
                safe_counts.append(float(c))
            except (ValueError, TypeError):
                safe_counts.append(0.0)

        if dates:
            # [ĐÃ FIX] Vẽ biểu đồ bằng mảng safe_counts đã được ép kiểu an toàn
            self.chart.plot(dates, safe_counts)
        else:
            self.chart.plot(["Mon", "Tue"], [0, 0])

        # 5. Table
        rows = self.service.get_recent_table(15, dept)
        self.table.setRowCount(0)
        for i, r in enumerate(rows):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(r['time'])))
            self.table.setItem(i, 1, QTableWidgetItem(str(r['dept'])))
            self.table.setItem(i, 2, QTableWidgetItem(str(r['test'])))
            self.table.setItem(i, 3, QTableWidgetItem(str(r['level'])))
            self.table.setItem(i, 4, QTableWidgetItem(str(r['value'])))

            it = QTableWidgetItem(r['status'])
            if r['status'] == "Đạt":
                it.setForeground(QColor("green"))
            else:
                it.setForeground(QColor("red"))
            self.table.setItem(i, 5, it)