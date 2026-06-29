import csv
import io
import streamlit as st
import pandas as pd
from attribution import parse_journeys, compute_median_hours, compute_credits, build_results

st.set_page_config(
    page_title="Contributors Analysis — Rocket Lab",
    page_icon="https://i.imgur.com/placeholder.png",
    layout="wide",
)

# ── Rocket Lab design tokens ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800;900&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Hide Streamlit default header */
#MainMenu, footer, header { visibility: hidden; }

/* App background */
.stApp {
    background-color: #17191C;
}

/* Custom header */
.rl-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 28px 0 8px 0;
    border-bottom: 1px solid #2A2D32;
    margin-bottom: 32px;
}
.rl-logo-slash {
    font-size: 32px;
    font-weight: 900;
    color: #7865E5;
    line-height: 1;
    letter-spacing: -1px;
}
.rl-header-text h1 {
    font-size: 20px;
    font-weight: 800;
    color: #FFFFFF;
    margin: 0;
    letter-spacing: -0.3px;
}
.rl-header-text p {
    font-size: 12px;
    font-weight: 400;
    color: #565D66;
    margin: 2px 0 0 0;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #1E2125 !important;
    border: 1px solid #2A2D32 !important;
    border-radius: 16px !important;
    padding: 20px 24px !important;
}
[data-testid="metric-container"] label {
    color: #565D66 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-size: 28px !important;
    font-weight: 800 !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    color: #6CD8CE !important;
    font-size: 12px !important;
}

/* Section labels */
.rl-section-label {
    font-size: 11px;
    font-weight: 700;
    color: #7865E5;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 8px;
}
.rl-section-title {
    font-size: 18px;
    font-weight: 800;
    color: #FFFFFF;
    margin-bottom: 4px;
    letter-spacing: -0.2px;
}
.rl-section-sub {
    font-size: 13px;
    color: #565D66;
    margin-bottom: 24px;
}

/* Slider */
[data-testid="stSlider"] label {
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}
[data-testid="stSlider"] p {
    color: #FFFFFF !important;
}
.stSlider > div > div > div {
    background: #7865E5 !important;
}

/* Param card */
.rl-param-card {
    background: #1E2125;
    border: 1px solid #2A2D32;
    border-radius: 16px;
    padding: 20px 24px;
}
.rl-param-card .label {
    font-size: 11px;
    font-weight: 700;
    color: #565D66;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}
.rl-param-card .value {
    font-size: 28px;
    font-weight: 800;
    color: #7865E5;
}
.rl-param-card .desc {
    font-size: 12px;
    color: #565D66;
    margin-top: 6px;
    line-height: 1.5;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    border: 1px solid #2A2D32 !important;
}
[data-testid="stDataFrame"] table {
    background: #1E2125 !important;
}
[data-testid="stDataFrame"] thead tr th {
    background: #17191C !important;
    color: #565D66 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    border-bottom: 1px solid #2A2D32 !important;
}
[data-testid="stDataFrame"] tbody tr td {
    color: #FFFFFF !important;
    border-bottom: 1px solid #2A2D32 !important;
    font-size: 13px !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: #2A2D32 !important;
}

/* Divider */
hr {
    border-color: #2A2D32 !important;
    margin: 28px 0 !important;
}

/* Upload area */
[data-testid="stFileUploader"] {
    border: 1px dashed #2A2D32 !important;
    border-radius: 16px !important;
    background: #1E2125 !important;
    padding: 8px !important;
}
[data-testid="stFileUploader"] label {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}
[data-testid="stFileUploader"] small {
    color: #565D66 !important;
}

/* Download button */
[data-testid="stDownloadButton"] button {
    background: #7865E5 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    padding: 10px 20px !important;
    letter-spacing: 0.3px !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: #5A47CC !important;
}

/* Spinner */
[data-testid="stSpinner"] { color: #7865E5 !important; }

/* Upload drop state */
[data-testid="stFileUploaderDropzoneInput"] + div {
    color: #565D66 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="rl-header">
    <div class="rl-logo-slash">R/</div>
    <div class="rl-header-text">
        <h1>Contributors Analysis</h1>
        <p>Time Decay Attribution · Rocket Lab</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────
st.markdown('<div class="rl-section-label">Dataset</div>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "Subí el CSV de installs exportado desde AppsFlyer",
    type="csv",
    help="Formato estándar de AppsFlyer con columnas: AppsFlyer ID, Media Source, Attributed Touch Time, Contributor 1/2/3 Media Source, Contributor 1/2/3 Touch Time, Install Time."
)

if not uploaded:
    st.markdown("""
    <div style="margin-top:40px; padding:32px; background:#1E2125; border:1px solid #2A2D32;
                border-radius:16px; text-align:center;">
        <div style="font-size:13px; color:#565D66; line-height:1.8;">
            Subí un CSV de installs de AppsFlyer para ver la distribución de crédito<br>
            entre <span style="color:#7865E5; font-weight:700;">Last Touch</span> y
            <span style="color:#6592FF; font-weight:700;">Time Decay</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Parse ─────────────────────────────────────────────────────────────────────
with st.spinner("Parseando journeys..."):
    content = uploaded.read().decode("utf-8-sig")
    reader  = csv.DictReader(io.StringIO(content))
    rows    = list(reader)
    journeys, skipped = parse_journeys(rows)

total      = len(journeys)
multitouch = sum(1 for j in journeys.values() if j["contributors"])
single     = total - multitouch
median_h   = compute_median_hours(journeys)

# ── Stats ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="rl-section-label" style="margin-top:8px;">Overview</div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total installs", f"{total:,}")
col2.metric("Multitouch", f"{multitouch:,}", f"{multitouch/total*100:.1f}%")
col3.metric("Single touch", f"{single:,}", f"{single/total*100:.1f}%")
col4.metric("Post-install filtrados", f"{skipped:,}")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Params ────────────────────────────────────────────────────────────────────
st.markdown('<div class="rl-section-label">Parámetros del modelo</div>', unsafe_allow_html=True)
st.markdown('<div class="rl-section-sub">LAST_TOUCH_HALF_LIFE se calcula automáticamente como la mediana de horas del dataset. HALF_LIFE es configurable.</div>', unsafe_allow_html=True)

col_slider, col_median = st.columns([3, 1])

with col_slider:
    half_life = st.slider(
        "HALF_LIFE — decay de contributors (horas)",
        min_value=1, max_value=72, value=24, step=1,
        help="Cuánto peso pierde un contributor según su distancia al install. Bajo = decay agresivo, alto = decay suave."
    )

with col_median:
    st.markdown(f"""
    <div class="rl-param-card">
        <div class="label">LAST_TOUCH_HALF_LIFE</div>
        <div class="value">{median_h:.1f}h</div>
        <div class="desc">Mediana del dataset — se ajusta automáticamente por cliente.</div>
    </div>
    """, unsafe_allow_html=True)

last_touch_half_life = median_h

# ── Compute ───────────────────────────────────────────────────────────────────
lt_credits, td_credits = compute_credits(journeys, half_life, last_touch_half_life)
results = build_results(lt_credits, td_credits)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Results ───────────────────────────────────────────────────────────────────
st.markdown(f'<div class="rl-section-label">Resultados</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="rl-section-title">Distribución de crédito por canal</div>'
    f'<div class="rl-section-sub">HALF_LIFE = {half_life}h · LAST_TOUCH_HALF_LIFE = {median_h:.1f}h · '
    f'<span style="color:#6CD8CE">▲ subestimado por AppsFlyer</span> · '
    f'<span style="color:#FF6C8E">▼ sobreestimado por AppsFlyer</span></div>',
    unsafe_allow_html=True
)

df = pd.DataFrame(results)
df.columns = ["Canal", "LT Installs", "LT %", "TD %", "Δ pp", "Var %"]

def fmt_delta(val):
    if val > 0.01:
        return f"▲ +{val:.2f}pp"
    elif val < -0.01:
        return f"▼ {val:.2f}pp"
    return f"= {val:.2f}pp"

def fmt_var(val):
    return f"{'+' if val > 0 else ''}{val:.1f}%"

def color_delta(val):
    if "▲" in str(val):
        return "color: #6CD8CE; font-weight: 700"
    elif "▼" in str(val):
        return "color: #FF6C8E; font-weight: 700"
    return "color: #565D66"

styled = (
    df.style
    .format({
        "LT Installs": "{:,.0f}",
        "LT %": "{:.2f}%",
        "TD %": "{:.2f}%",
        "Δ pp": fmt_delta,
        "Var %": fmt_var,
    })
    .applymap(color_delta, subset=["Δ pp"])
    .set_properties(**{"background-color": "#1E2125", "color": "#FFFFFF"})
    .set_table_styles([
        {"selector": "thead th", "props": [
            ("background-color", "#17191C"),
            ("color", "#565D66"),
            ("font-size", "11px"),
            ("font-weight", "700"),
            ("text-transform", "uppercase"),
            ("letter-spacing", "0.8px"),
        ]},
        {"selector": "tbody tr:hover td", "props": [("background-color", "#2A2D32")]},
    ])
)

st.dataframe(styled, use_container_width=True, height=520)

# ── Download ──────────────────────────────────────────────────────────────────
csv_out = df.to_csv(index=False)
st.download_button(
    "Descargar resultados CSV",
    data=csv_out,
    file_name="attribution_results.csv",
    mime="text/csv",
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:48px; padding-top:20px; border-top:1px solid #2A2D32;
            display:flex; justify-content:space-between; align-items:center;">
    <span style="font-size:12px; color:#2A2D32; font-weight:900; letter-spacing:-0.5px;">R/</span>
    <span style="font-size:11px; color:#2A2D32;">The App Growth Hub · An MiQ Company</span>
</div>
""", unsafe_allow_html=True)
