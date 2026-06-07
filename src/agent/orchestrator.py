from src.agent.agents.answer_agent import AnswerAgent
from src.agent.agents.catalog_agent import CatalogAgent
from src.agent.agents.intent_agent import IntentAgent
from src.agent.agents.market_advice_agent import MarketAdviceAgent
from src.agent.agents.order_agent import OrderAgent
from src.agent.agents.semantic_router import GENERIC_OUT_OF_SCOPE_ANSWER, SENSITIVE_REFUSAL_ANSWER, SemanticRouter
from src.agent.tools.burgerprints_tools import BurgerPrintsTools


ORDER_TOOL_NAMES = {
    "list_orders": "list_orders_tool",
    "get_order": "get_order_tool",
    "get_balance": "get_balance_tool",
}

CONCRETE_API_INTENTS = {"get_balance", "get_order", "get_sku", "get_product", "list_orders"}
MARKET_ROUTE_KINDS = {
    "season_product_advice",
    "niche_advice",
    "event_advice",
    "design_advice",
    "event_explanation",
    "market_follow_up",
}


class OrchestratorAgent:
    def __init__(self, semantic_router=None, market_advice_agent=None):
        tools = BurgerPrintsTools()
        self.intent_agent = IntentAgent()
        self.catalog_agent = CatalogAgent(tools)
        self.order_agent = OrderAgent(tools)
        self.answer_agent = AnswerAgent()
        self.semantic_router = semantic_router or SemanticRouter()
        self.market_advice_agent = market_advice_agent or MarketAdviceAgent()

    def run(self, message, intent_override=None, context=None):
        intent = intent_override or self.intent_agent.run(message)
        if not self._intent_has_required_params(intent):
            intent = {"name": "unknown"}
        name = intent["name"]
        semantic_route = None if intent_override or name in CONCRETE_API_INTENTS else self.semantic_router.route(message, context or {})

        if semantic_route and semantic_route.get("kind") == "out_of_scope":
            return self._out_of_scope_response(semantic_route)

        if semantic_route and semantic_route.get("kind") in MARKET_ROUTE_KINDS:
            return self.market_advice_agent.run(semantic_route, message, (context or {}).get("last_market_advice"))

        if semantic_route and semantic_route.get("kind") == "catalog_search" and name == "unknown":
            intent = self._catalog_intent_from_route(semantic_route)
            name = intent["name"]

        if name == "search_order_items":
            core_result, tool_calls = self.catalog_agent.search(message, intent=intent)
        elif name in {"get_product", "get_sku"}:
            core_result, tool_calls = self.catalog_agent.search(message, f"{name}_tool", intent)
        elif name in ORDER_TOOL_NAMES:
            core_result, tool_calls = self.order_agent.run(message, ORDER_TOOL_NAMES[name], intent)
        else:
            core_result = {
                "intent": name,
                "api": None,
                "params": {key: value for key, value in intent.items() if key != "name"},
                "result": None,
                "notes": ["Không hiểu yêu cầu hoặc intent này chưa được hỗ trợ trong rule-based agent."],
            }
            tool_calls = []

        answer = self.answer_agent.run(core_result)
        return {
            "answer": answer,
            "intent": core_result.get("intent"),
            "tool_calls": tool_calls,
            "api": core_result.get("api"),
            "params": core_result.get("params", {}),
            "data": core_result.get("result"),
            "notes": core_result.get("notes", []),
        }

    def _intent_has_required_params(self, intent):
        required = {"get_product": "short_code", "get_sku": "sku", "get_order": "order_id"}
        key = required.get(intent.get("name"))
        return not key or bool(intent.get(key))

    def _catalog_intent_from_route(self, route):
        intent = {"name": "search_order_items", "limit": 10}
        for key in ["country", "product_type", "quantity"]:
            if route.get(key) is not None:
                intent[key] = route[key]
        return intent

    def _out_of_scope_response(self, route):
        sensitive = bool(route.get("sensitive"))
        return {
            "answer": SENSITIVE_REFUSAL_ANSWER if sensitive else GENERIC_OUT_OF_SCOPE_ANSWER,
            "intent": "out_of_scope",
            "tool_calls": [],
            "api": None,
            "params": {"kind": "out_of_scope", "sensitive": sensitive},
            "data": {"source": "semantic_scope_guard", "kind": "out_of_scope", "sensitive": sensitive},
            "notes": ["Request was blocked by BurgerPrintsAgent scope guard."],
        }
