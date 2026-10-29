"""Latih Decision Tree. Data = simulator + (opsional) data asli dari data/*.csv.

  python tools/train_model.py
"""
import csv
import glob
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sklearn.metrics import classification_report, confusion_matrix   # noqa: E402
from sklearn.model_selection import train_test_split                  # noqa: E402
from sklearn.tree import DecisionTreeClassifier, export_text          # noqa: E402
import joblib                                                          # noqa: E402

from shared.classifier import LABELS, MODEL_PATH, rule_based           # noqa: E402
from shared.processing import FEATURE_KEYS, Processor                  # noqa: E402
from shared.simulator import make_window                               # noqa: E402


def synth(n_per_class=400, seed=1):
    rng, rows = random.Random(seed), []
    for label in LABELS:
        for _ in range(n_per_class):
            p = Processor(75)
            for s in make_window(label, rng):
                p.push(s)
            rows.append((p.features(), label))
    return rows


def real():
    rows = []
    for path in glob.glob(os.path.join(os.path.dirname(__file__), "..", "data", "*.csv")):
        with open(path) as f:
            for r in csv.DictReader(f):
                rows.append(({k: float(r[k]) for k in FEATURE_KEYS}, r["label"]))
    return rows


if __name__ == "__main__":
    rows = synth() + real()
    X = [[f[k] for k in FEATURE_KEYS] for f, _ in rows]
    y = [l for _, l in rows]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=7, stratify=y)
    tree = DecisionTreeClassifier(max_depth=4, random_state=0).fit(Xtr, ytr)
    pred = tree.predict(Xte)
    rule = [rule_based(dict(zip(FEATURE_KEYS, x))) for x in Xte]
    acc = lambda a, b: sum(p == t for p, t in zip(a, b)) / len(b)
    print(f"Data latih+uji: {len(rows)} window ({len(real())} dari data asli)")
    print(f"Akurasi rule-based  : {acc(rule, yte):.3f}")
    print(f"Akurasi DecisionTree: {acc(pred, yte):.3f}\n")
    print(classification_report(yte, pred, labels=LABELS, digits=3))
    print("Confusion matrix (baris=asli, kolom=prediksi):", LABELS)
    print(confusion_matrix(yte, pred, labels=LABELS))
    print("\n" + export_text(tree, feature_names=FEATURE_KEYS))
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(tree, MODEL_PATH)
    print("Model disimpan:", os.path.abspath(MODEL_PATH))
