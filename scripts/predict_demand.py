# -*- coding: utf-8 -*-
"""
Modelo A — Predicción de demanda (ocupación semanal)
Uso:
    python scripts/predict_demand.py --building EDIFICIO_B --year 2025 --week 31
    python scripts/predict_demand.py --building EDIFICIO_E --year 2025 --week 32 --occ_lag1 75
"""

import sys, argparse, json
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
import pandas as pd
import joblib
from pathlib import Path

ROOT   = Path(__file__).parent.parent
MODELS = ROOT / 'data' / 'processed' / 'models'

def cyclic(val, max_val):
    return np.sin(2 * np.pi * val / max_val), np.cos(2 * np.pi * val / max_val)

def get_event(year, week, events):
    try:
        monday = pd.Timestamp.fromisocalendar(year, week, 1)
        sunday = monday + pd.Timedelta(days=6)
    except ValueError:
        return 0
    for name, start, end in events:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        if not (e < monday or s > sunday):
            return 1
    return 0

def predict_demand(building: str, year: int, week: int,
                   occ_lag1: float = None, occ_lag52: float = None,
                   adr_lag52: float = None):

    model  = joblib.load(MODELS / 'model_A_demand.pkl')
    le_bld = joblib.load(MODELS / 'le_building.pkl')
    feats  = joblib.load(MODELS / 'features_A.pkl')

    with open(MODELS / 'metadata.json') as f:
        meta = json.load(f)

    if building not in meta['buildings']:
        raise ValueError(f"Edificio '{building}' desconocido. Opciones: {meta['buildings']}")

    INVENTARIO = {'EDIFICIO_A':2,'EDIFICIO_B':9,'EDIFICIO_C':9,'EDIFICIO_D':7,'EDIFICIO_E':14}
    avail = INVENTARIO.get(building, 0) * 7

    wk_sin, wk_cos = cyclic(week, 52)
    mo_sin, mo_cos = cyclic(((week - 1) // 4) + 1, 12)
    is_event = get_event(year, week, meta['events'])
    bld_enc  = le_bld.transform([building])[0]

    row = {
        'building_enc': bld_enc,
        'wk_sin': wk_sin, 'wk_cos': wk_cos,
        'mo_sin': mo_sin, 'mo_cos': mo_cos,
        'is_event': is_event,
        'year': year,
        'occ_lag1':  occ_lag1  if occ_lag1  is not None else 65.0,
        'occ_lag52': occ_lag52 if occ_lag52 is not None else 65.0,
        'adr_lag52': adr_lag52 if adr_lag52 is not None else 90.0,
        'avail': avail,
    }

    X = pd.DataFrame([row])[feats]
    pred = float(np.clip(model.predict(X)[0], 0, 100))

    try:
        monday = pd.Timestamp.fromisocalendar(year, week, 1)
        sunday = monday + pd.Timedelta(days=6)
        date_range = f"{monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"
    except Exception:
        date_range = f"W{week}/{year}"

    return {
        'building':    building,
        'year':        year,
        'week':        week,
        'period':      date_range,
        'pred_occ_pct': round(pred, 1),
        'is_event':    bool(is_event),
        'interpretation': (
            'Alta demanda — considerar subida de precio' if pred >= 80 else
            'Demanda media' if pred >= 50 else
            'Baja demanda — considerar descuento last-minute'
        ),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Predice ocupación semanal por edificio')
    parser.add_argument('--building', required=True, help='EDIFICIO_A | EDIFICIO_B | EDIFICIO_C | EDIFICIO_D | EDIFICIO_E')
    parser.add_argument('--year',     required=True, type=int)
    parser.add_argument('--week',     required=True, type=int, help='Semana ISO (1-52)')
    parser.add_argument('--occ_lag1', type=float, default=None, help='Occ% semana anterior')
    parser.add_argument('--occ_lag52',type=float, default=None, help='Occ% misma semana año anterior')
    parser.add_argument('--adr_lag52',type=float, default=None, help='ADR medio misma semana año anterior')
    args = parser.parse_args()

    result = predict_demand(
        building=args.building.upper(), year=args.year, week=args.week,
        occ_lag1=args.occ_lag1, occ_lag52=args.occ_lag52, adr_lag52=args.adr_lag52,
    )
    print("\n── Predicción de Demanda ──────────────────────────")
    for k, v in result.items():
        print(f"  {k:<22}: {v}")
    print("───────────────────────────────────────────────────\n")
