using System.Text.Json;
using System.Text.Json.Serialization;

namespace OFK.Gex.Core;

internal sealed class FullLevelsDocument
{
    [JsonPropertyName("generated_at")] public string? GeneratedAt { get; init; }
    [JsonPropertyName("trade_date")] public string? TradeDate { get; init; }
    [JsonPropertyName("json_schema_version")] public string? JsonSchemaVersion { get; init; }
    [JsonPropertyName("last_update_utc")] public string? LastUpdateUtc { get; init; }
    [JsonPropertyName("data_quality")] public string? DataQuality { get; init; }

    [JsonPropertyName("spot_nq")] public decimal? SpotNq { get; init; }
    [JsonPropertyName("spot_es")] public decimal? SpotEs { get; init; }
    [JsonPropertyName("gamma_flip")] public decimal? GammaFlip { get; init; }
    [JsonPropertyName("vol_trigger")] public decimal? VolTrigger { get; init; }
    [JsonPropertyName("call_wall")] public decimal? CallWall { get; init; }
    [JsonPropertyName("put_wall")] public decimal? PutWall { get; init; }
    [JsonPropertyName("risk_pivot")] public decimal? RiskPivot { get; init; }
    [JsonPropertyName("vanna_flip")] public decimal? VannaFlip { get; init; }
    [JsonPropertyName("charm_magnet")] public decimal? CharmMagnet { get; init; }
    [JsonPropertyName("max_pain_nq")] public decimal? MaxPainNq { get; init; }
    [JsonPropertyName("max_pain_es")] public decimal? MaxPainEs { get; init; }
    [JsonPropertyName("expected_move_nq")] public decimal? ExpectedMoveNq { get; init; }
    [JsonPropertyName("expected_move_es")] public decimal? ExpectedMoveEs { get; init; }
    [JsonPropertyName("range_haut_nq")] public decimal? RangeHighNq { get; init; }
    [JsonPropertyName("range_haut_es")] public decimal? RangeHighEs { get; init; }
    [JsonPropertyName("range_bas_nq")] public decimal? RangeLowNq { get; init; }
    [JsonPropertyName("range_bas_es")] public decimal? RangeLowEs { get; init; }
    [JsonPropertyName("pcr")] public decimal? Pcr { get; init; }
    [JsonPropertyName("call_wall_gex")] public decimal? CallWallGex { get; init; }
    [JsonPropertyName("put_wall_gex")] public decimal? PutWallGex { get; init; }
    [JsonPropertyName("total_gex")] public decimal? TotalGex { get; init; }
    [JsonPropertyName("total_vex")] public decimal? TotalVex { get; init; }
    [JsonPropertyName("total_cex")] public decimal? TotalCex { get; init; }
    [JsonPropertyName("total_dex")] public decimal? TotalDex { get; init; }
    [JsonPropertyName("gex_regime")] public int? GexRegime { get; init; }
    [JsonPropertyName("vex_regime")] public int? VexRegime { get; init; }

    [JsonPropertyName("call_wall_intraday_nq")] public decimal? CallWallIntradayNq { get; init; }
    [JsonPropertyName("call_wall_intraday_es")] public decimal? CallWallIntradayEs { get; init; }
    [JsonPropertyName("put_wall_intraday_nq")] public decimal? PutWallIntradayNq { get; init; }
    [JsonPropertyName("put_wall_intraday_es")] public decimal? PutWallIntradayEs { get; init; }
    [JsonPropertyName("call_wall_intraday_gex")] public decimal? CallWallIntradayGex { get; init; }
    [JsonPropertyName("put_wall_intraday_gex")] public decimal? PutWallIntradayGex { get; init; }
    [JsonPropertyName("walls_intraday_max_dte")] public int? WallsIntradayMaxDte { get; init; }
    [JsonPropertyName("c_trans_intraday_nq")] public decimal? CTransIntradayNq { get; init; }
    [JsonPropertyName("c_trans_intraday_es")] public decimal? CTransIntradayEs { get; init; }
    [JsonPropertyName("p_trans_intraday_nq")] public decimal? PTransIntradayNq { get; init; }
    [JsonPropertyName("p_trans_intraday_es")] public decimal? PTransIntradayEs { get; init; }
    [JsonPropertyName("dex_plus_intraday_nq")] public decimal? DexPlusIntradayNq { get; init; }
    [JsonPropertyName("dex_plus_intraday_es")] public decimal? DexPlusIntradayEs { get; init; }
    [JsonPropertyName("dex_minus_intraday_nq")] public decimal? DexMinusIntradayNq { get; init; }
    [JsonPropertyName("dex_minus_intraday_es")] public decimal? DexMinusIntradayEs { get; init; }
    [JsonPropertyName("dex_plus_intraday_dex")] public decimal? DexPlusIntradayDex { get; init; }
    [JsonPropertyName("dex_minus_intraday_dex")] public decimal? DexMinusIntradayDex { get; init; }

    [JsonPropertyName("atm_iv_intraday")] public decimal? AtmIvIntraday { get; init; }
    [JsonPropertyName("atm_iv_intraday_dte")] public int? AtmIvIntradayDte { get; init; }
    [JsonPropertyName("skew_25d_intraday")] public decimal? Skew25dIntraday { get; init; }
    [JsonPropertyName("skew_25d_intraday_dte")] public int? Skew25dIntradayDte { get; init; }
    [JsonPropertyName("term_intraday_slope")] public decimal? TermIntradaySlope { get; init; }
    [JsonPropertyName("term_intraday_front_dte")] public int? TermIntradayFrontDte { get; init; }
    [JsonPropertyName("term_intraday_back_dte")] public int? TermIntradayBackDte { get; init; }
    [JsonPropertyName("term_intraday_iv_front")] public decimal? TermIntradayIvFront { get; init; }
    [JsonPropertyName("term_intraday_iv_back")] public decimal? TermIntradayIvBack { get; init; }
    [JsonPropertyName("term_intraday_regime")] public string? TermIntradayRegime { get; init; }
    [JsonPropertyName("atm_iv_structural")] public decimal? AtmIvStructural { get; init; }
    [JsonPropertyName("skew_25d_structural")] public decimal? Skew25dStructural { get; init; }
    [JsonPropertyName("iv_structural_back")] public decimal? IvStructuralBack { get; init; }
    [JsonPropertyName("iv_structural_back_dte")] public int? IvStructuralBackDte { get; init; }
    [JsonPropertyName("term_structural_slope")] public decimal? TermStructuralSlope { get; init; }
    [JsonPropertyName("term_structural_regime")] public string? TermStructuralRegime { get; init; }

    [JsonPropertyName("top_oi_strikes")] public List<TopOpenInterestDocument>? TopOiStrikes { get; init; }
    [JsonPropertyName("top_oi_intraday")] public List<TopOpenInterestDocument>? TopOiIntraday { get; init; }
    [JsonPropertyName("iv_rank_intraday")] public IvRankDocument? IvRankIntraday { get; init; }

    [JsonPropertyName("max_pain_0dte_nq")] public decimal? MaxPain0DteNq { get; init; }
    [JsonPropertyName("max_pain_0dte_es")] public decimal? MaxPain0DteEs { get; init; }
    [JsonPropertyName("pin_strike_0dte_nq")] public decimal? PinStrike0DteNq { get; init; }
    [JsonPropertyName("pin_strike_0dte_es")] public decimal? PinStrike0DteEs { get; init; }
    [JsonPropertyName("charm_magnet_0dte_nq")] public decimal? CharmMagnet0DteNq { get; init; }
    [JsonPropertyName("charm_magnet_0dte_es")] public decimal? CharmMagnet0DteEs { get; init; }
    [JsonPropertyName("zero_dte_oi_total")] public decimal? ZeroDteOiTotal { get; init; }
    [JsonPropertyName("zero_dte_dte")] public int? ZeroDteDte { get; init; }

    [JsonPropertyName("abs_gex_intraday_1_nq")] public decimal? AbsGex1Nq { get; init; }
    [JsonPropertyName("abs_gex_intraday_1_es")] public decimal? AbsGex1Es { get; init; }
    [JsonPropertyName("abs_gex_intraday_2_nq")] public decimal? AbsGex2Nq { get; init; }
    [JsonPropertyName("abs_gex_intraday_2_es")] public decimal? AbsGex2Es { get; init; }
    [JsonPropertyName("abs_gex_intraday_3_nq")] public decimal? AbsGex3Nq { get; init; }
    [JsonPropertyName("abs_gex_intraday_3_es")] public decimal? AbsGex3Es { get; init; }
    [JsonPropertyName("abs_gex_intraday_1_gex")] public decimal? AbsGex1Gex { get; init; }
    [JsonPropertyName("abs_gex_intraday_2_gex")] public decimal? AbsGex2Gex { get; init; }
    [JsonPropertyName("abs_gex_intraday_3_gex")] public decimal? AbsGex3Gex { get; init; }
    [JsonPropertyName("gex_wall_ext_1_nq")] public decimal? GexExt1Nq { get; init; }
    [JsonPropertyName("gex_wall_ext_1_es")] public decimal? GexExt1Es { get; init; }
    [JsonPropertyName("gex_wall_ext_2_nq")] public decimal? GexExt2Nq { get; init; }
    [JsonPropertyName("gex_wall_ext_2_es")] public decimal? GexExt2Es { get; init; }
    [JsonPropertyName("gex_wall_ext_3_nq")] public decimal? GexExt3Nq { get; init; }
    [JsonPropertyName("gex_wall_ext_3_es")] public decimal? GexExt3Es { get; init; }
    [JsonPropertyName("gex_wall_ext_4_nq")] public decimal? GexExt4Nq { get; init; }
    [JsonPropertyName("gex_wall_ext_4_es")] public decimal? GexExt4Es { get; init; }
    [JsonPropertyName("gex_wall_ext_1_gex")] public decimal? GexExt1Gex { get; init; }
    [JsonPropertyName("gex_wall_ext_2_gex")] public decimal? GexExt2Gex { get; init; }
    [JsonPropertyName("gex_wall_ext_3_gex")] public decimal? GexExt3Gex { get; init; }
    [JsonPropertyName("gex_wall_ext_4_gex")] public decimal? GexExt4Gex { get; init; }
    [JsonPropertyName("gex_wall_ext_1_side")] public string? GexExt1Side { get; init; }
    [JsonPropertyName("gex_wall_ext_2_side")] public string? GexExt2Side { get; init; }
    [JsonPropertyName("gex_wall_ext_3_side")] public string? GexExt3Side { get; init; }
    [JsonPropertyName("gex_wall_ext_4_side")] public string? GexExt4Side { get; init; }

    [JsonPropertyName("vix")] public decimal? Vix { get; init; }
    [JsonPropertyName("vix9d")] public decimal? Vix9d { get; init; }
    [JsonPropertyName("vix_dod_change")] public decimal? VixDodChange { get; init; }
    [JsonPropertyName("vix_term_slope")] public decimal? VixTermSlope { get; init; }
    [JsonPropertyName("vix_regime")] public string? VixRegime { get; init; }
    [JsonPropertyName("vix_term")] public string? VixTerm { get; init; }
    [JsonPropertyName("macro_in_blackout")] public bool? MacroInBlackout { get; init; }
    [JsonPropertyName("macro_blackout_until")] public string? MacroBlackoutUntil { get; init; }
    [JsonPropertyName("macro_current_event")] public JsonElement? MacroCurrentEvent { get; init; }
    [JsonPropertyName("macro_next_event")] public JsonElement? MacroNextEvent { get; init; }
    [JsonPropertyName("macro_minutes_to_next")] public int? MacroMinutesToNext { get; init; }
}

internal sealed class TopOpenInterestDocument
{
    [JsonPropertyName("strike_nq")] public decimal? StrikeNq { get; init; }
    [JsonPropertyName("strike_es")] public decimal? StrikeEs { get; init; }
    [JsonPropertyName("call_oi")] public decimal? CallOi { get; init; }
    [JsonPropertyName("put_oi")] public decimal? PutOi { get; init; }
    [JsonPropertyName("total_oi")] public decimal? TotalOi { get; init; }
}

internal sealed class IvRankDocument
{
    [JsonPropertyName("ivr")] public decimal? Ivr { get; init; }
    [JsonPropertyName("status")] public string? Status { get; init; }
}
