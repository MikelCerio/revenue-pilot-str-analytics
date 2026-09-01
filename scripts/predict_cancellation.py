# -*- coding: utf-8 -*-
"""
Modelo B — Probabilidad de cancelación (Booking.com)
Uso:
    python scripts/predict_cancellation.py --building EDIFICIO_B --lead_time 60 --nights 3 --month 8
    python scripts/predict_cancellation.py --building EDIFICIO_E --lead_time 5 --nights 1 --month 1 --is_weekend 0
"""

import sys, argparse, json
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
import pandas as pd
import joblib
from pathlib import Path

ROOT   = Path(__file__).parent.parent
MODELS = ROOT / 'data' / 'processed' / 'models'

def get_event_for_month_week(month, year=2025):
    """Aproxima si hay evento dado mes (para inferencia sin semana exacta)."""
    events = [(7,'BBK Live'), (8,'Aste Nagusia'), (11,'Bilbao Marathon')]
    for m, name in events:
        if month == m:
            return 1
    return 0

def predict_cancellation(building: str, lead_time: int, nights: int, month: int,
                          is_weekend: int = 0, adults: int = 2, year: int = 2025,
                          threshold_alert: float = 0.35,
                          threshold_action: float = 0.65):

    model  = joblib.load(MODELS / 'model_B_cancellation.pkl')
    le_bld = joblib.load(MODELS / 'le_building.pkl')
    feats  = joblib.load(MODELS / 'features_B.pkl')

    with open(MODELS / 'metadata.json') as f:
        meta = json.load(f)

    if building not in meta['buildings']:
        raise ValueError(f"Edificio '{building}' desconocido. Opciones: {meta['buildings']}")

    bld_enc  = le_bld.transform([building])[0]
    is_event = get_event_for_month_week(month, year)

    row = {
        'lt_days':     min(lead_time, 365),
        'nights_c':    min(nights, 30),
        'adults':      min(max(adults, 1), 8),
        'month':       month,
        'is_wkend':    is_weekend,
        'building_enc': bld_enc,
        'is_event':    is_event,
        'year':        year,
    }

    X = pd.DataFrame([row])[feats]
    prob = float(model.predict_proba(X)[0, 1])

    if prob >= threshold_action:
        risk    = 'ALTO'
        action  = 'Ofrecer tarifa NR con descuento o solicitar prepago'
    elif prob >= threshold_alert:
        risk    = 'MEDIO'
        action  = 'Monitorizar — considerar recordatorio pre-estancia'
    else:
        risk    = 'BAJO'
        action  = 'Sin acción necesaria'

    return {
        'building':         building,
        'lead_time_days':   lead_time,
        'nights':           nights,
        'month':            month,
        'is_weekend':       bool(is_weekend),
        'prob_cancelacion': round(prob, 3),
        'prob_pct':         f"{prob*100:.1f}%",
        'riesgo':           risk,
        'accion_sugerida':  action,
        'umbral_alerta':    threshold_alert,
        'umbral_accion':    threshold_action,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Predice probabilidad de cancelación')
    parser.add_argument('--building',   required=True, help='EDIFICIO_A | EDIFICIO_B | EDIFICIO_C | EDIFICIO_D | EDIFICIO_E')
    parser.add_argument('--lead_time',  required=True, type=int,   help='Días entre reserva y check-in')
    parser.add_argument('--nights',     required=True, type=int,   help='Duración de la estancia (noches)')
    parser.add_argument('--month',      required=True, type=int,   help='Mes del check-in (1-12)')
    parser.add_argument('--is_weekend', type=int, default=0,       help='1=check-in viernes/sábado/domingo')
    parser.add_argument('--adults',     type=int, default=2,       help='Nº adultos')
    parser.add_argument('--year',       type=int, default=2025)
    parser.add_argument('--threshold_alert',  type=float, default=0.35)
    parser.add_argument('--threshold_action', type=float, default=0.65)
    args = parser.parse_args()

    result = predict_cancellation(
        building=args.building.upper(), lead_time=args.lead_time,
        nights=args.nights, month=args.month, is_weekend=args.is_weekend,
        adults=args.adults, year=args.year,
        threshold_alert=args.threshold_alert, threshold_action=args.threshold_action,
    )
    print("\n── Predicción de Cancelación ──────────────────────")
    for k, v in result.items():
        print(f"  {k:<24}: {v}")
    print("───────────────────────────────────────────────────\n")
