# -*- coding: utf-8 -*-
"""
app/features/catalog/catalog_detail_dialog.py
(FIXED: Signal connection & Data loading)
"""
from __future__ import annotations
from typing import Optional, Dict, Any
import json
# Import PySide6
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCompleter, QFormLayout,
    QMessageBox
)
# Import Fluent Widgets
from qfluentwidgets import (
    MessageBoxBase, LineEdit, ComboBox, EditableComboBox,
    DoubleSpinBox, SpinBox, PushButton, FluentIcon as FIF,
    StrongBodyLabel, BodyLabel, SubtitleLabel
)
# Import services
from app.services.department_service import DepartmentService
from app.services.catalog_service import CatalogService


# --- Helper ---
def _parse_meta_from_note(note: Optional[str]) -> Dict[str, Any]:
    if not note or not str(note).strip().startswith("{"):
        return {}
    try:
        obj = json.loads(note)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {}


def _merge_meta(note: Optional[str], patch: Dict[str, Any]) -> str:
    base = _parse_meta_from_note(note)
    for k, v in (patch or {}).items():
        if v is None or v == "":
            if k in base:
                del base[k]
        else:
            base[k] = v
    return json.dumps(base, ensure_ascii=False)


# --- DATA LISTS ---
SEMI_RANGE_LIST = [
                      'neg', 'negative', 'âm tính', 'âm', '-', 'norm', 'normal', 'bình thường', '0', '0.0',
                      '+-', 'trace', 'tr', 'vết', '±', '0.5', '5', '0.15',
                      '1+', '+1', 'pos', 'positive', 'dương tính', 'dương', '10', '15', '2.8', '0.3', '8.8', '3.2',
                      '2+', '+2', '25', '5.5', '1.0', '1', '17', '1.5', '16', '70',
                      '3+', '+3', '80', '14', '3.0', '3', '33', '4.0', '4', '125',
                      '4+', '+4', '200', '28', '100', '8.0', '8', '500',
                      '5+', '+5', '55', '6+', '+6'
                  ] + [f"{x:.1f}" for x in [4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0]] + \
                  ['1.000', '1.005', '1.010', '1.015', '1.020', '1.025', '1.030', '1.035']

SEMI_TYPES = {
    "Tùy chỉnh (Custom)": SEMI_RANGE_LIST,
    "Loại 1 (POS/NEG)": ['NEG', 'POS'],
    "Loại 2 (0+, 1+, trace...)": ['0+', '+-', 'trace', '1+', '2+', '3+', '4+', '5+'],
    "Loại 4 (Tỷ trọng)": ['1.000', '1.005', '1.010', '1.015', '1.020', '1.025', '1.030', '1.035']
}


# --- Main Dialog ---
class CatalogDetailDialog(MessageBoxBase):
    """
    Dialog to Add/Edit Analyte (Quant/Semi/Qual).
    """

    def __init__(self,
                 parent: QWidget,
                 dept_name: str,
                 catalog_service: CatalogService,
                 dept_service: Optional[DepartmentService] = None,
                 prefill: Optional[Dict[str, Any]] = None,
                 prefill_lot_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)

        self.setWindowTitle(f"Chỉ số cho: {dept_name}")

        # [FIX] 1. KHỞI TẠO LABEL TRƯỚC (Bắt buộc phải có dòng này trước _build_ui)
        self.titleLabel = SubtitleLabel(f"Chỉ số cho: {dept_name}", self)

        self.catalog_service = catalog_service
        self.dept_service = dept_service or DepartmentService()
        self.dept_name = dept_name
        self.prefill = prefill
        self.prefill_lot_data = prefill_lot_data or {}

        # 2. SAU ĐÓ MỚI XÂY DỰNG GIAO DIỆN
        self._build_ui()

        # 3. Kết nối sự kiện (Signal/Slot)
        self.cb_dep.currentIndexChanged.connect(self._on_dep_changed)
        self.cb_test.currentTextChanged.connect(self._on_test_changed)
        self.btn_recalc.clicked.connect(self._on_recalculate_stats)

        # 4. Nạp dữ liệu
        self._load_departments()

        # ... (Phần xử lý prefill và select department giữ nguyên như cũ)
        dep_to_select = (self.prefill or {}).get("department") or self.dept_name
        if dep_to_select:
            idx = self.cb_dep.findText(str(dep_to_select))
            if idx >= 0:
                self.cb_dep.setCurrentIndex(idx)
            else:
                # Fallback tìm theo ID nếu tên không khớp
                # Fallback tìm theo ID dùng danh sách song song
                dep_id = self.prefill_lot_data.get("department_id")
                if dep_id and hasattr(self, '_dep_ids'):
                    try:
                        # Tìm vị trí của ID này trong danh sách
                        target_index = self._dep_ids.index(str(dep_id))
                        self.cb_dep.setCurrentIndex(target_index)
                    except ValueError:
                        print(f"⚠️ Không tìm thấy ID {dep_id} trong danh sách phòng ban.")

        if self.prefill:
            self._load_existing(self.prefill)

        self._update_semi_target_ui()
        self._update_semi_ref_range_ui()

        # Config Buttons
        self.yesButton.setText("Lưu")
        self.cancelButton.setText("Hủy")
        try:
            self.yesButton.clicked.disconnect()
        except:
            pass
        self.yesButton.clicked.connect(self._on_save)

    def _build_ui(self):
        # 1. Header
        self.viewLayout.addWidget(self.titleLabel)

        # 2. Form Inputs
        self.cb_dep = ComboBox(self)

        self.cb_test = EditableComboBox(self)
        self.cb_test.setPlaceholderText("Gõ để tìm hoặc thêm mới...")

        self._test_model = QStandardItemModel(self)
        self._test_completer = QCompleter(self._test_model, self)
        # Use CaseInsensitive (PySide6 standard)
        self._test_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.cb_test.setCompleter(self._test_completer)

        self.cb_level = ComboBox(self)
        self.cb_level.addItems(["L1", "L2", "L3"])

        self.cb_dtype = ComboBox(self)
        self.cb_dtype.addItem("Định lượng (Quantitative)", "Quant")
        self.cb_dtype.addItem("Bán định lượng (Semi-Quantitative)", "Semi")
        self.cb_dtype.addItem("Định tính (Qualitative)", "Qual")

        self.cb_cat = EditableComboBox(self)
        self.cb_cat.addItems(["", "Clinical Chemistry", "Immunology", "Urinalysis", "Hematology", "Electrolytes"])

        # --- Quant Block ---
        self._quant_box_widget = QWidget()
        quant_form = QFormLayout(self._quant_box_widget)
        quant_form.setContentsMargins(0, 0, 0, 0)

        self.cb_unit = EditableComboBox(self)
        self.cb_unit.setPlaceholderText("Đơn vị (tự động điền)")

        self.sp_mean = DoubleSpinBox(self)
        self.sp_mean.setRange(-1e12, 1e12)
        self.sp_mean.setDecimals(4)

        self.sp_sd = DoubleSpinBox(self)
        self.sp_sd.setRange(0.0, 1e12)
        self.sp_sd.setDecimals(4)

        self.sp_tea = DoubleSpinBox(self)
        self.sp_tea.setRange(-1e12, 1e12)
        self.sp_tea.setDecimals(4)

        self.btn_recalc = PushButton(FIF.SYNC, "Tính lại Mean/SD từ IQC", self)
        self.btn_recalc.setToolTip("Tính Mean/SD từ 500 điểm IQC gần nhất của LOT này.")

        quant_form.addRow("Đơn vị *", self.cb_unit)
        quant_form.addRow("Mean", self.sp_mean)
        quant_form.addRow("SD", self.sp_sd)
        quant_form.addRow("TEa", self.sp_tea)
        quant_form.addRow("", self.btn_recalc)

        # --- Semi Block ---
        self._semi_box_widget = QWidget()
        semi_form = QFormLayout(self._semi_box_widget)
        semi_form.setContentsMargins(0, 0, 0, 0)
        self.cb_semi_type = ComboBox(self)
        self.cb_semi_type.addItems(SEMI_TYPES.keys())

        self.cb_target_semi = EditableComboBox(self)

        self.semi_ref_range_widget = QWidget()
        self.semi_ref_range_layout = QHBoxLayout(self.semi_ref_range_widget)
        self.semi_ref_range_layout.setContentsMargins(0, 0, 0, 0)

        self.semi_ref_from_cb = EditableComboBox(self)
        self.semi_ref_to_cb = EditableComboBox(self)

        self.semi_ref_range_layout.addWidget(BodyLabel("Từ", self))
        self.semi_ref_range_layout.addWidget(self.semi_ref_from_cb, 1)
        self.semi_ref_range_layout.addWidget(BodyLabel("Đến", self))
        self.semi_ref_range_layout.addWidget(self.semi_ref_to_cb, 1)

        self.ed_ref_semi_text = LineEdit(self)
        self.ed_ref_semi_text.setReadOnly(True)

        semi_form.addRow("Loại Bán định lượng", self.cb_semi_type)
        semi_form.addRow("Target (Giá trị đích)", self.cb_target_semi)
        semi_form.addRow("Reference Range", self.semi_ref_range_widget)
        semi_form.addRow(self.ed_ref_semi_text)

        self.cb_semi_type.currentIndexChanged.connect(self._update_semi_target_ui)
        self.cb_target_semi.textChanged.connect(self._update_semi_ref_range_ui)

        # --- Qual Block ---
        self._qual_box_widget = QWidget()
        qual_form = QFormLayout(self._qual_box_widget)
        qual_form.setContentsMargins(0, 0, 0, 0)

        self.cb_target_qual = EditableComboBox(self)
        self.cb_target_qual.addItems(["NEG", "POS"])

        self.ed_ref_qual_text = LineEdit(self)
        self.ed_ref_qual_text.setReadOnly(True)

        qual_form.addRow("Target/Expected", self.cb_target_qual)
        qual_form.addRow("Reference Range", self.ed_ref_qual_text)

        self.cb_target_qual.currentTextChanged.connect(self._update_qual_ref_range_ui)

        # Footer
        self.ed_note = LineEdit(self)
        self.ed_note.setPlaceholderText("Ghi chú (tuỳ chọn)")

        self.sp_sort_order = SpinBox(self)
        self.sp_sort_order.setRange(0, 9999)
        self.sp_sort_order.setToolTip("Số nhỏ hơn sẽ xếp trước")

        # Layout Assembly
        self.viewLayout.addWidget(StrongBodyLabel("Thông tin", self))
        self.viewLayout.addWidget(self.cb_dep)
        self.viewLayout.addWidget(self.cb_test)

        h_info = QHBoxLayout()
        v_lvl = QVBoxLayout()
        v_lvl.addWidget(BodyLabel("Level *", self))
        v_lvl.addWidget(self.cb_level)
        v_dt = QVBoxLayout()
        v_dt.addWidget(BodyLabel("Kiểu dữ liệu", self))
        v_dt.addWidget(self.cb_dtype)
        v_cat = QVBoxLayout()
        v_cat.addWidget(BodyLabel("Phân loại", self))
        v_cat.addWidget(self.cb_cat)
        h_info.addLayout(v_lvl)
        h_info.addLayout(v_dt)
        h_info.addLayout(v_cat)
        self.viewLayout.addLayout(h_info)

        self.viewLayout.addWidget(self._quant_box_widget)
        self.viewLayout.addWidget(self._semi_box_widget)
        self.viewLayout.addWidget(self._qual_box_widget)

        h_foot = QHBoxLayout()
        v_sort = QVBoxLayout()
        v_sort.addWidget(BodyLabel("Thứ tự", self))
        v_sort.addWidget(self.sp_sort_order)
        v_note = QVBoxLayout()
        v_note.addWidget(BodyLabel("Ghi chú", self))
        v_note.addWidget(self.ed_note)
        h_foot.addLayout(v_sort)
        h_foot.addLayout(v_note)
        self.viewLayout.addLayout(h_foot)

        self.widget.setMinimumWidth(550)

        self.cb_dtype.currentIndexChanged.connect(self._apply_dtype_layout)
        self._apply_dtype_layout()
        self._update_qual_ref_range_ui()

    def _load_departments(self):
        """
        Nạp phòng ban và lưu ID vào danh sách riêng (self._dep_ids).
        Cách này KHÔNG phụ thuộc vào ComboBox, đảm bảo không bao giờ lỗi.
        """
        self.cb_dep.blockSignals(True)
        self.cb_dep.clear()

        # Khởi tạo danh sách ID song song (reset lại)
        # Index 0 là dòng trống tương ứng với item trống trong ComboBox
        self._dep_ids = [None]
        self.cb_dep.addItem("")

        try:
            print("--- [BẮT ĐẦU NẠP PHÒNG BAN (PARALLEL MODE)] ---")
            deps = self.dept_service.list_departments(active_only=False)

            for d in deps:
                # Lấy dữ liệu an toàn
                if isinstance(d, dict):
                    name = d.get('name')
                    uid = d.get('id')
                else:
                    name = getattr(d, 'name', "")
                    uid = getattr(d, 'id', None)

                if name and uid:
                    str_uid = str(uid)
                    print(f"   -> Map: [{len(self._dep_ids)}] {name} = {str_uid}")

                    # 1. Thêm tên vào giao diện
                    self.cb_dep.addItem(str(name))

                    # 2. Thêm ID vào danh sách song song
                    self._dep_ids.append(str_uid)

        except Exception as e:
            print(f"❌ Lỗi nạp phòng ban: {e}")

        print("--- [KẾT THÚC NẠP] ---")
        self.cb_dep.blockSignals(False)

    def _reload_testname_suggestions(self, force_dep_id=None):
        dep_id = force_dep_id
        # ... (logic lấy dep_id giữ nguyên)
        if not dep_id:
            idx = self.cb_dep.currentIndex()
            if hasattr(self, '_dep_ids') and 0 <= idx < len(self._dep_ids):
                dep_id = self._dep_ids[idx]

        print(f"--> [DEBUG LOAD TEST] Đang gọi xét nghiệm cho ID: {dep_id}")

        self._cached_tests = []
        test_names = []

        if dep_id:
            try:
                raw_result = self.dept_service.list_tests_by_department(str(dep_id))

                # [FIX QUAN TRỌNG]: Chuẩn hóa về List
                # Nếu kết quả không phải là list (ví dụ là 1 object đơn lẻ), ép nó vào list
                if not isinstance(raw_result, list):
                    if raw_result is not None:
                        tests = [raw_result]
                    else:
                        tests = []
                else:
                    tests = raw_result

                self._cached_tests = tests  # Đã chắc chắn là List
                print(f"--> [DEBUG] Tìm thấy {len(self._cached_tests)} xét nghiệm.")

                for t in self._cached_tests:
                    n = getattr(t, 'test_name', None) or (t.get('test_name') if isinstance(t, dict) else None)
                    if n: test_names.append(str(n))
            except Exception as e:
                print(f"❌ Lỗi Service: {e}")

        # Cập nhật UI (Giữ nguyên)
        self.cb_test.blockSignals(True)
        self.cb_test.clear()
        for name in sorted(list(set(test_names))):
            self.cb_test.addItem(name)
        self.cb_test.blockSignals(False)

        # [MỚI] Nếu chỉ có 1 xét nghiệm, tự động chọn và điền đơn vị luôn cho tiện
        if len(test_names) == 1:
            self.cb_test.setCurrentIndex(0)
            self._on_test_changed(test_names[0])
    def _reload_unit_suggestions(self):
        test_name = (self.cb_test.currentText() or "").strip()
        units = []
        if test_name:
            try:
                meta = self.catalog_service.get_test_meta(self.dept_name, test_name)
                if meta and meta.get("unit"):
                    units.append(meta["unit"])
            except Exception:
                pass

        current = (self.cb_unit.currentText() or "").strip()
        self.cb_unit.blockSignals(True)
        self.cb_unit.clear()
        self.cb_unit.addItem("")
        for u in units:
            self.cb_unit.addItem(u)
        self.cb_unit.blockSignals(False)

        if current:
            self.cb_unit.setText(current)
        elif units:
            self.cb_unit.setText(units[0])

    def _auto_fill_meta_from_db(self):
        test = self.cb_test.currentText().strip()
        if not test: return

        try:
            meta = self.catalog_service.get_test_meta(self.dept_name, test)
        except Exception:
            meta = {}
        if not meta: return

        unit = meta.get("unit")
        if unit and not self.cb_unit.currentText().strip():
            self.cb_unit.setText(str(unit))

        dt_raw = meta.get("data_type")
        if isinstance(dt_raw, str) and dt_raw:
            dt_key = dt_raw.strip().lower()
            idx = -1

            for i in range(self.cb_dtype.count()):
                item_text = self.cb_dtype.itemText(i).lower()
                if "quant" in dt_key and "quant" in item_text and "semi" not in item_text:
                    idx = i
                    break
                elif "semi" in dt_key and "semi" in item_text:
                    idx = i
                    break
                elif "qual" in dt_key and "qual" in item_text:
                    idx = i
                    break

            if idx >= 0:
                self.cb_dtype.setCurrentIndex(idx)

    def _load_existing(self, detail_data: Dict[str, Any]):
        """
        Tải dữ liệu của một Analyte hiện có vào form để thực hiện chỉnh sửa.
        Đảm bảo danh sách xét nghiệm được nạp lại đúng theo phòng ban cũ.
        """
        # 1. Giải mã metadata từ trường note (chứa unit, target, semi_type...)
        meta = _parse_meta_from_note(detail_data.get("note"))

        # 2. Xác định kiểu dữ liệu (Quant/Semi/Qual)
        dtype = detail_data.get("data_type") or meta.get("data_type") or "Quant"
        dtype_key = "Quant"
        if dtype.lower().startswith("semi"):
            dtype_key = "Semi"
        elif dtype.lower().startswith("qual"):
            dtype_key = "Qual"

        # 3. [QUAN TRỌNG] Thiết lập Phòng ban và nạp lại gợi ý xét nghiệm
        dep_name = detail_data.get("department") or ""
        idx = self.cb_dep.findText(dep_name)
        if idx >= 0:
            # Ngắt block signals tạm thời nếu cần để tránh loop,
            # nhưng phải đảm bảo _reload_testname_suggestions được gọi
            self.cb_dep.setCurrentIndex(idx)
            # Ép nạp lại danh sách xét nghiệm theo ID của phòng ban cũ này
            self._reload_testname_suggestions()

        # 4. Thiết lập tên xét nghiệm (Sau khi đã nạp danh sách gợi ý ở bước 3)
        self.cb_test.setText(detail_data.get("test_name") or "")

        # 5. Thiết lập Level (L1, L2, L3)
        level_str = detail_data.get("level") or meta.get("level") or "L1"
        idx_level = self.cb_level.findText(level_str.upper())
        if idx_level >= 0:
            self.cb_level.setCurrentIndex(idx_level)

        # 6. Thiết lập Đơn vị và Phân loại
        unit = detail_data.get("unit") or meta.get("unit")
        self.cb_unit.setText(unit or "")

        category = detail_data.get("category") or meta.get("category")
        self.cb_cat.setText(category or "")

        # 7. Cập nhật ComboBox Kiểu dữ liệu trên giao diện
        for i in range(self.cb_dtype.count()):
            item_text = self.cb_dtype.itemText(i)
            if dtype_key in item_text:
                self.cb_dtype.setCurrentIndex(i)
                break

        # 8. Lấy các thông số kỹ thuật (Mean, Target, Ref Range)
        target = detail_data.get("mean") or meta.get("target")
        ref_range = detail_data.get("reference_range") or meta.get("reference_range")
        semi_type_str = meta.get("semi_type")

        self.sp_sort_order.setValue(int(detail_data.get("sort_order") or 0))

        # 9. Điền dữ liệu chi tiết theo từng kiểu (Quant/Semi/Qual)
        if dtype_key == "Quant":
            self.sp_mean.setValue(float(detail_data.get("mean") or 0.0))
            self.sp_sd.setValue(float(detail_data.get("sd") or 0.0))
            self.sp_tea.setValue(float(detail_data.get("tea") or 0.0))

        elif dtype_key == "Semi":
            if semi_type_str:
                idx_type = self.cb_semi_type.findText(semi_type_str)
                if idx_type >= 0:
                    self.cb_semi_type.setCurrentIndex(idx_type)

            self.cb_target_semi.setText(str(target or ""))

            # Xử lý dải tham chiếu bán định lượng
            if semi_type_str == "Loại 1 (POS/NEG)":
                self.ed_ref_semi_text.setText(ref_range or "")
            elif semi_type_str in ["Tùy chỉnh (Custom)", "Loại 2 (0+, 1+, trace...)", "Loại 4 (Tỷ trọng)"]:
                if ref_range and ('to' in str(ref_range) or '-' in str(ref_range)):
                    # Chuẩn hóa dấu phân cách để tách dải Từ - Đến
                    parts = str(ref_range).replace('-', 'to').split('to')
                    if len(parts) == 2:
                        self.semi_ref_from_cb.setText(parts[0].strip())
                        self.semi_ref_to_cb.setText(parts[1].strip())
                else:
                    self.semi_ref_from_cb.setText(str(ref_range or ""))
                    self.semi_ref_to_cb.setText(str(ref_range or ""))
            self.sp_tea.setValue(float(detail_data.get("tea") or 0.0))

        else:  # Qual (Định tính)
            target_str = (str(target or "NEG")).upper()
            if target_str not in ["NEG", "POS"]:
                target_str = "NEG"
            self.cb_target_qual.setCurrentText(target_str)
            self.ed_ref_qual_text.setText(target_str)

        # 10. Ghi chú cuối cùng
        self.ed_note.setText(detail_data.get("note") or "")

    def _on_save(self):
        try:
            self.values()
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Thiếu thông tin", str(e))

    def _on_dep_changed(self, index):
        """
        Lấy ID từ danh sách song song dựa trên index được chọn.
        """
        self.dept_name = self.cb_dep.currentText()

        # [FIX] Lấy ID từ list riêng, không lấy từ ComboBox nữa
        dep_id = None
        if 0 <= index < len(self._dep_ids):
            dep_id = self._dep_ids[index]

        print(f"DEBUG: Chọn index {index} -> Tên: '{self.dept_name}' -> ID chuẩn: {dep_id}")

        if dep_id:
            # Truyền trực tiếp ID vào hàm nạp để tránh phải get lại
            self._reload_testname_suggestions(force_dep_id=dep_id)
        else:
            print("❌ ID là None (Dòng trống hoặc lỗi map). Clear list.")
            self.cb_test.clear()

        self._auto_fill_meta_from_db()

    def _on_test_changed(self, text):
        if not text: return

        # Đảm bảo cache tồn tại và là list (đề phòng)
        if not hasattr(self, '_cached_tests') or not isinstance(self._cached_tests, list):
            return

        print(f"DEBUG: Đang tìm đơn vị cho '{text}'...")
        found_unit = ""

        for t in self._cached_tests:
            # Lấy tên an toàn
            t_name = getattr(t, 'test_name', "") or (t.get('test_name') if isinstance(t, dict) else "")

            # So sánh chuỗi (strip để xóa khoảng trắng thừa nếu có)
            if str(t_name).strip() == str(text).strip():
                # Lấy đơn vị
                found_unit = getattr(t, 'default_unit', "") or \
                             getattr(t, 'unit', "") or \
                             (t.get('default_unit') if isinstance(t, dict) else t.get('unit', ""))
                break

        if found_unit:
            print(f"   -> Tìm thấy: {found_unit}")
            self.cb_unit.setCurrentText(str(found_unit))
            # Nếu chưa có trong list đơn vị thì add thêm vào
            if self.cb_unit.findText(str(found_unit)) == -1:
                self.cb_unit.addItem(str(found_unit))
                self.cb_unit.setCurrentText(str(found_unit))

        self._auto_fill_meta_from_db()

    def _on_recalculate_stats(self):
        department = self.cb_dep.currentText()
        test_name = self.cb_test.currentText().strip()
        level = self.cb_level.currentText().strip()
        lot_no = self.prefill_lot_data.get("lot_no") or self.prefill_lot_data.get("lot")

        if not (department and test_name and level and lot_no):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn Phòng ban, Test, Level và Lot.")
            return

        dtype = self.cb_dtype.currentText()
        if "Quant" not in dtype:
            QMessageBox.warning(self, "Lỗi", "Chỉ áp dụng cho Định lượng (Quant).")
            return

        try:
            stats = self.catalog_service.calculate_lot_stats(department, test_name, level, lot_no)
            if stats.get("error"):
                QMessageBox.warning(self, "Lỗi Dữ liệu", stats.get("error"))
                return

            mean_new = stats.get("mean")
            sd_new = stats.get("sd")
            if mean_new is not None: self.sp_mean.setValue(mean_new)
            if sd_new is not None: self.sp_sd.setValue(sd_new)

            QMessageBox.information(self, "Thành công", f"Đã tính lại từ {stats.get('n', 0)} điểm IQC.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi tính toán: {e}")

    def _update_semi_target_ui(self):
        semi_type_key = self.cb_semi_type.currentText()
        target_list = SEMI_TYPES.get(semi_type_key, [])
        self.cb_target_semi.setVisible(True)
        self.cb_target_semi.clear()
        self.cb_target_semi.addItems(target_list)
        self._update_semi_ref_range_ui()

    def _update_semi_ref_range_ui(self):
        semi_type_key = self.cb_semi_type.currentText()
        show_text = semi_type_key == "Loại 1 (POS/NEG)"
        show_combos = semi_type_key in ["Tùy chỉnh (Custom)", "Loại 2 (0+, 1+, trace...)", "Loại 4 (Tỷ trọng)"]

        self.ed_ref_semi_text.setVisible(show_text)
        self.semi_ref_range_widget.setVisible(show_combos)

        if show_text:
            self.ed_ref_semi_text.setText(self.cb_target_semi.currentText())
        elif show_combos:
            range_list = SEMI_RANGE_LIST
            current_from = self.semi_ref_from_cb.currentText()
            current_to = self.semi_ref_to_cb.currentText()
            self.semi_ref_from_cb.clear()
            self.semi_ref_to_cb.clear()
            self.semi_ref_from_cb.addItems(range_list)
            self.semi_ref_to_cb.addItems(range_list)

            if current_from: self.semi_ref_from_cb.setText(current_from)
            if current_to: self.semi_ref_to_cb.setText(current_to)

    def _update_qual_ref_range_ui(self):
        target = self.cb_target_qual.currentText()
        self.ed_ref_qual_text.setText(target)

    def _apply_dtype_layout(self):
        dtype = (self.cb_dtype.currentText() or "").lower()
        is_quant = "quant" in dtype and "semi" not in dtype
        is_semi = "semi" in dtype
        is_qual = "qual" in dtype

        self._quant_box_widget.setVisible(is_quant)
        self._semi_box_widget.setVisible(is_semi)
        self._qual_box_widget.setVisible(is_qual)

        if is_semi:
            self._update_semi_target_ui()
        elif is_qual:
            self._update_qual_ref_range_ui()

    def values(self) -> Dict[str, Any]:
        def _text_or_none(s: str) -> Optional[str]:
            s = (s or "").strip()
            return s if s else None

        dtype_text = self.cb_dtype.currentText().lower()
        if "semi" in dtype_text:
            dtype_key = "Semi"
        elif "qual" in dtype_text:
            dtype_key = "Qual"
        else:
            dtype_key = "Quant"

        test_name = (self.cb_test.currentText() or "").strip()
        if not test_name: raise ValueError("Tên xét nghiệm không được để trống.")

        out: Dict[str, Any] = {
            "department": _text_or_none(self.cb_dep.currentText()),
            "test_name": test_name,
            "data_type": dtype_key,
            "level": _text_or_none(self.cb_level.currentText()),
            "unit": None,
            "category": _text_or_none(self.cb_cat.currentText()),
            "note": _text_or_none(self.ed_note.text()),
            "mean": None, "sd": None, "tea": None,
            "target": None, "reference_range": None,
            "semi_type": None,
            "sort_order": int(self.sp_sort_order.value())
        }

        if dtype_key == "Quant":
            out["unit"] = _text_or_none(self.cb_unit.currentText())
            out["mean"] = float(self.sp_mean.value())
            out["sd"] = float(self.sp_sd.value())
            out["tea"] = float(self.sp_tea.value())
        elif dtype_key == "Semi":
            out["unit"] = _text_or_none(self.cb_unit.currentText())
            semi_type_key = self.cb_semi_type.currentText()
            out["semi_type"] = semi_type_key
            target = _text_or_none(self.cb_target_semi.currentText())
            out["target"] = target
            out["mean"] = None
            if semi_type_key == "Loại 1 (POS/NEG)":
                out["reference_range"] = target
            else:
                ref_from = self.semi_ref_from_cb.currentText().strip()
                ref_to = self.semi_ref_to_cb.currentText().strip()
                if ref_from and ref_to:
                    out["reference_range"] = f"{ref_from} to {ref_to}"
                else:
                    out["reference_range"] = target
            out["tea"] = float(self.sp_tea.value()) if self.sp_tea.value() != 0.0 else None
        else:
            target = _text_or_none(self.cb_target_qual.currentText())
            out["target"] = target or "NEG"
            out["mean"] = None
            out["reference_range"] = target or "NEG"

        meta = {
            "data_type": out["data_type"],
            "unit": out["unit"],
            "reference_range": out["reference_range"],
            "category": out["category"],
            "target": out["target"],
            "semi_type": out["semi_type"],
            "sort_order": out["sort_order"],
            "level": out["level"]
        }
        out["note"] = _merge_meta(out["note"], meta)
        return out