using OFK.Gex.Core.Alerts;
using OFK.Gex.Core.Analysis;
using OFK.Gex.Core.Health;
using OFK.Gex.Core.Tests.Fixtures;

namespace OFK.Gex.Core.Tests.Analysis;

public sealed class MarketSnapshotAdapterTests
{
    private static readonly DateTimeOffset Now =
        new(2026, 5, 1, 16, 0, 0, TimeSpan.Zero);

    [Fact]
    public void Parsed_snapshot_maps_all_context_score_inputs()
    {
        var snapshot = ParseNq();

        var input = snapshot.ToContextScoreInput();

        Assert.Equal(snapshot.Gex.Spot, input.Spot);
        Assert.Equal(snapshot.Gex.GammaFlip, input.GammaFlip);
        Assert.Equal(snapshot.Gex.CallWallIntraday, input.CallWallIntraday);
        Assert.Equal(snapshot.Gex.PutWallIntraday, input.PutWallIntraday);
        Assert.Equal(snapshot.Gex.CTransIntraday, input.CTransIntraday);
        Assert.Equal(snapshot.Gex.PTransIntraday, input.PTransIntraday);
        Assert.Equal(snapshot.Gex.DexPlusIntraday, input.DexPlusIntraday);
        Assert.Equal(snapshot.Gex.DexMinusIntraday, input.DexMinusIntraday);
        Assert.Equal(snapshot.Gex.PinStrike0DTE, input.PinStrike0Dte);
        Assert.Equal(snapshot.Meta.Vix, input.Vix);
        Assert.Equal(snapshot.Meta.MacroNextEventTitle, input.MacroNextEventTitle);
        Assert.Equal(snapshot.Meta.DataQuality, input.DataQuality);
    }

    [Fact]
    public void Parsed_snapshot_maps_health_metadata_for_fixed_clock()
    {
        var parsed = SnapshotParser.Parse(
            FixtureFiles.ReadNqGolden(),
            InstrumentDefinitions.Nq);
        var snapshot = Assert.IsType<MarketSnapshot>(parsed.Snapshot);

        var health = HealthEvaluator.Evaluate(
            snapshot.ToHealthEvaluationInput(parsed.Source),
            Now);

        Assert.Equal(HealthState.Healthy, health.State);
        Assert.Equal(TimeSpan.FromMinutes(1), health.Age);
    }

    [Fact]
    public void Parsed_snapshot_maps_to_alert_engine_without_platform_state()
    {
        var snapshot = ParseNq();

        var input = snapshot.ToAlertEvaluationInput(
            previousClose: 149m,
            currentClose: 150m,
            previousVixRegime: "normal");
        var result = snapshot.EvaluateAlerts(
            previousClose: 149m,
            currentClose: 150m,
            now: Now,
            previousVixRegime: "normal");

        Assert.Equal("NQ", input.Symbol);
        Assert.Equal(snapshot.Instrument.TickSize, input.TickSize);
        Assert.Equal(snapshot.Gex.GexExt1, input.GexExtension1);
        var crossing = Assert.Single(
            result.Decisions,
            decision => decision.Key == "gamma_flip");
        Assert.Equal(AlertFamily.GammaFlipCrossing, crossing.Family);
    }

    private static MarketSnapshot ParseNq()
    {
        var parsed = SnapshotParser.Parse(
            FixtureFiles.ReadNqGolden(),
            InstrumentDefinitions.Nq);
        Assert.Equal(HealthState.Healthy, parsed.State);
        return Assert.IsType<MarketSnapshot>(parsed.Snapshot);
    }
}
