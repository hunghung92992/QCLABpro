# -*- coding: utf-8 -*-
import sys
import pathlib

# --- BƯỚC THẦN THÁNH: ÉP PATH ---
# Lấy đường dẫn tuyệt đối của thư mục QClab_Manager
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- BÂY GIỜ MỚI IMPORT ---
try:
    from app.core.database_orm import SessionLocal
    from app.models.core_models import Department
    from app.services.sync_manager import SyncManager

    print("✅ Hệ thống đã nhận diện được module App.")
except ImportError as e:
    print(f"❌ Vẫn lỗi Import: {e}")
    print(f"Thử kiểm tra file: {BASE_DIR / 'app' / 'core' / 'sync_manager.py'} có tồn tại không?")
    sys.exit(1)


def run_test():
    db = SessionLocal()
    manager = SyncManager()
    try:
        # Lấy dữ liệu để test
        dept = db.query(Department).first()
        if not dept:
            print("⚠️ DB trống, hãy chạy final_rebuild.py trước!")
            return

        print(f"📊 Trước khi sửa: {dept.name}, sync_flag={dept.sync_flag}")

        # Sửa tên để test Event Trigger
        dept.name = "Khoa Xét Nghiệm Trung Tâm"
        db.commit()

        db.refresh(dept)
        print(f"✅ Sau khi sửa: sync_flag={dept.sync_flag}, version={dept.version}")

        if dept.sync_flag == 1:
            print("🚀 THÀNH CÔNG: Dữ liệu đã tự động đánh dấu chờ đồng bộ!")
            manager.simulate_sync_process()

    finally:
        db.close()
        manager.close()


if __name__ == "__main__":
    run_test()