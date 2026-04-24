# Proyecto Demo: Analista de Datos – Equipo Comercial (Industria Farmacéutica)

## 1. Contexto del pedido

Postulación al puesto **Analista de Datos – Equipo Comercial (Data Science)** en la compañía líder de la industria farmacéutica en Uruguay. Modalidad presencial.

### Descripción del puesto

Orientado a profesionales de Data Science, Contador Público o Economía. La persona es responsable de gestionar y potenciar el uso de la información comercial, transformando datos en insumos clave para la toma de decisiones.

**Principales desafíos:**

- Centralizar y ordenar la información proveniente de distintas fuentes comerciales.
- Analizar datos de ventas y generar reportes periódicos.
- Dar soporte al equipo comercial mediante información clara y oportuna.
- Detectar oportunidades, tendencias y desvíos en los indicadores de negocio.
- Automatizar reportes y procesos vinculados al manejo de datos.
- Asegurar la calidad y consistencia de la información.

**Requisitos:**

- Formación en Data Science, Economía o Contador Público.
- Experiencia en análisis de datos (deseable en áreas comerciales).
- Manejo avanzado de Excel y herramientas de visualización (Power BI, Tableau o similares).
- Perfil analítico, ordenado y con buena capacidad de comunicación.

### Objetivo de este documento

Seleccionar un dataset público en Kaggle que permita construir un proyecto demo end-to-end para demostrar habilidades alineadas al puesto: ingesta de datos, calidad, análisis comercial, detección de tendencias, automatización de reportes y visualización.

---

## 2. Dataset recomendado

### Pharma Sales Data — Milan Zdravkovic

- **URL:** https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data
- **Período:** 2014–2019 (6 años)
- **Volumen:** ~600.000 transacciones
- **Productos:** 57 drogas clasificadas en 8 categorías ATC
- **Origen:** Exportación de sistemas Point-of-Sale (POS) de farmacias individuales
- **Formato:** 4 archivos CSV con distinta granularidad temporal (horaria, diaria, semanal, mensual)

### Categorías ATC incluidas

El **Anatomical Therapeutic Chemical (ATC) Classification System** es el estándar internacional usado por la OMS y adoptado por la industria farmacéutica a nivel global (incluyendo Uruguay).

| Código ATC | Descripción |
|---|---|
| M01AB | Antiinflamatorios y antirreumáticos no esteroides — derivados del ácido acético |
| M01AE | Antiinflamatorios y antirreumáticos no esteroides — derivados del ácido propiónico |
| N02BA | Otros analgésicos y antipiréticos — ácido salicílico y derivados |
| N02BE/B | Otros analgésicos y antipiréticos — pirazolonas y anilidas |
| N05B | Psicolépticos — ansiolíticos |
| N05C | Psicolépticos — hipnóticos y sedantes |
| R03 | Medicamentos para enfermedades obstructivas de las vías respiratorias |
| R06 | Antihistamínicos para uso sistémico |

---

## 3. Justificación de la elección

### Por qué este dataset sobre otras opciones evaluadas

| Dataset | Volumen | Problemas |
|---|---|---|
| **Pharma Sales Data (Milan Zdravkovic)** ✅ | 600k transacciones, 6 años | Ninguno relevante |
| Pharmaceutical Company Wholesale-Retail Data | Menor | Menos tracción, documentación débil |
| Pharma Drug Sales (ybifoundation) | Chico | Orientado a ejercicios académicos |
| Drug Pharma New Dataset | Chico | Sin profundidad para análisis comercial |
| Retail Insights / Retail Transactions | Medio | Genéricos, pierden el ángulo farma |

### Alineación con el puesto

| Requisito del puesto | Cómo lo cubre el dataset |
|---|---|
| Centralizar info de distintas fuentes | 4 archivos con distinta granularidad → demuestra ETL y consolidación |
| Análisis de ventas + reportes periódicos | KPIs comerciales, ticket promedio, mix de categorías |
| Detectar tendencias y desvíos | Series de tiempo, estacionalidad, anomalías, comparables YoY |
| Excel avanzado + Power BI/Tableau | Exportación de agregados a Excel + dashboard interactivo |
| Automatizar reportes | Script Python con CLI para reporte mensual one-command |
| Calidad y consistencia | Validaciones, logging, manejo de nulos, reconciliación entre granularidades |

### Ventajas estratégicas

1. **Dominio directo:** ventas farmacéuticas a nivel transaccional — exactamente el negocio de la empresa que busca.
2. **Vocabulario del sector:** manejar clasificación ATC en la entrevista posiciona como alguien que entiende el lenguaje del laboratorio.
3. **Volumen realista:** 600k filas son suficientes para demostrar técnicas de análisis serio sin ser inmanejables.
4. **Cobertura temporal amplia:** 6 años permiten análisis de estacionalidad, YoY, y tendencias de largo plazo.

---

## 4. Plan de proyecto propuesto

### Estructura del repositorio

```
pharma-sales-analytics/
├── src/
│   ├── ingestion/      # Carga de los 4 CSV (horario/diario/semanal/mensual)
│   ├── quality/        # Validaciones + reconciliación entre granularidades
│   ├── analytics/      # KPIs, estacionalidad, detección de desvíos
│   ├── reporting/      # Exportación a Excel + PDF
│   └── cli.py          # Argparse: `python -m pharma_sales monthly-report --month 2019-09`
├── dashboards/
│   └── powerbi/        # .pbix con el dashboard comercial
├── notebooks/          # EDA + storytelling
├── tests/              # pytest
├── config.yaml
├── requirements.txt / pyproject.toml
└── README.md           # Con screenshots del dashboard y casos de uso
```

### Principios técnicos

- **Modularidad:** cada módulo funciona independientemente (testing y uso individual).
- **Estilo pythónico:** código claro, PEP 8, docstrings completas.
- **Logging detallado** para trazabilidad de cada paso del pipeline.
- **Manejo robusto de errores** en ingesta y transformación.
- **Configuración externa** en YAML (paths, umbrales, parámetros).
- **CLI ejecutable** con `argparse` — un solo comando genera el reporte completo.
- **Tests con pytest** cubriendo validaciones críticas.
- **Git workflow limpio:** commits semánticos, branches por feature.

### Entregables estrella para la entrevista

1. **Dashboard Power BI** con drill-down por categoría ATC, estacionalidad semanal, alertas de desvío vs. mes anterior y comparables YoY.
2. **Script CLI automatizado** que genera el reporte mensual completo (Excel + PDF) con un único comando.
3. **Notebook de storytelling** titulado *"3 insights accionables para el equipo comercial"* — demuestra perfil analítico + capacidad de comunicación.

### Análisis concretos a incluir

- **KPIs comerciales:** unidades totales, ticket promedio, mix por categoría ATC.
- **Estacionalidad:** patrones por día de la semana, mes del año, hora del día.
- **Tendencias:** evolución YoY por categoría, productos en crecimiento vs. declive.
- **Detección de desvíos:** alertas cuando una categoría se desvía >X% del promedio móvil.
- **Segmentación:** top N productos por volumen, Pareto 80/20 de ventas.
- **Forecasting simple:** proyección del mes siguiente usando regresión lineal + promedio móvil (opcional, como valor agregado).

---

## 5. Referencias

- **Dataset principal:** https://www.kaggle.com/datasets/milanzdravkovic/pharma-sales-data
- **Notebook de análisis y forecasting del autor:** https://www.kaggle.com/code/milanzdravkovic/pharma-sales-data-analysis-and-forecasting
- **Artículo Towards Data Science (referencia metodológica):** https://towardsdatascience.com/analysing-pharmaceutical-sales-data-in-python-6ce74da818ab/
- **Ejemplo de dashboard con Streamlit:** https://medium.com/@isa.dario.isa/pharma-sales-interactive-dashboard-with-streamlit-26da8fb21dab
