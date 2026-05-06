# Claude Code Prompt — Finish Translating OFK_Atas_GEX (Phase 2)

Copy-paste this in a fresh Claude Code session, in your repo root.

---

I'm finalizing the translation of this OFK_Atas_GEX repo from French to English
for an international open-source release. Phase 1 (all 14 .md files) is already
done — they live in their normal places and serve as the **canonical glossary**.

**Read first**: `TRANSLATION_GLOSSARY.md` at the repo root. It encodes every
terminology decision (JSON keys, enum values, UI strings, ATAS group names,
etc.). Apply it strictly.

## What's left to translate

1. **`docs/integration_handoff/06_SAMPLE_OUTPUTS.md`** — already done in the
   .md pass. Skip if green.
2. **17 Python files in `OFK_GEX_Pipeline/`**: all comments, docstrings, log
   messages (`logger.info`, `print`, `console.print`), CLI argparse help,
   exception messages, status banners. Keep variable/function names.
   - `config.py`, `logging_setup.py`, `market_calendar.py`, `vix_fetcher.py`,
     `econ_calendar.py`, `backup_snapshots.py`
   - `cme_NQ_browser_fetch.py`, `cme_ES_browser_fetch.py`,
     `data_fetcher_NQ.py`, `data_fetcher_ES.py`
   - `run_morning_NQ.py`, `run_morning_ES.py`, `run_intraday_refresh.py`
   - `claude_agent_NQ.py`, `claude_agent_ES.py`,
     `generate_pdf_NQ.py`, `generate_pdf_ES.py`
   - `backtest_briefings.py`
   - `tests/` (4 files)
3. **6 C# files in `OFK_ATAS/`**: comments, `[Display(Name=...)]`,
   `[Description(...)]`, `GroupName=...`, `AddAlert(...)` strings, panel WPF
   labels, status banner texts.
   - `OFK_NQ_GEX_Levels.cs` (~3000 lines), `OFK_ES_GEX_Levels.cs` (~3000 lines)
   - `OFK_NQ_ContextScore.cs`, `OFK_ES_ContextScore.cs`
   - `OFK_GexShared.cs`, `OFK_ReplayWindow.cs`
4. **JSON sample**: `OFK_GEX_Pipeline/data/samples/briefing_NQ.json`. Rename
   French keys to English per the glossary, translate enum values too.

## Critical rules

- **Do NOT touch** `full_levels_*.json` keys — they are already English and
  consumed by the C# indicators. Same for `top_oi_*` array item keys
  (`strike_qqq`, `strike_es`, `call_oi`, `put_oi`, `total_oi`).
- **Do NOT rename** classes, methods, properties, modules, files.
- **The Python `briefing.get(...)` dual-read pattern** must stay backward-
  compatible: code reads BOTH French and English JSON keys (so that historical
  French snapshots in `data/history/briefings/` keep rendering), but writes
  ONLY the English keys going forward. Confirm this on every reader/writer
  pair you touch in `claude_agent_*.py`, `generate_pdf_*.py`,
  `backtest_briefings.py`.
- ATAS UI strings (`[Display(...)]`) are visible to traders → translate
  carefully and keep numeric prefixes like `"01.Source"` for display ordering.

## Suggested processing order

1. Translate `briefing_NQ.json` sample first (small, validates the glossary).
2. Python pipeline files in dependency order:
   `config.py` → `logging_setup.py` → utilities → fetchers → run_morning →
   intraday refresh → agents → PDF → backtest → tests.
   Run `pytest -x OFK_GEX_Pipeline/tests/` after each batch.
3. C# files: small ones first
   (`OFK_GexShared.cs`, `OFK_ReplayWindow.cs`, `*_ContextScore.cs`),
   then the two big `*_GEX_Levels.cs`.
   Run `dotnet build OFK_ATAS/OFK_Atas_GEX.csproj -c Release` after each batch.
4. Commit per file or per small batch with messages like:
   `chore(i18n): translate <file> comments+strings to English`.

## Expected commits

About 25-30 small commits at the end, all on `main`, each green-tested.
