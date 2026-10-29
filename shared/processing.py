"""Pengolahan data di edge: dua jenis processing.

A. Getaran/ketukan (accelerometer): high-pass filter -> RMS + hitung puncak (peak).
B. Rotasi pintu (gyroscope): integrasi kecepatan sudut -> total rotasi (rad).
Yang dikirim ke cloud hanya fitur ringkas, bukan data mentah.
"""
from collections import deque
from dataclasses import dataclass
from math import sqrt

ALPHA = 0.1        # kecepatan EMA pelacak gravitasi (high-pass = magnitude - EMA)
PEAK_THR = 1.0     # m/s^2, ambang puncak ketukan
MIN_GAP = 0.12     # detik, jeda minimal antar puncak


@dataclass
class Sample:
    t: float        # detik (monotonic)
    acc: tuple      # (x, y, z) m/s^2
    gyro: tuple     # (x, y, z) rad/s


def norm(v) -> float:
    return sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


class Processor:
    def __init__(self, window: int = 75):
        self.window = window
        self.baseline = None
        self.buf = deque(maxlen=window)   # (t, hp, omega)

    def push(self, s: Sample) -> None:
        m = norm(s.acc)
        if self.baseline is None:
            self.baseline = m
        self.baseline += ALPHA * (m - self.baseline)
        self.buf.append((s.t, m - self.baseline, norm(s.gyro)))

    def ready(self) -> bool:
        return len(self.buf) == self.window

    def features(self) -> dict:
        b = list(self.buf)
        hp = [abs(x[1]) for x in b]
        # A. getaran: RMS + puncak
        hf_rms = sqrt(sum(h * h for h in hp) / len(hp))
        peaks, last_t = 0, -1e9
        for i, (t, _, _) in enumerate(b):
            left = hp[i - 1] if i > 0 else 0.0
            right = hp[i + 1] if i < len(hp) - 1 else 0.0
            if hp[i] >= PEAK_THR and hp[i] >= left and hp[i] >= right and t - last_t >= MIN_GAP:
                peaks += 1
                last_t = t
        # B. rotasi: integral |omega| dt
        rotation = sum(b[i][2] * (b[i][0] - b[i - 1][0]) for i in range(1, len(b)))
        return {
            "peak_count": peaks,
            "peak_max": round(max(hp), 3),
            "hf_rms": round(hf_rms, 3),
            "rotation_rad": round(rotation, 3),
            "omega_peak": round(max(x[2] for x in b), 3),
        }


FEATURE_KEYS = ["peak_count", "peak_max", "hf_rms", "rotation_rad", "omega_peak"]
