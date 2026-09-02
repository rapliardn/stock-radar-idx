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
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import yfinance as yf
import feedparser
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-base: #0A0E17;
        --bg-surface: #10151F;
        --border: #1C2333;
        --teal: #2DD4BF;
        --amber: #F5A623;
        --violet: #A78BFA;
        --up: #22C55E;
        --down: #EF4444;
        --text-primary: #E8EBF2;
        --text-muted: #7C8698;
    }

    .stApp {
        background:
            radial-gradient(900px 480px at 8% -8%, rgba(45, 212, 191, 0.06) 0%, transparent 60%),
            var(--bg-base);
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
    }
    section[data-testid="stSidebar"] {
        background: var(--bg-surface);
        border-right: 1px solid var(--border);
    }
    h1, h2, h3, h4 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    [data-testid="stMetricValue"], .mono-num {
        font-family: 'JetBrains Mono', monospace;
    }

    /* ---- Header ---- */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 16px;
        margin-bottom: 6px;
        border-bottom: 1px solid var(--border);
    }
    .app-header-left { display: flex; align-items: center; gap: 14px; }
    .logo-mark {
        font-family: 'JetBrains Mono', monospace;
        font-size: 18px;
        color: var(--teal);
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 8px 11px;
        line-height: 1;
    }
    .app-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 26px;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1.1;
    }
    .app-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        color: var(--text-muted);
        margin-top: 2px;
    }
    .live-chip {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: var(--teal);
        border: 1px solid rgba(45, 212, 191, 0.35);
        background: rgba(45, 212, 191, 0.06);
        border-radius: 20px;
        padding: 6px 14px;
    }

    /* ---- Metric strip ---- */
    .metric-box {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 14px 16px;
    }
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 21px;
        font-weight: 600;
        color: var(--text-primary);
    }
    .metric-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        margin-top: 2px;
    }

    /* ---- Radar signal cards: color-coded left border by signal type ---- */
    .radar-card {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-left: 3px solid var(--teal);
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 4px;
    }
    .radar-card.breakout { border-left-color: var(--teal); }
    .radar-card.bounce { border-left-color: var(--amber); }
    .radar-card.volspike { border-left-color: var(--violet); }
    .radar-ticker {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 16px;
        font-weight: 700;
        color: var(--text-primary);
    }
    .radar-detail {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12.5px;
        color: var(--text-muted);
        margin-top: 4px;
    }

    .badge-buy {
        background: rgba(34, 197, 94, 0.12);
        color: var(--up);
        border: 1px solid rgba(34, 197, 94, 0.35);
        padding: 2px 10px;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-sell {
        background: rgba(239, 68, 68, 0.12);
        color: var(--down);
        border: 1px solid rgba(239, 68, 68, 0.35);
        padding: 2px 10px;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-warn {
        background: rgba(245, 166, 35, 0.12);
        color: var(--amber);
        border: 1px solid rgba(245, 166, 35, 0.35);
        padding: 2px 10px;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 600;
    }

    /* ---- News list ---- */
    .news-item {
        border-bottom: 1px solid var(--border);
        padding: 11px 0;
    }
    .news-item a {
        color: var(--text-primary);
        text-decoration: none;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 14.5px;
    }
    .news-item a:hover { color: var(--teal); }
    .news-source {
        font-family: 'JetBrains Mono', monospace;
        color: var(--text-muted);
        font-size: 11.5px;
        margin-top: 3px;
    }

    /* ---- Ticker badge (colored avatar) ---- */
    .ticker-badge {
        width: 26px; height: 26px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 12px;
        flex-shrink: 0;
    }

    /* ---- Trading plan box ---- */
    .plan-box {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 12px 14px;
    }
    .plan-label {
        font-family: 'Inter', sans-serif;
        font-size: 11.5px;
        color: var(--text-muted);
        margin-bottom: 3px;
    }
    .plan-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
    }
    .progress-track {
        background: var(--border);
        border-radius: 20px;
        height: 8px;
        width: 100%;
        overflow: hidden;
        margin-top: 6px;
    }
    .progress-fill {
        background: linear-gradient(90deg, var(--teal), var(--amber));
        height: 100%;
        border-radius: 20px;
    }

    /* ---- Tabs & buttons ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 500;
        color: var(--text-muted);
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: var(--teal) !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: var(--teal) !important;
    }
    div.stButton > button[kind="primary"] {
        background: var(--teal);
        color: #0A0E17;
        border: none;
        font-weight: 600;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #26B8A5;
        color: #0A0E17;
    }

    footer {visibility: hidden;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DEFAULT_WATCHLIST = [
    "AADI", "AALI", "ABBA", "ABDA", "ABMM", "ACES", "ACRO", "ACST", "ADCP", "ADES",
    "ADHI", "ADMF", "ADMG", "ADMR", "ADRO", "AEGS", "AGAR", "AGII", "AGRO", "AGRS",
    "AHAP", "AIMS", "AISA", "AKKU", "AKPI", "AKRA", "AKSI", "ALDO", "ALII", "ALKA",
    "ALMI", "ALTO", "AMAG", "AMAN", "AMAR", "AMFG", "AMIN", "AMMN", "AMMS", "AMOR",
    "AMRT", "ANDI", "ANJT", "ANTM", "APEX", "APIC", "APII", "APLI", "APLN", "ARCI",
    "AREA", "ARGO", "ARII", "ARKA", "ARKO", "ARMY", "ARNA", "ARTA", "ARTI", "ARTO",
    "ASBI", "ASDM", "ASGR", "ASHA", "ASII", "ASJT", "ASLC", "ASLI", "ASMI", "ASPI",
    "ASRI", "ASRM", "ASSA", "ATAP", "ATIC", "ATLA", "AUTO", "AVIA", "AWAN", "AXIO",
    "AYAM", "AYLS", "BABP", "BABY", "BACA", "BAIK", "BAJA", "BALI", "BANK", "BAPA",
    "BAPI", "BATA", "BATR", "BAUT", "BAYU", "BBCA", "BBHI", "BBKP", "BBLD", "BBMD",
    "BBNI", "BBRI", "BBRM", "BBSI", "BBSS", "BBTN", "BBYB", "BCAP", "BCIC", "BCIP",
    "BDKR", "BDMN", "BEBS", "BEEF", "BEER", "BEKS", "BELI", "BELL", "BESS", "BEST",
    "BFIN", "BGTG", "BHAT", "BHIT", "BIKA", "BIKE", "BIMA", "BINA", "BINO", "BIPI",
    "BIPP", "BIRD", "BISI", "BJBR", "BJTM", "BKDP", "BKSL", "BKSW", "BLES", "BLTA",
    "BLTZ", "BLUE", "BMAS", "BMBL", "BMHS", "BMRI", "BMSR", "BMTR", "BNBA", "BNBR",
    "BNGA", "BNII", "BNLI", "BOAT", "BOBA", "BOGA", "BOLA", "BOLT", "BOSS", "BPFI",
    "BPII", "BPTR", "BRAM", "BREN", "BRIS", "BRMS", "BRNA", "BRPT", "BRRC", "BSBK",
    "BSDE", "BSIM", "BSML", "BSSR", "BSWD", "BTEK", "BTEL", "BTON", "BTPN", "BTPS",
    "BUAH", "BUDI", "BUKA", "BUKK", "BULL", "BUMI", "BUVA", "BVIC", "BWPT", "BYAN",
    "CAKK", "CAMP", "CANI", "CARE", "CARS", "CASA", "CASH", "CASS", "CBDK", "CBMF",
    "CBPE", "CBRE", "CBUT", "CCSI", "CEKA", "CENT", "CFIN", "CGAS", "CHEM", "CHIP",
    "CINT", "CITA", "CITY", "CLAY", "CLEO", "CLPI", "CMNP", "CMNT", "CMPP", "CMRY",
    "CNKO", "CNMA", "CNTX", "COAL", "COCO", "COWL", "CPIN", "CPRI", "CPRO", "CRAB",
    "CRSN", "CSAP", "CSIS", "CSMI", "CSRA", "CTBN", "CTRA", "CTTH", "CUAN", "CYBR",
    "DAAZ", "DADA", "DART", "DATA", "DAYA", "DCII", "DEAL", "DEFI", "DEPO", "DEWA",
    "DEWI", "DFAM", "DGIK", "DGNS", "DGWG", "DIGI", "DILD", "DIVA", "DKFT", "DLTA",
    "DMAS", "DMMX", "DMND", "DNAR", "DNET", "DOID", "DOOH", "DOSS", "DPNS", "DPUM",
    "DRMA", "DSFI", "DSNG", "DSSA", "DUCK", "DUTI", "DVLA", "DWGL", "DYAN", "EAST",
    "ECII", "EDGE", "EKAD", "ELIT", "ELPI", "ELSA", "ELTY", "EMDE", "EMTK", "ENAK",
    "ENRG", "ENVY", "ENZO", "EPAC", "EPMT", "ERAA", "ERAL", "ERTX", "ESIP", "ESSA",
    "ESTA", "ESTI", "ETWA", "EURO", "EXCL", "FAPA", "FAST", "FASW", "FILM", "FIMP",
    "FIRE", "FISH", "FITT", "FLMC", "FMII", "FOLK", "FOOD", "FORU", "FORZ", "FPNI",
    "FREN", "FUJI", "FUTR", "FWCT", "GAMA", "GDST", "GDYR", "GEMA", "GEMS", "GGRM",
    "GGRP", "GHON", "GIAA", "GJTL", "GLOB", "GLVA", "GMFI", "GMTD", "GOLD", "GOLF",
    "GOLL", "GOOD", "GOTO", "GPRA", "GPSO", "GRIA", "GRPH", "GRPM", "GSMF", "GTBO",
    "GTRA", "GTSI", "GULA", "GUNA", "GWSA", "GZCO", "HADE", "HAIS", "HAJJ", "HALO",
    "HATM", "HBAT", "HDFA", "HDIT", "HDTX", "HEAL", "HELI", "HERO", "HEXA", "HGII",
    "HILL", "HITS", "HKMU", "HMSP", "HOKI", "HOME", "HOMI", "HOPE", "HOTL", "HRME",
    "HRTA", "HRUM", "HUMI", "HYGN", "IATA", "IBFN", "IBOS", "IBST", "ICBP", "ICON",
    "IDEA", "IDPR", "IFII", "IFSH", "IGAR", "IIKP", "IKAI", "IKAN", "IKBI", "IKPM",
    "IMAS", "IMJS", "IMPC", "INAF", "INAI", "INCF", "INCI", "INCO", "INDF", "INDO",
    "INDR", "INDS", "INDX", "INDY", "INET", "INKP", "INOV", "INPC", "INPP", "INPS",
    "INRU", "INTA", "INTD", "INTP", "IOTF", "IPAC", "IPCC", "IPCM", "IPOL", "IPPE",
    "IPTV", "IRRA", "IRSX", "ISAP", "ISAT", "ISEA", "ISSP", "ITIC", "ITMA", "ITMG",
    "JARR", "JAST", "JATI", "JAWA", "JAYA", "JECC", "JGLE", "JIHD", "JKON", "JKSW",
    "JMAS", "JPFA", "JRPT", "JSKY", "JSMR", "JSPT", "JTPE", "KAEF", "KARW", "KAYU",
    "KBAG", "KBLI", "KBLM", "KBLV", "KBRI", "KDSI", "KDTN", "KEEN", "KEJU", "KETR",
    "KIAS", "KICI", "KIJA", "KING", "KINO", "KIOS", "KJEN", "KKES", "KKGI", "KLAS",
    "KLBF", "KLIN", "KMDS", "KMTR", "KOBX", "KOCI", "KOIN", "KOKA", "KONI", "KOPI",
    "KOTA", "KPAL", "KPAS", "KPIG", "KRAH", "KRAS", "KREN", "KRYA", "KSIX", "KUAS",
    "LABA", "LABS", "LAJU", "LAND", "LAPD", "LCGP", "LCKM", "LEAD", "LFLO", "LIFE",
    "LINK", "LION", "LIVE", "LMAS", "LMAX", "LMPI", "LMSH", "LOPI", "LPCK", "LPGI",
    "LPIN", "LPKR", "LPLI", "LPPF", "LPPS", "LRNA", "LSIP", "LTLS", "LUCK", "LUCY",
    "MABA", "MAGP", "MAHA", "MAIN", "MAMI", "MANG", "MAPA", "MAPB", "MAPI", "MARI",
    "MARK", "MASA", "MASB", "MAXI", "MAYA", "MBAP", "MBMA", "MBSS", "MBTO", "MCAS",
    "MCOL", "MCOR", "MDIA", "MDIY", "MDKA", "MDKI", "MDLN", "MDRN", "MEDC", "MEDS",
    "MEGA", "MEJA", "MENN", "MERK", "META", "MFIN", "MFMI", "MGLV", "MGNA", "MGRO",
    "MHKI", "MICE", "MIDI", "MIKA", "MINA", "MIRA", "MITI", "MKAP", "MKNT", "MKPI",
    "MKTR", "MLBI", "MLIA", "MLPL", "MLPT", "MMIX", "MMLP", "MNCN", "MOLI", "MORA",
    "MPIX", "MPMX", "MPOW", "MPPA", "MPRO", "MPXL", "MRAT", "MREI", "MSIE", "MSIN",
    "MSJA", "MSKY", "MSTI", "MTDL", "MTEL", "MTFN", "MTLA", "MTMH", "MTPS", "MTRA",
    "MTSM", "MTWI", "MUTU", "MYOH", "MYOR", "MYRX", "MYTX", "NAIK", "NANO", "NASA",
    "NASI", "NATO", "NAYZ", "NCKL", "NELY", "NEST", "NETV", "NFCX", "NICE", "NICK",
    "NICL", "NIKL", "NINE", "NIPS", "NIRO", "NISP", "NOBU", "NPGF", "NRCA", "NSSS",
    "NTBK", "NUSA", "NZIA", "OASA", "OBAT", "OBMD", "OCAP", "OILS", "OKAS", "OLIV",
    "OMED", "OMRE", "OPMS", "PACK", "PADA", "PADI", "PALM", "PAMG", "PANI", "PANR",
    "PANS", "PART", "PBID", "PBRX", "PBSA", "PCAR", "PDES", "PDPP", "PEGE", "PEHA",
    "PEVE", "PGAS", "PGEO", "PGJO", "PGLI", "PGUN", "PICO", "PIPA", "PJAA", "PKPK",
    "PLAN", "PLAS", "PLIN", "PMJS", "PMMP", "PNBN", "PNBS", "PNGO", "PNIN", "PNLF",
    "PNSE", "POLA", "POLI", "POLL", "POLU", "POLY", "POOL", "PORT", "POSA", "POWR",
    "PPGL", "PPRE", "PPRI", "PPRO", "PRAS", "PRAY", "PRDA", "PRIM", "PSAB", "PSDN",
    "PSGO", "PSKT", "PSSI", "PTBA", "PTDU", "PTIS", "PTMP", "PTMR", "PTPP", "PTPS",
    "PTPW", "PTRO", "PTSN", "PTSP", "PUDP", "PURA", "PURE", "PURI", "PWON", "PYFA",
    "PZZA", "RAAM", "RAFI", "RAJA", "RALS", "RANC", "RATU", "RBMS", "RCCC", "RDTX",
    "REAL", "RELF", "RELI", "RGAS", "RICY", "RIGS", "RIMO", "RISE", "RMKE", "RMKO",
    "ROCK", "RODA", "RONY", "ROTI", "RSCH", "RSGK", "RUIS", "RUNS", "SAFE", "SAGE",
    "SAME", "SAMF", "SAPX", "SATU", "SBAT", "SBMA", "SCCO", "SCMA", "SCNP", "SCPI",
    "SDMU", "SDPC", "SDRA", "SEMA", "SFAN", "SGER", "SGRO", "SHID", "SHIP", "SICO",
    "SIDO", "SILO", "SIMA", "SIMP", "SINI", "SIPD", "SKBM", "SKLT", "SKRN", "SKYB",
    "SLIS", "SMAR", "SMBR", "SMCB", "SMDM", "SMDR", "SMGA", "SMGR", "SMIL", "SMKL",
    "SMKM", "SMLE", "SMMA", "SMMT", "SMRA", "SMRU", "SMSM", "SNLK", "SOCI", "SOFA",
    "SOHO", "SOLA", "SONA", "SOSS", "SOTS", "SOUL", "SPMA", "SPRE", "SPTO", "SQMI",
    "SRAJ", "SRIL", "SRSN", "SRTG", "SSIA", "SSMS", "SSTM", "STAA", "STAR", "STRK",
    "STTP", "SUGI", "SULI", "SUNI", "SUPR", "SURE", "SURI", "SWAT", "SWID", "TALF",
    "TAMA", "TAMU", "TAPG", "TARA", "TAXI", "TAYS", "TBIG", "TBLA", "TBMS", "TCID",
    "TCPI", "TDPM", "TEBE", "TECH", "TELE", "TFAS", "TFCO", "TGKA", "TGRA", "TGUK",
    "TIFA", "TINS", "TIRA", "TIRT", "TKIM", "TLDN", "TLKM", "TMAS", "TMPO", "TNCA",
    "TOBA", "TOOL", "TOPS", "TOSK", "TOTL", "TOTO", "TOWR", "TOYS", "TPIA", "TPMA",
    "TRAM", "TRGU", "TRIL", "TRIM", "TRIN", "TRIO", "TRIS", "TRJA", "TRON", "TRST",
    "TRUE", "TRUK", "TRUS", "TSPC", "TUGU", "TYRE", "UANG", "UCID", "UDNG", "UFOE",
    "ULTJ", "UNIC", "UNIQ", "UNIT", "UNSP", "UNTD", "UNTR", "UNVR", "URBN", "UVCR",
    "VAST", "VERN", "VICI", "VICO", "VINS", "VISI", "VIVA", "VKTR", "VOKS", "VRNA",
    "VTNY", "WAPO", "WEGE", "WEHA", "WGSH", "WICO", "WIDI", "WIFI", "WIIM", "WIKA",
    "WINE", "WINR", "WINS", "WIRG", "WMPP", "WMUU", "WOMF", "WOOD", "WOWS", "WSBP",
    "WSKT", "WTON", "YELO", "YOII", "YPAS", "YULE", "ZATA", "ZBRA", "ZINC", "ZONE",
    "ZYRX",
]

SECTOR_GROUPS = {
    "Teknologi": [
        "AREA", "ATIC", "AWAN", "AXIO", "BELI", "BUKA", "CASH", "CHIP", "CYBR", "DCII",
        "DIVA", "DMMX", "EDGE", "ELIT", "EMTK", "ENVY", "GLVA", "GOTO", "HDIT", "IOTF",
        "IRSX", "JATI", "KIOS", "KREN", "LMAS", "LUCK", "MCAS", "MENN", "MLPT", "MPIX",
        "MSTI", "MTDL", "NFCX", "NINE", "PGJO", "PTSN", "RUNS", "SKYB", "TECH", "TFAS",
        "TOSK", "TRON", "UVCR", "WGSH", "WIFI", "WIRG", "ZYRX",
    ],
    "Energi": [
        "ABMM", "ADMR", "ADRO", "AIMS", "AKRA", "ALII", "APEX", "ARII", "ARTI", "ATLA",
        "BBRM", "BESS", "BIPI", "BOSS", "BSML", "BSSR", "BULL", "BUMI", "BYAN", "CANI",
        "CBRE", "CGAS", "CNKO", "COAL", "CUAN", "DEWA", "DOID", "DSSA", "DWGL", "ELSA",
        "ENRG", "FIRE", "GEMS", "GTBO", "GTSI", "HILL", "HITS", "HRUM", "HUMI", "IATA",
        "INDY", "INPS", "ITMA", "ITMG", "JSKY", "KKGI", "KOPI", "LEAD", "MAHA", "MBAP",
        "MBSS", "MCOL", "MEDC", "MKAP", "MTFN", "MYOH", "PGAS", "PKPK", "PSSI", "PTBA",
        "PTIS", "PTRO", "RAJA", "RGAS", "RIGS", "RMKE", "RMKO", "RUIS", "SEMA", "SGER",
        "SHIP", "SICO", "SMMT", "SMRU", "SOCI", "SUGI", "SUNI", "SURE", "TAMU", "TCPI",
        "TEBE", "TOBA", "TPMA", "TRAM", "UNIQ", "WINS", "WOWS",
    ],
    "Consumer Cyclicals": [
        "ABBA", "ACES", "ACRO", "AEGS", "AKKU", "ARGO", "ARTA", "ASLC", "AUTO", "BABY",
        "BAIK", "BATA", "BAUT", "BAYU", "BELL", "BIKE", "BIMA", "BLTZ", "BMBL", "BMTR",
        "BOGA", "BOLA", "BOLT", "BRAM", "BUVA", "CARS", "CBMF", "CINT", "CLAY", "CNMA",
        "CNTX", "CSAP", "CSMI", "DEPO", "DFAM", "DIGI", "DOOH", "DRMA", "DUCK", "EAST",
        "ECII", "ENAK", "ERAA", "ERAL", "ERTX", "ESTA", "ESTI", "FAST", "FILM", "FITT",
        "FORU", "FUTR", "GDYR", "GEMA", "GJTL", "GLOB", "GOLF", "GRPH", "GWSA", "HAJJ",
        "HDTX", "HOME", "HOTL", "HRME", "HRTA", "IDEA", "IIKP", "IMAS", "INDR", "INDS",
        "INOV", "IPTV", "ISAP", "JGLE", "JIHD", "JSPT", "KDTN", "KICI", "KLIN", "KOTA",
        "KPIG", "LFLO", "LIVE", "LMAX", "LMPI", "LPIN", "LPPF", "LUCY", "MABA", "MAMI",
        "MAPA", "MAPB", "MAPI", "MARI", "MASA", "MDIA", "MEJA", "MGLV", "MGNA", "MICE",
        "MINA", "MKNT", "MNCN", "MPMX", "MSIN", "MSKY", "MYTX", "NATO", "NETV", "NIPS",
        "NUSA", "OLIV", "PANR", "PART", "PBRX", "PDES", "PGLI", "PJAA", "PLAN", "PMJS",
        "PNSE", "POLU", "POLY", "PRAS", "PSKT", "PTSP", "PZZA", "RAAM", "RAFI", "RALS",
        "RICY", "SBAT", "SCMA", "SCNP", "SHID", "SLIS", "SMSM", "SNLK", "SOFA", "SONA",
        "SOTS", "SPRE", "SRIL", "SSTM", "SWID", "TELE", "TFCO", "TMPO", "TOOL", "TOYS",
        "TRIO", "TRIS", "TYRE", "UFOE", "UNIT", "UNTD", "VIVA", "VKTR", "WOOD", "YELO",
        "ZATA", "ZONE",
    ],
    "Basic Materials": [
        "ADMG", "AGII", "AKPI", "ALDO", "ALKA", "ALMI", "AMMN", "ANTM", "APLI", "ARCI",
        "AVIA", "AYLS", "BAJA", "BATR", "BEBS", "BLES", "BMSR", "BRMS", "BRNA", "BRPT",
        "BTON", "CHEM", "CITA", "CLPI", "CMNT", "CTBN", "DKFT", "DPNS", "EKAD", "EPAC",
        "ESIP", "ESSA", "ETWA", "FASW", "FPNI", "FWCT", "GDST", "GGRP", "HKMU", "IFII",
        "IFSH", "IGAR", "INAI", "INCF", "INCI", "INCO", "INKP", "INRU", "INTD", "INTP",
        "IPOL", "ISSP", "JKSW", "KAYU", "KBRI", "KDSI", "KKES", "KMTR", "KRAS", "LMSH",
        "LTLS", "MBMA", "MDKA", "MDKI", "MOLI", "NCKL", "NICE", "NICL", "NIKL", "NPGF",
        "OBMD", "OKAS", "OPMS", "PACK", "PBID", "PDPP", "PICO", "PPRI", "PSAB", "PURE",
        "SAMF", "SBMA", "SIMA", "SMBR", "SMCB", "SMGA", "SMGR", "SMKL", "SMLE", "SOLA",
        "SPMA", "SQMI", "SRSN", "SULI", "SWAT", "TALF", "TBMS", "TDPM", "TINS", "TIRT",
        "TKIM", "TPIA", "TRST", "UNIC", "WSBP", "WTON", "YPAS", "ZINC",
    ],
    "Perbankan & Keuangan": [
        "ABDA", "ADMF", "AGRO", "AGRS", "AHAP", "AMAG", "AMAR", "AMOR", "APIC", "ARTO",
        "ASBI", "ASDM", "ASJT", "ASMI", "ASRM", "BABP", "BACA", "BANK", "BBCA", "BBHI",
        "BBKP", "BBLD", "BBMD", "BBNI", "BBRI", "BBSI", "BBTN", "BBYB", "BCAP", "BCIC",
        "BDMN", "BEKS", "BFIN", "BGTG", "BHAT", "BINA", "BJBR", "BJTM", "BKSW", "BMAS",
        "BMRI", "BNBA", "BNGA", "BNII", "BNLI", "BPFI", "BPII", "BRIS", "BSIM", "BSWD",
        "BTPN", "BTPS", "BVIC", "CASA", "CFIN", "DEFI", "DNAR", "DNET", "FUJI", "GSMF",
        "HDFA", "INPC", "JMAS", "LIFE", "LPGI", "LPPS", "MASB", "MAYA", "MCOR", "MEGA",
        "MFIN", "MREI", "MTWI", "NICK", "NISP", "NOBU", "OCAP", "PADI", "PALM", "PANS",
        "PEGE", "PLAS", "PNBN", "PNBS", "PNIN", "PNLF", "POLA", "POOL", "RELI", "SDRA",
        "SFAN", "SMMA", "SRTG", "STAR", "TIFA", "TRIM", "TRUS", "TUGU", "VICO", "VINS",
        "VRNA", "VTNY", "WOMF", "YULE",
    ],
    "Kesehatan": [
        "BMHS", "CARE", "DGNS", "DVLA", "HALO", "HEAL", "IKPM", "INAF", "IRRA", "KAEF",
        "KLBF", "LABS", "MEDS", "MERK", "MIKA", "MMIX", "MTMH", "OMED", "PEHA", "PEVE",
        "PRAY", "PRDA", "PRIM", "PYFA", "RSCH", "RSGK", "SAME", "SCPI", "SIDO", "SILO",
        "SOHO", "SRAJ", "SURI", "TSPC",
    ],
    "Infrastruktur": [
        "ACST", "ADHI", "ARKO", "ASLI", "BALI", "BDKR", "BREN", "BTEL", "BUKK", "CASS",
        "CENT", "CMNP", "DATA", "DGIK", "EXCL", "FIMP", "FREN", "GHON", "GMFI", "GOLD",
        "HADE", "IBST", "IDPR", "INET", "IPCC", "IPCM", "ISAT", "JAST", "JKON", "JSMR",
        "KARW", "KBLV", "KEEN", "KETR", "KOKA", "KRYA", "LCKM", "LINK", "MANG", "META",
        "MORA", "MPOW", "MTEL", "MTPS", "MTRA", "NRCA", "OASA", "PBSA", "PGEO", "PORT",
        "POWR", "PPRE", "PTDU", "PTPP", "PTPW", "RONY", "SMKM", "SSIA", "SUPR", "TAMA",
        "TBIG", "TGRA", "TLKM", "TOPS", "TOTL", "TOWR", "WEGE", "WIKA", "WSKT",
    ],
    "Properti & Real Estate": [
        "ADCP", "AMAN", "APLN", "ARMY", "ASPI", "ASRI", "ATAP", "BAPA", "BAPI", "BBSS",
        "BCIP", "BEST", "BIKA", "BIPP", "BKDP", "BKSL", "BSBK", "BSDE", "CBPE", "CITY",
        "COWL", "CPRI", "CSIS", "CTRA", "DADA", "DART", "DILD", "DMAS", "DUTI", "ELTY",
        "EMDE", "FMII", "FORZ", "GAMA", "GMTD", "GPRA", "GRIA", "HBAT", "HOMI", "INDO",
        "INPP", "IPAC", "JRPT", "KBAG", "KIJA", "KOCI", "LAND", "LCGP", "LPCK", "LPKR",
        "LPLI", "MDLN", "MKPI", "MMLP", "MPRO", "MSIE", "MTLA", "MTSM", "MYRX", "NASA",
        "NIRO", "NZIA", "OMRE", "PAMG", "PANI", "PLIN", "POLI", "POLL", "POSA", "PPRO",
        "PUDP", "PURI", "PWON", "RBMS", "RDTX", "REAL", "RELF", "RIMO", "RISE", "ROCK",
        "RODA", "SAGE", "SATU", "SMDM", "SMRA", "TARA", "TRIN", "TRUE", "UANG", "URBN",
        "VAST", "WINR",
    ],
    "Consumer Non-Cyclicals": [
        "AALI", "ADES", "AGAR", "AISA", "ALTO", "AMMS", "AMRT", "ANDI", "ANJT", "ASHA",
        "AYAM", "BEEF", "BEER", "BISI", "BOBA", "BTEK", "BUAH", "BUDI", "BWPT", "CAMP",
        "CBUT", "CEKA", "CLEO", "CMRY", "COCO", "CPIN", "CPRO", "CRAB", "CSRA", "DAYA",
        "DEWI", "DLTA", "DMND", "DPUM", "DSFI", "DSNG", "ENZO", "EPMT", "EURO", "FAPA",
        "FISH", "FLMC", "FOOD", "GGRM", "GOLL", "GOOD", "GRPM", "GULA", "GUNA", "GZCO",
        "HERO", "HMSP", "HOKI", "IBOS", "ICBP", "IKAN", "INDF", "IPPE", "ISEA", "ITIC",
        "JARR", "JAWA", "JPFA", "KEJU", "KINO", "KMDS", "KPAS", "LAPD", "LSIP", "MAGP",
        "MAIN", "MAXI", "MBTO", "MGRO", "MIDI", "MKTR", "MLBI", "MLPL", "MPPA", "MRAT",
        "MSJA", "MYOR", "NANO", "NASI", "NAYZ", "NSSS", "OILS", "PCAR", "PGUN", "PMMP",
        "PNGO", "PSDN", "PSGO", "PTPS", "RANC", "ROTI", "SDPC", "SGRO", "SIMP", "SIPD",
        "SKBM", "SKLT", "SMAR", "SOUL", "SSMS", "STAA", "STRK", "STTP", "TAPG", "TAYS",
        "TBLA", "TCID", "TGKA", "TGUK", "TLDN", "TRGU", "UCID", "UDNG", "ULTJ", "UNSP",
        "UNVR", "VICI", "WAPO", "WICO", "WIIM", "WINE", "WMPP", "WMUU",
    ],
    "Industri": [
        "AMFG", "AMIN", "APII", "ARKA", "ARNA", "ASGR", "ASII", "BHIT", "BINO", "BLUE",
        "BNBR", "CAKK", "CCSI", "CRSN", "CTTH", "DYAN", "FOLK", "GPSO", "HEXA", "HOPE",
        "HYGN", "IBFN", "ICON", "IKAI", "IKBI", "IMPC", "INDX", "INTA", "JECC", "JTPE",
        "KBLI", "KBLM", "KIAS", "KING", "KOBX", "KOIN", "KONI", "KPAL", "KRAH", "KUAS",
        "LABA", "LION", "MARK", "MDRN", "MFMI", "MHKI", "MLIA", "MUTU", "NTBK", "PADA",
        "PIPA", "PTMP", "SCCO", "SINI", "SKRN", "SMIL", "SOSS", "SPTO", "TIRA", "TOTO",
        "TRIL", "UNTR", "VISI", "VOKS", "WIDI", "ZBRA",
    ],
    "Transportasi & Logistik": [
        "AKSI", "ASSA", "BIRD", "BLTA", "BPTR", "CMPP", "DEAL", "ELPI", "GIAA", "GTRA",
        "HAIS", "HATM", "HELI", "IMJS", "JAYA", "KJEN", "KLAS", "LAJU", "LOPI", "LRNA",
        "MIRA", "MITI", "MPXL", "NELY", "PPGL", "PURA", "RCCC", "SAFE", "SAPX", "SDMU",
        "SMDR", "TAXI", "TMAS", "TNCA", "TRJA", "TRUK", "WEHA",
    ],
}

SECTOR_MAP = {kode: sektor for sektor, kodes in SECTOR_GROUPS.items() for kode in kodes}


def get_sector(kode: str) -> str:
    return SECTOR_MAP.get(kode.upper(), "Lainnya")

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
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df.index = pd.to_datetime(df.index)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def fetch_history_batch(kodes: tuple, period: str = "4mo") -> dict:
    """Ambil data banyak saham sekaligus (jauh lebih cepat daripada satu-satu)."""
    yf_tickers = [to_yf_ticker(k) for k in kodes]
    raw = yf.download(
        tickers=yf_tickers, period=period, interval="1d",
        group_by="ticker", threads=True, progress=False, auto_adjust=False,
    )
    result = {}
    for kode, yft in zip(kodes, yf_tickers):
        try:
            if len(yf_tickers) == 1:
                df = raw
            else:
                df = raw[yft]
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
            if not df.empty:
                result[kode] = df
        except Exception:
            continue
    return result


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ihsg_index(period: str = "6mo") -> pd.DataFrame:
    """Ambil data index IHSG (Jakarta Composite Index, kode Yahoo Finance: ^JKSE)."""
    df = yf.Ticker("^JKSE").history(period=period, interval="1d", auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
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


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger(series: pd.Series, period: int = 20, num_std: float = 2.0):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["EMA9"] = compute_ema(df["Close"], 9)
    df["EMA21"] = compute_ema(df["Close"], 21)
    df["EMA50"] = compute_ema(df["Close"], 50)
    df["RSI14"] = compute_rsi(df["Close"], 14)
    df["VolAvg20"] = df["Volume"].rolling(20).mean()
    df["High20"] = df["High"].rolling(20).max().shift(1)
    df["Low20"] = df["Low"].rolling(20).min().shift(1)
    df["ValueTraded"] = df["Close"] * df["Volume"]
    df["AvgValue20"] = df["ValueTraded"].rolling(20).mean()
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = compute_macd(df["Close"])
    df["BB_Upper"], df["BB_Mid"], df["BB_Lower"] = compute_bollinger(df["Close"])
    return df


def format_rupiah_ringkas(value: float) -> str:
    """Format angka jadi ringkas: 74.5B, 1.2T, dst (gaya terminal trading)."""
    if value is None or pd.isna(value):
        return "-"
    if value >= 1e12:
        return f"{value / 1e12:.2f}T"
    if value >= 1e9:
        return f"{value / 1e9:.2f}B"
    if value >= 1e6:
        return f"{value / 1e6:.2f}M"
    return f"{value:,.0f}"


def evaluate_signals(df: pd.DataFrame, min_avg_value_rp: float = 0) -> dict:
    """Cek sinyal radar sederhana: breakout, bounce, volume spike."""
    if len(df) < 25:
        return {}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Filter likuiditas: skip saham dengan rata-rata nilai transaksi 20 hari di bawah ambang
    avg_value = last["AvgValue20"] if pd.notna(last["AvgValue20"]) else 0
    if avg_value < min_avg_value_rp:
        return {}

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
        "avg_value": avg_value,
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


BADGE_PALETTE = ["#2DD4BF", "#F5A623", "#A78BFA", "#60A5FA", "#F472B6", "#34D399", "#FB923C", "#38BDF8"]


def ticker_badge_color(kode: str) -> str:
    idx = sum(ord(c) for c in kode) % len(BADGE_PALETTE)
    return BADGE_PALETTE[idx]


def compute_trading_plan(df: pd.DataFrame, pivots: dict) -> dict:
    """Rencana trading referensi (bukan sinyal pasti) dari support/resistance & pivot point."""
    last = df.iloc[-1]
    low20 = df["Low20"].iloc[-1] if pd.notna(df["Low20"].iloc[-1]) else last["Close"] * 0.95
    high20 = df["High20"].iloc[-1] if pd.notna(df["High20"].iloc[-1]) else last["Close"] * 1.05

    entry_low = min(last["EMA21"], last["Close"]) if pd.notna(last["EMA21"]) else pivots["s1"]
    entry_high = last["Close"]
    entry_mid = (entry_low + entry_high) / 2

    stop_loss = min(low20, pivots["s1"]) * 0.99
    target1 = pivots["r1"]
    target2 = max(pivots["r2"], high20)

    risk = entry_mid - stop_loss
    reward = target1 - entry_mid
    rr = reward / risk if risk > 0 else None

    progress_pct = 0
    if target1 != entry_mid:
        progress_pct = (last["Close"] - entry_mid) / (target1 - entry_mid) * 100
    progress_pct = max(0, min(100, progress_pct))

    return {
        "entry_low": entry_low, "entry_high": entry_high,
        "stop_loss": stop_loss, "target1": target1, "target2": target2,
        "rr": rr, "progress_pct": progress_pct,
    }


# ----------------------------------------------------------------------------
# HELPER: ANALISA FUNDAMENTAL
# ----------------------------------------------------------------------------

@st.cache_data(ttl=43200, show_spinner=False)  # 12 jam — data fundamental jarang berubah
def fetch_fundamentals(kode: str) -> dict:
    ticker = to_yf_ticker(kode)
    try:
        info = yf.Ticker(ticker).get_info()
    except Exception:
        return {}
    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
        return {}
    return {
        "kode": kode,
        "nama": info.get("longName") or info.get("shortName") or kode,
        "sektor": info.get("sector") or "-",
        "industri": info.get("industry") or "-",
        "harga": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": info.get("marketCap"),
        "per": info.get("trailingPE"),
        "pbv": info.get("priceToBook"),
        "roe": info.get("returnOnEquity"),
        "der": info.get("debtToEquity"),
        "revenue_growth": info.get("revenueGrowth"),
        "npm": info.get("profitMargins"),
        "dividend_yield": info.get("dividendYield"),
    }


def fetch_fundamentals_batch(kodes: list, max_workers: int = 8, progress_callback=None) -> list:
    """Ambil data fundamental banyak saham secara paralel (tetap 1 request per saham,
    tapi dijalankan bersamaan supaya jauh lebih cepat dari sekuensial)."""
    results = []
    total = len(kodes)
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_fundamentals, k): k for k in kodes}
        for future in as_completed(futures):
            done += 1
            if progress_callback:
                progress_callback(done, total, futures[future])
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception:
                continue
    return results


def fundamental_label(metric: str, value) -> tuple:
    """Return (label, css_class_badge) — aturan umum, bukan patokan mutlak, beda tiap sektor."""
    if value is None or pd.isna(value):
        return "N/A", "badge-sell"
    if metric == "per":
        if value <= 0:
            return "Rugi/N/A", "badge-sell"
        if value < 15:
            return "Relatif Murah", "badge-buy"
        if value <= 25:
            return "Wajar", "badge-warn"
        return "Relatif Mahal", "badge-sell"
    if metric == "pbv":
        if value < 1:
            return "Di Bawah Nilai Buku", "badge-buy"
        if value <= 3:
            return "Wajar", "badge-warn"
        return "Premium", "badge-sell"
    if metric == "roe":
        pct = value * 100
        if pct >= 15:
            return "Bagus", "badge-buy"
        if pct >= 8:
            return "Cukup", "badge-warn"
        return "Kurang", "badge-sell"
    if metric == "der":
        if value < 100:
            return "Sehat", "badge-buy"
        if value <= 200:
            return "Waspada", "badge-warn"
        return "Tinggi", "badge-sell"
    if metric == "npm":
        pct = value * 100
        if pct >= 10:
            return "Bagus", "badge-buy"
        if pct >= 3:
            return "Cukup", "badge-warn"
        return "Tipis", "badge-sell"
    if metric == "revenue_growth":
        pct = value * 100
        if pct > 5:
            return "Tumbuh", "badge-buy"
        if pct >= -5:
            return "Stagnan", "badge-warn"
        return "Menyusut", "badge-sell"
    return "-", "badge-warn"


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
st.sidebar.markdown("## ▲▼ Stock Radar")
st.sidebar.caption("Tools analisa saham pribadi — data via Yahoo Finance (delay ~15-20 menit)")

# Watchlist tersimpan lewat URL (bookmark link ini biar watchlist otomatis ke-load lagi)
url_watchlist = st.query_params.get("wl", "")
default_watchlist_str = url_watchlist.replace("_", ",") if url_watchlist else ", ".join(DEFAULT_WATCHLIST)

watchlist_input = st.sidebar.text_area(
    "Watchlist (pisahkan dengan koma)",
    value=default_watchlist_str,
    height=110,
)
watchlist = [x.strip().upper() for x in watchlist_input.split(",") if x.strip()]

# Cuma simpan ke URL kalau watchlist beda dari default (biar URL nggak jadi super panjang
# kalau kamu pakai default 951 saham). Custom watchlist yang lebih kecil tetap ke-bookmark normal.
if set(watchlist) != set(DEFAULT_WATCHLIST):
    st.query_params["wl"] = "_".join(watchlist)
elif "wl" in st.query_params:
    del st.query_params["wl"]

st.sidebar.caption(
    "💾 Kalau kamu custom-edit watchlist (bukan default 951 saham), otomatis kesimpen di URL browser — "
    "**bookmark halaman ini** biar watchlist custom kamu otomatis ke-load lagi."
)
st.sidebar.caption(f"📋 Total saham di watchlist saat ini: **{len(watchlist)}**")

liquidity_min_miliar = st.sidebar.slider(
    "Minimum rata-rata nilai transaksi harian (Miliar Rp)",
    min_value=0, max_value=100, value=5, step=1,
)
st.sidebar.caption(
    "Saham dengan rata-rata nilai transaksi 20 hari di bawah ambang ini "
    "akan disaring dari hasil Radar Harian (mengurangi sinyal palsu dari saham tipis)."
)

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
h_left, h_right = st.columns([3, 1])
with h_left:
    st.markdown(
        """
        <div class="app-header-left" style="padding-bottom:16px;border-bottom:1px solid var(--border);margin-bottom:6px">
            <div class="logo-mark">▲▼</div>
            <div>
                <div class="app-title">Stock Radar</div>
                <div class="app-subtitle">Analisa Teknikal & Radar Saham Harian — Bursa Efek Indonesia</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with h_right:
    components.html(
        """
        <div style="display:flex;align-items:center;justify-content:flex-end;height:100%;padding-top:6px">
            <div id="live-clock" style="
                font-family:'JetBrains Mono',monospace;
                font-size:12px;
                color:#2DD4BF;
                border:1px solid rgba(45,212,191,0.35);
                background:rgba(45,212,191,0.06);
                border-radius:20px;
                padding:6px 14px;
                white-space:nowrap;
            ">● memuat waktu...</div>
        </div>
        <style>
            html, body { background: transparent !important; margin:0; padding:0; }
        </style>
        <script>
            function updateClock() {
                const now = new Date();
                const opts = { timeZone: 'Asia/Jakarta' };
                const dateStr = now.toLocaleDateString('id-ID', { ...opts, day:'2-digit', month:'short', year:'numeric' });
                const timeStr = now.toLocaleTimeString('id-ID', { ...opts, hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false });
                const el = document.getElementById('live-clock');
                if (el) { el.innerText = '● ' + dateStr + ' · ' + timeStr + ' WIB'; }
            }
            updateClock();
            setInterval(updateClock, 1000);
        </script>
        """,
        height=50,
    )


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Analisa Saham", "🎯 Radar Harian", "🗺️ Overview IHSG", "🧮 Fundamental", "📰 Berita IHSG & Global",
])

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
    elif len(df_raw) < 2:
        st.warning(f"Data historis untuk **{kode_final}** terlalu sedikit untuk dianalisa (mungkin baru IPO atau jarang diperdagangkan). Coba saham lain atau perpanjang rentang data di sidebar.")
    else:
        df = enrich_indicators(df_raw)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        chg = last["Close"] - prev["Close"]
        chg_pct = chg / prev["Close"] * 100

        pivots = compute_pivot_points(df_raw)
        trend = trend_label(last)
        rsi_stat = rsi_label(last["RSI14"])
        plan = compute_trading_plan(df, pivots)

        # Metric cards
        m1, m2, m3, m4, m5 = st.columns(5)
        chg_color = "var(--up)" if chg >= 0 else "var(--down)"
        chg_sign = "+" if chg >= 0 else ""
        with m1:
            st.markdown(
                f"<div class='metric-box'><div class='metric-label'>Harga Terakhir</div>"
                f"<div class='metric-value'>Rp {last['Close']:,.0f}</div>"
                f"<div class='metric-sub' style='color:{chg_color}'>"
                f"{chg_sign}{chg:,.0f} ({chg_pct:+.2f}%)</div></div>",
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"<div class='metric-box'><div class='metric-label'>RSI (14)</div>"
                f"<div class='metric-value'>{last['RSI14']:.1f}</div>"
                f"<div class='metric-sub' style='color:var(--text-muted)'>{rsi_stat}</div></div>",
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f"<div class='metric-box'><div class='metric-label'>Trend (EMA)</div>"
                f"<div style='font-family:\"Space Grotesk\",sans-serif;font-size:16px;font-weight:700;margin-top:6px'>{trend}</div></div>",
                unsafe_allow_html=True,
            )
        with m4:
            vol_ratio = last["Volume"] / last["VolAvg20"] if last["VolAvg20"] else 0
            st.markdown(
                f"<div class='metric-box'><div class='metric-label'>Volume vs Avg20</div>"
                f"<div class='metric-value'>{vol_ratio:.2f}x</div></div>",
                unsafe_allow_html=True,
            )
        with m5:
            st.markdown(
                f"<div class='metric-box'><div class='metric-label'>Support / Resistance (Pivot)</div>"
                f"<div class='metric-sub' style='margin-top:6px;color:var(--text-primary)'>"
                f"S1: {pivots['s1']:,.0f} &nbsp;·&nbsp; R1: {pivots['r1']:,.0f}</div></div>",
                unsafe_allow_html=True,
            )

        st.write("")

        show_bb = st.checkbox("Tampilkan Bollinger Bands di chart harga", value=True, key="show_bb")

        # Candlestick chart + EMA + S/R + MACD
        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            row_heights=[0.42, 0.15, 0.2, 0.23], vertical_spacing=0.03,
            subplot_titles=("Harga & EMA", "Volume", "RSI (14)", "MACD"),
        )

        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name="Harga", increasing_line_color="#22C55E", decreasing_line_color="#EF4444",
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], name="EMA 9",
                                  line=dict(color="#2DD4BF", width=1.3)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA21"], name="EMA 21",
                                  line=dict(color="#F5A623", width=1.3)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50",
                                  line=dict(color="#A78BFA", width=1.3)), row=1, col=1)

        if show_bb:
            fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper",
                                      line=dict(color="#7C8698", width=1, dash="dot"),
                                      showlegend=True), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
                                      line=dict(color="#7C8698", width=1, dash="dot"),
                                      fill="tonexty", fillcolor="rgba(124,134,152,0.07)",
                                      showlegend=True), row=1, col=1)

        # Entry / Target / Stop Loss — digambar langsung di chart
        fig.add_hline(y=plan["entry_high"], line_dash="dash", line_color="#2DD4BF",
                      annotation_text="Entry 1", annotation_font_color="#2DD4BF", row=1, col=1)
        fig.add_hline(y=plan["entry_low"], line_dash="dash", line_color="#2DD4BF",
                      annotation_text="Entry 2", annotation_font_color="#2DD4BF", row=1, col=1)
        fig.add_hline(y=plan["stop_loss"], line_dash="dash", line_color="#EF4444",
                      annotation_text="SL", annotation_font_color="#EF4444", row=1, col=1)
        fig.add_hline(y=plan["target1"], line_dash="dash", line_color="#22C55E",
                      annotation_text="TP1", annotation_font_color="#22C55E", row=1, col=1)
        fig.add_hline(y=plan["target2"], line_dash="dot", line_color="#22C55E",
                      annotation_text="TP2", annotation_font_color="#22C55E", row=1, col=1)

        vol_colors = np.where(df["Close"] >= df["Open"], "#22C55E", "#EF4444")
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                              marker_color=vol_colors), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["VolAvg20"], name="Vol Avg 20",
                                  line=dict(color="#7C8698", width=1)), row=2, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI 14",
                                  line=dict(color="#A78BFA", width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#EF4444", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#22C55E", row=3, col=1)

        macd_hist_colors = np.where(df["MACD_Hist"] >= 0, "#22C55E", "#EF4444")
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_Hist"], name="MACD Histogram",
                              marker_color=macd_hist_colors), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                                  line=dict(color="#2DD4BF", width=1.3)), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal",
                                  line=dict(color="#F5A623", width=1.3)), row=4, col=1)
        fig.add_hline(y=0, line_color="#7C8698", line_width=1, row=4, col=1)

        fig.update_layout(
            height=980, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis_rangeslider_visible=False,
            font=dict(family="Inter, sans-serif", color="#E8EBF2"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Interpretasi otomatis
        st.markdown("#### 🧠 Ringkasan Analisa Otomatis")
        interp = []
        interp.append(f"- **Trend EMA**: {trend} (EMA9 {last['EMA9']:,.0f} / EMA21 {last['EMA21']:,.0f} / EMA50 {last['EMA50']:,.0f}).")
        interp.append(f"- **RSI 14**: {last['RSI14']:.1f} → kondisi **{rsi_stat}**.")
        macd_status = "Bullish (MACD di atas Signal)" if last["MACD"] > last["MACD_Signal"] else "Bearish (MACD di bawah Signal)"
        interp.append(f"- **MACD**: {last['MACD']:.2f} vs Signal {last['MACD_Signal']:.2f} → **{macd_status}**.")
        bb_position = "di atas Upper Band (overbought)" if last["Close"] > last["BB_Upper"] else "di bawah Lower Band (oversold)" if last["Close"] < last["BB_Lower"] else "di dalam band (normal)"
        interp.append(f"- **Bollinger Bands**: harga saat ini {bb_position}.")
        interp.append(f"- **Volume**: {vol_ratio:.2f}x rata-rata 20 hari" + (" (di atas rata-rata, ada minat pasar lebih tinggi)." if vol_ratio > 1 else " (di bawah rata-rata, minat pasar relatif sepi)."))
        interp.append(f"- **Support terdekat**: Rp {pivots['s1']:,.0f} (pivot) / Rp {df['Low20'].iloc[-1]:,.0f} (low 20 hari).")
        interp.append(f"- **Resistance terdekat**: Rp {pivots['r1']:,.0f} (pivot) / Rp {df['High20'].iloc[-1]:,.0f} (high 20 hari).")
        st.markdown("\n".join(interp))
        st.caption("Catatan: ringkasan ini murni hasil perhitungan indikator teknikal, bukan saran investasi.")

        # Rencana Trading (referensi teknikal)
        st.markdown("#### 📋 Rencana Trading (Referensi Teknikal)")

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown(
                f"<div class='plan-box'><div class='plan-label'>Entry Area</div>"
                f"<div class='plan-value'>{plan['entry_low']:,.0f} – {plan['entry_high']:,.0f}</div></div>",
                unsafe_allow_html=True,
            )
        with p2:
            st.markdown(
                f"<div class='plan-box'><div class='plan-label'>Target (TP1 / TP2)</div>"
                f"<div class='plan-value' style='color:var(--up)'>{plan['target1']:,.0f} / {plan['target2']:,.0f}</div></div>",
                unsafe_allow_html=True,
            )
        with p3:
            st.markdown(
                f"<div class='plan-box'><div class='plan-label'>Stop Loss</div>"
                f"<div class='plan-value' style='color:var(--down)'>{plan['stop_loss']:,.0f}</div></div>",
                unsafe_allow_html=True,
            )
        with p4:
            rr_text = f"1 : {plan['rr']:.1f}" if plan["rr"] else "-"
            st.markdown(
                f"<div class='plan-box'><div class='plan-label'>Risk / Reward</div>"
                f"<div class='plan-value'>{rr_text}</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<div style='margin-top:10px'>"
            f"<div class='plan-label'>{plan['progress_pct']:.1f}% menuju TP1 dari area entry</div>"
            f"<div class='progress-track'><div class='progress-fill' style='width:{plan['progress_pct']:.0f}%'></div></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "⚠️ Rencana trading ini dihitung otomatis dari support/resistance & pivot point — "
            "bukan sinyal pasti dan bukan rekomendasi jual/beli. Selalu sesuaikan dengan analisa & manajemen risiko kamu sendiri."
        )

# ----------------------------------------------------------------------------
# TAB 2 — RADAR SAHAM HARIAN
# ----------------------------------------------------------------------------
with tab2:
    st.markdown("### 🎯 Radar Saham Harian")
    st.caption("Scan watchlist untuk sinyal **Breakout**, **Bounce/Rebound**, dan **Volume Spike**.")

    if len(watchlist) > 300:
        st.caption(f"⏱️ Watchlist kamu ada {len(watchlist)} saham — scan pertama bisa makan waktu beberapa menit. Hasil akan di-cache 5 menit.")
    scan_btn = st.button("🔍 Scan Watchlist Sekarang", type="primary")

    if scan_btn:
        results = []
        min_avg_value_rp = liquidity_min_miliar * 1_000_000_000
        with st.spinner(f"Mengambil data {len(watchlist)} saham sekaligus (batch)..."):
            batch_data = fetch_history_batch(tuple(watchlist), period="4mo")

        progress = st.progress(0, text="Menganalisa sinyal...")
        skipped_illiquid = 0
        for i, kode in enumerate(watchlist):
            progress.progress((i + 1) / len(watchlist), text=f"Menganalisa {kode}...")
            try:
                raw = batch_data.get(kode)
                if raw is None or raw.empty:
                    continue
                enriched = enrich_indicators(raw)
                sig = evaluate_signals(enriched, min_avg_value_rp=min_avg_value_rp)
                if sig:
                    sig["kode"] = kode
                    results.append(sig)
                elif len(enriched) >= 25:
                    last_val = enriched["AvgValue20"].iloc[-1]
                    if pd.notna(last_val) and last_val < min_avg_value_rp:
                        skipped_illiquid += 1
            except Exception:
                continue
        progress.empty()

        if skipped_illiquid > 0:
            st.caption(f"ℹ️ {skipped_illiquid} saham disaring karena rata-rata nilai transaksi di bawah Rp {liquidity_min_miliar} Miliar/hari.")

        if not results:
            st.info("Tidak ada sinyal Breakout / Bounce / Volume Spike terdeteksi di watchlist saat ini.")
        else:
            df_res = pd.DataFrame(results)
            df_res = df_res[["kode", "harga", "perubahan_%", "rsi", "vol_ratio", "avg_value", "sinyal"]]

            csv_export = df_res.copy()
            csv_export["sinyal"] = csv_export["sinyal"].apply(lambda s: ", ".join(s))
            csv_export.columns = ["Kode", "Harga", "Perubahan (%)", "RSI", "Vol Ratio", "Avg Value (Rp)", "Sinyal"]
            st.download_button(
                "⬇️ Download Hasil Scan (CSV)",
                data=csv_export.to_csv(index=False).encode("utf-8"),
                file_name=f"radar_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

            for sinyal_type, emoji, desc, css_class in [
                ("Breakout", "▲", "Harga menembus resistance 20 hari dengan volume tinggi", "breakout"),
                ("Bounce", "↻", "Rebound dari area support / EMA21 dengan RSI membaik", "bounce"),
                ("Volume Spike", "◆", "Lonjakan volume signifikan (≥2x rata-rata 20 hari)", "volspike"),
            ]:
                subset = df_res[df_res["sinyal"].apply(lambda s: sinyal_type in s)]
                if subset.empty:
                    continue
                st.markdown(f"#### {emoji} {sinyal_type}")
                st.caption(desc)
                for _, row in subset.iterrows():
                    badge_class = "badge-buy" if row["perubahan_%"] >= 0 else "badge-sell"
                    bcolor = ticker_badge_color(row["kode"])
                    st.markdown(
                        f"<div class='radar-card {css_class}'>"
                        f"<div style='display:flex;align-items:center;gap:12px'>"
                        f"<div class='ticker-badge' style='background:{bcolor}22;color:{bcolor};border:1px solid {bcolor}66'>{row['kode'][0]}</div>"
                        f"<div style='flex:1'>"
                        f"<span class='radar-ticker'>{row['kode']}</span> "
                        f"<span class='{badge_class}'>{row['perubahan_%']:+.2f}%</span>"
                        f"<div class='radar-detail'>"
                        f"Rp {row['harga']:,.0f} &nbsp;·&nbsp; RSI {row['rsi']} "
                        f"&nbsp;·&nbsp; Vol {row['vol_ratio']:.2f}x avg20 "
                        f"&nbsp;·&nbsp; Nilai {format_rupiah_ringkas(row['avg_value'])}</div>"
                        f"</div></div></div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.info("Klik tombol di atas untuk mulai scan watchlist kamu.")

# ----------------------------------------------------------------------------
# TAB 3 — OVERVIEW IHSG & HEATMAP SEKTOR
# ----------------------------------------------------------------------------
with tab3:
    st.markdown("### 🗺️ Overview IHSG & Heatmap Sektor")

    # --- Index IHSG ---
    with st.spinner("Mengambil data index IHSG..."):
        df_ihsg = fetch_ihsg_index(period="6mo")

    if df_ihsg.empty:
        st.error("Data index IHSG tidak dapat diambil saat ini.")
    else:
        last_ihsg = df_ihsg.iloc[-1]
        prev_ihsg = df_ihsg.iloc[-2]
        ihsg_chg = last_ihsg["Close"] - prev_ihsg["Close"]
        ihsg_chg_pct = ihsg_chg / prev_ihsg["Close"] * 100
        ihsg_color = "var(--up)" if ihsg_chg >= 0 else "var(--down)"
        ihsg_sign = "+" if ihsg_chg >= 0 else ""

        i1, i2, i3 = st.columns(3)
        with i1:
            st.markdown(
                f"<div class='metric-box'><div class='metric-label'>IHSG (Jakarta Composite)</div>"
                f"<div class='metric-value' style='font-size:24px'>{last_ihsg['Close']:,.2f}</div>"
                f"<div class='metric-sub' style='color:{ihsg_color}'>{ihsg_sign}{ihsg_chg:,.2f} ({ihsg_chg_pct:+.2f}%)</div></div>",
                unsafe_allow_html=True,
            )
        with i2:
            st.markdown(
                f"<div class='metric-box'><div class='metric-label'>Tertinggi Hari Ini</div>"
                f"<div class='metric-value'>{last_ihsg['High']:,.2f}</div></div>",
                unsafe_allow_html=True,
            )
        with i3:
            st.markdown(
                f"<div class='metric-box'><div class='metric-label'>Terendah Hari Ini</div>"
                f"<div class='metric-value'>{last_ihsg['Low']:,.2f}</div></div>",
                unsafe_allow_html=True,
            )

        fig_ihsg = go.Figure()
        fig_ihsg.add_trace(go.Scatter(
            x=df_ihsg.index, y=df_ihsg["Close"], mode="lines", name="IHSG",
            line=dict(color="#2DD4BF", width=2),
            fill="tozeroy", fillcolor="rgba(45,212,191,0.08)",
        ))
        fig_ihsg.update_layout(
            height=280, template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#E8EBF2"),
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis=dict(range=[df_ihsg["Close"].min() * 0.98, df_ihsg["Close"].max() * 1.02]),
        )
        st.plotly_chart(fig_ihsg, use_container_width=True)

    st.markdown("---")

    # --- Market Breadth & Heatmap Sektor ---
    st.markdown("#### 📡 Market Breadth & Heatmap Sektor")
    st.caption("Berdasarkan pergerakan harga hari terakhir dari seluruh saham di watchlist kamu.")

    if len(watchlist) > 300:
        st.caption(f"⏱️ Watchlist kamu ada {len(watchlist)} saham — proses ini bisa makan waktu beberapa menit.")
    breadth_btn = st.button("🔄 Muat Data Market", type="primary", key="breadth_btn")

    if breadth_btn:
        with st.spinner(f"Mengambil data {len(watchlist)} saham..."):
            batch_data = fetch_history_batch(tuple(watchlist), period="1mo")

        rows = []
        for kode in watchlist:
            raw = batch_data.get(kode)
            if raw is None or len(raw) < 2:
                continue
            last_c = raw["Close"].iloc[-1]
            prev_c = raw["Close"].iloc[-2]
            if prev_c == 0:
                continue
            chg_pct = (last_c - prev_c) / prev_c * 100
            rows.append({"kode": kode, "sektor": get_sector(kode), "chg_pct": chg_pct})

        if not rows:
            st.warning("Data tidak tersedia. Coba lagi beberapa saat.")
        else:
            df_breadth = pd.DataFrame(rows)
            n_up = (df_breadth["chg_pct"] > 0).sum()
            n_down = (df_breadth["chg_pct"] < 0).sum()
            n_flat = (df_breadth["chg_pct"] == 0).sum()
            total = len(df_breadth)

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                st.markdown(
                    f"<div class='metric-box'><div class='metric-label'>Saham Naik</div>"
                    f"<div class='metric-value' style='color:var(--up)'>{n_up}</div></div>",
                    unsafe_allow_html=True,
                )
            with b2:
                st.markdown(
                    f"<div class='metric-box'><div class='metric-label'>Saham Turun</div>"
                    f"<div class='metric-value' style='color:var(--down)'>{n_down}</div></div>",
                    unsafe_allow_html=True,
                )
            with b3:
                st.markdown(
                    f"<div class='metric-box'><div class='metric-label'>Tidak Berubah</div>"
                    f"<div class='metric-value'>{n_flat}</div></div>",
                    unsafe_allow_html=True,
                )
            with b4:
                ratio = n_up / n_down if n_down > 0 else n_up
                st.markdown(
                    f"<div class='metric-box'><div class='metric-label'>Rasio Naik:Turun</div>"
                    f"<div class='metric-value'>{ratio:.2f}</div></div>",
                    unsafe_allow_html=True,
                )

            # Bar breadth sederhana
            fig_breadth = go.Figure()
            fig_breadth.add_trace(go.Bar(
                x=["Naik", "Turun", "Tidak Berubah"], y=[n_up, n_down, n_flat],
                marker_color=["#22C55E", "#EF4444", "#7C8698"],
            ))
            fig_breadth.update_layout(
                height=220, template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#E8EBF2"),
                margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
            )
            st.plotly_chart(fig_breadth, use_container_width=True)

            st.markdown("#### 🔥 Heatmap Performa Sektor")
            sector_avg = df_breadth.groupby("sektor")["chg_pct"].mean().reset_index()
            sector_count = df_breadth.groupby("sektor").size().reset_index(name="count")
            sector_stats = sector_avg.merge(sector_count, on="sektor")

            fig_heat = go.Figure(go.Treemap(
                labels=sector_stats["sektor"],
                parents=[""] * len(sector_stats),
                values=sector_stats["count"],
                marker=dict(
                    colors=sector_stats["chg_pct"],
                    colorscale=[[0, "#EF4444"], [0.5, "#7C8698"], [1, "#22C55E"]],
                    cmid=0,
                    showscale=True,
                    colorbar=dict(title="% Chg"),
                ),
                text=[f"{s}<br>{c:+.2f}%" for s, c in zip(sector_stats["sektor"], sector_stats["chg_pct"])],
                textinfo="text",
                textfont=dict(family="Inter, sans-serif", size=13, color="#0A0E17"),
            ))
            fig_heat.update_layout(
                height=380, margin=dict(l=5, r=5, t=5, b=5),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_heat, use_container_width=True)
            st.caption("Ukuran kotak = jumlah saham per sektor di watchlist. Warna = rata-rata perubahan harga sektor hari ini.")
    else:
        st.info("Klik tombol di atas untuk memuat market breadth & heatmap sektor.")

# ----------------------------------------------------------------------------
# TAB 4 — ANALISA FUNDAMENTAL
# ----------------------------------------------------------------------------
with tab4:
    st.markdown("### 🧮 Analisa Fundamental")
    st.caption(
        "Metrik: PER, PBV, ROE, DER, pertumbuhan pendapatan, net profit margin. "
        "Data dari Yahoo Finance — beberapa saham IDX punya data terbatas."
    )

    sub_tab_single, sub_tab_screener = st.tabs(["🔍 Cek 1 Saham", "📋 Screener Watchlist"])

    with sub_tab_single:
        kode_fund = st.selectbox(
            "Pilih kode saham",
            options=sorted(set(watchlist)),
            index=0,
            key="fund_ticker_select",
        )
        manual_fund = st.text_input("Atau ketik kode lain", value="", key="fund_ticker_manual")
        kode_fund_final = manual_fund.strip().upper() if manual_fund.strip() else kode_fund

        with st.spinner(f"Mengambil data fundamental {kode_fund_final}..."):
            fdata = fetch_fundamentals(kode_fund_final)

        if not fdata:
            st.error(f"Data fundamental untuk **{kode_fund_final}** tidak tersedia.")
        else:
            st.markdown(f"#### {fdata['nama']} ({fdata['kode']})")
            st.caption(f"Sektor: {fdata['sektor']} · Industri: {fdata['industri']}")

            f1, f2, f3, f4, f5, f6 = st.columns(6)
            metric_defs = [
                (f1, "PER", fdata["per"], "per", lambda v: f"{v:.1f}x" if v else "N/A"),
                (f2, "PBV", fdata["pbv"], "pbv", lambda v: f"{v:.2f}x" if v else "N/A"),
                (f3, "ROE", fdata["roe"], "roe", lambda v: f"{v*100:.1f}%" if v is not None else "N/A"),
                (f4, "DER", fdata["der"], "der", lambda v: f"{v:.0f}%" if v is not None else "N/A"),
                (f5, "NPM", fdata["npm"], "npm", lambda v: f"{v*100:.1f}%" if v is not None else "N/A"),
                (f6, "Growth Revenue", fdata["revenue_growth"], "revenue_growth", lambda v: f"{v*100:+.1f}%" if v is not None else "N/A"),
            ]
            for col, label, val, metric_key, fmt in metric_defs:
                with col:
                    lbl_text, badge_cls = fundamental_label(metric_key, val)
                    st.markdown(
                        f"<div class='metric-box'><div class='metric-label'>{label}</div>"
                        f"<div class='metric-value' style='font-size:17px'>{fmt(val)}</div>"
                        f"<div style='margin-top:6px'><span class='{badge_cls}'>{lbl_text}</span></div></div>",
                        unsafe_allow_html=True,
                    )

            st.write("")
            m1, m2 = st.columns(2)
            with m1:
                mcap = fdata["market_cap"]
                st.markdown(
                    f"<div class='metric-box'><div class='metric-label'>Market Cap</div>"
                    f"<div class='metric-value'>Rp {format_rupiah_ringkas(mcap)}</div></div>",
                    unsafe_allow_html=True,
                )
            with m2:
                dy = fdata["dividend_yield"]
                dy_text = f"{dy*100:.2f}%" if dy is not None else "N/A"
                st.markdown(
                    f"<div class='metric-box'><div class='metric-label'>Dividend Yield</div>"
                    f"<div class='metric-value'>{dy_text}</div></div>",
                    unsafe_allow_html=True,
                )

            st.caption(
                "⚠️ Ambang label (mis. ROE 'Bagus' ≥15%) adalah aturan umum lintas sektor, bukan patokan mutlak — "
                "perusahaan perbankan/properti/komoditas punya karakteristik rasio yang berbeda-beda. "
                "Bandingkan dengan kompetitor sesektor sebelum mengambil keputusan."
            )

    with sub_tab_screener:
        st.caption(
            "Scan seluruh watchlist untuk metrik fundamental. Data di-cache 12 jam, "
            "jadi scan berikutnya jauh lebih cepat."
        )
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            min_roe = st.number_input("Min ROE (%)", value=0, step=1)
        with f_col2:
            max_der = st.number_input("Max DER (%)", value=300, step=10)
        with f_col3:
            max_per = st.number_input("Max PER (0 = tanpa batas)", value=0, step=1)

        if len(watchlist) > 300:
            st.caption(f"⏱️ Watchlist kamu ada {len(watchlist)} saham — fetch data fundamental (1 request per saham) bisa makan waktu cukup lama di scan pertama. Hasil di-cache 12 jam.")
        screener_btn = st.button("🔍 Scan Fundamental Watchlist", type="primary", key="fund_screener_btn")

        if screener_btn:
            progress = st.progress(0, text="Mengambil data fundamental...")

            def update_progress(done, total, kode):
                progress.progress(done / total, text=f"Mengambil data fundamental... ({done}/{total}) {kode}")

            fund_results = fetch_fundamentals_batch(watchlist, max_workers=8, progress_callback=update_progress)
            progress.empty()

            if not fund_results:
                st.warning("Tidak ada data fundamental yang berhasil diambil.")
            else:
                df_fund = pd.DataFrame(fund_results)

                mask = pd.Series(True, index=df_fund.index)
                if min_roe > 0:
                    mask &= df_fund["roe"].apply(lambda v: v is not None and pd.notna(v) and v * 100 >= min_roe)
                if max_der > 0:
                    mask &= df_fund["der"].apply(lambda v: v is not None and pd.notna(v) and v <= max_der)
                if max_per > 0:
                    mask &= df_fund["per"].apply(lambda v: v is not None and pd.notna(v) and 0 < v <= max_per)

                df_filtered = df_fund[mask].copy()
                st.caption(f"{len(df_filtered)} dari {len(df_fund)} saham (dengan data tersedia) lolos filter.")

                if df_filtered.empty:
                    st.info("Tidak ada saham yang lolos kriteria filter. Coba longgarkan filternya.")
                else:
                    df_filtered = df_filtered.sort_values("roe", ascending=False, na_position="last")
                    display_df = df_filtered[["kode", "nama", "sektor", "per", "pbv", "roe", "der", "npm", "revenue_growth"]].copy()
                    display_df["roe"] = display_df["roe"].apply(lambda v: f"{v*100:.1f}%" if pd.notna(v) else "-")
                    display_df["der"] = display_df["der"].apply(lambda v: f"{v:.0f}%" if pd.notna(v) else "-")
                    display_df["npm"] = display_df["npm"].apply(lambda v: f"{v*100:.1f}%" if pd.notna(v) else "-")
                    display_df["revenue_growth"] = display_df["revenue_growth"].apply(lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "-")
                    display_df["per"] = display_df["per"].apply(lambda v: f"{v:.1f}x" if pd.notna(v) else "-")
                    display_df["pbv"] = display_df["pbv"].apply(lambda v: f"{v:.2f}x" if pd.notna(v) else "-")
                    display_df.columns = ["Kode", "Nama", "Sektor", "PER", "PBV", "ROE", "DER", "NPM", "Growth Rev."]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    st.download_button(
                        "⬇️ Download Hasil Screener (CSV)",
                        data=display_df.to_csv(index=False).encode("utf-8"),
                        file_name=f"fundamental_screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        key="download_fund_csv",
                    )
        else:
            st.info("Atur filter (opsional) lalu klik tombol scan untuk mulai.")


with tab5:
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
