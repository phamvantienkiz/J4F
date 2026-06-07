import re
from typing import Any, TypedDict
from uuid import uuid4

import requests
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agent.agents.semantic_router import SemanticRouter
from src.agent.orchestrator import OrchestratorAgent
from src.agent.order_draft import (
    base_response,
    build_create_order_payload,
    format_confirmation_prompt,
    format_missing_fields_prompt,
    is_cancel_order_request,
    is_final_confirmation,
    is_start_order_request,
    merge_order_fields,
    missing_required_fields,
    parse_order_fields,
    recommendation_to_draft,
    sanitize_draft_summary,
)
from src.core.config import settings
from src.core.text_parser import normalize_text, parse_country, parse_filters, parse_product_type, parse_sku_code
from src.services.burgerprints_client import BurgerPrintsClient


ORDER_FIELD_DESCRIPTIONS = {
    "shipping_name": "shipping_name là tên người nhận hàng.",
    "shipping_address1": "shipping_address1 là địa chỉ nhận hàng dòng chính, ví dụ số nhà, đường, phường/xã.",
    "shipping_address2": "shipping_address2 là địa chỉ bổ sung như căn hộ, tầng, tòa nhà; field này có thể bỏ trống nếu không có.",
    "shipping_city": "shipping_city là thành phố nhận hàng.",
    "shipping_state": "shipping_state là bang/tỉnh. Với đơn ship US, field này bắt buộc, ví dụ TX hoặc CA.",
    "shipping_zip": "shipping_zip là mã bưu chính/postal code của địa chỉ nhận hàng.",
    "shipping_country": "shipping_country là mã quốc gia nhận hàng, ví dụ US, CA, AU, GB.",
    "reference_order_id": "reference_order_id là mã đơn tham chiếu do bạn tự đặt để đối soát, ví dụ TEST-1001.",
    "design_url_front": "design_url_front là URL ảnh design mặt trước cần in lên sản phẩm. Link phải là http/https công khai để BurgerPrints có thể tải file in.",
}


class AgentGraphState(TypedDict, total=False):
    message: str
    session_id: str
    history: list[dict[str, Any]]
    response: dict[str, Any]
    phase: str
    last_recommendation: dict[str, Any]
    last_market_advice: dict[str, Any]
    pending_order: dict[str, Any] | None
    missing_fields: list[str]
    confirmation_required: bool
    confirmed: bool
    pending_search_message: str | None
    pending_search_params: dict | None
    pending_product_category: str | None


class AgentGraph:
    def __init__(self, orchestrator=None, order_client=None):
        self.orchestrator = orchestrator or OrchestratorAgent()
        self.order_client = order_client
        self.semantic_router = SemanticRouter()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentGraphState)
        graph.add_node("agent", self._agent_node)
        graph.set_entry_point("agent")
        graph.add_edge("agent", END)
        return graph.compile(checkpointer=self.checkpointer)

    def _agent_node(self, state: AgentGraphState) -> AgentGraphState:
        message = state["message"]
        session_id = state["session_id"]
        phase = state.get("phase", "idle")

        if is_cancel_order_request(message):
            return self._cancel_order_draft(state, session_id)

        if phase in {"collecting_order_info", "awaiting_final_confirmation"}:
            order_field_answer = self._order_field_follow_up_answer(message)
            if order_field_answer:
                return self._explain_order_field_follow_up(state, session_id, order_field_answer)

        if self._is_explanation_follow_up(message) and state.get("last_recommendation"):
            return self._explain_last_recommendation(state, session_id)

        market_follow_up = self._market_advice_follow_up_answer(message, state.get("last_market_advice") or {})
        if market_follow_up:
            return self._explain_market_advice_follow_up(state, session_id, market_follow_up)

        if phase == "awaiting_search_country":
            return self._continue_search_with_country(state, session_id)

        if phase == "awaiting_product_type_clarification":
            product_follow_up = self._continue_search_with_product_type(state, session_id)
            if product_follow_up:
                return product_follow_up

        if phase in {"collecting_order_info", "awaiting_final_confirmation"}:
            if self._is_new_agent_request(message):
                response = self.orchestrator.run(message)
                response = self._with_session_id(response, session_id)
                return self._state_after_agent_response(
                    {**state, "pending_order": None, "missing_fields": [], "confirmation_required": False, "confirmed": False},
                    response,
                    session_id,
                    message,
                )
            return self._continue_order_draft(state, session_id)

        if is_final_confirmation(message):
            response = base_response(
                "Chưa có sandbox order draft đang chờ xác nhận. Bạn cần hỏi agent tìm/recommend SKU trước.",
                session_id,
            )
            return {**state, "response": response, "phase": "idle", "pending_order": None}

        if is_start_order_request(message):
            return self._start_order_draft(state, session_id)

        order_fields = parse_order_fields(message)
        if order_fields:
            return self._start_order_draft(state, session_id, order_fields)

        ambiguous_category = self._ambiguous_product_category(message, state.get("last_recommendation") or {})
        if ambiguous_category:
            return self._ask_product_type_clarification(state, session_id, ambiguous_category)

        search_context_update = self._search_context_follow_up_intent(message, state.get("last_recommendation") or {})
        if search_context_update:
            response = self.orchestrator.run(self._search_context_message(message, search_context_update), intent_override=search_context_update)
            response = self._with_session_id(response, session_id)
            return self._state_after_agent_response(state, response, session_id, message)

        response = self.orchestrator.run(message)
        response = self._with_session_id(response, session_id)
        return self._state_after_agent_response(state, response, session_id, message)

    def _is_new_agent_request(self, message: str) -> bool:
        if is_final_confirmation(message) or is_start_order_request(message) or parse_order_fields(message):
            return False
        route = self.semantic_router.route(message, {})
        if not route:
            return False
        return route.get("kind") in {
            "catalog_search",
            "season_product_advice",
            "niche_advice",
            "event_advice",
            "design_advice",
            "event_explanation",
            "market_follow_up",
            "out_of_scope",
        }

    def _ambiguous_product_category(self, message: str, last_recommendation: dict[str, Any]) -> str | None:
        if not last_recommendation:
            return None
        normalized = normalize_text(message)
        if self._is_new_agent_request(message):
            return None
        filters = parse_filters(message)
        if filters.get("selling_price") is not None or filters.get("country") is not None:
            return None
        product_type = parse_product_type(normalized) or self._product_type_from_short_answer(message)
        broad_drinkware = product_type == "Mug" and not any(term in normalized for term in ["11oz", "15oz", "travel"])
        if product_type and not broad_drinkware:
            return None
        categories = {
            "apparel": ["ao", "apparel", "shirt", "clothing", "quan ao"],
            "drinkware": ["coc", "cup", "drinkware"],
            "wall_art": ["canvas", "poster", "sign", "wall art", "tranh"],
            "kids": ["do tre em", "baby", "kids", "youth"],
        }
        for category, terms in categories.items():
            if any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in terms):
                return category
        return None

    def _ask_product_type_clarification(self, state: AgentGraphState, session_id: str, category: str) -> AgentGraphState:
        options = {
            "apparel": "T-shirt, Hoodie, Sweatshirt hoặc Tank top",
            "drinkware": "11oz Mug, 15oz Mug hoặc travel cup",
            "wall_art": "Canvas, Poster hoặc Metal Sign",
            "kids": "Baby T-shirt, Kids T-shirt hoặc Youth T-shirt",
        }
        label = {
            "apparel": "nhóm áo",
            "drinkware": "nhóm cốc/drinkware",
            "wall_art": "nhóm wall art",
            "kids": "nhóm trẻ em",
        }.get(category, "nhóm sản phẩm này")
        response = base_response(
            f"Bạn muốn search loại sản phẩm nào cho {label}? Mình có thể tìm {options.get(category, 'một product type cụ thể')}. Bạn chọn loại nào?",
            session_id,
            intent="product_type_clarification",
            params=(state.get("last_recommendation") or {}).get("params", {}),
            data={"source": "product_type_clarification", "category": category},
            notes=["Asked for a concrete product type before calling Catalog API."],
        )
        return {
            **state,
            "response": response,
            "phase": "awaiting_product_type_clarification",
            "pending_search_params": (state.get("last_recommendation") or {}).get("params", {}),
            "pending_product_category": category,
            "pending_order": None,
            "missing_fields": [],
            "confirmation_required": False,
            "confirmed": False,
        }

    def _continue_search_with_product_type(self, state: AgentGraphState, session_id: str) -> AgentGraphState | None:
        message = state["message"]
        if self._is_new_agent_request(message):
            response = self.orchestrator.run(message)
            response = self._with_session_id(response, session_id)
            return self._state_after_agent_response(
                {**state, "pending_search_params": None, "pending_product_category": None},
                response,
                session_id,
                message,
            )

        product_type = parse_product_type(message) or self._product_type_from_short_answer(message)
        if not product_type:
            category = state.get("pending_product_category") or "product"
            return self._ask_product_type_clarification(state, session_id, category)

        last_params = (state.get("last_recommendation") or {}).get("params") or {}
        pending_params = state.get("pending_search_params") or {}
        intent = {**last_params, **pending_params, "name": "search_order_items", "product_type": product_type}
        response = self.orchestrator.run(self._search_context_message(message, intent), intent_override=intent)
        response = self._with_session_id(response, session_id)
        return self._state_after_agent_response(
            {**state, "pending_search_params": None, "pending_product_category": None},
            response,
            session_id,
            message,
        )

    def _product_type_from_short_answer(self, message: str) -> str | None:
        normalized = normalize_text(message)
        aliases = {
            "hoodie": "Hoodie",
            "t shirt": "T-shirt",
            "t-shirt": "T-shirt",
            "tee": "T-shirt",
            "sweatshirt": "Sweatshirt",
            "tank top": "Tank top",
            "baby t-shirt": "Baby T-shirt",
            "baby tshirt": "Baby T-shirt",
            "kids t-shirt": "Kids T-shirt",
            "youth t-shirt": "Youth T-shirt",
            "11oz mug": "11oz Mug",
            "15oz mug": "15oz Mug",
        }
        for term, product_type in aliases.items():
            if term in normalized:
                return product_type
        return None

    def _search_context_follow_up_intent(self, message: str, last_recommendation: dict[str, Any]) -> dict[str, Any] | None:
        if not last_recommendation:
            return None
        filters = parse_filters(message)
        selling_price = filters.get("selling_price")
        country = filters.get("country")
        product_type = filters.get("product_type") or self._product_type_from_short_answer(message)
        if selling_price is None and country is None and product_type is None:
            return None

        normalized = normalize_text(message)
        explicit_new_request_terms = [
            "sku",
            "product",
            "san pham",
            "xuong nao",
            "chon xuong",
            "goi y",
            "suggest",
            "design",
            "niche",
            "event",
            "tim ",
            "find ",
            "search ",
        ]
        if any(term in normalized for term in explicit_new_request_terms):
            return None

        if country is not None:
            country_only = normalized.strip() in {"us", "usa", "my", "ca", "canada", "au", "uc", "uk", "gb", "vn", "viet nam", "vietnam", "eu"}
            shipping_context = any(term in normalized for term in ["ship", "shipping", "giao hang", "fulfill", "delivery", "van chuyen"])
            if not country_only and not shipping_context:
                return None

        params = dict(last_recommendation.get("params") or {})
        if not params:
            return None
        params["name"] = "search_order_items"
        if selling_price is not None:
            params["selling_price"] = selling_price
            params["platform"] = filters.get("platform") or params.get("platform") or "generic"
        if country is not None:
            params["country"] = country
        if product_type is not None:
            params["product_type"] = product_type
        return params

    def _search_context_message(self, message: str, intent: dict[str, Any]) -> str:
        parts = [message]
        if intent.get("product_type"):
            parts.append(str(intent["product_type"]))
        if intent.get("country"):
            parts.append(f"ship {intent['country']}")
        return " ".join(parts)

    def _order_field_follow_up_answer(self, message: str) -> str | None:
        normalized = normalize_text(message)
        asks_definition = any(phrase in normalized for phrase in ["la gi", "nghia la gi", "what is", "explain"])
        if not asks_definition:
            return None
        for field, description in ORDER_FIELD_DESCRIPTIONS.items():
            if field in normalized:
                return description
        return None

    def _explain_order_field_follow_up(self, state: AgentGraphState, session_id: str, answer: str) -> AgentGraphState:
        response = base_response(
            answer,
            session_id,
            intent="order_field_explanation",
            params=sanitize_draft_summary(state.get("pending_order") or {}),
            data={"source": "order_field_explanation"},
            notes=["Explained an order draft field without creating an order."],
        )
        return {**state, "response": response}

    def _is_explanation_follow_up(self, message: str) -> bool:
        normalized = normalize_text(message)
        return any(
            phrase in normalized
            for phrase in ["tai sao", "vi sao", "sao co", "why", "reason", "giai thich", "nhieu goi y", "nhieu lua chon"]
        )

    def _market_advice_follow_up_answer(self, message: str, last_market_advice: dict[str, Any]) -> str | None:
        if not last_market_advice:
            return None
        normalized = normalize_text(message)
        asks_definition = any(phrase in normalized for phrase in ["la gi", "nghia la gi", "what is", "explain"])
        if not asks_definition:
            return None
        descriptions = {
            "july 4 prep": "July 4 prep là giai đoạn chuẩn bị design trước Independence Day 4/7 ở US. Seller thường làm chủ đề cờ Mỹ, fireworks, BBQ, family gathering, patriotic quote và nên chuẩn bị listing trước event vài tuần.",
            "independence day": "Independence Day là ngày Quốc khánh Mỹ 4/7. Với POD, event này hợp với design patriotic, fireworks, BBQ, family, veteran/USA pride và apparel mùa hè.",
            "father's day": "Father's Day là Ngày của Cha. Với POD, event này hợp với áo/cốc quà tặng cho dad, grandpa, husband, funny dad quote và family matching.",
            "mother's day": "Mother's Day là Ngày của Mẹ. Với POD, event này hợp với gift design cho mom, grandma, wife, floral typography và family quote.",
            "black friday": "Black Friday là mùa sale lớn cuối tháng 11. Với POD, nên chuẩn bị deal design, giftable products, holiday prep và campaign giảm giá rõ ràng.",
            "thanksgiving": "Thanksgiving là lễ Tạ ơn ở US vào tháng 11. Design thường xoay quanh family gathering, gratitude, turkey, fall colors và cozy apparel.",
            "christmas": "Christmas là mùa quà tặng lớn nhất cuối năm. POD phù hợp với hoodie, sweatshirt, mug, family matching, ornament-style graphics và funny holiday quotes.",
        }
        for term, description in descriptions.items():
            if term in normalized:
                return description
        events = last_market_advice.get("events") or []
        if events:
            return f"Đây là event/seasonal keyword trong market vừa gợi ý. Với {last_market_advice.get('country', 'market này')}, bạn có thể khai thác các event: {', '.join(events[:4])}."
        return None

    def _explain_market_advice_follow_up(self, state: AgentGraphState, session_id: str, answer: str) -> AgentGraphState:
        response = base_response(
            answer,
            session_id,
            intent="market_follow_up_explanation",
            data={"source": "market_follow_up_explanation", "last_market_advice": state.get("last_market_advice")},
            notes=["Explained a market/event term from conversation state."],
        )
        return {
            **state,
            "response": response,
            "phase": "market_advice_offered",
            "pending_order": None,
            "missing_fields": [],
            "confirmation_required": False,
            "confirmed": False,
        }

    def _explain_last_recommendation(self, state: AgentGraphState, session_id: str) -> AgentGraphState:
        last_recommendation = state.get("last_recommendation") or {}
        item = last_recommendation.get("item") or {}
        product_name = item.get("product_name") or item.get("display_name") or "SKU này"
        color = item.get("color") or "màu đang chọn"
        delivery = item.get("delivery_time") or "delivery tốt"
        supplier = item.get("partner_name") or item.get("location_name") or "xưởng phù hợp"
        total_cost = item.get("total_cost")
        cost_text = f"${total_cost:.2f}" if isinstance(total_cost, (int, float)) else "chi phí hợp lý"
        normalized_message = normalize_text(state["message"])
        if "nhieu goi y" in normalized_message or "nhieu lua chon" in normalized_message or "sao co" in normalized_message:
            answer = (
                "Có nhiều gợi ý vì BurgerPrints Catalog API trả về nhiều biến thể cùng phù hợp với filter của bạn: khác màu, size, supplier hoặc product type. "
                "UI đang hiển thị top options để bạn so sánh nhanh cost, delivery và xưởng trước khi chọn một SKU để tạo draft.\n\n"
                f"Nếu muốn gọn hơn, bạn có thể lọc thêm màu/size, ví dụ: tìm T-shirt Black size M ship US. SKU đang đứng đầu hiện tại là {item.get('sku') or product_name}."
            )
        else:
            answer = (
                f"Mình gợi ý {product_name} vì ranking hiện tại ưu tiên dữ liệu fulfill thực tế: tổng cost {cost_text}, "
                f"delivery {delivery}, xưởng {supplier}, và SKU/màu {color} đang có trong Catalog API.\n\n"
                "Nếu câu hỏi là về mùa summer, cốc/mug không phải lựa chọn duy nhất cho mùa hè; nó thường phù hợp khi bạn bán design dạng quà tặng, event hoặc niche quanh Father's Day/July 4. "
                "Nếu bạn muốn đúng apparel mùa hè hơn, hãy hỏi: Tìm T-shirt hoặc Tank top cho US mùa summer."
            )
        response = base_response(
            answer,
            session_id,
            intent="follow_up_explanation",
            params=last_recommendation.get("params", {}),
            data={"source": "follow_up_explanation", "item": item},
            notes=["Explained the latest recommendation from conversation state."],
        )
        return {
            **state,
            "response": response,
            "phase": "recommendation_offered",
            "pending_order": None,
            "missing_fields": [],
            "confirmation_required": False,
            "confirmed": False,
            "pending_search_message": None,
            "pending_search_params": None,
        }

    def _state_after_agent_response(self, state: AgentGraphState, response: dict[str, Any], session_id: str, message: str) -> AgentGraphState:
        next_state: AgentGraphState = {**state, "response": response}
        data = response.get("data") if isinstance(response.get("data"), dict) else {}

        if response.get("intent") == "search_order_items" and data.get("clarification_required"):
            next_state.update(
                {
                    "phase": "awaiting_search_country",
                    "pending_search_message": message,
                    "pending_search_params": response.get("params", {}),
                    "pending_order": None,
                    "missing_fields": [],
                    "confirmation_required": False,
                    "confirmed": False,
                }
            )
            return next_state

        if response.get("intent") == "market_advice":
            next_state.update(
                {
                    "phase": "market_advice_offered",
                    "last_market_advice": data,
                    "pending_order": None,
                    "missing_fields": [],
                    "confirmation_required": False,
                    "confirmed": False,
                }
            )
            return next_state

        items = (data.get("items") or []) if isinstance(data, dict) else []
        if response.get("intent") == "search_order_items" and items:
            response["answer"] = (
                f"{response.get('answer', '')}\n\n"
                "Bạn có muốn tạo sandbox order draft từ SKU này không? Nếu có, hãy nhắn: tạo sandbox order."
            )
            next_state.update(
                {
                    "response": response,
                    "phase": "recommendation_offered",
                    "last_recommendation": {"item": items[0], "items": items, "params": response.get("params", {})},
                    "pending_search_message": None,
                    "pending_search_params": None,
                    "pending_product_category": None,
                    "pending_order": None,
                    "missing_fields": [],
                    "confirmation_required": False,
                    "confirmed": False,
                }
            )
        else:
            next_state.update({"phase": "idle", "confirmation_required": False, "confirmed": False})
        return next_state

    def _continue_search_with_country(self, state: AgentGraphState, session_id: str) -> AgentGraphState:
        country = parse_country(state["message"])
        if not country:
            response = base_response(
                "Mình cần biết đơn này ship/fulfill tới nước nào để tính đúng shipping, delivery và xưởng. Bạn muốn ship tới market nào? Ví dụ: US, CA, UK, AU, VN.",
                session_id,
                params=state.get("pending_search_params") or {},
                data={"source": "clarification", "clarification_required": True, "missing_field": "country"},
            )
            return {**state, "response": response, "phase": "awaiting_search_country"}

        pending_message = state.get("pending_search_message") or state["message"]
        pending_params = state.get("pending_search_params") or {}
        last_params = (state.get("last_recommendation") or {}).get("params") or {}
        intent = {**last_params, **pending_params, "name": "search_order_items", "country": country}
        response = self.orchestrator.run(pending_message, intent_override=intent)
        response = self._with_session_id(response, session_id)
        return self._state_after_agent_response(state, response, session_id, pending_message)

    def _selected_recommendation_item(self, message: str, last_recommendation: dict[str, Any]) -> dict[str, Any] | None:
        items = last_recommendation.get("items") or []
        selected_sku = parse_sku_code(message)
        if selected_sku:
            for item in items:
                sku = item.get("catalog_sku") or item.get("sku")
                if sku and sku.lower() == selected_sku.lower():
                    return item
        return last_recommendation.get("item")

    def _start_order_draft(self, state: AgentGraphState, session_id: str, initial_fields: dict | None = None) -> AgentGraphState:
        last_recommendation = state.get("last_recommendation") or {}
        item = self._selected_recommendation_item(state.get("message", ""), last_recommendation)
        if item:
            draft = recommendation_to_draft(item, last_recommendation.get("params", {}))
        elif initial_fields:
            draft = merge_order_fields({"sandbox": True, "items": [{}]}, initial_fields)
        else:
            response = base_response(
                "Bạn cần hỏi agent tìm/recommend SKU trước, sau đó tôi mới tạo sandbox order draft từ SKU đã chọn.",
                session_id,
            )
            return {**state, "response": response, "phase": "idle", "pending_order": None}

        if initial_fields:
            draft = merge_order_fields(draft, initial_fields)
        missing = missing_required_fields(draft)
        if missing:
            response = base_response(format_missing_fields_prompt(missing), session_id, params=sanitize_draft_summary(draft))
            phase = "collecting_order_info"
            confirmation_required = False
        else:
            response = base_response(format_confirmation_prompt(draft), session_id, params=sanitize_draft_summary(draft), confirmation_required=True)
            phase = "awaiting_final_confirmation"
            confirmation_required = True
        return {
            **state,
            "response": response,
            "phase": phase,
            "pending_order": draft,
            "missing_fields": missing,
            "confirmation_required": confirmation_required,
            "confirmed": False,
        }

    def _continue_order_draft(self, state: AgentGraphState, session_id: str) -> AgentGraphState:
        draft = state.get("pending_order") or {}

        if is_final_confirmation(state["message"]):
            missing = missing_required_fields(draft)
            if missing:
                response = base_response(format_missing_fields_prompt(missing), session_id, params=sanitize_draft_summary(draft))
                return {
                    **state,
                    "response": response,
                    "phase": "collecting_order_info",
                    "missing_fields": missing,
                    "confirmation_required": False,
                    "confirmed": False,
                }
            return self._create_sandbox_order(state, session_id, draft)

        fields = parse_order_fields(state["message"])
        if fields:
            draft = merge_order_fields(draft, fields)

        missing = missing_required_fields(draft)
        if missing:
            response = base_response(format_missing_fields_prompt(missing), session_id, params=sanitize_draft_summary(draft))
            return {
                **state,
                "response": response,
                "phase": "collecting_order_info",
                "pending_order": draft,
                "missing_fields": missing,
                "confirmation_required": False,
                "confirmed": False,
            }

        response = base_response(format_confirmation_prompt(draft), session_id, params=sanitize_draft_summary(draft), confirmation_required=True)
        return {
            **state,
            "response": response,
            "phase": "awaiting_final_confirmation",
            "pending_order": draft,
            "missing_fields": [],
            "confirmation_required": True,
            "confirmed": False,
        }

    def _create_sandbox_order(self, state: AgentGraphState, session_id: str, draft: dict) -> AgentGraphState:
        payload = build_create_order_payload(draft)
        params = sanitize_draft_summary(draft)
        if self.order_client is None and not settings.burgerprints_enable_sandbox_create_order:
            response = base_response(
                "Sandbox order draft đã sẵn sàng, nhưng live sandbox POST đang bị tắt để tránh tạo order ngoài ý muốn. Set BURGERPRINTS_ENABLE_SANDBOX_CREATE_ORDER=true rồi xác nhận lại nếu muốn gọi BurgerPrints sandbox API.",
                session_id,
                params=params,
                data={"sandbox": True, "status": "disabled"},
                confirmation_required=True,
            )
            return {
                **state,
                "response": response,
                "phase": "awaiting_final_confirmation",
                "pending_order": draft,
                "missing_fields": [],
                "confirmation_required": True,
                "confirmed": False,
            }

        client = self.order_client or BurgerPrintsClient()

        try:
            data, api_meta = client.create_order(payload)
        except (RuntimeError, requests.RequestException) as error:
            error_detail = str(error)
            if isinstance(error, requests.HTTPError) and error.response is not None:
                error_detail = error.response.text or str(error)
            response = base_response(
                f"Chưa tạo được sandbox order. BurgerPrints API trả lỗi: {error_detail[:500]}",
                session_id,
                params=params,
                data={"sandbox": True, "status": "failed", "error": error_detail[:500]},
                confirmation_required=True,
            )
            return {
                **state,
                "response": response,
                "phase": "awaiting_final_confirmation",
                "pending_order": draft,
                "missing_fields": [],
                "confirmation_required": True,
                "confirmed": False,
            }

        result = self._sanitize_create_order_result(data, params)
        response = base_response(
            "Sandbox order đã được tạo thành công trong BurgerPrints sandbox mode.",
            session_id,
            tool_calls=[{"name": "create_order_tool", "params": params}],
            api=api_meta,
            params=params,
            data=result,
            notes=["Created in BurgerPrints sandbox mode only."],
        )
        return {
            **state,
            "response": response,
            "phase": "order_created",
            "pending_order": None,
            "missing_fields": [],
            "confirmation_required": False,
            "confirmed": True,
        }

    def _cancel_order_draft(self, state: AgentGraphState, session_id: str) -> AgentGraphState:
        response = base_response("Đã hủy sandbox order draft. Không có API tạo order nào được gọi.", session_id)
        return {
            **state,
            "response": response,
            "phase": "cancelled",
            "pending_order": None,
            "missing_fields": [],
            "confirmation_required": False,
            "confirmed": False,
            "last_recommendation": None,
        }

    def _with_session_id(self, response: dict[str, Any], session_id: str) -> dict[str, Any]:
        return {**response, "session_id": session_id}

    def _sanitize_create_order_result(self, data: Any, params: dict[str, Any]) -> dict[str, Any]:
        result = {
            "sandbox": True,
            "items_count": 1 if params.get("catalog_sku") else 0,
            "catalog_sku": params.get("catalog_sku"),
            "quantity": params.get("quantity"),
        }
        if isinstance(data, dict):
            for key in ["id", "order_id", "code", "status"]:
                if data.get(key):
                    result[key] = data[key]
        return result

    def invoke(self, message: str, history: list[dict[str, Any]] | None = None, session_id: str | None = None) -> dict[str, Any]:
        session_id = session_id or str(uuid4())
        config = {"configurable": {"thread_id": session_id}}
        previous = self.graph.get_state(config).values or {}
        state = {**previous, "message": message, "history": history or [], "session_id": session_id}
        result = self.graph.invoke(state, config=config)
        return result["response"]
