# -*- coding: utf-8 -*-
import hashlib

# ⚠️ Copy y hệt SECRET_SALT từ file security.py sang đây
SECRET_SALT = "QCLabManager_Pro_2026_@NguyenHung_!#$"


def generate_license_key(hwid):
    raw_key = f"{hwid}_{SECRET_SALT}"
    full_hash = hashlib.sha256(raw_key.encode()).hexdigest().upper()
    key = f"{full_hash[:5]}-{full_hash[5:10]}-{full_hash[10:15]}-{full_hash[15:20]}"
    return key


print("=" * 50)
print("🔑 PHẦN MỀM TẠO KEY BẢN QUYỀN - QC LAB MANAGER")
print("=" * 50)

while True:
    hwid = input("\n📝 Nhập Mã Máy (HWID) do khách hàng gửi (Gõ 'exit' để thoát): ").strip()
    if hwid.lower() == 'exit':
        break
    if not hwid:
        continue

    license_key = generate_license_key(hwid)
    print(f"\n✅ Mã kích hoạt cho máy này là: {license_key}")
    print("👉 Hãy copy và gửi mã này cho khách hàng.")
    print("-" * 50)