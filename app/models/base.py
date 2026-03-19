# -*- coding: utf-8 -*-
# app/models/base.py

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, event
from sqlalchemy.orm import declarative_base

# 🌟 GỐC RỄ CỦA TOÀN BỘ SCHEMA (Nguồn chân lý duy nhất)
Base = declarative_base()


def generate_uuid() -> str:
    """Tạo ID ngẫu nhiên duy nhất (UUID v4)."""
    return str(uuid.uuid4())


class HybridModel(Base):
    """
    Class cha cho tất cả các bảng dữ liệu cần đồng bộ Hybrid (Offline-First).
    Tự động thêm UUID và các cột phục vụ sync/audit.
    """
    __abstract__ = True

    # 1. ĐỊNH DANH (IDENTITY)
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # ID trên Server (nếu cần map dữ liệu cũ hoặc đồng bộ đặc biệt)
    server_id = Column(String(36), default=generate_uuid, nullable=True)

    # 2. QUẢN LÝ THỜI GIAN (TIMESTAMPS)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 3. TRẠNG THÁI ĐỒNG BỘ (SYNC LOGIC)
    # 0 = Synced
    # 1 = Pending Insert/Update
    # 2 = Pending Delete (soft delete để sync xóa lên server)
    sync_flag = Column(Integer, default=1)

    # 4. PHIÊN BẢN (VERSION CONTROL)
    version = Column(Integer, default=1)

    # 5. AUDIT LOG
    created_by = Column(String(50), nullable=True)
    updated_by = Column(String(50), nullable=True)

    def to_dict(self) -> dict:
        """
        Chuyển object SQLAlchemy thành dict để sync / serialize.
        """
        data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = value
        return data

    def mark_pending_update(self, username: str | None = None) -> None:
        """
        Đánh dấu bản ghi vừa bị sửa, cần sync lại.
        """
        self.sync_flag = 1
        self.version += 1
        self.updated_at = datetime.now()
        if username:
            self.updated_by = username

    def mark_synced(self) -> None:
        """
        Đánh dấu bản ghi đã sync thành công.
        """
        self.sync_flag = 0

    def soft_delete(self, username: str | None = None) -> None:
        """
        Xóa mềm: không xóa khỏi DB local, chỉ đánh dấu để worker sync xóa lên server.
        """
        self.sync_flag = 2
        self.updated_at = datetime.now()
        if username:
            self.updated_by = username

    def update_from_dict(self, data: dict) -> None:
        """
        Cập nhật object từ dict (ví dụ khi pull từ server về).
        Không cho sửa `id` và `created_at`.
        """
        for key, value in data.items():
            if hasattr(self, key) and key not in ["id", "created_at"]:
                if ("date" in key or key.endswith("_at")) and isinstance(value, str):
                    try:
                        value = datetime.fromisoformat(value)
                    except ValueError:
                        pass
                setattr(self, key, value)


# ==========================================
# SQLALCHEMY EVENTS
# ==========================================

@event.listens_for(Base, "before_insert", propagate=True)
def before_insert_logic(mapper, connection, target):
    """
    Trước khi insert:
    - Nếu model có sync_flag thì mặc định đánh dấu cần sync.
    """
    if hasattr(target, "sync_flag"):
        target.sync_flag = 1


@event.listens_for(Base, "before_update", propagate=True)
def before_update_logic(mapper, connection, target):
    """
    Trước khi update:
    - Nếu bản ghi đang ở trạng thái synced (0) mà bị sửa,
      tự động chuyển thành pending update (1)
    - Tăng version để phục vụ conflict resolution
    """
    if hasattr(target, "sync_flag") and target.sync_flag == 0:
        target.sync_flag = 1
        if hasattr(target, "version") and target.version is not None:
            target.version += 1
        else:
            target.version = 1