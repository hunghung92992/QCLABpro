# -*- coding: utf-8 -*-
"""
app/features/iqc/iqc_system_ops_tab.py
(FIXED COLUMN NAME MISMATCH)
- Sửa lỗi 'no such column: timestamp'.
- Đồng bộ tên cột thành 'ts_utc' để khớp với core_models.py.
"""
from __future__ import annotations
import os
import shutil
import datetime as dt
import time
from typing import Optional
from app.core.path_manager import PathManager
# --- PYSIDE6 IMPORTS ---
from PySide6.QtCore import Qt, QDate, QTime, QThread, Signal, QSettings
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QFileDialog, QDateEdit, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QTimeEdit,
    QTabWidget
)

# --- APP IMPORTS ---
try:
    from app.core.config import cfg
    from sqlalchemy import text
    # Import DB_PATH từ database_orm
    from app.core.database_orm import engine, DB_PATH

    DB_MODULE_OK = True
except ImportError:
    DB_MODULE_OK = False
    DB_PATH = PathManager.get_db_path()
    print("⚠️ Thiếu module database. Chạy chế độ UI Demo.")

# Pandas
try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# --- CONSTANTS ---
AUTO_BACKUP_DIR = "backups"

# --- FLUENT STYLESHEET ---
FLUENT_QSS = """
    QWidget { font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif; font-size: 14px; color: #1A1A1A; background-color: #F3F3F3; }
    QFrame.Card { background-color: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 8px; }
    QLabel.SectionTitle { font-size: 16px; font-weight: 600; color: #0067C0; }
    QDateEdit, QTimeEdit { background-color: #FFFFFF; border: 1px solid #D1D1D1; border-radius: 4px; padding: 4px 8px; min-height: 24px; }
    QPushButton { background-color: #FFFFFF; border: 1px solid #D1D1D1; border-radius: 4px; padding: 6px 16px; font-weight: 500; }
    QPushButton:hover { background-color: #F6F6F6; }
    QPushButton[class="primary"] { background-color: #0067C0; color: #FFFFFF; border: 1px solid #005FB8; }
    QPushButton[class="danger"] { background-color: #FEF2F2; color: #D9534F; border: 1px solid #FCA5A5; }
    QTableWidget { border: 1px solid #E5E5E5; border-radius: 4px; background-color: white; selection-background-color: #E1DFDD; selection-color: black; }
    QHeaderView::section { background-color: #FAFAFA; border: none; border-bottom: 1px solid #D1D1D1; padding: 4px; font-weight: 600; }
"""


# --- WORKER ---
class AutoBackupWorker(QThread):
    log_signal = Signal(str)

    def __init__(self, db_path, target_time: QTime, enabled: bool):
        super().__init__()
        self.db_path = db_path
        self.target_time = target_time
        self.enabled = enabled
        self._is_running = True
        self._has_backed_up_today = False

    def run(self):
        while self._is_running:
            if self.enabled:
                now = QTime.currentTime()
                diff_secs = abs(now.secsTo(self.target_time))
                if diff_secs < 60 and not self._has_backed_up_today:
                    self._perform_backup()
                    self._has_backed_up_today = True

                if now.hour() == 0 and now.minute() > 5 and self._has_backed_up_today:
                    self._has_backed_up_today = False

            for _ in range(30):
                if not self._is_running: return
                time.sleep(1)

    def _perform_backup(self):
        if not os.path.exists(self.db_path):
            self.log_signal.emit(f"❌ Lỗi: Không tìm thấy DB tại {self.db_path}")
            return

        if not os.path.exists(AUTO_BACKUP_DIR):
            os.makedirs(AUTO_BACKUP_DIR)

        filename = f"AutoBackup_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}{os.extsep}db"
        dest = os.path.join(AUTO_BACKUP_DIR, filename)
        try:
            shutil.copy2(self.db_path, dest)
            self.log_signal.emit(f"✅ Auto-Backup thành công: {filename}")
        except Exception as e:
            self.log_signal.emit(f"❌ Auto-Backup thất bại: {str(e)}")

    def stop(self):
        self._is_running = False


# --- MAIN UI ---
class IQCSystemOpsTab(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(FLUENT_QSS)

        self.settings = QSettings("QCLabPro", "SystemOps")
        self.db_path = DB_PATH
        print(f"🔧 [SystemOps] Đang sử dụng DB tại: {self.db_path}")

        self._ensure_audit_table()
        self._build_ui()
        self._init_auto_backup()

    def closeEvent(self, event):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.worker.wait()
        super().closeEvent(event)

    def _ensure_db_path_valid(self) -> bool:
        if os.path.exists(self.db_path) and os.path.isfile(self.db_path):
            return True
        QMessageBox.critical(self, "Lỗi Database", f"Không tìm thấy file DB: {self.db_path}")
        return False

    def _get_connection(self):
        if DB_MODULE_OK:
            return engine.connect()
        else:
            raise Exception("Database Module not loaded")

    def _ensure_audit_table(self):
        if not DB_MODULE_OK: return
        try:
            with self._get_connection() as conn:
                # [FIX] Dùng ts_utc thay vì timestamp để khớp với Model
                sql = text("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts_utc TEXT, user_id TEXT, action_type TEXT,
                        details TEXT, old_value TEXT, new_value TEXT,
                        actor TEXT, action TEXT, target TEXT, before_json TEXT, after_json TEXT, note TEXT
                    )
                """)
                conn.execute(sql)
                if hasattr(conn, 'commit'): conn.commit()
        except Exception as e:
            print(f"[Audit Init Error] {e}")

    def _log_audit(self, action, details, old="", new=""):
        if not DB_MODULE_OK: return
        try:
            with self._get_connection() as conn:
                ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                user = "Administrator"
                # [FIX] Dùng ts_utc
                sql = text("""
                    INSERT INTO audit_log (ts_utc, user_id, action_type, details, old_value, new_value)
                    VALUES (:ts, :u, :act, :det, :old, :new)
                """)
                conn.execute(sql, {"ts": ts, "u": user, "act": action, "det": details, "old": old, "new": new})
                if hasattr(conn, 'commit'): conn.commit()
            self._load_audit_logs()
        except:
            pass

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10);
        root.setSpacing(10)

        tabs = QTabWidget()
        root.addWidget(tabs)

        # TAB 1
        tab_ops = QWidget();
        v_ops = QVBoxLayout(tab_ops)

        card_auto = QFrame();
        card_auto.setProperty("class", "Card");
        l_auto = QVBoxLayout(card_auto)
        lbl = QLabel("Cấu hình Tự động Backup");
        lbl.setProperty("class", "SectionTitle");
        l_auto.addWidget(lbl)

        h_auto = QHBoxLayout()
        self.chk_auto_enable = QCheckBox("Bật tự động Backup hàng ngày")
        self.chk_auto_enable.setChecked(self.settings.value("auto_backup", True, type=bool))

        self.tm_auto = QTimeEdit();
        self.tm_auto.setDisplayFormat("HH:mm")
        saved_val = self.settings.value("backup_time", "00:00")
        self.tm_auto.setTime(
            QTime.fromString(saved_val, "HH:mm") if isinstance(saved_val, str) else (saved_val or QTime(0, 0)))

        h_auto.addWidget(self.chk_auto_enable);
        h_auto.addWidget(QLabel("lúc:"));
        h_auto.addWidget(self.tm_auto)

        self.b_save_cfg = QPushButton("Lưu Cấu hình");
        self.b_save_cfg.setProperty("class", "primary")
        h_auto.addWidget(self.b_save_cfg);
        h_auto.addStretch()
        l_auto.addLayout(h_auto)
        self.lbl_auto_status = QLabel("Trạng thái: Đang chờ...");
        self.lbl_auto_status.setStyleSheet("color: #0067C0; font-style: italic;")
        l_auto.addWidget(self.lbl_auto_status)
        v_ops.addWidget(card_auto)

        card_man = QFrame();
        card_man.setProperty("class", "Card");
        l_man = QVBoxLayout(card_man)
        lbl2 = QLabel("Thao tác Thủ công");
        lbl2.setProperty("class", "SectionTitle");
        l_man.addWidget(lbl2)
        h_man = QHBoxLayout()
        self.b_backup = QPushButton("📂 Backup Ngay")
        self.b_restore = QPushButton("♻️ Restore Data")
        self.b_export = QPushButton("📊 Xuất Excel (Log)")
        self.b_clean = QPushButton("🗑️ Dọn dẹp Log cũ");
        self.b_clean.setProperty("class", "danger")
        h_man.addWidget(self.b_backup);
        h_man.addWidget(self.b_restore);
        h_man.addWidget(self.b_export);
        h_man.addWidget(self.b_clean)
        l_man.addLayout(h_man)
        v_ops.addWidget(card_man)
        v_ops.addStretch()
        tabs.addTab(tab_ops, "Tác vụ & Cấu hình")

        # TAB 2
        tab_audit = QWidget();
        v_audit = QVBoxLayout(tab_audit)
        h_filter = QHBoxLayout()
        self.dt_audit_from = QDateEdit(QDate.currentDate().addMonths(-1));
        self.dt_audit_from.setCalendarPopup(True)
        self.dt_audit_to = QDateEdit(QDate.currentDate());
        self.dt_audit_to.setCalendarPopup(True)
        self.b_filter_audit = QPushButton("🔍 Lọc Nhật ký")
        h_filter.addWidget(QLabel("Từ:"));
        h_filter.addWidget(self.dt_audit_from)
        h_filter.addWidget(QLabel("Đến:"));
        h_filter.addWidget(self.dt_audit_to);
        h_filter.addWidget(self.b_filter_audit);
        h_filter.addStretch()
        v_audit.addLayout(h_filter)

        self.tbl_audit = QTableWidget(0, 5)
        self.tbl_audit.setHorizontalHeaderLabels(["Thời gian", "Người dùng", "Hành động", "Chi tiết", "Thay đổi"])
        self.tbl_audit.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl_audit.setAlternatingRowColors(True)
        v_audit.addWidget(self.tbl_audit)
        tabs.addTab(tab_audit, "Nhật ký hệ thống")

        self.b_save_cfg.clicked.connect(self._save_auto_config)
        self.b_backup.clicked.connect(self._backup_db)
        self.b_restore.clicked.connect(self._restore_db)
        self.b_export.clicked.connect(self._export_audit_data)
        self.b_clean.clicked.connect(self._clean_old_data)
        self.b_filter_audit.clicked.connect(self._load_audit_logs)

        if DB_MODULE_OK: self._load_audit_logs()

    # --- LOGIC ---
    def _init_auto_backup(self):
        if hasattr(self, 'worker'): self.worker.stop(); self.worker.wait()
        self.worker = AutoBackupWorker(self.db_path, self.tm_auto.time(), self.chk_auto_enable.isChecked())
        self.worker.log_signal.connect(self._update_auto_status)
        self.worker.start()

    def _save_auto_config(self):
        self.settings.setValue("auto_backup", self.chk_auto_enable.isChecked())
        self.settings.setValue("backup_time", self.tm_auto.time().toString("HH:mm"))
        self._init_auto_backup()
        QMessageBox.information(self, "Đã lưu", "Đã cập nhật cấu hình.")

    def _update_auto_status(self, msg):
        self.lbl_auto_status.setText(msg)
        if "thành công" in msg: self._log_audit("SYSTEM", "Auto Backup", "", msg)

    def _load_audit_logs(self):
        if not DB_MODULE_OK or not self._ensure_db_path_valid(): return
        f_date = self.dt_audit_from.date().toString("yyyy-MM-dd 00:00:00")
        t_date = self.dt_audit_to.date().toString("yyyy-MM-dd 23:59:59")
        try:
            with self._get_connection() as conn:
                # [FIX] Dùng ts_utc
                sql = text(
                    "SELECT ts_utc, user_id, action_type, details, old_value, new_value FROM audit_log WHERE ts_utc BETWEEN :f AND :t ORDER BY ts_utc DESC")
                rows = conn.execute(sql, {"f": f_date, "t": t_date}).fetchall()
                self.tbl_audit.setRowCount(len(rows))
                for i, r in enumerate(rows):
                    self.tbl_audit.setItem(i, 0, QTableWidgetItem(str(r[0])))
                    self.tbl_audit.setItem(i, 1, QTableWidgetItem(str(r[1])))
                    act = QTableWidgetItem(str(r[2]))
                    if "DELETE" in str(r[2]): act.setForeground(QColor("red"))
                    self.tbl_audit.setItem(i, 2, act)
                    self.tbl_audit.setItem(i, 3, QTableWidgetItem(str(r[3])))
                    self.tbl_audit.setItem(i, 4, QTableWidgetItem(f"{r[4]}->{r[5]}" if r[4] or r[5] else ""))
        except Exception as e:
            print(f"Audit Error: {e}")

    def _backup_db(self):
        if not self._ensure_db_path_valid(): return
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst, _ = QFileDialog.getSaveFileName(self, "Lưu File Backup", f"ManualBackup_{ts}{os.extsep}db", f"Database Files (*{os.extsep}db)")
        if dst:
            try:
                shutil.copy2(self.db_path, dst)
                QMessageBox.information(self, "Thành công", f"Đã backup: {dst}")
                self._log_audit("BACKUP", "Manual backup", "", dst)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Backup", str(e))

    def _restore_db(self):
        src, _ = QFileDialog.getOpenFileName(self, "Chọn File Backup", "", "SQLite (*.db)")
        if not src: return
        if QMessageBox.warning(self, "Cảnh báo", f"Dữ liệu hiện tại sẽ bị ghi đè.\nTiếp tục?",
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                shutil.copy2(src, self.db_path)
                self._log_audit("RESTORE", "System Restored", "", f"From {src}")
                QMessageBox.information(self, "OK", "Restore thành công. Khởi động lại ứng dụng.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))

    def _clean_old_data(self):
        d_limit = QDate.currentDate().addYears(-1).toString("yyyy-MM-dd")
        if QMessageBox.question(self, "Dọn dẹp", f"Xóa log trước {d_limit}?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                with self._get_connection() as conn:
                    # [FIX] Dùng ts_utc thay vì timestamp
                    conn.execute(text("DELETE FROM audit_log WHERE ts_utc < :d"), {"d": d_limit})
                    if hasattr(conn, 'commit'): conn.commit()
                self._log_audit("CLEANUP", f"Cleaned logs before {d_limit}")
                self._load_audit_logs()
                QMessageBox.information(self, "OK", "Đã dọn dẹp.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))

    def _export_audit_data(self):
        if not HAS_PANDAS: QMessageBox.warning(self, "Thiếu lib", "Cần cài pandas"); return
        path, _ = QFileDialog.getSaveFileName(self, "Xuất Excel", "Audit_Log.xlsx", "Excel (*.xlsx)")
        if path:
            try:
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                df = pd.read_sql_query("SELECT * FROM audit_log", conn)
                conn.close()
                df.to_excel(path, index=False)
                QMessageBox.information(self, "OK", "Xuất file thành công.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", str(e))