"""Klasifikasi jendela fitur -> IDLE / KNOCK / DOOR_MOVE / DOOR_SLAM.

Dua algoritma: aturan (rule-based) dan Decision Tree (AI) hasil training.
Kalau model/door_tree.joblib ada, detector memakai Decision Tree; kalau tidak, aturan.
"""
import os
from .processing import FEATURE_KEYS

LABELS = ["IDLE", "KNOCK", "DOOR_MOVE", "DOOR_SLAM"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "door_tree.joblib")


def rule_based(f: dict) -> str:
    if f["peak_max"] >= 4.0:
        return "DOOR_SLAM"
        
    if f["rotation_rad"] >= 0.8 or f["omega_peak"] >= 2.0:
        return "DOOR_MOVE"
        
    if f["peak_count"] >= 1 and f["peak_max"] >= 1.5 and f["omega_peak"] < 1.0:
        return "KNOCK"
        
    return "IDLE"


def load_model():
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def tree_predict(model, f: dict) -> str:
    return str(model.predict([[f[k] for k in FEATURE_KEYS]])[0])


def classify(f: dict, model=None) -> str:
    return tree_predict(model, f) if model is not None else rule_based(f)
