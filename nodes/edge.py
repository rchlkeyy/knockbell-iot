"""Edge device (jalan di HP lewat Termux, atau di laptop sebagai simulasi).

  python nodes/edge.py --role door     # HP A: dipasang di pintu (kirim telemetri, terima balasan)
  python nodes/edge.py --role owner    # HP B: bersama pemilik (kirim telemetri, terima alert)
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.config import PROJECT_ID, STRIDE, WINDOW, topic          # noqa: E402
from shared.mqtt_client import make_client, now_ms                  # noqa: E402
from shared.processing import Processor                             # noqa: E402
from shared.sensors import get_source                                # noqa: E402


def run(cmd):
    """Jalankan perintah Termux:API; kalau tidak ada (di laptop) cukup dicetak."""
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("[SIMULASI]", " ".join(cmd))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", choices=["door", "owner"], required=True)
    ap.add_argument("--source", choices=["auto", "termux", "simulator"], default="auto")
    ap.add_argument("--scenario", default="cycle", help="cycle|idle|knock|open|slam|pickup (simulator)")
    a = ap.parse_args()

    device_id = "edge1" if a.role == "door" else "edge2"
    tag = f"[{device_id.upper()}]"

    def on_message(client, userdata, msg):
        try:
            d = json.loads(msg.payload)
        except ValueError:
            return
        if a.role == "door" and d.get("action") == "speak":          # balasan 2 arah ke tamu
            print(f"{tag} Balasan untuk tamu: {d['text']}")
            run(["termux-tts-speak", d["text"]])
            run(["termux-toast", d["text"]])
            # konfirmasi ke dashboard bahwa balasan benar-benar sampai di HP pintu
            client.publish(topic("events"), json.dumps({"type": "REPLY_PLAYED", "ts": now_ms(),
                           "message": "HP pintu membacakan: " + d["text"]}), qos=1)
        elif a.role == "owner" and d.get("type") in ("KNOCK_ALERT", "INTRUSION_ALERT"):
            print(f"{tag} !!! {d['message']}")
            run(["termux-vibrate", "-d", "1500"])
            run(["termux-notification", "--title", "KnockBell", "--content", d["message"]])

    sub = topic("commands") if a.role == "door" else topic("events")
    client = make_client(f"knockbell-{PROJECT_ID}-{device_id}", topic("edge", device_id, "status"),
                         on_message, [sub])
    source, src_name = get_source(a.source, a.role, a.scenario)
    print(f"{tag} sumber sensor: {src_name} | publish: {topic('edge', device_id, 'telemetry')}")

    proc, seq, since = Processor(WINDOW), 0, 0
    for sample in source.stream():
        proc.push(sample)
        since += 1
        if proc.ready() and since >= STRIDE:
            since, seq = 0, seq + 1
            payload = {"device_id": device_id, "sequence": seq, "sent_at_ms": now_ms(),
                       "features": proc.features()}
            client.publish(topic("edge", device_id, "telemetry"), json.dumps(payload), qos=0)
            if seq % 10 == 0:
                print(f"{tag} #{seq} {payload['features']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBerhenti.")
