"""
00_build_from_public.py
=======================
Reconstruye la capa `data/processed/` a partir de los datos publicos
anonimizados de `data/public/`.

Por que existe este script
--------------------------
El pipeline original parte de ficheros crudos (extractos de Booking.com,
exportaciones del channel manager) que no se publican: contienen datos
personales de huespedes e informacion comercial. Lo que si se publica es
el star schema ya anonimizado.

Este script deshace el star schema para regenerar la tabla unificada que
esperan las fases 1-3 y 5, de modo que el pipeline sea ejecutable desde
un `git clone` sin necesidad de los datos crudos.

Uso:
    python scripts/00_build_from_public.py
    python scripts/kpis_phase1.py        # ya funciona
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "data" / "public"
PROCESSED = ROOT / "data" / "processed"


def to_date(series: pd.Series) -> pd.Series:
    """Convierte una date_key con formato YYYYMMDD en datetime."""
    return pd.to_datetime(series.astype("Int64").astype(str),
                          format="%Y%m%d", errors="coerce")


def main() -> None:
    print("=" * 62)
    print("RECONSTRUCCION DE data/processed/ DESDE data/public/")
    print("=" * 62)

    fact = pd.read_parquet(PUBLIC / "fact_reservations.parquet")
    prop = pd.read_csv(PUBLIC / "dim_property.csv")
    chan = pd.read_csv(PUBLIC / "dim_channel.csv")
    print(f"  fact_reservations : {len(fact):,} filas")
    print(f"  dim_property      : {len(prop)} edificios")
    print(f"  dim_channel       : {len(chan)} canales")

    df = fact.merge(
        prop[["property_key", "building_code", "building_name_public"]],
        on="property_key", how="left",
    ).merge(
        chan[["channel_key", "channel_name", "channel_type",
              "typical_commission_pct"]],
        on="channel_key", how="left",
    )

    # Renombrado al esquema que esperan las fases 1-3 y 5
    out = pd.DataFrame({
        "reservation_id": df["reservation_id"],
        "source":         df["source"],
        # Los scripts del pipeline usan claves EDIFICIO_X (ver INVENTARIO/OPENING);
        # dim_property guarda la clave corta del star schema (A-E).
        "building":       "EDIFICIO_" + df["building_code"].astype(str),
        "building_key":   df["building_code"],
        "building_name":  df["building_name_public"],
        "channel":        df["channel_name"],
        "channel_type":   df["channel_type"],
        "comision_pct":   df["typical_commission_pct"],
        "check_in":       to_date(df["date_key_checkin"]),
        "check_out":      to_date(df["date_key_checkout"]),
        "booking_date":   to_date(df["date_key_booking"]),
        "nights":         df["nights"],
        "adults":         df["adults"],
        "children":       df["children"],
        "gross_amount":   df["revenue_gross"],
        "net_amount":     df["revenue_net"],
        "commission":     df["commission"],
        # Alias: powerbi_phase5 espera este nombre
        "commission_amount": df["commission"],
        "adr":            df["adr"],
        "adr_net":        df["adr_net"],
        "lead_time_days": df["lead_time_days"],
        "cancelled":      df["is_cancelled"].astype(bool),
        "no_show":        df["is_no_show"].astype(bool),
        "status":         df["status_norm"],
        "country":        df["country"],
    })

    out["year"] = out["check_in"].dt.year
    out["month"] = out["check_in"].dt.month
    out["dow"] = out["check_in"].dt.dayofweek
    out["dow_name"] = out["check_in"].dt.day_name()
    out["week"] = out["check_in"].dt.isocalendar().week.astype("Int64")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED / "reservas_unified.parquet"
    out.to_parquet(dest, index=False)

    print(f"\n  Escrito: data/processed/reservas_unified.parquet")
    print(f"  {len(out):,} filas x {len(out.columns)} columnas")
    rng = f"{out['check_in'].min():%Y-%m-%d} -> {out['check_in'].max():%Y-%m-%d}"
    print(f"  Rango de fechas: {rng}")
    print(f"  Edificios: {sorted(out['building'].dropna().unique())}")
    print("\n  Ya puedes ejecutar: python scripts/kpis_phase1.py")


if __name__ == "__main__":
    main()
