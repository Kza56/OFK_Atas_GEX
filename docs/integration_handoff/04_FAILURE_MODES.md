# 04 — Failure Modes

## Failure matrix

| Source | Failure type | Impact on `full_levels_*.json` | `data_quality` | Affected fields |
|--------|--------------|--------------------------------|---------------|-----------------|
| **CME** | Playwright timeout | File **not written** (morning) or stale CME data (intraday) | `"partial"` or file unchanged | `gamma_flip`, `vol_trigger`, `call_wall`, `put_wall`, `risk_pivot`, `vanna_flip`, `charm_magnet`, `total_gex/vex/cex/dex`, `*_regime`, `top_oi_strikes`, `max_pain_*`, `expected_move_*`, `pcr`, structural IV |
| **CME** | Page structure changed | Scraper crash, file not written | File unchanged | All CME fields |
| **CBOE** | HTTP 5xx / timeout | File written without intraday data | `"partial"` | `*_intraday_*`, `*_0dte_*`, `top_oi_intraday`, intraday IV |
| **CBOE** | Malformed JSON | Exception caught, intraday fields set to 0 | `"partial"` | Same |
| **CBOE** | Empty chain (pre-market, weekend) | Intraday fields at 0, no error | `"partial"` | Same |
| **yfinance** | Timeout / API down | VIX fields at 0 / absent | `"partial"` | `vix`, `vix9d`, `vix_regime`, `vix_term`, `vix_dod_change`, `vix_term_slope` |
| **Forex Factory** | CSV 404 / format change | Macro fields absent or default | `"ok"` (non-blocking) | `macro_*` fields |
| **Claude CLI** | Timeout / API rate limit | Briefing not generated, full_levels **unaffected** | No impact | `briefing_*.json` and PDF absent |
| **Disk** | Out of space | Crash on write | Possible corrupt file | All |
| **Network** | Total outage | No file written | File unchanged (stale) | All |

---

## Per-source detail

### CME unavailable

**Symptom**: `cme_{NQ|ES}_browser_fetch.py` fails (Playwright timeout, page changed, captcha).

**Morning impact**:
- `NQ_gex_latest.json` is not written.
- `run_morning_NQ.py` aborts or writes a `full_levels_NQ.json` without CME data (per implementation: currently the merge requires CME as a base).
- In practice: **the morning pipeline fails and the old file remains**.

**Intraday impact**:
- The loop uses the morning `NQ_gex_latest.json` as the CME base.
- If the morning CME is missing, the loop cannot merge → it writes a CBOE-only file or skips.
- `--cme-refresh-every` re-attempts the CME scrape every N cycles.

**Consumer detection**:
- Check `trade_date`: if it is a past date, CME data is stale.
- Check that `gamma_flip > 0` and `call_wall > 0`: if `0`, CME has not loaded.

### CBOE unavailable

**Symptom**: HTTP timeout or empty response from `cdn.cboe.com`.

**Impact**:
- All `*_intraday_*` and `*_0dte_*` fields are `0`.
- The `full_levels_*.json` file is still written (CME data remains).
- `data_quality` becomes `"partial"`.

**Consumer detection**:
- `data_quality == "partial"` AND `call_wall_intraday_nq == 0`.
- Or check `walls_intraday_max_dte`: if absent or 0, CBOE did not respond.

**CBOE specifics**: the chain is empty in pre-market (before ~09:15 ET) and after close (after ~16:15 ET). This is not an error — it is normal. Intraday fields will be 0 outside market hours.

### Claude AI briefing fails

**Symptom**: `claude_agent_NQ.py` timeout or API error.

**Impact**:
- `briefing_NQ.json` is not written (or contains an error).
- `briefing_NQ_YYYY-MM-DD.pdf` is not generated.
- **`full_levels_NQ.json` is NOT affected** — the briefing is independent post-processing.

**Consumer detection**:
- If you consume `briefing_NQ.json`, check its existence and freshness.
- If you only consume `full_levels_NQ.json`, no impact.

### yfinance unavailable

**Symptom**: Yahoo Finance timeout.

**Impact**:
- `vix`, `vix9d` and related fields at `0` or absent.
- `vix_regime` becomes `"unknown"`.
- `data_quality` becomes `"partial"`.

**Detection**: `vix == 0` or `vix_regime == "unknown"`.

### Forex Factory unavailable

**Symptom**: CSV 404 or format change.

**Impact**:
- `macro_in_blackout` at `false` (default safe).
- `macro_next_event` at `null`.
- **`data_quality` stays `"ok"`** — macro is not considered a critical source.

**Detection**: `macro_next_event == null` AND during RTH = likely a Forex Factory issue.

---

## Health file

There is **no separate health/status file**. Health is encoded **within the JSON itself** via:

1. **`data_quality`** (root level): `"ok"` / `"partial"` / `"error"`
2. **`last_update_utc`**: temporal freshness
3. **`trade_date`**: detects stale data (past date)
4. **`json_schema_version`**: detects format incompatibility

### Full detection logic

```
IF file does not exist → CRITICAL ERROR (pipeline never run)
IF mtime > 15 min AND intraday loop expected to run → STALE
IF data_quality == "error" → CORRUPT DATA
IF data_quality == "partial" → DEGRADED (some sources missing)
IF trade_date != today (YYYYMMDD format) → PREVIOUS DAY DATA
IF gamma_flip == 0 → CME NOT LOADED
IF call_wall_intraday_nq == 0 → CBOE NOT LOADED
IF vix == 0 → VIX NOT LOADED
ELSE → OK
```

---

## Warning levels for a consumer

| Level | Condition | Recommendation |
|-------|-----------|----------------|
| `OK` | `data_quality == "ok"` AND `trade_date == today` AND `mtime < 10 min` | Use normally |
| `STALE` | `mtime > 10 min` (loop expected to run) | Show a warning, continue with existing data |
| `PARTIAL` | `data_quality == "partial"` | Use available data, ignore zero fields |
| `YESTERDAY` | `trade_date != today` (YYYYMMDD) | Morning pipeline not run. CME levels are valid (OI changes little day-over-day) but intraday CBOE levels are obsolete |
| `ERROR` | `data_quality == "error"` or file absent | Do not use. Alert the user |

---

## Atomic write

JSON writing is **not atomic** in the current implementation. The file is written directly via `json.dump()`. In theory, a consumer reading during the write could read a truncated JSON.

**Practical mitigation**:
- Write takes < 10 ms (15-25 KB file).
- The C# (ATAS) consumer re-reads the file every 5 minutes, not continuously.
- If JSON parsing fails on the consumer side, that is a concurrent read case → retry in 1 second.

**Possible improvement** (not implemented): write to a temporary file then `os.replace()` (atomic on Windows NTFS and Linux ext4).
