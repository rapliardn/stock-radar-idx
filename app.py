# -*- coding: utf-8 -*-
"""
IDX Stock Radar & Technical Analyzer
=====================================
Tools analisa saham pribadi untuk Bursa Efek Indonesia (IDX).
Fitur:
- Analisa teknikal per saham: EMA, RSI, Support/Resistance, chart candlestick interaktif
- Radar Saham Harian: scan watchlist untuk sinyal Breakout, Bounce/Rebound, dan Volume Spike
- Berita IHSG & Market Global (via Google News RSS)

Cara pakai: lihat README.md
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import feedparser
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from urllib.parse import quote_plus
import time

# ----------------------------------------------------------------------------
# KONFIGURASI HALAMAN & STYLE
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="IDX Stock Radar",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .stApp {
        background: radial-gradient(1200px 600px at 10% -10%, #16213a 0%, #0b0f1a 45%, #05070d 100%);
        color: #e6e8ef;
    }
    section[data-testid="stSidebar"] {
        background: #0b0f1a;
        border-right: 1px solid #1f2740;
    }
    h1, h2, h3, h4 {
        font-family: 'Segoe UI', sans-serif;
        letter-spacing: 0.3px;
    }
    .radar-card {
        background: linear-gradient(145deg, #121a2e, #0d1322);
        border: 1px solid #22304f;
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 10px;
    }
    .metric-box {
        background: linear-gradient(145deg, #121a2e, #0d1322);
        border: 1px solid #22304f;
        border-radius: 14px;
        padding: 14px 18px;
        text-align: center;
    }
    .badge-buy {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(74, 222, 128, 0.4);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-warn {
        background: rgba(250, 204, 21, 0.12);
        color: #facc15;
        border: 1px solid rgba(250, 204, 21, 0.4);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-sell {
        background: rgba(248, 113, 113, 0.12);
        color: #f87171;
        border: 1px solid rgba(248, 113, 113, 0.4);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .news-item {
        border-bottom: 1px solid #1f2740;
        padding: 10px 0;
    }
    .news-item a {
        color: #93c5fd;
        text-decoration: none;
        font-weight: 600;
    }
    .news-source {
        color: #7d8aa8;
        font-size: 12px;
    }
    footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DEFAULT_WATCHLIST = [
    "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ICBP",
    "ANTM", "ADRO", "PGAS", "INDF", "KLBF", "SMGR", "PTBA", "MDKA",
    "BRPT", "GOTO", "BUKA", "ARTO", "EMTK", "MEDC", "INCO", "TOWR",
    "EXCL", "CPIN", "AMRT", "ITMG", "HRUM", "TPIA",
]

# ----------------------------------------------------------------------------
# HELPER: DATA & INDIKATOR
# ----------------------------------------------------------------------------

def to_yf_ticker(kode: str) -> str:
    kode = kode.strip().upper()
    if not kode:
        return kode
    if "." in kode:
        return kode
    return f"{kode}.JK"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_history(kode: str, period: str = "9mo", interval: str = "1d") -> pd.DataFrame:
    ticker = to_yf_ticker(kode)
    df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.dropna(how="all")
    df.index = pd.to_datetime(df.index)
    return df


def compute_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)
    return rsi


def compute_pivot_points(df: pd.DataFrame):
    last = df.iloc[-1]
    p = (last["High"] + last["Low"] + last["Close"]) / 3
    r1 = 2 * p - last["Low"]
    s1 = 2 * p - last["High"]
    r2 = p + (last["High"] - last["Low"])
    s2 = p - (last["High"] - last["Low"])
    return {"pivot": p, "r1": r1, "r2": r2, "s1": s1, "s2": s2}


def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["EMA9"] = compute_ema(df["Close"], 9)
    df["EMA21"] = compute_ema(df["Close"], 21)
    df["EMA50"] = compute_ema(df["Close"], 50)
    df["RSI14"] = compute_rsi(df["Close"], 14)
    df["VolAvg20"] = df["Volume"].rolling(20).mean()
    df["High20"] = df["High"].rolling(20).max().shift(1)
    df["Low20"] = df["Low"].rolling(20).min().shift(1)
    return df


def evaluate_signals(df: pd.DataFrame) -> dict:
    """Cek sinyal radar sederhana: breakout, bounce, volume spike."""
    if len(df) < 25:
        return {}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    vol_ratio = last["Volume"] / last["VolAvg20"] if last["VolAvg20"] and last["VolAvg20"] > 0 else 0
    price_chg_pct = (last["Close"] - prev["Close"]) / prev["Close"] * 100 if prev["Close"] else 0

    signals = []

    # Breakout: tembus resistance 20 hari dengan volume tinggi
    if pd.notna(last["High20"]) and last["Close"] > last["High20"] and vol_ratio >= 1.5:
        signals.append("Breakout")

    # Bounce/Rebound: dekat support 20 hari / EMA21, RSI keluar dari oversold, harga naik
    near_support = pd.notna(last["Low20"]) and last["Close"] <= last["Low20"] * 1.03
    near_ema21 = abs(last["Close"] - last["EMA21"]) / last["Close"] <= 0.02 if last["EMA21"] else False
    rsi_turning_up = last["RSI14"] > prev["RSI14"] and prev["RSI14"] < 40
    if (near_support or near_ema21) and rsi_turning_up and last["Close"] > prev["Close"]:
        signals.append("Bounce")

    # Volume Spike murni
    if vol_ratio >= 2:
        signals.append("Volume Spike")

    if not signals:
        return {}

    return {
        "harga": last["Close"],
        "perubahan_%": round(price_chg_pct, 2),
        "rsi": round(last["RSI14"], 1),
        "vol_ratio": round(vol_ratio, 2),
        "sinyal": signals,
    }


def trend_label(last_row) -> str:
    if last_row["EMA9"] > last_row["EMA21"] > last_row["EMA50"]:
        return "Uptrend Kuat"
    if last_row["EMA9"] > last_row["EMA21"]:
        return "Uptrend Jangka Pendek"
    if last_row["EMA9"] < last_row["EMA21"] < last_row["EMA50"]:
        return "Downtrend Kuat"
    if last_row["EMA9"] < last_row["EMA21"]:
        return "Downtrend Jangka Pendek"
    return "Sideways"


def rsi_label(rsi_val: float) -> str:
    if rsi_val >= 70:
        return "Overbought"
    if rsi_val <= 30:
        return "Oversold"
    return "Netral"


# ----------------------------------------------------------------------------
# HELPER: BERITA (Google News RSS)
# ----------------------------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def fetch_news(query: str, lang: str = "id-ID", country: str = "ID", limit: int = 10):
    ceid = f"{country}:{lang.split('-')[0]}"
    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl={country}&ceid={ceid}"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        items.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "source": entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else "",
        })
    return items


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
st.sidebar.markdown("## 📈 IDX Stock Radar")
st.sidebar.caption("Tools analisa saham pribadi — data via Yahoo Finance (delay ~15-20 menit)")

watchlist_input = st.sidebar.text_area(
    "Watchlist (pisahkan dengan koma)",
    value=", ".join(DEFAULT_WATCHLIST),
    height=110,
)
watchlist = [x.strip().upper() for x in watchlist_input.split(",") if x.strip()]

period_option = st.sidebar.selectbox(
    "Rentang data historis",
    options=["3mo", "6mo", "9mo", "1y", "2y"],
    index=2,
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ Disclaimer: tools ini untuk edukasi & bantu riset pribadi, "
    "bukan rekomendasi jual/beli. Selalu DYOR (Do Your Own Research)."
)

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
st.markdown("# 📈 IDX Stock Radar & Technical Analyzer")
st.caption(f"Update terakhir: {datetime.now().strftime('%A, %d %B %Y — %H:%M')} WIB")

tab1, tab2, tab3 = st.tabs(["📊 Analisa Saham", "🎯 Radar Harian", "📰 Berita IHSG & Global"])

# ----------------------------------------------------------------------------
# TAB 1 — ANALISA SAHAM PER TICKER
# ----------------------------------------------------------------------------
with tab1:
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        kode_saham = st.selectbox(
            "Pilih / ketik kode saham (tanpa .JK)",
            options=sorted(set(watchlist)),
            index=0,
        )
    manual_kode = st.text_input("Atau cari kode lain langsung di sini (mis. BREN, AADI, dst.)", value="")
    kode_final = manual_kode.strip().upper() if manual_kode.strip() else kode_saham

    with st.spinner(f"Mengambil data {kode_final}..."):
        df_raw = fetch_history(kode_final, period=period_option)

    if df_raw.empty:
        st.error(f"Data untuk **{kode_final}** tidak ditemukan. Cek kembali kode sahamnya.")
    else:
        df = enrich_indicators(df_raw)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        chg = last["Close"] - prev["Close"]
        chg_pct = chg / prev["Close"] * 100

        pivots = compute_pivot_points(df_raw)
        trend = trend_label(last)
        rsi_stat = rsi_label(last["RSI14"])

        # Metric cards
        m1, m2, m3, m4, m5 = st.columns(5)
        chg_color = "#4ade80" if chg >= 0 else "#f87171"
        chg_sign = "+" if chg >= 0 else ""
        with m1:
            st.markdown(
                f"<div class='metric-box'><div style='color:#7d8aa8;font-size:12px'>Harga Terakhir</div>"
                f"<div style='font-size:22px;font-weight:700'>Rp {last['Close']:,.0f}</div>"
                f"<div style='color:{chg_color};font-size:13px'>"
                f"{chg_sign}{chg:,.0f} ({chg_pct:+.2f}%)</div></div>",
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"<div class='metric-box'><div style='color:#7d8aa8;font-size:12px'>RSI (14)</div>"
                f"<div style='font-size:22px;font-weight:700'>{last['RSI14']:.1f}</div>"
                f"<div style='font-size:13px'>{rsi_stat}</div></div>",
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f"<div class='metric-box'><div style='color:#7d8aa8;font-size:12px'>Trend (EMA)</div>"
                f"<div style='font-size:16px;font-weight:700;margin-top:6px'>{trend}</div></div>",
                unsafe_allow_html=True,
            )
        with m4:
            vol_ratio = last["Volume"] / last["VolAvg20"] if last["VolAvg20"] else 0
            st.markdown(
                f"<div class='metric-box'><div style='color:#7d8aa8;font-size:12px'>Volume vs Avg20</div>"
                f"<div style='font-size:22px;font-weight:700'>{vol_ratio:.2f}x</div></div>",
                unsafe_allow_html=True,
            )
        with m5:
            st.markdown(
                f"<div class='metric-box'><div style='color:#7d8aa8;font-size:12px'>Support / Resistance (Pivot)</div>"
                f"<div style='font-size:14px;font-weight:700;margin-top:6px'>"
                f"S1: {pivots['s1']:,.0f} | R1: {pivots['r1']:,.0f}</div></div>",
                unsafe_allow_html=True,
            )

        st.write("")

        # Candlestick chart + EMA + S/R
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.2, 0.25], vertical_spacing=0.03,
            subplot_titles=("Harga & EMA", "Volume", "RSI (14)"),
        )

        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name="Harga", increasing_line_color="#4ade80", decreasing_line_color="#f87171",
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], name="EMA 9",
                                  line=dict(color="#38bdf8", width=1.3)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA21"], name="EMA 21",
                                  line=dict(color="#facc15", width=1.3)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50",
                                  line=dict(color="#c084fc", width=1.3)), row=1, col=1)

        # Support / resistance (rolling 20 & pivot)
        fig.add_hline(y=pivots["r1"], line_dash="dot", line_color="#f87171",
                      annotation_text="R1", row=1, col=1)
        fig.add_hline(y=pivots["s1"], line_dash="dot", line_color="#4ade80",
                      annotation_text="S1", row=1, col=1)
        fig.add_hline(y=df["High20"].iloc[-1], line_dash="dash", line_color="#fb923c",
                      annotation_text="High 20D", row=1, col=1)
        fig.add_hline(y=df["Low20"].iloc[-1], line_dash="dash", line_color="#22d3ee",
                      annotation_text="Low 20D", row=1, col=1)

        vol_colors = np.where(df["Close"] >= df["Open"], "#4ade80", "#f87171")
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                              marker_color=vol_colors), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["VolAvg20"], name="Vol Avg 20",
                                  line=dict(color="#93c5fd", width=1)), row=2, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI 14",
                                  line=dict(color="#f472b6", width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#f87171", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#4ade80", row=3, col=1)

        fig.update_layout(
            height=780, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Interpretasi otomatis
        st.markdown("#### 🧠 Ringkasan Analisa Otomatis")
        interp = []
        interp.append(f"- **Trend EMA**: {trend} (EMA9 {last['EMA9']:,.0f} / EMA21 {last['EMA21']:,.0f} / EMA50 {last['EMA50']:,.0f}).")
        interp.append(f"- **RSI 14**: {last['RSI14']:.1f} → kondisi **{rsi_stat}**.")
        interp.append(f"- **Volume**: {vol_ratio:.2f}x rata-rata 20 hari" + (" (di atas rata-rata, ada minat pasar lebih tinggi)." if vol_ratio > 1 else " (di bawah rata-rata, minat pasar relatif sepi)."))
        interp.append(f"- **Support terdekat**: Rp {pivots['s1']:,.0f} (pivot) / Rp {df['Low20'].iloc[-1]:,.0f} (low 20 hari).")
        interp.append(f"- **Resistance terdekat**: Rp {pivots['r1']:,.0f} (pivot) / Rp {df['High20'].iloc[-1]:,.0f} (high 20 hari).")
        st.markdown("\n".join(interp))
        st.caption("Catatan: ringkasan ini murni hasil perhitungan indikator teknikal, bukan saran investasi.")

# ----------------------------------------------------------------------------
# TAB 2 — RADAR SAHAM HARIAN
# ----------------------------------------------------------------------------
with tab2:
    st.markdown("### 🎯 Radar Saham Harian")
    st.caption("Scan watchlist untuk sinyal **Breakout**, **Bounce/Rebound**, dan **Volume Spike**.")

    scan_btn = st.button("🔍 Scan Watchlist Sekarang", type="primary")

    if scan_btn:
        results = []
        progress = st.progress(0, text="Memulai scan...")
        for i, kode in enumerate(watchlist):
            progress.progress((i + 1) / len(watchlist), text=f"Menganalisa {kode}...")
            try:
                raw = fetch_history(kode, period="4mo")
                if raw.empty:
                    continue
                enriched = enrich_indicators(raw)
                sig = evaluate_signals(enriched)
                if sig:
                    sig["kode"] = kode
                    results.append(sig)
            except Exception:
                continue
        progress.empty()

        if not results:
            st.info("Tidak ada sinyal Breakout / Bounce / Volume Spike terdeteksi di watchlist saat ini.")
        else:
            df_res = pd.DataFrame(results)
            df_res = df_res[["kode", "harga", "perubahan_%", "rsi", "vol_ratio", "sinyal"]]

            for sinyal_type, emoji, desc in [
                ("Breakout", "🚀", "Harga menembus resistance 20 hari dengan volume tinggi"),
                ("Bounce", "🔄", "Rebound dari area support / EMA21 dengan RSI membaik"),
                ("Volume Spike", "🔊", "Lonjakan volume signifikan (≥2x rata-rata 20 hari)"),
            ]:
                subset = df_res[df_res["sinyal"].apply(lambda s: sinyal_type in s)]
                if subset.empty:
                    continue
                st.markdown(f"#### {emoji} {sinyal_type}")
                st.caption(desc)
                for _, row in subset.iterrows():
                    badge_class = "badge-buy" if row["perubahan_%"] >= 0 else "badge-sell"
                    st.markdown(
                        f"<div class='radar-card'>"
                        f"<b style='font-size:16px'>{row['kode']}</b> "
                        f"<span class='{badge_class}'>{row['perubahan_%']:+.2f}%</span><br>"
                        f"Harga: Rp {row['harga']:,.0f} &nbsp;|&nbsp; RSI: {row['rsi']} "
                        f"&nbsp;|&nbsp; Volume: {row['vol_ratio']:.2f}x avg20"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.info("Klik tombol di atas untuk mulai scan watchlist kamu.")

# ----------------------------------------------------------------------------
# TAB 3 — BERITA IHSG & GLOBAL
# ----------------------------------------------------------------------------
with tab3:
    col_ihsg, col_global = st.columns(2)

    with col_ihsg:
        st.markdown("### 🇮🇩 Berita IHSG & Saham Indonesia")
        with st.spinner("Memuat berita..."):
            news_ihsg = fetch_news("IHSG OR bursa saham Indonesia", lang="id-ID", country="ID")
        if not news_ihsg:
            st.warning("Berita tidak dapat dimuat. Cek koneksi internet.")
        for n in news_ihsg:
            st.markdown(
                f"<div class='news-item'><a href='{n['link']}' target='_blank'>{n['title']}</a>"
                f"<div class='news-source'>{n['source']} • {n['published']}</div></div>",
                unsafe_allow_html=True,
            )

    with col_global:
        st.markdown("### 🌍 Berita Market Global")
        with st.spinner("Memuat berita..."):
            news_global = fetch_news("wall street OR global stock market", lang="en-US", country="US")
        if not news_global:
            st.warning("Berita tidak dapat dimuat. Cek koneksi internet.")
        for n in news_global:
            st.markdown(
                f"<div class='news-item'><a href='{n['link']}' target='_blank'>{n['title']}</a>"
                f"<div class='news-source'>{n['source']} • {n['published']}</div></div>",
                unsafe_allow_html=True,
            )

st.markdown("---")
st.caption("Dibuat untuk penggunaan pribadi. Data harga: Yahoo Finance. Berita: Google News RSS. Bukan nasihat keuangan.")
