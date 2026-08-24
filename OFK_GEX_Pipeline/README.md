# OFK GEX Pipeline

Python pipeline that produces the Greeks Exposure (GEX/VEX/CEX/DEX) levels for
NQ and ES E-mini futures, then read by the C# ATAS indicators of the OFK suite.

---

## Architecture

```
OFK_GEX_Pipeline/
├── config.py                   # centralized paths (override via env vars)
├── cme_NQ_browser_fetch.py     # scrape CME NQ options (headless Playwright)
├── cme_ES_browser_fetch.py     # scrape CME ES options (headless Playwright)
├── data_fetcher_NQ.py          # CBOE QQQ → missing metrics (NQ proxy)
├── data_fetcher_ES.py          # CBOE SPY → missing metrics (ES proxy)
├── codex_briefing.py           # AI briefing via Codex CLI (read-only)
├── generate_pdf_{NQ,ES}.py     # PDF rendering of the briefing
├── run_morning_{NQ,ES}.py      # orchestrator (CME → CBOE → merge → AI → PDF)
├── skills/                     # markdown specs for the briefing provider
├── data/                       # runtime outputs (gitignored)
│   └── samples/                # output examples (committed)
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Pipeline (5 stages)

```
1. CME scrape   → cme_*_browser_fetch.py    →  {NQ,ES}_gex_latest.json   (native Greeks)
2. CBOE scrape  → data_fetcher_*.py         →  levels_{NQ,ES}.json       (Max Pain, PCR, Top OI, EM)
3. Merge        → run_morning_*.py          →  full_levels_{NQ,ES}.json  (what ATAS reads)
4. AI briefing  → codex_briefing.py         →  briefing_{NQ,ES}.json
5. PDF          → generate_pdf_*.py         →  briefing_{NQ,ES}_YYYY-MM-DD.pdf
```

If Codex is unavailable, `codex_briefing.py` writes a deterministic briefing
with `_provider.status == "fallback"` and preserves the complete source data
under `_raw_full_levels`. The morning runner leaves `full_levels_*.json` intact
and skips the PDF for that run.

---

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

For the AI briefing, install the Codex CLI and make `codex` available on your
PATH. If the binary is elsewhere, configure it without changing the code:

```bash
cp .env.example .env
set -a; source .env; set +a
# edit .env first if CODEX_CMD or the output directory needs changing
```

---

## Running

```bash
# Full NQ pipeline (≈ 2-3 min)
python run_morning_NQ.py

# Full ES pipeline
python run_morning_ES.py

# Individual stages (for debug)
python cme_NQ_browser_fetch.py
python data_fetcher_NQ.py
python codex_briefing.py NQ
python generate_pdf_NQ.py
```

---

## Configuration

All paths are defined in `config.py` with a local default + environment
variable override. You do **not** need to modify the code to redirect outputs
elsewhere — use `.env` or shell variables.

Available variables: see `.env.example`.

---

## Historical snapshots

On every successful run, the pipeline duplicates `full_levels_*.json` into
`data/history/` with a dated name:

```
data/history/NQ_full_levels_20260501.json
data/history/ES_full_levels_20260501.json
```

Re-runs of the same day overwrite the existing snapshot (idempotent). This
history will later feed the IVR (IV Rank over 252 days, Phase 3).

---

## Output for ATAS

The C# indicators `OFK_NQ_GEX_Levels.cs` and `OFK_ES_GEX_Levels.cs` read by
default from `full_levels_{NQ,ES}.json`. Configure the `JsonPath` in the ATAS
indicator settings to point to the file produced by this pipeline, for example:

```
<repo path>/OFK_GEX_Pipeline/data/full_levels_NQ.json
```

Or redirect the pipeline to write directly to the ATAS folder via
`NQ_FULL_JSON` in `.env`.
