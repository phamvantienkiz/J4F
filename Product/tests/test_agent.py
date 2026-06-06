from ai.agent import agent_graph
from ai.state import Requirements, UserPreference

def test_agent_clarify_flow():
    # Test case: missing product type and market should route to clarify
    initial_state = {
        "thread_id": "test_thread_1",
        "user_preferences": UserPreference(preferred_market="US", target_margin=40.0),
        "conversation_history": [{"sender": "user", "content": "Xin chào"}],
        "requirements": Requirements(product_type=None, market=None),
        "candidates": [],
        "calculated_options": [],
        "ranking_results": [],
        "last_missing_fields": [],
        "order_draft": None,
        "order_status": None
    }
    
    config = {"configurable": {"thread_id": "test_thread_1"}}
    # Execute the graph
    output = agent_graph.invoke(initial_state, config)
    
    # Verify that it went to clarify node
    assert len(output["last_missing_fields"]) > 0
    assert any("loại sản phẩm" in field or "thị trường" in field for field in output["last_missing_fields"])

def test_agent_retrieve_flow():
    # Test case: full requirements should route to retrieve_catalog, calculate_pricing, rank_and_recommend
    initial_state = {
        "thread_id": "test_thread_2",
        "user_preferences": UserPreference(preferred_market="US", target_margin=40.0),
        "conversation_history": [{"sender": "user", "content": "Tìm xưởng in Unisex T-Shirt tại thị trường US"}],
        "requirements": Requirements(product_type="Classic Unisex T-Shirt", market="US"),
        "candidates": [],
        "calculated_options": [],
        "ranking_results": [],
        "last_missing_fields": [],
        "order_draft": None,
        "order_status": None
    }
    
    config = {"configurable": {"thread_id": "test_thread_2"}}
    # Execute the graph
    output = agent_graph.invoke(initial_state, config)
    
    # Verify calculation and ranking completed
    assert len(output["candidates"]) > 0
    assert len(output["calculated_options"]) > 0
    assert len(output["ranking_results"]) > 0
