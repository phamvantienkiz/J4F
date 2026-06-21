import os
os.environ["TESTING"] = "True"

import pytest
import asyncio
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
import app.database as database_module
from app.models.catalog import Product, ProductVariant
from app.agent.engine.intent import parse_intent_and_slots
from app.agent.tools import _expand_search_tokens

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

@pytest.fixture(name="session", scope="function", autouse=True)
def session_fixture():
    original_engine = database_module.engine
    database_module.engine = test_engine
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)
    database_module.engine = original_engine

def test_accessories_mapping_and_exceptions():
    # Kiểm tra phân tích intent khi tìm phụ kiện/tất/vớ và các phụ kiện trang trí
    for query in [
        "tôi muốn tìm tất",
        "tôi muốn tìm phụ kiện trang trí",
        "tôi muốn tìm sticker",
        "tôi muốn tìm keychain",
        "tôi muốn tìm stickers",
        "tôi muốn tìm keychains",
        "tôi muốn tìm móc khóa",
        "tôi muốn tìm moc khoa",
    ]:
        intent, slots = parse_intent_and_slots(query, {}, None)
        assert slots.get("product_type") == "Accessories"

    # Kiểm tra expand tokens cho tất không bị ép thành Polo
    tokens = _expand_search_tokens("tất")
    assert "socks" in tokens or "sock" in tokens
    assert "polo" not in tokens

def test_tshirt_vs_tank_top_bleeding():
    # Nếu tìm kiếm áo thun (t-shirt), token của tank top / ba lỗ phải bị loại bỏ
    tokens = _expand_search_tokens("áo thun")
    assert "t-shirt" in tokens
    assert "tank top" not in tokens
    assert "ba lỗ" not in tokens

def test_pure_margin_preserves_context():
    from app.agent.engine.intent import is_pure_pricing_adjustment_fn
    # Xác định pricing adjustment thuần túy
    assert is_pure_pricing_adjustment_fn("Tính margin với giá bán lẻ $30") is True
    assert is_pure_pricing_adjustment_fn("áo polo giá bán lẻ $30") is False

    # Kiểm tra bảo toàn slots trong intent parser
    intent, slots = parse_intent_and_slots(
        "Tính margin với giá bán lẻ $30",
        {"product_type": "polo", "sku": "ZPBJ-Polo-S"},
        "calculate_margin"
    )
    assert slots.get("product_type") == "polo"
    assert slots.get("sku") == "ZPBJ-Polo-S"


@pytest.mark.asyncio
async def test_heuristic_flow_margin_preservation(session):
    from app.agent.engine.heuristic import execute_heuristic_flow

    # Tạo mock engine đơn giản
    class MockEngine:
        def __init__(self):
            self.trend_service = None

    engine = MockEngine()

    # Giả lập slots khi đã tìm thấy product_type và sku trước đó
    slots = {"product_type": "polo", "sku": "ZPBJ-Polo-S", "country": "US"}
    message = "Tính margin với giá bán lẻ $30"

    # Chạy heuristic flow
    res = await execute_heuristic_flow(
        engine=engine,
        intent="calculate_margin",
        slots=slots,
        message=message,
        lang="vi",
        country_code="US",
        history=[{"role": "user", "content": "áo polo"}, {"role": "assistant", "content": "Đây là áo polo..."}]
    )

    # Phải kế thừa đúng product_type và sku
    assert res["metadata"]["product_type"] == "polo"
    assert res["metadata"]["sku"] == "ZPBJ-Polo-S"
