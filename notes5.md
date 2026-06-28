# Laporan Stage 5 — Tracking Implementation Plan (Outcome Resolution + Real Confidence)

## Overview
Stage 5 berfokus pada melengkapi siklus penuh sistem (Develop 1 selesai) dengan cara melacak sinyal yang dikirim, menentukan statusnya (WIN / LOSS / EXPIRED), dan menghitung metrik kepercayaan (Confidence) yang otentik (berdasarkan data performa nyata).

Seluruh sistem pelacakan berjalan secara lokal dan deterministik berbekal data _candle_ 5m historis tanpa membutuhkan bantuan LLM. Total _test suite_ sekarang mencapai **238 test (0 failure)**, menjamin keandalan sistem tanpa adanya data bocor (_look-ahead bias_) maupun _crash_ berantai.

---

## ✅ Yang Sudah Dikerjakan (Otomatis via TDD)

### A1 — `outcomes` table + store helpers
- Membuat modul `tracking/` beserta tabel `outcomes` (menyimpan baris status _win/loss/expired_ per sinyal).
- **Fungsi tambahan:** `get_candles_since()` pada `db.py` untuk mengambil rentang _candle_ 5m setelah waktu *entry*.

### B1 — `resolve()` (Pure Resolution Core)
- Mengimplementasikan logika resolusi yang solid:
  - **No-Lookahead:** Mengabaikan _candle_ sebelum waktu _entry_.
  - **Pessimistic Ambiguity:** Jika harga menyentuh TP dan SL di dalam 1 *candle* 5m yang sama, dianggap sebagai **LOSS** (lebih aman/konservatif).
  - **Timeout:** Sinyal yang lewat batas waktu (`TIMEOUT_BARS = 10`) tanpa menyentuh TP/SL akan berstatus **EXPIRED**. Nilai _realized RR_ dikalkulasi secara presisi dan bisa bernilai negatif jika ditutup dalam keadaan merugi.

### C1 & C2 — Orchestration & Wiring (Step 5)
- Membuat fungsi pembungkus `run_resolver()` yang menarik data _pending signals_ (belum teresolusi), menarik *candle* historisnya, lalu memanggil fungsi `resolve()`.
- Menyambungkannya ke `data_layer/runner.py` sebagai **langkah ke-5** (langkah terakhir). Diisolasi dengan `try-except` sehingga jika terjadi kegagalan _tracking_, proses _ingest_ (langkah 1) maupun pengiriman notifikasi (langkah 3) tetap aman.

### D1 & D2 — Stats Aggregation & "Confidence" Card
- Membuat fungsi aglomerasi `aggregate_stats()` untuk menghitung _win-rate_ dan _expectancy_ per kelompok strategi-timeframe.
- Apabila data sinyal _resolved_ belum mencapai 20 sampel (konfigurasi `N_MIN_CONFIDENCE`), kartu notifikasi akan menampilkan teks **Confidence: building (n=X)**.
- Jika sudah cukup sampel, berubah menjadi metrik nyata: **Confidence: 65% TP-first (n=23)**. Modifikasi _pure_ sudah masuk ke `delivery/format.py`.

### E1 & E2 (Script) — Weekly Recap & Backlog Resolver
- **E1:** Script `scripts/weekly_recap.py` bertugas mengkalkulasi metrik _win-rate_ & _expectancy_ dari seluruh strategi, kemudian merangkumnya dalam bentuk tabel ke WhatsApp melalui Hermes.
- **E2:** Script `scripts/resolve_backlog.py` disiapkan bagi _user_ untuk menyelesaikan sinyal-sinyal lama di VPS secara massal tanpa perlu menunggu _tick runner_.

---

## ⏳ Yang Belum Dikerjakan (Membutuhkan Proses Manual dari User di VPS)

Tahap ini **wajib** dilakukan langsung dari terminal VPS untuk merealisasikan penggunaan di *environment* sesungguhnya:

### 1. Deploy dan Update
Masuk ke terminal VPS, lalu perbarui _codebase_:
```bash
git pull origin main
```

### 2. Selesaikan Backlog Data (One-Time Execution)
Jalankan perintah ini satu kali saja agar sinyal-sinyal lama yang sudah terkumpul di *database* VPS langsung dievaluasi (WIN/LOSS/EXPIRED):
```bash
python -m scripts.resolve_backlog
```
*Verifikasi: Lakukan spot-check pada tabel `outcomes`.*
```bash
sqlite3 data/bot.db "SELECT * FROM outcomes ORDER BY resolved_at DESC LIMIT 10;"
```
*Bandingkan hasilnya (entry time vs status win/loss) dengan chart TradingView / Binance aslinya.*

### 3. Konfigurasi Cron untuk Weekly Recap
Buat automasi untuk mengirim rapor performa strategi mingguan setiap hari Senin (misal jam 00.00). Buka `crontab -e` di VPS dan tambahkan:
```bash
0 0 * * 1 cd /path/ke/folder/Sinyal && /path/ke/venv/bin/python -m scripts.weekly_recap >> data/recap.log 2>&1
```

### 4. Observasi *Live*
Biarkan sistem *runner* berjalan seperti biasa via cron (setiap 5 menit). Amati _message_ WhatsApp yang masuk selanjutnya; pastikan baris **Confidence:** muncul dan *resolver* terus bertugas di belakang layar menyelesaikan status _card_ beberapa jam setelahnya.

> **Note:** Stage 5 menandai berakhirnya keseluruhan fase **Develop 1** dari masterplan. 
> Semua tulang punggung fungsional sistem, dari penarikan data hingga determinasi _outcome_, telah diimplementasikan 100%.
