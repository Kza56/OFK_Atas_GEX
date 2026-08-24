using OFK.Gex.Core;
using OFK.Gex.Core.Analysis;
using OFK.Gex.Core.Health;
using OFK.Gex.Core.Tests.Fixtures;

namespace OFK.Gex.Core.Tests.Analysis;

public sealed class ContextScoreGoldenTests
{
    private static readonly DateTimeOffset NqFixtureTime =
        new(2026, 5, 1, 16, 0, 0, TimeSpan.Zero);

    private static readonly DateTimeOffset EsFixtureTime =
        new(2026, 5, 1, 20, 0, 0, TimeSpan.Zero);

    [Fact]
    public void Nq_golden_score_matches_legacy_algorithm()
    {
        // Legacy evidence (OFK_NQ_ContextScore.ComputeScore):
        // wall +30, GF +15, squeeze +20, D+ pull +12 = +77.
        var result = ContextScoreCalculator.Calculate(
            ParseGolden(FixtureFiles.ReadNqGolden(), InstrumentDefinitions.Nq),
            NqFixtureTime);

        Assert.Equal(77, result.Score);
        Assert.Equal("BULLISH HIGH", result.Tag);
        Assert.Equal(ContextScoreBucket.BullishHigh, result.Bucket);
        Assert.False(result.IsBlocked);
        Assert.Null(result.BlockingReason);
        Assert.Equal(
            ["CW broke", "GF+", "squeeze+", "D+ pull"],
            result.Reasons);
        Assert.Equal("CW broke • GF+ • squeeze+ • D+ pull", result.ReasonText);
    }

    [Fact]
    public void Es_golden_score_matches_legacy_algorithm()
    {
        // Legacy evidence (OFK_ES_ContextScore.ComputeScore):
        // wall -30, GF -15, squeeze -20, D- pull -13, skew -10,
        // backwardation -5, afternoon pin +5 = -88.
        var result = ContextScoreCalculator.Calculate(
            ParseGolden(FixtureFiles.ReadEsGolden(), InstrumentDefinitions.Es),
            EsFixtureTime);

        Assert.Equal(-88, result.Score);
        Assert.Equal("BEARISH HIGH", result.Tag);
        Assert.Equal(ContextScoreBucket.BearishHigh, result.Bucket);
        Assert.False(result.IsBlocked);
        Assert.Equal(
            ["PW broke", "GF-", "squeeze-", "D- pull", "skew>5vp", "term-back", "0DTE pin"],
            result.Reasons);
        Assert.Equal(
            "PW broke • GF- • squeeze- • D- pull • skew>5vp • term-back • 0DTE pin",
            result.ReasonText);
    }

    [Theory]
    [InlineData(70, ContextScoreBucket.BullishHigh)]
    [InlineData(69, ContextScoreBucket.Bullish)]
    [InlineData(30, ContextScoreBucket.Bullish)]
    [InlineData(29, ContextScoreBucket.Neutral)]
    [InlineData(-29, ContextScoreBucket.Neutral)]
    [InlineData(-30, ContextScoreBucket.Bearish)]
    [InlineData(-69, ContextScoreBucket.Bearish)]
    [InlineData(-70, ContextScoreBucket.BearishHigh)]
    public void Bucket_boundaries_match_legacy_indicator(
        int score,
        ContextScoreBucket expected)
    {
        Assert.Equal(expected, ContextScoreCalculator.ToBucket(score));
    }

    [Theory]
    [InlineData(99, -50, "PW broke")]
    [InlineData(100, 30, "PW zone")]
    [InlineData(200, -25, "CW zone")]
    [InlineData(201, 50, "CW broke")]
    public void Wall_boundary_discontinuity_is_preserved_as_legacy_characterization(
        decimal spot,
        int expectedScore,
        string expectedWallReason)
    {
        // Legacy wall contribution is counterintuitive but observable:
        // just below PW => -30, at PW => +30, at CW => -30, above CW => +30.
        // Gamma-zone contribution then adds -20/0/+5/+20 respectively.
        var result = ContextScoreCalculator.Calculate(
            new ContextScoreInput
            {
                Spot = spot,
                PutWallIntraday = 100m,
                CallWallIntraday = 200m,
                PTransIntraday = 100m,
                CTransIntraday = 200m,
                DataQuality = "ok",
            },
            ContextScoreProfile.Nq,
            NqFixtureTime);

        Assert.Equal(expectedScore, result.Score);
        Assert.Contains(expectedWallReason, result.Reasons);
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public void Missing_levels_or_spot_returns_data_result(
        bool hasLevels,
        bool includeSpot)
    {
        var result = ContextScoreCalculator.Calculate(
            new ContextScoreInput
            {
                HasLevels = hasLevels,
                Spot = includeSpot ? 150m : null,
            },
            ContextScoreProfile.Nq,
            NqFixtureTime);

        Assert.Equal(0, result.Score);
        Assert.Equal("DATA", result.Tag);
        Assert.Equal(ContextScoreBucket.Data, result.Bucket);
        Assert.Equal(["No data"], result.Reasons);
    }

    [Fact]
    public void Blocking_filters_follow_legacy_precedence()
    {
        var allBlockingConditions = GoldenNqInput() with
        {
            Vix = 42m,
            VixRegime = "extreme",
            MacroInBlackout = true,
            MacroMinutesToNext = 5,
            DataQuality = "error",
        };

        var vix = ContextScoreCalculator.Calculate(
            allBlockingConditions,
            ContextScoreProfile.Nq,
            NqFixtureTime);
        var macro = ContextScoreCalculator.Calculate(
            allBlockingConditions with { VixRegime = "normal" },
            ContextScoreProfile.Nq,
            NqFixtureTime);
        var imminent = ContextScoreCalculator.Calculate(
            allBlockingConditions with
            {
                VixRegime = "normal",
                MacroInBlackout = false,
            },
            ContextScoreProfile.Nq,
            NqFixtureTime);
        var quality = ContextScoreCalculator.Calculate(
            allBlockingConditions with
            {
                VixRegime = "normal",
                MacroInBlackout = false,
                MacroMinutesToNext = 31,
            },
            ContextScoreProfile.Nq,
            NqFixtureTime);

        Assert.Equal("VIX EXTREME (42.0) — STOP", vix.BlockingReason);
        Assert.Equal("Macro blackout IN PROGRESS", macro.BlockingReason);
        Assert.Equal("Nonfarm Payrolls in 5min", imminent.BlockingReason);
        Assert.Equal("Data ERROR", quality.BlockingReason);
        Assert.All([vix, macro, imminent, quality], AssertBlocked);
    }

    [Fact]
    public void Disabled_blocking_filters_preserve_score_calculation()
    {
        var result = ContextScoreCalculator.Calculate(
            GoldenNqInput() with
            {
                VixRegime = "extreme",
                MacroInBlackout = true,
                MacroMinutesToNext = 5,
                DataQuality = "error",
            },
            ContextScoreProfile.Nq,
            NqFixtureTime,
            enableBlockingFilters: false);

        Assert.Equal(77, result.Score);
        Assert.False(result.IsBlocked);
    }

    [Fact]
    public void Elevated_partial_and_high_ivr_attenuators_compound_in_legacy_order()
    {
        var result = ContextScoreCalculator.Calculate(
            GoldenNqInput() with
            {
                VixRegime = "elevated",
                DataQuality = "partial",
                IvRankIntraday = 95m,
            },
            ContextScoreProfile.Nq,
            NqFixtureTime);

        // 77 × 0.6 × 0.7 × 0.5 = 16.17, banker's rounding => 16.
        Assert.Equal(16, result.Score);
        Assert.Equal(ContextScoreBucket.Neutral, result.Bucket);
    }

    [Theory]
    [InlineData(17, -5)]
    [InlineData(18, 0)]
    [InlineData(21, 0)]
    [InlineData(22, -5)]
    public void Afternoon_pin_period_is_inclusive_at_18_and_21_utc(
        int hourUtc,
        int expectedScore)
    {
        var input = new ContextScoreInput
        {
            Spot = 150m,
            CallWallIntraday = 200m,
            PutWallIntraday = 100m,
            PinStrike0Dte = 155m,
            DataQuality = "ok",
        };

        var result = ContextScoreCalculator.Calculate(
            input,
            ContextScoreProfile.Nq,
            new DateTimeOffset(2026, 5, 1, hourUtc, 0, 0, TimeSpan.Zero));

        Assert.Equal(expectedScore, result.Score);
    }

    [Fact]
    public void Pin_at_exact_zone_boundary_does_not_contribute()
    {
        var result = ContextScoreCalculator.Calculate(
            new ContextScoreInput
            {
                Spot = 150m,
                CallWallIntraday = 200m,
                PutWallIntraday = 100m,
                PinStrike0Dte = 160m,
                DataQuality = "ok",
            },
            ContextScoreProfile.Nq,
            new DateTimeOffset(2026, 5, 1, 18, 0, 0, TimeSpan.Zero));

        Assert.Equal(-5, result.Score);
        Assert.DoesNotContain("0DTE pin", result.Reasons);
    }

    [Theory]
    [InlineData("NQ")]
    [InlineData("nq")]
    [InlineData("ES")]
    [InlineData("es")]
    public void Profiles_accept_both_supported_symbols_case_insensitively(string symbol)
    {
        Assert.Equal(symbol.ToUpperInvariant(), ContextScoreProfile.ForSymbol(symbol).Symbol);
    }

    [Fact]
    public void Profiles_reject_unknown_symbols()
    {
        Assert.Throws<ArgumentException>(() => ContextScoreProfile.ForSymbol("YM"));
    }

    internal static ContextScoreInput GoldenNqInput() => new()
    {
        Spot = 205m,
        GammaFlip = 150m,
        CallWallIntraday = 200m,
        PutWallIntraday = 100m,
        CTransIntraday = 160m,
        PTransIntraday = 140m,
        DexPlusIntraday = 210m,
        DexMinusIntraday = 125m,
        Skew25dIntraday = 0.02m,
        TermIntradaySlope = -0.01m,
        PinStrike0Dte = 204m,
        IvRankIntraday = 50m,
        Vix = 17.2m,
        VixRegime = "normal",
        MacroNextEventTitle = "Nonfarm Payrolls",
        MacroMinutesToNext = 90,
        DataQuality = "ok",
    };

    internal static ContextScoreInput GoldenEsInput() => new()
    {
        Spot = 5590m,
        GammaFlip = 5675m,
        CallWallIntraday = 5750m,
        PutWallIntraday = 5600m,
        CTransIntraday = 5700m,
        PTransIntraday = 5650m,
        DexPlusIntraday = 5720m,
        DexMinusIntraday = 5585m,
        Skew25dIntraday = 0.06m,
        TermIntradaySlope = 0.02m,
        PinStrike0Dte = 5594m,
        IvRankIntraday = 65m,
        Vix = 21.4m,
        VixRegime = "normal",
        MacroNextEventTitle = "FOMC Minutes",
        MacroMinutesToNext = 75,
        DataQuality = "ok",
    };

    private static void AssertBlocked(ContextScoreResult result)
    {
        Assert.True(result.IsBlocked);
        Assert.Equal(0, result.Score);
        Assert.Equal("BLOCKED", result.Tag);
        Assert.Equal(ContextScoreBucket.Blocked, result.Bucket);
        var blockingReason = Assert.IsType<string>(result.BlockingReason);
        Assert.Equal(blockingReason, Assert.Single(result.Reasons));
    }

    private static MarketSnapshot ParseGolden(
        string json,
        InstrumentDefinition instrument)
    {
        var parsed = SnapshotParser.Parse(json, instrument);
        Assert.Equal(HealthState.Healthy, parsed.State);
        Assert.Empty(parsed.Diagnostics);
        return Assert.IsType<MarketSnapshot>(parsed.Snapshot);
    }
}
