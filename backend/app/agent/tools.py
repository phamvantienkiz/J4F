from sqlmodel import Session, select
import app.database as db
from app.models.catalog import Product, ProductVariant, ShippingZone, ShippingFee
from app.services.burgerprints import BurgerPrintsClient
from typing import List, Dict, Any, Optional
import math
import logging
import re
import datetime

logger = logging.getLogger(__name__)

def get_tax_rate(country_code: str) -> float:
    """
    Trả về thuế suất giả định dựa trên quốc gia để tính landed cost.
    - US: 8% (Sales tax trung bình)
    - EU (DE, FR, GB): 19% (VAT trung bình)
    - VN: 0% (Không tính thuế nội địa)
    """
    c = country_code.upper()
    if c == "US":
        return 0.08
    elif c in ["DE", "FR", "GB", "EU"]:
        return 0.19
    return 0.0

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
    country_code = country.upper() if country else "US"
    # Chuẩn hóa tên quốc gia thành mã code
    if "MỸ" in country_code or "US" in country_code or "STATE" in country_code:
        country_code = "US"
    elif "ĐỨC" in country_code or "DE" in country_code or "GERMANY" in country_code:
        country_code = "DE"
    elif "PHÁP" in country_code or "FR" in country_code or "FRANCE" in country_code:
        country_code = "FR"
    elif "ANH" in country_code or "GB" in country_code or "UK" in country_code or "KINGDOM" in country_code:
        country_code = "GB"
    elif "VIỆT" in country_code or "VN" in country_code:
        country_code = "VN"

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

            # Tính thuế
            tax_rate = get_tax_rate(country_code)
            tax_fee = base_cost_value * tax_rate

            # Tính Landed Cost = Base Cost + Shipping + Tax
            landed_cost = base_cost_value + shipping_cost + tax_fee

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
    country_code = country.upper() if country else "US"
    if "MỸ" in country_code or "US" in country_code or "STATE" in country_code:
        country_code = "US"
    elif "ĐỨC" in country_code or "DE" in country_code or "GERMANY" in country_code:
        country_code = "DE"
    elif "PHÁP" in country_code or "FR" in country_code or "FRANCE" in country_code:
        country_code = "FR"
    elif "ANH" in country_code or "GB" in country_code or "UK" in country_code or "KINGDOM" in country_code:
        country_code = "GB"
    elif "VIỆT" in country_code or "VN" in country_code:
        country_code = "VN"

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

                    tax_rate = get_tax_rate(country_code)
                    min_landed_cost = p_info["min_base_cost"] + shipping_fee + (p_info["min_base_cost"] * tax_rate)

                    compare_results.append({
                        "partner_name": partner_name,
                        "location_name": p_info["location_name"],
                        "carrier": carrier_name,
                        "base_cost": round(p_info["min_base_cost"], 2),
                        "shipping_fee": round(shipping_fee, 2),
                        "second_item_price": round(p_info["second_item_price"], 2) if p_info["second_item_price"] is not None else round(p_info["clone_price"], 2),
                        "tax_fee": round(p_info["min_base_cost"] * tax_rate, 2),
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

                tax_rate = get_tax_rate(country_code)
                min_landed_cost = p_info["min_base_cost"] + shipping_fee + (p_info["min_base_cost"] * tax_rate)

                compare_results.append({
                    "partner_name": partner_name,
                    "location_name": p_info["location_name"],
                    "carrier": carrier_name,
                    "base_cost": round(p_info["min_base_cost"], 2),
                    "shipping_fee": round(shipping_fee, 2),
                    "second_item_price": round(p_info["second_item_price"], 2) if p_info["second_item_price"] is not None else round(p_info["clone_price"], 2),
                    "tax_fee": round(p_info["min_base_cost"] * tax_rate, 2),
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
    print_sides: str = "front"
) -> Dict[str, Any]:
    """
    Tính toán landed cost chi tiết cho 1 SKU cụ thể và tính toán Margin / Profit nếu có giá bán.
    """
    country_code = country.upper() if country else "US"
    if "MỸ" in country_code or "US" in country_code or "STATE" in country_code:
        country_code = "US"
    elif "ĐỨC" in country_code or "DE" in country_code or "GERMANY" in country_code:
        country_code = "DE"
    elif "PHÁP" in country_code or "FR" in country_code or "FRANCE" in country_code:
        country_code = "FR"
    elif "ANH" in country_code or "GB" in country_code or "UK" in country_code or "KINGDOM" in country_code:
        country_code = "GB"
    elif "VIỆT" in country_code or "VN" in country_code:
        country_code = "VN"

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

        # Thuế
        tax_rate = get_tax_rate(country_code)
        total_base = base_cost_value * quantity
        tax_fee = total_base * tax_rate

        # Landed cost = Total Base + Shipping + Tax
        landed_cost = total_base + shipping_fee + tax_fee

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

        # Nếu có giá bán, tính Profit và Margin
        if selling_price is not None:
            total_selling_price = selling_price * quantity
            profit = total_selling_price - landed_cost
            margin_percent = (profit / total_selling_price) * 100 if total_selling_price > 0 else 0

            result["selling_price"] = round(selling_price, 2)
            result["total_selling_price"] = round(total_selling_price, 2)
            result["profit"] = round(profit, 2)
            result["margin_percent"] = round(margin_percent, 2)

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
