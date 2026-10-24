"""Date-partitioned synthetic source simulator; provenance is saved with each batch."""

import hashlib
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

FACILITIES = [
    ("Aster General", "Chennai", 13.08, 80.27),
    ("Northgate Medical", "Bengaluru", 12.97, 77.59),
    ("Meridian Hospital", "Hyderabad", 17.38, 78.49),
    ("Harbor Health", "Kochi", 9.93, 76.26),
]
PRODUCTS = [
    {"product_id": "P01", "product_name": "Diagnostic reagent", "min_c": 2, "max_c": 8},
    {"product_id": "P02", "product_name": "Temperature-sensitive biologic", "min_c": 2, "max_c": 8},
    {"product_id": "P03", "product_name": "Laboratory control kit", "min_c": 2, "max_c": 8},
]
FIELDS = [
    "event_id",
    "shipment_date",
    "facility",
    "city",
    "product_id",
    "units",
    "temperature_c",
    "ambient_c",
    "expiry_date",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def input_digest(root):
    paths = [
        root / p for p in ["landing/shipments.json", "inbox/shipments.json", "registry.json", "manifest.json"]
    ]
    return hashlib.sha256("".join(sha(p) if p.exists() else "missing" for p in paths).encode()).hexdigest()


def seed(root, day, scenario, live_weather=False):
    root = Path(root)
    if (root / "manifest.json").exists():
        return
    for sub in ["landing", "inbox"]:
        (root / sub).mkdir(parents=True, exist_ok=True)
    batch_day = date.fromisoformat(day)
    rng = random.Random(batch_day.toordinal())
    weather = {}
    provenance = {
        "shipments": "synthetic, deterministic daily simulation; no patient data",
        "weather": "synthetic ambient temperatures",
        "date": day,
    }
    if live_weather:
        # Forecast API supports the current day. Historical demos stay explicitly synthetic.
        if batch_day == datetime.now(ZoneInfo("Asia/Kolkata")).date():
            try:
                response = httpx.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": ",".join(str(f[2]) for f in FACILITIES),
                        "longitude": ",".join(str(f[3]) for f in FACILITIES),
                        "daily": "temperature_2m_max",
                        "timezone": "Asia/Kolkata",
                        "forecast_days": 1,
                    },
                    timeout=15,
                )
                response.raise_for_status()
                payload = response.json()
                weather = {
                    f[1]: p["daily"]["temperature_2m_max"][0]
                    for f, p in zip(FACILITIES, payload, strict=True)
                }
                provenance["weather"] = "Open-Meteo forecast snapshot (CC BY 4.0); https://open-meteo.com/"
            except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
                provenance["weather_error"] = type(exc).__name__
    rows = []
    for i in range(192):
        facility, city, _, _ = FACILITIES[i % 4]
        rows.append(
            dict(
                zip(
                    FIELDS,
                    [
                        f"{day.replace('-', '')}-S{i:04d}",
                        day,
                        facility + (" " if i % 7 == 0 else ""),
                        city,
                        PRODUCTS[i % 3]["product_id"],
                        rng.randint(12, 180),
                        round(rng.uniform(1, 10) if i % 11 == 0 else rng.uniform(3, 7), 2),
                        weather.get(city, round(rng.uniform(27, 36), 1)),
                        (batch_day + timedelta(days=rng.randint(3, 180))).isoformat(),
                    ],
                    strict=True,
                )
            )
        )
    if scenario == "schema_drift":
        for row in rows:
            row["temp_c"] = row.pop("temperature_c")
    if scenario == "duplicates":
        rows += [dict(r) for r in rows[:12]]
    if scenario == "invalid_values":
        rows[0]["temperature_c"] = 999.0
        rows[1]["units"] = -20
    raw = "\n".join(json.dumps(r) for r in rows) + "\n"
    (root / "landing/shipments.json").write_text(raw)
    if scenario != "missing_partition":
        (root / "inbox/shipments.json").write_text(raw)
    (root / "registry.json").write_text(
        json.dumps(
            {
                "primary_available": scenario != "dependency_down",
                "mirror_available": True,
                "products": PRODUCTS,
                "version": "catalogue-2026-10",
                "mirror_sha256": hashlib.sha256(json.dumps(PRODUCTS, sort_keys=True).encode()).hexdigest(),
            }
        )
    )
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "partition": day,
                "records": len(rows),
                "unique_events": 192,
                "landing_sha256": sha(root / "landing/shipments.json"),
                "provenance": provenance,
            },
            indent=2,
        )
    )
