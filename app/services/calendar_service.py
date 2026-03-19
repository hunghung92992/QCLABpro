# -*- coding: utf-8 -*-
"""
app/services/calendar_service.py
Dịch vụ Lịch Tổng Hợp: Trái tim quản lý thời gian của phòng Lab.
(FULL INTEGRATION: EQA + IQC + MAINTENANCE + MANUAL - ORM HYBRID VERSION)
"""
import datetime as dt
from typing import List, Dict
from sqlalchemy import text

# 🌟 Dùng SessionLocal chuẩn của kiến trúc mới
from app.core.database_orm import SessionLocal

# Định nghĩa màu sắc chuẩn
EVENT_TYPES = {
    "EQA": {"label": "Ngoại kiểm (EQA)", "color": "#C50F1F", "icon": "🔴"},
    "IQC": {"label": "Nội kiểm (IQC)", "color": "#0078D4", "icon": "📉"},
    "MAINTENANCE": {"label": "Bảo trì", "color": "#D83B01", "icon": "🟠"},
    "ADMIN": {"label": "Họp/Đào tạo", "color": "#8764B8", "icon": "🔵"},
    "GENERAL": {"label": "Chung", "color": "#737373", "icon": "📅"}
}


class CalendarService:
    def __init__(self):
        self._db = SessionLocal()

        # 1. Kết nối EQA Service
        try:
            from app.services.eqa_service import EQAService
            self.eqa_service = EQAService()
        except ImportError:
            self.eqa_service = None

        # 2. Kết nối IQC Service
        try:
            from app.services.iqc_schedule_service import IQCScheduleService
            self.iqc_service = IQCScheduleService()
        except ImportError:
            self.iqc_service = None

        # 3. Kết nối Equipment Service (Bảo trì)
        try:
            from app.services.device_service import  DeviceService
            self.maint_service =  DeviceService()
        except ImportError:
            self.maint_service = None

        self._ensure_table()

    def _ensure_table(self):
        """Tạo bảng phụ cho lịch thủ công (Tương lai nên chuyển thành Model ORM)"""
        try:
            self._db.execute(text("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    event_type TEXT,
                    start_date TEXT, start_time TEXT, end_time TEXT, description TEXT
                )
            """))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            print(f"⚠️ Lỗi tạo bảng calendar_events: {e}")

    def get_all_events(self, start_date: dt.date, end_date: dt.date, filter_types: List[str] = None) -> List[Dict]:
        all_events = []

        # 1. Manual Events (Sự kiện thủ công)
        if not filter_types or any(t in filter_types for t in ["GENERAL", "ADMIN"]):
            all_events.extend(self._get_manual_events(start_date, end_date))

        # 2. EQA Events (Auto-Sync)
        if self.eqa_service and (not filter_types or "EQA" in filter_types):
            all_events.extend(self._get_eqa_events(start_date, end_date))

        # 3. IQC Events (Auto-Sync - Chỉ hiện hôm nay để nhắc nhở)
        today = dt.date.today()
        if self.iqc_service and (not filter_types or "IQC" in filter_types):
            if start_date <= today <= end_date:
                pending = self.iqc_service.list_pending_tasks(today)
                if pending:
                    count = len(pending)
                    desc_list = [f"{t.get('test', '')} L{t.get('level', '')}" for t in pending[:4]]
                    if count > 4: desc_list.append(f"... (+{count - 4})")

                    all_events.append({
                        "id": "IQC_TODAY", "source": "IQC",
                        "title": f"Cần chạy IQC ({count} mẫu)",
                        "date": today, "time_str": "Đầu giờ",
                        "type": "IQC",
                        "color": EVENT_TYPES["IQC"]["color"],
                        "icon": EVENT_TYPES["IQC"]["icon"],
                        "desc": ", ".join(desc_list),
                        "status": "PENDING"
                    })

        # 4. Maintenance Events (Auto-Sync - Bảo trì thiết bị)
        if self.maint_service and (not filter_types or "MAINTENANCE" in filter_types):
            maint_events = self.maint_service.get_maintenance_events(start_date, end_date)
            all_events.extend(maint_events)

        return sorted(all_events, key=lambda x: (x['date'], x.get('time_str', '')))

    def _get_manual_events(self, start, end) -> List[Dict]:
        s_str, e_str = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        events = []
        try:
            sql = text("SELECT * FROM calendar_events WHERE start_date BETWEEN :start AND :end")
            rows = self._db.execute(sql, {"start": s_str, "end": e_str}).fetchall()

            for r in rows:
                # 🌟 SỬ DỤNG DICTIONARY MAPPING THAY VÌ INDEX RỦI RO
                row = r._mapping
                etype = row['event_type'] if row['event_type'] in EVENT_TYPES else "GENERAL"
                events.append({
                    "id": row['id'],
                    "source": "MANUAL",
                    "title": row['title'],
                    "date": dt.date.fromisoformat(row['start_date']),
                    "time_str": f"{row['start_time']} - {row['end_time']}",
                    "type": etype,
                    "color": EVENT_TYPES[etype]["color"],
                    "icon": EVENT_TYPES[etype]["icon"],
                    "desc": row['description']
                })
        except Exception as e:
            print(f"❌ [Calendar] Get Manual Error: {e}")
        return events

    def _get_eqa_events(self, start, end) -> List[Dict]:
        events = []
        try:
            years = set([start.year, end.year])
            for y in years:
                tasks = self.eqa_service.list_tasks(y)
                if not tasks: continue

                for t in tasks:
                    if not t.get("due_date"): continue
                    due = dt.date.fromisoformat(t["due_date"])

                    if start <= due <= end:
                        is_done = t.get("status") == "DONE"
                        events.append({
                            "id": t["id"], "source": "EQA",
                            "title": f"Nộp EQA: {t.get('program_name', 'Chưa rõ')}",
                            "date": due, "time_str": "Hạn chót",
                            "type": "EQA",
                            "color": "#107C10" if is_done else EVENT_TYPES["EQA"]["color"],
                            "icon": "✅" if is_done else EVENT_TYPES["EQA"]["icon"],
                            "desc": f"Mẫu: {t.get('sample_code', '')} | Máy: {t.get('device_name', '')}",
                            "status": t.get("status")
                        })
        except Exception as e:
            print(f"❌ [Calendar] Get EQA Error: {e}")
        return events

    def add_event(self, data):
        try:
            sql = text("""
                INSERT INTO calendar_events 
                (title, event_type, start_date, start_time, end_time, description) 
                VALUES (:title, :type, :date, :start, :end, :desc)
            """)
            self._db.execute(sql, {
                "title": data['title'], "type": data['type'],
                "date": data['date'], "start": data['start'],
                "end": data['end'], "desc": data['desc']
            })
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            print(f"❌ [Calendar] Add Error: {e}")
            raise e

    def delete_event(self, eid):
        try:
            sql = text("DELETE FROM calendar_events WHERE id=:id")
            self._db.execute(sql, {"id": eid})
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            print(f"❌ [Calendar] Delete Error: {e}")

    def __del__(self):
        try:
            self._db.close()
        except:
            pass