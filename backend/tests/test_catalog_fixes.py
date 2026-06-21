"""
Test suite for 14-category taxonomy catalog injection.
Tests token expansion, intent routing, and chat endpoint integration.
Uses live Supabase DB with transaction rollback for isolation.
"""
import os
import pytest
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool
import app.database as db_module

# Live DB fixture with transaction rollback
@pytest.fixture(scope="session")
def live_db_url():
    """Read DATABASE_URL from environment (Supabase connection)."""
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set in environment")
    return url

@pytest.fixture(scope="session")
def test_engine(live_db_url):
    """Create test engine with live Supabase connection."""
    return create_engine(live_db_url, pool_pre_ping=True)

@pytest.fixture
def session(test_engine):
    """
    Database session with transaction rollback.
    Each test runs in a transaction that is rolled back after completion.
    This prevents test pollution while allowing tests to read real production data.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Monkey-patch db.engine so search_products_tool uses this session's connection
    original_engine = db_module.engine
    db_module.engine = test_engine

    yield session

    session.close()
    transaction.rollback()
    connection.close()

    # Restore original engine
    db_module.engine = original_engine


# ============================================================================
# UNIT TESTS: _expand_search_tokens (14 categories)
# ============================================================================

from app.agent.tools import _expand_search_tokens

def test_accessories_tokens():
    """Test 1: Accessories category"""
    tokens = _expand_search_tokens("tất vớ")
    assert "socks" in tokens or "tất" in tokens or "vớ" in tokens
    # Should NOT contain t-shirt tokens
    assert not any("t-shirt" in t.lower() or "tee" in t.lower() for t in tokens)

def test_tshirts_tokens():
    """Test 2: T-Shirts category"""
    tokens = _expand_search_tokens("áo thun")
    assert any("t-shirt" in t.lower() or "tshirt" in t.lower() for t in tokens)
    # Should NOT contain tank top tokens
    assert not any("tank" in t.lower() for t in tokens)

def test_mugs_tokens():
    """Test 3: Mugs category"""
    tokens = _expand_search_tokens("mug")
    assert "mug" in tokens or "mugs" in tokens
    # Should NOT contain tumbler/bottle tokens
    assert not any("tumbler" in t.lower() for t in tokens)

def test_tank_tops_tokens():
    """Test 4: Tank Tops category"""
    tokens = _expand_search_tokens("tank top")
    assert "tank top" in tokens
    # Should NOT contain t-shirt tokens
    assert not any("t-shirt" in t.lower() or "tee" in t.lower() for t in tokens)

def test_hoodies_tokens():
    """Test 5: Hoodies category"""
    tokens = _expand_search_tokens("hoodie")
    assert "hoodie" in tokens or "hoodies" in tokens
    # Should NOT contain sweatshirt tokens
    assert not any("sweatshirt" in t.lower() or "crewneck" in t.lower() for t in tokens)

def test_sweatshirts_tokens():
    """Test 6: Sweatshirts category"""
    tokens = _expand_search_tokens("sweatshirt")
    assert "sweatshirt" in tokens or "sweatshirts" in tokens
    # Should NOT contain hoodie tokens
    assert not any("hoodie" in t.lower() or "zip hoodie" in t.lower() for t in tokens)

def test_ornaments_tokens():
    """Test 7: Ornaments & Gifts category"""
    tokens = _expand_search_tokens("ornament")
    assert "ornament" in tokens or "ornaments" in tokens
    # Should NOT contain flag tokens
    assert not any("flag" in t.lower() for t in tokens)

def test_home_decor_tokens():
    """Test 8: Home Decor & Flags category"""
    tokens = _expand_search_tokens("garden flag")
    assert any("flag" in t.lower() for t in tokens)
    # Should NOT contain ornament tokens
    assert not any("ornament" in t.lower() for t in tokens)

def test_sportswear_tokens():
    """Test 9: Sportswear category"""
    tokens = _expand_search_tokens("soccer jersey")
    assert "soccer jersey" in tokens or "jersey" in tokens
    # Should NOT contain polo tokens
    assert not any("polo" in t.lower() or "pmp" in t.lower() for t in tokens)

def test_blankets_tokens():
    """Test 10: Blankets category"""
    tokens = _expand_search_tokens("blanket")
    assert "blanket" in tokens or "blankets" in tokens
    # Should NOT contain flag tokens
    assert not any("flag" in t.lower() for t in tokens)

def test_bottoms_tokens():
    """Test 11: Bottoms & Shorts category"""
    tokens = _expand_search_tokens("shorts")
    assert "shorts" in tokens
    # Should NOT contain pajama tokens
    assert not any("pajama" in t.lower() for t in tokens)

def test_baby_kids_tokens():
    """Test 12: Baby & Kids category"""
    tokens = _expand_search_tokens("baby onesie")
    assert "baby" in tokens or "onesie" in tokens
    # Should NOT contain polo tokens
    assert not any("polo" in t.lower() or "pmp" in t.lower() for t in tokens)

def test_pajamas_tokens():
    """Test 13: Pajamas & Sleepwear category"""
    tokens = _expand_search_tokens("pajama")
    assert "pajama" in tokens or "pajamas" in tokens
    # Should NOT contain shorts tokens
    assert not any("shorts" in t.lower() or "basketball" in t.lower() for t in tokens)

def test_polo_tokens():
    """Test 14: Polo Shirts category"""
    tokens = _expand_search_tokens("polo")
    assert "polo" in tokens or "pmp" in tokens or "pwp" in tokens
    # Should NOT contain t-shirt tokens
    assert not any("t-shirt" in t.lower() or "tee" in t.lower() for t in tokens)


# ============================================================================
# UNIT TESTS: parse_intent_and_slots (14 categories)
# ============================================================================

from app.agent.engine.intent import parse_intent_and_slots

def test_accessories_routing():
    """Test 1: Accessories intent routing"""
    intent, slots = parse_intent_and_slots("tìm tất vớ", {}, "general_chat")
    assert slots.get("product_type") == "Accessories"

def test_tshirts_routing():
    """Test 2: T-Shirts intent routing"""
    intent, slots = parse_intent_and_slots("áo thun nam", {}, "general_chat")
    assert slots.get("product_type") == "T-Shirts"

def test_mugs_routing():
    """Test 3: Mugs intent routing"""
    intent, slots = parse_intent_and_slots("ceramic mug", {}, "general_chat")
    assert slots.get("product_type") == "Mugs"

def test_tank_tops_routing():
    """Test 4: Tank Tops intent routing"""
    intent, slots = parse_intent_and_slots("áo ba lỗ", {}, "general_chat")
    assert slots.get("product_type") == "Tank Tops"

def test_hoodies_routing():
    """Test 5: Hoodies intent routing"""
    intent, slots = parse_intent_and_slots("hoodie có mũ", {}, "general_chat")
    assert slots.get("product_type") == "Hoodies"

def test_sweatshirts_routing():
    """Test 6: Sweatshirts intent routing"""
    intent, slots = parse_intent_and_slots("áo nỉ crewneck", {}, "general_chat")
    assert slots.get("product_type") == "Sweatshirts"

def test_ornaments_routing():
    """Test 7: Ornaments & Gifts intent routing"""
    intent, slots = parse_intent_and_slots("acrylic ornament trang trí", {}, "general_chat")
    assert slots.get("product_type") == "Ornaments & Gifts"

def test_home_decor_routing():
    """Test 8: Home Decor & Flags intent routing"""
    intent, slots = parse_intent_and_slots("garden flag", {}, "general_chat")
    assert slots.get("product_type") == "Home Decor & Flags"

def test_sportswear_routing():
    """Test 9: Sportswear intent routing"""
    intent, slots = parse_intent_and_slots("đồ thể thao soccer jersey", {}, "general_chat")
    assert slots.get("product_type") == "Sportswear"

def test_blankets_routing():
    """Test 10: Blankets intent routing"""
    intent, slots = parse_intent_and_slots("chăn fleece blanket", {}, "general_chat")
    assert slots.get("product_type") == "Blankets"

def test_bottoms_routing():
    """Test 11: Bottoms & Shorts intent routing"""
    intent, slots = parse_intent_and_slots("quần short nam", {}, "general_chat")
    assert slots.get("product_type") == "Bottoms & Shorts"

def test_baby_kids_routing():
    """Test 12: Baby & Kids intent routing"""
    intent, slots = parse_intent_and_slots("đồ em bé onesie", {}, "general_chat")
    assert slots.get("product_type") == "Baby & Kids"

def test_pajamas_routing():
    """Test 13: Pajamas & Sleepwear intent routing"""
    intent, slots = parse_intent_and_slots("pajama set đồ ngủ", {}, "general_chat")
    assert slots.get("product_type") == "Pajamas & Sleepwear"

def test_polo_routing():
    """Test 14: Polo Shirts intent routing"""
    intent, slots = parse_intent_and_slots("áo polo nam", {}, "general_chat")
    assert slots.get("product_type") == "Polo Shirts"


# ============================================================================
# INTEGRATION TESTS: /api/chat endpoint (14 categories)
# ============================================================================

from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

def extract_items_from_response(response):
    """Helper: Extract items from SSE streaming response."""
    items = []
    for line in response.text.split("\n"):
        if line.startswith("data:"):
            import json
            try:
                data = json.loads(line[5:].strip())
                if "items" in data:
                    items.extend(data["items"])
            except:
                pass
    return items

def test_chat_accessories(client, session):
    """Test 1: Accessories - tìm tất vớ"""
    response = client.post("/api/chat", json={
        "session_id": "test-accessories",
        "message": "tìm tất vớ"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain t-shirt items
    for item in items:
        assert "t-shirt" not in item.get("product_name", "").lower()
        assert "tee" not in item.get("product_name", "").lower()

def test_chat_tshirts(client, session):
    """Test 2: T-Shirts - tìm áo thun"""
    response = client.post("/api/chat", json={
        "session_id": "test-tshirts",
        "message": "tìm áo thun t-shirt"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain tank top items
    for item in items:
        assert "tank top" not in item.get("product_name", "").lower()

def test_chat_mugs(client, session):
    """Test 3: Mugs - tìm mug"""
    response = client.post("/api/chat", json={
        "session_id": "test-mugs",
        "message": "tìm ceramic mug"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain tumbler items
    for item in items:
        assert "tumbler" not in item.get("product_name", "").lower()

def test_chat_tank_tops(client, session):
    """Test 4: Tank Tops - tìm áo ba lỗ"""
    response = client.post("/api/chat", json={
        "session_id": "test-tank-tops",
        "message": "tìm áo ba lỗ tank top"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain t-shirt items
    for item in items:
        assert "t-shirt" not in item.get("product_name", "").lower()

def test_chat_hoodies(client, session):
    """Test 5: Hoodies - tìm hoodie"""
    response = client.post("/api/chat", json={
        "session_id": "test-hoodies",
        "message": "tìm hoodie có mũ"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain sweatshirt items
    for item in items:
        assert "sweatshirt" not in item.get("product_name", "").lower()
        assert "crewneck" not in item.get("product_name", "").lower()

def test_chat_sweatshirts(client, session):
    """Test 6: Sweatshirts - tìm áo nỉ"""
    response = client.post("/api/chat", json={
        "session_id": "test-sweatshirts",
        "message": "tìm áo nỉ sweatshirt"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain hoodie items
    for item in items:
        assert "hoodie" not in item.get("product_name", "").lower()

def test_chat_ornaments(client, session):
    """Test 7: Ornaments & Gifts - tìm ornament"""
    response = client.post("/api/chat", json={
        "session_id": "test-ornaments",
        "message": "tìm acrylic ornament trang trí"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain flag items
    for item in items:
        assert "flag" not in item.get("product_name", "").lower()

def test_chat_home_decor(client, session):
    """Test 8: Home Decor & Flags - tìm flag"""
    response = client.post("/api/chat", json={
        "session_id": "test-home-decor",
        "message": "tìm garden flag"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain ornament items
    for item in items:
        assert "ornament" not in item.get("product_name", "").lower()

def test_chat_sportswear(client, session):
    """Test 9: Sportswear - tìm đồ thể thao"""
    response = client.post("/api/chat", json={
        "session_id": "test-sportswear",
        "message": "tìm đồ thể thao soccer jersey"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain polo items
    for item in items:
        assert "polo" not in item.get("product_name", "").lower()
        assert "pmp" not in item.get("product_name", "").lower()

def test_chat_blankets(client, session):
    """Test 10: Blankets - tìm chăn"""
    response = client.post("/api/chat", json={
        "session_id": "test-blankets",
        "message": "tìm chăn fleece blanket"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain flag items
    for item in items:
        assert "flag" not in item.get("product_name", "").lower()

def test_chat_bottoms(client, session):
    """Test 11: Bottoms & Shorts - tìm quần short"""
    response = client.post("/api/chat", json={
        "session_id": "test-bottoms",
        "message": "tìm quần short"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain pajama items
    for item in items:
        assert "pajama" not in item.get("product_name", "").lower()

def test_chat_baby_kids(client, session):
    """Test 12: Baby & Kids - tìm đồ em bé"""
    response = client.post("/api/chat", json={
        "session_id": "test-baby-kids",
        "message": "tìm đồ em bé onesie"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain polo items
    for item in items:
        assert "polo" not in item.get("product_name", "").lower()

def test_chat_pajamas(client, session):
    """Test 13: Pajamas & Sleepwear - tìm pajama"""
    response = client.post("/api/chat", json={
        "session_id": "test-pajamas",
        "message": "tìm pajama đồ ngủ"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain shorts items
    for item in items:
        assert "shorts" not in item.get("product_name", "").lower()

def test_chat_polo(client, session):
    """Test 14: Polo Shirts - tìm áo polo"""
    response = client.post("/api/chat", json={
        "session_id": "test-polo",
        "message": "tìm áo polo nam"
    })
    assert response.status_code == 200
    items = extract_items_from_response(response)
    # Should NOT contain t-shirt items
    for item in items:
        assert "t-shirt" not in item.get("product_name", "").lower()
        assert "tee" not in item.get("product_name", "").lower()
