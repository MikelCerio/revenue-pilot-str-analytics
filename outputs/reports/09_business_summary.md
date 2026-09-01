# Revenue Management Project — Business Summary
## Portfolio de Alojamiento Turístico · Bilbao · 2019-2026

---

## 1. DESCRIPCIÓN DEL NEGOCIO

Portfolio de **~49 unidades de alojamiento** distribuidas en 5 edificios de apartamentos turísticos y 1 EDIFICIO_E en el área metropolitana de Bilbao (Bizkaia). Operación multi-canal a través de Booking.com, Airbnb y canal directo, gestionada mediante Smoobu como PMS (Property Management System).

### Composición del portfolio
| Propiedad | Tipo | Unidades | Zona |
|-----------|------|----------|------|
| Edificio Edificio B | Apartamentos turísticos | 9 | Bilbao centro |
| Edificio EDIFICIO_C | Apartamentos turísticos | 9 | EDIFICIO_C/Ribera |
| Edificio Edificio D | Apartamentos turísticos | 8 | Casco Viejo |
| Edificio A | Apartamentos turísticos | 2 | Bilbao centro |
| EDIFICIO_E | EDIFICIO_E/Hostal | 18 | Centro |
| Garaje | Plazas de parking | 3 | — |

---

## 2. MÉTRICAS CLAVE (Agregado 2019-2025)

| KPI | Valor |
|-----|-------|
| Revenue bruto acumulado | ~€5.0M |
| Revenue neto (post-comisiones) | ~€4.4M |
| ADR global | €100.77/noche |
| RevPAR global | €68.34 |
| Ocupación media | 67.8% |
| ALOS (estancia media) | 1.74 noches |
| Lead time medio | 9 días |
| Tasa de cancelación | 11.4% |
| Reservas activas totales | 28,573 |

### Evolución del Revenue (tendencia creciente)
- **2019:** €132K (apertura, 2 edificios)
- **2020:** €129K (COVID-19, caída -2%)
- **2021:** €357K (recuperación +175%)
- **2022:** €724K (expansión portfolio +103%)
- **2023:** €1.15M (madurez +59%)
- **2024:** €1.23M (consolidación +7%)
- **2025:** €1.28M (optimización +4%)

---

## 3. POSICIONAMIENTO EN EL MERCADO DE BILBAO

| Métrica | Portfolio | Mercado STR Bilbao | Ventaja |
|---------|----------|-------------------|---------|
| Ocupación | 77.8% | 47.6% | ✅ +30pp |
| ADR (aptos) | €126 | €185 | ⚠️ Margen de subida |
| ALOS | 1.7 noches | 2.3 noches | ⚠️ Estancias cortas |
| Lead time | 9 días | 62-73 días | ⚠️ Muy bajo |

**Lectura estratégica:** Alta ocupación con ADR por debajo del mercado = oportunidad de optimización de pricing dinámico valorada en €266K-€928K anuales.

---

## 4. CANALES DE DISTRIBUCIÓN

| Canal | % Revenue | Comisión |
|-------|-----------|----------|
| Booking.com | ~75% | 15.5% |
| Airbnb | ~12% | 15.1% |
| Directo / Web | ~13% | 0% |

**Coste total en comisiones OTA:** ~€75K-€120K/año

---

## 5. DIAGNÓSTICO PRINCIPAL

### Problemas identificados
1. **Pricing estático** en períodos de alta demanda → €172K-€425K de revenue no capturado
2. **571 orphan gaps** (huecos de 1 noche entre reservas) → €84K/año perdidos
3. **Cancelaciones sin tarifa NR** para reservas anticipadas (46.9% cancelación en >90d)
4. **Lead time de 9 días** vs 62-73 del mercado → se vende en modo last-minute
5. **Dependencia OTA >85%** del revenue pasa por intermediarios

### Oportunidad total identificada
| Escenario | Impacto anual |
|-----------|--------------|
| Conservador | +€382K (+30% sobre revenue actual) |
| Optimista | +€928K (+70% sobre revenue actual) |

---

## 6. STACK TECNOLÓGICO DEL PROYECTO

| Componente | Tecnología |
|-----------|------------|
| ETL & Data Pipeline | Python (Pandas, NumPy) |
| Machine Learning | LightGBM, Scikit-learn |
| Visualización | Plotly, Streamlit |
| BI / Reporting | Power BI, Word (python-docx) |
| PMS | Smoobu API |
| Canales OTA | Booking.com, Airbnb |
| NLP | TextBlob, NLTK (análisis de reviews) |
| Datos sintéticos | Generador propio (para portfolio público) |

---

*Proyecto desarrollado por Mikel Cerio · Revenue Management & Data Analytics · Bilbao*
