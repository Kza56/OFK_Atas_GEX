# 01 — Output Contract: files produced by GEX Levels

## Primary files (stable contract)

### `full_levels_NQ.json` / `full_levels_ES.json`

- **Windows path**: `C:\OFK_Atas_GEX\OFK_GEX_Pipeline\data\full_levels_NQ.json`
- **macOS / Linux**: ATAS is Windows-only, but the Python pipeline itself is portable. Set `GEX_DATA_DIR` to your local data directory.
- **Override**: env variable `GEX_DATA_DIR` overrides the `data/` directory
- **When**: written by the morning pipeline (~08:30 ET), then overwritten every 5 min by the intraday loop (09:30-16:00 ET)
- **Format**: JSON UTF-8, single root object `{}`
- **Typical size**: 15-25 KB
- **Coexisting versions**: no — a single file per instrument, overwritten each cycle
- **Schema version**: root field `json_schema_version` (currently `"1.0"`)

This is **the file every downstream consumer must read**. It contains all merged data CME + CBOE + VIX + macro.

---

## Secondary files

| File | Path relative to `data/` | When | Use |
|------|-------------------------|------|-----|
| `NQ_gex_latest.json` | `data/` | Morning only | CME-only intermediate (not for external consumption) |
| `levels_NQ.json` | `data/` | Each intraday cycle | CBOE-only intermediate (not for external consumption) |
| `briefing_NQ.json` | `data/` | Morning only | Narrative AI briefing |
| `briefing_NQ_YYYY-MM-DD.pdf` | `data/` | Morning only | Briefing PDF (one per day, older ones deleted) |
| `history/NQ_full_levels_YYYYMMDD.json` | `data/history/` | Morning (1×/day) | Daily snapshot for 252-day IVR. Retention: 380 days |
| `history/intraday/NQ_full_levels_YYYYMMDD_HHMM.json` | `data/history/intraday/` | Each intraday cycle | Snapshots for replay. Retention: 7 days |
| `backups/snapshots_YYYYmmdd_HHMMSS.tar.gz` | `data/backups/` | Morning | Compressed archive of the history/ folder. Retention: 30 days |

All ES files follow the same pattern with `ES` instead of `NQ` and `SPY` instead of `QQQ`.

---

## Full JSON schema — `full_levels_{NQ|ES}.json`

### Metadata

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `generated_at` | string (ISO 8601 UTC) | yes | Generation timestamp |
| `trade_date` | string (`YYYYMMDD`) | yes | CME trading date (may be D-1 if generated pre-market) |
| `json_schema_version` | string | yes | Schema version (`"1.0"`) |
| `last_update_utc` | string (ISO 8601 UTC) | yes | Last update (= `generated_at` in morning, refreshed in intraday) |
| `data_quality` | string enum | yes | `"ok"` \| `"partial"` \| `"error"` |
| `refresh_mode` | string | no | `"intraday"` if written by the loop, absent in morning |
| `spot_nq` | float | yes | NQ spot at generation time |
| `spot_qqq` | float | yes | QQQ spot |
| `qqq_nq_ratio` | float | yes | Conversion ratio `spot_nq / spot_qqq` |

### CME — Structural levels (49d+ expirations)

| Field | Type | Unit | Required | Typical range |
|-------|------|------|:--------:|---------------|
| `gamma_flip` | float | NQ price | yes | 25000-30000 |
| `vol_trigger` | float | NQ price | yes | 25000-30000 |
| `call_wall` | float | NQ price | yes | 25000-32000 |
| `put_wall` | float | NQ price | yes | 20000-28000 |
| `risk_pivot` | float | NQ price | yes | 20000-28000 |
| `vanna_flip` | float | NQ price | yes | 25000-30000 |
| `charm_magnet` | float | NQ price | yes | 25000-30000 |
| `call_wall_gex` | float | raw GEX ($) | yes | 10⁸ – 10¹⁰ |
| `put_wall_gex` | float | raw GEX ($) | yes | -10¹⁰ – -10⁸ (negative) |
| `total_gex` | float | raw GEX ($) | yes | -10¹⁰ – 10¹¹ |
| `total_vex` | float | raw VEX ($) | yes | -10¹⁰ – 10¹¹ |
| `total_cex` | float | raw CEX ($) | yes | -10⁶ – 10⁶ |
| `total_dex` | float | raw DEX ($) | yes | -10¹⁰ – 10¹⁰ |
| `gex_regime` | int | enum | yes | `1` (positive) or `-1` (negative) |
| `vex_regime` | int | enum | yes | `1` or `-1` |

### CME — Structural IV (49d+)

| Field | Type | Unit | Required | Typical range |
|-------|------|------|:--------:|---------------|
| `atm_iv_structural` | float | ratio (0.xx) | no | 0.10 – 0.60 |
| `skew_25d_structural` | float | ratio | no | 0.00 – 0.15 |
| `term_structural_regime` | string enum | — | no | `"backwardation"` \| `"contango"` \| `"flat"` \| `"unknown"` |
| `term_structural_slope` | float | ratio | no | -0.10 – 0.10 |
| `iv_structural_back` | float | ratio | no | 0.10 – 0.60 |
| `iv_structural_back_dte` | int | days | no | 49 – 365 |

### CME — Max Pain & Expected Move

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `max_pain_qqq` | float | QQQ price | yes |
| `max_pain_nq` | float | NQ price (converted) | yes |
| `expected_move_qqq` | float | QQQ pts | yes |
| `expected_move_nq` | float | NQ pts | yes |
| `range_low_qqq` / `range_low_nq` | float | price | yes |
| `range_high_qqq` / `range_high_nq` | float | price | yes |
| `pcr` | float | put/call ratio | yes |

### CME — Top OI Strikes

| Field | Type | Required |
|-------|------|:--------:|
| `top_oi_strikes` | array of objects | yes |

Each object:
```json
{
  "strike_qqq": 600.0,
  "strike_nq": 25573,
  "call_oi": 115656.0,
  "put_oi": 292117.0,
  "total_oi": 407773.0
}
```
Sorted by `total_oi` descending. Typically 10 entries.

### CBOE — Intraday Walls (0-7 DTE)

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `call_wall_intraday_qqq` | float | QQQ price | no* |
| `call_wall_intraday_nq` | float | NQ price | no* |
| `call_wall_intraday_gex` | float | raw GEX | no* |
| `put_wall_intraday_qqq` | float | QQQ price | no* |
| `put_wall_intraday_nq` | float | NQ price | no* |
| `put_wall_intraday_gex` | float | raw GEX | no* |
| `walls_intraday_max_dte` | int | days | no* |

*\* Present only if CBOE responded. Absent or `0` on CBOE timeout.*

### CBOE — Transition levels (C-Trans / P-Trans)

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `c_trans_intraday_qqq` / `c_trans_intraday_nq` | float | price | no |
| `p_trans_intraday_qqq` / `p_trans_intraday_nq` | float | price | no |
| `trans_intraday_max_dte` | int | days | no |

### CBOE — DEX (Delta Exposure)

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `dex_plus_intraday_qqq` / `dex_plus_intraday_nq` | float | price | no |
| `dex_plus_intraday_dex` | float | raw DEX | no |
| `dex_minus_intraday_qqq` / `dex_minus_intraday_nq` | float | price | no |
| `dex_minus_intraday_dex` | float | raw DEX | no |
| `dex_intraday_max_dte` | int | days | no |

### CBOE — Abs GEX (Pin Risk)

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `abs_gex_intraday_1_qqq` / `abs_gex_intraday_1_nq` | float | price | no |
| `abs_gex_intraday_1_gex` | float | \|GEX\| raw | no |
| `abs_gex_intraday_2_*` | same | — | no |
| `abs_gex_intraday_3_*` | same | — | no |
| `abs_gex_intraday_max_dte` | int | days | no |

### CBOE — Extended Walls

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `gex_wall_ext_1_qqq` / `gex_wall_ext_1_nq` | float | price | no |
| `gex_wall_ext_1_gex` | float | raw GEX | no |
| `gex_wall_ext_1_side` | string | `"call"` \| `"put"` | no |
| `gex_wall_ext_2/3/4_*` | same | — | no |
| `gex_walls_ext_max_dte` | int | days | no |

### CBOE — Top OI intraday

| Field | Type | Required |
|-------|------|:--------:|
| `top_oi_intraday` | array of objects | no |

Same structure as `top_oi_strikes` but for 0-7 DTE expirations.

### CBOE — 0DTE

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `max_pain_0dte_qqq` / `max_pain_0dte_nq` | float | price | no |
| `pin_strike_0dte_qqq` / `pin_strike_0dte_nq` | float | price | no |
| `charm_magnet_0dte_qqq` / `charm_magnet_0dte_nq` | float | price | no |
| `zero_dte_oi_total` | float | contracts | no |
| `zero_dte_dte` | int | = 0 | no |

### CBOE — Intraday IV (0-7 DTE)

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `atm_iv_intraday` | float | ratio (0.xx) | no |
| `atm_iv_intraday_dte` | int | days | no |
| `skew_25d_intraday` | float | ratio (vol points) | no |
| `skew_25d_intraday_dte` | int | days | no |
| `term_intraday_regime` | string enum | — | no |
| `term_intraday_slope` | float | ratio | no |
| `term_intraday_front_dte` | int | days | no |
| `term_intraday_back_dte` | int | days | no |
| `term_intraday_iv_front` | float | ratio | no |
| `term_intraday_iv_back` | float | ratio | no |

### IV Rank (252 rolling days)

| Field | Type | Required |
|-------|------|:--------:|
| `iv_rank_intraday` | object or null | no |

Object structure:
```json
{
  "ivr": 45.2,
  "iv_min": 0.12,
  "iv_max": 0.38,
  "n_samples": 252,
  "status": "ok",
  "lookback": 252,
  "field": "atm_iv_intraday"
}
```

`status`: `"ok"` (≥20 samples), `"partial"` (5-19), `"insufficient"` (<5)

### VIX (yfinance)

| Field | Type | Unit | Required |
|-------|------|------|:--------:|
| `vix` | float | index pts | no |
| `vix9d` | float | index pts | no |
| `vix_regime` | string enum | — | no |
| `vix_term` | string enum | — | no |
| `vix_term_slope` | float | pts | no |
| `vix_dod_change` | float | pts | no |

`vix_regime`: `"low"` (<14) \| `"normal"` (14-20) \| `"elevated"` (20-28) \| `"extreme"` (>28) \| `"unknown"`

`vix_term`: `"backwardation"` (VIX9D > VIX+0.5) \| `"contango"` \| `"flat"` \| `"unknown"`

### Macro (Forex Factory)

| Field | Type | Required |
|-------|------|:--------:|
| `macro_in_blackout` | bool | no |
| `macro_blackout_until` | string (ISO) or null | no |
| `macro_current_event` | object or null | no |
| `macro_next_event` | object or null | no |
| `macro_minutes_to_next` | int or null | no |

Macro event structure:
```json
{
  "title": "CPI m/m",
  "datetime_utc": "2026-05-04T12:30:00+00:00",
  "impact": "High",
  "forecast": "0.3%",
  "previous": "0.2%"
}
```

### Session tracking (intraday only)

| Field | Type | Required |
|-------|------|:--------:|
| `open_rth_spot` | float | no |
| `open_rth_time` | string (ISO) | no |
| `close_rth_spot` | float | no |
| `close_rth_time` | string (ISO) | no |
| `intraday_refresh_count` | int | no |

---

## "Required" vs "no" convention

- **Required** = always present if the pipeline runs without crashing. If absent, the JSON is corrupt.
- **No** = depends on source availability (CBOE, yfinance, Forex Factory). On source timeout, the field is either absent or `0` / `null`.

The `data_quality` field summarizes overall state:
- `"ok"`: CME + CBOE + VIX all present
- `"partial"`: at least one source missing
- `"error"`: broken or empty structure

---

## Rotation policy

| File type | Retention | Auto cleanup |
|-----------|-----------|--------------|
| `full_levels_*.json` | Overwritten each cycle | — |
| `history/*.json` | 380 days | `cleanup_history()` called every morning |
| `history/intraday/*.json` | 7 days | `cleanup_intraday_history()` called every cycle |
| `backups/*.tar.gz` | 30 days | `backup_snapshots.py` |
| `briefing_*_YYYY-MM-DD.pdf` | 1 day (today only) | `generate_pdf_*.py` deletes older ones |
