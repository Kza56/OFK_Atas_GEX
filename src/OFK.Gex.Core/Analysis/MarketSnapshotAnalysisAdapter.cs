using OFK.Gex.Core.Health;

namespace OFK.Gex.Core.Analysis;

/// <summary>
/// Bridges the typed loader contract to the pure context-score input without
/// coupling the parser to analysis policy.
/// </summary>
public static class MarketSnapshotAnalysisAdapter
{
    public static ContextScoreInput ToContextScoreInput(this MarketSnapshot snapshot)
    {
        ArgumentNullException.ThrowIfNull(snapshot);

        return new ContextScoreInput
        {
            HasLevels = true,
            HasMetadata = true,
            Spot = snapshot.Gex.Spot,
            GammaFlip = snapshot.Gex.GammaFlip,
            CallWallIntraday = snapshot.Gex.CallWallIntraday,
            PutWallIntraday = snapshot.Gex.PutWallIntraday,
            CTransIntraday = snapshot.Gex.CTransIntraday,
            PTransIntraday = snapshot.Gex.PTransIntraday,
            DexPlusIntraday = snapshot.Gex.DexPlusIntraday,
            DexMinusIntraday = snapshot.Gex.DexMinusIntraday,
            Skew25dIntraday = snapshot.Gex.Skew25dIntraday,
            TermIntradaySlope = snapshot.Gex.TermIntradaySlope,
            PinStrike0Dte = snapshot.Gex.PinStrike0DTE,
            IvRankIntraday = snapshot.Gex.IvRankIntraday,
            Vix = snapshot.Meta.Vix,
            VixRegime = snapshot.Meta.VixRegime,
            MacroInBlackout = snapshot.Meta.MacroInBlackout == true,
            MacroNextEventTitle = snapshot.Meta.MacroNextEventTitle,
            MacroMinutesToNext = snapshot.Meta.MacroMinutesToNext,
            DataQuality = snapshot.Meta.DataQuality,
        };
    }

    public static ContextScoreResult CalculateContextScore(
        this MarketSnapshot snapshot,
        DateTimeOffset now,
        bool enableBlockingFilters = true) =>
        ContextScoreCalculator.Calculate(
            snapshot.ToContextScoreInput(),
            ContextScoreProfile.ForSymbol(snapshot.Instrument.Code),
            now,
            enableBlockingFilters);

    /// <summary>
    /// Produces health input from parsed metadata and portable source metadata.
    /// Loader parse/schema diagnostics still decide SourceExists and
    /// JsonIsValid; this adapter supplies the typed values consistently.
    /// </summary>
    public static HealthEvaluationInput ToHealthEvaluationInput(
        this MarketSnapshot snapshot,
        SnapshotSource source,
        bool sourceExists = true,
        bool jsonIsValid = true,
        string expectedSchemaVersion = "1.0",
        TimeSpan? staleAfter = null,
        TimeSpan? futureTolerance = null)
    {
        ArgumentNullException.ThrowIfNull(snapshot);
        ArgumentNullException.ThrowIfNull(source);

        return new HealthEvaluationInput
        {
            SourceExists = sourceExists,
            JsonIsValid = jsonIsValid,
            ExpectedSchemaVersion = expectedSchemaVersion,
            SchemaVersion = snapshot.Meta.JsonSchemaVersion,
            DataQuality = snapshot.Meta.DataQuality,
            LastUpdateUtc = snapshot.Meta.LastUpdateUtc,
            FileLastWriteUtc = source.LastWriteTimeUtc,
            StaleAfter = staleAfter ?? TimeSpan.FromMinutes(10),
            FutureTolerance = futureTolerance ?? TimeSpan.FromMinutes(5),
        };
    }
}
