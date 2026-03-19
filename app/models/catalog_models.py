# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship

# 🌟 ĐIỂM QUYẾT ĐỊNH: Import HybridModel từ đúng file 'base.py'
from app.models.base import HybridModel


# --- 1. BẢNG LÔ HÓA CHẤT (LOT) ---
class CatalogLot(HybridModel):
    """
    Quản lý các Lô mẫu ngoại kiểm/nội kiểm (QC Lots).
    """
    __tablename__ = "catalog_lots"

    lot_name = Column(String(100), nullable=False)
    lot_code = Column(String(50), nullable=False, index=True)  # Số Lô (Lot number)

    level = Column(String(20))  # L1, L2, L3 hoặc Normal, Abnormal
    manufacturer = Column(String(100), nullable=True)

    # Sử dụng String để lưu ngày cho đơn giản hoặc Date nếu cần tính toán hạn dùng
    mfg_date = Column(String(20))  # Ngày sản xuất
    exp_date = Column(String(20), index=True)  # Ngày hết hạn

    status = Column(String(20), default="active")  # active, expired, closed

    # Khóa ngoại liên kết với bảng departments (Đảm bảo bảng departments đã được tạo)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)

    # Mã nhận diện mẫu trên máy (VD: QC_LEVEL_1)
    device_sample_id = Column(String(50), nullable=True)

    # Quan hệ 1-N với bảng CatalogAnalyte
    analytes = relationship("CatalogAnalyte", back_populates="lot", cascade="all, delete-orphan")


# --- 2. BẢNG THÔNG SỐ XÉT NGHIỆM (ANALYTE) ---
class CatalogAnalyte(HybridModel):
    """
    Giá trị mục tiêu (Target) và dải sai số cho từng thông số trong Lô.
    """
    __tablename__ = "catalog_analytes"

    # Khóa ngoại liên kết với bảng Lô
    lot_id = Column(String(36), ForeignKey("catalog_lots.id"), nullable=False)

    test_code = Column(String(50), nullable=False, index=True)
    test_name = Column(String(100))

    # Các thông số thống kê quan trọng cho biểu đồ Levey-Jennings / Westgard
    mean = Column(Float, nullable=True)
    sd = Column(Float, nullable=True)
    tea = Column(Float, nullable=True)  # Total Allowable Error

    unit = Column(String(20))
    # Lưu danh sách quy tắc Westgard áp dụng, cách nhau bằng dấu phẩy
    westgard_rules = Column(String(200), default="1_3s,2_2s,R_4s")
    sort_order = Column(Integer, default=0)

    # Mã kết nối hệ thống (LIS / Máy xét nghiệm)
    lims_code = Column(String(100), nullable=True)
    instrument_code = Column(String(100), nullable=True)

    note = Column(Text, nullable=True)

    # Quan hệ ngược lại với bảng CatalogLot
    lot = relationship("CatalogLot", back_populates="analytes")