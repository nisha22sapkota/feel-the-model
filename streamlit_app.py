import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from scipy import stats

st.set_page_config(
    page_title="Feel-the-Model™ | Between 0 and 1",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS — must use st.markdown to inject into the main page ────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root {
  --bg:#03050a; --card:#0c1220; --text:#e2e8f0;
  --muted:#64748b; --subtle:#94a3b8;
  --indigo:#818cf8; --sky:#38bdf8;
}
*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background-color:#03050a!important;color:#e2e8f0!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stAppViewContainer"]{background:#03050a!important}
[data-testid="stMainBlockContainer"]{padding:0 2.5rem!important;max-width:1200px!important}
section[data-testid="stSidebar"]{display:none}
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-thumb{background:#1e293b;border-radius:4px}
label[data-testid="stWidgetLabel"] p{
  font-family:'JetBrains Mono',monospace!important;font-size:11px!important;
  color:#64748b!important;letter-spacing:.08em;text-transform:uppercase}
[data-testid="stTextInput"] input{
  background:rgba(12,18,32,.8)!important;border:1px solid rgba(255,255,255,.1)!important;
  color:#e2e8f0!important;border-radius:10px!important;
  font-family:'JetBrains Mono',monospace!important;font-size:13px!important}
[data-testid="stFileUploader"]{
  background:rgba(12,18,32,.6)!important;border:1px solid rgba(255,255,255,.07)!important;
  border-radius:14px!important}
[data-testid="stDownloadButton"] button{
  background:rgba(129,140,248,.08)!important;border:1px solid rgba(129,140,248,.2)!important;
  color:#a5b4fc!important;font-family:'JetBrains Mono',monospace!important;
  font-size:11px!important;border-radius:8px!important}
[data-testid="stButton"] button{
  background:linear-gradient(135deg,rgba(129,140,248,.12),rgba(56,189,248,.08))!important;
  border:1px solid rgba(129,140,248,.25)!important;color:#a5b4fc!important;
  font-family:'JetBrains Mono',monospace!important;font-size:12px!important;border-radius:10px!important}
hr{border-color:rgba(255,255,255,.05)!important}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NTL CORE
# ══════════════════════════════════════════════════════════════════════════════

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))

def ntl_params(s):
    return {
        "hue":   195.0 - s["risk"] * 195.0,
        "sat":   0.15  + s["confidence"] * 0.65,
        "light": 0.32  + s["signal_strength"] * 0.22,
        "blur":  s["volatility"] * 10.0,
        "angle": 135.0 + (1.0 - s["stability"]) * 45.0,
    }

def hsl(h, s, l):
    return f"hsl({h:.0f},{s*100:.0f}%,{l*100:.0f}%)"

def colors(p):
    h, s, l = p["hue"], p["sat"], p["light"]
    return hsl(h, s, l), hsl(h+28, s*.55, l*.80), hsl(h-18, s*.35, l*1.15), hsl(h, s*.6, l*1.3)

def neuro_label(s):
    r, c, v = s["risk"], s["confidence"], s["volatility"]
    if r > .72 and c < .40: return "⚡ High tension — move with caution"
    if r > .55 and c > .65: return "⚠ Elevated risk — signal is clear"
    if r < .25 and c > .72: return "● Calm and confident — strong position"
    if v > .65:              return "〜 High uncertainty — hold and observe"
    if c > .82:              return "◉ Strong signal — low noise"
    if r < .35 and v < .35: return "◦ Stable — continue monitoring"
    return "∿ Mixed signal — seek confirmation"

def neuro_state(s):
    r, c, v = s["risk"], s["confidence"], s["volatility"]
    if r > .65:              return "TENSION"
    if c > .78 and r < .3:  return "CONFIDENCE"
    if v > .60:              return "UNCERTAINTY"
    if c > .70 and v < .3:  return "CLARITY"
    if r < .25 and v < .25: return "CALM"
    return "EQUILIBRIUM"

def agg(rows):
    return {k: float(np.mean([r[k] for r in rows]))
            for k in ["confidence","risk","volatility","stability","signal_strength"]}


# ══════════════════════════════════════════════════════════════════════════════
# LIVE DATA
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def fetch(ticker):
    try:
        hist = yf.Ticker(ticker.upper()).history(period="3mo")
        if hist.empty or len(hist) < 10:
            return None
        prices  = hist["Close"].values.astype(float)
        volumes = hist["Volume"].values.astype(float)
        returns = np.diff(prices) / (prices[:-1] + 1e-8)
        w = min(30, len(prices))
        _, _, r_val, _, _ = stats.linregress(np.arange(w), prices[-w:])
        daily_vol  = float(np.std(returns)) if len(returns) > 1 else .01
        short_vol  = float(np.std(returns[-5:])) if len(returns) >= 5 else daily_vol
        ac = float(np.corrcoef(returns[:-1], returns[1:])[0,1]) if len(returns) > 5 else 0.0
        avg_vol = float(np.mean(volumes[-30:])) + 1e-8
        info = yf.Ticker(ticker.upper()).info
        return {
            "ticker": ticker.upper(),
            "name":   info.get("shortName", ticker.upper()),
            "price":  float(prices[-1]),
            "chg":    float((prices[-1]-prices[-2])/(prices[-2]+1e-8)*100) if len(prices)>1 else 0.0,
            "confidence":      clamp(abs(r_val)),
            "risk":            clamp(daily_vol * 252**.5 / .80),
            "volatility":      clamp(short_vol / (daily_vol + 1e-8) * .65),
            "stability":       clamp((ac + 1.0) / 2.0),
            "signal_strength": clamp(min(float(np.mean(volumes[-5:])) / avg_vol, 2.0) / 2.0),
        }
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# HTML COMPONENTS  — all use st.html(), never st.markdown()
# ══════════════════════════════════════════════════════════════════════════════

def ntl_card_html(name, s, subtitle="", show_numbers=False, large=False):
    p           = ntl_params(s)
    c1,c2,c3,bc = colors(p)
    label       = neuro_label(s)
    state       = neuro_state(s)
    grad_h      = "160px" if large else "110px"

    signal_defs = [
        ("CONF", "confidence",      "#818cf8"),
        ("RISK", "risk",            c1),
        ("VOL",  "volatility",      "#94a3b8"),
        ("STAB", "stability",       "#38bdf8"),
        ("SIG",  "signal_strength", "#a78bfa"),
    ]
    dots = ""
    for k, key, color in signal_defs:
        v = s[key]
        h_px = int(v * 28) + 4
        num_html = f'<div style="font-size:9px;font-family:JetBrains Mono,monospace;color:#475569">{v:.0%}</div>' if show_numbers else ""
        dots += f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px">
            <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:#334155">{k}</div>
            <div style="width:5px;height:{h_px}px;border-radius:3px;background:{color};opacity:{0.35+v*0.65:.2f}"></div>
            {num_html}
        </div>"""

    sub = f'<div style="font-size:11px;color:#475569;font-family:JetBrains Mono,monospace;margin-bottom:4px">{subtitle}</div>' if subtitle else ""

    return f"""
<div style="background:rgba(12,18,32,.88);border:1px solid {bc};border-radius:18px;overflow:hidden;
            margin-bottom:14px;backdrop-filter:blur(12px)">
  <div style="position:relative;height:{grad_h};overflow:hidden">
    <div style="position:absolute;inset:-4px;
                background:linear-gradient({p['angle']:.0f}deg,{c1},{c2},{c3});
                filter:blur({p['blur']:.1f}px);transform:scale(1.05)"></div>
    <div style="position:absolute;top:10px;left:14px;font-family:'JetBrains Mono',monospace;
                font-size:9px;letter-spacing:2px;background:rgba(3,5,10,.55);
                backdrop-filter:blur(8px);padding:3px 10px;border-radius:20px;
                color:rgba(255,255,255,.6)">BETWEEN 0 AND 1 · NTL</div>
    <div style="position:absolute;bottom:10px;right:12px;font-family:'JetBrains Mono',monospace;
                font-size:10px;letter-spacing:2px;font-weight:700;
                background:rgba(3,5,10,.65);backdrop-filter:blur(8px);
                padding:4px 12px;border-radius:20px;color:{c1}">{state}</div>
  </div>
  <div style="padding:16px 20px 14px">
    {sub}
    <div style="font-size:17px;font-weight:700;color:#e2e8f0;margin-bottom:5px">{name}</div>
    <div style="font-size:11px;color:#64748b;margin-bottom:14px;font-family:'JetBrains Mono',monospace">{label}</div>
    <div style="display:flex;gap:9px;align-items:flex-end;padding:10px 0 6px;border-top:1px solid rgba(255,255,255,.04)">
      {dots}
      <div style="flex:1"></div>
      <div style="font-size:9px;color:#1e293b;font-family:'JetBrains Mono',monospace;text-align:right">
        HUE {p['hue']:.0f} · SAT {p['sat']:.0%} · BLUR {p['blur']:.1f}px
      </div>
    </div>
  </div>
</div>"""

def portfolio_banner_html(s):
    p           = ntl_params(s)
    c1,c2,c3,_  = colors(p)
    return f"""
<div style="position:relative;border-radius:20px;overflow:hidden;margin-bottom:24px;
            border:1px solid rgba(255,255,255,.06)">
  <div style="position:absolute;inset:-4px;
              background:linear-gradient({p['angle']:.0f}deg,{c1},{c2},{c3});
              filter:blur({p['blur']:.1f}px);opacity:.16;transform:scale(1.04)"></div>
  <div style="position:relative;background:rgba(8,13,23,.88);backdrop-filter:blur(20px);padding:28px 32px">
    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;
                background:linear-gradient(90deg,{c1},{c2});
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;font-weight:600;margin-bottom:8px">PORTFOLIO NEUROAESTHETIC STATE</div>
    <div style="font-size:30px;font-weight:800;color:#e2e8f0;letter-spacing:-1px;margin-bottom:6px">{neuro_state(s)}</div>
    <div style="font-size:12px;color:#64748b;font-family:'JetBrains Mono',monospace">{neuro_label(s)}</div>
  </div>
</div>"""

def sec_header_html(label, title):
    return f"""
<div style="padding:28px 0 14px">
  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;
              background:linear-gradient(90deg,#818cf8,#38bdf8);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text;font-weight:600;margin-bottom:7px">{label}</div>
  <div style="font-size:26px;font-weight:800;color:#e2e8f0;letter-spacing:-.5px">{title}</div>
  <div style="width:32px;height:3px;background:linear-gradient(90deg,#818cf8,#38bdf8);border-radius:2px;margin-top:9px"></div>
</div>"""

def trad_card_html(name, s, subtitle=""):
    sub = f'<div style="font-size:11px;color:#475569;font-family:JetBrains Mono,monospace;margin-bottom:4px">{subtitle}</div>' if subtitle else ""
    rows_html = ""
    for lbl, key, color in [
        ("Confidence",     "confidence",      "#818cf8"),
        ("Risk Score",     "risk",            "#f87171"),
        ("Volatility",     "volatility",      "#94a3b8"),
        ("Trend Stability","stability",       "#38bdf8"),
        ("Signal Strength","signal_strength", "#a78bfa"),
    ]:
        v = s[key]
        rows_html += f"""
        <div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b">
            <span>{lbl}</span>
            <span style="color:#94a3b8;font-family:JetBrains Mono,monospace">{v:.0%}</span>
          </div>
          <div style="height:6px;background:rgba(255,255,255,.05);border-radius:3px;margin-top:3px">
            <div style="height:100%;width:{v*100:.0f}%;background:{color};border-radius:3px"></div>
          </div>
        </div>"""
    return f"""
<div style="background:rgba(12,18,32,.88);border:1px solid rgba(255,255,255,.07);
            border-radius:18px;padding:20px 22px;margin-bottom:14px">
  {sub}
  <div style="font-size:17px;font-weight:700;color:#e2e8f0;margin-bottom:14px">{name}</div>
  <div style="font-size:11px;color:#475569;font-family:'JetBrains Mono',monospace;margin-bottom:12px">TRADITIONAL VIEW</div>
  {rows_html}
</div>"""


# ══════════════════════════════════════════════════════════════════════════════
# NAV
# ══════════════════════════════════════════════════════════════════════════════
st.html("""
<div style="position:sticky;top:0;z-index:1000;background:rgba(3,5,10,.92);
            backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.05);
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
""")

# ══════════════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════════════
st.html("""
<div style="padding:52px 0 18px;border-bottom:1px solid rgba(255,255,255,.04);margin-bottom:6px">
  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;
              background:linear-gradient(90deg,#818cf8,#38bdf8);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text;margin-bottom:13px">ENTERPRISE INTELLIGENCE</div>
  <div style="font-size:42px;font-weight:800;letter-spacing:-2px;line-height:1.05;margin-bottom:13px;
              background:linear-gradient(135deg,#f8fafc 0%,#e2e8f0 50%,#94a3b8 100%);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">
    Enterprise BI you feel,<br>not just read.</div>
  <div style="font-size:14px;color:#64748b;max-width:540px;line-height:1.85;margin-bottom:20px">
    The Neuroaesthetic Translation Layer converts confidence, risk, volatility, and stability
    into color, gradient, blur, and motion. Executives understand data before reading a number.
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,.08);
                 border:1px solid rgba(129,140,248,.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
      Confidence → Saturation</span>
    <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,.08);
                 border:1px solid rgba(129,140,248,.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
      Risk → Hue</span>
    <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,.08);
                 border:1px solid rgba(129,140,248,.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
      Uncertainty → Blur</span>
    <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,.08);
                 border:1px solid rgba(129,140,248,.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
      Stability → Symmetry</span>
    <span style="font-size:10px;font-family:'JetBrains Mono',monospace;background:rgba(129,140,248,.08);
                 border:1px solid rgba(129,140,248,.2);color:#a5b4fc;padding:4px 12px;border-radius:20px">
      Signal → Brightness</span>
  </div>
</div>
""")

# ══════════════════════════════════════════════════════════════════════════════
# MODE SELECTOR
# ══════════════════════════════════════════════════════════════════════════════
col_mode, col_opt = st.columns([3, 1])
with col_mode:
    mode = st.radio("View", ["Single Asset", "Live Market Data", "Portfolio View", "A/B Demo"],
                    horizontal=True, label_visibility="collapsed")
with col_opt:
    show_numbers = st.toggle("Show Numbers", value=False)

st.html("<div style='height:6px'></div>")


# ══════════════════════════════════════════════════════════════════════════════
# MODE 1 — SINGLE ASSET
# ══════════════════════════════════════════════════════════════════════════════
if mode == "Single Asset":
    st.html(sec_header_html("SIGNAL INPUT", "Model Parameters"))
    col_in, col_out = st.columns(2, gap="large")
    with col_in:
        name_in         = st.text_input("Asset / Metric Label", "Portfolio Alpha")
        confidence      = st.slider("Confidence",      0.0, 1.0, 0.72, 0.01)
        risk            = st.slider("Risk Score",      0.0, 1.0, 0.30, 0.01)
        volatility      = st.slider("Volatility",      0.0, 1.0, 0.25, 0.01)
        stability       = st.slider("Trend Stability", 0.0, 1.0, 0.70, 0.01)
        signal_strength = st.slider("Signal Strength", 0.0, 1.0, 0.80, 0.01)
    with col_out:
        s = {"confidence": confidence, "risk": risk, "volatility": volatility,
             "stability": stability, "signal_strength": signal_strength}
        st.html(ntl_card_html(name_in, s, show_numbers=show_numbers, large=True))
        if show_numbers:
            st.html(f"""
            <div style="background:rgba(12,18,32,.5);border:1px solid rgba(255,255,255,.05);
                        border-radius:12px;padding:14px 18px;font-family:'JetBrains Mono',monospace;font-size:11px">
              <div style="color:#334155;font-size:9px;letter-spacing:2px;margin-bottom:9px">TRADITIONAL VIEW</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;color:#64748b">
                <span>Confidence: <b style="color:#94a3b8">{confidence:.0%}</b></span>
                <span>Risk: <b style="color:#94a3b8">{risk:.0%}</b></span>
                <span>Volatility: <b style="color:#94a3b8">{volatility:.0%}</b></span>
                <span>Stability: <b style="color:#94a3b8">{stability:.0%}</b></span>
                <span>Signal: <b style="color:#94a3b8">{signal_strength:.0%}</b></span>
              </div>
              <div style="margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,.04);
                          font-size:9px;color:#1e293b">Which helped you understand faster? That is the NTL.</div>
            </div>""")


# ══════════════════════════════════════════════════════════════════════════════
# MODE 2 — LIVE MARKET DATA
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "Live Market Data":
    st.html(sec_header_html("LIVE DATA", "Real Market Signals via yfinance"))
    col_t, col_b = st.columns([3, 1])
    with col_t:
        tickers_input = st.text_input("Tickers (comma-separated)", "AAPL, MSFT, NVDA, SPY")
    with col_b:
        st.html("<div style='height:28px'></div>")
        st.button("Refresh")

    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]
    if tickers:
        with st.spinner("Fetching live signals..."):
            results = {t: fetch(t) for t in tickers}
        valid   = {t: r for t, r in results.items() if r}
        invalid = [t for t, r in results.items() if not r]

        if invalid:
            st.html(f"""
            <div style="background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.2);
                        border-radius:10px;padding:10px 16px;font-size:12px;color:#f87171;
                        font-family:'JetBrains Mono',monospace;margin-bottom:12px">
              Could not fetch: {', '.join(invalid)}
            </div>""")

        if valid:
            all_s = [{"confidence": r["confidence"], "risk": r["risk"], "volatility": r["volatility"],
                      "stability": r["stability"], "signal_strength": r["signal_strength"]}
                     for r in valid.values()]
            st.html(portfolio_banner_html(agg(all_s)))

            ticker_list = list(valid.items())
            for i in range(0, len(ticker_list), 3):
                row  = ticker_list[i:i+3]
                cols = st.columns(len(row))
                for col, (ticker, r) in zip(cols, row):
                    with col:
                        s = {k: r[k] for k in ["confidence","risk","volatility","stability","signal_strength"]}
                        sign = "+" if r["chg"] >= 0 else ""
                        st.html(ntl_card_html(ticker, s,
                                              subtitle=f"${r['price']:.2f}  {sign}{r['chg']:.2f}%  ·  {r['name']}",
                                              show_numbers=show_numbers))
        st.html("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#1e293b;
                    text-align:right;margin-top:4px">
          Data via yfinance · 5-min cache · 3-month window</div>""")


# ══════════════════════════════════════════════════════════════════════════════
# MODE 3 — PORTFOLIO CSV
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "Portfolio View":
    st.html(sec_header_html("PORTFOLIO INPUT", "Upload Your Signals"))
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
        uploaded = st.file_uploader("CSV: name, confidence, risk, volatility, stability, signal_strength",
                                    type=["csv"], label_visibility="visible")
    with col_dl:
        st.html("<div style='height:28px'></div>")
        st.download_button("Sample CSV", sample_df.to_csv(index=False).encode(),
                           "sample.csv", "text/csv")
    df = pd.read_csv(uploaded) if uploaded else sample_df
    all_signals = [{k: clamp(row.get(k, .5)) for k in
                    ["confidence","risk","volatility","stability","signal_strength"]}
                   for _, row in df.iterrows()]

    st.html(portfolio_banner_html(agg(all_signals)))
    st.html(sec_header_html("ASSET SIGNALS", "Neuroaesthetic Readout"))

    names = list(df.get("name", pd.Series([f"Asset {i+1}" for i in range(len(df))])))
    for i in range(0, len(names), 3):
        row_n = names[i:i+3]
        row_s = all_signals[i:i+3]
        cols  = st.columns(len(row_n))
        for col, name, s in zip(cols, row_n, row_s):
            with col:
                st.html(ntl_card_html(name, s, show_numbers=show_numbers))

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
         "context": "High-yield credit approaching covenant breach."},
    ]
    st.session_state.setdefault("ab_idx",     0)
    st.session_state.setdefault("ab_votes",   {"NTL": 0, "Traditional": 0})
    st.session_state.setdefault("ab_history", [])

    idx      = st.session_state["ab_idx"] % len(SCENARIOS)
    scenario = SCENARIOS[idx]
    s        = {k: scenario[k] for k in ["confidence","risk","volatility","stability","signal_strength"]}

    st.html(sec_header_html("A/B DEMO", "Which view helps you understand faster?"))
    st.html(f"""
    <div style="background:rgba(12,18,32,.6);border:1px solid rgba(255,255,255,.06);
                border-radius:12px;padding:14px 20px;margin-bottom:18px;
                font-family:'JetBrains Mono',monospace">
      <span style="font-size:9px;color:#475569;letter-spacing:2px">
        SCENARIO {idx+1} OF {len(SCENARIOS)}  ·  </span>
      <span style="font-size:11px;color:#94a3b8">{scenario['context']}</span>
    </div>""")

    col_l, col_r = st.columns(2, gap="large")
    with col_l:
        st.html('<div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:2px;color:#475569;margin-bottom:10px;text-align:center">TRADITIONAL VIEW</div>')
        st.html(trad_card_html(scenario["name"], s))
        if st.button("This helped me faster", key="vote_trad"):
            st.session_state["ab_votes"]["Traditional"] += 1
            st.session_state["ab_history"].append({"scenario": scenario["name"], "winner": "Traditional"})
            st.session_state["ab_idx"] += 1
            st.rerun()
    with col_r:
        st.html('<div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:2px;color:#818cf8;margin-bottom:10px;text-align:center">NTL VIEW</div>')
        st.html(ntl_card_html(scenario["name"], s))
        if st.button("This helped me faster", key="vote_ntl"):
            st.session_state["ab_votes"]["NTL"] += 1
            st.session_state["ab_history"].append({"scenario": scenario["name"], "winner": "NTL"})
            st.session_state["ab_idx"] += 1
            st.rerun()

    votes = st.session_state["ab_votes"]
    total = votes["NTL"] + votes["Traditional"]
    if total > 0:
        ntl_pct  = votes["NTL"]          / total * 100
        trad_pct = votes["Traditional"]  / total * 100
        winning  = '<div style="margin-top:10px;font-size:11px;color:#818cf8;font-family:JetBrains Mono,monospace">NTL is winning your personal validation.</div>' if votes["NTL"] > votes["Traditional"] else ""
        st.html(f"""
        <div style="background:rgba(12,18,32,.5);border:1px solid rgba(255,255,255,.05);
                    border-radius:14px;padding:18px 22px;margin-top:8px">
          <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#475569;
                      letter-spacing:2px;margin-bottom:14px">RESULTS · {total} RESPONSES</div>
          <div style="display:flex;gap:20px">
            <div style="flex:1">
              <div style="font-size:11px;color:#64748b;margin-bottom:6px">NTL</div>
              <div style="height:6px;background:rgba(255,255,255,.05);border-radius:3px">
                <div style="height:100%;width:{ntl_pct:.0f}%;background:linear-gradient(90deg,#818cf8,#38bdf8);border-radius:3px"></div>
              </div>
              <div style="font-size:18px;font-weight:700;color:#818cf8;margin-top:6px">{ntl_pct:.0f}%</div>
            </div>
            <div style="flex:1">
              <div style="font-size:11px;color:#64748b;margin-bottom:6px">Traditional</div>
              <div style="height:6px;background:rgba(255,255,255,.05);border-radius:3px">
                <div style="height:100%;width:{trad_pct:.0f}%;background:#334155;border-radius:3px"></div>
              </div>
              <div style="font-size:18px;font-weight:700;color:#475569;margin-top:6px">{trad_pct:.0f}%</div>
            </div>
          </div>
          {winning}
        </div>""")

    if st.button("Reset"):
        st.session_state["ab_votes"]   = {"NTL": 0, "Traditional": 0}
        st.session_state["ab_history"] = []
        st.session_state["ab_idx"]     = 0
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# NTL LEGEND
# ══════════════════════════════════════════════════════════════════════════════
st.html(sec_header_html("HOW IT WORKS", "The NTL Mapping"))
mappings = [
    ("Confidence", "Color Saturation", "Vivid = certain. Muted = unsure.",         "#818cf8"),
    ("Risk Score", "Hue",              "Blue-green (calm) to Red (danger).",        "#f87171"),
    ("Volatility", "Blur",             "Sharp = clear signal. Blur = ambiguity.",   "#94a3b8"),
    ("Stability",  "Gradient Angle",   "Balanced = stable. Skewed = tension.",      "#38bdf8"),
    ("Signal Str", "Brightness",       "Brighter = actionable. Dim = weak.",        "#a78bfa"),
]
cols = st.columns(5)
for col, (inp, out, desc, color) in zip(cols, mappings):
    col.html(f"""
    <div style="background:rgba(12,18,32,.6);border:1px solid rgba(255,255,255,.06);
                border-radius:14px;padding:16px;height:100%">
      <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:{color};
                  letter-spacing:1.5px;margin-bottom:8px">INPUT</div>
      <div style="font-size:13px;font-weight:700;color:#e2e8f0;margin-bottom:5px">{inp}</div>
      <div style="font-size:10px;color:#334155;margin-bottom:8px">→</div>
      <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:{color};
                  letter-spacing:1.5px;margin-bottom:6px">OUTPUT</div>
      <div style="font-size:12px;font-weight:600;color:#94a3b8;margin-bottom:8px">{out}</div>
      <div style="font-size:10px;color:#475569;line-height:1.6">{desc}</div>
    </div>""")

st.html("""
<div style="text-align:center;padding:36px 0 24px;border-top:1px solid rgba(255,255,255,.04);margin-top:36px">
  <div style="font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;
              background:linear-gradient(135deg,#818cf8,#38bdf8);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text;margin-bottom:7px">BETWEEN 0 AND 1</div>
  <div style="font-size:10px;color:#1e293b;font-family:'JetBrains Mono',monospace">
    NEUROAESTHETIC TRANSLATION LAYER · FEEL-THE-MODEL · v0.2</div>
</div>""")
