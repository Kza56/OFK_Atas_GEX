"""
econ_calendar.py — Calendrier économique US (Forex Factory) avec blackout window.

Source : Forex Factory hebdomadaire CSV (gratuit).
URLs :
  https://nfs.faireconomy.media/ff_calendar_thisweek.csv
  https://nfs.faireconomy.media/ff_calendar_nextweek.csv

Filtre : USD seulement, impact High par défaut (FOMC, NFP, CPI, PCE, ISM, GDP, retail, etc.).

API :
- fetch_econ_events(min_impact="High") -> List[dict] : événements à risque
- blackout_status(now_utc, blackout_minutes=30) -> dict :
    {in_blackout, blackout_until_utc, current_event, next_event, minutes_to_next}

Utilisation pendant scalping :
- Si in_blackout=True → bannière rouge dans ATAS, signaux désactivés
- Si minutes_to_next < 30 → préparer le retrait des stops
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

# Cache module-level (évite refetch dans la même boucle intraday)
_events_cache: List[Dict] = []
_cache_fetched_at: Optional[datetime] = None
_CACHE_TTL_SECONDS = 1800   # 30 min : ForexFactory ne bouge pas plus vite


def _et_to_utc(dt_naive: datetime) -> Optional[datetime]:
    """Convertit datetime naïve ET (Eastern Time) en datetime UTC aware.
    Utilise pytz si dispo (DST correct), sinon fallback statique ET=UTC-5."""
    try:
        import pytz
        et = pytz.timezone("America/New_York")
        return et.localize(dt_naive).astimezone(timezone.utc)
    except ImportError:
        # Fallback statique — incorrect en DST, mais évite crash si pytz absent
        return dt_naive.replace(tzinfo=timezone(timedelta(hours=-5))).astimezone(timezone.utc)


def fetch_econ_events(min_impact: str = "High",
                       force_refresh: bool = False) -> List[Dict]:
    """Fetch Forex Factory calendar pour USD, filtre par impact.

    Cache TTL 30 min. Renvoie liste vide si fetch échoue.
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
        log.warning("requests absent — econ_calendar désactivé")
        return []

    for url in FF_CSV_URLS:
        try:
            resp = requests.get(url, timeout=10,
                                 headers={"User-Agent": "Mozilla/5.0 (OFK_Suite/1.0)"})
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"Forex Factory fetch échoué [{url}]: {e}")
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
            log.warning(f"Parse FF CSV échoué [{url}]: {e}")
            continue

    events.sort(key=lambda e: e["datetime_utc"])
    _events_cache = events
    _cache_fetched_at = now
    log.info(f"Forex Factory : {len(events)} événements USD impact={min_impact}")
    return events


def blackout_status(now_utc: Optional[datetime] = None,
                     blackout_minutes: int = 30,
                     min_impact: str = "High") -> Dict:
    """Statut blackout autour des événements éco US à risque.

    blackout_minutes : fenêtre symétrique avant/après l'événement.

    Returns dict :
      in_blackout         : bool
      blackout_until_utc  : ISO str ou None
      current_event       : dict (titre, dt, impact, forecast, previous) ou None
      next_event          : dict ou None
      minutes_to_next     : int ou None
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
        # Skip si déjà passé bien au-delà de la fenêtre blackout
        if delta_min < -blackout_minutes:
            continue
        # Dans la fenêtre blackout
        if -blackout_minutes <= delta_min <= blackout_minutes:
            blackout_until = ev_dt + timedelta(minutes=blackout_minutes)
            return {
                "in_blackout"       : True,
                "blackout_until_utc": blackout_until.isoformat(),
                "current_event"     : ev,
                "next_event"        : None,
                "minutes_to_next"   : 0,
            }
        # Premier événement futur hors fenêtre → c'est le next
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
        print(f"  Événement actif : {ev['title']} @ {ev['datetime_utc']} ({ev['impact']})")
    if status["next_event"]:
        ev = status["next_event"]
        print(f"  Prochain événement : {ev['title']} @ {ev['datetime_utc']} "
              f"dans {status['minutes_to_next']} min ({ev['impact']})")
    if status["blackout_until_utc"]:
        print(f"  Blackout jusqu'à : {status['blackout_until_utc']}")
    print(f"\n(Cache: {len(_events_cache)} événements en cache)")
