"""
Between 0 and 1 -- Neuroaesthetic Validation Experiment
Experiment 1: Comprehension + Calibration
Experiment 5: NTL vs Traditional (placebo control)

Run: streamlit run experiment.py --server.port 8503
Data saved to: experiment_data.csv
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import uuid
import os
import json
from datetime import datetime

st.set_page_config(
    page_title="NTL Validation Study",
    page_icon="◉",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root { --bg:#03050a; --surface:#0c1220; --border:rgba(255,255,255,0.07);
        --text:#e2e8f0; --muted:#64748b; --indigo:#818cf8; --sky:#38bdf8; }
*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background-color:var(--bg)!important;color:var(--text)!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stAppViewContainer"]{background:var(--bg)!important}
[data-testid="stMainBlockContainer"]{padding:2rem 2.5rem!important;max-width:780px!important}

[data-testid="stButton"]>button{
  width:100%;padding:12px!important;font-size:14px!important;font-weight:600!important;
  border-radius:12px!important;font-family:'Inter',sans-serif!important;
  transition:all 0.2s!important;}
[data-testid="stRadio"] label{font-size:13px!important;color:var(--muted)!important}
[data-testid="stSlider"] label p{font-family:'JetBrains Mono',monospace!important;font-size:11px!important;color:var(--muted)!important}
[data-testid="stSelectbox"] label p{font-family:'JetBrains Mono',monospace!important;font-size:11px!important;color:var(--muted)!important}
hr{border-color:rgba(255,255,255,0.05)!important}
</style>
""")

# ── Data file ─────────────────────────────────────────────────────────────────
DATA_FILE = "experiment_data.csv"
COLS = [
    "participant_id", "timestamp", "age_range", "role", "dashboard_exp_years",
    "scenario_idx", "scenario_name", "condition",         # NTL or Traditional
    "response_time_sec", "risk_answer", "risk_correct",
    "confidence_rating", "clarity_rating",
    "tlx_mental", "tlx_physical", "tlx_temporal",
    "tlx_performance", "tlx_effort", "tlx_frustration",
    "overall_preference", "notes",
]

def save_row(row: dict):
    df_new = pd.DataFrame([row])
    if os.path.exists(DATA_FILE):
        df_new.to_csv(DATA_FILE, mode="a", header=False, index=False)
    else:
        df_new.to_csv(DATA_FILE, mode="w", header=True, index=False)

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=COLS)

# ── NTL helpers ───────────────────────────────────────────────────────────────
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

def ntl_state(s):
    r, c, v = s["risk"], s["confidence"], s["volatility"]
    if r > .65: return "TENSION"
    if c > .78 and r < .3: return "CONFIDENCE"
    if v > .60: return "UNCERTAINTY"
    if c > .70 and v < .3: return "CLARITY"
    if r < .25 and v < .25: return "CALM"
    return "EQUILIBRIUM"

def ntl_card_html(name, s, large=False):
    p  = ntl_params(s)
    h, sat, l = p["hue"], p["sat"], p["light"]
    c1 = hsl(h, sat, l)
    c2 = hsl(h+28, sat*.55, l*.80)
    c3 = hsl(h-18, sat*.35, l*1.15)
    bc = hsl(h, sat*.6, l*1.3)
    state = ntl_state(s)
    gh = "200px" if large else "140px"

    dots = ""
    for k, key, color in [("CONF","confidence","#818cf8"),("RISK","risk",c1),
                           ("VOL","volatility","#94a3b8"),("STAB","stability","#38bdf8"),
                           ("SIG","signal_strength","#a78bfa")]:
        v = s[key]
        dots += f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px">
          <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:#334155">{k}</div>
          <div style="width:6px;height:{int(v*32)+4}px;border-radius:3px;
                      background:{color};opacity:{0.35+v*0.65:.2f}"></div>
        </div>"""

    return f"""
<div style="background:rgba(12,18,32,.9);border:1px solid {bc};border-radius:16px;overflow:hidden">
  <div style="position:relative;height:{gh};overflow:hidden">
    <div style="position:absolute;inset:-4px;
                background:linear-gradient({p['angle']:.0f}deg,{c1},{c2},{c3});
                filter:blur({p['blur']:.1f}px);transform:scale(1.05)"></div>
    <div style="position:absolute;top:10px;left:14px;font-family:'JetBrains Mono',monospace;
                font-size:9px;letter-spacing:2px;background:rgba(3,5,10,.6);
                backdrop-filter:blur(8px);padding:3px 10px;border-radius:20px;
                color:rgba(255,255,255,.65)">BETWEEN 0 AND 1 - NTL</div>
    <div style="position:absolute;bottom:10px;right:12px;font-family:'JetBrains Mono',monospace;
                font-size:10px;letter-spacing:2px;font-weight:700;
                background:rgba(3,5,10,.7);backdrop-filter:blur(8px);
                padding:4px 12px;border-radius:20px;color:{c1}">{state}</div>
  </div>
  <div style="padding:14px 18px 12px">
    <div style="font-size:15px;font-weight:700;color:#e2e8f0;margin-bottom:12px">{name}</div>
    <div style="display:flex;gap:8px;align-items:flex-end;
                padding:8px 0 4px;border-top:1px solid rgba(255,255,255,.05)">{dots}</div>
  </div>
</div>"""

def trad_card_html(name, s):
    rows = ""
    for lbl, key, color in [
        ("Confidence",     "confidence",      "#818cf8"),
        ("Risk Score",     "risk",            "#f87171"),
        ("Volatility",     "volatility",      "#94a3b8"),
        ("Trend Stability","stability",       "#38bdf8"),
        ("Signal Strength","signal_strength", "#a78bfa"),
    ]:
        v = s[key]
        rows += f"""
        <div style="margin-bottom:9px">
          <div style="display:flex;justify-content:space-between;font-size:12px;color:#64748b;margin-bottom:3px">
            <span>{lbl}</span>
            <span style="font-family:'JetBrains Mono',monospace;color:#94a3b8">{v:.0%}</span>
          </div>
          <div style="height:5px;background:rgba(255,255,255,.06);border-radius:3px">
            <div style="height:100%;width:{v*100:.0f}%;background:{color};border-radius:3px"></div>
          </div>
        </div>"""
    return f"""
<div style="background:rgba(12,18,32,.9);border:1px solid rgba(255,255,255,.08);
            border-radius:16px;padding:18px 20px">
  <div style="font-size:10px;font-family:'JetBrains Mono',monospace;color:#475569;
              letter-spacing:2px;margin-bottom:10px">TRADITIONAL VIEW</div>
  <div style="font-size:15px;font-weight:700;color:#e2e8f0;margin-bottom:14px">{name}</div>
  {rows}
</div>"""

def card_wrap(html, label, color):
    return f"""
<div style="border:1px solid {color}33;border-radius:18px;padding:16px;
            background:rgba(12,18,32,.4)">
  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
              color:{color};letter-spacing:2px;margin-bottom:10px;text-align:center">{label}</div>
  {html}
</div>"""

# ── Scenarios ─────────────────────────────────────────────────────────────────
SCENARIOS = [
    {
        "name":    "EM Equity Position",
        "context": "Emerging market equity with geopolitical exposure and recent currency volatility.",
        "signals": {"confidence": 0.42, "risk": 0.80, "volatility": 0.75, "stability": 0.25, "signal_strength": 0.40},
        "true_risk_level": "High",
        "risk_options": ["Low", "Medium", "High", "Very High"],
        "correct_answer": "High",
    },
    {
        "name":    "US Treasury Bond",
        "context": "2-year duration investment-grade fixed income, held to maturity.",
        "signals": {"confidence": 0.93, "risk": 0.08, "volatility": 0.12, "stability": 0.90, "signal_strength": 0.72},
        "true_risk_level": "Very Low",
        "risk_options": ["Very Low", "Low", "Medium", "High"],
        "correct_answer": "Very Low",
    },
    {
        "name":    "Tech Growth Fund",
        "context": "Large-cap technology equity position, approaching earnings release.",
        "signals": {"confidence": 0.62, "risk": 0.58, "volatility": 0.65, "stability": 0.44, "signal_strength": 0.80},
        "true_risk_level": "Medium-High",
        "risk_options": ["Low", "Medium", "Medium-High", "High"],
        "correct_answer": "Medium-High",
    },
    {
        "name":    "Portfolio Alpha Strategy",
        "context": "Diversified multi-factor equity strategy with consistent historical alpha.",
        "signals": {"confidence": 0.82, "risk": 0.22, "volatility": 0.28, "stability": 0.78, "signal_strength": 0.80},
        "true_risk_level": "Low-Medium",
        "risk_options": ["Very Low", "Low-Medium", "Medium", "High"],
        "correct_answer": "Low-Medium",
    },
    {
        "name":    "Distressed Credit",
        "context": "High-yield corporate bond approaching covenant threshold. Restructuring possible.",
        "signals": {"confidence": 0.32, "risk": 0.90, "volatility": 0.85, "stability": 0.15, "signal_strength": 0.28},
        "true_risk_level": "Very High",
        "risk_options": ["Medium", "High", "Very High", "Extreme"],
        "correct_answer": "Very High",
    },
]

# ── Session state init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "phase":         "consent",     # consent > demographics > instructions > trial > nasa_tlx > preference > done
        "participant_id": str(uuid.uuid4())[:8].upper(),
        "scenario_order": list(np.random.permutation(len(SCENARIOS))),
        "condition_order": [],          # NTL or Traditional per scenario
        "trial_idx":     0,
        "trial_data":    [],
        "trial_start":   None,
        "demographics":  {},
        "view":          "researcher",  # researcher / participant
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # randomize condition per scenario (counterbalanced)
    if not st.session_state["condition_order"]:
        conds = (["NTL", "Traditional"] * 3)[:len(SCENARIOS)]
        np.random.shuffle(conds)
        st.session_state["condition_order"] = conds

init_state()

# ── Sidebar: researcher view toggle ──────────────────────────────────────────
with st.sidebar:
    st.markdown("**Researcher Controls**")
    view = st.radio("Mode", ["Participant", "Results Dashboard"], index=0)
    st.session_state["view"] = view
    if st.button("Reset Session"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# RESULTS DASHBOARD (researcher only)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["view"] == "Results Dashboard":
    st.html("""
    <div style="padding:20px 0 8px">
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;
                  background:linear-gradient(90deg,#818cf8,#38bdf8);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  background-clip:text;margin-bottom:8px">RESEARCHER VIEW</div>
      <div style="font-size:24px;font-weight:800;color:#e2e8f0">Validation Results</div>
    </div>""")

    df = load_data()
    if df.empty:
        st.html("""
        <div style="background:rgba(12,18,32,.6);border:1px solid rgba(255,255,255,.07);
                    border-radius:14px;padding:32px;text-align:center;color:#64748b;
                    font-family:'JetBrains Mono',monospace;font-size:12px">
          No data yet. Run participants through the experiment first.
        </div>""")
    else:
        n_participants = df["participant_id"].nunique()
        n_trials       = len(df)
        ntl_acc  = df[df["condition"]=="NTL"]["risk_correct"].mean()   if "NTL" in df["condition"].values else 0
        trad_acc = df[df["condition"]=="Traditional"]["risk_correct"].mean() if "Traditional" in df["condition"].values else 0
        ntl_rt   = df[df["condition"]=="NTL"]["response_time_sec"].mean()   if "NTL" in df["condition"].values else 0
        trad_rt  = df[df["condition"]=="Traditional"]["response_time_sec"].mean() if "Traditional" in df["condition"].values else 0
        pref_ntl = (df["overall_preference"]=="NTL").sum()
        pref_trad= (df["overall_preference"]=="Traditional").sum()

        # stat cards
        col1, col2, col3, col4 = st.columns(4)
        for col, val, lbl, color in [
            (col1, n_participants,        "Participants",       "#818cf8"),
            (col2, n_trials,              "Total Trials",       "#38bdf8"),
            (col3, f"{ntl_acc:.0%}",      "NTL Accuracy",       "#34d399"),
            (col4, f"{trad_acc:.0%}",     "Traditional Acc.",   "#94a3b8"),
        ]:
            col.html(f"""
            <div style="background:rgba(12,18,32,.7);border:1px solid rgba(255,255,255,.07);
                        border-radius:14px;padding:18px;text-align:center">
              <div style="font-size:26px;font-weight:800;color:{color}">{val}</div>
              <div style="font-size:10px;color:#64748b;font-family:'JetBrains Mono',monospace;
                          margin-top:4px;letter-spacing:1px">{lbl}</div>
            </div>""")

        st.html("<div style='height:12px'></div>")

        # Response time comparison
        col_rt, col_pref = st.columns(2)
        with col_rt:
            st.html(f"""
            <div style="background:rgba(12,18,32,.7);border:1px solid rgba(255,255,255,.07);
                        border-radius:14px;padding:18px">
              <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#475569;
                          letter-spacing:2px;margin-bottom:12px">RESPONSE TIME (sec)</div>
              <div style="display:flex;gap:16px;align-items:flex-end">
                <div>
                  <div style="font-size:22px;font-weight:700;color:#818cf8">{ntl_rt:.1f}s</div>
                  <div style="font-size:10px;color:#64748b">NTL</div>
                </div>
                <div>
                  <div style="font-size:22px;font-weight:700;color:#475569">{trad_rt:.1f}s</div>
                  <div style="font-size:10px;color:#64748b">Traditional</div>
                </div>
                {'<div style="font-size:11px;color:#34d399;margin-left:8px;align-self:center">NTL faster</div>' if ntl_rt < trad_rt and ntl_rt > 0 else ''}
              </div>
            </div>""")

        with col_pref:
            total_pref = pref_ntl + pref_trad
            ntl_pct  = pref_ntl  / total_pref * 100 if total_pref > 0 else 0
            trad_pct = pref_trad / total_pref * 100 if total_pref > 0 else 0
            st.html(f"""
            <div style="background:rgba(12,18,32,.7);border:1px solid rgba(255,255,255,.07);
                        border-radius:14px;padding:18px">
              <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#475569;
                          letter-spacing:2px;margin-bottom:12px">PREFERENCE ({total_pref} responses)</div>
              <div style="margin-bottom:8px">
                <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-bottom:4px">
                  <span>NTL</span><span style="color:#818cf8">{ntl_pct:.0f}%</span>
                </div>
                <div style="height:6px;background:rgba(255,255,255,.05);border-radius:3px">
                  <div style="height:100%;width:{ntl_pct:.0f}%;background:linear-gradient(90deg,#818cf8,#38bdf8);border-radius:3px"></div>
                </div>
              </div>
              <div>
                <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;margin-bottom:4px">
                  <span>Traditional</span><span style="color:#475569">{trad_pct:.0f}%</span>
                </div>
                <div style="height:6px;background:rgba(255,255,255,.05);border-radius:3px">
                  <div style="height:100%;width:{trad_pct:.0f}%;background:#334155;border-radius:3px"></div>
                </div>
              </div>
            </div>""")

        # Per-scenario accuracy
        st.html("<div style='height:8px'></div>")
        st.html("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#475569;
                    letter-spacing:2px;margin-bottom:10px">ACCURACY BY SCENARIO</div>""")
        if "scenario_name" in df.columns:
            for scenario_name in df["scenario_name"].unique():
                sub = df[df["scenario_name"]==scenario_name]
                for cond, color in [("NTL","#818cf8"),("Traditional","#475569")]:
                    c_sub = sub[sub["condition"]==cond]
                    if len(c_sub) > 0:
                        acc = c_sub["risk_correct"].mean()
                        st.html(f"""
                        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
                          <div style="width:140px;font-size:11px;color:#64748b;white-space:nowrap;overflow:hidden">{scenario_name[:20]}</div>
                          <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:{color};width:80px">{cond}</div>
                          <div style="flex:1;height:5px;background:rgba(255,255,255,.05);border-radius:3px">
                            <div style="height:100%;width:{acc*100:.0f}%;background:{color};border-radius:3px"></div>
                          </div>
                          <div style="font-size:11px;color:#94a3b8;width:35px;text-align:right">{acc:.0%}</div>
                        </div>""")

        # NASA-TLX summary
        tlx_cols = ["tlx_mental","tlx_physical","tlx_temporal","tlx_performance","tlx_effort","tlx_frustration"]
        tlx_labels = ["Mental","Physical","Temporal","Performance","Effort","Frustration"]
        if all(c in df.columns for c in tlx_cols):
            st.html("<div style='height:8px'></div>")
            st.html("""
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#475569;
                        letter-spacing:2px;margin-bottom:10px">NASA-TLX WORKLOAD (lower = better)</div>""")
            for cond, color in [("NTL","#818cf8"),("Traditional","#475569")]:
                c_df = df[df["condition"]==cond]
                if len(c_df) > 0:
                    avg_tlx = c_df[tlx_cols].mean().mean()
                    st.html(f"""
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
                      <div style="width:120px;font-size:11px;color:#64748b">{cond}</div>
                      <div style="flex:1;height:5px;background:rgba(255,255,255,.05);border-radius:3px">
                        <div style="height:100%;width:{avg_tlx:.0f}%;background:{color};border-radius:3px"></div>
                      </div>
                      <div style="font-size:11px;color:#94a3b8;width:40px;text-align:right">{avg_tlx:.0f}/100</div>
                    </div>""")

        # Raw data + download
        st.html("<div style='height:8px'></div>")
        with st.expander("Raw Data"):
            st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode(),
            f"ntl_experiment_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv",
        )

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PARTICIPANT FLOW
# ══════════════════════════════════════════════════════════════════════════════

phase = st.session_state["phase"]

# ── CONSENT ───────────────────────────────────────────────────────────────────
if phase == "consent":
    st.html("""
    <div style="padding:24px 0 16px">
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;
                  background:linear-gradient(90deg,#818cf8,#38bdf8);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  background-clip:text;margin-bottom:10px">RESEARCH STUDY</div>
      <div style="font-size:26px;font-weight:800;color:#e2e8f0;margin-bottom:8px">
        Neuroaesthetic Intelligence Study</div>
      <div style="font-size:13px;color:#64748b;line-height:1.8">
        Between 0 and 1 -- Validation Experiment</div>
    </div>""")

    st.html("""
    <div style="background:rgba(12,18,32,.6);border:1px solid rgba(255,255,255,.07);
                border-radius:14px;padding:22px 24px;margin-bottom:16px">
      <div style="font-size:13px;color:#94a3b8;line-height:1.85">
        <b style="color:#e2e8f0">Purpose:</b> This study examines whether neuroaesthetic visual displays
        help people interpret financial risk signals more accurately and quickly than
        traditional numerical displays.<br><br>
        <b style="color:#e2e8f0">What you will do:</b> View 5 scenarios, each showing a financial
        signal in one of two formats. Answer a comprehension question and rate your experience.
        Takes approximately 8-12 minutes.<br><br>
        <b style="color:#e2e8f0">Your data:</b> Anonymous. Identified only by a random participant ID.
        No personally identifiable information is collected.<br><br>
        <b style="color:#e2e8f0">Voluntary:</b> You may stop at any time.
      </div>
    </div>""")

    pid = st.session_state["participant_id"]
    st.html(f"""
    <div style="background:rgba(129,140,248,.06);border:1px solid rgba(129,140,248,.2);
                border-radius:10px;padding:12px 16px;margin-bottom:20px;
                font-family:'JetBrains Mono',monospace;font-size:12px;color:#a5b4fc">
      Your participant ID: <b>{pid}</b>
    </div>""")

    agree = st.checkbox("I have read the above and agree to participate.")
    if agree:
        if st.button("Begin Study", type="primary"):
            st.session_state["phase"] = "demographics"
            st.rerun()


# ── DEMOGRAPHICS ──────────────────────────────────────────────────────────────
elif phase == "demographics":
    st.html("""
    <div style="padding:16px 0 12px">
      <div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:6px">About You</div>
      <div style="font-size:12px;color:#64748b;font-family:'JetBrains Mono',monospace">
        Step 1 of 3 -- Demographics</div>
    </div>""")

    age      = st.selectbox("Age range", ["18-24","25-34","35-44","45-54","55+"])
    role     = st.selectbox("Primary role", [
        "Finance / Investment Professional",
        "Data Analyst / Data Scientist",
        "Product / Design",
        "Engineering / Tech",
        "Executive / Leadership",
        "Student",
        "Other",
    ])
    exp = st.select_slider(
        "Years using data dashboards professionally",
        options=["0","1-2","3-5","6-10","10+"]
    )
    familiar = st.radio(
        "How familiar are you with AI/ML model outputs?",
        ["Not familiar", "Somewhat familiar", "Very familiar"],
        horizontal=True,
    )

    if st.button("Continue", type="primary"):
        st.session_state["demographics"] = {
            "age_range": age, "role": role,
            "dashboard_exp_years": exp, "ai_familiarity": familiar,
        }
        st.session_state["phase"] = "instructions"
        st.rerun()


# ── INSTRUCTIONS ──────────────────────────────────────────────────────────────
elif phase == "instructions":
    st.html("""
    <div style="padding:16px 0 12px">
      <div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:6px">How It Works</div>
      <div style="font-size:12px;color:#64748b;font-family:'JetBrains Mono',monospace">
        Step 2 of 3 -- Instructions</div>
    </div>""")

    st.html("""
    <div style="background:rgba(12,18,32,.6);border:1px solid rgba(255,255,255,.07);
                border-radius:14px;padding:22px 24px;margin-bottom:20px">
      <div style="font-size:13px;color:#94a3b8;line-height:1.95">
        You will see <b style="color:#e2e8f0">5 financial scenarios</b>, one at a time.<br><br>
        Each scenario shows a financial position displayed in a specific visual format.
        Study the display, then answer:<br><br>
        1. <b style="color:#e2e8f0">What is the risk level</b> of this position?<br>
        2. <b style="color:#e2e8f0">How confident</b> are you in your answer?<br>
        3. <b style="color:#e2e8f0">How clear</b> did the display feel?<br><br>
        There are no trick questions. Answer based on your genuine first impression.
        Try to respond within about 30 seconds per scenario.
      </div>
    </div>""")

    if st.button("Start Scenarios", type="primary"):
        st.session_state["phase"]       = "trial"
        st.session_state["trial_idx"]   = 0
        st.session_state["trial_start"] = time.time()
        st.rerun()


# ── TRIAL ─────────────────────────────────────────────────────────────────────
elif phase == "trial":
    idx       = st.session_state["trial_idx"]
    order     = st.session_state["scenario_order"]
    conditions= st.session_state["condition_order"]

    if idx >= len(order):
        st.session_state["phase"] = "nasa_tlx"
        st.rerun()

    scenario  = SCENARIOS[order[idx]]
    condition = conditions[idx]
    s         = scenario["signals"]

    progress = (idx) / len(order)
    st.html(f"""
    <div style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;
                  font-size:10px;color:#475569;margin-bottom:6px">
        <span>SCENARIO {idx+1} OF {len(order)}</span>
        <span>{condition} FORMAT</span>
      </div>
      <div style="height:3px;background:rgba(255,255,255,.05);border-radius:3px">
        <div style="height:100%;width:{progress*100:.0f}%;
                    background:linear-gradient(90deg,#818cf8,#38bdf8);border-radius:3px"></div>
      </div>
    </div>""")

    st.html(f"""
    <div style="background:rgba(12,18,32,.5);border:1px solid rgba(255,255,255,.06);
                border-radius:12px;padding:12px 16px;margin-bottom:16px">
      <div style="font-size:10px;font-family:'JetBrains Mono',monospace;color:#475569;
                  letter-spacing:1px;margin-bottom:4px">SCENARIO CONTEXT</div>
      <div style="font-size:13px;color:#94a3b8;line-height:1.7">{scenario['context']}</div>
    </div>""")

    # Show the right card format
    if condition == "NTL":
        st.html(card_wrap(ntl_card_html(scenario["name"], s, large=True),
                          "NTL VIEW", "#818cf8"))
    else:
        st.html(card_wrap(trad_card_html(scenario["name"], s),
                          "TRADITIONAL VIEW", "#64748b"))

    st.html("<div style='height:16px'></div>")

    # Comprehension question
    st.html("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#475569;
                letter-spacing:2px;margin-bottom:10px">YOUR ASSESSMENT</div>""")

    risk_answer = st.radio(
        "Based on what you see, what is the risk level of this position?",
        scenario["risk_options"],
        horizontal=True,
        index=None,
    )

    col_conf, col_clarity = st.columns(2)
    with col_conf:
        confidence_rating = st.slider(
            "How confident are you in your answer?",
            1, 5, 3,
            help="1 = not at all confident, 5 = very confident"
        )
    with col_clarity:
        clarity_rating = st.slider(
            "How clear was the display?",
            1, 5, 3,
            help="1 = very unclear, 5 = extremely clear"
        )

    if risk_answer and st.button("Submit and Continue", type="primary"):
        elapsed    = time.time() - st.session_state["trial_start"]
        is_correct = (risk_answer == scenario["correct_answer"])
        dem        = st.session_state["demographics"]

        row = {
            "participant_id":    st.session_state["participant_id"],
            "timestamp":         datetime.now().isoformat(),
            "age_range":         dem.get("age_range",""),
            "role":              dem.get("role",""),
            "dashboard_exp_years": dem.get("dashboard_exp_years",""),
            "scenario_idx":      order[idx],
            "scenario_name":     scenario["name"],
            "condition":         condition,
            "response_time_sec": round(elapsed, 2),
            "risk_answer":       risk_answer,
            "risk_correct":      int(is_correct),
            "confidence_rating": confidence_rating,
            "clarity_rating":    clarity_rating,
            "tlx_mental": None, "tlx_physical": None, "tlx_temporal": None,
            "tlx_performance": None, "tlx_effort": None, "tlx_frustration": None,
            "overall_preference": None,
            "notes": "",
        }
        st.session_state["trial_data"].append(row)
        st.session_state["trial_idx"]   += 1
        st.session_state["trial_start"]  = time.time()
        st.rerun()


# ── NASA-TLX ──────────────────────────────────────────────────────────────────
elif phase == "nasa_tlx":
    st.html("""
    <div style="padding:16px 0 12px">
      <div style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:6px">
        Workload Assessment</div>
      <div style="font-size:12px;color:#64748b;font-family:'JetBrains Mono',monospace">
        Step 3 of 3 -- NASA Task Load Index (TLX)</div>
    </div>""")

    st.html("""
    <div style="background:rgba(12,18,32,.5);border:1px solid rgba(255,255,255,.06);
                border-radius:12px;padding:12px 16px;margin-bottom:16px;font-size:12px;color:#64748b">
      Rate your overall experience across all scenarios you just completed.
      These scales measure the mental effort required, not your performance.
    </div>""")

    tlx_mental      = st.slider("Mental Demand — How mentally demanding was the task?",        0, 100, 50, 5)
    tlx_physical    = st.slider("Physical Demand — How physically demanding was the task?",    0, 100, 10, 5)
    tlx_temporal    = st.slider("Temporal Demand — How much time pressure did you feel?",      0, 100, 30, 5)
    tlx_performance = st.slider("Performance — How successful were you? (0=perfect, 100=fail)",0, 100, 30, 5)
    tlx_effort      = st.slider("Effort — How hard did you have to work?",                     0, 100, 40, 5)
    tlx_frustration = st.slider("Frustration — How stressed or irritated did you feel?",       0, 100, 20, 5)

    overall_pref = st.radio(
        "Overall, which display format helped you understand financial risk faster?",
        ["NTL (color/gradient)", "Traditional (numbers/bars)", "No difference"],
        horizontal=False,
        index=None,
    )

    notes = st.text_area("Any comments or observations? (optional)", height=80)

    if overall_pref and st.button("Complete Study", type="primary"):
        for row in st.session_state["trial_data"]:
            row["tlx_mental"]       = tlx_mental
            row["tlx_physical"]     = tlx_physical
            row["tlx_temporal"]     = tlx_temporal
            row["tlx_performance"]  = tlx_performance
            row["tlx_effort"]       = tlx_effort
            row["tlx_frustration"]  = tlx_frustration
            row["overall_preference"] = "NTL" if "NTL" in overall_pref else \
                                         "Traditional" if "Traditional" in overall_pref else "None"
            row["notes"]            = notes
            save_row(row)

        st.session_state["phase"] = "done"
        st.rerun()


# ── DONE ──────────────────────────────────────────────────────────────────────
elif phase == "done":
    trial_data = st.session_state["trial_data"]
    n_correct  = sum(r["risk_correct"] for r in trial_data)
    avg_rt     = np.mean([r["response_time_sec"] for r in trial_data])

    st.html(f"""
    <div style="padding:32px 0 16px;text-align:center">
      <div style="font-size:36px;margin-bottom:12px">◉</div>
      <div style="font-size:24px;font-weight:800;color:#e2e8f0;margin-bottom:8px">
        Thank you.</div>
      <div style="font-size:13px;color:#64748b;margin-bottom:24px">
        Your responses have been recorded.</div>
      <div style="display:flex;justify-content:center;gap:24px;flex-wrap:wrap">
        <div style="background:rgba(12,18,32,.6);border:1px solid rgba(129,140,248,.2);
                    border-radius:12px;padding:16px 24px;min-width:120px">
          <div style="font-size:24px;font-weight:700;color:#818cf8">{n_correct}/{len(trial_data)}</div>
          <div style="font-size:10px;color:#64748b;font-family:'JetBrains Mono',monospace;margin-top:4px">CORRECT</div>
        </div>
        <div style="background:rgba(12,18,32,.6);border:1px solid rgba(56,189,248,.2);
                    border-radius:12px;padding:16px 24px;min-width:120px">
          <div style="font-size:24px;font-weight:700;color:#38bdf8">{avg_rt:.1f}s</div>
          <div style="font-size:10px;color:#64748b;font-family:'JetBrains Mono',monospace;margin-top:4px">AVG RESPONSE</div>
        </div>
        <div style="background:rgba(12,18,32,.6);border:1px solid rgba(255,255,255,.07);
                    border-radius:12px;padding:16px 24px;min-width:120px">
          <div style="font-size:13px;font-weight:600;color:#94a3b8;margin-top:4px">
            {st.session_state["participant_id"]}</div>
          <div style="font-size:10px;color:#64748b;font-family:'JetBrains Mono',monospace;margin-top:4px">PARTICIPANT ID</div>
        </div>
      </div>
    </div>""")

    st.html("""
    <div style="background:rgba(12,18,32,.5);border:1px solid rgba(255,255,255,.06);
                border-radius:12px;padding:16px;text-align:center;margin-top:8px">
      <div style="font-size:11px;color:#475569;font-family:'JetBrains Mono',monospace">
        BETWEEN 0 AND 1 -- NEUROAESTHETIC VALIDATION STUDY</div>
    </div>""")
