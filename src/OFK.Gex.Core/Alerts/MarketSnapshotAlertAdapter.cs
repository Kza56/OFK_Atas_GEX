using OFK.Gex.Core.Health;

namespace OFK.Gex.Core.Alerts;

/// <summary>Maps the typed market snapshot to the pure alert engine.</summary>
public static class MarketSnapshotAlertAdapter
{
    public static AlertEvaluationInput ToAlertEvaluationInput(
        this MarketSnapshot snapshot,
        decimal? previousClose,
        decimal? currentClose,
        HealthResult? health = null,
        string? previousVixRegime = null,
        IReadOnlyDictionary<string, bool>? approachStates = null,
        bool intradayLoopRunning = false)
    {
        ArgumentNullException.ThrowIfNull(snapshot);

        return new AlertEvaluationInput
        {
            Symbol = snapshot.Instrument.Code,
            PreviousClose = previousClose,
            CurrentClose = currentClose,
            TickSize = snapshot.Instrument.TickSize,
            GammaFlip = snapshot.Gex.GammaFlip,
            CallWallIntraday = snapshot.Gex.CallWallIntraday,
            PutWallIntraday = snapshot.Gex.PutWallIntraday,
            CTransIntraday = snapshot.Gex.CTransIntraday,
            PTransIntraday = snapshot.Gex.PTransIntraday,
            PinStrike0Dte = snapshot.Gex.PinStrike0DTE,
            CharmMagnet0Dte = snapshot.Gex.CharmMagnet0DTE,
            IvRankIntraday = snapshot.Gex.IvRankIntraday,
            IvRankIntradayStatus = snapshot.Gex.IvRankIntradayStatus,
            TermIntradaySlope = snapshot.Gex.TermIntradaySlope,
            Skew25dIntraday = snapshot.Gex.Skew25dIntraday,
            PreviousVixRegime = previousVixRegime,
            VixRegime = snapshot.Meta.VixRegime,
            Vix = snapshot.Meta.Vix,
            VixDayOverDayChange = snapshot.Meta.VixDodChange,
            GexExtension1 = snapshot.Gex.GexExt1,
            MacroInBlackout = snapshot.Meta.MacroInBlackout == true,
            MacroNextEventTitle = snapshot.Meta.MacroNextEventTitle,
            MacroMinutesToNext = snapshot.Meta.MacroMinutesToNext,
            Health = health,
            IntradayLoopRunning = intradayLoopRunning,
            ApproachStates = approachStates,
        };
    }

    public static AlertEvaluationResult EvaluateAlerts(
        this MarketSnapshot snapshot,
        decimal? previousClose,
        decimal? currentClose,
        DateTimeOffset now,
        AlertOptions? options = null,
        HealthResult? health = null,
        string? previousVixRegime = null,
        IReadOnlyDictionary<string, bool>? approachStates = null,
        bool intradayLoopRunning = false) =>
        AlertEvaluator.Evaluate(
            snapshot.ToAlertEvaluationInput(
                previousClose,
                currentClose,
                health,
                previousVixRegime,
                approachStates,
                intradayLoopRunning),
            now,
            options);
}
