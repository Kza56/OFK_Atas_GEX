"""
data_fetcher_ES.py — CBOE SPY options chain fetcher (ES proxy)
Computes: Max Pain, Expected Move, PCR, GEX per strike, Top OI strikes
Converts SPY values to ES using the live SPY/ES ratio

Usage: python3 data_fetcher_ES.py
"""
import requests
import json
import re
import math
from datetime import datetime, timezone
from pathlib import Path

from config import ES_LEVELS_JSON

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/SPY.json"
HEADERS  = {"User-Agent": "Mozilla/5.0"}

OCC_RE = re.compile(r'^(.+?)(\d{6})([CP])(\d{8})$')

def parse_symbol(symbol: str) -> dict:
    m = OCC_RE.match(symbol)
    if not m:
        return {}
    ticker, date_str, cp, strike_raw = m.groups()
    return {
        "ticker"  : ticker,
        "expiry"  : datetime.strptime(date_str, "%y%m%d").date(),
        "type"    : "call" if cp == "C" else "put",
        "strike"  : int(strike_raw) / 1000
    }

def bs_gamma(S, K, T, r, sigma):
    """Black-Scholes gamma — used when CBOE gamma is missing."""
    if T <= 0 or sigma <= 0:
        return 0.0
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        return math.exp(-0.5 * d1**2) / (S * sigma * math.sqrt(T) * math.sqrt(2 * math.pi))
    except Exception:
        return 0.0

def fetch_chain() -> dict:
    r = requests.get(CBOE_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    raw   = r.json()["data"]
    spot  = float(raw["current_price"])
    today = datetime.now(timezone.utc).date()

    contracts = []
    for opt in raw["options"]:
        parsed = parse_symbol(opt.get("option", ""))
        if not parsed:
            continue
        oi     = float(opt.get("open_interest") or 0)
        iv     = float(opt.get("iv")            or 0)
        gamma  = float(opt.get("gamma")         or 0)
        strike = parsed["strike"]
        expiry = parsed["expiry"]
        dte    = (expiry - today).days

        if gamma == 0 and iv > 0 and dte > 0:
            T     = dte / 365
            gamma = bs_gamma(spot, strike, T, 0.05, iv)

        contracts.append({
            "symbol" : opt.get("option"),
            "type"   : parsed["type"],
            "strike" : strike,
            "expiry" : str(expiry),
            "dte"    : dte,
            "oi"     : oi,
            "volume" : float(opt.get("volume") or 0),
            "iv"     : iv,
            "gamma"  : gamma,
            "delta"  : float(opt.get("delta") or 0),
            "bid"    : float(opt.get("bid")   or 0),
            "ask"    : float(opt.get("ask")   or 0),
        })

    return {
        "spot"       : spot,
        "contracts"  : contracts,
        "fetched_at" : datetime.now(timezone.utc).isoformat()
    }

def calc_gex(contracts: list, spot: float) -> dict:
    """Compute Gamma Exposure: Gamma Flip, Call Wall, Put Wall, Net GEX."""
    by_strike = {}
    for c in contracts:
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "call_gex": 0.0, "put_gex": 0.0, "net_gex": 0.0}
        gex = c["gamma"] * c["oi"] * 100 * spot ** 2 * 0.01
        if c["type"] == "call":
            by_strike[k]["call_gex"] += gex
        else:
            by_strike[k]["put_gex"]  -= gex

    for k in by_strike:
        by_strike[k]["net_gex"] = by_strike[k]["call_gex"] + by_strike[k]["put_gex"]

    strikes = sorted(by_strike.values(), key=lambda x: x["strike"])

    # Gamma Flip
    gamma_flip = None
    cumulative = 0.0
    for s in strikes:
        prev       = cumulative
        cumulative += s["net_gex"]
        if prev != 0 and (prev < 0) != (cumulative < 0):
            gamma_flip = s["strike"]
            break

    call_wall_s = max(strikes, key=lambda x: x["call_gex"])
    put_wall_s  = min(strikes, key=lambda x: x["put_gex"])
    net_gex     = sum(s["net_gex"] for s in strikes)
    regime      = "positive" if net_gex >= 0 else "negative"

    return {
        "gamma_flip"    : gamma_flip,
        "call_wall"     : call_wall_s["strike"],
        "call_wall_gex" : round(call_wall_s["call_gex"], 0),
        "put_wall"      : put_wall_s["strike"],
        "put_wall_gex"  : round(put_wall_s["put_gex"], 0),
        "net_gex"       : round(net_gex, 0),
        "regime"        : regime,
    }

def calc_max_pain(contracts: list) -> float:
    strikes = sorted(set(c["strike"] for c in contracts))
    min_pain, max_pain_strike = float("inf"), strikes[0]
    for s in strikes:
        pain = 0.0
        for c in contracts:
            if c["type"] == "call" and s > c["strike"]:
                pain += (s - c["strike"]) * c["oi"] * 100
            elif c["type"] == "put" and s < c["strike"]:
                pain += (c["strike"] - s) * c["oi"] * 100
        if pain < min_pain:
            min_pain        = pain
            max_pain_strike = s
    return max_pain_strike

def calc_expected_move(spot: float, contracts: list) -> float:
    valid = [c for c in contracts if c["dte"] > 0 and c["iv"] > 0]
    if not valid:
        return 0.0
    nearest_expiry = min(valid, key=lambda x: x["dte"])["expiry"]
    dte = next(c["dte"] for c in valid if c["expiry"] == nearest_expiry)
    atm = [c for c in valid if c["expiry"] == nearest_expiry
           and abs(c["strike"] - spot) / spot < 0.02]
    if not atm:
        return 0.0
    avg_iv = sum(c["iv"] for c in atm) / len(atm)
    return round(spot * avg_iv * math.sqrt(dte / 365), 2)


def calc_expected_move_tt(contracts: list, spot: float) -> dict:
    """Expected Move TastyTrade-style (Phase 2).

    Weighted formula on ATM straddles/strangles:
        EM = (ATM_straddle × 0.6) + (1st_OTM_strangle × 0.3) + (2nd_OTM_strangle × 0.1)
    """
    valid = [c for c in contracts
             if c["dte"] >= 0 and (c["bid"] > 0 or c["ask"] > 0)]
    if not valid:
        return {}

    by_expiry: dict = {}
    for c in valid:
        by_expiry.setdefault(c["expiry"], []).append(c)
    nearest = min(by_expiry.keys(), key=lambda e: by_expiry[e][0]["dte"])
    nearest_dte = by_expiry[nearest][0]["dte"]
    chain = by_expiry[nearest]

    calls = sorted({c["strike"] for c in chain
                    if c["type"] == "call" and (c["bid"] > 0 or c["ask"] > 0)})
    puts  = sorted({c["strike"] for c in chain
                    if c["type"] == "put"  and (c["bid"] > 0 or c["ask"] > 0)})
    if not calls or not puts:
        return {}

    def mid(strike: float, side: str) -> float:
        items = [c for c in chain if c["strike"] == strike and c["type"] == side]
        if not items:
            return 0.0
        c = items[0]
        if c["bid"] > 0 and c["ask"] > 0:
            return (c["bid"] + c["ask"]) / 2.0
        return c["bid"] or c["ask"] or 0.0

    atm_strike = min(set(calls) & set(puts), key=lambda k: abs(k - spot))
    atm_straddle = mid(atm_strike, "call") + mid(atm_strike, "put")
    if atm_straddle <= 0:
        return {}

    common = sorted(set(calls) & set(puts))
    idx = common.index(atm_strike)

    def strangle_at(offset: int) -> float:
        if idx + offset >= len(common) or idx - offset < 0:
            return 0.0
        c_strike = common[idx + offset]
        p_strike = common[idx - offset]
        return mid(c_strike, "call") + mid(p_strike, "put")

    s1 = strangle_at(1)
    s2 = strangle_at(2)

    em = atm_straddle * 0.6 + s1 * 0.3 + s2 * 0.1

    return {
        "expected_move_tt"      : round(em, 2),
        "expected_move_tt_dte"  : nearest_dte,
        "expected_move_tt_strike": atm_strike,
        "expected_move_tt_high" : round(spot + em, 2),
        "expected_move_tt_low"  : round(spot - em, 2),
    }

def calc_pcr(contracts: list) -> float:
    call_oi = sum(c["oi"] for c in contracts if c["type"] == "call")
    put_oi  = sum(c["oi"] for c in contracts if c["type"] == "put")
    return round(put_oi / call_oi, 3) if call_oi > 0 else 0.0

def calc_top_strikes(contracts: list, n: int = 10) -> list:
    by_strike = {}
    for c in contracts:
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "call_oi": 0, "put_oi": 0, "total_oi": 0}
        if c["type"] == "call":
            by_strike[k]["call_oi"] += c["oi"]
        else:
            by_strike[k]["put_oi"]  += c["oi"]
        by_strike[k]["total_oi"] += c["oi"]
    return sorted(by_strike.values(), key=lambda x: x["total_oi"], reverse=True)[:n]

def calc_skew_25d(contracts: list, spot: float, max_delta_miss: float = 0.10) -> dict:
    """CBOE 25Δ skew for each available expiration.

    Returns dict with:
      - skew_25d_cboe          : front-DTE skew (backward compat)
      - skew_cboe_*            : front-DTE diagnostic details (backward compat)
      - skew_25d_cboe_by_dte   : dict {dte: skew} for all valid expirations
      - skew_cboe_details_by_dte : dict {dte: {strikes, deltas, ivs}}
    """
    by_expiry = {}
    for c in contracts:
        if c["dte"] <= 0 or c["iv"] <= 0 or c["delta"] == 0:
            continue
        by_expiry.setdefault(c["expiry"], []).append(c)

    skew_by_dte: dict = {}
    details_by_dte: dict = {}

    for expiry, contracts_exp in by_expiry.items():
        calls = [(c["strike"], c["delta"], c["iv"]) for c in contracts_exp
                 if c["type"] == "call" and 0 < c["delta"] <= 0.5]
        puts  = [(c["strike"], c["delta"], c["iv"]) for c in contracts_exp
                 if c["type"] == "put" and -0.5 <= c["delta"] < 0]
        if not calls or not puts:
            continue

        c_strike, c_delta, c_iv = min(calls, key=lambda x: abs(x[1] - 0.25))
        p_strike, p_delta, p_iv = min(puts,  key=lambda x: abs(x[1] + 0.25))

        if abs(c_delta - 0.25) > max_delta_miss or abs(abs(p_delta) - 0.25) > max_delta_miss:
            continue

        dte = contracts_exp[0]["dte"]
        skew_by_dte[dte] = round(p_iv - c_iv, 4)
        details_by_dte[dte] = {
            "call_strike": c_strike,
            "call_delta" : round(c_delta, 4),
            "call_iv"    : round(c_iv, 4),
            "put_strike" : p_strike,
            "put_delta"  : round(p_delta, 4),
            "put_iv"     : round(p_iv, 4),
        }

    if not skew_by_dte:
        return {"skew_25d_cboe": 0.0, "skew_25d_cboe_by_dte": {}}

    front_dte = min(skew_by_dte.keys())
    front     = details_by_dte[front_dte]

    return {
        "skew_25d_cboe"          : skew_by_dte[front_dte],
        "skew_cboe_call_strike"  : front["call_strike"],
        "skew_cboe_call_delta"   : front["call_delta"],
        "skew_cboe_call_iv"      : front["call_iv"],
        "skew_cboe_put_strike"   : front["put_strike"],
        "skew_cboe_put_delta"    : front["put_delta"],
        "skew_cboe_put_iv"       : front["put_iv"],
        "skew_cboe_dte"          : front_dte,
        "skew_25d_cboe_by_dte"   : skew_by_dte,
        "skew_cboe_details_by_dte": details_by_dte,
    }


def calc_atm_iv_intraday(contracts: list, spot: float, max_dte: int = 7) -> dict:
    """ATM IV for 0-7 DTE expirations (scalping horizon)."""
    by_dte: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["dte"] > max_dte or c["iv"] <= 0:
            continue
        by_dte.setdefault(c["dte"], []).append(c)

    iv_by_dte: dict = {}
    for dte, items in by_dte.items():
        strikes = {c["strike"] for c in items}
        if not strikes:
            continue
        atm_strike = min(strikes, key=lambda k: abs(k - spot))
        ivs = [c["iv"] for c in items if c["strike"] == atm_strike and c["iv"] > 0]
        if ivs:
            iv_by_dte[dte] = sum(ivs) / len(ivs)

    if not iv_by_dte:
        return {"atm_iv_intraday": 0.0, "atm_iv_intraday_by_dte": {}}

    front_dte = min(iv_by_dte.keys())
    return {
        "atm_iv_intraday"       : round(iv_by_dte[front_dte], 4),
        "atm_iv_intraday_dte"   : front_dte,
        "atm_iv_intraday_by_dte": {int(k): round(v, 4) for k, v in iv_by_dte.items()},
    }


def calc_term_intraday(contracts: list, spot: float,
                       front_target_dte: int = 0,
                       back_target_dte: int = 30) -> dict:
    """Term structure scalping: front (~0DTE) vs back (~30 DTE).
    Backwardation = immediate stress. Contango = calm market."""
    by_dte: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["iv"] <= 0:
            continue
        by_dte.setdefault(c["dte"], []).append(c)
    if not by_dte:
        return {"term_intraday_regime": "unknown"}

    def atm_iv_at(target):
        if not by_dte:
            return None, None
        closest = min(by_dte.keys(), key=lambda d: abs(d - target))
        items = by_dte[closest]
        strikes = {c["strike"] for c in items}
        atm_strike = min(strikes, key=lambda k: abs(k - spot))
        ivs = [c["iv"] for c in items if c["strike"] == atm_strike and c["iv"] > 0]
        if not ivs:
            return None, None
        return closest, sum(ivs) / len(ivs)

    front_dte, iv_front = atm_iv_at(front_target_dte)
    back_dte,  iv_back  = atm_iv_at(back_target_dte)
    if iv_front is None or iv_back is None or front_dte == back_dte:
        return {"term_intraday_regime": "unknown"}

    slope = iv_front - iv_back
    if abs(slope) < 0.005:
        regime = "flat"
    elif slope > 0:
        regime = "backwardation"
    else:
        regime = "contango"

    return {
        "term_intraday_regime"   : regime,
        "term_intraday_slope"    : round(slope, 4),
        "term_intraday_front_dte": int(front_dte),
        "term_intraday_back_dte" : int(back_dte),
        "term_intraday_iv_front" : round(iv_front, 4),
        "term_intraday_iv_back"  : round(iv_back, 4),
    }


def calc_zero_dte_metrics(contracts: list, spot: float) -> dict:
    """0DTE metrics (Max Pain, Pin Strike, Charm Magnet) on options expiring
    today (or tomorrow if no expiration today).
    _spy suffix because values are SPY strikes (to be converted to ES on the merge side)."""
    zero_dte = [c for c in contracts if c["dte"] == 0 and c["oi"] > 0]
    used_dte = 0
    if not zero_dte:
        zero_dte = [c for c in contracts if c["dte"] == 1 and c["oi"] > 0]
        used_dte = 1
    if not zero_dte:
        return {}

    # Max Pain 0DTE
    strikes = sorted(set(c["strike"] for c in zero_dte))
    min_pain, max_pain_strike = float("inf"), strikes[0]
    for s in strikes:
        pain = 0.0
        for c in zero_dte:
            if c["type"] == "call" and s > c["strike"]:
                pain += (s - c["strike"]) * c["oi"] * 100
            elif c["type"] == "put" and s < c["strike"]:
                pain += (c["strike"] - s) * c["oi"] * 100
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = s

    # 0DTE Pin Strike: max combined absolute gamma
    by_strike: dict = {}
    for c in zero_dte:
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "gex_abs": 0.0, "total_oi": 0.0}
        gex = abs(c["gamma"]) * c["oi"] * 100 * spot * spot * 0.01
        by_strike[k]["gex_abs"] += gex
        by_strike[k]["total_oi"] += c["oi"]
    pin_strike = (max(by_strike.values(), key=lambda x: x["gex_abs"])["strike"]
                  if by_strike else 0.0)

    # 0DTE Charm Magnet proxy
    total_oi = sum(c["oi"] for c in zero_dte)
    charm_candidates = [
        (k, v) for k, v in by_strike.items()
        if v["total_oi"] > total_oi * 0.05
    ]
    charm_strike = (min(charm_candidates, key=lambda kv: abs(kv[0] - spot))[0]
                    if charm_candidates else pin_strike)

    return {
        "max_pain_0dte_spy"     : max_pain_strike,
        "pin_strike_0dte_spy"   : pin_strike,
        "charm_magnet_0dte_spy" : charm_strike,
        "zero_dte_oi_total"     : int(total_oi),
        "zero_dte_dte"          : used_dte,
    }


def calc_walls_intraday(contracts: list, spot: float, max_dte: int = 7) -> dict:
    """Call Wall / Put Wall for 0-7 DTE options (intraday scalping)."""
    by_strike: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["dte"] > max_dte:
            continue
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "call_gex": 0.0, "put_gex": 0.0}
        gex = c["gamma"] * c["oi"] * 100 * spot ** 2 * 0.01
        if c["type"] == "call":
            by_strike[k]["call_gex"] += gex
        else:
            by_strike[k]["put_gex"] -= gex
    if not by_strike:
        return {}
    strikes = list(by_strike.values())
    call_wall_s = max(strikes, key=lambda x: x["call_gex"])
    put_wall_s  = min(strikes, key=lambda x: x["put_gex"])
    return {
        "call_wall_intraday"     : call_wall_s["strike"],
        "call_wall_intraday_gex" : round(call_wall_s["call_gex"], 0),
        "put_wall_intraday"      : put_wall_s["strike"],
        "put_wall_intraday_gex"  : round(put_wall_s["put_gex"], 0),
        "walls_intraday_max_dte" : max_dte,
    }


def calc_volume_flow_levels(contracts: list, spot: float,
                              max_dte: int = 7, n: int = 3) -> dict:
    """Volume Flow V1/V2/V3 — strikes with the highest volume of the day
    (Phase 7, TanukiTrade-style). Captures where the smart-money flow
    is concentrated today.
    """
    by_strike: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["dte"] > max_dte:
            continue
        v = c.get("volume", 0) or 0
        if v <= 0:
            continue
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "call_vol": 0.0, "put_vol": 0.0, "total_vol": 0.0}
        if c["type"] == "call":
            by_strike[k]["call_vol"] += v
        else:
            by_strike[k]["put_vol"] += v
        by_strike[k]["total_vol"] += v
    if not by_strike:
        return {}

    top = sorted(by_strike.values(), key=lambda x: x["total_vol"], reverse=True)[:n]
    out = {"vol_flow_intraday_max_dte": max_dte}
    for i, s in enumerate(top, 1):
        out[f"vol_flow_{i}"]          = s["strike"]
        out[f"vol_flow_{i}_call_vol"] = int(s["call_vol"])
        out[f"vol_flow_{i}_put_vol"]  = int(s["put_vol"])
        out[f"vol_flow_{i}_total"]    = int(s["total_vol"])
    return out


def calc_extended_walls(contracts: list, spot: float, max_dte: int = 7,
                         n: int = 4, exclude: list = None) -> dict:
    """Extended GEX walls (Phase 6, TanukiTrade GEX7-GEX10).
    4 additional strikes sorted by descending |net_gex|. Each strike is
    labeled call/put by the sign of net_gex.
    """
    by_strike: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["dte"] > max_dte:
            continue
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "call_gex": 0.0, "put_gex": 0.0, "net_gex": 0.0}
        gex = c["gamma"] * c["oi"] * 100 * spot ** 2 * 0.01
        if c["type"] == "call":
            by_strike[k]["call_gex"] += gex
        else:
            by_strike[k]["put_gex"] -= gex
    for k in by_strike:
        by_strike[k]["net_gex"] = by_strike[k]["call_gex"] + by_strike[k]["put_gex"]
    if not by_strike:
        return {}

    excl = set(exclude or [])
    items = [s for s in by_strike.values() if s["strike"] not in excl]
    items.sort(key=lambda x: abs(x["net_gex"]), reverse=True)
    top = items[:n]

    out = {"gex_walls_ext_max_dte": max_dte}
    for i, s in enumerate(top, 1):
        out[f"gex_wall_ext_{i}"]      = s["strike"]
        out[f"gex_wall_ext_{i}_gex"]  = round(s["net_gex"], 0)
        out[f"gex_wall_ext_{i}_side"] = "call" if s["net_gex"] >= 0 else "put"
    return out


def calc_abs_gex_levels(contracts: list, spot: float,
                         max_dte: int = 7, n: int = 3) -> dict:
    """Abs GEX (Absolute Gamma Exposure) Ab1/Ab2/Ab3 — strikes with the
    highest total absolute gamma (calls + puts combined) (Phase 5,
    TanukiTrade-style). Captures strong pin-risk zones.
    """
    by_strike: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["dte"] > max_dte:
            continue
        if c["gamma"] == 0 or c["oi"] <= 0:
            continue
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "abs_gex": 0.0}
        by_strike[k]["abs_gex"] += abs(c["gamma"]) * c["oi"] * 100 * spot ** 2 * 0.01
    if not by_strike:
        return {}

    top = sorted(by_strike.values(), key=lambda x: x["abs_gex"], reverse=True)[:n]
    out = {"abs_gex_intraday_max_dte": max_dte}
    for i, s in enumerate(top, 1):
        out[f"abs_gex_intraday_{i}"]      = s["strike"]
        out[f"abs_gex_intraday_{i}_gex"]  = round(s["abs_gex"], 0)
    return out


def calc_dex_levels(contracts: list, spot: float, max_dte: int = 7) -> dict:
    """DEX (Delta Exposure) D+ / D- — strikes with the highest directional
    hedging pressure (Phase 4, TanukiTrade-style).
    """
    by_strike: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["dte"] > max_dte:
            continue
        if c["delta"] == 0 or c["oi"] <= 0:
            continue
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "net_dex": 0.0,
                             "call_dex": 0.0, "put_dex": 0.0}
        d = c["delta"] * c["oi"] * 100
        if c["type"] == "call":
            by_strike[k]["call_dex"] += d
        else:
            by_strike[k]["put_dex"]  += d
        by_strike[k]["net_dex"] += d
    if not by_strike:
        return {}

    items = list(by_strike.values())
    pos = max(items, key=lambda x: x["net_dex"])
    neg = min(items, key=lambda x: x["net_dex"])

    return {
        "dex_plus_intraday"      : pos["strike"] if pos["net_dex"] > 0 else None,
        "dex_plus_intraday_dex"  : round(pos["net_dex"], 0) if pos["net_dex"] > 0 else None,
        "dex_minus_intraday"     : neg["strike"] if neg["net_dex"] < 0 else None,
        "dex_minus_intraday_dex" : round(neg["net_dex"], 0) if neg["net_dex"] < 0 else None,
        "dex_intraday_max_dte"   : max_dte,
    }


def calc_transition_levels(contracts: list, spot: float,
                            max_dte: int = 7, threshold_pct: float = 0.10) -> dict:
    """cTrans / pTrans — transition levels where call/put gamma starts
    dominating (Phase 3, inspired by TanukiTrade's Gamma Classification Engine).

    Method: starting from spot, we accumulate net GEX going up (resp. down).
    cTrans is the first strike above spot where the positive cumulative
    exceeds threshold_pct of total absolute gamma (10% by default). pTrans
    is the negative descending equivalent.
    """
    by_strike: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["dte"] > max_dte:
            continue
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "call_gex": 0.0, "put_gex": 0.0, "net_gex": 0.0}
        gex = c["gamma"] * c["oi"] * 100 * spot ** 2 * 0.01
        if c["type"] == "call":
            by_strike[k]["call_gex"] += gex
        else:
            by_strike[k]["put_gex"] -= gex
    for k in by_strike:
        by_strike[k]["net_gex"] = by_strike[k]["call_gex"] + by_strike[k]["put_gex"]
    if not by_strike:
        return {}

    strikes = sorted(by_strike.values(), key=lambda x: x["strike"])
    total_abs = sum(abs(s["net_gex"]) for s in strikes)
    if total_abs == 0:
        return {}
    threshold = total_abs * threshold_pct

    above = [s for s in strikes if s["strike"] >= spot]
    c_trans = None
    cum = 0.0
    for s in above:
        cum += s["net_gex"]
        if cum > threshold:
            c_trans = s["strike"]
            break

    below = [s for s in strikes if s["strike"] <= spot][::-1]
    p_trans = None
    cum = 0.0
    for s in below:
        cum += s["net_gex"]
        if cum < -threshold:
            p_trans = s["strike"]
            break

    return {
        "c_trans_intraday"      : c_trans,
        "p_trans_intraday"      : p_trans,
        "trans_intraday_max_dte": max_dte,
    }


def calc_top_strikes_intraday(contracts: list, max_dte: int = 7, n: int = 3) -> list:
    """Top OI strikes for 0-7 DTE options."""
    by_strike: dict = {}
    for c in contracts:
        if c["dte"] < 0 or c["dte"] > max_dte:
            continue
        k = c["strike"]
        if k not in by_strike:
            by_strike[k] = {"strike": k, "call_oi": 0, "put_oi": 0, "total_oi": 0}
        if c["type"] == "call":
            by_strike[k]["call_oi"] += c["oi"]
        else:
            by_strike[k]["put_oi"] += c["oi"]
        by_strike[k]["total_oi"] += c["oi"]
    return sorted(by_strike.values(), key=lambda x: x["total_oi"], reverse=True)[:n]


def build_levels_ES(max_dte: int = 7) -> dict:
    """Builds the CBOE SPY JSON (ES proxy).
    max_dte=7  → 'cumulative' mode (TanukiTrade ∑) — aggregates 0-7 DTE
    max_dte=0  → 'selected' mode   (TanukiTrade ⊙) — 0DTE only
    """
    mode = "selected" if max_dte == 0 else f"cumulative_0-{max_dte}d"
    print("=" * 55)
    print(f"  GEX AGENT — CBOE SPY fetch (ES proxy)  [mode: {mode}]")
    print("=" * 55)

    chain     = fetch_chain()
    spot      = chain["spot"]
    contracts = chain["contracts"]
    print(f"Contracts fetched: {len(contracts)}")

    gex           = calc_gex(contracts, spot)
    max_pain      = calc_max_pain(contracts)
    expected_move = calc_expected_move(spot, contracts)
    em_tt         = calc_expected_move_tt(contracts, spot)
    pcr           = calc_pcr(contracts)
    top_strikes   = calc_top_strikes(contracts)
    skew_cboe     = calc_skew_25d(contracts, spot)
    iv_intraday   = calc_atm_iv_intraday(contracts, spot, max_dte=max(max_dte, 7))
    term_intraday = calc_term_intraday(contracts, spot)
    walls_intraday   = calc_walls_intraday(contracts, spot, max_dte=max_dte)
    top_oi_intraday  = calc_top_strikes_intraday(contracts, max_dte=max_dte)
    trans_intraday   = calc_transition_levels(contracts, spot, max_dte=max_dte)
    dex_intraday     = calc_dex_levels(contracts, spot, max_dte=max_dte)
    abs_gex_intraday = calc_abs_gex_levels(contracts, spot, max_dte=max_dte)
    excl_strikes = [s for s in [walls_intraday.get("call_wall_intraday"),
                                  walls_intraday.get("put_wall_intraday")] if s]
    ext_walls    = calc_extended_walls(contracts, spot, max_dte=max_dte, exclude=excl_strikes)
    vol_flow     = calc_volume_flow_levels(contracts, spot, max_dte=max_dte)
    zero_dte         = calc_zero_dte_metrics(contracts, spot)

    levels = {
        "spot"           : spot,
        "fetched_at"     : chain["fetched_at"],
        "intraday_mode"  : mode,
        "intraday_max_dte_param": max_dte,
        "gamma_flip"     : gex["gamma_flip"],
        "call_wall"      : gex["call_wall"],
        "call_wall_gex"  : gex["call_wall_gex"],
        "put_wall"       : gex["put_wall"],
        "put_wall_gex"   : gex["put_wall_gex"],
        "net_gex"        : gex["net_gex"],
        "regime"         : gex["regime"],
        "max_pain"       : max_pain,
        "expected_move"  : expected_move,
        "range_bas"      : round(spot - expected_move, 2),
        "range_haut"     : round(spot + expected_move, 2),
        "pcr"            : pcr,
        **em_tt,
        "top_oi_strikes" : top_strikes,
        "top_oi_intraday": top_oi_intraday,
        **skew_cboe,
        **iv_intraday,
        **term_intraday,
        **walls_intraday,
        **trans_intraday,
        **dex_intraday,
        **abs_gex_intraday,
        **ext_walls,
        **vol_flow,
        **zero_dte,
    }

    ES_LEVELS_JSON.parent.mkdir(parents=True, exist_ok=True)
    ES_LEVELS_JSON.write_text(json.dumps(levels, indent=2))

    print(f"\n{'─'*55}")
    print(f"  Spot SPY      : ${spot:.2f}")
    print(f"  Regime        : {gex['regime'].upper()} GEX")
    print(f"  Net GEX       : ${gex['net_gex']:,.0f}")
    print(f"{'─'*55}")
    if gex["gamma_flip"]:
        print(f"  Gamma Flip    : ${gex['gamma_flip']:.2f}")
    print(f"  Call Wall     : ${gex['call_wall']:.2f}  (GEX {gex['call_wall_gex']:,.0f})")
    print(f"  Put Wall      : ${gex['put_wall']:.2f}  (GEX {gex['put_wall_gex']:,.0f})")
    print(f"{'─'*55}")
    print(f"  Max Pain      : ${max_pain:.2f}")
    print(f"  Expected Move : +/-${expected_move:.2f}  (IV-based)")
    print(f"  Range         : [${levels['range_bas']} — ${levels['range_haut']}]")
    if em_tt.get("expected_move_tt"):
        em = em_tt['expected_move_tt']
        d  = em_tt.get('expected_move_tt_dte', 0)
        print(f"  EM TastyTrade : +/-${em:.2f}  ({d}DTE, straddle-weighted)")
        print(f"  Range TT      : [${em_tt['expected_move_tt_low']} - ${em_tt['expected_move_tt_high']}]")
    print(f"  PCR           : {pcr}  ({'put-heavy' if pcr > 1 else 'call-heavy'})")
    print(f"{'─'*55}")
    print(f"  Top OI #1     : ${top_strikes[0]['strike']} (OI {top_strikes[0]['total_oi']:,.0f})")
    print(f"  Top OI #2     : ${top_strikes[1]['strike']} (OI {top_strikes[1]['total_oi']:,.0f})")
    print(f"  Top OI #3     : ${top_strikes[2]['strike']} (OI {top_strikes[2]['total_oi']:,.0f})")
    print(f"{'─'*55}")
    if walls_intraday.get("call_wall_intraday"):
        print(f"  Call Wall ID  : ${walls_intraday['call_wall_intraday']:.2f}  (GEX {walls_intraday['call_wall_intraday_gex']:,.0f})  [0-7d]")
        print(f"  Put Wall ID   : ${walls_intraday['put_wall_intraday']:.2f}  (GEX {walls_intraday['put_wall_intraday_gex']:,.0f})  [0-7d]")
    if trans_intraday.get("c_trans_intraday") or trans_intraday.get("p_trans_intraday"):
        ct = trans_intraday.get('c_trans_intraday')
        pt = trans_intraday.get('p_trans_intraday')
        ct_str = f"${ct:.2f}" if ct else "—"
        pt_str = f"${pt:.2f}" if pt else "—"
        print(f"  cTrans ID     : {ct_str}  [call gamma dominant]  [0-7d]")
        print(f"  pTrans ID     : {pt_str}  [put gamma dominant]   [0-7d]")
    if dex_intraday.get("dex_plus_intraday") or dex_intraday.get("dex_minus_intraday"):
        dp = dex_intraday.get('dex_plus_intraday')
        dm = dex_intraday.get('dex_minus_intraday')
        dp_str = f"${dp:.2f}" if dp else "—"
        dm_str = f"${dm:.2f}" if dm else "—"
        print(f"  D+ DEX        : {dp_str}  [dealers buy → bullish]  [0-7d]")
        print(f"  D- DEX        : {dm_str}  [dealers sell → bearish] [0-7d]")
    for i in range(1, 4):
        ab = abs_gex_intraday.get(f"abs_gex_intraday_{i}")
        if ab:
            g = abs_gex_intraday.get(f"abs_gex_intraday_{i}_gex", 0)
            print(f"  Abs GEX Ab{i}   : ${ab:.2f}  (|GEX| {g:,.0f})  [pin risk]  [0-7d]")
    for i in range(1, 5):
        e = ext_walls.get(f"gex_wall_ext_{i}")
        if e:
            g = ext_walls.get(f"gex_wall_ext_{i}_gex", 0)
            side = ext_walls.get(f"gex_wall_ext_{i}_side", "?")
            print(f"  GEX Ext #{i+6:<2d}: ${e:.2f}  (net {g:+,.0f}, {side})  [0-7d]")
    for i in range(1, 4):
        v = vol_flow.get(f"vol_flow_{i}")
        if v:
            tot = vol_flow.get(f"vol_flow_{i}_total", 0)
            print(f"  Vol Flow V{i}   : ${v:.2f}  (vol {tot:,d})  [today's flow]")
    if len(top_oi_intraday) >= 3:
        print(f"  Top OI ID #1  : ${top_oi_intraday[0]['strike']}  (OI {top_oi_intraday[0]['total_oi']:,.0f})  [0-7d]")
        print(f"  Top OI ID #2  : ${top_oi_intraday[1]['strike']}  (OI {top_oi_intraday[1]['total_oi']:,.0f})  [0-7d]")
        print(f"  Top OI ID #3  : ${top_oi_intraday[2]['strike']}  (OI {top_oi_intraday[2]['total_oi']:,.0f})  [0-7d]")
    if zero_dte.get("max_pain_0dte_spy"):
        d = zero_dte.get('zero_dte_dte', 0)
        print(f"{'─'*55}")
        print(f"  Max Pain 0DTE : ${zero_dte['max_pain_0dte_spy']}  ({d}DTE)")
        print(f"  Pin Strike 0D : ${zero_dte['pin_strike_0dte_spy']}  (gamma max {d}DTE)")
        print(f"  Charm Mag. 0D : ${zero_dte['charm_magnet_0dte_spy']}  (near spot, OI > 5%)")
    print(f"{'─'*55}")
    iv_id = iv_intraday.get("atm_iv_intraday", 0)
    if iv_id:
        print(f"  IVx intraday  : {iv_id*100:.1f}%  (SPY {iv_intraday.get('atm_iv_intraday_dte',0)} DTE)")
    tr = term_intraday.get("term_intraday_regime", "unknown")
    if tr != "unknown":
        slope = term_intraday.get('term_intraday_slope', 0)
        fdte  = term_intraday.get('term_intraday_front_dte', 0)
        bdte  = term_intraday.get('term_intraday_back_dte', 0)
        print(f"  Term intraday : {tr} ({slope*100:+.2f} vp)  "
              f"{fdte}d→{bdte}d")
    print(f"{'─'*55}")
    sk = skew_cboe.get("skew_25d_cboe", 0)
    if sk:
        print(f"  Skew 25Δ CBOE : {sk*100:+.2f} vp  (SPY {skew_cboe.get('skew_cboe_dte',0)} DTE)")
        print(f"    call K=${skew_cboe['skew_cboe_call_strike']}  "
              f"Δ={skew_cboe['skew_cboe_call_delta']:.3f}  "
              f"IV={skew_cboe['skew_cboe_call_iv']*100:.1f}%")
        print(f"    put  K=${skew_cboe['skew_cboe_put_strike']}  "
              f"Δ={skew_cboe['skew_cboe_put_delta']:.3f}  "
              f"IV={skew_cboe['skew_cboe_put_iv']*100:.1f}%")
    print(f"{'─'*55}")
    print(f"  Saved -> {ES_LEVELS_JSON}")
    print(f"{'='*55}")
    return levels

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--max-dte", type=int, default=7,
                   help="Max DTE for intraday metrics. 7=cumulative ∑ (default), 0=selected ⊙ (0DTE only).")
    args = p.parse_args()
    build_levels_ES(max_dte=args.max_dte)
