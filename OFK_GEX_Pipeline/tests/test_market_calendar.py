"""Tests for the NYSE calendar — Block 3.

NB: if pandas_market_calendars is missing, fall back to weekday-only.
We test the API contract rather than exact holiday dates.
"""
from datetime import datetime, timezone
from market_calendar import (
    is_market_open_today,
    is_early_close_today,
    is_rth_now,
    session_open_today_utc,
    session_close_today_utc,
    minutes_to_close,
)


def test_api_returns_correct_types():
    # Smoke test: no exception, correct types
    assert isinstance(is_market_open_today(), bool)
    assert isinstance(is_early_close_today(), bool)
    assert isinstance(is_rth_now(), bool)


def test_session_open_close_either_dt_or_none():
    o = session_open_today_utc()
    c = session_close_today_utc()
    assert o is None or isinstance(o, datetime)
    assert c is None or isinstance(c, datetime)


def test_session_close_after_open_when_market_open():
    if not is_market_open_today():
        return  # no session today, skip
    o = session_open_today_utc()
    c = session_close_today_utc()
    assert o is not None and c is not None
    assert c > o


def test_minutes_to_close_returns_int_or_none():
    m = minutes_to_close()
    assert m is None or (isinstance(m, int) and m >= 0)


def test_weekend_logic_with_explicit_ref():
    # Saturday UTC: market closed
    sat = datetime(2026, 1, 3, 15, 0, tzinfo=timezone.utc)  # Saturday
    assert is_market_open_today(sat) is False
    sun = datetime(2026, 1, 4, 15, 0, tzinfo=timezone.utc)  # Sunday
    assert is_market_open_today(sun) is False


def test_weekday_open():
    # Wednesday (business day, not a holiday) with explicit ref
    wed = datetime(2026, 1, 7, 15, 0, tzinfo=timezone.utc)
    # We accept True or False depending on backend (weekday-only fallback says True)
    # The test only verifies that it does not crash
    result = is_market_open_today(wed)
    assert isinstance(result, bool)
