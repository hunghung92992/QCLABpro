# -*- coding: utf-8 -*-
"""
app/services/eqa_service.py
Dịch vụ lõi: Quản lý Ngoại kiểm (EQA).
(UPGRADED VERSION PHASE 7.2)
- Hỗ trợ tính En-Score, SDI, %Bias (ISO 13528 & ISO 15189).
- Đánh giá xu hướng Ngoại kiểm (Trend Evaluation - Randox RIQAS).
- Hỗ trợ lấy dữ liệu Youden chuẩn.
- Lưu metadata (U_lab) vào cột note dưới dạng JSON.
"""
from sqlalchemy import text
import sqlite3
import datetime
import math
import json
from typing import List, Optional, Dict, Any, Tuple
from app.core.database_orm import SessionLocal
from app.core.database_orm import get_db_connection
import uuid


class EQAService:

    def __init__(self):
        # Service này không cần trạng thái
        pass

    # ---------- Core DB Helpers ----------
    def _con(self) -> sqlite3.Connection:
        """Sử dụng kết nối chuẩn từ core."""
        return get_db_connection()

    def _to_float(self, x: Any) -> Optional[float]:
        try:
            if x is None: return None
            s = str(x).strip().replace(",", ".")
            if s == "": return None
            return float(s)
        except Exception:
            return None

    # ---------- Logic Tính toán (Advanced ISO 15189 & 13528) ----------

    def calculate_z_score(self, result: Any, assigned: Any, sd: Any) -> Optional[float]:
        """Tính Z-score / SDI = (Lab - Group) / SD."""
        r = self._to_float(result)
        a = self._to_float(assigned)
        s = self._to_float(sd)
        if r is None or a is None or s in (None, 0.0):
            return None
        return (r - a) / s

    def calculate_percent_bias(self, result: Any, assigned: Any) -> Optional[float]:
        """Tính %Bias = (Lab - Group) / Group * 100."""
        r = self._to_float(result)
        a = self._to_float(assigned)
        if r is None or a in (None, 0.0):
            return None
        return 100.0 * (r - a) / a

    def calculate_en_score(self, result: Any, ref: Any, u_lab: Any, u_ref: Any) -> Optional[float]:
        """
        Tính En-score (Evaluation of Measurement Uncertainty).
        En = (Val_lab - Val_ref) / sqrt(U_lab^2 + U_ref^2)
        """
        r = self._to_float(result)
        a = self._to_float(ref)
        ul = self._to_float(u_lab) or 0.0
        ur = self._to_float(u_ref) or 0.0

        if r is None or a is None:
            return None

        denom = math.sqrt(ul * ul + ur * ur)
        if denom == 0.0:
            return None
        return (r - a) / denom

    def classify_z_score(self, z: Optional[float], warn: float = 2.0, fail: float = 3.0) -> Tuple[str, str]:
        """
        Trả về ('PASS'|'WARN'|'FAIL'|'NA', mã_màu_hex).
        """
        try:
            if z is None or math.isnan(z):
                return ("NA", "#DDDDDD")
            az = abs(float(z))
            if az < warn:
                return ("PASS", "#D6F5D6")  # Xanh lá
            if az < fail:
                return ("WARN", "#FFF2B2")  # Vàng
            return ("FAIL", "#F8C4C4")  # Đỏ
        except Exception:
            return ("NA", "#DDDDDD")

    def evaluate_single_result(self, lab_value: Any, peer_mean: Any, peer_sd: Any) -> Dict[str, Any]:
        """
        (MỚI) Đánh giá tổng hợp 1 kết quả Ngoại kiểm: Trả về SDI, %Bias và Phân loại ISO.
        """
        sdi = self.calculate_z_score(lab_value, peer_mean, peer_sd)
        bias_pct = self.calculate_percent_bias(lab_value, peer_mean)

        if sdi is None:
            return {"sdi": None, "bias_pct": None, "evaluation": "Invalid", "pass_fail": 0}

        abs_sdi = abs(sdi)
        if abs_sdi >= 3.0:
            evaluation = "Unacceptable"
            pass_fail = 0
        elif 2.0 < abs_sdi < 3.0:
            evaluation = "Warning"
            pass_fail = 1
        else:
            evaluation = "Acceptable"
            pass_fail = 1

        return {
            "sdi": round(sdi, 2),
            "bias_pct": round(bias_pct, 2) if bias_pct is not None else None,
            "evaluation": evaluation,
            "pass_fail": pass_fail
        }

    def evaluate_trend(self, sdi_history: List[float]) -> Dict[str, Any]:
        """
        (MỚI) Đánh giá xu hướng Ngoại kiểm qua nhiều vòng (Kỳ) theo RIQAS.
        Phát hiện sớm lỗi hệ thống dù SDI vẫn < 2.0.
        """
        valid_sdi = [s for s in sdi_history if s is not None and not math.isnan(s)]
        if len(valid_sdi) < 2:
            return {"trend_warning": False, "message": "OK", "warnings": []}

        warnings = []

        # 1. Hai kỳ liên tiếp có |SDI| > 1.5 cùng chiều
        if len(valid_sdi) >= 2:
            s1, s2 = valid_sdi[-2], valid_sdi[-1]
            if (s1 > 1.5 and s2 > 1.5) or (s1 < -1.5 and s2 < -1.5):
                warnings.append("Cảnh báo: 2 kỳ liên tiếp có |SDI| > 1.5 (Cùng chiều).")

        # 2. Bốn kỳ liên tiếp có |SDI| > 1.0 cùng chiều
        if len(valid_sdi) >= 4:
            tail = valid_sdi[-4:]
            if all(s > 1.0 for s in tail) or all(s < -1.0 for s in tail):
                warnings.append("Lỗi Hệ Thống: 4 kỳ liên tiếp có |SDI| > 1.0.")

        # 3. Xu hướng trượt (Drift) qua 4 kỳ liên tiếp
        if len(valid_sdi) >= 4:
            tail = valid_sdi[-4:]
            is_increasing = all(tail[i] < tail[i + 1] for i in range(3))
            is_decreasing = all(tail[i] > tail[i + 1] for i in range(3))
            if is_increasing or is_decreasing:
                warnings.append("Trượt (Drift): 4 kỳ liên tiếp dịch chuyển cùng 1 hướng.")

        return {
            "trend_warning": len(warnings) > 0,
            "message": " | ".join(warnings) if warnings else "OK",
            "warnings": warnings
        }

    # ---------- Danh mục (Providers, Programs, Devices) ----------
    def list_providers(self) -> List[Dict[str, Any]]:
        try:
            with self._con() as con:
                rows = list(con.execute("SELECT id, name FROM eqa_providers ORDER BY name"))
            return [{"id": r[0], "name": r[1]} for r in rows]
        except sqlite3.Error as e:
            print(f"[EQAService ERROR] list_providers: {e}")
            return []

    def list_programs(self, provider_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = "SELECT id, name, COALESCE(code,'') as code FROM eqa_programs"
        params = []
        if provider_id is not None:
            sql += " WHERE provider_id = ?"
            params.append(int(provider_id))
        sql += " ORDER BY name"

        try:
            with self._con() as con:
                rows = list(con.execute(sql, params))
            return [{"id": r[0], "name": r[1], "code": r[2]} for r in rows]
        except sqlite3.Error as e:
            print(f"[EQAService ERROR] list_programs: {e}")
            return []

    def list_eqa_devices(self, program_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = "SELECT id, name FROM eqa_device"
        params = []
        if program_id is not None:
            sql += " WHERE program_id = ?"
            params.append(int(program_id))
        sql += " ORDER BY name"

        try:
            with self._con() as con:
                rows = list(con.execute(sql, params))
            return [{"id": r[0], "name": r[1]} for r in rows]
        except sqlite3.Error as e:
            print(f"[EQAService ERROR] list_eqa_devices: {e}")
            return []

    def _upsert_eqa_device(self, con: sqlite3.Connection, name: str, program_id: Optional[int] = None,
                           provider_id: Optional[int] = None):
        if not name: return
        now = datetime.datetime.now().isoformat(timespec="seconds")
        try:
            con.execute(
                "INSERT OR IGNORE INTO eqa_device(name, program_id, provider_id, created_at) VALUES(?,?,?,?)",
                (str(name),
                 int(program_id) if program_id is not None else None,
                 int(provider_id) if provider_id is not None else None,
                 now)
            )
        except sqlite3.Error:
            pass

    # ---------- Lịch (Task Schedule) ----------
    def list_tasks(self, year: int) -> List[Dict[str, Any]]:
        session = SessionLocal()
        try:
            sql = text("""
                SELECT 
                    id, year, round_no, 
                    provider_name, program_name, sample_code, device_name,
                    assigned_to, 
                    deadline as due_date, 
                    status, 
                    note 
                FROM eqa_tasks 
                WHERE year = :year
                ORDER BY deadline IS NULL, deadline ASC, id DESC
            """)
            result = session.execute(sql, {"year": year}).fetchall()
            return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"❌ [EQAService ERROR] list_tasks: {e}")
            return []
        finally:
            session.close()

    def upsert_task(self, data: Dict[str, Any], actor: str = "system") -> int:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        pid = int(data.get("provider_id")) if data.get("provider_id") else None
        progid = int(data.get("program_id")) if data.get("program_id") else None

        with self._con() as con:
            prov_name = con.execute("SELECT name FROM eqa_providers WHERE id=?", (pid,)).fetchone() if pid else None
            prog_name = con.execute("SELECT name FROM eqa_programs WHERE id=?",
                                    (progid,)).fetchone() if progid else None

            prov_name_str = prov_name[0] if prov_name else data.get("provider_name")
            prog_name_str = prog_name[0] if prog_name else data.get("program_name")

            row = con.execute(
                """SELECT id FROM eqa_tasks WHERE year=? AND round_no=?
                   AND COALESCE(provider_id,0)=COALESCE(?,0) AND COALESCE(program_id,0)=COALESCE(?,0)
                   AND COALESCE(device_name,'')=COALESCE(?, '')""",
                (int(data.get("year", 0)), str(data.get("round_no") or ""),
                 pid, progid, str(data.get("device_name") or ""))
            ).fetchone()

            if row:
                tid = int(row[0])
                con.execute(
                    """UPDATE eqa_tasks SET 
                       assigned_to=?, start_date=?, end_date=?, due_date=?, status=?, note=?, updated_at=?
                       WHERE id=?""",
                    (str(data.get("assigned_to") or ""), str(data.get("start_date") or ""),
                     str(data.get("end_date") or ""), str(data.get("due_date") or ""),
                     str(data.get("status") or ""), str(data.get("note") or ""), now, tid)
                )
                con.commit()
                return tid
            else:
                cur = con.cursor()
                cur.execute(
                    """INSERT INTO eqa_tasks (
                        year, round_no, provider_id, provider_name, program_id, program_name, 
                        device_name, sample_plan, assigned_to, due_date, status, note, 
                        created_at, updated_at, created_by, start_date, end_date
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (int(data.get("year", 0)), str(data.get("round_no") or ""), pid, prov_name_str, progid,
                     prog_name_str,
                     str(data.get("device_name") or ""), str(data.get("sample_plan") or ""),
                     str(data.get("assigned_to") or ""), str(data.get("due_date") or ""),
                     str(data.get("status") or ""), str(data.get("note") or ""),
                     now, now, str(actor or "system"),
                     str(data.get("start_date") or ""), str(data.get("end_date") or ""))
                )
                new_id = cur.lastrowid
                con.commit()
                return int(new_id)

    def delete_task(self, task_id: str) -> int:
        session = SessionLocal()
        try:
            try:
                session.execute(text("DELETE FROM eqa_tasks_log WHERE task_id = :id"), {"id": task_id})
            except:
                pass
            result = session.execute(text("DELETE FROM eqa_tasks WHERE id = :id"), {"id": task_id})
            session.commit()
            return result.rowcount
        except Exception as e:
            session.rollback()
            return 0
        finally:
            session.close()

    # ---------- Kết quả (Round & Result) ----------
    def get_or_create_round(self, program_id: int, year: int, round_no: str, device_name: Optional[str]) -> int:
        with self._con() as con:
            p_info = con.execute("SELECT name, provider_id FROM eqa_programs WHERE id=?", (program_id,)).fetchone()
            pname = p_info[0] if p_info else None
            provider_id = p_info[1] if p_info else None

            if device_name:
                self._upsert_eqa_device(con, device_name, program_id=program_id, provider_id=provider_id)

            key_cols = "program_id=? AND year=? AND round_no=? AND COALESCE(device_name, '') = COALESCE(?, '')"
            params = [program_id, int(year), round_no, device_name or '']

            r = con.execute(f"SELECT id FROM eqa_round WHERE {key_cols}", params).fetchone()
            if r: return int(r[0])

            now = datetime.datetime.now().isoformat(timespec='seconds')
            cur = con.cursor()
            cur.execute(
                """INSERT INTO eqa_round (program_id, program_name, year, round_no, device_name, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (program_id, pname, int(year), round_no, device_name, 'draft', now)
            )
            new_id = cur.lastrowid
            con.commit()
            return int(new_id)

    def get_param_templates(self, program_id: int) -> List[Dict[str, Any]]:
        try:
            with self._con() as con:
                rows = list(con.execute(
                    "SELECT analyte, COALESCE(unit,'') as unit FROM eqa_param_template WHERE program_id=? ORDER BY id",
                    (int(program_id),)
                ))
            return [{"analyte": r[0], "unit": r[1]} for r in rows]
        except sqlite3.Error:
            return []

    def get_results(self, round_id: int) -> List[Dict[str, Any]]:
        try:
            with self._con() as con:
                rows = list(con.execute(
                    """SELECT analyte, unit, result_site, result_center, note,
                       sample_code, provider_analyte
                       FROM eqa_result WHERE round_id=? ORDER BY id""",
                    (int(round_id),)
                ))

            results = []
            for r in rows:
                note_str = r[4]
                u_lab = ""
                try:
                    if note_str and str(note_str).strip().startswith("{"):
                        meta = json.loads(note_str)
                        u_lab = meta.get("u_lab", "")
                except:
                    pass

                results.append({
                    "analyte": r[0], "unit": r[1],
                    "result_site": r[2], "result_center": r[3],
                    "note": r[4], "sample_code": r[5],
                    "u_lab": u_lab
                })
            return results
        except sqlite3.Error:
            return []

    def save_results(self, round_id: int, items: List[Dict[str, Any]], actor: str = "system"):
        now = datetime.datetime.now().isoformat(timespec='seconds')
        try:
            with self._con() as con:
                r = con.execute("SELECT program_id FROM eqa_round WHERE id=?", (int(round_id),)).fetchone()
                pid = int(r[0]) if r else None

                con.execute("DELETE FROM eqa_result WHERE round_id=?", (int(round_id),))

                for it in items:
                    analyte = str(it.get("analyte") or "")
                    unit = str(it.get("unit") or "")
                    note_content = str(it.get("note") or "")
                    u_lab = it.get("u_lab")

                    if u_lab:
                        try:
                            meta = json.loads(note_content) if note_content.startswith("{") else {"text": note_content}
                        except:
                            meta = {"text": note_content}
                        meta["u_lab"] = u_lab
                        note_content = json.dumps(meta, ensure_ascii=False)

                    con.execute(
                        """INSERT INTO eqa_result (
                            round_id, analyte, unit, result_site, result_center, note, 
                            created_at, updated_at, provider_analyte
                           ) VALUES (?,?,?,?,?,?,?,?,?)""",
                        (int(round_id), analyte, unit,
                         str(it.get("result_site") or ""),
                         str(it.get("result_center") or ""),
                         note_content, now, now, analyte)
                    )

                    if pid is not None and analyte.strip():
                        con.execute(
                            "INSERT OR IGNORE INTO eqa_param_template(program_id, analyte, unit) VALUES(?,?,COALESCE(?,''))",
                            (pid, analyte.strip(), unit.strip())
                        )
                con.commit()
        except sqlite3.Error as e:
            raise e

    # --- PROVIDER/PROGRAM CRUD ---
    def upsert_provider(self, name: str, prov_id: Optional[int] = None) -> bool:
        if not name.strip(): return False
        try:
            with self._con() as con:
                if prov_id is not None:
                    con.execute("UPDATE eqa_providers SET name = ? WHERE id = ?", (name.strip(), prov_id))
                else:
                    con.execute("INSERT INTO eqa_providers (name) VALUES (?)", (name.strip(),))
                con.commit()
            return True
        except sqlite3.Error:
            return False

    def delete_provider(self, prov_id: int) -> bool:
        try:
            with self._con() as con:
                con.execute("DELETE FROM eqa_providers WHERE id = ?", (prov_id,))
                con.commit()
            return True
        except sqlite3.Error:
            return False

    def upsert_program(self, provider_id: int, name: str, code: Optional[str] = None,
                       prog_id: Optional[int] = None) -> bool:
        if not name.strip(): return False
        try:
            with self._con() as con:
                if prog_id is not None:
                    con.execute("UPDATE eqa_programs SET name = ?, code = ? WHERE id = ?",
                                (name.strip(), code.strip() if code else None, prog_id))
                else:
                    con.execute("INSERT INTO eqa_programs (provider_id, name, code) VALUES (?, ?, ?)",
                                (provider_id, name.strip(), code.strip() if code else None))
                con.commit()
            return True
        except sqlite3.Error:
            return False

    def delete_program(self, prog_id: int) -> bool:
        try:
            with self._con() as con:
                con.execute("DELETE FROM eqa_programs WHERE id = ?", (prog_id,))
                con.commit()
            return True
        except sqlite3.Error:
            return False

    def save_param_templates_overwrite(self, program_id: int, items: List[Dict[str, Any]]) -> None:
        try:
            with self._con() as con:
                con.execute("DELETE FROM eqa_param_template WHERE program_id = ?", (program_id,))
                for item in items:
                    analyte = str(item.get("analyte") or "").strip()
                    unit = str(item.get("unit") or "").strip()
                    if analyte:
                        con.execute("INSERT INTO eqa_param_template(program_id, analyte, unit) VALUES(?,?,?)",
                                    (program_id, analyte, unit))
                con.commit()
        except sqlite3.Error as e:
            raise e

    # --- TASK LOGS ---
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self._con() as con:
                con.row_factory = sqlite3.Row
                row = con.execute("SELECT * FROM eqa_tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None
        except sqlite3.Error:
            return None

    def list_task_logs(self, task_id: int) -> List[Dict[str, Any]]:
        try:
            with self._con() as con:
                con.row_factory = sqlite3.Row
                rows = con.execute("SELECT * FROM eqa_tasks_log WHERE task_id = ? ORDER BY ts DESC",
                                   (task_id,)).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []

    def log_task_action(self, task_id: int, actor: str, action: str, note: Optional[str] = None):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        try:
            with self._con() as con:
                con.execute(
                    "INSERT INTO eqa_tasks_log (task_id, ts, actor, action, note) VALUES (?, ?, ?, ?, ?)",
                    (task_id, now, actor, action, note)
                )
                con.commit()
        except sqlite3.Error:
            pass

    def update_task_status(self, task_id: str, new_status: str) -> bool:
        session = SessionLocal()
        try:
            sql = text("UPDATE eqa_tasks SET status = :status WHERE id = :id")
            session.execute(sql, {"status": new_status, "id": task_id})
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    # --- YOUDEN DATA (Nâng cấp) ---
    def get_youden_data(self, program_id: int, analyte: str) -> List[Dict[str, Any]]:
        sql = """
            SELECT r.round_no, res.result_site, res.result_center, res.unit
            FROM eqa_result res
            JOIN eqa_round r ON res.round_id = r.id
            WHERE r.program_id = ? AND res.analyte = ?
            ORDER BY r.year, r.round_no
        """
        try:
            with self._con() as con:
                rows = con.execute(sql, (program_id, analyte)).fetchall()

            data_points = []
            for r in rows:
                lab_val = self._to_float(r[1])
                target_val = self._to_float(r[2])
                if lab_val is not None and target_val is not None:
                    data_points.append({
                        "round": r[0],
                        "x": target_val,
                        "y": lab_val,
                        "unit": r[3]
                    })
            return data_points
        except Exception:
            return []

    def add_task(self, data):
        session = SessionLocal()
        try:
            sql = text("""
                INSERT INTO eqa_tasks (
                    id, year, program_name, sample_code, deadline, status, 
                    assigned_to, note, device_name, round_no
                ) VALUES (
                    :id, :year, :program_name, :sample_code, :deadline, :status,
                    :assigned_to, :note, :device_name, :round_no
                )
            """)
            params = {
                "id": str(uuid.uuid4()),
                "year": data.get('year', datetime.datetime.now().year),
                "program_name": data.get('program_name'),
                "sample_code": data.get('sample_code'),
                "deadline": data.get('due_date'),
                "status": "Pending",
                "assigned_to": data.get('assigned_to', ''),
                "note": data.get('note', ''),
                "device_name": data.get('device_name', ''),
                "round_no": data.get('round_no', 1)
            }
            session.execute(sql, params)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()