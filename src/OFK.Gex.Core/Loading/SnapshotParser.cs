using System.Text;
using System.Text.Json;
using OFK.Gex.Core.Health;

namespace OFK.Gex.Core;

/// <summary>Parses full-level JSON independently of filesystem access.</summary>
public static class SnapshotParser
{
    public const string ExpectedSchemaVersion = "1.0";

    private static readonly JsonSerializerOptions SerializerOptions = new()
    {
        PropertyNameCaseInsensitive = false,
    };

    public static SnapshotLoadResult Parse(
        string json,
        InstrumentSymbol symbol,
        string? sourcePath = null) =>
        Parse(json, InstrumentDefinitions.Get(symbol), sourcePath);

    public static SnapshotLoadResult Parse(
        string json,
        InstrumentDefinition instrument,
        string? sourcePath = null)
    {
        ArgumentNullException.ThrowIfNull(instrument);
        if (json is null)
        {
            return Invalid("json.null", "JSON input cannot be null.", new SnapshotSource(sourcePath));
        }

        using var stream = new MemoryStream(Encoding.UTF8.GetBytes(json), writable: false);
        return Parse(stream, instrument, new SnapshotSource(sourcePath, LengthBytes: stream.Length));
    }

    public static SnapshotLoadResult Parse(
        Stream jsonStream,
        InstrumentDefinition instrument,
        SnapshotSource? source = null)
    {
        ArgumentNullException.ThrowIfNull(jsonStream);
        ArgumentNullException.ThrowIfNull(instrument);
        source ??= new SnapshotSource();

        FullLevelsDocument? document;
        try
        {
            document = JsonSerializer.Deserialize<FullLevelsDocument>(jsonStream, SerializerOptions);
        }
        catch (JsonException exception)
        {
            var message = string.IsNullOrWhiteSpace(exception.Path)
                ? exception.Message
                : $"{exception.Message} Path: {exception.Path}.";
            return Invalid("json.invalid", message, source, exception.Path);
        }
        catch (NotSupportedException exception)
        {
            return Invalid("json.unsupported", exception.Message, source);
        }

        if (document is null)
        {
            return Invalid("json.empty", "JSON must contain an object.", source);
        }

        var diagnostics = new List<LoadDiagnostic>();
        var snapshot = Map(document, instrument, diagnostics);
        Validate(document, snapshot, diagnostics);
        var state = DetermineState(document, diagnostics);
        return new SnapshotLoadResult(snapshot, state, diagnostics, source);
    }

    public static SnapshotLoadResult Parse(
        Stream jsonStream,
        InstrumentSymbol symbol,
        SnapshotSource? source = null) =>
        Parse(jsonStream, InstrumentDefinitions.Get(symbol), source);

    private static MarketSnapshot Map(
        FullLevelsDocument document,
        InstrumentDefinition instrument,
        List<LoadDiagnostic> diagnostics)
    {
        var isNq = instrument.Symbol == InstrumentSymbol.Nq;
        var gex = new GexSnapshot
        {
            Spot = isNq ? document.SpotNq : document.SpotEs,
            GammaFlip = document.GammaFlip,
            VolTrigger = document.VolTrigger,
            CallWall = document.CallWall,
            PutWall = document.PutWall,
            RiskPivot = document.RiskPivot,
            VannaFlip = document.VannaFlip,
            CharmMagnet = document.CharmMagnet,
            MaxPain = isNq ? document.MaxPainNq : document.MaxPainEs,
            ExpectedMoveHigh = isNq ? document.RangeHighNq : document.RangeHighEs,
            ExpectedMoveLow = isNq ? document.RangeLowNq : document.RangeLowEs,
            ExpectedMovePoints = isNq ? document.ExpectedMoveNq : document.ExpectedMoveEs,
            PutCallRatio = document.Pcr,
            CallWallGex = document.CallWallGex,
            PutWallGex = document.PutWallGex,
            TotalGex = document.TotalGex,
            TotalVex = document.TotalVex,
            TotalCex = document.TotalCex,
            TotalDex = document.TotalDex,
            GexRegime = document.GexRegime,
            VexRegime = document.VexRegime,
            CallWallIntraday = isNq ? document.CallWallIntradayNq : document.CallWallIntradayEs,
            PutWallIntraday = isNq ? document.PutWallIntradayNq : document.PutWallIntradayEs,
            CallWallIntradayGex = document.CallWallIntradayGex,
            PutWallIntradayGex = document.PutWallIntradayGex,
            WallsIntradayMaxDte = document.WallsIntradayMaxDte,
            CTransIntraday = isNq ? document.CTransIntradayNq : document.CTransIntradayEs,
            PTransIntraday = isNq ? document.PTransIntradayNq : document.PTransIntradayEs,
            DexPlusIntraday = isNq ? document.DexPlusIntradayNq : document.DexPlusIntradayEs,
            DexMinusIntraday = isNq ? document.DexMinusIntradayNq : document.DexMinusIntradayEs,
            DexPlusIntradayDex = document.DexPlusIntradayDex,
            DexMinusIntradayDex = document.DexMinusIntradayDex,
            AtmIvIntraday = document.AtmIvIntraday,
            AtmIvIntradayDte = document.AtmIvIntradayDte,
            Skew25dIntraday = document.Skew25dIntraday,
            Skew25dIntradayDte = document.Skew25dIntradayDte,
            TermIntradaySlope = document.TermIntradaySlope,
            TermIntradayFrontDte = document.TermIntradayFrontDte,
            TermIntradayBackDte = document.TermIntradayBackDte,
            TermIntradayIvFront = document.TermIntradayIvFront,
            TermIntradayIvBack = document.TermIntradayIvBack,
            TermIntradayRegime = document.TermIntradayRegime,
            AtmIvStructural = document.AtmIvStructural,
            Skew25dStructural = document.Skew25dStructural,
            IvStructuralBack = document.IvStructuralBack,
            IvStructuralBackDte = document.IvStructuralBackDte,
            TermStructuralSlope = document.TermStructuralSlope,
            TermStructuralRegime = document.TermStructuralRegime,
            TopOpenInterest = MapOpenInterest(document.TopOiStrikes, isNq, diagnostics, "top_oi_strikes"),
            TopOpenInterestIntraday = MapOpenInterest(document.TopOiIntraday, isNq, diagnostics, "top_oi_intraday"),
            AbsoluteGexLevels = MapAbsoluteGex(document, isNq),
            ExtendedGexWalls = MapExtendedGex(document, isNq),
            MaxPain0DTE = isNq ? document.MaxPain0DteNq : document.MaxPain0DteEs,
            PinStrike0DTE = isNq ? document.PinStrike0DteNq : document.PinStrike0DteEs,
            CharmMagnet0DTE = isNq ? document.CharmMagnet0DteNq : document.CharmMagnet0DteEs,
            ZeroDteOiTotal = ToLong(document.ZeroDteOiTotal, "zero_dte_oi_total", diagnostics),
            ZeroDteDte = document.ZeroDteDte,
            IvRankIntraday = document.IvRankIntraday?.Ivr,
            IvRankIntradayStatus = document.IvRankIntraday?.Status,
        };

        var meta = new MetaSnapshot
        {
            TradeDate = document.TradeDate,
            GeneratedAt = ParseDate(document.GeneratedAt, "generated_at", diagnostics),
            JsonSchemaVersion = document.JsonSchemaVersion,
            LastUpdateUtc = ParseDate(document.LastUpdateUtc, "last_update_utc", diagnostics),
            DataQuality = document.DataQuality,
            Vix = document.Vix,
            Vix9d = document.Vix9d,
            VixDodChange = document.VixDodChange,
            VixTermSlope = document.VixTermSlope,
            VixRegime = document.VixRegime,
            VixTerm = document.VixTerm,
            MacroInBlackout = document.MacroInBlackout,
            MacroBlackoutUntilUtc = ParseDate(document.MacroBlackoutUntil, "macro_blackout_until", diagnostics),
            MacroCurrentEvent = ReadEventTitle(document.MacroCurrentEvent),
            MacroNextEventTitle = ReadEventTitle(document.MacroNextEvent),
            MacroMinutesToNext = document.MacroMinutesToNext,
        };

        return new MarketSnapshot(instrument, gex, meta);
    }

    private static void Validate(
        FullLevelsDocument document,
        MarketSnapshot snapshot,
        List<LoadDiagnostic> diagnostics)
    {
        if (string.IsNullOrWhiteSpace(document.JsonSchemaVersion))
        {
            diagnostics.Add(Error(
                "schema.missing",
                $"json_schema_version is required and must equal {ExpectedSchemaVersion}.",
                "json_schema_version"));
        }
        else if (!string.Equals(document.JsonSchemaVersion, ExpectedSchemaVersion, StringComparison.Ordinal))
        {
            diagnostics.Add(Error(
                "schema.mismatch",
                $"Unsupported schema {document.JsonSchemaVersion}; expected {ExpectedSchemaVersion}.",
                "json_schema_version"));
        }

        Require(snapshot.Gex.Spot, $"spot_{snapshot.Instrument.FieldSuffix}", diagnostics);
        Require(snapshot.Gex.GammaFlip, "gamma_flip", diagnostics);
        Require(snapshot.Gex.CallWall, "call_wall", diagnostics);
        Require(snapshot.Gex.PutWall, "put_wall", diagnostics);

        if (string.IsNullOrWhiteSpace(document.DataQuality))
        {
            diagnostics.Add(Warning(
                "field.missing",
                "data_quality is absent; downstream health is degraded.",
                "data_quality"));
        }
        else if (document.DataQuality is not ("ok" or "partial" or "error"))
        {
            diagnostics.Add(Warning(
                "field.value",
                $"Unrecognized data_quality value '{document.DataQuality}'.",
                "data_quality"));
        }
    }

    private static HealthState DetermineState(
        FullLevelsDocument document,
        IReadOnlyCollection<LoadDiagnostic> diagnostics)
    {
        if (diagnostics.Any(d => d.Code is "schema.missing" or "schema.mismatch"))
        {
            return HealthState.SchemaMismatch;
        }

        if (string.Equals(document.DataQuality, "error", StringComparison.OrdinalIgnoreCase))
        {
            return HealthState.Error;
        }

        if (string.Equals(document.DataQuality, "partial", StringComparison.OrdinalIgnoreCase) ||
            diagnostics.Count != 0)
        {
            return HealthState.Partial;
        }

        return HealthState.Healthy;
    }

    private static IReadOnlyList<TopOpenInterestStrike> MapOpenInterest(
        IEnumerable<TopOpenInterestDocument>? values,
        bool isNq,
        List<LoadDiagnostic> diagnostics,
        string field)
    {
        if (values is null)
        {
            return [];
        }

        return values.Select((value, index) => new TopOpenInterestStrike(
            isNq ? value.StrikeNq : value.StrikeEs,
            ToLong(value.CallOi, $"{field}[{index}].call_oi", diagnostics),
            ToLong(value.PutOi, $"{field}[{index}].put_oi", diagnostics),
            ToLong(value.TotalOi, $"{field}[{index}].total_oi", diagnostics))).ToArray();
    }

    private static long? ToLong(
        decimal? value,
        string field,
        List<LoadDiagnostic> diagnostics)
    {
        if (value is null)
        {
            return null;
        }

        if (decimal.Truncate(value.Value) != value.Value ||
            value.Value is < long.MinValue or > long.MaxValue)
        {
            diagnostics.Add(Warning(
                "field.invalid_integer",
                $"'{value}' is not a valid 64-bit integer.",
                field));
            return null;
        }

        return decimal.ToInt64(value.Value);
    }

    private static IReadOnlyList<GexLevel> MapAbsoluteGex(FullLevelsDocument d, bool isNq) =>
    [
        new(isNq ? d.AbsGex1Nq : d.AbsGex1Es, d.AbsGex1Gex),
        new(isNq ? d.AbsGex2Nq : d.AbsGex2Es, d.AbsGex2Gex),
        new(isNq ? d.AbsGex3Nq : d.AbsGex3Es, d.AbsGex3Gex),
    ];

    private static IReadOnlyList<GexLevel> MapExtendedGex(FullLevelsDocument d, bool isNq) =>
    [
        new(isNq ? d.GexExt1Nq : d.GexExt1Es, d.GexExt1Gex, d.GexExt1Side),
        new(isNq ? d.GexExt2Nq : d.GexExt2Es, d.GexExt2Gex, d.GexExt2Side),
        new(isNq ? d.GexExt3Nq : d.GexExt3Es, d.GexExt3Gex, d.GexExt3Side),
        new(isNq ? d.GexExt4Nq : d.GexExt4Es, d.GexExt4Gex, d.GexExt4Side),
    ];

    private static DateTimeOffset? ParseDate(
        string? value,
        string field,
        List<LoadDiagnostic> diagnostics)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        if (DateTimeOffset.TryParse(
                value,
                System.Globalization.CultureInfo.InvariantCulture,
                System.Globalization.DateTimeStyles.RoundtripKind,
                out var result))
        {
            return result;
        }

        diagnostics.Add(Warning("field.invalid_timestamp", $"'{value}' is not a valid timestamp.", field));
        return null;
    }

    private static string? ReadEventTitle(JsonElement? eventValue)
    {
        if (eventValue is null)
        {
            return null;
        }

        var value = eventValue.Value;
        if (value.ValueKind == JsonValueKind.String)
        {
            return value.GetString();
        }

        if (value.ValueKind == JsonValueKind.Object &&
            value.TryGetProperty("title", out var title) &&
            title.ValueKind == JsonValueKind.String)
        {
            return title.GetString();
        }

        return null;
    }

    private static void Require<T>(T? value, string field, List<LoadDiagnostic> diagnostics)
        where T : struct
    {
        if (value is null)
        {
            diagnostics.Add(Error("field.missing", $"Required field '{field}' is missing or null.", field));
        }
    }

    private static LoadDiagnostic Error(string code, string message, string? field = null) =>
        new(code, message, LoadDiagnosticSeverity.Error, field);

    private static LoadDiagnostic Warning(string code, string message, string? field = null) =>
        new(code, message, LoadDiagnosticSeverity.Warning, field);

    private static SnapshotLoadResult Invalid(
        string code,
        string message,
        SnapshotSource source,
        string? field = null) =>
        new(
            null,
            HealthState.Invalid,
            [new LoadDiagnostic(code, message, LoadDiagnosticSeverity.Error, field)],
            source);
}
