# -*- coding: utf-8 -*-
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
from app.models.base import HybridModel  # Đảm bảo import đúng từ file base.py của bạn


class SyncState(HybridModel):
    """
    Theo dõi dấu thời gian (watermark) cuối cùng của từng bảng.
    Đây là căn cứ để SyncWorker biết chỉ cần lấy dữ liệu 'mới hơn' thời điểm này.
    """
    __tablename__ = "sync_states"

    device_id = Column(String(100), nullable=False)
    table_name = Column(String(100), nullable=False)

    # Thời điểm cuối cùng thực hiện kéo dữ liệu từ Server về
    last_pull_time = Column(DateTime, nullable=True)
    # Thời điểm cuối cùng thực hiện đẩy dữ liệu lên Server
    last_push_time = Column(DateTime, nullable=True)

    # Thêm extend_existing để tránh lỗi 'already defined' nếu bị import trùng
    __table_args__ = (
        UniqueConstraint('device_id', 'table_name', name='uq_device_table'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<SyncState(table='{self.table_name}', pull='{self.last_pull_time}', push='{self.last_push_time}')>"


class SyncHistory(HybridModel):
    """
    Lịch sử chi tiết của từng phiên đồng bộ.
    Giúp quản trị viên tra soát khi có dữ liệu bị mất hoặc lỗi.
    """
    __tablename__ = "sync_histories"

    device_id = Column(String(100), nullable=False)

    # Tự động lấy giờ hệ thống khi bắt đầu phiên đồng bộ
    start_time = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)

    direction = Column(String(20))  # PUSH, PULL, FULL
    status = Column(String(20))  # SUCCESS, FAILED, PARTIAL

    push_count = Column(Integer, default=0)  # Số dòng đã đẩy đi
    pull_count = Column(Integer, default=0)  # Số dòng đã tải về

    error_log = Column(Text, nullable=True)

    __table_args__ = {'extend_existing': True}

    def __repr__(self):
        return f"<SyncHistory(dir='{self.direction}', status='{self.status}', push={self.push_count}, pull={self.pull_count})>"