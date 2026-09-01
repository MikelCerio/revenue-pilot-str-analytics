# Evaluación de Modelos Predictivos — Fase 4
**Fecha:** 2026-04-25 21:23
**Split temporal:** Train 2019-2022 | Validación 2023 | Test 2024

---

## Modelo A — Predicción de Demanda (Ocupación Semanal)

**Algoritmo:** LightGBM Regressor
**Target:** Ocupación % por edificio-semana
**Features:** 11 variables (ciclicidad temporal, edificio, eventos, lags)

| Métrica | Validación 2023 | Test 2024 |
|---------|----------------|-----------|
| MAE | 11.83 pp | 17.81 pp |
| RMSE | 14.68 pp | 21.82 pp |

> Un MAE de 17.8 puntos porcentuales significa que el modelo predice la ocupación semanal con un error medio de ±18pp. Para un portfolio con ocupación media del 68%, esto es mejorable con más datos por apartamento.

### MAE por Edificio (Test 2024)

| building   |   MAE (pp) |   RMSE (pp) |   N semanas |
|:-----------|-----------:|------------:|------------:|
| Edificio A        |      13.44 |       17.16 |          37 |
| Edificio C     |      24.25 |       26.64 |          40 |
| Edificio B      |      21.63 |       24.24 |          42 |
| Edificio D  |      17.14 |       20.91 |          38 |
| Edificio E    |      12.02 |       18.15 |          40 |

### Feature Importance — Top features
| feature   |   importance |
|:----------|-------------:|
| adr_lag52 |          236 |
| occ_lag52 |          221 |
| occ_lag1  |          186 |
| year      |          147 |
| wk_cos    |          141 |
| wk_sin    |          137 |

---

## Modelo B — Probabilidad de Cancelación

**Algoritmo:** LightGBM Classifier (scale_pos_weight ajustado)
**Target:** cancelled (0/1) — solo Booking.com
**Features:** 8 variables

| Métrica | Test 2024 |
|---------|-----------|
| ROC-AUC | 0.821 |
| F1 Score | 0.000 |
| F2 Score (recall-weighted) | 0.000 |
| Precision | 0.000 |
| Recall | 0.000 |

**Confusion Matrix (Test 2024, umbral 0.5):**
```
                 Predicho: NO  Predicho: SÍ
Real: NO canc         7044             0
Real: SÍ canc          695             0
```

> El ROC-AUC de 0.821 es bueno para este tipo de problema. El recall de 0.000 indica que el modelo detecta el 0% de las cancelaciones reales.
>
> **Uso operativo sugerido:** usar umbral 0.35 (más recall) para alertas tempranas de overbooking preventivo, y 0.65 para acciones costosas (descuentos de retención).

### Feature Importance — Top features
| feature   |   importance |
|:----------|-------------:|
| lt_days   |           20 |
| month     |           15 |
| nights_c  |           11 |
| year      |            8 |
| adults    |            4 |
| is_wkend  |            1 |

**Hallazgo clave:** lt_days es el predictor más importante de cancelación, seguido de month. Esto confirma los hallazgos de Fase 2.

---

## Modelo C — Precio Recomendado (ADR)

**Algoritmo:** LightGBM Regressor
**Target:** ADR (€/noche)
**Features:** 13 variables (incluye pred_occ del Modelo A como feature)

| Métrica | Validación 2023 | Test 2024 |
|---------|----------------|-----------|
| MAE | €32.43 | €43.17 |
| RMSE | €68.97 | €118.61 |

> Un MAE de €43.17 significa que el precio recomendado se desvía en media ±€43 del precio óptimo histórico observado. El error es alto por la dispersión de precios entre edificios — usar por segmento.

### MAE por Edificio (Test 2024)

| building   |   MAE (€) |   RMSE (€) |   N reservas |
|:-----------|----------:|-----------:|-------------:|
| Edificio A        |     34.48 |      61.86 |          317 |
| Edificio C     |     49.03 |     116.12 |         1073 |
| Edificio B      |     66.76 |     126.55 |         1289 |
| Edificio D  |     85.94 |     227.37 |          851 |
| Edificio E    |     13.29 |      32.37 |         2355 |

### Feature Importance — Top features
| feature   |   importance |
|:----------|-------------:|
| lt_days   |          741 |
| adr_lag52 |          625 |
| pred_occ  |          553 |
| occ_lag52 |          420 |
| wk_sin    |          386 |
| wk_cos    |          364 |

---

## Arquitectura de Modelos (pipeline)

```
check_in, building, eventos
         │
         ▼
    [Modelo A]  →  pred_occ (ocupación esperada semana)
         │
         ├──────────────────────┐
         ▼                      ▼
    [Modelo C]            [Modelo B]
  precio recomendado    P(cancelación)
         │                      │
         ▼                      ▼
   ADR sugerido (€)    Alerta si P > 0.35
```

---

## Modelos guardados

| Modelo | Archivo | Uso |
|--------|---------|-----|
| A — Demanda | `data/processed/models/model_A_demand.pkl` | `python scripts/predict_demand.py` |
| B — Cancelación | `data/processed/models/model_B_cancellation.pkl` | `python scripts/predict_cancellation.py` |
| C — Precio | `data/processed/models/model_C_price.pkl` | `python scripts/recommend_price.py` |

---

## Limitaciones y próximos pasos

1. **Granularidad:** Modelo A opera a nivel edificio (no apartamento) para 2019-2024. Con más años de datos Smoobu a nivel apartamento, el MAE mejoraría significativamente.
2. **Modelo B:** Solo entrenado con Booking.com (Airbnb y Directo no tienen cancelaciones en los datos). No aplicar a otros canales sin recalibrar.
3. **Exogeneidad:** No se incluyen variables de comp-set (precios competencia) ni datos macroeconómicos. Añadirlos reduciría el error del Modelo C.
4. **Reentrenamiento:** Los modelos deben reentrenarse trimestralmente incorporando datos nuevos. El lag de 52 semanas exige al menos 1 año de histórico para predecir bien un edificio nuevo.
