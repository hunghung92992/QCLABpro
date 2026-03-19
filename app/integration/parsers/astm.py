import re


class ASTMParser:
    def __init__(self):
        self.buffer = ""

    def parse_frame(self, data: str) -> dict:
        """
        Phân tích chuỗi ASTM.
        Trả về Dictionary chứa thông tin mẫu và danh sách kết quả.
        Output:
        {
            "sample_id": "QC_LEVEL_1",
            "results": [
                {'test_code': 'GLU', 'value': 5.5, 'unit': 'mmol/L'},
                ...
            ]
        }
        """
        parsed_data = {
            "sample_id": None,
            "results": []
        }

        # 1. Làm sạch dữ liệu (Xóa STX \x02, ETX \x03, và checksum nếu có)
        # Thông thường ASTM frame bắt đầu bằng STX và kết thúc bằng ETX/ETB + Checksum + CR LF
        clean_data = data.strip()

        # Tách dòng
        records = clean_data.split('\r')  # ASTM chuẩn dùng \r làm record delimiter

        for rec in records:
            rec = rec.strip()
            if not rec: continue

            # Xóa số thứ tự dòng ở đầu (VD: 1O|... -> O|...) nếu máy gửi kèm
            # Hoặc xử lý STX dính ở đầu
            rec = re.sub(r'^[\x02\d]*', '', rec)

            fields = rec.split('|')
            if len(fields) < 2: continue

            rec_type = fields[0]

            # --- XỬ LÝ ORDER (O) -> Lấy Sample ID ---
            if rec_type == 'O':
                try:
                    # ASTM field O: |Seq|SampleID|InstrumentSpec|...
                    # Thường SampleID nằm ở vị trí index 2 (field thứ 3)
                    if len(fields) > 2:
                        # Barcode máy gửi lên thường nằm đây
                        raw_sid = fields[2].strip()
                        # Xử lý nếu máy gửi kèm ^ (VD: ^Barcode^)
                        parsed_data["sample_id"] = raw_sid.split('^')[0].strip()
                except Exception as e:
                    print(f"[ASTM] Lỗi parse Sample ID: {e}")

            # --- XỬ LÝ RESULT (R) -> Lấy Kết quả ---
            elif rec_type == 'R':
                try:
                    # Cấu trúc: R|seq|^^^TestCode|Value|Unit|...
                    # Field 2: Test ID (VD: ^^^GLU^...)
                    test_field = fields[2]
                    # Lấy phần text nằm giữa các dấu ^ hoặc lấy nguyên
                    parts = test_field.split('^')
                    # Thông thường mã nằm ở part 3 (^^^GLU) -> index 3
                    # Nhưng để an toàn, ta lấy phần tử dài nhất hoặc phần tử thứ 4 (index 3)
                    test_code = ""
                    for p in parts:
                        if p.strip():
                            test_code = p.strip()
                            break  # Lấy cái non-empty đầu tiên (Thường là mã)

                    if len(parts) >= 4 and parts[3].strip():
                        test_code = parts[3].strip()  # Ưu tiên vị trí chuẩn ASTM

                    # Field 3: Giá trị
                    val_str = fields[3].strip()

                    # Field 4: Đơn vị
                    unit = fields[4].strip() if len(fields) > 4 else ""

                    # Xử lý convert Value sang Float (Quan trọng cho IQC)
                    final_val = self._safe_float(val_str)

                    if test_code and final_val is not None:
                        parsed_data["results"].append({
                            "test_code": test_code,
                            "value": final_val,
                            "unit": unit,
                            "raw_value": val_str  # Lưu lại giá trị gốc phòng khi cần (VD: "Positive")
                        })
                except Exception as e:
                    print(f"[ASTM] Lỗi parse dòng R: {rec} -> {e}")

        return parsed_data

    def _safe_float(self, value_str: str):
        """Chuyển đổi chuỗi sang float an toàn, xử lý các dấu <, >"""
        try:
            # Xóa các ký tự không phải số (trừ dấu chấm và dấu âm)
            # VD: "< 0.5" -> "0.5", "High" -> None
            clean_str = re.sub(r'[^\d.-]', '', value_str)
            if not clean_str: return None
            return float(clean_str)
        except:
            return None

    @staticmethod
    def calculate_checksum(frame: str) -> str:
        """Tính checksum chuẩn ASTM (tổng ASCII % 256)."""
        total = sum(ord(c) for c in frame)
        return hex(total % 256)[2:].upper().zfill(2)