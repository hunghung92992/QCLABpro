# -*- coding: utf-8 -*-
"""
upgrade_tool_v2.py
Công cụ nâng cấp PySide6 thông minh hơn.
Sửa lỗi Table, Header và Enum instance.
"""
import os
import re

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSIONS = (".py",)
IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "backups", "logs"}


def fix_content(content):
    changes = []
    original = content

    # 1. Cơ bản: PyQt5 -> PySide6, exec_() -> exec()
    if "PyQt5" in content:
        content = content.replace("PyQt5", "PySide6")
        changes.append("PyQt5->PySide6")
    if ".exec()" in content:
        content = content.replace(".exec()", ".exec()")
        changes.append("exec_()->exec()")
    if "backend_qt5agg" in content:
        content = content.replace("backend_qt5agg", "backend_qtagg")
        changes.append("Matplotlib Backend")

    # 2. Sửa lỗi Enum gọi từ biến (QUAN TRỌNG)
    # self.tbl.NoEditTriggers -> QAbstractItemView.NoEditTriggers
    # self.table.SelectRows -> QAbstractItemView.SelectRows

    # Regex tìm: (bất kỳ ký tự nào).NoEditTriggers
    if "NoEditTriggers" in content:
        content = re.sub(r"[\w\.]+\.NoEditTriggers", "QAbstractItemView.NoEditTriggers", content)
        changes.append("Fix NoEditTriggers")
        # Đảm bảo đã import QAbstractItemView
        if "QAbstractItemView" not in content:
            content = "from PySide6.QtWidgets import QAbstractItemView\n" + content

    if "SelectRows" in content:
        content = re.sub(r"[\w\.]+\.SelectRows", "QAbstractItemView.SelectRows", content)
        changes.append("Fix SelectRows")

    if "SingleSelection" in content:
        content = re.sub(r"[\w\.]+\.SingleSelection", "QAbstractItemView.SingleSelection", content)
        changes.append("Fix SingleSelection")

    # 3. Sửa lỗi HeaderView
    if "ResizeToContents" in content and "QHeaderView" not in content:
        # Nếu code dùng self.tbl.horizontalHeader().ResizeToContents
        # Ta sửa thành QHeaderView.ResizeToContents (nhờ qt_compat patch)
        content = re.sub(r"[\w\.]+\.ResizeToContents", "QHeaderView.ResizeToContents", content)
        changes.append("Fix ResizeToContents")
        if "QHeaderView" not in content:
            content = "from PySide6.QtWidgets import QHeaderView\n" + content

    return content, changes


def main():
    print("🚀 Bắt đầu quét và sửa lỗi V2...")
    count = 0
    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            if not file.endswith(EXTENSIONS) or file == "upgrade_tool.py": continue

            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                new_content, changes = fix_content(content)

                if new_content != content:
                    with open(path, "w", encoding="utf-8") as f: f.write(new_content)
                    print(f"✅ Đã sửa: {file} | {', '.join(changes)}")
                    count += 1
            except Exception as e:
                print(f"⚠️ Lỗi {file}: {e}")

    print(f"\n🏁 Xong! Đã sửa {count} file. Hãy chạy lại main.py.")


if __name__ == "__main__":
    main()