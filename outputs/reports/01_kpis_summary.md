# KPIs Base — Fase 1
**Fecha:** 2026-04-25 17:19
**Período:** 2019-2025 | **Portfolio:** 41 unidades rentables en 5 edificios

---

## KPIs Globales del Portfolio

| KPI | Valor global (2019-2025) |
|-----|--------------------------|
| Revenue bruto total | €4,997,222 |
| Revenue neto total | €4,404,239 |
| ADR global | €100.77 |
| RevPAR global | €68.34 |
| Ocupación media | 67.8% |
| ALOS medio | 1.74 noches |
| Lead Time medio | 9 días |
| Tasa cancelación | 11.4% |
| Total reservas (activas) | 28,573 |

> **Nota inventario:** RevPAR y Ocupación calculados con 41 unidades rentables:
> Edificio A(2) + Edificio B(9) + Edificio C(9) + Edificio D(7) + Edificio E(14).
> Para 2019-2024, los edificios no-EDIFICIO_E solo tienen granularidad por edificio (no apartamento).

---

## Evolución Anual de KPIs

|   Año |   Revenue (€) |   ADR (€) |   RevPAR (€) | Ocupación %   |   ALOS (noches) |   Lead Time (d) | Canc. Rate %   |   Nº Reservas |
|------:|--------------:|----------:|-------------:|:--------------|----------------:|----------------:|:---------------|--------------:|
|  2019 |       131,963 |    110.71 |        75.71 | 68.4%         |            2.02 |              18 | 22.3%          |           589 |
|  2020 |       129,435 |     84.1  |        25    | 29.7%         |            1.98 |               8 | 24.3%          |           778 |
|  2021 |       356,545 |     88.76 |        37.59 | 42.4%         |            1.85 |               7 | 20.6%          |         2,176 |
|  2022 |       724,229 |     82.92 |        58.36 | 70.4%         |            1.67 |               7 | 13.4%          |         5,240 |
|  2023 |     1,149,008 |     99.58 |        80.11 | 80.4%         |            1.69 |              13 | 14.5%          |         6,846 |
|  2024 |     1,230,334 |    105.74 |        81.99 | 77.5%         |            1.65 |               9 | 9.0%           |         7,044 |
|  2025 |     1,275,708 |    116.69 |        85.25 | 73.1%         |            1.85 |               7 | 0.4%           |         5,900 |

---

## Net ADR por Canal

| Canal | ADR Bruto (€) | ADR Neto (€) | Comisión media % |
|-------|--------------|-------------|-----------------|
| Airbnb | €126.07 | €126.07 | 0.0% |
| Booking.com | €99.72 | €87.01 | 12.7% |
| Direct booking | €113.63 | €113.63 | 0.0% |
| Website | €114.53 | €114.53 | 0.0% |

---

## Distribución Booking Window

| Segmento | Reservas | % |
|----------|----------|---|
| Same day | 7,471 | 26.8% |
| 1-3d | 6,299 | 22.6% |
| 4-7d | 5,226 | 18.7% |
| 8-14d | 3,508 | 12.6% |
| 15-30d | 3,127 | 11.2% |
| 31-60d | 1,633 | 5.9% |
| 61-90d | 382 | 1.4% |
| 91-180d | 237 | 0.8% |
| 180d+ | 20 | 0.1% |

---

## ADR por Día de Semana

| Día | ADR medio (€) |
|-----|--------------|
| Lun | €77.54 |
| Mar | €78.68 |
| Mié | €92.46 |
| Jue | €91.60 |
| Vie | €122.23 |
| Sáb | €126.87 |
| Dom | €74.92 |

---

## Revenue por Edificio (2019-2025)

| Edificio | Revenue Total (€) | % del portfolio |
|----------|------------------|----------------|
| Edificio B | €1,663,712 | 33.3% |
| Edificio C | €1,094,924 | 21.9% |
| Edificio E | €991,891 | 19.8% |
| Edificio D | €926,019 | 18.5% |
| Edificio A | €320,675 | 6.4% |

---

## Figuras generadas

| Archivo | Descripción |
|---------|-------------|
| 01_revenue_anual_canal | Revenue bruto anual apilado por canal |
| 01_adr_revpar_mensual | ADR y RevPAR mensual (líneas) |
| 01_ocupacion_heatmap | Heatmap ocupación % mes × año |
| 01_alos_canal_anual | ALOS por año y canal |
| 01_booking_window | Histograma distribución lead time |
| 01_mix_canales_anual | Mix canales % revenue por año |
| 01_cancellation_rate | Tasa cancelación por año y canal |
| 01_adr_dia_semana | ADR medio por día de la semana |
| 01_net_adr_canal | ADR bruto vs neto por canal |
| 01_revenue_edificio_anual | Revenue por edificio y año |

> Todas las figuras disponibles en formato interactivo (.html) y estático (.png) en `outputs/figures/`.
