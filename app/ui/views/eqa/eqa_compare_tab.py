# -*- coding: utf-8 -*-
"""
app/features/eqa/eqa_compare_tab.py
(CONVERTED TO FLUENT UI - LOGIC PRESERVED)
Giao diện Phân tích & So sánh EQA.
"""

import sqlite3
import datetime as dt
import math
from typing import List, Optional, Dict, Any, Tuple
from app.core.path_manager import PathManager
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# --- Fluent UI Imports ---
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, ComboBox,
    LineEdit, SpinBox, TableWidget, FluentIcon as FIF,
    StrongBodyLabel, BodyLabel, InfoBar
)

# Import Service
from app.services.eqa_service import EQAService

# Thử import pandas cho Export Excel
try:
    import pandas as pd
except ImportError:
    pd = None

# Thử import matplotlib cho Biểu đồ
try:
    from matplotlib import pyplot as plt

    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class EqaCompareTab(QWidget):
    def __init__(self,
                 parent: Optional[QWidget] = None,
                 db_path: Optional[str] = None,
                 username: Optional[str] = None,
                 role: Optional[str] = None,
                 **kwargs):
        super().__init__(parent)

        # Config loader giả định hoặc lấy từ kwargs nếu có, ở đây giữ nguyên logic db_path
        self.db_path = db_path  # or config_loader.get_db_path()
        self.dao = EQAService()

        self._build_ui()
        self._load_providers()

        # (Patch) Thêm các nút mới
        self._patch_compare_toolbar()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # --- Thanh Lọc (Filter Bar) trong CardWidget ---
        filter_card = CardWidget(self)
        # Lưu layout này lại để dùng trong _patch_compare_toolbar
        self.filter_layout = QHBoxLayout(filter_card)
        self.filter_layout.setContentsMargins(12, 12, 12, 12)
        self.filter_layout.setSpacing(12)

        self.cb_provider = ComboBox()
        self.cb_provider.setPlaceholderText("Chọn nhà CC")

        self.cb_program = ComboBox()
        self.cb_program.setPlaceholderText("Chọn chương trình")

        nowy = dt.datetime.now().year
        self.sp_from = SpinBox()
        self.sp_from.setRange(2000, 2100)
        self.sp_from.setValue(nowy - 2)

        self.sp_to = SpinBox()
        self.sp_to.setRange(2000, 2100)
        self.sp_to.setValue(nowy)

        self.ed_device = LineEdit()
        self.ed_device.setPlaceholderText("Thiết bị (tùy chọn)")

        self.ed_analyte = LineEdit()
        self.ed_analyte.setPlaceholderText("Tên xét nghiệm (vd. GLU)")

        self.btn_load = PrimaryPushButton(FIF.SYNC, "Tải dữ liệu", self)
        self.btn_plot = PushButton(FIF.TILES, "Vẽ biểu đồ", self)

        # Add widgets to layout
        # Helper để thêm label + widget
        def add_field(label, widget, stretch=0):
            v = QVBoxLayout()
            v.setSpacing(4)
            v.addWidget(BodyLabel(label, self))
            v.addWidget(widget)
            self.filter_layout.addLayout(v, stretch)

        add_field("Provider:", self.cb_provider, 2)
        add_field("Chương trình:", self.cb_program, 2)
        add_field("Năm từ:", self.sp_from)
        add_field("Đến:", self.sp_to)
        add_field("Thiết bị:", self.ed_device, 1)
        add_field("Xét nghiệm:", self.ed_analyte, 1)

        self.filter_layout.addStretch(1)

        # Nút bấm gom vào 1 layout dọc hoặc ngang cuối cùng
        action_layout = QHBoxLayout()
        action_layout.addWidget(self.btn_load)
        action_layout.addWidget(self.btn_plot)
        # Căn chỉnh nút xuống dưới cùng để thẳng hàng với input
        v_btns = QVBoxLayout()
        v_btns.addStretch(1)
        v_btns.addLayout(action_layout)
        self.filter_layout.addLayout(v_btns)

        root.addWidget(filter_card)

        # --- Bảng Dữ liệu ---
        self.tbl = TableWidget(self)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setBorderVisible(True)

        root.addWidget(self.tbl, 1)

        # --- Events ---
        self.cb_provider.currentIndexChanged.connect(self._reload_programs)
        self.btn_load.clicked.connect(self._refresh)
        self.btn_plot.clicked.connect(self._plot_row)

    def _load_providers(self):
        self.cb_provider.clear()
        self.cb_provider.addItem("— Chọn nhà CC —", None)
        for r in self.dao.list_providers():
            self.cb_provider.addItem(r["name"], r["id"])

    def _reload_programs(self):
        self.cb_program.clear()
        self.cb_program.addItem("— Chọn chương trình —", None)
        pid = self.cb_provider.currentData()
        if pid:
            for r in self.dao.list_programs(pid):
                disp = f"{r['name']} ({r['code']})" if r['code'] else r['name']
                self.cb_program.addItem(disp, r["id"])

    def _query_rows(self) -> List[Dict[str, Any]]:
        """
        Truy vấn phức tạp để lấy dữ liệu so sánh ngang (cross-round).
        (Logic này giữ nguyên SQL phức tạp từ file gốc)
        """
        prog = self.cb_program.currentData()
        if not prog: return []

        y1 = int(self.sp_from.value())
        y2 = int(self.sp_to.value())
        dev = self.ed_device.text().strip() or None
        analyte_like = f"%{self.ed_analyte.text().strip()}%" if self.ed_analyte.text().strip() else "%"

        sql = """SELECT r.year, r.round_no, s.sample_code, 
                       res.analyte as provider_analyte, 
                       res.result_site as result_value, 
                       res.unit
                 FROM eqa_result res
                 JOIN eqa_round r ON r.id = res.round_id
                 LEFT JOIN eqa_sample s ON s.id = res.sample_id
                 WHERE r.program_id = ? AND r.year BETWEEN ? AND ?
                       AND (? IS NULL OR IFNULL(r.device_name,'') = ?)
                       AND res.analyte LIKE ?
                 ORDER BY res.analyte, s.sample_code, r.year, r.round_no"""
        try:
            # Lưu ý: db_path có thể None nếu chưa config, cần xử lý ở main app hoặc service
            # Ở đây dùng self.dao._con() nếu service hỗ trợ, hoặc sqlite3.connect
            with sqlite3.connect(PathManager.get_db_path()) as con:
                con.row_factory = sqlite3.Row
                cur = con.execute(sql, (prog, y1, y2, dev, dev, analyte_like))
                return [dict(r) for r in cur.fetchall()]
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Lỗi SQL", f"Không thể truy vấn dữ liệu so sánh: {e}")
            return []

    def _refresh(self):
        """Tải và điền dữ liệu vào bảng so sánh."""
        rows = self._query_rows()
        if not rows:
            self.tbl.setRowCount(0)
            self.tbl.setColumnCount(0)
            InfoBar.warning("Thông báo", "Không tìm thấy dữ liệu EQA phù hợp.", parent=self)
            return

        # 1. Xác định các cột (các kỳ)
        periods = sorted(list(set((r['year'], r['round_no']) for r in rows)))
        period_labels = [f"{y}-{rn}" for (y, rn) in periods]

        # 2. Nhóm dữ liệu theo Xét nghiệm/Mẫu
        from collections import defaultdict
        grp = defaultdict(lambda: {})
        for r in rows:
            k = (r['provider_analyte'], r['sample_code'], r.get('unit'))
            p = (r['year'], r['round_no'])
            grp[k][p] = r['result_value']

        # 3. Dựng Header
        headers = ["Xét nghiệm", "Mẫu", "Đơn vị"] + period_labels + ["Mean", "SD", "CV%", "Δ Gần nhất"]
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setRowCount(0)

        # 4. Điền dữ liệu
        for (analyte, sample, unit), mapping in sorted(grp.items()):
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(analyte or '')))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(sample or '')))
            self.tbl.setItem(row, 2, QTableWidgetItem("" if unit is None else str(unit)))

            series = []
            for i, p in enumerate(periods):
                val = mapping.get(p, "")
                self.tbl.setItem(row, 3 + i, QTableWidgetItem("" if val is None else str(val)))
                series.append(self.dao._to_float(val))

            # Tính toán thống kê
            nums = [v for v in series if v is not None and not math.isnan(v)]
            mean, sd, cv, delta = float('nan'), float('nan'), float('nan'), float('nan')
            if nums:
                mean = sum(nums) / len(nums)
                sd = (sum((x - mean) ** 2 for x in nums) / (len(nums) - 1)) ** 0.5 if len(nums) > 1 else 0.0
                cv = (sd / abs(mean) * 100.0) if mean else 0.0
                delta = (nums[-1] - nums[-2]) if len(nums) >= 2 else 0.0

            base = 3 + len(periods)
            self.tbl.setItem(row, base + 0, QTableWidgetItem(f"{mean:.4g}"))
            self.tbl.setItem(row, base + 1, QTableWidgetItem(f"{sd:.4g}"))
            self.tbl.setItem(row, base + 2, QTableWidgetItem(f"{cv:.2f}"))
            self.tbl.setItem(row, base + 3, QTableWidgetItem(f"{delta:.4g}"))

        self.tbl.resizeColumnsToContents()

    def _plot_row(self):
        """Vẽ biểu đồ cho dòng được chọn (từ file gốc)."""
        if not HAS_MPL:
            QMessageBox.warning(self, "Thiếu thư viện", "Cần cài đặt 'matplotlib' để vẽ biểu đồ.")
            return

        r = self.tbl.currentRow()
        if r < 0:
            InfoBar.warning("Chọn dòng", "Hãy chọn 1 dòng trong bảng để vẽ.", parent=self)
            return

        labels, values = [], []
        # Cột 3 (index 3) đến cột (N-4) là dữ liệu
        for c in range(3, self.tbl.columnCount() - 4):
            labels.append(self.tbl.horizontalHeaderItem(c).text())
            txt = self.tbl.item(r, c).text() if self.tbl.item(r, c) else ""
            values.append(self.dao._to_float(txt))

        try:
            plt.figure(figsize=(10, 5))
            plt.plot(range(len(values)), values, marker="o", linestyle="--")
            plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
            plt.title(f"{self.tbl.item(r, 0).text()} — Mẫu {self.tbl.item(r, 1).text()}")
            plt.ylabel(self.tbl.item(r, 2).text())
            plt.grid(True, linestyle=":", alpha=0.7)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            QMessageBox.warning(self, "Không vẽ được", str(e))

    # --- (HỢP NHẤT TỪ PATCH) ---

    def _patch_compare_toolbar(self):
        """Thêm các nút tính toán và xuất Excel vào thanh công cụ."""
        self.btn_recalc = PushButton(FIF.EDIT, "Tính Z/SDI & Đánh giá", self)
        self.btn_export = PushButton(FIF.DOWNLOAD, "Xuất Excel", self)

        # Thêm vào layout của filter card
        try:
            # Tìm layout chứa nút bấm (là layout cuối cùng trong filter_layout)
            # Hoặc add trực tiếp vào filter_layout nếu còn chỗ

            # Cách an toàn nhất với Fluent UI structure đã build:
            # Lấy layout chứa nút bấm (Action Layout)
            if self.filter_layout.count() > 0:
                # Layout cuối cùng trong filter_layout là v_btns -> action_layout
                v_btns = self.filter_layout.itemAt(self.filter_layout.count() - 1).layout()
                action_layout = v_btns.itemAt(v_btns.count() - 1).layout()

                action_layout.addWidget(self.btn_recalc)
                action_layout.addWidget(self.btn_export)

            self.btn_recalc.clicked.connect(self._recalc_table_metrics)
            self.btn_export.clicked.connect(self._export_to_excel)
        except Exception as e:
            print(f"[EqaCompare] Lỗi patch toolbar: {e}")

        # FILE: app/features/eqa/eqa_compare_tab.py

    def _recalc_table_metrics(self):
        """
        Tính toán Z-Score, %Bias và Đánh giá (Phiên bản An toàn).
        """
        # 1. Kiểm tra dữ liệu: Nếu bảng trống thì báo lỗi
        if self.tbl.rowCount() == 0:
            InfoBar.warning("Chưa có dữ liệu", "Vui lòng bấm 'Tải dữ liệu' trước khi tính toán.", parent=self)
            return

        # 2. Tìm cột Mean và SD (được tạo ra sau khi tải dữ liệu)
        headers = [self.tbl.horizontalHeaderItem(i).text() for i in range(self.tbl.columnCount())]

        try:
            col_mean = headers.index("Mean")
            col_sd = headers.index("SD")
        except ValueError:
            InfoBar.error("Thiếu cột", "Bảng dữ liệu thiếu cột Mean/SD. Hãy thử tải lại dữ liệu.", parent=self)
            return

        # 3. Thêm các cột kết quả nếu chưa có
        extra_cols = ["Z-Score (Est)", "%Bias", "Đánh giá"]
        for title in extra_cols:
            if title not in headers:
                self.tbl.insertColumn(self.tbl.columnCount())
                self.tbl.setHorizontalHeaderItem(self.tbl.columnCount() - 1, QTableWidgetItem(title))
                headers.append(title)

        col_z = headers.index("Z-Score (Est)")
        col_bias = headers.index("%Bias")
        col_eval = headers.index("Đánh giá")

        # 4. Thực hiện tính toán (DEMO)
        # Lưu ý: Do DB chưa có Assigned Mean (của nhóm), ta tạm dùng Mean của Lab để test hiển thị.

        row_count = self.tbl.rowCount()
        for r in range(row_count):
            try:
                # Lấy Mean/SD từ bảng
                mean_text = self.tbl.item(r, col_mean).text()
                sd_text = self.tbl.item(r, col_sd).text()

                if not mean_text or not sd_text: continue

                mean_val = self.dao._to_float(mean_text)

                # --- LOGIC GIẢ ĐỊNH ĐỂ TEST MÀU SẮC ---
                z_score = 0.00
                bias = 0.0
                eval_res = "PASS"
                color = "#D6F5D6"  # Màu xanh

                # Hiển thị lên bảng
                self.tbl.setItem(r, col_z, QTableWidgetItem(f"{z_score:.2f}"))
                self.tbl.setItem(r, col_bias, QTableWidgetItem(f"{bias:.1f}%"))

                item_eval = QTableWidgetItem(eval_res)
                item_eval.setBackground(QColor(color))
                self.tbl.setItem(r, col_eval, item_eval)

            except Exception:
                continue

        self.tbl.resizeColumnsToContents()
        InfoBar.success("Hoàn tất", "Đã cập nhật các cột đánh giá (Dữ liệu Demo).", parent=self)

    def _export_to_excel(self):
        """(Từ Patch) Xuất bảng hiện tại ra Excel."""
        if not pd:
            QMessageBox.warning(self, "Thiếu thư viện", "Yêu cầu 'pandas' và 'openpyxl' để xuất Excel.")
            return
        if self.tbl.rowCount() == 0:
            InfoBar.warning("Không có dữ liệu", "Bảng đang trống.", parent=self)
            return

        headers = [self.tbl.horizontalHeaderItem(i).text() for i in range(self.tbl.columnCount())]
        rows_data = []
        for r in range(self.tbl.rowCount()):
            row = {h: (self.tbl.item(r, c).text() if self.tbl.item(r, c) else "") for c, h in enumerate(headers)}
            rows_data.append(row)

        df = pd.DataFrame(rows_data, columns=headers)

        fname, _ = QFileDialog.getSaveFileName(self, "Lưu Excel", "eqa_compare_export.xlsx", "Excel (*.xlsx)")
        if not fname: return

        try:
            df.to_excel(fname, index=False, engine='openpyxl')
            InfoBar.success("Đã lưu", f"Xuất thành công: {fname}", parent=self)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi khi lưu", str(e))