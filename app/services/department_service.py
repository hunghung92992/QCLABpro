import uuid
from typing import Tuple
from app.core.database_orm import SessionLocal
from app.models.core_models import Department, DepartmentTest, Device, User
from datetime import datetime


class DepartmentService:

    # ---------- Department CRUD ----------
    def get_all(self):
        """Lấy danh sách tất cả phòng ban đang hoạt động (Logic mới)."""
        session = SessionLocal()
        try:
            return session.query(Department).filter(Department.active == 1).order_by(Department.name).all()
        finally:
            session.close()

    # [QUAN TRỌNG] Thêm hàm này để tương thích với code cũ đang gọi list_departments
    def list_departments(self, active_only=True):
        """Lấy danh sách phòng ban"""
        session = SessionLocal()
        try:
            q = session.query(Department)
            if active_only:
                q = q.filter(Department.active == 1)
            return q.order_by(Department.name).all()
        finally:
            session.close()

    def create(self, name: str, note: str = "") -> Tuple[bool, str]:
        if not name.strip(): return False, "Tên phòng ban là bắt buộc."
        session = SessionLocal()
        try:
            if session.query(Department).filter(Department.name == name.strip()).first():
                return False, f"Phòng ban '{name}' đã tồn tại!"
            new_dept = Department(id=str(uuid.uuid4()), name=name.strip(), note=note.strip(), active=1)
            session.add(new_dept)
            session.commit()
            return True, "Thêm phòng ban thành công!"
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()

    def update(self, dept_id: str, name: str, note: str) -> Tuple[bool, str]:
        if not name.strip(): return False, "Tên phòng ban là bắt buộc."
        session = SessionLocal()
        try:
            dept = session.query(Department).filter(Department.id == dept_id).first()
            if not dept: return False, "Không tìm thấy phòng ban!"
            # Check duplicate name exclude current
            if session.query(Department).filter(Department.name == name.strip(), Department.id != dept_id).first():
                return False, f"Tên '{name}' đã được sử dụng!"
            dept.name = name.strip()
            dept.note = note.strip()
            session.commit()
            return True, "Cập nhật thành công!"
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()

    def delete(self, dept_id: str) -> Tuple[bool, str]:
        session = SessionLocal()
        try:
            dept = session.query(Department).filter(Department.id == dept_id).first()
            if not dept: return False, "Không tìm thấy!"
            if session.query(User).filter(User.department_id == dept_id, User.is_active == 1).count() > 0:
                return False, "Còn nhân viên trong phòng ban này."
            if session.query(Device).filter(Device.department_id == dept_id, Device.active == 1).count() > 0:
                return False, "Còn thiết bị trong phòng ban này."
            dept.active = 0  # Ẩn khỏi giao diện người dùng
            dept.sync_flag = 2  # Đánh dấu: "Worker ơi, hãy báo Server xóa cái này đi"
            dept.updated_at = datetime.utcnow()  # Cập nhật thời gian để thắng Server nếu có xung đột

            session.commit()
            return True, "Đã xóa phòng ban."
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()

    # ---------- Dept Tests CRUD (FULL LOGIC) ----------

    def list_tests_by_department(self, dept_id: str):
        session = SessionLocal()
        try:
            # Ép kiểu UUID sang string để SQLite/Postgres so sánh chính xác
            # [LỖI GỐC CÓ THỂ Ở ĐÂY]: Đảm bảo dept_id không bị convert thành số
            tests = session.query(DepartmentTest).filter(
                DepartmentTest.department_id == str(dept_id),
                DepartmentTest.active == 1
            ).all()
            return tests
        finally:
            session.close()

    def add_test_to_department(self, dept_id: str, test_code: str, test_name: str, unit: str, data_type: str,
                               method: str) -> Tuple[bool, str]:
        """Thêm xét nghiệm với đầy đủ các trường."""
        if not test_code.strip(): return False, "Mã xét nghiệm thiếu."

        session = SessionLocal()
        try:
            exist = session.query(DepartmentTest).filter(
                DepartmentTest.department_id == dept_id,
                DepartmentTest.test_code == test_code.strip(),
                DepartmentTest.active == 1
            ).first()
            if exist: return False, f"Mã '{test_code}' đã tồn tại."

            new_test = DepartmentTest(
                id=str(uuid.uuid4()),
                department_id=dept_id,
                test_code=test_code.strip(),
                test_name=test_name.strip(),
                unit=unit.strip(),
                data_type=data_type,
                method=method.strip(),
                active=1
            )
            session.add(new_test)
            session.commit()
            return True, "Thêm thành công!"
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()

    def update_test_in_department(self, test_id: str, test_code: str, test_name: str, unit: str, data_type: str,
                                  method: str) -> Tuple[bool, str]:
        """Cập nhật thông tin xét nghiệm."""
        session = SessionLocal()
        try:
            test = session.query(DepartmentTest).filter(DepartmentTest.id == test_id).first()
            if not test: return False, "Không tìm thấy xét nghiệm."

            # Check trùng mã nếu đổi mã
            if test.test_code != test_code.strip():
                exist = session.query(DepartmentTest).filter(
                    DepartmentTest.department_id == test.department_id,
                    DepartmentTest.test_code == test_code.strip(),
                    DepartmentTest.active == 1
                ).first()
                if exist: return False, f"Mã '{test_code}' đã được dùng."

            test.test_code = test_code.strip()
            test.test_name = test_name.strip()
            test.unit = unit.strip()
            test.data_type = data_type
            test.method = method.strip()

            session.commit()
            return True, "Cập nhật thành công!"
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()

    def remove_test_from_department(self, test_id: str) -> Tuple[bool, str]:
        """Xóa mềm xét nghiệm."""
        session = SessionLocal()
        try:
            test = session.query(DepartmentTest).filter(DepartmentTest.id == test_id).first()
            if not test: return False, "Không tìm thấy."
            test.active = 0
            session.commit()
            return True, "Đã xóa."
        except Exception as e:
            session.rollback()
            return False, f"Lỗi: {str(e)}"
        finally:
            session.close()