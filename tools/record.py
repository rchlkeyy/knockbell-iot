"""Rekam data asli berlabel dari sensor HP untuk melatih/mengkalibrasi model.

  python tools/record.py --label KNOCK --seconds 30     # lakukan ketukan berulang selama 30 detik
  python tools/record.py --label DOOR_MOVE --seconds 30 # buka-tutup pintu berulang
  python tools/record.py --label DOOR_SLAM --seconds 20
  python tools/record.py --label IDLE --seconds 30      # pintu diam
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.config import STRIDE, WINDOW                         # noqa: E402
from shared.processing import FEATURE_KEYS, Processor            # noqa: E402
from shared.sensors import get_source                             # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--label", required=True, choices=["IDLE", "KNOCK", "DOOR_MOVE", "DOOR_SLAM"])
ap.add_argument("--seconds", type=int, default=30)
ap.add_argument("--source", default="auto")
a = ap.parse_args()

source, name = get_source(a.source, "door", a.label.lower())
out = os.path.join(os.path.dirname(__file__), "..", "data", "real.csv")
new = not os.path.exists(out)
proc, since, n, end = Processor(WINDOW), 0, 0, time.time() + a.seconds
print(f"Merekam '{a.label}' selama {a.seconds} detik dari {name}. Mulai sekarang!")
with open(out, "a", newline="") as f:
    w = csv.writer(f)
    if new:
        w.writerow(FEATURE_KEYS + ["label"])
    for s in source.stream():
        proc.push(s)
        since += 1
        if proc.ready() and since >= STRIDE:
            since = 0
            ft = proc.features()
            if a.label != "IDLE" and ft["peak_max"] < 1.0 and ft["omega_peak"] < 0.3:
                continue            # buang window kosong pada kelas aksi
            w.writerow([ft[k] for k in FEATURE_KEYS] + [a.label])
            n += 1
        if time.time() > end:
            break
print(f"Selesai: {n} window disimpan ke data/real.csv")
