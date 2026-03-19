# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import HybridModel


class EQAProvider(HybridModel):
    """Đơn vị cung cấp ngoại kiểm (VD: CAP, RIQAS, Trung tâm kiểm chuẩn)."""
    __tablename__ = "eqa_providers"

    name = Column(String(100), nullable=False)
    contact_info = Column(Text, nullable=True)
    active = Column(Integer, default=1)

    programs = relationship("EQAProgram", back_populates="provider")


class EQAProgram(HybridModel):
    """Chương trình ngoại kiểm (VD: Hóa sinh, Huyết học)."""
    __tablename__ = "eqa_programs"

    # Lưu ý: HybridModel dùng UUID nên ID là String(50), ta chỉnh String(36) thành String(50) cho đồng bộ
    provider_id = Column(String(50), ForeignKey("eqa_providers.id"))
    name = Column(String(100))
    code = Column(String(50), nullable=True)
    year = Column(Integer)
    active = Column(Integer, default=1)

    provider = relationship("EQAProvider", back_populates="programs")
    tasks = relationship("EQATask", back_populates="program")


class EQATask(HybridModel):
    """Mẫu ngoại kiểm cụ thể và thời hạn thực hiện (Task/Sample)."""
    __tablename__ = "eqa_tasks"

    program_id = Column(String(50), ForeignKey("eqa_programs.id"))

    # 🌟 BỔ SUNG: 2 Cột này để đáp ứng câu lệnh SQL thuần của EQAService cũ
    provider_name = Column(String(100))
    program_name = Column(String(100))

    sample_code = Column(String(50))
    round_no = Column(Integer, default=1)
    deadline = Column(String(20))  # YYYY-MM-DD
    status = Column(String(20), default="PENDING")  # Pending, Done, Late

    # 🌟 BỔ SUNG: Cột year đã được thêm vào đây
    year = Column(Integer, index=True)

    device_name = Column(String(100), nullable=True)
    assigned_to = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)

    program = relationship("EQAProgram", back_populates="tasks")