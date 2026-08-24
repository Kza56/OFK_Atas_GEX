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
└── .env.example
```

Repository-wide ignore rules live in the root `.gitignore`.

---

## Pipeline (5 stages)

```
1. CME scrape   → cme_*_browser_fetch.py    →  {NQ,ES}_gex_latest.json   (native Greeks)
2. CBOE scrape  → data_fetcher_*.py         →  levels_{NQ,ES}.json       (Max Pain, PCR, Top OI, EM)
3. Merge        → run_morning_*.py          →  full_levels_{NQ,ES}.json  (what ATAS reads)
4. AI briefing  → codex_briefing.py         →  briefing_{NQ,ES}.json
5. PDF          → generate_pdf_*.py         →  briefing_{NQ,ES}_YYYY-MM-DD.pdf
```

Codex briefing publication is optional and isolated from raw market-data
generation. The CLI response is constrained by the closed Structured Outputs
contract in `schemas/codex_output.schema.json`, then validated locally against
`schemas/briefing.schema.json` and atomically published. If Codex is
unavailable, the adapter atomically records a complete raw-data fallback in its
diagnostic file. A previous schema-valid briefing remains untouched; on a first
run with no valid briefing, the validated fallback is atomically published.
The morning runner always leaves `full_levels_*.json` intact and skips the PDF
for a fallback run.

---

## Installation

Python 3.10 or newer is required. From the repository root on macOS:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r OFK_GEX_Pipeline/requirements.txt
python3 -m playwright install chromium
```

For the AI briefing, install the Codex CLI and make `codex` available on your
PATH. If the binary is elsewhere, configure it without changing the code:

```bash
cd OFK_GEX_Pipeline
cp .env.example .env
# edit .env first if CODEX_CMD or the output directory needs changing
set -a
source .env
set +a
```

`.venv`, `.env`, generated data, history, logs, and PDFs are ignored by Git.

---

## Running

```bash
# Full NQ pipeline (≈ 2-3 min)
python3 run_morning_NQ.py

# Full ES pipeline
python3 run_morning_ES.py

# Individual stages (for debug)
python3 cme_NQ_browser_fetch.py
python3 data_fetcher_NQ.py
python3 codex_briefing.py NQ
python3 generate_pdf_NQ.py
```

Use `python3 run_morning_NQ.py --fast` (or the ES equivalent) to skip the Codex
briefing and PDF stages. Add `--skip-cme` to reuse the latest CME file. Run
`python3 run_intraday_refresh.py --help` for intraday loop and interval options.

---

## Verification

From the repository root with the virtual environment active:

```bash
python3 -m pytest OFK_GEX_Pipeline/tests
git diff --check
./scripts/build_atas_x_probe.sh
```

The ATAS X build does not prove runtime compatibility. Loading the probe on a
chart and confirming that it visibly renders remains a manual Phase 1 gate.
Real Codex NQ and ES acceptance runs also require working CLI authentication and
network access; report them as pending if those external prerequisites are not
available.

Phase 2 is complete only after the deterministic tests, NQ/ES schema and PDF
checks, Codex-disabled behavior, and the external Codex acceptance runs have all
been verified. Do not infer completion merely from a passing unit-test run.

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
