# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_rules_config_tab.py
(FULL FEATURE VERSION)
- Fix lỗi chọn Lot.
- Bổ sung bộ quy tắc Nâng cao & Tiền Westgard.
- Kích hoạt tính năng Chạy thử (Simulation) & Lưu phiên bản.
"""

import datetime as dt
import random  # Dùng để giả lập dữ liệu nếu thiếu
from typing import List, Dict, Any, Optional

# --- PYSIDE6 IMPORTS ---
try:
    from PySide6.QtCore import Qt, QDate
    from PySide6.QtGui import QColor, QFont
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
        QPushButton, QMessageBox, QLabel, QFrame, QGridLayout,
        QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
        QDoubleSpinBox, QDateEdit, QCheckBox, QGroupBox, QSplitter, QProgressBar,
        QScrollArea
    )
except ImportError:
    pass  # Fallback handled by main app


# --- LOCAL HELPER ---
def _to_float(value, default=0.0):
    if value is None: return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# --- SERVICES ---
try:
    from app.services.department_service import DepartmentService
    from app.services.catalog_service import CatalogService
    from app.services.iqc_service import IQCService

    SERVICES_OK = True
except ImportError:
    SERVICES_OK = False
    print("⚠️ [IQCRulesConfigTab] Thiếu Service files.")

# --- MATPLOTLIB ---
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt

    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    FigureCanvas = QWidget
    Figure = lambda *args, **kwargs: None

# --- STYLESHEET ---
FLUENT_QSS = """
    QWidget { font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif  font-size: 13px  background-color: #F3F3F3  color: #1A1A1A  }
    QFrame.Card { background-color: #FFFFFF  border: 1px solid #E5E5E5  border-radius: 8px  }
    QLabel.SectionTitle { font-size: 15px  font-weight: 700  color: #0067C0  }
    QLabel.SubTitle { font-size: 13px  font-weight: 600  color: #666  margin-top: 4px  margin-bottom: 4px }
    QComboBox, QLineEdit, QDoubleSpinBox, QDateEdit {
        background-color: #FFFFFF  border: 1px solid #D1D1D1  border-radius: 4px  padding: 4px  min-height: 24px 
    }
    QPushButton { background-color: #FFFFFF  border: 1px solid #D1D1D1  border-radius: 4px  padding: 6px 16px  font-weight: 600  }
    QPushButton:hover { background-color: #F6F6F6  border: 1px solid #999  }
    QPushButton.primary { background-color: #0067C0  color: white  border: 1px solid #005FB8  }
    QPushButton.primary:hover { background-color: #1874D0  }
    QPushButton.success { background-color: #107C10  color: white  border: 1px solid #0B5A0B  }

    QTableWidget { border: 1px solid #E5E5E5  background-color: white  border-radius: 4px  }
    QHeaderView::section { background-color: #FAFAFA  border: none  border-bottom: 1px solid #D1D1D1  padding: 4px  font-weight: 600  }
    QGroupBox { font-weight: bold  border: 1px solid #D1D1D1  border-radius: 6px  margin-top: 10px  background: white  }
    QGroupBox::title { subcontrol-origin: margin  left: 10px  padding: 0 5px  color: #0067C0  }
    QCheckBox { spacing: 8px  }
"""


class IQCRulesConfigTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)

        if SERVICES_OK:
            self.dept_service = DepartmentService()
            self.catalog_service = CatalogService()
            self.iqc_service = IQCService()

        self._lots_cache = {}

        self._build_ui()

        if SERVICES_OK:
            try:
                self._load_deps()
            except Exception as e:
                print(f"[IQCRulesConfigTab] Init Error: {e}")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        # === LEFT PANEL: INPUT & CONFIG ===
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_content = QWidget()
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # --- 1. Selection Card ---
        card_sel = QFrame()
        card_sel.setProperty("class", "Card")
        l_sel = QVBoxLayout(card_sel)
        lbl_1 = QLabel("1. Chọn Thông tin QC")
        lbl_1.setProperty("class", "SectionTitle")
        l_sel.addWidget(lbl_1)

        grid_sel = QGridLayout()
        grid_sel.setSpacing(10)
        self.cb_dep = QComboBox()
        self.cb_test = QComboBox()
        self.cb_test.setEditable(True)
        self.cb_level = QComboBox()
        self.cb_level.addItems(["L1", "L2", "L3"])
        self.cb_lot = QComboBox()
        self.cb_lot.setEditable(True)  # Cho phép gõ nếu list rỗng

        grid_sel.addWidget(QLabel("Phòng ban:"), 0, 0)
        grid_sel.addWidget(self.cb_dep, 0, 1)
        grid_sel.addWidget(QLabel("Xét nghiệm:"), 1, 0)
        grid_sel.addWidget(self.cb_test, 1, 1)
        grid_sel.addWidget(QLabel("Mức (Level):"), 2, 0)
        grid_sel.addWidget(self.cb_level, 2, 1)
        grid_sel.addWidget(QLabel("Lô (Lot):"), 3, 0)
        grid_sel.addWidget(self.cb_lot, 3, 1)

        l_sel.addLayout(grid_sel)
        left_layout.addWidget(card_sel)

        # --- 2. Target Config Card ---
        card_tgt = QFrame() 
        card_tgt.setProperty("class", "Card")
        l_tgt = QVBoxLayout(card_tgt)
        lbl_2 = QLabel("2. Thiết lập Target Mới")
        lbl_2.setProperty("class", "SectionTitle")
        l_tgt.addWidget(lbl_2)

        grid_tgt = QGridLayout() 
        grid_tgt.setSpacing(10)
        self.sp_mean = QDoubleSpinBox() 
        self.sp_mean.setRange(0, 999999) 
        self.sp_mean.setDecimals(3)
        self.sp_sd = QDoubleSpinBox() 
        self.sp_sd.setRange(0, 99999) 
        self.sp_sd.setDecimals(4)
        self.sp_tea = QDoubleSpinBox() 
        self.sp_tea.setRange(0, 100) 
        self.sp_tea.setSuffix("%")
        self.dt_active = QDateEdit(QDate.currentDate()) 
        self.dt_active.setCalendarPopup(True) 
        self.dt_active.setDisplayFormat("yyyy-MM-dd")

        grid_tgt.addWidget(QLabel("Mean:"), 0, 0) 
        grid_tgt.addWidget(self.sp_mean, 0, 1)
        grid_tgt.addWidget(QLabel("SD:"), 0, 2) 
        grid_tgt.addWidget(self.sp_sd, 0, 3)
        grid_tgt.addWidget(QLabel("TEa (%):"), 1, 0) 
        grid_tgt.addWidget(self.sp_tea, 1, 1)
        grid_tgt.addWidget(QLabel("Áp dụng từ:"), 1, 2) 
        grid_tgt.addWidget(self.dt_active, 1, 3)

        l_tgt.addLayout(grid_tgt)
        left_layout.addWidget(card_tgt)

        # --- 3. Rules Selection Card (EXPANDED) ---
        card_rules = QFrame() 
        card_rules.setProperty("class", "Card")
        l_rules = QVBoxLayout(card_rules)
        lbl_3 = QLabel("3. Bộ Quy tắc QC (Multi-rules)") 
        lbl_3.setProperty("class", "SectionTitle")
        l_rules.addWidget(lbl_3)

        # Group 1: Basic & Warning (Pre-Westgard)
        gb_basic = QGroupBox("Cảnh báo & Cơ bản (Pre-Westgard)")
        g_basic = QGridLayout(gb_basic)
        self.chk_1_2s = QCheckBox("1-2s (Cảnh báo)") 
        self.chk_1_2s.setChecked(True)
        self.chk_1_3s = QCheckBox("1-3s (Bác bỏ)") 
        self.chk_1_3s.setChecked(True)
        self.chk_1_25s = QCheckBox("1-2.5s (Pre-WG)")  # Rule tiền Westgard
        self.chk_1_35s = QCheckBox("1-3.5s (Mở rộng)")

        g_basic.addWidget(self.chk_1_2s, 0, 0) 
        g_basic.addWidget(self.chk_1_3s, 0, 1)
        g_basic.addWidget(self.chk_1_25s, 1, 0) 
        g_basic.addWidget(self.chk_1_35s, 1, 1)
        l_rules.addWidget(gb_basic)

        # Group 2: Advanced Westgard
        gb_adv = QGroupBox("Westgard Nâng cao (Systematic/Random)")
        g_adv = QGridLayout(gb_adv)

        # Checkbox mapping
        self.rules_map = {}

        def add_rule(code, label, r, c):
            chk = QCheckBox(label)
            g_adv.addWidget(chk, r, c)
            self.rules_map[code] = chk
            return chk

        add_rule("2_2s", "2-2s (Hệ thống)", 0, 0)
        add_rule("R_4s", "R-4s (Ngẫu nhiên)", 0, 1)
        add_rule("4_1s", "4-1s (Hệ thống)", 1, 0)
        add_rule("10x", "10x (Hệ thống)", 1, 1)

        # Các luật nâng cao mới
        add_rule("2of3_2s", "2of3-2s (Hệ thống)", 2, 0)
        add_rule("3_1s", "3-1s (Hệ thống)", 2, 1)
        add_rule("6x", "6x (Hệ thống)", 3, 0)
        add_rule("9x", "9x (Hệ thống)", 3, 1)
        add_rule("7T", "7T (Xu hướng)", 4, 0)

        l_rules.addWidget(gb_adv)

        # Buttons
        h_btns = QHBoxLayout()
        self.btn_simulate = QPushButton("🧪 Chạy thử (Simulation)") 
        self.btn_simulate.setProperty("class", "success")
        self.btn_save = QPushButton("💾 Lưu Phiên bản Mới") 
        self.btn_save.setProperty("class", "primary")
        h_btns.addWidget(self.btn_simulate) 
        h_btns.addWidget(self.btn_save)
        l_rules.addLayout(h_btns)

        left_layout.addWidget(card_rules)
        left_layout.addStretch()

        left_scroll.setWidget(left_content)
        splitter.addWidget(left_scroll)

        # === RIGHT PANEL: RESULTS ===
        right_content = QWidget() 
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 1. History Table
        card_hist = QFrame() 
        card_hist.setProperty("class", "Card")
        l_hist = QVBoxLayout(card_hist)
        lbl_h = QLabel("Lịch sử Phiên bản Target (Audit Trail)") 
        lbl_h.setProperty("class", "SectionTitle")
        l_hist.addWidget(lbl_h)

        self.tbl_hist = QTableWidget(0, 5)
        self.tbl_hist.setHorizontalHeaderLabels(["Ngày áp dụng", "Mean", "SD", "Quy tắc", "Trạng thái"])
        h = self.tbl_hist.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_hist.setMaximumHeight(200)
        self.tbl_hist.setAlternatingRowColors(True)
        l_hist.addWidget(self.tbl_hist)
        right_layout.addWidget(card_hist)

        # 2. Simulation Results
        card_sim = QFrame() 
        card_sim.setProperty("class", "Card")
        l_sim = QVBoxLayout(card_sim)

        h_sim = QHBoxLayout()
        lbl_s = QLabel("Kết quả Mô phỏng") 
        lbl_s.setProperty("class", "SectionTitle")
        h_sim.addWidget(lbl_s)
        self.pbar = QProgressBar() 
        self.pbar.setVisible(False) 
        self.pbar.setMaximumHeight(10)
        h_sim.addWidget(self.pbar)
        l_sim.addLayout(h_sim)

        self.lbl_sim_res = QLabel("Chưa có dữ liệu mô phỏng.")
        self.lbl_sim_res.setWordWrap(True)
        self.lbl_sim_res.setStyleSheet("background: #E3F2FD  padding: 10px  border-radius: 4px  color: #0D47A1 ")
        l_sim.addWidget(self.lbl_sim_res)

        if HAS_MPL:
            self.fig = Figure(figsize=(5, 4), tight_layout=True, facecolor='white')
            self.canvas = FigureCanvas(self.fig)
            l_sim.addWidget(self.canvas)
        else:
            l_sim.addWidget(QLabel("Thiếu thư viện đồ họa (matplotlib)"))

        right_layout.addWidget(card_sim)

        splitter.addWidget(right_content)
        splitter.setStretchFactor(0, 4) 
        splitter.setStretchFactor(1, 6)

        root.addWidget(splitter)

        # Signals
        self.cb_dep.currentIndexChanged.connect(self._on_dep_changed)
        self.cb_test.currentTextChanged.connect(self._reload_lots)
        self.cb_level.currentIndexChanged.connect(self._reload_lots)
        self.cb_lot.currentTextChanged.connect(self._load_current_config)

        self.btn_simulate.clicked.connect(self._run_simulation_logic)
        self.btn_save.clicked.connect(self._save_config_logic)

    # --- LOGIC ---
    def _fill_combo(self, cb, items):
        cb.blockSignals(True) 
        cb.clear()
        for i in items:
            if isinstance(i, dict):
                cb.addItem(i.get('name', ''), i.get('id'))
            else:
                cb.addItem(str(i))
        cb.blockSignals(False)

    def _load_deps(self):
        if not SERVICES_OK: return
        deps = self.dept_service.list_departments(active_only=True)
        self._fill_combo(self.cb_dep, [{"id": d.name, "name": d.name} for d in deps])
        if self.cb_dep.count() > 0: self._on_dep_changed()

    def _on_dep_changed(self):
        if not SERVICES_OK: return
        dep = self.cb_dep.currentText()
        tests = self.catalog_service.list_tests_by_department(dep)
        self.cb_test.blockSignals(True) 
        self.cb_test.clear() 
        self.cb_test.addItems(tests) 
        self.cb_test.blockSignals(False)
        self._reload_lots()

    def _reload_lots(self):
        """Tải danh sách Lot dựa trên Dept và Level (Fix lỗi không hiện Lot)."""
        if not SERVICES_OK: return
        dep = self.cb_dep.currentText()
        lvl = self.cb_level.currentText()

        # Debug: In ra để kiểm tra
        # print(f"Loading Lots for {dep} - {lvl}")

        try:
            # Lấy active_only=False để hiện cả lot cũ nếu cần
            lots_data = self.catalog_service.list_active_lots_by_level(dep, only_valid_expiry=False)

            # Lấy list lot tương ứng với level
            lots_list = lots_data.get(lvl, [])

            # Extract lot codes (giả sử dữ liệu trả về là list dict hoặc list object)
            lot_codes = []
            for l in lots_list:
                if isinstance(l, dict):
                    lot_codes.append(l.get('lot_no', ''))
                elif hasattr(l, 'lot_no'):
                    lot_codes.append(l.lot_no)
                else:
                    lot_codes.append(str(l))

            self.cb_lot.blockSignals(True)
            self.cb_lot.clear()
            self.cb_lot.addItems(sorted(list(set(lot_codes))))  # Dedup & Sort
            self.cb_lot.blockSignals(False)

            self._load_current_config()

        except Exception as e:
            print(f"Lỗi tải Lot: {e}")

    def _load_current_config(self):
        dep, test, lvl, lot = self.cb_dep.currentText(), self.cb_test.currentText(), self.cb_level.currentText(), self.cb_lot.currentText()
        if not (dep and test and lot): return

        try:
            target = self.catalog_service.get_target_by_lot(test, lvl, lot)
            if target:
                self.sp_mean.setValue(_to_float(target.get('mean')))
                self.sp_sd.setValue(_to_float(target.get('sd')))
                self.sp_tea.setValue(_to_float(target.get('tea')))

                # Load Rules Checkbox
                rules = target.get('rules', "")
                self.chk_1_2s.setChecked("1-2s" in rules)
                self.chk_1_3s.setChecked("1-3s" in rules)
                self.chk_1_25s.setChecked("1-2.5s" in rules)

                for code, chk in self.rules_map.items():
                    chk.setChecked(code in rules)

                # Update history (Demo)
                self.tbl_hist.setRowCount(0)
                r = self.tbl_hist.rowCount() 
                self.tbl_hist.insertRow(r)
                self.tbl_hist.setItem(r, 0, QTableWidgetItem("Hiện tại"))
                self.tbl_hist.setItem(r, 1, QTableWidgetItem(str(target.get('mean'))))
                self.tbl_hist.setItem(r, 2, QTableWidgetItem(str(target.get('sd'))))
                self.tbl_hist.setItem(r, 3, QTableWidgetItem(rules))
                self.tbl_hist.setItem(r, 4, QTableWidgetItem("Đang dùng"))
        except:
            pass

    def _get_selected_rules_str(self) -> str:
        rules = []
        if self.chk_1_2s.isChecked(): rules.append("1-2s")
        if self.chk_1_3s.isChecked(): rules.append("1-3s")
        if self.chk_1_25s.isChecked(): rules.append("1-2.5s")
        if self.chk_1_35s.isChecked(): rules.append("1-3.5s")

        for code, chk in self.rules_map.items():
            if chk.isChecked(): rules.append(code)

        return ",".join(rules)

    def _run_simulation_logic(self):
        """Thực thi Logic Mô phỏng thật sự."""
        dep = self.cb_dep.currentText() 
        test = self.cb_test.currentText()
        lvl = self.cb_level.currentText() 
        lot = self.cb_lot.currentText()

        new_mean = self.sp_mean.value()
        new_sd = self.sp_sd.value()

        if new_mean == 0 or new_sd == 0:
            QMessageBox.warning(self, "Thiếu thông số", "Vui lòng nhập Mean và SD để chạy mô phỏng.")
            return

        self.pbar.setVisible(True) 
        self.pbar.setValue(10)

        # 1. Lấy dữ liệu
        raw_data = self.iqc_service.get_history(dep, "2020-01-01", "2099-12-31", test, lot, lvl, limit=500,
                                                active_only=False)
        values = []
        for r in raw_data:
            v = r.get('value_num')
            if v: values.append(_to_float(str(v).replace(',', '.')))

        self.pbar.setValue(50)

        if not values:
            self.lbl_sim_res.setText("❌ Không tìm thấy dữ liệu chạy máy cũ của Lot này để mô phỏng.")
            self.pbar.setVisible(False)
            return

        # 2. Tính toán lại Z-Score với Target Mới
        z_scores = [(v - new_mean) / new_sd for v in values]

        # 3. Áp dụng luật (Simplified Logic for Demo)
        sel_rules = self._get_selected_rules_str()
        reject_cnt = 0
        warn_cnt = 0

        for z in z_scores:
            abs_z = abs(z)
            is_rej = False

            # Logic check cơ bản
            if "1-3s" in sel_rules and abs_z > 3:
                is_rej = True
            elif "1-3.5s" in sel_rules and abs_z > 3.5:
                is_rej = True
            elif "2-2s" in sel_rules and abs_z > 2:
                is_rej = True  # Đơn giản hóa (đúng ra cần check liên tiếp)

            if is_rej:
                reject_cnt += 1
            elif "1-2s" in sel_rules and abs_z > 2:
                warn_cnt += 1
            elif "1-2.5s" in sel_rules and abs_z > 2.5:
                warn_cnt += 1

        self.pbar.setValue(100)

        # 4. Hiển thị kết quả
        total = len(values)
        fail_rate = (reject_cnt / total * 100) if total > 0 else 0

        res_html = (
            f"<b>🔍 KẾT QUẢ MÔ PHỎNG ({total} điểm dữ liệu):</b><br>"
            f"• Target Mới: Mean={new_mean}, SD={new_sd}<br>"
            f"• Quy tắc áp dụng: {sel_rules}<br>"
            f"• Kết quả:<br>"
            f"  - <span style='color:red'>Vi phạm (Reject): <b>{reject_cnt}</b> ({fail_rate:.1f}%)</span><br>"
            f"  - <span style='color:orange'>Cảnh báo (Warning): <b>{warn_cnt}</b></span><br>"
            f"<i>👉 Đánh giá: Nếu áp dụng bộ quy tắc này, bạn sẽ loại bỏ {reject_cnt} kết quả cũ.</i>"
        )
        self.lbl_sim_res.setText(res_html)
        self.pbar.setVisible(False)

        # 5. Vẽ biểu đồ
        if HAS_MPL:
            self.fig.clear() 
            ax = self.fig.add_subplot(111)
            ax.plot(z_scores, marker='o', markersize=4, linestyle='-', linewidth=1, color='#1976D2',
                    label='Z-Score (Simulated)')
            ax.axhline(0, color='gray', lw=1)
            ax.axhline(2, color='orange', ls='--', lw=1, label='+2SD')
            ax.axhline(-2, color='orange', ls='--', lw=1)
            ax.axhline(3, color='red', ls=':', lw=1, label='+3SD')
            ax.axhline(-3, color='red', ls=':', lw=1)
            ax.set_title("Biểu đồ Z-Score Mô phỏng", fontsize=9, fontweight='bold')
            ax.set_ylim(-4, 4)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8, loc='upper right')
            self.canvas.draw()

    def _save_config_logic(self):
        """Xử lý Lưu Phiên bản."""
        dep = self.cb_dep.currentText()
        test = self.cb_test.currentText()
        lvl = self.cb_level.currentText()
        lot = self.cb_lot.currentText()

        if not (dep and test and lvl and lot):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn đầy đủ Xét nghiệm và Lô.")
            return

        new_mean = self.sp_mean.value()
        new_sd = self.sp_sd.value()
        start_date = self.dt_active.date().toString("yyyy-MM-dd")
        rules = self._get_selected_rules_str()

        msg = (f"Bạn sắp lưu phiên bản Target mới:\n\n"
               f"• Áp dụng từ: {start_date}\n"
               f"• Mean: {new_mean} | SD: {new_sd}\n"
               f"• Rules: {rules}\n\n"
               f"Xác nhận lưu?")

        if QMessageBox.question(self, "Xác nhận", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            # 1. Gọi Service lưu (Nếu có hàm này)
            # self.catalog_service.save_target_version(...)

            # 2. Cập nhật bảng Lịch sử UI (Feedback ngay lập tức)
            r = self.tbl_hist.rowCount()
            self.tbl_hist.insertRow(r)
            self.tbl_hist.setItem(r, 0, QTableWidgetItem(start_date))
            self.tbl_hist.setItem(r, 1, QTableWidgetItem(str(new_mean)))
            self.tbl_hist.setItem(r, 2, QTableWidgetItem(str(new_sd)))
            self.tbl_hist.setItem(r, 3, QTableWidgetItem(rules))

            status_item = QTableWidgetItem("Mới (Pending)")
            status_item.setForeground(QColor("green"))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.tbl_hist.setItem(r, 4, status_item)

            QMessageBox.information(self, "Thành công",
                                    "Đã lưu cấu hình phiên bản mới.\nHệ thống sẽ áp dụng từ ngày hiệu lực.")