"""
market_calendar.py — Calendrier officiel NYSE (DST + jours fériés US + early close).

Utilise pandas_market_calendars pour gérer correctement :
- Heure d'été US (DST) automatique → conversion UTC ↔ ET sans bug
- Jours fériés (Thanksgiving, Christmas, MLK, July 4th, etc.) → marché fermé
- Early close (Thanksgiving veille 13:00 ET, Christmas Eve, July 3rd) → 13:00 ET

Si pandas_market_calendars absent → fallback approximatif (window UTC 13:30-20:00).

API publique :
- is_rth_now() -> bool             : marché RTH ouvert MAINTENANT
- is_market_open_today() -> bool   : NYSE ouvert aujourd'hui (pas weekend/holiday)
- is_early_close_today() -> bool   : early close aujourd'hui (13:00 ET)
- session_close_today_utc() -> datetime|None : heure close UTC ce jour
- minutes_to_close() -> int|None   : minutes restantes avant close (None si fermé)
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
    log.warning("pandas_market_calendars absent — fallback approximatif (sans DST/holidays). "
                "Installer avec: pip install pandas_market_calendars")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_market_open_today(ref: Optional[datetime] = None) -> bool:
    """True si NYSE ouverte aujourd'hui (pas weekend, pas jour férié)."""
    ref = ref or _now_utc()
    if _NYSE is None:
        return ref.weekday() < 5  # fallback : exclut weekend uniquement

    try:
        sched = _NYSE.schedule(start_date=ref.date(), end_date=ref.date())
        return not sched.empty
    except Exception as e:
        log.debug(f"is_market_open_today fallback: {e}")
        return ref.weekday() < 5


def is_early_close_today(ref: Optional[datetime] = None) -> bool:
    """True si early close (close 13:00 ET au lieu de 16:00)."""
    ref = ref or _now_utc()
    if _NYSE is None:
        return False

    try:
        sched = _NYSE.schedule(start_date=ref.date(), end_date=ref.date())
        if sched.empty:
            return False
        close_utc = sched.iloc[0]["market_close"].to_pydatetime()
        # close en UTC. ET=UTC-5 (EST) ou UTC-4 (EDT). 16:00 ET = 20:00 ou 21:00 UTC.
        # Early close 13:00 ET = 17:00 ou 18:00 UTC.
        # On considère early close si close < 19:00 UTC.
        return close_utc.hour < 19
    except Exception:
        return False


def session_close_today_utc(ref: Optional[datetime] = None) -> Optional[datetime]:
    """Datetime UTC de la close NYSE aujourd'hui. None si marché fermé."""
    ref = ref or _now_utc()
    if _NYSE is None:
        # Fallback : 20:00 UTC (16:00 EST) — incorrect en DST mais approximation simple
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
    """Datetime UTC de l'open NYSE aujourd'hui. None si marché fermé."""
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
    """True si on est PRESENTEMENT en session RTH NYSE (open <= now <= close)."""
    ref = ref or _now_utc()
    open_utc  = session_open_today_utc(ref)
    close_utc = session_close_today_utc(ref)
    if open_utc is None or close_utc is None:
        return False
    return open_utc <= ref <= close_utc


def minutes_to_close(ref: Optional[datetime] = None) -> Optional[int]:
    """Minutes restantes avant la close RTH. None si marché fermé ou hors session."""
    ref = ref or _now_utc()
    close_utc = session_close_today_utc(ref)
    if close_utc is None or ref > close_utc:
        return None
    if ref < (session_open_today_utc(ref) or close_utc):
        return None
    return int((close_utc - ref).total_seconds() // 60)


# Compat ascendante : alias pour run_intraday_refresh.py
def is_rth_now_et() -> bool:
    """Alias historique. Utiliser is_rth_now() à la place."""
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
