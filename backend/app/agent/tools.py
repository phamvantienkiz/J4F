from sqlmodel import Session, select
import app.database as db
from app.models.catalog import Product, ProductVariant, ShippingZone, ShippingFee
from app.services.burgerprints import BurgerPrintsClient
from app.services.tax_engine import calculate_tax
from typing import List, Dict, Any, Optional
import math
import logging
import re
import datetime

logger = logging.getLogger(__name__)

EU_TAX_COUNTRY_CODES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR",
    "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
}

COUNTRY_CODE_ALIASES = {
    "US": "US",
    "USA": "US",
    "UNITED STATES": "US",
    "UNITED STATES OF AMERICA": "US",
    "AMERICA": "US",
    "MỸ": "US",
    "MY": "US",
    "DE": "DE",
    "GERMANY": "DE",
    "DEUTSCHLAND": "DE",
    "ĐỨC": "DE",
    "DUC": "DE",
    "FR": "FR",
    "FRANCE": "FR",
    "PHÁP": "FR",
    "PHAP": "FR",
    "GB": "GB",
    "UK": "GB",
    "UNITED KINGDOM": "GB",
    "GREAT BRITAIN": "GB",
    "ENGLAND": "GB",
    "ANH": "GB",
    "VN": "VN",
    "VIETNAM": "VN",
    "VIET NAM": "VN",
    "VIỆT NAM": "VN",
    "VIỆT": "VN",
    "CA": "CA",
    "CANADA": "CA",
    "AU": "AU",
    "AUS": "AU",
    "AUSTRALIA": "AU",
    "ÚC": "AU",
    "UC": "AU",
    "EU": "EU",
    "EUROPE": "EU",
    "EUROPEAN UNION": "EU",
    "NL": "NL",
    "NETHERLANDS": "NL",
    "HOLLAND": "NL",
    "ES": "ES",
    "SPAIN": "ES",
    "IT": "IT",
    "ITALY": "IT",
    "PL": "PL",
    "POLAND": "PL",
}


def normalize_country_code(country: str | None) -> str:
    raw = str(country or "US").strip()
    if not raw:
        return "US"

    country_code = re.sub(r"[\s_-]+", " ", raw.upper()).strip()
    if country_code in COUNTRY_CODE_ALIASES:
        return COUNTRY_CODE_ALIASES[country_code]

    tokens = set(re.findall(r"[A-ZÀ-Ỹ]+", country_code))
    if {"UNITED", "STATES"}.issubset(tokens):
        return "US"
    if {"UNITED", "KINGDOM"}.issubset(tokens):
        return "GB"
    if "VIET" in tokens or "VIỆT" in tokens:
        return "VN"
    if "EU" in tokens or "EUROPE" in tokens:
        return "EU"

    return country_code


def tax_region_for_country(country_code: str) -> tuple[str, str | None]:
    country_code = normalize_country_code(country_code)
    if country_code in EU_TAX_COUNTRY_CODES:
        return "EU", country_code
    return country_code, None


def get_tax_rate(country_code: str) -> float:
    """Backward-compatible helper: returns the configured destination tax rate."""
    tax_region, tax_sub_region = tax_region_for_country(country_code)
    return calculate_tax(1.0, tax_region, tax_sub_region).rate


def add_tax_pricing_fields(
    item: Dict[str, Any],
    selling_price: Optional[float],
    country_code: str,
    tax_sub_region: Optional[str] = None,
    product_type: Optional[str] = None,
    quantity: int = 1,
) -> Dict[str, Any]:
    if selling_price is None:
        return item

    quantity = max(1, int(quantity or item.get("quantity") or 1))
    total_selling_price = float(selling_price) * quantity
    tax_region, default_sub_region = tax_region_for_country(country_code)
    tax_result = calculate_tax(
        total_selling_price,
        tax_region,
        tax_sub_region or default_sub_region,
        product_type or item.get("product_name") or item.get("display_name"),
    )

    fulfillment_cost = float(item.get("landed_cost") or 0.0)
    platform_fee = float(item.get("payment_processing_fee") or 0.0)
    total_cost = fulfillment_cost + platform_fee
    profit = tax_result.net_revenue - total_cost
    margin_percent = (profit / tax_result.net_revenue) * 100 if tax_result.net_revenue else 0.0

    item.update({
        "selling_price": round(float(selling_price), 2),
        "total_selling_price": round(total_selling_price, 2),
        "net_revenue": round(tax_result.net_revenue, 2),
        "profit": round(profit, 2),
        "margin_percent": round(margin_percent, 2),
        "tax_region": tax_result.region,
        "tax_sub_region": tax_result.sub_region,
        "tax_type": tax_result.tax_type,
        "tax_rate": tax_result.rate,
        "tax_rate_pct": tax_result.rate_pct,
        "tax_amount": tax_result.tax_amount,
        "buyer_tax": tax_result.tax_amount if tax_result.tax_type == "Sales Tax" else 0.0,
        "seller_tax": 0.0 if tax_result.tax_type == "Sales Tax" else tax_result.tax_amount,
        "tax_fee": 0.0 if tax_result.tax_type == "Sales Tax" else tax_result.tax_amount,
        "tax_data_source": tax_result.data_source,
        "tax_note": tax_result.note,
        "tax_is_estimated": tax_result.is_estimated,
    })
    return item


def minimum_selling_price_for_margin(
    item: Dict[str, Any],
    min_margin: float,
    country_code: str,
    tax_sub_region: Optional[str] = None,
    product_type: Optional[str] = None,
) -> float:
    target_margin = max(0.0, min(float(min_margin or 0.0) / 100, 0.99))
    fulfillment_cost = float(item.get("landed_cost") or 0.0)
    platform_fee = float(item.get("payment_processing_fee") or 0.0)
    total_cost = fulfillment_cost + platform_fee
    net_required = total_cost / (1 - target_margin) if target_margin < 1 else total_cost
    tax_region, default_sub_region = tax_region_for_country(country_code)
    sample_tax = calculate_tax(1.0, tax_region, tax_sub_region or default_sub_region, product_type or item.get("product_name"))
    if sample_tax.tax_type == "Sales Tax":
        return round(net_required, 2)
    return round(net_required * (1 + sample_tax.rate), 2)

def mask_pii(text: str) -> str:
    """
    Che giấu thông tin cá nhân nhạy cảm trong phản hồi chatbot.
    """
    if not text:
        return ""
    # Che giấu số điện thoại
    text = re.sub(r'\b\d{7,11}\b', lambda m: m.group(0)[:3] + "****" + m.group(0)[-2:], text)
    # Che giấu email
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                  lambda m: m.group(0)[0] + "***@" + m.group(0).split('@')[1], text)
    return text

def _diversify_results(results: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Đa dạng hóa danh sách kết quả theo xưởng sản xuất (partner_name) bằng Round Robin,
    trong đó các xưởng được ưu tiên duyệt theo giá landed_cost tốt nhất của họ tăng dần.
    Sau đó sắp xếp lại toàn bộ kết quả được chọn theo landed_cost tăng dần.
    """
    if not results:
        return []

    # Gom nhóm theo partner_name
    groups = {}
    for item in results:
        partner = item.get("partner_name") or "BurgerPrints"
        if partner not in groups:
            groups[partner] = []
        groups[partner].append(item)

    # Sắp xếp các item trong mỗi nhóm theo landed_cost tăng dần
    for partner in groups:
        groups[partner].sort(key=lambda x: x["landed_cost"])

    # Sắp xếp các partner theo landed_cost nhỏ nhất của họ tăng dần
    sorted_partners = sorted(groups.keys(), key=lambda p: groups[p][0]["landed_cost"])

    diversified = []
    max_len = max(len(lst) for lst in groups.values()) if groups else 0

    # Lấy xen kẽ theo Round Robin
    for i in range(max_len):
        for partner in sorted_partners:
            if i < len(groups[partner]):
                diversified.append(groups[partner][i])
                if len(diversified) >= limit:
                    break
        if len(diversified) >= limit:
            break

    # Sắp xếp lại danh sách kết quả cuối cùng theo landed_cost tăng dần
    diversified.sort(key=lambda x: x["landed_cost"])
    return diversified

def search_products_tool(
    product_type: str,
    country: str,
    max_base_cost: Optional[float] = None,
    max_shipping_days: Optional[int] = None,
    print_sides: str = "front"
) -> List[Dict[str, Any]]:
    """
    Tìm kiếm và đề xuất các biến thể phù hợp nhất.
    Có chế độ "lựa chọn thay thế gần nhất" (nearest alternative mode) nếu không có SKU nào khớp 100%.
    """
    country_code = normalize_country_code(country)

    with Session(db.engine) as session:
        # Tìm các sản phẩm khớp với loại sản phẩm
        stmt = select(Product)
        if product_type:
            stmt = stmt.where(Product.category.ilike(f"%{product_type}%") | Product.name.ilike(f"%{product_type}%"))
        products = session.exec(stmt).all()

        if not products:
            # Nếu không tìm thấy, thử tìm kiếm rộng hơn
            products = session.exec(select(Product)).all()

        product_ids = [p.id for p in products]

        # Lấy tất cả các variant của các sản phẩm này
        variants = session.exec(select(ProductVariant).where(ProductVariant.product_id.in_(product_ids))).all()

        # Lọc các variant phù hợp với thị trường đích (EU) nếu country_code thuộc EU
        is_eu_market = country_code in ["DE", "FR", "EU"]
        if is_eu_market:
            variants = [v for v in variants if v.location_name == "EU" or (v.shipping_cost_ww is not None and v.shipping_cost_ww > 0)]

        # Lấy thông tin vận chuyển cho quốc gia này
        zone = session.exec(select(ShippingZone).where(ShippingZone.country_code == country_code)).first()

        fees = []
        if zone:
            fees = session.exec(select(ShippingFee).where(ShippingFee.zone_id == zone.id)).all()

        # Chọn phương thức vận chuyển tiêu chuẩn làm mặc định
        std_fee = None
        for fee in fees:
            if "standard" in fee.carrier.lower() or "giao hàng nhanh" in fee.carrier.lower():
                std_fee = fee
                break
        if not std_fee and fees:
            std_fee = fees[0]

        all_results = []
        matched_results = []

        for var in variants:
            # Phí ship từ variant hoặc từ zone fee
            if std_fee:
                shipping_cost = std_fee.first_item_fee
                shipping_adding = std_fee.additional_item_fee
                carrier_name = std_fee.carrier
                del_time = std_fee.delivery_time or "3-5 business days"
            else:
                if country_code == "US":
                    shipping_cost = var.shipping_cost_us
                    shipping_adding = var.shipping_adding_us
                    carrier_name = "Standard Shipping"
                    del_time = "3-5 business days"
                else:
                    shipping_cost = var.shipping_cost_ww
                    shipping_adding = var.shipping_adding_ww
                    carrier_name = "Worldwide Shipping"
                    if is_eu_market and var.location_name == "EU":
                        del_time = "3-5 business days"
                    else:
                        del_time = "7-10 business days" if country_code != "US" else "3-5 business days"

            # Trích xuất số ngày từ chuỗi delivery_time để so khớp
            shipping_days = 5
            try:
                days_parts = del_time.replace("business", "").replace("days", "").strip().split("-")
                if len(days_parts) >= 2:
                    shipping_days = int(days_parts[1].strip())
                elif len(days_parts) == 1:
                    shipping_days = int(days_parts[0].strip())
            except Exception:
                pass

            # Tính base cost dựa vào tùy chọn in
            base_cost_value = var.base_cost
            if print_sides == "both":
                second_cost = var.second_item_price if var.second_item_price is not None else var.clone_price
                base_cost_value += second_cost

            # Không tính thuế khi chưa có selling_price; tax engine sẽ tính từ giá bán.
            tax_rate = 0.0
            tax_fee = 0.0

            # Fulfillment landed cost = Base/print cost + Shipping. Tax hiển thị riêng khi có giá bán.
            landed_cost = base_cost_value + shipping_cost

            prod = next((p for p in products if p.id == var.product_id), None)
            prod_name = prod.name if prod else "Product"

            item_data = {
                "sku": var.sku,
                "product_name": prod_name,
                "display_name": f"{prod_name} ({var.color} / {var.size})",
                "color": var.color,
                "size": var.size,
                "partner_name": var.partner_name or "BurgerPrints",
                "location_name": var.location_name or "US",
                "base_cost": round(var.base_cost, 2),
                "second_item_price": round(var.second_item_price, 2),
                "shipping_fee": round(shipping_cost, 2),
                "tax_fee": round(tax_fee, 2),
                "tax_rate": tax_rate,
                "landed_cost": round(landed_cost, 2),
                "delivery_time": del_time,
                "carrier": [carrier_name],
                "mockup_url": var.mockup_url,
                "print_sides": print_sides,
                "filter_match": "exact",
                "filter_excess": {}
            }

            all_results.append(item_data)

            # Kiểm tra bộ lọc
            is_match = True
            excess = {}

            if max_base_cost is not None and base_cost_value > max_base_cost:
                is_match = False
                excess["base_cost"] = round(base_cost_value - max_base_cost, 2)

            if max_shipping_days is not None and shipping_days > max_shipping_days:
                is_match = False
                excess["shipping_days"] = shipping_days - max_shipping_days

            if is_match:
                matched_results.append(item_data)
            else:
                item_data_copy = item_data.copy()
                item_data_copy["filter_match"] = "nearest_alternative"
                item_data_copy["filter_excess"] = excess
                # Ghi nhận vào danh sách thay thế
                all_results[-1] = item_data_copy

        # Sắp xếp
        matched_results.sort(key=lambda x: x["landed_cost"])
        all_results.sort(key=lambda x: x["landed_cost"])

        # Áp dụng đa dạng hóa xưởng sản xuất
        diversified_matched = _diversify_results(matched_results, limit=10)
        diversified_all = _diversify_results(all_results, limit=10)

        # Nếu có kết quả khớp 100%, trả về
        if diversified_matched:
            return diversified_matched

        # Nếu không có kết quả khớp, áp dụng Nearest Alternative Mode
        # Trả về các lựa chọn thay thế gần nhất
        logger.info("Chế độ Nearest Alternative được kích hoạt do không có kết quả khớp hoàn toàn.")
        return diversified_all


def compare_shipping_tool(product_type: str, country: str, print_sides: str = "front") -> List[Dict[str, Any]]:
    """
    So sánh phí vận chuyển và thời gian vận chuyển của các xưởng đến một quốc gia cụ thể.
    """
    country_code = normalize_country_code(country)

    with Session(db.engine) as session:
        # Lấy thông tin Shipping Zone và Fee
        zone = session.exec(select(ShippingZone).where(ShippingZone.country_code == country_code)).first()

        fees = []
        if zone:
            fees = session.exec(select(ShippingFee).where(ShippingFee.zone_id == zone.id)).all()

        # Lấy danh sách variants để so sánh xưởng
        stmt = select(Product)
        if product_type:
            stmt = stmt.where(Product.category.ilike(f"%{product_type}%") | Product.name.ilike(f"%{product_type}%"))
        products = session.exec(stmt).all()

        product_ids = [p.id for p in products] if products else []
        variants = []
        if product_ids:
            variants = session.exec(select(ProductVariant).where(ProductVariant.product_id.in_(product_ids))).all()

        is_eu_market = country_code in ["DE", "FR", "EU"]
        if is_eu_market:
            variants = [v for v in variants if v.location_name == "EU" or (v.shipping_cost_ww is not None and v.shipping_cost_ww > 0)]

        # Gom nhóm theo xưởng để so sánh
        partners = {}
        for var in variants:
            partner_name = var.partner_name or "BurgerPrints"
            location_name = var.location_name or "US"

            # Tính toán base cost thực tế dựa trên số mặt in
            base_cost_value = var.base_cost
            if print_sides == "both":
                second_cost = var.second_item_price if var.second_item_price is not None else var.clone_price
                base_cost_value += second_cost

            if partner_name not in partners:
                partners[partner_name] = {
                    "partner_name": partner_name,
                    "location_name": location_name,
                    "min_base_cost": base_cost_value,
                    "second_item_price": var.second_item_price,
                    "clone_price": var.clone_price,
                    "shipping_cost_us": var.shipping_cost_us,
                    "shipping_adding_us": var.shipping_adding_us,
                    "shipping_cost_ww": var.shipping_cost_ww,
                    "shipping_adding_ww": var.shipping_adding_ww,
                    "color": var.color or "Default",
                    "size": var.size or "OS",
                    "sku": var.sku
                }
            else:
                if base_cost_value < partners[partner_name]["min_base_cost"]:
                    partners[partner_name]["min_base_cost"] = base_cost_value
                    partners[partner_name]["color"] = var.color or "Default"
                    partners[partner_name]["size"] = var.size or "OS"
                    partners[partner_name]["sku"] = var.sku

        compare_results = []
        for partner_name, p_info in partners.items():
            if fees:
                for fee in fees:
                    shipping_fee = fee.first_item_fee
                    second_item_price = fee.additional_item_fee
                    carrier_name = fee.carrier
                    del_time = fee.delivery_time or "3-5 business days"

                    tax_rate = 0.0
                    min_landed_cost = p_info["min_base_cost"] + shipping_fee

                    compare_results.append({
                        "partner_name": partner_name,
                        "location_name": p_info["location_name"],
                        "carrier": carrier_name,
                        "base_cost": round(p_info["min_base_cost"], 2),
                        "shipping_fee": round(shipping_fee, 2),
                        "second_item_price": round(p_info["second_item_price"], 2) if p_info["second_item_price"] is not None else round(p_info["clone_price"], 2),
                        "tax_fee": 0.0,
                        "landed_cost": round(min_landed_cost, 2),
                        "delivery_time": del_time,
                        "color": p_info["color"],
                        "size": p_info["size"],
                        "sku": p_info["sku"]
                    })
            else:
                shipping_fee = p_info["shipping_cost_us"] if country_code == "US" else p_info["shipping_cost_ww"]
                second_item_price = p_info["shipping_adding_us"] if country_code == "US" else p_info["shipping_adding_ww"]
                carrier_name = "Worldwide Shipping" if country_code != "US" else "Standard Shipping"
                if is_eu_market and p_info["location_name"] == "EU":
                    del_time = "3-5 business days"
                else:
                    del_time = "7-10 business days" if country_code != "US" else "3-5 business days"

                tax_rate = 0.0
                min_landed_cost = p_info["min_base_cost"] + shipping_fee

                compare_results.append({
                    "partner_name": partner_name,
                    "location_name": p_info["location_name"],
                    "carrier": carrier_name,
                    "base_cost": round(p_info["min_base_cost"], 2),
                    "shipping_fee": round(shipping_fee, 2),
                    "second_item_price": round(p_info["second_item_price"], 2) if p_info["second_item_price"] is not None else round(p_info["clone_price"], 2),
                    "tax_fee": 0.0,
                    "landed_cost": round(min_landed_cost, 2),
                    "delivery_time": del_time,
                    "color": p_info["color"],
                    "size": p_info["size"],
                    "sku": p_info["sku"]
                })

        # Sắp xếp theo landed cost tăng dần
        compare_results.sort(key=lambda x: x["landed_cost"])
        return compare_results


def calculate_landed_cost_tool(
    sku: str,
    country: str,
    quantity: int = 1,
    selling_price: Optional[float] = None,
    print_sides: str = "front",
    tax_sub_region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tính toán landed cost chi tiết cho 1 SKU cụ thể và tính toán Margin / Profit nếu có giá bán.
    """
    country_code = normalize_country_code(country)

    with Session(db.engine) as session:
        # Tìm variant bằng SKU
        variant = session.exec(select(ProductVariant).where(ProductVariant.sku == sku)).first()
        if not variant:
            return {"error": f"Không tìm thấy biến thể với SKU: {sku}"}

        product = session.exec(select(Product).where(Product.id == variant.product_id)).first()
        product_name = product.name if product else "Product"

        # Lấy thông tin Shipping
        zone = session.exec(select(ShippingZone).where(ShippingZone.country_code == country_code)).first()

        fees = []
        if zone:
            fees = session.exec(select(ShippingFee).where(ShippingFee.zone_id == zone.id)).all()

        # Chọn standard shipping làm mặc định
        std_fee = None
        for fee in fees:
            if "standard" in fee.carrier.lower() or "giao hàng nhanh" in fee.carrier.lower():
                std_fee = fee
                break
        if not std_fee and fees:
            std_fee = fees[0]

        # Công thức tính phí ship: first_item_fee + (quantity - 1) * additional_item_fee
        is_eu_market = country_code in ["DE", "FR", "EU"]
        if std_fee:
            shipping_fee = std_fee.first_item_fee + (quantity - 1) * std_fee.additional_item_fee
            carrier_name = std_fee.carrier
            delivery_time = std_fee.delivery_time
        else:
            first_cost = variant.shipping_cost_us if country_code == "US" else variant.shipping_cost_ww
            adding_cost = variant.shipping_adding_us if country_code == "US" else variant.shipping_adding_ww
            shipping_fee = first_cost + (quantity - 1) * adding_cost
            carrier_name = "Worldwide Shipping" if country_code != "US" else "Standard Shipping"
            if is_eu_market and variant.location_name == "EU":
                delivery_time = "3-5 business days"
            else:
                delivery_time = "7-10 business days" if country_code != "US" else "3-5 business days"

        # Tính base cost dựa vào tùy chọn in
        base_cost_value = variant.base_cost
        if print_sides == "both":
            second_cost = variant.second_item_price if variant.second_item_price is not None else variant.clone_price
            base_cost_value += second_cost

        total_base = base_cost_value * quantity
        tax_rate = 0.0
        tax_fee = 0.0

        # Fulfillment landed cost = Total Base + Shipping. Tax is calculated from selling price below.
        landed_cost = total_base + shipping_fee

        result = {
            "sku": variant.sku,
            "product_name": product_name,
            "display_name": f"{product_name} ({variant.color} / {variant.size})",
            "color": variant.color,
            "size": variant.size,
            "partner_name": variant.partner_name or "BurgerPrints",
            "location_name": variant.location_name or "US",
            "quantity": quantity,
            "base_cost": round(variant.base_cost, 2),
            "total_base_cost": round(total_base, 2),
            "second_item_price": round(variant.second_item_price, 2),
            "clone_price": round(variant.clone_price, 2),
            "shipping_fee": round(shipping_fee, 2),
            "tax_fee": round(tax_fee, 2),
            "tax_rate": tax_rate,
            "landed_cost": round(landed_cost, 2),
            "delivery_time": delivery_time,
            "carrier": [carrier_name],
            "mockup_url": variant.mockup_url,
            "print_sides": print_sides
        }

        # Nếu có giá bán, tính tax-adjusted Profit và Margin
        if selling_price is not None:
            add_tax_pricing_fields(result, selling_price, country_code, tax_sub_region, product_name, quantity=quantity)

        return result


async def create_draft_order_tool(
    sku: str,
    quantity: int,
    country: str,
    full_name: str,
    address1: str,
    city: str,
    zip_code: str,
    print_sides: str = "front"
) -> Dict[str, Any]:
    """
    Tạo đơn hàng nháp qua BurgerPrints API v2.0
    """
    client = BurgerPrintsClient()

    # Dựng cấu trúc dữ liệu đơn hàng
    order_data = {
        "shipping_name": full_name,
        "shipping_address1": address1,
        "shipping_city": city,
        "shipping_zip": zip_code,
        "shipping_country": country.upper(),
        "reference_order_id": f"REF-{sku}-{int(datetime.datetime.now().timestamp())}",
        "items": [
            {
                "catalog_sku": sku,
                "quantity": quantity,
                "print_sides": print_sides
            }
        ]
    }

    # Gọi API tạo đơn hàng
    result = await client.create_order(order_data)
    return result
