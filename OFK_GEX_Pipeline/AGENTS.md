# Python pipeline development notes

- Treat `full_levels_NQ.json` and `full_levels_ES.json` as the stable contract
  consumed by ATAS.
- Use `pathlib.Path`, `sys.executable`, and subprocess argument lists. Do not
  add shell pipelines, Windows drive-letter paths, `.cmd` executables, or
  `shell=True`.
- `codex_briefing.py` is optional: if Codex is unavailable, the merged market
  data must remain written and usable. Keep AI output JSON-only and validate it
  before publishing `briefing_*.json`.
- Keep generated files under `data/` (which is ignored except for samples).
- Run `python -m pytest tests` and `git diff --check` before handoff.
