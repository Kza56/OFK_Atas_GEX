"""
market_calendar.py — Official NYSE calendar (DST + US holidays + early close).

Uses pandas_market_calendars to correctly handle:
- US Daylight Saving Time (DST) automatic → bug-free UTC ↔ ET conversion
- Holidays (Thanksgiving, Christmas, MLK, July 4th, etc.) → market closed
- Early close (Thanksgiving eve 13:00 ET, Christmas Eve, July 3rd) → 13:00 ET

If pandas_market_calendars is missing → approximate fallback (UTC window 13:30-20:00).

Public API:
- is_rth_now() -> bool             : RTH market open RIGHT NOW
- is_market_open_today() -> bool   : NYSE open today (no weekend/holiday)
- is_early_close_today() -> bool   : early close today (13:00 ET)
- session_close_today_utc() -> datetime|None : UTC close time today
- minutes_to_close() -> int|None   : minutes remaining before close (None if closed)
"""

from __future__ import annotations

import logging
from datetime import datetime, time as dtime, timezone, timedelta
from typing import Optional

log = logging.getLogger(__name__)

try:
    import pandas_market_calendars as mcal
    import pandas as pd
    _NYSE = mcal.get_calendar("NYSE")
    _BACKEND = "pandas_market_calendars"
except ImportError:
    _NYSE = None
    _BACKEND = "fallback"
    log.warning("pandas_market_calendars missing — approximate fallback (no DST/holidays). "
                "Install with: pip install pandas_market_calendars")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_market_open_today(ref: Optional[datetime] = None) -> bool:
    """True if NYSE is open today (no weekend, no holiday)."""
    ref = ref or _now_utc()
    if _NYSE is None:
        return ref.weekday() < 5  # fallback: weekend only

    try:
        sched = _NYSE.schedule(start_date=ref.date(), end_date=ref.date())
        return not sched.empty
    except Exception as e:
        log.debug(f"is_market_open_today fallback: {e}")
        return ref.weekday() < 5


def is_early_close_today(ref: Optional[datetime] = None) -> bool:
    """True if early close (close 13:00 ET instead of 16:00)."""
    ref = ref or _now_utc()
    if _NYSE is None:
        return False

    try:
        sched = _NYSE.schedule(start_date=ref.date(), end_date=ref.date())
        if sched.empty:
            return False
        close_utc = sched.iloc[0]["market_close"].to_pydatetime()
        # close in UTC. ET=UTC-5 (EST) or UTC-4 (EDT). 16:00 ET = 20:00 or 21:00 UTC.
        # Early close 13:00 ET = 17:00 or 18:00 UTC.
        # We consider it early close if close < 19:00 UTC.
        return close_utc.hour < 19
    except Exception:
        return False


def session_close_today_utc(ref: Optional[datetime] = None) -> Optional[datetime]:
    """UTC datetime of today's NYSE close. None if market closed."""
    ref = ref or _now_utc()
    if _NYSE is None:
        # Fallback: 20:00 UTC (16:00 EST) — incorrect under DST but a simple approximation
        if ref.weekday() >= 5:
            return None
        return ref.replace(hour=20, minute=0, second=0, microsecond=0)

    try:
        sched = _NYSE.schedule(start_date=ref.date(), end_date=ref.date())
        if sched.empty:
            return None
        return sched.iloc[0]["market_close"].to_pydatetime()
    except Exception:
        return None


def session_open_today_utc(ref: Optional[datetime] = None) -> Optional[datetime]:
    """UTC datetime of today's NYSE open. None if market closed."""
    ref = ref or _now_utc()
    if _NYSE is None:
        if ref.weekday() >= 5:
            return None
        return ref.replace(hour=13, minute=30, second=0, microsecond=0)

    try:
        sched = _NYSE.schedule(start_date=ref.date(), end_date=ref.date())
        if sched.empty:
            return None
        return sched.iloc[0]["market_open"].to_pydatetime()
    except Exception:
        return None


def is_rth_now(ref: Optional[datetime] = None) -> bool:
    """True if we are CURRENTLY in NYSE RTH session (open <= now <= close)."""
    ref = ref or _now_utc()
    open_utc  = session_open_today_utc(ref)
    close_utc = session_close_today_utc(ref)
    if open_utc is None or close_utc is None:
        return False
    return open_utc <= ref <= close_utc


def minutes_to_close(ref: Optional[datetime] = None) -> Optional[int]:
    """Minutes remaining before the RTH close. None if market closed or outside session."""
    ref = ref or _now_utc()
    close_utc = session_close_today_utc(ref)
    if close_utc is None or ref > close_utc:
        return None
    if ref < (session_open_today_utc(ref) or close_utc):
        return None
    return int((close_utc - ref).total_seconds() // 60)


# Backward compat: alias for run_intraday_refresh.py
def is_rth_now_et() -> bool:
    """Legacy alias. Use is_rth_now() instead."""
    return is_rth_now()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    now = _now_utc()
    print(f"Backend       : {_BACKEND}")
    print(f"Now (UTC)     : {now.isoformat()}")
    print(f"Market open today : {is_market_open_today()}")
    print(f"Early close today : {is_early_close_today()}")
    print(f"Session open  UTC : {session_open_today_utc()}")
    print(f"Session close UTC : {session_close_today_utc()}")
    print(f"Is RTH now    : {is_rth_now()}")
    mtc = minutes_to_close()
    print(f"Minutes to close  : {mtc if mtc is not None else 'N/A (closed)'}")
