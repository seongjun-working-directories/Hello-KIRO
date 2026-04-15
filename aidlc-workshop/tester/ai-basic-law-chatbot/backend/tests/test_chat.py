"""
Feature: ai-basic-law-chatbot
Property 1: 입력 길이 경계 검증 (Validates: Requirements 1.3, 1.4)
Property 2: 응답 구조 완전성 (Validates: Requirements 2.2, 2.3)
Property 3: 개선 권고사항 구조 완전성 (Validates: Requirements 3.1, 3.2, 3.3)
"""
import pytest
import hypothesis
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from hypothesis import given, settings
from hypothesis import strategies as st
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


# Rate Limiter를 항상 통과시키는 패치
RATE_LIMIT_PATCH = patch(
    "app.middleware.rate_limiter._limiter.is_allowed",
    return_value=True,
)


# --- Property 1: 입력 길이 경계 검증 ---

# Feature: ai-basic-law-chatbot, Property 1: 입력 길이 경계 검증
@given(st.integers(min_value=5001, max_value=6000))
@settings(max_examples=50)
def test_property_input_too_long_returns_400(length: int):
    import asyncio
    text = "가" * length

    async def _run():
        with RATE_LIMIT_PATCH:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/chat",
                    json={"message": text, "session_id": "test-session", "history": []},
                )
            assert response.status_code == 400

    asyncio.run(_run())


@pytest.mark.anyio
async def test_input_exactly_5000_chars_is_accepted():
    """5000자 정확히는 허용되어야 한다 (OpenAI 모킹)."""
    message = "가" * 5000

    async def fake_stream(*args, **kwargs):
        yield "분석 결과입니다."

    with RATE_LIMIT_PATCH:
        with patch("app.routers.chat.openai_service") as mock_svc:
            mock_svc.stream_chat = fake_stream
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/chat",
                    json={"message": message, "session_id": "test-session", "history": []},
                )
    assert response.status_code == 200
