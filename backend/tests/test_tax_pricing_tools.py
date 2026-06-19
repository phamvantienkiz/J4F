from app.agent.tools import (
    add_tax_pricing_fields,
    minimum_selling_price_for_margin,
    normalize_country_code,
    tax_region_for_country,
)


def test_normalize_country_code_does_not_confuse_australia_with_us():
    assert normalize_country_code("Australia") == "AU"
    assert normalize_country_code("AU") == "AU"
    assert normalize_country_code("United States") == "US"


def test_tax_region_for_country_maps_eu_countries_to_eu_tax_region():
    assert tax_region_for_country("Germany") == ("EU", "DE")
    assert tax_region_for_country("Netherlands") == ("EU", "NL")


def test_add_tax_pricing_fields_keeps_us_sales_tax_out_of_landed_cost():
    item = {"landed_cost": 50.0, "product_name": "Poster"}

    result = add_tax_pricing_fields(item, 100.0, "US", tax_sub_region="CA")

    assert result["landed_cost"] == 50.0
    assert result["tax_type"] == "Sales Tax"
    assert result["tax_amount"] == 8.68
    assert result["buyer_tax"] == 8.68
    assert result["seller_tax"] == 0.0
    assert result["tax_fee"] == 0.0
    assert result["net_revenue"] == 100.0
    assert result["profit"] == 50.0
    assert result["margin_percent"] == 50.0


def test_add_tax_pricing_fields_embeds_vat_in_seller_revenue():
    item = {"landed_cost": 50.0, "product_name": "T-Shirt"}

    result = add_tax_pricing_fields(item, 120.0, "GB")

    assert result["landed_cost"] == 50.0
    assert result["tax_type"] == "VAT"
    assert result["tax_amount"] == 20.0
    assert result["buyer_tax"] == 0.0
    assert result["seller_tax"] == 20.0
    assert result["tax_fee"] == 20.0
    assert result["net_revenue"] == 100.0
    assert result["profit"] == 50.0
    assert result["margin_percent"] == 50.0


def test_minimum_selling_price_for_margin_handles_sales_tax_vs_vat():
    item = {"landed_cost": 70.0, "payment_processing_fee": 5.0, "product_name": "Poster"}

    assert minimum_selling_price_for_margin(item, 25, "US", tax_sub_region="CA") == 100.0
    assert minimum_selling_price_for_margin(item, 25, "GB") == 120.0
