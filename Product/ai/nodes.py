import os
import json
import logging
from typing import Dict, Any, List
from google import genai
from google.genai import types

from ai.state import AgentState, Requirements, CandidateOption, OrderDraft, UserPreference
from ai.tools import search_catalog, get_factory_quotes, get_shipping_options, create_order
from ai.pricing_engine import calculate_landed_cost, calculate_margin, suggest_retail_price, calculate_sla_risk
from ai.vector_rag import index_message, recall_context

logger = logging.getLogger(__name__)

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai_client = genai.Client(api_key=api_key)
else:
    genai_client = None

def extract_intent_node(state: AgentState) -> Dict[str, Any]:
    """
    Extract user intent and slots using Gemini structured outputs.
    If Gemini API fails or is not available, uses fallback regex/heuristics.
    """
    history = state.get("conversation_history", [])
    if not history:
        return {"requirements": state.get("requirements", Requirements())}

    # Get the latest user message
    user_msg = ""
    for msg in reversed(history):
        if msg.get("sender") == "user":
            user_msg = msg.get("content", "")
            break

    # Also retrieve similar historical conversations for context recall
    user_id = "default_seller"  # In a real app, this would be retrieved from authenticated user
    recalled = recall_context(user_id, user_msg, limit=2)
    recalled_context_str = ""
    if recalled:
        recalled_context_str = "\n".join([f"- {item['document']}" for item in recalled])

    # Default slots
    req = state.get("requirements", Requirements())
    
    # Try using Gemini API to extract requirements
    if genai_client:
        try:
            pref = state.get("user_preferences", UserPreference())
            prompt = f"""
            You are an expert NLU assistant for a Print-on-Demand (POD) catalog agent.
            Analyze the user's latest query and extract the filtering slots.
            
            USER QUERY: "{user_msg}"
            
            RECALLED PAST CONVERSATIONS CONTEXT (Use this to resolve missing preferences or references if relevant):
            {recalled_context_str}
            
            DEFAULT SELLER PREFERENCES:
            - Preferred Market: {pref.preferred_market}
            
            Strictly extract:
            - product_type: name of the product category (e.g. "Classic Unisex T-Shirt", "Premium Fleece Hoodie", "Ceramic Glossy Mug 11oz")
            - color: product color
            - size: product size (S, M, L, XL, etc.)
            - market: target country code for delivery (US, EU, VN)
            - max_cogs: maximum cost of goods sold (float)
            - print_method: printing method (DTG, embroidery, sublimation)
            
            Only extract what is explicitly mentioned or clearly implied. Do not make up values.
            If the user does not specify a market, use the DEFAULT SELLER PREFERRED MARKET: "{pref.preferred_market}".
            """
            
            response = genai_client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Requirements,
                ),
            )
            
            extracted_req = Requirements.model_validate_json(response.text)
            
            # Merge with existing requirements if any fields are newly extracted
            new_product_type = extracted_req.product_type or req.product_type
            new_color = extracted_req.color or req.color
            new_size = extracted_req.size or req.size
            new_market = extracted_req.market or req.market or pref.preferred_market
            new_max_cogs = extracted_req.max_cogs or req.max_cogs
            new_print_method = extracted_req.print_method or req.print_method
            
            req = Requirements(
                product_type=new_product_type,
                color=new_color,
                size=new_size,
                market=new_market,
                max_cogs=new_max_cogs,
                print_method=new_print_method
            )
        except Exception as e:
            logger.error(f"Error in extract_intent_node Gemini call: {e}")

    # Fallback/Heuristic parsing if Gemini failed or is not configured
    if not req.product_type:
        text = user_msg.lower()
        if "t-shirt" in text or "tshirt" in text or "áo thun" in text:
            req.product_type = "Classic Unisex T-Shirt"
        elif "hoodie" in text or "áo khoác" in text or "áo mũ" in text:
            req.product_type = "Premium Fleece Hoodie"
        elif "mug" in text or "ly sứ" in text or "cốc" in text:
            req.product_type = "Ceramic Glossy Mug 11oz"

    if not req.market:
        text = user_msg.lower()
        pref = state.get("user_preferences", UserPreference())
        if "mỹ" in text or "us" in text or "usa" in text:
            req.market = "US"
        elif "châu âu" in text or "eu" in text or "đức" in text or "europe" in text:
            req.market = "EU"
        elif "việt nam" in text or "vn" in text or "vnam" in text:
            req.market = "VN"
        else:
            req.market = pref.preferred_market or "US"

    return {"requirements": req}

def clarify_node(state: AgentState) -> Dict[str, Any]:
    """
    Ask user to clarify missing required parameters (product_type or market).
    """
    req = state.get("requirements", Requirements())
    missing = []
    if not req.product_type:
        missing.append("loại sản phẩm (ví dụ: áo T-shirt, Hoodie, Cốc sứ)")
    if not req.market:
        missing.append("thị trường giao hàng (ví dụ: US, EU, VN)")

    state["last_missing_fields"] = missing

    # Generate a clarification question
    if missing:
        missing_str = " và ".join(missing)
        clarify_msg = f"Em thấy bạn đang cần tìm xưởng in tối ưu, nhưng em chưa rõ **{missing_str}**. Bạn vui lòng cung cấp thêm thông tin để em tìm kiếm chính xác nhé! 😊"
    else:
        clarify_msg = "Bạn vui lòng cho biết yêu cầu chi tiết của bạn."

    history = state.get("conversation_history", [])
    new_history = list(history)
    new_history.append({
        "sender": "assistant",
        "content": clarify_msg
    })
    
    # Save user & assistant messages to semantic vector store
    user_id = "default_seller"
    if history:
        # Index the last user message
        user_msgs = [m for m in history if m["sender"] == "user"]
        if user_msgs:
            index_message(state.get("thread_id", "default_thread"), "user", user_id, user_msgs[-1]["content"], "2026-06-06 12:00:00")
    
    index_message(state.get("thread_id", "default_thread"), "assistant", user_id, clarify_msg, "2026-06-06 12:00:00")

    return {"conversation_history": new_history, "last_missing_fields": missing}

def retrieve_catalog_node(state: AgentState) -> Dict[str, Any]:
    """
    Query BurgerPrints Catalog and retrieve quotes from factories.
    """
    req = state.get("requirements", Requirements())
    product_type = req.product_type or "Classic Unisex T-Shirt"
    market = req.market or "US"

    # 1. Search products in catalog
    products = search_catalog(product_type)
    if not products:
        return {"candidates": []}

    # Take the first matched product
    target_product = products[0]
    product_id = target_product["product_id"]

    # 2. Get factory quotes for this product
    # We pass target variant_id (can be empty string or select a default based on requirements)
    variant_id = "default_variant"
    quotes = get_factory_quotes(product_id, variant_id, market)

    # Attach product details to quotes
    candidates = []
    for q in quotes:
        candidate_item = dict(q)
        candidate_item["product_id"] = product_id
        candidate_item["product_name"] = target_product["name"]
        candidate_item["colors"] = target_product.get("colors", [])
        candidate_item["sizes"] = target_product.get("sizes", [])
        candidates.append(candidate_item)

    return {"candidates": candidates}

def calculate_pricing_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministic calculation of Landed Cost, Margin, and SLA Risk.
    """
    candidates = state.get("candidates", [])
    req = state.get("requirements", Requirements())
    market = req.market or "US"
    pref = state.get("user_preferences", UserPreference())

    # ZIP code fallbacks for shipping estimation
    zip_code_map = {"US": "95112", "EU": "10115", "VN": "100000"}
    zip_code = zip_code_map.get(market.upper(), "95112")

    # Suggested selling prices based on product type
    # If the user specifies maximum cost of goods sold, let's use that as reference
    retail_prices = {
        "Classic Unisex T-Shirt": 20.00,
        "Premium Fleece Hoodie": 39.00,
        "Ceramic Glossy Mug 11oz": 12.00
    }
    
    calculated_options = []
    for c in candidates:
        factory_id = c["factory_id"]
        base_cost = c["base_cost"]
        printing_cost = c["printing_cost"]
        reliability = c.get("sla_reliability_score", 95.0)
        
        # Call shipping API wrapper
        ship_options = get_shipping_options(factory_id, market, zip_code)
        # Select standard or first option
        shipping_cost = 5.00
        delivery_min = 5
        delivery_max = 8
        if ship_options:
            selected_ship = ship_options[0]
            shipping_cost = selected_ship["shipping_cost"]
            delivery_min = selected_ship["delivery_days_min"]
            delivery_max = selected_ship["delivery_days_max"]
            reliability = selected_ship.get("sla_reliability_score", reliability)

        # 1. Landed Cost
        cost_details = calculate_landed_cost(base_cost, printing_cost, shipping_cost, market)
        landed_cost = cost_details["landed_cost"]

        # 2. Suggested Selling Price & Margin
        product_name = c.get("product_name", "Classic Unisex T-Shirt")
        # Match retail price or calculate based on target margin
        selling_price = retail_prices.get(product_name, base_cost * 2.0)
        
        # If target margin is defined, let's recommend suggested price to meet target
        suggested_retail = suggest_retail_price(landed_cost, pref.target_margin)
        margin_percent = calculate_margin(landed_cost, selling_price)

        # 3. SLA Risk
        sla_risk = calculate_sla_risk(reliability, c["location"], market, delivery_max)

        option = CandidateOption(
            option_id=factory_id,
            factory_name=c["factory_name"],
            factory_location=c["location"],
            base_cost=base_cost,
            printing_cost=printing_cost,
            shipping_cost=shipping_cost,
            tax_cost=cost_details["tax"],
            landed_cost=landed_cost,
            margin_percentage=margin_percent,
            delivery_days_min=delivery_min,
            delivery_days_max=delivery_max,
            sla_risk_score=sla_risk
        )
        calculated_options.append(option)

    return {"calculated_options": calculated_options}

def rank_and_recommend_node(state: AgentState) -> Dict[str, Any]:
    """
    Rank options based on Seller priority, select Top 3, and generate the final decision response.
    """
    options = state.get("calculated_options", [])
    pref = state.get("user_preferences", UserPreference())
    priority = pref.fulfillment_priority or "margin"

    # Step 1: Scoring Algorithm
    scored_options = []
    for opt in options:
        # Lower landed cost is better
        # Lower delivery days is better
        # Lower SLA risk is better
        # Higher margin is better
        if priority == "margin":
            score = (opt.margin_percentage * 0.6) + ((30.0 - opt.landed_cost) * 0.2) + ((15 - opt.delivery_days_max) * 0.2)
        else:  # speed
            score = ((15 - opt.delivery_days_max) * 0.6) + (opt.margin_percentage * 0.2) + ((100.0 - opt.sla_risk_score) * 0.2)
            
        scored_options.append((score, opt))

    # Sort in descending order of score
    scored_options.sort(key=lambda x: x[0], reverse=True)
    top_options = [item[1] for item in scored_options[:3]]

    # Step 2: Format comparison table as Markdown
    product_name = state.get("candidates", [{}])[0].get("product_name", "sản phẩm")
    market = state.get("requirements", Requirements()).market or "US"
    
    table_rows = []
    for i, opt in enumerate(top_options, 1):
        table_rows.append(
            f"| Top {i}: {opt.factory_name} ({opt.factory_location}) | ${opt.base_cost} | ${opt.printing_cost} | ${opt.shipping_cost} | ${opt.tax_cost} | **${opt.landed_cost}** | **{opt.margin_percentage}%** | {opt.delivery_days_min}-{opt.delivery_days_max} ngày | {opt.sla_risk_score} (Thấp) |"
        )
    
    comparison_table = (
        "| Nhà in / Xưởng | Base Cost | Print Cost | Shipping | Tax | **Landed Cost** | **Margin** | **Thời gian ship** | **Rủi ro SLA** |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        + "\n".join(table_rows)
    )

    # Step 3: LLM generation for explanation & trade-offs
    explanation = ""
    next_steps = f"Bạn muốn chọn xưởng nào để lên đơn hàng nháp? Hãy nhập lệnh: *'Đặt xưởng {top_options[0].factory_name}'* hoặc sử dụng nút bấm tương tác."

    if genai_client:
        try:
            # Prepare options serialization for LLM context
            options_json = json.dumps([opt.model_dump() for opt in top_options], indent=2)
            prompt = f"""
            Bạn là trợ lý tư vấn tối ưu chuỗi cung ứng POD của BurgerPrints.
            Hãy viết bài phân tích đề xuất tối ưu và so sánh các xưởng in sau cho sản phẩm "{product_name}" tại thị trường "{market}".
            
            DỮ LIỆU TOP 3 XƯỞNG ĐÃ XẾP HẠNG:
            {options_json}
            
            HÃY PHẢN HỒI THEO ĐÚNG CẤU TRÚC 4 PHẦN SAU:
            1. **Kết Luận (Nhanh gọn):** Đề xuất ngay xưởng in tối ưu nhất và lý do ngắn gọn vì sao nó thắng cuộc (ví dụ: margin cao nhất hay giao nhanh nhất).
            2. **Bảng So Sánh:** (Em đã tự tạo bảng ở dưới rồi, hãy dùng văn bản chuyển tiếp sang bảng).
            3. **Giải Trình Trade-offs (Quan trọng nhất):** Phân tích điểm mạnh/yếu của từng xưởng. Ví dụ: Xưởng A rẻ nhất nhưng ship lâu hơn Xưởng B, Xưởng C nội địa giao nhanh nhất nhưng giá cao.
            4. **Gợi ý bước tiếp theo:** Hỏi người dùng xem họ muốn chọn xưởng nào để khởi tạo đơn hàng nháp (như SKU, số lượng, địa chỉ).
            
            Ngôn ngữ: Tiếng Việt, giữ các thuật ngữ landed cost, base cost, margin, SLA.
            """
            
            response = genai_client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt
            )
            explanation = response.text
        except Exception as e:
            logger.error(f"Error in rank_and_recommend_node Gemini call: {e}")

    if not explanation:
        # Text fallback if Gemini failed
        best_opt = top_options[0]
        explanation = (
            f"### 1. Kết Luận\n"
            f"Em đề xuất lựa chọn **{best_opt.factory_name}** vì đây là phương án tối ưu nhất phù hợp với ưu tiên `{priority}` của bạn. Phương án này mang lại Landed Cost là **${best_opt.landed_cost}** và tỷ lệ Margin dự kiến đạt **{best_opt.margin_percentage}%**.\n\n"
            f"### 2. Bảng So Sánh Chi Tiết\n"
            f"{comparison_table}\n\n"
            f"### 3. Phân Tích Trade-offs\n"
            f"- **{best_opt.factory_name}** có landed cost tối ưu và SLA vận hành tốt.\n"
            f"- Các xưởng khác có thể rẻ hơn nhưng thời gian vận chuyển kéo dài hơn hoặc rủi ro trễ hẹn cao hơn.\n\n"
            f"### 4. Bước Tiếp Theo\n"
            f"{next_steps}"
        )
    else:
        # Merge comparison table into the generated response (replace or append)
        # To be safe, if LLM didn't write the table, we inject it in the middle
        if "| Landed Cost |" not in explanation:
            explanation = explanation.replace("2. **Bảng So Sánh:**", f"2. **Bảng So Sánh:**\n\n{comparison_table}")
            if "2. **Bảng So Sánh:**" not in explanation:
                explanation = f"{explanation}\n\n### Bảng So Sánh\n{comparison_table}"

    # Save to message history
    history = state.get("conversation_history", [])
    new_history = list(history)
    new_history.append({
        "sender": "assistant",
        "content": explanation,
        "metadata": {
            "comparison_table": [opt.model_dump() for opt in top_options],
            "product_name": product_name,
            "market": market
        }
    })

    # Save user message to vector store
    user_id = "default_seller"
    if history:
        user_msgs = [m for m in history if m["sender"] == "user"]
        if user_msgs:
            index_message(state.get("thread_id", "default_thread"), "user", user_id, user_msgs[-1]["content"], "2026-06-06 12:00:00")
            
    index_message(state.get("thread_id", "default_thread"), "assistant", user_id, explanation, "2026-06-06 12:00:00")

    return {"ranking_results": top_options, "conversation_history": new_history}

def execute_order_node(state: AgentState) -> Dict[str, Any]:
    """
    Validate and execute order creation on BurgerPrints.
    """
    draft = state.get("order_draft")
    if not draft:
        return {"order_status": {"success": False, "error": "Order draft is missing"}}

    # Call BurgerPrints API to create order
    shipping_addr = {
        "full_name": draft.shipping_name,
        "address_line1": draft.shipping_address_line1,
        "city": draft.shipping_city,
        "state": draft.shipping_state,
        "zip_code": draft.shipping_zip,
        "country": draft.shipping_country
    }
    
    result = create_order(
        sku=draft.sku,
        quantity=draft.quantity,
        shipping_address=shipping_addr,
        selected_factory_id=draft.selected_option_id
    )

    # Add confirmation message to chat history
    history = state.get("conversation_history", [])
    new_history = list(history)
    
    if result.get("success"):
        confirm_msg = (
            f"🎉 **Đơn hàng đã được tạo thành công trên BurgerPrints!**\n\n"
            f"- **Mã đơn hàng:** `{result['order_id']}`\n"
            f"- **SKU:** `{draft.sku}`\n"
            f"- **Số lượng:** {draft.quantity}\n"
            f"- **Tổng chi phí (Landed Cost):** ${result['total_cogs']}\n"
            f"- **Trạng thái:** `{result['status']}`\n\n"
            f"Vận đơn tracking sẽ được cập nhật tự động khi xưởng in hoàn tất sản xuất."
        )
    else:
        confirm_msg = f"❌ **Tạo đơn hàng thất bại.** Lỗi: {result.get('error', 'Không xác định')}"

    new_history.append({
        "sender": "assistant",
        "content": confirm_msg
    })

    user_id = "default_seller"
    index_message(state.get("thread_id", "default_thread"), "assistant", user_id, confirm_msg, "2026-06-06 12:00:00")

    return {"order_status": result, "conversation_history": new_history}
