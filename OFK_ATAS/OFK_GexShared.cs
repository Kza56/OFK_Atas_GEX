// ============================================================================
//  OFK_GexShared.cs — Classes partagées entre indicateurs OFK GEX
//
//  Contient:
//   - GexSnapshot  : snapshot immutable des niveaux GEX/options/walls
//   - MetaSnapshot : snapshot immutable du contexte VIX + macro + health
//   - GexLoader    : chargeur unique du JSON full_levels_*.json (NQ ou ES)
//
//  Utilisé par:
//   - OFK_NQ_GEX_Levels.cs     (lecture full_levels_NQ.json)
//   - OFK_ES_GEX_Levels.cs     (lecture full_levels_ES.json)
//   - OFK_NQ_ContextScore.cs   (à venir)
//   - OFK_ES_ContextScore.cs   (à venir)
// ============================================================================
using System;
using System.IO;

namespace OFK_GEX
{
    // ── GexSnapshot ─────────────────────────────────────────────────────────
    public sealed class GexSnapshot
    {
        public readonly double GammaFlip, VolTrigger, CallWall, PutWall;
        public readonly double RiskPivot, VannaFlip, CharmMagnet;
        public readonly double MaxPain, ExpectedMoveHigh, ExpectedMoveLow, ExpectedMovePts;
        public readonly double TopOI1, TopOI2, TopOI3;
        public readonly long   TopOI1Vol, TopOI2Vol, TopOI3Vol;
        public readonly double Pcr;
        public readonly double CallWallGex, PutWallGex;
        public readonly double CallWallIntraday, PutWallIntraday;
        public readonly double CallWallIntradayGex, PutWallIntradayGex;
        public readonly double TopOIIntraday1, TopOIIntraday2, TopOIIntraday3;
        public readonly long   TopOIIntraday1Vol, TopOIIntraday2Vol, TopOIIntraday3Vol;
        public readonly int    WallsIntradayMaxDte;
        public readonly double CTransIntraday, PTransIntraday;
        public readonly double DexPlusIntraday, DexMinusIntraday;
        public readonly double DexPlusIntradayDex, DexMinusIntradayDex;
        public readonly double AbsGex1, AbsGex2, AbsGex3;
        public readonly double AbsGex1Gex, AbsGex2Gex, AbsGex3Gex;
        public readonly double GexExt1, GexExt2, GexExt3, GexExt4;
        public readonly double GexExt1Gex, GexExt2Gex, GexExt3Gex, GexExt4Gex;
        public readonly string GexExt1Side, GexExt2Side, GexExt3Side, GexExt4Side;
        public readonly double MaxPain0DTE, PinStrike0DTE, CharmMagnet0DTE;
        public readonly long   ZeroDTEOITotal;
        public readonly int    ZeroDTEDte;
        public readonly double IvRankIntraday;
        public readonly string IvRankIntradayStatus;
        public readonly double GexTotal, VexTotal, CexTotal, DexTotal, SpotLoaded;
        public readonly int    GexRegime, VexRegime;
        public readonly double AtmIvIntraday;
        public readonly int    AtmIvIntradayDte;
        public readonly double Skew25dIntraday;
        public readonly int    Skew25dIntradayDte;
        public readonly double TermIntradaySlope;
        public readonly int    TermIntradayFrontDte, TermIntradayBackDte;
        public readonly double TermIntradayIvFront, TermIntradayIvBack;
        public readonly string TermIntradayRegime;
        public readonly double AtmIvStructural;
        public readonly double Skew25dStructural;
        public readonly double IvStructuralBack, TermStructuralSlope;
        public readonly int    IvStructuralBackDte;
        public readonly string TermStructuralRegime;
        public readonly string TradeDate;
        public readonly bool   Loaded;

        public static readonly GexSnapshot Empty = new GexSnapshot();

        private GexSnapshot()
        {
            TermIntradayRegime = ""; TermStructuralRegime = ""; IvRankIntradayStatus = "";
            TradeDate = ""; GexExt1Side = ""; GexExt2Side = ""; GexExt3Side = ""; GexExt4Side = "";
        }

        public GexSnapshot(
            double gammaFlip, double volTrigger, double callWall, double putWall,
            double riskPivot, double vannaFlip,  double charmMagnet,
            double maxPain,   double emHigh,     double emLow,     double emPts,
            double topOI1,    double topOI2,     double topOI3,
            long   topOI1Vol, long   topOI2Vol,  long   topOI3Vol,
            double pcr,       double callWallGex, double putWallGex,
            double gexTotal,  double vexTotal,   double cexTotal,  double dexTotal,
            double spotLoaded, int gexRegime,    int vexRegime,
            double atmIvIntraday, int atmIvIntradayDte,
            double skew25dIntraday, int skew25dIntradayDte,
            string termIntradayRegime, double termIntradaySlope,
            int    termIntradayFrontDte, int termIntradayBackDte,
            double termIntradayIvFront, double termIntradayIvBack,
            double atmIvStructural, double skew25dStructural,
            double ivStructuralBack, int ivStructuralBackDte,
            double termStructuralSlope, string termStructuralRegime,
            double callWallIntraday, double putWallIntraday,
            double callWallIntradayGex, double putWallIntradayGex,
            double topOIIntraday1, double topOIIntraday2, double topOIIntraday3,
            long topOIIntraday1Vol, long topOIIntraday2Vol, long topOIIntraday3Vol,
            int    wallsIntradayMaxDte,
            double cTransIntraday, double pTransIntraday,
            double dexPlusIntraday, double dexMinusIntraday,
            double dexPlusIntradayDex, double dexMinusIntradayDex,
            double absGex1, double absGex2, double absGex3,
            double absGex1Gex, double absGex2Gex, double absGex3Gex,
            double gexExt1, double gexExt2, double gexExt3, double gexExt4,
            double gexExt1Gex, double gexExt2Gex, double gexExt3Gex, double gexExt4Gex,
            string gexExt1Side, string gexExt2Side, string gexExt3Side, string gexExt4Side,
            double maxPain0DTE, double pinStrike0DTE, double charmMagnet0DTE,
            long zeroDTEOITotal, int zeroDTEDte,
            double ivRankIntraday, string ivRankIntradayStatus,
            string tradeDate, bool loaded)
        {
            GammaFlip = gammaFlip; VolTrigger = volTrigger; CallWall = callWall; PutWall = putWall;
            RiskPivot = riskPivot; VannaFlip = vannaFlip; CharmMagnet = charmMagnet;
            MaxPain = maxPain; ExpectedMoveHigh = emHigh; ExpectedMoveLow = emLow; ExpectedMovePts = emPts;
            TopOI1 = topOI1; TopOI2 = topOI2; TopOI3 = topOI3;
            TopOI1Vol = topOI1Vol; TopOI2Vol = topOI2Vol; TopOI3Vol = topOI3Vol;
            Pcr = pcr; CallWallGex = callWallGex; PutWallGex = putWallGex;
            GexTotal = gexTotal; VexTotal = vexTotal; CexTotal = cexTotal; DexTotal = dexTotal;
            SpotLoaded = spotLoaded; GexRegime = gexRegime; VexRegime = vexRegime;
            AtmIvIntraday = atmIvIntraday; AtmIvIntradayDte = atmIvIntradayDte;
            Skew25dIntraday = skew25dIntraday; Skew25dIntradayDte = skew25dIntradayDte;
            TermIntradayRegime = termIntradayRegime ?? ""; TermIntradaySlope = termIntradaySlope;
            TermIntradayFrontDte = termIntradayFrontDte; TermIntradayBackDte = termIntradayBackDte;
            TermIntradayIvFront = termIntradayIvFront; TermIntradayIvBack = termIntradayIvBack;
            AtmIvStructural = atmIvStructural; Skew25dStructural = skew25dStructural;
            IvStructuralBack = ivStructuralBack; IvStructuralBackDte = ivStructuralBackDte;
            TermStructuralSlope = termStructuralSlope; TermStructuralRegime = termStructuralRegime ?? "";
            CallWallIntraday = callWallIntraday; PutWallIntraday = putWallIntraday;
            CallWallIntradayGex = callWallIntradayGex; PutWallIntradayGex = putWallIntradayGex;
            TopOIIntraday1 = topOIIntraday1; TopOIIntraday2 = topOIIntraday2; TopOIIntraday3 = topOIIntraday3;
            TopOIIntraday1Vol = topOIIntraday1Vol; TopOIIntraday2Vol = topOIIntraday2Vol; TopOIIntraday3Vol = topOIIntraday3Vol;
            WallsIntradayMaxDte = wallsIntradayMaxDte;
            CTransIntraday = cTransIntraday; PTransIntraday = pTransIntraday;
            DexPlusIntraday = dexPlusIntraday; DexMinusIntraday = dexMinusIntraday;
            DexPlusIntradayDex = dexPlusIntradayDex; DexMinusIntradayDex = dexMinusIntradayDex;
            AbsGex1 = absGex1; AbsGex2 = absGex2; AbsGex3 = absGex3;
            AbsGex1Gex = absGex1Gex; AbsGex2Gex = absGex2Gex; AbsGex3Gex = absGex3Gex;
            GexExt1 = gexExt1; GexExt2 = gexExt2; GexExt3 = gexExt3; GexExt4 = gexExt4;
            GexExt1Gex = gexExt1Gex; GexExt2Gex = gexExt2Gex; GexExt3Gex = gexExt3Gex; GexExt4Gex = gexExt4Gex;
            GexExt1Side = gexExt1Side ?? ""; GexExt2Side = gexExt2Side ?? "";
            GexExt3Side = gexExt3Side ?? ""; GexExt4Side = gexExt4Side ?? "";
            MaxPain0DTE = maxPain0DTE; PinStrike0DTE = pinStrike0DTE; CharmMagnet0DTE = charmMagnet0DTE;
            ZeroDTEOITotal = zeroDTEOITotal; ZeroDTEDte = zeroDTEDte;
            IvRankIntraday = ivRankIntraday; IvRankIntradayStatus = ivRankIntradayStatus ?? "";
            TradeDate = tradeDate ?? ""; Loaded = loaded;
        }
    }

    // ── MetaSnapshot ────────────────────────────────────────────────────────
    public sealed class MetaSnapshot
    {
        public readonly double Vix, Vix9d, VixDodChange, VixTermSlope;
        public readonly string VixRegime, VixTerm;
        public readonly bool   MacroInBlackout;
        public readonly string MacroBlackoutUntilUtc;
        public readonly string MacroNextEventTitle;
        public readonly int    MacroMinutesToNext;
        public readonly string JsonSchemaVersion;
        public readonly string LastUpdateUtc;
        public readonly string DataQuality;
        public readonly bool   Loaded;

        public static readonly MetaSnapshot Empty = new MetaSnapshot();
        private MetaSnapshot()
        {
            VixRegime = ""; VixTerm = ""; MacroBlackoutUntilUtc = ""; MacroNextEventTitle = "";
            JsonSchemaVersion = ""; LastUpdateUtc = ""; DataQuality = "";
        }

        public MetaSnapshot(double vix, double vix9d, double vixDod, double vixTermSlope,
            string vixRegime, string vixTerm,
            bool macroInBlackout, string macroBlackoutUntil,
            string macroNextEventTitle, int macroMinutesToNext,
            string jsonSchemaVersion, string lastUpdateUtc, string dataQuality,
            bool loaded)
        {
            Vix = vix; Vix9d = vix9d; VixDodChange = vixDod; VixTermSlope = vixTermSlope;
            VixRegime = vixRegime ?? ""; VixTerm = vixTerm ?? "";
            MacroInBlackout = macroInBlackout;
            MacroBlackoutUntilUtc = macroBlackoutUntil ?? "";
            MacroNextEventTitle = macroNextEventTitle ?? "";
            MacroMinutesToNext = macroMinutesToNext;
            JsonSchemaVersion = jsonSchemaVersion ?? "";
            LastUpdateUtc     = lastUpdateUtc     ?? "";
            DataQuality       = dataQuality       ?? "";
            Loaded = loaded;
        }
    }

    // ── OfkUtils : helpers partagés ──────────────────────────────────────────
    public static class OfkUtils
    {
        /// <summary>
        /// Résout un chemin d'exécutable. Si <paramref name="exePath"/> est un
        /// chemin absolu existant, retourne tel quel. Sinon, cherche le nom
        /// dans la variable d'environnement PATH (utile pour spawn Process.Start
        /// avec UseShellExecute = false, qui ne résout pas PATH par défaut).
        /// Fallback : retourne <paramref name="exePath"/> tel quel.
        /// </summary>
        public static string ResolveExe(string exePath)
        {
            if (string.IsNullOrWhiteSpace(exePath)) return exePath;
            try
            {
                if (System.IO.Path.IsPathRooted(exePath) && File.Exists(exePath))
                    return exePath;
                string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
                foreach (var dir in pathEnv.Split(';'))
                {
                    string trimmed = dir.Trim().Trim('"');
                    if (string.IsNullOrEmpty(trimmed)) continue;
                    try
                    {
                        string candidate = System.IO.Path.Combine(trimmed, exePath);
                        if (File.Exists(candidate)) return candidate;
                    }
                    catch { }
                }
            }
            catch { }
            return exePath;
        }
    }

    // ── GexLoader ───────────────────────────────────────────────────────────
    public static class GexLoader
    {
        /// <summary>
        /// Charge un fichier full_levels_*.json et retourne (GexSnapshot, MetaSnapshot, ok).
        /// symbol = "nq" ou "es" — détermine les suffixes de champ JSON.
        /// </summary>
        public static (GexSnapshot gex, MetaSnapshot meta, bool ok) Load(string jsonPath, string symbol)
        {
            if (string.IsNullOrEmpty(jsonPath) || !File.Exists(jsonPath))
                return (GexSnapshot.Empty, MetaSnapshot.Empty, false);
            try
            {
                string json = File.ReadAllText(jsonPath);
                string sym  = (symbol ?? "nq").ToLowerInvariant();

                double spot = ParseDouble(json, $"spot_{sym}");
                if (spot <= 0) spot = ParseDouble(json, "spot");

                double emHigh = ParseDouble(json, $"range_haut_{sym}");
                double emLow  = ParseDouble(json, $"range_bas_{sym}");
                double emPts  = ParseDouble(json, $"expected_move_{sym}");

                double oi1, oi2, oi3; long v1, v2, v3;
                ParseTopOIArray(json, "top_oi_strikes", $"strike_{sym}",
                    out oi1, out v1, out oi2, out v2, out oi3, out v3);

                double oid1, oid2, oid3; long vid1, vid2, vid3;
                ParseTopOIArray(json, "top_oi_intraday", $"strike_{sym}",
                    out oid1, out vid1, out oid2, out vid2, out oid3, out vid3);

                var gex = new GexSnapshot(
                    gammaFlip:   ParseDouble(json, "gamma_flip"),
                    volTrigger:  ParseDouble(json, "vol_trigger"),
                    callWall:    ParseDouble(json, "call_wall"),
                    putWall:     ParseDouble(json, "put_wall"),
                    riskPivot:   ParseDouble(json, "risk_pivot"),
                    vannaFlip:   ParseDouble(json, "vanna_flip"),
                    charmMagnet: ParseDouble(json, "charm_magnet"),
                    maxPain:     ParseDouble(json, $"max_pain_{sym}"),
                    emHigh:      emHigh,
                    emLow:       emLow,
                    emPts:       emPts,
                    topOI1: oi1, topOI2: oi2, topOI3: oi3,
                    topOI1Vol: v1, topOI2Vol: v2, topOI3Vol: v3,
                    pcr:         ParseDouble(json, "pcr"),
                    callWallGex: ParseDouble(json, "call_wall_gex"),
                    putWallGex:  ParseDouble(json, "put_wall_gex"),
                    gexTotal:    ParseDouble(json, "total_gex"),
                    vexTotal:    ParseDouble(json, "total_vex"),
                    cexTotal:    ParseDouble(json, "total_cex"),
                    dexTotal:    ParseDouble(json, "total_dex"),
                    spotLoaded:  spot,
                    gexRegime:   (int)ParseDouble(json, "gex_regime"),
                    vexRegime:   (int)ParseDouble(json, "vex_regime"),
                    atmIvIntraday:        ParseDouble(json, "atm_iv_intraday"),
                    atmIvIntradayDte:     (int)ParseDouble(json, "atm_iv_intraday_dte"),
                    skew25dIntraday:      ParseDouble(json, "skew_25d_intraday"),
                    skew25dIntradayDte:   (int)ParseDouble(json, "skew_25d_intraday_dte"),
                    termIntradayRegime:   ParseString(json, "term_intraday_regime"),
                    termIntradaySlope:    ParseDouble(json, "term_intraday_slope"),
                    termIntradayFrontDte: (int)ParseDouble(json, "term_intraday_front_dte"),
                    termIntradayBackDte:  (int)ParseDouble(json, "term_intraday_back_dte"),
                    termIntradayIvFront:  ParseDouble(json, "term_intraday_iv_front"),
                    termIntradayIvBack:   ParseDouble(json, "term_intraday_iv_back"),
                    atmIvStructural:      ParseDouble(json, "atm_iv_structural"),
                    skew25dStructural:    ParseDouble(json, "skew_25d_structural"),
                    ivStructuralBack:     ParseDouble(json, "iv_structural_back"),
                    ivStructuralBackDte:  (int)ParseDouble(json, "iv_structural_back_dte"),
                    termStructuralSlope:  ParseDouble(json, "term_structural_slope"),
                    termStructuralRegime: ParseString(json, "term_structural_regime"),
                    callWallIntraday:     ParseDouble(json, $"call_wall_intraday_{sym}"),
                    putWallIntraday:      ParseDouble(json, $"put_wall_intraday_{sym}"),
                    callWallIntradayGex:  ParseDouble(json, "call_wall_intraday_gex"),
                    putWallIntradayGex:   ParseDouble(json, "put_wall_intraday_gex"),
                    topOIIntraday1: oid1, topOIIntraday2: oid2, topOIIntraday3: oid3,
                    topOIIntraday1Vol: vid1, topOIIntraday2Vol: vid2, topOIIntraday3Vol: vid3,
                    wallsIntradayMaxDte:  (int)ParseDouble(json, "walls_intraday_max_dte"),
                    cTransIntraday:       ParseDouble(json, $"c_trans_intraday_{sym}"),
                    pTransIntraday:       ParseDouble(json, $"p_trans_intraday_{sym}"),
                    dexPlusIntraday:      ParseDouble(json, $"dex_plus_intraday_{sym}"),
                    dexMinusIntraday:     ParseDouble(json, $"dex_minus_intraday_{sym}"),
                    dexPlusIntradayDex:   ParseDouble(json, "dex_plus_intraday_dex"),
                    dexMinusIntradayDex:  ParseDouble(json, "dex_minus_intraday_dex"),
                    absGex1: ParseDouble(json, $"abs_gex_intraday_1_{sym}"),
                    absGex2: ParseDouble(json, $"abs_gex_intraday_2_{sym}"),
                    absGex3: ParseDouble(json, $"abs_gex_intraday_3_{sym}"),
                    absGex1Gex: ParseDouble(json, "abs_gex_intraday_1_gex"),
                    absGex2Gex: ParseDouble(json, "abs_gex_intraday_2_gex"),
                    absGex3Gex: ParseDouble(json, "abs_gex_intraday_3_gex"),
                    gexExt1: ParseDouble(json, $"gex_wall_ext_1_{sym}"),
                    gexExt2: ParseDouble(json, $"gex_wall_ext_2_{sym}"),
                    gexExt3: ParseDouble(json, $"gex_wall_ext_3_{sym}"),
                    gexExt4: ParseDouble(json, $"gex_wall_ext_4_{sym}"),
                    gexExt1Gex: ParseDouble(json, "gex_wall_ext_1_gex"),
                    gexExt2Gex: ParseDouble(json, "gex_wall_ext_2_gex"),
                    gexExt3Gex: ParseDouble(json, "gex_wall_ext_3_gex"),
                    gexExt4Gex: ParseDouble(json, "gex_wall_ext_4_gex"),
                    gexExt1Side: ParseString(json, "gex_wall_ext_1_side"),
                    gexExt2Side: ParseString(json, "gex_wall_ext_2_side"),
                    gexExt3Side: ParseString(json, "gex_wall_ext_3_side"),
                    gexExt4Side: ParseString(json, "gex_wall_ext_4_side"),
                    maxPain0DTE:    ParseDouble(json, $"max_pain_0dte_{sym}"),
                    pinStrike0DTE:  ParseDouble(json, $"pin_strike_0dte_{sym}"),
                    charmMagnet0DTE:ParseDouble(json, $"charm_magnet_0dte_{sym}"),
                    zeroDTEOITotal: (long)ParseDouble(json, "zero_dte_oi_total"),
                    zeroDTEDte:     (int)ParseDouble(json, "zero_dte_dte"),
                    ivRankIntraday:       ParseNestedDouble(json, "iv_rank_intraday", "ivr"),
                    ivRankIntradayStatus: ParseNestedString(json, "iv_rank_intraday", "status"),
                    tradeDate:    ParseString(json, "trade_date"),
                    loaded:       true
                );

                var meta = new MetaSnapshot(
                    vix:                 ParseDouble(json, "vix"),
                    vix9d:                ParseDouble(json, "vix9d"),
                    vixDod:               ParseDouble(json, "vix_dod_change"),
                    vixTermSlope:         ParseDouble(json, "vix_term_slope"),
                    vixRegime:            ParseString(json, "vix_regime"),
                    vixTerm:              ParseString(json, "vix_term"),
                    macroInBlackout:      ParseBool(json, "macro_in_blackout"),
                    macroBlackoutUntil:   ParseString(json, "macro_blackout_until"),
                    macroNextEventTitle:  ParseNestedString(json, "macro_next_event", "title"),
                    macroMinutesToNext:   (int)ParseDouble(json, "macro_minutes_to_next"),
                    jsonSchemaVersion:    ParseString(json, "json_schema_version"),
                    lastUpdateUtc:        ParseString(json, "last_update_utc"),
                    dataQuality:          ParseString(json, "data_quality"),
                    loaded:               true);

                return (gex, meta, true);
            }
            catch (Exception)
            {
                return (GexSnapshot.Empty, MetaSnapshot.Empty, false);
            }
        }

        // ── Replay intraday : listing + chargement de snapshots horodatés ─────

        public readonly struct SnapshotInfo
        {
            public readonly DateTime Timestamp; // local time (HHMM in filename)
            public readonly string   Path;
            public SnapshotInfo(DateTime ts, string path) { Timestamp = ts; Path = path; }
        }

        /// <summary>
        /// Liste les snapshots intraday d'un symbole pour une date locale donnée.
        /// Pattern attendu : {SYMBOL}_full_levels_{YYYYMMDD}_{HHMM}.json
        /// Renvoie la liste triée par timestamp croissant (vide si dossier absent).
        /// symbol = "NQ" ou "ES" (insensible à la casse, normalisé en majuscules).
        /// </summary>
        public static System.Collections.Generic.List<SnapshotInfo> ListSnapshots(
            string intradayDir, string symbol, DateTime localDate)
        {
            var result = new System.Collections.Generic.List<SnapshotInfo>();
            if (string.IsNullOrEmpty(intradayDir) || !Directory.Exists(intradayDir))
                return result;
            string sym = (symbol ?? "NQ").ToUpperInvariant();
            string dateStr = localDate.ToString("yyyyMMdd");
            string pattern = $"{sym}_full_levels_{dateStr}_*.json";
            try
            {
                foreach (var path in Directory.GetFiles(intradayDir, pattern))
                {
                    string stem = Path.GetFileNameWithoutExtension(path);
                    var parts = stem.Split('_');
                    if (parts.Length < 5) continue;
                    string hhmm = parts[parts.Length - 1];
                    if (hhmm.Length != 4) continue;
                    if (!int.TryParse(hhmm.Substring(0, 2), out int hh)) continue;
                    if (!int.TryParse(hhmm.Substring(2, 2), out int mm)) continue;
                    var ts = new DateTime(localDate.Year, localDate.Month, localDate.Day, hh, mm, 0,
                                          DateTimeKind.Local);
                    result.Add(new SnapshotInfo(ts, path));
                }
            }
            catch (Exception) { }
            result.Sort((a, b) => a.Timestamp.CompareTo(b.Timestamp));
            return result;
        }

        /// <summary>
        /// Charge un snapshot précis (chemin déjà résolu via ListSnapshots).
        /// symbol = "nq" ou "es" pour adapter les suffixes de champ JSON.
        /// </summary>
        public static (GexSnapshot gex, MetaSnapshot meta, bool ok) LoadSnapshotPath(
            string snapshotPath, string symbol)
            => Load(snapshotPath, symbol);

        // ── Helpers de parsing JSON manuel (rapide, sans dépendance externe) ──

        public static double ParseDouble(string json, string key)
        {
            int pos = json.IndexOf("\"" + key + "\"", StringComparison.Ordinal); if (pos < 0) return 0;
            int colon = json.IndexOf(':', pos); if (colon < 0) return 0;
            int start = colon + 1;
            while (start < json.Length && (json[start]==' '||json[start]=='\t')) start++;
            int end = start;
            while (end < json.Length && (char.IsDigit(json[end])||json[end]=='.'||json[end]=='-'||json[end]=='e'||json[end]=='E'||json[end]=='+')) end++;
            if (end == start) return 0;
            return double.TryParse(json.Substring(start, end-start),
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out double v) ? v : 0;
        }

        public static double ParseDoubleInStr(string s, string key)
        {
            int pos = s.IndexOf("\"" + key + "\"", StringComparison.Ordinal); if (pos < 0) return 0;
            int colon = s.IndexOf(':', pos); if (colon < 0) return 0;
            int start = colon + 1;
            while (start < s.Length && (s[start]==' '||s[start]=='\t')) start++;
            int end = start;
            while (end < s.Length && (char.IsDigit(s[end])||s[end]=='.'||s[end]=='-'||s[end]=='e'||s[end]=='E'||s[end]=='+')) end++;
            if (end == start) return 0;
            return double.TryParse(s.Substring(start, end-start),
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out double v) ? v : 0;
        }

        public static bool ParseBool(string json, string key)
        {
            int pos = json.IndexOf("\"" + key + "\"", StringComparison.Ordinal); if (pos < 0) return false;
            int colon = json.IndexOf(':', pos); if (colon < 0) return false;
            int start = colon + 1;
            while (start < json.Length && (json[start]==' '||json[start]=='\t')) start++;
            return start < json.Length - 3 &&
                   string.Compare(json, start, "true", 0, 4, StringComparison.OrdinalIgnoreCase) == 0;
        }

        public static string ParseString(string json, string key)
        {
            int pos = json.IndexOf("\"" + key + "\"", StringComparison.Ordinal); if (pos < 0) return "";
            int colon = json.IndexOf(':', pos); if (colon < 0) return "";
            int q1 = json.IndexOf('"', colon+1); if (q1 < 0) return "";
            int q2 = json.IndexOf('"', q1+1);    if (q2 < 0) return "";
            return json.Substring(q1+1, q2-q1-1);
        }

        public static double ParseNestedDouble(string json, string parentKey, string key)
        {
            int pos = json.IndexOf("\"" + parentKey + "\"", StringComparison.Ordinal); if (pos < 0) return 0;
            int ob = json.IndexOf('{', pos); if (ob < 0) return 0;
            int depth = 1, end = ob + 1;
            while (end < json.Length && depth > 0)
            {
                if (json[end] == '{') depth++;
                else if (json[end] == '}') depth--;
                end++;
            }
            if (depth != 0) return 0;
            return ParseDoubleInStr(json.Substring(ob, end - ob), key);
        }

        public static string ParseNestedString(string json, string parentKey, string key)
        {
            int pos = json.IndexOf("\"" + parentKey + "\"", StringComparison.Ordinal); if (pos < 0) return "";
            int ob = json.IndexOf('{', pos); if (ob < 0) return "";
            int depth = 1, end = ob + 1;
            while (end < json.Length && depth > 0)
            {
                if (json[end] == '{') depth++;
                else if (json[end] == '}') depth--;
                end++;
            }
            if (depth != 0) return "";
            string sub = json.Substring(ob, end - ob);
            return ParseString(sub, key);
        }

        public static void ParseTopOIArray(string json, string arrKey, string strikeKey,
            out double s1, out long v1, out double s2, out long v2, out double s3, out long v3)
        {
            s1 = s2 = s3 = 0; v1 = v2 = v3 = 0;
            int arrStart = json.IndexOf("\"" + arrKey + "\"", StringComparison.Ordinal);
            if (arrStart < 0) return;
            int bracket = json.IndexOf('[', arrStart);
            if (bracket < 0) return;
            int end = json.IndexOf(']', bracket);
            if (end < 0) return;
            string arr = json.Substring(bracket, end - bracket + 1);

            double[] strikes = new double[3]; long[] vols = new long[3]; int found = 0;
            int pos = 0;
            while (found < 3)
            {
                int ob = arr.IndexOf('{', pos); if (ob < 0) break;
                int cb = arr.IndexOf('}', ob);  if (cb < 0) break;
                string obj = arr.Substring(ob, cb - ob + 1);
                double sNq  = ParseDoubleInStr(obj, strikeKey);
                double totOI= ParseDoubleInStr(obj, "total_oi");
                if (sNq > 0) { strikes[found] = sNq; vols[found] = (long)totOI; found++; }
                pos = cb + 1;
            }
            if (found > 0) { s1 = strikes[0]; v1 = vols[0]; }
            if (found > 1) { s2 = strikes[1]; v2 = vols[1]; }
            if (found > 2) { s3 = strikes[2]; v3 = vols[2]; }
        }
    }
}
