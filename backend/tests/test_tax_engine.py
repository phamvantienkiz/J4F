from datetime import date

from app.services import tax_engine


def test_us_sales_tax_is_buyer_paid_and_not_embedded():
    result = tax_engine.calculate_tax(100, "US", "CA", product_type="poster")

    assert result.region == "US"
    assert result.sub_region == "CA"
    assert result.tax_type == "Sales Tax"
    assert result.rate == 0.0868
    assert result.tax_amount == 8.68
    assert result.net_revenue == 100.0
    assert result.is_estimated is False


def test_vietnam_vat_uses_8_percent_through_2026():
    result = tax_engine.calculate_tax(108, "VN", calculation_date=date(2026, 6, 18))

    assert result.tax_type == "VAT"
    assert result.rate == 0.08
    assert result.tax_amount == 8.0
    assert result.net_revenue == 100.0


def test_uk_canada_and_australia_tax_are_inclusive():
    uk = tax_engine.calculate_tax(120, "GB")
    canada = tax_engine.calculate_tax(113, "CA", "ON")
    australia = tax_engine.calculate_tax(110, "AU")

    assert uk.tax_amount == 20.0
    assert uk.net_revenue == 100.0
    assert canada.tax_amount == 13.0
    assert canada.net_revenue == 100.0
    assert australia.tax_amount == 10.0
    assert australia.net_revenue == 100.0


def test_eu_vat_falls_back_when_live_api_fails(monkeypatch):
    def fail_fetch(country_code):
        raise RuntimeError(f"No live VAT rate for {country_code}")

    monkeypatch.setattr(tax_engine, "_fetch_eu_vat_rate", fail_fetch)

    result = tax_engine.calculate_tax(119, "EU", "DE")

    assert result.region == "EU"
    assert result.sub_region == "DE"
    assert result.rate == 0.19
    assert result.tax_amount == 19.0
    assert result.net_revenue == 100.0
    assert result.data_source == "Static table"
    assert result.is_estimated is True


def test_unknown_region_does_not_crash_or_apply_tax():
    result = tax_engine.calculate_tax(50, "XX")

    assert result.tax_type == "Unknown"
    assert result.tax_amount == 0.0
    assert result.net_revenue == 50.0
    assert result.is_estimated is True
