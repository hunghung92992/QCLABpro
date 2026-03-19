# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_predictive_tab.py
(FLUENT DESIGN VERSION - AI TREND PREDICTION UPGRADE - FIXED IMPORTS)
Tab phân tích dự đoán AI cho QC (Predictive AI) với các tính năng nâng cao:
- Time to Failure: Dự báo ngày vi phạm 2SD/3SD.
- Failure Forecast: Dự báo điểm rơi Z-score.
- Future Simulation: Vẽ vùng dự đoán trên biểu đồ.
- Drift Warning: Cảnh báo trôi dạt sớm.
"""
from __future__ import annotations
from typing import Optional, List, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QPushButton, QMessageBox, QLabel, QSpinBox, QFrame, QGridLayout, QScrollArea, QCheckBox
)

# Services
from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService
from app.services.predictive_service import PredictiveService

# Helper functions
from app.utils.qt_compat import (
    fill_combo_from_list
)
# [FIX] Thêm dòng import còn thiếu
from app.utils.validators import to_float_safe as _to_float

# Matplotlib & Scipy
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats

    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = QWidget
    Figure = lambda *args, **kwargs: None
    np = None

# --- FLUENT DESIGN STYLESHEET (Mini) ---
FLUENT_QSS = """
    QWidget {
        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
        font-size: 14px;
        color: #1A1A1A;
        background-color: #F3F3F3;
    }
    QFrame.Card {
        background-color: #FFFFFF;
        border: 1px solid #E5E5E5;
        border-radius: 8px;
    }
    QLabel.SectionTitle {
        font-size: 16px;
        font-weight: 600;
        color: #0067C0;
    }
    QComboBox, QSpinBox, QDoubleSpinBox {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 5px 8px;
        min-height: 24px;
    }
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
        border: 2px solid #0067C0;
        border-bottom: 2px solid #0067C0;
    }
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: 500;
    }
    QPushButton:hover { background-color: #F6F6F6; }

    QPushButton[class="primary"] {
        background-color: #0067C0;
        color: #FFFFFF;
        border: 1px solid #005FB8;
    }
    QPushButton[class="primary"]:hover { background-color: #1874D0; }

    QCheckBox { spacing: 8px; }
    QCheckBox::indicator { width: 18px; height: 18px; }
"""


class IQCPredictiveTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)

        self.dept_service = DepartmentService()
        self.catalog_service = CatalogService()
        # Nếu chưa có PredictiveService đầy đủ, ta sẽ dùng logic nội tại trong class này
        # Lưu ý: Cần đảm bảo PredictiveService đã được khởi tạo đúng hoặc dùng IQCService thay thế nếu cần lấy data
        self.predictive_service = PredictiveService()
        # Để lấy dữ liệu lịch sử, ta có thể cần truy cập IQCService thông qua PredictiveService hoặc khởi tạo riêng
        # self.iqc_service = IQCService()

        self._lots_cache: Dict[str, List[Dict[str, str]]] = {'L1': [], 'L2': [], 'L3': []}

        self._build_ui()
        self._load_deps()
        self._on_dep_changed()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # --- Card 1: Cấu hình (Config) ---
        config_card = QFrame()
        config_card.setProperty("class", "Card")
        lay_config = QVBoxLayout(config_card)

        lbl_config = QLabel("Cấu hình Mô hình Dự đoán & Phân tích Xu hướng")
        lbl_config.setProperty("class", "SectionTitle")
        lay_config.addWidget(lbl_config)

        # Grid Inputs
        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(16)

        # Row 1
        self.cb_dep = QComboBox()
        self.cb_test = QComboBox()
        self.cb_test.setEditable(True)
        self.cb_level = QComboBox()
        self.cb_level.addItems(["L1", "L2", "L3"])
        self.cb_lot = QComboBox()
        self.cb_lot.setEditable(True)

        grid.addWidget(QLabel("Phòng ban:"), 0, 0)
        grid.addWidget(self.cb_dep, 0, 1)
        grid.addWidget(QLabel("Test Code:"), 0, 2)
        grid.addWidget(self.cb_test, 0, 3)
        grid.addWidget(QLabel("Level:"), 0, 4)
        grid.addWidget(self.cb_level, 0, 5)

        # Row 2
        grid.addWidget(QLabel("Lot:"), 1, 0)
        grid.addWidget(self.cb_lot, 1, 1)

        self.sp_predict_steps = QSpinBox()
        self.sp_predict_steps.setRange(1, 30)  # Tăng range lên để dự báo xa hơn
        self.sp_predict_steps.setValue(7)
        self.sp_predict_steps.setSuffix(" ngày")

        self.chk_remove_outliers = QCheckBox("Loại bỏ nhiễu (Outliers > 3SD)")
        self.chk_remove_outliers.setChecked(True)

        grid.addWidget(QLabel("Dự báo trước:"), 1, 2)
        grid.addWidget(self.sp_predict_steps, 1, 3)
        grid.addWidget(self.chk_remove_outliers, 1, 4, 1, 2)

        lay_config.addLayout(grid)

        # Run Button
        self.btn_run = QPushButton("⚡ Chạy Phân tích & Dự báo Trend")
        self.btn_run.setProperty("class", "primary")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setMinimumHeight(36)
        lay_config.addWidget(self.btn_run)

        root.addWidget(config_card)

        # --- Card 2: Kết quả & Action (Horizontal Split) ---
        h_split = QHBoxLayout()
        h_split.setSpacing(16)

        # Result Box
        res_card = QFrame()
        res_card.setProperty("class", "Card")
        lay_res = QVBoxLayout(res_card)

        lbl_res = QLabel("Kết quả Dự báo")
        lbl_res.setProperty("class", "SectionTitle")
        lay_res.addWidget(lbl_res)

        form_res = QFormLayout()
        form_res.setSpacing(10)

        self.lbl_slope = QLabel("---")
        self.lbl_slope.setStyleSheet("font-weight: bold;")
        self.lbl_next_z = QLabel("---")
        self.lbl_next_z.setStyleSheet("font-weight: bold; color: #0067C0;")
        self.lbl_time_to_fail = QLabel("---")
        self.lbl_time_to_fail.setStyleSheet("font-weight: bold; color: #D32F2F;")
        self.lbl_status = QLabel("---")

        form_res.addRow("Độ dốc (Slope):", self.lbl_slope)
        form_res.addRow("Dự báo Z-Score (Cuối kỳ):", self.lbl_next_z)
        form_res.addRow("Dự báo 'Ngày sụp đổ' (2SD):", self.lbl_time_to_fail)
        form_res.addRow("Trạng thái:", self.lbl_status)
        lay_res.addLayout(form_res)
        lay_res.addStretch(1)

        h_split.addWidget(res_card, 1)  # Flex 1

        # Action Box
        act_card = QFrame()
        act_card.setProperty("class", "Card")
        lay_act = QVBoxLayout(act_card)

        lbl_act = QLabel("Phân tích & Đề xuất Hành động")
        lbl_act.setProperty("class", "SectionTitle")
        lay_act.addWidget(lbl_act)

        self.lbl_recommendation = QLabel("Vui lòng chạy phân tích để nhận báo cáo chi tiết.")
        self.lbl_recommendation.setWordWrap(True)
        self.lbl_recommendation.setStyleSheet("""
            padding: 10px; background-color: #F8F9FA; 
            border: 1px solid #E9ECEF; border-radius: 4px; color: #495057; font-size: 13px;
        """)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        l_scroll = QVBoxLayout(scroll_content)
        l_scroll.setContentsMargins(0, 0, 0, 0)
        l_scroll.addWidget(self.lbl_recommendation)
        l_scroll.addStretch(1)
        scroll.setWidget(scroll_content)

        lay_act.addWidget(scroll)
        h_split.addWidget(act_card, 2)  # Flex 2 (Wider)

        root.addLayout(h_split, 1)

        # --- Card 3: Chart ---
        if HAS_MPL:
            chart_card = QFrame()
            chart_card.setProperty("class", "Card")
            lay_chart = QVBoxLayout(chart_card)

            # Use white background for figure to match card
            self.fig = Figure(figsize=(6, 4), tight_layout=True, facecolor='white')
            self.canvas = FigureCanvas(self.fig)
            lay_chart.addWidget(self.canvas)
            root.addWidget(chart_card, 2)  # Flex 2
        else:
            self.canvas = None
            lbl_err = QLabel("Thiếu 'matplotlib' hoặc 'scipy' để vẽ biểu đồ và phân tích.")
            lbl_err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(lbl_err)

        # --- Signals ---
        self.cb_dep.currentIndexChanged.connect(self._on_dep_changed)
        self.cb_level.currentIndexChanged.connect(self._reload_lot_list)
        self.btn_run.clicked.connect(self._on_run_predictive_model)

    # --- LOGIC ---
    def _load_deps(self):
        try:
            deps_list = self.dept_service.list_departments(active_only=True)
            fill_combo_from_list(self.cb_dep, [{"id": d.name, "name": d.name} for d in deps_list], text_key="name",
                                 id_key="id")
        except:
            pass

    def _reload_lot_list(self):
        dep_name = self.cb_dep.currentText()
        level_selected = self.cb_level.currentText()
        try:
            self._lots_cache = self.catalog_service.list_active_lots_by_level(dep_name, only_valid_expiry=False)
            lot_names = [info['lot_no'] for info in self._lots_cache.get(level_selected, [])]
            lot_names.sort()
            current_lot = self.cb_lot.currentText()
            self.cb_lot.clear()
            self.cb_lot.addItem("", None)
            self.cb_lot.addItems(lot_names)
            self.cb_lot.setCurrentText(current_lot)
        except Exception as e:
            print(f"[IQCPredictive] Lỗi nạp LOT: {e}")
            self.cb_lot.clear()

    def _on_dep_changed(self):
        dep_name = self.cb_dep.currentText()
        try:
            tests = self.catalog_service.list_tests_by_department(dep_name)
            current_test = self.cb_test.currentText()
            self.cb_test.clear()
            self.cb_test.addItem("", None)
            self.cb_test.addItems(tests)
            self.cb_test.setCurrentText(current_test)
        except Exception as e:
            print(f"[IQCPredictive] Lỗi nạp test: {e}")
        self._reload_lot_list()

    def _calculate_time_to_failure(self, slope: float, intercept: float, current_x: int) -> str:
        """Tính số ngày dự kiến chạm ngưỡng 2SD hoặc 3SD."""
        if slope == 0: return "Không xác định (Xu hướng phẳng)"

        # Ngưỡng mục tiêu: +2SD, -2SD
        target_z = 2.0 if slope > 0 else -2.0

        # y = mx + c => x = (y - c) / m
        days_needed = (target_z - intercept) / slope
        days_remaining = days_needed - current_x

        if days_remaining <= 0:
            return "Đã vượt ngưỡng!"
        elif days_remaining > 100:
            return "> 3 tháng (An toàn)"
        else:
            return f"~ {int(days_remaining)} ngày nữa"

    def _on_run_predictive_model(self):
        dep = self.cb_dep.currentText()
        test = self.cb_test.currentText()
        level = self.cb_level.currentText()
        lot = self.cb_lot.currentText()

        if not (dep and test and level and lot):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn đầy đủ Phòng ban, Test, Level và Lot.")
            return

        if not HAS_MPL:
            QMessageBox.critical(self, "Lỗi Thư viện", "Thiếu thư viện ML/Matplotlib.")
            return

        try:
            # 1. Lấy dữ liệu thô để tính Z-Score
            # Lưu ý: Cần đảm bảo self.predictive_service có thuộc tính iqc_service hoặc dùng self.iqc_service nếu khởi tạo
            # Ở đây giả định PredictiveService có access vào IQCService hoặc bạn có thể import IQCService và dùng trực tiếp
            # Để an toàn, tôi sẽ dùng self.predictive_service.iqc_service nếu có, nếu không thì báo lỗi hoặc cần sửa lại __init__

            # Sửa lại phần này: Dùng trực tiếp IQCService nếu PredictiveService chưa expose
            from app.services.iqc_service import IQCService
            iqc_srv = IQCService()

            raw_data = iqc_srv.get_history(dep, "2020-01-01", "2099-12-31", test, lot, level, limit=100,
                                           active_only=False)
            if not raw_data:
                QMessageBox.information(self, "Thông báo", "Không có dữ liệu lịch sử.")
                return

            # Lấy target để tính Z
            target = self.catalog_service.get_target_by_lot(test, level, lot)
            mean, sd = _to_float(target.get('mean')), _to_float(target.get('sd'))

            if not mean or not sd:
                QMessageBox.warning(self, "Lỗi Target", "Chưa thiết lập Mean/SD cho Lot này.")
                return

            z_scores = []
            for r in raw_data:
                val = r.get('value_num')
                if val is not None:
                    # Xử lý dấu phẩy
                    if isinstance(val, str): val = float(val.replace(',', '.'))
                    z = (val - mean) / sd
                    z_scores.append(z)

            # Xử lý lọc nhiễu
            if self.chk_remove_outliers.isChecked():
                z_scores = [z for z in z_scores if abs(z) <= 3.0]

            if len(z_scores) < 5:
                QMessageBox.warning(self, "Dữ liệu ít", "Cần tối thiểu 5 điểm dữ liệu để dự báo xu hướng.")
                return

        except Exception as e:
            QMessageBox.critical(self, "Lỗi xử lý dữ liệu", str(e))
            return

        # 2. Phân tích Hồi quy Tuyến tính (Linear Regression)
        try:
            X = np.arange(len(z_scores))
            Y = np.array(z_scores)

            slope, intercept, r_value, p_value, std_err = stats.linregress(X, Y)

            # Dự báo điểm tiếp theo
            future_steps = self.sp_predict_steps.value()
            next_x = len(X) + future_steps
            next_z = slope * next_x + intercept

            # Tính Time to Failure
            ttf_str = self._calculate_time_to_failure(slope, intercept, len(X))

            # 3. Hiển thị kết quả
            self.lbl_slope.setText(f"{slope:.4f}")
            self.lbl_next_z.setText(f"{next_z:.2f}")
            self.lbl_time_to_fail.setText(ttf_str)

            # Đánh giá trạng thái
            status_text = "Ổn định"
            color = "green"
            recommendation = ""

            if abs(slope) > 0.1:  # Độ dốc cao
                status_text = "CẢNH BÁO: Xu hướng trôi dạt (Drift)"
                color = "orange"
                recommendation += "⚠️ Phát hiện xu hướng trôi dạt rõ rệt.\n"
                recommendation += "👉 Kiểm tra lại hệ thống: Kim hút, nhiệt độ ủ, hoặc lô thuốc thử sắp hết hạn.\n"

            if abs(next_z) > 2.0:
                status_text = "NGUY HIỂM: Sắp vượt ngưỡng 2SD"
                color = "red"
                recommendation += f"🚨 Dự báo QC sẽ chạm ngưỡng {abs(next_z):.2f}SD trong {future_steps} ngày tới.\n"
                recommendation += "👉 Hành động ngay: Hiệu chuẩn (Calibrate) lại máy hoặc thay mới QC/Thuốc thử.\n"

            if not recommendation:
                recommendation = "✅ Hệ thống hoạt động ổn định. Không phát hiện xu hướng bất thường."

            self.lbl_status.setText(status_text)
            self.lbl_status.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 14px;")
            self.lbl_recommendation.setText(recommendation)

            # 4. Vẽ biểu đồ
            self._plot_trend_forecast(X, Y, slope, intercept, future_steps)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi tính toán", f"Lỗi khi chạy mô hình: {str(e)}")

    def _plot_trend_forecast(self, X, Y, slope, intercept, future_steps):
        if not self.canvas: return
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        # Vẽ dữ liệu lịch sử
        ax.plot(X, Y, 'o', label='Dữ liệu thực tế', color='#1976D2', alpha=0.6)

        # Vẽ đường xu hướng (Trendline) cho quá khứ
        ax.plot(X, slope * X + intercept, 'b-', label='Xu hướng hiện tại', alpha=0.5)

        # Vẽ vùng dự báo tương lai
        X_future = np.arange(X[-1], X[-1] + future_steps + 1)
        Y_future = slope * X_future + intercept

        # Vẽ vùng tin cậy (Confidence Interval - Giả lập đơn giản bằng độ lệch chuẩn dư)
        residuals = Y - (slope * X + intercept)
        std_resid = np.std(residuals)
        # Vùng 95% tin cậy (~1.96 SD) mở rộng theo thời gian
        # Công thức đơn giản hóa cho visual
        ci = 1.96 * std_resid * np.sqrt(1 + 1 / len(X) + (X_future - np.mean(X)) ** 2 / np.sum((X - np.mean(X)) ** 2))

        ax.plot(X_future, Y_future, 'r--', label='Dự báo tương lai', linewidth=2)
        ax.fill_between(X_future, Y_future - ci, Y_future + ci, color='red', alpha=0.1, label='Vùng tin cậy 95%')

        # Các đường giới hạn SD
        ax.axhline(0, color='gray', linestyle='-', linewidth=0.5)
        ax.axhline(2, color='orange', linestyle='--', label='+2SD')
        ax.axhline(-2, color='orange', linestyle='--')
        ax.axhline(3, color='red', linestyle=':', label='+3SD')
        ax.axhline(-3, color='red', linestyle=':')

        ax.set_title("Biểu đồ Dự báo Xu hướng QC (AI Trend Prediction)", fontsize=10, fontweight='bold')
        ax.set_xlabel("Lần chạy (Run)")
        ax.set_ylabel("Z-Score (SDI)")
        ax.legend(loc='upper left', fontsize='small')
        ax.grid(True, linestyle=':', alpha=0.5)

        # Giới hạn trục Y để dễ nhìn
        y_max = max(3.5, np.max(np.abs(Y)) + 0.5)
        ax.set_ylim(-y_max, y_max)

        self.canvas.draw()