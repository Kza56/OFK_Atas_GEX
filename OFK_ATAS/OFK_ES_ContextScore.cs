// ============================================================================
//  OFK_ES_ContextScore.cs — ATAS
//  Contextual directional score for ES E-mini scalping.
//
//  Score = -100 to +100:
//   +70 to +100 : BULLISH HIGH (very high long conviction)
//   +30 to +69  : BULLISH (moderate)
//   -29 to +29  : NEUTRAL (stay flat)
//   -69 to -30  : BEARISH (moderate)
//   -100 to -70 : BEARISH HIGH (very high short conviction)
//
//  Components (gradient relative to PW-CW range):
//   - Position within PW-CW range (±30, gradient)
//   - Distance to Gamma Flip (±15, gradient)
//   - Gamma regime (zone) (±20)
//   - DEX D+/D- relative proximity (±15, gradient 25% of range)
//   - Skew 25D (±10) / Term backwardation (±5)
//   - 0DTE Pin afternoon (±5, zone 10% of range)
//
//  Blocking filters (forces score=0): VIX extreme, macro blackout,
//   macro <30min, data_quality=error
//  Attenuating filters (×0.5-0.7): VIX elevated, data partial, IVR>90
//
//  Reads the same JSON as OFK_ES_GEX_Levels via GexLoader (shared).
// ============================================================================
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Drawing;
using ATAS.Indicators;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;
using DrawingColor = System.Drawing.Color;

namespace OFK_GEX
{
    [DisplayName("OFK ES Context Score")]
    [Category("OFK Suite")]
    [Description("Contextual directional score (GEX + VIX + macro). Reads full_levels_ES.json.")]
    public class OFK_ES_ContextScore : Indicator
    {
        #region Source

        [Display(Name = "JSON Path", GroupName = "01.Source", Order = 1)]
        public string JsonPath { get; set; } = @"C:\OFK_Atas_GEX\OFK_GEX_Pipeline\data\full_levels_ES.json";

        [Display(Name = "Refresh (minutes)", GroupName = "01.Source", Order = 2)]
        [Range(1, 60)]
        public int RefreshMinutes { get; set; } = 5;

        #endregion

        #region Score parameters

        [Display(Name = "Blocking filters (VIX extr / macro / err)", GroupName = "02.Score params", Order = 4,
                 Description = "If enabled, forces the score to 0 under critical conditions")]
        public bool EnableBlockingFilters { get; set; } = true;

        [Display(Name = "Show score as text", GroupName = "02.Score params", Order = 5)]
        public bool ShowScoreText { get; set; } = true;

        [Display(Name = "Score text size", GroupName = "02.Score params", Order = 6)]
        [Range(10, 64)]
        public int ScoreFontSize { get; set; } = 24;

        #endregion

        #region Colors

        [Display(Name = "Bullish HIGH (≥70)", GroupName = "03.Colors", Order = 1)]
        public DrawingColor BullishStrongColor { get; set; } = DrawingColor.FromArgb(255, 0, 200, 80);

        [Display(Name = "Bullish (30-69)", GroupName = "03.Colors", Order = 2)]
        public DrawingColor BullishMildColor { get; set; } = DrawingColor.FromArgb(255, 100, 200, 130);

        [Display(Name = "Neutral (-29 to 29)", GroupName = "03.Colors", Order = 3)]
        public DrawingColor NeutralColor { get; set; } = DrawingColor.FromArgb(255, 140, 140, 140);

        [Display(Name = "Bearish (-69 to -30)", GroupName = "03.Colors", Order = 4)]
        public DrawingColor BearishMildColor { get; set; } = DrawingColor.FromArgb(255, 230, 150, 60);

        [Display(Name = "Bearish HIGH (≤-70)", GroupName = "03.Colors", Order = 5)]
        public DrawingColor BearishStrongColor { get; set; } = DrawingColor.FromArgb(255, 230, 50, 50);

        #endregion

        #region Private

        private volatile GexSnapshot  _levels = GexSnapshot.Empty;
        private volatile MetaSnapshot _meta   = MetaSnapshot.Empty;
        private bool     _levelsLoaded = false;
        private DateTime _lastLoadTime = DateTime.MinValue;
        private string   _loadedDate   = "";

        // Last computed score (for OnRender)
        private int    _lastScore = 0;
        private string _lastScoreReason = "";
        private string _lastScoreTag = "neutral";

        #endregion

        private static System.Windows.Media.Color ToMediaColor(DrawingColor c)
            => System.Windows.Media.Color.FromArgb(c.A, c.R, c.G, c.B);

        public OFK_ES_ContextScore() : base(true)
        {
            Panel = IndicatorDataProvider.NewPanel;
            DenyToChangePanel = true;
            EnableCustomDrawing = true;
            SubscribeToDrawingEvents(DrawingLayouts.Historical | DrawingLayouts.LatestBar | DrawingLayouts.Final);

            // 5 histogram series (one per color bucket), exclusive assignment
            DataSeries[0].Name = "Bullish HIGH";
            ((ValueDataSeries)DataSeries[0]).VisualType = VisualMode.Histogram;
            ((ValueDataSeries)DataSeries[0]).Color = ToMediaColor(BullishStrongColor);
            ((ValueDataSeries)DataSeries[0]).Width = 6;
            ((ValueDataSeries)DataSeries[0]).ShowZeroValue = false;

            DataSeries.Add(new ValueDataSeries("Bullish") {
                VisualType = VisualMode.Histogram,
                Color = ToMediaColor(BullishMildColor),
                Width = 6,
                ShowZeroValue = false
            });
            DataSeries.Add(new ValueDataSeries("Neutral") {
                VisualType = VisualMode.Histogram,
                Color = ToMediaColor(NeutralColor),
                Width = 6,
                ShowZeroValue = false
            });
            DataSeries.Add(new ValueDataSeries("Bearish") {
                VisualType = VisualMode.Histogram,
                Color = ToMediaColor(BearishMildColor),
                Width = 6,
                ShowZeroValue = false
            });
            DataSeries.Add(new ValueDataSeries("Bearish HIGH") {
                VisualType = VisualMode.Histogram,
                Color = ToMediaColor(BearishStrongColor),
                Width = 6,
                ShowZeroValue = false
            });
        }

        protected override void OnCalculate(int bar, decimal value)
        {
            if (bar == 0)
            {
                if (!_levelsLoaded) LoadLevels();
            }
            if (!_levelsLoaded) return;

            bool isLastBar = bar >= CurrentBar - 1;
            bool newDay    = _loadedDate != DateTime.Today.ToString("yyyy-MM-dd");
            bool elapsed   = RefreshMinutes > 0 && (DateTime.Now - _lastLoadTime).TotalMinutes >= RefreshMinutes;
            if (isLastBar && (newDay || elapsed)) LoadLevels();

            // Score is only computed on the live bar (no JSON history)
            if (!isLastBar) return;
            var candle = GetCandle(bar);
            if (candle == null) return;

            var (score, reason, tag) = ComputeScore(candle.Close);
            _lastScore = score;
            _lastScoreReason = reason;
            _lastScoreTag = tag;

            // Reset the 5 series to 0 on this bar then assign to the correct one
            ((ValueDataSeries)DataSeries[0])[bar] = 0;
            ((ValueDataSeries)DataSeries[1])[bar] = 0;
            ((ValueDataSeries)DataSeries[2])[bar] = 0;
            ((ValueDataSeries)DataSeries[3])[bar] = 0;
            ((ValueDataSeries)DataSeries[4])[bar] = 0;

            int idx = ScoreToBucket(score);
            ((ValueDataSeries)DataSeries[idx])[bar] = score;
        }

        private (int score, string reason, string tag) ComputeScore(decimal spot)
        {
            var lv = _levels;
            var meta = _meta;
            if (!lv.Loaded) return (0, "No data", "DATA");

            // BLOCKING FILTERS — checked first, before any scoring
            if (EnableBlockingFilters && meta.Loaded)
            {
                if (meta.VixRegime == "extreme")
                    return (0, $"VIX EXTREME ({meta.Vix:F1}) — STOP", "BLOCKED");
                if (meta.MacroInBlackout)
                    return (0, "Macro blackout IN PROGRESS", "BLOCKED");
                if (meta.MacroMinutesToNext > 0 && meta.MacroMinutesToNext <= 30)
                    return (0, $"{(string.IsNullOrEmpty(meta.MacroNextEventTitle) ? "Macro" : meta.MacroNextEventTitle)} in {meta.MacroMinutesToNext}min", "BLOCKED");
                if (meta.DataQuality == "error")
                    return (0, "Data ERROR", "BLOCKED");
            }

            int score = 0;
            var reasons = new System.Collections.Generic.List<string>();

            decimal cw = (decimal)lv.CallWallIntraday;
            decimal pw = (decimal)lv.PutWallIntraday;
            bool hasRange = cw > pw && pw > 0;
            decimal range = hasRange ? cw - pw : 0;

            // 1. WALLS POSITION (±30) — gradient in PW-CW range
            if (hasRange)
            {
                decimal ratio = (spot - pw) / range;
                int wallScore;
                if (ratio < 0m)
                {
                    wallScore = -30;
                    reasons.Add("PW broke");
                }
                else if (ratio > 1m)
                {
                    wallScore = 30;
                    reasons.Add("CW broke");
                }
                else
                {
                    wallScore = (int)Math.Round((0.5m - ratio) * 60m);
                    if (wallScore >= 15) reasons.Add("PW zone");
                    else if (wallScore <= -15) reasons.Add("CW zone");
                }
                score += wallScore;
            }

            // 2. GAMMA FLIP (±15) — gradient, 0 at GF, scales with distance
            if (lv.GammaFlip > 0 && hasRange)
            {
                decimal gf = (decimal)lv.GammaFlip;
                decimal normalized = (spot - gf) / range;
                normalized = Math.Max(-0.5m, Math.Min(0.5m, normalized));
                int gfScore = (int)Math.Round(normalized * 30m);
                score += gfScore;
                if (gfScore >= 5) reasons.Add("GF+");
                else if (gfScore <= -5) reasons.Add("GF-");
            }

            // 3. GAMMA ZONE (±20) — zone-based
            if (hasRange)
            {
                decimal ct = (decimal)lv.CTransIntraday;
                decimal pt = (decimal)lv.PTransIntraday;
                if (spot > cw)                          { score += 20;  reasons.Add("squeeze+"); }
                else if (ct > 0 && spot >= ct)          { score += 5;   reasons.Add("pos-gamma"); }
                else if (pt > 0 && spot >= pt)          { /* transition: 0 */                    }
                else if (spot >= pw)                    { score -= 5;   reasons.Add("neg-gamma"); }
                else                                    { score -= 20;  reasons.Add("squeeze-"); }
            }

            // 4. DEX D+/D- (±15) — gradient within 25% of range
            if (hasRange)
            {
                decimal dexZone = range * 0.25m;
                if (lv.DexPlusIntraday > 0)
                {
                    decimal dp = (decimal)lv.DexPlusIntraday;
                    decimal dist = dp - spot;
                    if (dist > 0 && dist < dexZone)
                    {
                        int dScore = (int)Math.Round((1m - dist / dexZone) * 15m);
                        score += dScore;
                        if (dScore >= 5) reasons.Add("D+ pull");
                    }
                }
                if (lv.DexMinusIntraday > 0)
                {
                    decimal dm = (decimal)lv.DexMinusIntraday;
                    decimal dist = spot - dm;
                    if (dist > 0 && dist < dexZone)
                    {
                        int dScore = (int)Math.Round((1m - dist / dexZone) * 15m);
                        score -= dScore;
                        if (dScore >= 5) reasons.Add("D- pull");
                    }
                }
            }

            // 5. Skew 25Δ (±10)
            if (lv.Skew25dIntraday > 0.05)      { score -= 10; reasons.Add("skew>5vp"); }
            else if (lv.Skew25dIntraday > 0.03) { score -= 5;  }

            // 6. Term IV backwardation (-5)
            if (lv.TermIntradaySlope > 0.01) { score -= 5; reasons.Add("term-back"); }

            // 7. 0DTE Pin afternoon (±5) — RTH 19:00-21:00 UTC ≈ 14h-16h ET
            int hUtc = DateTime.UtcNow.Hour;
            if ((hUtc >= 18 && hUtc <= 21) && lv.PinStrike0DTE > 0 && hasRange)
            {
                decimal pin = (decimal)lv.PinStrike0DTE;
                decimal pinZone = range * 0.10m;
                decimal pinDist = Math.Abs(spot - pin);
                if (pinDist < pinZone)
                {
                    int sign = spot > pin ? -1 : 1;
                    score += sign * 5;
                    reasons.Add("0DTE pin");
                }
            }

            // ATTENUATORS
            double mult = 1.0;
            if (meta.Loaded)
            {
                if (meta.VixRegime == "elevated")    mult *= 0.6;
                if (meta.DataQuality == "partial")   mult *= 0.7;
                if (lv.IvRankIntraday > 90)          mult *= 0.5;
            }
            score = (int)Math.Round(score * mult);
            score = Math.Max(-100, Math.Min(100, score));

            string tag = score >= 70   ? "BULLISH HIGH"
                       : score >= 30   ? "BULLISH"
                       : score > -30   ? "NEUTRAL"
                       : score > -70   ? "BEARISH"
                       :                 "BEARISH HIGH";

            string reason = reasons.Count > 0 ? string.Join(" • ", reasons) : "neutral";
            return (score, reason, tag);
        }

        private static int ScoreToBucket(int score)
        {
            if (score >= 70)  return 0; // BullishHigh
            if (score >= 30)  return 1; // Bullish
            if (score > -30)  return 2; // Neutral
            if (score > -70)  return 3; // Bearish
            return 4;                   // BearishHigh
        }

        private DrawingColor ScoreToColor(int score)
        {
            switch (ScoreToBucket(score))
            {
                case 0: return BullishStrongColor;
                case 1: return BullishMildColor;
                case 2: return NeutralColor;
                case 3: return BearishMildColor;
                default: return BearishStrongColor;
            }
        }

        private void LoadLevels()
        {
            var (gex, meta, ok) = GexLoader.Load(JsonPath, "es");
            if (!ok) { _levelsLoaded = false; return; }
            _levels       = gex;
            _meta         = meta;
            _loadedDate   = DateTime.Today.ToString("yyyy-MM-dd");
            _lastLoadTime = DateTime.Now;
            _levelsLoaded = true;
        }

        protected override void OnRender(RenderContext context, DrawingLayouts layout)
        {
            if (!ShowScoreText || !_levelsLoaded || ChartInfo == null) return;

            int fs = Math.Max(10, Math.Min(64, ScoreFontSize));
            var fontBig   = new RenderFont("Arial", fs);
            var fontSmall = new RenderFont("Arial", Math.Max(8, fs / 3));

            string scoreTxt = $"{_lastScore:+0;-0;0}  [{_lastScoreTag}]";
            var ts = context.MeasureString(scoreTxt, fontBig);
            int x = 10;
            int panelH = ChartArea.Height;

            var reasonSize = !string.IsNullOrEmpty(_lastScoreReason)
                ? context.MeasureString(_lastScoreReason, fontSmall)
                : new System.Drawing.Size(0, 0);
            int totalH = (int)ts.Height + (reasonSize.Height > 0 ? reasonSize.Height + 2 : 0);
            int y = panelH - totalH - 8;

            int bgW = (int)ts.Width + 16;
            int bgH = totalH + 6;
            context.FillRectangle(DrawingColor.FromArgb(150, 15, 15, 20),
                new Rectangle(x - 4, y - 2, bgW, bgH));

            context.DrawString(scoreTxt, fontBig, ScoreToColor(_lastScore), x + 4, y);

            if (!string.IsNullOrEmpty(_lastScoreReason))
            {
                context.DrawString(_lastScoreReason, fontSmall,
                    DrawingColor.FromArgb(220, 200, 200, 210), x + 4, y + (int)ts.Height + 2);
            }
        }

        public override string ToString() => "OFK ES Context Score";
    }
}
