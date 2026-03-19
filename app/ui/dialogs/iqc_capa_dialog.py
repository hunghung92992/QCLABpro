# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_capa_dialog.py
(FLUENT DESIGN VERSION)
Form nhập liệu Hành động khắc phục (CAPA).
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QComboBox,
    QTextEdit, QDialogButtonBox, QMessageBox, QFrame, QPushButton
)
from app.services.capa_service import CapaService

# Danh sách gợi ý (Standard Options)
ROOT_CAUSES = [
    "Lỗi ngẫu nhiên (Random Error)",
    "Lỗi hệ thống (Systematic Error)",
    "Hóa chất hỏng/hết hạn",
    "Calibration không đạt",
    "Bóng đèn quang kế già",
    "Kim hút mẫu bị tắc",
    "Bọt khí trong đường ống",
    "Lỗi pha chế mẫu QC"
]

ACTIONS = [
    "Chạy lại mẫu (Rerun)",
    "Hiệu chuẩn lại (Recalibrate)",
    "Thay hóa chất mới (New Reagent)",
    "Thay bóng đèn/Bảo trì máy",
    "Pha lại mẫu QC mới",
    "Kiểm tra lại nhiệt độ tủ lạnh"
]

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
    QComboBox, QTextEdit {
        background-color: #FFFFFF;
        border: 1px solid #D1D1D1;
        border-radius: 4px;
        padding: 5px 8px;
    }
    QComboBox:focus, QTextEdit:focus {
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

    QPushButton[class="primary"] {
        background-color: #0067C0;
        color: #FFFFFF;
        border: 1px solid #005FB8;
    }
    QPushButton[class="primary"]:hover { background-color: #1874D0; }
"""


class CapaDialog(QDialog):
    def __init__(self, parent=None, result_id=None, test_info=""):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_DIALOG_QSS)
        self.setWindowTitle("Phiếu Hành động Khắc phục (CAPA)")
        self.resize(550, 520)

        self.result_id = result_id
        self.svc = CapaService()

        self._build_ui(test_info)
        self._load_data()

    def _build_ui(self, test_info):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- Header Section ---
        lbl_title = QLabel("Báo cáo Sự cố & Khắc phục")
        lbl_title.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_title)

        # Info Box (Context)
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #E3F2FD; border-radius: 6px; padding: 10px;")
        l_info = QVBoxLayout(info_frame)
        l_info.setContentsMargins(10, 10, 10, 10)

        lbl_info_text = QLabel(f"<b>Kết quả IQC:</b> {test_info}")
        lbl_info_text.setStyleSheet("color: #0D47A1;")
        lbl_info_text.setWordWrap(True)
        l_info.addWidget(lbl_info_text)

        layout.addWidget(info_frame)

        # --- Card: Form Input ---
        card = QFrame()
        card.setProperty("class", "Card")
        l_card = QVBoxLayout(card)
        l_card.setSpacing(15)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        # 1. Nguyên nhân gốc rễ
        self.cb_root = QComboBox()
        self.cb_root.setEditable(True)
        self.cb_root.addItems([""] + ROOT_CAUSES)
        self.cb_root.setPlaceholderText("Chọn hoặc nhập nguyên nhân...")
        self.cb_root.setMinimumHeight(30)

        # 2. Hành động khắc phục
        self.cb_action = QComboBox()
        self.cb_action.setEditable(True)
        self.cb_action.addItems([""] + ACTIONS)
        self.cb_action.setPlaceholderText("Chọn hoặc nhập hành động...")
        self.cb_action.setMinimumHeight(30)

        # 3. Phòng ngừa (Optional)
        self.txt_prevent = QTextEdit()
        self.txt_prevent.setPlaceholderText("Hành động để tránh lặp lại lỗi này (nếu có)...")
        self.txt_prevent.setMaximumHeight(70)

        # 4. Kết quả sau khắc phục
        self.cb_outcome = QComboBox()
        self.cb_outcome.addItems(["Đã khắc phục (Pass)", "Chưa khắc phục (Fail)", "Cần theo dõi thêm"])
        self.cb_outcome.setMinimumHeight(30)

        form.addRow("1. Nguyên nhân:", self.cb_root)
        form.addRow("2. Khắc phục:", self.cb_action)
        form.addRow("3. Phòng ngừa:", self.txt_prevent)
        form.addRow("4. Kết quả:", self.cb_outcome)

        l_card.addLayout(form)
        layout.addWidget(card)

        # --- Buttons ---
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        # Style Save Button
        btn_save = btns.button(QDialogButtonBox.Save)
        btn_save.setText("Lưu Phiếu")
        btn_save.setProperty("class", "primary")

        # Style Cancel Button
        btn_cancel = btns.button(QDialogButtonBox.Cancel)
        btn_cancel.setText("Hủy bỏ")

        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_data(self):
        if not self.result_id: return
        data = self.svc.get_capa(self.result_id)
        if data:
            self.cb_root.setCurrentText(data.get("root_cause") or "")
            self.cb_action.setCurrentText(data.get("corrective_action") or "")
            self.txt_prevent.setText(data.get("preventive_action") or "")
            self.cb_outcome.setCurrentText(data.get("outcome") or "Đã khắc phục (Pass)")

    def _save(self):
        data = {
            "result_id": self.result_id,
            "root_cause": self.cb_root.currentText(),
            "corrective_action": self.cb_action.currentText(),
            "preventive_action": self.txt_prevent.toPlainText(),
            "outcome": self.cb_outcome.currentText(),
            "created_by": "current_user"
        }

        if self.svc.upsert_capa(data):
            QMessageBox.information(self, "Thành công", "Đã lưu phiếu CAPA.")
            self.accept()
        else:
            QMessageBox.warning(self, "Lỗi", "Không thể lưu phiếu CAPA.")