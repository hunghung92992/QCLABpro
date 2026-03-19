# -*- coding: utf-8 -*-
import logging
from sqlalchemy import text
from app.core.database_orm import engine, Base, SessionLocal
from app.core.path_manager import PathManager

logger = logging.getLogger(__name__)


def init_database_schema():
    """Tạo toàn bộ các bảng nếu chưa tồn tại dựa trên Base models."""
    try:
        # Nạp TẤT CẢ các module models vào bộ nhớ để SQLAlchemy (Base) nhận diện Schema
        from app.models import (
            core_models,
            catalog_models,
            eqa_models,
            iqc_models,
            sync_models
        )

        logger.info("🔨 Đang kiểm tra và khởi tạo Schema Database...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Khởi tạo Schema thành công.")
    except Exception as e:
        logger.error(f"❌ Lỗi khởi tạo Schema: {e}")


def seed_initial_data():
    """Bơm dữ liệu mặc định (Admin, Config cơ bản) vào DB trắng."""
    db = SessionLocal()
    try:
        # Kiểm tra xem đã có tài khoản admin chưa (Dùng SQL thô cho an toàn lúc bootstrap)
        check_admin_sql = text("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        count = db.execute(check_admin_sql).scalar()

        if count == 0:
            logger.info("🌱 Không tìm thấy Admin. Đang khởi tạo tài khoản SUPERADMIN mặc định...")
            # Tạo tài khoản admin/admin123 (Nhớ hash password nếu hệ thống của bạn yêu cầu)
            insert_admin = text("""
                INSERT INTO users (username, password, full_name, role, is_active) 
                VALUES ('admin', 'admin123', 'Administrator', 'SUPERADMIN', 1)
            """)
            db.execute(insert_admin)
            db.commit()
            logger.info("✅ Đã tạo tài khoản mặc định: admin / admin123")
    except Exception as e:
        db.rollback()
        # Bỏ qua lỗi nếu bảng users chưa thực sự tồn tại (do lỗi model import)
        logger.warning(f"⚠️ Bỏ qua seed data (Có thể bảng users chưa cấu hình đúng): {e}")
    finally:
        db.close()


def run_bootstrap():
    """Hàm chạy duy nhất được gọi từ main.py khi bật App."""
    logger.info("🚀 BẮT ĐẦU TIẾN TRÌNH BOOTSTRAP...")
    PathManager.ensure_structure()  # Đảm bảo thư mục AppData đã có
    init_database_schema()
    seed_initial_data()
    logger.info("🏁 BOOTSTRAP HOÀN TẤT! HỆ THỐNG SẴN SÀNG.")