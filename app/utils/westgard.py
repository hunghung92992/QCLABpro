# -*- coding: utf-8 -*-
"""
//westgard.py
(ENTERPRISE EDITION)
Tích hợp: Westgard Cơ bản, Sigma-Metrics Rules, Multi-level Across-Run, và CUSUM (Cảnh báo sớm).
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Any
import math


# =============================================================================
# 1. HÀM TRỢ GIÚP (HELPERS)
# =============================================================================
def _to_float(v: Any) -> float:
    try:
        return float(v)
    except (ValueError, TypeError, OverflowError):
        return float('nan')


def _gt(val: float, thr: float) -> bool:
    if math.isnan(val):
        return False
    return abs(val) > thr


def _same_side(vals: List[float], center: float) -> bool:
    valid_vals = [v for v in vals if not math.isnan(v)]
    if not valid_vals:
        return False
    pos = [v > center for v in valid_vals]
    neg = [v < center for v in valid_vals]
    return all(pos) or all(neg)


def _is_trending(vals: List[float], n: int) -> bool:
    if len(vals) < n: return False
    tail = vals[-n:]
    is_increasing = all(tail[i] < tail[i + 1] for i in range(n - 1))
    is_decreasing = all(tail[i] > tail[i + 1] for i in range(n - 1))
    return is_increasing or is_decreasing


# =============================================================================
# 2. WESTGARD SIGMA RULES (LUẬT ĐỘNG THEO CHẤT LƯỢNG)
# =============================================================================
def get_rules_by_sigma(sigma: float) -> Set[str]:
    """
    Tự động chọn luật Westgard dựa trên hiệu năng Sigma của xét nghiệm.
    Giúp giảm thiểu cảnh báo giả (False Rejection) cho các hóa chất xịn.
    """
    if math.isnan(sigma) or sigma <= 0:
        # Mặc định bật full khi không có dữ liệu Sigma
        return {"1_3s", "1_2s", "2_2s", "R_4s", "4_1s", "10_x", "7_t"}

    if sigma >= 6.0:
        return {"1_3s"}  # Đạt 6 Sigma: Lỗi ngẫu nhiên là quá hiếm, chỉ cần 1 luật
    elif sigma >= 5.0:
        return {"1_3s", "2_2s", "R_4s"}
    elif sigma >= 4.0:
        return {"1_3s", "2_2s", "R_4s", "4_1s"}
    else:
        # Dưới 4 Sigma: Bật toàn bộ lá chắn
        return {"1_3s", "1_2s", "2_2s", "R_4s", "4_1s", "10_x", "7_t"}


# =============================================================================
# 3. SINGLE-LEVEL WESTGARD EVALUATION
# =============================================================================
def eval_rules(
        history: List[float],
        mean: float,
        sd: float,
        rules: Optional[Set[str]] = None,
        sigma: Optional[float] = None
) -> Dict[str, Any]:
    """
    Đánh giá Westgard cho 1 Level độc lập. Tích hợp tự động chọn luật theo Sigma.
    """
    # Nếu truyền vào Sigma, tự động ưu tiên bộ luật Sigma
    if sigma is not None and sigma > 0:
        rules = get_rules_by_sigma(sigma)
    elif rules is None:
        rules = {"1_3s", "1_2s", "2_2s", "R_4s", "4_1s", "10_x", "7_t"}

    out_v = []
    details = {}

    m, s = _to_float(mean), _to_float(sd)
    if not history or math.isnan(m) or math.isnan(s) or s <= 0:
        return {"violated": [], "details": {}, "last_z": float('nan'), "rules_applied": list(rules)}

    zscores = [(_to_float(v) - m) / s for v in history]
    z_last = zscores[-1] if zscores else float('nan')

    if math.isnan(z_last):
        return {"violated": [], "details": {}, "last_z": z_last, "rules_applied": list(rules)}

    # 1-3s: |z_last| > 3 (REJECT)
    if "1_3s" in rules and _gt(z_last, 3):
        out_v.append("1_3s")
        details["1_3s"] = f"Vi phạm 1_3s (Z={z_last:.2f})"

    # 1-2s: |z_last| > 2 (WARN)
    if "1_2s" in rules and _gt(z_last, 2):
        out_v.append("1_2s")
        details["1_2s"] = f"Cảnh báo 1_2s (Z={z_last:.2f})"

    # 2-2s: 2 điểm liên tiếp cùng phía vượt 2SD (REJECT)
    if "2_2s" in rules and len(zscores) >= 2:
        z1, z2 = zscores[-2], zscores[-1]
        if _gt(z1, 2) and _gt(z2, 2) and (z1 * z2) > 0:
            out_v.append("2_2s")
            details["2_2s"] = f"Vi phạm 2_2s (Z={z1:.2f}, {z2:.2f})"

    # R-4s: Độ lệch 2 điểm liên tiếp cắt ngang Mean và >= 4SD (REJECT)
    if "R_4s" in rules and len(zscores) >= 2:
        z1, z2 = zscores[-2], zscores[-1]
        if not math.isnan(z1):
            if (z1 > 2 and z2 < -2) or (z1 < -2 and z2 > 2):
                out_v.append("R_4s")
                details["R_4s"] = f"Vi phạm R_4s chênh lệch {abs(z1 - z2):.1f}SD"

    # 4-1s: 4 điểm liên tiếp cùng phía vượt 1SD (REJECT)
    if "4_1s" in rules and len(zscores) >= 4:
        tail = zscores[-4:]
        if all(_gt(z, 1) for z in tail) and _same_side(tail, 0.0):
            out_v.append("4_1s")
            details["4_1s"] = "Vi phạm 4_1s"

    # 10x: 10 điểm liên tiếp cùng phía (REJECT)
    if "10_x" in rules and len(zscores) >= 10:
        tail = zscores[-10:]
        if _same_side(tail, 0.0):
            out_v.append("10_x")
            details["10_x"] = "Vi phạm 10_X (Lỗi hệ thống)"

    # 7T: 7 điểm liên tiếp xu hướng (REJECT)
    if "7_t" in rules and len(zscores) >= 7:
        if _is_trending(zscores, 7):
            out_v.append("7_t")
            details["7_t"] = "Vi phạm 7_T (Trượt/Drift)"

    return {
        "violated": out_v,
        "details": details,
        "last_z": round(z_last, 2),
        "rules_applied": list(rules)
    }


# =============================================================================
# 4. MULTI-LEVEL WESTGARD EVALUATION (CROSS-MATERIAL)
# =============================================================================
def eval_multilevel(current_z_scores: Dict[str, float]) -> Dict[str, str]:
    """
    Đánh giá chéo giữa L1, L2, L3... trong CÙNG MỘT LẦN CHẠY (Within-Run).
    Input: {'L1': 2.5, 'L2': -2.1}
    Output: {'L1': 'R_4s', 'L2': 'R_4s'}
    """
    violations = {}
    levels = list(current_z_scores.keys())

    if len(levels) < 2:
        return violations  # Không đủ 2 level để đánh giá chéo

    z_values = [current_z_scores[l] for l in levels if not math.isnan(current_z_scores[l])]
    if len(z_values) < 2:
        return violations

    z_max, z_min = max(z_values), min(z_values)

    # 1. R-4s (Across-Level): L1 vọt lên +2SD, L2 rớt xuống -2SD
    if (z_max - z_min) >= 4.0:
        for lvl in levels:
            z = current_z_scores[lvl]
            if z == z_max or z == z_min:
                violations[lvl] = "R_4s"

    # 2. 2-2s (Across-Level): L1 và L2 đều > +2SD hoặc đều < -2SD
    count_pos = sum(1 for z in z_values if z > 2)
    count_neg = sum(1 for z in z_values if z < -2)

    if count_pos >= 2 or count_neg >= 2:
        for lvl in levels:
            if abs(current_z_scores[lvl]) > 2:
                # Ưu tiên R_4s nặng hơn nếu đã có
                if lvl not in violations:
                    violations[lvl] = "2_2s"

    return violations


# =============================================================================
# 5. CUSUM (CUMULATIVE SUM - CẢNH BÁO SỚM TRƯỢT/SHIFT)
# =============================================================================
def eval_cusum(zscores: List[float], k: float = 0.5, h: float = 2.7) -> Dict[str, Any]:
    """
    Thuật toán Tabular CUSUM (CUSUM Bảng) phát hiện lỗi hệ thống sớm hơn 10_x.
    Công thức:
    Upper Shift (SH): S_{i}^+ = max(0, S_{i-1}^+ + Z_i - k)
    Lower Shift (SL): S_{i}^- = max(0, S_{i-1}^- - Z_i - k)
    """
    if not zscores:
        return {"alarm": False, "sh": 0.0, "sl": 0.0}

    sh, sl = 0.0, 0.0
    alarm_triggered = False

    for z in zscores:
        if math.isnan(z): continue

        # Tính lũy kế dịch chuyển dương (SH) và âm (SL)
        sh = max(0.0, sh + z - k)
        sl = max(0.0, sl - z - k)

        # Vượt ngưỡng h (Thường là 2.7 hoặc 2.77)
        if sh > h or sl > h:
            alarm_triggered = True

    return {
        "alarm": alarm_triggered,
        "sh_final": round(sh, 2),
        "sl_final": round(sl, 2),
        "shift_type": "Positive (Tăng)" if sh > h else ("Negative (Giảm)" if sl > h else "Normal")
    }


# =============================================================================
# 6. MỨC ĐỘ ƯU TIÊN LỖI (PRIORITY ENGINE)
# =============================================================================
def get_rule_priority(rule_code: str) -> int:
    if rule_code == "1_3s": return 1
    if rule_code == "R_4s": return 2
    if rule_code == "2_2s": return 3
    if rule_code in ("4_1s", "8_x", "10_x", "7_t"): return 4
    if rule_code == "1_2s": return 6
    return 99


def get_highest_priority_violation(violated: List[str]) -> Optional[str]:
    if not violated: return None
    return min(violated, key=get_rule_priority)