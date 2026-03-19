import os
import sys
from sqlalchemy import inspect

# Thêm đường dẫn hiện tại
sys.path.append(os.getcwd())

from app.core.database_orm import engine, Base

# ==========================================================
# 1. NẠP TOÀN BỘ MODELS (QUAN TRỌNG)
# ==========================================================
print(">>> [1/3] ĐANG NẠP ĐỊNH NGHĨA BẢNG (MODELS)...")

try:
    # 1. Core
    from app.models.core_models import Department, Device, User, AuditLog

    print("   ✅ [Core] OK")
except ImportError as e:
    print(f"   ❌ [Core] Lỗi: {e}")

try:
    # 2. Catalog
    from app.models.catalog_models import CatalogLot, CatalogAnalyte

    print("   ✅ [Catalog] OK")
except ImportError as e:
    print(f"   ❌ [Catalog] Lỗi: {e}")

try:
    # 3. IQC (Vừa tạo xong)
    from app.models.iqc_models import IQCResult, IQCRun

    print("   ✅ [IQC] OK")
except ImportError as e:
    print(f"   ⚠️ [IQC] Chưa có file model (Overview sẽ báo lỗi).")

try:
    # 4. EQA
    from app.models import EQAProvider, EQAProgram, EQATask

    print("   ✅ [EQA] OK")
except ImportError as e:
    print(f"   ⚠️ [EQA] Chưa có file model.")

# ==========================================================
# 2. XÓA DB CŨ VÀ TẠO MỚI
# ==========================================================
DB_FILE = "../Datauser.db"


def reset_db():
    print(f"\n>>> [2/3] RESET DATABASE '{DB_FILE}'...")

    # Xóa file cũ
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print(f"   🗑️  Đã xóa file '{DB_FILE}' cũ.")
        except Exception as e:
            print(f"   ❌ Không thể xóa file (Đang mở?): {e}")
            return

    # Tạo bảng mới
    print("   🔨 Đang tạo lại toàn bộ bảng...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   ✅ TẠO BẢNG THÀNH CÔNG!")
    except Exception as e:
        print(f"   ❌ LỖI TẠO BẢNG: {e}")
        return

    # Kiểm tra lại
    print("\n>>> [3/3] KIỂM TRA KẾT QUẢ...")
    insp = inspect(engine)
    tables = insp.get_table_names()
    print(f"   Danh sách bảng hiện có ({len(tables)}):")
    print(f"   {tables}")

    if 'department' in tables and 'iqc_result' in tables:
        print("\n🎉 HỆ THỐNG ĐÃ SẴN SÀNG! LỖI 'NO SUCH TABLE' VÀ 'NOT NULL' SẼ HẾT.")
    else:
        print("\n⚠️ Vẫn thiếu bảng. Hãy kiểm tra lại phần Import.")


if __name__ == "__main__":
    reset_db()