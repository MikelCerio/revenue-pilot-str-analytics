# -*- coding: utf-8 -*-
"""
Fase 1 — KPIs Base
Genera 10 gráficos plotly + 01_kpis_summary.md
Uso: python scripts/kpis_phase1.py
"""

import sys, os, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# ── Rutas ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
FIGURES     = ROOT / 'outputs' / 'figures'
REPORTS     = ROOT / 'outputs' / 'reports'
FIGURES.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

PLOTLY_TEMPLATE = 'plotly_white'
COLOR_PALETTE   = px.colors.qualitative.Set2

# Inventario: apartamentos rentables por edificio
# Fuente: d_apartamentos.csv (excluyendo garajes y almacenes)
INVENTARIO = {
    'EDIFICIO_A':       2,
    'EDIFICIO_B':     9,
    'EDIFICIO_C':    9,
    'EDIFICIO_D': 7,
    'EDIFICIO_E':   14,   # 19 unidades - 5 almacenes/servicios
}
TOTAL_UNITS = sum(INVENTARIO.values())  # 41

# Fechas reales de primera reserva por edificio (detectadas de los datos)
OPENING_DATES = {
    'EDIFICIO_A':       pd.Timestamp('2019-05-27'),
    'EDIFICIO_B':     pd.Timestamp('2019-08-09'),
    'EDIFICIO_C':    pd.Timestamp('2020-08-26'),
    'EDIFICIO_E':   pd.Timestamp('2021-07-29'),
    'EDIFICIO_D': pd.Timestamp('2023-03-31'),
}

CHANNEL_COLORS = {
    'Booking.com':    '#003580',
    'Airbnb':         '#FF5A5F',
    'Direct booking': '#00A699',
    'Website':        '#FC642D',
    'manual':         '#999999',
}

# ── Carga de datos ────────────────────────────────────────────────────────────
print("=" * 60)
print("FASE 1 — KPIs BASE")
print("=" * 60)

df_all = pd.read_parquet(ROOT / 'data' / 'processed' / 'reservas_unified.parquet')
df_all['check_in']  = pd.to_datetime(df_all['check_in'])
df_all['check_out'] = pd.to_datetime(df_all['check_out'])

# Solo reservas activas (no canceladas) para revenue/ocupación
df = df_all[~df_all['cancelled']].copy()
# Excluir "Blocked channel" del análisis de revenue
df = df[df['channel'] != 'Blocked channel'].copy()

# Filtrar datos con año válido (2019-2025, excluir datos futuros > hoy)
df = df[df['check_in'].dt.year.between(2019, 2025)].copy()
df_all_filtered = df_all[df_all['check_in'].dt.year.between(2019, 2025)].copy()

print(f"Reservas activas 2019-2025: {len(df):,}")
print(f"Edificios: {df['building'].unique()}")

# ── Función auxiliar: noches disponibles por período ─────────────────────────
def available_nights(year=None, month=None, building=None):
    """Calcula noches disponibles según inventario y fecha real de apertura."""
    if year and month:
        period_start = pd.Timestamp(year, month, 1)
        period_end   = period_start + pd.offsets.MonthEnd(0)
    elif year:
        period_start = pd.Timestamp(year, 1, 1)
        period_end   = pd.Timestamp(year, 12, 31)
    else:
        period_start = df['check_in'].min()
        period_end   = df['check_in'].max()

    if building and building in INVENTARIO:
        open_date = OPENING_DATES.get(building, period_start)
        effective_start = max(period_start, open_date)
        days = max(0, (period_end - effective_start).days + 1)
        return INVENTARIO[building] * days

    # Portfolio: suma solo las unidades abiertas en ese período
    total = 0
    for bld, units in INVENTARIO.items():
        open_date = OPENING_DATES.get(bld, period_start)
        effective_start = max(period_start, open_date)
        days = max(0, (period_end - effective_start).days + 1)
        total += units * days
    return total


def save_fig(fig, name, width=1200, height=600):
    fig.write_html(str(FIGURES / f'{name}.html'))
    try:
        fig.write_image(str(FIGURES / f'{name}.png'), width=width, height=height, scale=2)
        print(f"  Guardado: {name}.png + .html")
    except Exception as e:
        print(f"  Guardado: {name}.html  (PNG falló: {e})")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 1 — Revenue anual total y por canal
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1/10] Revenue anual por canal...")

yearly_channel = (
    df.groupby(['year', 'channel'])['gross_amount']
    .sum().reset_index()
)
yearly_total = df.groupby('year')['gross_amount'].sum().reset_index()

fig1 = px.bar(
    yearly_channel, x='year', y='gross_amount', color='channel',
    color_discrete_map=CHANNEL_COLORS,
    labels={'gross_amount': 'Revenue bruto (€)', 'year': 'Año', 'channel': 'Canal'},
    title='Revenue Bruto Anual por Canal (2019–2025)',
    template=PLOTLY_TEMPLATE,
    barmode='stack',
    text_auto=False,
)
for _, row in yearly_total.iterrows():
    fig1.add_annotation(
        x=row['year'], y=row['gross_amount'],
        text=f"€{row['gross_amount']/1e6:.2f}M",
        showarrow=False, yshift=12, font=dict(size=11, color='black')
    )
fig1.update_layout(legend=dict(orientation='h', y=-0.15))
save_fig(fig1, '01_revenue_anual_canal')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 2 — ADR y RevPAR mensual (últimos 3 años como referencia)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[2/10] ADR y RevPAR mensual...")

monthly = df.groupby(['year', 'month']).agg(
    revenue=('gross_amount', 'sum'),
    nights_sold=('nights', 'sum'),
).reset_index()
monthly['ADR']    = (monthly['revenue'] / monthly['nights_sold']).round(2)
monthly['period'] = pd.to_datetime(monthly[['year', 'month']].assign(day=1))

# RevPAR: revenue / noches disponibles ese mes
monthly['avail_nights'] = monthly.apply(
    lambda r: available_nights(year=int(r['year']), month=int(r['month'])), axis=1
)
monthly['RevPAR'] = (monthly['revenue'] / monthly['avail_nights']).round(2)

fig2 = make_subplots(specs=[[{"secondary_y": True}]])
fig2.add_trace(go.Scatter(
    x=monthly['period'], y=monthly['ADR'],
    name='ADR', line=dict(color='#003580', width=2)
), secondary_y=False)
fig2.add_trace(go.Scatter(
    x=monthly['period'], y=monthly['RevPAR'],
    name='RevPAR', line=dict(color='#FF5A5F', width=2, dash='dash')
), secondary_y=True)
fig2.update_layout(
    title='ADR y RevPAR mensual (2019–2025)',
    xaxis_title='Mes',
    template=PLOTLY_TEMPLATE,
    legend=dict(orientation='h', y=-0.15),
)
fig2.update_yaxes(title_text='ADR (€)', secondary_y=False)
fig2.update_yaxes(title_text='RevPAR (€)', secondary_y=True)
save_fig(fig2, '01_adr_revpar_mensual')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 3 — Heatmap de ocupación % por mes y año
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3/10] Heatmap ocupación...")

occ_data = []
for year in range(2019, 2026):
    for month in range(1, 13):
        mask = (df['check_in'].dt.year == year) & (df['check_in'].dt.month == month)
        nights_sold = df.loc[mask, 'nights'].sum()
        avail = available_nights(year=year, month=month)
        occ_data.append({'year': year, 'month': month,
                         'occ_pct': round(nights_sold / avail * 100, 1) if avail > 0 else 0})

occ_df = pd.DataFrame(occ_data)
occ_pivot = occ_df.pivot(index='year', columns='month', values='occ_pct')
month_names = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
occ_pivot.columns = month_names

fig3 = px.imshow(
    occ_pivot,
    labels=dict(x='Mes', y='Año', color='Ocupación %'),
    color_continuous_scale='RdYlGn',
    zmin=0, zmax=100,
    title='Ocupación % por Mes y Año (portfolio completo)',
    template=PLOTLY_TEMPLATE,
    text_auto='.0f',
    aspect='auto',
)
fig3.update_layout(coloraxis_colorbar=dict(title='Occ%'))
save_fig(fig3, '01_ocupacion_heatmap')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 4 — ALOS por año y canal
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4/10] ALOS por año y canal...")

alos = df.groupby(['year', 'channel'])['nights'].mean().reset_index()
alos.columns = ['year', 'channel', 'ALOS']
alos['ALOS'] = alos['ALOS'].round(2)

fig4 = px.line(
    alos[alos['channel'].isin(['Booking.com','Airbnb','Direct booking'])],
    x='year', y='ALOS', color='channel',
    color_discrete_map=CHANNEL_COLORS,
    markers=True,
    labels={'ALOS': 'Noches medias (ALOS)', 'year': 'Año', 'channel': 'Canal'},
    title='ALOS (Average Length of Stay) por Año y Canal',
    template=PLOTLY_TEMPLATE,
)
fig4.update_xaxes(tickmode='linear', dtick=1)
fig4.update_layout(legend=dict(orientation='h', y=-0.15))
save_fig(fig4, '01_alos_canal_anual')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 5 — Distribución Booking Window (lead time)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[5/10] Booking window distribution...")

lt_df = df[df['lead_time_days'].between(0, 365)].copy()

BINS = [0, 1, 3, 7, 14, 30, 60, 90, 180, 366]
LABELS = ['Same day','1-3d','4-7d','8-14d','15-30d','31-60d','61-90d','91-180d','180d+']
lt_df['lt_bucket'] = pd.cut(lt_df['lead_time_days'], bins=BINS, labels=LABELS, right=False)
lt_counts = lt_df['lt_bucket'].value_counts().reindex(LABELS).reset_index()
lt_counts.columns = ['bucket', 'count']
lt_counts['pct'] = (lt_counts['count'] / lt_counts['count'].sum() * 100).round(1)

fig5 = px.bar(
    lt_counts, x='bucket', y='count',
    text=lt_counts['pct'].apply(lambda x: f'{x}%'),
    labels={'bucket': 'Antelación reserva', 'count': 'Nº reservas'},
    title='Distribución Booking Window (Lead Time) — 2019-2025',
    template=PLOTLY_TEMPLATE,
    color='count',
    color_continuous_scale='Blues',
)
fig5.update_traces(textposition='outside')
fig5.update_layout(showlegend=False, coloraxis_showscale=False)
save_fig(fig5, '01_booking_window')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 6 — Mix de canales por año (% revenue)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[6/10] Mix canales por año...")

channel_mix = df.groupby(['year', 'channel'])['gross_amount'].sum().reset_index()
year_totals = df.groupby('year')['gross_amount'].sum()
channel_mix['pct'] = channel_mix.apply(
    lambda r: r['gross_amount'] / year_totals[r['year']] * 100, axis=1
).round(1)

fig6 = px.bar(
    channel_mix[channel_mix['channel'].isin(['Booking.com','Airbnb','Direct booking','Website'])],
    x='year', y='pct', color='channel',
    color_discrete_map=CHANNEL_COLORS,
    barmode='stack',
    labels={'pct': '% Revenue', 'year': 'Año', 'channel': 'Canal'},
    title='Mix de Canales por Año (% sobre Revenue Total)',
    template=PLOTLY_TEMPLATE,
    text_auto='.0f',
)
fig6.update_layout(legend=dict(orientation='h', y=-0.15))
save_fig(fig6, '01_mix_canales_anual')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 7 — Cancellation Rate por año y canal
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[7/10] Cancellation rate...")

canc = df_all_filtered[df_all_filtered['channel'] != 'Blocked channel'].copy()
canc_rate = canc.groupby(['year', 'channel']).agg(
    total=('reservation_id', 'count'),
    cancelled=('cancelled', 'sum')
).reset_index()
canc_rate['canc_pct'] = (canc_rate['cancelled'] / canc_rate['total'] * 100).round(1)

fig7 = px.line(
    canc_rate[canc_rate['channel'].isin(['Booking.com','Airbnb','Direct booking'])],
    x='year', y='canc_pct', color='channel',
    color_discrete_map=CHANNEL_COLORS,
    markers=True,
    labels={'canc_pct': 'Tasa cancelación (%)', 'year': 'Año', 'channel': 'Canal'},
    title='Tasa de Cancelación por Año y Canal (%)',
    template=PLOTLY_TEMPLATE,
)
fig7.update_xaxes(tickmode='linear', dtick=1)
fig7.update_layout(legend=dict(orientation='h', y=-0.15))
save_fig(fig7, '01_cancellation_rate')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 8 — ADR por día de semana
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[8/10] ADR por día de semana...")

df['dow'] = df['check_in'].dt.dayofweek
DOW_NAMES = {0:'Lun',1:'Mar',2:'Mié',3:'Jue',4:'Vie',5:'Sáb',6:'Dom'}
df['dow_name'] = df['dow'].map(DOW_NAMES)

dow_adr = df.groupby(['dow','dow_name']).agg(
    ADR=('adr', 'mean'),
    revenue=('gross_amount', 'sum'),
    reservas=('reservation_id', 'count'),
).reset_index().sort_values('dow')
dow_adr['ADR'] = dow_adr['ADR'].round(2)

fig8 = px.bar(
    dow_adr, x='dow_name', y='ADR',
    color='ADR', color_continuous_scale='RdYlGn',
    text=dow_adr['ADR'].apply(lambda x: f'€{x:.0f}'),
    labels={'ADR': 'ADR medio (€)', 'dow_name': 'Día check-in'},
    title='ADR Medio por Día de Semana del Check-in',
    template=PLOTLY_TEMPLATE,
)
fig8.update_traces(textposition='outside')
fig8.update_layout(showlegend=False, coloraxis_showscale=False)
save_fig(fig8, '01_adr_dia_semana')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 9 — Net ADR por canal (descontando comisiones)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[9/10] Net ADR por canal...")

net_adr = df.groupby('channel').agg(
    gross_revenue=('gross_amount', 'sum'),
    net_revenue=('net_amount', 'sum'),
    nights=('nights', 'sum'),
).reset_index()
net_adr['ADR_bruto'] = (net_adr['gross_revenue'] / net_adr['nights']).round(2)
net_adr['ADR_neto']  = (net_adr['net_revenue']   / net_adr['nights']).round(2)
net_adr['comision_pct'] = ((1 - net_adr['ADR_neto'] / net_adr['ADR_bruto']) * 100).round(1)
net_adr = net_adr[net_adr['nights'] > 100]  # excluir canales con muy pocos datos

fig9 = go.Figure()
fig9.add_trace(go.Bar(
    x=net_adr['channel'], y=net_adr['ADR_bruto'],
    name='ADR Bruto', marker_color='#003580', opacity=0.7
))
fig9.add_trace(go.Bar(
    x=net_adr['channel'], y=net_adr['ADR_neto'],
    name='ADR Neto', marker_color='#00A699'
))
fig9.update_layout(
    barmode='overlay',
    title='ADR Bruto vs Neto por Canal (impacto comisión)',
    xaxis_title='Canal',
    yaxis_title='ADR (€)',
    template=PLOTLY_TEMPLATE,
    legend=dict(orientation='h', y=-0.15),
)
for _, row in net_adr.iterrows():
    fig9.add_annotation(
        x=row['channel'], y=row['ADR_bruto'],
        text=f"-{row['comision_pct']}%",
        showarrow=False, yshift=14, font=dict(size=10, color='red')
    )
save_fig(fig9, '01_net_adr_canal')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 10 — Revenue por edificio (evolución anual)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[10/10] Revenue por edificio anual...")

bld_year = df.groupby(['year','building']).agg(
    revenue=('gross_amount','sum'),
    noches=('nights','sum'),
    reservas=('reservation_id','count'),
).reset_index()

fig10 = px.line(
    bld_year, x='year', y='revenue', color='building',
    markers=True,
    labels={'revenue': 'Revenue bruto (€)', 'year': 'Año', 'building': 'Edificio'},
    title='Revenue Bruto por Edificio y Año',
    template=PLOTLY_TEMPLATE,
    color_discrete_sequence=COLOR_PALETTE,
)
fig10.update_xaxes(tickmode='linear', dtick=1)
fig10.update_layout(legend=dict(orientation='h', y=-0.15))
save_fig(fig10, '01_revenue_edificio_anual')


# ═══════════════════════════════════════════════════════════════════════════════
# TABLA RESUMEN KPIs
# ═══════════════════════════════════════════════════════════════════════════════
print("\nCalculando tabla resumen KPIs...")

kpi_rows = []
for year in range(2019, 2026):
    mask = df['year'] == year
    yr = df[mask]
    yr_all = df_all_filtered[df_all_filtered['check_in'].dt.year == year]

    if len(yr) == 0:
        continue

    avail   = available_nights(year=year)
    rev     = yr['gross_amount'].sum()
    nights  = yr['nights'].sum()
    n_res   = len(yr)
    n_all   = len(yr_all[yr_all['channel'] != 'Blocked channel'])
    n_canc  = yr_all[yr_all['channel'] != 'Blocked channel']['cancelled'].sum()

    kpi_rows.append({
        'Año':          year,
        'Revenue (€)':  f"{rev:,.0f}",
        'ADR (€)':      f"{rev/nights:.2f}" if nights > 0 else '-',
        'RevPAR (€)':   f"{rev/avail:.2f}" if avail > 0 else '-',
        'Ocupación %':  f"{nights/avail*100:.1f}%" if avail > 0 else '-',
        'ALOS (noches)':f"{yr['nights'].mean():.2f}",
        'Lead Time (d)':f"{yr['lead_time_days'].mean():.0f}",
        'Canc. Rate %': f"{n_canc/n_all*100:.1f}%" if n_all > 0 else '-',
        'Nº Reservas':  f"{n_res:,}",
    })

kpi_df = pd.DataFrame(kpi_rows)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE MARKDOWN
# ═══════════════════════════════════════════════════════════════════════════════
print("Generando 01_kpis_summary.md...")

# Net ADR por canal para el reporte
net_adr_str = net_adr[['channel','ADR_bruto','ADR_neto','comision_pct']].to_string(index=False)

# Ocupación global
total_avail  = sum(available_nights(year=y) for y in range(2019, 2026))
total_nights = df['nights'].sum()
global_occ   = total_nights / total_avail * 100

# ALOS global
global_alos  = df['nights'].mean()

# Lead time global
global_lt    = df['lead_time_days'].mean()

# Cancellation rate global
n_all_global = len(df_all_filtered[df_all_filtered['channel'] != 'Blocked channel'])
n_canc_global = df_all_filtered[df_all_filtered['channel'] != 'Blocked channel']['cancelled'].sum()
global_canc  = n_canc_global / n_all_global * 100

report = f"""# KPIs Base — Fase 1
**Fecha:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
**Período:** 2019-2025 | **Portfolio:** 41 unidades rentables en 5 edificios

---

## KPIs Globales del Portfolio

| KPI | Valor global (2019-2025) |
|-----|--------------------------|
| Revenue bruto total | €{df['gross_amount'].sum():,.0f} |
| Revenue neto total | €{df['net_amount'].sum():,.0f} |
| ADR global | €{df['gross_amount'].sum()/df['nights'].sum():.2f} |
| RevPAR global | €{df['gross_amount'].sum()/total_avail:.2f} |
| Ocupación media | {global_occ:.1f}% |
| ALOS medio | {global_alos:.2f} noches |
| Lead Time medio | {global_lt:.0f} días |
| Tasa cancelación | {global_canc:.1f}% |
| Total reservas (activas) | {len(df):,} |

> **Nota inventario:** RevPAR y Ocupación calculados con {TOTAL_UNITS} unidades rentables:
> EDIFICIO_A(2) + EDIFICIO_B(9) + EDIFICIO_C(9) + EDIFICIO_D(7) + EDIFICIO_E(14).
> Para 2019-2024, los edificios no-EDIFICIO_E solo tienen granularidad por edificio (no apartamento).

---

## Evolución Anual de KPIs

{kpi_df.to_markdown(index=False)}

---

## Net ADR por Canal

| Canal | ADR Bruto (€) | ADR Neto (€) | Comisión media % |
|-------|--------------|-------------|-----------------|
"""
for _, row in net_adr.iterrows():
    report += f"| {row['channel']} | €{row['ADR_bruto']:.2f} | €{row['ADR_neto']:.2f} | {row['comision_pct']:.1f}% |\n"

report += f"""
---

## Distribución Booking Window

| Segmento | Reservas | % |
|----------|----------|---|
"""
for _, row in lt_counts.iterrows():
    report += f"| {row['bucket']} | {row['count']:,} | {row['pct']}% |\n"

report += f"""
---

## ADR por Día de Semana

| Día | ADR medio (€) |
|-----|--------------|
"""
for _, row in dow_adr.iterrows():
    report += f"| {row['dow_name']} | €{row['ADR']:.2f} |\n"

report += f"""
---

## Revenue por Edificio (2019-2025)

| Edificio | Revenue Total (€) | % del portfolio |
|----------|------------------|----------------|
"""
bld_totals = df.groupby('building')['gross_amount'].sum().sort_values(ascending=False)
total_rev = bld_totals.sum()
for bld, rev in bld_totals.items():
    report += f"| {bld} | €{rev:,.0f} | {rev/total_rev*100:.1f}% |\n"

report += """
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
"""

(REPORTS / '01_kpis_summary.md').write_text(report, encoding='utf-8')
print(f"  Reporte guardado: outputs/reports/01_kpis_summary.md")

print("\n" + "=" * 60)
print("FASE 1 COMPLETADA")
print(f"  Figuras: {len(list(FIGURES.glob('01_*.html')))} HTML + PNG en outputs/figures/")
print("=" * 60)
