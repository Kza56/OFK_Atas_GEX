# OFK_GEX_Pipeline — Context for Claude Agent

## 1. Overview

Python pipeline for acquiring and computing options data (GEX/DEX/VEX/CEX)
for intraday scalping on NQ (E-mini Nasdaq-100) and ES (E-mini S&P500).

Produces `full_levels_NQ.json` / `full_levels_ES.json` files consumed by the
ATAS indicators (`OFK_NQ_GEX_Levels.cs` / `OFK_ES_GEX_Levels.cs`).

---

## 2. File architecture

```
OFK_GEX_Pipeline/
├── config.py                  # Centralized paths, JSON_SCHEMA_VERSION, data_quality, IV Rank, snapshots
├── logging_setup.py           # RotatingFileHandler (10 MB × 5) + console, idempotent
├── market_calendar.py         # NYSE DST/holidays via pandas_market_calendars
├── vix_fetcher.py             # VIX + VIX9D via yfinance, regime + term structure
├── econ_calendar.py           # Forex Factory calendar, ±30min macro blackout
├── backup_snapshots.py        # Tarball snapshots + retention cleanup
│
├── cme_NQ_browser_fetch.py    # CME NQ scraping (Playwright) — intraday OI + settlements
├── cme_ES_browser_fetch.py    # CME ES scraping (Playwright) — intraday OI + settlements
├── data_fetcher_NQ.py         # CBOE NQ/QQQ — IV, skew, term structure, intraday walls
├── data_fetcher_ES.py         # CBOE ES/SPY — IV, skew, term structure, intraday walls
│
├── run_morning_NQ.py          # NQ morning pipeline: CME + CBOE + merge + PDF + briefing
├── run_morning_ES.py          # ES morning pipeline: CME + CBOE + merge + PDF + briefing
├── run_intraday_refresh.py    # Intraday refresh (default 5 min): CBOE + VIX + macro
│
├── claude_agent_NQ.py         # Claude agent → NQ briefing (strict JSON)
├── claude_agent_ES.py         # Claude agent → ES briefing (strict JSON)
├── generate_pdf_NQ.py         # NQ briefing PDF generation (ReportLab)
├── generate_pdf_ES.py         # ES briefing PDF generation (ReportLab)
├── backtest_briefings.py      # Backtest of historical briefings
│
├── skills/
│   ├── gex_analyst_NQ.md      # NQ agent prompt/spec
│   └── gex_analyst_ES.md      # ES agent prompt/spec
├── data/
│   ├── full_levels_NQ.json    # Final NQ JSON (consumed by ATAS)
│   ├── full_levels_ES.json    # Final ES JSON (consumed by ATAS)
│   ├── NQ_gex_latest.json     # CME-only NQ
│   ├── ES_gex_latest.json     # CME-only ES
│   ├── levels_NQ.json         # CBOE-only NQ
│   ├── levels_ES.json         # CBOE-only ES
│   └── history/               # Daily snapshots (380-day retention for 252-day IVR)
├── tests/                     # pytest (26 tests)
│   ├── conftest.py
│   ├── test_data_quality.py
│   ├── test_vix.py
│   ├── test_market_calendar.py
│   └── test_backup.py
└── requirements.txt
```

---

## 3. Data flow

```
CME (Playwright)                 CBOE (data_fetcher)
  OI, settle prices                IV, skew, term, walls 0-7d
         ↓                                ↓
  NQ/ES_gex_latest.json          levels_NQ/ES.json
         ↓                                ↓
         └───────── merge_levels() ────────┘
                         ↓
                  + fetch_vix()           ← yfinance (VIX, VIX9D)
                  + blackout_status()     ← Forex Factory CSV
                  + compute_data_quality()
                  + JSON_SCHEMA_VERSION
                  + compute_iv_rank()
                  + save_snapshot()
                         ↓
                  full_levels_NQ/ES.json  → ATAS C# indicator
                         ↓
                  claude_agent → briefing JSON → generate_pdf
```

---

## 4. Utility modules

### config.py
- `JSON_SCHEMA_VERSION = "1.0"` — increment on every JSON structure change.
  The ATAS indicator compares it and shows a warning on mismatch.
- `compute_data_quality(full_dict)` → `"ok"` | `"partial"` | `"error"`
  - ok: CME + CBOE + VIX all present
  - partial: at least one source missing
  - error: empty dict or broken structure
- `save_snapshot(symbol, full_dict)` → daily archive in `data/history/`
- `compute_iv_rank(symbol, current_iv)` → 252-day IVR (0-100%)
- `cleanup_history(symbol)` → removes snapshots > 380 days
- `update_session_log(symbol, trade_date, spot)` → RTH open/close tracking

### market_calendar.py
- `is_rth_now()` → bool (RTH 09:30-16:00 ET, DST-aware)
- `is_market_open_today()` → bool (excludes weekends + NYSE holidays)
- `is_early_close_today()` → bool (Thanksgiving eve, etc.)
- `session_open_today_utc()` / `session_close_today_utc()` → UTC datetime
- `minutes_to_close()` → int
- Backend: `pandas_market_calendars` NYSE, weekday-only fallback on error

### vix_fetcher.py
- `fetch_vix()` → dict:
  - `vix`, `vix9d`, `vix_dod_change` (day-over-day change)
  - `vix_regime`: `"low"` (<14), `"normal"` (14-20), `"elevated"` (20-28), `"extreme"` (>28)
  - `vix_term`: `"backwardation"` (VIX9D > VIX), `"flat"`, `"contango"`
  - `vix_term_slope`: VIX9D - VIX

### econ_calendar.py
- `fetch_econ_events(min_impact="High")` → list of USD events (30min cache)
- `blackout_status(now_utc, blackout_minutes=30)` → dict:
  - `in_blackout`: bool
  - `blackout_until_utc`, `current_event`, `next_event`, `minutes_to_next`
- Source: Forex Factory CSV API

### backup_snapshots.py
- `make_backup()` → tarball `data/backups/snapshots_YYYYmmdd_HHMMSS.tar.gz`
- `cleanup_old_backups(retention_days=30, keep_monthly=True)`

### logging_setup.py
- `setup_logging()` — RotatingFileHandler 10 MB × 5 backups + console
- Idempotent (does not add duplicate handlers)

---

## 5. Execution scripts

### run_morning_NQ.py / run_morning_ES.py
Full morning pipeline:
1. Check NYSE holiday (`--ignore-holiday` to force)
2. Detect early close (warning banner)
3. Scrape CME (Playwright) → `NQ/ES_gex_latest.json`
4. Fetch CBOE → `levels_NQ/ES.json`
5. Merge + VIX + blackout + data_quality + schema_version
6. Save `full_levels_NQ/ES.json` + historical snapshot
7. Backup (`make_backup` + `cleanup_old_backups`)
8. Claude agent → briefing JSON → PDF

### run_intraday_refresh.py
Loop refresh (default 300s = 5 min):
- `--interval N`: interval in seconds
- `--cme-refresh-every N`: re-scrape CME every N cycles (otherwise CBOE only)
- `--max-dte N`: DTE filter for intraday walls
- Each cycle: CBOE + VIX + blackout → re-merge → full_levels JSON
- `setup_logging()` initialized at startup

---

## 6. CME scraping (intraday OI)

### STANDARD_PIDS vs WEEKLY_PIDS
- **STANDARD_PIDS** (NQ: 148, ES: 136/138) → `get_oi_standard_with_intraday()`:
  uses `Volume/Options/Details?reporttype=F` for intraday OI during the session,
  merged with settlements for settle prices (required for IV inversion).
  Automatic fallback to settlements-only outside market hours.
- **WEEKLY_PIDS** → classic `get_oi_volume_details()` (settlements only)

---

## 7. full_levels_*.json structure

### GEX/options fields (CME)
`gamma_flip`, `vol_trigger`, `call_wall`, `put_wall`, `risk_pivot`,
`vanna_flip`, `charm_magnet`, `max_pain`, `total_gex`, `total_vex`,
`total_cex`, `total_dex`, `gex_regime`, `pcr`, `spot_loaded`

### Intraday fields (CBOE 0-7 DTE)
`call_wall_intraday_*`, `put_wall_intraday_*`, `c_trans_intraday_*`,
`p_trans_intraday_*`, `dex_plus_intraday_*`, `dex_minus_intraday_*`,
`top_oi_intraday[]`, `abs_gex_intraday[]`, `gex_ext_intraday[]`

### 0DTE fields
`max_pain_0dte_*`, `pin_strike_0dte_*`, `charm_magnet_0dte_*`,
`zero_dte_oi_total`, `zero_dte_dte`

### Volatility fields
`atm_iv_intraday`, `skew_25d_intraday`, `term_intraday_slope`,
`term_intraday_regime`, `iv_rank_intraday` (object with ivr, status, n_samples)

### VIX + macro + health context fields (at JSON root)
All these fields are written at the **root** of `full_levels_*.json` (not in
a `_meta` object). The Python code (`run_morning_*`, `run_intraday_refresh`)
writes them as such, and the C# side (`GexLoader` → `MetaSnapshot`) reads
them at the same level.

```json
{
  "vix": 18.5,
  "vix9d": 17.2,
  "vix_regime": "normal",
  "vix_term": "backwardation",
  "vix_term_slope": -1.3,
  "vix_dod_change": 0.8,

  "macro_in_blackout": false,
  "macro_blackout_until": null,
  "macro_current_event": null,
  "macro_next_event": { "title": "FOMC Minutes", "...": "..." },
  "macro_minutes_to_next": 45,

  "json_schema_version": "1.0",
  "last_update_utc": "2026-05-04T14:30:00+00:00",
  "data_quality": "ok"
}
```

Notes:
- `macro_current_event` / `macro_next_event` are **objects** (or `null`).
  The title is read via `ParseNestedString(json, "macro_next_event", "title")`.
- `macro_blackout_until` (no `_utc` suffix in current Python code).
- `vix_regime` ∈ `{"low","normal","elevated","extreme","unknown"}`.
- `vix_term` ∈ `{"backwardation","flat","contango","unknown"}`.
- `data_quality` ∈ `{"ok","partial","error"}`.

---

## 8. Regime interpretation (scalping)

### GEX regime
- `1` (positive) → dealers dampen moves → pinning, tight range, mean-reversion
- `-1` (negative) → dealers amplify → breakouts, momentum, expanding vol

### Gamma zones (5 zones, TanukiTrade-style)
Spot position vs bounds Put Wall < pTrans < cTrans < Call Wall:
- `spot > Call Wall` → BULLISH SQUEEZE (momentum, no fade)
- `cTrans < spot < Call Wall` → POSITIVE gamma (mean-reversion)
- `pTrans < spot < cTrans` → TRANSITION (neutral)
- `Put Wall < spot < pTrans` → NEGATIVE gamma (directional breakouts)
- `spot < Put Wall` → BEARISH SQUEEZE (panic, explosive vol)

### VIX regime
- `low` (<14) → complacency, tight ranges
- `normal` (14-20) → classic scalping
- `elevated` (20-28) → widen stops, reduce size
- `extreme` (>28) → avoid scalping

### Intraday term structure
- `backwardation` (slope > 0) → immediate stress, breakouts
- `contango` (slope < 0) → calm, mean-reversion
- `flat` → neutral

---

## 9. ATAS alerts (12 types)

The C# indicators trigger on-chart alerts (banner + sound):

| # | Key | Trigger |
|---|-----|---------|
| 1 | `gamma_flip` | Price crosses Gamma Flip |
| 2 | `call_wall_id` / `put_wall_id` | Price crosses intraday Call/Put Wall |
| 3 | `c_trans` / `p_trans` | Price crosses cTrans/pTrans (gamma zone) |
| 4 | `pin_0dte` | Price near Pin Strike 0DTE (±N ticks) |
| 5 | `charm_magnet` | Price near Charm Magnet 0DTE (last RTH hour) |
| 6 | `ivr_high` / `ivr_low` | IVR > 90% or < 10% |
| 7 | `term_back` | Acute term backwardation (slope > 1 vp) |
| 8 | `skew_high` | Explosive 25D skew (> 5 vp) |
| 9 | `vix_extreme` | VIX enters extreme regime |
| 10 | `vol_flow` | Price crosses GEX ext-1 |
| 11 | `macro_imminent` | High-impact macro event in < 30 min |
| 12 | `stale_data` / `data_partial` / `data_error` / `schema_mismatch` | Pipeline issue |

On-chart visual banners (top-right corner) with color coding:
- **Red**: danger (VIX extreme, macro blackout)
- **Orange**: regime (IVR, term, skew)
- **Cyan**: proximity (Pin Strike, Charm Magnet)
- **Amber**: level cross
- **Gray**: stale/partial/error data

---

## 10. Tests

```bash
pytest OFK_GEX_Pipeline/tests/ -v
```

26 tests covering: `data_quality`, `vix_fetcher`, `market_calendar`, `backup_snapshots`.

---

## 11. CI/CD

`.github/workflows/ci.yml`:
- Python: `compileall` + `pytest`
- .NET: `dotnet build -c Release` (continue-on-error)

---

## 12. Dependencies

```
playwright>=1.40      # CME scraping
requests>=2.31        # misc HTTP
reportlab>=4.0        # briefing PDFs
pandas-market-calendars>=4.4  # NYSE DST + holidays
yfinance>=0.2.40      # VIX feed
pytz>=2024.1          # timezones
pytest>=8.0           # tests
```

---

## 13. Files NOT to read

- `data/history/` — thousands of daily JSON snapshots
- `data/backups/` — large tarballs
- `ATAS_Complete_Reference.html` — 14 MB, everything is in the root `CLAUDE.md`
