import csv
import io
import streamlit as st
import pandas as pd
from attribution import parse_journeys, compute_median_hours, compute_credits, build_results

st.set_page_config(
    page_title="Contributors Analysis — Rocket Lab",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
#MainMenu, footer { visibility: hidden; }
.rl-header { padding: 8px 0 24px 0; border-bottom: 1px solid #2A2D32; margin-bottom: 24px; }
.rl-slash { font-size: 28px; font-weight: 900; color: #7865E5; display: inline; }
.rl-title { font-size: 20px; font-weight: 800; color: #FFFFFF; display: inline; margin-left: 10px; }
.rl-sub { font-size: 11px; color: #565D66; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
.rl-label { font-size: 11px; font-weight: 700; color: #7865E5; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.rl-card { background: #1E2125; border: 1px solid #2A2D32; border-radius: 16px; padding: 20px 24px; }
.rl-card .val { font-size: 28px; font-weight: 800; color: #7865E5; }
.rl-card .lbl { font-size: 11px; color: #565D66; text-transform: uppercase; letter-spacing: 0.8px; }
.rl-card .desc { font-size: 12px; color: #565D66; margin-top: 6px; line-height: 1.5; }
.rl-legend { font-size: 12px; color: #565D66; margin-bottom: 8px; }
.rl-footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid #2A2D32;
             font-size: 11px; color: #2A2D32; text-align: right; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="rl-header">
    <span class="rl-slash">R/</span>
    <span class="rl-title">Contributors Analysis</span>
    <div class="rl-sub">Time Decay Attribution &middot; Rocket Lab</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="rl-label">Dataset</div>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "Subí el CSV de installs exportado desde AppsFlyer",
    type="csv",
)

if not uploaded:
    st.stop()

with st.spinner("Parseando journeys..."):
    content = uploaded.read().decode("utf-8-sig")
    reader  = csv.DictReader(io.StringIO(content))
    rows    = list(reader)
    journeys, skipped = parse_journeys(rows)

total      = len(journeys)
multitouch = sum(1 for j in journeys.values() if j["contributors"])
single     = total - multitouch
median_h   = compute_median_hours(journeys)

st.markdown('<div class="rl-label" style="margin-top:16px;">Overview</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total installs",          f"{total:,}")
c2.metric("Multitouch",              f"{multitouch:,}",  f"{multitouch/total*100:.1f}%")
c3.metric("Single touch",            f"{single:,}",      f"{single/total*100:.1f}%")
c4.metric("Post-install filtrados",  f"{skipped:,}")

st.divider()

st.markdown('<div class="rl-label">Parámetros del modelo</div>', unsafe_allow_html=True)

col_s, col_m = st.columns([3, 1])
with col_s:
    half_life = st.slider(
        "HALF_LIFE — decay de contributors (horas)",
        min_value=1, max_value=72, value=24, step=1,
    )
with col_m:
    st.markdown(f"""
    <div class="rl-card">
        <div class="lbl">LAST_TOUCH_HALF_LIFE</div>
        <div class="val">{median_h:.1f}h</div>
        <div class="desc">Mediana del dataset — se ajusta automáticamente.</div>
    </div>
    """, unsafe_allow_html=True)

last_touch_half_life = median_h

lt_credits, td_credits = compute_credits(journeys, half_life, last_touch_half_life)
results = build_results(lt_credits, td_credits)

st.divider()

st.markdown('<div class="rl-label">Resultados</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="rl-legend">'
    f'HALF_LIFE = {half_life}h &nbsp;·&nbsp; LAST_TOUCH_HALF_LIFE = {median_h:.1f}h &nbsp;·&nbsp;'
    f'<span style="color:#6CD8CE">▲ subestimado</span> &nbsp;·&nbsp;'
    f'<span style="color:#FF6C8E">▼ sobreestimado</span>'
    f'</div>',
    unsafe_allow_html=True,
)

df = pd.DataFrame(results)
df.columns = ["Canal", "LT Installs", "LT %", "TD %", "Δ pp", "Var %"]

def fmt_delta(val):
    if val > 0.01:   return f"▲ +{val:.2f}pp"
    elif val < -0.01: return f"▼ {val:.2f}pp"
    return f"= {val:.2f}pp"

def fmt_var(val):
    return f"{'+' if val > 0 else ''}{val:.1f}%"

def color_delta(val):
    if "▲" in str(val): return "color: #6CD8CE; font-weight: 700"
    if "▼" in str(val): return "color: #FF6C8E; font-weight: 700"
    return "color: #565D66"

styled = (
    df.style
    .format({"LT Installs": "{:,.0f}", "LT %": "{:.2f}%", "TD %": "{:.2f}%",
             "Δ pp": fmt_delta, "Var %": fmt_var})
    .map(color_delta, subset=["Δ pp"])
)

st.dataframe(styled, use_container_width=True, height=520)

csv_out = df.to_csv(index=False)
st.download_button("Descargar resultados CSV", data=csv_out,
                   file_name="attribution_results.csv", mime="text/csv")

st.markdown('<div class="rl-footer">The App Growth Hub · An MiQ Company</div>',
            unsafe_allow_html=True)
