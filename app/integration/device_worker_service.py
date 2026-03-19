# -*- coding: utf-8 -*-
"""
/device_worker_service.py
Dịch vụ chạy nền (threading) để thu thập dữ liệu từ thiết bị.
Đã tối ưu hóa Thread Shutdown để chống treo cổng COM.
"""

import threading
import time
from typing import Dict, Any, List

# Service để GHI dữ liệu
from app.services.device_service import DeviceService

# Import các drivers I/O
from .tcp_driver import TcpLineDriver
from .serial_driver import SerialLineDriver

DRIVERS = {
    'tcp': TcpLineDriver,
    'serial': SerialLineDriver,
}


class DeviceWorkerService:
    """
    Quản lý việc khởi chạy và dừng các thread I/O cho thiết bị.
    """

    def __init__(self, device_service: DeviceService):
        self.device_service = device_service
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def start_workers(self):
        """Khởi động các Worker dựa trên Database chuẩn ORM."""
        print("🔧 [DeviceWorker] Đang quét danh sách thiết bị...")
        try:
            devices = self.device_service.list_devices(filters={"active": 1})

            if not devices:
                print("⚠️ [DeviceWorker] Không có thiết bị nào được kích hoạt.")
                return

            for dev_row in devices:
                t = threading.Thread(
                    target=self._device_loop,
                    args=(dev_row,),
                    name=f"Worker-{dev_row.get('name')}",
                    daemon=True
                )
                t.start()
                self._threads.append(t)
                print(f"✅ [DeviceWorker] Đã bật luồng cho: {dev_row.get('name')}")
        except Exception as e:
            print(f"❌ [DeviceWorker FATAL] Lỗi khởi chạy: {e}")

    def stop_workers(self):
        """Dừng tất cả các worker an toàn (Chống kẹt cổng COM)."""
        print("[DeviceWorker] Đang gửi tín hiệu dừng đến tất cả workers...")
        self._stop_event.set()

        for t in self._threads:
            if t.is_alive():
                t.join(timeout=3.0)  # Nới lỏng thời gian chờ lên 3s để driver kịp nhả cổng

        self._threads.clear()
        print("[DeviceWorker] Tất cả workers đã dừng.")

    def _device_loop(self, device_config: Dict[str, Any]):
        """Vòng lặp chạy nền cho từng thiết bị."""
        dev_id = device_config["id"]
        dev_name = device_config["name"]
        kind = (device_config.get("conn_type") or "none").lower()
        protocol = (device_config.get("protocol") or "plain").lower()

        driver_class = DRIVERS.get(kind)
        if not driver_class:
            print(f"⚠️ [Worker-{dev_name}] Bỏ qua: Loại kết nối '{kind}' không hỗ trợ.")
            return

        cfg = {}
        if kind == "tcp":
            cfg = dict(
                host=device_config.get("ip") or device_config.get("ip_address"),
                port=int(device_config.get("port") or device_config.get("ip_port") or 0)
            )
        elif kind == "serial":
            cfg = dict(
                port=device_config.get("serial_port") or device_config.get("com_port"),
                baudrate=int(device_config.get("baudrate", 9600)),
                parity=device_config.get("parity", 'N'),
                stopbits=int(device_config.get("stopbits") or device_config.get("stop_bits") or 1)
            )

        driver = driver_class(**cfg)

        while not self._stop_event.is_set():
            try:
                print(f"🔗 [Worker-{dev_name}] Đang thử kết nối ({kind.upper()})...")
                driver.open()
                print(f"✅ [Worker-{dev_name}] Đã kết nối thành công.")

                # Có thể hàm này của bạn chưa được định nghĩa trong DeviceService mới,
                # ta dùng try-except để bypass nếu chưa code tính năng Heartbeat
                try:
                    self.device_service.update_heartbeat(dev_id)
                except AttributeError:
                    pass

                last_heartbeat = time.time()

                while not self._stop_event.is_set():
                    frame = driver.readline(timeout=1.0)

                    if frame:
                        self.device_service.insert_device_message(
                            device_id=dev_id,
                            direction="IN",
                            payload=frame,
                            protocol=protocol
                        )
                        last_heartbeat = time.time()
                        try:
                            self.device_service.update_heartbeat(dev_id)
                        except AttributeError:
                            pass

                    if time.time() - last_heartbeat > 30:
                        try:
                            self.device_service.update_heartbeat(dev_id)
                        except AttributeError:
                            pass
                        last_heartbeat = time.time()

            except Exception as e:
                print(f"❌ [Worker-{dev_name}] Lỗi kết nối: {e}")
                try:
                    driver.close()
                except:
                    pass
                self._stop_event.wait(5.0)

        try:
            driver.close()
        except:
            pass
        print(f"🏁 [Worker-{dev_name}] Đã dừng hoàn toàn.")