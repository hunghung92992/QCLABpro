# -*- coding: utf-8 -*-
"""
app/core/database_orm.py
Quản lý kết nối Database Local (SQLite) và Remote (PostgreSQL).
Tự động khởi tạo Schema, dữ liệu mẫu và đồng bộ cấu hình 1 nguồn (config.json).
"""
import logging
import os
import json
import sqlite3
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 🌟 IMPORT ĐƯỜNG DẪN CHUẨN
from app.core.path_manager import PathManager
# 🌟 IMPORT BASE (Chỉ import Base để tránh Circular Import)
from app.models.base import Base

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. THIẾT LẬP ĐƯỜNG DẪN LOCAL DB & BẢO MẬT (SQLCIPHER PREPARATION)
# ==============================================================================
db_path = PathManager.get_db_path()
DB_PATH = db_path
os.makedirs(os.path.dirname(db_path), exist_ok=True)

clean_path = db_path.replace('\\', '/')

# [TÙY CHỌN BẢO MẬT] - Nếu sau này bạn cài pysqlcipher3, hãy bỏ comment 2 dòng dưới
# DB_PASSWORD = "QC_Secure_Pass_2026"
# SQLALCHEMY_DATABASE_URL = f"sqlite+pysqlcipher://:{DB_PASSWORD}@/{clean_path}"

# Mặc định dùng SQLite bản rõ:
SQLALCHEMY_DATABASE_URL = f"sqlite:///{clean_path}"


# ==============================================================================
# 1. HÀM MIGRATION TỰ ĐỘNG
# ==============================================================================
def apply_migrations(engine_obj):
    """Tự động vá tất cả các cột thiếu cho các bảng (VD: audit_logs)"""
    TABLE_NAME = "audit_logs"
    columns_to_add = [
        ("user_id", "TEXT"),
        ("action_type", "TEXT"),
        ("details", "TEXT"),
        ("old_value", "TEXT"),
        ("new_value", "TEXT")
    ]

    try:
        # Sử dụng begin() thay vì connect() để tự động commit trong SQLAlchemy 2.0
        with engine_obj.begin() as conn:
            check_table = conn.execute(text(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'"
            )).fetchone()

            if not check_table:
                return

            cursor = conn.execute(text(f"PRAGMA table_info({TABLE_NAME})"))
            existing_columns = [row[1] for row in cursor]

            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    print(f"🔧 [Migration] Đang vá cột: '{col_name}' vào bảng '{TABLE_NAME}'...")
                    conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {col_name} {col_type}"))

    except Exception as e:
        logger.warning(f"⚠️ [Migration Info] {e}")


# ==============================================================================
# 2. TỰ ĐỘNG KHỞI TẠO SCHEMA & DỮ LIỆU MẪU
# ==============================================================================
def init_database(engine_obj):
    """Import toàn bộ Models và khởi tạo bảng vào DB Local."""
    try:
        # 🌟 PHẢI IMPORT ĐẦY ĐỦ Ở ĐÂY để Metadata nhận diện được TẤT CẢ các bảng trước khi tạo
        from app.models.core_models import User, Department, AuditLog, Device, DeviceTestMap
        from app.models.catalog_models import CatalogLot, CatalogAnalyte
        from app.models.iqc_models import IQCRun, IQCResult, DeviceMessage
        from app.models.eqa_models import EQAProvider, EQAProgram, EQATask
        from app.models.sync_models import SyncState, SyncHistory

        # 1. Tạo bảng (SQLAlchemy sẽ chỉ tạo những bảng chưa tồn tại)
        Base.metadata.create_all(bind=engine_obj)

        # 2. Chạy migration vá cột
        apply_migrations(engine_obj)

        print("✅ [DB] Toàn bộ Schema (bao gồm LIS và EQA) đã được kiểm tra/khởi tạo.")

        # 3. Khởi tạo tài khoản Admin mặc định
        Session = sessionmaker(bind=engine_obj)
        with Session() as session:
            admin_user = session.query(User).filter(User.username == 'admin').first()
            if not admin_user:
                print("⚠️ [DB] Đang tạo tài khoản Admin mặc định...")
                new_admin = User()
                new_admin.id = str(uuid.uuid4())
                new_admin.username = 'admin'
                new_admin.fullname = 'Administrator'
                new_admin.role = 'SUPERADMIN'

                # Gán thuộc tính linh hoạt để tránh lỗi "invalid keyword"
                for field in ['active', 'is_active']:
                    if hasattr(new_admin, field):
                        setattr(new_admin, field, 1)

                if hasattr(new_admin, 'password_hash'):
                    # Mật khẩu mặc định: admin123
                    new_admin.password_hash = '$2b$12$l.xjCmCVCPZmjq/W8sAgVu6eVslNGTNpri.cQQURGAuVoPvevlPxa'

                session.add(new_admin)
                session.commit()
                print("✅ [DB] Đã khởi tạo thành công tài khoản: admin / admin123")

    except Exception as e:
        logger.error(f"⚠️ [DB INIT ERROR] {e}")
        print(f"❌ [DB INIT ERROR] {e}")


# ==============================================================================
# 3. KHỞI TẠO ENGINE VÀ SESSION CHO LOCAL DB
# ==============================================================================
try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}  # Rất quan trọng cho SQLite khi dùng đa luồng
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Thực hiện khởi tạo ngay khi file được import
    init_database(engine)
    print(f"🚀 [DB] Kết nối Local thành công tại: {db_path}")

except Exception as e:
    logger.critical(f"❌ [DB CRITICAL LỖI KHỞI TẠO] {e}")
    engine = None
    SessionLocal = sessionmaker()


# ==============================================================================
# 4. ENGINE ĐỒNG BỘ SERVER (POSTGRESQL LAN)
# ==============================================================================
def get_remote_engine():
    """
    Tạo engine kết nối tới PostgreSQL (Đọc thống nhất từ config.json)
    """
    config_path = PathManager.get_config_path()
    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        pg_cfg = cfg.get("postgresql", {})
        host = pg_cfg.get("host")
        port = pg_cfg.get("port", "5432")
        db_name = pg_cfg.get("dbname")
        user = pg_cfg.get("user")
        pwd = pg_cfg.get("password")

        # Nếu chưa cấu hình Host trong giao diện Cài đặt, bỏ qua
        if not host or not db_name or not user:
            return None

        # URL chuẩn của PostgreSQL
        url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db_name}"

        # Timeout 5s để hệ thống không bị treo nếu mất mạng LAN
        remote_engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        return remote_engine

    except Exception as e:
        logger.error(f"❌ Lỗi khởi tạo Remote Engine (PostgreSQL): {e}")
        return None


# ==============================================================================
# 5. CÁC HÀM TIỆN ÍCH DEPENDENCY
# ==============================================================================
def get_db():
    """Hỗ trợ Dependency Injection cho FastAPI hoặc các Service"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_connection():
    """Hỗ trợ lấy raw connection cho Pandas/SQL thuần"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
