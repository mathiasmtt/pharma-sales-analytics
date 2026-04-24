"""Dashboard Streamlit — Pharma Sales Analytics.

Ejecutar localmente:
    uv run streamlit run app/streamlit_app.py

Esperado en ``data/raw/``:
    salesdaily.csv, saleshourly.csv, salesmonthly.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Permite importar ``src`` cuando streamlit ejecuta desde /app.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analytics import (  # noqa: E402
    detectar_desvios,
    estacionalidad_hora_dow,
    kpis_por_categoria,
    pareto_productos,
    tendencia_mensual,
    yoy_por_categoria,
)
from src.data_loader import (  # noqa: E402
    ATC_CATEGORIES,
    ATC_DESCRIPTIONS,
    DatasetPaths,
    load_daily,
    load_hourly,
    load_monthly,
)
from src.reporting import build_excel_report, report_filename  # noqa: E402

st.set_page_config(
    page_title="Pharma Sales Analytics",
    page_icon="💊",
    layout="wide",
)

# ---------- Paleta corporativa Megalabs ----------
# Extraída del CSS de https://www.megalabs.com.uy/ (verde #149971 dominante).
MEGA_GREEN = "#149971"
MEGA_GREEN_DARK = "#0f7258"
MEGA_GREEN_LIGHT = "#4fb893"
MEGA_GRAY = "#d2d2d2"
MEGA_TEXT = "#32373c"

# Paleta cualitativa para gráficos multi-serie (tendencia mensual con 8 ATC).
MEGA_QUALITATIVE = [
    "#149971",  # verde Megalabs
    "#0f7258",  # verde oscuro
    "#4fb893",  # verde claro
    "#2c6e7f",  # teal
    "#e6a532",  # ámbar (contraste cálido)
    "#c0392b",  # rojo ladrillo
    "#7d6b91",  # violeta apagado
    "#545454",  # gris oscuro
]

# Escala secuencial verde para heatmaps (de claro a verde Megalabs).
MEGA_GREEN_SCALE = [
    [0.0, "#f0faf5"],
    [0.25, "#bfe4d3"],
    [0.5, "#7fc9a8"],
    [0.75, "#3faf7c"],
    [1.0, MEGA_GREEN],
]

# Escala divergente roja-blanco-verde para YoY (alineada a Megalabs en el positivo).
MEGA_DIVERGING = [
    [0.0, "#c0392b"],
    [0.5, "#f2f2f2"],
    [1.0, MEGA_GREEN],
]


@st.cache_data(show_spinner="Cargando datos…")
def _load_all(raw_dir: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paths = DatasetPaths.from_dir(raw_dir)
    daily = load_daily(paths.daily)
    hourly = load_hourly(paths.hourly) if paths.hourly.exists() else None
    monthly = load_monthly(paths.monthly) if paths.monthly.exists() else None
    return daily, hourly, monthly


# ---------- Sidebar ----------

with st.sidebar:
    st.markdown("### 💊 Pharma Sales")
    st.caption("Analítica comercial · demo")
    st.divider()

    with st.expander("⚙️ Fuente de datos", expanded=False):
        raw_dir = st.text_input(
            "Directorio",
            value=str(ROOT / "data" / "raw"),
            label_visibility="collapsed",
        )

try:
    daily, hourly, monthly = _load_all(raw_dir)
except FileNotFoundError:
    url = "https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data"
    st.error(
        "No se encontraron los CSV. Descargá el dataset de Kaggle "
        f"([Pharma Sales Data]({url})) y colocá los archivos en `{raw_dir}`."
    )
    st.stop()
except Exception as exc:  # noqa: BLE001
    st.error(f"Error cargando datos: {exc}")
    st.stop()

min_date = daily["date"].min().date()
max_date = daily["date"].max().date()

with st.sidebar:
    st.markdown("**📅 Rango de fechas**")
    rango = st.date_input(
        "Rango",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        label_visibility="collapsed",
        format="YYYY-MM-DD",
    )

    st.markdown("**🏷️ Categorías ATC**")
    categorias_sel = st.pills(
        "Categorías",
        options=ATC_CATEGORIES,
        selection_mode="multi",
        default=ATC_CATEGORIES,
        label_visibility="collapsed",
    )
    with st.expander("ℹ️ Qué significan"):
        for c in ATC_CATEGORIES:
            st.caption(f"**{c}** · {ATC_DESCRIPTIONS[c]}")

    st.divider()

if isinstance(rango, tuple) and len(rango) == 2:
    d_ini, d_fin = rango
else:
    d_ini, d_fin = min_date, max_date

mask = (daily["date"].dt.date >= d_ini) & (daily["date"].dt.date <= d_fin)
df = daily.loc[mask].copy()
if not categorias_sel:
    st.warning("Seleccioná al menos una categoría ATC en el sidebar.")
    st.stop()

df["total"] = df[categorias_sel].sum(axis=1)

# ---------- Header ----------

st.title("Pharma Sales Analytics")
_DATASET_URL = "https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data"
st.caption(
    "Demo sobre el dataset público de ventas farmacéuticas "
    f"[Pharma Sales Data]({_DATASET_URL}) "
    "(2014–2019, ~600k transacciones, 8 categorías ATC)."
)

# ---------- KPIs ----------

st.subheader("📌 Indicadores clave")
st.caption(
    "Resumen del período seleccionado. Los KPIs se recalculan automáticamente "
    "al cambiar el rango de fechas o las categorías ATC en el panel lateral."
)

total_unidades = float(df["total"].sum())
dias = int(df["date"].nunique())
promedio_dia = total_unidades / max(dias, 1)
top_cat = (
    df[categorias_sel].sum().sort_values(ascending=False).index[0]
    if categorias_sel
    else "—"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Unidades totales", f"{total_unidades:,.0f}")
c2.metric("Días en el rango", f"{dias:,}")
c3.metric("Promedio diario", f"{promedio_dia:,.1f}")
c4.metric("Categoría líder", top_cat)

st.divider()

# ---------- Tendencia mensual ----------

st.subheader("📈 Tendencia mensual")
st.caption(
    "Evolución de las unidades vendidas mes a mes, desglosadas por categoría ATC. "
    "Permite ver crecimiento sostenido, estacionalidad anual y picos atípicos."
)
trend = tendencia_mensual(df)
melted = trend.melt(
    id_vars="date",
    value_vars=categorias_sel,
    var_name="categoria",
    value_name="unidades",
)
fig_trend = px.line(
    melted,
    x="date",
    y="unidades",
    color="categoria",
    labels={"date": "Mes", "unidades": "Unidades"},
    color_discrete_sequence=MEGA_QUALITATIVE,
)
fig_trend.update_layout(
    height=400,
    legend_title_text="Categoría ATC",
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    font_color=MEGA_TEXT,
)
st.plotly_chart(fig_trend, width="stretch")

# ---------- Pareto + Heatmap ----------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🎯 Pareto por categoría")
    st.caption(
        "**Principio 80/20**: qué porcentaje del volumen aporta cada categoría. "
        "Las barras **azules** forman el top-80% de ventas (foco comercial); "
        "las **grises** son la cola larga (candidatas a análisis de rentabilidad)."
    )
    pareto = pareto_productos(df)
    fig_par = px.bar(
        pareto,
        x="categoria",
        y="share_pct",
        text="share_pct",
        color="en_top_80",
        labels={"share_pct": "Share %", "categoria": "Categoría ATC"},
        color_discrete_map={True: MEGA_GREEN, False: MEGA_GRAY},
    )
    fig_par.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_par.update_layout(
        showlegend=False,
        height=380,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font_color=MEGA_TEXT,
    )
    st.plotly_chart(fig_par, width="stretch")

with col_right:
    st.subheader("🗓️ Estacionalidad (día × hora)")
    st.caption(
        "Ventas **promedio** para cada combinación día-de-semana × hora. "
        "Colores más oscuros = mayor demanda. Útil para dimensionar staffing "
        "y planificar promociones en las ventanas pico."
    )
    if hourly is not None:
        mask_h = (hourly["date"].dt.date >= d_ini) & (
            hourly["date"].dt.date <= d_fin
        )
        heat_df = hourly.loc[mask_h].copy()
        heat_df["total"] = heat_df[categorias_sel].sum(axis=1)
        heat = estacionalidad_hora_dow(heat_df)
        fig_heat = px.imshow(
            heat,
            aspect="auto",
            color_continuous_scale=MEGA_GREEN_SCALE,
            labels={"x": "Hora", "y": "Día", "color": "Ventas prom."},
        )
        fig_heat.update_layout(
            height=380,
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            font_color=MEGA_TEXT,
        )
        st.plotly_chart(fig_heat, width="stretch")
    else:
        st.info("`saleshourly.csv` no disponible — heatmap deshabilitado.")

# ---------- YoY ----------

st.subheader("📊 Crecimiento Year-over-Year (YoY)")
st.markdown(
    """
**¿Qué es?** El *Year-over-Year* compara las ventas del último año
contra las del año anterior para responder: **¿qué categorías están
creciendo y cuáles están cayendo?**

**Cómo leer el gráfico:**
- Barra **verde hacia arriba** → la categoría vendió más que el año pasado ✅
- Barra **roja hacia abajo** → la categoría vendió menos ⚠️
- El número es el **% de variación** respecto al mismo período del año anterior.

**⚠️ Detalle metodológico:** como el último año del dataset puede estar
incompleto (por ej. datos hasta octubre), se comparan únicamente los
*meses coincidentes* entre ambos años — evita el sesgo clásico de
comparar 10 meses contra 12.
"""
)
if monthly is not None and monthly["year"].nunique() >= 2:
    yoy = yoy_por_categoria(monthly).reset_index(names="categoria")
    yoy = yoy[yoy["categoria"].isin(categorias_sel)]
    y_prev_col = [c for c in yoy.columns if c.startswith("unidades_")][0]
    y_curr_col = [c for c in yoy.columns if c.startswith("unidades_")][1]
    y_prev = y_prev_col.split("_")[1]
    y_curr = y_curr_col.split("_")[1]
    st.caption(
        f"Comparando **{y_curr}** contra **{y_prev}** "
        "(mismos meses en ambos años)."
    )
    fig_yoy = px.bar(
        yoy,
        x="categoria",
        y="delta_pct",
        color="delta_pct",
        color_continuous_scale=MEGA_DIVERGING,
        color_continuous_midpoint=0,
        labels={"delta_pct": "% variación YoY", "categoria": "Categoría ATC"},
        hover_data=["descripcion"],
    )
    fig_yoy.update_layout(
        height=380,
        coloraxis_showscale=False,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font_color=MEGA_TEXT,
    )
    fig_yoy.update_traces(
        texttemplate="%{y:.1f}%", textposition="outside", text=yoy["delta_pct"]
    )
    st.plotly_chart(fig_yoy, width="stretch")
    with st.expander("📄 Ver tabla detallada"):
        cols_tabla = [
            "categoria", "descripcion",
            y_prev_col, y_curr_col,
            "delta_abs", "delta_pct",
        ]
        st.dataframe(yoy[cols_tabla], width="stretch", hide_index=True)
else:
    st.info("`salesmonthly.csv` no disponible o con menos de 2 años.")

# ---------- Desvíos ----------

with st.expander("🚨 Detección de desvíos (promedio móvil 30d)"):
    st.caption(
        "Identifica días atípicos comparando el total de ventas contra el "
        "**promedio móvil de los últimos 30 días**. Sirve como *early warning*: "
        "un pico o caída por encima del umbral dispara una alerta que el equipo "
        "comercial puede investigar (quiebre de stock, evento puntual, error de carga)."
    )
    umbral = st.slider("Umbral de desvío (%)", 10, 80, 30, 5)
    alertas = detectar_desvios(df, ventana=30, umbral_pct=float(umbral))
    solo_alertas = alertas[alertas["alerta"]].sort_values(
        "desvio_pct", key=abs, ascending=False
    )
    st.write(
        f"**{len(solo_alertas)}** días con desvío ≥ {umbral}% respecto del "
        "promedio móvil."
    )
    st.dataframe(
        solo_alertas.head(20).assign(date=solo_alertas["date"].dt.date),
        width="stretch",
    )

# ---------- KPIs tabla ----------

with st.expander("📋 KPIs por categoría (tabla)"):
    st.dataframe(kpis_por_categoria(df), width="stretch")


@st.cache_data(show_spinner="Generando Excel…")
def _excel_bytes(
    df_daily: pd.DataFrame, df_monthly: pd.DataFrame | None
) -> tuple[bytes, str]:
    data = build_excel_report(df_daily, df_monthly)
    return data, report_filename(df_daily)


with st.sidebar:
    st.markdown("**📥 Exportar**")
    excel_bytes, fname = _excel_bytes(df, monthly)
    st.download_button(
        label="Descargar reporte Excel",
        data=excel_bytes,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        help="Incluye KPIs, Pareto, tendencia mensual, YoY, top meses y desvíos.",
    )

st.caption(
    "Código: [github.com/mathiasmtt/pharma-sales-analytics]"
    "(https://github.com/mathiasmtt/pharma-sales-analytics) · "
    "Dataset: Milan Zdravkovic · "
    "Construido con pandas + plotly + streamlit."
)
