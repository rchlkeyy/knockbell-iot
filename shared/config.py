"""Konfigurasi bersama: baca .env, bentuk nama topic MQTT."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv tidak wajib untuk unit test
    pass

PROJECT_ID = os.getenv("PROJECT_ID", "kelas_iot_demo")
MQTT_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_TLS = os.getenv("MQTT_TLS", "true").lower() == "true"

SAMPLE_RATE_HZ = 50      # target pembacaan sensor
WINDOW = 75              # 75 sampel = 1,5 detik
STRIDE = 25              # kirim fitur tiap 25 sampel = 0,5 detik


def topic(*parts: str) -> str:
    """topic('edge','edge1','telemetry') -> knockbell/<PROJECT_ID>/edge/edge1/telemetry"""
    return "/".join(["knockbell", PROJECT_ID, *parts])
