"""Funciones analíticas puras sobre los DataFrames de ventas.

Todas las funciones:
  - Reciben un DataFrame ya cargado por ``data_loader`` (separación de
    responsabilidades: acá no se lee IO).
  - Son puras: no mutan el DataFrame de entrada.
  - Devuelven DataFrames/Series listos para graficar o exportar.

Ejemplo de uso
--------------
>>> from src.data_loader import load_daily
>>> from src.analytics import kpis_por_categoria, pareto_productos
>>> df = load_daily("data/raw/salesdaily.csv")
>>> kpis_por_categoria(df)
>>> pareto_productos(df)
"""

from __future__ import annotations

import pandas as pd

from src.data_loader import ATC_CATEGORIES, ATC_DESCRIPTIONS


def kpis_por_categoria(daily: pd.DataFrame) -> pd.DataFrame:
    """KPIs comerciales agregados por categoría ATC.

    Devuelve: unidades totales, share %, promedio diario, días con venta,
    descripción legible de la categoría.
    """
    totals = daily[ATC_CATEGORIES].sum()
    share = (totals / totals.sum() * 100).round(2)
    avg_daily = daily[ATC_CATEGORIES].mean().round(3)
    active_days = (daily[ATC_CATEGORIES] > 0).sum()
    out = pd.DataFrame(
        {
            "descripcion": [ATC_DESCRIPTIONS[c] for c in ATC_CATEGORIES],
            "unidades_totales": totals.round(2),
            "share_pct": share,
            "promedio_diario": avg_daily,
            "dias_con_venta": active_days,
        }
    )
    return out.sort_values("unidades_totales", ascending=False)


def pareto_productos(daily: pd.DataFrame) -> pd.DataFrame:
    """Análisis Pareto sobre las 8 categorías ATC.

    Devuelve las categorías ordenadas por volumen con su % acumulado,
    marcando el corte 80/20.
    """
    totals = daily[ATC_CATEGORIES].sum().sort_values(ascending=False)
    share = totals / totals.sum() * 100
    acc = share.cumsum()
    out = pd.DataFrame(
        {
            "categoria": totals.index,
            "unidades": totals.values.round(2),
            "share_pct": share.values.round(2),
            "share_acumulado_pct": acc.values.round(2),
        }
    )
    out["en_top_80"] = out["share_acumulado_pct"] <= 80
    return out.reset_index(drop=True)


def estacionalidad_hora_dow(hourly: pd.DataFrame) -> pd.DataFrame:
    """Matriz día-de-semana × hora con ventas totales promedio por celda.

    Ideal para heatmap. Filas: 0=lunes … 6=domingo. Columnas: 0..23 (hora).
    """
    pivot = (
        hourly.groupby(["dow", "hour"])["total"]
        .mean()
        .unstack("hour")
        .round(3)
    )
    pivot.index = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    return pivot


def tendencia_mensual(daily: pd.DataFrame) -> pd.DataFrame:
    """Serie de tiempo mensual: total y por categoría."""
    agg = (
        daily.assign(period=daily["date"].dt.to_period("M").dt.to_timestamp())
        .groupby("period")[ATC_CATEGORIES + ["total"]]
        .sum()
        .reset_index()
        .rename(columns={"period": "date"})
    )
    return agg


def yoy_por_categoria(monthly: pd.DataFrame) -> pd.DataFrame:
    """Crecimiento Year-over-Year por categoría ATC.

    Compara el último año contra el anterior usando **solo los meses
    comunes** — evita sesgos cuando el último año está incompleto (ej.
    datos hasta octubre vs. año anterior completo).
    """
    df = monthly.copy()
    years = sorted(df["year"].unique())
    if len(years) < 2:
        raise ValueError("Se necesitan al menos 2 años para YoY.")
    y_curr, y_prev = years[-1], years[-2]
    meses_curr = set(df.loc[df["year"] == y_curr, "month"])
    meses_prev = set(df.loc[df["year"] == y_prev, "month"])
    meses_comunes = sorted(meses_curr & meses_prev)
    if not meses_comunes:
        raise ValueError("No hay meses comunes entre los dos últimos años.")
    mask_curr = (df["year"] == y_curr) & (df["month"].isin(meses_comunes))
    mask_prev = (df["year"] == y_prev) & (df["month"].isin(meses_comunes))
    curr = df.loc[mask_curr, ATC_CATEGORIES].sum()
    prev = df.loc[mask_prev, ATC_CATEGORIES].sum()
    out = pd.DataFrame(
        {
            f"unidades_{y_prev}": prev.round(2),
            f"unidades_{y_curr}": curr.round(2),
            "delta_abs": (curr - prev).round(2),
            "delta_pct": ((curr - prev) / prev.replace(0, pd.NA) * 100).round(2),
        }
    )
    out["descripcion"] = [ATC_DESCRIPTIONS[c] for c in out.index]
    return out.sort_values("delta_pct", ascending=False)


def detectar_desvios(
    daily: pd.DataFrame, ventana: int = 30, umbral_pct: float = 25.0
) -> pd.DataFrame:
    """Detecta días donde ``total`` se desvía del promedio móvil > umbral.

    Parameters
    ----------
    ventana : int
        Días del promedio móvil.
    umbral_pct : float
        Umbral absoluto de desvío relativo (en %).
    """
    df = daily[["date", "total"]].copy()
    df["ma"] = df["total"].rolling(ventana, min_periods=ventana // 2).mean()
    df["desvio_pct"] = ((df["total"] - df["ma"]) / df["ma"] * 100).round(2)
    df["alerta"] = df["desvio_pct"].abs() >= umbral_pct
    return df


def top_meses(daily: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Top N meses por ventas totales."""
    agg = (
        daily.assign(period=daily["date"].dt.to_period("M").astype(str))
        .groupby("period")["total"]
        .sum()
        .round(2)
        .sort_values(ascending=False)
        .head(n)
        .reset_index()
    )
    return agg
