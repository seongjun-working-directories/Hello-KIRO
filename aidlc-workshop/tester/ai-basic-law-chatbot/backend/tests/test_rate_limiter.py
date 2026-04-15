"""
Feature: ai-basic-law-chatbot, Property 8: Rate Limiting 슬라이딩 윈도우
Validates: Requirements 7.1, 7.2, 7.4
"""
import time
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from app.middleware.rate_limiter import SlidingWindowRateLimiter


def make_limiter():
    return SlidingWindowRateLimiter(max_requests=5, window_seconds=600)


# --- Unit tests ---

def test_allows_up_to_max_requests():
    limiter = make_limiter()
    for _ in range(5):
        assert limiter.is_allowed("1.2.3.4") is True


def test_blocks_on_exceeding_limit():
    limiter = make_limiter()
    for _ in range(5):
        limiter.is_allowed("1.2.3.4")
    assert limiter.is_allowed("1.2.3.4") is False


def test_different_ips_are_independent():
    limiter = make_limiter()
    for _ in range(5):
        limiter.is_allowed("1.1.1.1")
    assert limiter.is_allowed("2.2.2.2") is True


def test_get_retry_after_returns_positive_when_blocked():
    limiter = make_limiter()
    for _ in range(5):
        limiter.is_allowed("1.2.3.4")
    assert limiter.get_retry_after("1.2.3.4") > 0


def test_window_expiry_allows_new_requests():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=1)
    limiter.is_allowed("1.2.3.4")
    limiter.is_allowed("1.2.3.4")
    assert limiter.is_allowed("1.2.3.4") is False
    time.sleep(1.1)
    assert limiter.is_allowed("1.2.3.4") is True


# --- Property-based tests ---

# Feature: ai-basic-law-chatbot, Property 8: Rate Limiting 슬라이딩 윈도우
@given(st.integers(min_value=1, max_value=5))
@settings(max_examples=100)
def test_property_allows_up_to_5_requests(n: int):
    limiter = make_limiter()
    for _ in range(n):
        assert limiter.is_allowed("10.0.0.1") is True


# Feature: ai-basic-law-chatbot, Property 8: Rate Limiting 슬라이딩 윈도우
@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=100)
def test_property_blocks_after_5_requests(extra: int):
    limiter = make_limiter()
    for _ in range(5):
        limiter.is_allowed("10.0.0.2")
    for _ in range(extra):
        assert limiter.is_allowed("10.0.0.2") is False
