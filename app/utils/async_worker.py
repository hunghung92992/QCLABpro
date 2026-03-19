# -*- coding: utf-8 -*-
"""
app/shared/async_worker.py (PySide6 Version)
"""

from PySide6.QtCore import QThread, Signal  # <--- Dùng Signal của PySide6
import traceback

class Worker(QThread):
    """
    Luồng xử lý chung (Generic Worker).
    """
    finished = Signal(object) # Trả về kết quả
    error = Signal(str)       # Trả về lỗi nếu có

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            # Chạy hàm nặng ở đây
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            traceback.print_exc()
            self.error.emit(str(e))