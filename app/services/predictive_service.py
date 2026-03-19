# -*- coding: utf-8 -*-
"""
app/services/predictive_service.py
Dịch vụ học thuật: Dự đoán xu hướng (Trend) và Lỗi (Shift).
(UPDATED: Sử dụng Real Target từ CatalogService)
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional

try:
    from sklearn.linear_model import LinearRegression
    import numpy as np

    HAS_ML_LIBS = True
except ImportError:
    HAS_ML_LIBS = False


    # Fallback dummy class để không crash app nếu thiếu thư viện
    class LinearRegression:
        def __init__(self): self.coef_ = [0.0]; self.intercept_ = 0.0; self.n_features_in_ = 0

        def fit(self, X, Y): pass

        def predict(self, X): return np.array([0.0])


    import numpy as np

from app.services.iqc_service import IQCService
from app.services.catalog_service import CatalogService  # <--- THÊM IMPORT
from app.utils.validators import to_float_safe as _to_float


class PredictiveService:
    def __init__(self):
        self.iqc_service = IQCService()
        self.catalog_service = CatalogService()  # <--- KHỞI TẠO SERVICE

        self.HAS_ML_LIBS = HAS_ML_LIBS
        self._cache: Dict[str, Any] = {}

    def _get_history_z_score(self, dep, test, lot, level) -> List[float]:
        """
        Lấy lịch sử Z-score (SDI) chuẩn hóa dựa trên Target thật.
        """
        # 1. Lấy Target (Mean/SD) thật từ Catalog
        target = self.catalog_service.get_target_by_lot(test, level, lot)

        if not target:
            # Nếu chưa cấu hình Target -> Không thể tính Z-score
            return []

        t_mean = _to_float(target.get('mean'))
        t_sd = _to_float(target.get('sd'))

        # Kiểm tra tính hợp lệ của Target
        if t_mean is None or t_sd is None or t_sd == 0:
            return []

        # 2. Lấy dữ liệu lịch sử
        history = self.iqc_service.get_history(
            department=dep, test_code=test, lot_no=lot, level=level,
            limit=200, active_only=True, sort_order="ASC"
        )

        # 3. Tính toán Z-score thực tế
        z_scores = []
        for r in history:
            val = _to_float(r.get('value_num'))
            if val is not None:
                # Công thức Z = (Value - TargetMean) / TargetSD
                z = (val - t_mean) / t_sd
                z_scores.append(z)

        return z_scores

    def train_trend_model(self, model_key: str, data: List[float]) -> bool:
        """Huấn luyện mô hình Hồi quy Tuyến tính đơn giản trên Z-scores."""
        if not self.HAS_ML_LIBS or len(data) < 10:
            return False

        try:
            # X = index (thời gian), Y = Z-score
            X = np.arange(len(data)).reshape(-1, 1)
            Y = np.array(data)

            model = LinearRegression()
            model.fit(X, Y)

            self._cache[model_key] = {
                "model": model,
                "slope": model.coef_[0],
                "intercept": model.intercept_,
                "history_length": len(data)
            }
            return True
        except Exception as e:
            print(f"[PredictiveService] Lỗi huấn luyện: {e}")
            return False

    def predict_next_z_score(self, model_key: str, num_steps: int = 1) -> Optional[float]:
        """Dự đoán Z-score cho N điểm tiếp theo."""
        if model_key not in self._cache or not self.HAS_ML_LIBS:
            return None

        model_info = self._cache[model_key]
        model: LinearRegression = model_info["model"]

        # Index tiếp theo là độ dài lịch sử + số bước dự đoán
        next_index = model_info["history_length"] + num_steps  # type: ignore

        prediction = model.predict(np.array([[next_index]]))
        return prediction[0]

    def check_trend_shift(self, dep, test, lot, level) -> Dict[str, Any]:
        """
        Kiểm tra và dự đoán khả năng trôi dạt (shift).
        """
        if not self.HAS_ML_LIBS:
            return {"status": "ERROR", "reason": "Thiếu thư viện ML"}

        # Bước 1: Lấy Z-Score dựa trên Target thật
        z_scores = self._get_history_z_score(dep, test, lot, level)
        model_key = f"{dep}_{test}_{lot}_{level}"

        if len(z_scores) < 10:
            return {"status": "N/A", "reason": "Cần tối thiểu 10 điểm để dự đoán"}

        # Bước 2: Huấn luyện
        success = self.train_trend_model(model_key, z_scores)
        if not success or model_key not in self._cache:
            return {"status": "ERROR", "reason": "Lỗi huấn luyện mô hình"}

        model_info = self._cache[model_key]
        slope = model_info["slope"]

        # Bước 3: Dự đoán
        next_z = self.predict_next_z_score(model_key, num_steps=1)

        return {
            "status": "OK",
            "slope": slope,
            "prediction_next_z": next_z,
            "history_z_scores": z_scores
        }