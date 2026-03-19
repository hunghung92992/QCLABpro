# -*- coding: utf-8 -*-
"""
/serial_driver.py
[cite_start](Ported từ serial_line.py [cite: 724, 725, 731])
Driver kết nối cổng Serial (COM) và đọc dữ liệu theo dòng.
"""

import time
from typing import Optional

# Yêu cầu 'pyserial'
try:
    import serial

    HAS_PYSERIAL = True
except ImportError:
    print("FATAL: 'pyserial' package is required for serial communication.")
    print("Hãy chạy: pip install pyserial")
    HAS_PYSERIAL = False
    serial = None  # Placeholder


class SerialLineDriver:
    """
    Quản lý kết nối cổng Serial và cung cấp hàm readline()
    để đọc dữ liệu dựa trên ký tự kết thúc dòng (EOL).
    """

    def __init__(self, port: str, baudrate: int = 9600,
                 parity: str = 'N', stopbits: int = 1,
                 timeout: float = 1.0, eol: bytes = b'\r'):

        if not HAS_PYSERIAL:
            raise ImportError("Không thể tải thư viện 'pyserial'.")

        self.port = port
        self.baudrate = int(baudrate)
        # [cite_start]Đảm bảo parity/stopbits hợp lệ [cite: 731]
        self.parity = parity.upper() if parity and parity.upper() in ('N', 'E', 'O', 'M', 'S') else 'N'
        self.stopbits = int(stopbits) if int(stopbits) in (1, 2) else 1

        self.timeout = timeout  # Timeout cho serial.Serial.read()
        self.eol = eol
        self.ser: Optional[serial.Serial] = None
        self._buffer = b''

    def open(self):
        """Mở kết nối Serial."""
        if self.ser:
            self.close()
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            parity=self.parity,
            stopbits=self.stopbits,
            timeout=self.timeout  # Timeout cho read()
        )
        self._buffer = b''

    def close(self):
        """Đóng kết nối Serial."""
        if self.ser:
            self.ser.close()
            self.ser = None

    def readline(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Đọc một dòng dữ liệu (kết thúc bằng EOL) từ cổng serial.
        Hàm này sẽ trả về None nếu không nhận được EOL trong khoảng 'timeout'.
        """
        if not self.ser:
            self.open()
        if not self.ser:
            raise IOError("Không thể mở cổng Serial.")

        # 1. Kiểm tra buffer trước
        if self.eol in self._buffer:
            line, self._buffer = self._buffer.split(self.eol, 1)
            return line + self.eol

        start = time.time()
        while time.time() - start < timeout:
            try:
                # 2. Đọc dữ liệu mới (nếu có)
                # Đọc số byte đang chờ, hoặc 1 byte (tránh đọc 0)
                bytes_to_read = self.ser.in_waiting or 1
                data = self.ser.read(bytes_to_read)

                if data:
                    self._buffer += data
                    # Kiểm tra lại buffer sau khi đọc
                    if self.eol in self._buffer:
                        line, self._buffer = self._buffer.split(self.eol, 1)
                        return line + self.eol
                else:
                    # Không có dữ liệu (serial read timeout)
                    time.sleep(0.05)  # Chờ

            except serial.SerialException as e:
                self.close()
                raise IOError(f"Serial error: {e}")  # Ném lỗi để worker reconnect

        return None  # Hết thời gian chờ (timeout) của readline

    def write(self, data: bytes):
        """Gửi dữ liệu qua cổng Serial."""
        if not self.ser:
            self.open()
        if self.ser:
            self.ser.write(data)