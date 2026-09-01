# Guía Power BI — Revenue Management Dashboard
## Modelo de datos, medidas DAX y estructura de páginas

---

## 1. ARCHIVOS CSV A IMPORTAR

Estos archivos ya están generados en tu proyecto:

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `f_master_reservas.csv` | Tabla de hechos | 1 fila = 1 reserva (principal) |
| `f_kpis_edificio_mes.csv` | Tabla agregada | KPIs por edificio × año × mes |
| `f_kpis_canal.csv` | Tabla agregada | KPIs por canal × edificio × año × mes |
| `d_apartamentos.csv` | Dimensión | Catálogo de apartamentos |
| `f_gastos_2025.csv` | Tabla de hechos | Gastos operativos 2025 |
| `reservas_sinteticas.csv` | Demo | Datos ficticios para portfolio público |
| `pyl_sintetico.csv` | Demo | P&L sintético para demo |

### Configuración de importación
- **Separador:** punto y coma (;)
- **Decimal:** coma (,)
- **Encoding:** UTF-8 BOM

---

## 2. MODELO DE DATOS (ESTRELLA)

```
                    ┌─────────────────┐
                    │  d_calendario   │
                    │─────────────────│
                    │ fecha           │
                    │ año             │
                    │ mes             │
                    │ trimestre       │
                    │ dia_semana      │
                    │ es_finde        │
                    │ semana_iso      │
                    └────────┬────────┘
                             │
    ┌────────────┐    ┌──────┴──────────┐    ┌──────────────┐
    │ d_edificio │    │ f_master_reservas│    │  d_canal     │
    │────────────│    │─────────────────│    │──────────────│
    │ edificio   │◄───┤ edificio        ├───►│ canal        │
    │ n_aptos    │    │ arrival (fecha) │    │ comision_pct │
    │ zona       │    │ canal           │    │ tipo         │
    └────────────┘    │ price           │    └──────────────┘
                      │ net_revenue     │
                      │ noches          │
                      │ lead_time       │
                      │ cancelled       │
                      │ adr, adr_net    │
                      └─────────────────┘
```

### Crear tabla d_calendario en DAX:

```dax
d_calendario = 
ADDCOLUMNS(
    CALENDAR(DATE(2019,1,1), DATE(2026,12,31)),
    "Año", YEAR([Date]),
    "Mes", MONTH([Date]),
    "Mes_Nombre", FORMAT([Date], "MMMM"),
    "Trimestre", "Q" & FORMAT([Date], "Q"),
    "Dia_Semana", FORMAT([Date], "dddd"),
    "Es_Finde", IF(WEEKDAY([Date],2) >= 5, 1, 0),
    "Semana_ISO", WEEKNUM([Date], 21),
    "Año_Mes", FORMAT([Date], "YYYY-MM")
)
```

### Crear tabla d_edificio:

```dax
d_edificio = 
DATATABLE(
    "edificio", STRING,
    "n_apartamentos", INTEGER,
    "zona", STRING,
    {
        {"Edificio A", 2, "Centro"},
        {"Edificio B", 9, "Edificio B"},
        {"Edificio C", 9, "EDIFICIO_C"},
        {"Edificio D", 8, "Casco Viejo"},
        {"Edificio E", 18, "Centro"},
        {"GARAJE", 3, "Centro"}
    }
)
```

---

## 3. MEDIDAS DAX ESENCIALES

```dax
// === KPIs PRINCIPALES ===

Revenue Bruto = 
SUM(f_master_reservas[revenue_efectivo])

Revenue Neto = 
SUM(f_master_reservas[net_revenue_efectivo])

Comisiones OTA = 
[Revenue Bruto] - [Revenue Neto]

ADR = 
DIVIDE(
    [Revenue Bruto],
    SUM(f_master_reservas[nights]),
    0
)

Noches Disponibles = 
SUMX(
    d_edificio,
    d_edificio[n_apartamentos] * 
    COUNTROWS(FILTER(d_calendario, 
        d_calendario[Año] = SELECTEDVALUE(d_calendario[Año])))
)

Ocupacion = 
DIVIDE(
    SUM(f_master_reservas[nights]),
    [Noches Disponibles],
    0
)

RevPAR = 
[ADR] * [Ocupacion]

ALOS = 
DIVIDE(
    SUM(f_master_reservas[nights]),
    COUNTROWS(f_master_reservas),
    0
)

Lead Time Medio = 
AVERAGE(f_master_reservas[lead_time])

// === COMPARATIVAS YoY ===

Revenue YoY = 
VAR CurrentRev = [Revenue Bruto]
VAR PriorRev = CALCULATE([Revenue Bruto], SAMEPERIODLASTYEAR(d_calendario[Date]))
RETURN DIVIDE(CurrentRev - PriorRev, PriorRev, 0)

ADR YoY = 
VAR CurrentADR = [ADR]
VAR PriorADR = CALCULATE([ADR], SAMEPERIODLASTYEAR(d_calendario[Date]))
RETURN CurrentADR - PriorADR

// === ANÁLISIS DE CANALES ===

Pct Canal Directo = 
DIVIDE(
    CALCULATE([Revenue Bruto], 
        f_master_reservas[canal] IN {"Direct booking", "Website"}),
    [Revenue Bruto],
    0
)

Coste Adquisicion por Reserva = 
DIVIDE(
    [Comisiones OTA],
    COUNTROWS(FILTER(f_master_reservas, 
        f_master_reservas[canal] IN {"Booking.com", "Airbnb"})),
    0
)

// === CANCELACIONES ===

Tasa Cancelacion = 
DIVIDE(
    COUNTROWS(FILTER(f_master_reservas, f_master_reservas[cancelled] = 1)),
    COUNTROWS(f_master_reservas),
    0
)

// === GOP ===

GOP = 
[Revenue Bruto] - SUM(f_gastos_2025[importe])

Margen GOP = 
DIVIDE([GOP], [Revenue Bruto], 0)
```

---

## 4. ESTRUCTURA DE PÁGINAS

### Página 1 — Executive Overview
- 5 tarjetas KPI: Revenue, ADR, Ocupación, RevPAR, GOP
- Gráfico de barras: Revenue mensual (bruto vs neto)
- Gráfico de líneas: ADR + Ocupación trending
- Slicer: Año, Edificio, Canal

### Página 2 — Channel Intelligence
- Donut chart: mix de canales (% revenue)
- Tabla: Canal × Gross ADR × Net ADR × Comisión × Reservas
- Barras apiladas: evolución canal directo vs OTA por año
- KPI card: "Ahorro si +10% directo"

### Página 3 — Portfolio Performance
- Scatter plot: ADR vs RevPAR por edificio (tamaño = revenue)
- Heatmap: Ocupación edificio × mes
- Ranking: edificios por margen GOP
- Semáforo: edificios underpriced vs on-track

### Página 4 — Pricing & Forecast
- Línea: ADR P75 por mes y edificio (precio base sugerido)
- Waterfall: Revenue perdido por componente
- Tabla: reglas de pricing recomendadas
- KPI: oportunidad total (€382K-€928K)

### Página 5 — ML Insights
- Feature importance Modelo C (precio)
- Scatter: Real vs Predicho
- Distribución probabilidad cancelación
- KPI: ROC-AUC, MAE

### Página 6 — Trends (YoY)
- Revenue YoY por edificio
- Cohort: RevPAR indexado desde apertura
- Estacionalidad: curva semanal promedio

---

## 5. TIPS DE DISEÑO

- **Tema:** Oscuro (similar al RevenuePilot Streamlit)
- **Colores:** #0a0f1e fondo, #22d3a0 acento positivo, #ef4444 negativo, #f59e0b warning
- **Fuente:** Segoe UI o DM Sans
- **Interactividad:** Cross-filter entre todas las páginas
- **Bookmarks:** crear vistas por edificio para presentaciones rápidas

---

## 6. PARA PORTFOLIO PÚBLICO (CON DATOS SINTÉTICOS)

Para subir a GitHub/LinkedIn sin exponer datos reales:
1. Usa `reservas_sinteticas.csv` y `pyl_sintetico.csv` (ya generados)
2. Los nombres de propiedades están anonimizados
3. Mantén la misma estructura de Power BI
4. Exporta a PDF las páginas más visuales para LinkedIn
