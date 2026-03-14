# -*- coding: utf-8 -*-
import sys
import os
import pathlib
import bcrypt

# --- THIẾT LẬP PATH ---
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.database_orm import engine, SessionLocal

# 🔥 CHIẾN THUẬT ÉP BUỘC: Import trực tiếp từ file vật lý
# Tôi nghi ngờ bạn đang bị loạn giữa base.py và base_model.py
# Chúng ta sẽ import Base từ models để đảm bảo lấy đúng cái 'Registry' chung
from app.models import Base, User, Department, HybridModel


def rebuild():
    print("🚀 BẮT ĐẦU CƯỠNG CHẾ TẠO DATABASE M2...")

    # 1. Xóa file vật lý để đảm bảo không bị lock hoặc cache
    db_path = str(engine.url.database)
    if os.path.exists(db_path):
        try:
            engine.dispose()
            os.remove(db_path)
            print(f"✅ Đã xóa bỏ file DB cũ: {db_path}")
        except:
            pass

    # 2. ÉP BUỘC đăng ký bảng vào Metadata
    # Nếu Base.metadata.tables vẫn trống, chúng ta sẽ nạp thủ công
    import app.models.core_models
    import app.models.catalog_models
    import app.models.iqc_models
    import app.models.eqa_models
    import app.models.sync_models

    table_list = list(Base.metadata.tables.keys())
    print(f"📋 Danh sách bảng đã nạp thành công: {table_list}")

    if not table_list:
        print("❌ LỖI NGHIÊM TRỌNG: Vẫn không thấy bảng nào! Kiểm tra ngay file app/models/__init__.py")
        return

    # 3. Tạo bảng
    Base.metadata.create_all(bind=engine)
    print("🔨 Đã xây dựng lại toàn bộ cấu trúc bảng trên ổ cứng.")

    # 4. Seed dữ liệu
    db = SessionLocal()
    try:
        print("🌱 Đang bơm dữ liệu Seed...")
        # Sử dụng đúng class đã được map
        new_dept = Department(name="Khoa Xét Nghiệm", active=1)
        db.add(new_dept)
        db.flush()

        hashed_pw = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_admin = User(
            username="admin",
            password_hash=hashed_pw,
            fullname="Administrator",
            role="ADMIN",
            department_id=new_dept.id,
            sync_flag=0
        )
        db.add(new_admin)
        db.commit()
        print("✅ SEED THÀNH CÔNG: Tài khoản admin/admin123 đã sẵn sàng.")

    except Exception as e:
        print(f"❌ Lỗi Seed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    rebuild()
    print("\n" + "⭐" * 40)
    print("🔥 MỐC M2 ĐÃ ĐƯỢC CHỐT HẠ THÀNH CÔNG! 🔥")
    print("⭐" * 40)