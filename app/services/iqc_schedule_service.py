# -*- coding: utf-8 -*-
"""
app/services/iqc_schedule_service.py
Dịch vụ lõi: Quản lý Lịch Nội kiểm (IQC Schedule).
(PHIÊN BẢN CHUẨN ORM - SẠCH BÓNG SQLITE3 THUẦN)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
import datetime as _dt

# 🌟 Dùng SQLAlchemy và SessionLocal chuẩn
from sqlalchemy import text
from app.core.database_orm import SessionLocal


@dataclass
class IQCScheduleRow:
    id: int
    department_id: Optional[str]  # Đổi thành str để hỗ trợ chuẩn UUID mới
    device_id: Optional[str]
    test_code: str
    level: int
    freq: str  # 'daily' | 'weekly' | 'monthly' | 'ndays'
    every_n: int
    grace_days: int
    hard_lock: int
    last_run: Optional[str]  # YYYY-MM-DD
    note: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    due_date: Optional[str] = None
    lock_input: Optional[int] = 0


# --- Các hàm tính toán (Helpers GIỮ NGUYÊN HOÀN TOÀN) ---

def _parse_date(d: Optional[str]) -> Optional[_dt.date]:
    if not d: return None
    try:
        return _dt.date.fromisoformat(d)
    except ValueError:
        for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return _dt.datetime.strptime(d, fmt).date()
            except Exception:
                pass
    return None


def _date_to_str(d: Optional[_dt.date]) -> Optional[str]:
    return d.isoformat() if d else None


def _add_months(d: _dt.date, months: int) -> _dt.date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    try:
        return d.replace(year=y, month=m)
    except ValueError:
        if m == 12:
            next_month = d.replace(year=y + 1, month=1, day=1)
        else:
            next_month = d.replace(year=y, month=m + 1, day=1)
        return next_month - _dt.timedelta(days=1)


def compute_next_due(last_run: Optional[str], freq: str, every_n: int,
                     today: Optional[_dt.date] = None) -> _dt.date:
    today_date = today or _dt.date.today()
    if not last_run: return today_date
    lr = _parse_date(last_run)
    if not lr: return today_date

    f = (freq or "ndays").lower()
    n = max(1, int(every_n or 1))

    if f == "daily":
        due = lr + _dt.timedelta(days=n)
    elif f == "weekly":
        due = lr + _dt.timedelta(weeks=n)
    elif f == "monthly":
        due = _add_months(lr, n)
    elif f == "ndays":
        due = lr + _dt.timedelta(days=n)
    else:
        due = lr + _dt.timedelta(days=1)
    return due


def eval_status(next_due: _dt.date, grace_days: int,
                today: Optional[_dt.date] = None) -> str:
    today_date = today or _dt.date.today()
    if next_due > today_date: return "ok"

    days_past = (today_date - next_due).days
    if 0 <= days_past <= max(0, int(grace_days or 0)): return "due"
    return "overdue"


# --- Service Class (ORM REFACTOR) ---

class IQCScheduleService:
    def __init__(self):
        self._ensure_table_exists()

    def _get_db(self):
        return SessionLocal()

    def _ensure_table_exists(self):
        """Tạo bảng bằng SessionLocal an toàn"""
        create_sql = text("""
        CREATE TABLE IF NOT EXISTS iqc_schedule_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id TEXT,
            device_id TEXT,
            test_code TEXT NOT NULL,
            level INTEGER NOT NULL,
            freq TEXT DEFAULT 'daily',
            every_n INTEGER DEFAULT 1,
            grace_days INTEGER DEFAULT 0,
            hard_lock INTEGER DEFAULT 0,
            last_run TEXT,
            start_date TEXT,
            end_date TEXT,
            due_date TEXT,
            lock_input INTEGER DEFAULT 0,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        db = self._get_db()
        try:
            db.execute(create_sql)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ [IQCScheduleService INIT ERROR] Không thể tạo bảng: {e}")
        finally:
            db.close()

    def _row_to_dataclass(self, row_mapping) -> IQCScheduleRow:
        data = dict(row_mapping)
        return IQCScheduleRow(
            id=data.get("id"),
            department_id=data.get("department_id"),
            device_id=data.get("device_id"),
            test_code=data.get("test_code"),
            level=data.get("level"),
            freq=data.get("freq"),
            every_n=data.get("every_n"),
            grace_days=data.get("grace_days"),
            hard_lock=data.get("hard_lock"),
            last_run=data.get("last_run"),
            note=data.get("note"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            due_date=data.get("due_date"),
            lock_input=data.get("lock_input")
        )

    # --- CRUD ---

    def upsert(self, department_id: Optional[str], device_id: Optional[str],
               test_code: str, level: int, freq: str = "ndays", every_n: int = 1,
               grace_days: int = 0, hard_lock: int = 0, note: str = "") -> int:
        db = self._get_db()
        try:
            # Dùng tham số đặt tên (Named Parameters) để tránh lỗi SQL Injection
            sql_check = text("""
                SELECT id FROM iqc_schedule_config 
                WHERE COALESCE(department_id, 'UNKNOWN') = COALESCE(:dept, 'UNKNOWN') 
                  AND COALESCE(device_id, 'UNKNOWN') = COALESCE(:dev, 'UNKNOWN') 
                  AND test_code = :tc 
                  AND level = :lvl
            """)
            params = {"dept": department_id, "dev": device_id, "tc": test_code, "lvl": int(level)}
            row = db.execute(sql_check, params).fetchone()

            if row:
                sql_upd = text("""
                    UPDATE iqc_schedule_config
                    SET freq=:freq, every_n=:en, grace_days=:gd, hard_lock=:hl, note=:note, updated_at=CURRENT_TIMESTAMP
                    WHERE id=:id
                """)
                db.execute(sql_upd,
                           {"freq": freq, "en": int(every_n), "gd": int(grace_days), "hl": int(hard_lock), "note": note,
                            "id": row[0]})
                db.commit()
                return int(row[0])
            else:
                sql_ins = text("""
                    INSERT INTO iqc_schedule_config(department_id, device_id, test_code, level, freq, every_n, grace_days, hard_lock, note)
                    VALUES (:dept, :dev, :tc, :lvl, :freq, :en, :gd, :hl, :note)
                """)
                # Lấy ID vừa insert (chỉ hoạt động với SQLite/MySQL)
                result = db.execute(sql_ins,
                                    {"dept": department_id, "dev": device_id, "tc": test_code, "lvl": int(level),
                                     "freq": freq, "en": int(every_n), "gd": int(grace_days), "hl": int(hard_lock),
                                     "note": note})
                db.commit()
                return result.lastrowid
        except Exception as e:
            db.rollback()
            print(f"❌ [IQCScheduleService ERROR] upsert: {e}")
            raise e
        finally:
            db.close()

    def mark_run_today(self, department_id: Optional[str], device_id: Optional[str],
                       test_code: str, level: int, date: Optional[str] = None) -> None:
        run_date = date or _date_to_str(_dt.date.today())
        db = self._get_db()
        try:
            sql_upd = text("""
                UPDATE iqc_schedule_config 
                SET last_run=:rd 
                WHERE COALESCE(department_id, 'UNKNOWN') = COALESCE(:dept, 'UNKNOWN') 
                  AND COALESCE(device_id, 'UNKNOWN') = COALESCE(:dev, 'UNKNOWN') 
                  AND test_code=:tc 
                  AND level=:lvl
            """)
            params = {"rd": run_date, "dept": department_id, "dev": device_id, "tc": test_code, "lvl": int(level)}
            res = db.execute(sql_upd, params)

            if res.rowcount == 0:
                sql_ins = text("""
                    INSERT INTO iqc_schedule_config(department_id, device_id, test_code, level, last_run, freq)
                    VALUES (:dept, :dev, :tc, :lvl, :rd, 'daily')
                """)
                db.execute(sql_ins, params)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ [IQCScheduleService ERROR] mark_run_today: {e}")
        finally:
            db.close()

    def get_schedule(self, department_id: Optional[str], device_id: Optional[str],
                     test_code: str, level: int) -> Optional[IQCScheduleRow]:
        db = self._get_db()
        try:
            sql = text("""
                SELECT * FROM iqc_schedule_config 
                WHERE COALESCE(department_id, 'UNKNOWN') = COALESCE(:dept, 'UNKNOWN') 
                  AND COALESCE(device_id, 'UNKNOWN') = COALESCE(:dev, 'UNKNOWN') 
                  AND test_code=:tc 
                  AND level=:lvl
            """)
            params = {"dept": department_id, "dev": device_id, "tc": test_code, "lvl": int(level)}
            r = db.execute(sql, params).fetchone()

            return self._row_to_dataclass(r._mapping) if r else None
        except Exception:
            return None
        finally:
            db.close()

    # --- LOGIC QUAN TRỌNG CHO LỊCH ---

    def compute_lock_status(self, department_id: Optional[str], device_id: Optional[str],
                            test_code: str, level: int,
                            today: Optional[_dt.date] = None,
                            preloaded_row: Optional[IQCScheduleRow] = None) -> Tuple[str, Optional[str], bool]:
        """
        Đã tối ưu: Truyền preloaded_row vào để tránh query lại DB nếu đã có sẵn dữ liệu.
        """
        row = preloaded_row or self.get_schedule(department_id, device_id, test_code, level)
        today_date = today or _dt.date.today()

        if not row or not row.last_run:
            return "due", _date_to_str(today_date), False

        next_due_date = compute_next_due(row.last_run, row.freq, row.every_n, today=today_date)
        status = eval_status(next_due_date, row.grace_days, today=today_date)

        is_locked = True if (status == "overdue" and row.hard_lock) else False
        return status, _date_to_str(next_due_date), is_locked

    def list_pending_tasks(self, for_date: _dt.date) -> List[Dict[str, Any]]:
        tasks = []
        db = self._get_db()
        try:
            # Dùng _mapping để lấy dữ liệu an toàn dưới dạng Dict
            configs = db.execute(text("SELECT * FROM iqc_schedule_config")).fetchall()

            for r in configs:
                row = self._row_to_dataclass(r._mapping)

                # Truyền luôn row vào để tiết kiệm query
                status, next_due_str, _ = self.compute_lock_status(
                    row.department_id, row.device_id, row.test_code, row.level, for_date, preloaded_row=row
                )

                if status in ['due', 'overdue']:
                    tasks.append({
                        "test": row.test_code,
                        "level": row.level,
                        "status": status,
                        "due_date": next_due_str,
                        "device_id": row.device_id,
                        "department_id": row.department_id
                    })
        except Exception as e:
            print(f"❌ [IQCScheduleService] List pending error: {e}")
        finally:
            db.close()

        return tasks