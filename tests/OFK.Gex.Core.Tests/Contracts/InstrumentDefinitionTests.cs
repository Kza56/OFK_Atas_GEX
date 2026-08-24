using OFK.Gex.Core;

namespace OFK.Gex.Core.Tests.Contracts;

public sealed class InstrumentDefinitionTests
{
    [Fact]
    public void Nq_and_es_definitions_drive_symbol_specific_json_fields()
    {
        Assert.Equal(InstrumentSymbol.Nq, InstrumentDefinitions.Nq.Symbol);
        Assert.Equal("NQ", InstrumentDefinitions.Nq.Code);
        Assert.Equal("nq", InstrumentDefinitions.Nq.FieldSuffix);
        Assert.Equal("qqq", InstrumentDefinitions.Nq.EtfFieldSuffix);
        Assert.Equal("spot_nq", InstrumentDefinitions.Nq.SpotField);
        Assert.Equal("strike_nq", InstrumentDefinitions.Nq.StrikeField);

        Assert.Equal(InstrumentSymbol.Es, InstrumentDefinitions.Es.Symbol);
        Assert.Equal("ES", InstrumentDefinitions.Es.Code);
        Assert.Equal("es", InstrumentDefinitions.Es.FieldSuffix);
        Assert.Equal("spy", InstrumentDefinitions.Es.EtfFieldSuffix);
        Assert.Equal("spot_es", InstrumentDefinitions.Es.SpotField);
        Assert.Equal("strike_es", InstrumentDefinitions.Es.StrikeField);
    }

    [Theory]
    [InlineData("NQ", InstrumentSymbol.Nq)]
    [InlineData(" nq ", InstrumentSymbol.Nq)]
    [InlineData("ES", InstrumentSymbol.Es)]
    [InlineData("es", InstrumentSymbol.Es)]
    public void Instrument_selection_is_case_insensitive(
        string symbol,
        InstrumentSymbol expected)
    {
        Assert.Equal(expected, InstrumentDefinitions.Get(symbol).Symbol);
        Assert.True(InstrumentDefinitions.TryGet(symbol, out var definition));
        Assert.Equal(expected, definition.Symbol);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("YM")]
    public void Unsupported_instrument_is_not_silently_mapped_to_nq(string? symbol)
    {
        Assert.False(InstrumentDefinitions.TryGet(symbol, out _));
        Assert.Throws<ArgumentException>(() => InstrumentDefinitions.Get(symbol!));
    }
}
