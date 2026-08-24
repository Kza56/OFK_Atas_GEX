namespace OFK.Gex.Core;

/// <summary>
/// Portable, validated view of the indicator fields in full_levels_*.json.
/// Nullable values deliberately distinguish missing data from numeric zero.
/// </summary>
public sealed record GexSnapshot
{
    public decimal? Spot { get; init; }
    public decimal? GammaFlip { get; init; }
    public decimal? VolTrigger { get; init; }
    public decimal? CallWall { get; init; }
    public decimal? PutWall { get; init; }
    public decimal? RiskPivot { get; init; }
    public decimal? VannaFlip { get; init; }
    public decimal? CharmMagnet { get; init; }
    public decimal? MaxPain { get; init; }
    public decimal? ExpectedMoveHigh { get; init; }
    public decimal? ExpectedMoveLow { get; init; }
    public decimal? ExpectedMovePoints { get; init; }
    public decimal? PutCallRatio { get; init; }
    public decimal? CallWallGex { get; init; }
    public decimal? PutWallGex { get; init; }
    public decimal? TotalGex { get; init; }
    public decimal? TotalVex { get; init; }
    public decimal? TotalCex { get; init; }
    public decimal? TotalDex { get; init; }
    public int? GexRegime { get; init; }
    public int? VexRegime { get; init; }

    public decimal? CallWallIntraday { get; init; }
    public decimal? PutWallIntraday { get; init; }
    public decimal? CallWallIntradayGex { get; init; }
    public decimal? PutWallIntradayGex { get; init; }
    public int? WallsIntradayMaxDte { get; init; }
    public decimal? CTransIntraday { get; init; }
    public decimal? PTransIntraday { get; init; }
    public decimal? DexPlusIntraday { get; init; }
    public decimal? DexMinusIntraday { get; init; }
    public decimal? DexPlusIntradayDex { get; init; }
    public decimal? DexMinusIntradayDex { get; init; }

    public decimal? AtmIvIntraday { get; init; }
    public int? AtmIvIntradayDte { get; init; }
    public decimal? Skew25dIntraday { get; init; }
    public int? Skew25dIntradayDte { get; init; }
    public decimal? TermIntradaySlope { get; init; }
    public int? TermIntradayFrontDte { get; init; }
    public int? TermIntradayBackDte { get; init; }
    public decimal? TermIntradayIvFront { get; init; }
    public decimal? TermIntradayIvBack { get; init; }
    public string? TermIntradayRegime { get; init; }

    public decimal? AtmIvStructural { get; init; }
    public decimal? Skew25dStructural { get; init; }
    public decimal? IvStructuralBack { get; init; }
    public int? IvStructuralBackDte { get; init; }
    public decimal? TermStructuralSlope { get; init; }
    public string? TermStructuralRegime { get; init; }

    public IReadOnlyList<TopOpenInterestStrike> TopOpenInterest { get; init; } = [];
    public IReadOnlyList<TopOpenInterestStrike> TopOpenInterestIntraday { get; init; } = [];
    public IReadOnlyList<GexLevel> AbsoluteGexLevels { get; init; } = [];
    public IReadOnlyList<GexLevel> ExtendedGexWalls { get; init; } = [];

    public decimal? AbsGex1 => AbsoluteGexLevels.ElementAtOrDefault(0)?.Price;
    public decimal? AbsGex2 => AbsoluteGexLevels.ElementAtOrDefault(1)?.Price;
    public decimal? AbsGex3 => AbsoluteGexLevels.ElementAtOrDefault(2)?.Price;
    public decimal? GexExt1 => ExtendedGexWalls.ElementAtOrDefault(0)?.Price;
    public decimal? GexExt2 => ExtendedGexWalls.ElementAtOrDefault(1)?.Price;
    public decimal? GexExt3 => ExtendedGexWalls.ElementAtOrDefault(2)?.Price;
    public decimal? GexExt4 => ExtendedGexWalls.ElementAtOrDefault(3)?.Price;

    public decimal? MaxPain0DTE { get; init; }
    public decimal? PinStrike0DTE { get; init; }
    public decimal? CharmMagnet0DTE { get; init; }
    public long? ZeroDteOiTotal { get; init; }
    public int? ZeroDteDte { get; init; }
    public decimal? IvRankIntraday { get; init; }
    public string? IvRankIntradayStatus { get; init; }
}

public sealed record TopOpenInterestStrike(
    decimal? Strike,
    long? CallOi,
    long? PutOi,
    long? TotalOi);

public sealed record GexLevel(
    decimal? Price,
    decimal? Gex,
    string? Side = null);
