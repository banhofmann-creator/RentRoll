"""One-off script: import property master data from Immobilie_Liste CSV."""
import csv
import sys
from datetime import datetime
from pathlib import Path

import requests

API = "http://localhost:8000/api/master-data/properties"

COUNTRY_MAP = {
    "Deutschland": "DE",
    "Niederlande": "NL",
    "Slowakei": "SK",
    "Polen": "PL",
    "Frankreich": "FR",
    "Italien": "IT",
    "Österreich": "AT",
}

CSV_PATH = Path(__file__).resolve().parent.parent / "samples" / "260504_Immobilie_Liste_1-Garbe.csv"


def parse_date(val: str) -> str | None:
    val = val.strip()
    if not val:
        return None
    try:
        return datetime.strptime(val, "%d.%m.%Y").date().isoformat()
    except ValueError:
        return None


def main():
    lines = CSV_PATH.read_text(encoding="latin-1").splitlines()
    reader = csv.reader(lines[6:], delimiter=";")

    created = 0
    skipped = 0
    errors = []

    for row in reader:
        if len(row) < 10 or not row[2].strip():
            continue

        property_id = row[2].strip()
        street_parts = [row[5].strip(), row[6].strip()]
        street = " ".join(p for p in street_parts if p) or None
        country_raw = row[9].strip()

        payload = {
            "property_id": property_id,
            "fund_csv_name": row[4].strip() or None,
            "street": street,
            "zip_code": row[7].strip() or None,
            "city": row[8].strip() or None,
            "country": COUNTRY_MAP.get(country_raw, country_raw[:2].upper() if country_raw else None),
            "purchase_date": parse_date(row[14]) if len(row) > 14 else None,
        }

        # Strip None values so we don't send nulls for missing fields
        payload = {k: v for k, v in payload.items() if v is not None}

        resp = requests.post(API, json=payload)

        if resp.status_code == 201:
            created += 1
        elif resp.status_code == 409:
            skipped += 1
        else:
            errors.append(f"{property_id}: {resp.status_code} {resp.text}")

    print(f"Created: {created}")
    print(f"Skipped (already exist): {skipped}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
