# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import HybridModel # Không được dùng từ nơi khác
from datetime import datetime, timezone



# 2. Bảng Phòng Ban
class Department(HybridModel):
    __tablename__ = "departments"  # Đổi từ 'department' -> 'departments' (số nhiều)
    name = Column(String(100), unique=True, nullable=False)
    note = Column(Text, nullable=True)
    active = Column(Integer, default=1)

    # Relationships
    devices = relationship("Device", back_populates="department")
    tests = relationship("DepartmentTest", back_populates="department")
    users = relationship("User", back_populates="department")


# 3. Bảng Thiết bị (Instruments)
class Device(HybridModel):
    __tablename__ = "catalog_devices"
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    active = Column(Integer, default=1)

    # --- CẤU HÌNH KẾT NỐI ---
    connection_type = Column(String(20), default="NONE")  # LIS, RS232, TCPIP
    protocol = Column(String(20), default="ASTM")
    ip_address = Column(String(50), nullable=True)
    ip_port = Column(Integer, nullable=True)
    com_port = Column(String(20), nullable=True)

    note = Column(Text, nullable=True)

    # Relationships
    department = relationship("Department", back_populates="devices")
    test_maps = relationship("DeviceTestMap", back_populates="device", cascade="all, delete-orphan")


# 4. Bảng Mapping Mã Xét Nghiệm
class DeviceTestMap(HybridModel):
    __tablename__ = "device_test_maps"
    device_id = Column(String(36), ForeignKey("catalog_devices.id"))
    machine_code = Column(String(50), nullable=False)  # Mã máy gửi về
    internal_code = Column(String(50), nullable=False)  # Mã quy định trong phần mềm

    device = relationship("Device", back_populates="test_maps")


# 5. Bảng User
class User(HybridModel):
    __tablename__ = "users"
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    fullname = Column(String(100))
    role = Column(String(20), default="VIEWER")  # ADMIN, TECHNICIAN, VIEWER
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    is_active = Column(Integer, default=1)

    department = relationship("Department", back_populates="users")


# 6. Bảng Audit Log
class AuditLog(HybridModel):
    __tablename__ = "audit_logs"
    ts_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    actor = Column(String(50))
    action = Column(String(50))
    target = Column(String(100))
    before_json = Column(Text, nullable=True)
    after_json = Column(Text, nullable=True)
    note = Column(Text, nullable=True)


# 7. Bảng Danh mục xét nghiệm theo khoa
class DepartmentTest(HybridModel):
    __tablename__ = "department_tests"
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False)
    test_code = Column(String(50), nullable=False)
    test_name = Column(String(100))
    unit = Column(String(20))
    active = Column(Integer, default=1)

    department = relationship("Department", back_populates="tests")