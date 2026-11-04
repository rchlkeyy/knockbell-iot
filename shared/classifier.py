"""Klasifikasi jendela fitur -> IDLE / KNOCK / DOOR_MOVE / DOOR_SLAM.

Dua algoritma: aturan (rule-based) dan Decision Tree (AI) hasil training.
Kalau model/door_tree.joblib ada, detector memakai Decision Tree; kalau tidak, aturan.
"""
import os
from .processing import FEATURE_KEYS

LABELS = ["IDLE", "KNOCK", "DOOR_MOVE", "DOOR_SLAM"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "door_tree.joblib")


def rule_based(f: dict) -> str:
    if f["peak_max"] >= 6.0 and f["omega_peak"] >= 2.0:
        return "DOOR_SLAM"
    if f["rotation_rad"] >= 0.4 and f["omega_peak"] >= 0.5:
        return "DOOR_MOVE"
    if f["peak_count"] >= 2 and f["rotation_rad"] < 0.15:
        return "KNOCK"
    return "IDLE"


def load_model():
    """Kembalikan bundle {'model','features','meta'} atau None kalau belum dilatih."""
    try:
        import joblib
        b = joblib.load(MODEL_PATH)
        return b if isinstance(b, dict) else {"model": b, "features": FEATURE_KEYS[:5], "meta": {}}
    except Exception:
        return None


def tree_predict(bundle, f: dict) -> str:
    return str(bundle["model"].predict([[f[k] for k in bundle["features"]]])[0])


def classify(f: dict, model=None) -> str:
    return tree_predict(model, f) if model is not None else rule_based(f)
