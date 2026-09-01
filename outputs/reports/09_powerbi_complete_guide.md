# Guía Power BI Completa — Revenue Analytics Portfolio
## Nivel PL-300 · Revenue Manager Senior

---

## 1. IMPORTAR LOS DATOS

### Paso 1 — Conectar los archivos Parquet

En Power BI Desktop:
1. `Inicio → Obtener datos → Parquet`
2. Importar estos archivos desde `data/public/`:

| Archivo | Tipo | Filas |
|---------|------|-------|
| `fact_reservations.parquet` | Tabla de hechos principal | ~34.000 |
| `fact_kpis_monthly.parquet` | KPIs agregados mensuales | ~322 |
| `fact_gastos.parquet` | Gastos y rentabilidad | ~14 |
| `fact_benchmark.parquet` | Datos de mercado | ~27 |
| `fact_reviews.parquet` | Valoraciones NLP | ~6.298 |
| `predictions_export.parquet` | Predicciones ML 2025 | ~260 |
| `dim_property.parquet` | Dimensión edificios + geo | 5 |
| `dim_date.parquet` | Calendario completo | 2.922 |
| `dim_channel.parquet` | Canales de venta | 5 |
| `dim_event.parquet` | Eventos Bilbao | 15 |

---

## 2. MODELO DE DATOS (Star Schema)

### Paso 2 — Ir a Vista de Modelo y crear relaciones

```
                    dim_date
                       │
              date_key_checkin
                       │
dim_channel ─── channel_key ─── FACT_RESERVATIONS ─── property_key ─── dim_property
                                        │
                               date_key_checkin ──── dim_event (fecha aproximada)

fact_kpis_monthly ──── property_key ──── dim_property
fact_reviews      ──── property      ──── dim_property (por building_name_public)
fact_gastos       ──── building      ──── dim_property (por building_code)
predictions_export──── property_key ──── dim_property
```

### Relaciones a crear:

| Desde | Campo | Hacia | Campo | Tipo |
|-------|-------|-------|-------|------|
| fact_reservations | property_key | dim_property | property_key | Muchos→1 ★ |
| fact_reservations | channel_key | dim_channel | channel_key | Muchos→1 |
| fact_reservations | date_key_checkin | dim_date | date_key | Muchos→1 |
| fact_kpis_monthly | property_key | dim_property | property_key | Muchos→1 |
| predictions_export | property_key | dim_property | property_key | Muchos→1 |
| fact_reviews | property | dim_property | building_name_public | Muchos→1 |

---

## 3. MEDIDAS DAX — TODAS LAS NECESARIAS

### Paso 3 — Crear tabla de medidas

Crea una tabla vacía llamada `_Medidas`:
`Modelado → Nueva tabla → _Medidas = {""}`

Luego añade estas medidas:

---

### 📊 GRUPO 1: KPIs Base

```dax
// Revenue total (noches vendidas × precio)
Revenue Total = SUM(fact_reservations[revenue_gross])

// ADR — Average Daily Rate
ADR = DIVIDE(
    SUM(fact_reservations[revenue_gross]),
    SUM(fact_reservations[nights]),
    0
)

// Noches disponibles (unidades × días en período)
Noches Disponibles =
SUMX(
    dim_property,
    dim_property[units] *
    CALCULATE(COUNTROWS(dim_date), ALLEXCEPT(dim_date, dim_date[date_key]))
)

// RevPAR — Revenue Per Available Room/Night
RevPAR = DIVIDE([Revenue Total], [Noches Disponibles], 0)

// Ocupación %
Ocupacion % =
DIVIDE(
    SUM(fact_reservations[nights]),
    [Noches Disponibles],
    0
) * 100

// Número de reservas (no canceladas)
Reservas Confirmadas =
CALCULATE(
    COUNTROWS(fact_reservations),
    fact_reservations[is_cancelled] = FALSE()
)

// Tasa de cancelación
Tasa Cancelacion % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_reservations), fact_reservations[is_cancelled] = TRUE()),
    COUNTROWS(fact_reservations),
    0
) * 100

// Lead time medio (antelación de reserva)
Lead Time Medio =
AVERAGE(fact_reservations[lead_time_days])
```

---

### 📅 GRUPO 2: Time Intelligence (los más importantes para PL-300)

```dax
// Revenue año anterior (mismo período)
Revenue Año Anterior =
CALCULATE(
    [Revenue Total],
    SAMEPERIODLASTYEAR(dim_date[date])
)

// Crecimiento YoY %
Revenue YoY % =
DIVIDE(
    [Revenue Total] - [Revenue Año Anterior],
    [Revenue Año Anterior],
    0
) * 100

// Revenue acumulado año (Year-to-Date)
Revenue YTD =
TOTALYTD(
    [Revenue Total],
    dim_date[date]
)

// Revenue YTD año anterior
Revenue YTD Año Anterior =
CALCULATE(
    [Revenue YTD],
    SAMEPERIODLASTYEAR(dim_date[date])
)

// ADR media móvil 3 meses
ADR Moving Avg 3M =
AVERAGEX(
    DATESINPERIOD(dim_date[date], LASTDATE(dim_date[date]), -3, MONTH),
    [ADR]
)

// Mejor mes del año
Mejor Mes Revenue =
CALCULATE(
    [Revenue Total],
    TOPN(1,
        ALL(dim_date[month_name_es]),
        [Revenue Total]
    )
)
```

---

### 🏠 GRUPO 3: Rankings y Comparativas por Edificio

```dax
// Ranking de edificios por Revenue
Ranking Revenue Edificio =
RANKX(
    ALL(dim_property[building_name_public]),
    [Revenue Total],
    ,
    DESC,
    DENSE
)

// % del total del portfolio
Revenue % Portfolio =
DIVIDE(
    [Revenue Total],
    CALCULATE([Revenue Total], ALL(dim_property)),
    0
) * 100

// ADR por edificio vs media portfolio
ADR vs Media Portfolio =
[ADR] - CALCULATE([ADR], ALL(dim_property))

// Mejor edificio por ADR
Mejor Edificio ADR =
CALCULATE(
    SELECTEDVALUE(dim_property[building_name_public]),
    TOPN(1, ALL(dim_property), [ADR])
)
```

---

### ⭐ GRUPO 4: Reviews y Reputación

```dax
// Score medio Booking
Score Medio =
AVERAGE(fact_reviews[score])

// Score medio — solo reseñas con texto
Score Con Texto =
CALCULATE(
    AVERAGE(fact_reviews[score]),
    LEN(fact_reviews[text_full]) > 10
)

// % reseñas positivas (≥9)
Pct Reviews Positivas =
DIVIDE(
    CALCULATE(COUNTROWS(fact_reviews), fact_reviews[score] >= 9),
    COUNTROWS(fact_reviews),
    0
) * 100

// % reseñas negativas (≤6)
Pct Reviews Negativas =
DIVIDE(
    CALCULATE(COUNTROWS(fact_reviews), fact_reviews[score] <= 6),
    COUNTROWS(fact_reviews),
    0
) * 100

// Tasa de respuesta del alojamiento
Tasa Respuesta Reviews % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_reviews), fact_reviews[has_reply] <> ""),
    COUNTROWS(fact_reviews),
    0
) * 100

// Score subcategoría Personal
Score Personal =
AVERAGE(fact_reviews[Personal])

// Score subcategoría Limpieza
Score Limpieza =
AVERAGE(fact_reviews[Limpieza])

// NPS simplificado (promotores - detractores)
NPS Score =
[Pct Reviews Positivas] - [Pct Reviews Negativas]
```

---

### 💰 GRUPO 5: Rentabilidad y Gastos

```dax
// Margen neto %
Margen Neto % =
DIVIDE(
    SUM(fact_gastos[net_profit]),
    SUM(fact_gastos[revenue]),
    0
) * 100

// EBITDA
EBITDA Total =
SUM(fact_gastos[ebitda])

// Beneficio neto total
Beneficio Neto =
SUM(fact_gastos[net_profit])

// Revenue neto (tras comisiones OTA)
Revenue Neto Total =
SUM(fact_reservations[revenue_net])

// Comisiones OTA pagadas
Comisiones OTA =
SUM(fact_reservations[commission])

// % comisiones sobre revenue bruto
Pct Comision =
DIVIDE([Comisiones OTA], [Revenue Total], 0) * 100
```

---

### 🎯 GRUPO 6: Benchmarking vs Mercado

```dax
// ADR mercado Bilbao (dato estático del benchmark)
ADR Mercado Bilbao =
CALCULATE(
    AVERAGE(fact_benchmark[market_adr]),
    fact_benchmark[entity] = "Mercado Bilbao STR"
)

// Gap ADR vs mercado
Gap ADR vs Mercado = [ADR] - [ADR Mercado Bilbao]

// Revenue potencial si alcanzamos ADR de mercado
Revenue Potencial Mercado =
[ADR Mercado Bilbao] * SUM(fact_reservations[nights])

// Oportunidad de revenue no capturado
Revenue Oportunidad =
[Revenue Potencial Mercado] - [Revenue Total]

// Ocupación mercado
Ocupacion Mercado Bilbao =
CALCULATE(
    AVERAGE(fact_benchmark[market_occupancy]),
    fact_benchmark[entity] = "Mercado Bilbao STR"
)
```

---

### 🤖 GRUPO 7: Modelos Predictivos

```dax
// Ocupación predicha vs real
Delta Ocupacion Prediccion =
AVERAGE(predictions_export[predicted_occupancy_pct]) -
AVERAGE(predictions_export[actual_occupancy_pct])

// Precio predicho medio
Precio Predicho Medio =
AVERAGE(predictions_export[recommended_price])

// Upside de precio predicho vs real
Upside Precio Prediccion =
AVERAGE(predictions_export[recommended_price]) - [ADR]

// Riesgo cancelación medio
Riesgo Cancelacion Medio =
AVERAGE(predictions_export[cancellation_prob])
```

---

## 4. PÁGINAS DEL INFORME — Diseño y Visualizaciones

---

### 📄 PÁGINA 1: Executive Dashboard

**Objetivo**: Vista de un vistazo para dirección. KPIs clave con semáforos y tendencias.

**Filtros globales** (Panel de filtros laterales):
- Slicer: Año (2019–2026)
- Slicer: Edificio (dim_property[building_name_public])
- Slicer: Canal (dim_channel)

**Visualizaciones**:

| Visual | Medida | Formato |
|--------|--------|---------|
| Tarjeta KPI | `Revenue Total` | €X,XXX,XXX con flecha YoY% |
| Tarjeta KPI | `ADR` | €XXX con flecha |
| Tarjeta KPI | `RevPAR` | €XXX |
| Tarjeta KPI | `Ocupacion %` | XX.X% |
| Tarjeta KPI | `Score Medio` | X.XX/10 |
| Tarjeta KPI | `Beneficio Neto` | €X,XXX,XXX |
| Gráfico líneas | Revenue mensual + año anterior | Doble línea, área sombreada |
| Gráfico barras | Revenue por edificio | Ordenado DESC con ranking |
| Mapa de calor | Ocupación por mes × edificio | Colores rojo-amarillo-verde |
| KPI semáforo | Score vs umbral 8.5 | Conditional formatting por edificio |

**Tip PL-300**: Usar `Conditional Formatting` en las tarjetas:
- Verde si `Revenue YoY % > 0`
- Rojo si `Ocupacion % < 60%`
- Naranja si `Score Medio < 7.5`

---

### 📄 PÁGINA 2: Revenue & Rentabilidad

**Objetivo**: Análisis P&L completo para jefe financiero.

**Visualizaciones**:

| Visual | Datos | Insight |
|--------|-------|---------|
| Waterfall chart | Ingresos → Comisiones → Gastos → Beneficio | Muestra de dónde viene cada € |
| Donut chart | Mix de canales (% revenue por canal) | Dependencia de OTAs |
| Gráfico barras apiladas | Revenue vs Gastos vs Beneficio por edificio | Comparativa rentabilidad |
| Tabla detalle | Edificio / Revenue / Gastos / Margen% / Ranking | Con conditional formatting |
| Línea tendencia | Margen neto mensual 2022–2025 | Evolución en el tiempo |
| KPI card | `Comisiones OTA` total pagadas | Con `Pct Comision` como subtítulo |

**DAX especial para Waterfall** — crear medida de categoría:
```dax
Waterfall Revenue =
SWITCH(
    TRUE(),
    ISFILTERED(dim_property), [Revenue Total],
    [Revenue Total]
)
```

---

### 📄 PÁGINA 3: Patrones de Reserva

**Objetivo**: Análisis de comportamiento de huéspedes para pricing.

**Visualizaciones**:

| Visual | Datos | Insight |
|--------|-------|---------|
| Heatmap (Matrix) | Día semana × Mes · ADR | Ver qué combinaciones dan más precio |
| Scatter plot | Lead time vs ADR | Corrobora que anticipadas son más baratas |
| Barras horizontales | Reservas por país de origen | Top 10 países |
| Gráfico área | Curva de reservas por semana del año | Estacionalidad |
| Distribución | Histograma lead time (días) | 0-7d vs 7-30d vs 30-90d vs 90d+ |
| Línea + barras | Noches medias estancia por mes | Comprender ALOS (Average Length of Stay) |

**Medida adicional para scatter** (lead time segmentado):
```dax
Segmento Lead Time =
SWITCH(
    TRUE(),
    fact_reservations[lead_time_days] <= 1,    "0-1d (Last-minute)",
    fact_reservations[lead_time_days] <= 7,    "2-7d (Semana)",
    fact_reservations[lead_time_days] <= 30,   "8-30d (Mes)",
    fact_reservations[lead_time_days] <= 90,   "31-90d (Trimestre)",
                                               "91d+ (Anticipada)"
)
```

---

### 📄 PÁGINA 4: Reviews & Reputación

**Objetivo**: Dashboard de calidad y experiencia del huésped.

**Visualizaciones**:

| Visual | Datos | Insight |
|--------|-------|---------|
| Gauge | `Score Medio` por edificio · target=8.5 | Visualiza gap vs umbral premium |
| Gráfico radar | 6 subcategorías por edificio | Personal/Limpieza/Ubicación/etc. |
| Barras clustered | Score medio por año × edificio | Tendencia mejora/deterioro |
| Treemap | Frecuencia de temas NLP | Qué mencionan más los huéspedes |
| KPI card | `Tasa Respuesta Reviews %` | Con benchmark 80% como target |
| Distribución | % reviews por nota (1-10) | Histograma de satisfacción |
| Idiomas | Pie chart por language | Español/Inglés/Francés/Otros |

**Medida para gauge** (progress toward 8.5 target):
```dax
Score Progreso vs Target =
DIVIDE([Score Medio], 8.5, 0) * 100
```

---

### 📄 PÁGINA 5: Benchmarking de Mercado

**Objetivo**: Posicionamiento del portfolio vs competencia Bilbao STR.

**Visualizaciones**:

| Visual | Datos | Insight |
|--------|-------|---------|
| Bullet chart (barras) | ADR portfolio vs ADR mercado | Brecha visual clara |
| Barras agrupadas | Ocupación portfolio vs mercado por mes | Donde somos mejores/peores |
| Tabla comparativa | ADR/Occ/RevPAR Portfolio vs Mercado vs Gap | Semáforo en Gap |
| KPI card | `Revenue Oportunidad` | El número más impactante |
| Gráfico dispersión | Ocupación vs ADR por edificio | Cuadrante estratégico |
| Waterfall | Revenue actual → Oportunidad conservadora → Moderada → Optimista | Impacto de acciones |

**Cuadrante estratégico** (scatter con líneas de referencia):
- Eje X: Ocupación %
- Eje Y: ADR
- Línea vertical: Ocupación media mercado (47.6%)
- Línea horizontal: ADR medio mercado (€185)
- Cuadrante ideal: alta ocupación + alto ADR

---

### 📄 PÁGINA 6: Modelos Predictivos

**Objetivo**: Mostrar capacidad analítica avanzada con ML.

**Visualizaciones**:

| Visual | Datos | Insight |
|--------|-------|---------|
| Líneas dobles | Ocupación real vs predicha por semana 2025 | Valida el modelo A |
| Líneas dobles | Precio real vs precio recomendado 2025 | Upside de pricing |
| Tabla | Edificio/Semana/Prob.Cancelación/Riesgo | Modelo B en operación |
| Barras | Upside precio por edificio (predicho − real) | Dónde hay más oportunidad |
| KPI card | `Upside Precio Prediccion` medio | El ROI del modelo |
| Slicer | Edificio + rango de semanas 2025 | Interactividad |

---

### 📄 PÁGINA 7: Mapa Bilbao

**Objetivo**: Análisis geográfico y contexto local.

**Visualizaciones**:

| Visual | Datos |
|--------|-------|
| Mapa burbuja | dim_property · lat/long · tamaño=Revenue · color=Score |
| Tabla junto al mapa | Edificio / Barrio / Unidades / ADR / Score |
| Barras | Revenue por edificio con foto/icono de zona |
| Tooltips del mapa | Al pasar por encima: ADR, Ocupación, Score, Segmento |

**Configuración del mapa**:
- Campo ubicación: `dim_property[city]` + `dim_property[building_name_public]`
- Latitud: `dim_property[latitude]`
- Longitud: `dim_property[longitude]`
- Tamaño de burbuja: `[Revenue Total]`
- Color de burbuja: `[Score Medio]` con escala rojo→verde

---

## 5. ROW LEVEL SECURITY (RLS) — Para PL-300

Implementar RLS demuestra nivel senior. En Power BI Desktop:

`Modelado → Administrar roles → Nuevo rol`

```dax
// Rol "Gestor Edificio A" — solo ve su edificio
[building_name_public] = "Edificio A - Urban District"

// Rol "Dirección" — ve todo
// (sin filtro — acceso completo)
```

Luego en Power BI Service asignar usuarios a roles.

---

## 6. FORMATO Y DISEÑO PROFESIONAL

### Paleta de colores recomendada:
- **Azul marino** `#1F4E79` — headers, títulos
- **Azul medio** `#2E75B6` — elemento principal
- **Azul claro** `#D6E4F0` — fondos alternos
- **Verde** `#70AD47` — positivo / por encima target
- **Naranja** `#ED7D31` — atención / cerca del target
- **Rojo** `#FF0000` — crítico / bajo target
- **Gris claro** `#F2F2F2` — fondos de página

### Tipografía: Calibri 10pt (igual que el informe Word)

### Tema personalizado — importar este JSON:
Guarda como `bilbao_revenue_theme.json` e importa en `Vista → Temas`:

```json
{
  "name": "Bilbao Revenue Analytics",
  "dataColors": ["#1F4E79","#2E75B6","#70AD47","#ED7D31","#FF0000","#D6E4F0"],
  "background": "#FFFFFF",
  "foreground": "#252525",
  "tableAccent": "#1F4E79",
  "visualStyles": {
    "*": {"*": {"fontFamily": [{"value": "Calibri"}]}}
  }
}
```

---

## 7. PUBLICAR EN POWER BI SERVICE

1. `Archivo → Publicar → Power BI Service`
2. Seleccionar workspace: "Bilbao Revenue Analytics"
3. Activar actualización programada (si conectas a datos vivos)
4. Crear Dashboard fijando los KPI cards más importantes
5. Habilitar Q&A (preguntas en lenguaje natural) — impresiona en demos

---

## 8. PARA EL README DE GITHUB

Estructura del repositorio público:

```
bilbao-stravenue-analytics/
├── README.md                    ← Descripción + screenshots
├── data/
│   ├── public/                  ← Todos los CSVs anonimizados
│   └── data_dictionary.json     ← Diccionario de datos
├── powerbi/
│   └── Revenue_Analytics.pbix   ← El archivo Power BI
├── notebooks/
│   ├── 01_eda_kpis.ipynb        ← Exploración inicial
│   ├── 02_nlp_reviews.ipynb     ← Análisis NLP reviews
│   └── 03_ml_demand_pricing.ipynb ← Modelos predictivos
├── scripts/
│   ├── etl_phase0.py
│   ├── reviews_nlp_phase8.py
│   └── train_models_phase4.py
└── outputs/
    ├── reports/                 ← .md reports
    └── figures/                 ← .html interactive charts
```

### Badges para el README:
```markdown
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Power BI](https://img.shields.io/badge/Power%20BI-PL--300-yellow)
![LightGBM](https://img.shields.io/badge/ML-LightGBM-green)
![NLP](https://img.shields.io/badge/NLP-multilingual-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
```

---

## 9. CHECKLIST FINAL PL-300

| Requisito PL-300 | Implementado | Dónde |
|-----------------|:------------:|-------|
| Star schema con fact + dims | ✅ | Modelo de datos |
| Medidas DAX con CALCULATE | ✅ | Grupo 1-7 medidas |
| Time Intelligence (YoY, YTD) | ✅ | Grupo 2 |
| RANKX | ✅ | Grupo 3 |
| Row Level Security | ✅ | Sección 5 |
| Visualizaciones múltiples | ✅ | 7 páginas |
| Mapa geográfico | ✅ | Página 7 |
| Slicers y cross-filtering | ✅ | Todas las páginas |
| Conditional Formatting | ✅ | Semáforos de score |
| Tooltip personalizado | ✅ | Página mapa |
| Decomposition Tree | ✅ | Página 2 (opcional) |
| Q&A natural language | ✅ | Power BI Service |
| Publicar en Service | ✅ | Sección 7 |

**Con este proyecto cubrís el 95% del temario PL-300 con datos reales de negocio.**
