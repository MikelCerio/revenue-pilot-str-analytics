# Reporte de Calidad de Datos — Fase 0

**Fecha de generación:** 2026-04-25 16:21

## Resumen General

| Métrica | Valor |
|---------|-------|
| Total reservas unificadas | 34,167 |
| Reservas activas (no canceladas) | 30,463 |
| Canceladas | 3,704 (10.8%) |
| Rango fechas check-in | 2019-05-27 → 2026-04-12 |
| Edificios identificados | 5 |
| Fuentes integradas | XLS Booking, Statements Booking, Smoobu |

## Registros por Fuente

| Fuente | Registros | % del total |
|--------|-----------|-------------|
| xls_booking | 15,235 | 44.6% |
| statements_booking | 11,368 | 33.3% |
| smoobu | 7,564 | 22.1% |

## Registros por Canal

| Canal | Registros | % del total |
|-------|-----------|-------------|
| Booking.com | 32,507 | 95.1% |
| Airbnb | 774 | 2.3% |
| Direct booking | 742 | 2.2% |
| Website | 122 | 0.4% |
| Blocked channel | 22 | 0.1% |

## Registros por Edificio

| Edificio | Reservas activas | Reservas totales |
|----------|-----------------|-----------------|
| Edificio A | 2,283 | 2,651 |
| Edificio C | 5,271 | 5,791 |
| Edificio B | 7,271 | 8,223 |
| Edificio D | 3,009 | 3,187 |
| Edificio E | 12,629 | 14,315 |

## Completitud por Columna

| Columna | % Completo | Nulos |
|---------|-----------|-------|
| reservation_id | 100.0% | 1 |
| channel | 100.0% | 0 |
| apartment_name | 100.0% | 0 |
| building | 100.0% | 0 |
| check_in | 100.0% | 0 |
| check_out | 100.0% | 0 |
| nights | 100.0% | 0 |
| booking_date | 97.5% | 845 |
| adults | 55.4% | 15,235 |
| gross_amount | 100.0% | 0 |
| commission_pct | 99.9% | 41 |
| net_amount | 100.0% | 0 |
| country | 33.3% | 22,799 |
| lead_time_days | 97.5% | 845 |
| adr | 100.0% | 0 |

## Flags de Calidad

| Flag | Registros afectados |
|------|-------------------|
| sin_apartamento | 0 |
| sin_fecha_reserva | 845 |
| noches_negativas | 0 |
| precio_cero_activa | 19 |
| duplicado_entre_fuentes | 0 |
| sin_pais | 22,799 |

## Log de Deduplicación

- XLS↔Statements solapamiento: 0 reservas comunes (enriquecidas, no duplicadas)
- Smoobu↔Statements solapamiento: 0 reservas (se prioriza Smoobu)

## Decisiones y Supuestos

- **Prioridad de fuentes en dedup:** Smoobu > Statements > XLS
- **Enriquecimiento XLS:** campos `country` y `adults` obtenidos de Statements por `reservation_id`
- **Airbnb histórico:** solo disponible como agregado por apartamento (f_airbnb_earnings.csv). Las reservas individuales Airbnb solo existen desde 2025-01 (vía Smoobu).
- **guest_country:** 0% en todas las fuentes Smoobu. Solo disponible en Booking Statements (2021-2025).
- **Noches negativas/cero:** las reservas CANCELLED con check_in=check_out se marcan con flag `noches_negativas` pero se conservan.
- **Edificio UNKNOWN:** apartamentos cuyo nombre no coincide con el mapa de keywords. Revisar manualmente.

## Archivos de Salida

- `data/processed/reservas_unified.parquet` — dataset unificado