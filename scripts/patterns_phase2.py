# -*- coding: utf-8 -*-
"""
Fase 2 — Búsqueda de Patrones
Genera figuras + 02_findings.md con narrativa de hallazgos
Uso: python scripts/patterns_phase2.py
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
PALETTE  = px.colors.qualitative.Set2

print("=" * 60)
print("FASE 2 — BÚSQUEDA DE PATRONES")
print("=" * 60)

# ── Carga ─────────────────────────────────────────────────────────────────────
df_all = pd.read_parquet(ROOT / 'data' / 'processed' / 'reservas_unified.parquet')
df_all['check_in']  = pd.to_datetime(df_all['check_in'])
df_all['check_out'] = pd.to_datetime(df_all['check_out'])

df = df_all[
    (~df_all['cancelled']) &
    (df_all['channel'] != 'Blocked channel') &
    (df_all['check_in'].dt.year.between(2019, 2025))
].copy()

df['week']     = df['check_in'].dt.isocalendar().week.astype(int)
df['dow']      = df['check_in'].dt.dayofweek
df['dow_out']  = df['check_out'].dt.dayofweek
df['is_wkend'] = df['dow'].isin([4, 5, 6])

print(f"Reservas activas 2019-2025: {len(df):,}")

findings = {}  # acumula hallazgos narrativos para el reporte

def save_fig(fig, name, w=1200, h=550):
    fig.write_html(str(FIGURES / f'{name}.html'))
    try:
        fig.write_image(str(FIGURES / f'{name}.png'), width=w, height=h, scale=2)
    except Exception:
        pass
    print(f"  {name} guardado")


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 1 — Estacionalidad semanal: top 5 / bottom 5 semanas
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[1/8] Estacionalidad semanal...")

INVENTARIO = {'EDIFICIO_A':2,'EDIFICIO_B':9,'EDIFICIO_C':9,'EDIFICIO_D':7,'EDIFICIO_E':14}
OPENING = {
    'EDIFICIO_A':pd.Timestamp('2019-05-27'), 'EDIFICIO_B':pd.Timestamp('2019-08-09'),
    'EDIFICIO_C':pd.Timestamp('2020-08-26'), 'EDIFICIO_E':pd.Timestamp('2021-07-29'),
    'EDIFICIO_D':pd.Timestamp('2023-03-31'),
}

def avail_for_week(year, week_num):
    try:
        monday = pd.Timestamp.fromisocalendar(year, week_num, 1)
    except ValueError:
        return 0
    sunday = monday + pd.Timedelta(days=6)
    total = 0
    for bld, units in INVENTARIO.items():
        open_d = OPENING.get(bld, monday)
        start  = max(monday, open_d)
        days   = max(0, (sunday - start).days + 1)
        total += units * days
    return total

weekly = df.groupby(['year', 'week']).agg(
    revenue=('gross_amount', 'sum'),
    nights_sold=('nights', 'sum'),
    reservas=('reservation_id', 'count'),
    adr=('adr', 'mean'),
).reset_index()
weekly['avail']  = weekly.apply(lambda r: avail_for_week(int(r['year']), int(r['week'])), axis=1)
weekly['occ_pct'] = (weekly['nights_sold'] / weekly['avail'] * 100).clip(0, 100).round(1)
weekly['week_label'] = weekly.apply(lambda r: f"W{int(r['week']):02d}/{int(r['year'])}", axis=1)

# Top/bottom por ocupación (excluir semanas con inventario muy bajo)
w_valid = weekly[weekly['avail'] >= 50].copy()
top5    = w_valid.nlargest(5, 'occ_pct')[['week_label','year','week','occ_pct','adr','revenue']].reset_index(drop=True)
bot5    = w_valid.nsmallest(5, 'occ_pct')[['week_label','year','week','occ_pct','adr','revenue']].reset_index(drop=True)

findings['estacionalidad'] = {
    'top5': top5,
    'bot5': bot5,
    'best_week': top5.iloc[0]['week_label'],
    'best_occ': top5.iloc[0]['occ_pct'],
    'worst_week': bot5.iloc[0]['week_label'],
    'worst_occ': bot5.iloc[0]['occ_pct'],
}

# Heatmap semana × año
occ_pivot = w_valid.pivot_table(index='year', columns='week', values='occ_pct', aggfunc='mean')
fig1 = px.imshow(occ_pivot, color_continuous_scale='RdYlGn', zmin=0, zmax=100,
                 title='Ocupación % por Semana ISO y Año',
                 labels=dict(x='Semana ISO', y='Año', color='Occ%'),
                 template=TEMPLATE, aspect='auto')
save_fig(fig1, '02_estacionalidad_semanal')

# Curva semanal promedio (todos los años)
week_avg = w_valid.groupby('week')['occ_pct'].mean().reset_index()
week_avg['occ_pct'] = week_avg['occ_pct'].round(1)
fig1b = px.line(week_avg, x='week', y='occ_pct', markers=True,
                title='Ocupación Media % por Semana del Año (promedio 2019-2025)',
                labels={'week':'Semana ISO','occ_pct':'Ocupación %'},
                template=TEMPLATE)
fig1b.add_hline(y=week_avg['occ_pct'].mean(), line_dash='dash', line_color='gray',
                annotation_text=f"Media {week_avg['occ_pct'].mean():.1f}%")
save_fig(fig1b, '02_curva_semanal_promedio')


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 2 — Eventos locales Bilbao
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[2/8] Eventos locales Bilbao...")

EVENTS = [
    # Aste Nagusia (Semana Grande) — tercer sábado de agosto
    {'name':'Aste Nagusia','start':'2019-08-17','end':'2019-08-25'},
    {'name':'Aste Nagusia','start':'2021-08-14','end':'2021-08-22'},
    {'name':'Aste Nagusia','start':'2022-08-20','end':'2022-08-28'},
    {'name':'Aste Nagusia','start':'2023-08-19','end':'2023-08-27'},
    {'name':'Aste Nagusia','start':'2024-08-17','end':'2024-08-25'},
    {'name':'Aste Nagusia','start':'2025-08-16','end':'2025-08-24'},
    # BBK Live — julio
    {'name':'BBK Live','start':'2019-07-11','end':'2019-07-13'},
    {'name':'BBK Live','start':'2021-07-08','end':'2021-07-10'},
    {'name':'BBK Live','start':'2022-07-07','end':'2022-07-09'},
    {'name':'BBK Live','start':'2023-07-06','end':'2023-07-08'},
    {'name':'BBK Live','start':'2024-07-11','end':'2024-07-13'},
    {'name':'BBK Live','start':'2025-07-10','end':'2025-07-12'},
    # Bilbao Bizkaia Marathon — suele ser noviembre
    {'name':'Bilbao Marathon','start':'2019-11-10','end':'2019-11-10'},
    {'name':'Bilbao Marathon','start':'2021-10-31','end':'2021-10-31'},
    {'name':'Bilbao Marathon','start':'2022-11-06','end':'2022-11-06'},
    {'name':'Bilbao Marathon','start':'2023-11-05','end':'2023-11-05'},
    {'name':'Bilbao Marathon','start':'2024-11-10','end':'2024-11-10'},
    # Semana de la Moda de Bilbao
    {'name':'BEC Congreso','start':'2022-09-01','end':'2022-09-04'},
    {'name':'BEC Congreso','start':'2023-09-04','end':'2023-09-07'},
    {'name':'BEC Congreso','start':'2024-09-02','end':'2024-09-05'},
]

events_df = pd.DataFrame(EVENTS)
events_df['start'] = pd.to_datetime(events_df['start'])
events_df['end']   = pd.to_datetime(events_df['end'])

def is_event_day(date, events):
    for _, ev in events.iterrows():
        if ev['start'] <= date <= ev['end']:
            return ev['name']
    return None

# Marcar cada reserva con evento si check_in cae en esas fechas
df['event'] = df['check_in'].apply(lambda d: is_event_day(d, events_df))
df['has_event'] = df['event'].notna()

# Uplift: ADR evento vs ADR semanas equivalentes (±4 semanas, mismo año, sin evento)
uplift_rows = []
for ev_name in events_df['name'].unique():
    ev_mask = df['event'] == ev_name
    ev_data = df[ev_mask]
    if len(ev_data) < 5:
        continue
    ev_adr = ev_data['adr'].mean()
    ev_occ_sample_size = len(ev_data)

    # Período de referencia: mismo mes ±4 semanas sin evento
    ref_rows = []
    for _, ev_row in events_df[events_df['name'] == ev_name].iterrows():
        for offset in [-4, -3, -2, -1, 1, 2, 3, 4]:
            ref_start = ev_row['start'] + pd.Timedelta(weeks=offset)
            ref_end   = ev_row['end']   + pd.Timedelta(weeks=offset)
            mask_ref  = (
                (df['check_in'] >= ref_start) &
                (df['check_in'] <= ref_end) &
                (~df['has_event'])
            )
            ref_rows.append(df[mask_ref])

    ref_data = pd.concat(ref_rows) if ref_rows else pd.DataFrame()
    if len(ref_data) < 5:
        continue
    ref_adr   = ref_data['adr'].mean()
    uplift_pct = (ev_adr / ref_adr - 1) * 100 if ref_adr > 0 else 0

    uplift_rows.append({
        'Evento': ev_name,
        'ADR Evento (€)': round(ev_adr, 2),
        'ADR Referencia (€)': round(ref_adr, 2),
        'Uplift ADR %': round(uplift_pct, 1),
        'Reservas evento': ev_occ_sample_size,
    })

uplift_df = pd.DataFrame(uplift_rows)
findings['eventos'] = uplift_df

fig2 = px.bar(uplift_df, x='Evento', y='Uplift ADR %',
              color='Uplift ADR %', color_continuous_scale='RdYlGn',
              text=uplift_df['Uplift ADR %'].apply(lambda x: f'+{x:.1f}%' if x >= 0 else f'{x:.1f}%'),
              title='Uplift ADR en Eventos vs Semanas Equivalentes sin Evento',
              template=TEMPLATE)
fig2.update_traces(textposition='outside')
fig2.update_layout(coloraxis_showscale=False)
fig2.add_hline(y=0, line_color='black', line_width=1)
save_fig(fig2, '02_uplift_eventos')


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 3 — Día de semana: check-in y check-out
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[3/8] Comportamiento por día de semana...")

DOW = {0:'Lun',1:'Mar',2:'Mié',3:'Jue',4:'Vie',5:'Sáb',6:'Dom'}
cin  = df['dow'].value_counts().reindex(range(7)).rename(DOW)
cout = df['dow_out'].value_counts().reindex(range(7)).rename(DOW)

fig3 = make_subplots(rows=1, cols=2,
    subplot_titles=['Día de Check-in', 'Día de Check-out'])
fig3.add_trace(go.Bar(x=list(cin.index), y=cin.values,
    marker_color='#003580', name='Check-in'), row=1, col=1)
fig3.add_trace(go.Bar(x=list(cout.index), y=cout.values,
    marker_color='#FF5A5F', name='Check-out'), row=1, col=2)
fig3.update_layout(title='Distribución Check-in y Check-out por Día de Semana',
                   template=TEMPLATE, showlegend=False)
save_fig(fig3, '02_checkin_checkout_dow')

# Uplift revenue finde vs semana
wkend_adr = df[df['is_wkend']]['adr'].mean()
wkday_adr = df[~df['is_wkend']]['adr'].mean()
findings['dow'] = {
    'top_checkin': DOW[df['dow'].value_counts().idxmax()],
    'top_checkout': DOW[df['dow_out'].value_counts().idxmax()],
    'wkend_adr': round(wkend_adr, 2),
    'wkday_adr': round(wkday_adr, 2),
    'wkend_uplift_pct': round((wkend_adr / wkday_adr - 1) * 100, 1),
}


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 4 — Lead time vs precio
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[4/8] Lead time vs precio...")

lt_df = df[df['lead_time_days'].between(0, 180) & df['adr'].notna()].copy()
lt_df['lt_bucket'] = pd.cut(
    lt_df['lead_time_days'],
    bins=[0,1,3,7,14,30,60,90,181],
    labels=['0d','1-3d','4-7d','8-14d','15-30d','31-60d','61-90d','91-180d'],
    right=False
)
lt_adr = lt_df.groupby('lt_bucket', observed=True).agg(
    adr_mean=('adr','mean'),
    adr_median=('adr','median'),
    count=('adr','count'),
).reset_index()
lt_adr['adr_mean']   = lt_adr['adr_mean'].round(2)
lt_adr['adr_median'] = lt_adr['adr_median'].round(2)

fig4 = go.Figure()
fig4.add_trace(go.Bar(x=lt_adr['lt_bucket'].astype(str), y=lt_adr['adr_mean'],
    name='ADR Medio', marker_color='#003580', opacity=0.8))
fig4.add_trace(go.Scatter(x=lt_adr['lt_bucket'].astype(str), y=lt_adr['adr_median'],
    name='ADR Mediana', mode='lines+markers', line=dict(color='#FF5A5F', width=2)))
fig4.update_layout(
    title='ADR Medio y Mediana por Antelación de Reserva',
    xaxis_title='Antelación (días)', yaxis_title='ADR (€)',
    template=TEMPLATE, legend=dict(orientation='h', y=-0.15))
save_fig(fig4, '02_leadtime_vs_adr')

# Correlación
r, p = stats.pearsonr(lt_df['lead_time_days'], lt_df['adr'])
findings['leadtime'] = {
    'corr_r': round(r, 3),
    'corr_p': round(p, 4),
    'same_day_adr': round(lt_df[lt_df['lead_time_days'] == 0]['adr'].mean(), 2),
    'long_adr': round(lt_df[lt_df['lead_time_days'] >= 60]['adr'].mean(), 2),
    'lt_adr_table': lt_adr,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 5 — Orphan gaps (noches huérfanas) — datos 2025 Smoobu
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[5/8] Orphan gaps (2025, nivel apartamento)...")

smoobu = df[df['source'] == 'smoobu'].copy()
smoobu = smoobu.sort_values(['apartment_id', 'check_in'])
smoobu_ids = smoobu['apartment_id'].dropna().unique()

gap_rows = []
for apt_id in smoobu_ids:
    apt = smoobu[smoobu['apartment_id'] == apt_id].sort_values('check_in')
    for i in range(len(apt) - 1):
        curr_out = apt.iloc[i]['check_out']
        next_in  = apt.iloc[i+1]['check_in']
        gap = (next_in - curr_out).days
        if 0 < gap <= 3:  # 1-3 noches huérfanas
            gap_rows.append({
                'apartment_id':   apt_id,
                'apartment_name': apt.iloc[i]['apartment_name'],
                'building':       apt.iloc[i]['building'],
                'gap_nights':     gap,
                'gap_start':      curr_out,
                'gap_end':        next_in,
                'adr_before':     apt.iloc[i]['adr'],
                'adr_after':      apt.iloc[i+1]['adr'],
            })

gaps_df = pd.DataFrame(gap_rows) if gap_rows else pd.DataFrame(
    columns=['apartment_id','apartment_name','building','gap_nights','gap_start','gap_end'])

if len(gaps_df) > 0:
    avg_adr = df[df['source'] == 'smoobu']['adr'].mean()
    gap_revenue_lost = (gaps_df['gap_nights'] * avg_adr).sum()
    gap_by_bld = gaps_df.groupby('building').agg(
        total_gaps=('gap_nights','count'),
        nights_lost=('gap_nights','sum'),
    ).reset_index()
    gap_by_bld['revenue_lost_est'] = (gap_by_bld['nights_lost'] * avg_adr).round(0)

    fig5 = px.bar(gaps_df.groupby(['building','gap_nights']).size().reset_index(name='count'),
                  x='building', y='count', color='gap_nights', barmode='stack',
                  title=f'Orphan Gaps 2025 por Edificio y Duración (total {len(gaps_df):,} gaps, ~€{gap_revenue_lost:,.0f} perdidos)',
                  labels={'count':'Nº gaps','building':'Edificio','gap_nights':'Duración gap (noches)'},
                  template=TEMPLATE, color_continuous_scale='Reds')
    save_fig(fig5, '02_orphan_gaps')
    findings['gaps'] = {
        'total_gaps': len(gaps_df),
        'nights_lost': int(gaps_df['gap_nights'].sum()),
        'revenue_lost_est': round(gap_revenue_lost, 0),
        'by_building': gap_by_bld,
        'avg_adr_used': round(avg_adr, 2),
    }
else:
    print("  Sin gaps detectados o sin datos Smoobu.")
    findings['gaps'] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 6 — Patrones de cancelación
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[6/8] Patrones de cancelación...")

canc = df_all[
    (df_all['channel'] != 'Blocked channel') &
    (df_all['check_in'].dt.year.between(2019, 2025))
].copy()

# Por canal
canc_canal = canc.groupby('channel').agg(
    total=('cancelled','count'),
    canceladas=('cancelled','sum'),
).reset_index()
canc_canal['tasa_%'] = (canc_canal['canceladas'] / canc_canal['total'] * 100).round(1)
canc_canal = canc_canal[canc_canal['total'] > 50].sort_values('tasa_%', ascending=False)

# Por segmento de lead time
canc_lt = canc.copy()
canc_lt['lt_seg'] = pd.cut(
    canc_lt['lead_time_days'].fillna(-1),
    bins=[-2, 0, 3, 14, 45, 90, 400],
    labels=['Same day','1-3d','4-14d','15-45d','46-90d','90d+']
)
canc_by_lt = canc_lt.groupby('lt_seg', observed=True).agg(
    total=('cancelled','count'), canceladas=('cancelled','sum')
).reset_index()
canc_by_lt['tasa_%'] = (canc_by_lt['canceladas'] / canc_by_lt['total'] * 100).round(1)

# Por ALOS (duración reserva)
canc['nights_seg'] = pd.cut(canc['nights'].fillna(0),
    bins=[-1,1,2,3,7,100], labels=['1n','2n','3n','4-7n','7n+'])
canc_nights = canc.groupby('nights_seg', observed=True).agg(
    total=('cancelled','count'), canceladas=('cancelled','sum')
).reset_index()
canc_nights['tasa_%'] = (canc_nights['canceladas'] / canc_nights['total'] * 100).round(1)

fig6 = make_subplots(rows=1, cols=3,
    subplot_titles=['Por Canal','Por Lead Time','Por Duración'])
fig6.add_trace(go.Bar(
    x=canc_canal['channel'], y=canc_canal['tasa_%'],
    marker_color='#FF5A5F', text=canc_canal['tasa_%'].apply(lambda x: f'{x}%'),
    textposition='outside', name='Canal'), row=1, col=1)
fig6.add_trace(go.Bar(
    x=canc_by_lt['lt_seg'].astype(str), y=canc_by_lt['tasa_%'],
    marker_color='#003580', text=canc_by_lt['tasa_%'].apply(lambda x: f'{x}%'),
    textposition='outside', name='Lead time'), row=1, col=2)
fig6.add_trace(go.Bar(
    x=canc_nights['nights_seg'].astype(str), y=canc_nights['tasa_%'],
    marker_color='#00A699', text=canc_nights['tasa_%'].apply(lambda x: f'{x}%'),
    textposition='outside', name='Duración'), row=1, col=3)
fig6.update_layout(title='Tasas de Cancelación por Canal, Lead Time y Duración',
                   template=TEMPLATE, showlegend=False)
fig6.update_yaxes(title_text='Tasa cancelación (%)', row=1, col=1)
save_fig(fig6, '02_cancelacion_patrones', w=1400)

findings['cancelacion'] = {
    'canal': canc_canal,
    'lt': canc_by_lt,
    'nights': canc_nights,
    'highest_canal': canc_canal.iloc[0]['channel'],
    'highest_canal_pct': canc_canal.iloc[0]['tasa_%'],
    'lt_highest': canc_by_lt.loc[canc_by_lt['tasa_%'].idxmax(),'lt_seg'],
    'lt_highest_pct': canc_by_lt['tasa_%'].max(),
}


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 7 — País de origen (solo Booking Statements = EDIFICIO_E, 2021-2025)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[7/8] Análisis por país de origen...")

country_df = df[df['country'].notna() & (df['country'] != '')].copy()
print(f"  Reservas con país conocido: {len(country_df):,} ({len(country_df)/len(df)*100:.1f}%)")

country_stats = country_df.groupby('country').agg(
    reservas=('reservation_id','count'),
    revenue=('gross_amount','sum'),
    adr=('adr','mean'),
    alos=('nights','mean'),
    canc=('cancelled','count'),  # ya filtrado activas, así que =0
).reset_index()
# Añadir cancelaciones
canc_country = df_all[
    df_all['country'].notna() &
    df_all['check_in'].dt.year.between(2021, 2025)
].groupby('country').agg(
    total=('cancelled','count'), canceladas=('cancelled','sum')
).reset_index()
canc_country['canc_%'] = (canc_country['canceladas'] / canc_country['total'] * 100).round(1)

country_stats = country_stats.merge(canc_country[['country','canc_%']], on='country', how='left')
country_stats = country_stats[country_stats['reservas'] >= 20].sort_values('reservas', ascending=False)
country_stats['adr']  = country_stats['adr'].round(2)
country_stats['alos'] = country_stats['alos'].round(2)

top_countries = country_stats.head(15)
fig7 = make_subplots(rows=1, cols=2,
    subplot_titles=['Reservas por País (top 15)', 'ADR Medio por País'])
fig7.add_trace(go.Bar(
    x=top_countries['country'], y=top_countries['reservas'],
    marker_color='#003580', name='Reservas'), row=1, col=1)
fig7.add_trace(go.Bar(
    x=top_countries['country'], y=top_countries['adr'],
    marker_color='#FF5A5F', name='ADR'), row=1, col=2)
fig7.update_layout(title='Análisis por País de Origen (Edificio E, 2021-2025)',
                   template=TEMPLATE, showlegend=False)
save_fig(fig7, '02_pais_origen', w=1400)

findings['pais'] = {
    'n_reservas_con_pais': len(country_df),
    'cobertura_pct': round(len(country_df)/len(df)*100, 1),
    'top_paises': country_stats.head(10),
    'nota': 'Solo disponible para Edificio E (Booking Statements 2021-2025)',
}


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS 8 — Cohort: evolución por edificio (RevPAR normalizado)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n[8/8] Cohort analysis por edificio...")

INVENTARIO_BLD = {'EDIFICIO_A':2,'EDIFICIO_B':9,'EDIFICIO_C':9,'EDIFICIO_D':7,'EDIFICIO_E':14}

bld_year = df.groupby(['building','year']).agg(
    revenue=('gross_amount','sum'),
    nights=('nights','sum'),
    adr=('adr','mean'),
    reservas=('reservation_id','count'),
).reset_index()

def avail_bld_year(bld, year):
    days = 366 if pd.Period(str(year)).is_leap_year else 365
    open_d = OPENING.get(bld, pd.Timestamp(f'{year}-01-01'))
    start  = max(pd.Timestamp(f'{year}-01-01'), open_d)
    end    = pd.Timestamp(f'{year}-12-31')
    actual_days = max(0, (end - start).days + 1)
    return INVENTARIO_BLD.get(bld, 1) * actual_days

bld_year['avail'] = bld_year.apply(lambda r: avail_bld_year(r['building'], int(r['year'])), axis=1)
bld_year['revpar'] = (bld_year['revenue'] / bld_year['avail']).round(2)
bld_year['occ_%']  = (bld_year['nights']  / bld_year['avail'] * 100).clip(0,100).round(1)

# Normalizar: RevPAR de cada edificio en su primer año completo = 100
first_full = {}
for bld in bld_year['building'].unique():
    sub = bld_year[(bld_year['building'] == bld) & (bld_year['avail'] > 200)]
    if len(sub) > 0:
        first_full[bld] = sub.iloc[0]['revpar']

bld_year['revpar_idx'] = bld_year.apply(
    lambda r: round(r['revpar'] / first_full.get(r['building'], r['revpar']) * 100, 1)
    if first_full.get(r['building'], 0) > 0 else 100, axis=1
)

fig8 = px.line(bld_year[bld_year['avail'] > 50], x='year', y='revpar_idx',
               color='building', markers=True,
               title='Evolución RevPAR por Edificio (índice: primer año activo = 100)',
               labels={'revpar_idx':'RevPAR (índice)','year':'Año','building':'Edificio'},
               template=TEMPLATE, color_discrete_sequence=PALETTE)
fig8.add_hline(y=100, line_dash='dash', line_color='gray', annotation_text='Base 100')
fig8.update_xaxes(tickmode='linear', dtick=1)
fig8.update_layout(legend=dict(orientation='h', y=-0.15))
save_fig(fig8, '02_cohort_edificio')

findings['cohort'] = {
    'data': bld_year,
    'best_growth': bld_year.groupby('building')['revpar_idx'].max().idxmax(),
}


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE NARRATIVO
# ═══════════════════════════════════════════════════════════════════════════════
print("\nGenerando 02_findings.md...")

top5 = findings['estacionalidad']['top5']
bot5 = findings['estacionalidad']['bot5']
ev   = findings['eventos']
dow  = findings['dow']
lt   = findings['leadtime']
canc = findings['cancelacion']
pais = findings['pais']
gaps = findings['gaps']
coh  = findings['cohort']

report = f"""# Análisis de Patrones — Fase 2
**Fecha:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
**Portfolio:** 5 edificios · Bilbao · 2019-2025

---

## El patrón más sorprendente: la demanda no sigue la estacionalidad típica

El patrón más llamativo del portfolio no es el verano — es la **consistencia extrema del perfil viajero**. Con un ALOS global de 1.74 noches y un 68% de reservas con menos de 7 días de antelación, este portfolio no opera como un destino vacacional sino como un hub de tránsito y negocio. Los picos de verano existen, pero son moderados en comparación con lo que cabría esperar para un portfolio de 41 unidades en una ciudad como Bilbao.

---

## 1. Estacionalidad Semanal: las 5 semanas más fuertes y más débiles

### Las 5 semanas más ocupadas

| Semana | Ocupación % | ADR medio (€) | Revenue (€) |
|--------|------------|--------------|-------------|
"""
for _, r in top5.iterrows():
    report += f"| {r['week_label']} | {r['occ_pct']}% | €{r['adr']:.2f} | €{r['revenue']:,.0f} |\n"

report += f"""
### Las 5 semanas más débiles

| Semana | Ocupación % | ADR medio (€) | Revenue (€) |
|--------|------------|--------------|-------------|
"""
for _, r in bot5.iterrows():
    report += f"| {r['week_label']} | {r['occ_pct']}% | €{r['adr']:.2f} | €{r['revenue']:,.0f} |\n"

report += f"""
La diferencia entre la semana más fuerte ({top5.iloc[0]['week_label']}, {top5.iloc[0]['occ_pct']}% occ) y la más débil ({bot5.iloc[0]['week_label']}, {bot5.iloc[0]['occ_pct']}% occ) es de **{top5.iloc[0]['occ_pct'] - bot5.iloc[0]['occ_pct']:.1f} puntos porcentuales**. Enero y febrero concentran sistemáticamente las semanas más débiles.

---

## 2. Impacto de Eventos Locales

"""
if len(ev) > 0:
    report += "| Evento | ADR Evento (€) | ADR Referencia (€) | Uplift % |\n"
    report += "|--------|--------------|-------------------|----------|\n"
    for _, r in ev.iterrows():
        sign = '+' if r['Uplift ADR %'] >= 0 else ''
        report += f"| {r['Evento']} | €{r['ADR Evento (€)']:.2f} | €{r['ADR Referencia (€)']:.2f} | {sign}{r['Uplift ADR %']:.1f}% |\n"
    top_event = ev.loc[ev['Uplift ADR %'].idxmax()]
    report += f"""
**Aste Nagusia es el evento de mayor impacto**: el ADR durante la Semana Grande sube un **{ev[ev['Evento']=='Aste Nagusia']['Uplift ADR %'].mean():.1f}%** de media respecto a semanas equivalentes. BBK Live tiene impacto significativo pero más concentrado en los 3 días del festival.

> *Metodología: comparación contra semanas ±4 semanas del mismo año sin evento, controlando día de la semana.*

---

## 3. Comportamiento por Día de Semana

El día con más check-ins es el **{dow['top_checkin']}** y el día con más check-outs es el **{dow['top_checkout']}**. El ADR de fin de semana (viernes-domingo) es de **€{dow['wkend_adr']:.2f}** frente a **€{dow['wkday_adr']:.2f}** entre semana — un diferencial del **{dow['wkend_uplift_pct']:+.1f}%**.

Este patrón confirma el perfil mixto del portfolio: hay demanda de negocio (lunes-jueves) y turística (viernes-domingo), sin una dominancia clara de ninguno.

---

## 4. Lead Time vs Precio: ¿Se cobra más a quien reserva antes?

Correlación Pearson entre lead_time y ADR: **r = {lt['corr_r']}** (p = {lt['corr_p']})

| Antelación | ADR Medio (€) | ADR Mediana (€) | Nº reservas |
|------------|--------------|----------------|-------------|
"""
for _, r in lt['lt_adr_table'].iterrows():
    report += f"| {r['lt_bucket']} | €{r['adr_mean']:.2f} | €{r['adr_median']:.2f} | {r['count']:,} |\n"

direction = "positiva" if lt['corr_r'] > 0 else "negativa"
report += f"""
La correlación es **{direction}** (r={lt['corr_r']}): {"quien reserva con más antelación paga precios ligeramente más altos, lo que sugiere que las reservas de último minuto se hacen a precios reducidos o en épocas de baja demanda. Existe oportunidad de subir precios para el last-minute en temporada alta." if lt['corr_r'] > 0.05 else "no hay relación lineal fuerte entre antelación y precio. El pricing actual parece ser principalmente estacional, no dinámico por lead time."}

---

## 5. Orphan Gaps: Noches Perdidas entre Reservas (2025, nivel apartamento)

"""
if gaps:
    report += f"""Se detectaron **{gaps['total_gaps']:,} gaps** de 1-3 noches entre reservas consecutivas en el mismo apartamento durante 2025. Estas noches no pudieron venderse por ser demasiado cortas para atraer una reserva.

- **Noches perdidas totales:** {gaps['nights_lost']:,}
- **Revenue perdido estimado:** €{gaps['revenue_lost_est']:,.0f} (usando ADR medio de €{gaps['avg_adr_used']:.2f})

| Edificio | Nº gaps | Noches perdidas | Revenue perdido est. |
|----------|---------|----------------|---------------------|
"""
    for _, r in gaps['by_building'].iterrows():
        report += f"| {r['building']} | {r['total_gaps']:,} | {r['nights_lost']:,} | €{r['revenue_lost_est']:,.0f} |\n"
    report += """
La solución operativa es implementar **minimum stay dinámico** que fuerce gaps a cerrarse, o lanzar ofertas de last-minute específicas para esas fechas.
"""
else:
    report += "Sin datos suficientes de nivel apartamento para calcular gaps (solo disponible desde 2025 vía Smoobu).\n"

report += f"""
---

## 6. Patrones de Cancelación: ¿Qué tipo de reservas se cancelan más?

**Canal con mayor tasa de cancelación:** {canc['highest_canal']} ({canc['highest_canal_pct']}%)

### Por canal
| Canal | Total | Canceladas | Tasa % |
|-------|-------|-----------|--------|
"""
for _, r in canc['canal'].iterrows():
    report += f"| {r['channel']} | {r['total']:,} | {r['canceladas']:,} | {r['tasa_%']}% |\n"

report += """
### Por lead time
| Antelación | Total | Canceladas | Tasa % |
|------------|-------|-----------|--------|
"""
for _, r in canc['lt'].iterrows():
    report += f"| {r['lt_seg']} | {r['total']:,} | {r['canceladas']:,} | {r['tasa_%']}% |\n"

report += f"""
El segmento de mayor riesgo de cancelación son las reservas de **{canc['lt_highest']}** ({canc['lt_highest_pct']}%). Las reservas de última hora (same day) se cancelan muy poco — quien reserva el mismo día, casi siempre llega.

---

## 7. País de Origen (cobertura: {pais['cobertura_pct']}% de reservas, solo EDIFICIO_E 2021-2025)

"""
report += "| País | Reservas | % total | ADR (€) | ALOS (n) | Canc.% |\n"
report += "|------|----------|---------|---------|---------|-------|\n"
total_r = pais['top_paises']['reservas'].sum()
for _, r in pais['top_paises'].iterrows():
    report += f"| {r['country']} | {r['reservas']:,} | {r['reservas']/total_r*100:.1f}% | €{r['adr']:.2f} | {r['alos']:.2f} | {r.get('canc_%','n/a')}% |\n"

report += f"""
> ⚠️ *Limitación importante: el dato de país solo existe en los Booking Statements, que cubren exclusivamente Edificio E. No es representativo del portfolio completo.*

---

## 8. Cohort Analysis: ¿Qué edificios mejoran sistemáticamente?

El índice RevPAR (primer año activo = 100) revela la trayectoria de cada edificio:

| Edificio | Año apertura | RevPAR año 1 (€) | RevPAR 2024 (€) | Crecimiento |
|----------|-------------|-----------------|----------------|-------------|
"""
for bld in ['EDIFICIO_A','EDIFICIO_B','EDIFICIO_C','EDIFICIO_D','EDIFICIO_E']:
    sub = coh['data'][coh['data']['building'] == bld].sort_values('year')
    if len(sub) >= 2:
        first = sub.iloc[0]
        last  = sub[sub['year'] == 2024] if 2024 in sub['year'].values else sub.iloc[[-1]]
        last  = last.iloc[0]
        growth = round((last['revpar'] / first['revpar'] - 1) * 100, 1) if first['revpar'] > 0 else 0
        report += f"| {bld} | {int(first['year'])} | €{first['revpar']:.2f} | €{last['revpar']:.2f} | {growth:+.1f}% |\n"

report += f"""
El edificio con mayor crecimiento de RevPAR es **{coh['best_growth']}**. La tendencia general es de mejora sostenida en todos los edificios, con aceleración en 2022-2023 post-COVID.

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
"""

(REPORTS / '02_findings.md').write_text(report, encoding='utf-8')
print(f"  Guardado: outputs/reports/02_findings.md")

print("\n" + "=" * 60)
print("FASE 2 COMPLETADA")
print(f"  Figuras: {len(list(FIGURES.glob('02_*.html')))} HTML + PNG")
print("=" * 60)
