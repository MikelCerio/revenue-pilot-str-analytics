# -*- coding: utf-8 -*-
"""
Modelo C — Precio recomendado por noche (ADR)
Uso:
    python scripts/recommend_price.py --building EDIFICIO_B --year 2025 --week 31 --lead_time 14
    python scripts/recommend_price.py --building EDIFICIO_C --year 2025 --week 32 --is_weekend 1 --nights 2
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

def recommend_price(building: str, year: int, week: int,
                    lead_time: int = 14, nights: int = 2, is_weekend: int = None,
                    pred_occ: float = None, occ_lag52: float = None, adr_lag52: float = None):

    from predict_demand import predict_demand  # reutilizamos Modelo A

    model  = joblib.load(MODELS / 'model_C_price.pkl')
    le_bld = joblib.load(MODELS / 'le_building.pkl')
    feats  = joblib.load(MODELS / 'features_C.pkl')

    with open(MODELS / 'metadata.json') as f:
        meta = json.load(f)

    if building not in meta['buildings']:
        raise ValueError(f"Edificio '{building}' desconocido. Opciones: {meta['buildings']}")

    # Si no se proporciona pred_occ, calcularlo con Modelo A
    if pred_occ is None:
        demand = predict_demand(building=building, year=year, week=week,
                                occ_lag52=occ_lag52, adr_lag52=adr_lag52)
        pred_occ = demand['pred_occ_pct']

    month    = ((week - 1) // 4) + 1
    bld_enc  = le_bld.transform([building])[0]
    wk_sin, wk_cos = cyclic(week, 52)
    mo_sin, mo_cos = cyclic(month, 12)
    is_event = get_event(year, week, meta['events'])

    # is_weekend: si no se indica, asumir finde si la semana incluye viernes
    if is_weekend is None:
        try:
            monday = pd.Timestamp.fromisocalendar(year, week, 1)
            is_weekend = 1 if monday.weekday() >= 4 else 0
        except Exception:
            is_weekend = 0

    row = {
        'building_enc': bld_enc,
        'wk_sin': wk_sin, 'wk_cos': wk_cos,
        'mo_sin': mo_sin, 'mo_cos': mo_cos,
        'is_wkend':  is_weekend,
        'is_event':  is_event,
        'lt_days':   min(lead_time, 365),
        'nights_c':  min(nights, 30),
        'pred_occ':  pred_occ,
        'occ_lag52': occ_lag52 if occ_lag52 is not None else 65.0,
        'adr_lag52': adr_lag52 if adr_lag52 is not None else 90.0,
        'year':      year,
    }

    X    = pd.DataFrame([row])[feats]
    adr  = float(np.clip(model.predict(X)[0], 20, 1000))

    # Rango sugerido: ±10%
    adr_min = round(adr * 0.90, 2)
    adr_max = round(adr * 1.10, 2)

    # Justificación de ajustes
    adjustments = []
    if is_event:
        adjustments.append('+35% por evento local en esta semana')
    if pred_occ >= 80:
        adjustments.append(f'+20% por ocupación esperada alta ({pred_occ:.0f}%)')
    elif pred_occ < 40:
        adjustments.append(f'Precio conservador por baja ocupación esperada ({pred_occ:.0f}%)')
    if is_weekend:
        adjustments.append('+15% por check-in fin de semana')
    if lead_time <= 3:
        adjustments.append('Last-minute: mantener P75 del mes como mínimo')

    try:
        monday = pd.Timestamp.fromisocalendar(year, week, 1)
        sunday = monday + pd.Timedelta(days=6)
        period = f"{monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"
    except Exception:
        period = f"W{week}/{year}"

    return {
        'building':        building,
        'period':          period,
        'pred_occ_pct':    round(pred_occ, 1),
        'lead_time_days':  lead_time,
        'is_event':        bool(is_event),
        'is_weekend':      bool(is_weekend),
        'adr_recomendado': round(adr, 2),
        'rango_min':       adr_min,
        'rango_max':       adr_max,
        'ajustes_aplicados': ' | '.join(adjustments) if adjustments else 'Sin ajustes especiales',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Recomienda precio por noche (ADR)')
    parser.add_argument('--building',   required=True, help='EDIFICIO_A | EDIFICIO_B | EDIFICIO_C | EDIFICIO_D | EDIFICIO_E')
    parser.add_argument('--year',       required=True, type=int)
    parser.add_argument('--week',       required=True, type=int, help='Semana ISO')
    parser.add_argument('--lead_time',  type=int,   default=14,  help='Días de antelación (default 14)')
    parser.add_argument('--nights',     type=int,   default=2,   help='Duración estancia')
    parser.add_argument('--is_weekend', type=int,   default=None,help='0/1 (auto si no se indica)')
    parser.add_argument('--pred_occ',   type=float, default=None,help='Ocupación esperada % (auto con Modelo A)')
    parser.add_argument('--occ_lag52',  type=float, default=None)
    parser.add_argument('--adr_lag52',  type=float, default=None)
    args = parser.parse_args()

    result = recommend_price(
        building=args.building.upper(), year=args.year, week=args.week,
        lead_time=args.lead_time, nights=args.nights, is_weekend=args.is_weekend,
        pred_occ=args.pred_occ, occ_lag52=args.occ_lag52, adr_lag52=args.adr_lag52,
    )
    print("\n── Precio Recomendado ─────────────────────────────")
    for k, v in result.items():
        print(f"  {k:<24}: {v}")
    print("───────────────────────────────────────────────────\n")
