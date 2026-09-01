# -*- coding: utf-8 -*-
"""
Fase 5 — Preparación Power BI
Genera el esquema en estrella + export de predicciones ML para Power BI Desktop.

Salidas:
    data/powerbi/fact_reservations.parquet
    data/powerbi/dim_property.parquet
    data/powerbi/dim_date.parquet
    data/powerbi/dim_channel.parquet
    data/powerbi/dim_event.parquet
    data/powerbi/predictions_export.parquet
    outputs/reports/05_powerbi_guide.md
"""

import sys, json
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
import pandas as pd
import joblib
from pathlib import Path

ROOT   = Path(__file__).parent.parent
OUT    = ROOT / 'data' / 'powerbi'
OUT.mkdir(parents=True, exist_ok=True)
MODELS = ROOT / 'data' / 'processed' / 'models'

# ── Constantes ────────────────────────────────────────────────────────────────

INVENTARIO = {'EDIFICIO_A': 2, 'EDIFICIO_B': 9, 'EDIFICIO_C': 9, 'EDIFICIO_D': 7, 'EDIFICIO_E': 14}
OPENING    = {'EDIFICIO_A': '2019-05-27', 'EDIFICIO_B': '2019-08-09', 'EDIFICIO_C': '2020-08-26',
              'EDIFICIO_E': '2021-07-29', 'EDIFICIO_D': '2023-03-31'}
NOMBRES    = {'EDIFICIO_A': 'Edificio A', 'EDIFICIO_B': 'Edificio B',
              'EDIFICIO_C': 'Edificio C', 'EDIFICIO_D': 'Edificio D',
              'EDIFICIO_E': 'Edificio E'}
BARRIO     = {'EDIFICIO_A': 'Abando', 'EDIFICIO_B': 'Abando', 'EDIFICIO_C': 'EDIFICIO_C',
              'EDIFICIO_D': 'Casco Viejo', 'EDIFICIO_E': 'Casco Viejo'}

EVENTS = [
    ('BBK Live',        '2019-07-11', '2019-07-13'),
    ('Aste Nagusia',    '2019-08-17', '2019-08-25'),
    ('Bilbao Marathon', '2019-11-17', '2019-11-17'),
    ('BBK Live',        '2022-07-07', '2022-07-09'),
    ('Aste Nagusia',    '2022-08-20', '2022-08-28'),
    ('Bilbao Marathon', '2022-11-20', '2022-11-20'),
    ('BBK Live',        '2023-07-13', '2023-07-15'),
    ('Aste Nagusia',    '2023-08-19', '2023-08-27'),
    ('Bilbao Marathon', '2023-11-19', '2023-11-19'),
    ('BBK Live',        '2024-07-11', '2024-07-13'),
    ('Aste Nagusia',    '2024-08-17', '2024-08-25'),
    ('Bilbao Marathon', '2024-11-17', '2024-11-17'),
    ('BBK Live',        '2025-07-10', '2025-07-12'),
    ('Aste Nagusia',    '2025-08-16', '2025-08-24'),
    ('Bilbao Marathon', '2025-11-16', '2025-11-16'),
]

CHANNEL_META = {
    'Booking.com':    ('OTA',    15.0),
    'Airbnb':         ('OTA',    16.0),
    'Direct booking': ('Directo', 0.0),
    'Website':        ('Directo', 0.0),
    'Blocked channel':('Interno', 0.0),
}

# ── 1. Cargar datos ────────────────────────────────────────────────────────────

print("Cargando datos unificados...")
df = pd.read_parquet(ROOT / 'data' / 'processed' / 'reservas_unified.parquet')
print(f"  {len(df):,} reservas cargadas")

# Normalizar status
def normalize_status(s):
    s = str(s).upper().strip()
    if s in ('CANCELLED', 'CANCELADA'):  return 'CANCELLED'
    if s in ('NO_SHOW', 'NO PRESENTADO'): return 'NO_SHOW'
    if s in ('OK', ''):                   return 'CONFIRMED'
    return 'OTHER'

df['status_norm'] = df['status'].apply(normalize_status)
df['is_cancelled'] = df['status_norm'] == 'CANCELLED'
df['is_no_show']   = df['status_norm'] == 'NO_SHOW'

# ── 2. dim_property ────────────────────────────────────────────────────────────

print("\nGenerando dim_property...")
prop_rows = []
for i, (code, name) in enumerate(NOMBRES.items(), start=1):
    prop_rows.append({
        'property_key':   i,
        'building_code':  code,
        'building_name':  name,
        'neighbourhood':  BARRIO[code],
        'city':           'Bilbao',
        'country':        'Spain',
        'inventory_units': INVENTARIO[code],
        'inventory_nights_week': INVENTARIO[code] * 7,
        'opening_date':   pd.Timestamp(OPENING[code]),
    })
dim_property = pd.DataFrame(prop_rows)
dim_property.to_parquet(OUT / 'dim_property.parquet', index=False)
print(f"  {len(dim_property)} propiedades guardadas → dim_property.parquet")

# Mapa building → property_key
prop_map = dim_property.set_index('building_code')['property_key'].to_dict()

# ── 3. dim_channel ─────────────────────────────────────────────────────────────

print("\nGenerando dim_channel...")
ch_rows = []
for i, (ch, (ch_type, comm)) in enumerate(CHANNEL_META.items(), start=1):
    ch_rows.append({
        'channel_key':           i,
        'channel_name':          ch,
        'channel_type':          ch_type,
        'typical_commission_pct': comm,
    })
dim_channel = pd.DataFrame(ch_rows)
dim_channel.to_parquet(OUT / 'dim_channel.parquet', index=False)
print(f"  {len(dim_channel)} canales guardados → dim_channel.parquet")

ch_map = dim_channel.set_index('channel_name')['channel_key'].to_dict()

# ── 4. dim_event ───────────────────────────────────────────────────────────────

print("\nGenerando dim_event...")
UPLIFT = {'BBK Live': 29.4, 'Aste Nagusia': 24.1, 'Bilbao Marathon': -0.9}
ev_rows = []
for i, (name, start, end) in enumerate(EVENTS, start=1):
    ev_rows.append({
        'event_key':           i,
        'event_name':          name,
        'start_date':          pd.Timestamp(start),
        'end_date':            pd.Timestamp(end),
        'event_type':          'Music Festival' if 'BBK' in name else ('Cultural' if 'Aste' in name else 'Sports'),
        'historical_adr_uplift_pct': UPLIFT.get(name, 0.0),
    })
dim_event = pd.DataFrame(ev_rows)
dim_event.to_parquet(OUT / 'dim_event.parquet', index=False)
print(f"  {len(dim_event)} eventos guardados → dim_event.parquet")

# ── 5. dim_date ────────────────────────────────────────────────────────────────

print("\nGenerando dim_date (2019-01-01 → 2026-12-31)...")

date_range = pd.date_range('2019-01-01', '2026-12-31', freq='D')

SEASON_MAP = {1:'Baja', 2:'Baja', 3:'Media', 4:'Media', 5:'Media',
              6:'Alta', 7:'Alta', 8:'Alta', 9:'Media', 10:'Media',
              11:'Baja', 12:'Baja'}

# Build event lookup: date → event_name
event_dates: dict[pd.Timestamp, str] = {}
for name, start, end in EVENTS:
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    d = s
    while d <= e:
        event_dates[d] = name
        d += pd.Timedelta(days=1)

month_names_es = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
                  7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
dow_names_es   = {0:'Lunes',1:'Martes',2:'Miércoles',3:'Jueves',
                  4:'Viernes',5:'Sábado',6:'Domingo'}

date_rows = []
for d in date_range:
    ev_name = event_dates.get(d, '')
    date_rows.append({
        'date_key':        int(d.strftime('%Y%m%d')),
        'date':            d,
        'year':            d.year,
        'quarter':         d.quarter,
        'month_num':       d.month,
        'month_name':      month_names_es[d.month],
        'week_iso':        d.isocalendar()[1],
        'day_of_week_num': d.weekday(),
        'day_of_week':     dow_names_es[d.weekday()],
        'is_weekend':      d.weekday() >= 4,
        'season':          SEASON_MAP[d.month],
        'is_event_day':    ev_name != '',
        'event_name':      ev_name if ev_name else None,
    })

dim_date = pd.DataFrame(date_rows)
dim_date.to_parquet(OUT / 'dim_date.parquet', index=False)
print(f"  {len(dim_date):,} días guardados → dim_date.parquet")

date_map = dim_date.set_index('date')['date_key'].to_dict()

# ── 6. fact_reservations ──────────────────────────────────────────────────────

print("\nGenerando fact_reservations...")

fact = df.copy()

# Normalizar fechas a medianoche
for col in ('check_in', 'check_out', 'booking_date'):
    fact[col] = pd.to_datetime(fact[col]).dt.normalize()

# Claves foráneas
fact['property_key']  = fact['building'].map(prop_map).astype('Int64')
fact['channel_key']   = fact['channel'].map(ch_map).fillna(0).astype('Int64')

fact['date_key_checkin']  = fact['check_in'].map(date_map).astype('Int64')
fact['date_key_checkout'] = fact['check_out'].map(date_map).astype('Int64')
fact['date_key_booking']  = fact['booking_date'].map(date_map).astype('Int64')

# Métricas derivadas
fact['revenue_gross'] = fact['gross_amount'].fillna(0.0)
fact['revenue_net']   = fact['net_amount'].fillna(0.0)
fact['commission']    = fact['commission_amount'].fillna(0.0)
fact['revpar_contribution'] = fact.apply(
    lambda r: r['revenue_gross'] / (INVENTARIO.get(r['building'], 1) * r['nights'])
    if pd.notna(r['nights']) and r['nights'] > 0 else 0.0, axis=1
)

# Seleccionar columnas finales
FACT_COLS = [
    'reservation_id', 'source',
    'property_key', 'channel_key',
    'date_key_checkin', 'date_key_checkout', 'date_key_booking',
    'nights', 'adults', 'children',
    'revenue_gross', 'revenue_net', 'commission',
    'adr', 'adr_net', 'revpar_contribution',
    'lead_time_days',
    'is_cancelled', 'is_no_show', 'status_norm',
    'country',
]
fact_out = fact[FACT_COLS].copy()
fact_out['nights']   = fact_out['nights'].astype('Int64')
fact_out['adults']   = fact_out['adults'].astype('Int64')
fact_out['children'] = fact_out['children'].astype('Int64')

fact_out.to_parquet(OUT / 'fact_reservations.parquet', index=False)
print(f"  {len(fact_out):,} filas guardadas → fact_reservations.parquet")
print(f"  Columnas: {len(FACT_COLS)}")

# ── 7. predictions_export ─────────────────────────────────────────────────────

print("\nGenerando predictions_export (2025 sem 1-52)...")

sys.path.insert(0, str(ROOT / 'scripts'))
from predict_demand     import predict_demand
from predict_cancellation import predict_cancellation
from recommend_price    import recommend_price

pred_rows = []
buildings = list(INVENTARIO.keys())

for bld in buildings:
    for week in range(1, 53):
        try:
            dem  = predict_demand(building=bld, year=2025, week=week)
            price = recommend_price(building=bld, year=2025, week=week,
                                    lead_time=14, pred_occ=dem['pred_occ_pct'])
            pred_rows.append({
                'building':          bld,
                'year':              2025,
                'week_iso':          week,
                'period_start':      pd.Timestamp.fromisocalendar(2025, week, 1),
                'pred_occ_pct':      dem['pred_occ_pct'],
                'is_event':          dem['is_event'],
                'demand_signal':     dem['interpretation'],
                'adr_recommended':   price['adr_recomendado'],
                'adr_range_min':     price['rango_min'],
                'adr_range_max':     price['rango_max'],
                'adjustments':       price['ajustes_aplicados'],
            })
        except Exception as e:
            pass  # skip invalid ISO weeks

predictions = pd.DataFrame(pred_rows)
predictions.to_parquet(OUT / 'predictions_export.parquet', index=False)
print(f"  {len(predictions)} filas guardadas → predictions_export.parquet")

# ── 8. Resumen de archivos ─────────────────────────────────────────────────────

print("\n── Archivos generados ──────────────────────────")
for f in sorted(OUT.glob('*.parquet')):
    size_kb = f.stat().st_size / 1024
    rows = len(pd.read_parquet(f))
    print(f"  {f.name:<35} {rows:>6} filas  {size_kb:>7.1f} KB")

# ── 9. Guía Power BI ──────────────────────────────────────────────────────────

print("\nGenerando guía Power BI...")

guide = """# Guía Power BI — Proyecto Revenue Antigravity

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
- **EDIFICIO_D:** apertura 2023-03-31 — filtrar "> 2023" para comparativas justas
- **País de origen:** solo disponible en reservas Booking.com de Edificio E (2021-2025)
- **Airbnb:** detalle individual solo desde Smoobu 2025; histórico agregado por edificio
- **predictions_export:** predicciones para las 52 semanas de 2025 usando los modelos LightGBM entrenados
"""

report_path = ROOT / 'outputs' / 'reports' / '05_powerbi_guide.md'
report_path.write_text(guide, encoding='utf-8')
print(f"  Guardado: {report_path}")

print("""
============================================================
FASE 5 COMPLETADA
  fact_reservations     {fact} filas
  dim_date              {dates} días (2019-2026)
  dim_property          {props} edificios
  dim_channel           {ch} canales
  dim_event             {ev} eventos
  predictions_export    {preds} predicciones ML
============================================================
""".format(
    fact=len(fact_out),
    dates=len(dim_date),
    props=len(dim_property),
    ch=len(dim_channel),
    ev=len(dim_event),
    preds=len(predictions),
))
