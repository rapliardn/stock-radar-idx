# 📈 IDX Stock Radar & Technical Analyzer

Tools analisa saham pribadi untuk saham-saham di Bursa Efek Indonesia (IDX).
Jalan 100% di komputer/laptop kamu sendiri (localhost) — gratis, tidak perlu API key.

## Fitur

1. **Analisa Saham per Ticker**
   - Chart candlestick interaktif + EMA 9 / 21 / 50
   - RSI (14) dengan garis overbought (70) & oversold (30)
   - Support & Resistance (pivot point harian + high/low 20 hari)
   - Ringkasan analisa otomatis dalam Bahasa Indonesia

2. **Radar Saham Harian**
   - Scan watchlist untuk sinyal:
     - 🚀 **Breakout** — harga tembus resistance 20 hari + volume tinggi
     - 🔄 **Bounce/Rebound** — pantul dari support/EMA21 dengan RSI membaik
     - 🔊 **Volume Spike** — lonjakan volume ≥2x rata-rata 20 hari

3. **Berita IHSG & Market Global**
   - Berita terbaru seputar IHSG & saham Indonesia
   - Berita market global (Wall Street, dll)
   - Sumber: Google News RSS (real-time, tanpa API key)

## Cara Install & Jalankan (Windows / Mac / Linux)

### 1. Install Python
Pastikan Python 3.9+ sudah terinstall. Cek dengan:
```bash
python3 --version
```
Kalau belum ada, download di https://www.python.org/downloads/

### 2. Download folder ini
Simpan folder `stock-radar-idx` (berisi `app.py`, `requirements.txt`, `README.md`) di komputer kamu.

### 3. (Opsional tapi disarankan) Buat virtual environment
```bash
cd stock-radar-idx
python3 -m venv venv

# Aktifkan:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Jalankan aplikasi
```bash
streamlit run app.py
```

Browser akan otomatis terbuka ke `http://localhost:8501`. Kalau tidak otomatis, buka manual link tersebut.

## Cara Pakai

- **Sidebar kiri**: edit watchlist kamu (kode saham dipisah koma, tanpa `.JK` — otomatis ditambahkan).
- **Tab "Analisa Saham"**: pilih/ketik satu kode saham untuk lihat chart teknikal lengkap.
- **Tab "Radar Harian"**: klik "Scan Watchlist Sekarang" untuk cari sinyal breakout/bounce/volume spike di semua saham di watchlist.
- **Tab "Berita"**: baca berita IHSG & global terbaru, klik judul untuk buka artikel lengkap.

## Catatan Penting

- Data harga saham diambil dari **Yahoo Finance** via library `yfinance` — biasanya delay 15–20 menit dari harga real-time bursa, cukup untuk analisa swing/harian tapi **jangan dipakai untuk keputusan scalping detik-per-detik**.
- Untuk saham yang baru IPO atau kurang likuid, data historisnya mungkin terbatas.
- Tools ini murni untuk **edukasi & bantu riset pribadi**, bukan rekomendasi jual/beli. Tetap lakukan riset sendiri (DYOR) dan pertimbangkan profil risiko kamu.
- Kalau muncul error "Data tidak ditemukan", cek lagi penulisan kode sahamnya (harus sesuai kode resmi di BEI, contoh: BBCA, TLKM, GOTO).
- Kalau koneksi internet lambat, proses scan watchlist di tab Radar bisa makan waktu beberapa detik per saham — ini normal karena mengambil data satu per satu dari Yahoo Finance.

## Kustomisasi Lanjutan (opsional)

- Ubah `DEFAULT_WATCHLIST` di `app.py` untuk mengganti daftar saham default.
- Ubah threshold sinyal di fungsi `evaluate_signals()` — misalnya ambang volume spike (default 2x) atau breakout (default 1.5x volume + tembus high 20 hari).
- Ubah cache TTL (`ttl=300` untuk harga, `ttl=600` untuk berita) kalau ingin data lebih sering/lebih jarang di-refresh.

Selamat trading & investing yang cerdas! 🚀
