import socket
import time
import sys

# ==========================================
# CẤU HÌNH SERVER
# ==========================================
HOST = '127.0.0.1'  # Localhost (Chạy trên cùng máy tính)
PORT = 12345  # Cổng kết nối (Phải khớp với cấu hình trong phần mềm QC)

# ==========================================
# DỮ LIỆU GIẢ LẬP (MẪU ASTM)
# ==========================================
# Cấu trúc: Header -> Patient -> Order -> Results -> Terminator
# \r\n: Xuống dòng chuẩn
# \x04: Ký tự EOT (End of Transmission) để báo cho phần mềm biết đã hết dữ liệu
# Lưu ý: Test Code ở đây là GLU, AST, ALT.
# Phần mềm của bạn sẽ tự động map (VD: AST -> AST (GOT)) nhờ tính năng Smart Mapping.
DATA_TO_SEND = (
    "H|\\^&|||Simulated_Analyzer|||||Host||P|1|20260202100000\r\n"
    "P|1||PID_123|||||||||||||||||||||||||\r\n"
    "O|1|||LOT1|False||||||||||Serum\r\n"
    "R|1|AST||U/L||||45.2||||F\r\n"
    "R|2|ALT||U/L||||32.5||||F\r\n"
      "L|1|N\r\n"
    "\x04"
).encode('utf-8')  # Chuyển chuỗi thành bytes để gửi qua mạng


def start_server():
    """Khởi chạy TCP Server lắng nghe kết nối"""
    try:
        # Tạo socket IPv4, TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Cho phép dùng lại cổng ngay lập tức sau khi tắt (tránh lỗi Address already in use)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Gắn socket vào IP và Port
            s.bind((HOST, PORT))

            # Bắt đầu lắng nghe
            s.listen()
            print(f"\n✅ SERVER GIẢ LẬP ĐANG CHẠY TẠI: {HOST}:{PORT}")
            print("⏳ Đang chờ phần mềm QC kết nối...")
            print("-------------------------------------------------")

            while True:
                # Chấp nhận kết nối từ phần mềm QC
                conn, addr = s.accept()
                with conn:
                    print(f"🔗 [MỚI] Phần mềm đã kết nối từ: {addr}")

                    time.sleep(0.5)  # Giả lập độ trễ xử lý

                    print(f"📤 Đang gửi dữ liệu ({len(DATA_TO_SEND)} bytes)...")
                    conn.sendall(DATA_TO_SEND)
                    print("✅ Gửi hoàn tất.")

                    # [THÊM DÒNG NÀY] Chờ 2 giây để Client kịp nhận dữ liệu trước khi đóng
                    time.sleep(2)

                    print("Đóng kết nối.")
                    print("-------------------------------------------------")
                    # Kết nối tự động đóng khi thoát khỏi block 'with conn'

    except KeyboardInterrupt:
        print("\n🛑 Đã dừng Server.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Lỗi Server: {e}")


if __name__ == "__main__":
    start_server()