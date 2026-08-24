# Phase 3 portable indicator core

## Status and boundary

Phase 3 extracts the non-visual indicator behavior into a platform-neutral
`.NET 10`/AnyCPU library under `src/OFK.Gex.Core`. Its tests run on macOS
without ATAS, WPF, Windows desktop assemblies, or proprietary binaries.

The Python merger remains the producer of the stable
`full_levels_NQ.json`/`full_levels_ES.json` contract. `OFK_ATAS` remains the
read-only Windows behavioral reference; no legacy indicator source was changed.

Phase 4 is intentionally deferred. It will own the functional ATAS X adapter,
chart rendering, alerts displayed by ATAS, refresh lifecycle, and any other
host integration. The Phase 1 ATAS X probe is still only a compile/compatibility
baseline, with chart loading and rendering as a manual acceptance step.

## Architecture

| Area | Location | Responsibility |
|---|---|---|
| Contracts | `src/OFK.Gex.Core/Contracts` | Nullable market and metadata records; missing values remain distinct from zero |
| Configuration | `src/OFK.Gex.Core/Configuration` | Shared NQ/ES instrument selection and symbol-specific JSON suffixes |
| Loading | `src/OFK.Gex.Core/Loading` | Typed `System.Text.Json` parsing, schema/field diagnostics, and portable file I/O |
| Analysis | `src/OFK.Gex.Core/Analysis` | Pure shared context score and typed snapshot adapter |
| Alerts | `src/OFK.Gex.Core/Alerts` | Pure alert decisions and caller-carried transition state |
| Health | `src/OFK.Gex.Core/Health` | Deterministic quality/freshness policy using a supplied timestamp |
| Replay | `src/OFK.Gex.Core/Replay` | Portable snapshot filename parsing, filtering, ordering, and deduplication |
| Tests | `tests/OFK.Gex.Core.Tests` | Golden fixtures, parity tests, boundary tests, and failure coverage |

The core contains no UI, sound, banners, cooldown persistence, logging,
process launching, global clock access, or host-specific rendering. Consumers
supply current time, prices, prior VIX regime, approach-state values, and file
metadata explicitly.

## Public contracts

- `InstrumentDefinitions.Nq` and `.Es` select one shared loader and calculator
  implementation through `InstrumentDefinition`.
- `SnapshotParser.Parse(...)` accepts JSON strings or streams. Unknown JSON
  fields are tolerated; consumed numeric fields are nullable and wrong types
  fail parsing rather than becoming zero.
- `SnapshotLoader.Load(...)` and `LoadAsync(...)` add portable path/file I/O and
  return source path, last-write time, and byte length.
- `SnapshotLoadResult` contains the typed `MarketSnapshot`, a `HealthState`,
  structured diagnostics, source metadata, and an `IsSuccess` usability flag.
  Unsupported schemas and `data_quality=error` are not successful results.
- Decimal-form OI values such as `9000.0` are accepted only when they are exact
  64-bit integers. Fractional or out-of-range OI remains null and produces a
  `field.invalid_integer` diagnostic.
- `ContextScoreCalculator.Calculate(...)` accepts either a typed snapshot or a
  focused `ContextScoreInput` plus profile and supplied UTC time.
- `AlertEvaluator.Evaluate(...)` returns decisions plus the next predictive
  approach-state map and VIX-regime state; it does not perform host effects.
- `HealthEvaluator.Evaluate(...)` accepts a focused health input and supplied
  current time. `last_update_utc` is preferred, with file last-write time as a
  fallback.
- `ReplayIndex` parses names shaped like
  `SYMBOL_full_levels_YYYYMMDD_HHMM.json`, filters by NQ/ES and session date,
  sorts by encoded time, and resolves duplicates using ordinal path order.

The merger's current root-level metadata layout is preserved, including
`json_schema_version`, `last_update_utc`, `data_quality`, VIX fields,
`macro_in_blackout`, and object-shaped `macro_next_event`. The parser also
accepts the earlier string-shaped macro event for compatibility.

## Health precedence

The deterministic precedence, from strongest to weakest, is:

1. `Missing` — the source file is absent or no path was supplied.
2. `Invalid` — JSON is malformed, a consumed field has the wrong type, or a
   supplied source timestamp is unreasonably far in the future.
3. `SchemaMismatch` — `json_schema_version` is missing or is not `1.0`.
4. `Error` — pipeline `data_quality` is `error`.
5. `Partial` — pipeline `data_quality` is `partial`, optional/required values
   have diagnostics, or no valid update/file timestamp is available.
6. `Stale` — the effective timestamp is older than the configured threshold.
7. `Healthy` — schema, quality, and freshness checks pass.

Parser health covers document validity, schema, field diagnostics, and declared
quality. Freshness is a separate pure evaluation because it requires the
caller's fixed/current time and optional filesystem timestamp.

## Legacy-to-core mapping

| Legacy behavior | Portable core |
|---|---|
| NQ/ES JSON loading in the full indicators | `SnapshotParser`, `SnapshotLoader`, and `InstrumentDefinition` |
| Duplicated NQ/ES `ComputeScore` | One `ContextScoreCalculator` plus an instrument profile |
| Crossings, proximity, 0DTE, IVR, term, skew, VIX, macro, flow, and data alerts | Pure `AlertEvaluator` decisions |
| Data-quality banners and stale checks | `HealthEvaluator` and health alert decisions |
| Intraday snapshot discovery | `ReplayIndex` |
| `AddAlert`, sounds, banners, panels, chart drawing, and replay UI | Deferred host effects; not in the portable core |

The score preserves the legacy ordering: wall position, gamma flip, gamma zone,
DEX pull, skew, term, afternoon 0DTE pin, attenuation, clamp, and bucket/tag.
Blocking order is VIX extreme, active macro blackout, imminent macro event, and
data-quality error. Ordered reason text is part of the tested result.

## NQ/ES golden parity

The constants below were derived line-by-line from the legacy NQ and ES context
score implementations and the committed fixtures, not from the new output.

| Evidence | NQ | ES |
|---|---:|---:|
| Input fixture | `full_levels_NQ_golden.json` | `full_levels_ES_golden.json` |
| Instrument configuration | `InstrumentDefinitions.Nq` | `InstrumentDefinitions.Es` |
| Fixed evaluation time | `2026-05-01 16:00Z` | `2026-05-01 20:00Z` |
| Parsed spot | 205 | 5590 |
| Gamma flip | 150 | 5675 |
| Structural call / put walls | 210 / 90 | 5760 / 5580 |
| Intraday call / put walls | 200 / 100 | 5750 / 5600 |
| cTrans / pTrans | 160 / 140 | 5700 / 5650 |
| D+ / D- | 210 / 125 | 5720 / 5585 |
| Legacy contribution evidence | `+30 +15 +20 +12` | `-30 -15 -20 -13 -10 -5 +5` |
| Context score | **77** | **-88** |
| Score tag | `BULLISH HIGH` | `BEARISH HIGH` |
| Blocking result | none | none |
| Parsed/evaluated health | `Healthy` | `Healthy` |
| Schema behavior | `1.0` accepted | `1.0` accepted |

The NQ ordered reasons are
`CW broke • GF+ • squeeze+ • D+ pull`. The ES ordered reasons are
`PW broke • GF- • squeeze- • D- pull • skew>5vp • term-back • 0DTE pin`.
Golden tests fail if these values, tags, blocking results, or reason ordering
change.

## Preserved legacy ambiguities

- The wall formula is `(0.5 - ratio) * 60`. Inside the wall range it trends
  from positive near the put wall to negative near the call wall, but strictly
  below the put wall is `-30` and strictly above the call wall is `+30`. Those
  boundary discontinuities are preserved and characterized by tests.
- The score's afternoon pin condition actually uses inclusive UTC hours
  `18..21`, despite a narrower legacy comment. The executable condition wins.
- The charm helper uses UTC hours `19` and `20` only. That host-independent DST
  approximation is preserved.
- Attenuation uses legacy `double` factors `0.6`, `0.7`, then `0.5` followed by
  `Math.Round`; the wall, gamma-flip, and DEX calculations use `decimal`.
- NQ and ES score and alert conditions are equivalent in the inspected legacy
  source. Instrument differences are therefore configuration/data selection,
  not duplicated algorithms.

No parity claim is made for visual rendering, host alerts/cooldowns, refresh
orchestration, or replay UI; those behaviors were not extracted in Phase 3.

## Verification

From the repository root:

```bash
dotnet restore tests/OFK.Gex.Core.Tests/OFK.Gex.Core.Tests.csproj --nologo
dotnet build src/OFK.Gex.Core/OFK.Gex.Core.csproj \
  --configuration Release --no-restore --nologo
dotnet test tests/OFK.Gex.Core.Tests/OFK.Gex.Core.Tests.csproj \
  --configuration Release --no-restore --nologo

PYTHONPYCACHEPREFIX=/private/tmp/ofk-phase3-pycache \
  .venv/bin/python -m pytest -p no:cacheprovider OFK_GEX_Pipeline/tests

./scripts/build_atas_x_probe.sh
git diff --check
```

The test project includes separate filters for the NQ golden, ES golden,
loading/failure, health, alert, and replay suites so each acceptance area can be
run independently.
