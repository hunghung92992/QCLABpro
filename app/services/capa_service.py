# -*- coding: utf-8 -*-
"""
app/services/capa_service.py
(CENTRALIZED CAPA SERVICE - ISO 15189 COMPLIANT)
BẢN CHUẨN: Đã đồng bộ 100% với cấu trúc Database thực tế.
Tích hợp lưu file đính kèm an toàn qua PathManager.
"""

import uuid
import shutil
import os
import datetime as dt
from typing import Optional, Dict, List, Any
from sqlalchemy import text
from app.core.database_orm import engine

# [FIX] Import PathManager để lưu file an toàn, tránh lỗi Read-only ở Program Files
from app.core.path_manager import PathManager


class CapaService:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        """Khởi tạo các bảng CAPA và Đính kèm"""
        with engine.connect() as conn:
            # 1. Bảng CAPA Chính
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_capas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guid TEXT UNIQUE,
                    capa_id TEXT UNIQUE,         
                    result_id INTEGER,           
                    source TEXT,                
                    title TEXT,                 
                    risk_level TEXT,            
                    status TEXT,                
                    owner TEXT,                 
                    due_date TEXT,              
                    description TEXT,           
                    root_cause TEXT,            
                    correction TEXT,            
                    corrective TEXT,        
                    verify_evidence TEXT,   
                    test_info TEXT,             
                    ts_utc TEXT,                
                    closed_at TEXT,
                    approved_by TEXT,
                    approval_date TEXT,
                    is_locked INTEGER DEFAULT 0
                )
            """))

            # 2. [FIX] Bảng File Đính kèm
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_capa_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    capa_id TEXT,
                    file_name TEXT,
                    file_path TEXT,
                    upload_date TEXT,
                    FOREIGN KEY(capa_id) REFERENCES audit_capas(capa_id) ON DELETE CASCADE
                )
            """))
            conn.commit()

    def create_capa_entry(self, **data) -> bool:
        """Tạo mới hồ sơ CAPA"""
        new_guid = str(uuid.uuid4())
        readable_id = self._generate_readable_id()
        ts_now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO audit_capas (
                        guid, capa_id, result_id, source, title, description, 
                        risk_level, status, owner, due_date, root_cause, 
                        correction, corrective, verify_evidence, ts_utc
                    ) VALUES (
                        :guid, :capa_id, :result_id, :source, :title, :description, 
                        :risk_level, :status, :owner, :due_date, :root_cause, 
                        :correction, :corrective, :verify_evidence, :ts_utc
                    )
                """), {
                    "guid": new_guid,
                    "capa_id": readable_id,
                    "result_id": data.get("result_id"),
                    "source": data.get("source", "System"),
                    "title": data.get("title", "Sự cố không tên"),
                    "description": data.get("description", ""),
                    "risk_level": data.get("risk_level", "Medium"),
                    "status": data.get("status", "Open"),
                    "owner": data.get("owner", "Unassigned"),
                    "due_date": data.get("due_date", ""),
                    "root_cause": data.get("root_cause", ""),
                    "correction": data.get("correction", ""),
                    "corrective": data.get("corrective", ""),
                    "verify_evidence": data.get("verify_evidence", ""),
                    "ts_utc": ts_now
                })
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Lỗi Create CAPA: {e}")
            return False

    def update_capa(self, data: dict) -> bool:
        """CẬP NHẬT: Lưu trực tiếp dữ liệu từ UI vào DB"""
        ts_now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status = data.get("status", "Open")
        closed_at = ts_now if status == "Closed" else None

        sql = text("""
            UPDATE audit_capas 
            SET title = :title,
                source = :source,
                risk_level = :risk_level,
                owner = :owner,
                due_date = :due_date,
                description = :description,
                root_cause = :root_cause,
                correction = :correction,
                corrective = :corrective, 
                verify_evidence = :verify_evidence,
                status = :status,
                closed_at = :closed_at
            WHERE capa_id = :capa_id
        """)

        # [FIX] Đảm bảo trích xuất an toàn từ dict để tránh lỗi KeyError của SQLAlchemy
        safe_params = {
            "title": data.get("title", ""),
            "source": data.get("source", ""),
            "risk_level": data.get("risk_level", ""),
            "owner": data.get("owner", ""),
            "due_date": data.get("due_date", ""),
            "description": data.get("description", ""),
            "root_cause": data.get("root_cause", ""),
            "correction": data.get("correction", ""),
            "corrective": data.get("corrective", ""),
            "verify_evidence": data.get("verify_evidence", ""),
            "status": status,
            "closed_at": closed_at,
            "capa_id": data.get("capa_id")
        }

        try:
            with engine.connect() as conn:
                conn.execute(sql, safe_params)
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Lỗi SQL Update CAPA: {e}")
            return False

    def get_all_capas(self, status: str = None) -> List[Dict]:
        """Lấy danh sách CAPA từ DB"""
        with engine.connect() as conn:
            query = "SELECT * FROM audit_capas"
            params = {}
            if status and status != "Tất cả trạng thái":
                query += " WHERE status = :st"
                params["st"] = status
            query += " ORDER BY ts_utc DESC"

            res = conn.execute(text(query), params)
            return [dict(row._mapping) for row in res]

    def check_existing_capa(self, result_id: int) -> Optional[str]:
        if not result_id: return None
        with engine.connect() as conn:
            res = conn.execute(text("SELECT capa_id FROM audit_capas WHERE result_id = :rid"), {"rid": result_id})
            return res.scalar()

    def _generate_readable_id(self) -> str:
        date_prefix = dt.datetime.now().strftime("%Y%m%d")
        with engine.connect() as conn:
            res = conn.execute(
                text("SELECT COUNT(*) FROM audit_capas WHERE capa_id LIKE :p"),
                {"p": f"CP-{date_prefix}-%"}
            )
            count = res.scalar() or 0
            return f"CP-{date_prefix}-{str(count + 1).zfill(3)}"

    def get_detailed_stats(self) -> Dict[str, Any]:
        with engine.connect() as conn:
            res_status = conn.execute(text("SELECT status, COUNT(*) FROM audit_capas GROUP BY status"))
            status_map = {row[0]: row[1] for row in res_status}

            res_source = conn.execute(text("SELECT source, COUNT(*) FROM audit_capas GROUP BY source"))
            source_map = {row[0]: row[1] for row in res_source}

            today = dt.date.today().strftime("%Y-%m-%d")
            res_overdue = conn.execute(text(
                "SELECT capa_id, title, due_date, owner FROM audit_capas "
                "WHERE status != 'Closed' AND due_date < :today"
            ), {"today": today})
            overdue_list = [dict(row._mapping) for row in res_overdue]

            return {"status": status_map, "source": source_map, "overdue": overdue_list}

    def approve_capa(self, capa_id: str, approver_name: str) -> bool:
        return self.approve_capa_record(capa_id, approver_name)

    def approve_capa_record(self, capa_id: str, current_user: str) -> bool:
        today = dt.date.today().strftime("%Y-%m-%d")
        with engine.connect() as conn:
            try:
                conn.execute(text("""
                    UPDATE audit_capas SET approved_by = :u, approval_date = :d, is_locked = 1, status = 'Closed'
                    WHERE capa_id = :id
                """), {"u": current_user, "d": today, "id": capa_id})
                conn.commit()
                return True
            except Exception as e:
                print(f"❌ Lỗi Approve: {e}")
                return False

    def add_attachment(self, capa_id: str, source_path: str) -> bool:
        """[FIX] Lưu file vào thư mục AppData/Local thay vì ổ đĩa C cài đặt"""
        if not os.path.exists(source_path): return False
        try:
            # Sử dụng thư mục gốc an toàn từ PathManager
            base_app_dir = PathManager.get_project_root()
            attachment_dir = os.path.join(base_app_dir, "Attachments", str(capa_id))

            if not os.path.exists(attachment_dir):
                os.makedirs(attachment_dir, exist_ok=True)

            file_name = os.path.basename(source_path)
            dest_path = os.path.join(attachment_dir, file_name)

            # Copy file
            shutil.copy2(source_path, dest_path)

            # Lưu đường dẫn tương đối vào DB
            relative_path = os.path.join("Attachments", str(capa_id), file_name)
            today = dt.date.today().strftime("%Y-%m-%d")

            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO audit_capa_attachments (capa_id, file_name, file_path, upload_date)
                    VALUES (:id, :name, :path, :date)
                """), {"id": capa_id, "name": file_name, "path": relative_path, "date": today})
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ Lỗi đính kèm file (add_attachment): {e}")
            return False

    def get_attachments(self, capa_id: str):
        with engine.connect() as conn:
            res = conn.execute(text("SELECT * FROM audit_capa_attachments WHERE capa_id = :id"), {"id": capa_id})
            return [dict(row._mapping) for row in res]

    def get_overdue_count(self) -> int:
        today = dt.date.today().strftime("%Y-%m-%d")
        with engine.connect() as conn:
            query = text("SELECT COUNT(*) FROM audit_capas WHERE due_date < :today AND status != 'Closed'")
            return conn.execute(query, {"today": today}).scalar() or 0