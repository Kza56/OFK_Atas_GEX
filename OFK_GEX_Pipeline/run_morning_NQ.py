"""
run_morning_NQ.py — NQ E-mini pipeline orchestrator
Steps: CME NQ → CBOE QQQ → merge → Claude briefing → PDF

Usage: py run_morning_NQ.py
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

from config import (
    PIPELINE_ROOT,
    NQ_GEX_JSON    as GEX_JSON,
    NQ_LEVELS_JSON as LEVELS_JSON,
    NQ_FULL_JSON   as FULL_JSON,
    NQ_BRIEFING_JSON,
    save_snapshot,
    compute_iv_rank,
)

PROJECT_DIR = PIPELINE_ROOT
CME_SCRIPT  = PIPELINE_ROOT / "cme_NQ_browser_fetch.py"


def step(msg: str):
    print(f"\n{'─'*55}")
    print(f"  {msg}")
    print(f"{'─'*55}")


def run_cme():
    """Launch CME script (opens visible Chromium browser)."""
    step("STEP 1 — Fetch CME NQ options")
    result = subprocess.run(
        [sys.executable, "cme_NQ_browser_fetch.py"],
        cwd=str(PIPELINE_ROOT)
    )
    if result.returncode != 0:
        raise RuntimeError("CME fetch failed")
    print("  CME → NQ_gex_latest.json ✓")


def run_cboe():
    """Fetch CBOE QQQ options chain."""
    step("STEP 2 — Fetch CBOE QQQ options")
    from data_fetcher_NQ import build_levels
    return build_levels()


def merge_levels() -> dict:
    """Merge CME (native NQ) + CBOE QQQ (missing metrics) + VIX context."""
    step("STEP 3 — Merge data sources")

    cme  = json.loads(GEX_JSON.read_text())   if GEX_JSON.exists()   else {}
    cboe = json.loads(LEVELS_JSON.read_text()) if LEVELS_JSON.exists() else {}
    from vix_fetcher import fetch_vix
    from econ_calendar import blackout_status
    vix      = fetch_vix()
    blackout = blackout_status()

    nq_spot  = cme.get("spot", 0)
    qqq_spot = cboe.get("spot", 0)
    ratio    = nq_spot / qqq_spot if qqq_spot > 0 else 20.0

    def qqq_to_nq(val):
        return round(val * ratio) if val else None

    full = {
        # Metadata
        "generated_at"       : datetime.now(timezone.utc).isoformat(),
        "trade_date"         : cme.get("trade_date"),
        "spot_nq"            : nq_spot,
        "spot_qqq"           : qqq_spot,
        "qqq_nq_ratio"       : round(ratio, 4),

        # Native NQ levels (CME)
        "gamma_flip"         : cme.get("gamma_flip"),
        "vol_trigger"        : cme.get("vol_trigger"),
        "call_wall"          : cme.get("call_wall"),
        "put_wall"           : cme.get("put_wall"),
        "risk_pivot"         : cme.get("risk_pivot"),
        "vanna_flip"         : cme.get("vanna_flip"),
        "charm_magnet"       : cme.get("charm_magnet"),

        # Greeks exposures (CME)
        "total_gex"          : cme.get("total_gex"),
        "total_vex"          : cme.get("total_vex"),
        "total_cex"          : cme.get("total_cex"),
        "total_dex"          : cme.get("total_dex"),
        "gex_regime"         : cme.get("gex_regime"),
        "vex_regime"         : cme.get("vex_regime"),

        # ─── PRIMARY SCALPING (CBOE intraday 0-7 DTE) ─────────────────────
        "atm_iv_intraday"        : cboe.get("atm_iv_intraday"),
        "atm_iv_intraday_dte"    : cboe.get("atm_iv_intraday_dte"),
        "atm_iv_intraday_by_dte" : cboe.get("atm_iv_intraday_by_dte"),

        "skew_25d_intraday"      : cboe.get("skew_25d_cboe"),       # alias front CBOE
        "skew_25d_intraday_dte"  : cboe.get("skew_cboe_dte"),
        "skew_25d_intraday_by_dte": cboe.get("skew_25d_cboe_by_dte"),
        "skew_intraday_detail"   : {
            "call_strike": cboe.get("skew_cboe_call_strike"),
            "call_delta" : cboe.get("skew_cboe_call_delta"),
            "call_iv"    : cboe.get("skew_cboe_call_iv"),
            "put_strike" : cboe.get("skew_cboe_put_strike"),
            "put_delta"  : cboe.get("skew_cboe_put_delta"),
            "put_iv"     : cboe.get("skew_cboe_put_iv"),
            "dte"        : cboe.get("skew_cboe_dte"),
        } if cboe.get("skew_25d_cboe") else None,

        "term_intraday_regime"   : cboe.get("term_intraday_regime"),
        "term_intraday_slope"    : cboe.get("term_intraday_slope"),
        "term_intraday_front_dte": cboe.get("term_intraday_front_dte"),
        "term_intraday_back_dte" : cboe.get("term_intraday_back_dte"),
        "term_intraday_iv_front" : cboe.get("term_intraday_iv_front"),
        "term_intraday_iv_back"  : cboe.get("term_intraday_iv_back"),

        # ─── STRUCTURAL (CME 49d+, secondary context) ────────────────────
        "atm_iv_structural"      : cme.get("atm_iv_front"),
        "iv_structural_by_dte"   : cme.get("iv_by_dte"),
        "skew_25d_structural"    : cme.get("skew_25d_front"),
        "skew_structural_by_dte" : cme.get("skew_by_dte"),
        "term_structural_regime" : cme.get("term_regime"),
        "term_structural_slope"  : cme.get("term_slope"),
        "iv_structural_back_dte" : cme.get("iv_back_dte"),
        "iv_structural_back"     : cme.get("iv_back"),

        # Call/Put Wall GEX values (CBOE — structural, all-expirations)
        "call_wall_gex"      : cboe.get("call_wall_gex"),
        "put_wall_gex"       : cboe.get("put_wall_gex"),

        # ─── INTRADAY levels (CBOE 0-7 DTE, primary for scalping) ────────
        "call_wall_intraday_qqq" : cboe.get("call_wall_intraday"),
        "call_wall_intraday_nq"  : qqq_to_nq(cboe.get("call_wall_intraday")),
        "call_wall_intraday_gex" : cboe.get("call_wall_intraday_gex"),
        "put_wall_intraday_qqq"  : cboe.get("put_wall_intraday"),
        "put_wall_intraday_nq"   : qqq_to_nq(cboe.get("put_wall_intraday")),
        "put_wall_intraday_gex"  : cboe.get("put_wall_intraday_gex"),
        "walls_intraday_max_dte" : cboe.get("walls_intraday_max_dte"),

        # ─── Transition levels cTrans/pTrans (Phase 3, TanukiTrade-style) ──
        "c_trans_intraday_qqq"   : cboe.get("c_trans_intraday"),
        "c_trans_intraday_nq"    : qqq_to_nq(cboe.get("c_trans_intraday")),
        "p_trans_intraday_qqq"   : cboe.get("p_trans_intraday"),
        "p_trans_intraday_nq"    : qqq_to_nq(cboe.get("p_trans_intraday")),
        "trans_intraday_max_dte" : cboe.get("trans_intraday_max_dte"),

        # ─── DEX Delta Exposure D+/D- (Phase 4, TanukiTrade-style) ─────────
        "dex_plus_intraday_qqq"  : cboe.get("dex_plus_intraday"),
        "dex_plus_intraday_nq"   : qqq_to_nq(cboe.get("dex_plus_intraday")),
        "dex_plus_intraday_dex"  : cboe.get("dex_plus_intraday_dex"),
        "dex_minus_intraday_qqq" : cboe.get("dex_minus_intraday"),
        "dex_minus_intraday_nq"  : qqq_to_nq(cboe.get("dex_minus_intraday")),
        "dex_minus_intraday_dex" : cboe.get("dex_minus_intraday_dex"),
        "dex_intraday_max_dte"   : cboe.get("dex_intraday_max_dte"),

        # ─── Abs GEX Ab1/Ab2/Ab3 (Phase 5, TanukiTrade-style — pin risk) ───
        "abs_gex_intraday_1_qqq" : cboe.get("abs_gex_intraday_1"),
        "abs_gex_intraday_1_nq"  : qqq_to_nq(cboe.get("abs_gex_intraday_1")),
        "abs_gex_intraday_1_gex" : cboe.get("abs_gex_intraday_1_gex"),
        "abs_gex_intraday_2_qqq" : cboe.get("abs_gex_intraday_2"),
        "abs_gex_intraday_2_nq"  : qqq_to_nq(cboe.get("abs_gex_intraday_2")),
        "abs_gex_intraday_2_gex" : cboe.get("abs_gex_intraday_2_gex"),
        "abs_gex_intraday_3_qqq" : cboe.get("abs_gex_intraday_3"),
        "abs_gex_intraday_3_nq"  : qqq_to_nq(cboe.get("abs_gex_intraday_3")),
        "abs_gex_intraday_3_gex" : cboe.get("abs_gex_intraday_3_gex"),
        "abs_gex_intraday_max_dte": cboe.get("abs_gex_intraday_max_dte"),

        # ─── Extended walls GEX7-GEX10 (Phase 6, TanukiTrade-style) ────────
        "gex_wall_ext_1_qqq"  : cboe.get("gex_wall_ext_1"),
        "gex_wall_ext_1_nq"   : qqq_to_nq(cboe.get("gex_wall_ext_1")),
        "gex_wall_ext_1_gex"  : cboe.get("gex_wall_ext_1_gex"),
        "gex_wall_ext_1_side" : cboe.get("gex_wall_ext_1_side"),
        "gex_wall_ext_2_qqq"  : cboe.get("gex_wall_ext_2"),
        "gex_wall_ext_2_nq"   : qqq_to_nq(cboe.get("gex_wall_ext_2")),
        "gex_wall_ext_2_gex"  : cboe.get("gex_wall_ext_2_gex"),
        "gex_wall_ext_2_side" : cboe.get("gex_wall_ext_2_side"),
        "gex_wall_ext_3_qqq"  : cboe.get("gex_wall_ext_3"),
        "gex_wall_ext_3_nq"   : qqq_to_nq(cboe.get("gex_wall_ext_3")),
        "gex_wall_ext_3_gex"  : cboe.get("gex_wall_ext_3_gex"),
        "gex_wall_ext_3_side" : cboe.get("gex_wall_ext_3_side"),
        "gex_wall_ext_4_qqq"  : cboe.get("gex_wall_ext_4"),
        "gex_wall_ext_4_nq"   : qqq_to_nq(cboe.get("gex_wall_ext_4")),
        "gex_wall_ext_4_gex"  : cboe.get("gex_wall_ext_4_gex"),
        "gex_wall_ext_4_side" : cboe.get("gex_wall_ext_4_side"),
        "gex_walls_ext_max_dte": cboe.get("gex_walls_ext_max_dte"),

        # ─── Volume Flow V1/V2/V3 (Phase 7, TanukiTrade-style) ─────────────
        **{f"vol_flow_{i}_qqq": cboe.get(f"vol_flow_{i}") for i in range(1, 4)},
        **{f"vol_flow_{i}_nq":  qqq_to_nq(cboe.get(f"vol_flow_{i}")) for i in range(1, 4)},
        **{f"vol_flow_{i}_total": cboe.get(f"vol_flow_{i}_total") for i in range(1, 4)},
        "vol_flow_intraday_max_dte": cboe.get("vol_flow_intraday_max_dte"),

        # Intraday mode (cumulative ∑ vs selected ⊙)
        "intraday_mode"          : cboe.get("intraday_mode"),
        "intraday_max_dte_param" : cboe.get("intraday_max_dte_param"),

        "top_oi_intraday"    : [
            {
                "strike_qqq" : s["strike"],
                "strike_nq"  : qqq_to_nq(s["strike"]),
                "call_oi"    : s["call_oi"],
                "put_oi"     : s["put_oi"],
                "total_oi"   : s["total_oi"],
            }
            for s in cboe.get("top_oi_intraday", [])
        ],

        # ─── 0DTE levels (Phase C — end of session, acute pinning) ────────
        "max_pain_0dte_qqq"     : cboe.get("max_pain_0dte_qqq"),
        "max_pain_0dte_nq"      : qqq_to_nq(cboe.get("max_pain_0dte_qqq")),
        "pin_strike_0dte_qqq"   : cboe.get("pin_strike_0dte_qqq"),
        "pin_strike_0dte_nq"    : qqq_to_nq(cboe.get("pin_strike_0dte_qqq")),
        "charm_magnet_0dte_qqq" : cboe.get("charm_magnet_0dte_qqq"),
        "charm_magnet_0dte_nq"  : qqq_to_nq(cboe.get("charm_magnet_0dte_qqq")),
        "zero_dte_oi_total"     : cboe.get("zero_dte_oi_total"),
        "zero_dte_dte"          : cboe.get("zero_dte_dte"),

        # CBOE metrics converted to NQ — prefer TastyTrade EM if available
        "max_pain_qqq"       : cboe.get("max_pain"),
        "max_pain_nq"        : qqq_to_nq(cboe.get("max_pain")),
        "expected_move_qqq"  : cboe.get("expected_move_tt") or cboe.get("expected_move"),
        "expected_move_nq"   : qqq_to_nq(cboe.get("expected_move_tt") or cboe.get("expected_move")),
        "range_bas_qqq"      : cboe.get("expected_move_tt_low")  or cboe.get("range_bas"),
        "range_haut_qqq"     : cboe.get("expected_move_tt_high") or cboe.get("range_haut"),
        "range_bas_nq"       : qqq_to_nq(cboe.get("expected_move_tt_low")  or cboe.get("range_bas")),
        "range_haut_nq"      : qqq_to_nq(cboe.get("expected_move_tt_high") or cboe.get("range_haut")),
        "expected_move_tt_qqq" : cboe.get("expected_move_tt"),
        "expected_move_tt_nq"  : qqq_to_nq(cboe.get("expected_move_tt")),
        "expected_move_tt_dte" : cboe.get("expected_move_tt_dte"),
        "expected_move_iv_qqq" : cboe.get("expected_move"),
        "expected_move_iv_nq"  : qqq_to_nq(cboe.get("expected_move")),
        "pcr"                : cboe.get("pcr"),

        # VIX context (yfinance)
        "vix"                : vix.get("vix"),
        "vix9d"              : vix.get("vix9d"),
        "vix_regime"         : vix.get("vix_regime"),
        "vix_term"           : vix.get("vix_term"),
        "vix_term_slope"     : vix.get("vix_term_slope"),
        "vix_dod_change"     : vix.get("vix_dod_change"),

        # Macro blackout (Forex Factory ±30min High-impact USD events)
        "macro_in_blackout"     : blackout.get("in_blackout", False),
        "macro_blackout_until"  : blackout.get("blackout_until_utc"),
        "macro_current_event"   : blackout.get("current_event"),
        "macro_next_event"      : blackout.get("next_event"),
        "macro_minutes_to_next" : blackout.get("minutes_to_next"),

        # Top OI strikes QQQ → NQ
        "top_oi_strikes"     : [
            {
                "strike_qqq" : s["strike"],
                "strike_nq"  : qqq_to_nq(s["strike"]),
                "call_oi"    : s["call_oi"],
                "put_oi"     : s["put_oi"],
                "total_oi"   : s["total_oi"],
            }
            for s in cboe.get("top_oi_strikes", [])
        ],
    }

    # Match CME front DTE to closest CBOE expiration for fair comparison
    cme_front_dte = None
    if full.get("iv_structural_by_dte"):
        try:
            cme_front_dte = min(int(d) for d in full["iv_structural_by_dte"].keys())
        except Exception:
            pass
    cboe_by_dte = full.get("skew_25d_intraday_by_dte") or {}
    if cme_front_dte and cboe_by_dte:
        items = [(int(k), v) for k, v in cboe_by_dte.items()]
        match_dte, match_skew = min(items, key=lambda x: abs(x[0] - cme_front_dte))
        full["skew_25d_cboe_match"]     = match_skew
        full["skew_25d_cboe_match_dte"] = match_dte

    # IV Rank (Phase 3) — computed from the snapshots history, BEFORE
    # saving today's snapshot (otherwise self-reference).
    iv_id = full.get("atm_iv_intraday")
    if iv_id and iv_id > 0:
        full["iv_rank_intraday"] = compute_iv_rank("NQ", iv_id,
                                                   iv_field="atm_iv_intraday")
    iv_str = full.get("atm_iv_structural")
    if iv_str and iv_str > 0:
        full["iv_rank_structural"] = compute_iv_rank("NQ", iv_str,
                                                     iv_field="atm_iv_structural")

    # Block 7: versioning + health check
    from config import JSON_SCHEMA_VERSION, compute_data_quality
    full["json_schema_version"] = JSON_SCHEMA_VERSION
    full["last_update_utc"]     = datetime.now(timezone.utc).isoformat()
    full["data_quality"]        = compute_data_quality(full)

    FULL_JSON.parent.mkdir(parents=True, exist_ok=True)
    FULL_JSON.write_text(json.dumps(full, indent=2))

    # Daily snapshot (Phase 1.3) — history for IVR (Phase 3)
    snap_path = save_snapshot("NQ", full)
    print(f"  Snapshot -> {snap_path}")

    # Backup tarball (Block 6) — protects the 252-day IVR history
    try:
        from backup_snapshots import make_backup, cleanup_old_backups
        bk = make_backup()
        if bk:
            cleanup_old_backups()
            print(f"  Backup   -> {bk.name}")
    except Exception as e:
        print(f"  ⚠ backup warning: {e}")

    # Console summary
    cw_gex = full.get("call_wall_gex")
    pw_gex = full.get("put_wall_gex")
    em_nq  = full.get("expected_move_nq")
    tops   = full.get("top_oi_strikes", [])

    print(f"  Spot NQ          : {nq_spot:.0f}")
    print(f"  Spot QQQ         : {qqq_spot:.2f}  (ratio {ratio:.2f})")
    print(f"  Gamma Flip NQ    : {full['gamma_flip']}")
    print(f"  Vol Trigger NQ   : {full['vol_trigger']}")
    if cw_gex is not None:
        print(f"  Call Wall NQ     : {full['call_wall']}  (GEX {cw_gex:,.0f})")
    else:
        print(f"  Call Wall NQ     : {full['call_wall']}")
    if pw_gex is not None:
        print(f"  Put Wall NQ      : {full['put_wall']}  (GEX {pw_gex:,.0f})")
    else:
        print(f"  Put Wall NQ      : {full['put_wall']}")
    print(f"  Risk Pivot NQ    : {full['risk_pivot']}")
    print(f"  Vanna Flip NQ    : {full['vanna_flip']}")
    print(f"  Charm Magnet NQ  : {full['charm_magnet']}")
    # ─── Intraday metrics (primary for scalping) ─────────────────────────
    iv_id = full.get("atm_iv_intraday")
    if iv_id:
        ivr = full.get("iv_rank_intraday") or {}
        ivr_str = ""
        if ivr.get("ivr") is not None:
            ivr_str = f"  IVR {ivr['ivr']:.0f}% ({ivr['n_samples']}d hist., {ivr['status']})"
        elif ivr.get("status"):
            ivr_str = f"  (IVR {ivr['status']}, {ivr.get('n_samples',0)}d hist.)"
        print(f"  IVx intraday     : {iv_id*100:.1f}%  (QQQ {full.get('atm_iv_intraday_dte','?')} DTE){ivr_str}")
    sk_id = full.get("skew_25d_intraday")
    if sk_id is not None:
        d = full.get('skew_25d_intraday_dte', '?')
        print(f"  Skew 25d intraday: {sk_id*100:+.2f} vol pts  "
              f"(QQQ {d} DTE — {'bearish' if sk_id > 0 else 'bullish'})")
    tr_id = full.get("term_intraday_regime")
    if tr_id and tr_id != "unknown":
        sl = full.get('term_intraday_slope', 0) or 0
        fdte = full.get('term_intraday_front_dte', 0)
        bdte = full.get('term_intraday_back_dte', 0)
        ivf = (full.get('term_intraday_iv_front') or 0)*100
        ivb = (full.get('term_intraday_iv_back') or 0)*100
        print(f"  Term intraday    : {ivf:.1f}% ({fdte}d) → {ivb:.1f}% ({bdte}d)  "
              f"({tr_id}, {sl*100:+.2f} vp)")

    # ─── Structural (CME 49d+ context) ───────────────────────────────────
    if full.get("atm_iv_structural"):
        print(f"  IVx structural   : {full['atm_iv_structural']*100:.1f}%  (CME 49d)")
    if full.get("skew_25d_structural") is not None:
        sk = full['skew_25d_structural']
        print(f"  Skew structural  : {sk*100:+.2f} vol pts  (CME 49d, may be inflated by illiquid OTM calls)")
    if full.get("term_structural_regime") and full.get("term_structural_regime") != "unknown":
        slope = full.get('term_structural_slope', 0) or 0
        print(f"  Term structural  : {full['term_structural_regime']} ({slope*100:+.2f} vp, CME 49d→{full.get('iv_structural_back_dte', 0)}d)")
    print(f"  Max Pain NQ      : {full['max_pain_nq']}  (QQQ {full['max_pain_qqq']})")
    if em_nq:
        em_tt_dte = full.get('expected_move_tt_dte')
        tag = f" (TastyTrade {em_tt_dte}DTE)" if full.get('expected_move_tt_nq') else " (IV-based)"
        print(f"  Expected Move NQ : +/-{em_nq} pts{tag}")
        print(f"  Range NQ         : [{full['range_bas_nq']} - {full['range_haut_nq']}]")
    print(f"  PCR              : {full['pcr']}  ({'put-heavy' if (full['pcr'] or 0) > 1 else 'call-heavy'})")
    if len(tops) >= 3:
        print(f"  Top OI #1 (str.) : NQ {tops[0]['strike_nq']}  (OI {tops[0]['total_oi']:,.0f})")
        print(f"  Top OI #2 (str.) : NQ {tops[1]['strike_nq']}  (OI {tops[1]['total_oi']:,.0f})")
        print(f"  Top OI #3 (str.) : NQ {tops[2]['strike_nq']}  (OI {tops[2]['total_oi']:,.0f})")

    # INTRADAY levels (0-7 DTE, primary for scalping)
    cw_id = full.get("call_wall_intraday_nq")
    pw_id = full.get("put_wall_intraday_nq")
    if cw_id and pw_id:
        max_dte = full.get("walls_intraday_max_dte", 7)
        print(f"  Call Wall ID     : NQ {cw_id}  (GEX {full.get('call_wall_intraday_gex',0):,.0f})  [0-{max_dte}d]")
        print(f"  Put Wall ID      : NQ {pw_id}  (GEX {full.get('put_wall_intraday_gex',0):,.0f})  [0-{max_dte}d]")
    ct_nq = full.get("c_trans_intraday_nq")
    pt_nq = full.get("p_trans_intraday_nq")
    if ct_nq or pt_nq:
        ct_str = f"NQ {ct_nq}" if ct_nq else "—"
        pt_str = f"NQ {pt_nq}" if pt_nq else "—"
        print(f"  cTrans intraday  : {ct_str}  [call gamma dominant above]")
        print(f"  pTrans intraday  : {pt_str}  [put gamma dominant below]")
    dp_nq = full.get("dex_plus_intraday_nq")
    dm_nq = full.get("dex_minus_intraday_nq")
    if dp_nq or dm_nq:
        dp_str = f"NQ {dp_nq} (DEX {full.get('dex_plus_intraday_dex',0):,.0f})" if dp_nq else "—"
        dm_str = f"NQ {dm_nq} (DEX {full.get('dex_minus_intraday_dex',0):,.0f})" if dm_nq else "—"
        print(f"  D+ DEX intraday  : {dp_str}  [dealers buy → bullish]")
        print(f"  D- DEX intraday  : {dm_str}  [dealers sell → bearish]")
    for i in range(1, 4):
        ab = full.get(f"abs_gex_intraday_{i}_nq")
        if ab:
            g = full.get(f"abs_gex_intraday_{i}_gex", 0) or 0
            print(f"  Abs GEX Ab{i}     : NQ {ab}  (|GEX| {g:,.0f})  [pin risk]")
    tops_id = full.get("top_oi_intraday", [])
    if len(tops_id) >= 3:
        print(f"  Top OI ID #1     : NQ {tops_id[0]['strike_nq']}  (OI {tops_id[0]['total_oi']:,.0f})")
        print(f"  Top OI ID #2     : NQ {tops_id[1]['strike_nq']}  (OI {tops_id[1]['total_oi']:,.0f})")
        print(f"  Top OI ID #3     : NQ {tops_id[2]['strike_nq']}  (OI {tops_id[2]['total_oi']:,.0f})")
    if full.get("pin_strike_0dte_nq"):
        d = full.get('zero_dte_dte', 0)
        print(f"  Max Pain 0DTE    : NQ {full['max_pain_0dte_nq']}  ({d}DTE)")
        print(f"  Pin Strike 0DTE  : NQ {full['pin_strike_0dte_nq']}  (gamma max)")
        print(f"  Charm Mag. 0DTE  : NQ {full['charm_magnet_0dte_nq']}  (near spot)")
    print(f"  -> {FULL_JSON} OK")
    return full


def run_agent():
    """Run Claude AI briefing."""
    step("STEP 4 — Claude AI briefing")
    from claude_agent_NQ import run_briefing
    run_briefing()


def run_pdf():
    """Generate PDF briefing."""
    step("STEP 5 — PDF generation")
    from generate_pdf_NQ import build_pdf
    briefing = json.loads(NQ_BRIEFING_JSON.read_text(encoding="utf-8"))
    path = build_pdf(briefing)
    print(f"  PDF -> {path}")


if __name__ == "__main__":
    from logging_setup import setup_logging
    setup_logging()

    def _pause_console():
        """Prevents the cmd window from closing instantly (launched from ATAS button)."""
        try:
            input("\n  Press ENTER to close this window...")
        except (EOFError, KeyboardInterrupt, OSError):
            pass

    try:
        import argparse
        p = argparse.ArgumentParser(description="NQ morning pipeline (CME + CBOE + Claude + PDF)")
        p.add_argument("--fast", action="store_true",
                       help="Fast mode: skip Claude AI + PDF (CME + CBOE → JSON only)")
        p.add_argument("--skip-cme", action="store_true",
                       help="Skip CME scraping (uses the last existing CME JSON)")
        p.add_argument("--max-dte", type=int, default=7,
                       help="Max intraday CBOE DTE. 7=cumulative ∑ (default), 0=selected ⊙ 0DTE.")
        p.add_argument("--ignore-holiday", action="store_true",
                       help="Continue even if NYSE closed today (otherwise clean abort).")
        args = p.parse_args()

        # NYSE holidays / weekends: no session → abort unless overridden
        from market_calendar import is_market_open_today, is_early_close_today
        if not is_market_open_today() and not args.ignore_holiday:
            print(f"\n  ABORT — NYSE closed today (weekend or holiday).")
            print(f"  Override with --ignore-holiday to fetch anyway.")
            _pause_console()
            sys.exit(0)

        early_close = is_early_close_today()
        mode_label = "FAST (no AI/PDF)" if args.fast else "FULL"
        if early_close:
            mode_label += " ⚠ EARLY-CLOSE 13:00 ET"
        print(f"\n{'='*55}")
        print(f"  GEX AGENT NQ — Morning Run [{mode_label}]")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}  max_dte={args.max_dte}")
        print(f"{'='*55}")

        if not args.skip_cme:
            try:
                run_cme()
            except Exception as e:
                print(f"  WARNING: CME failed: {e}")
                print(f"  Continuing with existing JSON if available...")
        else:
            print(f"  STEP 1 — SKIP CME (--skip-cme)")

        # Patch the CBOE call with max_dte
        from data_fetcher_NQ import build_levels
        step("STEP 2 — Fetch CBOE QQQ options")
        build_levels(max_dte=args.max_dte)

        merge_levels()
        if not args.fast:
            run_agent()
            run_pdf()
        else:
            print(f"\n  FAST mode: skip Claude AI + PDF.")
    except SystemExit:
        _pause_console()
        raise
    except Exception as e:
        import traceback
        print(f"\n  ❌ ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        _pause_console()
        sys.exit(1)
    _pause_console()
