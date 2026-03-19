# -*- coding: utf-8 -*-
"""
app/services/iqc_repository.py
DAO (Kho lưu trữ) cho Nội kiểm (SQLite).
Đảm bảo an toàn (safe) khi chạy với DB hiện có, tự tạo bảng tối thiểu nếu thiếu.
Ported từ iqc_repository.py.
"""

from __future__ import annotations
import sqlite3
import os
import datetime
from typing import List, Optional, Dict, Any, Tuple

# Imports từ core
from app.core.database_orm import get_db_connection


class IQCRepository:
    """
    DAO "an toàn" cho Nội kiểm.
    Các hàm trong đây phải kiểm tra sự tồn tại của bảng/cột trước khi truy vấn.
    """

    def __init__(self):
        self.ensure_min_schema()

    def _con(self) -> sqlite3.Connection:
        # Repository này tự quản lý kết nối để đảm bảo schema
        # (Không dùng get_db_connection() chung vì nó không chạy ensure_min_schema)

        # Lấy DB path từ config (thay vì tự đoán)
        from app.core.config import config_loader
        db_path = config_loader.get_db_path()

        if not db_path:
            raise ValueError("IQCRepository: db_path không được cấu hình.")

        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        return con

    def table_exists(self, con: sqlite3.Connection, name: str) -> bool:
        r = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
        return bool(r)

    def ensure_min_schema(self):
        """
        Đảm bảo 3 bảng TỐI THIỂU (legacy) tồn tại.
        Không làm thay đổi schema v2 (iqc_run, iqc_result).
        """
        try:
            with self._con() as con:
                con.execute("""
                CREATE TABLE IF NOT EXISTS qc_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_time TEXT NOT NULL,
                    department_id INTEGER,
                    device_id INTEGER,
                    device_name TEXT,
                    test_code TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    value REAL,
                    unit TEXT,
                    lot_id INTEGER,
                    user TEXT,
                    note TEXT
                )""")

                con.execute("""
                CREATE TABLE IF NOT EXISTS qc_lot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_code TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    lot_code TEXT,
                    expiry_date TEXT
                )""")

                con.execute("""
                CREATE TABLE IF NOT EXISTS qc_target (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_code TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    lot_id INTEGER,
                    mean REAL,
                    sd REAL
                )""")
                con.commit()
        except sqlite3.Error as e:
            print(f"[IQCRepository ERROR] ensure_min_schema: {e}")

    # --- Các hàm truy vấn an toàn (Fallback) ---

    def get_qc_target(self, test_code: str, level: int, lot_id: Optional[int]) -> Tuple[
        Optional[float], Optional[float]]:
        """Lấy target (mean, sd) từ bảng qc_target (cũ)."""
        try:
            with self._con() as con:
                if not self.table_exists(con, "qc_target"):
                    return (None, None)

                r = con.execute("""
                    SELECT mean, sd FROM qc_target
                    WHERE test_code=? AND level=? AND (lot_id IS ? OR lot_id=?)
                    ORDER BY (lot_id IS NOT NULL) DESC LIMIT 1
                """, (test_code, int(level), lot_id, lot_id)).fetchone()

                if r:
                    return (r["mean"], r["sd"])
        except sqlite3.Error as e:
            print(f"[IQCRepository ERROR] get_qc_target: {e}")

        return (None, None)

    def get_qc_history(self, test_code: str, device_id: Optional[int], lot_id: Optional[int], level: int,
                       limit: int = 20) -> List[float]:
        """Lấy lịch sử (values) từ bảng qc_results (cũ)."""
        try:
            with self._con() as con:
                if not self.table_exists(con, "qc_results"):
                    return []

                sql = """
                    SELECT value FROM qc_results
                    WHERE test_code=? AND level=?
                    {and_device} {and_lot}
                    ORDER BY datetime(run_time) DESC LIMIT ?
                """
                and_device = "AND device_id=?" if device_id is not None else ""
                and_lot = "AND lot_id=?" if lot_id is not None else ""
                sql = sql.format(and_device=and_device, and_lot=and_lot)

                params = [test_code, int(level)]
                if device_id is not None: params.append(device_id)
                if lot_id is not None: params.append(lot_id)
                params.append(int(limit))

                rows = list(con.execute(sql, params))
                vals = [r["value"] for r in rows if r["value"] is not None]
                return list(reversed(vals))  # Trả về: cũ -> mới
        except sqlite3.Error as e:
            print(f"[IQCRepository ERROR] get_qc_history: {e}")
            return []