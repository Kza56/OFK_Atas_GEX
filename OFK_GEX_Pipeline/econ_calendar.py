"""
econ_calendar.py — US economic calendar (Forex Factory) with blackout window.

Source: Forex Factory weekly CSV (free).
URLs:
  https://nfs.faireconomy.media/ff_calendar_thisweek.csv
  https://nfs.faireconomy.media/ff_calendar_nextweek.csv

Filter: USD only, impact High by default (FOMC, NFP, CPI, PCE, ISM, GDP, retail, etc.).

API:
- fetch_econ_events(min_impact="High") -> List[dict] : risk events
- blackout_status(now_utc, blackout_minutes=30) -> dict:
    {in_blackout, blackout_until_utc, current_event, next_event, minutes_to_next}

Usage during scalping:
- If in_blackout=True → red banner in ATAS, signals disabled
- If minutes_to_next < 30 → prepare to pull stops
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

FF_CSV_URLS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.csv",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.csv",
]

# Module-level cache (avoids refetch in the same intraday loop)
_events_cache: List[Dict] = []
_cache_fetched_at: Optional[datetime] = None
_CACHE_TTL_SECONDS = 1800   # 30 min: ForexFactory does not change faster than this


def _et_to_utc(dt_naive: datetime) -> Optional[datetime]:
    """Convert a naive ET (Eastern Time) datetime to a UTC-aware datetime.
    Uses pytz if available (DST correct), otherwise static ET=UTC-5 fallback."""
    try:
        import pytz
        et = pytz.timezone("America/New_York")
        return et.localize(dt_naive).astimezone(timezone.utc)
    except ImportError:
        # Static fallback — incorrect under DST, but avoids crash if pytz missing
        return dt_naive.replace(tzinfo=timezone(timedelta(hours=-5))).astimezone(timezone.utc)


def fetch_econ_events(min_impact: str = "High",
                       force_refresh: bool = False) -> List[Dict]:
    """Fetch Forex Factory calendar for USD, filtered by impact.

    Cache TTL 30 min. Returns empty list on fetch failure.
    """
    global _events_cache, _cache_fetched_at

    now = datetime.now(timezone.utc)
    if (not force_refresh and _cache_fetched_at and
            (now - _cache_fetched_at).total_seconds() < _CACHE_TTL_SECONDS):
        return _events_cache

    impacts_allowed = {"High"} if min_impact == "High" else {"High", "Medium"}
    events: List[Dict] = []

    try:
        import requests
    except ImportError:
        log.warning("requests missing — econ_calendar disabled")
        return []

    for url in FF_CSV_URLS:
        try:
            resp = requests.get(url, timeout=10,
                                 headers={"User-Agent": "Mozilla/5.0 (OFK_Atas_GEX/1.0)"})
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"Forex Factory fetch failed [{url}]: {e}")
            continue

        try:
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                if row.get("Country") != "USD":
                    continue
                if row.get("Impact") not in impacts_allowed:
                    continue
                date_str = row.get("Date", "").strip()
                time_str = row.get("Time", "").strip()
                if not date_str or time_str.lower() in ("all day", "tentative", ""):
                    continue
                try:
                    dt_naive = datetime.strptime(f"{date_str} {time_str}",
                                                   "%m-%d-%Y %I:%M%p")
                except ValueError:
                    continue
                dt_utc = _et_to_utc(dt_naive)
                if dt_utc is None:
                    continue
                events.append({
                    "title"       : row.get("Title", "").strip(),
                    "datetime_utc": dt_utc.isoformat(),
                    "impact"      : row.get("Impact", ""),
                    "forecast"    : (row.get("Forecast", "") or "").strip() or None,
                    "previous"    : (row.get("Previous", "") or "").strip() or None,
                })
        except Exception as e:
            log.warning(f"Parse FF CSV failed [{url}]: {e}")
            continue

    events.sort(key=lambda e: e["datetime_utc"])
    _events_cache = events
    _cache_fetched_at = now
    log.info(f"Forex Factory: {len(events)} USD events impact={min_impact}")
    return events


def blackout_status(now_utc: Optional[datetime] = None,
                     blackout_minutes: int = 30,
                     min_impact: str = "High") -> Dict:
    """Blackout status around US risky econ events.

    blackout_minutes: symmetric window before/after the event.

    Returns dict:
      in_blackout         : bool
      blackout_until_utc  : ISO str or None
      current_event       : dict (title, dt, impact, forecast, previous) or None
      next_event          : dict or None
      minutes_to_next     : int or None
    """
    now_utc = now_utc or datetime.now(timezone.utc)
    events  = fetch_econ_events(min_impact=min_impact)
    empty   = {"in_blackout": False, "blackout_until_utc": None,
               "current_event": None, "next_event": None, "minutes_to_next": None}
    if not events:
        return empty

    next_ev = None
    for ev in events:
        try:
            ev_dt = datetime.fromisoformat(ev["datetime_utc"])
        except Exception:
            continue
        delta_min = (ev_dt - now_utc).total_seconds() / 60
        # Skip if already passed well beyond the blackout window
        if delta_min < -blackout_minutes:
            continue
        # Inside the blackout window
        if -blackout_minutes <= delta_min <= blackout_minutes:
            blackout_until = ev_dt + timedelta(minutes=blackout_minutes)
            return {
                "in_blackout"       : True,
                "blackout_until_utc": blackout_until.isoformat(),
                "current_event"     : ev,
                "next_event"        : None,
                "minutes_to_next"   : 0,
            }
        # First future event outside the window → that's the next
        if delta_min > blackout_minutes:
            next_ev = ev
            return {
                "in_blackout"       : False,
                "blackout_until_utc": None,
                "current_event"     : None,
                "next_event"        : ev,
                "minutes_to_next"   : int(delta_min),
            }

    return empty


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    status = blackout_status()
    print(f"In blackout : {status['in_blackout']}")
    if status["current_event"]:
        ev = status["current_event"]
        print(f"  Active event: {ev['title']} @ {ev['datetime_utc']} ({ev['impact']})")
    if status["next_event"]:
        ev = status["next_event"]
        print(f"  Next event: {ev['title']} @ {ev['datetime_utc']} "
              f"in {status['minutes_to_next']} min ({ev['impact']})")
    if status["blackout_until_utc"]:
        print(f"  Blackout until: {status['blackout_until_utc']}")
    print(f"\n(Cache: {len(_events_cache)} cached events)")
