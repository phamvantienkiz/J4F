from dataclasses import dataclass
from datetime import date

import requests


VATCOMPLY_BASE_URL = "https://api.vatcomply.com"
VATCOMPLY_TIMEOUT_SECONDS = 2


@dataclass
class TaxResult:
    region: str
    sub_region: str
    tax_type: str
    rate: float
    rate_pct: str
    tax_amount: float
    net_revenue: float
    data_source: str
    note: str
    is_estimated: bool


US_STATE_RATES = {
    "OR": 0.0,
    "MT": 0.0,
    "NH": 0.0,
    "DE": 0.0,
    "AK": 0.0,
    "CA": 0.0868,
    "TX": 0.0820,
    "NY": 0.0852,
    "FL": 0.0701,
    "IL": 0.0882,
    "PA": 0.0634,
    "OH": 0.0724,
    "GA": 0.0731,
    "NC": 0.0698,
    "MI": 0.0600,
    "NJ": 0.0660,
    "VA": 0.0565,
    "WA": 0.0923,
    "AZ": 0.0840,
    "TN": 0.0955,
    "MA": 0.0625,
    "IN": 0.0700,
    "MO": 0.0802,
    "MN": 0.0746,
    "WI": 0.0543,
    "CO": 0.0777,
    "SC": 0.0746,
    "AL": 0.0922,
    "LA": 0.0955,
    "KY": 0.0600,
}
US_NO_SALES_TAX_STATES = {"OR", "MT", "NH", "DE", "AK"}
US_APPAREL_EXEMPT_STATES = {"PA", "MN"}
US_APPAREL_THRESHOLD_EXEMPTIONS = {"NY": 110.0, "NJ": 110.0, "MA": 175.0}
US_DEFAULT_RATE = 0.08

CANADA_RATES = {
    "AB": 0.05,
    "BC": 0.12,
    "MB": 0.12,
    "NB": 0.15,
    "NL": 0.15,
    "NS": 0.15,
    "NT": 0.05,
    "NU": 0.05,
    "ON": 0.13,
    "PE": 0.15,
    "QC": 0.14975,
    "SK": 0.11,
    "YT": 0.05,
}
CANADA_DEFAULT_PROVINCE = "ON"

EU_FALLBACK_RATES = {
    "AT": 0.20,
    "BE": 0.21,
    "BG": 0.20,
    "CY": 0.19,
    "CZ": 0.21,
    "DE": 0.19,
    "DK": 0.25,
    "EE": 0.24,
    "ES": 0.21,
    "FI": 0.255,
    "FR": 0.20,
    "GR": 0.24,
    "HR": 0.25,
    "HU": 0.27,
    "IE": 0.23,
    "IT": 0.22,
    "LT": 0.21,
    "LU": 0.17,
    "LV": 0.21,
    "MT": 0.18,
    "NL": 0.21,
    "PL": 0.23,
    "PT": 0.23,
    "RO": 0.19,
    "SE": 0.25,
    "SI": 0.22,
    "SK": 0.20,
}
EU_DEFAULT_RATE = 0.21

COUNTRY_ALIASES = {
    "UK": "GB",
    "UNITED KINGDOM": "GB",
    "GREAT BRITAIN": "GB",
    "ENGLAND": "GB",
    "USA": "US",
    "UNITED STATES": "US",
    "CANADA": "CA",
    "AUSTRALIA": "AU",
    "VIETNAM": "VN",
    "VIET NAM": "VN",
    "EUROPE": "EU",
}

SUB_REGION_ALIASES = {
    "CALIFORNIA": "CA",
    "TEXAS": "TX",
    "NEW YORK": "NY",
    "FLORIDA": "FL",
    "ONTARIO": "ON",
    "QUEBEC": "QC",
    "BRITISH COLUMBIA": "BC",
    "ALBERTA": "AB",
    "GERMANY": "DE",
    "DEUTSCHLAND": "DE",
    "DUC": "DE",
    "FRANCE": "FR",
    "PHAP": "FR",
    "NETHERLANDS": "NL",
    "HOLLAND": "NL",
    "SPAIN": "ES",
    "ITALY": "IT",
    "POLAND": "PL",
}


def _upper(value):
    return str(value or "").strip().upper()


def normalize_region(region):
    value = _upper(region)
    return COUNTRY_ALIASES.get(value, value)


def normalize_sub_region(sub_region):
    value = _upper(sub_region)
    return SUB_REGION_ALIASES.get(value, value)


def _is_apparel(product_type):
    normalized = str(product_type or "").lower()
    apparel_terms = ["apparel", "clothing", "shirt", "t-shirt", "tshirt", "tee", "hoodie", "sweatshirt", "tank"]
    return any(term in normalized for term in apparel_terms)


def _rate_pct(rate):
    percent = rate * 100
    if percent.is_integer():
        return f"{int(percent)}%"
    return f"{percent:.3f}".rstrip("0").rstrip(".") + "%"


def _money(value):
    return round(float(value or 0), 2)


def _build_result(region, sub_region, tax_type, rate, selling_price, data_source, note, is_estimated, inclusive):
    selling_price = float(selling_price or 0)
    if inclusive:
        net_revenue = selling_price / (1 + rate) if rate > -1 else selling_price
        tax_amount = selling_price - net_revenue
    else:
        net_revenue = selling_price
        tax_amount = selling_price * rate
    return TaxResult(
        region=region,
        sub_region=sub_region or "",
        tax_type=tax_type,
        rate=round(rate, 6),
        rate_pct=_rate_pct(rate),
        tax_amount=_money(tax_amount),
        net_revenue=_money(net_revenue),
        data_source=data_source,
        note=note,
        is_estimated=bool(is_estimated),
    )


def _us_tax(selling_price, sub_region=None, product_type=None):
    state = normalize_sub_region(sub_region)
    is_estimated = False
    note = "US sales tax is added on top; buyer pays it and seller revenue is unchanged."

    if not state or state not in US_STATE_RATES:
        state = state or "US_AVG"
        rate = US_DEFAULT_RATE
        is_estimated = True
        note += " State not specified; using 8.0% average effective rate."
    elif state in US_NO_SALES_TAX_STATES:
        rate = 0.0
        note += f" {state} has no state sales tax; local taxes may still apply."
    else:
        rate = US_STATE_RATES[state]

    if _is_apparel(product_type):
        if state in US_APPAREL_EXEMPT_STATES:
            rate = 0.0
            note += f" Clothing/apparel is treated as exempt in {state}."
        threshold = US_APPAREL_THRESHOLD_EXEMPTIONS.get(state)
        if threshold is not None and float(selling_price or 0) < threshold:
            rate = 0.0
            note += f" Clothing/apparel under ${threshold:.0f} is treated as exempt in {state}."

    return _build_result("US", state, "Sales Tax", rate, selling_price, "Static table", note, is_estimated, inclusive=False)


def _canada_tax(selling_price, province=None):
    province = normalize_sub_region(province)
    is_estimated = False
    if not province or province not in CANADA_RATES:
        province = CANADA_DEFAULT_PROVINCE
        is_estimated = True
    note = "Canada GST/HST/PST is treated as embedded in the listed price for margin estimation."
    if is_estimated:
        note += " Province not specified; using Ontario HST 13% as default."
    return _build_result("CA", province, "GST/HST/PST", CANADA_RATES[province], selling_price, "Static table", note, is_estimated, inclusive=True)


def _uk_tax(selling_price):
    return _build_result("GB", "GB", "VAT", 0.20, selling_price, "Static table", "UK POD products use standard 20% VAT embedded in listed price.", False, inclusive=True)


def _au_tax(selling_price):
    return _build_result("AU", "AU", "GST", 0.10, selling_price, "Static table", "Australia GST is 10% nationally and embedded in listed price.", False, inclusive=True)


def _vn_tax(selling_price, calculation_date=None):
    calculation_date = calculation_date or date.today()
    rate = 0.08 if calculation_date <= date(2026, 12, 31) else 0.10
    note = "Vietnam VAT is treated as embedded in listed price for margin estimation."
    if rate == 0.08:
        note += " Using 8% VAT rate effective through 31/12/2026."
    else:
        note += " Using 10% standard VAT rate from 01/01/2027."
    return _build_result("VN", "VN", "VAT", rate, selling_price, "Static table", note, False, inclusive=True)


def _fetch_eu_vat_rate(country_code):
    response = requests.get(
        f"{VATCOMPLY_BASE_URL}/vat_rates",
        params={"country_code": country_code},
        timeout=VATCOMPLY_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()

    country_payload = payload.get(country_code)
    if not isinstance(country_payload, dict):
        rates_payload = payload.get("rates")
        if isinstance(rates_payload, dict):
            country_payload = rates_payload.get(country_code)

    if not isinstance(country_payload, dict):
        raise ValueError("VATcomply response did not include requested country")

    standard_rate = country_payload.get("standard_rate") or country_payload.get("standard")
    if standard_rate is None:
        raise ValueError("VATcomply response did not include standard_rate")
    return float(standard_rate) / 100


def _eu_tax(selling_price, sub_region=None):
    country_code = normalize_sub_region(sub_region)
    if country_code == "GB":
        return _uk_tax(selling_price)

    if country_code in EU_FALLBACK_RATES:
        try:
            rate = _fetch_eu_vat_rate(country_code)
            return _build_result(
                "EU",
                country_code,
                "VAT",
                rate,
                selling_price,
                "VATcomply API",
                "EU VAT is embedded in the listed price. Rate loaded from VATcomply.",
                False,
                inclusive=True,
            )
        except Exception:
            return _build_result(
                "EU",
                country_code,
                "VAT",
                EU_FALLBACK_RATES[country_code],
                selling_price,
                "Static table",
                "EU VAT is embedded in the listed price. VATcomply failed; using static fallback table.",
                True,
                inclusive=True,
            )

    return _build_result(
        "EU",
        country_code or "EU_ESTIMATE",
        "VAT",
        EU_DEFAULT_RATE,
        selling_price,
        "Static table",
        "EU country not specified; using 21% estimated/default VAT. Provide DE/FR/NL/etc. for a more exact rate.",
        True,
        inclusive=True,
    )


def calculate_tax(selling_price, region, sub_region=None, product_type=None, calculation_date=None):
    region = normalize_region(region)
    sub_region = normalize_sub_region(sub_region)

    if region == "US":
        return _us_tax(selling_price, sub_region, product_type)
    if region in {"GB", "UK"}:
        return _uk_tax(selling_price)
    if region == "CA":
        return _canada_tax(selling_price, sub_region)
    if region == "AU":
        return _au_tax(selling_price)
    if region == "VN":
        return _vn_tax(selling_price, calculation_date=calculation_date)
    if region == "EU" or region in EU_FALLBACK_RATES:
        return _eu_tax(selling_price, sub_region or region)

    return _build_result(
        region or "UNKNOWN",
        sub_region or "",
        "Unknown",
        0.0,
        selling_price,
        "None",
        "No tax rule matched this region; tax was not applied.",
        True,
        inclusive=False,
    )
