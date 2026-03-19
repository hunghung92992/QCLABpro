# -*- coding: utf-8 -*-
"""
app/services/menu_service.py
Dịch vụ quản lý phân quyền (ẩn/hiện) menu.
Ported từ db_menu_visibility.py.
"""

import sqlite3
from typing import Dict, Optional

from app.core.database_orm import get_db_connection

# Các khóa menu chuẩn của hệ thống
MENU_KEYS = [
    "overview", "qc_sample", "qc_result", "eqa", "devices",
    "reports", "reports", "alerts", "users", "settings"
]


class MenuService:

    def get_visibility_map(self, username: str, role: str) -> Dict[str, int]:
        """
        Lấy bản đồ (map) các menu được phép hiển thị.
        Logic: Ưu tiên cài đặt theo user, nếu không có thì fallback theo role (mặc định là 1).
        """
        # Mặc định tất cả đều hiển thị
        visibility = {key: 1 for key in MENU_KEYS}

        # (Logic fallback theo Role có thể thêm ở đây nếu cần)
        # Ví dụ: if role == 'VIEWER': visibility['users'] = 0

        # Ghi đè bằng cài đặt cụ thể của user (nếu có)
        try:
            with get_db_connection() as conn:
                rows = conn.execute(
                    "SELECT menu_key, visible FROM menu_visibility WHERE username = ?",
                    (username,)
                ).fetchall()

                user_settings = {row["menu_key"]: int(row["visible"]) for row in rows}
                visibility.update(user_settings)

        except sqlite3.Error as e:
            print(f"[MenuService ERROR] Không thể tải visibility map: {e}")

        return visibility

    def set_visibility(self, username: str, visibility_dict: Dict[str, int]) -> bool:
        """Lưu cài đặt ẩn/hiện menu cho một user."""
        try:
            with get_db_connection() as conn:
                # Xóa cài đặt cũ của user
                conn.execute("DELETE FROM menu_visibility WHERE username = ?", (username,))

                # Thêm cài đặt mới
                params = [
                    (username, key, int(visible))
                    for key, visible in visibility_dict.items()
                    if key in MENU_KEYS
                ]
                conn.executemany(
                    "INSERT INTO menu_visibility (username, menu_key, visible) VALUES (?, ?, ?)",
                    params
                )
                conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"[MenuService ERROR] Không thể lưu visibility: {e}")
            return False