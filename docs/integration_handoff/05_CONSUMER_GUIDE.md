# 05 — Consumer Guide: integrating GEX Levels in a C# project

## Minimum C# code to read the JSON

```csharp
using System;
using System.IO;
using System.Text.Json;

public static class GexReader
{
    public static JsonDocument ReadLatest(string instrument)
    {
        // instrument = "NQ" or "ES"
        string dataDir = Environment.GetEnvironmentVariable("GEX_DATA_DIR")
            ?? @"C:\OFK_Atas_GEX\OFK_GEX_Pipeline\data";

        string path = Path.Combine(dataDir, $"full_levels_{instrument}.json");

        if (!File.Exists(path))
            throw new FileNotFoundException($"GEX JSON not found: {path}");

        string json = File.ReadAllText(path);
        return JsonDocument.Parse(json);
    }
}
```

### Basic usage

```csharp
using var doc = GexReader.ReadLatest("NQ");
var root = doc.RootElement;

double gammaFlip     = root.GetProperty("gamma_flip").GetDouble();
double callWall      = root.GetProperty("call_wall").GetDouble();
double putWall       = root.GetProperty("put_wall").GetDouble();
double callWallID    = root.GetProperty("call_wall_intraday_nq").GetDouble();
double putWallID     = root.GetProperty("put_wall_intraday_nq").GetDouble();
double spotNq        = root.GetProperty("spot_nq").GetDouble();
string dataQuality   = root.GetProperty("data_quality").GetString() ?? "unknown";
string tradeDate     = root.GetProperty("trade_date").GetString() ?? "";
int    gexRegime     = root.GetProperty("gex_regime").GetInt32();
```

### Safe read of an optional field

```csharp
double GetOptionalDouble(JsonElement root, string key, double fallback = 0)
{
    if (root.TryGetProperty(key, out var prop) && prop.ValueKind == JsonValueKind.Number)
        return prop.GetDouble();
    return fallback;
}

string GetOptionalString(JsonElement root, string key, string fallback = "")
{
    if (root.TryGetProperty(key, out var prop) && prop.ValueKind == JsonValueKind.String)
        return prop.GetString() ?? fallback;
    return fallback;
}

// Usage
double dexPlus = GetOptionalDouble(root, "dex_plus_intraday_nq");
string vixRegime = GetOptionalString(root, "vix_regime", "unknown");
```

### Reading a nested object (IV Rank)

```csharp
double ivr = 0;
string ivrStatus = "insufficient";
if (root.TryGetProperty("iv_rank_intraday", out var ivrProp)
    && ivrProp.ValueKind == JsonValueKind.Object)
{
    ivr = GetOptionalDouble(ivrProp, "ivr");
    ivrStatus = GetOptionalString(ivrProp, "status", "insufficient");
}
```

---

## Fallback logic

### If today's file does not exist

The `full_levels_NQ.json` file is always the same file — it is overwritten, never recreated with a date-stamped name. So "today's file does not exist" = "the file was never generated".

```csharp
if (!File.Exists(path))
{
    // Option A: error — pipeline never ran
    throw new InvalidOperationException("GEX pipeline never ran. Run run_morning_NQ.py first.");

    // Option B: look for yesterday's snapshot in history/
    // (not recommended because intraday levels will be obsolete)
}
```

### If the file exists but is stale

```csharp
var lastWrite = File.GetLastWriteTime(path);
var age = DateTime.Now - lastWrite;

if (age.TotalMinutes > 15 && IsRTH())
{
    // The intraday loop should refresh every 5 min.
    // If > 15 min → the loop is probably stopped.
    LogWarning($"GEX data stale ({age.TotalMinutes:F0} min). Intraday loop stopped?");
    // Continue with existing data — it is still usable.
}
```

### If the data is partial

```csharp
string quality = GetOptionalString(root, "data_quality", "unknown");

switch (quality)
{
    case "ok":
        // All sources available
        break;
    case "partial":
        // Some fields at 0. Check each field before use.
        if (GetOptionalDouble(root, "call_wall_intraday_nq") == 0)
            LogWarning("CBOE data missing — intraday walls unavailable");
        break;
    case "error":
        // Corrupt data. Do not use.
        LogError("GEX data error — skipping");
        return;
}
```

---

## Freshness monitoring

### Pattern: internal cache with periodic refresh

```csharp
public class GexCache
{
    private readonly string _jsonPath;
    private readonly int _refreshSeconds;
    private DateTime _lastCheck = DateTime.MinValue;
    private DateTime _lastFileWrite = DateTime.MinValue;
    private JsonDocument? _cached;
    private readonly object _lock = new();

    public GexCache(string jsonPath, int refreshSeconds = 300)
    {
        _jsonPath = jsonPath;
        _refreshSeconds = refreshSeconds;
    }

    public JsonDocument? GetLevels()
    {
        lock (_lock)
        {
            if ((DateTime.Now - _lastCheck).TotalSeconds < _refreshSeconds)
                return _cached;

            _lastCheck = DateTime.Now;

            if (!File.Exists(_jsonPath))
                return _cached;  // keep the old one

            var fileWrite = File.GetLastWriteTime(_jsonPath);
            if (fileWrite == _lastFileWrite)
                return _cached;  // file unchanged

            try
            {
                _cached?.Dispose();
                string json = File.ReadAllText(_jsonPath);
                _cached = JsonDocument.Parse(json);
                _lastFileWrite = fileWrite;
            }
            catch (Exception ex)
            {
                // Concurrent read during write?
                // Keep the old cache, retry next cycle.
                LogWarning($"GEX JSON parse error (will retry): {ex.Message}");
            }

            return _cached;
        }
    }
}
```

---

## Frequency recommendations

| Context | Reread frequency | Rationale |
|---------|------------------|-----------|
| **On-chart indicator** | 5 min (or on `mtime` change) | The pipeline writes every 5 min. Reading more often is pointless. |
| **Context Score** | 5 min | Same reason. The score only changes when the JSON changes. |
| **WPF panel** | On open + manual button | No polling needed — user triggers refresh. |
| **Alerts** | 5 min | Check `data_quality` and freshness each cycle. |
| **Backtesting** | One read per snapshot | Historical snapshots do not change. |

**Do NOT reread the file on every tick.** The JSON is 15-25 KB and requires full parsing. At 4 ticks/sec on NQ, that would be 350,000 reads/day for identical data.

---

## Concrete examples

### "Is the current price above the Gamma Flip?"

```csharp
using var doc = GexReader.ReadLatest("NQ");
var root = doc.RootElement;

double gammaFlip = root.GetProperty("gamma_flip").GetDouble();
decimal currentPrice = GetCandle(CurrentBar).Close;  // or any live price source

bool isAboveGammaFlip = (double)currentPrice > gammaFlip;
// true → positive gamma → dealers stabilize → range-bound
// false → negative gamma → dealers amplify → trend possible
```

### "Which gamma zone is the price in?"

```csharp
double cw = GetOptionalDouble(root, "call_wall_intraday_nq");
double pw = GetOptionalDouble(root, "put_wall_intraday_nq");
double ct = GetOptionalDouble(root, "c_trans_intraday_nq");
double pt = GetOptionalDouble(root, "p_trans_intraday_nq");
double price = (double)currentPrice;

string zone;
if (price > cw)        zone = "SQUEEZE+";        // very bullish, breakout
else if (price >= ct)  zone = "POSITIVE_GAMMA";  // range, mean-reversion
else if (price >= pt)  zone = "TRANSITION";      // neutral
else if (price >= pw)  zone = "NEGATIVE_GAMMA";  // trend, volatile
else                   zone = "SQUEEZE-";        // very bearish, crash
```

### "Is this a macro risk day?"

```csharp
bool inBlackout = false;
if (root.TryGetProperty("macro_in_blackout", out var mb))
    inBlackout = mb.GetBoolean();

int minutesToNext = 999;
if (root.TryGetProperty("macro_minutes_to_next", out var mtn)
    && mtn.ValueKind == JsonValueKind.Number)
    minutesToNext = mtn.GetInt32();

if (inBlackout || minutesToNext <= 30)
{
    // Do not take a position — imminent macro event
}
```

### "Is VIX in panic mode?"

```csharp
string vixRegime = GetOptionalString(root, "vix_regime", "unknown");
double vix = GetOptionalDouble(root, "vix");

bool isPanic = vixRegime == "extreme" || vix > 28;
bool isElevated = vixRegime == "elevated" || (vix > 20 && vix <= 28);
```

### "What is the expected range today?"

```csharp
double rangeLow  = root.GetProperty("range_low_nq").GetDouble();
double rangeHigh = root.GetProperty("range_high_nq").GetDouble();
double emPts     = root.GetProperty("expected_move_nq").GetDouble();

// rangeLow / rangeHigh = spot ± expected move
// emPts = expected move in NQ points (e.g. 280 pts)
```

---

## Quick reference: most-used fields for scalping

| Need | JSON field | Type |
|------|------------|------|
| Main support | `put_wall_intraday_nq` | float |
| Main resistance | `call_wall_intraday_nq` | float |
| Gamma flip (regime) | `gamma_flip` | float |
| Current gamma zone | `c_trans_intraday_nq` + `p_trans_intraday_nq` | float |
| D+ magnet | `dex_plus_intraday_nq` | float |
| D- magnet | `dex_minus_intraday_nq` | float |
| 0DTE pinning | `pin_strike_0dte_nq` | float |
| Expected move range | `range_low_nq` / `range_high_nq` | float |
| Gamma regime | `gex_regime` | int (1/-1) |
| VIX | `vix` + `vix_regime` | float + string |
| Macro blackout | `macro_in_blackout` | bool |
| Freshness | `data_quality` + `last_update_utc` | string |
