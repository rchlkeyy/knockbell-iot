"""Detector (jalan di laptop): subscribe telemetri 2 edge -> klasifikasi -> keputusan -> alert & balasan.

  python nodes/detector.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.classifier import classify, load_model     # noqa: E402
from shared.config import PROJECT_ID, topic             # noqa: E402

COOLDOWN = 3.0        # detik, cegah event ganda dari window yang saling tumpang tindih
ACK_WINDOW = 20.0     # detik, pemilik harus mengangkat HP B maksimal segini setelah ketukan
REPLY_TEXT = "Sebentar ya, penghuni sedang menuju pintu."


def owner_active(f: dict) -> bool:
    """HP B dianggap 'diangkat pemilik' kalau bergetar/berotasi cukup besar."""
    return f["hf_rms"] >= 0.4 or f["rotation_rad"] >= 0.3


class Detector:
    def __init__(self, publish, model=None, clock=time.time):
        self.publish, self.model, self.clock = publish, model, clock
        self.mode = "HOME"
        self.last_event = {}
        self.pending_knock = None
        self.owner_is_active = False

    def _emit(self, etype, message, label=None):
        ev = {"type": etype, "message": message, "label": label, "mode": self.mode,
              "ts": int(self.clock() * 1000)}
        self.publish(topic("events"), ev)
        print(f"[DETECTOR] {etype}: {message}")

    def _cooling(self, key):
        now = self.clock()
        if now - self.last_event.get(key, -1e9) < COOLDOWN:
            return True
        self.last_event[key] = now
        return False

    def on_door(self, f):
        label = classify(f, self.model)
        if label == "KNOCK":
            if self.clock() - self.last_event.get("DOOR", -1e9) < 3.0:
                self._state(label)
                return label
            if not self._cooling("KNOCK"):
                self.pending_knock = self.clock()
                self._emit("KNOCK_ALERT", "Ada yang mengetuk pintu.", label)
        elif label in ("DOOR_MOVE", "DOOR_SLAM"):
            self.last_event["KNOCK"] = self.clock()
            if not self._cooling("DOOR"):
                what = "dibanting" if label == "DOOR_SLAM" else "dibuka/ditutup"
                if self.mode == "AWAY":
                    self._emit("INTRUSION_ALERT", f"Pintu {what} saat kamu pergi!", label)
                else:
                    self._emit("DOOR_INFO", f"Pintu {what}.", label)
        self._state(label)
        return label

    def on_owner(self, f):
        self.owner_is_active = owner_active(f)
        if self.pending_knock and self.owner_is_active:
            if self.clock() - self.pending_knock <= ACK_WINDOW:
                self.publish(topic("commands"), {"target": "edge1", "action": "speak", "text": REPLY_TEXT})
                self._emit("ACK", "Pemilik mengangkat HP, balasan dikirim ke pintu.")
            self.pending_knock = None

    def on_control(self, d):
        if d.get("action") == "set_mode" and d.get("mode") in ("HOME", "AWAY"):
            self.mode = d["mode"]
            self._emit("MODE", f"Mode sekarang: {self.mode}")

    def _state(self, label):
        self.publish(topic("state"), {"label": label, "mode": self.mode,
                                       "owner_active": self.owner_is_active,
                                       "ts": int(self.clock() * 1000)})


def main():
    from shared.mqtt_client import make_client

    model = load_model()
    print(f"PROJECT_ID: {PROJECT_ID} | algoritma: {'Decision Tree' if model else 'rule-based'}")

    holder = {}

    def publish(t, payload):
        holder["c"].publish(t, json.dumps(payload), qos=1)

    det = Detector(publish, model)

    def on_message(client, userdata, msg):
        try:
            d = json.loads(msg.payload)
        except ValueError:
            return
        if msg.topic == topic("control"):
            det.on_control(d)
        elif msg.topic.endswith("/telemetry"):
            (det.on_door if d.get("device_id") == "edge1" else det.on_owner)(d["features"])

    holder["c"] = make_client(f"knockbell-{PROJECT_ID}-detector", topic("detector", "status"), on_message,
                              [topic("edge", "+", "telemetry"), topic("control")])
    print("Menunggu telemetri Edge 1 (pintu) dan Edge 2 (pemilik)...  Ctrl+C untuk berhenti.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
