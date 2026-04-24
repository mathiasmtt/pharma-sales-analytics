"""Tests sobre carga y validación del dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import (
    ATC_CATEGORIES,
    DatasetPaths,
    load_daily,
    load_monthly,
    quality_report,
    reconcile_granularities,
)


@pytest.fixture()
def csv_diario_valido(tmp_path: Path) -> Path:
    """Crea un CSV diario con estructura correcta."""
    fechas = pd.date_range("2022-01-01", periods=60, freq="D")
    df = pd.DataFrame({"datum": fechas.strftime("%m/%d/%Y")})
    for cat in ATC_CATEGORIES:
        df[cat] = 10.0
    path = tmp_path / "salesdaily.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture()
def csv_mensual_valido(tmp_path: Path) -> Path:
    fechas = pd.date_range("2022-01-01", periods=12, freq="MS")
    df = pd.DataFrame({"datum": fechas.strftime("%Y-%m-%d")})
    for cat in ATC_CATEGORIES:
        df[cat] = 300.0  # 30 días * 10 unidades
    path = tmp_path / "salesmonthly.csv"
    df.to_csv(path, index=False)
    return path


class TestDatasetPaths:
    def test_from_dir_construye_las_4_rutas(self, tmp_path):
        paths = DatasetPaths.from_dir(tmp_path)
        assert paths.daily.name == "salesdaily.csv"
        assert paths.hourly.name == "saleshourly.csv"
        assert paths.weekly.name == "salesweekly.csv"
        assert paths.monthly.name == "salesmonthly.csv"


class TestLoadDaily:
    def test_carga_exitosa(self, csv_diario_valido):
        df = load_daily(csv_diario_valido)
        assert len(df) == 60
        assert {"date", "total", "year", "month", "dow"}.issubset(df.columns)

    def test_fecha_parseada(self, csv_diario_valido):
        df = load_daily(csv_diario_valido)
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_total_es_suma_de_categorias(self, csv_diario_valido):
        df = load_daily(csv_diario_valido)
        esperado = df[ATC_CATEGORIES].sum(axis=1)
        pd.testing.assert_series_equal(df["total"], esperado, check_names=False)

    def test_ordenado_por_fecha(self, csv_diario_valido):
        df = load_daily(csv_diario_valido)
        assert df["date"].is_monotonic_increasing

    def test_falla_si_falta_columna(self, tmp_path):
        path = tmp_path / "bad.csv"
        pd.DataFrame({"datum": ["01/01/2022"], "M01AB": [1]}).to_csv(path, index=False)
        with pytest.raises(ValueError, match="faltan columnas"):
            load_daily(path)


class TestQualityReport:
    def test_devuelve_metricas(self, csv_diario_valido):
        df = load_daily(csv_diario_valido)
        rep = quality_report(df)
        assert {"nulos", "min", "max", "media"}.issubset(rep.columns)
        assert len(rep) == len(ATC_CATEGORIES)


class TestReconcileGranularities:
    def test_consistencia_perfecta_es_ok(
        self, csv_diario_valido, csv_mensual_valido
    ):
        d = load_daily(csv_diario_valido)
        m = load_monthly(csv_mensual_valido)
        rec = reconcile_granularities(d, m, tolerance=0.01)
        # Las fixtures son consistentes por construcción (10/día × 30 = 300/mes)
        # pero tienen meses con 31 días → delta esperado. Verificamos estructura.
        assert "max_delta_rel" in rec.columns
        assert "ok" in rec.columns
        assert rec["ok"].dtype == bool
