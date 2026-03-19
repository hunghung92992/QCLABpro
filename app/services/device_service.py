# -*- coding: utf-8 -*-
"""
app/services/device_service.py
Service TẬP TRUNG quản lý Thiết bị LIS & Lịch Bảo trì (Hợp nhất từ equipment_service).
Tuân thủ Single Source of Truth, dùng SessionLocal chuẩn ORM (An toàn Threading).
"""
import uuid
import socket
import datetime
import os
import logging
from datetime import timezone
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import desc, text
from sqlalchemy.orm import Session, joinedload

# App Imports
from app.core.database_orm import SessionLocal
from app.models.core_models import Device, Department, DeviceTestMap
from app.models.iqc_models import DeviceMessage

# Pyserial (Optional)
try:
    import serial
except ImportError:
    serial = None

logger = logging.getLogger(__name__)

class DeviceService:
    def __init__(self):
        # Lấy tên bảng chính xác từ Model để xử lý Migration
        self.table_name = Device.__tablename__
        self._ensure_maintenance_columns()

    def _ensure_maintenance_columns(self):
        """Kiểm tra và thêm cột bảo trì vào đúng bảng nếu chưa có."""
        session = SessionLocal()
        try:
            # Kiểm tra cột trên bảng thật
            session.execute(text(f"SELECT maintenance_cycle FROM {self.table_name} LIMIT 1"))
        except Exception:
            session.rollback()
            try:
                # Thêm cột nếu thiếu
                session.execute(text(f"ALTER TABLE {self.table_name} ADD COLUMN maintenance_cycle INTEGER DEFAULT 0"))
                session.execute(text(f"ALTER TABLE {self.table_name} ADD COLUMN last_maintenance_date TEXT"))
                session.commit()
                logger.info(f"[DeviceService] Đã thêm cột bảo trì vào bảng {self.table_name}")
            except Exception as e:
                logger.warning(f"[DeviceService] Migration Info: {e}")
        finally:
            session.close()

    # ==========================================
    # 1. QUẢN LÝ DANH MỤC & THIẾT BỊ (CRUD)
    # ==========================================

    def get_departments(self) -> List[Dict[str, Any]]:
        """Lấy danh sách phòng ban."""
        session = SessionLocal()
        try:
            depts = session.query(Department).filter(Department.active == 1).order_by(Department.name).all()
            return [{"id": d.id, "name": d.name} for d in depts]
        except Exception as e:
            logger.error(f"[DeviceService] Lỗi lấy phòng ban: {e}")
            return []
        finally:
            session.close()

    def get_device(self, device_id: str) -> Optional[Device]:
        """Lấy thông tin 1 thiết bị."""
        session = SessionLocal()
        try:
            dev = session.query(Device).filter(Device.id == str(device_id)).first()
            if dev: return dev
            # Fallback tìm theo Code
            return session.query(Device).filter(Device.code == str(device_id)).first()
        except Exception as e:
            logger.error(f"[DeviceService] Lỗi lấy thiết bị: {e}")
            return None
        finally:
            session.close()

    def list_devices(self, filters=None) -> List[Dict[str, Any]]:
        """Lấy danh sách thiết bị. Sử dụng ORM chuẩn."""
        session = SessionLocal()
        try:
            query = session.query(Device).options(joinedload(Device.department)).filter(Device.active == 1)

            if filters:
                if 'department_id' in filters and filters['department_id']:
                    query = query.filter(Device.department_id == filters['department_id'])
                if 'search' in filters and filters['search']:
                    kw = f"%{filters['search']}%"
                    query = query.filter((Device.name.ilike(kw)) | (Device.code.ilike(kw)))

            # Sắp xếp
            devices = query.order_by(desc(Device.created_at) if hasattr(Device, 'created_at') else desc(Device.id)).all()

            result = []
            for dev in devices:
                d = {
                    "id": str(dev.id),
                    "code": getattr(dev, 'code', '') or '',
                    "name": getattr(dev, 'name', '') or '',
                    "model": getattr(dev, 'model', '') or '',
                    "protocol": getattr(dev, 'protocol', '') or '',
                    "department_id": getattr(dev, 'department_id', '') or '',
                    "note": getattr(dev, 'note', '') or '',
                    "department_name": dev.department.name if dev.department else "",

                    # Kết nối
                    "conn_type": getattr(dev, 'connection_type', 'NONE'),
                    "ip": getattr(dev, 'ip_address', '') or '',
                    "port": getattr(dev, 'ip_port', 5000) or 5000,
                    "serial_port": getattr(dev, 'com_port', '') or '',
                    "file_path": getattr(dev, 'file_path', '') or '',

                    # Serial params
                    "baudrate": getattr(dev, 'baudrate', 9600),
                    "data_bits": getattr(dev, 'data_bits', 8),
                    "stop_bits": getattr(dev, 'stop_bits', 1),
                    "parity": getattr(dev, 'parity', 'N'),

                    # Bảo trì
                    "maintenance_cycle": getattr(dev, 'maintenance_cycle', 0) or 0,
                    "last_maintenance_date": getattr(dev, 'last_maintenance_date', '') or ''
                }
                result.append(d)
            return result
        except Exception as e:
            logger.error(f"[DeviceService] Lỗi List Devices: {e}")
            return []
        finally:
            session.close()

    def create_device(self, data: dict) -> Tuple[bool, str]:
        session = SessionLocal()
        try:
            if data.get('code'):
                exists = session.query(Device).filter(Device.code == data['code'], Device.active == 1).first()
                if exists: return False, f"Mã máy '{data['code']}' đã tồn tại!"

            # Xử lý giá trị bảo trì (chấp nhận cả key cũ và mới)
            cycle = data.get('maintenance_cycle') if data.get('maintenance_cycle') is not None else data.get('maint_cycle')
            last_date = data.get('last_maintenance_date') or data.get('last_maint')

            new_dev = Device(
                id=str(uuid.uuid4()),
                name=data['name'],
                code=data.get('code'),
                model=data.get('model'),
                protocol=data.get('protocol'),
                department_id=data.get('department_id'),
                note=data.get('note'),
                connection_type=data.get('conn_type'),
                file_path=data.get('file_path'),
                ip_address=data.get('ip'),
                ip_port=data.get('port'),
                com_port=data.get('serial_port'),
                baudrate=data.get('baudrate'),
                parity=data.get('parity'),
                stop_bits=data.get('stopbits', 1),
                data_bits=data.get('data_bits', 8),
                maintenance_cycle=int(cycle or 0),
                last_maintenance_date=last_date,
                created_by=data.get('created_by'),
                active=1,
                sync_flag=1,
                created_at=datetime.datetime.now(timezone.utc),
                updated_at=datetime.datetime.now(timezone.utc)
            )

            session.add(new_dev)
            session.commit()
            return True, "Thêm thiết bị thành công!"
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()

    def update_device(self, dev_id, data: dict) -> Tuple[bool, str]:
        session = SessionLocal()
        try:
            dev = session.query(Device).filter(Device.id == str(dev_id)).first()
            if not dev: return False, "Không tìm thấy thiết bị!"

            dev.name = data['name']
            dev.code = data.get('code')
            dev.model = data.get('model')
            dev.protocol = data.get('protocol')
            dev.department_id = data.get('department_id')
            dev.note = data.get('note')
            dev.connection_type = data.get('conn_type')
            dev.file_path = data.get('file_path')
            dev.ip_address = data.get('ip')
            dev.ip_port = data.get('port')
            dev.com_port = data.get('serial_port')
            dev.baudrate = data.get('baudrate')
            dev.parity = data.get('parity')
            dev.stop_bits = data.get('stopbits', 1)
            dev.data_bits = data.get('data_bits', 8)

            cycle = data.get('maintenance_cycle') if data.get('maintenance_cycle') is not None else data.get('maint_cycle')
            last_date = data.get('last_maintenance_date') or data.get('last_maint')

            dev.maintenance_cycle = int(cycle or 0)
            dev.last_maintenance_date = last_date

            if data.get('updated_by'):
                dev.updated_by = data.get('updated_by')

            dev.sync_flag = 1
            dev.updated_at = datetime.datetime.now(timezone.utc)

            session.commit()
            return True, "Cập nhật thành công!"
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()

    def delete_device(self, dev_id) -> Tuple[bool, str]:
        session = SessionLocal()
        try:
            dev = session.query(Device).filter(Device.id == str(dev_id)).first()
            if dev:
                dev.active = 0
                dev.sync_flag = 2
                dev.updated_at = datetime.datetime.now(timezone.utc)
                session.commit()
                return True, "Đã xóa thiết bị."
            return False, "Không tìm thấy thiết bị."
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()

    # ==========================================
    # 2. LOGIC TEST KẾT NỐI (TCP/SERIAL)
    # ==========================================

    def test_connection(self, config: dict) -> Tuple[bool, str]:
        conn_type = config.get('conn_type', 'none')

        if conn_type == 'tcp':
            ip = config.get('ip')
            try:
                port = int(config.get('port'))
                with socket.create_connection((ip, port), timeout=2):
                    pass
                return True, f"Kết nối TCP {ip}:{port} OK!"
            except Exception as e:
                return False, f"Lỗi TCP: {e}"

        elif conn_type == 'serial':
            if not serial: return False, "Chưa cài thư viện pyserial."
            port = config.get('serial_port')
            if not port: return False, "Thiếu cổng COM."
            try:
                ser = serial.Serial(port, baudrate=9600, timeout=1)
                ser.close()
                return True, f"Cổng {port} OK!"
            except Exception as e:
                return False, f"Lỗi Serial: {e}"

        elif conn_type == 'file':
            path = config.get('file_path')
            if path and os.path.exists(path): return True, "Thư mục tồn tại."
            return False, f"Thư mục không tồn tại: {path}"

        return True, "Cấu hình hợp lệ."

    # ==========================================
    # 3. AUTO-SYNC LỊCH (CALENDAR)
    # ==========================================

    def get_maintenance_events(self, start_date: datetime.date, end_date: datetime.date) -> List[Dict]:
        events = []
        devices = self.list_devices()

        for dev in devices:
            cycle = dev.get('maintenance_cycle') or 0
            last_str = dev.get('last_maintenance_date')

            if cycle <= 0 or not last_str: continue

            try:
                try:
                    last_run = datetime.date.fromisoformat(last_str[:10])
                except ValueError:
                    last_run = datetime.datetime.strptime(last_str, "%d/%m/%Y").date()

                next_due = last_run + datetime.timedelta(days=cycle)

                if start_date <= next_due <= end_date:
                    today = datetime.date.today()
                    diff = (next_due - today).days

                    status = "OK"
                    if diff < 0:
                        status = "OVERDUE"
                    elif diff <= 3:
                        status = "DUE"

                    events.append({
                        "id": f"MAINT_{dev['id']}",
                        "source": "MAINTENANCE",
                        "title": f"Bảo trì: {dev['name']}",
                        "date": next_due,
                        "time_str": "Định kỳ",
                        "type": "MAINTENANCE",
                        "color": "#D83B01",
                        "icon": "🔧",
                        "desc": f"Chu kỳ: {cycle} ngày | Model: {dev['model']}",
                        "status": status
                    })
            except Exception as e:
                logger.warning(f"Lỗi parse lịch bảo trì máy {dev.get('name')}: {e}")

        return events

    # ==========================================
    # 4. NHẬN TIN NHẮN THÔ TỪ LIS (ASTM/HL7)
    # ==========================================

    def insert_device_message(self, device_id: str, direction: str, payload: Any, protocol: str = "astm"):
        session = SessionLocal()
        try:
            raw_text = ""
            if isinstance(payload, bytes):
                raw_text = payload.decode('latin-1', errors='replace')
            else:
                raw_text = str(payload)

            new_msg = DeviceMessage(
                id=str(uuid.uuid4()),
                device_id=device_id,
                raw_data=raw_text,
                status="PENDING",
            )
            session.add(new_msg)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"[DeviceService] Lỗi lưu tin nhắn: {e}")
        finally:
            session.close()

    # ==========================================
    # 5. DEVICE TEST MAPPING
    # ==========================================

    def get_test_maps(self, device_id: str) -> List[Dict]:
        session = SessionLocal()
        try:
            maps = session.query(DeviceTestMap).filter(DeviceTestMap.device_id == device_id).all()
            return [{"id": m.id, "machine_code": m.machine_code, "internal_code": m.internal_code} for m in maps]
        finally:
            session.close()

    def add_test_map(self, device_id, machine_code, internal_code):
        session = SessionLocal()
        try:
            exists = session.query(DeviceTestMap).filter(
                DeviceTestMap.device_id == device_id,
                DeviceTestMap.machine_code == machine_code
            ).first()
            if exists: return False, "Mã máy này đã được ánh xạ!"

            new_map = DeviceTestMap(
                id=str(uuid.uuid4()),
                device_id=device_id,
                machine_code=machine_code,
                internal_code=internal_code
            )
            session.add(new_map)
            session.commit()
            return True, "Đã thêm ánh xạ."
        except Exception as e:
            return False, str(e)
        finally:
            session.close()

    def delete_test_map(self, map_id):
        session = SessionLocal()
        try:
            m = session.query(DeviceTestMap).filter(DeviceTestMap.id == map_id).first()
            if m:
                session.delete(m)
                session.commit()
                return True
            return False
        finally:
            session.close()