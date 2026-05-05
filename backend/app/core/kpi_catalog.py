from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.api.analytics import _csv_kpis, _snapshot_kpis
from app.models.database import ReportingPeriod


@dataclass(frozen=True)
class KpiSpec:
    kpi_id: str
    label: str
    aliases: list[str]
    scope: str
    format_hint: str
    source_key: str


KPI_CATALOG: dict[str, KpiSpec] = {
    "total_rent": KpiSpec(
        kpi_id="total_rent",
        label="Total Rent",
        aliases=["Gesamtmiete", "Jahresnettomiete", "Total annual rent", "Contract rent"],
        scope="portfolio",
        format_hint="money_eur_millions",
        source_key="total_rent",
    ),
    "total_area": KpiSpec(
        kpi_id="total_area",
        label="Total Area",
        aliases=["Gesamtfläche", "Mietfläche", "Total area", "Rentable area"],
        scope="portfolio",
        format_hint="area_sqm",
        source_key="total_area",
    ),
    "vacant_area": KpiSpec(
        kpi_id="vacant_area",
        label="Vacant Area",
        aliases=["Leerstandsfläche", "Vacancy area", "Vacant space"],
        scope="portfolio",
        format_hint="area_sqm",
        source_key="vacant_area",
    ),
    "vacancy_rate": KpiSpec(
        kpi_id="vacancy_rate",
        label="Vacancy Rate",
        aliases=["Leerstandsquote", "Vacancy", "Vacancy rate"],
        scope="portfolio",
        format_hint="percent",
        source_key="vacancy_rate",
    ),
    "tenant_count": KpiSpec(
        kpi_id="tenant_count",
        label="Tenant Count",
        aliases=["Mieteranzahl", "Anzahl Mieter", "Tenant count", "Tenants"],
        scope="portfolio",
        format_hint="integer",
        source_key="tenant_count",
    ),
    "property_count": KpiSpec(
        kpi_id="property_count",
        label="Property Count",
        aliases=["Objektanzahl", "Anzahl Immobilien", "Property count", "Properties"],
        scope="portfolio",
        format_hint="integer",
        source_key="property_count",
    ),
    "fair_value": KpiSpec(
        kpi_id="fair_value",
        label="Fair Value",
        aliases=["Verkehrswert", "Marktwert", "Fair value", "Market value"],
        scope="portfolio",
        format_hint="money_eur_millions",
        source_key="fair_value",
    ),
    "total_debt": KpiSpec(
        kpi_id="total_debt",
        label="Total Debt",
        aliases=["Fremdkapital", "Darlehen", "Total debt", "Debt"],
        scope="portfolio",
        format_hint="money_eur_millions",
        source_key="total_debt",
    ),
    "wault_avg": KpiSpec(
        kpi_id="wault_avg",
        label="Average WAULT",
        aliases=["WAULT", "Ø WAULT", "Weighted average unexpired lease term"],
        scope="portfolio",
        format_hint="years_decimal",
        source_key="wault_avg",
    ),
}


def get_kpi(kpi_id: str) -> KpiSpec | None:
    return KPI_CATALOG.get(kpi_id)


def _to_float(value: float | int | Decimal) -> float:
    return float(value)


def _decimal_comma(value: str) -> str:
    return value.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_number(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    if decimals > 0:
        formatted = formatted.rstrip("0").rstrip(".")
    return _decimal_comma(formatted)


def format_value(value: float | int, format_hint: str, locale: str = "de_DE") -> str:
    number = _to_float(value)

    if format_hint == "money_eur_millions":
        return f"{_format_number(number / 1_000_000, 1)} M€"
    if format_hint == "money_eur":
        return f"{_format_number(number, 0)} €"
    if format_hint == "area_sqm":
        decimals = 0 if number.is_integer() else 1
        return f"{_format_number(number, decimals)} m²"
    if format_hint == "percent":
        return f"{_format_number(number, 2)} %"
    if format_hint == "integer":
        return str(int(round(number)))
    if format_hint == "years_decimal":
        return f"{_format_number(number, 1)} Jahre"
    return str(value)


def resolve_kpi_value(db: Session, kpi_id: str, period_id: int) -> float | int | None:
    spec = get_kpi(kpi_id)
    if not spec:
        return None

    period = db.get(ReportingPeriod, period_id)
    if not period:
        return None

    values = {**_csv_kpis(db, period), **_snapshot_kpis(db, period)}
    return values.get(spec.source_key)
