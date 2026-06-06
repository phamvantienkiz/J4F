import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

async def get_auth_headers(ac: AsyncClient, email: str) -> dict:
    """
    Helper to register a new user and retrieve their authorization headers.
    """
    # 1. Register
    await ac.post("/api/v1/auth/register", json={
        "email": email,
        "password": "testpassword123",
        "store_name": "My test store"
    })
    # 2. Login
    res = await ac.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpassword123"
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to BurgerPrints Agent API Gateway"

@pytest.mark.asyncio
async def test_auth_workflow():
    local_email = f"seller_test_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register a test user
        register_payload = {
            "email": local_email,
            "password": "testpassword123",
            "store_name": "My test store"
        }
        res_register = await ac.post("/api/v1/auth/register", json=register_payload)
        assert res_register.status_code == 200
        assert "access_token" in res_register.json()

        # 2. Login
        login_payload = {
            "email": local_email,
            "password": "testpassword123"
        }
        res_login = await ac.post("/api/v1/auth/login", json=login_payload)
        assert res_login.status_code == 200
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Get profile
        res_me = await ac.get("/api/v1/auth/me", headers=headers)
        assert res_me.status_code == 200
        assert res_me.json()["email"] == local_email

        # 4. Get preferences
        res_pref = await ac.get("/api/v1/auth/preference", headers=headers)
        assert res_pref.status_code == 200
        assert res_pref.json()["preferred_market"] == "US"

        # 5. Update preferences
        pref_update = {
            "preferred_market": "EU",
            "target_margin": 45.0,
            "fulfillment_priority": "speed"
        }
        res_update_pref = await ac.put("/api/v1/auth/preference", json=pref_update, headers=headers)
        assert res_update_pref.status_code == 200
        assert res_update_pref.json()["preferred_market"] == "EU"
        assert res_update_pref.json()["target_margin"] == 45.0

@pytest.mark.asyncio
async def test_chat_workflow():
    local_email = f"seller_test_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = await get_auth_headers(ac, local_email)

        # 1. Create conversation
        res_conv = await ac.post("/api/v1/chat/conversations", headers=headers)
        assert res_conv.status_code == 200
        conv_id = res_conv.json()["id"]

        # 2. Send message (should trigger clarify since requirements are empty)
        msg_payload = {"content": "Tìm xưởng in áo thun"}
        res_msg = await ac.post(f"/api/v1/chat/conversations/{conv_id}/message", json=msg_payload, headers=headers)
        assert res_msg.status_code == 200
        assert len(res_msg.json()["messages"]) > 0
        latest_reply = res_msg.json()["messages"][-1]["content"]
        assert "thị trường" in latest_reply or "loại sản phẩm" in latest_reply or "xưởng" in latest_reply
