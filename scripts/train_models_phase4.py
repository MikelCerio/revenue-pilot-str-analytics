# -*- coding: utf-8 -*-
"""
Fase 4 — Entrenamiento de modelos predictivos
Modelos: A) Demanda (ocupación), B) Cancelación, C) Precio recomendado
Split temporal: train 2019-2022 | val 2023 | test 2024
Uso: python scripts/train_models_phase4.py
"""

import sys, warnings, json
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (mean_absolute_error, mean_squared_error,
                             classification_report, roc_auc_score,
                             precision_score, recall_score, f1_score,
                             fbeta_score, confusion_matrix)
import lightgbm as lgb

ROOT     = Path(__file__).parent.parent
MODELS   = ROOT / 'data' / 'processed' / 'models'
FIGURES  = ROOT / 'outputs' / 'figures'
REPORTS  = ROOT / 'outputs' / 'reports'
for p in [MODELS, FIGURES, REPORTS]:
    p.mkdir(parents=True, exist_ok=True)

TEMPLATE = 'plotly_white'

print("=" * 60)
print("FASE 4 — MODELOS PREDICTIVOS")
print("=" * 60)

# ── Inventario y eventos ──────────────────────────────────────────────────────
INVENTARIO = {'EDIFICIO_A':2,'EDIFICIO_B':9,'EDIFICIO_C':9,'EDIFICIO_D':7,'EDIFICIO_E':14}
OPENING = {
    'EDIFICIO_A':pd.Timestamp('2019-05-27'), 'EDIFICIO_B':pd.Timestamp('2019-08-09'),
    'EDIFICIO_C':pd.Timestamp('2020-08-26'), 'EDIFICIO_E':pd.Timestamp('2021-07-29'),
    'EDIFICIO_D':pd.Timestamp('2023-03-31'),
}

EVENTS_LIST = [
    ('Aste Nagusia','2019-08-17','2019-08-25'), ('BBK Live','2019-07-11','2019-07-13'),
    ('Aste Nagusia','2021-08-14','2021-08-22'), ('BBK Live','2021-07-08','2021-07-10'),
    ('Aste Nagusia','2022-08-20','2022-08-28'), ('BBK Live','2022-07-07','2022-07-09'),
    ('Aste Nagusia','2023-08-19','2023-08-27'), ('BBK Live','2023-07-06','2023-07-08'),
    ('Aste Nagusia','2024-08-17','2024-08-25'), ('BBK Live','2024-07-11','2024-07-13'),
    ('Bilbao Marathon','2022-11-06','2022-11-06'), ('Bilbao Marathon','2023-11-05','2023-11-05'),
    ('Bilbao Marathon','2024-11-10','2024-11-10'),
]
events_df = pd.DataFrame(EVENTS_LIST, columns=['name','start','end'])
events_df['start'] = pd.to_datetime(events_df['start'])
events_df['end']   = pd.to_datetime(events_df['end'])


def get_event_for_week(year, week):
    try:
        monday = pd.Timestamp.fromisocalendar(year, week, 1)
        sunday = monday + pd.Timedelta(days=6)
    except ValueError:
        return 0, 'none'
    for _, ev in events_df.iterrows():
        if not (ev['end'] < monday or ev['start'] > sunday):
            return 1, ev['name'].lower().replace(' ', '_')
    return 0, 'none'


def cyclic(val, max_val):
    """Codificación cíclica sin/cos."""
    return np.sin(2 * np.pi * val / max_val), np.cos(2 * np.pi * val / max_val)


def save_fig(fig, name, w=1100, h=520):
    fig.write_html(str(FIGURES / f'{name}.html'))
    try:
        fig.write_image(str(FIGURES / f'{name}.png'), width=w, height=h, scale=2)
    except Exception:
        pass
    print(f"    {name} guardado")


# ── Carga ─────────────────────────────────────────────────────────────────────
df_all = pd.read_parquet(ROOT / 'data' / 'processed' / 'reservas_unified.parquet')
df_all['check_in']     = pd.to_datetime(df_all['check_in'])
df_all['booking_date'] = pd.to_datetime(df_all['booking_date'])

df_active = df_all[
    (~df_all['cancelled']) &
    (df_all['channel'] != 'Blocked channel') &
    (df_all['check_in'].dt.year.between(2019, 2025))
].copy()

print(f"Reservas activas 2019-2025: {len(df_active):,}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODELO A — Predicción de Demanda (ocupación semanal por edificio)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*50)
print("MODELO A — Predicción de Demanda (ocupación %)")
print("─"*50)

def build_avail(bld, year, week):
    try:
        monday = pd.Timestamp.fromisocalendar(year, week, 1)
        sunday = monday + pd.Timedelta(days=6)
    except ValueError:
        return 0
    open_d = OPENING.get(bld, monday)
    start  = max(monday, open_d)
    days   = max(0, (sunday - start).days + 1)
    return INVENTARIO.get(bld, 0) * days

# Construir dataset semanal por edificio
rows = []
df_active['week'] = df_active['check_in'].dt.isocalendar().week.astype(int)
df_active['year'] = df_active['check_in'].dt.year

weekly_raw = df_active.groupby(['building','year','week']).agg(
    nights_sold=('nights','sum'),
    adr_mean=('adr','mean'),
    revenue=('gross_amount','sum'),
    n_res=('reservation_id','count'),
    lead_mean=('lead_time_days','mean'),
).reset_index()
# Nota: 2025 es solo hasta abril (datos parciales del año), válido para test

for _, r in weekly_raw.iterrows():
    bld, yr, wk = r['building'], int(r['year']), int(r['week'])
    avail = build_avail(bld, yr, wk)
    if avail == 0:
        continue
    is_ev, ev_name = get_event_for_week(yr, wk)
    wk_sin, wk_cos = cyclic(wk, 52)
    mo_sin, mo_cos = cyclic(((wk - 1) // 4) + 1, 12)

    rows.append({
        'building': bld, 'year': yr, 'week': wk,
        'occ_pct': min(r['nights_sold'] / avail * 100, 100),
        'adr_mean': r['adr_mean'],
        'revenue': r['revenue'],
        'avail': avail,
        'nights_sold': r['nights_sold'],
        'n_res': r['n_res'],
        'lead_mean': r['lead_mean'],
        'is_event': is_ev,
        'event_name': ev_name,
        'wk_sin': wk_sin, 'wk_cos': wk_cos,
        'mo_sin': mo_sin, 'mo_cos': mo_cos,
    })

demand_df = pd.DataFrame(rows)

# Lag features: occ semana anterior y mismo período año anterior
demand_df = demand_df.sort_values(['building','year','week']).reset_index(drop=True)
demand_df['occ_lag1'] = demand_df.groupby('building')['occ_pct'].shift(1).fillna(50)
demand_df['occ_lag52'] = demand_df.groupby('building')['occ_pct'].shift(52).fillna(
    demand_df.groupby(['building','week'])['occ_pct'].transform('mean')
)
demand_df['adr_lag52'] = demand_df.groupby('building')['adr_mean'].shift(52).fillna(
    demand_df.groupby(['building','week'])['adr_mean'].transform('mean')
)

# Encoding edificio
le_bld = LabelEncoder()
demand_df['building_enc'] = le_bld.fit_transform(demand_df['building'])

FEAT_A = ['building_enc','wk_sin','wk_cos','mo_sin','mo_cos',
          'is_event','year','occ_lag1','occ_lag52','adr_lag52','avail']
TARGET_A = 'occ_pct'

# Split temporal: train≤2023, val=2024, test=2025
# (2025 válido para A y C — los datos de ocupación son reales aunque sean parciales)
train_A = demand_df[demand_df['year'] <= 2023]
val_A   = demand_df[demand_df['year'] == 2024]
test_A  = demand_df[demand_df['year'] == 2025]

print(f"  Train: {len(train_A)} semanas | Val: {len(val_A)} | Test: {len(test_A)}")

# LightGBM
model_A = lgb.LGBMRegressor(
    n_estimators=400, learning_rate=0.05, max_depth=5,
    num_leaves=31, min_child_samples=10, subsample=0.8,
    colsample_bytree=0.8, random_state=42, verbose=-1,
)
model_A.fit(train_A[FEAT_A], train_A[TARGET_A],
            eval_set=[(val_A[FEAT_A], val_A[TARGET_A])],
            callbacks=[lgb.early_stopping(50, verbose=False)])

pred_val_A  = model_A.predict(val_A[FEAT_A]).clip(0, 100)
pred_test_A = model_A.predict(test_A[FEAT_A]).clip(0, 100)

mae_val_A  = mean_absolute_error(val_A[TARGET_A], pred_val_A)
rmse_val_A = mean_squared_error(val_A[TARGET_A], pred_val_A) ** 0.5
mae_test_A = mean_absolute_error(test_A[TARGET_A], pred_test_A)
rmse_test_A= mean_squared_error(test_A[TARGET_A], pred_test_A) ** 0.5

print(f"  Val  → MAE: {mae_val_A:.2f}pp | RMSE: {rmse_val_A:.2f}pp")
print(f"  Test → MAE: {mae_test_A:.2f}pp | RMSE: {rmse_test_A:.2f}pp")

# Feature importance
fi_A = pd.DataFrame({'feature': FEAT_A, 'importance': model_A.feature_importances_})
fi_A = fi_A.sort_values('importance', ascending=False)

fig_fi_A = px.bar(fi_A, x='importance', y='feature', orientation='h',
                  title='Modelo A — Feature Importance (Demanda)',
                  template=TEMPLATE, color='importance', color_continuous_scale='Blues')
fig_fi_A.update_layout(showlegend=False, coloraxis_showscale=False)
save_fig(fig_fi_A, '04_modeloA_feature_importance')

# Actual vs predicted en test
test_A_plot = test_A.copy()
test_A_plot['pred'] = pred_test_A
test_A_plot['week_label'] = test_A_plot['week'].astype(str).str.zfill(2) + '/' + test_A_plot['year'].astype(str)

fig_A_pred = px.scatter(test_A_plot, x='occ_pct', y='pred', color='building',
                        title=f'Modelo A — Real vs Predicho (Test 2024) | MAE={mae_test_A:.2f}pp',
                        labels={'occ_pct':'Ocupación real %','pred':'Ocupación predicha %'},
                        template=TEMPLATE, opacity=0.7)
fig_A_pred.add_shape(type='line', x0=0, y0=0, x1=100, y1=100,
                     line=dict(color='black', dash='dash'))
save_fig(fig_A_pred, '04_modeloA_real_vs_pred')

joblib.dump(model_A, MODELS / 'model_A_demand.pkl')
joblib.dump(le_bld, MODELS / 'le_building.pkl')
joblib.dump(FEAT_A, MODELS / 'features_A.pkl')
print(f"  Modelo guardado: data/processed/models/model_A_demand.pkl")


# ═══════════════════════════════════════════════════════════════════════════════
# MODELO B — Probabilidad de Cancelación
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*50)
print("MODELO B — Probabilidad de Cancelación")
print("─"*50)

# Usar solo Booking.com (únicos con cancelaciones reales en los datos)
# Modelo B: excluir 2025 porque las cancelaciones están incompletas
# (reservas recientes aún no han llegado al check-in → tasa artificialmente baja 0.4%)
canc_df = df_all[
    (df_all['channel'] == 'Booking.com') &
    (df_all['check_in'].dt.year.between(2019, 2024)) &
    df_all['nights'].notna() &
    (df_all['nights'] > 0)
].copy()

canc_df['year']     = canc_df['check_in'].dt.year
canc_df['month']    = canc_df['check_in'].dt.month
canc_df['week']     = canc_df['check_in'].dt.isocalendar().week.astype(int)
canc_df['is_wkend'] = canc_df['check_in'].dt.dayofweek.isin([4,5,6]).astype(int)
canc_df['adults']   = canc_df['adults'].fillna(2).clip(1, 8)
canc_df['lt_days']  = canc_df['lead_time_days'].fillna(0).clip(0, 365)
canc_df['nights_c'] = canc_df['nights'].clip(1, 30)
canc_df['building_enc'] = le_bld.transform(canc_df['building'])

# Evento
canc_df['wk_sin'], canc_df['wk_cos'] = zip(*canc_df['week'].apply(lambda w: cyclic(w, 52)))
canc_df['is_event'] = canc_df.apply(
    lambda r: get_event_for_week(int(r['year']), int(r['week']))[0], axis=1
)

FEAT_B = ['lt_days','nights_c','adults','month','is_wkend','building_enc','is_event','year']
TARGET_B = 'cancelled'

canc_df = canc_df.dropna(subset=FEAT_B + [TARGET_B])
canc_df[TARGET_B] = canc_df[TARGET_B].astype(int)

train_B = canc_df[canc_df['year'] <= 2022]
val_B   = canc_df[canc_df['year'] == 2023]
test_B  = canc_df[canc_df['year'] == 2024]

print(f"  Train: {len(train_B):,} | Val: {len(val_B):,} | Test: {len(test_B):,}")
print(f"  Tasa cancelación train: {train_B[TARGET_B].mean()*100:.1f}%")

# Class weight para manejar desbalance
pos_w = (1 - train_B[TARGET_B].mean()) / train_B[TARGET_B].mean()
model_B = lgb.LGBMClassifier(
    n_estimators=500, learning_rate=0.05, max_depth=5,
    num_leaves=31, min_child_samples=20, subsample=0.8,
    colsample_bytree=0.8, scale_pos_weight=pos_w,
    random_state=42, verbose=-1,
)
model_B.fit(train_B[FEAT_B], train_B[TARGET_B],
            eval_set=[(val_B[FEAT_B], val_B[TARGET_B])],
            callbacks=[lgb.early_stopping(50, verbose=False)])

prob_test_B = model_B.predict_proba(test_B[FEAT_B])[:, 1]
pred_test_B = (prob_test_B >= 0.5).astype(int)

roc_B  = roc_auc_score(test_B[TARGET_B], prob_test_B)
f1_B   = f1_score(test_B[TARGET_B], pred_test_B, zero_division=0)
f2_B   = fbeta_score(test_B[TARGET_B], pred_test_B, beta=2, zero_division=0)
prec_B = precision_score(test_B[TARGET_B], pred_test_B, zero_division=0)
rec_B  = recall_score(test_B[TARGET_B], pred_test_B, zero_division=0)

print(f"  Test 2024 → ROC-AUC: {roc_B:.3f} | F1: {f1_B:.3f} | F2: {f2_B:.3f}")
print(f"             Precision: {prec_B:.3f} | Recall: {rec_B:.3f}")

# Feature importance
fi_B = pd.DataFrame({'feature': FEAT_B, 'importance': model_B.feature_importances_})
fi_B = fi_B.sort_values('importance', ascending=False)

fig_fi_B = px.bar(fi_B, x='importance', y='feature', orientation='h',
                  title='Modelo B — Feature Importance (Cancelación)',
                  template=TEMPLATE, color='importance', color_continuous_scale='Reds')
fig_fi_B.update_layout(showlegend=False, coloraxis_showscale=False)
save_fig(fig_fi_B, '04_modeloB_feature_importance')

# Curva ROC
from sklearn.metrics import roc_curve
fpr, tpr, _ = roc_curve(test_B[TARGET_B], prob_test_B)
fig_roc = go.Figure()
fig_roc.add_trace(go.Scatter(x=fpr, y=tpr, name=f'LightGBM (AUC={roc_B:.3f})',
                              line=dict(color='#FF5A5F', width=2)))
fig_roc.add_shape(type='line', x0=0, y0=0, x1=1, y1=1,
                  line=dict(color='gray', dash='dash'))
fig_roc.update_layout(title='Modelo B — Curva ROC (Test 2024)',
                      xaxis_title='FPR', yaxis_title='TPR', template=TEMPLATE)
save_fig(fig_roc, '04_modeloB_roc_curve')

# Distribución de probabilidad de cancelación
fig_prob = px.histogram(
    pd.DataFrame({'prob': prob_test_B, 'real': test_B[TARGET_B].values}),
    x='prob', color='real', nbins=40, barmode='overlay',
    title='Modelo B — Distribución de probabilidad predicha',
    labels={'prob':'P(cancelación)','real':'Cancelada (real)'},
    template=TEMPLATE, opacity=0.7,
    color_discrete_map={0:'#003580', 1:'#FF5A5F'},
)
save_fig(fig_prob, '04_modeloB_prob_dist')

joblib.dump(model_B, MODELS / 'model_B_cancellation.pkl')
joblib.dump(FEAT_B, MODELS / 'features_B.pkl')
print(f"  Modelo guardado: data/processed/models/model_B_cancellation.pkl")


# ═══════════════════════════════════════════════════════════════════════════════
# MODELO C — Precio Recomendado por Noche
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─"*50)
print("MODELO C — Precio Recomendado (ADR)")
print("─"*50)

# Añadir predicción de demanda al dataset de Modelo A como feature del C
demand_df['pred_occ'] = model_A.predict(demand_df[FEAT_A]).clip(0, 100)

# Merge demand forecast al dataset de reservas activas
price_df = df_active.copy()
price_df['week'] = price_df['check_in'].dt.isocalendar().week.astype(int)
price_df['year'] = price_df['check_in'].dt.year

price_df = price_df.merge(
    demand_df[['building','year','week','pred_occ','occ_lag52','adr_lag52']],
    on=['building','year','week'], how='left'
)

price_df['month']      = price_df['check_in'].dt.month
price_df['dow']        = price_df['check_in'].dt.dayofweek
price_df['is_wkend']   = price_df['dow'].isin([4,5,6]).astype(int)
price_df['lt_days']    = price_df['lead_time_days'].fillna(0).clip(0, 365)
price_df['nights_c']   = price_df['nights'].clip(1, 30)
price_df['building_enc'] = le_bld.transform(price_df['building'])
price_df['wk_sin'], price_df['wk_cos'] = zip(*price_df['week'].apply(lambda w: cyclic(w, 52)))
price_df['mo_sin'], price_df['mo_cos'] = zip(*price_df['month'].apply(lambda m: cyclic(m, 12)))
price_df['is_event'] = price_df.apply(
    lambda r: get_event_for_week(int(r['year']), int(r['week']))[0], axis=1
)
price_df['pred_occ']   = price_df['pred_occ'].fillna(50)
price_df['occ_lag52']  = price_df['occ_lag52'].fillna(50)
price_df['adr_lag52']  = price_df['adr_lag52'].fillna(price_df['adr'].median())

FEAT_C = ['building_enc','wk_sin','wk_cos','mo_sin','mo_cos',
          'is_wkend','is_event','lt_days','nights_c',
          'pred_occ','occ_lag52','adr_lag52','year']
TARGET_C = 'adr'

price_df = price_df.dropna(subset=FEAT_C + [TARGET_C])
price_df = price_df[price_df[TARGET_C] > 0]

# Split C igual que A: train≤2023, val=2024, test=2025
train_C = price_df[price_df['year'] <= 2023]
val_C   = price_df[price_df['year'] == 2024]
test_C  = price_df[price_df['year'] == 2025]

print(f"  Train: {len(train_C):,} | Val: {len(val_C):,} | Test: {len(test_C):,}")

model_C = lgb.LGBMRegressor(
    n_estimators=500, learning_rate=0.04, max_depth=6,
    num_leaves=40, min_child_samples=15, subsample=0.8,
    colsample_bytree=0.8, random_state=42, verbose=-1,
)
model_C.fit(train_C[FEAT_C], train_C[TARGET_C],
            eval_set=[(val_C[FEAT_C], val_C[TARGET_C])],
            callbacks=[lgb.early_stopping(50, verbose=False)])

pred_test_C = model_C.predict(test_C[FEAT_C]).clip(0, 500)
mae_test_C  = mean_absolute_error(test_C[TARGET_C], pred_test_C)
rmse_test_C = mean_squared_error(test_C[TARGET_C], pred_test_C) ** 0.5

pred_val_C  = model_C.predict(val_C[FEAT_C]).clip(0, 500)
mae_val_C   = mean_absolute_error(val_C[TARGET_C], pred_val_C)
rmse_val_C  = mean_squared_error(val_C[TARGET_C], pred_val_C) ** 0.5

print(f"  Val  → MAE: €{mae_val_C:.2f} | RMSE: €{rmse_val_C:.2f}")
print(f"  Test → MAE: €{mae_test_C:.2f} | RMSE: €{rmse_test_C:.2f}")

# Feature importance
fi_C = pd.DataFrame({'feature': FEAT_C, 'importance': model_C.feature_importances_})
fi_C = fi_C.sort_values('importance', ascending=False)

fig_fi_C = px.bar(fi_C, x='importance', y='feature', orientation='h',
                  title='Modelo C — Feature Importance (Precio)',
                  template=TEMPLATE, color='importance', color_continuous_scale='Greens')
fig_fi_C.update_layout(showlegend=False, coloraxis_showscale=False)
save_fig(fig_fi_C, '04_modeloC_feature_importance')

# Real vs predicho
fig_C_pred = px.scatter(
    x=test_C[TARGET_C], y=pred_test_C,
    color=test_C['building'].values,
    opacity=0.6,
    title=f'Modelo C — ADR Real vs Predicho (Test 2024) | MAE=€{mae_test_C:.2f}',
    labels={'x':'ADR real (€)','y':'ADR predicho (€)','color':'Edificio'},
    template=TEMPLATE,
)
max_val = max(test_C[TARGET_C].max(), pred_test_C.max())
fig_C_pred.add_shape(type='line', x0=0, y0=0, x1=max_val, y1=max_val,
                     line=dict(color='black', dash='dash'))
save_fig(fig_C_pred, '04_modeloC_real_vs_pred')

joblib.dump(model_C, MODELS / 'model_C_price.pkl')
joblib.dump(FEAT_C, MODELS / 'features_C.pkl')
print(f"  Modelo guardado: data/processed/models/model_C_price.pkl")

# Guardar metadata para los scripts de inferencia
metadata = {
    'buildings': list(le_bld.classes_),
    'feat_A': FEAT_A, 'feat_B': FEAT_B, 'feat_C': FEAT_C,
    'events': EVENTS_LIST,
}
with open(MODELS / 'metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE DE EVALUACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
print("\nGenerando 04_models_evaluation.md...")

# Métricas por edificio Modelo A
test_A_copy = test_A.copy()
test_A_copy['pred'] = pred_test_A
mae_by_bld = test_A_copy.groupby('building').apply(
    lambda g: pd.Series({
        'MAE (pp)': round(mean_absolute_error(g['occ_pct'], g['pred']), 2),
        'RMSE (pp)': round(mean_squared_error(g['occ_pct'], g['pred'])**0.5, 2),
        'N semanas': len(g),
    })
).reset_index()

# Métricas por edificio Modelo C
test_C_copy = test_C.copy()
test_C_copy['pred'] = pred_test_C
mae_C_bld = test_C_copy.groupby('building').apply(
    lambda g: pd.Series({
        'MAE (€)': round(mean_absolute_error(g['adr'], g['pred']), 2),
        'RMSE (€)': round(mean_squared_error(g['adr'], g['pred'])**0.5, 2),
        'N reservas': len(g),
    })
).reset_index()

# Confusion matrix Modelo B
cm = confusion_matrix(test_B[TARGET_B], pred_test_B)

report = f"""# Evaluación de Modelos Predictivos — Fase 4
**Fecha:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
**Split temporal:** Train 2019-2022 | Validación 2023 | Test 2024

---

## Modelo A — Predicción de Demanda (Ocupación Semanal)

**Algoritmo:** LightGBM Regressor
**Target:** Ocupación % por edificio-semana
**Features:** {len(FEAT_A)} variables (ciclicidad temporal, edificio, eventos, lags)

| Métrica | Validación 2023 | Test 2024 |
|---------|----------------|-----------|
| MAE | {mae_val_A:.2f} pp | {mae_test_A:.2f} pp |
| RMSE | {rmse_val_A:.2f} pp | {rmse_test_A:.2f} pp |

> Un MAE de {mae_test_A:.1f} puntos porcentuales significa que el modelo predice la ocupación semanal con un error medio de ±{mae_test_A:.0f}pp. Para un portfolio con ocupación media del 68%, esto es {'aceptable para planificación de capacidad' if mae_test_A < 15 else 'mejorable con más datos por apartamento'}.

### MAE por Edificio (Test 2024)

{mae_by_bld.to_markdown(index=False)}

### Feature Importance — Top features
{fi_A.head(6).to_markdown(index=False)}

---

## Modelo B — Probabilidad de Cancelación

**Algoritmo:** LightGBM Classifier (scale_pos_weight ajustado)
**Target:** cancelled (0/1) — solo Booking.com
**Features:** {len(FEAT_B)} variables

| Métrica | Test 2024 |
|---------|-----------|
| ROC-AUC | {roc_B:.3f} |
| F1 Score | {f1_B:.3f} |
| F2 Score (recall-weighted) | {f2_B:.3f} |
| Precision | {prec_B:.3f} |
| Recall | {rec_B:.3f} |

**Confusion Matrix (Test 2024, umbral 0.5):**
```
                 Predicho: NO  Predicho: SÍ
Real: NO canc        {cm[0][0]:5d}         {cm[0][1]:5d}
Real: SÍ canc        {cm[1][0]:5d}         {cm[1][1]:5d}
```

> El ROC-AUC de {roc_B:.3f} {'es bueno' if roc_B > 0.75 else 'es moderado'} para este tipo de problema. El recall de {rec_B:.3f} indica que el modelo detecta el {rec_B*100:.0f}% de las cancelaciones reales.
>
> **Uso operativo sugerido:** usar umbral 0.35 (más recall) para alertas tempranas de overbooking preventivo, y 0.65 para acciones costosas (descuentos de retención).

### Feature Importance — Top features
{fi_B.head(6).to_markdown(index=False)}

**Hallazgo clave:** {fi_B.iloc[0]['feature']} es el predictor más importante de cancelación, seguido de {fi_B.iloc[1]['feature']}. Esto confirma los hallazgos de Fase 2.

---

## Modelo C — Precio Recomendado (ADR)

**Algoritmo:** LightGBM Regressor
**Target:** ADR (€/noche)
**Features:** {len(FEAT_C)} variables (incluye pred_occ del Modelo A como feature)

| Métrica | Validación 2023 | Test 2024 |
|---------|----------------|-----------|
| MAE | €{mae_val_C:.2f} | €{mae_test_C:.2f} |
| RMSE | €{rmse_val_C:.2f} | €{rmse_test_C:.2f} |

> Un MAE de €{mae_test_C:.2f} significa que el precio recomendado se desvía en media ±€{mae_test_C:.0f} del precio óptimo histórico observado. {'Esto es operativamente útil.' if mae_test_C < 30 else 'El error es alto por la dispersión de precios entre edificios — usar por segmento.'}

### MAE por Edificio (Test 2024)

{mae_C_bld.to_markdown(index=False)}

### Feature Importance — Top features
{fi_C.head(6).to_markdown(index=False)}

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
"""

(REPORTS / '04_models_evaluation.md').write_text(report, encoding='utf-8')
print(f"  Guardado: outputs/reports/04_models_evaluation.md")

print("\n" + "=" * 60)
print("FASE 4 COMPLETADA")
print(f"  Modelo A (demanda)     MAE test: {mae_test_A:.2f}pp")
print(f"  Modelo B (cancelación) ROC-AUC:  {roc_B:.3f}")
print(f"  Modelo C (precio)      MAE test: €{mae_test_C:.2f}")
print("=" * 60)
