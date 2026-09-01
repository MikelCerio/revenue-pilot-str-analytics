# Guía Power BI — Proyecto Revenue Antigravity

## Esquema en Estrella

```
                        ┌─────────────────┐
                        │   dim_date      │
                        │─────────────────│
                        │ date_key (PK)   │
                        │ date            │
                        │ year / quarter  │
                        │ month_name      │
                        │ week_iso        │
                        │ day_of_week     │
                        │ is_weekend      │
                        │ season          │
                        │ is_event_day    │
                        │ event_name      │
                        └────────┬────────┘
                                 │ ×3 (checkin/checkout/booking)
┌──────────────────┐    ┌────────▼────────────────────────────┐    ┌──────────────────┐
│  dim_property    │    │         fact_reservations           │    │   dim_channel    │
│──────────────────│    │─────────────────────────────────────│    │──────────────────│
│ property_key(PK) ├────┤ property_key (FK)                   ├────┤ channel_key (PK) │
│ building_code    │    │ channel_key (FK)                    │    │ channel_name     │
│ building_name    │    │ date_key_checkin (FK)               │    │ channel_type     │
│ neighbourhood    │    │ date_key_checkout (FK)              │    │ commission_pct   │
│ inventory_units  │    │ date_key_booking (FK)               │    └──────────────────┘
│ opening_date     │    │ reservation_id                      │
└──────────────────┘    │ nights / adults / children          │
                        │ revenue_gross / revenue_net         │
                        │ adr / adr_net                       │
                        │ lead_time_days                      │
                        │ is_cancelled / is_no_show           │
                        │ country                             │
                        └─────────────────────────────────────┘
```

---

## Importar en Power BI Desktop

1. **Obtener datos → Parquet** y conectar a cada archivo en `data/powerbi/`:
   - `fact_reservations.parquet`
   - `dim_property.parquet`
   - `dim_date.parquet`
   - `dim_channel.parquet`
   - `dim_event.parquet`
   - `predictions_export.parquet`

2. **Relaciones** (vista Modelo):
   | Tabla origen | Campo | Tabla destino | Campo |
   |---|---|---|---|
   | fact_reservations | property_key | dim_property | property_key |
   | fact_reservations | channel_key | dim_channel | channel_key |
   | fact_reservations | date_key_checkin | dim_date | date_key |

   > Para checkout y booking crea relaciones inactivas y actívalas con `USERELATIONSHIP()`.

3. **Marcar dim_date como Tabla de Fechas**:
   - Pestaña Tabla → Marcar como tabla de fechas → columna `date`

---

## Medidas DAX

### KPIs Base

```dax
-- Ingresos totales (bruto)
Total Revenue =
    SUMX(fact_reservations, fact_reservations[revenue_gross])

-- ADR medio
ADR =
    DIVIDE(
        SUMX(fact_reservations, fact_reservations[adr] * fact_reservations[nights]),
        SUMX(fact_reservations, fact_reservations[nights]),
        0
    )

-- Noches disponibles (ajustadas por apertura de edificio)
Available Nights =
    SUMX(
        dim_property,
        VAR opening = dim_property[opening_date]
        VAR units   = dim_property[inventory_units]
        RETURN
            CALCULATE(
                COUNTROWS(dim_date),
                dim_date[date] >= opening,
                USERELATIONSHIP(dim_date[date_key], fact_reservations[date_key_checkin])
            ) * units
    )

-- Noches vendidas
Sold Nights =
    SUMX(fact_reservations,
         IF(NOT fact_reservations[is_cancelled], fact_reservations[nights], 0))

-- Ocupación %
Occupancy % =
    DIVIDE([Sold Nights], [Available Nights], 0) * 100

-- RevPAR
RevPAR =
    DIVIDE([Total Revenue], [Available Nights], 0)

-- Tasa de cancelación %
Cancellation Rate % =
    DIVIDE(
        COUNTROWS(FILTER(fact_reservations, fact_reservations[is_cancelled])),
        COUNTROWS(fact_reservations),
        0
    ) * 100

-- Estancia media (ALOS)
ALOS =
    DIVIDE([Sold Nights], COUNTROWS(FILTER(fact_reservations, NOT fact_reservations[is_cancelled])), 0)

-- Lead time medio
Avg Lead Time =
    AVERAGEX(
        FILTER(fact_reservations, NOT fact_reservations[is_cancelled]),
        fact_reservations[lead_time_days]
    )
```

### Comparativas YoY

```dax
-- Ingresos año anterior
Revenue LY =
    CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(dim_date[date]))

-- Variación YoY %
Revenue YoY % =
    DIVIDE([Total Revenue] - [Revenue LY], [Revenue LY], BLANK()) * 100

-- ADR año anterior
ADR LY =
    CALCULATE([ADR], SAMEPERIODLASTYEAR(dim_date[date]))

-- Ocupación año anterior
Occupancy LY =
    CALCULATE([Occupancy %], SAMEPERIODLASTYEAR(dim_date[date]))
```

### Análisis de Eventos

```dax
-- RevPAR en semanas de evento
RevPAR Event Weeks =
    CALCULATE(
        [RevPAR],
        FILTER(dim_date, dim_date[is_event_day] = TRUE())
    )

-- RevPAR en semanas sin evento
RevPAR Non-Event Weeks =
    CALCULATE(
        [RevPAR],
        FILTER(dim_date, dim_date[is_event_day] = FALSE())
    )

-- Uplift por eventos
Event Uplift % =
    DIVIDE([RevPAR Event Weeks] - [RevPAR Non-Event Weeks],
           [RevPAR Non-Event Weeks], BLANK()) * 100
```

### Revenue Perdido (Gaps)

```dax
-- Noches con reservas confirmadas
Confirmed Nights =
    SUMX(
        FILTER(fact_reservations, NOT fact_reservations[is_cancelled]),
        fact_reservations[nights]
    )

-- Noches potenciales perdidas (gap)
Gap Nights =
    [Available Nights] - [Confirmed Nights]

-- Revenue potencial de gaps (al ADR actual)
Gap Revenue Opportunity =
    [Gap Nights] * [ADR]
```

### Predicciones ML

```dax
-- ADR recomendado promedio (de predictions_export)
Recommended ADR Avg =
    AVERAGE(predictions_export[adr_recommended])

-- Diferencia ADR actual vs recomendado
ADR vs Recommended =
    [ADR] - [Recommended ADR Avg]
```

---

## Dashboards Recomendados

### Página 1 — Executive Summary
**KPIs tarjeta:** Total Revenue | ADR | RevPAR | Occupancy % | ALOS | Cancellation Rate %
**Gráficos:**
- Ingresos mensuales por edificio (columnas apiladas)
- Ocupación % YoY (líneas dobles)
- Mapa de calor: edificio × mes → RevPAR

### Página 2 — Análisis de Estacionalidad
- Ocupación semanal (línea, 52 semanas)
- ADR por semana con marcadores de eventos (scatter + línea)
- Heatmap: semana ISO × edificio

### Página 3 — Canales y Origen
- Mix de canales: pie chart (por revenue)
- ADR por canal (barras horizontales)
- Tendencia Airbnb vs Booking.com (líneas)
- Mapa de países de origen (si disponible)

### Página 4 — Análisis de Cancelaciones
- Cancelaciones % por mes y edificio
- Distribución lead time: canceladas vs confirmadas (histograma)
- Tasa cancelación por canal y lead time bucket

### Página 5 — Precios y Oportunidades
- ADR actual vs recomendado por semana (predictions_export)
- Revenue potencial adicional por edificio
- Semáforo: ocupación predicha (ALTO/MEDIO/BAJO)
- Top semanas con mayor uplift potencial (tabla)

### Página 6 — Revenue Perdido
- Nights gap por mes y edificio
- Gap Revenue Opportunity acumulado
- Resumen de oportunidades priorizadas

---

## Filtros Recomendados (Slicers)

| Slicer | Tabla | Campo |
|---|---|---|
| Año | dim_date | year |
| Edificio | dim_property | building_name |
| Canal | dim_channel | channel_name |
| Temporada | dim_date | season |
| Evento | dim_date | event_name |
| Rango de fechas | dim_date | date |

---

## Notas de Datos

- **Reservas activas:** ~28,500 (excluyendo Airbnb histórico sin detalle)
- **Período:** 2019-2025 (datos 2025 parciales hasta fecha de extracción)
- **Edificio D:** apertura 2023-03-31 — filtrar "> 2023" para comparativas justas
- **País de origen:** solo disponible en reservas Booking.com de Edificio E (2021-2025)
- **Airbnb:** detalle individual solo desde Smoobu 2025; histórico agregado por edificio
- **predictions_export:** predicciones para las 52 semanas de 2025 usando los modelos LightGBM entrenados
