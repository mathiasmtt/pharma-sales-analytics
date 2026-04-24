"""Tests sobre las funciones analíticas puras."""

from __future__ import annotations

import pandas as pd
import pytest

from src.analytics import (
    detectar_desvios,
    estacionalidad_hora_dow,
    kpis_por_categoria,
    pareto_productos,
    tendencia_mensual,
    top_meses,
    yoy_por_categoria,
)
from src.data_loader import ATC_CATEGORIES


class TestKpisPorCategoria:
    def test_devuelve_una_fila_por_categoria(self, daily_sintetico):
        out = kpis_por_categoria(daily_sintetico)
        assert len(out) == len(ATC_CATEGORIES)
        assert set(out.index) == set(ATC_CATEGORIES)

    def test_share_suma_100(self, daily_sintetico):
        out = kpis_por_categoria(daily_sintetico)
        assert out["share_pct"].sum() == pytest.approx(100.0, abs=0.05)

    def test_ordenado_descendente(self, daily_sintetico):
        out = kpis_por_categoria(daily_sintetico)
        totales = out["unidades_totales"].tolist()
        assert totales == sorted(totales, reverse=True)

    def test_columnas_esperadas(self, daily_sintetico):
        out = kpis_por_categoria(daily_sintetico)
        esperadas = {
            "descripcion",
            "unidades_totales",
            "share_pct",
            "promedio_diario",
            "dias_con_venta",
        }
        assert esperadas.issubset(out.columns)


class TestParetoProductos:
    def test_share_acumulado_termina_en_100(self, daily_sintetico):
        out = pareto_productos(daily_sintetico)
        assert out["share_acumulado_pct"].iloc[-1] == pytest.approx(100.0, abs=0.05)

    def test_share_acumulado_monotono_creciente(self, daily_sintetico):
        out = pareto_productos(daily_sintetico)
        diffs = out["share_acumulado_pct"].diff().dropna()
        assert (diffs >= 0).all()

    def test_flag_top80_consistente(self, daily_sintetico):
        out = pareto_productos(daily_sintetico)
        # Todas las True deben tener acumulado <= 80
        assert (out.loc[out["en_top_80"], "share_acumulado_pct"] <= 80).all()


class TestEstacionalidad:
    def test_shape_dias_por_24h(self, hourly_sintetico):
        out = estacionalidad_hora_dow(hourly_sintetico)
        assert out.shape[0] == 7  # días
        assert out.shape[1] == 24  # horas

    def test_indice_tiene_dias_legibles(self, hourly_sintetico):
        out = estacionalidad_hora_dow(hourly_sintetico)
        assert list(out.index) == ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    def test_detecta_pico_tarde(self, hourly_sintetico):
        """La fixture inyecta 3x las ventas entre 12-18h — debe notarse."""
        out = estacionalidad_hora_dow(hourly_sintetico)
        pico = out.loc[:, 12:18].mean().mean()
        valle = out.loc[:, [0, 1, 2, 22, 23]].mean().mean()
        assert pico > 2 * valle


class TestYoY:
    def test_incluye_todas_las_categorias(self, monthly_sintetico):
        out = yoy_por_categoria(monthly_sintetico)
        assert set(out.index) == set(ATC_CATEGORIES)

    def test_falla_con_un_solo_anio(self, monthly_sintetico):
        mono = monthly_sintetico[monthly_sintetico["year"] == 2022]
        with pytest.raises(ValueError, match="al menos 2 años"):
            yoy_por_categoria(mono)

    def test_compara_solo_meses_comunes(self, monthly_sintetico):
        """Si 2023 solo tiene enero, el cálculo debe usar solo enero de ambos años."""
        recortado = monthly_sintetico[
            (monthly_sintetico["year"] == 2022)
            | ((monthly_sintetico["year"] == 2023) & (monthly_sintetico["month"] == 1))
        ]
        out = yoy_por_categoria(recortado)
        # Los totales 2022 deben ser solo enero, no el año completo
        ene_2022 = monthly_sintetico[
            (monthly_sintetico["year"] == 2022) & (monthly_sintetico["month"] == 1)
        ][ATC_CATEGORIES].sum()
        assert out["unidades_2022"].sort_index().equals(ene_2022.sort_index().round(2))


class TestDetectarDesvios:
    def test_columnas(self, daily_sintetico):
        out = detectar_desvios(daily_sintetico, ventana=30, umbral_pct=25)
        assert {"date", "total", "ma", "desvio_pct", "alerta"}.issubset(out.columns)

    def test_alertas_son_booleanas(self, daily_sintetico):
        out = detectar_desvios(daily_sintetico)
        assert out["alerta"].dtype == bool

    def test_umbral_mas_alto_menos_alertas(self, daily_sintetico):
        laxo = detectar_desvios(daily_sintetico, umbral_pct=10)["alerta"].sum()
        estricto = detectar_desvios(daily_sintetico, umbral_pct=80)["alerta"].sum()
        assert estricto <= laxo


class TestTendenciaMensual:
    def test_tiene_columna_date(self, daily_sintetico):
        out = tendencia_mensual(daily_sintetico)
        assert "date" in out.columns
        assert pd.api.types.is_datetime64_any_dtype(out["date"])

    def test_numero_de_meses(self, daily_sintetico):
        out = tendencia_mensual(daily_sintetico)
        # 2 años completos = 24 meses
        assert len(out) == 24


class TestTopMeses:
    def test_respeta_n(self, daily_sintetico):
        out = top_meses(daily_sintetico, n=3)
        assert len(out) == 3

    def test_ordenado_desc(self, daily_sintetico):
        out = top_meses(daily_sintetico, n=5)
        assert out["total"].tolist() == sorted(out["total"].tolist(), reverse=True)
