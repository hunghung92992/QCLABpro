# -*- coding: utf-8 -*-
"""
app/models/capa_models.py
(PHASE 7.3) Model Database cho Báo cáo Khắc phục - Phòng ngừa (CAPA)
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
import uuid

from app.core.database_orm import Base


def generate_uuid():
    return str(uuid.uuid4())


class CapaReport(Base):
    __tablename__ = "capa_reports"

    id = Column(String, primary_key=True, default=generate_uuid)

    # --- THÔNG TIN NGUỒN GỐC LỖI ---
    # source_type có thể là 'IQC', 'EQA', hoặc 'OTHER'
    source_type = Column(String(50), nullable=False)
    # ID của kết quả IQC hoặc EQA bị lỗi
    source_id = Column(String(100), nullable=True)

    # Thông tin tóm tắt để hiển thị nhanh (VD: "Xét nghiệm GLU L1 vi phạm 1_3s")
    title = Column(String(255), nullable=False)

    # --- NỘI DUNG CAPA (Do KTV nhập) ---
    issue_description = Column(Text, nullable=True)  # Mô tả sự cố
    root_cause = Column(Text, nullable=True)  # Nguyên nhân gốc rễ
    corrective_action = Column(Text, nullable=True)  # Hành động khắc phục ngay lập tức
    preventive_action = Column(Text, nullable=True)  # Hành động phòng ngừa lâu dài

    # --- QUẢN LÝ TRẠNG THÁI & WORKFLOW ---
    # Trạng thái: DRAFT (Đang nháp), PENDING (Chờ duyệt), APPROVED (Đã duyệt), REJECTED (Yêu cầu làm lại)
    status = Column(String(50), default="DRAFT")

    # --- AUDIT TRAIL (Dấu vết kiểm toán) ---
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_note = Column(Text, nullable=True)  # Lời phê của Trưởng khoa

    # Cờ đồng bộ API
    sync_flag = Column(Integer, default=1)