# -*- coding: utf-8 -*-
"""
app/services/sync_service.py
(BẢN HOÀN THIỆN - LAN ARCHITECTURE)
Service đảm nhiệm logic đồng bộ TRỰC TIẾP giữa SQLite (Máy trạm) và PostgreSQL (Máy chủ).
Tích hợp Incremental Pull, Versioning và Xóa đồng bộ (Ghost Cleaning).
"""
import os
import json
import datetime
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database_orm import SessionLocal, engine as local_engine
from app.core.path_manager import PathManager

# Import các Models chính
from app.models.catalog_models import CatalogLot, CatalogAnalyte
from app.models.iqc_models import IQCRun, IQCResult
from app.models.sync_models import SyncState
from app.models.core_models import Department, User, AuditLog

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self):
        # Thiết bị Local hiện tại
        self.device_id = "device_local_temp_01"

        # Ánh xạ tên bảng với Model Local (Chung một class cho cả SQLite và PostgreSQL)
        self.model_mapping = {
            "department_v2": Department,
            "users_v2": User,
            "catalog_lot_v2": CatalogLot,
            "catalog_analyte_v2": CatalogAnalyte,
            "iqc_run_v2": IQCRun,
            "iqc_result_v2": IQCResult,
            "audit_log_v2": AuditLog
        }

    def _get_pg_session(self):
        """Đọc cấu hình và tạo Session kết nối trực tiếp đến PostgreSQL"""
        config_path = PathManager.get_config_path()
        if not os.path.exists(config_path):
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            pg_cfg = cfg.get("postgresql", {})
            host = pg_cfg.get("host")
            port = pg_cfg.get("port", "5432")
            dbname = pg_cfg.get("dbname")
            user = pg_cfg.get("user")
            pwd = pg_cfg.get("password")

            if not host or not dbname or not user:
                return None

            conn_str = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}"
            # connect_timeout=5 để không bị treo phần mềm nếu rớt mạng LAN
            pg_engine = create_engine(conn_str, connect_args={"connect_timeout": 5})

            # [FIX] Tự động tạo toàn bộ bảng trên PostgreSQL nếu chưa có
            from app.core.database_orm import Base
            try:
                Base.metadata.create_all(bind=pg_engine)
            except Exception as e:
                logger.error(f"Lỗi tạo bảng trên PostgreSQL: {e}")

            PGSession = sessionmaker(bind=pg_engine)
            return PGSession()

        except Exception as e:
            logger.error(f"Lỗi khởi tạo session PostgreSQL: {e}")
            return None

    def _record_to_dict(self, record):
        """Chuyển SQLAlchemy Object thành Dictionary (Bỏ qua ép kiểu ISO 8601 vì SQLAlchemy tự map Date)"""
        d = {}
        for column in record.__table__.columns:
            d[column.name] = getattr(record, column.name)
        return d

    # --- 1. PUSH (ĐẨY TỪ MÁY TRẠM LÊN MÁY CHỦ) ---
    def push_changes(self):
        """Gom dữ liệu sync_flag != 0 ở SQLite và Merge trực tiếp vào PostgreSQL"""
        pg_session = self._get_pg_session()
        if not pg_session:
            return False, 0, ["Chưa cấu hình PostgreSQL LAN"]

        local_session = SessionLocal()
        total_pushed = 0
        errors = []

        try:
            for table_name, model_class in self.model_mapping.items():
                pending = local_session.query(model_class).filter(model_class.sync_flag != 0).all()
                if pending:
                    for record in pending:
                        data = self._record_to_dict(record)
                        data['sync_flag'] = 0  # Khi đẩy lên Server, coi như đã đồng bộ an toàn

                        # Sử dụng quyền năng merge() của SQLAlchemy để đối chiếu ID (Thêm mới hoặc Cập nhật)
                        pg_instance = model_class(**data)
                        pg_session.merge(pg_instance)

                        # Hạ cờ ở máy Local
                        record.sync_flag = 0

                    total_pushed += len(pending)

            # Phải thành công cả 2 bên thì mới Commit
            pg_session.commit()
            local_session.commit()
            return True, total_pushed, errors

        except Exception as e:
            pg_session.rollback()
            local_session.rollback()
            logger.error(f"❌ [DB-PUSH ERROR] Lỗi đồng bộ lên Máy chủ: {e}")
            return False, 0, [str(e)]
        finally:
            pg_session.close()
            local_session.close()

    # --- 2. PULL (KÉO TỪ MÁY CHỦ VỀ MÁY TRẠM - INCREMENTAL) ---
    def pull_changes(self):
        """Chỉ kéo dữ liệu thay đổi từ Server dựa trên mốc SyncState"""
        pg_session = self._get_pg_session()
        if not pg_session:
            return False, 0, ["Chưa cấu hình PostgreSQL LAN"]

        local_session = SessionLocal()
        total_pulled = 0
        errors = []

        try:
            for table_name, model_class in self.model_mapping.items():
                state = local_session.query(SyncState).filter_by(
                    table_name=table_name,
                    device_id=self.device_id
                ).first()

                if not state:
                    state = SyncState(
                        device_id=self.device_id,
                        table_name=table_name,
                        last_pull_time=datetime.datetime(2000, 1, 1)
                    )
                    local_session.add(state)

                last_pull_time = state.last_pull_time
                current_pull_start = datetime.datetime.now()

                # Lấy dữ liệu thay đổi từ PostgreSQL
                if hasattr(model_class, 'updated_at'):
                    server_records = pg_session.query(model_class).filter(model_class.updated_at > last_pull_time).all()
                else:
                    server_records = pg_session.query(model_class).all()

                if server_records:
                    # Lấy tên cột Primary Key (thường là 'id')
                    pk_name = model_class.__mapper__.primary_key[0].name

                    for record in server_records:
                        data = self._record_to_dict(record)
                        data['sync_flag'] = 0

                        is_deleted = data.get('is_deleted', 0)
                        record_id = data.get(pk_name)

                        if is_deleted == 1:
                            # Ghost Cleaning: Nếu máy chủ đánh dấu xóa, xóa ở Local
                            existing = local_session.query(model_class).filter(
                                getattr(model_class, pk_name) == record_id).first()
                            if existing:
                                local_session.delete(existing)
                        else:
                            # Ghi đè hoặc thêm mới vào Local
                            local_instance = model_class(**data)
                            local_session.merge(local_instance)

                        total_pulled += 1

                # Cập nhật mốc thời gian kéo thành công
                state.last_pull_time = current_pull_start

            local_session.commit()
            return True, total_pulled, errors

        except Exception as e:
            local_session.rollback()
            logger.error(f"❌ [DB-PULL ERROR] Lỗi kéo dữ liệu từ Máy chủ: {e}")
            return False, 0, [str(e)]
        finally:
            pg_session.close()
            local_session.close()

    # --- 3. FORCE RESYNC (ÉP TẢI LẠI TOÀN BỘ) ---
    def force_resync_all(self):
        """Xóa mốc SyncState để tải lại toàn bộ từ PostgreSQL"""
        local_session = SessionLocal()
        try:
            logger.info("🔄 [RESET] Đang xóa mốc đồng bộ để Force Resync...")
            local_session.query(SyncState).filter_by(device_id=self.device_id).delete()
            local_session.commit()
            return self.pull_changes()
        except Exception as e:
            local_session.rollback()
            return False, 0, [str(e)]
        finally:
            local_session.close()