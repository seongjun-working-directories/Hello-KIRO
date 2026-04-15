"""
Feature: ai-basic-law-chatbot, Property 7: 관리자 인증 키 검증
Validates: Requirements 6.4, 6.5
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from hypothesis import given, settings
from hypothesis import strategies as st
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --- Unit tests ---

@pytest.mark.anyio
async def test_missing_admin_key_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/admin/parse-law")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_wrong_admin_key_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/admin/parse-law", headers={"X-Admin-Key": "wrong-key"}
        )
    assert response.status_code == 401


# --- Property 7: 관리자 인증 키 검증 ---

# Feature: ai-basic-law-chatbot, Property 7: 관리자 인증 키 검증
@given(
    st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),  # printable ASCII only
        min_size=1,
        max_size=100,
    ).filter(lambda k: k != "changeme")
)
@settings(max_examples=100)
def test_property_invalid_key_always_returns_401(key: str):
    import asyncio

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/admin/parse-law", headers={"X-Admin-Key": key}
            )
        assert response.status_code == 401

    asyncio.run(_run())
