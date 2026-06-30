import csv
import io
import streamlit as st
import pandas as pd
import altair as alt
from collections import defaultdict
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
.rl-footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid #2A2D32; font-size: 11px; color: #2A2D32; text-align: right; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="rl-header">
    <span class="rl-slash">R/</span>
    <span class="rl-title">Contributors Analysis</span>
    <div class="rl-sub">Time Decay Attribution &middot; Rocket Lab</div>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────
st.markdown('<div class="rl-label">Dataset</div>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "Subí el CSV de installs (ya filtrado con filter_columns.py)",
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

# ── Overview ──────────────────────────────────────────────────────────────────
st.markdown('<div class="rl-label" style="margin-top:16px;">Overview</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total installs",         f"{total:,}")
c2.metric("Multitouch",             f"{multitouch:,}",  f"{multitouch/total*100:.1f}%")
c3.metric("Single touch",           f"{single:,}",      f"{single/total*100:.1f}%")
c4.metric("Post-install filtrados", f"{skipped:,}")

st.divider()

# ── Params ────────────────────────────────────────────────────────────────────
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
df = pd.DataFrame(results)
df.columns = ["Canal", "LT Installs", "LT %", "TD %", "Δ pp", "Var %"]

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
st.markdown('<div class="rl-label">Sobre y subestimados por AppsFlyer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="rl-legend">'
    '<span style="color:#6CD8CE">▲ subestimado</span> — recibe más crédito con Time Decay &nbsp;·&nbsp;'
    '<span style="color:#FF6C8E">▼ sobreestimado</span> — recibe menos crédito con Time Decay'
    '</div>',
    unsafe_allow_html=True,
)

df_chart = df[df["Δ pp"].abs() > 0.01].copy()
df_chart["color"] = df_chart["Δ pp"].apply(lambda x: "#6CD8CE" if x > 0 else "#FF6C8E")
df_chart["label"] = df_chart["Δ pp"].apply(lambda x: f"+{x:.2f}pp" if x > 0 else f"{x:.2f}pp")
df_chart = df_chart.sort_values("Δ pp")

chart_delta = (
    alt.Chart(df_chart)
    .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
    .encode(
        x=alt.X("Δ pp:Q", title="Delta (Time Decay − Last Touch) en pp",
                axis=alt.Axis(labelColor="#565D66", titleColor="#565D66", gridColor="#2A2D32")),
        y=alt.Y("Canal:N", sort="-x", title=None,
                axis=alt.Axis(labelColor="#FFFFFF", labelFontSize=12)),
        color=alt.Color("color:N", scale=None, legend=None),
        tooltip=[
            alt.Tooltip("Canal:N", title="Canal"),
            alt.Tooltip("LT %:Q", title="Last Touch %", format=".2f"),
            alt.Tooltip("TD %:Q", title="Time Decay %", format=".2f"),
            alt.Tooltip("Δ pp:Q", title="Delta pp", format="+.2f"),
            alt.Tooltip("Var %:Q", title="Variación %", format="+.1f"),
        ],
    )
    .properties(height=max(280, len(df_chart) * 32))
    .configure_view(fill="#1E2125", stroke=None)
    .configure_axis(domainColor="#2A2D32", tickColor="#2A2D32")
    .configure(background="#1E2125")
)

st.altair_chart(chart_delta, use_container_width=True)

st.divider()

# ── Results table ─────────────────────────────────────────────────────────────
st.markdown('<div class="rl-label">Tabla de resultados</div>', unsafe_allow_html=True)

def fmt_delta(val):
    if val > 0.01:    return f"▲ +{val:.2f}pp"
    elif val < -0.01: return f"▼ {val:.2f}pp"
    return f"= {val:.2f}pp"

def fmt_var(val):
    return f"{'+' if val > 0 else ''}{val:.1f}%"

def bg_delta(val):
    s = str(val)
    if "▲" in s: return "background-color: #0d2a1a; color: #6CD8CE; font-weight: 700"
    if "▼" in s: return "background-color: #2a0d14; color: #FF6C8E; font-weight: 700"
    return "color: #565D66"

styled = (
    df.style
    .format({
        "LT Installs": "{:,.0f}",
        "LT %":  "{:.2f}%",
        "TD %":  "{:.2f}%",
        "Δ pp":  fmt_delta,
        "Var %": fmt_var,
    })
    .map(bg_delta, subset=["Δ pp"])
)

st.dataframe(styled, use_container_width=True, height=420)

csv_out = df.to_csv(index=False)
st.download_button("Descargar resultados CSV", data=csv_out,
                   file_name="attribution_results.csv", mime="text/csv")

st.divider()

# ── Contributor analysis ──────────────────────────────────────────────────────
st.markdown('<div class="rl-label">Análisis de contributors</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="rl-legend">Canales que asisten el install sin llevarse el crédito en Last Touch. '
    'Solo journeys multitouch.</div>',
    unsafe_allow_html=True,
)

contrib_freq  = defaultdict(int)
contrib_hours = defaultdict(list)
contrib_pairs = defaultdict(int)   # (contributor, last_touch) → count

for j in journeys.values():
    if not j["contributors"]:
        continue
    seen = set()
    for c in j["contributors"]:
        ms = c["ms"]
        if ms in seen:
            continue
        seen.add(ms)
        contrib_freq[ms] += 1
        if c["hours"] is not None:
            contrib_hours[ms].append(c["hours"])
        contrib_pairs[(ms, j["last"])] += 1

# Top contributors por frecuencia
df_contrib = pd.DataFrame([
    {
        "Contributor": ms,
        "Veces asistió": cnt,
        "% del multitouch": round(cnt / multitouch * 100, 1) if multitouch else 0,
        "Horas promedio al install": round(sum(contrib_hours[ms]) / len(contrib_hours[ms]), 1)
            if contrib_hours[ms] else None,
    }
    for ms, cnt in sorted(contrib_freq.items(), key=lambda x: -x[1])
])

col_ca, col_cb = st.columns(2)

with col_ca:
    st.markdown("**Canales contributors más frecuentes**")
    chart_contrib = (
        alt.Chart(df_contrib.head(12))
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#7865E5")
        .encode(
            x=alt.X("Veces asistió:Q", title="Installs asistidos",
                    axis=alt.Axis(labelColor="#565D66", titleColor="#565D66", gridColor="#2A2D32")),
            y=alt.Y("Contributor:N", sort="-x", title=None,
                    axis=alt.Axis(labelColor="#FFFFFF", labelFontSize=11)),
            tooltip=[
                alt.Tooltip("Contributor:N"),
                alt.Tooltip("Veces asistió:Q", format=","),
                alt.Tooltip("% del multitouch:Q", format=".1f", title="% multitouch"),
                alt.Tooltip("Horas promedio al install:Q", format=".1f", title="Horas prom"),
            ],
        )
        .properties(height=320)
        .configure_view(fill="#1E2125", stroke=None)
        .configure_axis(domainColor="#2A2D32", tickColor="#2A2D32")
        .configure(background="#1E2125")
    )
    st.altair_chart(chart_contrib, use_container_width=True)

with col_cb:
    st.markdown("**Horas promedio antes del install por contributor**")
    df_hours = df_contrib[df_contrib["Horas promedio al install"].notna()].head(12)
    chart_hours = (
        alt.Chart(df_hours)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#6592FF")
        .encode(
            x=alt.X("Horas promedio al install:Q", title="Horas promedio antes del install",
                    axis=alt.Axis(labelColor="#565D66", titleColor="#565D66", gridColor="#2A2D32")),
            y=alt.Y("Contributor:N", sort="-x", title=None,
                    axis=alt.Axis(labelColor="#FFFFFF", labelFontSize=11)),
            tooltip=[
                alt.Tooltip("Contributor:N"),
                alt.Tooltip("Horas promedio al install:Q", format=".1f", title="Horas prom"),
                alt.Tooltip("Veces asistió:Q", format=","),
            ],
        )
        .properties(height=320)
        .configure_view(fill="#1E2125", stroke=None)
        .configure_axis(domainColor="#2A2D32", tickColor="#2A2D32")
        .configure(background="#1E2125")
    )
    st.altair_chart(chart_hours, use_container_width=True)

# Top pares contributor → last touch
st.markdown("**¿A quién asisten? — pares contributor → last touch más frecuentes**")
df_pairs = pd.DataFrame([
    {"Contributor": c, "Last Touch": lt, "Installs asistidos": cnt}
    for (c, lt), cnt in sorted(contrib_pairs.items(), key=lambda x: -x[1])
]).head(20)

chart_pairs = (
    alt.Chart(df_pairs)
    .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#6CD8CE")
    .encode(
        x=alt.X("Installs asistidos:Q",
                axis=alt.Axis(labelColor="#565D66", titleColor="#565D66", gridColor="#2A2D32")),
        y=alt.Y("Contributor:N", sort="-x", title=None,
                axis=alt.Axis(labelColor="#FFFFFF", labelFontSize=11)),
        color=alt.Color("Last Touch:N",
                        scale=alt.Scale(scheme="tableau10"),
                        legend=alt.Legend(labelColor="#FFFFFF", titleColor="#565D66",
                                          labelFontSize=11, titleFontSize=11)),
        tooltip=[
            alt.Tooltip("Contributor:N"),
            alt.Tooltip("Last Touch:N"),
            alt.Tooltip("Installs asistidos:Q", format=","),
        ],
    )
    .properties(height=380)
    .configure_view(fill="#1E2125", stroke=None)
    .configure_axis(domainColor="#2A2D32", tickColor="#2A2D32")
    .configure(background="#1E2125")
)
st.altair_chart(chart_pairs, use_container_width=True)

st.dataframe(df_contrib, use_container_width=True, hide_index=True)

st.markdown('<div class="rl-footer">The App Growth Hub · An MiQ Company</div>',
            unsafe_allow_html=True)
