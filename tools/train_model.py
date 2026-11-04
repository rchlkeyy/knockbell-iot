"""Latih Decision Tree dari DATA ASLI (data/real_v2.csv), evaluasi jujur, bandingkan dengan if-else.

  python tools/train_model.py              # data asli dari tools/record.py
  python tools/train_model.py --sim        # coba alur latihan memakai data simulasi (bukan untuk laporan)

Evaluasi memakai cross-validation yang memisahkan per REKAMAN (session), jadi window yang
bertetangga tidak bocor ke data uji. Hasil lengkap disimpan di model/report.txt.
"""
import argparse
import csv
import datetime
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import joblib                                                                  # noqa: E402
from sklearn.metrics import classification_report, confusion_matrix            # noqa: E402
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict    # noqa: E402
from sklearn.tree import DecisionTreeClassifier, export_text                   # noqa: E402

from shared.classifier import LABELS, MODEL_PATH, rule_based                   # noqa: E402
from shared.processing import FEATURE_KEYS, Processor                          # noqa: E402
from shared.simulator import make_window                                       # noqa: E402

LINES = []


def out(s=""):
    print(s)
    LINES.append(str(s))


def load_csv(path):
    with open(path) as f:
        r = csv.DictReader(f)
        keys = [k for k in FEATURE_KEYS if k in r.fieldnames]
        rows = list(r)
    return keys, [[float(x[k]) for k in keys] for x in rows], [x["label"] for x in rows], [x["session"] for x in rows]


def load_sim():
    rng, X, y, g = random.Random(1), [], [], []
    for label in LABELS:
        for sess in range(6):
            for _ in range(40):
                p = Processor(75)
                for s in make_window(label, rng):
                    p.push(s)
                f = p.features()
                X.append([f[k] for k in FEATURE_KEYS]); y.append(label); g.append(f"{label}-{sess}")
    return FEATURE_KEYS, X, y, g


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "..", "data", "real_v2.csv"))
    ap.add_argument("--sim", action="store_true")
    a = ap.parse_args()

    keys, X, y, g = load_sim() if a.sim else load_csv(a.data)
    out(f"Sumber data: {'SIMULASI (bukan untuk laporan)' if a.sim else a.data}")
    out(f"Jumlah window: {len(y)} | rekaman: {len(set(g))} | fitur: {keys}")
    sess_per_class = {l: len({s for s, t in zip(g, y) if t == l}) for l in LABELS}
    cnt = {l: y.count(l) for l in LABELS}
    out(f"Window per kelas: {cnt} | rekaman per kelas: {sess_per_class}")
    if min(cnt.values()) == 0 or min(sess_per_class.values()) < 2:
        sys.exit("Tiap kelas butuh minimal 2 rekaman. Jalankan: python tools/record.py --guided")
    if min(cnt.values()) < 40:
        out("PERINGATAN: ada kelas dengan < 40 window. Rekam lebih banyak supaya hasil stabil.")

    cv = StratifiedGroupKFold(n_splits=min(3, min(sess_per_class.values())), shuffle=True, random_state=0)
    acc = lambda p: sum(a == b for a, b in zip(p, y)) / len(y)
    idx = {k: keys.index(k) for k in keys}
    rule_pred = [rule_based({k: row[idx[k]] for k in keys}) for row in X]
    out(f"\nAkurasi if-else (rule-based): {acc(rule_pred):.3f}")

    best = None
    for depth in (2, 3, 4, 5):
        clf = DecisionTreeClassifier(max_depth=depth, class_weight="balanced", random_state=0)
        pred = cross_val_predict(clf, X, y, cv=cv, groups=g)
        out(f"Decision Tree kedalaman {depth}: akurasi CV = {acc(pred):.3f}")
        if best is None or acc(pred) > best[0] + 1e-9:
            best = (acc(pred), depth, pred)
    tree_acc, depth, pred = best
    out(f"\nDipilih kedalaman {depth} (akurasi CV {tree_acc:.3f}) dibanding if-else {acc(rule_pred):.3f}\n")
    out(classification_report(y, pred, labels=LABELS, digits=3, zero_division=0))
    out(f"Confusion matrix (baris=asli, kolom=prediksi) urutan {LABELS}:")
    out(str(confusion_matrix(y, pred, labels=LABELS)))

    final = DecisionTreeClassifier(max_depth=depth, class_weight="balanced", random_state=0).fit(X, y)
    out("\nAturan yang dipelajari model:\n" + export_text(final, feature_names=keys))
    meta = {"tgl": datetime.date.today().isoformat(), "n_window": len(y), "akurasi_cv": round(tree_acc, 3),
            "akurasi_ifelse": round(acc(rule_pred), 3), "kedalaman": depth, "simulasi": a.sim}
    if not a.sim:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({"model": final, "features": keys, "meta": meta}, MODEL_PATH)
        out(f"Model disimpan: {os.path.abspath(MODEL_PATH)}")
        with open(os.path.join(os.path.dirname(MODEL_PATH), "report.txt"), "w") as f:
            f.write("\n".join(LINES))
        out("Laporan disimpan: model/report.txt (lampirkan di GitHub dan PPT)")
    else:
        out("Mode --sim: model TIDAK disimpan.")
