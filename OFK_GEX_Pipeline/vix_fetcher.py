"""
vix_fetcher.py — VIX + VIX9D fetcher pour contextualiser le régime de volatilité.

Source : yfinance (^VIX, ^VIX9D). Gratuit, ~15 min delayed mais OK pour scoring de régime.

API :
- fetch_vix() -> dict avec :
    vix             : VIX spot
    vix9d           : VIX9D spot
    vix_regime      : "low" (<14) | "normal" (14-20) | "elevated" (20-28) | "extreme" (>28)
    vix_term        : "backwardation" (VIX9D > VIX +0.5) | "flat" | "contango"
    vix_term_slope  : VIX9D - VIX
    vix_dod_change  : variation jour vs veille (en points VIX, signé)
"""

from __future__ import annotations

import logging
from typing import Dict

log = logging.getLogger(__name__)


def _classify_regime(vix: float) -> str:
    if vix <= 0:    return "unknown"
    if vix < 14:    return "low"
    if vix < 20:    return "normal"
    if vix < 28:    return "elevated"
    return "extreme"


def _classify_term(vix: float, vix9d: float) -> str:
    if vix <= 0 or vix9d <= 0:
        return "unknown"
    slope = vix9d - vix
    if slope > 0.5:
        return "backwardation"
    if slope < -0.5:
        return "contango"
    return "flat"


def fetch_vix() -> Dict:
    """Récupère VIX + VIX9D + métriques dérivées. Renvoie {} en cas d'échec."""
    try:
        import yfinance as yf
    except ImportError:
        log.warning("yfinance absent — pip install yfinance")
        return {}

    try:
        # period 5d pour avoir une close veille pour DoD change
        vix_hist   = yf.Ticker("^VIX").history(period="5d", interval="1d")
        vix9d_hist = yf.Ticker("^VIX9D").history(period="5d", interval="1d")
    except Exception as e:
        log.warning(f"VIX yfinance échec: {e}")
        return {}

    if vix_hist.empty:
        log.warning("VIX history vide")
        return {}

    vix_last  = float(vix_hist["Close"].iloc[-1])
    vix_prev  = float(vix_hist["Close"].iloc[-2]) if len(vix_hist) >= 2 else vix_last
    vix9d_last = float(vix9d_hist["Close"].iloc[-1]) if not vix9d_hist.empty else 0.0

    return {
        "vix"            : round(vix_last, 2),
        "vix9d"          : round(vix9d_last, 2),
        "vix_regime"     : _classify_regime(vix_last),
        "vix_term"       : _classify_term(vix_last, vix9d_last),
        "vix_term_slope" : round(vix9d_last - vix_last, 2) if vix9d_last > 0 else 0.0,
        "vix_dod_change" : round(vix_last - vix_prev, 2),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data = fetch_vix()
    if not data:
        print("ECHEC fetch VIX")
    else:
        print(f"VIX        : {data['vix']:.2f}  (DoD {data['vix_dod_change']:+.2f})")
        print(f"VIX9D      : {data['vix9d']:.2f}")
        print(f"Régime     : {data['vix_regime']}")
        print(f"Term       : {data['vix_term']}  (slope {data['vix_term_slope']:+.2f})")
