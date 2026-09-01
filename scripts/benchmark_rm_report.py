# -*- coding: utf-8 -*-
"""
Benchmark de Mercado + Recomendaciones Revenue Manager Senior
Genera el informe ejecutivo con comparativa vs mercado Bilbao y plan de acción.

Salidas:
    data/powerbi/fact_benchmark.parquet
    outputs/reports/07_rm_executive_report.md
    outputs/figures/07_*.png
"""

import sys, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path

ROOT  = Path(__file__).parent.parent
OUT_F = ROOT / 'outputs' / 'figures'
OUT_R = ROOT / 'outputs' / 'reports'
OUT_PB= ROOT / 'data' / 'powerbi'

# ── Datos de mercado Bilbao (fuentes: AirROI, EUSTAT, PriceLabs, INE) ─────────

# Benchmark mercado Bilbao STR 2025 (Airbnb + apartamentos turísticos)
MARKET = {
    'adr_market':           185.0,   # AirROI Mar 2026, Bilbao (~$198 → €185)
    'occ_market':           47.6,    # AirROI Bilbao STR market
    'revpar_market':        88.0,    # adr * occ_rate calculado
    'adr_spain_avg':        125.0,   # PriceLabs España 2025
    'occ_spain_avg':        60.0,    # PriceLabs España 2025
    'revpar_spain_avg':     77.0,    # PriceLabs España 2025
    'adr_dynamic_pricing':  163.0,   # PriceLabs "High Dynamic" tier España
    'occ_dynamic_pricing':  72.0,
    'revpar_dynamic_pricing':117.0,
    'listings_bilbao':      1257,    # AirROI
    'revenue_per_listing':  28691,   # AirROI anual por apartamento
    # Bizkaia EUSTAT 2025 - ocupación por apartamentos
    'occ_bizkaia_jul':      80.7,
    'occ_bizkaia_aug':      85.3,
    'occ_bizkaia_mar':      46.4,
    'occ_bizkaia_annual':   43.7,    # media anual oficial
    'alos_bizkaia':         2.27,    # estancia media agosto 2025
    # Hoteles Bilbao 2025
    'occ_hotels_bilbao':    62.1,
    'tourists_bilbao_2025': 1396841,
    'nights_bilbao_2025':   2723725,
    'growth_tourists_yoy':  12.0,
}

# ── Portfolio propio (de datos ya procesados) ────────────────────────────────

df = pd.read_parquet(ROOT / 'data' / 'processed' / 'reservas_unified.parquet')
df_active = df[~df['cancelled']]

# KPIs globales
total_revenue = df_active['gross_amount'].sum()
total_nights  = df_active['nights'].sum()
total_res     = len(df_active)
adr_portfolio = df_active['adr'].mean()
lead_time_avg = df_active['lead_time_days'].mean()

# KPIs por segmento: apartamentos premium vs EDIFICIO_E
premium_blds  = ['EDIFICIO_A','EDIFICIO_B','EDIFICIO_C','EDIFICIO_D']
pension_bld   = ['EDIFICIO_E']

df_premium = df_active[df_active['building'].isin(premium_blds)]
df_pension  = df_active[df_active['building'].isin(pension_bld)]

adr_premium = df_premium['adr'].mean()
adr_pension  = df_pension['adr'].mean()

# Ocupación media 2024 (año más representativo)
INVENTARIO = {'EDIFICIO_A':2,'EDIFICIO_B':9,'EDIFICIO_C':9,'EDIFICIO_D':7,'EDIFICIO_E':14}
OPENING    = {'EDIFICIO_A':'2019-05-27','EDIFICIO_B':'2019-08-09','EDIFICIO_C':'2020-08-26',
              'EDIFICIO_E':'2021-07-29','EDIFICIO_D':'2023-03-31'}

df_2024 = df_active[df_active['check_in'].dt.year == 2024].copy()
avail_2024 = sum(INVENTARIO[b] * 365 for b in INVENTARIO)
sold_2024  = df_2024['nights'].sum()
occ_2024   = sold_2024 / avail_2024 * 100

revpar_portfolio = total_revenue / (avail_2024 * (2026 - 2019))  # aproximado multiañal

# ADR por edificio 2024
adr_by_bld = df_2024.groupby('building')['adr'].mean().round(2)

# ── Fig 1 — Comparativa ADR: Portfolio vs Mercado ────────────────────────────

categories = ['Portfolio\n(total)', 'Portfolio\n(premium)', 'Portfolio\n(EDIFICIO_E)',
              'Mercado Bilbao\nSTR', 'España\npromedio', 'España\n(dynamic pricing)']
values      = [adr_portfolio, adr_premium, adr_pension,
               MARKET['adr_market'], MARKET['adr_spain_avg'], MARKET['adr_dynamic_pricing']]
colors      = ['#1f77b4','#2196F3','#64B5F6','#FF5722','#FF9800','#4CAF50']

fig1 = go.Figure(go.Bar(
    x=categories, y=values, marker_color=colors,
    text=[f'€{v:.0f}' for v in values], textposition='outside',
))
fig1.add_hline(y=MARKET['adr_market'], line_dash='dash', line_color='#FF5722',
               annotation_text=f'Benchmark mercado Bilbao: €{MARKET["adr_market"]}')
fig1.update_layout(title='ADR: Portfolio vs Mercado Bilbao STR',
                   yaxis_title='ADR (€/noche)', template='plotly_white',
                   height=500, yaxis_range=[0, 220])
try:
    fig1.write_image(str(OUT_F / '07_adr_vs_mercado.png'))
except Exception:
    pass
fig1.write_html(str(OUT_F / '07_adr_vs_mercado.html'))
print("  07_adr_vs_mercado guardado")

# ── Fig 2 — Ocupación: Portfolio vs Mercado ─────────────────────────────────

cats_occ = ['Portfolio 2024', 'Mercado Bilbao\nSTR (anual)',
            'Bizkaia\njulio', 'Bizkaia\nagosto', 'España\npromedio',
            'Hoteles\nBilbao', 'España dynamic\npricing']
vals_occ  = [occ_2024, MARKET['occ_market'],
             MARKET['occ_bizkaia_jul'], MARKET['occ_bizkaia_aug'],
             MARKET['occ_spain_avg'], MARKET['occ_hotels_bilbao'],
             MARKET['occ_dynamic_pricing']]
cols_occ  = ['#1f77b4','#FF5722','#FF7043','#FF5722','#FF9800','#9C27B0','#4CAF50']

fig2 = go.Figure(go.Bar(
    x=cats_occ, y=vals_occ, marker_color=cols_occ,
    text=[f'{v:.1f}%' for v in vals_occ], textposition='outside',
))
fig2.add_hline(y=occ_2024, line_dash='dash', line_color='#1f77b4',
               annotation_text=f'Portfolio: {occ_2024:.1f}%')
fig2.update_layout(title='Ocupación %: Portfolio vs Mercado Bilbao',
                   yaxis_title='Ocupación (%)', template='plotly_white',
                   height=500, yaxis_range=[0, 100])
try:
    fig2.write_image(str(OUT_F / '07_ocupacion_vs_mercado.png'))
except Exception:
    pass
fig2.write_html(str(OUT_F / '07_ocupacion_vs_mercado.html'))
print("  07_ocupacion_vs_mercado guardado")

# ── Fig 3 — Radar: Portfolio premium vs benchmark ─────────────────────────────

# Normalizar a 100 = benchmark
metrics  = ['ADR', 'Ocupación', 'ALOS', 'Lead time', 'RevPAR']
portfolio_vals = [
    adr_premium / MARKET['adr_market'] * 100,
    occ_2024 / MARKET['occ_market'] * 100,
    df_active['nights'].mean() / MARKET['alos_bizkaia'] * 100,
    min(lead_time_avg / 30 * 100, 150),   # 30 días = ideal
    revpar_portfolio / MARKET['revpar_market'] * 100,
]
benchmark_vals = [100, 100, 100, 100, 100]

fig3 = go.Figure()
fig3.add_trace(go.Scatterpolar(r=portfolio_vals + [portfolio_vals[0]],
    theta=metrics + [metrics[0]], fill='toself', name='Portfolio',
    line_color='#1f77b4', fillcolor='rgba(31,119,180,0.2)'))
fig3.add_trace(go.Scatterpolar(r=benchmark_vals + [benchmark_vals[0]],
    theta=metrics + [metrics[0]], fill='toself', name='Benchmark mercado',
    line_color='#FF5722', line_dash='dash', fillcolor='rgba(255,87,34,0.1)'))
fig3.update_layout(
    title='Posicionamiento Portfolio vs Mercado Bilbao (100 = benchmark)',
    polar=dict(radialaxis=dict(visible=True, range=[0, 160])),
    template='plotly_white', height=500)
try:
    fig3.write_image(str(OUT_F / '07_radar_benchmark.png'))
except Exception:
    pass
fig3.write_html(str(OUT_F / '07_radar_benchmark.html'))
print("  07_radar_benchmark guardado")

# ── Fig 4 — Impacto económico de las recomendaciones ─────────────────────────

acciones = [
    'Tarifa NR\n>45 días',
    'Precio dinámico\naltas demandas',
    'Reducir\norphan gaps',
    'Last-minute\nprecio alto',
    'Subir ADR\npremium 10%',
    'Canal directo\n+10%',
]
impacto_min = [10246,  171879,  83529,  42802,  48000,  25000]
impacto_max = [25614,  425060, 250587,  71337,  95000,  60000]

fig4 = go.Figure()
fig4.add_trace(go.Bar(name='Conservador', x=acciones, y=impacto_min,
                      marker_color='#64B5F6'))
fig4.add_trace(go.Bar(name='Optimista',   x=acciones, y=impacto_max,
                      marker_color='#1f77b4'))
fig4.update_layout(
    title='Impacto Económico Estimado por Acción (€/año)',
    barmode='group', template='plotly_white', height=500,
    yaxis_title='Revenue adicional (€)', yaxis_tickformat='€,.0f')
try:
    fig4.write_image(str(OUT_F / '07_impacto_acciones.png'))
except Exception:
    pass
fig4.write_html(str(OUT_F / '07_impacto_acciones.html'))
print("  07_impacto_acciones guardado")

# ── Fig 5 — ADR por edificio 2024 vs benchmark ───────────────────────────────

bld_order = ['EDIFICIO_A','EDIFICIO_B','EDIFICIO_C','EDIFICIO_D','EDIFICIO_E']
adr_vals  = [adr_by_bld.get(b, 0) for b in bld_order]

fig5 = go.Figure()
fig5.add_trace(go.Bar(x=bld_order, y=adr_vals,
    marker_color=['#1f77b4']*5,
    text=[f'€{v:.0f}' for v in adr_vals], textposition='outside', name='ADR Portfolio'))
fig5.add_hline(y=MARKET['adr_market'], line_dash='dash', line_color='#FF5722',
               annotation_text=f'Benchmark Bilbao STR: €{MARKET["adr_market"]}')
fig5.add_hline(y=MARKET['adr_spain_avg'], line_dash='dot', line_color='#FF9800',
               annotation_text=f'Media España: €{MARKET["adr_spain_avg"]}')
fig5.update_layout(title='ADR por Edificio 2024 vs Benchmarks de Mercado',
                   yaxis_title='ADR (€/noche)', template='plotly_white',
                   height=500, yaxis_range=[0, 220])
try:
    fig5.write_image(str(OUT_F / '07_adr_edificio_vs_mercado.png'))
except Exception:
    pass
fig5.write_html(str(OUT_F / '07_adr_edificio_vs_mercado.html'))
print("  07_adr_edificio_vs_mercado guardado")

# ── Guardar benchmark para Power BI ──────────────────────────────────────────

bench_rows = []
for k, v in MARKET.items():
    bench_rows.append({'metric': k, 'value': v, 'source': 'AirROI/EUSTAT/PriceLabs 2025'})

# Añadir métricas portfolio
portfolio_metrics = {
    'adr_portfolio_total':   round(adr_portfolio, 2),
    'adr_portfolio_premium': round(adr_premium, 2),
    'adr_portfolio_pension': round(adr_pension, 2),
    'occ_portfolio_2024':    round(occ_2024, 1),
    'revpar_portfolio':      round(revpar_portfolio, 2),
    'lead_time_portfolio':   round(lead_time_avg, 1),
    'alos_portfolio':        round(df_active['nights'].mean(), 2),
}
for k, v in portfolio_metrics.items():
    bench_rows.append({'metric': k, 'value': v, 'source': 'Portfolio propio'})

pd.DataFrame(bench_rows).to_parquet(OUT_PB / 'fact_benchmark.parquet', index=False)
print("  fact_benchmark.parquet guardado")

# ── Informe ejecutivo RM Senior ───────────────────────────────────────────────

gap_adr_premium = MARKET['adr_market'] - adr_premium
occ_advantage   = occ_2024 - MARKET['occ_market']
potential_if_dynamic = adr_premium * (1 + 0.10) * (occ_2024/100) * sum(INVENTARIO[b]*365 for b in premium_blds)

report = f"""# Revenue Management Report — Bilbao Tourist Apartments
## Executive Briefing para Dirección
**Fecha:** {pd.Timestamp.now().strftime('%B %Y')}
**Elaborado por:** Análisis de Revenue Management
**Fuentes:** Datos internos 2019-2025 · AirROI · EUSTAT · PriceLabs · INE

---

## 1. POSICIONAMIENTO EN EL MERCADO

### Contexto: El mercado de Bilbao crece con fuerza
En 2025, Bilbao recibió **1.396.841 turistas (+12% YoY)** con 2.723.725 pernoctaciones (+10,5%).
El mercado STR de Bilbao cuenta con **1.257 apartamentos activos** con un ADR medio de **€185/noche**
y una ocupación del 47,6% (fuente: AirROI, marzo 2026).

### ¿Dónde estamos nosotros?

| Métrica | **Portfolio propio** | Mercado Bilbao STR | España media | Ventaja/Brecha |
|---|---|---|---|---|
| ADR (apartamentos premium) | **€{adr_premium:.0f}** | €{MARKET['adr_market']:.0f} | €{MARKET['adr_spain_avg']:.0f} | {'✅ Por encima' if adr_premium > MARKET['adr_spain_avg'] else f'⚠️ Brecha de €{gap_adr_premium:.0f}'} |
| ADR (Edificio E) | **€{adr_pension:.0f}** | €{MARKET['adr_market']:.0f} | €{MARKET['adr_spain_avg']:.0f} | Categoría diferente |
| Ocupación 2024 | **{occ_2024:.1f}%** | {MARKET['occ_market']:.1f}% | {MARKET['occ_spain_avg']:.1f}% | ✅ +{occ_2024-MARKET['occ_market']:.1f}pp vs mercado |
| ALOS | **{df_active['nights'].mean():.1f} noches** | ~2,3 noches (Bizkaia) | 5,4 noches | ⚠️ Estancias cortas |
| Lead time medio | **{lead_time_avg:.0f} días** | 62-73 días (high season) | — | ⚠️ Muy bajo |

### Lectura clave
> El portfolio **supera al mercado en ocupación** (+{occ_advantage:.0f}pp), pero **el lead time de {lead_time_avg:.0f} días** indica que se está vendiendo demasiado tarde y demasiado barato. El mercado con pricing dinámico tiene ADR de €163 con 72% de ocupación — nosotros tenemos más ocupación pero menos precio.

---

## 2. ANÁLISIS DE RENTABILIDAD

### Revenue y beneficio 2024 (edificios con datos completos)

| Edificio | Revenue | Costes | **Beneficio neto** | Margen |
|---|---|---|---|---|
| EDIFICIO_B | €412k | €223k | **€189k** | 46% |
| EDIFICIO_D | €339k | €239k | **€100k** | 29% |
| EDIFICIO_E | €237k | €174k | **€63k** | 26% |

**Nota EDIFICIO_D:** La deuda hipotecaria consume ~€80k/año. Sin ella, el margen real operativo supera el 50%.

### La partida que más duele: comisiones OTA
Booking.com + Airbnb representan el **~15% del revenue bruto**. Para el portfolio completo eso son
aproximadamente **€75.000-€120.000 al año en comisiones**. Cada punto porcentual ganado en
reserva directa libera ~€8.000 adicionales de margen.

---

## 3. DIAGNÓSTICO: LO QUE ESTÁ FALLANDO

### Problema 1 — Pricing estático en picos de demanda
**Evidencia:** 41 semanas-edificio donde se llegó al 80%+ de ocupación con 21+ días de antelación.
**Coste:** €171k–€425k de revenue no capturado.
**Causa raíz:** Precio no sube automáticamente cuando la demanda supera umbrales.

### Problema 2 — Las cancelaciones anticipadas no tienen coste
**Evidencia:** Reservas con >90 días de antelación se cancelan el **46,9%** de las veces.
Con 0% de coste para el cliente, no hay incentivo para mantener la reserva.
**Coste:** €10k–€26k en reservas que se cancelan sin reposición.

### Problema 3 — Orphan gaps: noches irrecuperables
**Evidencia:** 571 huecos de 1 noche entre reservas en 2025. 756 noches perdidas.
**Coste:** ~€84k anuales. No son noches "sin vender" — son noches que **no se pueden vender**.
**Causa raíz:** No hay política de estancia mínima dinámica.

### Problema 4 — Lead time de 9 días: se vende en modo last-minute
**Evidencia:** Lead time medio de {lead_time_avg:.0f} días vs 62-73 días del mercado en temporada alta.
**Consecuencia:** No hay tiempo para ajustar precio. Se vende por urgencia, no por valor.

### Problema 5 — Canal OTA dominante, canal directo residual
**Evidencia:** >85% del revenue pasa por Booking.com o Airbnb.
**Coste:** 15-16% de cada reserva va directo al intermediario.

---

## 4. PLAN DE ACCIÓN — PRIORIZADO POR IMPACTO

### 🔴 ACCIÓN INMEDIATA (implementar antes de 30 días)

**A1 — Activar tarifa No Reembolsable con descuento del 10%**
- Para todas las reservas con >45 días de antelación
- Objetivo: reducir la tasa de cancelación anticipada del 47% al 25%
- Impacto estimado: **€10k–€26k/año** en revenue recuperado
- Herramienta: Panel de Booking.com y Airbnb (configuración en 30 minutos)

**A2 — Regla de precio automático por ocupación**
Configurar en el channel manager (Smoobu/Guesty) las siguientes reglas:

| Si la ocupación de la semana supera... | Con esta antelación... | Subir precio un... |
|---|---|---|
| 50% | >30 días | +5% |
| 70% | >21 días | +10% |
| 80% | >14 días | +20% |
| 90% | Cualquiera | +30% |

- Impacto estimado: **€172k–€425k/año** a escala del portfolio completo

### 🟡 ACCIÓN PRIORITARIA (implementar en 30-60 días)

**A3 — Estancia mínima dinámica para cerrar gaps**
- Regla: cuando queden 1-2 noches sueltas entre reservas, activar estancia mínima de 2 noches
- Puede configurarse en Smoobu/Guesty con reglas de calendario
- Impacto estimado: **€84k/año** en noches recuperadas

**A4 — Multiplicador de precio para eventos locales**
- BBK Live (julio), Aste Nagusia (agosto): precio base ×1.35 desde 60 días antes
- Maratón de Bilbao (noviembre): precio base ×1.10 desde 30 días antes
- Los datos muestran +24-29% de ADR real en esas semanas — se puede capturar más

**A5 — Precio last-minute elevado (no rebajado)**
- Para reservas same-day o <3 días: aplicar el percentil 75 del mes como precio mínimo
- Actualmente se baja el precio en last-minute — el comportamiento correcto es subirlo
  (quien reserva el mismo día no tiene alternativas y acepta pagar más)

### 🟢 ESTRATEGIA MEDIA-LARGO PLAZO (60-180 días)

**A6 — Canal de reserva directa: landing page + Google Hotel Ads**
- Crear una web propia con motor de reservas (HiJiffy, Lodgify, o similar)
- Invertir €500-1.000/mes en Google Hotel Ads
- ROI objetivo: si captura el 10% de reservas actuales de OTA → **+€25k-€60k/año** en margen

**A7 — Programa de clientes repetidores**
- Los datos muestran que el lead time es muy bajo — señal de que no hay base de clientes fieles
- Email post-estancia con descuento 5% para reserva directa en próxima visita
- Coste marginal: cero. Potencial: reducir dependencia OTA sistemáticamente.

**A8 — Reentrenamiento mensual del modelo de precio**
- Los modelos ML ya entrenados recomiendan precio por edificio/semana
- Incorporar el resultado del Modelo C en el proceso semanal de revisión de precios
- El error medio de €43 se reduce con más datos → cada trimestre reentrenar

---

## 5. RESUMEN EJECUTIVO: OPORTUNIDAD TOTAL

| Categoría | Conservador | Optimista |
|---|---|---|
| Pricing dinámico en alta demanda | €172k | €425k |
| Orphan gaps (min-stay) | €84k | €251k |
| Tarifa NR anticancelación | €10k | €26k |
| Last-minute precio alto | €43k | €71k |
| Reserva directa +10% | €25k | €60k |
| ADR premium +10% en temporada alta | €48k | €95k |
| **TOTAL OPORTUNIDAD** | **€382k** | **€928k** |
| Como % del revenue actual (€1M+/año) | **~30%** | **~70%** |

> **Mensaje para dirección:** Con las acciones A1+A2+A3 únicamente (todas configurables en el
> channel manager en menos de 1 semana), el impacto mínimo esperado es **+€266k/año**.
> La inversión requerida es cero — solo cambios de configuración de pricing.

---

## 6. CONTEXTO REGULATORIO (IMPORTANTE)

Bilbao está endureciendo la regulación de apartamentos turísticos en línea con otras ciudades
españolas. Recomendaciones:
- Verificar que todos los apartamentos tienen licencia turística al día (VUT)
- Registrar número de licencia en todas las plataformas (obligatorio desde 2025 en España)
- Monitorizar regulación municipal — posibles restricciones a nuevos permisos

---
*Fuentes: AirROI (mar 2026) · EUSTAT · PriceLabs Spain STR Report 2025 · INE ·
Datos internos 2019-2025 (34.167 reservas analizadas)*
"""

(OUT_R / '07_rm_executive_report.md').write_text(report, encoding='utf-8')
print("  07_rm_executive_report.md guardado")

print(f"""
============================================================
BENCHMARK + INFORME RM COMPLETADO
  ADR portfolio premium    : €{adr_premium:.0f} (mercado Bilbao: €{MARKET['adr_market']:.0f})
  Ocupación 2024           : {occ_2024:.1f}% (mercado: {MARKET['occ_market']:.1f}%)
  Ventaja en ocupación     : +{occ_advantage:.0f}pp vs mercado
  Oportunidad conservadora : €382k/año
  Oportunidad optimista    : €928k/año
  Figuras generadas        : 5
============================================================
""")
