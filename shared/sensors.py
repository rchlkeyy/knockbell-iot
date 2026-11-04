"""Pembaca sensor HP Android lewat Termux:API (streaming) + pemilihan sumber."""
import json
import queue
import subprocess
import threading
import time
from .processing import Sample
from .simulator import Simulator


def _cleanup():
    """Lepas listener sensor yang masih menggantung (penyebab rekaman ke-2 macet)."""
    try:
        subprocess.run(["termux-sensor", "-c"], capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def find_sensor_names():
    out = subprocess.run(["termux-sensor", "-l"], capture_output=True, text=True, timeout=15, check=True).stdout
    names = json.loads(out)["sensors"]

    bad = ("uncali", "linear", "game", "geo", "gravity", "rot_vec", "rotvec")

    def pick(keys):
        cands = [n for n in names if any(k in n.lower() for k in keys)
                 and not any(b in n.lower() for b in bad)]
        cands.sort(key=lambda n: "wakeup" in n.lower())   # utamakan yang non-wakeup
        return cands[0] if cands else None

    return pick(("accelerometer", "_acc")), pick(("gyroscope", "_gyro"))


class TermuxSensors:
    def __init__(self, delay_ms: int = 20):
        self.acc_name, self.gyro_name = find_sensor_names()
        if not (self.acc_name and self.gyro_name):
            raise RuntimeError("Accelerometer/Gyroscope tidak ditemukan. Cek: termux-sensor -l")
        self.delay_ms = delay_ms

    def stream(self, max_seconds=None, first_timeout=8):
        """Alirkan sampel. Berhenti sendiri setelah max_seconds, dan gagal jelas kalau sensor macet."""
        _cleanup()
        cmd = ["termux-sensor", "-s", f"{self.acc_name},{self.gyro_name}", "-d", str(self.delay_ms)]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        q = queue.Queue()

        def reader():
            for line in proc.stdout:
                q.put(line)
            q.put(None)

        threading.Thread(target=reader, daemon=True).start()
        dec, buf, got, t0 = json.JSONDecoder(), "", False, time.monotonic()
        acc, gyro = (0.0, 0.0, 9.81), (0.0, 0.0, 0.0)
        try:
            while True:
                try:
                    line = q.get(timeout=1.0)
                except queue.Empty:
                    if max_seconds and time.monotonic() - t0 > max_seconds:
                        return
                    if not got and time.monotonic() - t0 > first_timeout:
                        raise RuntimeError("Sensor tidak mengirim data. Jalankan 'termux-sensor -c', tutup lalu "
                                           "buka Termux lagi, dan biarkan layar menyala.")
                    continue
                if line is None:
                    return
                buf += line
                while True:
                    s = buf.lstrip()
                    if not s:
                        buf = ""
                        break
                    try:
                        obj, end = dec.raw_decode(s)
                    except ValueError:
                        break          # objek JSON belum lengkap, tunggu baris berikutnya
                    buf = s[end:]
                    if self.gyro_name in obj:
                        gyro = tuple(float(v) for v in obj[self.gyro_name]["values"][:3])
                    if self.acc_name in obj:
                        acc = tuple(float(v) for v in obj[self.acc_name]["values"][:3])
                        got = True
                        yield Sample(time.monotonic(), acc, gyro)
                        if max_seconds and time.monotonic() - t0 > max_seconds:
                            return
        finally:
            proc.terminate()
            try:
                proc.wait(2)
            except subprocess.TimeoutExpired:
                proc.kill()
            _cleanup()


def get_source(kind: str, role: str, scenario: str):
    """kind: auto | termux | simulator. 'auto' = Termux kalau ada, selain itu simulator."""
    if kind == "simulator":
        return Simulator(role, scenario), "simulator"
    try:
        return TermuxSensors(), "android"
    except (FileNotFoundError, RuntimeError, subprocess.SubprocessError, ValueError) as e:
        if kind == "termux":
            raise
        print(f"[SENSOR] Termux tidak tersedia ({e.__class__.__name__}), pakai simulator.")
        return Simulator(role, scenario), "simulator"
