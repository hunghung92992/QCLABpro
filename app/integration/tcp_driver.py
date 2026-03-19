# -*- coding: utf-8 -*-
"""
app/io/tcp_driver.py
[cite_start](Ported từ tcp_line.py [cite: 724, 725, 731])
Driver kết nối TCP và đọc dữ liệu theo dòng (line-based).
"""

import socket
import time
from typing import Optional


class TcpLineDriver:
    """
    Quản lý kết nối TCP socket và cung cấp hàm readline()
    để đọc dữ liệu dựa trên ký tự kết thúc dòng (EOL).
    """

    def __init__(self, host: str, port: int, timeout: float = 3.0, eol: bytes = b'\r'):
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self.eol = eol
        self.sock: Optional[socket.socket] = None
        self._buffer = b''  # Bộ đệm (buffer) dữ liệu đọc được

    def open(self):
        """Mở kết nối socket."""
        if self.sock:
            self.close()
        # [cite_start]Tạo kết nối mới [cite: 732]
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        # Đặt timeout thấp (0.1s) cho việc đọc (recv)
        # để vòng lặp readline không bị block quá lâu
        self.sock.settimeout(0.1)
        self._buffer = b''

    def close(self):
        """Đóng kết nối socket."""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # Bỏ qua lỗi nếu socket đã đóng
            self.sock.close()
            self.sock = None

    def readline(self, timeout: float = 1.0) -> Optional[bytes]:
        """
        Đọc một dòng dữ liệu (kết thúc bằng EOL) từ socket.
        Hàm này sẽ trả về None nếu không nhận được EOL trong khoảng 'timeout'.
        """
        start = time.time()
        while time.time() - start < timeout:
            # 1. Kiểm tra buffer trước
            if self.eol in self._buffer:
                line, self._buffer = self._buffer.split(self.eol, 1)
                return line + self.eol

            # 2. Nếu buffer không đủ, đọc thêm từ socket
            try:
                if not self.sock:
                    raise IOError("Socket is not open")

                # Đọc dữ liệu
                data = self.sock.recv(1024)
                if not data:
                    # Socket bị đóng bởi phía bên kia
                    raise IOError("Socket closed by peer")

                self._buffer += data

            except socket.timeout:
                # Đây là timeout của recv (0.1s), không phải timeout của readline
                # Chỉ có nghĩa là không có dữ liệu mới, tiếp tục vòng lặp
                time.sleep(0.05)  # Chờ 50ms
            except BlockingIOError:
                # Tương tự socket.timeout
                time.sleep(0.05)
            except IOError as e:
                # Lỗi socket nghiêm trọng (vd: mất kết nối)
                self.close()
                raise e  # Ném lỗi ra ngoài để worker_service biết và reconnect

        return None  # Hết thời gian chờ (timeout) của readline

    def write(self, data: bytes):
        """Gửi dữ liệu qua socket."""
        if not self.sock:
            self.open()
        if self.sock:
            self.sock.sendall(data)