# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from app.models.base import HybridModel


# 1. Bảng IQC Run (Phiên chạy QC)
class IQCRun(HybridModel):
    """
    Đại diện cho một phiên chạy QC (Header).
    Gom nhóm nhiều kết quả xét nghiệm trong cùng một lần chạy máy.
    """
    __tablename__ = "iqc_runs"

    # Kết nối với danh mục Lô (CatalogLot từ catalog_models)
    lot_id = Column(String(36), ForeignKey("catalog_lots.id"), nullable=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    device_id = Column(String(36), ForeignKey("catalog_devices.id"), nullable=True)

    run_date = Column(String(20), index=True)  # YYYY-MM-DD
    run_time = Column(String(20))
    status = Column(String(20), default="Pending")  # Pending, Validated, Rejected

    operator = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)

    # Relationships
    results = relationship("IQCResult", back_populates="run", cascade="all, delete-orphan")
    # lot = relationship("CatalogLot") # Sẽ được kích hoạt khi import CatalogLot


# 2. Bảng IQC Result (Chi tiết kết quả)
class IQCResult(HybridModel):
    """
    Chi tiết kết quả cho từng thông số xét nghiệm (Detail).
    Dùng để vẽ biểu đồ Levey-Jennings.
    """
    __tablename__ = "iqc_results"

    run_id = Column(String(36), ForeignKey("iqc_runs.id"), nullable=False)

    # Kết nối với Analyte gốc để lấy Mean/SD so sánh
    analyte_id = Column(String(36), ForeignKey("catalog_analytes.id"), nullable=True)

    test_code = Column(String(50), index=True)

    # [PHASE 3.1 KHẮC PHỤC]: Thêm level và note để đồng bộ 100% với Schema
    level = Column(String(20), nullable=True)
    note = Column(Text, nullable=True)

    value = Column(String(50))  # Kết quả dạng chữ (định tính)
    value_num = Column(Float, nullable=True)  # Kết quả dạng số (định lượng)

    z_score = Column(Float, nullable=True)  # (Value - Mean) / SD

    # Trạng thái theo Westgard
    pass_fail = Column(Integer, default=1)  # 1: Pass, 0: Fail
    violation_rule = Column(String(50), nullable=True)  # 1-3s, 2-2s...

    is_excluded = Column(Integer, default=0)  # 1: Loại bỏ khỏi thống kê
    comment = Column(Text, nullable=True)

    # Relationship
    run = relationship("IQCRun", back_populates="results")


# 3. Bảng Device Message (Hộp đen lưu trữ dữ liệu thô từ máy)
class DeviceMessage(HybridModel):
    """
    Lưu trữ toàn bộ bản tin thô (ASTM/HL7) từ thiết bị gửi về.
    """
    __tablename__ = "device_messages"

    device_id = Column(String(36), ForeignKey("catalog_devices.id"), nullable=True)
    direction = Column(String(10), default="IN")  # IN: Máy gửi đến, OUT: Lệnh gửi đi
    raw_data = Column(Text, nullable=False)
    protocol = Column(String(20), default="astm")
    status = Column(String(20), default="PENDING")  # PENDING, PROCESSED, ERROR
    error_msg = Column(Text, nullable=True)

    # Relationship
    # device = relationship("Device") # Sẽ được kích hoạt khi import Device