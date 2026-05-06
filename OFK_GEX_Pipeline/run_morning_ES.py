"""
run_morning_ES.py — Main orchestrator for ES E-mini S&P500
Steps: CME ES -> CBOE SPY -> merge -> Claude briefing -> PDF

Usage: py run_morning_ES.py
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

from config import (
    PIPELINE_ROOT,
    ES_GEX_JSON    as GEX_JSON,
    ES_LEVELS_JSON as LEVELS_JSON,
    ES_FULL_JSON   as FULL_JSON,
    ES_BRIEFING_JSON,
    save_snapshot,
    compute_iv_rank,
)

PROJECT_DIR = PIPELINE_ROOT


def step(msg: str):
    print(f"\n{'─'*55}")
    print(f"  {msg}")
    print(f"{'─'*55}")


def run_cme():
    """Launch CME ES script (opens visible Chromium browser)."""
    step("STEP 1 — Fetch CME ES options")
    result = subprocess.run(
        [sys.executable, "cme_ES_browser_fetch.py"],
        cwd=str(PIPELINE_ROOT)
    )
    if result.returncode != 0:
        raise RuntimeError("CME ES fetch failed")
    print("  CME ES -> ES_gex_latest.json OK")


def run_cboe():
    """Fetch CBOE SPY options chain (ES proxy)."""
    step("STEP 2 — Fetch CBOE SPY options")
    from data_fetcher_ES import build_levels_ES
    return build_levels_ES()


def merge_levels() -> dict:
    """Merge CME ES (native levels) + CBOE SPY (missing metrics) + VIX context."""
    step("STEP 3 — Merge data sources")

    cme  = json.loads(GEX_JSON.read_text())   if GEX_JSON.exists()   else {}
    cboe = json.loads(LEVELS_JSON.read_text()) if LEVELS_JSON.exists() else {}
    from vix_fetcher import fetch_vix
    from econ_calendar import blackout_status
    vix      = fetch_vix()
    blackout = blackout_status()

    es_spot  = cme.get("spot", 0)
    spy_spot = cboe.get("spot", 0)

    # SPY/ES ratio: SPY ~= ES / 10 (e.g. SPY 700 = ES 7000)
    # Use the real ratio computed from both spot prices
    ratio = es_spot / spy_spot if spy_spot > 0 else 10.0

    def spy_to_es(val):
        return round(val * ratio) if val else None

    full = {
        # Metadata
        "generated_at"       : datetime.now(timezone.utc).isoformat(),
        "trade_date"         : cme.get("trade_date"),
        "spot_es"            : es_spot,
        "spot_spy"           : spy_spot,
        "spy_es_ratio"       : round(ratio, 4),

        # Native ES levels (CME)
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

        # ─── PRIMAIRE SCALPING (CBOE intraday 0-7 DTE) ───────────────────
        "atm_iv_intraday"        : cboe.get("atm_iv_intraday"),
        "atm_iv_intraday_dte"    : cboe.get("atm_iv_intraday_dte"),
        "atm_iv_intraday_by_dte" : cboe.get("atm_iv_intraday_by_dte"),

        "skew_25d_intraday"      : cboe.get("skew_25d_cboe"),
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

        # ─── STRUCTUREL (CME 49d+, contexte secondaire) ──────────────────
        "atm_iv_structural"      : cme.get("atm_iv_front"),
        "iv_structural_by_dte"   : cme.get("iv_by_dte"),
        "skew_25d_structural"    : cme.get("skew_25d_front"),
        "skew_structural_by_dte" : cme.get("skew_by_dte"),
        "term_structural_regime" : cme.get("term_regime"),
        "term_structural_slope"  : cme.get("term_slope"),
        "iv_structural_back_dte" : cme.get("iv_back_dte"),
        "iv_structural_back"     : cme.get("iv_back"),

        # Call/Put Wall GEX values (CBOE SPY — structurel)
        "call_wall_gex"      : cboe.get("call_wall_gex"),
        "put_wall_gex"       : cboe.get("put_wall_gex"),

        # ─── Niveaux INTRADAY (CBOE 0-7 DTE, primaires scalping) ─────────
        "call_wall_intraday_spy" : cboe.get("call_wall_intraday"),
        "call_wall_intraday_es"  : spy_to_es(cboe.get("call_wall_intraday")),
        "call_wall_intraday_gex" : cboe.get("call_wall_intraday_gex"),
        "put_wall_intraday_spy"  : cboe.get("put_wall_intraday"),
        "put_wall_intraday_es"   : spy_to_es(cboe.get("put_wall_intraday")),
        "put_wall_intraday_gex"  : cboe.get("put_wall_intraday_gex"),
        "walls_intraday_max_dte" : cboe.get("walls_intraday_max_dte"),

        # ─── Transition levels cTrans/pTrans (Phase 3, TanukiTrade-style) ──
        "c_trans_intraday_spy"   : cboe.get("c_trans_intraday"),
        "c_trans_intraday_es"    : spy_to_es(cboe.get("c_trans_intraday")),
        "p_trans_intraday_spy"   : cboe.get("p_trans_intraday"),
        "p_trans_intraday_es"    : spy_to_es(cboe.get("p_trans_intraday")),
        "trans_intraday_max_dte" : cboe.get("trans_intraday_max_dte"),

        # ─── DEX Delta Exposure D+/D- (Phase 4, TanukiTrade-style) ─────────
        "dex_plus_intraday_spy"  : cboe.get("dex_plus_intraday"),
        "dex_plus_intraday_es"   : spy_to_es(cboe.get("dex_plus_intraday")),
        "dex_plus_intraday_dex"  : cboe.get("dex_plus_intraday_dex"),
        "dex_minus_intraday_spy" : cboe.get("dex_minus_intraday"),
        "dex_minus_intraday_es"  : spy_to_es(cboe.get("dex_minus_intraday")),
        "dex_minus_intraday_dex" : cboe.get("dex_minus_intraday_dex"),
        "dex_intraday_max_dte"   : cboe.get("dex_intraday_max_dte"),

        # ─── Abs GEX Ab1/Ab2/Ab3 (Phase 5, TanukiTrade-style — pin risk) ───
        "abs_gex_intraday_1_spy" : cboe.get("abs_gex_intraday_1"),
        "abs_gex_intraday_1_es"  : spy_to_es(cboe.get("abs_gex_intraday_1")),
        "abs_gex_intraday_1_gex" : cboe.get("abs_gex_intraday_1_gex"),
        "abs_gex_intraday_2_spy" : cboe.get("abs_gex_intraday_2"),
        "abs_gex_intraday_2_es"  : spy_to_es(cboe.get("abs_gex_intraday_2")),
        "abs_gex_intraday_2_gex" : cboe.get("abs_gex_intraday_2_gex"),
        "abs_gex_intraday_3_spy" : cboe.get("abs_gex_intraday_3"),
        "abs_gex_intraday_3_es"  : spy_to_es(cboe.get("abs_gex_intraday_3")),
        "abs_gex_intraday_3_gex" : cboe.get("abs_gex_intraday_3_gex"),
        "abs_gex_intraday_max_dte": cboe.get("abs_gex_intraday_max_dte"),

        # ─── Extended walls GEX7-GEX10 (Phase 6, TanukiTrade-style) ────────
        "gex_wall_ext_1_spy"  : cboe.get("gex_wall_ext_1"),
        "gex_wall_ext_1_es"   : spy_to_es(cboe.get("gex_wall_ext_1")),
        "gex_wall_ext_1_gex"  : cboe.get("gex_wall_ext_1_gex"),
        "gex_wall_ext_1_side" : cboe.get("gex_wall_ext_1_side"),
        "gex_wall_ext_2_spy"  : cboe.get("gex_wall_ext_2"),
        "gex_wall_ext_2_es"   : spy_to_es(cboe.get("gex_wall_ext_2")),
        "gex_wall_ext_2_gex"  : cboe.get("gex_wall_ext_2_gex"),
        "gex_wall_ext_2_side" : cboe.get("gex_wall_ext_2_side"),
        "gex_wall_ext_3_spy"  : cboe.get("gex_wall_ext_3"),
        "gex_wall_ext_3_es"   : spy_to_es(cboe.get("gex_wall_ext_3")),
        "gex_wall_ext_3_gex"  : cboe.get("gex_wall_ext_3_gex"),
        "gex_wall_ext_3_side" : cboe.get("gex_wall_ext_3_side"),
        "gex_wall_ext_4_spy"  : cboe.get("gex_wall_ext_4"),
        "gex_wall_ext_4_es"   : spy_to_es(cboe.get("gex_wall_ext_4")),
        "gex_wall_ext_4_gex"  : cboe.get("gex_wall_ext_4_gex"),
        "gex_wall_ext_4_side" : cboe.get("gex_wall_ext_4_side"),
        "gex_walls_ext_max_dte": cboe.get("gex_walls_ext_max_dte"),

        # ─── Volume Flow V1/V2/V3 (Phase 7, TanukiTrade-style) ─────────────
        **{f"vol_flow_{i}_spy": cboe.get(f"vol_flow_{i}") for i in range(1, 4)},
        **{f"vol_flow_{i}_es":  spy_to_es(cboe.get(f"vol_flow_{i}")) for i in range(1, 4)},
        **{f"vol_flow_{i}_total": cboe.get(f"vol_flow_{i}_total") for i in range(1, 4)},
        "vol_flow_intraday_max_dte": cboe.get("vol_flow_intraday_max_dte"),

        # Mode intraday (cumulative ∑ vs selected ⊙)
        "intraday_mode"          : cboe.get("intraday_mode"),
        "intraday_max_dte_param" : cboe.get("intraday_max_dte_param"),

        "top_oi_intraday"    : [
            {
                "strike_spy" : s["strike"],
                "strike_es"  : spy_to_es(s["strike"]),
                "call_oi"    : s["call_oi"],
                "put_oi"     : s["put_oi"],
                "total_oi"   : s["total_oi"],
            }
            for s in cboe.get("top_oi_intraday", [])
        ],

        # ─── Niveaux 0DTE (Phase C — fin de session, pinning aigu) ────────
        "max_pain_0dte_spy"     : cboe.get("max_pain_0dte_spy"),
        "max_pain_0dte_es"      : spy_to_es(cboe.get("max_pain_0dte_spy")),
        "pin_strike_0dte_spy"   : cboe.get("pin_strike_0dte_spy"),
        "pin_strike_0dte_es"    : spy_to_es(cboe.get("pin_strike_0dte_spy")),
        "charm_magnet_0dte_spy" : cboe.get("charm_magnet_0dte_spy"),
        "charm_magnet_0dte_es"  : spy_to_es(cboe.get("charm_magnet_0dte_spy")),
        "zero_dte_oi_total"     : cboe.get("zero_dte_oi_total"),
        "zero_dte_dte"          : cboe.get("zero_dte_dte"),

        # CBOE metrics converted to ES — privilégie l'EM TastyTrade si dispo
        "max_pain_spy"       : cboe.get("max_pain"),
        "max_pain_es"        : spy_to_es(cboe.get("max_pain")),
        "expected_move_spy"  : cboe.get("expected_move_tt") or cboe.get("expected_move"),
        "expected_move_es"   : spy_to_es(cboe.get("expected_move_tt") or cboe.get("expected_move")),
        "range_bas_spy"      : cboe.get("expected_move_tt_low")  or cboe.get("range_bas"),
        "range_haut_spy"     : cboe.get("expected_move_tt_high") or cboe.get("range_haut"),
        "range_bas_es"       : spy_to_es(cboe.get("expected_move_tt_low")  or cboe.get("range_bas")),
        "range_haut_es"      : spy_to_es(cboe.get("expected_move_tt_high") or cboe.get("range_haut")),
        "expected_move_tt_spy" : cboe.get("expected_move_tt"),
        "expected_move_tt_es"  : spy_to_es(cboe.get("expected_move_tt")),
        "expected_move_tt_dte" : cboe.get("expected_move_tt_dte"),
        "expected_move_iv_spy" : cboe.get("expected_move"),
        "expected_move_iv_es"  : spy_to_es(cboe.get("expected_move")),
        "pcr"                : cboe.get("pcr"),

        # VIX context (yfinance)
        "vix"                : vix.get("vix"),
        "vix9d"              : vix.get("vix9d"),
        "vix_regime"         : vix.get("vix_regime"),
        "vix_term"           : vix.get("vix_term"),
        "vix_term_slope"     : vix.get("vix_term_slope"),
        "vix_dod_change"     : vix.get("vix_dod_change"),

        # Macro blackout (Forex Factory ±30min événements High USD)
        "macro_in_blackout"     : blackout.get("in_blackout", False),
        "macro_blackout_until"  : blackout.get("blackout_until_utc"),
        "macro_current_event"   : blackout.get("current_event"),
        "macro_next_event"      : blackout.get("next_event"),
        "macro_minutes_to_next" : blackout.get("minutes_to_next"),

        # Top OI strikes SPY -> ES
        "top_oi_strikes"     : [
            {
                "strike_spy" : s["strike"],
                "strike_es"  : spy_to_es(s["strike"]),
                "call_oi"    : s["call_oi"],
                "put_oi"     : s["put_oi"],
                "total_oi"   : s["total_oi"],
            }
            for s in cboe.get("top_oi_strikes", [])
        ],
    }

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

    # IV Rank (Phase 3) — calculé sur l'historique avant save_snapshot.
    iv_id = full.get("atm_iv_intraday")
    if iv_id and iv_id > 0:
        full["iv_rank_intraday"] = compute_iv_rank("ES", iv_id,
                                                   iv_field="atm_iv_intraday")
    iv_str = full.get("atm_iv_structural")
    if iv_str and iv_str > 0:
        full["iv_rank_structural"] = compute_iv_rank("ES", iv_str,
                                                     iv_field="atm_iv_structural")

    # Bloc 7 : versioning + health check
    from config import JSON_SCHEMA_VERSION, compute_data_quality
    full["json_schema_version"] = JSON_SCHEMA_VERSION
    full["last_update_utc"]     = datetime.now(timezone.utc).isoformat()
    full["data_quality"]        = compute_data_quality(full)

    FULL_JSON.parent.mkdir(parents=True, exist_ok=True)
    FULL_JSON.write_text(json.dumps(full, indent=2))

    # Snapshot quotidien (Phase 1.3) — historique pour IVR (Phase 3)
    snap_path = save_snapshot("ES", full)
    print(f"  Snapshot -> {snap_path}")

    # Backup tarball (Bloc 6) — protège les 252 jours d'historique IVR
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
    em_es  = full.get("expected_move_es")
    tops   = full.get("top_oi_strikes", [])

    print(f"  Spot ES          : {es_spot:.0f}")
    print(f"  Spot SPY         : {spy_spot:.2f}  (ratio {ratio:.2f})")
    print(f"  Gamma Flip ES    : {full['gamma_flip']}")
    print(f"  Vol Trigger ES   : {full['vol_trigger']}")
    if cw_gex is not None:
        print(f"  Call Wall ES     : {full['call_wall']}  (GEX {cw_gex:,.0f})")
    else:
        print(f"  Call Wall ES     : {full['call_wall']}")
    if pw_gex is not None:
        print(f"  Put Wall ES      : {full['put_wall']}  (GEX {pw_gex:,.0f})")
    else:
        print(f"  Put Wall ES      : {full['put_wall']}")
    print(f"  Risk Pivot ES    : {full['risk_pivot']}")
    print(f"  Vanna Flip ES    : {full['vanna_flip']}")
    print(f"  Charm Magnet ES  : {full['charm_magnet']}")
    # ─── Métriques intraday (primaires scalping) ─────────────────────────
    iv_id = full.get("atm_iv_intraday")
    if iv_id:
        ivr = full.get("iv_rank_intraday") or {}
        ivr_str = ""
        if ivr.get("ivr") is not None:
            ivr_str = f"  IVR {ivr['ivr']:.0f}% ({ivr['n_samples']}d hist., {ivr['status']})"
        elif ivr.get("status"):
            ivr_str = f"  (IVR {ivr['status']}, {ivr.get('n_samples',0)}d hist.)"
        print(f"  IVx intraday     : {iv_id*100:.1f}%  (SPY {full.get('atm_iv_intraday_dte','?')} DTE){ivr_str}")
    sk_id = full.get("skew_25d_intraday")
    if sk_id is not None:
        d = full.get('skew_25d_intraday_dte', '?')
        print(f"  Skew 25d intraday: {sk_id*100:+.2f} vol pts  "
              f"(SPY {d} DTE — {'bearish' if sk_id > 0 else 'bullish'})")
    tr_id = full.get("term_intraday_regime")
    if tr_id and tr_id != "unknown":
        sl = full.get('term_intraday_slope', 0) or 0
        fdte = full.get('term_intraday_front_dte', 0)
        bdte = full.get('term_intraday_back_dte', 0)
        ivf = (full.get('term_intraday_iv_front') or 0)*100
        ivb = (full.get('term_intraday_iv_back') or 0)*100
        print(f"  Term intraday    : {ivf:.1f}% ({fdte}d) → {ivb:.1f}% ({bdte}d)  "
              f"({tr_id}, {sl*100:+.2f} vp)")

    # ─── Structurel (contexte CME 49d+) ──────────────────────────────────
    if full.get("atm_iv_structural"):
        print(f"  IVx structural   : {full['atm_iv_structural']*100:.1f}%  (CME 49d)")
    if full.get("skew_25d_structural") is not None:
        sk = full['skew_25d_structural']
        print(f"  Skew structural  : {sk*100:+.2f} vol pts  (CME 49d, peut être gonflé par OTM calls illiquides)")
    if full.get("term_structural_regime") and full.get("term_structural_regime") != "unknown":
        slope = full.get('term_structural_slope', 0) or 0
        print(f"  Term structural  : {full['term_structural_regime']} ({slope*100:+.2f} vp, CME 49d→{full.get('iv_structural_back_dte', 0)}d)")
    print(f"  Max Pain ES      : {full['max_pain_es']}  (SPY {full['max_pain_spy']})")
    if em_es:
        em_tt_dte = full.get('expected_move_tt_dte')
        tag = f" (TastyTrade {em_tt_dte}DTE)" if full.get('expected_move_tt_es') else " (IV-based)"
        print(f"  Expected Move ES : +/-{em_es} pts{tag}")
        print(f"  Range ES         : [{full['range_bas_es']} — {full['range_haut_es']}]")
    print(f"  PCR              : {full['pcr']}  ({'put-heavy' if (full['pcr'] or 0) > 1 else 'call-heavy'})")
    if len(tops) >= 3:
        print(f"  Top OI #1 (str.) : ES {tops[0]['strike_es']}  (OI {tops[0]['total_oi']:,.0f})")
        print(f"  Top OI #2 (str.) : ES {tops[1]['strike_es']}  (OI {tops[1]['total_oi']:,.0f})")
        print(f"  Top OI #3 (str.) : ES {tops[2]['strike_es']}  (OI {tops[2]['total_oi']:,.0f})")

    # Niveaux INTRADAY (0-7 DTE, primaires scalping)
    cw_id = full.get("call_wall_intraday_es")
    pw_id = full.get("put_wall_intraday_es")
    if cw_id and pw_id:
        max_dte = full.get("walls_intraday_max_dte", 7)
        print(f"  Call Wall ID     : ES {cw_id}  (GEX {full.get('call_wall_intraday_gex',0):,.0f})  [0-{max_dte}d]")
        print(f"  Put Wall ID      : ES {pw_id}  (GEX {full.get('put_wall_intraday_gex',0):,.0f})  [0-{max_dte}d]")
    ct_es = full.get("c_trans_intraday_es")
    pt_es = full.get("p_trans_intraday_es")
    if ct_es or pt_es:
        ct_str = f"ES {ct_es}" if ct_es else "—"
        pt_str = f"ES {pt_es}" if pt_es else "—"
        print(f"  cTrans intraday  : {ct_str}  [call gamma dominant au-dessus]")
        print(f"  pTrans intraday  : {pt_str}  [put gamma dominant en-dessous]")
    dp_es = full.get("dex_plus_intraday_es")
    dm_es = full.get("dex_minus_intraday_es")
    if dp_es or dm_es:
        dp_str = f"ES {dp_es} (DEX {full.get('dex_plus_intraday_dex',0):,.0f})" if dp_es else "—"
        dm_str = f"ES {dm_es} (DEX {full.get('dex_minus_intraday_dex',0):,.0f})" if dm_es else "—"
        print(f"  D+ DEX intraday  : {dp_str}  [dealers achètent → bullish]")
        print(f"  D- DEX intraday  : {dm_str}  [dealers vendent → bearish]")
    for i in range(1, 4):
        ab = full.get(f"abs_gex_intraday_{i}_es")
        if ab:
            g = full.get(f"abs_gex_intraday_{i}_gex", 0) or 0
            print(f"  Abs GEX Ab{i}     : ES {ab}  (|GEX| {g:,.0f})  [pin risk]")
    tops_id = full.get("top_oi_intraday", [])
    if len(tops_id) >= 3:
        print(f"  Top OI ID #1     : ES {tops_id[0]['strike_es']}  (OI {tops_id[0]['total_oi']:,.0f})")
        print(f"  Top OI ID #2     : ES {tops_id[1]['strike_es']}  (OI {tops_id[1]['total_oi']:,.0f})")
        print(f"  Top OI ID #3     : ES {tops_id[2]['strike_es']}  (OI {tops_id[2]['total_oi']:,.0f})")
    if full.get("pin_strike_0dte_es"):
        d = full.get('zero_dte_dte', 0)
        print(f"  Max Pain 0DTE    : ES {full['max_pain_0dte_es']}  ({d}DTE)")
        print(f"  Pin Strike 0DTE  : ES {full['pin_strike_0dte_es']}  (gamma max)")
        print(f"  Charm Mag. 0DTE  : ES {full['charm_magnet_0dte_es']}  (proche spot)")
    print(f"  -> {FULL_JSON} OK")
    return full


def run_agent():
    """Run Claude AI briefing for ES."""
    step("STEP 4 — Claude AI briefing ES")
    from claude_agent_ES import run_briefing_ES
    run_briefing_ES()


def run_pdf():
    """Generate ES briefing PDF."""
    step("STEP 5 — PDF generation")
    from generate_pdf_ES import build_pdf_ES
    briefing = json.loads(ES_BRIEFING_JSON.read_text(encoding="utf-8"))
    path = build_pdf_ES(briefing)
    print(f"  PDF -> {path}")


if __name__ == "__main__":
    from logging_setup import setup_logging
    setup_logging()

    def _pause_console():
        """Empêche la fenêtre cmd de se fermer instantanément (lancée depuis bouton ATAS)."""
        try:
            input("\n  Appuyer sur ENTREE pour fermer cette fenetre...")
        except (EOFError, KeyboardInterrupt, OSError):
            pass

    try:
        import argparse
        p = argparse.ArgumentParser(description="Pipeline ES matin (CME + CBOE + Claude + PDF)")
        p.add_argument("--fast", action="store_true",
                       help="Mode fast : skip Claude AI + PDF (juste CME + CBOE → JSON)")
        p.add_argument("--skip-cme", action="store_true",
                       help="Skip le scraping CME (utilise le dernier JSON CME existant)")
        p.add_argument("--max-dte", type=int, default=7,
                       help="DTE max intraday CBOE. 7=cumulative ∑ (default), 0=selected ⊙ 0DTE.")
        p.add_argument("--ignore-holiday", action="store_true",
                       help="Continue même si NYSE fermée aujourd'hui (sinon abort propre).")
        args = p.parse_args()

        from market_calendar import is_market_open_today, is_early_close_today
        if not is_market_open_today() and not args.ignore_holiday:
            print(f"\n  ABORT — NYSE fermée aujourd'hui (weekend ou jour férié).")
            print(f"  Override avec --ignore-holiday si tu veux quand même fetch.")
            _pause_console()
            sys.exit(0)

        early_close = is_early_close_today()
        mode_label = "FAST (no AI/PDF)" if args.fast else "FULL"
        if early_close:
            mode_label += " ⚠ EARLY-CLOSE 13:00 ET"
        print(f"\n{'='*55}")
        print(f"  GEX AGENT ES — Morning Run [{mode_label}]")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}  max_dte={args.max_dte}")
        print(f"{'='*55}")

        if not args.skip_cme:
            try:
                run_cme()
            except Exception as e:
                print(f"  WARNING: CME ES failed: {e}")
                print(f"  Continuing with existing JSON if available...")
        else:
            print(f"  STEP 1 — SKIP CME (--skip-cme)")

        from data_fetcher_ES import build_levels_ES
        step("STEP 2 — Fetch CBOE SPY options")
        build_levels_ES(max_dte=args.max_dte)

        merge_levels()
        if not args.fast:
            run_agent()
            run_pdf()
        else:
            print(f"\n  Mode FAST : skip Claude AI + PDF.")
    except SystemExit:
        _pause_console()
        raise
    except Exception as e:
        import traceback
        print(f"\n  ❌ ERREUR : {type(e).__name__}: {e}")
        traceback.print_exc()
        _pause_console()
        sys.exit(1)
    _pause_console()
