namespace OFK.Gex.Core;

public enum InstrumentSymbol
{
    Nq,
    Es,
}

/// <summary>Defines symbol-specific JSON field suffixes without duplicating loader logic.</summary>
public sealed record InstrumentDefinition(
    InstrumentSymbol Symbol,
    string Code,
    string FieldSuffix,
    string EtfFieldSuffix,
    decimal TickSize)
{
    public string SpotField => $"spot_{FieldSuffix}";
    public string StrikeField => $"strike_{FieldSuffix}";
}

public static class InstrumentDefinitions
{
    public static InstrumentDefinition Nq { get; } =
        new(InstrumentSymbol.Nq, "NQ", "nq", "qqq", 0.25m);

    public static InstrumentDefinition Es { get; } =
        new(InstrumentSymbol.Es, "ES", "es", "spy", 0.25m);

    public static InstrumentDefinition Get(InstrumentSymbol symbol) =>
        symbol switch
        {
            InstrumentSymbol.Nq => Nq,
            InstrumentSymbol.Es => Es,
            _ => throw new ArgumentOutOfRangeException(nameof(symbol), symbol, "Unsupported instrument."),
        };

    public static InstrumentDefinition Get(string symbol) =>
        TryGet(symbol, out var definition)
            ? definition
            : throw new ArgumentException($"Unsupported instrument '{symbol}'. Expected NQ or ES.", nameof(symbol));

    public static bool TryGet(string? symbol, out InstrumentDefinition definition)
    {
        if (string.Equals(symbol?.Trim(), "NQ", StringComparison.OrdinalIgnoreCase))
        {
            definition = Nq;
            return true;
        }

        if (string.Equals(symbol?.Trim(), "ES", StringComparison.OrdinalIgnoreCase))
        {
            definition = Es;
            return true;
        }

        definition = null!;
        return false;
    }
}
