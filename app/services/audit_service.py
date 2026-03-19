# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime
from typing import List, Dict

# Import Database
from sqlalchemy import desc
from app.core.database_orm import SessionLocal
from app.models.core_models import AuditLog


class AuditService:
    def __init__(self):
        # Không cần khởi tạo gì đặc biệt vì SessionLocal được gọi mỗi khi dùng
        pass

    def log_action(self, actor: str, action: str, target: str,
                   before: dict = None, after: dict = None, note: str = ""):
        """Ghi lại một hành động vào nhật ký (Đã fix lỗi ID và Tiếng Việt)."""
        session = SessionLocal()
        try:
            # Chuyển dict sang JSON string với ensure_ascii=False để đọc được tiếng Việt
            before_json = json.dumps(before, ensure_ascii=False) if before else None
            after_json = json.dumps(after, ensure_ascii=False) if after else None

            # Sử dụng UUID để tránh trùng lặp và lỗi Null ID
            new_log = AuditLog(
                id=str(uuid.uuid4()),
                ts_utc=datetime.now(),  # Sử dụng thời gian hiện tại của hệ thống
                actor=str(actor),
                action=str(action),
                target=str(target),
                before_json=before_json,
                after_json=after_json,
                note=str(note)
            )

            session.add(new_log)
            session.commit()
            return True

        except Exception as e:
            print(f"❌ [AuditService ERROR] Không thể ghi log: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_recent_logs(self, limit=1000) -> List[Dict]:
        """Lấy danh sách nhật ký mới nhất, chuyển đổi sang Dict cho UI."""
        session = SessionLocal()
        try:
            # Sắp xếp giảm dần theo thời gian (mới nhất lên đầu)
            logs = session.query(AuditLog) \
                .order_by(desc(AuditLog.ts_utc)) \
                .limit(limit) \
                .all()

            result = []
            for log in logs:
                # Format datetime sang string (ISO format) để UI dễ xử lý (tránh lỗi TypeError)
                ts_str = log.ts_utc.isoformat() if isinstance(log.ts_utc, datetime) else str(log.ts_utc)

                log_dict = {
                    "id": log.id,
                    "ts_utc": ts_str,
                    "actor": log.actor,
                    "action": log.action,
                    "target": log.target,
                    "before_json": log.before_json,
                    "after_json": log.after_json,
                    "note": log.note
                }
                result.append(log_dict)
            return result
        except Exception as e:
            print(f"❌ [AuditService ERROR] Không thể đọc log: {e}")
            return []
        finally:
            session.close()

    def get_logs_by_filter(self, actor=None, action=None, date_str=None) -> List[Dict]:
        """Lọc log nâng cao từ phía Database."""
        session = SessionLocal()
        try:
            query = session.query(AuditLog)

            if actor:
                query = query.filter(AuditLog.actor == actor)
            if action:
                query = query.filter(AuditLog.action.ilike(f"%{action}%"))

            # Nếu có date_str (YYYY-MM-DD), lọc các bản ghi trong ngày đó
            if date_str:
                query = query.filter(AuditLog.ts_utc.like(f"{date_str}%"))
            limit = 50  # <--- Khai báo biến limit ở đây
            logs = query.order_by(desc(AuditLog.ts_utc)).limit(limit).all()

            # Chuyển đổi list object sang list dict
            result = []
            for log in logs:
                d = {k: v for k, v in log.__dict__.items() if k != '_sa_instance_state'}
                if isinstance(d.get('ts_utc'), datetime):
                    d['ts_utc'] = d['ts_utc'].isoformat()
                result.append(d)
            return result
        except Exception as e:
            print(f"❌ [AuditService ERROR] Filter log error: {e}")
            return []
        finally:
            session.close()