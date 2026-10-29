"""Simulator sensor: latihan tanpa HP + pembuat data latih untuk Decision Tree."""
import math
import random
import time
from .processing import Sample

RATE = 50
G = 9.81


def make_segment(label: str, rng: random.Random, n: int = 75):
    """Kembalikan n pasang (acc, gyro). label: IDLE/KNOCK/DOOR_MOVE/DOOR_SLAM."""
    acc = [[rng.gauss(0, 0.03), rng.gauss(0, 0.03), G + rng.gauss(0, 0.03)] for _ in range(n)]
    gyr = [[rng.gauss(0, 0.005), rng.gauss(0, 0.005), rng.gauss(0, 0.005)] for _ in range(n)]
    if label == "IDLE":
        if rng.random() < 0.4:  # gerakan kecil di sekitar (di bawah ambang)
            i = rng.randrange(n)
            acc[i][2] += rng.uniform(0.2, 0.7)
    elif label == "KNOCK":
        start = rng.randrange(0, 12)
        gap = rng.randint(8, 16)            # 0,16 - 0,32 detik
        for k in range(rng.choice([2, 3, 3, 4])):
            i = start + k * gap
            if i < n:
                acc[i][2] += rng.uniform(2.0, 5.0)
                for j in range(i, min(i + 4, n)):
                    gyr[j][2] += rng.uniform(0.0, 0.15)
    elif label == "DOOR_MOVE":
        dur = rng.randint(35, 48)           # 0,7 - 0,96 detik
        peak = rng.uniform(1.0, 1.8)
        start = rng.randrange(0, n - dur)
        for k in range(dur):
            gyr[start + k][2] += peak * math.sin(math.pi * k / dur)
            acc[start + k][2] += rng.gauss(0, 0.12)
    elif label == "DOOR_SLAM":
        dur = rng.randint(15, 22)           # 0,3 - 0,44 detik
        peak = rng.uniform(3.0, 6.0)
        start = rng.randrange(0, n - dur)
        for k in range(dur):
            gyr[start + k][2] += peak * math.sin(math.pi * k / dur)
        acc[start + dur - 1][2] += rng.uniform(7.0, 14.0)   # benturan
    return [(tuple(a), tuple(g)) for a, g in zip(acc, gyr)]


def make_window(label: str, rng: random.Random, n: int = 75):
    """Window berstempel waktu 50 Hz, siap dimasukkan ke Processor."""
    return [Sample(i / RATE, a, g) for i, (a, g) in enumerate(make_segment(label, rng, n))]


class Simulator:
    """Aliran sampel real-time. scenario: cycle, idle, knock, open, slam, pickup."""
    MAP = {"knock": "KNOCK", "open": "DOOR_MOVE", "slam": "DOOR_SLAM", "idle": "IDLE"}

    def __init__(self, role: str = "door", scenario: str = "cycle"):
        self.role, self.scenario = role, scenario
        self.rng = random.Random()

    def _next_labels(self):
        if self.role == "owner":      # HP pemilik: diam, kadang diangkat (pakai pola pintu agar ada gerak)
            return ["IDLE"] * 8 + (["DOOR_MOVE"] if self.scenario in ("pickup", "cycle") else ["IDLE"])
        if self.scenario == "cycle":
            return ["IDLE"] * 4 + ["KNOCK"] + ["IDLE"] * 4 + ["DOOR_MOVE"] + ["IDLE"] * 4 + ["DOOR_SLAM"]
        return ["IDLE"] * 4 + [self.MAP.get(self.scenario, "IDLE")]

    def stream(self):
        while True:
            for label in self._next_labels():
                for a, g in make_segment(label, self.rng, 75):
                    yield Sample(time.monotonic(), a, g)
                    time.sleep(1 / RATE)
