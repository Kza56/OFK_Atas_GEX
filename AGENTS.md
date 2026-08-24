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

## Phase 3 rules

- The platform-neutral indicator engine lives in `src/OFK.Gex.Core` and its
  tests live in `tests/OFK.Gex.Core.Tests`. Target plain `net10.0`/AnyCPU; do
  not use a Windows target framework.
- Keep the core independent of ATAS, WPF, rendering, process launching,
  platform-specific paths, P/Invoke, and proprietary application assemblies.
- Parse the stable merged JSON contract with `System.Text.Json`. Preserve the
  distinction between missing, malformed, and numeric-zero values.
- Keep context scoring, alert conditions, data health, freshness, and replay
  indexing deterministic and testable with an injected timestamp.
- Treat `OFK_ATAS` as a read-only behavioral reference until the portable core
  has passed its golden tests. Connecting the core to ATAS X is Phase 4.

## Verification

From the repository root:

```bash
dotnet restore tests/OFK.Gex.Core.Tests/OFK.Gex.Core.Tests.csproj --nologo
dotnet build src/OFK.Gex.Core/OFK.Gex.Core.csproj --configuration Release --no-restore --nologo
dotnet test tests/OFK.Gex.Core.Tests/OFK.Gex.Core.Tests.csproj --configuration Release --no-restore --nologo
PYTHONPYCACHEPREFIX=/private/tmp/ofk-phase3-pycache \
  .venv/bin/python -m pytest -p no:cacheprovider OFK_GEX_Pipeline/tests
./scripts/build_atas_x_probe.sh
git diff --check
```

For the Mac ATAS X probe, use `scripts/build_atas_x_probe.sh` with the local
ATAS X application bundle. Manual chart loading remains an explicit acceptance
step because a successful compile does not prove runtime compatibility.
