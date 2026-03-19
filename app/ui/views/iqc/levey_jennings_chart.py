# -*- coding: utf-8 -*-
"""
app/ui/views/iqc/levey_jennings_chart.py
(WIN11 FLUENT DESIGN - ENHANCED VERSION)
Widget vẽ biểu đồ Levey-Jennings chuyên nghiệp sử dụng Matplotlib.
Hỗ trợ:
- Mean, +/- 1,2,3 SD.
- Vùng màu (Color Bands) trực quan.
- Highlight điểm vi phạm quy tắc Westgard.
- Trục thời gian tự động (AutoDateLocator).
"""
import matplotlib

# Sử dụng Backend QT để nhúng vào PySide6
matplotlib.use('QtAgg')

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout
import matplotlib.dates as mdates
# [NEW] Import bộ xử lý ngày tháng tự động
from matplotlib.dates import AutoDateLocator, DateFormatter


class LeveyJenningsChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Layout chính
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 1. Khởi tạo Matplotlib Figure
        self.figure = Figure(figsize=(8, 6), dpi=100)

        # [THEME] Màu nền mặc định (Sẽ được ghi đè bởi trang cha khi đổi theme)
        self.figure.patch.set_facecolor('#FFFFFF')

        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Tạo subplot
        self.ax = self.figure.add_subplot(111)

        # Cấu hình font chữ chuẩn Windows 11
        matplotlib.rcParams['font.family'] = 'Segoe UI'
        matplotlib.rcParams['font.size'] = 9

        # [NEW] Tối ưu khoảng cách để không bị cắt chữ
        self.figure.tight_layout()

        # Khởi tạo biểu đồ rỗng
        self.reset_chart()

    def reset_chart(self):
        """Xóa trắng biểu đồ"""
        self.ax.clear()
        self.ax.text(0.5, 0.5, "Chưa có dữ liệu QC",
                     horizontalalignment='center',
                     verticalalignment='center',
                     transform=self.ax.transAxes,
                     color='#888888', fontsize=12)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()

    def update_chart(self, dates, values, mean, sd, violations=None, title="Biểu đồ QC"):
        """
        Vẽ lại biểu đồ với dữ liệu mới.
        :param dates: List ngày
        :param values: List kết quả
        :param mean: Mean
        :param sd: SD
        :param violations: List các index của điểm dữ liệu vi phạm (để tô đỏ). VD: [2, 5]
        """
        self.ax.clear()

        # Nếu không có dữ liệu
        if not values or not dates:
            self.reset_chart()
            return

        # --- 1. VẼ VÙNG MÀU (COLOR BANDS) ---
        # Giúp nhận biết nhanh vùng an toàn/cảnh báo
        # Vùng 1SD (Xanh nhạt - An toàn)
        self.ax.axhspan(mean - sd, mean + sd, color='green', alpha=0.08, zorder=0)

        # Vùng 1SD-2SD (Vàng nhạt - Cảnh báo)
        self.ax.axhspan(mean + sd, mean + 2 * sd, color='#FFD700', alpha=0.08, zorder=0)
        self.ax.axhspan(mean - 2 * sd, mean - sd, color='#FFD700', alpha=0.08, zorder=0)

        # --- 2. VẼ CÁC ĐƯỜNG GIỚI HẠN ---
        # Đường Mean (Xanh lá đậm)
        self.ax.axhline(mean, color='green', linestyle='-', linewidth=1.5, alpha=0.9, zorder=1, label='Mean')

        # Vẽ các đường SD (+/- 1, 2, 3)
        colors = {1: '#FFD700', 2: 'orange', 3: 'red'}
        for i in [1, 2, 3]:
            c = colors[i]
            ls = '--' if i < 3 else '-'  # 3SD vẽ liền, còn lại nét đứt
            self.ax.axhline(mean + i * sd, color=c, linestyle=ls, linewidth=1, alpha=0.6, zorder=1)
            self.ax.axhline(mean - i * sd, color=c, linestyle=ls, linewidth=1, alpha=0.6, zorder=1)

            # Label bên phải
            self._add_sd_label(mean + i * sd, f"+{i}SD", c)
            self._add_sd_label(mean - i * sd, f"-{i}SD", c)

        self._add_sd_label(mean, "Mean", "green")

        # --- 3. VẼ DỮ LIỆU (LINE & MARKER) ---
        # Đường nối (Line) - ZOrder thấp hơn điểm
        self.ax.plot(dates, values, color='#2b579a', linewidth=1.2, zorder=2)

        # Điểm bình thường (Scatter) - ZOrder cao
        self.ax.scatter(dates, values, color='#2b579a', s=25, zorder=3, label='Đạt')

        # --- 4. TÔ MÀU VI PHẠM (VIOLATIONS) ---
        # Logic: Ưu tiên danh sách violations truyền vào (từ Westgard Engine)
        if violations:
            # Lọc ra ngày và giá trị của các điểm vi phạm
            err_dates = [dates[i] for i in violations if i < len(dates)]
            err_vals = [values[i] for i in violations if i < len(values)]

            # Vẽ đè lên bằng điểm màu đỏ, viền trắng, to hơn
            self.ax.scatter(err_dates, err_vals, color='#C50F1F', s=50, zorder=4,
                            edgecolors='white', linewidth=1, label='Vi phạm')
        else:
            # Fallback: Nếu không truyền violations, tự tô đỏ điểm > 3SD
            for i, val in enumerate(values):
                if val > mean + 3 * sd or val < mean - 3 * sd:
                    self.ax.scatter(dates[i], val, color='#C50F1F', s=50, zorder=4, edgecolors='white')

        # --- 5. XỬ LÝ TRỤC THỜI GIAN (AUTO DATE LOCATOR) ---
        # Tự động tính toán khoảng cách chia (Ngày/Tuần/Tháng) để không đè chữ
        locator = AutoDateLocator()
        self.ax.xaxis.set_major_locator(locator)
        # Format ngày tháng gọn gàng
        self.ax.xaxis.set_major_formatter(DateFormatter('%d/%m'))
        # Xoay nhẹ nhãn trục X
        self.figure.autofmt_xdate(rotation=30)

        # --- 6. TRANG TRÍ ---
        self.ax.set_title(title, fontsize=11, fontweight='bold', pad=12)
        self.ax.set_xlabel("")  # Bỏ label X cho đỡ rối
        self.ax.set_ylabel("Kết quả")
        self.ax.grid(True, linestyle=':', alpha=0.5, zorder=0)

        # Giới hạn trục Y thông minh (Luôn hiển thị ít nhất +/- 4SD)
        y_max_range = max(4 * sd, abs(max(values) - mean) * 1.1 if values else 0)
        self.ax.set_ylim(mean - y_max_range, mean + y_max_range)

        # Vẽ lại canvas
        self.figure.tight_layout()
        self.canvas.draw()

    def _add_sd_label(self, y, text, color):
        """Hàm phụ trợ để ghi chú thích SD sát lề phải"""
        # x=1.01 nghĩa là nằm ngay sát bên ngoài trục Y bên phải
        self.ax.text(1.01, y, text, transform=self.ax.get_yaxis_transform(),
                     color=color, fontsize=8, verticalalignment='center', fontweight='bold')