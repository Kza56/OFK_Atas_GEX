# OFK_Atas_GEX — ATAS GEX Indicators

> **Persistent project context. Never reread `bin/`, `obj/`, or large files.
> All required ATAS API info is here.**

---

## 1. Project architecture

```
OFK_Atas_GEX/
├── OFK_ATAS/                            # C# .NET 10 indicators
│   ├── OFK_NQ_GEX_Levels.cs             # NQ GEX levels (walls, flip, DEX, 0DTE, IV, VIX)
│   ├── OFK_ES_GEX_Levels.cs             # ES GEX levels
│   ├── OFK_NQ_ContextScore.cs           # -100/+100 score: GEX + VIX + macro
│   ├── OFK_ES_ContextScore.cs           # ES score
│   ├── OFK_GexShared.cs                 # GexLoader + GexSnapshot + MetaSnapshot
│   ├── OFK_ReplayWindow.cs              # WPF intraday replay window
│   └── OFK_Atas_GEX.csproj              # Builds OFK_Atas_GEX.dll
├── OFK_GEX_Pipeline/                    # Python pipeline
│   ├── *.py                             # Scrapers, fetchers, mergers
│   ├── data/                            # JSON outputs + history
│   ├── CLAUDE.md                        # Pipeline architecture
│   └── GUIDE_GEX_LEVELS.md              # Plain-English guide to levels
├── docs/integration_handoff/            # Integration contract (7 docs)
└── OFK_Atas_GEX.sln
```

**Namespace**: `OFK_GEX`
**Target**: `net10.0-windows`
**Assembly**: `bin/Release/net10.0-windows/OFK_Atas_GEX.dll`
**Deployment**: `%APPDATA%\ATAS\Indicators\OFK_Atas_GEX.dll`

---

## 2. Base pattern — ATAS indicator

```csharp
using ATAS.Indicators;
using ATAS.DataFeedsCore;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;
using DrawingColor = System.Drawing.Color;

[DisplayName("OFK - MyIndicator")]
[Category("OFK Suite")]
[Description("Short description.")]
public class OFK_MyIndicator : Indicator
{
    [Display(Name = "My Param", GroupName = "01.Main", Order = 0)]
    [Range(1, 100)]
    public int MyParam { get; set; } = 20;

    public OFK_MyIndicator() : base(true)  // true = subscribe to live events
    {
        Panel = IndicatorDataProvider.NewPanel;
        DenyToChangePanel = true;

        EnableCustomDrawing = true;
        SubscribeToDrawingEvents(DrawingLayouts.Historical | DrawingLayouts.LatestBar | DrawingLayouts.Final);

        DataSeries[0].Name = "Main";
        ((ValueDataSeries)DataSeries[0]).VisualType = VisualMode.Histogram;
        ((ValueDataSeries)DataSeries[0]).IsHidden = true;
    }

    protected override void OnCalculate(int bar, decimal value)
    {
        var candle = GetCandle(bar);
        // candle.Open / .High / .Low / .Close / .Volume
        // candle.Ask (aggressive buy volume) / candle.Bid (aggressive sell volume)
        this[bar] = candle.Ask - candle.Bid;
    }

    protected override void OnRender(RenderContext context, DrawingLayouts layout)
    {
        // GetXByBar(bar) → X coordinate
        // GetYByValue(value) → Y coordinate
        // ChartArea.Height for panel height
    }
}
```

---

## 3. ATAS lifecycle

| Method | When | Usage |
|---|---|---|
| `OnCalculate(int bar, decimal value)` | Each bar (historical + live) | Main calculation |
| `OnRender(RenderContext context, DrawingLayouts layout)` | Each redraw | Custom drawing |
| `OnInitialize()` | Init before first bar | State reset |
| `Dispose()` | Indicator removal | Cleanup (process, WPF windows) |

---

## 4. Key APIs

### Candle (via `GetCandle(bar)`)
```csharp
candle.Open / .High / .Low / .Close
candle.Volume        // total volume
candle.Ask           // aggressive buy volume
candle.Bid           // aggressive sell volume
candle.Ticks         // number of trades in the bar
candle.Time          // bar DateTime
```

### InstrumentInfo
```csharp
InstrumentInfo.TickSize    // decimal — tick size (0.25 NQ, 0.25 ES)
InstrumentInfo.Multiplier  // decimal
```

### Render coordinates
```csharp
float x = GetXByBar(bar);                // X pixel of a bar
float y = (float)GetYByValue(value);     // Y pixel of a price value
int panelH = ChartArea.Height;           // active panel height
```

---

## 5. GEX Levels architecture

### Pipeline JSON loading

All GEX indicators use `GexLoader.Load(jsonPath, "nq" or "es")` which returns `(GexSnapshot, MetaSnapshot, ok)`.

- `GexSnapshot`: all levels (walls, flip, DEX, 0DTE, IV, IVR…)
- `MetaSnapshot`: VIX + macro + data_quality + last_update_utc

### Periodic refresh

The JSON is reloaded every `RefreshMinutes` (default 5 min). The Python pipeline `run_intraday_refresh.py` rewrites it every 5 min via the panel's "Loop ON" button.

### Intraday replay

Snapshots in `OFK_GEX_Pipeline/data/history/intraday/{NQ|ES}_full_levels_YYYYMMDD_HHMM.json`. The `OFK_ReplayWindow` (WPF) lets you scrub through the day with a slider.

### Context Score

±100 score computed as gradual components relative to the PW-CW range:
- Walls position ±30 (gradient)
- Gamma Flip ±15 (gradient)
- Gamma Zone ±20
- DEX D+/D- ±15 (gradient 25% range)
- Skew 25Δ -10
- Term backwardation -5
- 0DTE Pin ±5

Blocking filters: VIX extreme, macro blackout, macro <30min, data error → score = 0.
Attenuating filters: VIX elevated ×0.6, data partial ×0.7, IVR>90 ×0.5.

---

## 6. Custom drawing / rendering

```csharp
var pen = new Pen(color, thickness);
var brush = new SolidBrush(color);

context.DrawLine(pen, x1, y1, x2, y2);
context.FillRectangle(color, rect);
context.DrawString(text, font, brush, x, y);
context.MeasureString(text, font);

var font = new RenderFont("Arial", 12);
```

**DrawingLayouts flags**:
```csharp
DrawingLayouts.Historical    // historical bars
DrawingLayouts.LatestBar     // current bar (live)
DrawingLayouts.Final         // final render (print/export)
```

---

## 7. DataSeries

```csharp
ValueDataSeries       // decimal per bar
RangeDataSeries       // range (High/Low) per bar
PaintbarsDataSeries   // color per bar

this[bar] = value;
((ValueDataSeries)DataSeries[1])[bar] = v;

((ValueDataSeries)DataSeries[0]).VisualType = VisualMode.Histogram;
// VisualMode: Line / Histogram / Hide / Dot / TriangleUp / TriangleDown
```

---

## 8. Parameter attributes

```csharp
[Display(Name = "UI Label", GroupName = "01.GroupName", Order = 10,
         Description = "Hover tooltip")]
[Range(min, max)]
public int MyParam { get; set; } = defaultValue;

// Supported types: int, double, decimal, bool, DrawingColor, enum
```

---

## 9. Known pitfalls

1. **`base(true)` in the constructor** — enables live event subscription. Without it, `OnNewTrade` does not fire.

2. **`Panel = IndicatorDataProvider.NewPanel`** — required for a separate panel. `DenyToChangePanel = true` prevents repositioning.

3. **WPF in Dispose** — close the windows (`_panel?.Close()`, `_replayWindow?.Close()`) otherwise memory leaks on reload.

4. **Intraday loop process** — `_loopProcess` as nullable `Process?`. Always `Kill(entireProcessTree: true)` + `WaitForExit(2000)` in `Dispose()`.

5. **PYTHONIOENCODING=utf-8** mandatory for the Python loop (box-drawing chars ─ ═ → crash on cp1252 by default when stdout is piped).

6. **Async stdout/stderr drain** — `BeginOutputReadLine()` + `BeginErrorReadLine()` otherwise the Windows pipe (~4KB) saturates and the Python process blocks.

7. **`null!` for WPF fields** — fields assigned in `BuildUI()` rather than the ctor: use `= null!;` to silence CS8618.

8. **`_replayMode` guard in `LoadLevels()`** — otherwise the periodic refresh overwrites replay data.

---

## 10. Build workflow

```bash
cd OFK_ATAS
dotnet build OFK_Atas_GEX.csproj -c Release
# Output: bin/Release/net10.0-windows/OFK_Atas_GEX.dll
# Copy to %APPDATA%\ATAS\Indicators\
```

---

## 11. Useful links

- `OFK_GEX_Pipeline/CLAUDE.md` — Python pipeline architecture
- `OFK_GEX_Pipeline/GUIDE_GEX_LEVELS.md` — plain-English guide to levels
- `docs/integration_handoff/` — external integration contract
