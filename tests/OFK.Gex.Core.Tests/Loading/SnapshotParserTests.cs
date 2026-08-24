using System.Text;
using OFK.Gex.Core.Health;
using OFK.Gex.Core.Tests.Fixtures;

namespace OFK.Gex.Core.Tests.Loading;

public sealed class SnapshotParserTests
{
    [Fact]
    public void Nq_golden_fixture_extracts_exact_indicator_contract()
    {
        var result = SnapshotParser.Parse(
            FixtureFiles.ReadNqGolden(),
            InstrumentDefinitions.Nq,
            FixtureFiles.NqGolden);

        Assert.Equal(HealthState.Healthy, result.State);
        Assert.True(result.IsSuccess);
        Assert.Empty(result.Diagnostics);
        Assert.Equal(FixtureFiles.NqGolden, result.Source.Path);
        var snapshot = Assert.IsType<MarketSnapshot>(result.Snapshot);
        Assert.Equal(InstrumentSymbol.Nq, snapshot.Instrument.Symbol);

        var gex = snapshot.Gex;
        Assert.Equal(205m, gex.Spot);
        Assert.Equal(150m, gex.GammaFlip);
        Assert.Equal(210m, gex.CallWall);
        Assert.Equal(90m, gex.PutWall);
        Assert.Equal(200m, gex.CallWallIntraday);
        Assert.Equal(100m, gex.PutWallIntraday);
        Assert.Equal(160m, gex.CTransIntraday);
        Assert.Equal(140m, gex.PTransIntraday);
        Assert.Equal(210m, gex.DexPlusIntraday);
        Assert.Equal(125m, gex.DexMinusIntraday);
        Assert.Equal(1, gex.GexRegime);
        Assert.Equal(204m, gex.PinStrike0DTE);
        Assert.Equal(203m, gex.CharmMagnet0DTE);
        Assert.Equal(50m, gex.IvRankIntraday);
        Assert.Equal("ok", gex.IvRankIntradayStatus);
        Assert.Equal(208m, gex.GexExt1);

        var topOi = Assert.Single(gex.TopOpenInterest);
        Assert.Equal(200m, topOi.Strike);
        Assert.Equal(9000, topOi.CallOi);
        Assert.Equal(6000, topOi.PutOi);
        Assert.Equal(15000, topOi.TotalOi);

        var meta = snapshot.Meta;
        Assert.Equal("20260501", meta.TradeDate);
        Assert.Equal("1.0", meta.JsonSchemaVersion);
        Assert.Equal(new DateTimeOffset(2026, 5, 1, 15, 59, 0, TimeSpan.Zero), meta.LastUpdateUtc);
        Assert.Equal("ok", meta.DataQuality);
        Assert.Equal(17.2m, meta.Vix);
        Assert.Equal("normal", meta.VixRegime);
        Assert.False(meta.MacroInBlackout);
        Assert.Equal("Nonfarm Payrolls", meta.MacroNextEventTitle);
        Assert.Equal(90, meta.MacroMinutesToNext);
    }

    [Fact]
    public void Es_golden_fixture_extracts_exact_indicator_contract()
    {
        var result = SnapshotParser.Parse(
            FixtureFiles.ReadEsGolden(),
            InstrumentDefinitions.Es,
            FixtureFiles.EsGolden);

        Assert.Equal(HealthState.Healthy, result.State);
        Assert.True(result.IsSuccess);
        Assert.Empty(result.Diagnostics);
        var snapshot = Assert.IsType<MarketSnapshot>(result.Snapshot);
        Assert.Equal(InstrumentSymbol.Es, snapshot.Instrument.Symbol);

        var gex = snapshot.Gex;
        Assert.Equal(5590m, gex.Spot);
        Assert.Equal(5675m, gex.GammaFlip);
        Assert.Equal(5760m, gex.CallWall);
        Assert.Equal(5580m, gex.PutWall);
        Assert.Equal(5750m, gex.CallWallIntraday);
        Assert.Equal(5600m, gex.PutWallIntraday);
        Assert.Equal(5700m, gex.CTransIntraday);
        Assert.Equal(5650m, gex.PTransIntraday);
        Assert.Equal(5720m, gex.DexPlusIntraday);
        Assert.Equal(5585m, gex.DexMinusIntraday);
        Assert.Equal(-1, gex.GexRegime);
        Assert.Equal(5594m, gex.PinStrike0DTE);
        Assert.Equal(5596m, gex.CharmMagnet0DTE);
        Assert.Equal(65m, gex.IvRankIntraday);
        Assert.Equal("partial", gex.IvRankIntradayStatus);
        Assert.Equal(5610m, gex.GexExt1);

        var topOi = Assert.Single(gex.TopOpenInterest);
        Assert.Equal(5600m, topOi.Strike);
        Assert.Equal(12000, topOi.CallOi);
        Assert.Equal(22000, topOi.PutOi);
        Assert.Equal(34000, topOi.TotalOi);

        var meta = snapshot.Meta;
        Assert.Equal("1.0", meta.JsonSchemaVersion);
        Assert.Equal("ok", meta.DataQuality);
        Assert.Equal(21.4m, meta.Vix);
        Assert.Equal("normal", meta.VixRegime);
        Assert.False(meta.MacroInBlackout);
        Assert.Equal("FOMC Minutes", meta.MacroNextEventTitle);
        Assert.Equal(75, meta.MacroMinutesToNext);
    }

    [Fact]
    public void Symbol_selection_does_not_fall_back_to_other_instrument_fields()
    {
        var result = SnapshotParser.Parse(
            FixtureFiles.ReadNqGolden(),
            InstrumentDefinitions.Es);

        Assert.Equal(HealthState.Partial, result.State);
        var snapshot = Assert.IsType<MarketSnapshot>(result.Snapshot);
        Assert.Null(snapshot.Gex.Spot);
        var diagnostic = Assert.Single(
            result.Diagnostics,
            item => item.Code == "field.missing" && item.Field == "spot_es");
        Assert.Equal(LoadDiagnosticSeverity.Error, diagnostic.Severity);
    }

    [Theory]
    [InlineData("{")]
    [InlineData("[]")]
    [InlineData("{\"spot_nq\":\"205\"}")]
    public void Malformed_or_wrong_type_json_is_invalid(string json)
    {
        var result = SnapshotParser.Parse(json, InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.Invalid, result.State);
        Assert.False(result.IsSuccess);
        Assert.Null(result.Snapshot);
        Assert.Contains(result.Diagnostics, item => item.Code == "json.invalid");
    }

    [Fact]
    public void Null_json_has_explicit_diagnostic()
    {
        var result = SnapshotParser.Parse((string)null!, InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.Invalid, result.State);
        AssertDiagnostic(result, "json.null", LoadDiagnosticSeverity.Error);
    }

    [Fact]
    public void Json_null_has_explicit_empty_diagnostic()
    {
        var result = SnapshotParser.Parse("null", InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.Invalid, result.State);
        AssertDiagnostic(result, "json.empty", LoadDiagnosticSeverity.Error);
    }

    [Fact]
    public void Missing_required_field_remains_null_and_degrades_health()
    {
        var json = RequiredJsonWithoutSpot();

        var result = SnapshotParser.Parse(json, InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.Partial, result.State);
        Assert.True(result.IsSuccess);
        var snapshot = Assert.IsType<MarketSnapshot>(result.Snapshot);
        Assert.Null(snapshot.Gex.Spot);
        var diagnostic = Assert.Single(
            result.Diagnostics,
            item => item.Code == "field.missing" && item.Field == "spot_nq");
        Assert.Equal(LoadDiagnosticSeverity.Error, diagnostic.Severity);
    }

    [Fact]
    public void Optional_missing_and_numeric_zero_remain_distinguishable()
    {
        var missing = SnapshotParser.Parse(
            RequiredJsonWithoutSpot().Replace(
                "\"gamma_flip\"",
                "\"spot_nq\": 10, \"gamma_flip\"",
                StringComparison.Ordinal),
            InstrumentDefinitions.Nq);
        var zero = SnapshotParser.Parse(
            RequiredJsonWithoutSpot().Replace(
                "\"gamma_flip\"",
                "\"spot_nq\": 10, \"vol_trigger\": 0, \"gamma_flip\"",
                StringComparison.Ordinal),
            InstrumentDefinitions.Nq);

        Assert.Null(Assert.IsType<MarketSnapshot>(missing.Snapshot).Gex.VolTrigger);
        Assert.Equal(0m, Assert.IsType<MarketSnapshot>(zero.Snapshot).Gex.VolTrigger);
    }

    [Theory]
    [InlineData("9.0", "ok", HealthState.SchemaMismatch, "schema.mismatch")]
    [InlineData("1.0", "partial", HealthState.Partial, null)]
    [InlineData("1.0", "error", HealthState.Error, null)]
    [InlineData("1.0", "unknown", HealthState.Partial, "field.value")]
    public void Schema_and_data_quality_states_have_deterministic_precedence(
        string schema,
        string quality,
        HealthState expectedState,
        string? expectedDiagnostic)
    {
        var json = $$"""
            {
              "json_schema_version": "{{schema}}",
              "data_quality": "{{quality}}",
              "spot_nq": 10,
              "gamma_flip": 9,
              "call_wall": 12,
              "put_wall": 8
            }
            """;

        var result = SnapshotParser.Parse(json, InstrumentDefinitions.Nq);

        Assert.Equal(expectedState, result.State);
        Assert.Equal(expectedState == HealthState.Partial, result.IsSuccess);
        if (expectedDiagnostic is not null)
        {
            AssertDiagnostic(result, expectedDiagnostic);
        }
    }

    [Fact]
    public void Missing_schema_takes_precedence_over_error_quality()
    {
        var result = SnapshotParser.Parse(
            """
            {
              "data_quality": "error",
              "spot_nq": 10,
              "gamma_flip": 9,
              "call_wall": 12,
              "put_wall": 8
            }
            """,
            InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.SchemaMismatch, result.State);
        AssertDiagnostic(result, "schema.missing", LoadDiagnosticSeverity.Error);
    }

    [Fact]
    public void Fractional_and_out_of_range_open_interest_are_not_truncated()
    {
        var json = """
            {
              "json_schema_version": "1.0",
              "data_quality": "ok",
              "spot_nq": 10,
              "gamma_flip": 9,
              "call_wall": 12,
              "put_wall": 8,
              "top_oi_strikes": [
                {
                  "strike_nq": 11,
                  "call_oi": 12.5,
                  "put_oi": 9223372036854775808,
                  "total_oi": 2.0
                }
              ]
            }
            """;

        var result = SnapshotParser.Parse(json, InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.Partial, result.State);
        var openInterest = Assert.Single(
            Assert.IsType<MarketSnapshot>(result.Snapshot).Gex.TopOpenInterest);
        Assert.Null(openInterest.CallOi);
        Assert.Null(openInterest.PutOi);
        Assert.Equal(2, openInterest.TotalOi);
        Assert.Contains(
            result.Diagnostics,
            item => item.Code == "field.invalid_integer" &&
                item.Field == "top_oi_strikes[0].call_oi");
        Assert.Contains(
            result.Diagnostics,
            item => item.Code == "field.invalid_integer" &&
                item.Field == "top_oi_strikes[0].put_oi");
    }

    [Fact]
    public void Invalid_timestamp_is_nullable_and_diagnostic_not_epoch_zero()
    {
        var json = """
            {
              "json_schema_version": "1.0",
              "data_quality": "ok",
              "spot_nq": 10,
              "gamma_flip": 9,
              "call_wall": 12,
              "put_wall": 8,
              "last_update_utc": "not-a-time"
            }
            """;

        var result = SnapshotParser.Parse(json, InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.Partial, result.State);
        Assert.Null(Assert.IsType<MarketSnapshot>(result.Snapshot).Meta.LastUpdateUtc);
        AssertDiagnostic(result, "field.invalid_timestamp", field: "last_update_utc");
    }

    [Theory]
    [InlineData("\"CPI\"")]
    [InlineData("{\"title\":\"CPI\",\"impact\":\"High\"}")]
    public void Macro_event_accepts_legacy_string_and_current_object_shapes(string eventJson)
    {
        var json = $$"""
            {
              "json_schema_version": "1.0",
              "data_quality": "ok",
              "spot_nq": 10,
              "gamma_flip": 9,
              "call_wall": 12,
              "put_wall": 8,
              "macro_next_event": {{eventJson}}
            }
            """;

        var result = SnapshotParser.Parse(json, InstrumentDefinitions.Nq);

        Assert.Equal("CPI", Assert.IsType<MarketSnapshot>(result.Snapshot).Meta.MacroNextEventTitle);
    }

    [Fact]
    public void Stream_parse_preserves_supplied_source_metadata()
    {
        var bytes = Encoding.UTF8.GetBytes(FixtureFiles.ReadNqGolden());
        using var stream = new MemoryStream(bytes, writable: false);
        var source = new SnapshotSource(
            "fixture.json",
            new DateTimeOffset(2026, 5, 1, 16, 0, 0, TimeSpan.Zero),
            bytes.Length);

        var result = SnapshotParser.Parse(stream, InstrumentDefinitions.Nq, source);

        Assert.Same(source, result.Source);
        Assert.Equal(HealthState.Healthy, result.State);
    }

    private static string RequiredJsonWithoutSpot() =>
        """
        {
          "json_schema_version": "1.0",
          "data_quality": "ok",
          "gamma_flip": 9,
          "call_wall": 12,
          "put_wall": 8
        }
        """;

    private static void AssertDiagnostic(
        SnapshotLoadResult result,
        string code,
        LoadDiagnosticSeverity? severity = null,
        string? field = null)
    {
        var diagnostic = Assert.Single(
            result.Diagnostics,
            item => item.Code == code && (field is null || item.Field == field));
        if (severity is not null)
        {
            Assert.Equal(severity, diagnostic.Severity);
        }
    }
}
