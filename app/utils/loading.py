# -*- coding: utf-8 -*-
"""
app/shared/loading.py (PySide6 Version)
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QMovie, QColor, QPalette

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Chặn click chuột
        self.setAttribute(Qt.WA_NoSystemBackground)

        # Tạo nền mờ đen
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Sửa Qt.AlignCenter -> Qt.AlignmentFlag.AlignCenter

        # Spinner text
        self.lbl_msg = QLabel("Đang xử lý dữ liệu...\nVui lòng đợi")
        self.lbl_msg.setStyleSheet("""
            color: white; 
            font-weight: bold; 
            font-size: 16px; 
            background-color: #333; 
            padding: 20px; 
            border-radius: 10px;
        """)
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_msg)

        self.hide()

    def show_loading(self):
        if self.parent():
            self.resize(self.parent().size())
        self.show()
        self.raise_()

    def hide_loading(self):
        self.hide()