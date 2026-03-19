# -*- coding: utf-8 -*-
"""
/lis_parser_service.py
Dịch vụ chạy nền (threading) để PHÂN TÍCH (PARSE) tin nhắn thô
từ `device_messages` và lưu kết quả IQC.
(Đã fix lỗi tắt App bị văng cảnh báo QThread Destroyed)
"""

import threading
import time
from typing import Dict, Any, Optional, List
import datetime as dt

# Imports từ Cấu trúc v3
from app.core.database_orm import get_db_connection, SessionLocal
from app.services.iqc_service import IQCService  # Dịch vụ đích
from app.services.device_service import DeviceService
from app.models.iqc_models import DeviceMessage


class LisParserService:

    def __init__(self, iqc_service: IQCService, device_service: DeviceService):
        self.iqc_service = iqc_service
        self.device_service = device_service
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_processed_id = ""  # ID bây giờ là chuỗi UUID, không phải số nguyên 0 nữa

    def start(self, poll_interval: int = 10):
        """Bắt đầu vòng lặp quét CSDL."""
        if self._thread and self._thread.is_alive():
            return  # Đã chạy

        print("[LisParser] Đang khởi động service...")
        self._stop_event.clear()

        # Không dùng MAX(id) cho UUID nữa, vì UUID sắp xếp lộn xộn.
        # Cứ quét những tin nhắn có trạng thái 'PENDING'.

        self._thread = threading.Thread(
            target=self._poll_loop,
            args=(poll_interval,),
            daemon=True,
            name="LisParserWorker"
        )
        self._thread.start()
        print("[LisParser] Đã khởi động. Bắt đầu quét các bản tin 'PENDING'...")

    def stop(self):
        """Dừng vòng lặp an toàn chống văng cảnh báo khi tắt App."""
        print("[LisParser] Đang nhận lệnh dừng...")
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            # Ép luồng chính chờ tối đa 3 giây để luồng phụ thoát hẳn
            self._thread.join(timeout=3.0)

        print("[LisParser] Đã dừng hoàn toàn.")

    def _poll_loop(self, poll_interval: int):
        """Vòng lặp chính, quét CSDL định kỳ. Chẻ nhỏ thời gian ngủ để thoát nhanh."""
        while not self._stop_event.is_set():
            try:
                new_messages = self._fetch_new_messages()
                if new_messages:
                    print(f"[LisParser] Tìm thấy {len(new_messages)} tin nhắn mới. Đang xử lý...")
                    for msg in new_messages:
                        if self._stop_event.is_set(): break  # Thoát ngay nếu nhận lệnh dừng
                        self._process_message(msg)
            except Exception as e:
                print(f"[LisParser ERROR] Lỗi vòng lặp: {e}")

            # [QUAN TRỌNG] Chia nhỏ thời gian ngủ (1 giây/lần) để kiểm tra stop_event liên tục
            # Thay vì ngủ li bì 10s rồi mới tỉnh dậy tắt
            for _ in range(poll_interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1.0)

    def _fetch_new_messages(self) -> List[Dict[str, Any]]:
        """Lấy các tin nhắn mới từ CSDL (Dùng SQLAlchemy để an toàn)."""
        db = SessionLocal()
        try:
            # Truy vấn thẳng vào bảng DeviceMessage
            messages = db.query(DeviceMessage).filter(DeviceMessage.status == 'PENDING').limit(50).all()

            result = []
            for m in messages:
                # Lấy thêm tên thiết bị nếu cần
                dev_name = m.device.name if getattr(m, 'device', None) else "Unknown"
                dept_name = m.device.department.name if getattr(m, 'device', None) and getattr(m.device, 'department',
                                                                                               None) else "Unknown"

                result.append({
                    'id': str(m.id),
                    'raw_data': m.raw_data,
                    'protocol': m.protocol,
                    'device_id': m.device_id,
                    'device_name': dev_name,
                    'department_name': dept_name
                })
            return result
        except Exception as e:
            print(f"[LisParser] Fetch error: {e}")
            return []
        finally:
            db.close()

    def _process_message(self, msg: Dict[str, Any]):
        """Xử lý 1 tin nhắn thô và đẩy vào hệ thống IQC."""
        msg_id = msg.get('id')
        protocol = (msg.get('protocol') or 'plain').lower()
        payload = msg.get('raw_data')
        device_id = msg.get('device_id')

        if not payload:
            self._update_msg_status(msg_id, "ERROR", "Empty payload")
            return

        # 1. GIẢI MÃ (PARSING)
        results: List[Dict[str, Any]] = []
        try:
            if isinstance(payload, bytes):
                payload = payload.decode('latin-1', errors='replace')

            if protocol == 'astm':
                results = self._parse_astm(payload)
            elif protocol == 'hl7':
                results = self._parse_hl7(payload)
            else:
                results = self._parse_plain(payload)
        except Exception as e:
            self._update_msg_status(msg_id, "ERROR", f"Parse error: {e}")
            return

        if not results:
            self._update_msg_status(msg_id, "PROCESSED", "No QC results found in message")
            return

        # 2. MAPPING & LƯU KẾT QUẢ
        try:
            run_id = self.iqc_service.create_run(
                run_date=dt.date.today().isoformat(),
                user="auto_lis",
                device=msg.get("device_name", "Unknown"),
                department=msg.get("department_name", "Unknown"),
                levels_count=3,
                run_type="quant"
            )

            iqc_rows = []
            session = SessionLocal()
            try:
                from app.models.core_models import DeviceTestMap
                for res in results:
                    mapping = session.query(DeviceTestMap).filter(
                        DeviceTestMap.device_id == device_id,
                        DeviceTestMap.machine_code == res['test_code']
                    ).first()

                    final_code = mapping.internal_code if mapping else res['test_code']

                    iqc_rows.append({
                        "test_code": final_code,
                        "unit": res.get("unit", ""),
                        res["level"]: res["value"]
                    })
            finally:
                session.close()

            if iqc_rows:
                saved_count = self.iqc_service.upsert_results(run_id, iqc_rows)
                self._update_msg_status(msg_id, "PROCESSED")
                print(f"✅ [LisParser] Đã xử lý tin nhắn {msg_id}: {saved_count} kết quả.")

        except Exception as e:
            self._update_msg_status(msg_id, "ERROR", f"Save error: {e}")

    def _update_msg_status(self, msg_id: str, status: str, error_msg: str = None):
        """Cập nhật trạng thái tin nhắn vào DB để không xử lý lại."""
        db = SessionLocal()
        try:
            msg = db.query(DeviceMessage).filter(DeviceMessage.id == msg_id).first()
            if msg:
                msg.status = status
                msg.error_msg = error_msg
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Lỗi cập nhật status message: {e}")
        finally:
            db.close()

    # --- CÁC HÀM PARSER ---
    def _parse_astm(self, payload: str) -> List[Dict[str, Any]]:
        """Phân tích gói tin ASTM E1394."""
        results = []
        lines = payload.split('\r')
        current_level = "L1"

        for line in lines:
            line = line.strip()
            if not line: continue

            if line.startswith('O|'):
                parts = line.split('|')
                sample_id = parts[2].upper() if len(parts) > 2 else ""
                if "LEVEL" in sample_id or "LV" in sample_id or "L1" in sample_id or "L2" in sample_id or "L3" in sample_id:
                    if "1" in sample_id:
                        current_level = "L1"
                    elif "2" in sample_id:
                        current_level = "L2"
                    elif "3" in sample_id:
                        current_level = "L3"

            elif line.startswith('R|'):
                parts = line.split('|')
                if len(parts) > 3:
                    test_raw = parts[2].replace('^', '').strip()
                    value = parts[3].strip()
                    unit = parts[4].strip() if len(parts) > 4 else ""

                    if test_raw and value:
                        results.append({
                            "test_code": test_raw,
                            "value": value,
                            "unit": unit,
                            "level": current_level
                        })
        return results

    def _parse_hl7(self, payload: str) -> List[Dict[str, Any]]:
        return []

    def _parse_plain(self, payload: str) -> List[Dict[str, Any]]:
        return []