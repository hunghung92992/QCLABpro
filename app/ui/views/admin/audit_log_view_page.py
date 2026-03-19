# -*- coding: utf-8 -*-
import json
import traceback
import csv
import os
from PySide6.QtCore import Qt, QDate, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QTableWidgetItem, QFrame, QFileDialog,
    QAbstractItemView
)

# Nạp resource để hiển thị các icon FIF.LEFT_ARROW, FIF.RIGHT_ARROW, v.v.
try:
    import qfluentwidgets.resources_rc
except ImportError:
    pass

from qfluentwidgets import (
    TableWidget, PrimaryPushButton, PushButton,
    LineEdit, ComboBox, CalendarPicker,
    FluentIcon as FIF, InfoBar, InfoBarPosition,
    CardWidget, StrongBodyLabel, BodyLabel,
    InfoBadge, MessageBoxBase, SubtitleLabel, TextEdit,
    setTheme, Theme
)

# Import Service an toàn
try:
    from app.services.audit_service import AuditService
except ImportError:
    AuditService = None

try:
    from app.services.auth_service import AuthService
except ImportError:
    AuthService = None


# ============================================================================
# --- DIALOG XEM CHI TIẾT LOG ---
# ============================================================================
class LogDetailDialog(MessageBoxBase):
    def __init__(self, log_data, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Chi tiết Nhật ký", self)
        self.viewLayout.addWidget(self.titleLabel)

        # Xử lý thời gian hiển thị
        ts = str(log_data.get('ts_utc', '')).replace('T', ' ')[:19]
        # Ánh xạ actor từ 'actor' hoặc 'user_id' để tránh lỗi missing column
        actor = str(log_data.get('actor') or log_data.get('user_id') or 'N/A')
        action = str(log_data.get('action') or log_data.get('action_type') or 'N/A')
        target = str(log_data.get('target', 'Hệ thống'))

        info_card = QFrame(self)
        info_card.setObjectName("infoCard")
        info_card.setStyleSheet(
            "#infoCard { background: rgba(128, 128, 128, 0.08); border-radius: 8px; border: 1px solid rgba(0,0,0,0.05); }")
        info_layout = QVBoxLayout(info_card)

        info_text = (f"🕒 <b>Thời gian:</b> {ts}<br>"
                     f"👤 <b>Người thực hiện:</b> {actor}<br>"
                     f"⚡ <b>Hành động:</b> {action}<br>"
                     f"🎯 <b>Đối tượng:</b> {target}")

        self.lbl_info = BodyLabel(info_text, self)
        self.lbl_info.setWordWrap(True)
        info_layout.addWidget(self.lbl_info)
        self.viewLayout.addWidget(info_card)
        self.viewLayout.addSpacing(15)

        self.lbl_json = StrongBodyLabel("Dữ liệu chi tiết:", self)
        self.viewLayout.addWidget(self.lbl_json)

        self.txt_json = TextEdit(self)
        self.txt_json.setReadOnly(True)
        self.txt_json.setMinimumHeight(280)
        self.txt_json.setMinimumWidth(580)

        try:
            # Ưu tiên lấy dữ liệu từ old_value/new_value (chuẩn SQLAlchemy)
            before = log_data.get('old_value') or log_data.get('before_json')
            after = log_data.get('new_value') or log_data.get('after_json')
            details = log_data.get('details')

            display_data = {
                "Hành động": action,
                "Chi tiết": details if details else "Không có mô tả",
                "Dữ liệu trước": json.loads(before) if isinstance(before, str) and before.startswith('{') else before,
                "Dữ liệu sau": json.loads(after) if isinstance(after, str) and after.startswith('{') else after,
            }
            formatted_json = json.dumps(display_data, indent=4, ensure_ascii=False)
            self.txt_json.setText(formatted_json)
        except Exception:
            self.txt_json.setText(f"Dữ liệu thô:\n{str(log_data)}")

        self.viewLayout.addWidget(self.txt_json)
        self.yesButton.setText("Đóng")
        self.cancelButton.hide()
        self.widget.setMinimumWidth(620)


# ============================================================================
# --- TRANG CHÍNH: AUDIT LOG ---
# ============================================================================
class AuditLogViewPage(QWidget):
    def __init__(self, parent=None, username="", role="", **kwargs):
        super().__init__(parent)
        self.setObjectName("AuditLogViewPage")

        # Khởi tạo Service
        self.audit_service = AuditService() if AuditService else None
        self.auth_service = AuthService() if AuthService else None

        self.current_user = username
        self.user_role = role

        # Cấu hình phân trang
        self.page_size = 30
        self.current_page = 1
        self.total_pages = 1
        self.total_rows = 0
        self.full_data_cache = []
        self.current_filtered_data = []

        self._init_ui()
        self._load_combobox_data()
        self._refresh_data()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(15)

        # --- 1. Toolbar lọc ---
        filter_card = CardWidget(self)
        filter_layout = QHBoxLayout(filter_card)

        self.txt_search = LineEdit(self)
        self.txt_search.setPlaceholderText("Tìm hành động...")
        self.txt_search.setFixedWidth(200)
        self.txt_search.setClearButtonEnabled(True)

        self.cb_user = ComboBox(self)
        self.cb_user.setPlaceholderText("Người dùng")
        self.cb_user.setFixedWidth(150)

        self.date_picker = CalendarPicker(self)
        self.date_picker.setFixedWidth(160)

        self.btn_search = PrimaryPushButton(FIF.SEARCH, "Lọc", self)
        self.btn_search.clicked.connect(self._apply_filter)

        self.btn_reset = PushButton(FIF.SYNC, "Làm mới", self)
        self.btn_reset.clicked.connect(self._reset_filters)

        self.btn_export = PushButton(FIF.DOWNLOAD, "Xuất CSV", self)
        self.btn_export.clicked.connect(self._export_data)

        filter_layout.addWidget(self.txt_search)
        filter_layout.addWidget(self.cb_user)
        filter_layout.addWidget(self.date_picker)
        filter_layout.addWidget(self.btn_search)
        filter_layout.addWidget(self.btn_reset)
        filter_layout.addStretch(1)
        filter_layout.addWidget(self.btn_export)

        self.main_layout.addWidget(filter_card)

        # --- 2. Bảng dữ liệu ---
        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Thời gian", "Tài khoản", "Hành động", "Đối tượng", "Chi tiết"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 130)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self._show_detail)

        self.main_layout.addWidget(self.table)

        # --- 3. Điều hướng phân trang ---
        pagination_layout = QHBoxLayout()
        self.btn_prev = PushButton(FIF.LEFT_ARROW, "Trước", self)
        self.btn_next = PushButton(FIF.CHEVRON_RIGHT, "Sau", self)
        self.lbl_page = BodyLabel("Trang 1 / 1", self)
        self.lbl_total = BodyLabel("(Tổng: 0 bản ghi)", self)

        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_next.clicked.connect(self._next_page)

        pagination_layout.addStretch(1)
        pagination_layout.addWidget(self.lbl_total)
        pagination_layout.addSpacing(20)
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.lbl_page)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch(1)

        self.main_layout.addLayout(pagination_layout)

    def _load_combobox_data(self):
        if not self.auth_service: return
        self.cb_user.clear()
        self.cb_user.addItem("Tất cả người dùng", None)
        try:
            users = self.auth_service.list_users()
            if users:
                for u in users:
                    name = u.get('username')
                    self.cb_user.addItem(name, name)
        except:
            pass

    def _refresh_data(self):
        if not self.audit_service: return
        try:
            # Lấy log từ service. Hàm get_recent_logs nên được sửa để trả về list dict chuẩn
            self.full_data_cache = self.audit_service.get_recent_logs(limit=1000) or []
            self._apply_filter()
        except Exception as e:
            print(f"Audit Refresh Error: {e}")

    def _apply_filter(self):
        search_text = self.txt_search.text().lower().strip()
        selected_user = self.cb_user.currentData()

        q_date = self.date_picker.getDate()
        selected_date = q_date.toString("yyyy-MM-dd") if q_date and q_date.isValid() else None

        filtered = []
        for log in self.full_data_cache:
            # Phải hỗ trợ cả 'actor' và 'user_id'
            actor = str(log.get('actor') or log.get('user_id') or '')
            action = str(log.get('action') or log.get('action_type') or '')

            if selected_user and actor != selected_user:
                continue
            if selected_date and not str(log.get('ts_utc', '')).startswith(selected_date):
                continue
            if search_text:
                content = f"{action} {log.get('target', '')} {log.get('details', '')}".lower()
                if search_text not in content:
                    continue
            filtered.append(log)

        self.current_filtered_data = filtered
        self.total_rows = len(filtered)
        self.total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
        self.current_page = 1
        self._update_table_view()

    def _update_table_view(self):
        self.table.setRowCount(0)
        if not self.current_filtered_data:
            self._update_pagination_ui()
            return

        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        page_data = self.current_filtered_data[start:end]

        for i, log in enumerate(page_data):
            self.table.insertRow(i)
            ts = str(log.get('ts_utc', '')).replace('T', ' ')[:19]
            actor = str(log.get('actor') or log.get('user_id') or 'system')
            action = str(log.get('action') or log.get('action_type') or 'LOG')

            item_id = QTableWidgetItem(str(log.get('id')))
            item_id.setTextAlignment(Qt.AlignCenter)
            item_id.setData(Qt.UserRole, log)

            self.table.setItem(i, 0, item_id)
            self.table.setItem(i, 1, QTableWidgetItem(ts))
            self.table.setItem(i, 2, QTableWidgetItem(actor))

            self._set_action_badge(i, 3, action)
            self.table.setItem(i, 4, QTableWidgetItem(str(log.get('target') or 'System')))

            # Hiển thị chi tiết tóm tắt
            detail_txt = log.get('details') or log.get('note') or ""
            self.table.setItem(i, 5, QTableWidgetItem(str(detail_txt)))

        self._update_pagination_ui()

    def _update_pagination_ui(self):
        self.lbl_page.setText(f"Trang {self.current_page} / {self.total_pages}")
        self.lbl_total.setText(f"(Tổng: {self.total_rows} bản ghi)")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < self.total_pages)

    def _set_action_badge(self, row, col, action_text):
        action_up = action_text.upper()
        color = "#0078D4"  # Blue

        if any(x in action_up for x in ["DELETE", "REMOVE", "XÓA", "DROP"]):
            color = "#C42B1C"  # Red
        elif any(x in action_up for x in ["CREATE", "ADD", "INSERT", "TẠO"]):
            color = "#107C10"  # Green
        elif any(x in action_up for x in ["UPDATE", "EDIT", "SỬA", "CHANGE"]):
            color = "#9D5D00"  # Orange

        badge_container = QWidget()
        badge_layout = QHBoxLayout(badge_container)
        badge_layout.setContentsMargins(0, 4, 0, 4)
        badge_layout.setAlignment(Qt.AlignCenter)

        badge = InfoBadge.custom(action_up, color, "white")
        badge.setFixedSize(110, 24)
        badge_layout.addWidget(badge)
        self.table.setCellWidget(row, col, badge_container)

    def _show_detail(self):
        row = self.table.currentRow()
        if row < 0: return
        item = self.table.item(row, 0)
        if item:
            log_data = item.data(Qt.UserRole)
            dlg = LogDetailDialog(log_data, self)
            dlg.exec()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._update_table_view()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._update_table_view()

    def _reset_filters(self):
        self.txt_search.clear()
        self.cb_user.setCurrentIndex(0)
        self.date_picker.setDate(QDate())
        self._refresh_data()
        InfoBar.success("Thành công", "Đã cập nhật nhật ký mới nhất.", parent=self)

    def _export_data(self):
        if not self.current_filtered_data:
            InfoBar.warning("Chú ý", "Không có dữ liệu để xuất.", parent=self)
            return

        path, _ = QFileDialog.getSaveFileName(self, "Xuất CSV", "Nhat_ky_QC.csv", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Thời gian", "Người dùng", "Hành động", "Đối tượng", "Chi tiết"])
                    for log in self.current_filtered_data:
                        writer.writerow([
                            log.get('id'),
                            log.get('ts_utc'),
                            log.get('actor') or log.get('user_id'),
                            log.get('action') or log.get('action_type'),
                            log.get('target'),
                            log.get('details') or log.get('note')
                        ])
                InfoBar.success("Thành công", f"Đã lưu tại: {path}", parent=self)
            except Exception as e:
                InfoBar.error("Lỗi", str(e), parent=self)