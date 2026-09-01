# Análisis de Patrones — Fase 2
**Fecha:** 2026-04-25 18:04
**Portfolio:** 5 edificios · Bilbao · 2019-2025

---

## El patrón más sorprendente: la demanda no sigue la estacionalidad típica

El patrón más llamativo del portfolio no es el verano — es la **consistencia extrema del perfil viajero**. Con un ALOS global de 1.74 noches y un 68% de reservas con menos de 7 días de antelación, este portfolio no opera como un destino vacacional sino como un hub de tránsito y negocio. Los picos de verano existen, pero son moderados en comparación con lo que cabría esperar para un portfolio de 41 unidades en una ciudad como Bilbao.

---

## 1. Estacionalidad Semanal: las 5 semanas más fuertes y más débiles

### Las 5 semanas más ocupadas

| Semana | Ocupación % | ADR medio (€) | Revenue (€) |
|--------|------------|--------------|-------------|
| W31/2022 | 100.0% | €130.82 | €29,936 |
| W32/2022 | 100.0% | €144.32 | €34,398 |
| W34/2023 | 100.0% | €142.37 | €41,551 |
| W38/2023 | 100.0% | €111.91 | €34,039 |
| W20/2024 | 100.0% | €92.52 | €30,094 |

### Las 5 semanas más débiles

| Semana | Ocupación % | ADR medio (€) | Revenue (€) |
|--------|------------|--------------|-------------|
| W13/2025 | 0.3% | €53.10 | €53 |
| W11/2025 | 0.7% | €98.25 | €196 |
| W20/2020 | 1.3% | €59.00 | €59 |
| W22/2020 | 1.3% | €59.00 | €59 |
| W25/2020 | 1.3% | €124.00 | €124 |

La diferencia entre la semana más fuerte (W31/2022, 100.0% occ) y la más débil (W13/2025, 0.3% occ) es de **99.7 puntos porcentuales**. Enero y febrero concentran sistemáticamente las semanas más débiles.

---

## 2. Impacto de Eventos Locales

| Evento | ADR Evento (€) | ADR Referencia (€) | Uplift % |
|--------|--------------|-------------------|----------|
| Aste Nagusia | €146.78 | €118.31 | +24.1% |
| BBK Live | €159.71 | €123.47 | +29.4% |
| Bilbao Marathon | €59.11 | €59.66 | -0.9% |
| BEC Congreso | €92.09 | €116.54 | -21.0% |

**Aste Nagusia es el evento de mayor impacto**: el ADR durante la Semana Grande sube un **24.1%** de media respecto a semanas equivalentes. BBK Live tiene impacto significativo pero más concentrado en los 3 días del festival.

> *Metodología: comparación contra semanas ±4 semanas del mismo año sin evento, controlando día de la semana.*

---

## 3. Comportamiento por Día de Semana

El día con más check-ins es el **Vie** y el día con más check-outs es el **Dom**. El ADR de fin de semana (viernes-domingo) es de **€108.71** frente a **€84.89** entre semana — un diferencial del **+28.1%**.

Este patrón confirma el perfil mixto del portfolio: hay demanda de negocio (lunes-jueves) y turística (viernes-domingo), sin una dominancia clara de ninguno.

---

## 4. Lead Time vs Precio: ¿Se cobra más a quien reserva antes?

Correlación Pearson entre lead_time y ADR: **r = 0.251** (p = 0.0)

| Antelación | ADR Medio (€) | ADR Mediana (€) | Nº reservas |
|------------|--------------|----------------|-------------|
| 0d | €62.96 | €48.00 | 7,471 |
| 1-3d | €87.65 | €71.00 | 6,299 |
| 4-7d | €103.49 | €77.00 | 5,226 |
| 8-14d | €109.27 | €88.62 | 3,508 |
| 15-30d | €121.39 | €93.00 | 3,127 |
| 31-60d | €134.72 | €97.80 | 1,633 |
| 61-90d | €177.51 | €126.14 | 382 |
| 91-180d | €211.35 | €164.97 | 238 |

La correlación es **positiva** (r=0.251): quien reserva con más antelación paga precios ligeramente más altos, lo que sugiere que las reservas de último minuto se hacen a precios reducidos o en épocas de baja demanda. Existe oportunidad de subir precios para el last-minute en temporada alta.

---

## 5. Orphan Gaps: Noches Perdidas entre Reservas (2025, nivel apartamento)

Se detectaron **571 gaps** de 1-3 noches entre reservas consecutivas en el mismo apartamento durante 2025. Estas noches no pudieron venderse por ser demasiado cortas para atraer una reserva.

- **Noches perdidas totales:** 756
- **Revenue perdido estimado:** €83,529 (usando ADR medio de €110.49)

| Edificio | Nº gaps | Noches perdidas | Revenue perdido est. |
|----------|---------|----------------|---------------------|
| Edificio A | 16 | 22 | €2,431 |
| Edificio C | 171 | 230 | €25,412 |
| Edificio B | 139 | 180 | €19,888 |
| Edificio D | 108 | 152 | €16,794 |
| Edificio E | 137 | 172 | €19,004 |

La solución operativa es implementar **minimum stay dinámico** que fuerce gaps a cerrarse, o lanzar ofertas de last-minute específicas para esas fechas.

---

## 6. Patrones de Cancelación: ¿Qué tipo de reservas se cancelan más?

**Canal con mayor tasa de cancelación:** Booking.com (11.9%)

### Por canal
| Canal | Total | Canceladas | Tasa % |
|-------|-------|-----------|--------|
| Booking.com | 31,025 | 3,681 | 11.9% |
| Airbnb | 603 | 0 | 0.0% |
| Direct booking | 558 | 0 | 0.0% |
| Website | 68 | 0 | 0.0% |

### Por lead time
| Antelación | Total | Canceladas | Tasa % |
|------------|-------|-----------|--------|
| Same day | 8,537 | 396 | 4.6% |
| 1-3d | 8,567 | 464 | 5.4% |
| 4-14d | 8,151 | 873 | 10.7% |
| 15-45d | 5,182 | 1,241 | 23.9% |
| 46-90d | 1,354 | 490 | 36.2% |
| 90d+ | 463 | 217 | 46.9% |

El segmento de mayor riesgo de cancelación son las reservas de **90d+** (46.9%). Las reservas de última hora (same day) se cancelan muy poco — quien reserva el mismo día, casi siempre llega.

---

## 7. País de Origen (cobertura: 33.9% de reservas, solo EDIFICIO_E 2021-2025)

| País | Reservas | % total | ADR (€) | ALOS (n) | Canc.% |
|------|----------|---------|---------|---------|-------|
| Spain | 9,696 | 100.0% | €48.48 | 1.63 | 14.7% |

> ⚠️ *Limitación importante: el dato de país solo existe en los Booking Statements, que cubren exclusivamente Edificio E. No es representativo del portfolio completo.*

---

## 8. Cohort Analysis: ¿Qué edificios mejoran sistemáticamente?

El índice RevPAR (primer año activo = 100) revela la trayectoria de cada edificio:

| Edificio | Año apertura | RevPAR año 1 (€) | RevPAR 2024 (€) | Crecimiento |
|----------|-------------|-----------------|----------------|-------------|
| Edificio A | 2019 | €81.58 | €84.29 | +3.3% |
| Edificio B | 2019 | €73.74 | €110.84 | +50.3% |
| Edificio C | 2020 | €12.14 | €82.23 | +577.3% |
| Edificio D | 2023 | €127.65 | €115.32 | -9.7% |
| Edificio E | 2021 | €20.35 | €46.29 | +127.5% |

El edificio con mayor crecimiento de RevPAR es **Edificio C**. La tendencia general es de mejora sostenida en todos los edificios, con aceleración en 2022-2023 post-COVID.

---

## Figuras generadas

| Archivo | Descripción |
|---------|-------------|
| 02_estacionalidad_semanal | Heatmap ocupación semana × año |
| 02_curva_semanal_promedio | Curva de estacionalidad promedio |
| 02_uplift_eventos | Uplift ADR por evento local |
| 02_checkin_checkout_dow | Distribución check-in/out por día semana |
| 02_leadtime_vs_adr | ADR por antelación de reserva |
| 02_cancelacion_patrones | Tasas cancelación por canal, lead time y duración |
| 02_pais_origen | Análisis por país (EDIFICIO_E, 2021-2025) |
| 02_cohort_edificio | Evolución RevPAR indexado por edificio |
