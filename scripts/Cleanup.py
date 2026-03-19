# tools/cleanup_db.py
import sqlite3
from app.core.path_manager import get_db_path

TABLES_TO_KILL = [
    'sync_state_v2', 'catalog_lot_v2', 'catalog_analyte_v2',
    'sync_state', 'sync_history', 'departments',  # Xóa bảng departments trống để tạo lại chuẩn
    'catalog_device', 'department_test'
]


def cleanup():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()

    print("🧹 Bắt đầu dọn dẹp Database...")
    for table in TABLES_TO_KILL:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"✔️ Đã xóa: {table}")
        except Exception as e:
            print(f"❌ Lỗi khi xóa {table}: {e}")

    conn.commit()
    conn.close()
    print("✨ Dọn dẹp hoàn tất. Database đã sẵn sàng cho Schema mới.")


if __name__ == "__main__":
    cleanup()