"""
Generates the Between 0 and 1 / Feel-the-Model investor PDF.
Run: python generate_pdf.py
Output: feel_the_model_investor_deck.pdf
"""

from fpdf import FPDF
import math

# ?? Palette ???????????????????????????????????????????????????????????????????
BG       = (3,   5,  10)
SURFACE  = (12,  18,  32)
CARD     = (18,  26,  46)
BORDER   = (40,  50,  70)
WHITE    = (232, 232, 240)
MUTED    = (100, 116, 139)
SUBTLE   = (148, 163, 184)
INDIGO   = (129, 140, 248)
SKY      = ( 56, 189, 248)
VIOLET   = (167, 139, 250)
RED      = (248, 113, 113)
GREEN    = ( 52, 211, 153)
GOLD     = (251, 191,  36)

MONO  = "Courier"
SANS  = "Helvetica"


class Deck(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self.set_margins(0, 0, 0)

    # ?? helpers ???????????????????????????????????????????????????????????????

    def fill(self, r, g, b):
        self.set_fill_color(r, g, b)

    def ink(self, r, g, b):
        self.set_text_color(r, g, b)

    def dcolor(self, r, g, b):
        self.set_draw_color(r, g, b)

    def bg_rect(self, x, y, w, h, color):
        self.fill(*color)
        self.rect(x, y, w, h, style="F")

    def gradient_bar(self, x, y, w, h, c1, c2, steps=60):
        """Simulate a horizontal gradient with thin vertical slices."""
        sw = w / steps
        for i in range(steps):
            t  = i / (steps - 1)
            r  = int(c1[0] + (c2[0] - c1[0]) * t)
            g  = int(c1[1] + (c2[1] - c1[1]) * t)
            b  = int(c1[2] + (c2[2] - c1[2]) * t)
            self.fill(r, g, b)
            self.rect(x + i * sw, y, sw + 0.5, h, style="F")

    def label(self, x, y, text, size=7, color=None, bold=False, mono=False):
        color = color or MUTED
        self.ink(*color)
        self.set_font(MONO if mono else SANS, "B" if bold else "", size)
        self.set_xy(x, y)
        self.cell(0, 4, text)

    def para(self, x, y, w, text, size=8, color=None, line_h=4.5):
        color = color or SUBTLE
        self.ink(*color)
        self.set_font(SANS, "", size)
        self.set_xy(x, y)
        self.multi_cell(w, line_h, text)

    def section_title(self, x, y, title, size=13):
        self.ink(*INDIGO)
        self.set_font(SANS, "B", size)
        self.set_xy(x, y)
        self.cell(0, 6, title)
        # accent bar
        self.fill(*INDIGO)
        self.rect(x, y + 7, 24, 1.2, style="F")

    def chip(self, x, y, text, color=None):
        color = color or INDIGO
        self.set_font(MONO, "", 6)
        tw = self.get_string_width(text) + 6
        self.fill(color[0]//6, color[1]//6, color[2]//6)
        self.rect(x, y, tw, 5, style="F")
        self.ink(*color)
        self.set_xy(x + 3, y + 0.8)
        self.cell(tw, 4, text)
        return tw + 3

    def divider(self, y, alpha=30):
        self.dcolor(*BORDER)
        self.set_line_width(0.2)
        self.line(12, y, self.w - 12, y)

    def ntl_card(self, x, y, w, h, name, state, label, hue_frac,
                 conf, risk, vol, stab, sig):
        """Draw an NTL card."""
        # Compute gradient colors from hue_frac (0=red, 1=blue-green)
        t  = hue_frac
        c1 = (int(248*(1-t) + 56*t),  int(113*(1-t) + 189*t),  int(113*(1-t) + 248*t))
        c2 = (int(c1[0]*0.6), int(c1[1]*0.6), int(c1[2]*0.9))

        # card bg
        self.bg_rect(x, y, w, h, SURFACE)
        self.dcolor(*BORDER)
        self.set_line_width(0.3)
        self.rect(x, y, w, h)

        # gradient bar (top 28%)
        bar_h = h * 0.32
        self.gradient_bar(x, y, w, bar_h, c1, c2)

        # state badge
        self.fill(*BG)
        self.rect(x + w - 34, y + bar_h - 8, 32, 6, style="F")
        self.ink(*c1)
        self.set_font(MONO, "B", 5.5)
        self.set_xy(x + w - 33, y + bar_h - 7.2)
        self.cell(30, 4, state, align="C")

        # watermark
        self.ink(255, 255, 255)
        self.set_font(MONO, "", 4.5)
        self.set_xy(x + 3, y + 2)
        self.cell(0, 3, "BETWEEN 0 AND 1 - NTL")

        # name
        cy = y + bar_h + 3
        self.ink(*WHITE)
        self.set_font(SANS, "B", 8)
        self.set_xy(x + 4, cy)
        self.cell(w - 8, 5, name)

        # label
        self.ink(*MUTED)
        self.set_font(MONO, "", 5.5)
        self.set_xy(x + 4, cy + 5)
        self.cell(w - 8, 3.5, label)

        # signal bars
        bar_y = y + h - 12
        self.fill(*BORDER)
        self.rect(x + 2, bar_y - 1, w - 4, 0.3, style="F")

        signals = [
            ("CONF", conf,  INDIGO),
            ("RISK", risk,  c1),
            ("VOL",  vol,   SUBTLE),
            ("STAB", stab,  SKY),
            ("SIG",  sig,   VIOLET),
        ]
        bx = x + 4
        bw = (w - 12) / len(signals)
        for k, v, color in signals:
            bar_fill_h = v * 10
            self.fill(*SURFACE)
            self.rect(bx, bar_y, bw - 1, 10, style="F")
            self.fill(*color)
            self.rect(bx, bar_y + (10 - bar_fill_h), bw - 1, bar_fill_h, style="F")
            self.ink(*MUTED)
            self.set_font(MONO, "", 4)
            self.set_xy(bx, bar_y + 11)
            self.cell(bw - 1, 3, k, align="C")
            bx += bw

    def trad_card(self, x, y, w, h, name, signals):
        """Draw a traditional bar chart card."""
        self.bg_rect(x, y, w, h, SURFACE)
        self.dcolor(*BORDER)
        self.set_line_width(0.3)
        self.rect(x, y, w, h)

        self.ink(*MUTED)
        self.set_font(MONO, "", 5)
        self.set_xy(x + 4, y + 3)
        self.cell(0, 3, "TRADITIONAL VIEW")

        self.ink(*WHITE)
        self.set_font(SANS, "B", 8)
        self.set_xy(x + 4, y + 8)
        self.cell(0, 5, name)

        sy = y + 17
        colors = [INDIGO, RED, SUBTLE, SKY, VIOLET]
        labels = ["Confidence", "Risk Score", "Volatility", "Stability", "Signal Str"]
        for i, (lbl, val, color) in enumerate(zip(labels, signals, colors)):
            self.ink(*MUTED)
            self.set_font(SANS, "", 6)
            self.set_xy(x + 4, sy)
            self.cell(40, 3.5, lbl)
            self.ink(*SUBTLE)
            self.set_font(MONO, "", 6)
            self.set_xy(x + w - 16, sy)
            self.cell(12, 3.5, f"{val:.0%}", align="R")
            # track
            self.fill(30, 40, 60)
            self.rect(x + 4, sy + 4, w - 10, 2.5, style="F")
            self.fill(*color)
            self.rect(x + 4, sy + 4, (w - 10) * val, 2.5, style="F")
            sy += 10


# ??????????????????????????????????????????????????????????????????????????????
# BUILD PDF
# ??????????????????????????????????????????????????????????????????????????????

def build():
    pdf = Deck()
    W, H = 297, 210  # A4 landscape mm

    # ?????????????????????????????????????????????????????????????????????????
    # PAGE 1 - COVER
    # ?????????????????????????????????????????????????????????????????????????
    pdf.add_page()
    pdf.bg_rect(0, 0, W, H, BG)

    # gradient strip left
    pdf.gradient_bar(0, 0, 8, H, INDIGO, SKY, steps=40)

    # hero gradient panel (right side)
    pdf.gradient_bar(W//2 + 20, 0, W//2 - 20, H,
                     (8, 13, 23), (18, 30, 60), steps=30)

    # big title
    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 32)
    pdf.set_xy(18, 30)
    pdf.cell(0, 14, "Between 0 and 1")

    pdf.ink(*INDIGO)
    pdf.set_font(SANS, "B", 18)
    pdf.set_xy(18, 50)
    pdf.cell(0, 8, "Feel-the-Model(TM)")

    pdf.ink(*SUBTLE)
    pdf.set_font(SANS, "", 10)
    pdf.set_xy(18, 62)
    pdf.cell(0, 5, "Neuroaesthetic AI Infrastructure")

    # tagline
    pdf.ink(*MUTED)
    pdf.set_font(SANS, "I", 9)
    pdf.set_xy(18, 74)
    pdf.multi_cell(110, 5.5,
        "The translation layer between AI's math\n"
        "and the human nervous system.")

    # chips
    cx = 18
    for tag in ["Pre-Seed", "Enterprise AI", "Neuroaesthetics", "FinTech"]:
        cx += pdf.chip(cx, 92, tag) + 2

    # divider
    pdf.divider(105)

    # NTL mapping preview (right column)
    rx = W // 2 + 24
    pdf.section_title(rx, 20, "The NTL Mapping")
    my = 35
    mappings = [
        ("Confidence",  "-->  Color Saturation",  INDIGO),
        ("Risk Score",  "-->  Hue  (blue --> red)", RED),
        ("Volatility",  "-->  Blur / Softness",   SUBTLE),
        ("Stability",   "-->  Gradient Symmetry", SKY),
        ("Signal Str",  "-->  Brightness",        VIOLET),
    ]
    for inp, out, color in mappings:
        pdf.ink(*color)
        pdf.set_font(MONO, "B", 7)
        pdf.set_xy(rx, my)
        pdf.cell(40, 4.5, inp)
        pdf.ink(*SUBTLE)
        pdf.set_font(SANS, "", 7)
        pdf.set_xy(rx + 38, my)
        pdf.cell(60, 4.5, out)
        my += 9

    # mini NTL card preview
    pdf.ntl_card(rx, my + 4, 90, 52,
                 "Portfolio Alpha", "CONFIDENCE",
                 "Calm and confident - strong position",
                 hue_frac=0.88, conf=0.82, risk=0.22,
                 vol=0.28, stab=0.78, sig=0.80)

    # bottom bar
    pdf.bg_rect(0, H - 14, W, 14, SURFACE)
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(18, H - 9)
    pdf.cell(0, 4, "INVESTOR DECK  -  CONFIDENTIAL  -  2026")
    pdf.set_xy(W - 80, H - 9)
    pdf.cell(68, 4, "nishanalyzedata@gmail.com", align="R")

    # ?????????????????????????????????????????????????????????????????????????
    # PAGE 2 - THE PROBLEM
    # ?????????????????????????????????????????????????????????????????????????
    pdf.add_page()
    pdf.bg_rect(0, 0, W, H, BG)
    pdf.gradient_bar(0, 0, 8, H, INDIGO, SKY, steps=40)

    pdf.ink(*INDIGO)
    pdf.set_font(MONO, "", 7)
    pdf.set_xy(18, 14)
    pdf.cell(0, 4, "SLIDE 01  -  THE PROBLEM")

    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 20)
    pdf.set_xy(18, 22)
    pdf.cell(0, 9, "AI speaks math.")
    pdf.ink(*SUBTLE)
    pdf.set_font(SANS, "B", 20)
    pdf.set_xy(18, 32)
    pdf.cell(0, 9, "Humans feel gradients.")

    pdf.divider(46)

    points = [
        ("Dashboard Fatigue",
         "72% of executives cite information overload as the #1 barrier to AI\n"
         "adoption. Dashboards full of numbers create cognitive paralysis."),
        ("Misaligned Trust",
         "Binary AI outputs hide confidence gradients. Users either over-trust\n"
         "or under-trust - rarely calibrate correctly."),
        ("Explainability != Interpretability",
         "XAI tells you what the model did. No product tells your\n"
         "nervous system how to feel about it. Those are different problems."),
        ("The Core Gap",
         "AI computes in 0s and 1s. Human perception operates in gradients -\n"
         "color, warmth, tension, clarity. Nobody bridges this."),
    ]
    px, py = 18, 52
    for i, (title, body) in enumerate(points):
        if i == 2:
            px = W // 2 + 4
            py = 52
        pdf.bg_rect(px, py, 122, 34, SURFACE)
        pdf.dcolor(*BORDER)
        pdf.set_line_width(0.3)
        pdf.rect(px, py, 122, 34)
        # accent left bar
        pdf.fill(*INDIGO)
        pdf.rect(px, py, 2, 34, style="F")
        pdf.ink(*WHITE)
        pdf.set_font(SANS, "B", 8)
        pdf.set_xy(px + 6, py + 5)
        pdf.cell(0, 4, title)
        pdf.ink(*SUBTLE)
        pdf.set_font(SANS, "", 7)
        pdf.set_xy(px + 6, py + 11)
        pdf.multi_cell(112, 4.2, body)
        py += 40

    # stat callout
    pdf.bg_rect(18, H - 36, W - 36, 22, SURFACE)
    pdf.gradient_bar(18, H - 36, 4, 22, INDIGO, SKY, steps=10)
    pdf.ink(*INDIGO)
    pdf.set_font(SANS, "B", 22)
    pdf.set_xy(30, H - 33)
    pdf.cell(0, 10, "72%")
    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 9)
    pdf.set_xy(54, H - 30)
    pdf.cell(0, 5, "of executives report dashboard overload as their #1 AI adoption barrier")
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(54, H - 24)
    pdf.cell(0, 3.5, "Source: Gartner AI Adoption Survey, 2025")

    pdf.bg_rect(0, H - 14, W, 14, SURFACE)
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(18, H - 9)
    pdf.cell(0, 4, "BETWEEN 0 AND 1(TM)  -  FEEL-THE-MODEL(TM)")
    pdf.ink(*MUTED)
    pdf.set_xy(W - 30, H - 9)
    pdf.cell(18, 4, "1 / 5", align="R")

    # ?????????????????????????????????????????????????????????????????????????
    # PAGE 3 - THE SOLUTION
    # ?????????????????????????????????????????????????????????????????????????
    pdf.add_page()
    pdf.bg_rect(0, 0, W, H, BG)
    pdf.gradient_bar(0, 0, 8, H, INDIGO, SKY, steps=40)

    pdf.ink(*INDIGO)
    pdf.set_font(MONO, "", 7)
    pdf.set_xy(18, 14)
    pdf.cell(0, 4, "SLIDE 02  -  THE SOLUTION")

    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 18)
    pdf.set_xy(18, 22)
    pdf.cell(0, 8, "Neuroaesthetic Translation Layer")

    pdf.ink(*SUBTLE)
    pdf.set_font(SANS, "", 8.5)
    pdf.set_xy(18, 33)
    pdf.multi_cell(130, 4.8,
        "Middleware that converts AI model outputs into neurologically calibrated\n"
        "visual experiences - AI-agnostic, domain-agnostic, plug-in.")

    pdf.divider(46)

    # architecture flow
    arch_items = [
        ("AI Model Output",   SURFACE, BORDER),
        ("NTL Core",          (20, 30, 60), INDIGO),
        ("Human Interface",   SURFACE, BORDER),
    ]
    ax = 18
    ay = 52
    for label, bg, border in arch_items:
        pdf.bg_rect(ax, ay, 52, 18, bg)
        pdf.dcolor(*border)
        pdf.set_line_width(0.5 if border == INDIGO else 0.2)
        pdf.rect(ax, ay, 52, 18)
        pdf.ink(*WHITE if border == INDIGO else SUBTLE)
        pdf.set_font(SANS, "B" if border == INDIGO else "", 7.5)
        pdf.set_xy(ax, ay + 7)
        pdf.cell(52, 4, label, align="C")
        if ax < 122:
            # arrow
            pdf.ink(*INDIGO)
            pdf.set_font(SANS, "B", 10)
            pdf.set_xy(ax + 54, ay + 5)
            pdf.cell(8, 8, "-->", align="C")
        ax += 62

    # NTL mappings table
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(18, 76)
    pdf.cell(0, 3.5, "AI SIGNAL")
    pdf.set_xy(70, 76)
    pdf.cell(0, 3.5, "NTL OUTPUT")
    pdf.set_xy(130, 76)
    pdf.cell(0, 3.5, "NEUROSCIENCE BASIS")
    pdf.divider(80)

    rows = [
        ("Confidence",  "Color Saturation",  "Vivid hues activate dopamine reward circuits",     INDIGO),
        ("Risk Score",  "Hue (blue --> red)",  "480-520nm reduces cortisol; red triggers amygdala", RED),
        ("Volatility",  "Blur / Softness",   "Visual ambiguity mirrors cognitive uncertainty",    SUBTLE),
        ("Stability",   "Gradient Angle",    "Symmetry signals environmental safety",              SKY),
        ("Signal Str",  "Brightness",        "Luminance drives attentional salience networks",    VIOLET),
    ]
    ry = 82
    for sig, out, sci, color in rows:
        pdf.fill(*color)
        pdf.rect(18, ry + 1, 1.5, 4, style="F")
        pdf.ink(*WHITE)
        pdf.set_font(SANS, "B", 7)
        pdf.set_xy(22, ry)
        pdf.cell(44, 5, sig)
        pdf.ink(*SUBTLE)
        pdf.set_font(SANS, "", 7)
        pdf.set_xy(70, ry)
        pdf.cell(58, 5, out)
        pdf.ink(*MUTED)
        pdf.set_font(SANS, "", 6.5)
        pdf.set_xy(130, ry)
        pdf.cell(150, 5, sci)
        ry += 9

    # side-by-side demo cards
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(W - 118, 50)
    pdf.cell(0, 3.5, "TRADITIONAL VIEW")

    demo_sig = [0.82, 0.22, 0.28, 0.78, 0.80]
    pdf.trad_card(W - 118, 54, 52, 70, "Portfolio Alpha", demo_sig)

    pdf.ink(*INDIGO)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(W - 62, 50)
    pdf.cell(0, 3.5, "NTL VIEW")
    pdf.ntl_card(W - 62, 54, 52, 70,
                 "Portfolio Alpha", "CONFIDENCE",
                 "Calm and confident",
                 hue_frac=0.88, conf=0.82, risk=0.22,
                 vol=0.28, stab=0.78, sig=0.80)

    pdf.ink(*INDIGO)
    pdf.set_font(SANS, "B", 7)
    pdf.set_xy(W - 118, 128)
    pdf.multi_cell(108, 4.2,
        "Executives understand the NTL card before reading a single number.\n"
        "Explainable AI tells you what. Embodied AI tells you how to feel.")

    pdf.bg_rect(0, H - 14, W, 14, SURFACE)
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(18, H - 9)
    pdf.cell(0, 4, "BETWEEN 0 AND 1(TM)  -  FEEL-THE-MODEL(TM)")
    pdf.set_xy(W - 30, H - 9)
    pdf.cell(18, 4, "2 / 5", align="R")

    # ?????????????????????????????????????????????????????????????????????????
    # PAGE 4 - PRODUCT + TRACTION
    # ?????????????????????????????????????????????????????????????????????????
    pdf.add_page()
    pdf.bg_rect(0, 0, W, H, BG)
    pdf.gradient_bar(0, 0, 8, H, INDIGO, SKY, steps=40)

    pdf.ink(*INDIGO)
    pdf.set_font(MONO, "", 7)
    pdf.set_xy(18, 14)
    pdf.cell(0, 4, "SLIDE 03  -  PRODUCT + TRACTION")

    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 18)
    pdf.set_xy(18, 22)
    pdf.cell(0, 8, "Working. Live. Collecting data today.")

    pdf.divider(36)

    # product modules
    modules = [
        ("Single Asset",     "Real-time NTL card from 5 sliders.\nInstant visual feedback.",         INDIGO),
        ("Live Market Data", "Type any ticker. yfinance pulls 3 months\nof data. NTL renders live.", SKY),
        ("Portfolio View",   "CSV upload. Portfolio mood banner\n+ per-asset neuroaesthetic grid.",    VIOLET),
        ("A/B Demo Engine",  "NTL vs Traditional, side by side.\nCollects preference data live.",     GREEN),
    ]
    mx = 18
    for title, body, color in modules:
        pdf.bg_rect(mx, 42, 60, 42, SURFACE)
        pdf.dcolor(*BORDER)
        pdf.set_line_width(0.2)
        pdf.rect(mx, 42, 60, 42)
        pdf.gradient_bar(mx, 42, 60, 3, color, (color[0]//3, color[1]//3, color[2]//3))
        pdf.ink(*color)
        pdf.set_font(SANS, "B", 7.5)
        pdf.set_xy(mx + 4, 50)
        pdf.cell(52, 4, title)
        pdf.ink(*SUBTLE)
        pdf.set_font(SANS, "", 6.8)
        pdf.set_xy(mx + 4, 56)
        pdf.multi_cell(52, 4, body)
        mx += 64

    # traction stats
    pdf.section_title(18, 92, "Traction")
    stats = [
        ("MVP Live",      "Working app on localhost + GitHub",      INDIGO),
        ("Real Data",     "yfinance integration - live market NTL", SKY),
        ("A/B Running",   "Preference data collected each session", GREEN),
        ("6 Experiments", "Full validation study design complete",  VIOLET),
    ]
    sx = 18
    for stat_val, stat_lbl, color in stats:
        pdf.bg_rect(sx, 106, 60, 22, SURFACE)
        pdf.dcolor(*color)
        pdf.set_line_width(0.4)
        pdf.rect(sx, 106, 60, 22)
        pdf.ink(*color)
        pdf.set_font(SANS, "B", 9)
        pdf.set_xy(sx + 4, 110)
        pdf.cell(52, 5, stat_val)
        pdf.ink(*MUTED)
        pdf.set_font(SANS, "", 6.5)
        pdf.set_xy(sx + 4, 116)
        pdf.multi_cell(52, 3.8, stat_lbl)
        sx += 64

    # roadmap
    pdf.section_title(18, 133, "12-Month Roadmap")
    rmap = [
        ("Q3 2026", "Biometric validation\nN=150, HRV + eye tracking",         INDIGO),
        ("Q4 2026", "NTL API beta\n3 enterprise pilot partnerships",            SKY),
        ("Q1 2027", "Platform launch\nWhite-label SDK + neural profiles",       VIOLET),
        ("Q2 2027", "Standard push\nNTL as industry content standard",          GREEN),
    ]
    rx2 = 18
    for qtr, body, color in rmap:
        pdf.gradient_bar(rx2, 148, 60, 3, color, (color[0]//4, color[1]//4, color[2]//4))
        pdf.ink(*color)
        pdf.set_font(MONO, "B", 7)
        pdf.set_xy(rx2, 153)
        pdf.cell(60, 4, qtr)
        pdf.ink(*SUBTLE)
        pdf.set_font(SANS, "", 6.5)
        pdf.set_xy(rx2, 158)
        pdf.multi_cell(58, 4, body)
        rx2 += 64

    pdf.bg_rect(0, H - 14, W, 14, SURFACE)
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(18, H - 9)
    pdf.cell(0, 4, "BETWEEN 0 AND 1(TM)  -  FEEL-THE-MODEL(TM)")
    pdf.set_xy(W - 30, H - 9)
    pdf.cell(18, 4, "3 / 5", align="R")

    # ?????????????????????????????????????????????????????????????????????????
    # PAGE 5 - MARKET + BUSINESS MODEL
    # ?????????????????????????????????????????????????????????????????????????
    pdf.add_page()
    pdf.bg_rect(0, 0, W, H, BG)
    pdf.gradient_bar(0, 0, 8, H, INDIGO, SKY, steps=40)

    pdf.ink(*INDIGO)
    pdf.set_font(MONO, "", 7)
    pdf.set_xy(18, 14)
    pdf.cell(0, 4, "SLIDE 04  -  MARKET + BUSINESS MODEL")

    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 18)
    pdf.set_xy(18, 22)
    pdf.cell(0, 8, "Infrastructure for the human layer of AI.")

    pdf.divider(36)

    # market TAM/SAM/SOM
    pdf.section_title(18, 42, "Market Size")
    market = [
        ("$29B", "Enterprise BI",         "Total addressable market",       INDIGO),
        ("$6B",  "AI-Enhanced BI",        "35% YoY growth segment",         SKY),
        ("$800M","NTL-Addressable Layer", "AI-human interface outputs",      VIOLET),
    ]
    bx2 = 18
    for val, lbl, sub, color in market:
        pdf.bg_rect(bx2, 56, 70, 30, SURFACE)
        pdf.gradient_bar(bx2, 56, 70, 2.5, color,
                         (color[0]//4, color[1]//4, color[2]//4))
        pdf.ink(*color)
        pdf.set_font(SANS, "B", 16)
        pdf.set_xy(bx2 + 4, 62)
        pdf.cell(62, 8, val)
        pdf.ink(*WHITE)
        pdf.set_font(SANS, "B", 7)
        pdf.set_xy(bx2 + 4, 72)
        pdf.cell(62, 4, lbl)
        pdf.ink(*MUTED)
        pdf.set_font(SANS, "", 6)
        pdf.set_xy(bx2 + 4, 77)
        pdf.cell(62, 3.5, sub)
        bx2 += 74

    # business model table
    pdf.section_title(18, 94, "Revenue Model")
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    headers = ["CHANNEL", "PRICE", "CUSTOMER", "ARR POTENTIAL"]
    hx = 18
    for h, w2 in zip(headers, [52, 40, 55, 50]):
        pdf.set_xy(hx, 108)
        pdf.cell(w2, 4, h)
        hx += w2 + 2
    pdf.divider(113)

    biz_rows = [
        ("API per 1K calls",    "$0.10 / 1K",  "Developers",          "$100K at 1M daily calls",  INDIGO),
        ("Enterprise SDK",      "$10-50K / yr","Finance, Healthcare",  "$750K at 30 customers",    SKY),
        ("White-label NTL",     "$100K+",      "BI Platforms",        "$500K at 5 deals",         VIOLET),
        ("Neural Profile Sub",  "$9.99 / mo",  "Consumers",           "Data flywheel asset",      GREEN),
    ]
    ry2 = 115
    for ch, price, cust, arr, color in biz_rows:
        pdf.fill(*color)
        pdf.rect(18, ry2 + 1.5, 1.2, 4, style="F")
        pdf.ink(*WHITE)
        pdf.set_font(SANS, "", 7)
        pdf.set_xy(22, ry2)
        pdf.cell(48, 5, ch)
        pdf.ink(*SUBTLE)
        pdf.set_xy(74, ry2)
        pdf.cell(38, 5, price)
        pdf.set_xy(114, ry2)
        pdf.cell(53, 5, cust)
        pdf.ink(*MUTED)
        pdf.set_xy(169, ry2)
        pdf.cell(48, 5, arr)
        ry2 += 8

    # moat callout
    pdf.bg_rect(18, H - 46, W - 36, 28, SURFACE)
    pdf.gradient_bar(18, H - 46, W - 36, 2.5, INDIGO, SKY)
    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 8)
    pdf.set_xy(26, H - 40)
    pdf.cell(0, 5, "Defensible Moat")
    moat_items = [
        "Proprietary neuroaesthetic mappings (validated, not guessed)",
        "Biometric validation dataset - impossible to replicate without studies",
        "Neural profile dataset - personalization flywheel, grows with users",
        "AI-agnostic architecture - works with any model, any domain",
    ]
    mx2 = 26
    for item in moat_items:
        pdf.fill(*INDIGO)
        pdf.rect(mx2, H - 31, 1.2, 3.5, style="F")
        pdf.ink(*SUBTLE)
        pdf.set_font(SANS, "", 6.5)
        pdf.set_xy(mx2 + 4, H - 32)
        pdf.cell(58, 5, item)
        mx2 += 63

    pdf.bg_rect(0, H - 14, W, 14, SURFACE)
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(18, H - 9)
    pdf.cell(0, 4, "BETWEEN 0 AND 1(TM)  -  FEEL-THE-MODEL(TM)")
    pdf.set_xy(W - 30, H - 9)
    pdf.cell(18, 4, "4 / 5", align="R")

    # ?????????????????????????????????????????????????????????????????????????
    # PAGE 6 - TEAM + ASK
    # ?????????????????????????????????????????????????????????????????????????
    pdf.add_page()
    pdf.bg_rect(0, 0, W, H, BG)
    pdf.gradient_bar(0, 0, 8, H, INDIGO, SKY, steps=40)

    pdf.ink(*INDIGO)
    pdf.set_font(MONO, "", 7)
    pdf.set_xy(18, 14)
    pdf.cell(0, 4, "SLIDE 05  -  TEAM + ASK")

    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 18)
    pdf.set_xy(18, 22)
    pdf.cell(0, 8, "Built by someone who felt the problem every day.")

    pdf.divider(36)

    # founder card
    pdf.bg_rect(18, 42, 148, 80, SURFACE)
    pdf.dcolor(*BORDER)
    pdf.set_line_width(0.3)
    pdf.rect(18, 42, 148, 80)
    pdf.gradient_bar(18, 42, 148, 3, INDIGO, SKY)

    pdf.ink(*WHITE)
    pdf.set_font(SANS, "B", 13)
    pdf.set_xy(26, 50)
    pdf.cell(0, 6, "Nisha Sapkota")

    pdf.ink(*INDIGO)
    pdf.set_font(SANS, "", 8)
    pdf.set_xy(26, 58)
    pdf.cell(0, 4, "Founder & CEO  -  Between 0 and 1(TM)")

    creds = [
        ("MS Business Analytics (ML)",   "UT Austin McCombs School of Business"),
        ("Quant Researcher",              "Vise - institutional portfolio optimization"),
        ("Business Data Analyst",         "RBC Capital Markets - 2+ years"),
        ("Strategy Consultant",           "Accenture (acquired Logic) - 2+ years"),
        ("100 Most Influential Women",    "Nepal - 2018"),
        ("Open Data Hackathon Winner",    "Data-driven public good solution - 2017"),
    ]
    cy = 66
    for role, org in creds:
        pdf.fill(*INDIGO)
        pdf.rect(26, cy + 1.5, 1, 3.5, style="F")
        pdf.ink(*WHITE)
        pdf.set_font(SANS, "B", 7)
        pdf.set_xy(30, cy)
        pdf.cell(60, 5, role)
        pdf.ink(*MUTED)
        pdf.set_font(SANS, "", 6.8)
        pdf.set_xy(92, cy)
        pdf.cell(68, 5, org)
        cy += 7

    pdf.ink(*SUBTLE)
    pdf.set_font(SANS, "I", 7)
    pdf.set_xy(26, 113)
    pdf.multi_cell(136, 4,
        '"I sat at RBC building dashboards that 50 executives used every day. '
        'I watched them squint at numbers and miss signals. I built this because I lived the problem."')

    # The Ask
    pdf.section_title(W // 2 + 4, 42, "The Ask: $500K Pre-Seed")
    ask_items = [
        ("40%", "Biometric Validation",  "N=150 studies (HRV, EEG, eye tracking)",    INDIGO),
        ("35%", "Engineering",           "NTL API + developer SDK",                    SKY),
        ("15%", "Pilots",                "3 enterprise partnerships",                  VIOLET),
        ("10%", "Operations",            "12 months runway",                           GREEN),
    ]
    ay2 = 58
    for pct, title, detail, color in ask_items:
        # percent bar
        bar_w = float(pct.replace("%","")) * 1.0
        pdf.fill(*color)
        pdf.rect(W // 2 + 4, ay2 + 1, bar_w, 5, style="F")
        pdf.ink(*color)
        pdf.set_font(SANS, "B", 8)
        pdf.set_xy(W // 2 + 4 + bar_w + 3, ay2)
        pdf.cell(0, 5, pct + "  " + title)
        pdf.ink(*MUTED)
        pdf.set_font(SANS, "", 6.5)
        pdf.set_xy(W // 2 + 4 + bar_w + 3, ay2 + 5.5)
        pdf.cell(0, 4, detail)
        ay2 += 16

    # closing quote
    pdf.bg_rect(W // 2 + 4, 122, 124, 24, CARD)
    pdf.gradient_bar(W // 2 + 4, 122, 124, 2, INDIGO, SKY)
    pdf.ink(*SUBTLE)
    pdf.set_font(SANS, "I", 8)
    pdf.set_xy(W // 2 + 10, 128)
    pdf.multi_cell(112, 4.5,
        "Between black (0) and white (1), there are infinite colors.\n"
        "That's where intelligence becomes human.")

    # contact
    pdf.ink(*INDIGO)
    pdf.set_font(MONO, "", 7)
    pdf.set_xy(W // 2 + 4, 150)
    pdf.cell(0, 4.5, "nishanalyzedata@gmail.com")
    pdf.set_xy(W // 2 + 4, 155)
    pdf.cell(0, 4.5, "linkedin.com/in/nisha-sapkota-aidata")
    pdf.set_xy(W // 2 + 4, 160)
    pdf.cell(0, 4.5, "github.com/nisha22sapkota/feel-the-model")

    pdf.bg_rect(0, H - 14, W, 14, SURFACE)
    pdf.ink(*MUTED)
    pdf.set_font(MONO, "", 6)
    pdf.set_xy(18, H - 9)
    pdf.cell(0, 4, "BETWEEN 0 AND 1(TM)  -  FEEL-THE-MODEL(TM)  -  CONFIDENTIAL")
    pdf.set_xy(W - 30, H - 9)
    pdf.cell(18, 4, "5 / 5", align="R")

    # ?? save ??????????????????????????????????????????????????????????????????
    out = "feel_the_model_investor_deck.pdf"
    pdf.output(out)
    print(f"Saved: {out}")


if __name__ == "__main__":
    build()
