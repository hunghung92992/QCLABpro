import uuid
import bcrypt
from app.core.database_orm import SessionLocal
from app.models.core_models import User, Department
from datetime import datetime

class UserService:
    """
    Service quản lý người dùng thay thế cho auth_service cũ.
    Sử dụng SQLAlchemy và UUID.
    """

    def get_all_users(self):
        """
        Lấy danh sách user kèm tên phòng ban.
        Trả về: List[Dict] để tương thích với UI cũ.
        """
        session = SessionLocal()
        try:
            # Join bảng User và Department để lấy tên phòng
            # (Outer join để lấy cả user chưa có phòng)
            query = session.query(User, Department.name.label("dept_name")) \
                .outerjoin(Department, User.department_id == Department.id) \
                .order_by(User.username) \
                .all()

            result = []
            for user, dept_name in query:
                u_dict = {
                    "id": user.id,  # UUID
                    "username": user.username,
                    "fullname": user.fullname,
                    "role": user.role,
                    "department_id": user.department_id,
                    "department_name": dept_name if dept_name else "",
                    "is_active": user.is_active
                }
                result.append(u_dict)
            return result
        except Exception as e:
            print(f"[UserService] Error getting users: {e}")
            return []
        finally:
            session.close()

    def create_user(self, username, fullname, password, role, department_id, is_active=1):
        """Tạo user mới."""
        session = SessionLocal()
        try:
            # 1. Check trùng username
            if session.query(User).filter(User.username == username).first():
                return False, f"Tên đăng nhập '{username}' đã tồn tại!"

            # 2. Hash mật khẩu
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # 3. Tạo User (Tự sinh UUID)
            new_user = User(
                id=str(uuid.uuid4()),
                username=username,
                password_hash=hashed,
                fullname=fullname,
                role=role,
                department_id=department_id,  # Lưu UUID phòng ban
                is_active=is_active
            )
            session.add(new_user)
            session.commit()
            return True, "Tạo người dùng thành công!"
        except Exception as e:
            session.rollback()
            return False, f"Lỗi hệ thống: {str(e)}"
        finally:
            session.close()

    def update_user(self, user_id, fullname, role, department_id, password=None, is_active=None):
        """Cập nhật thông tin user."""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User không tồn tại!"

            # Cập nhật thông tin
            user.fullname = fullname
            user.role = role
            user.department_id = department_id

            if is_active is not None:
                user.is_active = is_active

            # Chỉ đổi pass nếu có nhập
            if password and password.strip():
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                user.password_hash = hashed

            session.commit()
            return True, "Cập nhật thành công!"
        except Exception as e:
            session.rollback()
            return False, f"Lỗi cập nhật: {str(e)}"
        finally:
            session.close()

    def delete_user(self, user_id):
        """Xóa mềm (Soft Delete) - Chuyển Active về 0."""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = 0  # <--- CHỈ ĐƯỢC LÀM THẾ NÀY
                user.sync_flag = 2 # Đánh dấu: "Worker ơi, hãy báo Server xóa cái này đi"
                user.updated_at = datetime.utcnow()  # Cập nhật thời gian sửa
                session.commit()
                return True, "Đã xóa (Soft Delete)"
            return False, "User không tồn tại."
        except Exception as e:
            session.rollback()
            return False, f"Lỗi xóa: {str(e)}"
        finally:
            session.close()