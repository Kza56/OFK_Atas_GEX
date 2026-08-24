# 00 — Overview: OFK GEX Levels

## What is GEX Levels?

OFK GEX Levels is a calculation pipeline that scrapes CME option chains (E-mini NQ/ES, 49d+ expirations) and CBOE (QQQ/SPY, 0-7 DTE), merges structural and intraday data, computes gamma/vanna/charm/delta levels (walls, flip, transition, DEX, pinning), enriches everything with VIX + macro context, and writes a single JSON file per instrument (`full_levels_NQ.json`, `full_levels_ES.json`) consumed in real time by the ATAS indicators.

---

## Tech stack

| Layer | Tech | Role |
|-------|------|------|
| **Calculation pipeline** | Python 3.10+ (Playwright, yfinance, pandas, numpy, scipy) | CME/CBOE scraping, Greek calculations, merge, JSON export |
| **AI briefing** | Codex CLI (OpenAI) | Generates a narrative JSON + PDF briefing from the merged JSON |
| **PDF** | ReportLab (Python) | Dark-theme A4 briefing rendering |
| **ATAS indicators** | C# .NET 10 (also net6.0) | JSON loading, on-chart level drawing, Context Score, WPF panel |
| **Persistence** | JSON files on local disk | No database, no server |

The Python pipeline **produces** the data. The C# ATAS code **consumes** it. There is no network communication between the two — the interface contract is a JSON file on disk.

---

## Target platforms

| Platform | Status | Notes |
|----------|--------|-------|
| **ATAS Windows** | Production | Indicators compiled to DLL, loaded by ATAS |
| ATAS X macOS | Not supported | The Python pipeline is portable, but the C# indicators use WPF (Windows-only) |
| NinjaTrader 8 | Not supported | The JSON is portable, but indicators are not ported |
| Other platform | Possible | Any consumer able to read a local JSON can integrate |

---

## Execution workflow

### Morning (before RTH open, ~08:30 ET)

```
User → clicks "GEX LEVELS" button in the ATAS panel
     → triggers run_morning_{NQ|ES}.py
     → CME scrape (Playwright) → CBOE fetch → VIX fetch → macro fetch
     → merge → full_levels_{NQ|ES}.json
     → Codex briefing (optional) → briefing JSON + PDF
     → historical snapshot archived
```

### Intraday (continuous, every 5 min)

```
User → clicks "Loop ON" button in the ATAS panel
     → triggers run_intraday_refresh.py {NQ|ES} --loop
     → loop every 5 min:
         CBOE re-fetch → re-merge with morning CME → full_levels_{NQ|ES}.json overwritten
         intraday snapshot archived (for replay)
     → the ATAS indicator reloads the JSON each cycle (configurable auto-refresh, default 5 min)
```

The pipeline can also be launched manually from a terminal:
```bash
python run_morning_NQ.py
python run_intraday_refresh.py NQ --loop --interval 300
```

---

## When the system is expected to run

| Phase | Time (ET) | Action |
|-------|-----------|--------|
| **Pre-market** | 08:00 – 09:30 | Morning pipeline: CME + CBOE + briefing |
| **RTH** | 09:30 – 16:00 | Intraday loop active (CBOE refresh every 5 min) |
| **Post-market** | 16:00+ | Loop stopped automatically (or manually) |
| **Overnight** | Nothing | Previous day's files remain in place |

The pipeline does **not** run on NYSE holidays (auto-detected via `pandas_market_calendars`, bypass with `--ignore-holiday`).

---

## Covered instruments

| Instrument | Pipeline symbol | CBOE proxy | Conversion ratio |
|------------|-----------------|------------|------------------|
| **E-mini Nasdaq-100** | `NQ` | QQQ (ETF) | `spot_nq / spot_qqq` (~42.6) |
| **E-mini S&P 500** | `ES` | SPY (ETF) | `spot_es / spot_spy` (~10.0) |

CBOE levels are computed in QQQ/SPY strikes then converted to NQ/ES prices via the day's spot ratio. Each JSON field exists in pairs: `*_qqq` / `*_nq` (or `*_spy` / `*_es`).

---

## Data sources

| Source | Data | Method | Delay | Auth |
|--------|------|--------|-------|------|
| **CME Group** | NQ/ES options OI + settlements (49d+) | Playwright browser scrape | D-1 data (EOD settlement) | None (public) |
| **CBOE** | Live QQQ/SPY option chain (0-7 DTE) | REST API `cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json` | 15 min delay | None (free) |
| **Yahoo Finance** | VIX, VIX9D, QQQ/SPY spots | `yfinance` library | 15 min | None |
| **Forex Factory** | USD macro calendar (High/Medium impact) | CSV `nfs.faireconomy.media/ff_calendar_thisweek.csv` | Real-time | None |
| **Codex CLI** | Narrative AI briefing | Local `codex exec` call | Configured timeout | Codex authentication |
