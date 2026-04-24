"""Fixtures compartidos para los tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data_loader import ATC_CATEGORIES


@pytest.fixture(scope="session")
def rng() -> np.random.Generator:
    return np.random.default_rng(seed=42)


@pytest.fixture()
def daily_sintetico(rng: np.random.Generator) -> pd.DataFrame:
    """DataFrame diario sintético con 2 años de datos y todas las categorías."""
    fechas = pd.date_range("2022-01-01", "2023-12-31", freq="D")
    data = {"date": fechas}
    # Valores crecientes para simular tendencia
    for i, cat in enumerate(ATC_CATEGORIES):
        base = 10 + i * 3
        noise = rng.normal(0, 2, size=len(fechas))
        data[cat] = np.clip(base + noise, 0, None).round(2)
    df = pd.DataFrame(data)
    df["total"] = df[ATC_CATEGORIES].sum(axis=1)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["dow"] = df["date"].dt.dayofweek
    return df


@pytest.fixture()
def hourly_sintetico(rng: np.random.Generator) -> pd.DataFrame:
    """DataFrame horario sintético: 30 días × 24 horas."""
    fechas = pd.date_range("2023-01-01", periods=30, freq="D")
    rows = []
    for fecha in fechas:
        for hour in range(24):
            row = {"date": fecha, "hour": hour, "dow": fecha.dayofweek}
            # Pico a la tarde (12-18h)
            factor = 3.0 if 12 <= hour <= 18 else 1.0
            for cat in ATC_CATEGORIES:
                row[cat] = float(rng.normal(5 * factor, 1))
            rows.append(row)
    df = pd.DataFrame(rows)
    df["total"] = df[ATC_CATEGORIES].sum(axis=1)
    return df


@pytest.fixture()
def monthly_sintetico(daily_sintetico: pd.DataFrame) -> pd.DataFrame:
    """Mensual derivado del diario — garantiza consistencia."""
    m = (
        daily_sintetico.assign(
            period=daily_sintetico["date"].dt.to_period("M").dt.to_timestamp()
        )
        .groupby("period")[ATC_CATEGORIES]
        .sum()
        .reset_index()
        .rename(columns={"period": "date"})
    )
    m["total"] = m[ATC_CATEGORIES].sum(axis=1)
    m["year"] = m["date"].dt.year
    m["month"] = m["date"].dt.month
    return m
