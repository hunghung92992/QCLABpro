# -*- coding: utf-8 -*-
import os
import sys
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_all

# Xác định thư mục gốc của dự án (nơi chứa file script này lùi ra 1 cấp)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("🚀 Đang chuẩn bị đóng gói QC Lab Manager...")

# --- 1. CẤU HÌNH ICON CHO FILE EXE ---
exe_icon_path = os.path.join(PROJECT_ROOT, 'app', 'assets', 'logo.ico')
icon_option = []

if os.path.exists(exe_icon_path):
    print(f"✅ Tìm thấy Exe Icon: {exe_icon_path}")
    icon_option = [f'--icon={exe_icon_path}']
else:
    print(f"⚠️ Cảnh báo: Không thấy file '{exe_icon_path}'. Exe sẽ dùng icon mặc định.")

# --- 2. THU THẬP TÀI NGUYÊN (UI & Thư viện ẩn) ---
# Lấy toàn bộ tài nguyên của qfluentwidgets (bao gồm cả SVG icons)
datas, binaries, hiddenimports = collect_all('qfluentwidgets')

# Bổ sung các thư viện ẩn cốt lõi của dự án
hiddenimports += [
    'app.core.config',
    'app.services.sync_worker',
    'pandas',
    'openpyxl',
    'jinja2',
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.ext.declarative',
    'psycopg2',           # Driver cho PostgreSQL
    'serial',             # Thư viện đọc cổng COM LIS
    'alembic',            # Thư viện tự động nâng cấp DB
    'PySide6.QtSvg',      # Cứu các icon SVG bị mất
    'PySide6.QtNetwork',  # Hỗ trợ kết nối mạng
]

# 👇👇👇 [GIẢI PHÁP TRIỆT ĐỂ: QUÉT ÉP BUỘC TỪNG FILE GIAO DIỆN] 👇👇👇
# Tự động chui vào từng ngóc ngách của thư mục views để "bắt" các file .py
views_dir = os.path.join(PROJECT_ROOT, 'app', 'ui', 'views')
print(f"\n🔍 Đang quét ép buộc thư mục giao diện: {views_dir}")

if os.path.exists(views_dir):
    count = 0
    for root, dirs, files in os.walk(views_dir):
        for file in files:
            # Bỏ qua các file hệ thống như __init__.py hay __pycache__
            if file.endswith('.py') and not file.startswith('__'):
                # Cắt lấy đường dẫn tương đối. VD: app\ui\views\overview\overview_page.py
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                # Đổi dấu chéo (slash) thành dấu chấm: app.ui.views.overview.overview_page
                module_name = rel_path.replace(os.sep, '.')[:-3]
                hiddenimports.append(module_name)
                print(f"   ✅ Đã ép nạp module: {module_name}")
                count += 1
    print(f"🎯 Đã nạp thành công {count} module giao diện!")
else:
    print(f"⚠️ KHÔNG TÌM THẤY THƯ MỤC: {views_dir}")
print("="*50)

# --- 3. QUAN TRỌNG: COPY TÀI NGUYÊN TĨNH VÀO EXE ---
# Chỉ copy assets (ảnh, logo) và các file cấu trúc Database (Alembic)
custom_datas = [
    (os.path.join(PROJECT_ROOT, 'app', 'assets'), os.path.join('app', 'assets')),
    (os.path.join(PROJECT_ROOT, 'migrations'), 'migrations'),
    (os.path.join(PROJECT_ROOT, 'alembic.ini'), '.'),
]

for src, dst in custom_datas:
    if os.path.exists(src):
        datas.append((src, dst))
        print(f"📦 Đã đính kèm: {src} -> {dst}")
    else:
        print(f"⚠️ Bỏ qua (không tìm thấy): {src}")

# Chuẩn bị cú pháp data cho PyInstaller
data_options = [f'--add-data={src}{os.pathsep}{dst}' for src, dst in datas]

# --- 4. CHẠY PYINSTALLER ---
app_name = 'QCLabManager'
main_script = os.path.join(PROJECT_ROOT, 'app', 'main.py')

print(f"\n⚙️ Bắt đầu tiến trình biên dịch (Vui lòng chờ 1-3 phút)...")

PyInstaller.__main__.run([
    main_script,
    f'--name={app_name}',
    '--onedir',     # Đóng gói dạng thư mục (Load nhanh, dễ sửa lỗi)
    '--noconsole',  # Tắt màn hình đen (Terminal)
    '--windowed',
    '--clean',
    '-y',           # Ghi đè thư mục dist không cần hỏi

    *icon_option,
    *data_options,
    *[f'--hidden-import={h}' for h in hiddenimports],
])

print(f"\n✅ ĐÓNG GÓI THÀNH CÔNG!")
print(f"👉 Thư mục phần mềm: dist/{app_name}/")
print(f"👉 File chạy chính: dist/{app_name}/{app_name}.exe")
print(f"👉 Dữ liệu Runtime (DB, Log, Backup) đã được phân luồng an toàn về AppData/Local.")