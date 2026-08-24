# OFK GEX development guide

## Scope

This repository combines a Python market-data pipeline with custom ATAS
indicators. The Python side is the portable integration boundary: it writes
`OFK_GEX_Pipeline/data/full_levels_NQ.json` and
`OFK_GEX_Pipeline/data/full_levels_ES.json`, which the indicators consume.

## Phase 2 rules

- Keep the Python pipeline macOS/Linux/Windows portable. Use `pathlib.Path`,
  `sys.executable`, and argument-list subprocess calls; never rely on `shell=True`,
  `cmd.exe`, PowerShell, drive-letter paths, or `.cmd` executables.
- AI briefings are generated through the Codex CLI adapter in
  `OFK_GEX_Pipeline/codex_briefing.py`. The adapter must run read-only, validate
  JSON, time out cleanly, and leave the merged market-data JSON usable when the
  CLI is unavailable.
- Keep the merged JSON contract stable unless a schema version and consumer
  update are included together.
- Do not put credentials, generated data, PDFs, logs, or local ATAS paths into
  commits. Use environment variables documented in the pipeline `.env.example`.
- The ATAS X probe is the macOS compatibility baseline. Changes to the full
  Windows indicator remain separate until the portable core has tests.

## Verification

From the repository root:

```bash
python -m pytest OFK_GEX_Pipeline/tests
git diff --check
```

For the Mac ATAS X probe, use `scripts/build_atas_x_probe.sh` with the local
ATAS X application bundle. Manual chart loading remains an explicit acceptance
step because a successful compile does not prove runtime compatibility.
