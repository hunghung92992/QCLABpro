# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Dict
from sqlalchemy import text

# 🌟 Sử dụng SessionLocal chuẩn của kiến trúc mới
from app.core.database_orm import SessionLocal


class AlertService:
    def __init__(self):
        self._db = SessionLocal()

    def get_all_alerts(self) -> List[Dict]:
        """Tổng hợp tất cả cảnh báo từ các nguồn."""
        alerts = []
        alerts.extend(self._check_catalog_lots())  # 1. Hóa chất
        alerts.extend(self._check_qc_failures())  # 2. Vi phạm Westgard
        alerts.extend(self._check_schedules())  # 3. Lịch QC (Mới)

        # Sắp xếp: Critical lên đầu, sau đó theo thời gian
        alerts.sort(key=lambda x: (0 if x.get('level') == 'critical' else 1, x.get('date')), reverse=False)
        return alerts

    def get_summary(self):
        """Đếm số lượng cảnh báo để hiển thị lên thẻ KPI."""
        alerts = self.get_all_alerts()
        total = len(alerts)
        critical = sum(1 for a in alerts if a.get('level') == 'critical')
        warning = sum(1 for a in alerts if a.get('level') == 'warning')
        return {"total": total, "critical": critical, "warning": warning}

    # --- PRIVATE METHODS ---

    def _check_catalog_lots(self) -> List[Dict]:
        """Kiểm tra lô QC sắp hết hạn hoặc đã hết hạn."""
        alerts = []
        try:
            # 🌟 Đã sửa tên cột: status, lot_name, lot_code, exp_date
            sql = text("""
                SELECT lot_name, lot_code, exp_date 
                FROM catalog_lots 
                WHERE status = 'active' OR status IS NULL
            """)
            rows = self._db.execute(sql).fetchall()

            today = datetime.now().date()
            warning_days = 30  # Cảnh báo trước 30 ngày

            for r in rows:
                row = r._mapping  # Lấy dữ liệu dạng Dictionary an toàn
                if not row['exp_date']:
                    continue

                try:
                    exp_date = datetime.strptime(row['exp_date'], '%Y-%m-%d').date()
                    delta = (exp_date - today).days

                    item = {
                        "type": "Hóa chất",
                        "source": "Kho Hóa chất",
                        "name": f"{row['lot_name']} ({row['lot_code']})",
                        "date": row['exp_date'],
                        "result_id": None
                    }

                    if delta < 0:
                        item.update({
                            "message": f"Đã hết hạn {abs(delta)} ngày!",
                            "level": "critical",
                            "action": "Ngừng sử dụng"
                        })
                        alerts.append(item)
                    elif delta <= warning_days:
                        item.update({
                            "message": f"Sắp hết hạn (còn {delta} ngày)",
                            "level": "warning",
                            "action": "Chuẩn bị lô mới"
                        })
                        alerts.append(item)
                except ValueError:
                    continue
        except Exception as e:
            print(f"❌ Alert Service Error (Lots): {e}")

        return alerts

    def _check_qc_failures(self) -> List[Dict]:
        """Lấy 20 kết quả QC thất bại (Fail) gần nhất."""
        alerts = []
        try:
            # 🌟 Đã bỏ r.level và r.lot. Lấy violation_rule thay thế.
            query = text("""
                SELECT r.id as result_id, r.test_code, r.value, r.pass_fail, r.violation_rule, run.run_date 
                FROM iqc_results r
                JOIN iqc_runs run ON r.run_id = run.id
                WHERE r.pass_fail IN (0, '0', 'False', 'FAIL') 
                ORDER BY run.run_date DESC
                LIMIT 20
            """)
            rows = self._db.execute(query).fetchall()

            for r in rows:
                row = r._mapping
                rule = row['violation_rule'] if row['violation_rule'] else "Vi phạm Rule"
                alerts.append({
                    "type": "Vi phạm Westgard",
                    "source": "Kết quả IQC",
                    "name": f"{row['test_code']}",
                    "date": row['run_date'],
                    "message": f"Lỗi {rule} (Val: {row['value']}): Cần CAPA.",
                    "level": "critical",
                    "action": "Xử lý ngay",
                    "result_id": row['result_id']
                })
        except Exception as e:
            print(f"❌ Alert Service Error (QC): {e}")

        return alerts

    def _check_schedules(self) -> List[Dict]:
        """Giả lập cảnh báo Lịch QC (Để test nút Xem Lịch)."""
        return [{
            "type": "Lịch QC",
            "source": "Lịch bảo dưỡng",
            "name": "Bảo dưỡng máy tuần (Tất cả máy)",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "message": "Task QC đến hạn (trong ân hạn).",
            "level": "warning",
            "result_id": None,
            "action": "Thực hiện"
        }]

    def __del__(self):
        try:
            self._db.close()
        except:
            pass