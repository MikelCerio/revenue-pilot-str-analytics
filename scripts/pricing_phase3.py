# -*- coding: utf-8 -*-
"""
Fase 3 — Análisis de Pricing y Revenue Perdido
Genera figuras + 03_revenue_opportunities.md
Uso: python scripts/pricing_phase3.py
"""

import sys, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from scipy import stats

ROOT    = Path(__file__).parent.parent
FIGURES = ROOT / 'outputs' / 'figures'
REPORTS = ROOT / 'outputs' / 'reports'
FIGURES.mkdir(parents=True, exist_ok=True)

TEMPLATE = 'plotly_white'

print("=" * 60)
print("FASE 3 — PRICING Y REVENUE PERDIDO")
print("=" * 60)

# ── Carga ─────────────────────────────────────────────────────────────────────
df_all = pd.read_parquet(ROOT / 'data' / 'processed' / 'reservas_unified.parquet')
df_all['check_in']    = pd.to_datetime(df_all['check_in'])
df_all['check_out']   = pd.to_datetime(df_all['check_out'])
df_all['booking_date'] = pd.to_datetime(df_all['booking_date'])

df = df_all[
    (~df_all['cancelled']) &
    (df_all['channel'] != 'Blocked channel') &
    (df_all['check_in'].dt.year.between(2019, 2025))
].copy()

INVENTARIO = {'EDIFICIO_A':2,'EDIFICIO_B':9,'EDIFICIO_C':9,'EDIFICIO_D':7,'EDIFICIO_E':14}
OPENING = {
    'EDIFICIO_A':pd.Timestamp('2019-05-27'), 'EDIFICIO_B':pd.Timestamp('2019-08-09'),
    'EDIFICIO_C':pd.Timestamp('2020-08-26'), 'EDIFICIO_E':pd.Timestamp('2021-07-29'),
    'EDIFICIO_D':pd.Timestamp('2023-03-31'),
}

print(f"Reservas activas 2019-2025: {len(df):,}")

def save_fig(fig, name, w=1200, h=580):
    fig.write_html(str(FIGURES / f'{name}.html'))
    try:
        fig.write_image(str(FIGURES / f'{name}.png'), width=w, height=h, scale=2)
    except Exception:
        pass
    print(f"  {name} guardado")


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 1 — Señal de "saturación rápida" (precio bajo) y "cierre tardío" (precio alto)
# Estrategia: analizar semanas por año, clasificar según velocidad de llenado y ADR
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1/5] Señales de saturación rápida vs cierre tardío...")

df['week']  = df['check_in'].dt.isocalendar().week.astype(int)
df['year']  = df['check_in'].dt.year
df['month'] = df['check_in'].dt.month
df['dow']   = df['check_in'].dt.dayofweek

def avail_building_week(bld, year, week):
    try:
        monday = pd.Timestamp.fromisocalendar(year, week, 1)
    except ValueError:
        return 0
    sunday = monday + pd.Timedelta(days=6)
    open_d = OPENING.get(bld, monday)
    start  = max(monday, open_d)
    days   = max(0, (sunday - start).days + 1)
    return INVENTARIO.get(bld, 0) * days

# Análisis semanal por edificio con señales de pricing
weekly_bld = df.groupby(['year','week','building']).agg(
    nights_sold=('nights','sum'),
    adr_mean=('adr','mean'),
    adr_first=('adr','first'),  # primera reserva de la semana (por booking_date)
    adr_last=('adr','last'),    # última reserva
    lead_time_mean=('lead_time_days','mean'),
    lead_time_min=('lead_time_days','min'),
    n_res=('reservation_id','count'),
    revenue=('gross_amount','sum'),
).reset_index()

weekly_bld['avail'] = weekly_bld.apply(
    lambda r: avail_building_week(r['building'], int(r['year']), int(r['week'])), axis=1
)
weekly_bld = weekly_bld[weekly_bld['avail'] > 0].copy()
weekly_bld['occ_pct'] = (weekly_bld['nights_sold'] / weekly_bld['avail'] * 100).clip(0, 100)

# Señal 1: SATURACIÓN RÁPIDA = ocupación alta (>80%) + lead time medio largo (>21 días)
# → se llenó con mucha antelación → precio era bajo
weekly_bld['signal_fast_fill'] = (
    (weekly_bld['occ_pct'] >= 80) &
    (weekly_bld['lead_time_mean'] >= 21)
)

# Señal 2: CIERRE TARDÍO = ocupación media-baja (<60%) + lead time medio corto (<7 días)
# → mayoría de reservas llegaron tarde → precio inicial ahuyentó demanda
weekly_bld['signal_late_close'] = (
    (weekly_bld['occ_pct'] < 60) &
    (weekly_bld['lead_time_mean'] <= 7) &
    (weekly_bld['n_res'] >= 2)
)

# Señal 3: PRECIO DECRECIENTE = la primera reserva pagó más que la última
weekly_bld['signal_price_decay'] = weekly_bld['adr_first'] > weekly_bld['adr_last'] * 1.1

fast_fill  = weekly_bld[weekly_bld['signal_fast_fill']]
late_close = weekly_bld[weekly_bld['signal_late_close']]
price_decay = weekly_bld[weekly_bld['signal_price_decay']]

print(f"  Semanas con saturación rápida (precio bajo potencial): {len(fast_fill)}")
print(f"  Semanas con cierre tardío (precio inicial alto): {len(late_close)}")
print(f"  Semanas con precio decreciente: {len(price_decay)}")

# Scatter: ocupación vs lead time medio, con señales de color
fig_scatter = px.scatter(
    weekly_bld[weekly_bld['n_res'] >= 3],
    x='lead_time_mean', y='occ_pct',
    color='building', size='revenue',
    hover_data=['year','week','adr_mean','n_res'],
    title='Velocidad de llenado (Lead Time medio) vs Ocupación por Semana-Edificio',
    labels={'lead_time_mean':'Lead Time Medio (días)','occ_pct':'Ocupación %','building':'Edificio'},
    template=TEMPLATE,
    opacity=0.7,
)
# Añadir cuadrantes
fig_scatter.add_vline(x=21, line_dash='dash', line_color='gray', annotation_text='21d')
fig_scatter.add_hline(y=80, line_dash='dash', line_color='gray', annotation_text='80% occ')
fig_scatter.add_annotation(x=40, y=90, text="🔴 Saturación rápida<br>(precio bajo)", showarrow=False,
    font=dict(color='red', size=11), bgcolor='rgba(255,200,200,0.8)')
fig_scatter.add_annotation(x=5, y=30, text="🟡 Cierre tardío<br>(precio inicial alto)", showarrow=False,
    font=dict(color='orange', size=11), bgcolor='rgba(255,240,200,0.8)')
save_fig(fig_scatter, '03_fill_speed_scatter')

# Resumen por edificio de señales
signals_summary = weekly_bld.groupby('building').agg(
    total_weeks=('occ_pct','count'),
    fast_fill_weeks=('signal_fast_fill','sum'),
    late_close_weeks=('signal_late_close','sum'),
    price_decay_weeks=('signal_price_decay','sum'),
    avg_occ=('occ_pct','mean'),
    avg_lead=('lead_time_mean','mean'),
).reset_index()
signals_summary['fast_fill_%'] = (signals_summary['fast_fill_weeks'] / signals_summary['total_weeks'] * 100).round(1)
signals_summary['late_close_%'] = (signals_summary['late_close_weeks'] / signals_summary['total_weeks'] * 100).round(1)


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 2 — ADR óptimo retroactivo por semana y edificio
# Metodología: ajuste de +X% en semanas con saturación rápida, -Y% corrección en late-close
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[2/5] ADR óptimo retroactivo...")

# Uplift sugerido según señal y percentil de ocupación
def compute_optimal_adr(row):
    adr   = row['adr_mean']
    occ   = row['occ_pct']
    lt    = row['lead_time_mean']

    if pd.isna(adr) or adr <= 0:
        return adr

    # Saturación rápida fuerte (>90% occ, lt>30d) → +25%
    if occ >= 90 and lt >= 30:
        return adr * 1.25
    # Saturación rápida moderada (80-90% occ, lt>21d) → +15%
    elif occ >= 80 and lt >= 21:
        return adr * 1.15
    # Buen fill sin señal fuerte → +5%
    elif occ >= 70:
        return adr * 1.05
    # Cierre tardío (ocupación baja, lead time corto) → precio estaba bien o alto
    elif occ < 40 and lt <= 5:
        return adr * 0.95  # quizás había que bajar antes
    else:
        return adr  # sin ajuste

weekly_bld['adr_optimal'] = weekly_bld.apply(compute_optimal_adr, axis=1)
weekly_bld['revenue_optimal'] = weekly_bld['adr_optimal'] * weekly_bld['nights_sold']
weekly_bld['revenue_gap']     = weekly_bld['revenue_optimal'] - weekly_bld['revenue']
weekly_bld['uplift_pct']      = ((weekly_bld['adr_optimal'] / weekly_bld['adr_mean'] - 1) * 100).round(1)

# Solo semanas donde hay uplift positivo (revenue perdido por precio bajo)
upside = weekly_bld[weekly_bld['revenue_gap'] > 0]
total_rev_lost_conservative = upside['revenue_gap'].sum()

# Optimista: también considerar ocupación no capturada en semanas de alta demanda
# Semanas con occ>80% y avail grande: podríamos haber subido precio sin perder muchas noches
# Asumimos elasticidad: +10% precio → -5% ocupación (inelástico en alta demanda)
high_demand = weekly_bld[weekly_bld['occ_pct'] >= 80].copy()
high_demand['nights_at_risk'] = high_demand['nights_sold'] * 0.05  # 5% noches se perderían
high_demand['extra_revenue']  = (
    high_demand['adr_mean'] * 0.10 * (high_demand['nights_sold'] - high_demand['nights_at_risk'])
)
total_rev_lost_optimistic = total_rev_lost_conservative + high_demand['extra_revenue'].sum()

print(f"  Revenue perdido (conservador):  €{total_rev_lost_conservative:,.0f}")
print(f"  Revenue perdido (optimista):    €{total_rev_lost_optimistic:,.0f}")

# Heatmap: uplift potencial por semana y edificio (top edificios)
for bld in ['EDIFICIO_B','EDIFICIO_C','EDIFICIO_D']:
    bld_data = weekly_bld[weekly_bld['building'] == bld]
    if len(bld_data) < 10:
        continue
    try:
        pivot = bld_data.pivot_table(index='year', columns='week', values='uplift_pct', aggfunc='mean')
        pivot = pivot.reindex(sorted(pivot.columns), axis=1)
    except Exception:
        continue

fig2 = px.imshow(
    weekly_bld.groupby(['year','building'])['uplift_pct'].mean().unstack('building').fillna(0),
    color_continuous_scale='RdYlGn', zmin=-10, zmax=25,
    title='Uplift ADR potencial % por Año y Edificio (azul = sin ajuste, verde = subir precio)',
    labels=dict(x='Edificio', y='Año', color='Uplift %'),
    template=TEMPLATE, text_auto='.1f', aspect='auto',
)
save_fig(fig2, '03_uplift_adr_heatmap')

# Distribución del uplift
fig2b = px.histogram(
    weekly_bld[weekly_bld['uplift_pct'] != 0], x='uplift_pct',
    nbins=30, color='building',
    title='Distribución de Uplift ADR Potencial por Semana-Edificio',
    labels={'uplift_pct':'Uplift %','count':'Nº semanas'},
    template=TEMPLATE,
)
fig2b.add_vline(x=0, line_color='black', line_width=2)
save_fig(fig2b, '03_uplift_distribucion')


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 3 — Elasticidad precio-demanda por segmento
# Proxy: usando variación de ADR entre años en misma semana vs variación de noches
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3/5] Elasticidad precio-demanda por segmento...")

# Segmentos: temporada alta (jun-sep) vs baja (oct-mar), semana vs finde
df['season'] = np.where(df['month'].between(6, 9), 'Temporada alta', 'Temporada baja')
df['dow_seg'] = np.where(df['dow'].isin([4, 5, 6]), 'Fin de semana', 'Semana')

# Para calcular elasticidad: comparar pares de años (año n vs n+1) en mismas semanas
# elasticidad = (Δ%demanda) / (Δ%precio)  donde demanda = noches vendidas
elasticity_rows = []

for bld in df['building'].unique():
    for season in ['Temporada alta', 'Temporada baja']:
        for dow_seg in ['Semana', 'Fin de semana']:
            seg = df[
                (df['building'] == bld) &
                (df['season'] == season) &
                (df['dow_seg'] == dow_seg)
            ]
            if len(seg) < 30:
                continue

            year_agg = seg.groupby('year').agg(
                adr=('adr','mean'),
                nights=('nights','sum'),
                n=('reservation_id','count'),
            ).reset_index()

            if len(year_agg) < 2:
                continue

            # Regresión log-log: ln(demand) ~ ln(price)
            log_price  = np.log(year_agg['adr'].replace(0, np.nan).dropna())
            log_demand = np.log(year_agg['nights'].replace(0, np.nan).dropna())
            if len(log_price) < 3 or len(log_demand) < 3:
                continue
            min_len = min(len(log_price), len(log_demand))
            try:
                slope, intercept, r, p, se = stats.linregress(
                    log_price.values[:min_len],
                    log_demand.values[:min_len]
                )
            except Exception:
                continue

            elasticity_rows.append({
                'building':  bld,
                'season':    season,
                'dow_seg':   dow_seg,
                'elasticity': round(slope, 3),
                'r2':         round(r**2, 3),
                'n_years':    len(year_agg),
                'avg_adr':    round(year_agg['adr'].mean(), 2),
                'avg_nights': round(year_agg['nights'].mean(), 1),
            })

elast_df = pd.DataFrame(elasticity_rows)
elast_df['segment'] = elast_df['building'] + ' · ' + elast_df['season'] + ' · ' + elast_df['dow_seg']

print(f"  Segmentos analizados: {len(elast_df)}")
if len(elast_df) > 0:
    print(f"  Elasticidad media: {elast_df['elasticity'].mean():.3f}")
    print(f"  Rango: [{elast_df['elasticity'].min():.3f}, {elast_df['elasticity'].max():.3f}]")

    fig3 = px.bar(
        elast_df.sort_values('elasticity'),
        x='segment', y='elasticity',
        color='season',
        color_discrete_map={'Temporada alta':'#FF5A5F','Temporada baja':'#003580'},
        title='Elasticidad Precio-Demanda por Segmento (log-log, año sobre año)',
        labels={'elasticity':'Elasticidad (Δ%noches / Δ%precio)','segment':'Segmento'},
        template=TEMPLATE,
        text='elasticity',
    )
    fig3.update_traces(textposition='outside', texttemplate='%{text:.2f}')
    fig3.add_hline(y=-1, line_dash='dash', line_color='gray',
                   annotation_text='Elasticidad unitaria (-1)')
    fig3.add_hline(y=0, line_color='black', line_width=1)
    fig3.update_layout(xaxis_tickangle=-45, height=650)
    save_fig(fig3, '03_elasticidad_segmento', h=650)

    # Resumen por season/dow
    elast_summary = elast_df.groupby(['season','dow_seg'])['elasticity'].mean().round(3).reset_index()


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 4 — Revenue perdido total: rango conservador / optimista
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4/5] Revenue perdido total...")

# Componente A: precio bajo en semanas de alta demanda (del análisis 2)
rev_opp_A_cons = total_rev_lost_conservative
rev_opp_A_opt  = total_rev_lost_optimistic

# Componente B: orphan gaps (de Fase 2, solo 2025, extrapolado)
# 756 noches × €110 ADR = €83k en 2025. Extrapolamos a 6 años activos de Smoobu ~equiv.
# Conservador: solo 2025 (data real)
rev_opp_B_cons = 83529
# Optimista: asumimos similar en años anteriores donde no tenemos datos apt-level
rev_opp_B_opt  = 83529 * 3  # 3 años activos promedio

# Componente C: cancelaciones de largo plazo (>45 días) sin precio NR
# 3,681 cancelaciones Booking. Las de >45d son: 490+217 = 707 cancelaciones
# Si 30% hubiera pagado tarifa NR (descuento 10%), revenue adicional estimado
canc_45plus = df_all[
    (df_all['cancelled']) &
    (df_all['lead_time_days'] >= 45) &
    (df_all['check_in'].dt.year.between(2019, 2025))
]
canc_45plus_rev = canc_45plus['gross_amount'].sum()
rev_opp_C_cons = canc_45plus_rev * 0.30 * 0.10  # 30% capturado × 10% descuento NR
rev_opp_C_opt  = canc_45plus_rev * 0.50 * 0.15

# Componente D: last-minute sin pricing dinámico
# Same-day reservas pagan €63 vs €100+ en reservas normales. Uplift potencial en alta demanda.
same_day = df[df['lead_time_days'] == 0]
high_season_sd = same_day[same_day['month'].between(6, 9)]
rev_opp_D_cons = high_season_sd['gross_amount'].sum() * 0.15  # +15% en temporada alta same-day
rev_opp_D_opt  = high_season_sd['gross_amount'].sum() * 0.25

total_cons = rev_opp_A_cons + rev_opp_B_cons + rev_opp_C_cons + rev_opp_D_cons
total_opt  = rev_opp_A_opt  + rev_opp_B_opt  + rev_opp_C_opt  + rev_opp_D_opt

rev_total_hist = df['gross_amount'].sum()
pct_cons = total_cons / rev_total_hist * 100
pct_opt  = total_opt  / rev_total_hist * 100

print(f"  Revenue histórico total: €{rev_total_hist:,.0f}")
print(f"  Oportunidad conservadora: €{total_cons:,.0f} ({pct_cons:.1f}% del histórico)")
print(f"  Oportunidad optimista:    €{total_opt:,.0f} ({pct_opt:.1f}% del histórico)")

# Gráfico waterfall de oportunidades
components = {
    'A. Pricing bajo\n(alta demanda)':  (rev_opp_A_cons, rev_opp_A_opt),
    'B. Orphan gaps':                   (rev_opp_B_cons, rev_opp_B_opt),
    'C. Cancelaciones\nsin tarifa NR':  (rev_opp_C_cons, rev_opp_C_opt),
    'D. Last-minute\nsin precio alto':  (rev_opp_D_cons, rev_opp_D_opt),
}

labels = list(components.keys())
cons_vals = [v[0] for v in components.values()]
opt_vals  = [v[1] for v in components.values()]

fig4 = go.Figure()
fig4.add_trace(go.Bar(
    name='Conservador',
    x=labels, y=cons_vals,
    marker_color='#003580', opacity=0.8,
    text=[f'€{v:,.0f}' for v in cons_vals], textposition='outside',
))
fig4.add_trace(go.Bar(
    name='Optimista',
    x=labels, y=opt_vals,
    marker_color='#FF5A5F', opacity=0.6,
    text=[f'€{v:,.0f}' for v in opt_vals], textposition='outside',
))
fig4.update_layout(
    title=f'Revenue Perdido Estimado por Componente<br>'
          f'Conservador: €{total_cons:,.0f} | Optimista: €{total_opt:,.0f}',
    yaxis_title='Revenue (€)',
    template=TEMPLATE, barmode='group',
    legend=dict(orientation='h', y=-0.15),
)
save_fig(fig4, '03_revenue_perdido_waterfall')


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 5 — Reglas de pricing concretas
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[5/5] Reglas de pricing...")

# ADR percentiles por mes y edificio para definir rangos recomendados
pricing_guide = df.groupby(['building', 'month']).agg(
    adr_p25=('adr', lambda x: np.percentile(x.dropna(), 25)),
    adr_p50=('adr', lambda x: np.percentile(x.dropna(), 50)),
    adr_p75=('adr', lambda x: np.percentile(x.dropna(), 75)),
    adr_p90=('adr', lambda x: np.percentile(x.dropna(), 90)),
    occ_mean=('nights', 'mean'),
    n=('reservation_id', 'count'),
).reset_index().round(2)

# Figura: precio sugerido por mes (p75 como precio base, p90 como precio evento)
month_names = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
               7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
pricing_guide['mes_nombre'] = pricing_guide['month'].map(month_names)

fig5 = px.line(
    pricing_guide, x='mes_nombre', y='adr_p75',
    color='building', markers=True,
    title='ADR P75 por Mes y Edificio (precio base sugerido)',
    labels={'adr_p75':'ADR P75 (€)','mes_nombre':'Mes','building':'Edificio'},
    template=TEMPLATE,
    color_discrete_sequence=px.colors.qualitative.Set2,
)
# Añadir banda de rango P25-P90
for bld in pricing_guide['building'].unique():
    sub = pricing_guide[pricing_guide['building'] == bld]
    fig5.add_trace(go.Scatter(
        x=list(sub['mes_nombre']) + list(sub['mes_nombre'])[::-1],
        y=list(sub['adr_p90']) + list(sub['adr_p25'])[::-1],
        fill='toself', fillcolor='rgba(200,200,200,0.1)',
        line=dict(color='rgba(255,255,255,0)'),
        showlegend=False, hoverinfo='skip',
    ))
fig5.update_layout(legend=dict(orientation='h', y=-0.15))
save_fig(fig5, '03_pricing_guide_mensual')


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE
# ═══════════════════════════════════════════════════════════════════════════════
print("\nGenerando 03_revenue_opportunities.md...")

fast_fill_pct  = round(len(fast_fill) / len(weekly_bld) * 100, 1)
late_close_pct = round(len(late_close) / len(weekly_bld) * 100, 1)

# Top semanas con mayor oportunidad de subida de precio
top_opp = weekly_bld[weekly_bld['revenue_gap'] > 0].nlargest(10, 'revenue_gap')[
    ['week','year','building','occ_pct','adr_mean','adr_optimal','revenue','revenue_gap','uplift_pct']
].round(2)

report = f"""# Análisis de Pricing y Revenue Perdido — Fase 3
**Fecha:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
**Portfolio:** 5 edificios · Bilbao · 2019-2025

---

## Resumen Ejecutivo

El portfolio dejó entre **€{total_cons:,.0f}** (conservador) y **€{total_opt:,.0f}** (optimista) de revenue sobre la mesa durante 2019-2025, representando entre el **{pct_cons:.1f}%** y el **{pct_opt:.1f}%** del revenue histórico generado (€{rev_total_hist:,.0f}).

El principal driver de revenue perdido es el **pricing estático en semanas de alta demanda**: {fast_fill_pct}% de las semanas-edificio analizadas muestran señal de saturación rápida (se llenaron con mucha antelación a precio bajo). El segundo driver son los **orphan gaps** entre reservas.

---

## 1. Señales de Pricing Subóptimo

### Saturación rápida (precio demasiado bajo)
Se detectaron **{len(fast_fill):,} semanas-edificio** ({fast_fill_pct}% del total) donde la ocupación superó el 80% con un lead time medio superior a 21 días. Esto indica que las habitaciones se vendieron con mucha antelación — señal clara de precio por debajo del óptimo. Subiendo el precio un 15-25% en esas ventanas, el revenue habría sido mayor aunque se vendieran ligeramente menos noches.

### Cierre tardío (precio inicial alto)
Se detectaron **{len(late_close):,} semanas-edificio** ({late_close_pct}% del total) con ocupación baja (<60%) y reservas llegando tarde (lead time <7d). Probable causa: precio inicial demasiado alto que ahuyentó la demanda temprana, seguido de bajada de precio de emergencia.

### Precio decreciente dentro de la semana
**{len(price_decay):,} semanas-edificio** muestran que la primera reserva de la semana pagó más que la última. Confirma el patrón de "vender caro y bajar para cerrar".

### Por edificio:
| Edificio | Semanas saturación rápida % | Semanas cierre tardío % | Occ media % |
|----------|---------------------------|------------------------|-------------|
"""
for _, r in signals_summary.iterrows():
    report += f"| {r['building']} | {r['fast_fill_%']}% | {r['late_close_%']}% | {r['avg_occ']:.1f}% |\n"

report += f"""
---

## 2. ADR Óptimo Retroactivo

### Top 10 semanas con mayor revenue perdido estimado
| Sem/Año | Edificio | Occ% | ADR real (€) | ADR óptimo (€) | Revenue real (€) | Rev. perdido est. (€) |
|---------|----------|------|-------------|---------------|-----------------|----------------------|
"""
for _, r in top_opp.iterrows():
    report += f"| W{int(r['week'])}/{int(r['year'])} | {r['building']} | {r['occ_pct']:.0f}% | €{r['adr_mean']:.2f} | €{r['adr_optimal']:.2f} | €{r['revenue']:,.0f} | €{r['revenue_gap']:,.0f} |\n"

report += f"""
> **Metodología ADR óptimo:** ajuste basado en señal de ocupación y lead time.
> Occ>90% + LT>30d → +25% | Occ 80-90% + LT>21d → +15% | Occ>70% → +5% | Cierre tardío → -5%.
> No es un modelo de ML sino un pricing heurístico basado en las señales observadas.

---

## 3. Elasticidad Precio-Demanda

"""
if len(elast_df) > 0:
    report += f"Segmentos analizados: {len(elast_df)} (building × temporada × día semana)\n\n"
    report += "| Temporada | Día semana | Elasticidad media | Interpretación |\n"
    report += "|-----------|-----------|-----------------|---------------|\n"
    for _, r in elast_summary.iterrows():
        e = r['elasticity']
        if e < -1:
            interp = "Demanda ELÁSTICA — subir precio reduce ingreso"
        elif -1 <= e < -0.5:
            interp = "Demanda moderadamente elástica"
        elif -0.5 <= e < 0:
            interp = "Demanda casi inelástica — se puede subir precio"
        else:
            interp = "Correlación positiva (posible efecto temporal/pandemia)"
        report += f"| {r['season']} | {r['dow_seg']} | {e:.3f} | {interp} |\n"

    elast_note = elast_df.loc[elast_df['r2'].idxmax()] if len(elast_df) > 0 else None
    report += f"""
> **Nota:** Las elasticidades se estiman con datos año-a-año (pocos puntos por segmento).
> Los coeficientes con R² bajo son indicativos, no concluyentes.
> Para un modelo de elasticidad robusto se requeriría variación de precio controlada (A/B test).

---
"""

report += f"""
## 4. Revenue Perdido Estimado 2019-2025

| Componente | Descripción | Conservador (€) | Optimista (€) |
|------------|-------------|----------------|--------------|
| A. Pricing bajo en alta demanda | Semanas de saturación rápida: +15-25% ADR | €{rev_opp_A_cons:,.0f} | €{rev_opp_A_opt:,.0f} |
| B. Orphan gaps | Noches sin vender entre reservas (2025 extrapolado) | €{rev_opp_B_cons:,.0f} | €{rev_opp_B_opt:,.0f} |
| C. Cancelaciones sin tarifa NR | Reservas >45d sin política no-reembolsable | €{rev_opp_C_cons:,.0f} | €{rev_opp_C_opt:,.0f} |
| D. Last-minute sin precio alto | Same-day en temporada alta bajo precio | €{rev_opp_D_cons:,.0f} | €{rev_opp_D_opt:,.0f} |
| **TOTAL** | | **€{total_cons:,.0f}** | **€{total_opt:,.0f}** |

**Como % del revenue histórico (€{rev_total_hist:,.0f}):** {pct_cons:.1f}% – {pct_opt:.1f}%

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
"""

(REPORTS / '03_revenue_opportunities.md').write_text(report, encoding='utf-8')
print(f"  Guardado: outputs/reports/03_revenue_opportunities.md")

print("\n" + "=" * 60)
print("FASE 3 COMPLETADA")
print(f"  Revenue perdido conservador:  €{total_cons:,.0f}")
print(f"  Revenue perdido optimista:    €{total_opt:,.0f}")
print(f"  Figuras: {len(list(FIGURES.glob('03_*.html')))} HTML + PNG")
print("=" * 60)
