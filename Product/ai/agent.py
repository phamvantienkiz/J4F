import os
import sqlite3
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    # Fallback to MemorySaver if SqliteSaver import fails
    from langgraph.checkpoint.memory import MemorySaver as SqliteSaver

from ai.state import AgentState, Requirements
from ai.nodes import (
    extract_intent_node,
    clarify_node,
    retrieve_catalog_node,
    calculate_pricing_node,
    rank_and_recommend_node,
    execute_order_node
)

logger = logging.getLogger(__name__)

# Base Directory: Product/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "ai", "data", "sqlite.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 1. Routing Function
def route_after_extraction(state: AgentState) -> str:
    """
    Decide whether to clarify, retrieve catalog, or execute order.
    """
    history = state.get("conversation_history", [])
    latest_msg = ""
    if history:
        for m in reversed(history):
            if m.get("sender") == "user":
                latest_msg = m.get("content", "").lower()
                break

    # If we have an order draft and the user confirms, route to execute order
    if state.get("order_draft") and any(kw in latest_msg for kw in ["chốt", "đặt đơn", "confirm", "tiến hành", "ok", "xác nhận"]):
        return "execute_order"

    # Otherwise, check if we have the core requirements
    req = state.get("requirements")
    if not req or not req.product_type or not req.market:
        return "clarify"
        
    return "retrieve_catalog"

# 2. Build the state machine
builder = StateGraph(AgentState)

# Register nodes
builder.add_node("extract_intent", extract_intent_node)
builder.add_node("clarify", clarify_node)
builder.add_node("retrieve_catalog", retrieve_catalog_node)
builder.add_node("calculate_pricing", calculate_pricing_node)
builder.add_node("rank_and_recommend", rank_and_recommend_node)
builder.add_node("execute_order", execute_order_node)

# Set entry point
builder.set_entry_point("extract_intent")

# Add edges
builder.add_conditional_edges(
    "extract_intent",
    route_after_extraction,
    {
        "clarify": "clarify",
        "retrieve_catalog": "retrieve_catalog",
        "execute_order": "execute_order"
    }
)

builder.add_edge("clarify", END)
builder.add_edge("retrieve_catalog", "calculate_pricing")
builder.add_edge("calculate_pricing", "rank_and_recommend")
builder.add_edge("rank_and_recommend", END)
builder.add_edge("execute_order", END)

# 3. Setup checkpoint memory saver
# Using SQLite database for state persistence checkpointing
try:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    memory = SqliteSaver(conn)
except Exception as e:
    logger.error(f"Failed to initialize SqliteSaver checkpoint: {e}. Falling back to in-memory checkpointer.")
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()

# Compile the graph
agent_graph = builder.compile(checkpointer=memory)
