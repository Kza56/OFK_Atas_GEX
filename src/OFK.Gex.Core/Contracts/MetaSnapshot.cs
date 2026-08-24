namespace OFK.Gex.Core;

public sealed record MetaSnapshot
{
    public string? TradeDate { get; init; }
    public DateTimeOffset? GeneratedAt { get; init; }
    public string? JsonSchemaVersion { get; init; }
    public DateTimeOffset? LastUpdateUtc { get; init; }
    public string? DataQuality { get; init; }
    public decimal? Vix { get; init; }
    public decimal? Vix9d { get; init; }
    public decimal? VixDodChange { get; init; }
    public decimal? VixTermSlope { get; init; }
    public string? VixRegime { get; init; }
    public string? VixTerm { get; init; }
    public bool? MacroInBlackout { get; init; }
    public DateTimeOffset? MacroBlackoutUntilUtc { get; init; }
    public string? MacroCurrentEvent { get; init; }
    public string? MacroNextEventTitle { get; init; }
    public int? MacroMinutesToNext { get; init; }
}

public sealed record MarketSnapshot(
    InstrumentDefinition Instrument,
    GexSnapshot Gex,
    MetaSnapshot Meta);
