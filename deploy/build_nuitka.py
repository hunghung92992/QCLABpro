# -*- coding: utf-8 -*-
"""
Script Biên dịch QC Lab Manager ra C++ bằng NUITKA
Vị trí file: deploy/build_nuitka.py
"""
import os
import subprocess
import shutil
import sys

# --- 1. XÁC ĐỊNH ĐƯỜNG DẪN TƯƠNG ĐỐI ---
DEPLOY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEPLOY_DIR)
OUTPUT_DIR = os.path.join(DEPLOY_DIR, "Release")

print("🚀 ĐANG CHUẨN BỊ BIÊN DỊCH C++ VỚI NUITKA...")
print(f"📂 Thư mục gốc dự án: {PROJECT_ROOT}")
print(f"📂 Thư mục xuất file: {OUTPUT_DIR}\n")

# --- 2. DỌN DẸP THƯ MỤC BUILD CŨ ---
if os.path.exists(OUTPUT_DIR):
    print(f"🧹 Đang dọn dẹp thư mục {OUTPUT_DIR}...")
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- 3. TÌM TẤT CẢ MODULE GIAO DIỆN CHÌM ---
views_dir = os.path.join(PROJECT_ROOT, 'app', 'ui', 'views')
ui_modules = []

print("🔍 Đang quét các file giao diện (.py) để ép nạp vào C++...")
if os.path.exists(views_dir):
    for root, dirs, files in os.walk(views_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                module_name = rel_path.replace(os.sep, '.')[:-3]
                ui_modules.append(module_name)
    print(f"🎯 Đã tìm thấy {len(ui_modules)} modules giao diện.")
else:
    print("⚠️ Cảnh báo: Không tìm thấy thư mục views!")

# --- 4. XÂY DỰNG LỆNH NUITKA ---
main_script = os.path.join(PROJECT_ROOT, "app", "main.py")
icon_path = os.path.join(PROJECT_ROOT, "app", "assets", "logo.ico")

nuitka_cmd = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--windows-disable-console",
    f"--output-dir={OUTPUT_DIR}",
    "--enable-plugin=pyside6",
    "--enable-plugin=matplotlib",
    "--enable-plugin=numpy",
    "--include-package=qfluentwidgets",
    "--include-package=sqlalchemy",
    "--include-package=psycopg2",
    "--include-package=serial",

    # [UPDATE] Thêm 2 thư viện bắt buộc cho tính năng Auto Updater
    "--include-package=requests",
    "--include-package=packaging",
]

# Đính kèm Icon nếu có
if os.path.exists(icon_path):
    nuitka_cmd.append(f"--windows-icon-from-ico={icon_path}")

# Đính kèm thư mục Assets (Hình ảnh, logo)
assets_dir = os.path.join(PROJECT_ROOT, 'app', 'assets')
if os.path.exists(assets_dir):
    nuitka_cmd.append(f"--include-data-dir={assets_dir}=app/assets")

# [FIX] Chỉ đính kèm Alembic nếu dự án có sử dụng
migrations_dir = os.path.join(PROJECT_ROOT, 'migrations')
alembic_ini = os.path.join(PROJECT_ROOT, 'alembic.ini')

if os.path.exists(migrations_dir):
    nuitka_cmd.append(f"--include-data-dir={migrations_dir}=migrations")
    nuitka_cmd.append("--include-package=alembic")
if os.path.exists(alembic_ini):
    nuitka_cmd.append(f"--include-data-file={alembic_ini}=alembic.ini")

# Ép nạp các module giao diện
for mod in ui_modules:
    nuitka_cmd.append(f"--include-module={mod}")

# Cấu hình file đầu ra
nuitka_cmd.append("--output-filename=QCLabManager.exe")
nuitka_cmd.append(main_script)

# --- 5. THỰC THI BIÊN DỊCH ---
print(f"\n⚙️ BẮT ĐẦU DỊCH SANG C++ VÀ COMPILE (Quá trình này mất từ 5 - 20 phút)...")
print("Cảnh báo: Lần đầu chạy, Nuitka có thể sẽ hỏi tải C Compiler (MinGW64). Hãy nhập 'Yes' nếu được hỏi.\n")

try:
    subprocess.check_call(nuitka_cmd, cwd=PROJECT_ROOT)

    print("\n✅ BIÊN DỊCH THÀNH CÔNG RỰC RỠ!")
    print(f"👉 Toàn bộ mã nguồn đã được mã hóa thành C++.")
    print(f"👉 Phần mềm hoàn chỉnh nằm trong thư mục: deploy/Release/main.dist/")

    dist_dir = os.path.join(OUTPUT_DIR, "main.dist")
    final_dir = os.path.join(OUTPUT_DIR, "QCLabManager")

    if os.path.exists(dist_dir):
        if os.path.exists(final_dir):
            shutil.rmtree(final_dir)
        os.rename(dist_dir, final_dir)
        print(f"👉 Đã đổi tên thư mục thành: deploy/Release/QCLabManager/")

except subprocess.CalledProcessError as e:
    print(f"\n❌ LỖI BIÊN DỊCH NUITKA. Mã lỗi: {e.returncode}")
except Exception as e:
    print(f"\n❌ LỖI HỆ THỐNG: {e}")