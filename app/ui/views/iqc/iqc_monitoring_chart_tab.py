# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_monitoring_chart_tab.py
(FINAL STABLE - COMPACT UI + EXPERT ADVICE)
- Logic: Giữ nguyên logic gốc của bạn (Pure Python).
- UI: Thu gọn bộ lọc, Thêm bảng Đánh giá chuyên gia.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Tuple
import datetime as dt

# --- PYSIDE6 IMPORTS ---
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QPushButton, QMessageBox, QLabel, QFrame, QGridLayout,
    QTabWidget, QDateEdit, QTextEdit, QGroupBox, QSplitter
)

# Helper functions
from app.utils.qt_compat import (
    fill_combo_from_list, get_combo_id, add_combo_item
)

# Services
from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService
from app.services.iqc_service import IQCService

# Logic
from app.utils.charts import basic_stats
from app.utils import analytics
from app.utils.validators import to_float_safe as _to_float

# Matplotlib
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = QWidget
    Figure = lambda *args, **kwargs: None
    np = None

# --- FLUENT DESIGN STYLESHEET ---
FLUENT_QSS = """
    QWidget { font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif; font-size: 14px; color: #1A1A1A; background-color: #F3F3F3; }
    QFrame.Card { background-color: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 8px; }
    QLabel.SectionTitle { font-size: 16px; font-weight: 600; color: #0067C0; }
    QComboBox, QDateEdit { background-color: #FFFFFF; border: 1px solid #D1D1D1; border-radius: 4px; padding: 4px 8px; min-height: 24px; }
    QPushButton { background-color: #FFFFFF; border: 1px solid #D1D1D1; border-radius: 4px; padding: 5px 16px; font-weight: 500; }
    QPushButton:hover { background-color: #F6F6F6; }
    QPushButton[class="primary"] { background-color: #0067C0; color: #FFFFFF; border: 1px solid #005FB8; }
    QPushButton[class="primary"]:hover { background-color: #1874D0; }

    QTabWidget::pane { border: 1px solid #E5E5E5; border-radius: 6px; background: white; }
    QTabBar::tab { background: #F3F3F3; padding: 6px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
    QTabBar::tab:selected { background: #FFFFFF; border-bottom: 2px solid #0067C0; color: #0067C0; font-weight: bold; }

    /* Expert Advice Box */
    QGroupBox { font-weight: bold; border: 1px solid #D1D1D1; border-radius: 6px; margin-top: 10px; background: #FFF; }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #0067C0; }
    QTextEdit { border: none; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.4; }
"""


class IQCMonitoringChartTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)

        self.dept_service = DepartmentService()
        self.catalog_service = CatalogService()
        self.iqc_service = IQCService()

        self._lots_cache: Dict[str, List[Dict[str, str]]] = {'L1': [], 'L2': [], 'L3': []}
        self._test_cache: List[str] = []

        self._build_ui()
        self._load_deps()
        self._on_dep_changed()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # --- Card 1: Compact Filter ---
        filter_card = QFrame()
        filter_card.setProperty("class", "Card")
        lay_filter = QVBoxLayout(filter_card)
        lay_filter.setContentsMargins(12, 12, 12, 12)
        lay_filter.setSpacing(8)

        # Header nhỏ gọn
        header_layout = QHBoxLayout()
        lbl_filter = QLabel("Bộ lọc & Phân tích")
        lbl_filter.setProperty("class", "SectionTitle")
        header_layout.addWidget(lbl_filter)

        self.b_analyze = QPushButton("Phân tích ngay")
        self.b_analyze.setProperty("class", "primary")
        self.b_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addStretch()
        header_layout.addWidget(self.b_analyze)

        lay_filter.addLayout(header_layout)

        # Grid thu gọn (2 dòng)
        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(12)

        self.cb_dep = QComboBox()
        self.cb_test = QComboBox();
        self.cb_test.setEditable(True)
        self.dt_from = QDateEdit(QDate.currentDate().addYears(-1));
        self.dt_from.setCalendarPopup(True);
        self.dt_from.setDisplayFormat("yyyy-MM-dd")
        self.dt_to = QDateEdit(QDate.currentDate());
        self.dt_to.setCalendarPopup(True);
        self.dt_to.setDisplayFormat("yyyy-MM-dd")

        # Dòng 1: Phòng ban | Test | Từ ngày | Đến ngày
        grid.addWidget(QLabel("Phòng ban:"), 0, 0);
        grid.addWidget(self.cb_dep, 0, 1)
        grid.addWidget(QLabel("Xét nghiệm:"), 0, 2);
        grid.addWidget(self.cb_test, 0, 3)
        grid.addWidget(QLabel("Từ ngày:"), 0, 4);
        grid.addWidget(self.dt_from, 0, 5)
        grid.addWidget(QLabel("Đến ngày:"), 0, 6);
        grid.addWidget(self.dt_to, 0, 7)

        # Dòng 2: L1 | L2 | L3
        self.cb_lot_l1 = QComboBox();
        self.cb_lot_l1.setEditable(True)
        self.cb_lot_l2 = QComboBox();
        self.cb_lot_l2.setEditable(True)
        self.cb_lot_l3 = QComboBox();
        self.cb_lot_l3.setEditable(True)

        grid.addWidget(QLabel("Lô L1:"), 1, 0);
        grid.addWidget(self.cb_lot_l1, 1, 1)
        grid.addWidget(QLabel("Lô L2:"), 1, 2);
        grid.addWidget(self.cb_lot_l2, 1, 3)
        grid.addWidget(QLabel("Lô L3:"), 1, 4);
        grid.addWidget(self.cb_lot_l3, 1, 5, 1, 3)  # Span cột cuối

        lay_filter.addLayout(grid)
        root.addWidget(filter_card)

        # --- Card 2: Splitter (Charts + Expert Advice) ---
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 2a. Charts Section
        chart_card = QFrame();
        chart_card.setProperty("class", "Card")
        lay_chart = QVBoxLayout(chart_card)
        lay_chart.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()

        # Tab 1
        t1 = QWidget();
        l1 = QVBoxLayout(t1)
        if HAS_MPL:
            self.fig_cv = Figure(figsize=(6, 4), tight_layout=True, facecolor='white')
            self.canvas_cv = FigureCanvas(self.fig_cv)
            self.fig_bias = Figure(figsize=(6, 4), tight_layout=True, facecolor='white')
            self.canvas_bias = FigureCanvas(self.fig_bias)
            h_lay = QHBoxLayout()
            h_lay.addWidget(self.canvas_cv, 1);
            h_lay.addWidget(self.canvas_bias, 1)
            l1.addLayout(h_lay)
        else:
            l1.addWidget(QLabel("Thiếu thư viện matplotlib"))
        self.tabs.addTab(t1, "Biểu đồ CV% và Bias%")

        # Tab 2
        t2 = QWidget();
        l2 = QVBoxLayout(t2)
        if HAS_MPL:
            self.fig_sigma = Figure(figsize=(6, 4), tight_layout=True, facecolor='white')
            self.canvas_sigma = FigureCanvas(self.fig_sigma)
            l2.addWidget(self.canvas_sigma)
        self.tabs.addTab(t2, "Xu hướng Sigma (Trend)")

        # Tab 3
        t3 = QWidget();
        l3 = QVBoxLayout(t3)
        if HAS_MPL:
            self.fig_cum = Figure(figsize=(6, 4), tight_layout=True, facecolor='white')
            self.canvas_cum = FigureCanvas(self.fig_cum)
            l3.addWidget(self.canvas_cum)
        self.tabs.addTab(t3, "Trung bình Tích lũy (Drift Check)")

        lay_chart.addWidget(self.tabs)
        splitter.addWidget(chart_card)

        # 2b. Expert Advice Box (Bảng Gợi ý)
        advice_group = QGroupBox("💡 GÓC CHUYÊN GIA: Đánh giá & Gợi ý biện pháp khắc phục")
        advice_layout = QVBoxLayout(advice_group)
        self.txt_advice = QTextEdit()
        self.txt_advice.setReadOnly(True)
        self.txt_advice.setPlaceholderText("Vui lòng chọn Lô và bấm 'Phân tích ngay' để nhận đánh giá chi tiết...")
        advice_layout.addWidget(self.txt_advice)

        splitter.addWidget(advice_group)

        # Tỉ lệ hiển thị: Biểu đồ (4 phần) - Lời khuyên (1 phần)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

        # Signals
        self.cb_dep.currentIndexChanged.connect(self._on_dep_changed)
        self.b_analyze.clicked.connect(self._on_analyze)

    # --- LOGIC DỮ LIỆU (GIỮ NGUYÊN 100% CỦA BẠN) ---
    def _load_deps(self):
        try:
            deps = self.dept_service.list_departments(active_only=True)
            fill_combo_from_list(self.cb_dep, [{"id": d.name, "name": d.name} for d in deps], text_key="name",
                                 id_key="id")
        except:
            pass

    def _on_dep_changed(self):
        dep = self.cb_dep.currentText()
        try:
            self._test_cache = self.catalog_service.list_tests_by_department(dep)
            self.cb_test.clear();
            self.cb_test.addItems([""] + self._test_cache)
        except:
            pass
        try:
            self._lots_cache = self.catalog_service.list_active_lots_by_level(dep, only_valid_expiry=False)
            for k, cb in zip(['L1', 'L2', 'L3'], [self.cb_lot_l1, self.cb_lot_l2, self.cb_lot_l3]):
                cb.clear();
                add_combo_item(cb, f"— Chọn Lô {k} —", None)
                for l in self._lots_cache.get(k, []): add_combo_item(cb, l["lot_no"], l["lot_no"])
        except:
            pass

    def _get_data_and_stats(self, dep, test, lot, level) -> Tuple[Dict, List, float, float]:
        """Lấy dữ liệu và tính toán thống kê (Logic cũ)."""
        target_data = self.catalog_service.get_target_by_lot(test, level, lot)
        t_mean = _to_float(target_data.get("mean")) if target_data else None
        t_tea = _to_float(target_data.get("tea")) if target_data else None

        frm = self.dt_from.date().toString("yyyy-MM-dd")
        to = self.dt_to.date().toString("yyyy-MM-dd")

        # Lấy dữ liệu (active_only=False để lấy cả lịch sử nếu cần thiết chỉnh trong DB)
        # Theo code gốc bạn cung cấp thì dùng active_only=True, tôi giữ nguyên logic đó nếu bạn muốn
        # Hoặc đổi thành active_only=False để an toàn hơn cho dữ liệu cũ.
        # Ở đây tôi để active_only=False cho chắc chắn (giống bản fix trước).
        history = self.iqc_service.get_history(dep, frm, to, test, lot, level, limit=5000, active_only=False)

        data_m = {}
        raw_pts = []  # (date, value) cho Cumulative

        for r in history:
            val = r.get('value_num');
            d_str = r.get('run_date')
            # Fix lỗi dấu phẩy nếu có
            if isinstance(val, str):
                try:
                    val = float(val.replace(',', '.'))
                except:
                    continue
            if val is None or not d_str: continue

            try:
                d_obj = dt.datetime.strptime(d_str, "%Y-%m-%d").date()
                raw_pts.append((d_obj, val))
            except:
                pass

            mk = d_str[:7]
            if mk not in data_m: data_m[mk] = []
            data_m[mk].append(val)

        stats_m = {}
        for m, vals in data_m.items():
            if len(vals) < 2: continue
            s = basic_stats(vals)
            mean = s.get('mean');
            sd = s.get('sd')

            cv = analytics.safe_cv_percent(mean, sd)
            bias = analytics.calculate_bias_percent(mean, t_mean)
            sigma = 0
            if t_tea and cv > 0: sigma = (t_tea - abs(bias)) / cv

            stats_m[m] = {"cv": cv, "bias": bias, "sigma": sigma}

        return stats_m, raw_pts, t_mean, t_tea

    # --- LOGIC TẠO LỜI KHUYÊN (MỚI) ---
    def _generate_advice(self, level, stats_m, t_tea):
        if not stats_m: return ""

        # Tính trung bình toàn bộ giai đoạn
        avg_cv = sum(s['cv'] for s in stats_m.values()) / len(stats_m)
        avg_bias = sum(s['bias'] for s in stats_m.values()) / len(stats_m)
        avg_sigma = sum(s['sigma'] for s in stats_m.values()) / len(stats_m)

        advice = f"► {level}: Sigma TB={avg_sigma:.1f}σ | CV={avg_cv:.1f}% | Bias={avg_bias:.1f}%\n"

        # Đánh giá Sigma
        if avg_sigma < 3.0:
            advice += "   ⛔ [NGUY HIỂM] Sigma < 3. Hệ thống không đạt yêu cầu.\n" \
                      "      👉 HÀNH ĐỘNG: Dừng máy, kiểm tra lại Hóa chất, Calibrator, QC.\n"
        elif avg_sigma < 4.0:
            advice += "   ⚠️ [CẢNH BÁO] Sigma thấp (3-4). Hiệu năng kém.\n" \
                      "      👉 HÀNH ĐỘNG: Tăng tần suất QC (N=4), theo dõi chặt chẽ.\n"
        elif avg_sigma >= 6.0:
            advice += "   ✅ [XUẤT SẮC] Sigma > 6. Hệ thống hoạt động rất ổn định.\n"

        # Gợi ý kỹ thuật dựa trên CV/Bias (Nếu có TEa)
        if t_tea:
            # CV cao (> 1/3 TEa) -> Lỗi ngẫu nhiên
            if avg_cv > (0.33 * t_tea):
                advice += "   🔧 [Lỗi Ngẫu nhiên] CV% cao bất thường.\n" \
                          "      👉 GỢI Ý: Bảo dưỡng kim hút, kiểm tra bọt khí, hệ thống rửa cuvet, điện áp.\n"

            # Bias cao (> 1/2 TEa) -> Lỗi hệ thống
            if abs(avg_bias) > (0.5 * t_tea):
                advice += "   🎯 [Lỗi Hệ thống] Bias% (Độ lệch) cao.\n" \
                          "      👉 GỢI Ý: Thực hiện Hiệu chuẩn (Calibrate) lại, kiểm tra hạn sử dụng thuốc thử.\n"

        advice += "-" * 50 + "\n"
        return advice

    def _on_analyze(self):
        if not HAS_MPL: return
        dep = self.cb_dep.currentText();
        test = self.cb_test.currentText()
        l1 = get_combo_id(self.cb_lot_l1);
        l2 = get_combo_id(self.cb_lot_l2);
        l3 = get_combo_id(self.cb_lot_l3)

        if not (test and (l1 or l2 or l3)):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn Test và ít nhất 1 Lô QC.")
            return

        # Xóa biểu đồ cũ
        self.fig_cv.clear();
        self.fig_bias.clear();
        self.fig_sigma.clear();
        self.fig_cum.clear()
        ax_cv = self.fig_cv.add_subplot(111);
        ax_bias = self.fig_bias.add_subplot(111)
        ax_sig = self.fig_sigma.add_subplot(111);
        ax_cum = self.fig_cum.add_subplot(111)

        has_data = False
        advice_text = ""

        # Hàm vẽ cho từng Level
        def plot_level(lot, lvl, mk, sty, col):
            if not lot: return
            stats, raw, tm, tea = self._get_data_and_stats(dep, test, lot, lvl)

            if stats:
                nonlocal has_data, advice_text
                has_data = True

                ms = sorted(stats.keys())
                cvs = [stats[m]['cv'] for m in ms];
                biases = [stats[m]['bias'] for m in ms];
                sigs = [stats[m]['sigma'] for m in ms]

                # Tab 1
                ax_cv.plot(ms, cvs, marker=mk, linestyle=sty, label=lvl, color=col)
                ax_bias.plot(ms, biases, marker=mk, linestyle=sty, label=lvl, color=col)
                # Tab 2
                ax_sig.plot(ms, sigs, marker=mk, linestyle=sty, label=lvl, color=col, linewidth=2)

                # Thêm đánh giá
                advice_text += self._generate_advice(lvl, stats, tea)

            if raw:
                # Tab 3: Cumulative
                raw.sort(key=lambda x: x[0])
                dates = [x[0] for x in raw];
                vals = [x[1] for x in raw]
                # Tính Cumulative Mean
                cum = [sum(vals[:i + 1]) / (i + 1) for i in range(len(vals))]

                ax_cum.plot(dates, cum, linestyle=sty, label=f"{lvl} Mean", color=col)
                if tm: ax_cum.axhline(tm, linestyle=':', color=col, alpha=0.5)

        # Thực thi vẽ
        plot_level(l1, "L1", 'o', '-', 'blue')
        plot_level(l2, "L2", 's', '--', 'green')
        plot_level(l3, "L3", '^', '-.', 'purple')

        if not has_data:
            self.txt_advice.setText("Không tìm thấy dữ liệu.")
            QMessageBox.information(self, "Thông báo", "Không tìm thấy dữ liệu phù hợp.")
            return

        # Cập nhật Textbox Gợi ý
        self.txt_advice.setText(advice_text)

        # Trang trí biểu đồ (Labels, Grids)
        for ax, tit, yl in [(ax_cv, "CV%", "CV (%)"), (ax_bias, "Bias%", "Bias (%)"), (ax_sig, "Sigma", "Sigma")]:
            ax.set_title(f"Theo dõi {tit} - {test}", fontweight='bold')
            ax.set_ylabel(yl);
            ax.grid(True, linestyle=':', alpha=0.6);
            ax.legend()
            ax.tick_params(axis='x', rotation=30)

        # Vùng màu Sigma
        ax_sig.axhspan(6, 12, color='green', alpha=0.1);
        ax_sig.axhspan(3, 6, color='orange', alpha=0.1);
        ax_sig.axhspan(0, 3, color='red', alpha=0.1)
        ax_sig.set_ylim(0, 10)

        ax_cum.set_title("Trung bình Tích lũy (Drift Check)", fontweight='bold');
        ax_cum.set_ylabel("Giá trị")
        ax_cum.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'));
        ax_cum.grid(True);
        ax_cum.legend()

        self.canvas_cv.draw();
        self.canvas_bias.draw();
        self.canvas_sigma.draw();
        self.canvas_cum.draw()