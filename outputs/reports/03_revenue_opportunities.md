# Análisis de Pricing y Revenue Perdido — Fase 3
**Fecha:** 2026-04-25 18:25
**Portfolio:** 5 edificios · Bilbao · 2019-2025

---

## Resumen Ejecutivo

El portfolio dejó entre **€308,456** (conservador) y **€772,599** (optimista) de revenue sobre la mesa durante 2019-2025, representando entre el **6.2%** y el **15.5%** del revenue histórico generado (€4,997,222).

El principal driver de revenue perdido es el **pricing estático en semanas de alta demanda**: 3.3% de las semanas-edificio analizadas muestran señal de saturación rápida (se llenaron con mucha antelación a precio bajo). El segundo driver son los **orphan gaps** entre reservas.

---

## 1. Señales de Pricing Subóptimo

### Saturación rápida (precio demasiado bajo)
Se detectaron **41 semanas-edificio** (3.3% del total) donde la ocupación superó el 80% con un lead time medio superior a 21 días. Esto indica que las habitaciones se vendieron con mucha antelación — señal clara de precio por debajo del óptimo. Subiendo el precio un 15-25% en esas ventanas, el revenue habría sido mayor aunque se vendieran ligeramente menos noches.

### Cierre tardío (precio inicial alto)
Se detectaron **246 semanas-edificio** (19.9% del total) con ocupación baja (<60%) y reservas llegando tarde (lead time <7d). Probable causa: precio inicial demasiado alto que ahuyentó la demanda temprana, seguido de bajada de precio de emergencia.

### Precio decreciente dentro de la semana
**341 semanas-edificio** muestran que la primera reserva de la semana pagó más que la última. Confirma el patrón de "vender caro y bajar para cerrar".

### Por edificio:
| Edificio | Semanas saturación rápida % | Semanas cierre tardío % | Occ media % |
|----------|---------------------------|------------------------|-------------|
| Edificio A | 8.2% | 15.4% | 76.6% |
| Edificio C | 0.4% | 33.0% | 53.6% |
| Edificio B | 1.9% | 24.1% | 59.7% |
| Edificio D | 2.3% | 13.1% | 75.4% |
| Edificio E | 2.4% | 7.7% | 87.8% |

---

## 2. ADR Óptimo Retroactivo

### Top 10 semanas con mayor revenue perdido estimado
| Sem/Año | Edificio | Occ% | ADR real (€) | ADR óptimo (€) | Revenue real (€) | Rev. perdido est. (€) |
|---------|----------|------|-------------|---------------|-----------------|----------------------|
| W48/2025 | Edificio D | 100% | €116.06 | €121.86 | €2,489 | €7,991 |
| W21/2025 | Edificio B | 100% | €349.68 | €367.16 | €21,707 | €4,729 |
| W21/2025 | Edificio C | 100% | €315.39 | €331.16 | €20,197 | €3,646 |
| W21/2024 | Edificio B | 81% | €233.62 | €268.66 | €10,232 | €3,470 |
| W21/2025 | Edificio D | 100% | €479.93 | €503.92 | €26,467 | €2,257 |
| W34/2025 | Edificio B | 100% | €237.32 | €249.19 | €13,763 | €2,185 |
| W32/2023 | Edificio E | 100% | €72.28 | €90.34 | €8,158 | €2,141 |
| W42/2025 | Edificio B | 100% | €201.41 | €211.49 | €19,409 | €1,951 |
| W52/2025 | Edificio B | 100% | €125.78 | €157.23 | €9,876 | €1,916 |
| W36/2025 | Edificio A | 100% | €89.12 | €93.58 | €1,191 | €1,803 |

> **Metodología ADR óptimo:** ajuste basado en señal de ocupación y lead time.
> Occ>90% + LT>30d → +25% | Occ 80-90% + LT>21d → +15% | Occ>70% → +5% | Cierre tardío → -5%.
> No es un modelo de ML sino un pricing heurístico basado en las señales observadas.

---

## 3. Elasticidad Precio-Demanda

Segmentos analizados: 20 (building × temporada × día semana)

| Temporada | Día semana | Elasticidad media | Interpretación |
|-----------|-----------|-----------------|---------------|
| Temporada alta | Fin de semana | 2.908 | Correlación positiva (posible efecto temporal/pandemia) |
| Temporada alta | Semana | 0.765 | Correlación positiva (posible efecto temporal/pandemia) |
| Temporada baja | Fin de semana | 5.042 | Correlación positiva (posible efecto temporal/pandemia) |
| Temporada baja | Semana | 0.142 | Correlación positiva (posible efecto temporal/pandemia) |

> **Nota:** Las elasticidades se estiman con datos año-a-año (pocos puntos por segmento).
> Los coeficientes con R² bajo son indicativos, no concluyentes.
> Para un modelo de elasticidad robusto se requeriría variación de precio controlada (A/B test).

---

## 4. Revenue Perdido Estimado 2019-2025

| Componente | Descripción | Conservador (€) | Optimista (€) |
|------------|-------------|----------------|--------------|
| A. Pricing bajo en alta demanda | Semanas de saturación rápida: +15-25% ADR | €171,879 | €425,060 |
| B. Orphan gaps | Noches sin vender entre reservas (2025 extrapolado) | €83,529 | €250,587 |
| C. Cancelaciones sin tarifa NR | Reservas >45d sin política no-reembolsable | €10,246 | €25,614 |
| D. Last-minute sin precio alto | Same-day en temporada alta bajo precio | €42,802 | €71,337 |
| **TOTAL** | | **€308,456** | **€772,599** |

**Como % del revenue histórico (€4,997,222):** 6.2% – 15.5%

---

## 5. Reglas de Pricing Recomendadas

### Regla 1 — Pricing por velocidad de llenado (lead time)
Revisar precio cada vez que la ocupación de una semana supere estos umbrales:

| Ocupación actual | Lead time restante | Acción |
|-----------------|-------------------|--------|
| < 30% | > 30 días | Precio base (sin cambio) |
| 30–60% | > 30 días | +5% sobre precio base |
| 60–80% | > 21 días | +10% sobre precio base |
| > 80% | > 14 días | +20–25% sobre precio base |
| > 90% | Cualquiera | Precio máximo (+30%) |
| < 40% | < 7 días | -10% (last-minute urgente) |

### Regla 2 — Pricing por evento local
| Evento | Ventana | Multiplicador sobre precio base |
|--------|---------|--------------------------------|
| Aste Nagusia (ago) | -60d a evento | ×1.35 |
| BBK Live (jul) | -45d a evento | ×1.35 |
| Maratón Bilbao (nov) | -30d a evento | ×1.10 |
| Fin de semana estándar | Siempre | ×1.15 vs días semana |

### Regla 3 — Tarifa No Reembolsable
Introducir tarifa NR con descuento del 10% para reservas con >45 días de antelación.
Objetivo: capturar al menos el 40% de la demanda anticipada en NR.
Impacto estimado: reducir tasa de cancelación de 46.9% → ~25% en ese segmento.

### Regla 4 — Minimum Stay para eliminar orphan gaps
Activar restricción de estancia mínima 2 noches cuando:
- Quedan 1 o 2 noches sueltas entre reservas confirmadas
- O cuando la ocupación general > 70% y quedan < 10 días para la fecha

### Regla 5 — Last-minute pricing en temporada alta
Same-day en Jun-Sep: precio mínimo = P75 del mes (no bajar del percentil 75).
Actualmente el ADR same-day (€62.96) está muy por debajo del P75 de temporada alta.

---

## Figuras generadas
| Archivo | Descripción |
|---------|-------------|
| 03_fill_speed_scatter | Lead time vs ocupación (cuadrantes de señal) |
| 03_uplift_adr_heatmap | Uplift ADR potencial por año y edificio |
| 03_uplift_distribucion | Distribución del uplift potencial |
| 03_elasticidad_segmento | Elasticidad por segmento (log-log) |
| 03_revenue_perdido_waterfall | Revenue perdido por componente |
| 03_pricing_guide_mensual | Guía de precio base P75 por mes y edificio |
