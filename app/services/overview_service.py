# -*- coding: utf-8 -*-
import os
import sqlite3
import datetime as dt
from app.core.database_orm import SessionLocal


class OverviewService:
    def _get_conn(self):
        """Tạo kết nối raw SQLite an toàn."""
        try:
            session = SessionLocal()
            db_url = session.bind.url.database
            session.close()

            # Xử lý đường dẫn
            if db_url and not os.path.isabs(db_url):
                db_path = os.path.abspath(db_url)
            else:
                db_path = db_url

            # [DEBUG] In ra để kiểm tra
            print(f"🔍 OVERVIEW ĐANG ĐỌC DB TẠI: {db_path}")

            if not os.path.exists(db_path):
                return None

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"❌ DB Connection Error: {e}")
            return None

    def _detect_real_dept_table(self, cursor):
        """Hàm thông minh: Tìm bảng khoa nào thực sự có dữ liệu."""
        try:
            # 1. Kiểm tra bảng 'departments' (số nhiều)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='departments'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM departments")
                if cursor.fetchone()[0] > 0:
                    print("✅ Sử dụng bảng: 'departments' (Có dữ liệu)")
                    return "departments"

            # 2. Kiểm tra bảng 'department' (số ít)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='department'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM department")
                if cursor.fetchone()[0] > 0:
                    print("✅ Sử dụng bảng: 'department' (Có dữ liệu)")
                    return "department"

            # 3. Fallback: Nếu cả 2 đều rỗng hoặc không có, ưu tiên departments nếu tồn tại
            print("⚠️ Cả 2 bảng đều rỗng, mặc định dùng 'departments'")
            return "departments"
        except:
            return "departments"

    def get_departments(self):
        """Lấy danh sách Khoa."""
        depts = []
        conn = self._get_conn()
        if not conn: return ["Lỗi kết nối DB"]

        try:
            cursor = conn.cursor()
            # Tự động chọn bảng có dữ liệu
            table_name = self._detect_real_dept_table(cursor)

            # Lấy dữ liệu
            query = f"SELECT name FROM {table_name} ORDER BY name"
            cursor.execute(query)
            rows = cursor.fetchall()

            if rows:
                depts = [row['name'] for row in rows]
                print(f"📊 Đã load được {len(depts)} khoa.")
            else:
                depts = ["Chưa có dữ liệu"]

        except Exception as e:
            print(f"❌ Get Dept Error: {e}")
            depts = ["Lỗi truy vấn"]
        finally:
            conn.close()

        return depts

    def check_system_health(self):
        status = {"db": False, "backup": False}
        try:
            conn = self._get_conn()
            if conn:
                conn.execute("SELECT 1")
                conn.close()
                status["db"] = True
        except:
            status["db"] = False

        try:
            possible_dirs = ["backups", "database/backups", "../backups"]
            # Thêm đường dẫn AppData nếu cần
            app_data = os.getenv('APPDATA')
            if app_data:
                possible_dirs.append(os.path.join(app_data, "QCLabManager", "backups"))

            for b_dir in possible_dirs:
                if os.path.exists(b_dir):
                    now = dt.datetime.now()
                    files = [os.path.join(b_dir, f) for f in os.listdir(b_dir) if f.endswith(f"{os.extsep}db")]
                    if files:
                        latest = max(files, key=os.path.getmtime)
                        if (now - dt.datetime.fromtimestamp(os.path.getmtime(latest))).total_seconds() < 86400:
                            status["backup"] = True
                            break
        except:
            pass
        return status

    def get_kpi_data(self, dept_name=None):
        today = dt.date.today().isoformat()
        kpi = {"total_samples": 0, "pass_rate": 0, "device_status": "0/0", "capa_status": "0/0"}

        conn = self._get_conn()
        if not conn: return kpi

        try:
            cursor = conn.cursor()
            tbl_dept = self._detect_real_dept_table(cursor)

            # --- 1. IQC ---
            try:
                sql_iqc = f"""
                    SELECT COUNT(*) as total, 
                    SUM(CASE WHEN r.pass_fail IN ('1','True','Pass','Dat','ok','đạt') THEN 1 ELSE 0 END) as passed
                    FROM iqc_result r 
                    JOIN iqc_run run ON r.run_id = run.id
                    LEFT JOIN {tbl_dept} d ON run.department_id = d.id
                    WHERE run.run_date = ?
                """
                params = [today]
                if dept_name and dept_name not in ["Tất cả", "Chưa có dữ liệu", "Lỗi truy vấn"]:
                    sql_iqc += " AND d.name = ?"
                    params.append(dept_name)

                row = cursor.execute(sql_iqc, params).fetchone()
                total = row['total'] or 0
                passed = row['passed'] or 0
                kpi["total_samples"] = total
                kpi["pass_rate"] = round((passed / total * 100), 1) if total > 0 else 0
            except:
                pass

            # --- 2. DEVICE ---
            try:
                # Tự động chọn bảng device
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='catalog_device'")
                tbl_dev = 'catalog_device' if cursor.fetchone() else 'devices'

                cursor.execute(f"SELECT COUNT(*) FROM {tbl_dev}")
                dev_total = cursor.fetchone()[0] or 0

                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {tbl_dev} WHERE active = 0")
                except:
                    cursor.execute(f"SELECT COUNT(*) FROM {tbl_dev} WHERE status = 'Broken'")
                dev_broken = cursor.fetchone()[0] or 0
                kpi["device_status"] = f"{dev_broken}/{dev_total}"
            except:
                pass

            # --- 3. CAPA ---
            try:
                cursor.execute("SELECT COUNT(*) FROM audit_capas WHERE status NOT IN ('Closed','Đóng')")
                capa_open = cursor.fetchone()[0] or 0
                cursor.execute(
                    "SELECT COUNT(*) FROM audit_capas WHERE status NOT IN ('Closed','Đóng') AND due_date < ?", (today,))
                capa_overdue = cursor.fetchone()[0] or 0
                kpi["capa_status"] = f"{capa_overdue}/{capa_open}"
            except:
                pass

        except Exception as e:
            print(f"Error KPI: {e}")
        finally:
            conn.close()
        return kpi

    def get_chart_data(self, dept_name=None):
        today = dt.date.today()
        dates, counts = [], []
        conn = self._get_conn()
        if not conn: return [], []

        try:
            cursor = conn.cursor()
            tbl_dept = self._detect_real_dept_table(cursor)

            for i in range(6, -1, -1):
                d = today - dt.timedelta(days=i)
                d_str = d.isoformat()

                sql = f"""
                    SELECT COUNT(*) FROM iqc_run r 
                    LEFT JOIN {tbl_dept} d ON r.department_id = d.id 
                    WHERE r.run_date = ?
                """
                params = [d_str]
                if dept_name and dept_name not in ["Tất cả", "Chưa có dữ liệu"]:
                    sql += " AND d.name = ?"
                    params.append(dept_name)

                try:
                    cnt = conn.execute(sql, params).fetchone()[0]
                except:
                    cnt = 0

                dates.append(d.strftime("%d/%m"))
                counts.append(cnt)
        except Exception as e:
            print(f"Chart Error: {e}")
        finally:
            conn.close()
        return dates, counts

    def get_recent_table(self, limit=10, dept_name=None):
        data = []
        conn = self._get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor()
            tbl_dept = self._detect_real_dept_table(cursor)

            sql = f"""
                SELECT run.run_date, run.run_time, r.test_code, r.level, r.value, r.pass_fail, d.name as dept_name
                FROM iqc_result r 
                JOIN iqc_run run ON r.run_id = run.id
                LEFT JOIN {tbl_dept} d ON run.department_id = d.id
            """
            params = []
            if dept_name and dept_name not in ["Tất cả", "Chưa có dữ liệu"]:
                sql += " WHERE d.name = ?"
                params.append(dept_name)

            sql += " ORDER BY run.run_date DESC, run.run_time DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            for r in rows:
                pf = str(r['pass_fail']).lower()
                st = "Đạt" if pf in ['1', 'true', 'pass', 'dat', 'ok', 'đạt'] else "Lỗi"

                t_str = f"{r['run_date']} {r['run_time']}"
                try:
                    if 'T' in str(r['run_time']):
                        t_str = str(r['run_time']).split('T')[1][:5]
                    else:
                        t_str = str(r['run_time'])[:5]
                except:
                    pass

                data.append({
                    "time": f"{r['run_date'][5:]} {t_str}",
                    "dept": r['dept_name'] or "-",
                    "test": r['test_code'],
                    "level": r['level'],
                    "value": r['value'],
                    "status": st
                })
        except:
            pass
        finally:
            conn.close()
        return data