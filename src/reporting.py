"""Generación de reportes Excel a partir de DataFrames ya analizados.

Responsabilidad única: empaquetar resultados en un ``.xlsx`` multi-hoja con
formato mínimo. La lógica de cálculo vive en ``analytics``; acá solo se arma
el entregable.

Ejemplo de uso
--------------
>>> from io import BytesIO
>>> from src.data_loader import load_daily, load_monthly, DatasetPaths
>>> from src.reporting import build_excel_report
>>> paths = DatasetPaths.from_dir("data/raw")
>>> buf = BytesIO()
>>> build_excel_report(load_daily(paths.daily), load_monthly(paths.monthly), buf)
>>> buf.seek(0)
"""

from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import pandas as pd

from src.analytics import (
    detectar_desvios,
    kpis_por_categoria,
    pareto_productos,
    tendencia_mensual,
    top_meses,
    yoy_por_categoria,
)


def build_excel_report(
    daily: pd.DataFrame,
    monthly: pd.DataFrame | None,
    buffer: BinaryIO | None = None,
    *,
    umbral_desvio_pct: float = 30.0,
) -> bytes:
    """Construye un reporte Excel con múltiples hojas analíticas.

    Hojas:
      - **Resumen**: KPIs por categoría ATC.
      - **Pareto**: share y acumulado por categoría.
      - **Tendencia Mensual**: serie de tiempo.
      - **YoY**: crecimiento año contra año (si ``monthly`` está disponible).
      - **Top Meses**: 10 mejores meses por ventas.
      - **Desvios**: días con desvío ≥ umbral sobre promedio móvil 30d.

    Parameters
    ----------
    buffer : BinaryIO, optional
        Si se provee, escribe ahí. Si es ``None``, crea un ``BytesIO`` interno.

    Returns
    -------
    bytes
        Contenido binario del Excel, listo para descarga.
    """
    own_buffer = buffer is None
    buf = buffer if buffer is not None else BytesIO()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        kpis_por_categoria(daily).to_excel(writer, sheet_name="Resumen")
        pareto_productos(daily).to_excel(writer, sheet_name="Pareto", index=False)
        tendencia_mensual(daily).to_excel(
            writer, sheet_name="Tendencia Mensual", index=False
        )
        if monthly is not None and monthly["year"].nunique() >= 2:
            yoy_por_categoria(monthly).to_excel(writer, sheet_name="YoY")
        top_meses(daily, n=10).to_excel(writer, sheet_name="Top Meses", index=False)
        desvios = detectar_desvios(daily, umbral_pct=umbral_desvio_pct)
        alertas = desvios[desvios["alerta"]].copy()
        alertas["date"] = alertas["date"].dt.date
        alertas.to_excel(writer, sheet_name="Desvios", index=False)

    if own_buffer:
        return buf.getvalue()
    # Si el caller pasó su buffer, lo dejamos posicionado al inicio.
    buf.seek(0)
    return buf.getvalue() if hasattr(buf, "getvalue") else b""


def report_filename(daily: pd.DataFrame) -> str:
    """Genera un nombre de archivo descriptivo basado en el rango de datos."""
    ini = daily["date"].min().strftime("%Y%m%d")
    fin = daily["date"].max().strftime("%Y%m%d")
    return f"pharma_sales_report_{ini}_{fin}.xlsx"
