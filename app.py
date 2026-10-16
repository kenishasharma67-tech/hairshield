"""
HairShield - Smart Response. Cleaner Seas.
A DUMMY (simulated) oil-spill monitoring dashboard for a school science exhibition.

IMPORTANT: This app does NOT analyse the uploaded picture. The uploaded image is
only shown as a preview. Every image gives the same fixed, pre-written result.
"""

import base64
import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, UnidentifiedImageError

# ----------------------------------------------------------------------------
# PAGE SETUP
# ----------------------------------------------------------------------------
st.set_page_config(page_title="HairShield", page_icon="🌊", layout="centered")

# ----------------------------------------------------------------------------
# FIXED DATA (single source for graph, table, cards and progress)
# ----------------------------------------------------------------------------
DATA = pd.DataFrame(
    {
        "time": [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0],
        "contained": [250, 210, 160, 90, 40, 15, 2],
        "uncontained": [1000, 820, 550, 280, 110, 35, 8],
        "status": [
            "Oil spilled into the water",
            "Hair mat introduced to the spill",
            "Rapid oil soaking observed",
            "Visible clearing of the water patch",
            "Hair mat turning dark",
            "Minor oil traces remain",
            "Clear water surface achieved",
        ],
    }
)
LAST = len(DATA) - 1  # index of the final row (5.0 min)

CONFIDENCE = "96%"
OIL_QTY = "5 mL"
START_CONTAINED = int(DATA.loc[0, "contained"])
START_UNCONTAINED = int(DATA.loc[0, "uncontained"])

# ----------------------------------------------------------------------------
# SESSION STATE (keeps things stable between button clicks)
# ----------------------------------------------------------------------------
# stage: 0 = detection, 1 = boom deployed, 2 = mat deployed, 3 = verification
for key, default in {"stage": 0, "idx": 0, "img_raw": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def deploy_boom():
    st.session_state.stage = 1


def deploy_mat():
    st.session_state.stage = 2


def start_verification():
    st.session_state.stage = 3
    st.session_state.idx = 0


def advance():
    st.session_state.idx = min(LAST, st.session_state.idx + 1)


def skip_to_final():
    st.session_state.stage = 3
    st.session_state.idx = LAST


def reset_demo():
    st.session_state.stage = 0
    st.session_state.idx = 0


# ----------------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------------
CSS = """
#MainMenu, footer {visibility: hidden;}
.stApp {
    background: radial-gradient(circle at 50% 0%, #0f3a66 0%, #071a33 45%, #040d1c 100%);
    color: #eaf6ff;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}
.block-container {max-width: 560px; padding-top: 1.5rem; padding-bottom: 3rem;}
.hs-title {text-align:center; font-size: 2.4rem; font-weight: 800; letter-spacing: 1px;
    background: linear-gradient(90deg, #7fe7ff, #2ea8ff); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; margin: 0; line-height: 1.1;}
.hs-tag {text-align:center; color:#9fd3f0; font-style: italic; margin: 2px 0 10px 0;}
.hs-status {text-align:center; font-size: .78rem; letter-spacing: 2px; color:#5dffb0;
    border: 1px solid rgba(93,255,176,.45); border-radius: 999px; padding: 6px 12px;
    background: rgba(93,255,176,.07); box-shadow: 0 0 14px rgba(93,255,176,.18);
    width: fit-content; margin: 0 auto 18px auto;}
.hs-section {font-size: .8rem; letter-spacing: 2px; color:#7fe7ff; margin: 22px 0 8px 0;
    font-weight: 700;}
.hs-card {background: linear-gradient(160deg, rgba(20,70,120,.55), rgba(8,28,58,.85));
    border: 1px solid rgba(80,200,255,.40); border-radius: 18px; padding: 16px;
    box-shadow: 0 0 22px rgba(46,168,255,.18), inset 0 0 18px rgba(80,200,255,.06);}
.hs-card-head {display:flex; justify-content:space-between; align-items:center;
    margin-bottom: 12px; gap: 8px; flex-wrap: wrap;}
.hs-card-title {font-weight: 800; letter-spacing: 1.5px; font-size: 1rem; color:#ffffff;}
.hs-demo {font-size:.62rem; letter-spacing:1.5px; color:#ffd166; border:1px solid #ffd166;
    border-radius: 999px; padding: 3px 9px; background: rgba(255,209,102,.08);}
.hs-img {width:100%; border-radius: 14px; border: 1px solid rgba(80,200,255,.5);
    display:block; max-height: 300px; object-fit: cover;}
.hs-placeholder {border: 2px dashed rgba(80,200,255,.5); border-radius: 14px; padding: 38px 12px;
    text-align:center; color:#9fd3f0; letter-spacing: 1.5px; font-size:.85rem;
    background: rgba(8,28,58,.5);}
.hs-chips {display:flex; gap:8px; flex-wrap:wrap; margin: 12px 0;}
.chip {font-size:.72rem; font-weight:700; letter-spacing:1px; padding:6px 11px;
    border-radius: 999px; border: 1px solid;}
.chip-cyan {color:#7fe7ff; border-color:#7fe7ff; background: rgba(127,231,255,.10);}
.chip-red {color:#ff6b6b; border-color:#ff6b6b; background: rgba(255,107,107,.12);
    box-shadow: 0 0 12px rgba(255,107,107,.3);}
.chip-green {color:#5dffb0; border-color:#5dffb0; background: rgba(93,255,176,.12);
    box-shadow: 0 0 12px rgba(93,255,176,.3);}
.chip-yellow {color:#ffd166; border-color:#ffd166; background: rgba(255,209,102,.12);}
.chip-grey {color:#8aa4bd; border-color:#4b6580; background: rgba(75,101,128,.15);}
.hs-grid {display:grid; grid-template-columns: 1fr 1fr; gap: 10px;}
.metric {background: rgba(5,20,42,.7); border: 1px solid rgba(80,200,255,.28);
    border-radius: 14px; padding: 11px 12px;}
.metric .lbl {font-size:.62rem; letter-spacing:1.3px; color:#8fc4e6;}
.metric .val {font-size:1.45rem; font-weight:800; color:#ffffff; line-height:1.25;}
.metric .sub {font-size:.64rem; color:#7fa6c4;}
.metric.red .val {color:#ff6b6b;}
.metric.green .val {color:#5dffb0;}
.metric.cyan .val {color:#7fe7ff;}
.reco {margin-top: 12px; border: 1px solid rgba(255,209,102,.5); border-radius: 14px;
    background: rgba(255,209,102,.07); padding: 11px 13px;}
.reco .lbl {font-size:.62rem; letter-spacing:1.5px; color:#ffd166;}
.reco .txt {font-weight:700; color:#fff;}
.steps {display:flex; gap:6px; margin: 4px 0 12px 0;}
.step {flex:1; text-align:center; font-size:.62rem; letter-spacing:.8px; padding:7px 2px;
    border-radius: 10px; border:1px solid #35516e; color:#6f8fae; background: rgba(5,20,42,.6);}
.step.done {color:#5dffb0; border-color:#5dffb0;}
.step.now {color:#7fe7ff; border-color:#7fe7ff; box-shadow: 0 0 12px rgba(127,231,255,.35);}
.explain {color:#cfe9f8; font-size:.9rem; margin-top: 10px; line-height:1.45;}
.pbar {height: 12px; border-radius: 999px; background: rgba(5,20,42,.9);
    border: 1px solid rgba(80,200,255,.35); overflow:hidden; margin-top: 6px;}
.pbar > div {height:100%; background: linear-gradient(90deg, #2ea8ff, #5dffb0);
    border-radius: 999px;}
.plabel {display:flex; justify-content:space-between; font-size:.72rem; color:#9fd3f0;
    letter-spacing:1px;}
table.tl {width:100%; border-collapse: collapse; font-size:.78rem;}
table.tl th {color:#7fe7ff; font-size:.62rem; letter-spacing:1px; text-align:left;
    padding: 6px 5px; border-bottom: 1px solid rgba(80,200,255,.4);}
table.tl td {padding: 7px 5px; border-bottom: 1px solid rgba(80,200,255,.12); color:#cfe9f8;}
table.tl tr.done td {color:#ffffff;}
table.tl tr.now td {background: rgba(46,168,255,.22); color:#fff; font-weight:700;}
table.tl tr.pending td {color:#6f8fae;}
.final {text-align:center; padding: 20px 14px; border-radius: 18px;}
.final.ok {border: 1px solid #5dffb0; background: linear-gradient(160deg, rgba(20,110,80,.45), rgba(8,40,40,.85));
    box-shadow: 0 0 28px rgba(93,255,176,.35);}
.final.wait {border: 1px dashed #4b6580; background: rgba(5,20,42,.6); color:#6f8fae;}
.final .big {font-size: 1.15rem; font-weight: 800; letter-spacing: 1.5px; color:#5dffb0;}
.final .small {font-size:.82rem; color:#cfe9f8; margin-top:6px;}
.note {font-size:.7rem; color:#7fa6c4; margin-top:8px; line-height:1.4;}
.stButton > button {width:100%; border-radius: 14px; font-weight:800; letter-spacing:1.5px;
    padding: .7rem 1rem; border: 1px solid #7fe7ff; color:#04122a;
    background: linear-gradient(90deg, #7fe7ff, #2ea8ff);
    box-shadow: 0 0 18px rgba(46,168,255,.45);}
.stButton > button:hover {border-color:#fff; color:#04122a; filter: brightness(1.1);}
.stButton > button:disabled {background:#1a2f48; color:#5f7d9a; border-color:#35516e; box-shadow:none;}
[data-testid="stFileUploader"] section {background: rgba(8,28,58,.7);
    border: 1px dashed rgba(80,200,255,.6); border-radius: 14px;}
[data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span {color:#cfe9f8 !important;}
"""
st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)


def html(s: str):
    """Render HTML safely: remove leading spaces so Markdown doesn't treat it as code."""
    flat = " ".join(line.strip() for line in s.strip().splitlines())
    st.markdown(flat, unsafe_allow_html=True)


def fmt(v) -> str:
    return f"{int(v):,} cm²"


def image_to_data_uri(raw: bytes) -> str:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img.thumbnail((900, 900))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ----------------------------------------------------------------------------
# 1 + 2. HEADER & STATUS
# ----------------------------------------------------------------------------
html("""<div class="hs-title">🌊 HairShield</div>
<div class="hs-tag">Smart Response. Cleaner Seas.</div>
<div class="hs-status">● OCEAN MONITORING SYSTEM ONLINE</div>""")

# ----------------------------------------------------------------------------
# 3. IMAGE UPLOAD
# ----------------------------------------------------------------------------
html('<div class="hs-section">📡 IMAGE UPLOAD</div>')
uploaded = st.file_uploader(
    "Upload oil spill image",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed",
)
if uploaded is not None:
    try:
        raw = uploaded.getvalue()
        Image.open(io.BytesIO(raw)).verify()  # checks the file is a real image
        if raw != st.session_state.img_raw:
            st.session_state.img_raw = raw
            st.session_state.stage = 0  # new image -> restart the demo
            st.session_state.idx = 0
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        st.error("⚠️ That file could not be read as an image. Please upload a JPG or PNG.")

has_image = st.session_state.img_raw is not None
stage = st.session_state.stage
idx = st.session_state.idx
complete = stage == 3 and idx == LAST

# Current (simulated) values shown on the cards
if stage == 3:
    cur_c = int(DATA.loc[idx, "contained"])
    cur_u = int(DATA.loc[idx, "uncontained"])
else:
    cur_c, cur_u = START_CONTAINED, START_UNCONTAINED

# ----------------------------------------------------------------------------
# 4 + 5. AI OIL SPILL ANALYSIS CARD (centrepiece)
# ----------------------------------------------------------------------------
html('<div class="hs-section">🧠 ANALYSIS</div>')

if has_image:
    try:
        img_html = f'<img class="hs-img" src="{image_to_data_uri(st.session_state.img_raw)}"/>'
    except Exception:
        img_html = '<div class="hs-placeholder">IMAGE PREVIEW UNAVAILABLE</div>'
    chips = """<div class="hs-chips">
        <span class="chip chip-cyan">✔ IMAGE RECEIVED</span>
        <span class="chip chip-red">⚠ OIL SPILL DETECTED</span>
        <span class="chip chip-yellow">SIMULATED DETECTION</span></div>"""
    area_class = "green" if complete else "red"
    area_note = "simulated · current" if stage == 3 else "simulated · initial"
    metrics = f"""<div class="hs-grid">
        <div class="metric cyan"><div class="lbl">DEMO CONFIDENCE</div>
            <div class="val">{CONFIDENCE}</div><div class="sub">fixed demo value</div></div>
        <div class="metric cyan"><div class="lbl">SIMULATED OIL QUANTITY</div>
            <div class="val">{OIL_QTY}</div><div class="sub">demo value</div></div>
        <div class="metric {area_class}"><div class="lbl">AREA · WITH CONTAINMENT</div>
            <div class="val">{fmt(cur_c)}</div><div class="sub">{area_note}</div></div>
        <div class="metric {area_class}"><div class="lbl">AREA · NO CONTAINMENT</div>
            <div class="val">{fmt(cur_u)}</div><div class="sub">{area_note}</div></div>
    </div>
    <div class="reco"><div class="lbl">RECOMMENDED RESPONSE</div>
        <div class="txt">Deploy hair booms, followed by hair mesh mats.</div></div>"""
else:
    img_html = '<div class="hs-placeholder">UPLOAD OIL SPILL IMAGE TO BEGIN ANALYSIS</div>'
    chips = '<div class="hs-chips"><span class="chip chip-grey">AWAITING IMAGE</span></div>'
    metrics = ""

html(f"""<div class="hs-card">
    <div class="hs-card-head"><span class="hs-card-title">AI OIL SPILL ANALYSIS</span>
        <span class="hs-demo">SIMULATION MODE · DEMO DATA</span></div>
    {img_html}{chips}{metrics}
    <div class="note">The picture is only a preview. The app does not measure anything from it —
    every image gives the same pre-set demo result.</div>
</div>""")

# ----------------------------------------------------------------------------
# 6 + 7. RESPONSE CONTROLS & STAGE
# ----------------------------------------------------------------------------
html('<div class="hs-section">🛟 RESPONSE CONTROL</div>')

labels = ["DETECT", "CONTAIN", "ABSORB", "VERIFY"]
step_html = ""
for i, name in enumerate(labels):
    if not has_image:
        cls = ""
    elif complete or i < stage:
        cls = "done"
    elif i == stage:
        cls = "now"
    else:
        cls = ""
    step_html += f'<div class="step {cls}">{i + 1}. {name}</div>'
html(f'<div class="steps">{step_html}</div>')

if not has_image:
    st.button("DEPLOY HAIR BOOM", disabled=True, key="b_disabled")
elif stage == 0:
    st.button("DEPLOY HAIR BOOM", on_click=deploy_boom, key="b_boom")
elif stage == 1:
    st.button("DEPLOY HAIR MAT", on_click=deploy_mat, key="b_mat")
elif stage == 2:
    st.button("START CLEANUP VERIFICATION", on_click=start_verification, key="b_verify")
elif stage == 3 and not complete:
    c1, c2 = st.columns(2)
    c1.button("NEXT READING ▶", on_click=advance, key="b_next")
    c2.button("SKIP TO FINAL ⏭", on_click=skip_to_final, key="b_skip")

if has_image and stage > 0:
    st.button("↺ RESET DEMO", on_click=reset_demo, key="b_reset")

# Stage status chip + explanation
if has_image:
    if stage == 0:
        chip = '<span class="chip chip-red">⚠ OIL SPILL DETECTED</span>'
        text = ("Stage 1 — Detection: a simulated oil spill has been detected. "
                f"Initial spill area: {fmt(START_CONTAINED)} with containment, "
                f"{fmt(START_UNCONTAINED)} without containment.")
    elif stage == 1:
        chip = '<span class="chip chip-cyan">🛡 HAIR BOOM DEPLOYED</span>'
        text = ("Stage 2 — Containment: the hair boom forms a floating barrier around "
                "the spill, stopping the oil from spreading across the water.")
    elif stage == 2:
        chip = '<span class="chip chip-cyan">🧽 HAIR MAT DEPLOYED</span>'
        text = ("Stage 3 — Absorption: the hair mesh mat is placed on the contained "
                "patch and absorbs the remaining floating oil.")
    elif not complete:
        chip = '<span class="chip chip-yellow">⏳ CLEANUP VERIFICATION IN PROGRESS</span>'
        text = (f"Stage 4 — Verification: mock reading at {DATA.loc[idx, 'time']:.1f} min — "
                f"{DATA.loc[idx, 'status']}.")
    else:
        chip = '<span class="chip chip-green">✔ SPILL CONTROLLED — CLEANUP SUCCESSFUL</span>'
        text = (f"Stage 4 — Verification complete: mock reading at 5.0 min — "
                f"{DATA.loc[LAST, 'status']}.")

    # progress: based on contained-area reduction once verification starts
    if stage == 3:
        pct = round((START_CONTAINED - cur_c) / START_CONTAINED * 100)
    else:
        pct = 0
    html(f"""<div class="hs-card">
        <div class="hs-chips" style="margin-top:0">{chip}</div>
        <div class="plabel"><span>CLEANUP PROGRESS (MOCK DATA)</span><span>{pct}%</span></div>
        <div class="pbar"><div style="width:{pct}%"></div></div>
        <div class="explain">{text}</div></div>""")

# ----------------------------------------------------------------------------
# 8. GRAPH
# ----------------------------------------------------------------------------
html('<div class="hs-section">📉 CLEANUP GRAPH</div>')

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=DATA["time"], y=DATA["contained"], name="Contained Boom",
    mode="lines+markers", line=dict(color="#5dffb0", width=3), marker=dict(size=8),
    hovertemplate="<b>Contained Boom</b><br>%{x} min<br>%{y} cm²<extra></extra>"))
fig.add_trace(go.Scatter(
    x=DATA["time"], y=DATA["uncontained"], name="Uncontained Free Spread",
    mode="lines+markers", line=dict(color="#ff6b6b", width=3), marker=dict(size=8),
    hovertemplate="<b>Uncontained Free Spread</b><br>%{x} min<br>%{y} cm²<extra></extra>"))
if stage == 3:  # highlight the current reading
    t = DATA.loc[idx, "time"]
    fig.add_trace(go.Scatter(
        x=[t, t], y=[DATA.loc[idx, "contained"], DATA.loc[idx, "uncontained"]],
        mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(size=15, color="rgba(0,0,0,0)", line=dict(color="#ffffff", width=3))))
fig.update_layout(
    title=dict(text="Oil Spill Area Reduction During Cleanup", font=dict(size=14, color="#eaf6ff")),
    paper_bgcolor="#071a33", plot_bgcolor="#0a2447",
    font=dict(color="#cfe9f8"), height=360, margin=dict(l=10, r=10, t=50, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=-0.38, x=0),
    hovermode="x unified",
    xaxis=dict(title="Elapsed Time (minutes)", gridcolor="#143a66", zeroline=False),
    yaxis=dict(title="Spill Area (cm²)", gridcolor="#143a66", zeroline=False),
)
try:
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.plotly_chart(fig, width="stretch")
html('<div class="note">Graph shows simulated data for the exhibition (mock cleanup data), '
     'not verified experimental results.</div>')

# ----------------------------------------------------------------------------
# 9. TIMELINE
# ----------------------------------------------------------------------------
html('<div class="hs-section">🕒 CLEANUP MONITORING TIMELINE</div>')
rows = ""
for i, r in DATA.iterrows():
    if stage == 3 and i < idx or complete:
        cls = "done"
    elif stage == 3 and i == idx:
        cls = "now"
    else:
        cls = ""
    if complete and i == LAST:
        cls = "now"
    rows += (f'<tr class="{cls}"><td>{r["time"]:.1f} min</td><td>{fmt(r["contained"])}</td>'
             f'<td>{fmt(r["uncontained"])}</td><td>{r["status"]}</td></tr>')
html(f"""<div class="hs-card" style="padding:10px"><table class="tl">
    <tr><th>TIME</th><th>CONTAINED</th><th>UNCONTAINED</th><th>STATUS</th></tr>
    {rows}</table></div>
    <div class="note">MOCK CLEANUP DATA — the highlighted row follows your demo progress.</div>""")

# ----------------------------------------------------------------------------
# 10. FINAL RESULT
# ----------------------------------------------------------------------------
html('<div class="hs-section">🏁 FINAL RESULT</div>')
if complete:
    red_c = round((1 - DATA.loc[LAST, "contained"] / START_CONTAINED) * 100, 1)
    red_u = round((1 - DATA.loc[LAST, "uncontained"] / START_UNCONTAINED) * 100, 1)
    html(f"""<div class="final ok"><div class="big">✔ SPILL CONTROLLED — CLEANUP SUCCESSFUL</div>
        <div class="small">Contained: {fmt(START_CONTAINED)} → {fmt(DATA.loc[LAST, 'contained'])}
        ({red_c}% smaller) &nbsp;|&nbsp; Uncontained: {fmt(START_UNCONTAINED)} →
        {fmt(DATA.loc[LAST, 'uncontained'])} ({red_u}% smaller)</div>
        <div class="note">Simulated demonstration result. Real AI detection and real-world
        measurements can be added in a future version.</div></div>""")
else:
    html("""<div class="final wait">FINAL RESULT PENDING — complete the cleanup stages above.</div>""")

html('<div class="note" style="text-align:center;margin-top:24px">HairShield · '
     'SIMULATION MODE · All values are fixed demo data, not real AI predictions.</div>')
