"""Rekam data ASLI berlabel dari sensor HP A (di pintu) untuk melatih AI.

Cara paling mudah (dipandu suara, 3 ronde x 4 kejadian, sekitar 8 menit):
  python tools/record.py --guided

Atau satu kejadian saja:
  python tools/record.py --label KNOCK --seconds 30
Hasil: data/real_v2.csv (tiap rekaman punya 'session' agar evaluasi tidak bocor).
"""
import argparse
import csv
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.config import STRIDE, WINDOW                         # noqa: E402
from shared.processing import FEATURE_KEYS, Processor            # noqa: E402
from shared.sensors import get_source                             # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "real_v2.csv")
PLAN = [("IDLE", 25, "Biarkan pintu DIAM"),
        ("KNOCK", 30, "KETUK pintu berulang-ulang, bervariasi pelan dan keras"),
        ("DOOR_MOVE", 30, "BUKA dan TUTUP pintu pelan, berulang-ulang"),
        ("DOOR_SLAM", 25, "BANTING pintu, ulangi dengan jeda 2 detik")]


def say(text):
    print(">>", text)
    try:
        subprocess.Popen(["termux-tts-speak", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def record(label, seconds, source_kind, writer):
    source, name = get_source(source_kind, "door", label.lower())
    session = f"{label}-{int(time.time())}"
    proc, since, kept, total, t0 = Processor(WINDOW), 0, 0, 0, time.time()
    for s in source.stream():
        proc.push(s)
        total += 1
        since += 1
        if proc.ready() and since >= STRIDE:
            since = 0
            ft = proc.features()
            if not (label != "IDLE" and ft["peak_max"] < 1.0 and ft["omega_peak"] < 0.3):
                writer.writerow([ft[k] for k in FEATURE_KEYS] + [label, session])
                kept += 1
        if time.time() - t0 > seconds:
            break
    rate = total / (time.time() - t0)
    print(f"   {label}: {kept} window disimpan | laju sensor ~{rate:.0f} Hz ({name})")
    if rate < 30:
        print("   PERINGATAN: laju sensor rendah (<30 Hz), ketukan bisa terlewat. Tutup aplikasi lain, "
              "matikan hemat baterai untuk Termux, lalu coba lagi.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", choices=[p[0] for p in PLAN])
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--guided", action="store_true")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--source", default="auto")
    a = ap.parse_args()
    if not (a.guided or a.label):
        ap.error("pakai --guided atau --label")
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FEATURE_KEYS + ["label", "session"])
        jobs = ([(l, sec, msg) for _ in range(a.rounds) for l, sec, msg in PLAN] if a.guided
                else [(a.label, a.seconds, "Lakukan kejadian " + a.label)])
        for i, (label, sec, msg) in enumerate(jobs, 1):
            say(f"Rekaman {i} dari {len(jobs)}. {msg}. Mulai dalam 5 detik")
            time.sleep(5)
            say("Mulai")
            record(label, sec, a.source, w)
            f.flush()
            say("Selesai, istirahat sebentar")
            time.sleep(2)
    print(f"Selesai. Data: {os.path.abspath(OUT)}")
