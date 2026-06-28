# Laporan Develop 2 — Mean-Reversion Bollinger Strategy ("Buy on Low")

## Overview
Develop 2 bertujuan menambah strategi _trading_ kedua yang saling melengkapi dengan EMA Cross. Strategi **Bollinger Mean-Reversion** ini dirancang untuk mendulang untung di kondisi pasar yang _choppy_ / _ranging_ dengan menangkap momen pantulan harga (*bounce*) dari titik ekstrem terbawah (*lower band*).

Sistem arsitektur dari *Develop 1* yang bersifat lepas (*decoupled*) terbukti efektif: strategi ini berhasil disuntikkan murni tanpa perlu menyentuh satu pun kode di modul pengumpul data (_ingest_), pengiriman pesan (_delivery_), ataupun pelacakan _win/loss_ (_tracking_). Keseluruhan _test suite_ proyek ini telah mencapai **255 test (100% Passed)**.

---

## ✅ Yang Sudah Dikerjakan (Otomatis via TDD)

### A1 — Indikator Bollinger Bands (Pure)
- Membuat fungsi perhitungan murni `bollinger_bands` di `signal_engine/indicators.py` yang mengembalikan tiga nilai: _middle_ (SMA), _upper_, dan _lower band_.

### A2 — Config MR & Helper EMA Slope
- Menyimpan konfigurasi khusus parameter strategi ke dalam `MEAN_REV_PARAMS` (berisi periode BB, standar deviasi, toleransi _buffer_ untuk _stop loss_, dsb).
- Menambah fungsi bantu `ema_slope_falling` untuk mendeteksi apakan arah laju EMA200 sedang turun.

### B1 — Inti Strategi (`bollinger_mr`)
- Logika fungsi _pure_ selesai diimplementasikan di `signal_engine/strategies/bollinger_mr.py` dengan penanganan edge cases:
  - **Bounce Confirmation:** Memastikan *close* candle sebelumnya ada di bawah *lower band*, dan *close* sekarang kembali naik ke atas *lower band*.
  - **TP (Target Profit):** Tepat di garis *middle band* (SMA).
  - **SL (Stop Loss):** Tepat di titik terendah (lowest low) selama harga terendam di bawah *lower band*, dikurangi *buffer* ATR.
  - **Downtrend Filter:** Sinyal langsung dibatalkan (return `None`) jika harga tertinggal di bawah garis EMA200 dan EMA200 sedang **menukik turun**.
  - **RR Gate:** Pembatalan sinyal yang _reward-to-risk ratio_-nya terlalu kecil (< 1.0).

### B2 — Auto-Pickup via Registry
- Strategi didaftarkan di dalam `signal_engine/registry.py`. Hasilnya, secara otomatis *signal engine* yang dieksekusi berkala via Cron akan turut memanggil `bollinger_mr` bersamaan dengan `ema_cross`.

---

## ⏳ Yang Belum Dikerjakan (Wajib Manual di VPS)

Langkah-langkah eksekusi terminal (*bash*) di bawah ini **belum dilakukan**. Wajib dieksekusi manual oleh User di *environment* VPS.

### C1 — Replay Dry-Run (Validasi Kualitas Sinyal)
Skrip ini bertujuan mengetes apakah sinyal MR ini berjalan logis pada histori masa lalu sebelum benar-benar dihidupkan.
**Status: Belum dilakukan**

_Jalankan di terminal VPS:_
```bash
python -u -c "
import sqlite3, pandas as pd
from data_layer.config import DB_PATH
from signal_engine.config import MEAN_REV_PARAMS, CANDLE_LIMIT
from signal_engine.strategies.bollinger_mr import bollinger_mean_reversion

for sym in ['BTC/USDT', 'ETH/USDT']:
    for tf in ['1h', '4h']:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            'SELECT open_time, open, high, low, close, volume FROM candles '
            'WHERE symbol=? AND timeframe=? ORDER BY open_time ASC',
            conn, params=(sym, tf))
        params = {**MEAN_REV_PARAMS, 'symbol': sym, 'timeframe': tf}
        sigs = []
        for i in range(CANDLE_LIMIT, len(df)):
            w = df.iloc[i - CANDLE_LIMIT + 1 : i + 1]
            s = bollinger_mean_reversion(w, params)
            if s: sigs.append(s)
        print(f'{sym} {tf}: {len(sigs)} signals')
        for s in sigs[:3]:
            t = pd.to_datetime(s.bar_open_time, unit='ms')
            print(f'  {t}  entry={s.entry:.2f} tp={s.tp:.2f} sl={s.sl:.2f} rr={s.rr:.2f} str={s.strength}')
"
```

### C2 — Deploy Live & Obeservasi
Penarikan kode sumber terbaru ke VPS agar strategi MR resmi aktif dan disebarkan via Hermes ke WhatsApp.
**Status: Belum dilakukan**

_Jalankan di terminal VPS:_
```bash
git pull origin main
```
_Pengecekan (Opsional, tunggu beberapa jam pasca deploy):_
```bash
sqlite3 data/candles.db "SELECT symbol,timeframe,strategy,entry,tp,sl,rr,strength FROM signals WHERE strategy='bollinger_mr' ORDER BY created_at DESC LIMIT 10;"
```
