# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_mu_dialog.py
(FLUENT DESIGN VERSION)
Dialog tính Độ không đảm bảo đo (Measurement Uncertainty - MU).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QDialogButtonBox, QFrame
)
from app.utils.analytics import calculate_measurement_uncertainty

# --- FLUENT DESIGN STYLESHEET ---
FLUENT_DIALOG_QSS = """
    QDialog {
        background-color: #F3F3F3;
        font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
        font-size: 14px;
        color: #1A1A1A;
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
        margin-bottom: 5px;
    }
    QLabel.ValueLabel {
        font-weight: bold;
        color: #333333;
    }
    QDoubleSpinBox {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 5px 8px;
        min-height: 24px;
    }
    QDoubleSpinBox:focus {
        border: 2px solid #0067C0;
        border-bottom: 2px solid #0067C0;
    }
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: 500;
        min-width: 80px;
    }
    QPushButton:hover { background-color: #F6F6F6; }
    QPushButton:pressed { background-color: #F0F0F0; border-color: #B0B0B0; }
"""


class MeasurementUncertaintyDialog(QDialog):
    def __init__(self, parent=None, test_name="", level="", mean=0.0, sd=0.0, bias=0.0, unit=""):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_DIALOG_QSS)
        self.setWindowTitle(f"Độ Không Đảm Bảo Đo (MU) - {test_name} {level}")
        self.resize(500, 480)

        self.lab_mean = mean
        self.lab_sd = sd
        self.lab_bias = abs(bias)
        self.unit = unit

        self._build_ui()
        self._calculate()  # Tính ngay lần đầu

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- Card 1: Input ---
        card_in = QFrame()
        card_in.setProperty("class", "Card")
        l_in = QVBoxLayout(card_in)

        # Title (Fix lỗi setProperty)
        lbl_title_in = QLabel("1. Thông số đầu vào (Từ IQC)")
        lbl_title_in.setProperty("class", "SectionTitle")
        l_in.addWidget(lbl_title_in)

        f_in = QFormLayout()
        f_in.setSpacing(12)

        # Labels (Read-only)
        self.lbl_mean = QLabel(f"{self.lab_mean:.4g} {self.unit}")
        self.lbl_mean.setProperty("class", "ValueLabel")

        self.lbl_sd = QLabel(f"{self.lab_sd:.4g} {self.unit} (uRw)")
        self.lbl_sd.setProperty("class", "ValueLabel")

        # Inputs (Editable)
        self.sp_bias = QDoubleSpinBox()
        self.sp_bias.setRange(0, 100000)
        self.sp_bias.setDecimals(4)
        self.sp_bias.setValue(self.lab_bias)
        self.sp_bias.setSuffix(f" {self.unit}")
        self.sp_bias.setToolTip("Độ chệch tuyệt đối (uBias). Có thể nhập từ báo cáo EQA.")

        self.sp_k = QDoubleSpinBox()
        self.sp_k.setRange(1, 3)
        self.sp_k.setValue(2.0)  # Mặc định 95%
        self.sp_k.setSingleStep(0.1)

        f_in.addRow("Trung bình (Mean):", self.lbl_mean)
        f_in.addRow("Độ lệch chuẩn (SD):", self.lbl_sd)
        f_in.addRow("Độ chệch (Bias):", self.sp_bias)
        f_in.addRow("Hệ số phủ (k):", self.sp_k)

        l_in.addLayout(f_in)
        layout.addWidget(card_in)

        # --- Card 2: Output ---
        card_out = QFrame()
        card_out.setProperty("class", "Card")
        l_out = QVBoxLayout(card_out)

        # Title (Fix lỗi setProperty)
        lbl_title_out = QLabel("2. Kết quả MU")
        lbl_title_out.setProperty("class", "SectionTitle")
        l_out.addWidget(lbl_title_out)

        f_out = QFormLayout()
        f_out.setSpacing(12)

        # Result Labels
        self.lbl_uc = QLabel("0.000")
        self.lbl_uc.setStyleSheet("font-size: 14px; color: #555;")

        self.lbl_U = QLabel("0.000")
        self.lbl_U.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078D4;")

        self.lbl_U_percent = QLabel("0.00%")
        self.lbl_U_percent.setStyleSheet("font-size: 16px; font-weight: bold; color: #27AE60;")

        f_out.addRow("ĐKBĐ chuẩn (u_c):", self.lbl_uc)
        f_out.addRow("ĐKBĐ mở rộng (U):", self.lbl_U)
        f_out.addRow("ĐKBĐ mở rộng (%):", self.lbl_U_percent)

        l_out.addLayout(f_out)
        layout.addWidget(card_out)

        # 3. Footer info
        lbl_formula = QLabel("<i>Công thức: U = k × √(SD² + Bias²)</i>")
        lbl_formula.setAlignment(Qt.AlignCenter)
        lbl_formula.setStyleSheet("color: #666; margin-top: 5px;")
        layout.addWidget(lbl_formula)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.accept)
        layout.addWidget(btns)

        # Signals
        self.sp_bias.valueChanged.connect(self._calculate)
        self.sp_k.valueChanged.connect(self._calculate)

    def _calculate(self):
        bias = self.sp_bias.value()
        k = self.sp_k.value()

        # Gọi logic tính toán (Giả định hàm này trả về dict {"u_c": float, "U_expanded": float})
        res = calculate_measurement_uncertainty(self.lab_sd, bias, k)

        u_c = res.get("u_c", 0.0)
        U = res.get("U_expanded", 0.0)

        U_perc = (U / self.lab_mean * 100.0) if self.lab_mean != 0 else 0.0

        self.lbl_uc.setText(f"{u_c:.4f}")
        self.lbl_U.setText(f"± {U:.4f} {self.unit}")
        self.lbl_U_percent.setText(f"± {U_perc:.2f} %")