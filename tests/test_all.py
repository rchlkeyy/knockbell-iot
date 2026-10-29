"""Unit test offline (tanpa HP, tanpa internet):  python tests/test_all.py"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nodes.detector import Detector, REPLY_TEXT                  # noqa: E402
from shared.classifier import LABELS, rule_based                  # noqa: E402
from shared.processing import Processor                           # noqa: E402
from shared.simulator import make_window                          # noqa: E402


def feats(label, rng):
    p = Processor(75)
    for s in make_window(label, rng):
        p.push(s)
    return p.features()


def test_rules_accuracy():
    rng, ok, tot = random.Random(42), 0, 0
    for label in LABELS:
        for _ in range(200):
            ok += rule_based(feats(label, rng)) == label
            tot += 1
    acc = ok / tot
    print(f"akurasi rule-based (simulasi): {acc:.3f}")
    assert acc >= 0.95


def test_feature_sanity():
    rng = random.Random(1)
    assert feats("KNOCK", rng)["peak_count"] >= 2
    assert feats("DOOR_MOVE", rng)["rotation_rad"] >= 0.4
    assert feats("IDLE", rng)["peak_count"] == 0


class Clock:
    t = 1000.0
    def __call__(self): return self.t


def make():
    sent, clk = [], Clock()
    d = Detector(lambda t, p: sent.append((t.split("/")[-1], p)), clock=clk)
    return d, sent, clk


KNOCK = {"peak_count": 3, "peak_max": 4, "hf_rms": 1, "rotation_rad": 0.05, "omega_peak": 0.1}
MOVE = {"peak_count": 0, "peak_max": 0.3, "hf_rms": 0.1, "rotation_rad": 0.8, "omega_peak": 1.2}
PICKED = {"peak_count": 0, "peak_max": 0.5, "hf_rms": 0.9, "rotation_rad": 0.6, "omega_peak": 1.0}


def types(sent): return [p["type"] for t, p in sent if t == "events"]


def test_knock_then_ack_two_way():
    d, sent, clk = make()
    d.on_door(KNOCK)
    assert "KNOCK_ALERT" in types(sent)
    clk.t += 5
    d.on_owner(PICKED)
    assert "ACK" in types(sent)
    cmd = [p for t, p in sent if t == "commands"][0]
    assert cmd["action"] == "speak" and cmd["text"] == REPLY_TEXT


def test_ack_expires():
    d, sent, clk = make()
    d.on_door(KNOCK); clk.t += 30
    d.on_owner(PICKED)
    assert "ACK" not in types(sent)


def test_cooldown_dedup():
    d, sent, clk = make()
    d.on_door(KNOCK); clk.t += 0.5; d.on_door(KNOCK)
    assert types(sent).count("KNOCK_ALERT") == 1


def test_mode_away_vs_home():
    d, sent, clk = make()
    d.on_door(MOVE)
    assert types(sent) == ["DOOR_INFO"]
    clk.t += 10
    d.on_control({"action": "set_mode", "mode": "AWAY"})
    d.on_door(MOVE)
    assert "INTRUSION_ALERT" in types(sent)


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn(); print("PASS", fn.__name__)
    print(f"\n{len(fns)} tes lulus.")
