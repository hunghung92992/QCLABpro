# -*- coding: utf-8 -*-
"""
app/services/iqc_rule_service.py
(MỚI) Dịch vụ quản lý Bảng cấu hình quy tắc (iqc_rule_config).
"""

import sqlite3
from typing import Optional, List, Dict, Any

from app.core.database_orm import get_db_connection


class IQCRuleService:

    def __init__(self):
        # Đảm bảo bảng tồn tại (an toàn)
        try:
            with get_db_connection() as con:
                self._ensure_rule_table(con)
        except Exception as e:
            print(f"[IQCRuleService INIT ERROR] {e}")

    def _ensure_rule_table(self, con: sqlite3.Connection):
        """Đảm bảo bảng iqc_rule_config tồn tại (an toàn)."""
        con.execute("""CREATE TABLE IF NOT EXISTS iqc_rule_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT, 
            test_code TEXT, 
            level TEXT,
            mean REAL, 
            sd REAL, 
            tea REAL, 
            rules TEXT,
            UNIQUE(department, test_code, level)
        )""")
        con.commit()

    def list_rules(self) -> List[Dict[str, Any]]:
        """Lấy tất cả các quy tắc đã cấu hình."""
        try:
            with get_db_connection() as con:
                rows = con.execute(
                    "SELECT * FROM iqc_rule_config ORDER BY department, test_code, level"
                ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error as e:
            print(f"[IQCRuleService ERROR] list_rules: {e}")
            return []

    def get_rule(self, department: str, test_code: str, level: str) -> Optional[Dict[str, Any]]:
        """Lấy một quy tắc cụ thể."""
        try:
            with get_db_connection() as con:
                r = con.execute(
                    """SELECT * FROM iqc_rule_config
                       WHERE LOWER(COALESCE(department,'')) = LOWER(COALESCE(?,'')) 
                         AND LOWER(test_code) = LOWER(?)
                         AND LOWER(COALESCE(level,'')) = LOWER(COALESCE(?,''))""",
                    (department or "", test_code, level or "")
                ).fetchone()
            return dict(r) if r else None
        except sqlite3.Error as e:
            print(f"[IQCRuleService ERROR] get_rule: {e}")
            return None

    def upsert_rule(self, department: str, test_code: str, level: str,
                    mean: float, sd: float, tea: float, rules: str) -> Dict[str, Any]:
        """Thêm mới hoặc cập nhật một quy tắc."""
        if not test_code:
            return {"ok": False, "reason": "Test Code là bắt buộc."}

        try:
            with get_db_connection() as con:
                con.execute(
                    """
                    INSERT INTO iqc_rule_config(department, test_code, level, mean, sd, tea, rules)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(department, test_code, level) DO UPDATE SET
                        mean=excluded.mean,
                        sd=excluded.sd,
                        tea=excluded.tea,
                        rules=excluded.rules
                    """,
                    (department or "", test_code, level or "", mean, sd, tea, rules)
                )
                con.commit()
            return {"ok": True}
        except sqlite3.Error as e:
            return {"ok": False, "reason": str(e)}

    def delete_rule(self, rule_id: int) -> Dict[str, Any]:
        """Xóa một quy tắc bằng ID."""
        try:
            with get_db_connection() as con:
                con.execute("DELETE FROM iqc_rule_config WHERE id=?", (rule_id,))
                con.commit()
            return {"ok": True}
        except sqlite3.Error as e:
            return {"ok": False, "reason": str(e)}