using System.Collections.ObjectModel;
using System.Globalization;
using OFK.Gex.Core.Health;

namespace OFK.Gex.Core.Alerts;

public enum AlertFamily
{
    GammaFlipCrossing,
    WallCrossing,
    TransitionCrossing,
    PredictiveProximity,
    Pin0Dte,
    Charm0Dte,
    IvrExtreme,
    TermBackwardation,
    SkewExtreme,
    VixRegime,
    MacroBlackout,
    VolumeFlow,
    DataHealth,
}

public sealed record AlertDecision(string Key, AlertFamily Family, string Message);

/// <summary>
/// All nullable market fields needed by the legacy alert conditions. The
/// adapter is responsible for mapping a parsed snapshot to this record.
/// </summary>
public sealed record AlertEvaluationInput
{
    public string Symbol { get; init; } = "NQ";

    public decimal? PreviousClose { get; init; }

    public decimal? CurrentClose { get; init; }

    public decimal TickSize { get; init; } = 0.25m;

    public decimal? GammaFlip { get; init; }

    public decimal? CallWallIntraday { get; init; }

    public decimal? PutWallIntraday { get; init; }

    public decimal? CTransIntraday { get; init; }

    public decimal? PTransIntraday { get; init; }

    public decimal? PinStrike0Dte { get; init; }

    public decimal? CharmMagnet0Dte { get; init; }

    public decimal? IvRankIntraday { get; init; }

    public string? IvRankIntradayStatus { get; init; }

    public decimal? TermIntradaySlope { get; init; }

    public decimal? Skew25dIntraday { get; init; }

    public string? PreviousVixRegime { get; init; }

    public string? VixRegime { get; init; }

    public decimal? Vix { get; init; }

    public decimal? VixDayOverDayChange { get; init; }

    public decimal? GexExtension1 { get; init; }

    public bool MacroInBlackout { get; init; }

    public string? MacroNextEventTitle { get; init; }

    public int? MacroMinutesToNext { get; init; }

    public HealthResult? Health { get; init; }

    public bool IntradayLoopRunning { get; init; }

    public IReadOnlyDictionary<string, bool>? ApproachStates { get; init; }
}

public sealed record AlertOptions
{
    public bool CrossGammaFlip { get; init; } = true;

    public bool CrossWalls { get; init; } = true;

    public bool CrossTransitions { get; init; } = true;

    public bool PredictiveAlerts { get; init; } = true;

    public bool Pin0Dte { get; init; } = true;

    public bool CharmMagnet { get; init; } = true;

    public bool IvrExtreme { get; init; } = true;

    public bool TermBackwardation { get; init; } = true;

    public bool SkewExtreme { get; init; } = true;

    public bool VixRegimeChange { get; init; } = true;

    public bool MacroBlackout { get; init; } = true;

    public bool VolumeFlowBreach { get; init; } = true;

    public bool DataHealth { get; init; } = true;

    public int ProximityTicks { get; init; } = 5;

    public int PredictiveProximityTicks { get; init; } = 10;

    /// <summary>
    /// Legacy only emits stale alerts while its intraday loop is active.
    /// Consumers that provide their own refresh lifecycle can disable this.
    /// </summary>
    public bool RequireIntradayLoopForStaleAlert { get; init; } = true;
}

public sealed record AlertEvaluationResult(
    IReadOnlyList<AlertDecision> Decisions,
    IReadOnlyDictionary<string, bool> NextApproachStates)
{
    /// <summary>
    /// State the caller should provide as PreviousVixRegime on the next
    /// evaluation. The evaluator itself remains stateless.
    /// </summary>
    public string? NextVixRegime { get; init; }
}

public sealed record ApproachTransition(bool ShouldAlert, bool IsInZone, int? DistanceTicks);

/// <summary>
/// Pure alert-condition extraction. This type intentionally owns no cooldown,
/// sound, banner, UI, logging, or persistence behavior.
/// </summary>
public static class AlertEvaluator
{
    public static AlertEvaluationResult Evaluate(
        MarketSnapshot snapshot,
        decimal? previousClose,
        decimal? currentClose,
        DateTimeOffset now,
        AlertOptions? options = null,
        HealthResult? health = null,
        string? previousVixRegime = null,
        IReadOnlyDictionary<string, bool>? approachStates = null,
        bool intradayLoopRunning = false)
    {
        ArgumentNullException.ThrowIfNull(snapshot);
        return snapshot.EvaluateAlerts(
            previousClose,
            currentClose,
            now,
            options,
            health,
            previousVixRegime,
            approachStates,
            intradayLoopRunning);
    }

    public static AlertEvaluationResult Evaluate(
        AlertEvaluationInput input,
        DateTimeOffset now,
        AlertOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(input);
        options ??= new AlertOptions();

        var symbol = NormalizeSymbol(input.Symbol);
        var decisions = new List<AlertDecision>();
        var approachStates = input.ApproachStates is null
            ? new Dictionary<string, bool>(StringComparer.Ordinal)
            : new Dictionary<string, bool>(input.ApproachStates, StringComparer.Ordinal);

        if (input.PreviousClose is not null && input.CurrentClose is not null)
        {
            var previous = input.PreviousClose.Value;
            var current = input.CurrentClose.Value;

            if (options.CrossGammaFlip && Crossed(previous, current, input.GammaFlip))
            {
                decisions.Add(new AlertDecision(
                    "gamma_flip",
                    AlertFamily.GammaFlipCrossing,
                    $"{symbol} {current:F0} crosses Gamma Flip {input.GammaFlip!.Value:F0} — gamma regime change"));
            }

            if (options.CrossWalls)
            {
                AddCrossing(decisions, previous, current, input.CallWallIntraday,
                    "call_wall_id", AlertFamily.WallCrossing,
                    $"{symbol} crosses Call Wall intraday {FormatLevel(input.CallWallIntraday)}");
                AddCrossing(decisions, previous, current, input.PutWallIntraday,
                    "put_wall_id", AlertFamily.WallCrossing,
                    $"{symbol} crosses Put Wall intraday {FormatLevel(input.PutWallIntraday)}");
            }

            if (options.CrossTransitions)
            {
                AddCrossing(decisions, previous, current, input.CTransIntraday,
                    "c_trans", AlertFamily.TransitionCrossing,
                    $"{symbol} crosses cTrans {FormatLevel(input.CTransIntraday)} — gamma zone change");
                AddCrossing(decisions, previous, current, input.PTransIntraday,
                    "p_trans", AlertFamily.TransitionCrossing,
                    $"{symbol} crosses pTrans {FormatLevel(input.PTransIntraday)} — gamma zone change");
            }

            if (options.VolumeFlowBreach && Crossed(previous, current, input.GexExtension1))
            {
                decisions.Add(new AlertDecision(
                    "vol_flow",
                    AlertFamily.VolumeFlow,
                    $"{symbol} crosses GEX ext-1 {input.GexExtension1!.Value:F0} — directional flow"));
            }

            if (options.PredictiveAlerts)
            {
                if (options.CrossGammaFlip)
                {
                    AddApproach(decisions, approachStates, "gamma_flip", "Gamma Flip",
                        symbol, current, input.GammaFlip, input.TickSize, options.PredictiveProximityTicks);
                }

                if (options.CrossWalls)
                {
                    AddApproach(decisions, approachStates, "call_wall_id", "Call Wall ID",
                        symbol, current, input.CallWallIntraday, input.TickSize, options.PredictiveProximityTicks);
                    AddApproach(decisions, approachStates, "put_wall_id", "Put Wall ID",
                        symbol, current, input.PutWallIntraday, input.TickSize, options.PredictiveProximityTicks);
                }

                if (options.CrossTransitions)
                {
                    AddApproach(decisions, approachStates, "c_trans", "cTrans",
                        symbol, current, input.CTransIntraday, input.TickSize, options.PredictiveProximityTicks);
                    AddApproach(decisions, approachStates, "p_trans", "pTrans",
                        symbol, current, input.PTransIntraday, input.TickSize, options.PredictiveProximityTicks);
                }

                if (options.VolumeFlowBreach)
                {
                    AddApproach(decisions, approachStates, "vol_flow", "GEX ext-1",
                        symbol, current, input.GexExtension1, input.TickSize, options.PredictiveProximityTicks);
                }
            }

            if (options.Pin0Dte &&
                IsWithinProximity(current, input.PinStrike0Dte, input.TickSize, options.ProximityTicks))
            {
                decisions.Add(new AlertDecision(
                    "pin_0dte",
                    AlertFamily.Pin0Dte,
                    $"{symbol} near Pin Strike 0DTE {input.PinStrike0Dte!.Value:F0} (±{options.ProximityTicks}t)"));
            }

            if (options.CharmMagnet &&
                IsLastHourRth(now) &&
                IsWithinProximity(current, input.CharmMagnet0Dte, input.TickSize, options.ProximityTicks * 3))
            {
                decisions.Add(new AlertDecision(
                    "charm_magnet",
                    AlertFamily.Charm0Dte,
                    $"{symbol} approaching Charm Magnet 0DTE {input.CharmMagnet0Dte!.Value:F0} (last hour)"));
            }
        }

        if (options.IvrExtreme &&
            input.IvRankIntraday is >= 0m &&
            HasUsableIvrStatus(input.IvRankIntradayStatus))
        {
            if (input.IvRankIntraday > 90m)
            {
                decisions.Add(new AlertDecision(
                    "ivr_high",
                    AlertFamily.IvrExtreme,
                    $"IVR very high {input.IvRankIntraday.Value:F0}% — high vol, widen stops"));
            }
            else if (input.IvRankIntraday < 10m)
            {
                decisions.Add(new AlertDecision(
                    "ivr_low",
                    AlertFamily.IvrExtreme,
                    $"IVR very low {input.IvRankIntraday.Value:F0}% — compressed vol, tight range"));
            }
        }

        if (options.TermBackwardation && input.TermIntradaySlope is > 0.01m)
        {
            decisions.Add(new AlertDecision(
                "term_back",
                AlertFamily.TermBackwardation,
                $"Acute term backwardation (slope +{input.TermIntradaySlope.Value * 100m:F1}vp) — STRESS, breakouts"));
        }

        if (options.SkewExtreme && input.Skew25dIntraday is > 0.05m)
        {
            decisions.Add(new AlertDecision(
                "skew_high",
                AlertFamily.SkewExtreme,
                $"Explosive Skew 25Δ {input.Skew25dIntraday.Value * 100m:F1}vp — aggressive put protection"));
        }

        if (options.VixRegimeChange &&
            !string.IsNullOrEmpty(input.VixRegime) &&
            !string.Equals(input.PreviousVixRegime, input.VixRegime, StringComparison.Ordinal) &&
            string.Equals(input.VixRegime, "extreme", StringComparison.Ordinal))
        {
            decisions.Add(new AlertDecision(
                "vix_extreme",
                AlertFamily.VixRegime,
                $"VIX EXTREME regime ({input.Vix.GetValueOrDefault():F1}, DoD {FormatSigned(input.VixDayOverDayChange)}) — avoid scalping"));
        }

        if (options.MacroBlackout && input.MacroInBlackout)
        {
            decisions.Add(new AlertDecision(
                "macro_blackout",
                AlertFamily.MacroBlackout,
                "Macro blackout IN PROGRESS — STOP scalping"));
        }

        if (options.MacroBlackout && input.MacroMinutesToNext is > 0 and <= 30)
        {
            decisions.Add(new AlertDecision(
                "macro_imminent",
                AlertFamily.MacroBlackout,
                $"Macro event {input.MacroNextEventTitle ?? string.Empty} in {input.MacroMinutesToNext}min — STOP scalping"));
        }

        if (options.DataHealth && input.Health is not null)
        {
            AddHealthDecision(decisions, input.Health, input.IntradayLoopRunning, options);
        }

        return new AlertEvaluationResult(
            decisions.AsReadOnly(),
            new ReadOnlyDictionary<string, bool>(approachStates))
        {
            NextVixRegime = input.VixRegime,
        };
    }

    /// <summary>
    /// Crossing matches the legacy boundary semantics: the prior value must be
    /// strictly on one side and the current value may land exactly on level.
    /// </summary>
    public static bool Crossed(decimal previous, decimal current, decimal? level) =>
        level is > 0m &&
        ((previous < level.Value && current >= level.Value) ||
         (previous > level.Value && current <= level.Value));

    public static bool IsWithinProximity(
        decimal price,
        decimal? level,
        decimal tickSize,
        int proximityTicks) =>
        level is > 0m &&
        tickSize > 0m &&
        proximityTicks > 0 &&
        Math.Abs(price - level.Value) <= proximityTicks * tickSize;

    /// <summary>
    /// Legacy RTH last-hour approximation: UTC hours 19 and 20, independent of
    /// local machine timezone.
    /// </summary>
    public static bool IsLastHourRth(DateTimeOffset now) =>
        now.UtcDateTime.Hour is 19 or 20;

    /// <summary>
    /// Stateless transition for the legacy predictive-alert hysteresis. Entry
    /// is inclusive; reset requires distance strictly greater than twice the
    /// entry threshold.
    /// </summary>
    public static ApproachTransition EvaluateApproach(
        decimal price,
        decimal? level,
        decimal tickSize,
        int proximityTicks,
        bool wasInZone)
    {
        if (level is not > 0m || tickSize <= 0m || proximityTicks <= 0)
        {
            return new ApproachTransition(false, wasInZone, null);
        }

        var distance = Math.Abs(price - level.Value);
        var entryThreshold = proximityTicks * tickSize;
        var distanceTicks = (int)(distance / tickSize);
        if (distance <= entryThreshold && !wasInZone)
        {
            return new ApproachTransition(true, true, distanceTicks);
        }

        if (distance > entryThreshold * 2m && wasInZone)
        {
            return new ApproachTransition(false, false, distanceTicks);
        }

        return new ApproachTransition(false, wasInZone, distanceTicks);
    }

    private static void AddCrossing(
        ICollection<AlertDecision> decisions,
        decimal previous,
        decimal current,
        decimal? level,
        string key,
        AlertFamily family,
        string message)
    {
        if (Crossed(previous, current, level))
        {
            decisions.Add(new AlertDecision(key, family, message));
        }
    }

    private static void AddApproach(
        ICollection<AlertDecision> decisions,
        IDictionary<string, bool> states,
        string baseKey,
        string levelLabel,
        string symbol,
        decimal price,
        decimal? level,
        decimal tickSize,
        int proximityTicks)
    {
        var key = baseKey + "_approach";
        states.TryGetValue(key, out var wasInZone);
        var transition = EvaluateApproach(price, level, tickSize, proximityTicks, wasInZone);

        if (level is > 0m)
        {
            states[key] = transition.IsInZone;
        }

        if (transition.ShouldAlert)
        {
            decisions.Add(new AlertDecision(
                key,
                AlertFamily.PredictiveProximity,
                $"{symbol} approaching {levelLabel} {level!.Value:F0} (at {transition.DistanceTicks} ticks)"));
        }
    }

    private static void AddHealthDecision(
        ICollection<AlertDecision> decisions,
        HealthResult health,
        bool intradayLoopRunning,
        AlertOptions options)
    {
        var decision = health.State switch
        {
            HealthState.Missing => new AlertDecision(
                "data_missing", AlertFamily.DataHealth, "Pipeline data file is missing."),
            HealthState.Invalid => new AlertDecision(
                "data_invalid", AlertFamily.DataHealth, "Pipeline data is invalid."),
            HealthState.SchemaMismatch => new AlertDecision(
                "schema_mismatch", AlertFamily.DataHealth, health.Reason),
            HealthState.Error => new AlertDecision(
                "data_error", AlertFamily.DataHealth, "Pipeline data ERROR — no valid levels"),
            HealthState.Partial => new AlertDecision(
                "data_partial", AlertFamily.DataHealth, "Pipeline data PARTIAL (CME or CBOE missing) — degraded quality"),
            HealthState.Stale when intradayLoopRunning || !options.RequireIntradayLoopForStaleAlert =>
                new AlertDecision(
                    "stale_data",
                    AlertFamily.DataHealth,
                    $"Intraday data frozen ({(int)(health.Age?.TotalMinutes ?? 0)}min) — check the Python process"),
            _ => null,
        };

        if (decision is not null)
        {
            decisions.Add(decision);
        }
    }

    private static bool HasUsableIvrStatus(string? value) =>
        string.Equals(value, "ok", StringComparison.Ordinal) ||
        string.Equals(value, "partial", StringComparison.Ordinal);

    private static string NormalizeSymbol(string symbol) =>
        string.IsNullOrWhiteSpace(symbol) ? "NQ" : symbol.Trim().ToUpperInvariant();

    private static string FormatLevel(decimal? value) => value?.ToString("F0", CultureInfo.InvariantCulture) ?? "0";

    private static string FormatSigned(decimal? value) =>
        value.GetValueOrDefault().ToString("+0.0;-0.0;0", CultureInfo.InvariantCulture);
}
