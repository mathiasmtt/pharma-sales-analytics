"""Carga y validación de los CSV del dataset Pharma Sales.

El dataset original (Milan Zdravkovic, Kaggle) provee 4 archivos con distinta
granularidad temporal sobre las mismas ventas. Este módulo expone una API
uniforme para cargarlos, parsear fechas y validar que la estructura esperada
esté presente.

Las 8 categorías ATC del dataset son columnas-producto (wide format):
    M01AB, M01AE, N02BA, N02BE, N05B, N05C, R03, R06

Ejemplo de uso
--------------
>>> from src.data_loader import load_daily, ATC_CATEGORIES
>>> df = load_daily("data/raw/salesdaily.csv")
>>> df[ATC_CATEGORIES].sum().sort_values(ascending=False)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ATC_CATEGORIES: list[str] = [
    "M01AB",
    "M01AE",
    "N02BA",
    "N02BE",
    "N05B",
    "N05C",
    "R03",
    "R06",
]

ATC_DESCRIPTIONS: dict[str, str] = {
    "M01AB": "Antiinflamatorios no esteroides — ácido acético",
    "M01AE": "Antiinflamatorios no esteroides — ácido propiónico",
    "N02BA": "Analgésicos — ácido salicílico y derivados",
    "N02BE": "Analgésicos — pirazolonas y anilidas",
    "N05B": "Ansiolíticos",
    "N05C": "Hipnóticos y sedantes",
    "R03": "Enfermedades obstructivas de vías respiratorias",
    "R06": "Antihistamínicos sistémicos",
}


@dataclass(frozen=True)
class DatasetPaths:
    """Rutas esperadas de los 4 CSV del dataset."""

    hourly: Path
    daily: Path
    weekly: Path
    monthly: Path

    @classmethod
    def from_dir(cls, raw_dir: str | Path) -> "DatasetPaths":
        base = Path(raw_dir)
        return cls(
            hourly=base / "saleshourly.csv",
            daily=base / "salesdaily.csv",
            weekly=base / "salesweekly.csv",
            monthly=base / "salesmonthly.csv",
        )


def _validate_columns(df: pd.DataFrame, required: list[str], source: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Al cargar {source} faltan columnas obligatorias: {missing}. "
            f"Columnas encontradas: {list(df.columns)}"
        )


def load_daily(path: str | Path) -> pd.DataFrame:
    """Carga el CSV diario y devuelve un DataFrame tipado.

    Agrega columnas derivadas útiles para el análisis:
      - ``date``: datetime (index no obligatorio).
      - ``total``: suma de las 8 categorías ATC en la fila.
      - ``year``, ``month``, ``dow`` (día de la semana, 0=lunes).
    """
    df = pd.read_csv(path)
    _validate_columns(df, ["datum", *ATC_CATEGORIES], source=str(path))
    df["date"] = pd.to_datetime(df["datum"], format="%m/%d/%Y", errors="coerce")
    if df["date"].isna().any():
        df["date"] = pd.to_datetime(df["datum"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["total"] = df[ATC_CATEGORIES].sum(axis=1)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["dow"] = df["date"].dt.dayofweek
    return df


def load_hourly(path: str | Path) -> pd.DataFrame:
    """Carga el CSV horario con fecha+hora parseadas."""
    df = pd.read_csv(path)
    _validate_columns(df, ["datum", "Hour", *ATC_CATEGORIES], source=str(path))
    df["date"] = pd.to_datetime(df["datum"], errors="coerce")
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    df["hour"] = df["Hour"].astype(int)
    df["dow"] = df["date"].dt.dayofweek
    df["total"] = df[ATC_CATEGORIES].sum(axis=1)
    return df


def load_weekly(path: str | Path) -> pd.DataFrame:
    """Carga el CSV semanal."""
    df = pd.read_csv(path)
    _validate_columns(df, ["datum", *ATC_CATEGORIES], source=str(path))
    df["date"] = pd.to_datetime(df["datum"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["total"] = df[ATC_CATEGORIES].sum(axis=1)
    return df


def load_monthly(path: str | Path) -> pd.DataFrame:
    """Carga el CSV mensual."""
    df = pd.read_csv(path)
    _validate_columns(df, ["datum", *ATC_CATEGORIES], source=str(path))
    df["date"] = pd.to_datetime(df["datum"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["total"] = df[ATC_CATEGORIES].sum(axis=1)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    return df


def quality_report(df: pd.DataFrame, name: str = "dataset") -> pd.DataFrame:
    """Genera un reporte de calidad básico sobre un DataFrame de ventas.

    Retorna filas × métricas: nulos por columna, mínimo, máximo, media.
    Útil para el EDA inicial y para loggear controles automáticos.
    """
    cols = [c for c in ATC_CATEGORIES if c in df.columns]
    summary = pd.DataFrame(
        {
            "nulos": df[cols].isna().sum(),
            "min": df[cols].min(),
            "max": df[cols].max(),
            "media": df[cols].mean().round(3),
        }
    )
    summary.index.name = f"ATC ({name})"
    return summary


def reconcile_granularities(
    daily: pd.DataFrame, monthly: pd.DataFrame, tolerance: float = 0.01
) -> pd.DataFrame:
    """Verifica consistencia entre el CSV diario y el mensual.

    Reagrega ``daily`` a mensual y compara contra ``monthly``. Devuelve un
    DataFrame con el delta relativo por año-mes y categoría ATC. Un proyecto
    serio de datos siempre reconcilia granularidades: este método es el
    control básico para descartar errores de ingesta.

    Parameters
    ----------
    tolerance : float
        Umbral de delta relativo aceptable (0.01 = 1%).
    """
    daily_agg = (
        daily.assign(period=daily["date"].dt.to_period("M"))
        .groupby("period")[ATC_CATEGORIES]
        .sum()
    )
    monthly_idx = monthly.assign(period=monthly["date"].dt.to_period("M")).set_index(
        "period"
    )[ATC_CATEGORIES]
    common = daily_agg.index.intersection(monthly_idx.index)
    delta = (daily_agg.loc[common] - monthly_idx.loc[common]).abs()
    denom = monthly_idx.loc[common].replace(0, pd.NA)
    rel = (delta / denom).fillna(0)
    rel["max_delta_rel"] = rel.max(axis=1)
    rel["ok"] = rel["max_delta_rel"] <= tolerance
    return rel
