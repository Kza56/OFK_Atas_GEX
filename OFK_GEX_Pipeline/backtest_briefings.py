"""
backtest_briefings.py — Measures the predictive quality of morning briefings.

For each daily snapshot in data/history/, loads the matching briefing (if any)
and compares the bias (bullish/bearish/neutral) against the actual price move
on the RTH session.

Since the pipeline does not store the RTH close, we use an approximation:
- If the NEXT DAY's snapshot exists, its opening spot is our "close" for the
  day (overnight gap included).
- Otherwise, the event is logged as "not verifiable".

Computed metrics:
- Global hit rate by direction (bullish/bearish/neutral)
- Hit rate by conviction (low/moderate/high)
- Hit rate by GEX regime (positive/negative)
- Hit rate by intraday term regime (contango/backwardation/flat)
- Average magnitude of correct vs incorrect moves

Usage:
  py backtest_briefings.py NQ
  py backtest_briefings.py ES
  py backtest_briefings.py NQ --since 2026-01-01

Output: console + writes data/backtest_<SYMBOL>_<datestamp>.csv
"""
import argparse
import csv
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional

from config import HISTORY_DIR, DATA_DIR


def list_snapshots(symbol: str) -> List[Path]:
    """Snapshots sorted in ascending date order."""
    pattern = f"{symbol}_full_levels_*.json"
    snaps = sorted(HISTORY_DIR.glob(pattern))
    return snaps


def parse_date_from_path(p: Path) -> Optional[date]:
    """Extract YYYYMMDD from {symbol}_full_levels_YYYYMMDD.json"""
    try:
        ds = p.stem.split("_")[-1]
        return datetime.strptime(ds, "%Y%m%d").date()
    except Exception:
        return None


def load_briefing_for(symbol: str, snap_date: date) -> Optional[dict]:
    """Loads the day's versioned briefing (codex_briefing.py saves them under
    HISTORY_DIR/briefings/{SYM}_briefing_YYYYMMDD.json)."""
    bdir = HISTORY_DIR / "briefings"
    if not bdir.exists():
        return None
    fname = f"{symbol}_briefing_{snap_date.strftime('%Y%m%d')}.json"
    p = bdir / fname
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def classify_gamma_zone(spot: float, snap: dict, symbol: str) -> str:
    """Determines the gamma zone at snapshot time (Phase 1 TanukiTrade).
    Bounds: Put Wall < pTrans < cTrans < Call Wall (intraday 0-7 DTE).
    Returns: bullish_squeeze / positive / transition / negative / bearish_squeeze / unknown
    """
    suf = "nq" if symbol == "NQ" else "es"
    cw = snap.get(f"call_wall_intraday_{suf}") or 0
    pw = snap.get(f"put_wall_intraday_{suf}") or 0
    ct = snap.get(f"c_trans_intraday_{suf}") or 0
    pt = snap.get(f"p_trans_intraday_{suf}") or 0

    if not spot:
        return "unknown"
    if cw and spot > cw:
        return "bullish_squeeze"
    if pw and spot < pw:
        return "bearish_squeeze"
    if ct and spot >= ct:
        return "positive"
    if pt and spot <= pt:
        return "negative"
    if ct and pt and pt < spot < ct:
        return "transition"
    # Fallback: if no cTrans/pTrans, fall back to HVL/gamma_flip
    gf = snap.get("gamma_flip") or 0
    if gf and spot > gf:
        return "positive"
    if gf and spot < gf:
        return "negative"
    return "unknown"


def evaluate_day(snap: dict, next_snap: Optional[dict], symbol: str,
                 briefing: Optional[dict] = None) -> Optional[dict]:
    """Compare the day's RTH move:
    - If open_rth_spot and close_rth_spot are available (captured by
      run_intraday_refresh.py): use the pure RTH move (open->close).
    - Otherwise fallback: snapshot spot vs next-day spot
      (includes overnight gap, less precise)."""
    spot_key = "spot_nq" if symbol == "NQ" else "spot_es"
    suf = "nq" if symbol == "NQ" else "es"

    open_r = snap.get("open_rth_spot")
    close_r = snap.get("close_rth_spot")

    if open_r and close_r and open_r > 0 and close_r > 0:
        # Clean mode: RTH open-to-close move
        spot_today = open_r
        spot_next  = close_r
        mode = "rth"
    else:
        # Fallback: snapshot N vs N+1
        if not next_snap:
            return None
        spot_today = snap.get(spot_key, 0)
        spot_next  = next_snap.get(spot_key, 0)
        if spot_today <= 0 or spot_next <= 0:
            return None
        mode = "overnight"

    move_pts = spot_next - spot_today
    move_pct = (move_pts / spot_today) * 100

    if move_pct > 0.5:
        actual = "bullish"
    elif move_pct < -0.5:
        actual = "bearish"
    else:
        actual = "neutral"

    # FR -> EN normalization for backward compat with old FR-keyed briefings
    fr_to_en_dir = {"haussier": "bullish", "baissier": "bearish", "neutre": "neutral"}
    fr_to_en_conv = {"faible": "low", "modérée": "moderate", "moderee": "moderate", "forte": "high"}

    predicted = None
    conviction = None
    plan_hit = None  # buy/sell zone touched?
    if briefing:
        biais = briefing.get("bias") or briefing.get("biais") or {}
        predicted = biais.get("direction")
        predicted = fr_to_en_dir.get(predicted, predicted)
        conviction = biais.get("conviction")
        conviction = fr_to_en_conv.get(conviction, conviction)
        plan = briefing.get("rth_plan") or briefing.get("plan_rth") or {}
        za = plan.get("buy_zone", plan.get("zone_achat", 0)) or 0
        zv = plan.get("sell_zone", plan.get("zone_vente", 0)) or 0
        # Very rough: if actual_low < buy_zone or actual_high > sell_zone,
        # the plan was tested. Approximated with the range [today, next].
        lo = min(spot_today, spot_next)
        hi = max(spot_today, spot_next)
        plan_hit = (za > 0 and lo <= za <= hi) or (zv > 0 and lo <= zv <= hi)

    correct = (predicted == actual) if predicted else None

    # Gamma zone classification at snapshot time
    gamma_zone = classify_gamma_zone(spot_today, snap, symbol)

    return {
        "date"          : snap.get("trade_date"),
        "mode"          : mode,
        "spot_today"    : round(spot_today, 2),
        "spot_next"     : round(spot_next, 2),
        "move_pts"      : round(move_pts, 2),
        "move_pct"      : round(move_pct, 3),
        "actual_dir"    : actual,
        "predicted_dir" : predicted,
        "conviction"    : conviction,
        "correct"       : correct,
        "plan_hit"      : plan_hit,
        "gex_regime"    : snap.get("gex_regime"),
        "term_intraday" : snap.get("term_intraday_regime"),
        "ivx_intraday"  : snap.get("atm_iv_intraday"),
        "skew_intraday" : snap.get("skew_25d_intraday"),
        "pcr"           : snap.get("pcr"),
        "ivr_intraday"  : (snap.get("iv_rank_intraday") or {}).get("ivr"),
        # Phase 1+3+4 metrics
        "gamma_zone"    : gamma_zone,
        "c_trans"       : snap.get(f"c_trans_intraday_{suf}"),
        "p_trans"       : snap.get(f"p_trans_intraday_{suf}"),
        "dex_plus"      : snap.get(f"dex_plus_intraday_{suf}"),
        "dex_minus"     : snap.get(f"dex_minus_intraday_{suf}"),
        "em_tt"         : snap.get(f"expected_move_tt_{suf}"),
        "cw_intraday"   : snap.get(f"call_wall_intraday_{suf}"),
        "pw_intraday"   : snap.get(f"put_wall_intraday_{suf}"),
    }


def aggregate_stats(rows: List[dict]) -> dict:
    """Computes global and per-bucket stats."""
    if not rows:
        return {}

    n = len(rows)
    by_dir = {"bullish": 0, "bearish": 0, "neutral": 0}
    by_gex = {"positive": [], "negative": []}
    by_term = {"contango": [], "backwardation": [], "flat": []}
    by_zone = {"bullish_squeeze": [], "positive": [], "transition": [],
                "negative": [], "bearish_squeeze": [], "unknown": []}
    moves_abs = []

    for r in rows:
        ad = r.get("actual_dir") or "neutral"
        by_dir[ad] = by_dir.get(ad, 0) + 1
        moves_abs.append(abs(r.get("move_pct") or 0))

        gex_r = r.get("gex_regime")
        if gex_r is not None:
            label = "positive" if gex_r > 0 else "negative"
            by_gex[label].append(r.get("move_pct") or 0)

        term = r.get("term_intraday")
        if term in by_term:
            by_term[term].append(r.get("move_pct") or 0)

        zone = r.get("gamma_zone") or "unknown"
        if zone in by_zone:
            by_zone[zone].append(r.get("move_pct") or 0)

    avg_move = sum(moves_abs) / n if n else 0.0

    def avg(xs): return sum(xs) / len(xs) if xs else 0.0
    def hit_pos(xs): return sum(1 for x in xs if x > 0.5) / len(xs) * 100 if xs else 0.0
    def hit_neg(xs): return sum(1 for x in xs if x < -0.5) / len(xs) * 100 if xs else 0.0
    def avg_abs(xs): return sum(abs(x) for x in xs) / len(xs) if xs else 0.0

    return {
        "n_days"        : n,
        "distribution"  : by_dir,
        "avg_move_pct"  : round(avg_move, 3),
        "gex_positive"  : {
            "n": len(by_gex["positive"]),
            "avg_move_pct": round(avg(by_gex["positive"]), 3),
            "pct_bullish": round(hit_pos(by_gex["positive"]), 1),
            "pct_bearish": round(hit_neg(by_gex["positive"]), 1),
        },
        "gex_negative"  : {
            "n": len(by_gex["negative"]),
            "avg_move_pct": round(avg(by_gex["negative"]), 3),
            "pct_bullish": round(hit_pos(by_gex["negative"]), 1),
            "pct_bearish": round(hit_neg(by_gex["negative"]), 1),
        },
        "term_contango" : {
            "n": len(by_term["contango"]),
            "avg_move_pct": round(avg(by_term["contango"]), 3),
        },
        "term_backwardation" : {
            "n": len(by_term["backwardation"]),
            "avg_move_pct": round(avg(by_term["backwardation"]), 3),
        },
        # Phase 1 — analysis by gamma_zone (TanukiTrade-style)
        "gamma_zones"   : {
            zone: {
                "n": len(vals),
                "avg_move_pct": round(avg(vals), 3),
                "magnitude_abs": round(avg_abs(vals), 3),
                "pct_bullish": round(hit_pos(vals), 1),
                "pct_bearish": round(hit_neg(vals), 1),
            }
            for zone, vals in by_zone.items() if vals
        },
    }


def main():
    p = argparse.ArgumentParser(description="Backtest market conditions vs realized moves")
    p.add_argument("symbol", choices=["NQ", "ES"])
    p.add_argument("--since", help="min date YYYY-MM-DD")
    p.add_argument("--csv", action="store_true", help="export detailed CSV")
    args = p.parse_args()

    snaps = list_snapshots(args.symbol)
    if len(snaps) < 2:
        print(f"WARN: only {len(snaps)} snapshot(s) — at least 2 are required to compare.")
        print(f"   History accumulates with each pipeline run.")
        return

    cutoff = None
    if args.since:
        cutoff = datetime.strptime(args.since, "%Y-%m-%d").date()

    rows = []
    for i in range(len(snaps) - 1):
        snap_date = parse_date_from_path(snaps[i])
        if snap_date is None or (cutoff and snap_date < cutoff):
            continue
        try:
            snap = json.loads(snaps[i].read_text())
            next_snap = json.loads(snaps[i + 1].read_text())
        except Exception:
            continue
        briefing = load_briefing_for(args.symbol, snap_date)
        ev = evaluate_day(snap, next_snap, args.symbol, briefing)
        if ev:
            rows.append(ev)

    print(f"\n=== Backtest {args.symbol} — {len(rows)} day(s) evaluated ===\n")
    if not rows:
        print("No usable day/next-day pair.")
        return

    n_rth = sum(1 for r in rows if r.get("mode") == "rth")
    n_on  = sum(1 for r in rows if r.get("mode") == "overnight")
    print(f"  Modes: {n_rth} RTH (pure open->close), {n_on} overnight (proxy)")

    stats = aggregate_stats(rows)
    print(f"  Move distribution :")
    for k, v in stats["distribution"].items():
        pct = v / stats["n_days"] * 100
        print(f"    {k:10s} : {v:3d}  ({pct:.1f}%)")
    print(f"  Avg move % (abs)   : {stats['avg_move_pct']:.2f}%")

    print(f"\n  GEX positive (n={stats['gex_positive']['n']}):")
    print(f"    Avg move          : {stats['gex_positive']['avg_move_pct']:+.2f}%")
    print(f"    % bullish days    : {stats['gex_positive']['pct_bullish']:.1f}%")
    print(f"    % bearish days    : {stats['gex_positive']['pct_bearish']:.1f}%")
    print(f"\n  GEX negative (n={stats['gex_negative']['n']}):")
    print(f"    Avg move          : {stats['gex_negative']['avg_move_pct']:+.2f}%")
    print(f"    % bullish days    : {stats['gex_negative']['pct_bullish']:.1f}%")
    print(f"    % bearish days    : {stats['gex_negative']['pct_bearish']:.1f}%")

    print(f"\n  Term contango (n={stats['term_contango']['n']}):")
    print(f"    Avg move : {stats['term_contango']['avg_move_pct']:+.2f}%")
    print(f"  Term backwardation (n={stats['term_backwardation']['n']}):")
    print(f"    Avg move : {stats['term_backwardation']['avg_move_pct']:+.2f}%")

    # Phase 1 — Gamma zones (TanukiTrade)
    if stats.get("gamma_zones"):
        print(f"\n  --- GAMMA ZONES (TanukiTrade) ---")
        zone_order = ["bullish_squeeze", "positive", "transition",
                       "negative", "bearish_squeeze", "unknown"]
        for zone in zone_order:
            z = stats["gamma_zones"].get(zone)
            if not z:
                continue
            print(f"  {zone:18s} (n={z['n']:3d}): "
                  f"move {z['avg_move_pct']:+.2f}% | "
                  f"|move| {z['magnitude_abs']:.2f}% | "
                  f"bull {z['pct_bullish']:.0f}% / "
                  f"bear {z['pct_bearish']:.0f}%")

    # Briefing accuracy (if versioned)
    with_brief = [r for r in rows if r.get("predicted_dir")]
    if with_brief:
        n_b = len(with_brief)
        correct = sum(1 for r in with_brief if r.get("correct"))
        plan_hits = sum(1 for r in with_brief if r.get("plan_hit"))
        print(f"\n  Briefings evaluated : {n_b}")
        print(f"  Correct direction   : {correct}/{n_b}  ({correct/n_b*100:.1f}%)")
        print(f"  rth_plan touched    : {plan_hits}/{n_b}  ({plan_hits/n_b*100:.1f}%)")
        for conv in ("high", "moderate", "low"):
            sub = [r for r in with_brief if r.get("conviction") == conv]
            if sub:
                c = sum(1 for r in sub if r.get("correct"))
                print(f"    Conviction {conv:8s}: {c}/{len(sub)}  ({c/len(sub)*100:.1f}%)")
    else:
        print(f"\n  WARN: no versioned briefing yet. Briefings will be archived "
              f"under data/history/briefings/ starting from upcoming runs.")

    if args.csv:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out = DATA_DIR / f"backtest_{args.symbol}_{ts}.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\n  CSV exported: {out}")


if __name__ == "__main__":
    main()
