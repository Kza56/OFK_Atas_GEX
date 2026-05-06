"""
run_intraday_refresh.py — Fast mode pour scalping intraday.

Re-fetch UNIQUEMENT CBOE (rapide, gratuit, ~1s) + merge avec le dernier
JSON CME du matin. Skip CME (lent + scrape navigateur), skip Claude
(coûteux), skip PDF (inutile en cours de session).

Mise à jour des métriques intraday dynamiques :
- atm_iv_intraday (IVx 0-7 DTE)
- skew_25d_intraday
- term_intraday_*
- call_wall_intraday, put_wall_intraday
- top_oi_intraday[]
- max_pain_0dte, pin_strike_0dte, charm_magnet_0dte
- IVR (recalculé)

Les niveaux GEX structurels (gamma_flip, vol_trigger, walls structurels,
charm_magnet, etc.) restent ceux du run du matin (peu changent intraday).

Usage:
  py run_intraday_refresh.py NQ          # un refresh
  py run_intraday_refresh.py ES
  py run_intraday_refresh.py NQ --loop   # boucle 5 min pendant RTH (défaut)
  py run_intraday_refresh.py ES --loop --interval 600  # toutes les 10 min
  py run_intraday_refresh.py NQ --loop --cme-refresh-every 6  # re-scrape CME tous les 6 cycles (≈30 min si interval=5min)

Conseil: lancer dans 2 terminaux pendant RTH (un par instrument).
"""
import argparse
import json
import sys
import time
from datetime import datetime, time as dtime, timezone, timedelta

from config import (
    NQ_GEX_JSON, ES_GEX_JSON,
    NQ_FULL_JSON, ES_FULL_JSON,
    save_snapshot,
    save_intraday_snapshot,
    compute_iv_rank,
    update_session_log,
)
from market_calendar import is_rth_now_et, is_market_open_today
from vix_fetcher import fetch_vix
from econ_calendar import blackout_status


def refresh_NQ(max_dte: int = 7) -> dict:
    """Re-fetch CBOE QQQ + merge avec dernier CME NQ JSON. Renvoie le full dict."""
    from data_fetcher_NQ import build_levels
    cboe = build_levels(max_dte=max_dte)  # écrit data/levels_NQ.json + renvoie le dict
    vix  = fetch_vix()  # VIX + VIX9D + régime
    blackout = blackout_status()  # macro events ±30 min

    cme = json.loads(NQ_GEX_JSON.read_text()) if NQ_GEX_JSON.exists() else {}
    if not cme:
        print("  ⚠ CME NQ JSON manquant — lance run_morning_NQ.py d'abord")
        return {}

    nq_spot  = cme.get("spot", 0)
    qqq_spot = cboe.get("spot", 0)
    ratio    = nq_spot / qqq_spot if qqq_spot > 0 else 41.30

    def qqq_to_nq(v): return round(v * ratio) if v else None

    full = {
        "generated_at"       : datetime.now(timezone.utc).isoformat(),
        "trade_date"         : cme.get("trade_date"),
        "refresh_mode"       : "intraday",
        "spot_nq"            : nq_spot,
        "spot_qqq"           : qqq_spot,
        "qqq_nq_ratio"       : round(ratio, 4),

        # Niveaux structurels (du run matin, inchangés intraday)
        "gamma_flip"         : cme.get("gamma_flip"),
        "vol_trigger"        : cme.get("vol_trigger"),
        "call_wall"          : cme.get("call_wall"),
        "put_wall"           : cme.get("put_wall"),
        "risk_pivot"         : cme.get("risk_pivot"),
        "vanna_flip"         : cme.get("vanna_flip"),
        "charm_magnet"       : cme.get("charm_magnet"),
        "total_gex"          : cme.get("total_gex"),
        "total_vex"          : cme.get("total_vex"),
        "total_cex"          : cme.get("total_cex"),
        "total_dex"          : cme.get("total_dex"),
        "gex_regime"         : cme.get("gex_regime"),
        "vex_regime"         : cme.get("vex_regime"),

        # Structurel (CME 49d, contexte secondaire)
        "atm_iv_structural"      : cme.get("atm_iv_front"),
        "iv_structural_by_dte"   : cme.get("iv_by_dte"),
        "skew_25d_structural"    : cme.get("skew_25d_front"),
        "skew_structural_by_dte" : cme.get("skew_by_dte"),
        "term_structural_regime" : cme.get("term_regime"),
        "term_structural_slope"  : cme.get("term_slope"),
        "iv_structural_back_dte" : cme.get("iv_back_dte"),
        "iv_structural_back"     : cme.get("iv_back"),

        # CBOE intraday (REFRESH ce qui change)
        "atm_iv_intraday"        : cboe.get("atm_iv_intraday"),
        "atm_iv_intraday_dte"    : cboe.get("atm_iv_intraday_dte"),
        "atm_iv_intraday_by_dte" : cboe.get("atm_iv_intraday_by_dte"),
        "skew_25d_intraday"      : cboe.get("skew_25d_cboe"),
        "skew_25d_intraday_dte"  : cboe.get("skew_cboe_dte"),
        "term_intraday_regime"   : cboe.get("term_intraday_regime"),
        "term_intraday_slope"    : cboe.get("term_intraday_slope"),
        "term_intraday_iv_front" : cboe.get("term_intraday_iv_front"),
        "term_intraday_iv_back"  : cboe.get("term_intraday_iv_back"),
        "term_intraday_front_dte": cboe.get("term_intraday_front_dte"),
        "term_intraday_back_dte" : cboe.get("term_intraday_back_dte"),

        "call_wall_gex"      : cboe.get("call_wall_gex"),
        "put_wall_gex"       : cboe.get("put_wall_gex"),
        "call_wall_intraday_qqq" : cboe.get("call_wall_intraday"),
        "call_wall_intraday_nq"  : qqq_to_nq(cboe.get("call_wall_intraday")),
        "call_wall_intraday_gex" : cboe.get("call_wall_intraday_gex"),
        "put_wall_intraday_qqq"  : cboe.get("put_wall_intraday"),
        "put_wall_intraday_nq"   : qqq_to_nq(cboe.get("put_wall_intraday")),
        "put_wall_intraday_gex"  : cboe.get("put_wall_intraday_gex"),
        "walls_intraday_max_dte" : cboe.get("walls_intraday_max_dte"),

        # cTrans/pTrans (Phase 3)
        "c_trans_intraday_qqq"   : cboe.get("c_trans_intraday"),
        "c_trans_intraday_nq"    : qqq_to_nq(cboe.get("c_trans_intraday")),
        "p_trans_intraday_qqq"   : cboe.get("p_trans_intraday"),
        "p_trans_intraday_nq"    : qqq_to_nq(cboe.get("p_trans_intraday")),
        "trans_intraday_max_dte" : cboe.get("trans_intraday_max_dte"),

        # DEX D+/D- (Phase 4)
        "dex_plus_intraday_qqq"  : cboe.get("dex_plus_intraday"),
        "dex_plus_intraday_nq"   : qqq_to_nq(cboe.get("dex_plus_intraday")),
        "dex_plus_intraday_dex"  : cboe.get("dex_plus_intraday_dex"),
        "dex_minus_intraday_qqq" : cboe.get("dex_minus_intraday"),
        "dex_minus_intraday_nq"  : qqq_to_nq(cboe.get("dex_minus_intraday")),
        "dex_minus_intraday_dex" : cboe.get("dex_minus_intraday_dex"),
        "dex_intraday_max_dte"   : cboe.get("dex_intraday_max_dte"),

        # Abs GEX Ab1/Ab2/Ab3 (Phase 5 — pin risk)
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

        # Extended walls GEX7-GEX10 (Phase 6)
        **{f"gex_wall_ext_{i}_qqq":  cboe.get(f"gex_wall_ext_{i}") for i in range(1, 5)},
        **{f"gex_wall_ext_{i}_nq":   qqq_to_nq(cboe.get(f"gex_wall_ext_{i}")) for i in range(1, 5)},
        **{f"gex_wall_ext_{i}_gex":  cboe.get(f"gex_wall_ext_{i}_gex") for i in range(1, 5)},
        **{f"gex_wall_ext_{i}_side": cboe.get(f"gex_wall_ext_{i}_side") for i in range(1, 5)},
        "gex_walls_ext_max_dte": cboe.get("gex_walls_ext_max_dte"),

        # Volume Flow V1/V2/V3 (Phase 7)
        **{f"vol_flow_{i}_qqq": cboe.get(f"vol_flow_{i}") for i in range(1, 4)},
        **{f"vol_flow_{i}_nq":  qqq_to_nq(cboe.get(f"vol_flow_{i}")) for i in range(1, 4)},
        **{f"vol_flow_{i}_total": cboe.get(f"vol_flow_{i}_total") for i in range(1, 4)},
        "vol_flow_intraday_max_dte": cboe.get("vol_flow_intraday_max_dte"),

        "intraday_mode"          : cboe.get("intraday_mode"),
        "intraday_max_dte_param" : cboe.get("intraday_max_dte_param"),

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

        # Macro blackout (Forex Factory ±30min événements High USD)
        "macro_in_blackout"     : blackout.get("in_blackout", False),
        "macro_blackout_until"  : blackout.get("blackout_until_utc"),
        "macro_current_event"   : blackout.get("current_event"),
        "macro_next_event"      : blackout.get("next_event"),
        "macro_minutes_to_next" : blackout.get("minutes_to_next"),

        "top_oi_strikes"     : [
            {"strike_qqq": s["strike"], "strike_nq": qqq_to_nq(s["strike"]),
             "call_oi": s["call_oi"], "put_oi": s["put_oi"], "total_oi": s["total_oi"]}
            for s in cboe.get("top_oi_strikes", [])
        ],
        "top_oi_intraday"    : [
            {"strike_qqq": s["strike"], "strike_nq": qqq_to_nq(s["strike"]),
             "call_oi": s["call_oi"], "put_oi": s["put_oi"], "total_oi": s["total_oi"]}
            for s in cboe.get("top_oi_intraday", [])
        ],

        # 0DTE
        "max_pain_0dte_qqq"     : cboe.get("max_pain_0dte_qqq"),
        "max_pain_0dte_nq"      : qqq_to_nq(cboe.get("max_pain_0dte_qqq")),
        "pin_strike_0dte_qqq"   : cboe.get("pin_strike_0dte_qqq"),
        "pin_strike_0dte_nq"    : qqq_to_nq(cboe.get("pin_strike_0dte_qqq")),
        "charm_magnet_0dte_qqq" : cboe.get("charm_magnet_0dte_qqq"),
        "charm_magnet_0dte_nq"  : qqq_to_nq(cboe.get("charm_magnet_0dte_qqq")),
        "zero_dte_oi_total"     : cboe.get("zero_dte_oi_total"),
        "zero_dte_dte"          : cboe.get("zero_dte_dte"),
    }

    # IVR (recalculé sur historique)
    iv_id = full.get("atm_iv_intraday")
    if iv_id and iv_id > 0:
        full["iv_rank_intraday"] = compute_iv_rank("NQ", iv_id, iv_field="atm_iv_intraday")

    # Bloc 7 : versioning + health check
    from config import JSON_SCHEMA_VERSION, compute_data_quality
    full["json_schema_version"] = JSON_SCHEMA_VERSION
    full["last_update_utc"]     = datetime.now(timezone.utc).isoformat()
    full["data_quality"]        = compute_data_quality(full)

    NQ_FULL_JSON.write_text(json.dumps(full, indent=2))

    # Snapshot intraday horodaté pour replay (rétention 7j)
    try:
        save_intraday_snapshot("NQ", full)
    except Exception as e:
        print(f"  ⚠ save_intraday_snapshot NQ: {type(e).__name__}: {e}")

    # Met à jour le snapshot du jour avec open/close RTH (pour backtest)
    if is_rth_now_et():
        update_session_log("NQ", full.get("trade_date", ""), nq_spot)

    return full


def refresh_ES(max_dte: int = 7) -> dict:
    """Idem NQ pour ES (CBOE SPY)."""
    from data_fetcher_ES import build_levels_ES
    cboe = build_levels_ES(max_dte=max_dte)
    vix  = fetch_vix()
    blackout = blackout_status()

    cme = json.loads(ES_GEX_JSON.read_text()) if ES_GEX_JSON.exists() else {}
    if not cme:
        print("  ⚠ CME ES JSON manquant — lance run_morning_ES.py d'abord")
        return {}

    es_spot  = cme.get("spot", 0)
    spy_spot = cboe.get("spot", 0)
    ratio    = es_spot / spy_spot if spy_spot > 0 else 10.0

    def spy_to_es(v): return round(v * ratio) if v else None

    full = {
        "generated_at"       : datetime.now(timezone.utc).isoformat(),
        "trade_date"         : cme.get("trade_date"),
        "refresh_mode"       : "intraday",
        "spot_es"            : es_spot,
        "spot_spy"           : spy_spot,
        "spy_es_ratio"       : round(ratio, 4),

        "gamma_flip"         : cme.get("gamma_flip"),
        "vol_trigger"        : cme.get("vol_trigger"),
        "call_wall"          : cme.get("call_wall"),
        "put_wall"           : cme.get("put_wall"),
        "risk_pivot"         : cme.get("risk_pivot"),
        "vanna_flip"         : cme.get("vanna_flip"),
        "charm_magnet"       : cme.get("charm_magnet"),
        "total_gex"          : cme.get("total_gex"),
        "total_vex"          : cme.get("total_vex"),
        "total_cex"          : cme.get("total_cex"),
        "total_dex"          : cme.get("total_dex"),
        "gex_regime"         : cme.get("gex_regime"),
        "vex_regime"         : cme.get("vex_regime"),

        "atm_iv_structural"      : cme.get("atm_iv_front"),
        "iv_structural_by_dte"   : cme.get("iv_by_dte"),
        "skew_25d_structural"    : cme.get("skew_25d_front"),
        "skew_structural_by_dte" : cme.get("skew_by_dte"),
        "term_structural_regime" : cme.get("term_regime"),
        "term_structural_slope"  : cme.get("term_slope"),
        "iv_structural_back_dte" : cme.get("iv_back_dte"),
        "iv_structural_back"     : cme.get("iv_back"),

        "atm_iv_intraday"        : cboe.get("atm_iv_intraday"),
        "atm_iv_intraday_dte"    : cboe.get("atm_iv_intraday_dte"),
        "atm_iv_intraday_by_dte" : cboe.get("atm_iv_intraday_by_dte"),
        "skew_25d_intraday"      : cboe.get("skew_25d_cboe"),
        "skew_25d_intraday_dte"  : cboe.get("skew_cboe_dte"),
        "term_intraday_regime"   : cboe.get("term_intraday_regime"),
        "term_intraday_slope"    : cboe.get("term_intraday_slope"),
        "term_intraday_iv_front" : cboe.get("term_intraday_iv_front"),
        "term_intraday_iv_back"  : cboe.get("term_intraday_iv_back"),
        "term_intraday_front_dte": cboe.get("term_intraday_front_dte"),
        "term_intraday_back_dte" : cboe.get("term_intraday_back_dte"),

        "call_wall_gex"      : cboe.get("call_wall_gex"),
        "put_wall_gex"       : cboe.get("put_wall_gex"),
        "call_wall_intraday_spy" : cboe.get("call_wall_intraday"),
        "call_wall_intraday_es"  : spy_to_es(cboe.get("call_wall_intraday")),
        "call_wall_intraday_gex" : cboe.get("call_wall_intraday_gex"),
        "put_wall_intraday_spy"  : cboe.get("put_wall_intraday"),
        "put_wall_intraday_es"   : spy_to_es(cboe.get("put_wall_intraday")),
        "put_wall_intraday_gex"  : cboe.get("put_wall_intraday_gex"),
        "walls_intraday_max_dte" : cboe.get("walls_intraday_max_dte"),

        # cTrans/pTrans (Phase 3)
        "c_trans_intraday_spy"   : cboe.get("c_trans_intraday"),
        "c_trans_intraday_es"    : spy_to_es(cboe.get("c_trans_intraday")),
        "p_trans_intraday_spy"   : cboe.get("p_trans_intraday"),
        "p_trans_intraday_es"    : spy_to_es(cboe.get("p_trans_intraday")),
        "trans_intraday_max_dte" : cboe.get("trans_intraday_max_dte"),

        # DEX D+/D- (Phase 4)
        "dex_plus_intraday_spy"  : cboe.get("dex_plus_intraday"),
        "dex_plus_intraday_es"   : spy_to_es(cboe.get("dex_plus_intraday")),
        "dex_plus_intraday_dex"  : cboe.get("dex_plus_intraday_dex"),
        "dex_minus_intraday_spy" : cboe.get("dex_minus_intraday"),
        "dex_minus_intraday_es"  : spy_to_es(cboe.get("dex_minus_intraday")),
        "dex_minus_intraday_dex" : cboe.get("dex_minus_intraday_dex"),
        "dex_intraday_max_dte"   : cboe.get("dex_intraday_max_dte"),

        # Abs GEX Ab1/Ab2/Ab3 (Phase 5 — pin risk)
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

        # Extended walls GEX7-GEX10 (Phase 6)
        **{f"gex_wall_ext_{i}_spy":  cboe.get(f"gex_wall_ext_{i}") for i in range(1, 5)},
        **{f"gex_wall_ext_{i}_es":   spy_to_es(cboe.get(f"gex_wall_ext_{i}")) for i in range(1, 5)},
        **{f"gex_wall_ext_{i}_gex":  cboe.get(f"gex_wall_ext_{i}_gex") for i in range(1, 5)},
        **{f"gex_wall_ext_{i}_side": cboe.get(f"gex_wall_ext_{i}_side") for i in range(1, 5)},
        "gex_walls_ext_max_dte": cboe.get("gex_walls_ext_max_dte"),

        # Volume Flow V1/V2/V3 (Phase 7)
        **{f"vol_flow_{i}_spy": cboe.get(f"vol_flow_{i}") for i in range(1, 4)},
        **{f"vol_flow_{i}_es":  spy_to_es(cboe.get(f"vol_flow_{i}")) for i in range(1, 4)},
        **{f"vol_flow_{i}_total": cboe.get(f"vol_flow_{i}_total") for i in range(1, 4)},
        "vol_flow_intraday_max_dte": cboe.get("vol_flow_intraday_max_dte"),

        "intraday_mode"          : cboe.get("intraday_mode"),
        "intraday_max_dte_param" : cboe.get("intraday_max_dte_param"),

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

        "top_oi_strikes"     : [
            {"strike_spy": s["strike"], "strike_es": spy_to_es(s["strike"]),
             "call_oi": s["call_oi"], "put_oi": s["put_oi"], "total_oi": s["total_oi"]}
            for s in cboe.get("top_oi_strikes", [])
        ],
        "top_oi_intraday"    : [
            {"strike_spy": s["strike"], "strike_es": spy_to_es(s["strike"]),
             "call_oi": s["call_oi"], "put_oi": s["put_oi"], "total_oi": s["total_oi"]}
            for s in cboe.get("top_oi_intraday", [])
        ],

        "max_pain_0dte_spy"     : cboe.get("max_pain_0dte_spy"),
        "max_pain_0dte_es"      : spy_to_es(cboe.get("max_pain_0dte_spy")),
        "pin_strike_0dte_spy"   : cboe.get("pin_strike_0dte_spy"),
        "pin_strike_0dte_es"    : spy_to_es(cboe.get("pin_strike_0dte_spy")),
        "charm_magnet_0dte_spy" : cboe.get("charm_magnet_0dte_spy"),
        "charm_magnet_0dte_es"  : spy_to_es(cboe.get("charm_magnet_0dte_spy")),
        "zero_dte_oi_total"     : cboe.get("zero_dte_oi_total"),
        "zero_dte_dte"          : cboe.get("zero_dte_dte"),
    }

    iv_id = full.get("atm_iv_intraday")
    if iv_id and iv_id > 0:
        full["iv_rank_intraday"] = compute_iv_rank("ES", iv_id, iv_field="atm_iv_intraday")

    # Bloc 7 : versioning + health check
    from config import JSON_SCHEMA_VERSION, compute_data_quality
    full["json_schema_version"] = JSON_SCHEMA_VERSION
    full["last_update_utc"]     = datetime.now(timezone.utc).isoformat()
    full["data_quality"]        = compute_data_quality(full)

    ES_FULL_JSON.write_text(json.dumps(full, indent=2))

    # Snapshot intraday horodaté pour replay (rétention 7j)
    try:
        save_intraday_snapshot("ES", full)
    except Exception as e:
        print(f"  ⚠ save_intraday_snapshot ES: {type(e).__name__}: {e}")

    # Met à jour le snapshot du jour avec open/close RTH (pour backtest)
    if is_rth_now_et():
        update_session_log("ES", full.get("trade_date", ""), es_spot)

    return full


def print_summary(full: dict, symbol: str):
    """Résumé concis pour console (loop friendly)."""
    ts = datetime.now().strftime("%H:%M:%S")
    spot = full.get("spot_nq") or full.get("spot_es", 0)
    iv = full.get("atm_iv_intraday", 0) * 100
    skew = (full.get("skew_25d_intraday") or 0) * 100
    term = full.get("term_intraday_regime", "?")
    tslope = (full.get("term_intraday_slope") or 0) * 100
    cw_id = full.get("call_wall_intraday_nq") or full.get("call_wall_intraday_es", 0)
    pw_id = full.get("put_wall_intraday_nq") or full.get("put_wall_intraday_es", 0)
    ct_id = full.get("c_trans_intraday_nq") or full.get("c_trans_intraday_es")
    pt_id = full.get("p_trans_intraday_nq") or full.get("p_trans_intraday_es")
    pin = full.get("pin_strike_0dte_nq") or full.get("pin_strike_0dte_es", 0)
    ivr = (full.get("iv_rank_intraday") or {}).get("ivr")
    ivr_str = f" IVR {ivr:.0f}%" if ivr is not None else ""
    trans_str = f" | cT={ct_id or '-'} pT={pt_id or '-'}" if (ct_id or pt_id) else ""
    print(f"[{ts}] {symbol} spot={spot:.0f} | IVx={iv:.1f}%{ivr_str} | "
          f"skew={skew:+.1f}vp | term={term}({tslope:+.1f}vp) | "
          f"CW={cw_id} PW={pw_id}{trans_str} | Pin0D={pin}")


def refresh_one(symbol: str, max_dte: int = 7):
    fn = refresh_NQ if symbol == "NQ" else refresh_ES
    try:
        full = fn(max_dte=max_dte)
        if full:
            print_summary(full, symbol)
    except Exception as e:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {symbol} ERREUR: {type(e).__name__}: {e}")


def refresh_cme(symbol: str):
    """Re-scrape CME (lent ~60s via Playwright). Met à jour data/levels_{symbol}.json (CME-only)."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {symbol} CME re-scrape (Playwright)...")
    try:
        if symbol == "NQ":
            from cme_NQ_browser_fetch import fetch_gex_levels as cme_fetch
        else:
            from cme_ES_browser_fetch import fetch_gex_levels as cme_fetch
        cme_fetch(0.0, headless=False)
        ts2 = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts2}] {symbol} CME re-scrape OK")
    except Exception as e:
        ts2 = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts2}] {symbol} CME ERREUR: {type(e).__name__}: {e}")


def main():
    from logging_setup import setup_logging
    setup_logging()
    p = argparse.ArgumentParser(description="Fast refresh CBOE intraday")
    p.add_argument("symbol", choices=["NQ", "ES"], help="instrument")
    p.add_argument("--loop", action="store_true", help="boucle pendant RTH")
    p.add_argument("--interval", type=int, default=300,
                   help="secondes entre refresh en mode loop (défaut 300 = 5 min)")
    p.add_argument("--rth-only", action="store_true",
                   help="en loop, ne refresh que pendant RTH (default: tout le temps)")
    p.add_argument("--max-dte", type=int, default=7,
                   help="DTE max intraday. 7=cumulative ∑ (default), 0=selected ⊙ 0DTE only.")
    p.add_argument("--cme-refresh-every", type=int, default=0,
                   help="re-scrape CME (Playwright lent ~60s) tous les N cycles. "
                        "0 = jamais (défaut). Ex: 6 avec interval=300 → CME toutes les 30 min.")
    args = p.parse_args()

    if not args.loop:
        refresh_one(args.symbol, max_dte=args.max_dte)
        return

    cme_every = max(0, args.cme_refresh_every)
    cme_str   = f", CME re-scrape tous les {cme_every} cycles" if cme_every > 0 else ""
    print(f"=== Boucle intraday {args.symbol} (interval {args.interval}s, max_dte={args.max_dte}{cme_str}) ===")
    print("CTRL+C pour arrêter.\n")
    cycle = 0
    try:
        while True:
            if args.rth_only and not is_rth_now_et():
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] hors RTH, sleep {args.interval}s...")
            else:
                if cme_every > 0 and cycle > 0 and cycle % cme_every == 0:
                    refresh_cme(args.symbol)
                refresh_one(args.symbol, max_dte=args.max_dte)
                cycle += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nArrêté par l'utilisateur.")


if __name__ == "__main__":
    main()
