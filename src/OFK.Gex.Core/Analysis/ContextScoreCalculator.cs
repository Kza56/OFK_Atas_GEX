namespace OFK.Gex.Core.Analysis;

/// <summary>
/// Symbol-specific settings for the otherwise shared context-score algorithm.
/// NQ and ES intentionally use the same values in the legacy indicators.
/// </summary>
public sealed record ContextScoreProfile(
    string Symbol,
    int PinStartHourUtc = 18,
    int PinEndHourUtc = 21)
{
    public static ContextScoreProfile Nq { get; } = new("NQ");

    public static ContextScoreProfile Es { get; } = new("ES");

    public static ContextScoreProfile ForSymbol(string symbol) =>
        string.Equals(symbol, "NQ", StringComparison.OrdinalIgnoreCase)
            ? Nq
            : string.Equals(symbol, "ES", StringComparison.OrdinalIgnoreCase)
                ? Es
                : throw new ArgumentException("Only NQ and ES are supported.", nameof(symbol));
}

/// <summary>
/// Nullable, platform-neutral inputs consumed by the legacy context score.
/// Missing values remain distinct from legitimate zero values.
/// </summary>
public sealed record ContextScoreInput
{
    public bool HasLevels { get; init; } = true;

    public bool HasMetadata { get; init; } = true;

    public decimal? Spot { get; init; }

    public decimal? GammaFlip { get; init; }

    public decimal? CallWallIntraday { get; init; }

    public decimal? PutWallIntraday { get; init; }

    public decimal? CTransIntraday { get; init; }

    public decimal? PTransIntraday { get; init; }

    public decimal? DexPlusIntraday { get; init; }

    public decimal? DexMinusIntraday { get; init; }

    public decimal? Skew25dIntraday { get; init; }

    public decimal? TermIntradaySlope { get; init; }

    public decimal? PinStrike0Dte { get; init; }

    public decimal? IvRankIntraday { get; init; }

    public decimal? Vix { get; init; }

    public string? VixRegime { get; init; }

    public bool MacroInBlackout { get; init; }

    public string? MacroNextEventTitle { get; init; }

    public int? MacroMinutesToNext { get; init; }

    public string? DataQuality { get; init; }
}

public enum ContextScoreBucket
{
    BullishHigh,
    Bullish,
    Neutral,
    Bearish,
    BearishHigh,
    Data,
    Blocked,
}

public sealed record ContextScoreResult(
    int Score,
    string Tag,
    ContextScoreBucket Bucket,
    IReadOnlyList<string> Reasons,
    string? BlockingReason = null)
{
    public bool IsBlocked => BlockingReason is not null;

    public string ReasonText => Reasons.Count == 0 ? "neutral" : string.Join(" • ", Reasons);
}

/// <summary>
/// Pure extraction of ComputeScore from OFK_NQ_ContextScore and
/// OFK_ES_ContextScore. The caller supplies UTC time to keep replay and tests
/// deterministic.
/// </summary>
public static class ContextScoreCalculator
{
    public static ContextScoreResult Calculate(
        MarketSnapshot snapshot,
        DateTimeOffset now,
        bool enableBlockingFilters = true)
    {
        ArgumentNullException.ThrowIfNull(snapshot);
        return snapshot.CalculateContextScore(now, enableBlockingFilters);
    }

    public static ContextScoreResult Calculate(
        ContextScoreInput input,
        ContextScoreProfile profile,
        DateTimeOffset now,
        bool enableBlockingFilters = true)
    {
        ArgumentNullException.ThrowIfNull(input);
        ArgumentNullException.ThrowIfNull(profile);

        if (!input.HasLevels || input.Spot is null)
        {
            return new ContextScoreResult(
                0,
                "DATA",
                ContextScoreBucket.Data,
                ["No data"]);
        }

        if (enableBlockingFilters && input.HasMetadata)
        {
            if (EqualsLegacyValue(input.VixRegime, "extreme"))
            {
                var reason = $"VIX EXTREME ({input.Vix.GetValueOrDefault():F1}) — STOP";
                return Blocked(reason);
            }

            if (input.MacroInBlackout)
            {
                return Blocked("Macro blackout IN PROGRESS");
            }

            if (input.MacroMinutesToNext is > 0 and <= 30)
            {
                var title = string.IsNullOrEmpty(input.MacroNextEventTitle)
                    ? "Macro"
                    : input.MacroNextEventTitle;
                return Blocked($"{title} in {input.MacroMinutesToNext}min");
            }

            if (EqualsLegacyValue(input.DataQuality, "error"))
            {
                return Blocked("Data ERROR");
            }
        }

        var spot = input.Spot.Value;
        var score = 0;
        var reasons = new List<string>();

        var callWall = input.CallWallIntraday.GetValueOrDefault();
        var putWall = input.PutWallIntraday.GetValueOrDefault();
        var hasRange = callWall > putWall && putWall > 0m;
        var range = hasRange ? callWall - putWall : 0m;

        // 1. Position in the intraday put-wall/call-wall range (±30).
        if (hasRange)
        {
            var ratio = (spot - putWall) / range;
            int wallScore;
            if (ratio < 0m)
            {
                wallScore = -30;
                reasons.Add("PW broke");
            }
            else if (ratio > 1m)
            {
                wallScore = 30;
                reasons.Add("CW broke");
            }
            else
            {
                wallScore = (int)Math.Round((0.5m - ratio) * 60m);
                if (wallScore >= 15)
                {
                    reasons.Add("PW zone");
                }
                else if (wallScore <= -15)
                {
                    reasons.Add("CW zone");
                }
            }

            score += wallScore;
        }

        // 2. Gamma-flip distance (±15).
        if (input.GammaFlip is > 0m && hasRange)
        {
            var normalized = (spot - input.GammaFlip.Value) / range;
            normalized = Math.Max(-0.5m, Math.Min(0.5m, normalized));
            var gammaFlipScore = (int)Math.Round(normalized * 30m);
            score += gammaFlipScore;
            if (gammaFlipScore >= 5)
            {
                reasons.Add("GF+");
            }
            else if (gammaFlipScore <= -5)
            {
                reasons.Add("GF-");
            }
        }

        // 3. Gamma zone (±20).
        if (hasRange)
        {
            var cTrans = input.CTransIntraday.GetValueOrDefault();
            var pTrans = input.PTransIntraday.GetValueOrDefault();
            if (spot > callWall)
            {
                score += 20;
                reasons.Add("squeeze+");
            }
            else if (cTrans > 0m && spot >= cTrans)
            {
                score += 5;
                reasons.Add("pos-gamma");
            }
            else if (pTrans > 0m && spot >= pTrans)
            {
                // The transition zone intentionally contributes zero.
            }
            else if (spot >= putWall)
            {
                score -= 5;
                reasons.Add("neg-gamma");
            }
            else
            {
                score -= 20;
                reasons.Add("squeeze-");
            }
        }

        // 4. DEX D+/D- pull within 25% of the wall range (±15 each).
        if (hasRange)
        {
            var dexZone = range * 0.25m;
            if (input.DexPlusIntraday is > 0m)
            {
                var distance = input.DexPlusIntraday.Value - spot;
                if (distance > 0m && distance < dexZone)
                {
                    var dexScore = (int)Math.Round((1m - distance / dexZone) * 15m);
                    score += dexScore;
                    if (dexScore >= 5)
                    {
                        reasons.Add("D+ pull");
                    }
                }
            }

            if (input.DexMinusIntraday is > 0m)
            {
                var distance = spot - input.DexMinusIntraday.Value;
                if (distance > 0m && distance < dexZone)
                {
                    var dexScore = (int)Math.Round((1m - distance / dexZone) * 15m);
                    score -= dexScore;
                    if (dexScore >= 5)
                    {
                        reasons.Add("D- pull");
                    }
                }
            }
        }

        // 5. Intraday skew.
        if (input.Skew25dIntraday is > 0.05m)
        {
            score -= 10;
            reasons.Add("skew>5vp");
        }
        else if (input.Skew25dIntraday is > 0.03m)
        {
            score -= 5;
        }

        // 6. Intraday term backwardation.
        if (input.TermIntradaySlope is > 0.01m)
        {
            score -= 5;
            reasons.Add("term-back");
        }

        // 7. Afternoon 0DTE pin. The inclusive UTC hour range is preserved
        // exactly from the legacy implementation.
        var hourUtc = now.UtcDateTime.Hour;
        if (hourUtc >= profile.PinStartHourUtc &&
            hourUtc <= profile.PinEndHourUtc &&
            input.PinStrike0Dte is > 0m &&
            hasRange)
        {
            var pin = input.PinStrike0Dte.Value;
            var pinZone = range * 0.10m;
            if (Math.Abs(spot - pin) < pinZone)
            {
                score += spot > pin ? -5 : 5;
                reasons.Add("0DTE pin");
            }
        }

        // Attenuation uses the same ordering and banker's rounding as legacy.
        var multiplier = 1.0;
        if (input.HasMetadata)
        {
            if (EqualsLegacyValue(input.VixRegime, "elevated"))
            {
                multiplier *= 0.6;
            }

            if (EqualsLegacyValue(input.DataQuality, "partial"))
            {
                multiplier *= 0.7;
            }

            if (input.IvRankIntraday is > 90m)
            {
                multiplier *= 0.5;
            }
        }

        score = (int)Math.Round(score * multiplier);
        score = Math.Max(-100, Math.Min(100, score));

        var bucket = ToBucket(score);
        return new ContextScoreResult(score, ToTag(bucket), bucket, reasons.AsReadOnly());
    }

    public static ContextScoreBucket ToBucket(int score) => score switch
    {
        >= 70 => ContextScoreBucket.BullishHigh,
        >= 30 => ContextScoreBucket.Bullish,
        > -30 => ContextScoreBucket.Neutral,
        > -70 => ContextScoreBucket.Bearish,
        _ => ContextScoreBucket.BearishHigh,
    };

    private static ContextScoreResult Blocked(string reason) =>
        new(0, "BLOCKED", ContextScoreBucket.Blocked, [reason], reason);

    private static string ToTag(ContextScoreBucket bucket) => bucket switch
    {
        ContextScoreBucket.BullishHigh => "BULLISH HIGH",
        ContextScoreBucket.Bullish => "BULLISH",
        ContextScoreBucket.Neutral => "NEUTRAL",
        ContextScoreBucket.Bearish => "BEARISH",
        ContextScoreBucket.BearishHigh => "BEARISH HIGH",
        ContextScoreBucket.Data => "DATA",
        ContextScoreBucket.Blocked => "BLOCKED",
        _ => throw new ArgumentOutOfRangeException(nameof(bucket)),
    };

    private static bool EqualsLegacyValue(string? value, string expected) =>
        string.Equals(value, expected, StringComparison.Ordinal);
}
