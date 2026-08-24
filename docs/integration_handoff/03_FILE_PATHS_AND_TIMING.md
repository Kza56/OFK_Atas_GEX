# 03 — File Paths & Timing

## Output file tree

```
{DATA_DIR}/
├── full_levels_NQ.json              ← PRIMARY NQ FILE
├── full_levels_ES.json              ← PRIMARY ES FILE
├── NQ_gex_latest.json               ← CME intermediate (do not consume)
├── ES_gex_latest.json               ← CME intermediate
├── levels_NQ.json                   ← CBOE intermediate (do not consume)
├── levels_ES.json                   ← CBOE intermediate
├── briefing_NQ.json                 ← AI briefing JSON
├── briefing_ES.json                 ← AI briefing JSON
├── briefing_NQ_2026-05-04.pdf       ← briefing PDF (one per day)
├── briefing_ES_2026-05-04.pdf       ← briefing PDF
├── history/
│   ├── NQ_full_levels_20260504.json ← daily snapshot (380d retention)
│   ├── ES_full_levels_20260504.json
│   ├── intraday/
│   │   ├── NQ_full_levels_20260504_0935.json  ← 5-min snapshot (7d retention)
│   │   ├── NQ_full_levels_20260504_0940.json
│   │   └── ...
│   └── briefings/
│       ├── NQ_briefing_20260504.json
│       └── ES_briefing_20260504.json
└── backups/
    └── snapshots_20260504_083000.tar.gz   ← archive (30d retention)
```

---

## Absolute paths

### Portable Python default

Without an override, the pipeline writes beneath its own source directory:

```text
<repo>/OFK_GEX_Pipeline/data
```

Set `GEX_DATA_DIR` to any writable directory to keep runtime output outside the
checkout. This works on macOS, Linux, and Windows.

### Legacy Windows full-indicator default

| Variable | Default value |
|----------|---------------|
| `{DATA_DIR}` | `C:\OFK_Atas_GEX\OFK_GEX_Pipeline\data` |
| Override | Environment variable `GEX_DATA_DIR` |

**Primary NQ file path:**
```
C:\OFK_Atas_GEX\OFK_GEX_Pipeline\data\full_levels_NQ.json
```

**Primary ES file path:**
```
C:\OFK_Atas_GEX\OFK_GEX_Pipeline\data\full_levels_ES.json
```

### macOS / Linux

The Python pipeline is portable. The default path is the repository-local
`OFK_GEX_Pipeline/data` directory; use `GEX_DATA_DIR` if output should live
elsewhere. ATAS X currently has a native build/load probe, while the full WPF
indicator remains Windows-only.

---

## Generation timing

### Morning pipeline

| Step | Typical time (ET) | File written | Duration |
|------|-------------------|--------------|----------|
| CME scrape | 08:00 – 08:10 | `NQ_gex_latest.json` | 30-90 sec (Playwright) |
| CBOE fetch | 08:10 – 08:12 | `levels_NQ.json` | 5-15 sec (HTTP) |
| VIX + macro | 08:12 – 08:15 | (in memory) | 2-5 sec |
| Merge → full_levels | 08:15 – 08:16 | **`full_levels_NQ.json`** | < 1 sec |
| Historical snapshot | 08:16 | `history/NQ_full_levels_YYYYMMDD.json` | < 1 sec |
| Codex briefing | 08:16 – 08:45 | `briefing_NQ.json` | Configured timeout |
| PDF | 08:45 – 08:46 | `briefing_NQ_YYYY-MM-DD.pdf` | 1-2 sec |

**Maximum acceptable delay**: `full_levels_NQ.json` must be written **before 09:30 ET** (RTH open). If the morning pipeline is not run before 09:30, the intraday loop will use the previous day's JSON.

### Intraday loop

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--interval` | 300 sec (5 min) | CBOE refresh frequency |
| `--cme-refresh-every` | 6 cycles (30 min) | Re-scrape CME (optional) |
| `--max-dte` | 7 | Max DTE included in CBOE calculations |

Each cycle writes:
1. `full_levels_NQ.json` (overwritten)
2. `history/intraday/NQ_full_levels_YYYYMMDD_HHMM.json` (new file)

**Effective frequency**: a new JSON every ~5 minutes between 09:30 and 16:00 ET.

---

## How to detect file freshness

### Method 1: file `mtime` (recommended for simple polling)

```csharp
var lastWrite = File.GetLastWriteTime(jsonPath);
bool isStale = (DateTime.Now - lastWrite).TotalMinutes > staleLimitMinutes;
```

This is the method used by existing ATAS indicators. Simple and reliable.

### Method 2: timestamp in the JSON

The `last_update_utc` field (ISO 8601 UTC) is updated on every write:
```json
"last_update_utc": "2026-05-04T13:45:12.123456+00:00"
```

```csharp
DateTime lastUpdate = DateTime.Parse(json["last_update_utc"]);
bool isStale = (DateTime.UtcNow - lastUpdate).TotalMinutes > staleLimitMinutes;
```

### Method 3: `generated_at` vs `last_update_utc`

- `generated_at`: timestamp of the morning's first creation.
- `last_update_utc`: timestamp of the last intraday refresh.

If `generated_at == last_update_utc`, the file has not been refreshed since the morning.

---

## Behavior when today's file does not exist

The pipeline **does not create** a new file each day — it **overwrites** the existing one. So `full_levels_NQ.json` always exists (except on first run).

| Situation | What happens |
|-----------|--------------|
| Morning not run | The file contains the previous day's data. The `trade_date` field will be D-1. |
| Loop not started | The file contains the morning snapshot. `last_update_utc` does not move. |
| CME scrape failed | The file is not written. The old one stays in place. |
| CBOE timeout in intraday | The file is written but with `data_quality: "partial"`. CBOE fields are 0 or absent. |
| Pipeline crash | The old file remains. No corrupt file (atomic write not guaranteed, but full write before rename). |

**Consumer recommendation**: check `trade_date` and `last_update_utc` to detect stale data rather than file existence.

---

## Intraday snapshot naming

Pattern: `{SYMBOL}_full_levels_{YYYYMMDD}_{HHMM}.json`

- `SYMBOL`: `NQ` or `ES` (uppercase)
- `YYYYMMDD`: local date (not UTC)
- `HHMM`: local time (not UTC), 24h format

Examples:
```
NQ_full_levels_20260504_0935.json   ← 09:35 local
NQ_full_levels_20260504_1430.json   ← 14:30 local
ES_full_levels_20260504_0940.json
```

---

## Retention summary

| Type | Pattern | Retention | Env override |
|------|---------|-----------|--------------|
| Primary file | `full_levels_{SYM}.json` | Continuously overwritten | — |
| Daily snapshot | `history/{SYM}_full_levels_YYYYMMDD.json` | 380 days | `GEX_HISTORY_MAX_DAYS` |
| Intraday snapshot | `history/intraday/{SYM}_full_levels_YYYYMMDD_HHMM.json` | 7 days | `GEX_INTRADAY_HISTORY_MAX_DAYS` |
| Backup | `backups/snapshots_*.tar.gz` | 30 days | — |
| Briefing PDF | `briefing_{SYM}_YYYY-MM-DD.pdf` | 1 day | — |
| Historical briefing JSON | `history/briefings/{SYM}_briefing_YYYYMMDD.json` | Not cleaned (grows indefinitely) | — |
