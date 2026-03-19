# tools/lis_simulator.py
import sys
import socket
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit


class LISSimulator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Giả lập Máy Xét nghiệm (ASTM Simulator)")
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Địa chỉ IP LIS Server (Phần mềm QC):"))
        self.txt_ip = QLineEdit("127.0.0.1")
        layout.addWidget(self.txt_ip)

        layout.addWidget(QLabel("Port:"))
        self.txt_port = QLineEdit("12345")
        layout.addWidget(self.txt_port)

        layout.addWidget(QLabel("Dữ liệu gửi (Mỗi dòng 1 record):"))
        self.txt_data = QTextEdit()
        # Dữ liệu mẫu chuẩn ASTM
        self.txt_data.setPlainText(
            "H|\^&|||Machine|||||||P|1\r"
            "P|1||12345||Doe^John||||||||\r"
            "O|1|Sample01||^^^GLU|R||||||N\r"
            "R|1|^^^GLU|5.6|mmol/L||N||F||\r"
            "R|2|^^^UREA|4.2|mmol/L||N||F||\r"
            "L|1|N\r"
        )
        layout.addWidget(self.txt_data)

        self.btn_send = QPushButton("Gửi Dữ liệu (TCP)")
        self.btn_send.clicked.connect(self.send_data)
        layout.addWidget(self.btn_send)

        self.lbl_status = QLabel("Sẵn sàng")
        layout.addWidget(self.lbl_status)

    def send_data(self):
        ip = self.txt_ip.text()
        port = int(self.txt_port.text())
        data = self.txt_data.toPlainText()

        # Thêm STX, ETX, Checksum (Giả lập đóng gói frame)
        # Trong thực tế phức tạp hơn, ở đây gửi raw text để test logic parse
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(data.encode('utf-8'))
                self.lbl_status.setText(f"Đã gửi {len(data)} bytes tới {ip}:{port}")
        except Exception as e:
            self.lbl_status.setText(f"Lỗi: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = LISSimulator()
    w.show()
    sys.exit(app.exec())