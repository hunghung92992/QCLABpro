# -*- coding: utf-8 -*-
"""
app/core/server_db.py
Quản lý kết nối tới PostgreSQL Server.
Đọc cấu hình từ app.core.config (config.json) thay vì biến môi trường.
"""
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.core.config import cfg  # <--- [QUAN TRỌNG] Đọc từ Config mới


def get_server_url():
    """Tạo chuỗi kết nối PostgreSQL từ Config, tự động mã hóa ký tự đặc biệt"""
    # Dùng strip() để loại bỏ các khoảng trắng thừa do vô tình gõ nhầm
    host = str(cfg.get("server_host", "localhost")).strip()
    port = str(cfg.get("server_port", "5432")).strip()
    dbname = str(cfg.get("server_name", "QClab")).strip()
    user = str(cfg.get("server_user", "postgres")).strip()
    password = str(cfg.get("server_password", "XN123456"))

    # [QUAN TRỌNG] Mã hóa user và password để SQLAlchemy không bị lỗi khi có ký tự @, /, #, :
    safe_user = urllib.parse.quote_plus(user)
    safe_password = urllib.parse.quote_plus(password)

    # Chuỗi kết nối chuẩn cho SQLAlchemy
    return f"postgresql://{safe_user}:{safe_password}@{host}:{port}/{dbname}"


# Biến engine toàn cục (lazy loading - chỉ tạo khi cần)
_server_engine = None


def get_server_engine():
    """Tạo hoặc lấy engine đã có"""
    global _server_engine
    if _server_engine is None:
        db_url = get_server_url()
        try:
            # pool_pre_ping=True giúp tự động kết nối lại nếu Server bị ngắt
            # connect_timeout=3: Giảm thời gian chờ nếu mạng rớt (để App đỡ bị đơ)
            _server_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3}
            )
        except Exception as e:
            print(f"❌ [SERVER DB] Lỗi khởi tạo Engine: {e}")
            return None
    return _server_engine


def get_server_session():
    """
    Tạo phiên làm việc (Session) mới tới Server.
    Trả về None nếu không kết nối được.
    """
    engine = get_server_engine()
    if not engine:
        return None

    try:
        # Thử kết nối nhẹ để kiểm tra sống chết
        with engine.connect() as conn:
            pass

        SessionServer = sessionmaker(bind=engine)
        return SessionServer()
    except Exception as e:
        # Log lỗi nhưng không crash app
        print(f"⚠️ [SERVER DB] Không thể kết nối Server: {e}")
        return None
