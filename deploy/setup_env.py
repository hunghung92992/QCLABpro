import subprocess
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_ROOT, ".venv")

def run(cmd):
    print(f"> {cmd}")
    subprocess.check_call(cmd, shell=True)

def main():
    print("=== SETUP ENV FOR QClab_Manager (PyCharm Interpreter) ===")

    # Kiểm tra python đang chạy script
    print(f"→ Python đang dùng: {sys.executable}")
    print(f"→ Version: {sys.version}")

    if not sys.version.startswith("3.12"):
        print("❌ Script này PHẢI được chạy bằng Python 3.12")
        print("👉 Trong PyCharm: Run setup_env.py bằng interpreter Python 3.12")
        sys.exit(1)

    if not os.path.exists(VENV_DIR):
        print("→ Tạo virtual environment (.venv)")
        run(f'"{sys.executable}" -m venv .venv')
    else:
        print("→ .venv đã tồn tại")

    python_exe = os.path.join(VENV_DIR, "Scripts", "python.exe")

    run(f'"{python_exe}" -m pip install --upgrade pip setuptools wheel')
    run(f'"{python_exe}" -m pip install PySide6 qfluentwidgets')
    run(f'"{python_exe}" --version')

    print("✅ SETUP HOÀN TẤT")
    print("👉 Gán PyCharm interpreter: .venv\\Scripts\\python.exe")

if __name__ == "__main__":
    main()