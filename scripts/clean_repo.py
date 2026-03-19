# scripts/clean_repo.py
import os
import shutil
from pathlib import Path


def clean_repo():
    print("🚀 Bắt đầu dọn dẹp Repository...")
    # Lấy thư mục gốc (lùi 1 cấp nếu file này nằm trong thư mục scripts/)
    root_dir = Path(__file__).resolve().parent.parent

    # 1. Các thư mục cần xóa
    target_dirs = ['build', 'dist', 'Output', 'logs', 'backups', '.pytest_cache']
    for d in target_dirs:
        dir_path = root_dir / d
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"🗑️ Đã xóa thư mục: {d}")

    # 2. Xóa toàn bộ __pycache__
    cache_count = 0
    for p in root_dir.rglob('__pycache__'):
        shutil.rmtree(p)
        cache_count += 1
    print(f"🗑️ Đã dọn dẹp {cache_count} thư mục __pycache__")

    # 3. Xóa các file runtime rác (chỉ quét ở thư mục dự án, không chạm vào AppData)
    target_files = ['*.pyc', '*.log', '*.bak']
    # Cẩn thận: Nếu bạn có file Datauser.db mẫu cần giữ lại để build Inno Setup,
    # hãy copy nó ra chỗ khác trước khi thêm '*.db' vào danh sách này.

    for pattern in target_files:
        for f in root_dir.rglob(pattern):
            try:
                f.unlink()
                print(f"🗑️ Đã xóa file rác: {f.name}")
            except Exception as e:
                pass

    print("✅ HOÀN TẤT DỌN DẸP REPO!")


if __name__ == '__main__':
    clean_repo()