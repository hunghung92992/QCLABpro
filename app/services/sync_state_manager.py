# app/services/sync_state_manager.py
import json
import os
from datetime import datetime

STATE_FILE = "sync_state.json"


class SyncStateManager:
    @staticmethod
    def get_last_sync_time(table_name):
        """Lấy mốc thời gian cập nhật cuối cùng của bảng"""
        if not os.path.exists(STATE_FILE):
            return "2000-01-01 00:00:00"  # Mặc định lấy từ quá khứ xa

        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get(table_name, "2000-01-01 00:00:00")
        except:
            return "2000-01-01 00:00:00"

    @staticmethod
    def update_last_sync_time(table_name, time_str):
        """Lưu lại mốc thời gian mới nhất"""
        data = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
            except:
                pass

        # Nếu time_str là datetime object, chuyển sang string
        if isinstance(time_str, datetime):
            time_str = time_str.strftime("%Y-%m-%d %H:%M:%S.%f")

        data[table_name] = str(time_str)

        with open(STATE_FILE, 'w') as f:
            json.dump(data, f)