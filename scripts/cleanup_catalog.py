# -*- coding: utf-8 -*-
"""
cleanup_catalog.py
Script chạy MỘT LẦN để xoá các Test Code không mong muốn khỏi Catalog mềm.
"""

import sys
import os

# Thêm thư mục gốc vào sys.path để có thể import 'app'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from app.services.catalog_service import CatalogService
except ImportError as e:
    print(f"LỖI: Không thể import. Hãy đảm bảo bạn chạy file này từ thư mục gốc QC_Manager_v3/")
    print(f"Chi tiết lỗi: {e}")
    sys.exit(1)


def cleanup_unwanted_tests():
    """
    Xác định và xóa các test code không mong muốn theo Phòng ban.
    """
    svc = CatalogService()

    # 🔴 BƯỚC 1: ĐỊNH NGHĨA DANH SÁCH CẦN XÓA
    # Bạn cần điền chính xác tên Phòng ban và Test Code cần xóa.

    # Ví dụ dựa trên yêu cầu của bạn:
    # Nếu "Huyết học" đang có test "Test_Cu_A" không hợp lệ:
    tests_to_delete = {
        "Huyết học": [
            "dadaa",  # Test Code không mong muốn
            "dad",
            "qas"# Ví dụ Test RBC cũ
        ],
        "HbA1c": [
            "Na+"  # Ví dụ: Test HbA1c bị lỗi trong quá trình import
        ],
        "Phòng Ban Khác": [
            # Thêm các test code khác nếu cần
        ]
    }

    # 🔴 BƯỚC 2: THỰC HIỆN XOÁ
    total_deleted = 0
    print("Bắt đầu dọn dẹp Catalog mềm...")

    for department, test_list in tests_to_delete.items():
        if not department: continue

        print(f"\n--- Xử lý Phòng ban: {department} ---")

        for test_name in test_list:
            if not test_name: continue

            # Hàm delete_test_from_catalog sử dụng LOWER(REPLACE(...)) để so khớp
            # không phân biệt khoảng trắng và chữ hoa/thường.
            was_deleted = svc.delete_test_from_catalog(department, test_name)

            if was_deleted:
                print(f"   [OK] Đã xoá test: {test_name}")
                total_deleted += 1
            else:
                print(f"   [INFO] Bỏ qua test: {test_name} (Không tìm thấy trong Catalog mềm)")

    print(f"\n--- HOÀN TẤT ---")
    print(f"Tổng số test code đã bị xoá khỏi Catalog mềm: {total_deleted}")


if __name__ == "__main__":
    cleanup_unwanted_tests()