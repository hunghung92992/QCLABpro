# -*- coding: utf-8 -*-
"""
app/services/auth_service.py
(PHIÊN BẢN HYBRID - ORM)
Chuyển đổi sang SQLAlchemy để hỗ trợ đồng bộ User từ Server về Local.
"""

import bcrypt
import hashlib
from typing import Dict, Any, Optional, List
from sqlalchemy import or_

# --- IMPORTS TỪ CORE ORM ---
from app.core.database_orm import SessionLocal
from app.models.core_models import User
from app.core.constants import DEFAULT_PASSWORD


class AuthService:
    def __init__(self):
        pass

    def _get_db(self):
        return SessionLocal()

    def _user_to_dict(self, u: User) -> Dict[str, Any]:
        """Helper chuyển đổi Object ORM sang Dict an toàn (Chống Crash ngầm)"""
        if not u: return None

        # Dùng getattr để lấy giá trị an toàn, nếu Model không có cột đó thì trả về mặc định
        return {
            "id": str(u.id),  # Ép kiểu string cho UUID
            "username": u.username,
            "fullname": getattr(u, 'fullname', ''),
            "role": getattr(u, 'role', ''),
            "department": getattr(u, 'department_id', None),
            # Linh hoạt nhận diện active hoặc is_active
            "is_active": getattr(u, 'is_active', getattr(u, 'active', 1)),
            "password_hash": getattr(u, 'password_hash', '').encode('utf-8') if getattr(u, 'password_hash',
                                                                                        None) else None,
            "salt": getattr(u, 'salt', None),
            "access_control": getattr(u, 'access_control', '')
        }

    # ================= LOGIC HASH & LEGACY =================
    def _hash_password_bcrypt(self, plain_password: str) -> bytes:
        return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())

    def _verify_legacy(self, plain: str, salt: Optional[bytes], stored_hash: Optional[bytes]) -> bool:
        if not salt or not stored_hash: return False
        try:
            salt_bytes = bytes.fromhex(salt.decode('utf-8')) if isinstance(salt, bytes) else salt.encode('utf-8')
            hash_bytes = bytes.fromhex(stored_hash.decode('utf-8')) if isinstance(stored_hash,
                                                                                  bytes) else stored_hash.encode(
                'utf-8')
            m = hashlib.sha256()
            m.update(plain.encode('utf-8'))
            m.update(salt_bytes)
            if m.digest() == hash_bytes: return True
        except:
            pass
        return False

    def _update_hash(self, user_id: str, new_hash: bytes):
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.password_hash = new_hash.decode('utf-8')
                user.sync_flag = 1
                db.commit()
        except Exception as e:
            print(f"Lỗi cập nhật Hash: {e}")
            db.rollback()
        finally:
            db.close()

    # ================= CÁC HÀM NGHIỆP VỤ =================

    def authenticate_user(self, username: str, plain_password: str) -> Dict[str, Any]:
        user_data = self.get_user_by_username(username)

        if not user_data:
            return {"ok": False, "reason": "Tài khoản không tồn tại"}

        if not user_data.get("is_active", 1):
            return {"ok": False, "reason": "Tài khoản bị khóa"}

        stored_hash = user_data.get("password_hash")
        stored_salt = user_data.get("salt")

        if not stored_hash:
            return {"ok": False, "reason": "Lỗi dữ liệu mật khẩu"}

        ok = False
        migrated = False
        new_hash = None

        try:
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode('utf-8')

            if stored_hash.startswith(b"$2"):
                ok = bcrypt.checkpw(plain_password.encode('utf-8'), stored_hash)
            else:
                ok = self._verify_legacy(plain_password, stored_salt, stored_hash)
                if ok:
                    migrated = True
                    new_hash = self._hash_password_bcrypt(plain_password)
        except Exception as e:
            print(f"❌ Auth Hash Error: {e}")
            ok = False

        if not ok:
            return {"ok": False, "reason": "Sai mật khẩu"}

        if migrated and new_hash:
            self._update_hash(user_data["id"], new_hash)

        return {"ok": True, "reason": "success", "user_data": user_data}

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        try:
            user = db.query(User).filter(User.username == username, User.sync_flag != 2).first()
            return self._user_to_dict(user)
        except Exception as e:
            # Bắt buộc in lỗi ra màn hình để debug
            print(f"❌ [AuthService] Crash ngầm khi truy vấn User '{username}': {e}")
            return None
        finally:
            db.close()

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == str(user_id)).first()
            return self._user_to_dict(user)
        except Exception as e:
            print(f"❌ [AuthService] Lỗi get_user: {e}")
            return None
        finally:
            db.close()

    def list_users(self, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        db = self._get_db()
        try:
            query = db.query(User).filter(User.sync_flag != 2)

            if search_term:
                term = f"%{search_term}%"
                query = query.filter(or_(
                    User.username.like(term),
                    User.fullname.like(term)
                ))

            users = query.order_by(User.username.asc()).all()
            return [self._user_to_dict(u) for u in users]
        except Exception as e:
            print(f"List Users Error: {e}")
            return []
        finally:
            db.close()

    def create_user(self, username: str, password: str, role: str, department: str, fullname: str, is_active: bool) -> \
    Dict[str, Any]:
        if not username or not role: return {"ok": False, "reason": "Thiếu thông tin."}

        pw_to_hash = password if password else DEFAULT_PASSWORD
        hashed_pw_bytes = self._hash_password_bcrypt(pw_to_hash)
        hashed_pw_str = hashed_pw_bytes.decode('utf-8')

        db = self._get_db()
        try:
            exist = db.query(User).filter(User.username == username).first()
            if exist:
                return {"ok": False, "reason": "Tên đăng nhập đã tồn tại"}

            new_user = User(
                username=username,
                password_hash=hashed_pw_str,
                fullname=fullname,
                role=role,
                department_id=department,
                is_active=1 if is_active else 0,
                sync_flag=1
            )
            db.add(new_user)
            db.commit()
            return {"ok": True}
        except Exception as e:
            db.rollback()
            return {"ok": False, "reason": str(e)}
        finally:
            db.close()

    def update_user(self, user_id: str, fullname: str, role: str, department: str, is_active: bool) -> Dict[str, Any]:
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == str(user_id)).first()
            if not user: return {"ok": False, "reason": "User not found"}

            user.fullname = fullname
            user.role = role
            user.department_id = department
            user.is_active = 1 if is_active else 0
            user.sync_flag = 1

            db.commit()
            return {"ok": True}
        except Exception as e:
            db.rollback()
            return {"ok": False, "reason": str(e)}
        finally:
            db.close()

    def reset_password(self, user_id: str, new_password: str = DEFAULT_PASSWORD) -> Dict[str, Any]:
        hashed_pw_bytes = self._hash_password_bcrypt(new_password)
        hashed_pw_str = hashed_pw_bytes.decode('utf-8')

        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == str(user_id)).first()
            if user:
                user.password_hash = hashed_pw_str
                user.sync_flag = 1
                db.commit()
                return {"ok": True}
            return {"ok": False, "reason": "User not found"}
        except Exception as e:
            db.rollback()
            return {"ok": False, "reason": str(e)}
        finally:
            db.close()

    def change_password(self, username: str, old_password: str, new_password: str) -> Dict[str, Any]:
        auth_result = self.authenticate_user(username, old_password)
        if not auth_result["ok"]: return {"ok": False, "reason": "Mật khẩu cũ không đúng."}

        new_hashed_pw_bytes = self._hash_password_bcrypt(new_password)
        user_id = auth_result["user_data"]["id"]

        self._update_hash(user_id, new_hashed_pw_bytes)
        return {"ok": True}

    def toggle_active(self, user_id: str) -> Dict[str, Any]:
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == str(user_id)).first()
            if user:
                user.is_active = 1 - (getattr(user, 'is_active', getattr(user, 'active', 0)))
                user.sync_flag = 1
                db.commit()
                return {"ok": True}
            return {"ok": False, "reason": "User not found"}
        except Exception as e:
            db.rollback()
            return {"ok": False, "reason": str(e)}
        finally:
            db.close()

    def delete_user(self, user_id: str, username: str) -> Dict[str, Any]:
        if username.lower() == 'admin': return {"ok": False, "reason": "Không thể xóa Super Admin"}

        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == str(user_id)).first()
            if user:
                user.sync_flag = 2

                # Cập nhật trạng thái an toàn
                if hasattr(user, 'is_active'):
                    user.is_active = 0
                elif hasattr(user, 'active'):
                    user.active = 0

                db.commit()
                return {"ok": True}
            return {"ok": False, "reason": "User not found"}
        except Exception as e:
            db.rollback()
            return {"ok": False, "reason": str(e)}
        finally:
            db.close()

    def update_user_access(self, user_id: str, access_json_str: str) -> bool:
        db = self._get_db()
        try:
            user = db.query(User).filter(User.id == str(user_id)).first()
            if user:
                user.access_control = access_json_str
                user.sync_flag = 1
                db.commit()
                return True
            return False
        except:
            db.rollback()
            return False
        finally:
            db.close()