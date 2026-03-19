# -*- coding: utf-8 -*-
"""
app/shared/widgets/importer.py
(Ported từ iqc_importer.py)
Tiện ích Import CSV/Excel (dùng pandas) vào QTableWidget.
"""
from __future__ import annotations
import csv
import os
from typing import List
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

# Thử import pandas
try:
    import pandas as pd
except ImportError:
    pd = None  # Sẽ báo lỗi nếu người dùng chọn file Excel


def import_to_table(file_path: str, table: QTableWidget, start_row: int = 0):
    """
    Nạp dữ liệu từ file CSV/Excel vào QTableWidget.
    Ghi đè hoặc nối tiếp (nếu start_row > 0).
    """
    ext = os.path.splitext(file_path)[1].lower()
    rows: List[List[str]] = []
    headers: List[str] = []

    if ext in [".csv", ".txt"]:
        try:
            # Dùng 'utf-8-sig' để xử lý BOM (Byte Order Mark)
            with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                all_rows = list(reader)
            if all_rows:
                headers = all_rows[0]
                rows = all_rows[1:]
        except Exception as e:
            raise RuntimeError(f"Lỗi đọc file CSV: {e}")

    elif ext in [".xlsx", ".xls"]:
        if pd is None:
            raise RuntimeError(
                "Thiếu thư viện 'pandas' và 'openpyxl' để đọc Excel.\nHãy cài đặt bằng: pip install pandas openpyxl")
        try:
            # header=0: đọc hàng đầu tiên làm header
            df = pd.read_excel(file_path, header=0)
            headers = list(df.columns)
            # Chuyển mọi thứ sang string, fill giá trị NaN (trống) bằng ""
            rows = df.fillna("").astype(str).values.tolist()
        except Exception as e:
            raise RuntimeError(f"Lỗi đọc file Excel: {e}")
    else:
        raise RuntimeError(f"Định dạng file không hỗ trợ: {ext}")

    if not rows:
        raise RuntimeError("File không có dữ liệu (chỉ có header hoặc rỗng).")

    # --- Đổ dữ liệu vào QTableWidget ---

    # (Tùy chọn: Cập nhật header của bảng nếu khớp số cột)
    if headers and table.columnCount() == len(headers):
        table.setHorizontalHeaderLabels(headers)

    # Đặt lại số hàng (nếu bắt đầu từ 0) hoặc đảm bảo đủ hàng
    if start_row == 0:
        table.setRowCount(len(rows))
    else:
        table.setRowCount(start_row + len(rows))

    for r_idx, row_data in enumerate(rows):
        r = start_row + r_idx  # Vị trí hàng trong bảng

        for c_idx, val in enumerate(row_data):
            if c_idx >= table.columnCount():
                break  # Dừng nếu dữ liệu file nhiều cột hơn bảng

            it = table.item(r, c_idx)
            if it is None:
                it = QTableWidgetItem()
                table.setItem(r, c_idx, it)

            # Xử lý giá trị 'nan' từ pandas
            str_val = "" if val is None or str(val).lower() == 'nan' else str(val)
            it.setText(str_val)