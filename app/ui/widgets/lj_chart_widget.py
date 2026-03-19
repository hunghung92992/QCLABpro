# -*- coding: utf-8 -*-
"""
app/shared/widgets/lj_chart_widget.py
(CẬP NHẬT GĐ 9 - Thêm Gợi ý 1: Bắt sự kiện Click)
Widget vẽ biểu đồ Levey-Jennings (dùng Matplotlib).
"""
from __future__ import annotations
from typing import List, Optional, Tuple, Dict, Any

from app.utils.qt_compat import QWidget, QVBoxLayout, Signal
import matplotlib
# Ép dùng backend chung cho Qt (tự động nhận diện PySide6)
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class LJWidget(QWidget):
    # (MỚI) Gợi ý 1: Tín hiệu phát ra khi một điểm được nhấp
    # Sẽ gửi một dict chứa thông tin về điểm
    pointClicked = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fig = Figure(figsize=(5, 3), tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._canvas)

        self._mean = 0.0
        self._sd = 1.0
        self._values: List[float] = []
        self._violations: List[Tuple[int, str]] = []
        self._highlight_last = True
        self._line_color = "#333333"

        self._multiple_lines_data: List[Dict[str, Any]] = []

        # (MỚI) Gợi ý 1: Kết nối sự kiện nhấp chuột
        self._canvas.mpl_connect('button_press_event', self._on_click)

        self._redraw()

    def set_target(self, mean: float, sd: float):
        """Thiết lập Mean và SD mục tiêu."""
        self._mean = float(mean or 0.0)
        self._sd = float(sd or 1.0)
        if self._sd == 0: self._sd = 1.0

    def set_history(self, values: List[float], violations: Optional[List[Tuple[int, str]]] = None):
        """Thiết lập chuỗi dữ liệu (points) và các vi phạm (violations) cho MỘT đường."""
        self._multiple_lines_data = []
        self._values = [float(v) for v in values if v is not None]
        self._violations = violations or []
        self._redraw()

    def set_multiple_histories(self, list_of_data: List[Dict[str, Any]]):
        """(MỚI) Thiết lập dữ liệu cho NHIỀU đường trên cùng một biểu đồ."""
        self._multiple_lines_data = list_of_data
        self._values = []
        self._violations = []
        self._redraw()

    def highlight_last(self, yes: bool):
        """Bật/tắt tô đậm điểm cuối cùng."""
        self._highlight_last = bool(yes)
        self._redraw()

    def set_color(self, color: str):
        """(MỚI) Thiết lập màu cho đường dữ liệu chính (chỉ dùng khi vẽ 1 đường)."""
        self._line_color = color

    def _redraw(self):
        ax = self._ax
        ax.clear()

        m, s = self._mean, self._sd

        # 1. Vẽ các đường Mean/SD
        if s > 0:
            ax.axhline(m, color="blue", linestyle="--", linewidth=1.5, label="Mean")
            ax.axhline(m + s, color="gray", linestyle=":", linewidth=0.8)
            ax.axhline(m - s, color="gray", linestyle=":", linewidth=0.8)

            ax.axhline(m + 2 * s, color="orange", linestyle="--", linewidth=1, label="±2SD (Warn)")
            ax.axhline(m - 2 * s, color="orange", linestyle="--", linewidth=1)

            ax.axhline(m + 3 * s, color="red", linestyle="--", linewidth=1, label="±3SD (Reject)")
            ax.axhline(m - 3 * s, color="red", linestyle="--", linewidth=1)

        # 2. Vẽ chuỗi dữ liệu
        primary_labels: List[str] = []
        primary_ticks: List[int] = []

        if self._multiple_lines_data:
            all_xs = []
            all_ys = []
            for data_idx, data in enumerate(self._multiple_lines_data):
                values = data['values']
                violations = data['violations']
                color = data['color']
                label = data['label']
                x_labels = data.get('x_labels', [])

                if values:
                    xs = list(range(1, len(values) + 1))
                    # (MỚI) Thêm 'picker=5' để cho phép nhấp chuột
                    ax.plot(xs, values, marker="o", linestyle="-", color=color, markersize=5, label=label, picker=5)
                    all_xs.extend(xs)
                    all_ys.extend(values)

                    if data_idx == 0:
                        primary_labels = x_labels
                        primary_ticks = xs

                    for idx, rule in violations:
                        if 0 <= idx < len(xs):
                            is_reject = any(r in rule for r in ("1-3s", "R-4s", "2-2s", "4-1s", "10x"))
                            violation_color = "red" if is_reject else "orange"
                            ax.plot(xs[idx], values[idx], marker="s", markersize=10,
                                    fillstyle="none", color=violation_color, linestyle="none",
                                    label=f"Vi phạm {rule} ({label})")

            if all_xs and all_ys:
                min_x, max_x = min(all_xs), max(all_xs)
                min_y, max_y = min(all_ys), max(all_ys)

                ax.set_xlim(min_x - 0.5, max_x + 0.5)

                if m == 0 and s == 1:
                    ax.set_ylim(min(min_y - 0.5, -4), max(max_y + 0.5, 4))
                else:
                    padding_y = (max_y - min_y) * 0.1
                    ax.set_ylim(min_y - (padding_y + 0.1), max_y + (padding_y + 0.1))

        elif self._values:
            xs = list(range(1, len(self._values) + 1))
            # (MỚI) Thêm 'picker=5'
            ax.plot(xs, self._values, marker="o", linestyle="-", color=self._line_color, markersize=5, picker=5)

            primary_ticks = xs
            primary_labels = [str(x) for x in xs]

            for idx, rule in self._violations:
                if 0 <= idx < len(xs):
                    is_reject = any(r in rule for r in ("1-3s", "R-4s", "2-2s", "4-1s", "10x"))
                    color = "red" if is_reject else "orange"
                    ax.plot(xs[idx], self._values[idx], marker="s", markersize=10,
                            fillstyle="none", color=color, linestyle="none",
                            label=f"Vi phạm {rule}")

            if self._highlight_last and xs:
                ax.plot(xs[-1], self._values[-1], marker="o", markersize=9, color="blue", label="Điểm cuối")

            ax.set_xlim(0.5, len(xs) + 0.5)
            if m == 0 and s == 1:
                ax.set_ylim(-4, 4)
            elif self._values:
                min_y, max_y = min(self._values), max(self._values)
                padding_y = (max_y - min_y) * 0.1
                ax.set_ylim(min_y - (padding_y + 0.1), max_y + (padding_y + 0.1))

        ax.set_title("Biểu đồ Levey–Jennings")

        if primary_labels:
            ax.set_xlabel("Ngày nhập (DD-MM-YYYY)")
            tick_spacing = max(1, len(primary_ticks) // 20)
            ax.set_xticks(primary_ticks[::tick_spacing])
            ax.set_xticklabels(primary_labels[::tick_spacing], rotation=45, ha="right", fontsize=9)
        else:
            ax.set_xlabel("N")

        ax.set_ylabel("Giá trị")
        ax.grid(True, linestyle=":", alpha=0.6)

        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(by_label.values(), by_label.keys(), fontsize='small', loc='upper left')

        self._canvas.draw_idle()

    def _on_click(self, event):
        """(MỚI) Gợi ý 1: Xử lý sự kiện nhấp chuột."""

        # Chỉ xử lý nhấp chuột phải
        if event.button != 3:
            return

        if not event.inaxes == self._ax:
            return

        # Tìm điểm dữ liệu gần nhất trên đường nào
        closest_line = None
        min_dist = float('inf')
        clicked_x, clicked_y = event.xdata, event.ydata

        if not self._multiple_lines_data and not self._values:
            return  # Không có dữ liệu

        if self._multiple_lines_data:
            # Trường hợp nhiều đường
            for line_idx, data in enumerate(self._multiple_lines_data):
                values = data['values']
                xs = list(range(1, len(values) + 1))
                for point_idx, (px, py) in enumerate(zip(xs, values)):
                    # Tính khoảng cách (chỉ cần X, vì Y có thể ở xa)
                    dist = abs(px - clicked_x)
                    if dist < 0.5 and dist < min_dist:  # 0.5 là dung sai (tolerance)
                        min_dist = dist
                        closest_line = {
                            "line_index": line_idx,  # L1/L2/L3 (0, 1, 2)
                            "point_index": point_idx,  # (0, 1, 2...)
                            "value": py,
                            "x_label": data.get('x_labels', [])[point_idx]
                        }
        else:
            # Trường hợp một đường
            values = self._values
            xs = list(range(1, len(values) + 1))
            for point_idx, (px, py) in enumerate(zip(xs, values)):
                dist = abs(px - clicked_x)
                if dist < 0.5 and dist < min_dist:
                    min_dist = dist
                    closest_line = {
                        "line_index": 0,  # Chỉ có 1 đường
                        "point_index": point_idx,
                        "value": py,
                        "x_label": ""  # Không có nhãn X cho 1 đường
                    }

        if closest_line:
            # Phát tín hiệu
            self.pointClicked.emit(closest_line)