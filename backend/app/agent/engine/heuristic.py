import datetime
from sqlmodel import Session
import app.database as db
from app.config import settings
from app.agent.tools import (
    search_products_tool,
    compare_shipping_tool,
    calculate_landed_cost_tool,
    create_draft_order_tool
)

ACTIVE_MARKETS = ["US", "EU", "VN", "AU", "NZ", "ZA"]
SHIPPING_SYNC_TECHNICAL_NOTE = "Hệ thống phát hiện DB thiếu dữ liệu Shipping Fee từ BurgerPrints API. Vui lòng kiểm tra hoặc kéo thêm dữ liệu từ endpoint /shipping/."


def _base_response() -> dict:
    return {
        "answer": "",
        "items": [],
        "tool_data": None,
        "is_nearest": False,
        "clarification_required": False,
        "missing_field": None,
        "question": None,
        "confirmation_required": False,
        "status": None,
        "order_id": None,
        "metadata": {},
        "margin_alert": False
    }


def _payload_has_api_sync_required(payload) -> bool:
    if isinstance(payload, dict):
        if payload.get("api_sync_required") is True:
            return True
        return any(_payload_has_api_sync_required(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_payload_has_api_sync_required(item) for item in payload)
    return False


def _apply_api_sync_metadata(res: dict) -> None:
    if _payload_has_api_sync_required(res.get("items")) or _payload_has_api_sync_required(res.get("tool_data")):
        res["metadata"]["api_sync_required"] = True
        res["metadata"]["technical_note"] = SHIPPING_SYNC_TECHNICAL_NOTE


def _apply_margin(items: list[dict], selling_price, min_margin) -> bool:
    if selling_price is not None:
        valid_items = []
        for item in items:
            item["selling_price"] = selling_price
            item["profit"] = round(selling_price - item["landed_cost"], 2)
            margin_percent = round((item["profit"] / selling_price) * 100, 2)
            item["margin_percent"] = margin_percent

            # Lọc sister variants
            if "variants" in item and isinstance(item["variants"], list):
                valid_variants = []
                for var in item["variants"]:
                    var["selling_price"] = selling_price
                    var["profit"] = round(selling_price - var["landed_cost"], 2)
                    var_margin = round((var["profit"] / selling_price) * 100, 2)
                    var["margin_percent"] = var_margin
                    if var_margin >= 45.0:
                        valid_variants.append(var)
                item["variants"] = valid_variants

            # Chỉ giữ lại sản phẩm nếu margin sản phẩm chính >= 45.0%
            if margin_percent >= 45.0:
                valid_items.append(item)

        items.clear()
        items.extend(valid_items)
        items.sort(key=lambda x: x["profit"], reverse=True)
        return False

    if min_margin is not None and min_margin < 100:
        valid_items = []
        for item in items:
            landed_cost = item["landed_cost"]
            suggested_price = round(landed_cost / (1 - min_margin / 100), 2)
            item["selling_price"] = suggested_price
            item["profit"] = round(suggested_price - landed_cost, 2)
            margin_percent = round((item["profit"] / suggested_price) * 100, 2)
            item["margin_percent"] = margin_percent

            # Lọc sister variants
            if "variants" in item and isinstance(item["variants"], list):
                valid_variants = []
                for var in item["variants"]:
                    var_landed = var["landed_cost"]
                    var_suggested = round(var_landed / (1 - min_margin / 100), 2)
                    var["selling_price"] = var_suggested
                    var["profit"] = round(var_suggested - var_landed, 2)
                    var_margin = round((var["profit"] / var_suggested) * 100, 2)
                    var["margin_percent"] = var_margin
                    if var_margin >= 45.0:
                        valid_variants.append(var)
                item["variants"] = valid_variants

            if margin_percent >= 45.0:
                valid_items.append(item)

        items.clear()
        items.extend(valid_items)
        items.sort(key=lambda x: x["landed_cost"])
        return True

    items.sort(key=lambda x: x["landed_cost"])
    return False


async def execute_heuristic_flow(engine, intent: str, slots: dict, message: str, lang: str, country_code: str, history: list = None) -> dict:
    product_type = slots.get("product_type")
    max_base_cost = slots.get("max_base_cost")
    max_shipping_days = slots.get("max_shipping_days")
    selling_price = slots.get("selling_price")
    min_margin = slots.get("min_margin")
    sku = slots.get("sku")
    quantity = slots.get("quantity", 1)
    shipping_address = slots.get("shipping_address")
    shipping_carrier = slots.get("shipping_carrier")
    print_sides = slots.get("print_sides", "front")

    user_messages = []
    if history:
        for msg in history:
            if msg.get("role") == "user":
                user_messages.append(msg.get("content", ""))
    if message and (not user_messages or user_messages[-1] != message):
        user_messages.append(message)

    # Cô lập lịch sử tin nhắn khi có sự chuyển đổi phân khúc sản phẩm hoặc đối tượng nhân khẩu học
    from app.agent.engine.intent import get_message_domain, get_slots_domain, get_message_demographic, get_slots_demographic, is_pure_pricing_adjustment_fn
    is_pure_adjustment = is_pure_pricing_adjustment_fn(message)

    if is_pure_adjustment:
        # Pure pricing adjustments must keep the active product context.
        combined_query = slots.get("product_type") or message
    else:
        msg_domain = get_message_domain(message)
        slots_domain = get_slots_domain(slots)
        msg_demo = get_message_demographic(message)
        slots_demo = get_slots_demographic(slots)

        is_domain_switch = (msg_domain is not None and slots_domain is not None and msg_domain != slots_domain)
        is_demo_switch = (msg_demo is not None and slots_demo is not None and msg_demo != slots_demo)
        explicit_keep = any(w in message.lower() for w in ["giữ nguyên", "giu nguyen", "keep target", "keep market", "keep margin", "như cũ", "nhu cu", "giữ lại", "giu lai"])

        if (is_domain_switch or is_demo_switch) and not explicit_keep:
            combined_query = message
        else:
            combined_query = " ".join(user_messages) if user_messages else message

    res = _base_response()
    res["metadata"] = {
        "intent": intent,
        "country": country_code,
        "target_market": slots.get("target_market"),
        "product_type": product_type,
        "print_sides": print_sides,
        "language": lang
    }

    if intent == "recommend" and not product_type:
        res["clarification_required"] = True
        res["missing_field"] = "product_type"
        res["metadata"]["required_slots"] = ["product_type"]
        res["tool_data"] = {"slots": slots, "missing_field": "product_type"}
        return res

    if intent == "recommend":
        if not product_type:
            req_month = slots.get("month") or datetime.datetime.now().month
            with Session(db.engine) as db_sess:
                suggestions = engine.trend_service.get_seasonal_suggestions(db_sess, country_code, req_month)

            recommended_items = []
            for suggested_product_type in suggestions.product_types[:2]:
                recommended_items.extend(search_products_tool(
                    product_type=suggested_product_type,
                    country=suggestions.country,
                    max_base_cost=max_base_cost,
                    max_shipping_days=max_shipping_days,
                    print_sides=print_sides,
                    query=combined_query
                ))

            res["answer"] = f"Dưới đây là một số sản phẩm gợi ý theo mùa cho bạn tại {country_code}:" if lang == "vi" else f"Here are some seasonal product suggestions for you in {country_code}:"
            res["items"] = recommended_items
            res["tool_data"] = {
                "seasonal_context": suggestions.model_dump(),
                "items": recommended_items
            }
            res["is_nearest"] = any(item.get("filter_match") == "nearest_alternative" for item in recommended_items)
            res["margin_alert"] = _apply_margin(recommended_items, selling_price, min_margin)
            res["metadata"].update({
                "resolved_country": suggestions.country,
                "original_country": suggestions.original_country,
                "is_fallback": suggestions.is_fallback,
                "month": req_month,
                "season": suggestions.season,
                "events": suggestions.events,
                "suggested_product_types": suggestions.product_types
            })
            _apply_api_sync_metadata(res)
            return res

        items = search_products_tool(
            product_type=product_type,
            country=country_code,
            max_base_cost=max_base_cost,
            max_shipping_days=max_shipping_days,
            print_sides=print_sides,
            query=combined_query
        )
        if product_type and product_type.startswith("alternative"):
            if "_" in product_type:
                excluded_cat = product_type.split("_", 1)[1]
                res["answer"] = f"Dưới đây là danh sách các loại sản phẩm khác ngoài {excluded_cat} đang có sẵn tại {country_code}:" if lang == "vi" else f"Here is the list of diverse products other than {excluded_cat} available in {country_code}:"
            else:
                res["answer"] = f"Dưới đây là danh sách các loại sản phẩm khác nhau đang có sẵn tại {country_code}:" if lang == "vi" else f"Here is the list of diverse products available in {country_code}:"
        else:
            res["answer"] = f"Dưới đây là các sản phẩm {product_type} được đề xuất cho bạn tại {country_code}:" if lang == "vi" else f"Here are the recommended {product_type} products for you in {country_code}:"
        res["items"] = items
        res["tool_data"] = items
        res["is_nearest"] = any(item.get("filter_match") == "nearest_alternative" for item in items)
        res["margin_alert"] = _apply_margin(items, selling_price, min_margin)
        res["metadata"].update({
            "max_base_cost": max_base_cost,
            "max_shipping_days": max_shipping_days,
            "selling_price": selling_price,
            "min_margin": min_margin,
            "is_nearest": res["is_nearest"]
        })
        _apply_api_sync_metadata(res)
        return res

    if intent == "compare":
        compare_data = compare_shipping_tool(product_type=product_type, country=country_code, print_sides=print_sides, query=combined_query)
        items = []
        for item in compare_data:
            items.append({
                "sku": item["sku"],
                "display_name": item["display_name"],
                "product_name": product_type,
                "color": item["color"],
                "size": item["size"],
                "partner_name": item["partner_name"],
                "location_name": item["location_name"],
                "base_cost": item["base_cost"],
                "shipping_fee": item["shipping_fee"],
                "second_item_price": item["second_item_price"],
                "tax_fee": item["tax_fee"],
                "landed_cost": item["landed_cost"],
                "delivery_time": item["delivery_time"],
                "carrier": [item["carrier"]],
                "available_carriers": item.get("available_carriers", []),
                "api_sync_required": item.get("api_sync_required", False),
                "print_sides": print_sides
            })
        res["items"] = items
        res["tool_data"] = items
        res["margin_alert"] = _apply_margin(items, selling_price, min_margin)
        _apply_api_sync_metadata(res)
        return res

    if intent == "calculate_margin":
        if not sku:
            res["clarification_required"] = True
            res["missing_field"] = "sku"
            res["metadata"]["required_slots"] = ["sku"]
            res["tool_data"] = {"slots": slots, "missing_field": "sku"}
            return res

        calc = calculate_landed_cost_tool(
            sku=sku,
            country=country_code,
            quantity=quantity,
            selling_price=selling_price,
            print_sides=print_sides
        )
        res["tool_data"] = calc
        if "error" not in calc:
            res["items"] = [calc]
            if selling_price is None and min_margin is not None and min_margin < 100:
                suggested_price = round(calc["landed_cost"] / (1 - min_margin / 100), 2)
                calc["selling_price"] = suggested_price
                calc["total_selling_price"] = round(suggested_price * quantity, 2)
                calc["profit"] = round(calc["total_selling_price"] - calc["landed_cost"], 2)
                calc["margin_percent"] = round((calc["profit"] / calc["total_selling_price"]) * 100, 2)
                res["margin_alert"] = True
        res["metadata"].update({
            "sku": sku,
            "quantity": quantity,
            "selling_price": selling_price,
            "min_margin": min_margin
        })
        _apply_api_sync_metadata(res)
        return res

    if intent == "create_order":
        if not sku:
            res["clarification_required"] = True
            res["missing_field"] = "sku"
            res["metadata"]["required_slots"] = ["sku"]
            res["tool_data"] = {"slots": slots, "missing_field": "sku"}
            return res

        if not shipping_address:
            res["clarification_required"] = True
            res["missing_field"] = "shipping_address"
            res["metadata"]["required_slots"] = ["shipping_address"]
            res["tool_data"] = {"slots": slots, "missing_field": "shipping_address"}
            return res

        if not slots.get("confirmed_order"):
            res["confirmation_required"] = True
            calc = calculate_landed_cost_tool(
                sku=sku,
                country=shipping_address.get("country", country_code),
                quantity=quantity,
                print_sides=print_sides
            )
            res["tool_data"] = {"order_preview": calc, "shipping_address": shipping_address}
            _apply_api_sync_metadata(res)
            slots["confirmed_order"] = True

            # Generate deterministic preview answer to prevent LLM hallucination
            if "error" in calc:
                res["answer"] = calc["error"]
            else:
                display_name = calc.get("display_name", sku)
                partner = calc.get("partner_name", "BurgerPrints")
                landed = calc.get("landed_cost", 0)
                ship_country = shipping_address.get("country", country_code)
                ship_name = shipping_address.get("full_name", "")
                ship_addr = shipping_address.get("address1", "")
                ship_city = shipping_address.get("city", "")
                ship_zip = shipping_address.get("zip_code", "")
                res["answer"] = (
                    f"Order preview confirmed. SKU {sku} ({display_name}) is available from partner {partner}.\n\n"
                    f"Landed Cost: ${landed:.2f} (quantity: {quantity}, print: {print_sides})\n"
                    f"Ship to: {ship_name}, {ship_addr}, {ship_city} {ship_zip}, {ship_country}\n\n"
                    f"Please confirm to create this sandbox order."
                )
            return res

        order_res = await create_draft_order_tool(
            sku=sku,
            quantity=quantity,
            country=shipping_address.get("country", country_code),
            full_name=shipping_address.get("full_name"),
            address1=shipping_address.get("address1"),
            city=shipping_address.get("city"),
            zip_code=shipping_address.get("zip_code"),
            print_sides=print_sides,
            shipping_carrier=shipping_carrier,
            state=shipping_address.get("state"),
            email=shipping_address.get("email"),
            phone=shipping_address.get("phone")
        )
        res["tool_data"] = order_res
        if order_res.get("success"):
            res["status"] = order_res.get("status")
            res["order_id"] = order_res.get("order_id")
            res["answer"] = f"Đơn hàng đã được tạo thành công với Order ID: {order_res.get('order_id')}."
            slots.pop("sku", None)
            slots.pop("shipping_address", None)
            slots.pop("confirmed_order", None)
        else:
            error_msg = order_res.get("error", "Unknown error")
            res["status"] = "failed"
            res["answer"] = f"Không thể tạo đơn hàng. Lỗi: {error_msg}"
            logger.error(f"Create order failed for SKU {sku}: {error_msg}")
        return res

    if intent == "get_system_metadata":
        res["tool_data"] = {
            "system_status": "active",
            "sandbox_mode": settings.burgerprints_enable_sandbox_create_order
        }
        res["metadata"].update(res["tool_data"])
        return res

    if intent == "capability_discovery":
        res["tool_data"] = {
            "active_markets": ACTIVE_MARKETS,
            "market_count": len(ACTIVE_MARKETS),
            "coverage": {
                "EU": ["DE", "FR"],
                "AU_NZ": ["AU", "NZ"]
            }
        }
        res["metadata"].update(res["tool_data"])
        return res

    if intent == "general_knowledge_conversation":
        res["tool_data"] = None
        return res

    res["tool_data"] = {"slots": slots}
    return res
