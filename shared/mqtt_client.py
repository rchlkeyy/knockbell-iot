"""Pembuat klien MQTT (paho 2.x) dengan TLS, LWT, dan auto-reconnect."""
import json
import time
import paho.mqtt.client as mqtt
from .config import MQTT_HOST, MQTT_PORT, MQTT_TLS


def make_client(client_id: str, status_topic: str = None, on_message=None, subscriptions=()):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if MQTT_TLS:
        c.tls_set()
    if status_topic:
        c.will_set(status_topic, json.dumps({"state": "offline"}), qos=1, retain=True)

    def _on_connect(client, userdata, flags, reason_code, properties):
        print(f"[MQTT] terhubung ke {MQTT_HOST}:{MQTT_PORT} ({reason_code})")
        for t in subscriptions:
            client.subscribe(t, qos=1)
            print(f"[MQTT] subscribe {t}")
        if status_topic:
            client.publish(status_topic, json.dumps({"state": "online"}), qos=1, retain=True)

    c.on_connect = _on_connect
    if on_message:
        c.on_message = on_message
    c.reconnect_delay_set(1, 10)
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    c.loop_start()
    return c


def now_ms() -> int:
    return int(time.time() * 1000)
