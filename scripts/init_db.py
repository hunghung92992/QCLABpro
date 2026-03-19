# -*- coding: utf-8 -*-
from app.core.database_orm import engine, Base
# QUAN TRỌNG: Phải import TẤT CẢ các model để SQLAlchemy nhận diện được các bảng

def initialize_database():
    print("🚀 Đang kiểm tra và khởi tạo cấu trúc Database...")
    try:
        # Lệnh này sẽ quét các Model và tạo bảng nếu chưa có trong file .db
        Base.metadata.create_all(bind=engine)
        print("✅ Khởi tạo bảng thành công (hoặc các bảng đã tồn tại).")
    except Exception as e:
        print(f"❌ Lỗi khi khởi tạo Database: {e}")

if __name__ == "__main__":
    initialize_database()