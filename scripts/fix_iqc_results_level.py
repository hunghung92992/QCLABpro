# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\User\AppData\Local\QCLabManager\Datauser.db")


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy DB: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        if not column_exists(cur, "iqc_results", "level"):
            print("➕ Đang thêm cột: iqc_results.level")
            cur.execute("ALTER TABLE iqc_results ADD COLUMN level TEXT")
        else:
            print("✅ Cột iqc_results.level đã tồn tại")

        if not column_exists(cur, "iqc_results", "comment"):
            print("➕ Đang thêm cột: iqc_results.comment")
            cur.execute("ALTER TABLE iqc_results ADD COLUMN comment TEXT")
        else:
            print("✅ Cột iqc_results.comment đã tồn tại")

        conn.commit()
        print("🎉 Hoàn tất migration IQCResult")
    finally:
        conn.close()


if __name__ == "__main__":
    main()