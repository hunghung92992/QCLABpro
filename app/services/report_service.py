# -*- coding: utf-8 -*-
"""
app/services/report_service.py
(PHASE 8 HOÀN THIỆN) Động cơ xuất báo cáo Excel & PDF chuẩn Y khoa.
"""
import os
import datetime as dt
import pandas as pd
import traceback
import xlsxwriter
from typing import List, Dict, Any
from sqlalchemy import func, desc, and_, Column, Integer, String

# --- CORE DB IMPORTS ---
try:
    from app.core.database_orm import SessionLocal, Base
except ImportError:
    print("❌ Lỗi Import: app.core.database_orm")
    SessionLocal = None

# --- PDF IMPORTS ---
from PySide6.QtGui import QTextDocument, QPageSize
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF

# --- 1. Models Core ---
try:
    from app.models.core_models import Department, Device
except ImportError:
    print("❌ Lỗi Import: app.models.core_models")

# --- 2. Models IQC ---
try:
    from app.models.iqc_models import IQCResult, IQCRun
    HAS_IQC = True
except ImportError:
    HAS_IQC = False

# --- 3. Models EQA ---
try:
    from app.models.eqa_models import EQATask # Đã sửa lại đường dẫn import chuẩn
    HAS_EQA = True
except ImportError:
    HAS_EQA = False

# --- 4. Models CAPA (Lấy từ Phase 7.3) ---
try:
    from app.models.capa_models import CapaReport
    HAS_CAPA = True
except ImportError:
    HAS_CAPA = False
    # Fallback nếu chưa kịp tạo file capa_models.py
    class CapaReport(Base):
        __tablename__ = "audit_capas"
        id = Column(Integer, primary_key=True)
        status = Column(String)
        risk_level = Column(String)
        due_date = Column(String)

class ReportService:
    def __init__(self):
        # Đường dẫn logo (Xử lý đường dẫn tuyệt đối an toàn)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(base_dir, "..", "..", "assets", "logo.png")
        self.logo_path = self.logo_path.replace("\\", "/")

        if not os.path.exists(self.logo_path):
            self.logo_path = ""

    def _get_db(self):
        if SessionLocal:
            return SessionLocal()
        return None

    # =========================================================================
    # 1. IQC REPORT (OVERVIEW)
    # =========================================================================
    def get_iqc_summary(self, start_date, end_date, dept_name=None) -> Dict[str, Any]:
        if not HAS_IQC: return {"total": 0, "passed": 0, "failed": 0, "rate": 0}

        db = self._get_db()
        if not db: return {"total": 0, "passed": 0, "failed": 0, "rate": 0}

        try:
            query = db.query(IQCResult).join(IQCRun, IQCResult.run_id == IQCRun.id)
            query = query.filter(and_(IQCRun.run_date >= start_date, IQCRun.run_date <= end_date))

            if dept_name and dept_name != "Tất cả":
                query = query.join(Department, IQCRun.department_id == Department.id) \
                    .filter(Department.name == dept_name)

            results = query.all()
            total = len(results)
            passed = 0

            for r in results:
                pf = str(r.pass_fail).lower().strip()
                if pf in ['1', 'true', 'pass', 'dat', 'ok', 'đạt']:
                    passed += 1

            failed = total - passed
            pass_rate = (passed / total * 100) if total > 0 else 0.0

            return {
                "total": total,
                "passed": passed,
                "failed": failed,
                "rate": round(pass_rate, 1)
            }
        except Exception as e:
            print(f"❌ Lỗi IQC Summary: {e}")
            return {"total": 0, "passed": 0, "failed": 0, "rate": 0}
        finally:
            db.close()

    def get_iqc_trend(self, start_date, end_date):
        if not HAS_IQC: return pd.DataFrame()
        db = self._get_db()
        if not db: return pd.DataFrame()

        try:
            query = db.query(IQCRun.run_date, func.count(IQCResult.id)) \
                .join(IQCResult, IQCRun.id == IQCResult.run_id) \
                .filter(and_(IQCRun.run_date >= start_date, IQCRun.run_date <= end_date)) \
                .group_by(IQCRun.run_date).order_by(IQCRun.run_date)

            data = query.all()
            if not data: return pd.DataFrame(columns=['date', 'count'])
            return pd.DataFrame(data, columns=['date', 'count'])
        except Exception:
            return pd.DataFrame()
        finally:
            db.close()

    # =========================================================================
    # 2. CAPA REPORT
    # =========================================================================
    def get_capa_summary(self, start_date, end_date) -> Dict[str, int]:
        db = self._get_db()
        if not db: return {"total": 0, "open": 0, "closed": 0, "risk_high": 0}

        try:
            rows = db.query(CapaReport).all()
            total = len(rows)
            closed = 0
            risk_high = 0

            for r in rows:
                stt = str(r.status).lower().strip() if r.status else ""
                risk = str(r.risk_level).lower().strip() if r.risk_level else ""

                if stt in ['closed', 'đóng', 'done', 'hoàn thành', 'đã xử lý', 'approved']:
                    closed += 1

                if risk in ['critical', 'high', 'cao', 'nguy cấp', 'khẩn cấp']:
                    risk_high += 1

            return {"total": total, "open": total - closed, "closed": closed, "risk_high": risk_high}
        except Exception as e:
            print(f"❌ Lỗi CAPA Report: {e}")
            return {"total": 0, "open": 0, "closed": 0, "risk_high": 0}
        finally:
            db.close()

    # =========================================================================
    # 3. EQA & EQUIPMENT
    # =========================================================================
    def get_eqa_summary(self, start_date, end_date):
        if not HAS_EQA: return {"total": 0, "passed": 0, "rate": 0}
        db = self._get_db()
        if not db: return {"total": 0, "passed": 0, "rate": 0}

        try:
            query = db.query(EQATask).filter(and_(EQATask.deadline >= start_date, EQATask.deadline <= end_date))
            rows = query.all()
            total = len(rows)
            passed = 0
            for r in rows:
                stt = str(r.status).lower()
                if stt in ['pass', 'dat', 'satisfactory', 'ok', 'acceptable', 'đạt']:
                    passed += 1

            rate = (passed / total * 100) if total > 0 else 0
            return {"total": total, "passed": passed, "rate": round(rate, 1)}
        except Exception:
            return {"total": 0, "passed": 0, "rate": 0}
        finally:
            db.close()

    def get_equipment_summary(self):
        db = self._get_db()
        if not db: return {"total": 0, "broken": 0, "maintenance": 0}

        try:
            devices = db.query(Device).filter(Device.active == 1).all()
            total = len(devices)
            maintenance_due = 0

            today = dt.date.today()
            for dev in devices:
                try:
                    if dev.maintenance_cycle and dev.maintenance_cycle > 0 and dev.last_maintenance_date:
                        last_maint = dt.datetime.strptime(dev.last_maintenance_date, "%Y-%m-%d").date()
                        next_maint = last_maint + dt.timedelta(days=dev.maintenance_cycle)

                        if next_maint <= (today + dt.timedelta(days=30)):
                            maintenance_due += 1
                except:
                    continue

            return {"total": total, "broken": 0, "maintenance": maintenance_due}
        except Exception:
            return {"total": 0, "broken": 0, "maintenance": 0}
        finally:
            db.close()

    # =========================================================================
    # 4. EXPORT UTILS (PDF & RAW EXCEL)
    # =========================================================================
    def get_departments(self) -> List[str]:
        db = self._get_db()
        if not db: return []

        try:
            depts = db.query(Department.name).filter(Department.active == 1).order_by(Department.name).all()
            return [d[0] for d in depts]
        except:
            return []
        finally:
            db.close()

    def get_iqc_details_raw(self, start_date, end_date, dept_name=None) -> List[Dict]:
        if not HAS_IQC: return []
        db = self._get_db()
        if not db: return []

        try:
            query = db.query(
                IQCRun.run_date, IQCResult.test_code, IQCResult.level,
                IQCResult.value, IQCResult.pass_fail, Department.name.label('department')
            ).join(IQCRun, IQCResult.run_id == IQCRun.id) \
                .outerjoin(Department, IQCRun.department_id == Department.id) \
                .filter(and_(IQCRun.run_date >= start_date, IQCRun.run_date <= end_date))

            if dept_name and dept_name != "Tất cả":
                query = query.filter(Department.name == dept_name)

            rows = query.order_by(desc(IQCRun.run_date)).all()

            results = []
            for r in rows:
                pf = str(r.pass_fail).lower()
                status = "Đạt" if pf in ['1', 'true', 'pass', 'dat', 'ok', 'đạt'] else "Lỗi"

                results.append({
                    "date": r.run_date,
                    "test": r.test_code,
                    "level": r.level,
                    "value": r.value,
                    "status": status,
                    "dept": r.department or ""
                })
            return results
        except Exception:
            return []
        finally:
            db.close()

    def export_pdf_report(self, file_path, data, metadata) -> bool:
        """Xuất PDF Thống kê (Dashboard)"""
        try:
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except: return False

            s, e, d = metadata.get('date_from'), metadata.get('date_to'), metadata.get('department')
            iqc = self.get_iqc_summary(s, e, d)
            eqa = self.get_eqa_summary(s, e)
            capa = self.get_capa_summary(s, e)
            dev = self.get_equipment_summary()

            img_tag = f'<img src="file:///{self.logo_path}" width="80" height="80">' if self.logo_path else ""

            html = f"""
            <html>
            <head>
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #333; }} 
                    h2 {{ color: #005fb8; margin: 0; font-size: 18pt; }}
                    h3 {{ color: #333; border-bottom: 2px solid #005fb8; padding-bottom: 5px; margin-top: 20px; }}
                    .summary-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                    .summary-table td {{ border: 1px solid #ddd; padding: 10px; vertical-align: top; width: 25%; background-color: #f9f9f9; }}
                    .stat-title {{ font-weight: bold; color: #555; display: block; margin-bottom: 5px; font-size: 11pt; }}
                    .stat-value {{ font-size: 20pt; font-weight: bold; color: #005fb8; }}
                    .stat-sub {{ font-size: 9pt; color: #777; }}
                    .pass-rate {{ color: green; font-weight: bold; }}
                    .fail-rate {{ color: red; font-weight: bold; }}
                    .detail-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    .detail-table th, .detail-table td {{ border: 1px solid #444; padding: 6px; text-align: center; font-size: 9pt; }}
                    .detail-table th {{ background-color: #f0f0f0; font-weight: bold; }}
                    .status-pass {{ color: green; font-weight: bold; }} 
                    .status-fail {{ color: red; font-weight: bold; }}
                </style>
            </head>
            <body>
                <table style="width:100%; border:none;">
                    <tr>
                        <td style="border:none; text-align:left; width:100px;">{img_tag}</td>
                        <td style="border:none; text-align:center;">
                            <h2>BÁO CÁO THỐNG KÊ CHẤT LƯỢNG</h2>
                            <p style="font-size: 11pt; margin: 5px;">QC Lab Manager Pro</p>
                        </td>
                    </tr>
                </table>
                <p style="text-align:center;">
                    <b>Thời gian:</b> {s} đến {e} &nbsp;|&nbsp; 
                    <b>Phòng ban:</b> {d}
                </p>
                <hr style="border: 0; border-top: 1px solid #ccc;">

                <h3>1. TỔNG QUAN HIỆU SUẤT</h3>
                <table class="summary-table">
                    <tr>
                        <td>
                            <span class="stat-title">Nội kiểm (IQC)</span>
                            <div class="stat-value">{iqc['rate']}%</div>
                            <div class="stat-sub">Tỷ lệ Đạt</div>
                            <br>
                            <div>Tổng mẫu: <b>{iqc['total']}</b></div>
                            <div>Đạt: <span class="pass-rate">{iqc['passed']}</span></div>
                            <div>Lỗi: <span class="fail-rate">{iqc['failed']}</span></div>
                        </td>
                        <td>
                            <span class="stat-title">Ngoại kiểm (EQA)</span>
                            <div class="stat-value">{eqa['rate']}%</div>
                            <div class="stat-sub">Tỷ lệ Đạt</div>
                            <br>
                            <div>Tổng mẫu: <b>{eqa['total']}</b></div>
                            <div>Đạt: <span class="pass-rate">{eqa['passed']}</span></div>
                        </td>
                        <td>
                            <span class="stat-title">Sự cố (CAPA)</span>
                            <div class="stat-value" style="color: #d13438;">{capa['open']}</div>
                            <div class="stat-sub">Đang mở</div>
                            <br>
                            <div>Tổng cộng: <b>{capa['total']}</b></div>
                            <div>Đã đóng: {capa['closed']}</div>
                            <div>Rủi ro cao: <b style="color:red;">{capa['risk_high']}</b></div>
                        </td>
                        <td>
                            <span class="stat-title">Thiết bị</span>
                            <div class="stat-value" style="color: #605e5c;">{dev['total']}</div>
                            <div class="stat-sub">Đang hoạt động</div>
                            <br>
                            <div>Bảo trì sắp tới: <b>{dev['maintenance']}</b></div>
                            <div>Hỏng hóc: {dev['broken']}</div>
                        </td>
                    </tr>
                </table>

                <h3>2. CHI TIẾT DỮ LIỆU IQC</h3>
                <table class="detail-table">
                    <thead>
                        <tr>
                            <th width="15%">Ngày</th>
                            <th width="15%">Khoa</th>
                            <th width="15%">Test</th>
                            <th width="15%">Level</th>
                            <th width="20%">Kết quả</th>
                            <th width="20%">Đánh giá</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join([f"<tr><td>{r['date']}</td><td>{r['dept']}</td><td>{r['test']}</td><td>{r['level']}</td><td>{r['value']}</td><td class='{'status-pass' if r['status'] == 'Đạt' else 'status-fail'}'>{r['status']}</td></tr>" for r in data])}
                    </tbody>
                </table>

                <br><br>
                <table style="border:none; margin-top:30px; width:100%;">
                    <tr>
                        <td style="border:none; text-align:left;">
                            <i>Ngày xuất báo cáo: {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}</i>
                        </td>
                        <td style="border:none; text-align:right;">
                            <b>Người lập báo cáo</b><br><br><br><br>
                            Administrator
                        </td>
                    </tr>
                </table>
            </body>
            </html>"""

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            try:
                printer.setPageSize(QPageSize(QPageSize.A4))
            except: pass

            printer.setPageMargins(QMarginsF(10, 10, 10, 10))

            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
            return True

        except Exception as e:
            print(f"❌ PDF Export Error: {e}")
            traceback.print_exc()
            return False

    # =========================================================================
    # 5. CHI TIẾT THỐNG KÊ (ISO 15189)
    # =========================================================================
    def get_monthly_statistics(self, start_date, end_date, dept_name=None) -> List[Dict[str, Any]]:
        if not HAS_IQC: return []
        db = self._get_db()
        if not db: return []

        try:
            # [FIX TẬN GỐC]: Đã xóa bỏ điều kiện is_active/is_excluded
            # vì Model IQCResult của bạn không khai báo các cột này.
            query = db.query(
                IQCResult.test_code,
                IQCResult.level,
                IQCResult.value_num,
                IQCResult.violation_rule,
                Department.name.label('department')
            ).join(IQCRun, IQCResult.run_id == IQCRun.id) \
                .outerjoin(Department, IQCRun.department_id == Department.id) \
                .filter(
                IQCRun.run_date >= start_date,
                IQCRun.run_date <= end_date,
                IQCResult.value_num.isnot(None)
                # ĐÃ XÓA dòng gây lỗi ở đây!
            )

            if dept_name and dept_name != "Tất cả":
                query = query.filter(Department.name == dept_name)

            rows = query.all()
            if not rows: return []

            df = pd.DataFrame([{
                "test": r.test_code,
                "level": r.level,
                "value": float(r.value_num),
                "rule": str(r.violation_rule) if r.violation_rule else "OK" # Xử lý Null
            } for r in rows])

            stats_results = []
            grouped = df.groupby(['test', 'level'])

            for name, group in grouped:
                test_code, level = name
                count = len(group)

                if count == 0: continue

                mean_val = group['value'].mean()
                sd_val = group['value'].std(ddof=1) if count > 1 else 0.0
                cv_val = (sd_val / mean_val * 100) if mean_val != 0 else 0.0

                # [FIX QUAN TRỌNG 2]: Đếm lỗi Westgard nhưng bỏ qua chữ "OK"
                error_count = group['rule'].apply(lambda x: 1 if x.strip() and x.strip() != "OK" else 0).sum()

                stats_results.append({
                    "test_code": test_code,
                    "level": level,
                    "N": count,
                    "mean": round(mean_val, 2),
                    "sd": round(sd_val, 2),
                    "cv": round(cv_val, 2),
                    "errors": int(error_count)
                })

            return stats_results

        except Exception as e:
            print(f"❌ Lỗi tính toán thống kê ISO: {e}")
            return []
        finally:
            db.close()
    # =========================================================================
    # 6. EXPORT MONTHLY EXCEL (ISO 15189)
    # =========================================================================
    def export_monthly_iqc(self, dept_name, start_date, end_date, output_path):
        try:
            stats = self.get_monthly_statistics(start_date, end_date, dept_name)

            workbook = xlsxwriter.Workbook(output_path)
            worksheet = workbook.add_worksheet("Thong_Ke_IQC")

            title_format = workbook.add_format({
                'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter', 'font_color': '#005fb8'
            })
            meta_format = workbook.add_format({
                'italic': True, 'font_size': 10, 'align': 'center'
            })
            header_format = workbook.add_format({
                'bold': True, 'bg_color': '#0078D4', 'font_color': 'white',
                'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            cell_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
            cell_left = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})

            alert_format = workbook.add_format({
                'border': 1, 'align': 'center', 'valign': 'vcenter',
                'font_color': '#d13438', 'bold': True, 'bg_color': '#fde7e9'
            })

            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 10)
            worksheet.set_column('C:C', 12)
            worksheet.set_column('D:E', 12)
            worksheet.set_column('F:F', 12)
            worksheet.set_column('G:G', 12)

            worksheet.merge_range('A1:G1', 'BÁO CÁO THỐNG KÊ CHẤT LƯỢNG XÉT NGHIỆM (IQC)', title_format)
            dept_str = dept_name if dept_name and dept_name != "Tất cả" else "Tất cả các khoa"
            worksheet.merge_range('A2:G2', f'Thời gian: {start_date} đến {end_date} | Khoa: {dept_str}', meta_format)
            worksheet.merge_range('A3:G3', f'Ngày xuất: {dt.datetime.now().strftime("%d/%m/%Y %H:%M")}', meta_format)

            headers = ['Xét nghiệm', 'Level', 'Số Mẫu (N)', 'Mean', 'SD', 'CV (%)', 'Số lỗi']
            row = 4
            for col, text in enumerate(headers):
                worksheet.write(row, col, text, header_format)

            row += 1
            if not stats:
                worksheet.merge_range(f'A{row + 1}:G{row + 1}', 'Không có dữ liệu hợp lệ trong khoảng thời gian', cell_center)
            else:
                for r in stats:
                    worksheet.write(row, 0, r['test_code'], cell_left)
                    worksheet.write(row, 1, r['level'], cell_center)
                    worksheet.write(row, 2, r['N'], cell_center)
                    worksheet.write(row, 3, r['mean'], cell_center)
                    worksheet.write(row, 4, r['sd'], cell_center)

                    if r['cv'] > 5.0:
                        worksheet.write(row, 5, r['cv'], alert_format)
                    else:
                        worksheet.write(row, 5, r['cv'], cell_center)

                    if r['errors'] > 0:
                        worksheet.write(row, 6, r['errors'], alert_format)
                    else:
                        worksheet.write(row, 6, r['errors'], cell_center)
                    row += 1

            row += 2
            worksheet.write(row, 1, "Người lập biểu", workbook.add_format({'bold': True, 'align': 'center', 'border': 0}))
            worksheet.write(row, 5, "Trưởng khoa/Phòng", workbook.add_format({'bold': True, 'align': 'center', 'border': 0}))
            worksheet.write(row + 4, 1, "(Ký & ghi rõ họ tên)", meta_format)
            worksheet.write(row + 4, 5, "(Ký & ghi rõ họ tên)", meta_format)

            workbook.close()
            return True

        except Exception as e:
            print(f"❌ Lỗi xuất báo cáo Excel: {e}")
            return False