# 06 — Sample Outputs: concrete non-truncated examples

## Example 1: NQ typical day (positive gamma, complete data)

Scenario: Wednesday April 30, 2026, pre-market 08:15 ET. Full morning pipeline. NQ spot ~27617.

```json
{
  "generated_at": "2026-04-30T12:10:58.239691+00:00",
  "trade_date": "20260430",
  "json_schema_version": "1.0",
  "last_update_utc": "2026-04-30T12:10:58.239691+00:00",
  "data_quality": "ok",

  "spot_nq": 27617.25,
  "spot_qqq": 647.97,
  "qqq_nq_ratio": 42.6212,

  "gamma_flip": 27617.25,
  "vol_trigger": 27700.0,
  "call_wall": 28500.0,
  "put_wall": 25000.0,
  "risk_pivot": 25000.0,
  "vanna_flip": 28500.0,
  "charm_magnet": 28500.0,
  "call_wall_gex": 1023951922.0,
  "put_wall_gex": -1552134849.0,
  "total_gex": 27634523641.31,
  "total_vex": 12635565080.05,
  "total_cex": 76856.08,
  "total_dex": 5565539078.76,
  "gex_regime": 1,
  "vex_regime": 1,

  "atm_iv_structural": 0.2145,
  "skew_25d_structural": 0.042,
  "term_structural_regime": "contango",
  "term_structural_slope": 0.018,
  "iv_structural_back": 0.2325,
  "iv_structural_back_dte": 112,

  "max_pain_qqq": 620.0,
  "max_pain_nq": 26425,
  "expected_move_qqq": 6.57,
  "expected_move_nq": 280,
  "range_low_qqq": 641.4,
  "range_high_qqq": 654.54,
  "range_low_nq": 27337,
  "range_high_nq": 27897,
  "pcr": 1.545,

  "top_oi_strikes": [
    {"strike_qqq": 600.0, "strike_nq": 25573, "call_oi": 115656, "put_oi": 292117, "total_oi": 407773},
    {"strike_qqq": 570.0, "strike_nq": 24294, "call_oi": 31695, "put_oi": 293684, "total_oi": 325379},
    {"strike_qqq": 590.0, "strike_nq": 25146, "call_oi": 45470, "put_oi": 228661, "total_oi": 274131},
    {"strike_qqq": 580.0, "strike_nq": 24720, "call_oi": 46414, "put_oi": 218941, "total_oi": 265355},
    {"strike_qqq": 550.0, "strike_nq": 23442, "call_oi": 22750, "put_oi": 223832, "total_oi": 246582},
    {"strike_qqq": 630.0, "strike_nq": 26851, "call_oi": 126320, "put_oi": 103813, "total_oi": 230133},
    {"strike_qqq": 540.0, "strike_nq": 23015, "call_oi": 17360, "put_oi": 212567, "total_oi": 229927},
    {"strike_qqq": 500.0, "strike_nq": 21311, "call_oi": 16296, "put_oi": 212730, "total_oi": 229026},
    {"strike_qqq": 610.0, "strike_nq": 25999, "call_oi": 94109, "put_oi": 133212, "total_oi": 227321},
    {"strike_qqq": 640.0, "strike_nq": 27278, "call_oi": 129286, "put_oi": 93335, "total_oi": 222621}
  ],

  "call_wall_intraday_qqq": 660.0,
  "call_wall_intraday_nq": 28130,
  "call_wall_intraday_gex": 485201345.0,
  "put_wall_intraday_qqq": 617.0,
  "put_wall_intraday_nq": 26297,
  "put_wall_intraday_gex": -312578901.0,
  "walls_intraday_max_dte": 7,

  "c_trans_intraday_qqq": 656.0,
  "c_trans_intraday_nq": 27960,
  "p_trans_intraday_qqq": 635.0,
  "p_trans_intraday_nq": 27065,
  "trans_intraday_max_dte": 7,

  "dex_plus_intraday_qqq": 655.0,
  "dex_plus_intraday_nq": 27917,
  "dex_plus_intraday_dex": 1234567.89,
  "dex_minus_intraday_qqq": 628.0,
  "dex_minus_intraday_nq": 26766,
  "dex_minus_intraday_dex": -987654.32,
  "dex_intraday_max_dte": 7,

  "abs_gex_intraday_1_qqq": 650.0,
  "abs_gex_intraday_1_nq": 27704,
  "abs_gex_intraday_1_gex": 892345678.0,
  "abs_gex_intraday_2_qqq": 645.0,
  "abs_gex_intraday_2_nq": 27491,
  "abs_gex_intraday_2_gex": 678234567.0,
  "abs_gex_intraday_3_qqq": 660.0,
  "abs_gex_intraday_3_nq": 28130,
  "abs_gex_intraday_3_gex": 485201345.0,
  "abs_gex_intraday_max_dte": 7,

  "gex_wall_ext_1_qqq": 670.0,
  "gex_wall_ext_1_nq": 28556,
  "gex_wall_ext_1_gex": 345678901.0,
  "gex_wall_ext_1_side": "call",
  "gex_wall_ext_2_qqq": 610.0,
  "gex_wall_ext_2_nq": 25999,
  "gex_wall_ext_2_gex": -289012345.0,
  "gex_wall_ext_2_side": "put",
  "gex_wall_ext_3_qqq": 675.0,
  "gex_wall_ext_3_nq": 28769,
  "gex_wall_ext_3_gex": 234567890.0,
  "gex_wall_ext_3_side": "call",
  "gex_wall_ext_4_qqq": 605.0,
  "gex_wall_ext_4_nq": 25786,
  "gex_wall_ext_4_gex": -198765432.0,
  "gex_wall_ext_4_side": "put",
  "gex_walls_ext_max_dte": 7,

  "top_oi_intraday": [
    {"strike_qqq": 650.0, "strike_nq": 27704, "call_oi": 45230, "put_oi": 32100, "total_oi": 77330},
    {"strike_qqq": 645.0, "strike_nq": 27491, "call_oi": 28100, "put_oi": 41200, "total_oi": 69300},
    {"strike_qqq": 660.0, "strike_nq": 28130, "call_oi": 51200, "put_oi": 12300, "total_oi": 63500}
  ],

  "max_pain_0dte_qqq": 648.0,
  "max_pain_0dte_nq": 27619,
  "pin_strike_0dte_qqq": 650.0,
  "pin_strike_0dte_nq": 27704,
  "charm_magnet_0dte_qqq": 649.0,
  "charm_magnet_0dte_nq": 27661,
  "zero_dte_oi_total": 1234567,
  "zero_dte_dte": 0,

  "atm_iv_intraday": 0.1820,
  "atm_iv_intraday_dte": 1,
  "skew_25d_intraday": 0.033,
  "skew_25d_intraday_dte": 1,
  "term_intraday_regime": "contango",
  "term_intraday_slope": 0.012,
  "term_intraday_front_dte": 1,
  "term_intraday_back_dte": 5,
  "term_intraday_iv_front": 0.1820,
  "term_intraday_iv_back": 0.1940,

  "iv_rank_intraday": {
    "ivr": 34.5,
    "iv_min": 0.11,
    "iv_max": 0.32,
    "n_samples": 252,
    "status": "ok",
    "lookback": 252,
    "field": "atm_iv_intraday"
  },

  "vix": 17.82,
  "vix9d": 16.45,
  "vix_regime": "normal",
  "vix_term": "contango",
  "vix_term_slope": -1.37,
  "vix_dod_change": -0.45,

  "macro_in_blackout": false,
  "macro_blackout_until": null,
  "macro_current_event": null,
  "macro_next_event": {
    "title": "ISM Manufacturing PMI",
    "datetime_utc": "2026-04-30T14:00:00+00:00",
    "impact": "High",
    "forecast": "49.5",
    "previous": "49.0"
  },
  "macro_minutes_to_next": 109
}
```

---

## Example 2: ES typical day

Scenario: same day, ES. Spot ~5620.

```json
{
  "generated_at": "2026-04-30T12:12:15.102340+00:00",
  "trade_date": "20260430",
  "json_schema_version": "1.0",
  "last_update_utc": "2026-04-30T12:12:15.102340+00:00",
  "data_quality": "ok",

  "spot_es": 5620.50,
  "spot_spy": 562.05,
  "spy_es_ratio": 10.0,

  "gamma_flip": 5600.0,
  "vol_trigger": 5650.0,
  "call_wall": 5800.0,
  "put_wall": 5300.0,
  "risk_pivot": 5350.0,
  "vanna_flip": 5750.0,
  "charm_magnet": 5700.0,
  "call_wall_gex": 856000000.0,
  "put_wall_gex": -1120000000.0,
  "total_gex": 18500000000.0,
  "total_vex": 8200000000.0,
  "total_cex": 52000.0,
  "total_dex": 3400000000.0,
  "gex_regime": 1,
  "vex_regime": 1,

  "atm_iv_structural": 0.1890,
  "skew_25d_structural": 0.038,
  "term_structural_regime": "contango",
  "term_structural_slope": 0.015,
  "iv_structural_back": 0.2040,
  "iv_structural_back_dte": 112,

  "max_pain_spy": 545.0,
  "max_pain_es": 5450,
  "expected_move_spy": 5.80,
  "expected_move_es": 58,
  "range_low_spy": 556.25,
  "range_high_spy": 567.85,
  "range_low_es": 5562,
  "range_high_es": 5678,
  "pcr": 1.42,

  "top_oi_strikes": [
    {"strike_spy": 500.0, "strike_es": 5000, "call_oi": 245000, "put_oi": 580000, "total_oi": 825000},
    {"strike_spy": 550.0, "strike_es": 5500, "call_oi": 180000, "put_oi": 320000, "total_oi": 500000},
    {"strike_spy": 600.0, "strike_es": 6000, "call_oi": 410000, "put_oi": 85000, "total_oi": 495000}
  ],

  "call_wall_intraday_spy": 570.0,
  "call_wall_intraday_es": 5700,
  "call_wall_intraday_gex": 390000000.0,
  "put_wall_intraday_spy": 548.0,
  "put_wall_intraday_es": 5480,
  "put_wall_intraday_gex": -250000000.0,
  "walls_intraday_max_dte": 7,

  "c_trans_intraday_spy": 567.0,
  "c_trans_intraday_es": 5670,
  "p_trans_intraday_spy": 555.0,
  "p_trans_intraday_es": 5550,
  "trans_intraday_max_dte": 7,

  "dex_plus_intraday_spy": 566.0,
  "dex_plus_intraday_es": 5660,
  "dex_plus_intraday_dex": 980000.0,
  "dex_minus_intraday_spy": 553.0,
  "dex_minus_intraday_es": 5530,
  "dex_minus_intraday_dex": -760000.0,
  "dex_intraday_max_dte": 7,

  "abs_gex_intraday_1_spy": 560.0,
  "abs_gex_intraday_1_es": 5600,
  "abs_gex_intraday_1_gex": 720000000.0,
  "abs_gex_intraday_2_spy": 565.0,
  "abs_gex_intraday_2_es": 5650,
  "abs_gex_intraday_2_gex": 540000000.0,
  "abs_gex_intraday_3_spy": 555.0,
  "abs_gex_intraday_3_es": 5550,
  "abs_gex_intraday_3_gex": 410000000.0,
  "abs_gex_intraday_max_dte": 7,

  "gex_wall_ext_1_spy": 575.0, "gex_wall_ext_1_es": 5750,
  "gex_wall_ext_1_gex": 280000000.0, "gex_wall_ext_1_side": "call",
  "gex_wall_ext_2_spy": 545.0, "gex_wall_ext_2_es": 5450,
  "gex_wall_ext_2_gex": -210000000.0, "gex_wall_ext_2_side": "put",
  "gex_wall_ext_3_spy": 580.0, "gex_wall_ext_3_es": 5800,
  "gex_wall_ext_3_gex": 190000000.0, "gex_wall_ext_3_side": "call",
  "gex_wall_ext_4_spy": 540.0, "gex_wall_ext_4_es": 5400,
  "gex_wall_ext_4_gex": -155000000.0, "gex_wall_ext_4_side": "put",
  "gex_walls_ext_max_dte": 7,

  "top_oi_intraday": [
    {"strike_spy": 560.0, "strike_es": 5600, "call_oi": 38000, "put_oi": 29000, "total_oi": 67000},
    {"strike_spy": 565.0, "strike_es": 5650, "call_oi": 31000, "put_oi": 25000, "total_oi": 56000}
  ],

  "max_pain_0dte_spy": 561.0, "max_pain_0dte_es": 5610,
  "pin_strike_0dte_spy": 560.0, "pin_strike_0dte_es": 5600,
  "charm_magnet_0dte_spy": 562.0, "charm_magnet_0dte_es": 5620,
  "zero_dte_oi_total": 890000,
  "zero_dte_dte": 0,

  "atm_iv_intraday": 0.1650,
  "atm_iv_intraday_dte": 1,
  "skew_25d_intraday": 0.028,
  "skew_25d_intraday_dte": 1,
  "term_intraday_regime": "contango",
  "term_intraday_slope": 0.010,
  "term_intraday_front_dte": 1,
  "term_intraday_back_dte": 5,
  "term_intraday_iv_front": 0.1650,
  "term_intraday_iv_back": 0.1750,

  "iv_rank_intraday": {
    "ivr": 28.0,
    "iv_min": 0.09,
    "iv_max": 0.29,
    "n_samples": 252,
    "status": "ok",
    "lookback": 252,
    "field": "atm_iv_intraday"
  },

  "vix": 17.82,
  "vix9d": 16.45,
  "vix_regime": "normal",
  "vix_term": "contango",
  "vix_term_slope": -1.37,
  "vix_dod_change": -0.45,

  "macro_in_blackout": false,
  "macro_blackout_until": null,
  "macro_current_event": null,
  "macro_next_event": {
    "title": "ISM Manufacturing PMI",
    "datetime_utc": "2026-04-30T14:00:00+00:00",
    "impact": "High",
    "forecast": "49.5",
    "previous": "49.0"
  },
  "macro_minutes_to_next": 107
}
```

---

## Example 3: partial data (CBOE timeout)

Scenario: the morning pipeline ran but CBOE did not respond (maintenance or pre-market too early).

```json
{
  "generated_at": "2026-05-02T11:45:00.000000+00:00",
  "trade_date": "20260501",
  "json_schema_version": "1.0",
  "last_update_utc": "2026-05-02T11:45:00.000000+00:00",
  "data_quality": "partial",

  "spot_nq": 27850.0,
  "spot_qqq": 653.40,
  "qqq_nq_ratio": 42.6281,

  "gamma_flip": 27800.0,
  "vol_trigger": 27900.0,
  "call_wall": 28500.0,
  "put_wall": 25500.0,
  "risk_pivot": 25500.0,
  "vanna_flip": 28200.0,
  "charm_magnet": 28100.0,
  "call_wall_gex": 980000000.0,
  "put_wall_gex": -1400000000.0,
  "total_gex": 25000000000.0,
  "total_vex": 11000000000.0,
  "total_cex": 68000.0,
  "total_dex": 5100000000.0,
  "gex_regime": 1,
  "vex_regime": 1,

  "max_pain_qqq": 625.0,
  "max_pain_nq": 26638,
  "expected_move_qqq": 7.10,
  "expected_move_nq": 302,
  "range_low_nq": 27548,
  "range_high_nq": 28152,
  "pcr": 1.38,

  "call_wall_intraday_qqq": 0,
  "call_wall_intraday_nq": 0,
  "call_wall_intraday_gex": 0,
  "put_wall_intraday_qqq": 0,
  "put_wall_intraday_nq": 0,
  "put_wall_intraday_gex": 0,
  "walls_intraday_max_dte": 0,

  "c_trans_intraday_qqq": 0,
  "c_trans_intraday_nq": 0,
  "p_trans_intraday_qqq": 0,
  "p_trans_intraday_nq": 0,

  "dex_plus_intraday_qqq": 0,
  "dex_plus_intraday_nq": 0,
  "dex_minus_intraday_qqq": 0,
  "dex_minus_intraday_nq": 0,

  "abs_gex_intraday_1_qqq": 0,
  "abs_gex_intraday_1_nq": 0,
  "abs_gex_intraday_1_gex": 0,

  "max_pain_0dte_nq": 0,
  "pin_strike_0dte_nq": 0,
  "charm_magnet_0dte_nq": 0,
  "zero_dte_oi_total": 0,

  "atm_iv_intraday": 0,
  "skew_25d_intraday": 0,
  "term_intraday_regime": "unknown",
  "term_intraday_slope": 0,

  "iv_rank_intraday": null,

  "vix": 18.50,
  "vix9d": 17.20,
  "vix_regime": "normal",
  "vix_term": "contango",
  "vix_term_slope": -1.30,
  "vix_dod_change": 0.68,

  "macro_in_blackout": false,
  "macro_next_event": null,
  "macro_minutes_to_next": null
}
```

**Key points**:
- `data_quality: "partial"` → at least one source missing.
- All `*_intraday_*` fields are `0` → CBOE did not respond.
- The structural CME data is intact (gamma_flip, walls, etc.).
- `iv_rank_intraday: null` → cannot compute IVR without intraday IV.
- A consumer must check `call_wall_intraday_nq > 0` before using intraday levels.

---

## Example 4: regime change (positive gamma → negative)

Scenario: NQ drops 400 points overnight. Gamma Flip was at 27800 yesterday, spot falls to 27200 today. The new CME calculation shows a negative total GEX.

**Yesterday's JSON** (key fields summary):
```json
{
  "trade_date": "20260430",
  "spot_nq": 27800.0,
  "gamma_flip": 27800.0,
  "gex_regime": 1,
  "total_gex": 25000000000.0,
  "call_wall_intraday_nq": 28130,
  "put_wall_intraday_nq": 26297,
  "vix": 17.82,
  "vix_regime": "normal"
}
```

**Today's JSON**:
```json
{
  "trade_date": "20260501",
  "spot_nq": 27200.0,
  "gamma_flip": 27500.0,
  "gex_regime": -1,
  "total_gex": -8500000000.0,
  "call_wall_intraday_nq": 27650,
  "put_wall_intraday_nq": 26500,
  "c_trans_intraday_nq": 27550,
  "p_trans_intraday_nq": 26800,
  "vix": 24.30,
  "vix_regime": "elevated",
  "vix_dod_change": 6.48,
  "skew_25d_intraday": 0.065,
  "term_intraday_regime": "backwardation",
  "term_intraday_slope": -0.025
}
```

**What changed**:
- `gex_regime`: `1` → `-1` (dealers amplify instead of stabilizing)
- `total_gex`: +25B → -8.5B (flipped to net negative gamma)
- `gamma_flip` rose to 27500 — spot (27200) is **below** → negative gamma confirmed
- `vix_regime`: `"normal"` → `"elevated"` (VIX jumped +6.48 pts)
- `skew_25d_intraday`: 0.033 → 0.065 (sharply higher put demand)
- `term_intraday_regime`: `"contango"` → `"backwardation"` (near-term stress)
- Intraday walls tightened (CW 28130→27650, PW 26297→26500)
- The PW-CW range narrowed: 1833 pts → 1150 pts (compression, high uncertainty)

**Consumer-side detection**:
```csharp
int regime = root.GetProperty("gex_regime").GetInt32();
if (regime == -1)
{
    // ALERT: switched to negative gamma
    // - Wall spread compressed → directional volatility
    // - VIX elevated → reduce position size
    // - Skew > 5vp → strong protection demand
    // - Term in backwardation → near-term panic
}
```

---

## Example 5: insufficient IVR status (first launch)

Scenario: pipeline just installed. Only 3 days of history available.

```json
{
  "iv_rank_intraday": {
    "ivr": 0,
    "iv_min": 0.17,
    "iv_max": 0.19,
    "n_samples": 3,
    "status": "insufficient",
    "lookback": 252,
    "field": "atm_iv_intraday"
  }
}
```

- `status: "insufficient"` → less than 5 days of history.
- `ivr: 0` → unreliable value, do not use for trading.
- After 20 days: `status` flips to `"ok"`, `ivr` becomes meaningful.
- The consumer must **gate on `status`** before displaying or using IVR.
