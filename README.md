# KnockBell — Bel Pintu Pintar Dua Arah dari Dua HP

Mata Kuliah Internet of Things · Kelompok 7

**Masalah:** penghuni kos/ruang belajar yang memakai headphone atau tertidur tidak mendengar ketukan pintu
(tamu, kurir, teman), dan tidak tahu kalau pintunya dibuka orang saat ia pergi.

**Ide:** HP A ditempel di pintu (Edge 1), HP B bersama pemilik (Edge 2). Ketukan/pintu bergerak terdeteksi →
HP B bergetar. Ketika pemilik mengangkat HP B, HP A di pintu otomatis mengucapkan
"Sebentar ya, penghuni sedang menuju pintu." (komunikasi **2 arah**). Mode AWAY menjaga pintu saat pemilik pergi.

## Arsitektur
```
HP A (pintu) --telemetry--> [MQTT Broker HiveMQ, TLS 8883] --telemetry--> Laptop (detector)
HP B (owner) --telemetry-->                                               |  klasifikasi + keputusan
HP B  <------events (alert)-------------------------------------------------+
HP A  <------commands (balasan suara)--------------------------------------+
Dashboard web (WebSocket TLS 8884): status, grafik, mode HOME/AWAY, tombol balas
```
Topic: `knockbell/<PROJECT_ID>/{edge/edge1|edge2/telemetry, events, commands, control, state}`

## Sesuai ketentuan tugas
| Ketentuan | Di KnockBell |
|---|---|
| ≥ 2 edge device | HP A (pintu) dan HP B (pemilik) |
| ≥ 2 sensor | Accelerometer + gyroscope di tiap HP |
| ≥ 2 data processing | (A) high-pass + RMS + deteksi puncak ketukan; (B) integrasi gyroscope → rotasi pintu |
| Algoritma | Rule-based + Decision Tree (AI) + sensor fusion HP A & HP B (konfirmasi pemilik) |
| Protokol ke cloud | MQTT over TLS ke HiveMQ publik, QoS 0/1, LWT, 2 arah |
| Dashboard (opsional) | `dashboard/index.html` |

## Cara jalan
```bash
# Laptop
pip install -r requirements-laptop.txt
cp .env.example .env        # isi PROJECT_ID unik
python tools/train_model.py # opsional: latih Decision Tree (lihat PANDUAN soal data asli)
python nodes/detector.py
# buka dashboard/index.html di browser, isi PROJECT_ID, klik Hubungkan

# HP A (Termux) -> tempel di pintu           # HP B (Termux) -> di dekat pemilik
python nodes/edge.py --role door             python nodes/edge.py --role owner
```
Tanpa HP: tambahkan `--source simulator` di kedua edge (otomatis simulasi di laptop).

## Tes
```bash
python tests/test_all.py
```

## HP B memakai iPhone (opsional)
`dashboard/owner.html` menggantikan `nodes/edge.py --role owner` di iPhone/Safari. Halaman harus dibuka lewat
HTTPS (mis. GitHub Pages): `https://USERNAME.github.io/knockbell-iot/dashboard/owner.html`.
Isi PROJECT_ID yang sama, tekan Mulai, izinkan sensor gerak, biarkan layar menyala.
