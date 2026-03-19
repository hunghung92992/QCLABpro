# -*- coding: utf-8 -*-
import os
import datetime as dt
import traceback

from PySide6.QtCore import Qt, QRectF, QPointF, QDate, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QHeaderView,
    QTableWidgetItem, QAbstractItemView, QFileDialog, QScrollArea, QLabel
)
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush

# --- FLUENT WIDGETS ---
from qfluentwidgets import (
    PrimaryPushButton, PushButton, CalendarPicker, ComboBox,
    FluentIcon as FIF, CardWidget, TableWidget,
    StrongBodyLabel, TitleLabel, BodyLabel, CaptionLabel,
    InfoBar, SimpleCardWidget
)

# Thử import Service
try:
    from app.services.report_service import ReportService
except ImportError:
    ReportService = None


# =============================================================================
# CHARTS & COMPONENTS
# =============================================================================
class NativeBarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 250)
        self.data_x = []
        self.data_y = []
        self.bar_color = QColor("#005fb8")

    def set_data(self, x, y):
        self.data_x = x
        self.data_y = y
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        if not self.data_y:
            painter.setPen(Qt.black)
            painter.drawText(rect, Qt.AlignCenter, "Không có dữ liệu hiển thị")
            return

        w, h = rect.width() - 60, rect.height() - 60
        max_val = max(self.data_y) if max(self.data_y) > 0 else 1
        count = len(self.data_x)
        if count == 0: return

        step_x = w / count
        bar_w = min(step_x * 0.6, 40)

        # Trục hoành
        painter.setPen(QPen(Qt.gray, 1))
        painter.drawLine(40, rect.height() - 30, rect.width() - 20, rect.height() - 30)

        painter.setBrush(QBrush(self.bar_color))
        painter.setPen(Qt.NoPen)

        for i, val in enumerate(self.data_y):
            bar_h = (val / max_val) * h
            x_pos = 40 + i * step_x + (step_x - bar_w) / 2
            y_pos = rect.height() - 30 - bar_h
            painter.drawRect(QRectF(x_pos, y_pos, bar_w, bar_h))

            # Label x
            painter.setPen(Qt.black)
            lbl = str(self.data_x[i])
            if len(lbl) > 5: lbl = lbl[-5:]
            painter.drawText(QRectF(40 + i * step_x, rect.height() - 25, step_x, 20), Qt.AlignCenter, lbl)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.bar_color))


class NativeDonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 250)
        self.data = {}
        self.colors = [QColor("#0078d4"), QColor("#107c10"), QColor("#d13438"), QColor("#ffaa00")]
        self.total = 0

    def set_data(self, d):
        self.data = d
        self.total = sum(d.values())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        if not self.data or self.total == 0:
            painter.setPen(Qt.black)
            painter.drawText(rect, Qt.AlignCenter, "Chưa có dữ liệu")
            return

        size = min(rect.width(), rect.height() - 60)
        cx, cy = rect.width() / 2, (rect.height() - 60) / 2 + 10
        angle = 90 * 16

        for i, (k, v) in enumerate(self.data.items()):
            if v == 0: continue
            span = -(v / self.total) * 360 * 16
            painter.setBrush(QBrush(self.colors[i % 4]))
            painter.setPen(Qt.NoPen)
            painter.drawPie(int(cx - size * 0.4), int(cy - size * 0.4), int(size * 0.8), int(size * 0.8), int(angle),
                            int(span))
            angle += span

        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(QPointF(cx, cy), size * 0.25, size * 0.25)

        # Legend
        ly = cy + size * 0.4 + 20
        lx = 20
        painter.setFont(QFont("Segoe UI", 9))
        for i, (k, v) in enumerate(self.data.items()):
            painter.setBrush(QBrush(self.colors[i % 4]))
            painter.drawRect(int(lx), int(ly), 10, 10)
            painter.setPen(Qt.black)
            painter.drawText(int(lx + 15), int(ly + 9), f"{k} ({v})")
            lx += 80


class KPICard(CardWidget):
    def __init__(self, icon, title, value, color, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        h = QHBoxLayout(self)
        h.setContentsMargins(15, 10, 15, 10)

        btn = PushButton(icon, "", self)
        btn.setFixedSize(40, 40)
        btn.setIconSize(QSize(20, 20))
        btn.setStyleSheet(f"background-color: {color}; border: none; border-radius: 20px; color: white;")

        v = QVBoxLayout()
        v.setSpacing(0)
        self.val = TitleLabel(str(value), self)
        self.val.setStyleSheet(f"color: {color}; font-size: 18px;")
        v.addWidget(self.val)
        v.addWidget(CaptionLabel(title, self))

        h.addWidget(btn)
        h.addSpacing(10)
        h.addLayout(v)
        h.addStretch(1)

    def update_value(self, v):
        self.val.setText(str(v))


# =============================================================================
# MAIN PAGE - Đã fix lỗi tham số khởi tạo
# =============================================================================
class ReportPage(QWidget):  # Tên class chuẩn để main_window gọi
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.setObjectName("ReportPage")

        # 1. Layout chính
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 2. ScrollArea
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")

        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.content)
        self.main_layout.addWidget(self.scroll)

        # 3. Service
        self.service = ReportService() if ReportService else None

        # 4. Init UI
        self._setup_content()

        # 5. Load Initial Data
        try:
            self._load_departments()
            if self.service:
                self._load_data()
        except Exception as e:
            print(f"ERROR: {e}")

    def _setup_content(self):
        self.vbox = QVBoxLayout(self.content)
        self.vbox.setContentsMargins(30, 20, 30, 40)
        self.vbox.setSpacing(20)

        # Header
        title = TitleLabel("Báo cáo Tổng hợp", self.content)
        sub = CaptionLabel("Phân tích dữ liệu hệ thống Lab", self.content)
        self.vbox.addWidget(title)
        self.vbox.addWidget(sub)

        # Filter Bar
        f_card = CardWidget(self.content)
        fh = QHBoxLayout(f_card)

        self.cb_dept = ComboBox(self.content)
        self.cb_dept.addItem("Tất cả")
        self.cb_dept.setFixedWidth(150)

        self.d_start = CalendarPicker(self.content)
        self.d_start.setDate(QDate.currentDate().addDays(-30))

        self.d_end = CalendarPicker(self.content)
        self.d_end.setDate(QDate.currentDate())

        btn_run = PrimaryPushButton(FIF.SYNC, "Phân tích", self.content)
        btn_run.clicked.connect(self._load_data)

        btn_pdf = PushButton(FIF.PRINT, "Xuất PDF", self.content)
        btn_pdf.clicked.connect(self._export_pdf)
        # [NEW M7] Nút xuất báo cáo Excel chuẩn ISO
        btn_excel = PushButton(FIF.DOWNLOAD, "Xuất Excel (ISO)", self.content)
        btn_excel.clicked.connect(self._export_excel_iso)
        fh.addWidget(BodyLabel("Khoa:"))
        fh.addWidget(self.cb_dept)
        fh.addWidget(BodyLabel("Từ:"))
        fh.addWidget(self.d_start)
        fh.addWidget(BodyLabel("Đến:"))
        fh.addWidget(self.d_end)
        fh.addWidget(btn_run)
        fh.addWidget(btn_pdf)
        fh.addWidget(btn_excel)  # Thêm nút Excel vào layout
        self.vbox.addWidget(f_card)

        # KPI Cards
        kpi_box = QHBoxLayout()
        self.kpi_iqc = KPICard(FIF.COMPLETED, "Tỷ lệ Đạt IQC", "0%", "#107c10", self.content)
        self.kpi_capa = KPICard(FIF.INFO, "Sự cố Mở", "0", "#d13438", self.content)
        self.kpi_eqa = KPICard(FIF.GLOBE, "EQA Đạt", "0%", "#0078d4", self.content)
        self.kpi_dev = KPICard(FIF.TILES, "Bảo trì", "0", "#605e5c", self.content)
        kpi_box.addWidget(self.kpi_iqc)
        kpi_box.addWidget(self.kpi_capa)
        kpi_box.addWidget(self.kpi_eqa)
        kpi_box.addWidget(self.kpi_dev)
        self.vbox.addLayout(kpi_box)

        # Charts
        chart_layout = QHBoxLayout()

        c1 = SimpleCardWidget(self.content)
        v1 = QVBoxLayout(c1)
        v1.addWidget(StrongBodyLabel("Xu hướng mẫu IQC"))
        self.chart1 = NativeBarChart(self.content)
        v1.addWidget(self.chart1)

        c2 = SimpleCardWidget(self.content)
        v2 = QVBoxLayout(c2)
        v2.addWidget(StrongBodyLabel("Tình trạng CAPA"))
        self.chart2 = NativeDonutChart(self.content)
        v2.addWidget(self.chart2)

        chart_layout.addWidget(c1, 2)
        chart_layout.addWidget(c2, 1)
        self.vbox.addLayout(chart_layout)

        # Table
        self.vbox.addWidget(StrongBodyLabel("Thống kê Chỉ số Chất lượng (ISO 15189)"))
        self.table = TableWidget(self.content)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Xét nghiệm", "Level", "Số Mẫu (N)", "Mean", "SD", "CV (%)", "Số lỗi"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setMinimumHeight(300)
        self.vbox.addWidget(self.table)

    def _load_departments(self):
        if self.service and hasattr(self.service, 'get_departments'):
            depts = self.service.get_departments()
            for d in depts:
                self.cb_dept.addItem(d)

    def _load_data(self):
        if not self.service: return

        s = self.d_start.getDate().toString(Qt.ISODate)
        e = self.d_end.getDate().toString(Qt.ISODate)
        dept = self.cb_dept.currentText()

        try:
            # ==========================================
            # 1. KPI Data (Giữ nguyên)
            # ==========================================
            iqc = self.service.get_iqc_summary(s, e, dept)
            capa = self.service.get_capa_summary(s, e)
            eqa = self.service.get_eqa_summary(s, e)
            equip = self.service.get_equipment_summary()

            self.kpi_iqc.update_value(f"{iqc.get('rate', 0)}%")
            self.kpi_capa.update_value(capa.get('open', 0))
            self.kpi_eqa.update_value(f"{eqa.get('rate', 0)}%")
            self.kpi_dev.update_value(equip.get('maintenance', 0))

            # ==========================================
            # 2. Chart Data (Giữ nguyên)
            # ==========================================
            trend = self.service.get_iqc_trend(s, e)
            if trend is not None and not trend.empty:
                self.chart1.set_data(trend['date'].tolist(), trend['count'].tolist())

            self.chart2.set_data({"Đóng": capa.get('closed', 0), "Mở": capa.get('open', 0)})

            # ==========================================
            # 3. Table Data [CẬP NHẬT M7 - THỐNG KÊ ISO]
            # ==========================================
            # Gọi hàm lấy thống kê thay vì lấy dữ liệu thô
            stats = self.service.get_monthly_statistics(s, e, dept)

            self.table.setRowCount(0)
            for i, r in enumerate(stats):
                self.table.insertRow(i)

                # Cột 0: Xét nghiệm
                self.table.setItem(i, 0, QTableWidgetItem(str(r['test_code'])))

                # Cột 1: Level
                self.table.setItem(i, 1, QTableWidgetItem(str(r['level'])))

                # Cột 2: Số lượng mẫu (N)
                self.table.setItem(i, 2, QTableWidgetItem(str(r['N'])))

                # Cột 3: Mean thực tế
                self.table.setItem(i, 3, QTableWidgetItem(str(r['mean'])))

                # Cột 4: SD thực tế
                self.table.setItem(i, 4, QTableWidgetItem(str(r['sd'])))

                # Cột 5: CV (%) - Tự động cảnh báo chữ Đỏ, In đậm nếu > 5.0%
                cv_item = QTableWidgetItem(str(r['cv']))
                if r['cv'] > 5.0:
                    cv_item.setForeground(QColor("#d13438"))  # Mã màu đỏ của Fluent Design
                    cv_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                self.table.setItem(i, 5, cv_item)

                # Cột 6: Số lần vi phạm luật Westgard - Báo đỏ nếu có lỗi
                err_item = QTableWidgetItem(str(r['errors']))
                if r['errors'] > 0:
                    err_item.setForeground(QColor("#d13438"))
                    err_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                self.table.setItem(i, 6, err_item)

        except Exception as ex:
            print(f"Data Load Error: {ex}")
            traceback.print_exc()  # In chi tiết lỗi ra Terminal để dễ gỡ lỗi nếu có

    def _export_pdf(self):
        if not self.service: return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu PDF", "Report.pdf", "PDF (*.pdf)")
        if path:
            s = self.d_start.getDate().toString(Qt.ISODate)
            e = self.d_end.getDate().toString(Qt.ISODate)
            data = self.service.get_iqc_details_raw(s, e, self.cb_dept.currentText())
            meta = {"date_from": s, "date_to": e, "department": self.cb_dept.currentText()}

            if self.service.export_pdf_report(path, data, meta):
                InfoBar.success("Thành công", f"Đã xuất file tại {path}", parent=self)
            else:
                InfoBar.error("Lỗi", "Không thể tạo PDF", parent=self)

    def _export_excel_iso(self):
        """Hành động khi bấm nút Xuất Excel."""
        if not self.service: return

        # Mở hộp thoại chọn nơi lưu file
        default_name = f"IQC_ISO_{dt.datetime.now().strftime('%Y%m')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Lưu báo cáo Excel", default_name, "Excel Files (*.xlsx)")

        if path:
            s = self.d_start.getDate().toString(Qt.ISODate)
            e = self.d_end.getDate().toString(Qt.ISODate)
            dept = self.cb_dept.currentText()

            # Gọi service để xuất file
            success = self.service.export_monthly_iqc(dept, s, e, path)

            if success:
                InfoBar.success("Thành công", f"Đã xuất báo cáo ISO tại:\n{path}", parent=self)
                # Tùy chọn: Mở file luôn sau khi xuất (chỉ chạy trên Windows)
                import os
                os.startfile(path)
            else:
                InfoBar.error("Lỗi", "Có lỗi xảy ra khi tạo file Excel.", parent=self)


# Để tương thích với các cách gọi khác nhau
ReportsPage = ReportPage