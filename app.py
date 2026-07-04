import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from scipy import stats
import time

st.set_page_config(
    page_title="Feel-the-Model™ | Between 0 and 1",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg:     #03050a; --surface: #080d17; --card: #0c1220;
  --border: rgba(255,255,255,0.07); --text: #e2e8f0;
  --muted:  #64748b; --subtle:  #94a3b8;
  --indigo: #818cf8; --sky:     #38bdf8; --violet: #a78bfa;
}
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: 'Inter', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stAppViewContainer"] { background: var(--bg) !important; }
[data-testid="stMainBlockContainer"] { padding: 0 2.5rem !important; max-width: 1200px !important; }
[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
section[data-testid="stSidebar"] { display: none; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
label[data-testid="stWidgetLabel"] p {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important; color: var(--muted) !important;
  letter-spacing: 0.08em; text-transform: uppercase;
}
[data-testid="stTextInput"] input {
  background: rgba(12,18,32,0.8) !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
  color: var(--text) !important; border-radius: 10px !important;
  font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important;
}
[data-testid="stFileUploader"] {
  background: rgba(12,18,32,0.6) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 14px !important;
}
[data-testid="stDownloadButton"] button {
  background: rgba(129,140,248,0.08) !important;
  border: 1px solid rgba(129,140,248,0.2) !important;
  color: #a5b4fc !important; font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important; border-radius: 8px !important;
}
[data-testid="stButton"] button {
  background: linear-gradient(135deg, rgba(129,140,248,0.12), rgba(56,189,248,0.08)) !important;
  border: 1px solid rgba(129,140,248,0.25) !important;
  color: #a5b4fc !important; font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important; border-radius: 10px !important;
  transition: all 0.2s !important;
}
hr { border-color: rgba(255,255,255,0.05) !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NEUROAESTHETIC TRANSLATION LAYER
# ══════════════════════════════════════════════════════════════════════════════

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))

def ntl_signals_to_params(s):
    hue        = 195.0 - (s["risk"] * 195.0)
    saturation = 0.15 + (s["confidence"] * 0.65)
    lightness  = 0.32 + (s["signal_strength"] * 0.22)
    blur       = s["volatility"] * 10.0
    angle      = 135.0 + ((1.0 - s["stability"]) * 45.0)
    return {"hue": hue, "saturation": saturation, "lightness": lightness,
            "blur": blur, "angle": angle}

def hsl(h, s, l):
    return f"hsl({h:.0f},{s*100:.0f}%,{l*100:.0f}%)"

def ntl_colors(p):
    h, s, l = p["hue"], p["saturation"], p["lightness"]
    return (hsl(h, s, l), hsl(h+28, s*0.55, l*0.80),
            hsl(h-18, s*0.35, l*1.15), hsl(h, s*0.6, l*1.3))

def neuro_label(s):
    r, c, v = s["risk"], s["confidence"], s["volatility"]
    if r > 0.72 and c < 0.40: return "⚡ High tension — move with caution"
    if r > 0.55 and c > 0.65: return "⚠ Elevated risk — signal is clear"
    if r < 0.25 and c > 0.72: return "● Calm & confident — strong position"
    if v > 0.65:               return "〜 High uncertainty — hold and observe"
    if c > 0.82:               return "◉ Strong signal — low noise"
    if r < 0.35 and v < 0.35: return "◦ Stable — continue monitoring"
    return "∿ Mixed signal — seek confirmation"

def neuro_state(s):
    r, c, v = s["risk"], s["confidence"], s["volatility"]
    if r > 0.65:               return "TENSION"
    if c > 0.78 and r < 0.3:  return "CONFIDENCE"
    if v > 0.60:               return "UNCERTAINTY"
    if c > 0.70 and v < 0.3:  return "CLARITY"
    if r < 0.25 and v < 0.25: return "CALM"
    return "EQUILIBRIUM"

def portfolio_agg(rows):
    return {k: float(np.mean([r[k] for r in rows]))
            for k in ["confidence","risk","volatility","stability","signal_strength"]}


# ══════════════════════════════════════════════════════════════════════════════
# LIVE MARKET DATA via yfinance
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def fetch_ticker_signals(ticker: str):
    try:
        stock = yf.Ticker(ticker.upper().strip())
        hist  = stock.history(period="3mo")
        if hist.empty or len(hist) < 10:
            return None

        prices  = hist["Close"].values.astype(float)
        volumes = hist["Volume"].values.astype(float)
        returns = np.diff(prices) / (prices[:-1] + 1e-8)

        # Confidence: R² of linear trend on last 30 candles
        window  = min(30, len(prices))
        x       = np.arange(window)
        y       = prices[-window:]
        slope, intercept, r_val, _, _ = stats.linregress(x, y)
        confidence = clamp(abs(r_val))

        # Risk: annualized vol normalized (80% annual vol = risk 1.0)
        daily_vol  = float(np.std(returns)) if len(returns) > 1 else 0.01
        annual_vol = daily_vol * np.sqrt(252)
        risk       = clamp(annual_vol / 0.80)

        # Volatility: short-term (5d) vs long-term ratio
        recent_ret = returns[-5:] if len(returns) >= 5 else returns
        short_vol  = float(np.std(recent_ret)) if len(recent_ret) > 1 else daily_vol
        volatility = clamp((short_vol / (daily_vol + 1e-8)) * 0.65)

        # Stability: return autocorrelation (trending vs mean-reverting)
        if len(returns) > 5:
            ac = np.corrcoef(returns[:-1], returns[1:])[0, 1]
            stability = clamp((float(ac) + 1.0) / 2.0)
        else:
            stability = 0.5

        # Signal strength: recent volume vs 30d average
        avg_vol    = float(np.mean(volumes[-30:])) + 1e-8
        recent_avg = float(np.mean(volumes[-5:]))
        signal_strength = clamp(min(recent_avg / avg_vol, 2.0) / 2.0)

        info     = stock.info
        name     = info.get("shortName", ticker.upper())
        price    = float(prices[-1])
        chg_pct  = float((prices[-1] - prices[-2]) / (prices[-2] + 1e-8) * 100) if len(prices) > 1 else 0.0

        return {
            "ticker": ticker.upper(), "name": name,
            "price": price, "change_pct": chg_pct,
            "confidence": confidence, "risk": risk,
            "volatility": volatility, "stability": stability,
            "signal_strength": signal_strength,
        }
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# HTML COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def ntl_card(name, signals, subtitle="", show_numbers=False, size="normal"):
    params         = ntl_signals_to_params(signals)
    c1, c2, c3, bc = ntl_colors(params)
    label          = neuro_label(signals)
    state          = neuro_state(signals)
    grad_h         = "160px" if size == "large" else "110px"

    signal_keys = [("CONF", "confidence","#818cf8"),
                   ("RISK", "risk",       c1),
                   ("VOL",  "volatility", "#94a3b8"),
                   ("STAB", "stability",  "#38bdf8"),
                   ("SIG",  "signal_strength","#a78bfa")]

    dots_html = "".join(f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px">
            <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:#334155">{k}</div>
            <div style="width:5px;height:{int(signals[key]*28)+4}px;border-radius:3px;
                        background:{color};opacity:{0.35+signals[key]*0.65:.2f}"></div>
            {'<div style="font-size:9px;font-family:JetBrains Mono,monospace;color:#475569">'+f"{signals[key]:.0%}"+'</div>' if show_numbers else ''}
        </div>
    """ for k, key, color in signal_keys)

    sub_html = f'<div style="font-size:11px;color:#475569;font-family:JetBrains Mono,monospace;margin-bottom:4px">{subtitle}</div>' if subtitle else ""

    return f"""
    <div style="
        background:rgba(12,18,32,0.88);border:1px solid {bc};
        border-radius:18px;overflow:hidden;margin-bottom:14px;
        backdrop-filter:blur(12px);
        transition:transform 0.3s,box-shadow 0.3s;"
    onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 24px 60px rgba(0,0,0,0.5)'"
    onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='none'">
        <div style="position:relative;height:{grad_h};overflow:hidden">
            <div style="position:absolute;inset:-4px;
                        background:linear-gradient({params['angle']:.0f}deg,{c1},{c2},{c3});
                        filter:blur({params['blur']:.1f}px);transform:scale(1.05)"></div>
            <div style="position:absolute;top:10px;left:14px;
                        font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:2px;
                        background:rgba(3,5,10,0.55);backdrop-filter:blur(8px);
                        padding:3px 10px;border-radius:20px;color:rgba(255,255,255,0.6)">
                BETWEEN 0 AND 1™ · NTL</div>
            <div style="position:absolute;bottom:10px;right:12px;
                        font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;font-weight:700;
                        background:rgba(3,5,10,0.65);backdrop-filter:blur(8px);
                        padding:4px 12px;border-radius:20px;color:{c1}">{state}</div>
        </div>
        <div style="padding:16px 20px 14px">
            {sub_html}
            <div style="font-size:17px;font-weight:700;color:#e2e8f0;margin-bottom:5px;letter-spacing:-0.2px">{name}</div>
            <div style="font-size:11px;color:#64748b;margin-bottom:14px;font-family:'JetBrains Mono',monospace">{label}</div>
            <div style="display:flex;gap:9px;align-items:flex-end;
                        padding:10px 0 6px;border-top:1px solid rgba(255,255,255,0.04)">
                {dots_html}
                <div style="flex:1"></div>
                <div style="font-size:9px;color:#1e293b;font-family:'JetBrains Mono',monospace;text-align:right">
                    HUE {params['hue']:.0f}° · SAT {params['saturation']:.0%} · BLUR {params['blur']:.1f}px
                </div>
            </div>
        </div>
    </div>"""

def portfolio_banner(agg_s):
    p           = ntl_signals_to_params(agg_s)
    c1,c2,c3,_  = ntl_colors(p)
    return f"""
    <div style="position:relative;border-radius:20px;overflow:hidden;margin-bottom:24px;border:1px solid rgba(255,255,255,0.06)">
        <div style="position:absolute;inset:-4px;
                    background:linear-gradient({p['angle']:.0f}deg,{c1},{c2},{c3});
                    filter:blur({p['blur']:.1f}px);opacity:0.16;transform:scale(1.04)"></div>
        <div style="position:relative;background:rgba(8,13,23,0.88);backdrop-filter:blur(20px);padding:28px 32px">
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;
                        background:linear-gradient(90deg,{c1},{c2});
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        background-clip:text;font-weight:600;margin-bottom:8px">PORTFOLIO NEUROAESTHETIC STATE</div>
            <div style="font-size:30px;font-weight:800;color:#e2e8f0;letter-spacing:-1px;margin-bottom:6px">{neuro_state(agg_s)}</div>
            <div style="font-size:12px;color:#64748b;font-family:'JetBrains Mono',monospace">{neuro_label(agg_s)}</div>
        </div>
    </div>"""

def sec_header(label, title):
    return f"""
    <div style="padding:28px 0 14px">
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;
                    background:linear-gradient(90deg,#818cf8,#38bdf8);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;font-weight:600;margin-bottom:7px">{label}</div>
        <div style="font-size:26px;font-weight:800;color:#e2e8f0;letter-spacing:-0.5px">{title}</div>
        <div style="width:32px;height:3px;background:linear-gradient(90deg,#818cf8,#38bdf8);border-radius:2px;margin-top:9px"></div>
    </div>"""

def trad_card(name, signals, subtitle=""):
    r, c, v = signals["risk"], signals["confidence"], signals["volatility"]
    st_v, sg = signals["stability"], signals["signal_strength"]

    def bar(val, color):
        return f"""<div style="height:6px;background:rgba(255,255,255,0.05);border-radius:3px;margin-top:3px">
            <div style="height:100%;width:{val*100:.0f}%;background:{color};border-radius:3px"></div></div>"""

    sub_html = f'<div style="font-size:11px;color:#475569;font-family:JetBrains Mono,monospace;margin-bottom:4px">{subtitle}</div>' if subtitle else ""

    return f"""
    <div style="background:rgba(12,18,32,0.88);border:1px solid rgba(255,255,255,0.07);
                border-radius:18px;padding:20px 22px;margin-bottom:14px;height:100%">
        {sub_html}
        <div style="font-size:17px;font-weight:700;color:#e2e8f0;margin-bottom:14px">{name}</div>
        <div style="font-size:11px;color:#475569;font-family:'JetBrains Mono',monospace;margin-bottom:12px">TRADITIONAL VIEW</div>
        {"".join(f'''
        <div style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b">
                <span>{lbl}</span><span style="color:#94a3b8;font-family:JetBrains Mono,monospace">{val:.0%}</span>
            </div>
            {bar(val, color)}
        </div>''' for lbl, val, color in [
            ("Confidence",     c,  "#818cf8"),
            ("Risk Score",     r,  "#f87171"),
            ("Volatility",     v,  "#94a3b8"),
            ("Trend Stability",st_v,"#38bdf8"),
            ("Signal Strength",sg, "#a78bfa"),
        ])}
    </div>"""


# ══════════════════════════════════════════════════════════════════════════════
# NAV
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="position:sticky;top:0;z-index:1000;background:rgba(3,5,10,0.90);
            backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,0.05);
            padding:13px 2.5rem;display:flex;justify-content:space-between;align-items:center;
            margin:0 -2.5rem">
    <div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;
                     background:linear-gradient(135deg,#818cf8,#38bdf8);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                     background-clip:text">Feel-the-Model™</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#1e293b;margin-left:12px">
            by Between 0 and 1™</span>
    </div>
    <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#334155;letter-spacing:1px">
        NEUROAESTHETIC TRANSLATION LAYER v0.2</span>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="padding:52px 0 18px;border-bottom:1px solid rgba(255,255,255,0.04);margin-bottom:6px">
    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;
                background:linear-gradient(90deg,#818cf8,#38bdf8);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;margin-bottom:13px">ENTERPRISE INTELLIGENCE</div>
    <div style="font-size:46px;font-weight:800;letter-spacing:-2px;line-height:1.05;margin-bottom:13px;
                background:linear-gradient(135deg,#f8fafc 0%,#e2e8f0 50%,#94a3b8 100%);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">
        Enterprise BI you feel,<br>not just read.</div>
    <div style="font-size:14px;color:#64748b;max-width:540px;line-height:1.85;margin-bottom:20px">
        The Neuroaesthetic Translation Layer converts confidence, risk, volatility, and stability
        into color, gradient, blur, and motion. Executives understand data before reading a single number.
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
        <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,0.08);
                     border:1px solid rgba(129,140,248,0.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
            Confidence → Color Saturation</span>
        <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,0.08);
                     border:1px solid rgba(129,140,248,0.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
            Risk → Hue</span>
        <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,0.08);
                     border:1px solid rgba(129,140,248,0.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
            Uncertainty → Blur</span>
        <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,0.08);
                     border:1px solid rgba(129,140,248,0.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
            Stability → Symmetry</span>
        <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,0.08);
                     border:1px solid rgba(129,140,248,0.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
            Signal Strength → Brightness</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE SELECTOR
# ══════════════════════════════════════════════════════════════════════════════
col_mode, col_opt = st.columns([3, 1])
with col_mode:
    mode = st.radio("View", ["Single Asset", "Live Market Data", "Portfolio View", "A/B Demo"],
                    horizontal=True, label_visibility="collapsed")
with col_opt:
    show_numbers = st.toggle("Show Numbers", value=False)

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 1 — SINGLE ASSET (SLIDERS)
# ══════════════════════════════════════════════════════════════════════════════
if mode == "Single Asset":
    st.markdown(sec_header("SIGNAL INPUT", "Model Parameters"), unsafe_allow_html=True)
    col_in, col_out = st.columns([1, 1], gap="large")
    with col_in:
        asset_name      = st.text_input("Asset / Metric Label", "Portfolio Alpha")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        confidence      = st.slider("Confidence",      0.0, 1.0, 0.72, 0.01)
        risk            = st.slider("Risk Score",      0.0, 1.0, 0.30, 0.01)
        volatility      = st.slider("Volatility",      0.0, 1.0, 0.25, 0.01)
        stability       = st.slider("Trend Stability", 0.0, 1.0, 0.70, 0.01)
        signal_strength = st.slider("Signal Strength", 0.0, 1.0, 0.80, 0.01)
    with col_out:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        signals = {"confidence": confidence, "risk": risk, "volatility": volatility,
                   "stability": stability, "signal_strength": signal_strength}
        st.markdown(ntl_card(asset_name, signals, show_numbers=show_numbers, size="large"),
                    unsafe_allow_html=True)
        if show_numbers:
            st.markdown(f"""
            <div style="background:rgba(12,18,32,0.5);border:1px solid rgba(255,255,255,0.05);
                        border-radius:12px;padding:14px 18px;font-family:'JetBrains Mono',monospace;font-size:11px">
                <div style="color:#334155;font-size:9px;letter-spacing:2px;margin-bottom:9px">TRADITIONAL VIEW</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;color:#64748b">
                    <span>Confidence: <b style="color:#94a3b8">{confidence:.0%}</b></span>
                    <span>Risk: <b style="color:#94a3b8">{risk:.0%}</b></span>
                    <span>Volatility: <b style="color:#94a3b8">{volatility:.0%}</b></span>
                    <span>Stability: <b style="color:#94a3b8">{stability:.0%}</b></span>
                    <span>Signal: <b style="color:#94a3b8">{signal_strength:.0%}</b></span>
                </div>
                <div style="margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.04);
                            font-size:9px;color:#1e293b">Which helped you understand faster? That's the NTL.</div>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 2 — LIVE MARKET DATA
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "Live Market Data":
    st.markdown(sec_header("LIVE DATA", "Real Market Signals via yfinance"), unsafe_allow_html=True)

    col_t, col_b = st.columns([3, 1])
    with col_t:
        tickers_input = st.text_input(
            "Enter ticker(s)",
            "AAPL, MSFT, NVDA, SPY",
            help="Comma-separated. E.g.: AAPL, MSFT, TSLA, SPY"
        )
    with col_b:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        refresh = st.button("Refresh Data")

    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

    if tickers:
        with st.spinner("Fetching live signals..."):
            results = {t: fetch_ticker_signals(t) for t in tickers}

        valid   = {t: r for t, r in results.items() if r}
        invalid = [t for t, r in results.items() if not r]

        if invalid:
            st.markdown(f"""
            <div style="background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.2);
                        border-radius:10px;padding:10px 16px;font-size:12px;color:#f87171;
                        font-family:'JetBrains Mono',monospace;margin-bottom:12px">
                Could not fetch: {', '.join(invalid)} — check tickers or try again
            </div>""", unsafe_allow_html=True)

        if valid:
            # Portfolio banner
            all_s = [{"confidence": r["confidence"], "risk": r["risk"],
                       "volatility": r["volatility"], "stability": r["stability"],
                       "signal_strength": r["signal_strength"]} for r in valid.values()]
            st.markdown(portfolio_banner(portfolio_agg(all_s)), unsafe_allow_html=True)

            # Cards grid
            ticker_list = list(valid.items())
            for row_start in range(0, len(ticker_list), 3):
                row  = ticker_list[row_start:row_start+3]
                cols = st.columns(len(row))
                for col, (ticker, r) in zip(cols, row):
                    with col:
                        signals = {"confidence": r["confidence"], "risk": r["risk"],
                                   "volatility": r["volatility"], "stability": r["stability"],
                                   "signal_strength": r["signal_strength"]}
                        chg_sign = "+" if r["change_pct"] >= 0 else ""
                        subtitle = f"${r['price']:.2f}  {chg_sign}{r['change_pct']:.2f}%  ·  {r['name']}"
                        st.markdown(
                            ntl_card(ticker, signals, subtitle=subtitle, show_numbers=show_numbers),
                            unsafe_allow_html=True
                        )

        st.markdown("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#1e293b;
                    text-align:right;margin-top:8px">
            Data via yfinance · 5-min cache · 3-month window</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 3 — PORTFOLIO VIEW (CSV)
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "Portfolio View":
    st.markdown(sec_header("PORTFOLIO INPUT", "Upload Your Signals"), unsafe_allow_html=True)

    sample_df = pd.DataFrame({
        "name":            ["Portfolio Alpha","AAPL Position","Fixed Income","Tech Growth","EM Equities"],
        "confidence":      [0.82, 0.65, 0.91, 0.55, 0.48],
        "risk":            [0.25, 0.48, 0.12, 0.72, 0.65],
        "volatility":      [0.30, 0.55, 0.18, 0.68, 0.75],
        "stability":       [0.75, 0.42, 0.88, 0.35, 0.28],
        "signal_strength": [0.80, 0.60, 0.70, 0.45, 0.40],
    })

    col_up, col_dl = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader(
            "CSV: name, confidence, risk, volatility, stability, signal_strength",
            type=["csv"], label_visibility="visible")
    with col_dl:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        st.download_button("⬡ Sample CSV", sample_df.to_csv(index=False).encode(),
                           "feel_the_model_sample.csv", "text/csv")

    df = pd.read_csv(uploaded) if uploaded else sample_df

    all_signals = []
    for _, row in df.iterrows():
        s = {k: clamp(row.get(k, 0.5)) for k in
             ["confidence","risk","volatility","stability","signal_strength"]}
        all_signals.append(s)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown(portfolio_banner(portfolio_agg(all_signals)), unsafe_allow_html=True)
    st.markdown(sec_header("ASSET SIGNALS", "Neuroaesthetic Readout"), unsafe_allow_html=True)

    names = list(df.get("name", pd.Series([f"Asset {i+1}" for i in range(len(df))])))
    for row_start in range(0, len(names), 3):
        row_names   = names[row_start:row_start+3]
        row_signals = all_signals[row_start:row_start+3]
        cols        = st.columns(len(row_names))
        for col, name, signals in zip(cols, row_names, row_signals):
            with col:
                st.markdown(ntl_card(name, signals, show_numbers=show_numbers),
                            unsafe_allow_html=True)

    with st.expander("Raw data"):
        st.dataframe(df, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 4 — A/B DEMO
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "A/B Demo":

    SCENARIOS = [
        {"name": "High-Risk EM Position",
         "confidence": 0.42, "risk": 0.80, "volatility": 0.75, "stability": 0.25, "signal_strength": 0.40,
         "context": "Emerging market equity with geopolitical exposure."},
        {"name": "Safe Harbor Bond",
         "confidence": 0.93, "risk": 0.08, "volatility": 0.12, "stability": 0.90, "signal_strength": 0.72,
         "context": "Investment-grade fixed income, 2-year duration."},
        {"name": "Growth Tech Momentum",
         "confidence": 0.68, "risk": 0.55, "volatility": 0.62, "stability": 0.48, "signal_strength": 0.85,
         "context": "Large-cap tech position on earnings run-up."},
        {"name": "Portfolio Alpha",
         "confidence": 0.82, "risk": 0.22, "volatility": 0.28, "stability": 0.78, "signal_strength": 0.80,
         "context": "Diversified equity strategy with positive alpha signal."},
        {"name": "Distressed Credit",
         "confidence": 0.35, "risk": 0.88, "volatility": 0.82, "stability": 0.18, "signal_strength": 0.30,
         "context": "High-yield credit approaching covenant breach threshold."},
    ]

    st.session_state.setdefault("ab_idx", 0)
    st.session_state.setdefault("ab_votes", {"NTL": 0, "Traditional": 0})
    st.session_state.setdefault("ab_history", [])

    idx      = st.session_state["ab_idx"] % len(SCENARIOS)
    scenario = SCENARIOS[idx]
    signals  = {k: scenario[k] for k in ["confidence","risk","volatility","stability","signal_strength"]}

    st.markdown(sec_header("A/B DEMO", "Which view helps you understand faster?"), unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:rgba(12,18,32,0.6);border:1px solid rgba(255,255,255,0.06);
                border-radius:12px;padding:14px 20px;margin-bottom:18px;
                font-family:'JetBrains Mono',monospace">
        <span style="font-size:9px;color:#475569;letter-spacing:2px">SCENARIO {idx+1} OF {len(SCENARIOS)}  ·  </span>
        <span style="font-size:11px;color:#94a3b8">{scenario['context']}</span>
    </div>""", unsafe_allow_html=True)

    col_trad, col_ntl = st.columns(2, gap="large")

    with col_trad:
        st.markdown("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;
                    color:#475569;margin-bottom:10px;text-align:center">← TRADITIONAL VIEW</div>""",
                    unsafe_allow_html=True)
        st.markdown(trad_card(scenario["name"], signals), unsafe_allow_html=True)
        if st.button("This helped me faster  ←", key="vote_trad"):
            st.session_state["ab_votes"]["Traditional"] += 1
            st.session_state["ab_history"].append({"scenario": scenario["name"], "winner": "Traditional"})
            st.session_state["ab_idx"] += 1
            st.rerun()

    with col_ntl:
        st.markdown("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:2px;
                    color:#818cf8;margin-bottom:10px;text-align:center">NTL VIEW →</div>""",
                    unsafe_allow_html=True)
        st.markdown(ntl_card(scenario["name"], signals, show_numbers=False), unsafe_allow_html=True)
        if st.button("→  This helped me faster", key="vote_ntl"):
            st.session_state["ab_votes"]["NTL"] += 1
            st.session_state["ab_history"].append({"scenario": scenario["name"], "winner": "NTL"})
            st.session_state["ab_idx"] += 1
            st.rerun()

    # Results so far
    votes = st.session_state["ab_votes"]
    total = votes["NTL"] + votes["Traditional"]
    if total > 0:
        ntl_pct  = votes["NTL"] / total * 100
        trad_pct = votes["Traditional"] / total * 100
        st.markdown(f"""
        <div style="background:rgba(12,18,32,0.5);border:1px solid rgba(255,255,255,0.05);
                    border-radius:14px;padding:18px 22px;margin-top:8px">
            <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#475569;
                        letter-spacing:2px;margin-bottom:14px">RUNNING RESULTS  ·  {total} RESPONSES</div>
            <div style="display:flex;gap:16px;align-items:center">
                <div style="flex:1">
                    <div style="font-size:11px;color:#64748b;margin-bottom:6px">NTL</div>
                    <div style="height:6px;background:rgba(255,255,255,0.05);border-radius:3px">
                        <div style="height:100%;width:{ntl_pct:.0f}%;background:linear-gradient(90deg,#818cf8,#38bdf8);border-radius:3px"></div></div>
                    <div style="font-size:18px;font-weight:700;color:#818cf8;margin-top:6px">{ntl_pct:.0f}%</div>
                </div>
                <div style="flex:1">
                    <div style="font-size:11px;color:#64748b;margin-bottom:6px">Traditional</div>
                    <div style="height:6px;background:rgba(255,255,255,0.05);border-radius:3px">
                        <div style="height:100%;width:{trad_pct:.0f}%;background:#334155;border-radius:3px"></div></div>
                    <div style="font-size:18px;font-weight:700;color:#475569;margin-top:6px">{trad_pct:.0f}%</div>
                </div>
            </div>
            {'<div style="margin-top:12px;font-size:11px;color:#818cf8;font-family:JetBrains Mono,monospace">NTL is winning your personal validation experiment.</div>' if votes["NTL"] > votes["Traditional"] else ''}
        </div>""", unsafe_allow_html=True)

    if st.button("Reset experiment"):
        st.session_state["ab_votes"]   = {"NTL": 0, "Traditional": 0}
        st.session_state["ab_history"] = []
        st.session_state["ab_idx"]     = 0
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# NTL LEGEND (always visible)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(sec_header("HOW IT WORKS", "The NTL Mapping"), unsafe_allow_html=True)

mappings = [
    ("Confidence", "Color Saturation", "Vivid = certain. Muted = model is unsure.",       "#818cf8"),
    ("Risk Score", "Hue",              "Blue-green (calm 195°) → Red (danger 0°).",        "#f87171"),
    ("Volatility", "Blur",             "Sharp edges = clear signal. Blur = ambiguity.",    "#94a3b8"),
    ("Stability",  "Gradient Angle",   "Balanced diagonal = stable. Skewed = tension.",    "#38bdf8"),
    ("Signal Str", "Brightness",       "Brighter = more actionable. Dim = weak signal.",   "#a78bfa"),
]
cols = st.columns(5)
for col, (inp, out, desc, color) in zip(cols, mappings):
    col.markdown(f"""
    <div style="background:rgba(12,18,32,0.6);border:1px solid rgba(255,255,255,0.06);
                border-radius:14px;padding:16px;height:100%;
                transition:border-color 0.3s,transform 0.3s"
    onmouseover="this.style.borderColor='{color}55';this.style.transform='translateY(-3px)'"
    onmouseout="this.style.borderColor='rgba(255,255,255,0.06)';this.style.transform='translateY(0)'">
        <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:{color};
                    letter-spacing:1.5px;margin-bottom:8px">INPUT</div>
        <div style="font-size:13px;font-weight:700;color:#e2e8f0;margin-bottom:5px">{inp}</div>
        <div style="font-size:11px;color:#334155;margin-bottom:8px">→</div>
        <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:{color};
                    letter-spacing:1.5px;margin-bottom:6px">OUTPUT</div>
        <div style="font-size:12px;font-weight:600;color:#94a3b8;margin-bottom:8px">{out}</div>
        <div style="font-size:10px;color:#475569;line-height:1.6">{desc}</div>
    </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:36px 0 24px;border-top:1px solid rgba(255,255,255,0.04);margin-top:36px">
    <div style="font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;
                background:linear-gradient(135deg,#818cf8,#38bdf8);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;margin-bottom:7px">BETWEEN 0 AND 1™</div>
    <div style="font-size:10px;color:#1e293b;font-family:'JetBrains Mono',monospace">
        NEUROAESTHETIC TRANSLATION LAYER · FEEL-THE-MODEL™ · v0.2</div>
</div>""", unsafe_allow_html=True)
