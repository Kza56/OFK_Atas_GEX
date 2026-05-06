# OFK_Atas_GEX — ATAS Indicators

ATAS indicators that read the GEX/options levels produced by the Python pipeline `OFK_GEX_Pipeline/`.

---

## Included indicators

| File | Display name | Description |
|---|---|---|
| `OFK_NQ_GEX_Levels.cs` | OFK NQ GEX Levels | NQ GEX/options levels (walls, gamma flip, DEX, 0DTE, IV, VIX) with WPF panel |
| `OFK_ES_GEX_Levels.cs` | OFK ES GEX Levels | Same for ES E-mini S&P500 |
| `OFK_NQ_ContextScore.cs` | OFK NQ Context Score | Directional score -100/+100 based on GEX + VIX + macro |
| `OFK_ES_ContextScore.cs` | OFK ES Context Score | Same for ES |
| `OFK_GexShared.cs` | (lib) | Shared JSON loader: `GexSnapshot`, `MetaSnapshot`, `GexLoader` |
| `OFK_ReplayWindow.cs` | (UI) | WPF intraday replay window (slider over snapshots) |

**Namespace**: `OFK_GEX`
**Assembly**: `OFK_Atas_GEX.dll`
**ATAS category**: `OFK Suite`

---

## Build

### Prerequisites
- Visual Studio 2022 or VS Code with the .NET 10 SDK
- ATAS installed (default path: `C:\Program Files (x86)\ATAS Platform`)

### Steps

**1 — Check the ATAS path in the csproj**

Open `OFK_ATAS/OFK_Atas_GEX.csproj`:
```xml
<ATASPath>C:\Program Files (x86)\ATAS Platform</ATASPath>
```

**2 — Build**
```bash
cd OFK_ATAS
dotnet build OFK_Atas_GEX.csproj -c Release
```
Produces `OFK_Atas_GEX.dll` in `bin\Release\net10.0-windows\`.

**3 — Install into ATAS**

Copy `OFK_Atas_GEX.dll` to:
```
%AppData%\ATAS\Indicators\
```

**4 — Restart ATAS**

The 4 indicators appear under **OFK Suite**:
- `OFK NQ GEX Levels`
- `OFK ES GEX Levels`
- `OFK NQ Context Score`
- `OFK ES Context Score`

---

## Python pipeline

The pipeline that produces the JSON files consumed by the indicators lives in `OFK_GEX_Pipeline/`. See `OFK_GEX_Pipeline/CLAUDE.md` for its architecture and `docs/integration_handoff/` for the output contract.

The indicators read by default from:
- `C:\Users\<user>\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline\data\full_levels_NQ.json`
- `C:\Users\<user>\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline\data\full_levels_ES.json`

The path is adjustable in each indicator's settings (group `01.Source`, parameter `JSON Path`).

---

## Documentation

- `OFK_GEX_Pipeline/GUIDE_GEX_LEVELS.md` — plain-English guide to reading the levels
- `OFK_GEX_Pipeline/CLAUDE.md` — Python pipeline architecture
- `docs/integration_handoff/` — integration contract for external consumers (7 documents)
- `CLAUDE.md` (root) — ATAS development context
