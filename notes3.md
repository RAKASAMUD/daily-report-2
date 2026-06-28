# Laporan Stage 3 — Delivery Implementation Plan (WhatsApp via `hermes send`)

## Overview
Implementasi sistem pengiriman notifikasi (delivery outbox) yang diintegrasikan sebagai langkah ke-4 dalam tick *engine*. Sistem ini bertugas merangkum sinyal *trading* dari *database* (yang belum terkirim), mengubahnya ke dalam bentuk kartu teks (*text card*), dan mengirimkannya menggunakan *CLI* `hermes send`. Semua fitur berjalan tanpa LLM (deterministik).

Sistem dilengkapi dengan isolasi *error* per-sinyal, mekanisme percobaan ulang (karena mengandalkan kolom `sent_at`), dan pembatasan maksimal pengiriman (cap) per tick. Total: **196 test, 0 failure** untuk keseluruhan Stage 1 sampai Stage 3.

---

## ✅ Yang Sudah Dikerjakan (Otomatis via TDD)

### A0 — Retrofit `strength` pada Signal (Stage 2 Amendment)
- **Status:** ✅ Selesai
- **Detail:** Menambahkan atribut `strength` (kekuatan sinyal) berdasar parameter `gap` dan `trend` EMA pada saat _fresh cross_ terdeteksi. Threshold telah dimasukkan ke `config.py`.
- **Dampak Code:** `types.py` (dataclass update), `config.py`, `ema_cross.py`, dan tes terkait.

### A1 — Outbox migration + delivery store helpers
- **Status:** ✅ Selesai
- **Detail:** Menambahkan kolom `sent_at` dan `strength` pada *database schema* (Idempotent Migration). Skema migrasi juga memastikan sinyal lama mendapatkan cap `sent_at = created_at` sehingga bot tidak akan melakukan *spam* data masa lalu pada pengiriman pertama.
- **Fungsi Baru:** `get_undelivered()` (untuk menarik antrean), `mark_sent()` (update status), dan `migrate_signals_schema()`.

### B1 — `format_signal` (Pure Formatter)
- **Status:** ✅ Selesai
- **Detail:** Memformat object `Signal` menjadi kartu teks yang rapi. Mengubah persentase RR, jarak TP/SL ke nilai yang wajar dan menambah *thousands separator*.

### B2 — `Notifier` adapter (`hermes send` seam)
- **Status:** ✅ Selesai
- **Detail:** Kelas `HermesNotifier` bertugas membungkus eksekusi `subprocess.run` (menggunakan input *stdin*) sehingga bot tidak pernah *crash* (menangkap semua kemungkinan error dari level sistem).
- **Konfigurasi:** Variabel `TARGET` dan `MAX_PER_TICK` telah diatur di `delivery/config.py`.

### C1 — `deliver_pending` (Outbox drain)
- **Status:** ✅ Selesai
- **Detail:** Penggerak utama pengiriman; memanggil `get_undelivered()`, memprosesnya dengan `format_signal`, dan jika berhasil `notifier.send()`, menyelesaikannya lewat `mark_sent()`. Dilengkapi proteksi error per pesan.

### D1 — Wiring delivery ke tick (Step 4)
- **Status:** ✅ Selesai
- **Detail:** Modifikasi pada `data_layer/runner.py`. Pemanggilan fungsi `run_delivery_step` ditambahkan dan diletakkan dalam blok `try/except` independen *setelah* evaluasi *Engine*. Jika delivery gagal sepenuhnya, ingest candle tetap utuh.

### E1 — Format preview (Dry-run script)
- **Status:** ✅ Selesai
- **Detail:** Penulisan script `scripts/preview_signals.py` yang bisa digunakan user secara manual untuk melihat wujud format teks sinyal teratas dari basis data tanpa melakukan proses `send()`. Disertai error handling jika tabel belum eksis.

---

## ⏳ Yang Belum Dikerjakan (Membutuhkan Proses Manual dari User)

Bagian di bawah ini adalah serangkaian eksekusi yang wajib dijalankan langsung oleh pengguna di environment tujuan (contohnya **VPS Ubuntu/Linux**):

### Task E2 — Live delivery 

**1. Pairing WhatsApp dengan `hermes`:**
- Lakukan eksekusi perintah: `hermes whatsapp` di VPS lalu *scan* QR code yang tampil di terminal.
- Install gateway *background service*: `hermes gateway install` kemudian ikuti langkah untuk menjalankan *service*-nya.
- Ketik perintah: `hermes send --list` dan simpan hasil string kontak WhatsApp tujuan (sebagai target notifikasi bot).

**2. Ubah Target Configuration:**
- Ubah secara manual nilai `TARGET = "telegram"` di dalam file `delivery/config.py` ke string kontak hermes yang didapat di atas.
*(Note: Jika kamu belum punya hermes whatsapp di VPS, membiarkannya di "telegram" bisa digunakan untuk tes dummy awal asalkan CLI hermes mendukungnya).*

**3. Uji Coba Delivery Langsung (`hermes` Smoke Test):**
- Jalankan di terminal VPS: `hermes send --to <TARGET-YANG-BENAR> "Test message Stage 3"` untuk membuktikan perantara berfungsi.

**4. Deploy Server (Git Pull) & Cron Verifikasi:**
- Update code base di VPS dengan: `git pull origin main`.
- Lakukan Replay/Backfill *candle* lama (jika perlu) menggunakan skrip: `python -m scripts.backfill` dan `python -m scripts.replay_signals --strategy ema_cross --symbol BTC/USDT --timeframe 1h`.
- Biarkan *cron runner* berjalan dan secara alami mengeksekusi tick setiap lima menit; tunggu satu sinyal baru terbuat, dan sebuah pesan WhatsApp bot akan masuk otomatis ke handphonemu!

*(Note: File ini merangkum penyelesaian penuh dari rencana instruksi Stage 3).*
