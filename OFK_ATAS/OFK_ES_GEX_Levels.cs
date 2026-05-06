// ============================================================================
//  OFK_ES_GEX_Levels.cs — ATAS
//  Lit full_levels_ES.json et affiche tous les niveaux GEX + Options ES.
//
//  Niveaux chart : Gamma Flip, Vol Trigger, Call Wall, Put Wall, Risk Pivot,
//                  Vanna Flip, Charm Magnet, Max Pain, EM High, EM Low,
//                  Top OI #1, Top OI #2, Top OI #3
//
//  Panel : GEX LEVELS (run_morning_ES.py) + Briefing (ouvre PDF ES)
// ============================================================================
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using ATAS.Indicators;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;
using DrawingColor = System.Drawing.Color;

namespace OFK_GEX
{
    [DisplayName("OFK ES GEX Levels")]
    [Category("OFK Suite")]
    [Description("Niveaux Greeks Options ES. Lit full_levels_ES.json.")]
    public class OFK_ES_GEX_Levels : Indicator
    {
        #region Snapshot

        // GexSnapshot, MetaSnapshot et GexLoader sont définis dans OFK_GexShared.cs
        // (partagés avec OFK_NQ_GEX_Levels et OFK_*_ContextScore).

        // Version du schéma JSON attendue par cet indicateur (synchro avec config.py)
        private const string EXPECTED_JSON_SCHEMA_VERSION = "1.0";

        #endregion
        #region 01.Source

        [Display(Name = "JSON Path", GroupName = "01.Source", Order = 1)]
        public string JsonPath { get; set; } = @"C:\Users\steph\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline\data\full_levels_ES.json";

        [Display(Name = "Refresh (minutes)", GroupName = "01.Source", Order = 2)]
        [Range(1, 240)]
        public int RefreshMinutes { get; set; } = 30;

        #endregion

        #region 02.Niveaux GEX

        [Display(Name = "Gamma Flip",            GroupName = "02.Niveaux GEX", Order = 1)]
        public bool ShowGammaFlip   { get; set; } = true;
        [Display(Name = "Vol Trigger",           GroupName = "02.Niveaux GEX", Order = 2)]
        public bool ShowVolTrigger  { get; set; } = true;
        [Display(Name = "Call Wall",             GroupName = "02.Niveaux GEX", Order = 3)]
        public bool ShowCallWall    { get; set; } = true;
        [Display(Name = "Put Wall",              GroupName = "02.Niveaux GEX", Order = 4)]
        public bool ShowPutWall     { get; set; } = true;
        [Display(Name = "Risk Pivot (trapdoor)", GroupName = "02.Niveaux GEX", Order = 5)]
        public bool ShowRiskPivot   { get; set; } = true;

        #endregion

        #region 02b.Niveaux INTRADAY (CBOE 0-7 DTE)

        [Display(Name = "Call Wall intraday",    GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 1)]
        public bool ShowCallWallIntraday  { get; set; } = true;
        [Display(Name = "Put Wall intraday",     GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 2)]
        public bool ShowPutWallIntraday   { get; set; } = true;
        [Display(Name = "Top OI intraday #1",    GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 3)]
        public bool ShowTopOIIntraday1    { get; set; } = true;
        [Display(Name = "Top OI intraday #2",    GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 4)]
        public bool ShowTopOIIntraday2    { get; set; } = true;
        [Display(Name = "Top OI intraday #3",    GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 5)]
        public bool ShowTopOIIntraday3    { get; set; } = true;
        [Display(Name = "cTrans (call dom.)",    GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 6,
                 Description = "Niveau au-dessus duquel la gamma call domine (TanukiTrade-style)")]
        public bool ShowCTransIntraday    { get; set; } = true;
        [Display(Name = "pTrans (put dom.)",     GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 7,
                 Description = "Niveau en-dessous duquel la gamma put domine (TanukiTrade-style)")]
        public bool ShowPTransIntraday    { get; set; } = true;
        [Display(Name = "D+ (delta+ max)",       GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 8,
                 Description = "DEX positif max — strike où dealers achètent agressivement (bullish hedging)")]
        public bool ShowDexPlusIntraday   { get; set; } = true;
        [Display(Name = "D- (delta- max)",       GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 9,
                 Description = "DEX négatif max — strike où dealers vendent agressivement (bearish hedging)")]
        public bool ShowDexMinusIntraday  { get; set; } = true;
        [Display(Name = "Abs GEX Ab1",           GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 10,
                 Description = "Strike avec gamma absolue (call+put) max — pin risk fort")]
        public bool ShowAbsGex1           { get; set; } = true;
        [Display(Name = "Abs GEX Ab2",           GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 11)]
        public bool ShowAbsGex2           { get; set; } = true;
        [Display(Name = "Abs GEX Ab3",           GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 12)]
        public bool ShowAbsGex3           { get; set; } = true;
        [Display(Name = "GEX Ext #7",            GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 13,
                 Description = "Wall supplémentaire après CW/PW principaux (TanukiTrade GEX7)")]
        public bool ShowGexExt1           { get; set; } = true;
        [Display(Name = "GEX Ext #8",            GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 14)]
        public bool ShowGexExt2           { get; set; } = true;
        [Display(Name = "GEX Ext #9",            GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 15)]
        public bool ShowGexExt3           { get; set; } = true;
        [Display(Name = "GEX Ext #10",           GroupName = "02b.Niveaux INTRADAY (0-7d)", Order = 16)]
        public bool ShowGexExt4           { get; set; } = true;

        #endregion

        #region 03.Niveaux VEX/CEX

        [Display(Name = "Vanna Flip",                      GroupName = "03.Niveaux VEX/CEX", Order = 1)]
        public bool ShowVannaFlip   { get; set; } = true;
        [Display(Name = "Charm Magnet (CME 49d)",          GroupName = "03.Niveaux VEX/CEX", Order = 2)]
        public bool ShowCharmMagnet { get; set; } = true;

        #endregion

        #region 03b.Niveaux 0DTE (CBOE expirations du jour)

        [Display(Name = "Max Pain 0DTE",      GroupName = "03b.Niveaux 0DTE", Order = 1)]
        public bool ShowMaxPain0DTE     { get; set; } = true;
        [Display(Name = "Pin Strike 0DTE",    GroupName = "03b.Niveaux 0DTE", Order = 2)]
        public bool ShowPinStrike0DTE   { get; set; } = true;
        [Display(Name = "Charm Magnet 0DTE",  GroupName = "03b.Niveaux 0DTE", Order = 3)]
        public bool ShowCharmMagnet0DTE { get; set; } = true;

        #endregion

        #region 04.Niveaux Options

        [Display(Name = "Max Pain",           GroupName = "04.Niveaux Options", Order = 1)]
        public bool ShowMaxPain          { get; set; } = true;
        [Display(Name = "Expected Move High", GroupName = "04.Niveaux Options", Order = 2)]
        public bool ShowExpectedMoveHigh  { get; set; } = true;
        [Display(Name = "Expected Move Low",  GroupName = "04.Niveaux Options", Order = 3)]
        public bool ShowExpectedMoveLow   { get; set; } = true;
        [Display(Name = "Bande EM (fond)",    GroupName = "04.Niveaux Options", Order = 4,
                 Description = "Bande Expected Move (TastyTrade-style, formule pondérée straddle/strangle si dispo)")]
        public bool ShowEMZone            { get; set; } = false;
        [Display(Name = "Opacité bande EM %", GroupName = "04.Niveaux Options", Order = 5)]
        [Range(2, 30)]
        public int  EMBandOpacity         { get; set; } = 8;
        [Display(Name = "Couleur bande EM",   GroupName = "04.Niveaux Options", Order = 6)]
        public DrawingColor EMBandColor   { get; set; } = DrawingColor.FromArgb(255, 165, 130, 90);

        #endregion

        #region 05.Niveaux Top OI

        // Désactivés par défaut: Top OI structurels (toutes expirations) souvent
        // à >5% du spot. Préférer les Top OI intraday (section 02b).
        [Display(Name = "Top OI #1 structurel", GroupName = "05.Niveaux Top OI", Order = 1)]
        public bool ShowTopOI1 { get; set; } = true;
        [Display(Name = "Top OI #2 structurel", GroupName = "05.Niveaux Top OI", Order = 2)]
        public bool ShowTopOI2 { get; set; } = true;
        [Display(Name = "Top OI #3 structurel", GroupName = "05.Niveaux Top OI", Order = 3)]
        public bool ShowTopOI3 { get; set; } = true;

        #endregion

        #region 06.Visuel

        [Display(Name = "Zone pinning Call/Put Wall", GroupName = "06.Visuel", Order = 1)]
        public bool ShowPinZone   { get; set; } = false;
        [Display(Name = "Epaisseur lignes",           GroupName = "06.Visuel", Order = 2)]
        [Range(1, 5)]
        public int  LineWidth     { get; set; } = 2;
        [Display(Name = "Taille police labels",       GroupName = "06.Visuel", Order = 3)]
        [Range(7, 14)]
        public int  LabelFontSize { get; set; } = 9;
        [Display(Name = "Opacité zone pinning %",     GroupName = "06.Visuel", Order = 4)]
        [Range(1, 40)]
        public int  PinZoneOpacity { get; set; } = 8;

        #endregion

        #region 06b.Zones Gamma (TanukiTrade-style)

        [Display(Name = "Afficher zones gamma",       GroupName = "06b.Zones Gamma", Order = 1,
                 Description = "Zones colorées : positive (au-dessus cTrans), transition (entre cTrans/pTrans), negative (sous pTrans), squeeze (au-dessus Call Wall / sous Put Wall).")]
        public bool ShowGammaZones { get; set; } = false;

        [Display(Name = "Opacité zones %",            GroupName = "06b.Zones Gamma", Order = 2)]
        [Range(2, 30)]
        public int GammaZoneOpacity { get; set; } = 7;

        [Display(Name = "Couleur positive gamma",     GroupName = "06b.Zones Gamma", Order = 3)]
        public DrawingColor ZonePositiveColor   { get; set; } = DrawingColor.FromArgb(255, 80, 200, 120);
        [Display(Name = "Couleur transition",         GroupName = "06b.Zones Gamma", Order = 4)]
        public DrawingColor ZoneTransitionColor { get; set; } = DrawingColor.FromArgb(255, 140, 140, 160);
        [Display(Name = "Couleur negative gamma",     GroupName = "06b.Zones Gamma", Order = 5)]
        public DrawingColor ZoneNegativeColor   { get; set; } = DrawingColor.FromArgb(255, 220, 80, 80);
        [Display(Name = "Couleur squeeze (jaune)",    GroupName = "06b.Zones Gamma", Order = 6)]
        public DrawingColor ZoneSqueezeColor    { get; set; } = DrawingColor.FromArgb(255, 240, 220, 60);

        #endregion

        #region 06c.Display fine-tuning (TanukiTrade)

        [Display(Name = "Afficher labels niveaux", GroupName = "06c.Display fine-tuning", Order = 1,
                 Description = "Si OFF, dessine les lignes sans aucun label (chart épuré).")]
        public bool ShowLineLabels    { get; set; } = true;

        [Display(Name = "Labels à droite",         GroupName = "06c.Display fine-tuning", Order = 2,
                 Description = "Position des labels : à gauche (default) ou à droite du chart.")]
        public bool LabelOnRight      { get; set; } = false;

        [Display(Name = "Lignes pleines",          GroupName = "06c.Display fine-tuning", Order = 3,
                 Description = "Si ON, lignes pleines au lieu de pointillées.")]
        public bool UseSolidLines     { get; set; } = false;

        [Display(Name = "Opacité fond label %",    GroupName = "06c.Display fine-tuning", Order = 4)]
        [Range(20, 100)]
        public int  LabelBgOpacity    { get; set; } = 65;

        [Display(Name = "Extension droite seule", GroupName = "06c.Display fine-tuning", Order = 5,
                 Description = "Si ON, lignes dessinées uniquement depuis la barre actuelle vers la droite.")]
        public bool LineExtensionRightOnly { get; set; } = false;

        #endregion

        #region 07.Couleurs GEX

        [Display(Name = "Gamma Flip",   GroupName = "07.Couleurs GEX", Order = 1)]
        public DrawingColor GammaFlipColor   { get; set; } = DrawingColor.Yellow;
        [Display(Name = "Vol Trigger",  GroupName = "07.Couleurs GEX", Order = 2)]
        public DrawingColor VolTriggerColor  { get; set; } = DrawingColor.Gold;
        [Display(Name = "Call Wall",    GroupName = "07.Couleurs GEX", Order = 3)]
        public DrawingColor CallWallColor    { get; set; } = DrawingColor.LimeGreen;
        [Display(Name = "Put Wall",     GroupName = "07.Couleurs GEX", Order = 4)]
        public DrawingColor PutWallColor     { get; set; } = DrawingColor.OrangeRed;
        [Display(Name = "Risk Pivot",   GroupName = "07.Couleurs GEX", Order = 5)]
        public DrawingColor RiskPivotColor   { get; set; } = DrawingColor.Crimson;
        [Display(Name = "Vanna Flip",   GroupName = "07.Couleurs GEX", Order = 6)]
        public DrawingColor VannaFlipColor   { get; set; } = DrawingColor.Violet;
        [Display(Name = "Charm Magnet", GroupName = "07.Couleurs GEX", Order = 7)]
        public DrawingColor CharmMagnetColor { get; set; } = DrawingColor.CornflowerBlue;

        #endregion

        #region 08.Couleurs Options

        [Display(Name = "Max Pain",           GroupName = "08.Couleurs Options", Order = 1)]
        public DrawingColor MaxPainColor          { get; set; } = DrawingColor.Gray;
        [Display(Name = "Expected Move High", GroupName = "08.Couleurs Options", Order = 2)]
        public DrawingColor ExpectedMoveHighColor { get; set; } = DrawingColor.MediumAquamarine;
        [Display(Name = "Expected Move Low",  GroupName = "08.Couleurs Options", Order = 3)]
        public DrawingColor ExpectedMoveLowColor  { get; set; } = DrawingColor.MediumAquamarine;
        [Display(Name = "Top OI #1",          GroupName = "08.Couleurs Options", Order = 4)]
        public DrawingColor TopOI1Color           { get; set; } = DrawingColor.FromArgb(255, 100, 180, 255);
        [Display(Name = "Top OI #2",          GroupName = "08.Couleurs Options", Order = 5)]
        public DrawingColor TopOI2Color           { get; set; } = DrawingColor.FromArgb(200, 100, 180, 255);
        [Display(Name = "Top OI #3",          GroupName = "08.Couleurs Options", Order = 6)]
        public DrawingColor TopOI3Color           { get; set; } = DrawingColor.FromArgb(150, 100, 180, 255);

        #endregion

        #region 08b.Couleurs INTRADAY

        [Display(Name = "Call Wall intraday", GroupName = "08b.Couleurs INTRADAY", Order = 1)]
        public DrawingColor CallWallIntradayColor { get; set; } = DrawingColor.FromArgb(255, 50, 255, 100);
        [Display(Name = "Put Wall intraday",  GroupName = "08b.Couleurs INTRADAY", Order = 2)]
        public DrawingColor PutWallIntradayColor  { get; set; } = DrawingColor.FromArgb(255, 255, 80, 80);
        [Display(Name = "Top OI intraday #1", GroupName = "08b.Couleurs INTRADAY", Order = 3)]
        public DrawingColor TopOIIntraday1Color   { get; set; } = DrawingColor.FromArgb(255, 255, 220, 100);
        [Display(Name = "Top OI intraday #2", GroupName = "08b.Couleurs INTRADAY", Order = 4)]
        public DrawingColor TopOIIntraday2Color   { get; set; } = DrawingColor.FromArgb(220, 255, 220, 100);
        [Display(Name = "Top OI intraday #3", GroupName = "08b.Couleurs INTRADAY", Order = 5)]
        public DrawingColor TopOIIntraday3Color   { get; set; } = DrawingColor.FromArgb(180, 255, 220, 100);
        [Display(Name = "cTrans intraday",    GroupName = "08b.Couleurs INTRADAY", Order = 6)]
        public DrawingColor CTransIntradayColor   { get; set; } = DrawingColor.FromArgb(255, 120, 220, 140);
        [Display(Name = "pTrans intraday",    GroupName = "08b.Couleurs INTRADAY", Order = 7)]
        public DrawingColor PTransIntradayColor   { get; set; } = DrawingColor.FromArgb(255, 220, 140, 140);
        [Display(Name = "D+ DEX intraday",    GroupName = "08b.Couleurs INTRADAY", Order = 8)]
        public DrawingColor DexPlusIntradayColor  { get; set; } = DrawingColor.FromArgb(255, 0, 191, 255);  // DeepSkyBlue, distinct des Top OI bleus
        [Display(Name = "D- DEX intraday",    GroupName = "08b.Couleurs INTRADAY", Order = 9)]
        public DrawingColor DexMinusIntradayColor { get; set; } = DrawingColor.FromArgb(255, 255, 105, 180); // HotPink
        [Display(Name = "Abs GEX Ab1",        GroupName = "08b.Couleurs INTRADAY", Order = 10)]
        public DrawingColor AbsGex1Color      { get; set; } = DrawingColor.FromArgb(255, 200, 130, 255); // violet TanukiTrade
        [Display(Name = "Abs GEX Ab2",        GroupName = "08b.Couleurs INTRADAY", Order = 11)]
        public DrawingColor AbsGex2Color      { get; set; } = DrawingColor.FromArgb(220, 200, 130, 255);
        [Display(Name = "Abs GEX Ab3",        GroupName = "08b.Couleurs INTRADAY", Order = 12)]
        public DrawingColor AbsGex3Color      { get; set; } = DrawingColor.FromArgb(180, 200, 130, 255);
        [Display(Name = "GEX Ext (call side)",GroupName = "08b.Couleurs INTRADAY", Order = 13,
                 Description = "Couleur extended walls quand côté call (net GEX positif)")]
        public DrawingColor GexExtCallColor   { get; set; } = DrawingColor.FromArgb(180, 130, 230, 160);
        [Display(Name = "GEX Ext (put side)", GroupName = "08b.Couleurs INTRADAY", Order = 14,
                 Description = "Couleur extended walls quand côté put (net GEX négatif)")]
        public DrawingColor GexExtPutColor    { get; set; } = DrawingColor.FromArgb(180, 230, 130, 130);

        #endregion

        #region 08c.Couleurs 0DTE

        [Display(Name = "Max Pain 0DTE",     GroupName = "08c.Couleurs 0DTE", Order = 1)]
        public DrawingColor MaxPain0DTEColor     { get; set; } = DrawingColor.FromArgb(255, 200, 200, 200);
        [Display(Name = "Pin Strike 0DTE",   GroupName = "08c.Couleurs 0DTE", Order = 2)]
        public DrawingColor PinStrike0DTEColor   { get; set; } = DrawingColor.FromArgb(255, 255, 165, 0);
        [Display(Name = "Charm Magnet 0DTE", GroupName = "08c.Couleurs 0DTE", Order = 3)]
        public DrawingColor CharmMagnet0DTEColor { get; set; } = DrawingColor.FromArgb(255, 200, 100, 255);

        #endregion

        #region 09.Panel flottant

        [Display(Name = "Afficher panneau", GroupName = "09.Panel flottant", Order = 1)]
        public bool ShowPanel
        {
            get => _showPanel;
            set
            {
                _showPanel = value;
                Application.Current?.Dispatcher?.BeginInvoke(new Action(() =>
                {
                    if (_showPanel  && !_panelOpen) OpenPanel();
                    else if (!_showPanel && _panelOpen) ClosePanel();
                }));
            }
        }
        private bool _showPanel = true;

        [Display(Name = "Chemin Python (exe)", GroupName = "09.Panel flottant", Order = 2)]
        public string PythonExePath { get; set; } = "python.exe";

        [Display(Name = "Chemin script .py", GroupName = "09.Panel flottant", Order = 3)]
        public string ScriptPath { get; set; } = @"C:\Users\steph\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline\run_morning_ES.py";

        [Display(Name = "Dossier PDF briefing", GroupName = "09.Panel flottant", Order = 4)]
        public string BriefingDir { get; set; } = @"C:\Users\steph\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline\data";

        [Display(Name = "Script intraday refresh", GroupName = "09.Panel flottant", Order = 5,
                 Description = "Script .py lancé en background quand 'Loop intraday' est ON")]
        public string IntradayRefreshScriptPath { get; set; } = @"C:\Users\steph\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline\run_intraday_refresh.py";

        #endregion

        #region 10.Alertes scalping

        [Display(Name = "Sound file (.wav)", GroupName = "10.Alertes scalping", Order = 1,
                 Description = "Fichier audio joué lors d'une alerte (alert1.wav, alert2.wav, …)")]
        public string AlertSoundFile { get; set; } = "alert1.wav";

        [Display(Name = "Alertes scalping activées", GroupName = "10.Alertes scalping", Order = 2)]
        public bool EnableScalpingAlerts { get; set; } = true;

        [Display(Name = "Cooldown alerte (s)", GroupName = "10.Alertes scalping", Order = 3,
                 Description = "Durée minimale entre deux alertes du même type")]
        [Range(10, 3600)]
        public int AlertCooldownSeconds { get; set; } = 120;

        [Display(Name = "Proximité ticks (Pin/Charm)", GroupName = "10.Alertes scalping", Order = 4)]
        [Range(1, 100)]
        public int AlertProximityTicks { get; set; } = 5;

        [Display(Name = "Alertes prédictives (approche cross)", GroupName = "10.Alertes scalping", Order = 5,
                 Description = "Déclenche une alerte AVANT que le prix traverse un niveau (gamma flip, walls, trans, vol flow)")]
        public bool EnablePredictiveAlerts { get; set; } = true;

        [Display(Name = "Proximité prédictive (ticks)", GroupName = "10.Alertes scalping", Order = 6,
                 Description = "Distance au niveau pour déclencher l'alerte d'approche")]
        [Range(1, 100)]
        public int PredictiveAlertProximityTicks { get; set; } = 10;

        [Display(Name = "1. Cross Gamma Flip", GroupName = "10.Alertes scalping", Order = 10)]
        public bool AlertCrossGammaFlip { get; set; } = true;

        [Display(Name = "2. Cross Call/Put Wall (intraday)", GroupName = "10.Alertes scalping", Order = 11)]
        public bool AlertCrossWalls { get; set; } = true;

        [Display(Name = "3. Cross cTrans/pTrans", GroupName = "10.Alertes scalping", Order = 12)]
        public bool AlertCrossTrans { get; set; } = true;

        [Display(Name = "4. Approche Pin Strike 0DTE", GroupName = "10.Alertes scalping", Order = 13)]
        public bool AlertPin0DTE { get; set; } = true;

        [Display(Name = "5. Approche Charm Magnet (last hour)", GroupName = "10.Alertes scalping", Order = 14)]
        public bool AlertCharmMagnet { get; set; } = true;

        [Display(Name = "6. IVR extrême au load (>90 ou <10)", GroupName = "10.Alertes scalping", Order = 15)]
        public bool AlertIvrExtreme { get; set; } = true;

        [Display(Name = "7. Term backwardation aigu (>1vp)", GroupName = "10.Alertes scalping", Order = 16)]
        public bool AlertTermBackwardation { get; set; } = true;

        [Display(Name = "8. Skew explosif (>5vp)", GroupName = "10.Alertes scalping", Order = 17)]
        public bool AlertSkewExplosive { get; set; } = true;

        [Display(Name = "9. VIX entrée régime EXTREME", GroupName = "10.Alertes scalping", Order = 18)]
        public bool AlertVixRegimeChange { get; set; } = true;

        [Display(Name = "10. Volume Flow breach (GEX ext)", GroupName = "10.Alertes scalping", Order = 19)]
        public bool AlertVolumeFlowBreach { get; set; } = true;

        [Display(Name = "11. Blackout macro imminent (<30min)", GroupName = "10.Alertes scalping", Order = 20)]
        public bool AlertMacroBlackout { get; set; } = true;

        [Display(Name = "12. Données obsolètes (>10min)", GroupName = "10.Alertes scalping", Order = 21)]
        public bool AlertStaleData { get; set; } = true;

        [Display(Name = "Bannière on-chart", GroupName = "11.Alertes visuelles", Order = 0,
                 Description = "Affiche les alertes directement sur le chart (coin haut-droit)")]
        public bool EnableVisualBanners { get; set; } = true;

        [Display(Name = "Durée bannière (s)", GroupName = "11.Alertes visuelles", Order = 1)]
        [Range(5, 300)]
        public int BannerDurationSeconds { get; set; } = 30;

        [Display(Name = "Max bannières affichées", GroupName = "11.Alertes visuelles", Order = 2)]
        [Range(1, 10)]
        public int MaxVisibleBanners { get; set; } = 5;

        [Display(Name = "Dossier snapshots intraday", GroupName = "12.Replay intraday", Order = 1,
                 Description = "Chemin vers le dossier des snapshots horodatés (5 min) pour le replay")]
        public string IntradayHistoryDir { get; set; } = @"C:\Users\steph\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline\data\history\intraday";

        #endregion

        #region Private

        private volatile GexSnapshot  _levels       = GexSnapshot.Empty;
        private volatile MetaSnapshot _meta         = MetaSnapshot.Empty;
        private string   _loadedDate  = "";
        private bool     _levelsLoaded = false;
        private DateTime _lastLoadTime = DateTime.MinValue;

        // Replay intraday
        private volatile bool _replayMode = false;
        private DateTime      _replayTimestamp = DateTime.MinValue;
        private Window        _replayWindow = null;
        private Button        _btnReplay = null;

        // Loop intraday refresh (background process)
        private Process?      _loopProcess = null;
        private volatile bool _loopRunning = false;
        private Button        _btnLoop = null;

        // Anti-spam alertes : key → dernière émission
        private readonly System.Collections.Concurrent.ConcurrentDictionary<string, DateTime> _lastAlerts = new();
        private string _lastVixRegime = "";

        private struct BannerEntry
        {
            public string Message;
            public DrawingColor Color;
            public DateTime Time;
        }
        private readonly System.Collections.Generic.List<BannerEntry> _banners = new();
        private readonly object _bannerSync = new object();

        // Stats alertes (compteurs jour + 7 derniers jours)
        private readonly System.Collections.Generic.Dictionary<string, (int today, int week)> _alertStats = new();
        private readonly object _alertStatsSync = new object();
        private const string AlertLogFileName = "alerts_log_ES.txt";

        // État hystérésis alertes prédictives (true = dans la zone de proximité)
        private readonly System.Collections.Concurrent.ConcurrentDictionary<string, bool> _approachState = new();

        // Font géré dynamiquement via GetLabelFont() qui respecte LabelFontSize.

        private Window    _panelWindow = null;
        private TextBlock _infoText    = null;
        private Button    _btnRefresh  = null;
        private Button    _btnBriefing = null;
        private TextBlock _statusText  = null;
        private bool      _isRunning   = false;
        private bool      _panelOpen   = false;

        #endregion

        public OFK_ES_GEX_Levels() : base(true)
        {
            EnableCustomDrawing = true;
            SubscribeToDrawingEvents(DrawingLayouts.Historical | DrawingLayouts.LatestBar | DrawingLayouts.Final);
            DenyToChangePanel = true;
            DataSeries[0].IsHidden = true;
            ((ValueDataSeries)DataSeries[0]).VisualType = VisualMode.Hide;
        }

        protected override void OnCalculate(int bar, decimal value)
        {
            if (bar == 0)
            {
                if (!_levelsLoaded) LoadLevels();
                Application.Current?.Dispatcher?.BeginInvoke(new Action(() =>
                {
                    if (ShowPanel && !_panelOpen) OpenPanel();
                }));
            }
            if (!_levelsLoaded) return;

            bool isLastBar = bar >= CurrentBar - 1;
            bool newDay    = _loadedDate != DateTime.Today.ToString("yyyy-MM-dd");
            bool elapsed   = RefreshMinutes > 0 &&
                             (DateTime.Now - _lastLoadTime).TotalMinutes >= RefreshMinutes;
            if (isLastBar && (newDay || elapsed)) { LoadLevels(); UpdatePanelText(); }

            // Alertes scalping (live bar uniquement)
            if (isLastBar && EnableScalpingAlerts) CheckAlerts(bar);
        }

        // ── Alertes scalping (Bloc 4) ────────────────────────────────────────
        private void CheckAlerts(int bar)
        {
            if (!_levelsLoaded || bar < 1 || bar >= CurrentBar) return;
            var lv = _levels;
            if (!lv.Loaded) return;

            var prev = GetCandle(bar - 1);
            var curr = GetCandle(bar);
            if (prev == null || curr == null) return;

            decimal prevClose = prev.Close;
            decimal currClose = curr.Close;
            decimal tick = InstrumentInfo?.TickSize ?? 0.25m;

            if (AlertCrossGammaFlip && CrossDetected(prevClose, currClose, (decimal)lv.GammaFlip))
                FireAlert("gamma_flip",
                    $"ES {currClose:0} traverse Gamma Flip {lv.GammaFlip:0} — changement régime gamma",
                    curr);

            if (AlertCrossWalls)
            {
                if (CrossDetected(prevClose, currClose, (decimal)lv.CallWallIntraday))
                    FireAlert("call_wall_id", $"ES traverse Call Wall intraday {lv.CallWallIntraday:0}", curr);
                if (CrossDetected(prevClose, currClose, (decimal)lv.PutWallIntraday))
                    FireAlert("put_wall_id", $"ES traverse Put Wall intraday {lv.PutWallIntraday:0}", curr);
            }

            if (AlertCrossTrans)
            {
                if (CrossDetected(prevClose, currClose, (decimal)lv.CTransIntraday))
                    FireAlert("c_trans", $"ES traverse cTrans {lv.CTransIntraday:0} — changement zone gamma", curr);
                if (CrossDetected(prevClose, currClose, (decimal)lv.PTransIntraday))
                    FireAlert("p_trans", $"ES traverse pTrans {lv.PTransIntraday:0} — changement zone gamma", curr);
            }

            // Alertes prédictives (approche avant cross)
            if (EnablePredictiveAlerts)
            {
                if (AlertCrossGammaFlip)
                    CheckApproach("gamma_flip", currClose, (decimal)lv.GammaFlip, tick, curr, "ES", "Gamma Flip");
                if (AlertCrossWalls)
                {
                    CheckApproach("call_wall_id", currClose, (decimal)lv.CallWallIntraday, tick, curr, "ES", "Call Wall ID");
                    CheckApproach("put_wall_id",  currClose, (decimal)lv.PutWallIntraday,  tick, curr, "ES", "Put Wall ID");
                }
                if (AlertCrossTrans)
                {
                    CheckApproach("c_trans", currClose, (decimal)lv.CTransIntraday, tick, curr, "ES", "cTrans");
                    CheckApproach("p_trans", currClose, (decimal)lv.PTransIntraday, tick, curr, "ES", "pTrans");
                }
                if (AlertVolumeFlowBreach)
                    CheckApproach("vol_flow", currClose, (decimal)lv.GexExt1, tick, curr, "ES", "GEX ext-1");
            }

            if (AlertPin0DTE && lv.PinStrike0DTE > 0)
            {
                decimal dist = Math.Abs(currClose - (decimal)lv.PinStrike0DTE);
                if (dist <= AlertProximityTicks * tick)
                    FireAlert("pin_0dte",
                        $"ES proche Pin Strike 0DTE {lv.PinStrike0DTE:0} (±{AlertProximityTicks}t)",
                        curr);
            }

            if (AlertCharmMagnet && lv.CharmMagnet0DTE > 0 && IsLastHourRTH())
            {
                decimal dist = Math.Abs(currClose - (decimal)lv.CharmMagnet0DTE);
                if (dist <= AlertProximityTicks * tick * 3)
                    FireAlert("charm_magnet",
                        $"ES approche Charm Magnet 0DTE {lv.CharmMagnet0DTE:0} (last hour)",
                        curr);
            }

            if (AlertIvrExtreme && lv.IvRankIntraday >= 0
                && (lv.IvRankIntradayStatus == "ok" || lv.IvRankIntradayStatus == "partial"))
            {
                if (lv.IvRankIntraday > 90)
                    FireAlert("ivr_high", $"IVR très élevée {lv.IvRankIntraday:0}% — vol haute, élargir stops", curr);
                else if (lv.IvRankIntraday < 10)
                    FireAlert("ivr_low", $"IVR très faible {lv.IvRankIntraday:0}% — vol comprimée, range serré", curr);
            }

            if (AlertTermBackwardation && lv.TermIntradaySlope > 0.01)
                FireAlert("term_back",
                    $"Term backwardation aigu (slope +{lv.TermIntradaySlope * 100:0.0}vp) — STRESS, breakouts",
                    curr);

            if (AlertSkewExplosive && lv.Skew25dIntraday > 0.05)
                FireAlert("skew_high",
                    $"Skew 25Δ explosif {lv.Skew25dIntraday * 100:0.0}vp — protection puts agressive",
                    curr);

            if (AlertVixRegimeChange && _meta.Loaded && !string.IsNullOrEmpty(_meta.VixRegime))
            {
                if (_meta.VixRegime != _lastVixRegime && _meta.VixRegime == "extreme")
                    FireAlert("vix_extreme",
                        $"VIX régime EXTREME ({_meta.Vix:0.0}, DoD {_meta.VixDodChange:+0.0;-0.0;0}) — fuir le scalping",
                        curr);
                _lastVixRegime = _meta.VixRegime;
            }

            if (AlertVolumeFlowBreach && lv.GexExt1 > 0 &&
                CrossDetected(prevClose, currClose, (decimal)lv.GexExt1))
                FireAlert("vol_flow", $"ES traverse GEX ext-1 {lv.GexExt1:0} — flux directionnel", curr);

            if (AlertMacroBlackout && _meta.Loaded &&
                _meta.MacroMinutesToNext > 0 && _meta.MacroMinutesToNext <= 30)
                FireAlert("macro_imminent",
                    $"Événement macro {_meta.MacroNextEventTitle} dans {_meta.MacroMinutesToNext}min — STOP scalping",
                    curr);

            if (AlertStaleData)
            {
                // Stale = le JSON sur disque n'a pas été régénéré depuis >10min,
                // mais uniquement si Loop intraday est ON (sinon le user gère
                // son refresh manuellement → pas la peine de spammer).
                if (_loopRunning)
                {
                    try
                    {
                        if (File.Exists(JsonPath))
                        {
                            var ageMin = (DateTime.Now - File.GetLastWriteTime(JsonPath)).TotalMinutes;
                            if (ageMin > 10)
                                FireAlert("stale_data",
                                    $"Loop intraday actif mais JSON figé ({(int)ageMin}min) — vérifier le process Python",
                                    curr);
                        }
                    }
                    catch { }
                }
                if (_meta.Loaded && _meta.DataQuality == "partial")
                    FireAlert("data_partial",
                        $"Données pipeline PARTIELLES (CME ou CBOE manquant) — qualité dégradée",
                        curr);
                if (_meta.Loaded && _meta.DataQuality == "error")
                    FireAlert("data_error",
                        $"Données pipeline en ERREUR — pas de levels valides",
                        curr);
                if (_meta.Loaded && !string.IsNullOrEmpty(_meta.JsonSchemaVersion) &&
                    _meta.JsonSchemaVersion != EXPECTED_JSON_SCHEMA_VERSION)
                    FireAlert("schema_mismatch",
                        $"JSON schema {_meta.JsonSchemaVersion} ≠ attendu {EXPECTED_JSON_SCHEMA_VERSION} — pipeline désynchro indicateur",
                        curr);
            }
        }

        private static bool CrossDetected(decimal prev, decimal curr, decimal level)
        {
            if (level <= 0) return false;
            return (prev < level && curr >= level) || (prev > level && curr <= level);
        }

        // Alerte prédictive avec hystérésis : déclenche à l'entrée dans la zone, reset à la sortie élargie
        private void CheckApproach(string baseKey, decimal price, decimal level, decimal tick, IndicatorCandle candle, string instrumentLabel, string levelLabel)
        {
            if (level <= 0 || !EnablePredictiveAlerts) return;
            decimal dist = Math.Abs(price - level);
            decimal proximity = PredictiveAlertProximityTicks * tick;
            decimal exitThreshold = proximity * 2m;

            string key = baseKey + "_approach";
            bool wasInZone = _approachState.TryGetValue(key, out bool prev) && prev;

            if (dist <= proximity && !wasInZone)
            {
                int distTicks = (int)(dist / tick);
                FireAlert(key, $"{instrumentLabel} approche {levelLabel} {level:F0} (à {distTicks} ticks)", candle);
                _approachState[key] = true;
            }
            else if (dist > exitThreshold && wasInZone)
            {
                _approachState[key] = false;
            }
        }

        private static bool IsLastHourRTH()
        {
            int h = DateTime.UtcNow.Hour;
            return h == 19 || h == 20;
        }

        private void FireAlert(string key, string message, IndicatorCandle candle)
        {
            if (!_lastAlerts.TryGetValue(key, out var last)) last = DateTime.MinValue;
            if ((DateTime.Now - last).TotalSeconds < AlertCooldownSeconds) return;
            try
            {
                string sound = string.IsNullOrWhiteSpace(AlertSoundFile) ? "alert1.wav" : AlertSoundFile;
                var bg = System.Windows.Media.Color.FromArgb(255, 50, 50, 50);
                var fg = System.Windows.Media.Color.FromArgb(255, 255, 200, 80);
                AddAlert(sound, InstrumentInfo?.Instrument ?? "", message, bg, fg);
                _lastAlerts[key] = DateTime.Now;

                lock (_alertStatsSync)
                {
                    if (_alertStats.TryGetValue(key, out var cur))
                        _alertStats[key] = (cur.today + 1, cur.week + 1);
                    else
                        _alertStats[key] = (1, 1);
                }

                if (EnableVisualBanners)
                {
                    lock (_bannerSync)
                    {
                        _banners.Add(new BannerEntry { Message = message, Color = GetBannerColor(key), Time = DateTime.Now });
                        while (_banners.Count > MaxVisibleBanners * 2) _banners.RemoveAt(0);
                    }
                }

                // Log fichier append (Bloc 8 stats) — historique consultable hors session
                try
                {
                    string dir = Path.GetDirectoryName(JsonPath) ?? "";
                    string logPath = Path.Combine(dir, "alerts_log_ES.txt");
                    File.AppendAllText(logPath,
                        $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} [{key}] {message}\n");
                }
                catch { /* log file optional */ }
            }
            catch { /* AddAlert signature peut varier selon version ATAS */ }
        }

        private static DrawingColor GetBannerColor(string key)
        {
            if (key == "vix_extreme" || key == "macro_imminent")
                return DrawingColor.FromArgb(255, 255, 60, 60);
            if (key == "ivr_high" || key == "ivr_low" || key == "term_back" || key == "skew_high")
                return DrawingColor.FromArgb(255, 255, 140, 0);
            if (key == "pin_0dte" || key == "charm_magnet")
                return DrawingColor.FromArgb(255, 0, 200, 255);
            if (key.Contains("data") || key.Contains("schema") || key.Contains("stale"))
                return DrawingColor.FromArgb(255, 140, 140, 150);
            return DrawingColor.FromArgb(255, 255, 200, 0);
        }

        // ── Position sizing dynamique (VIX × macro × data_quality) ──────────
        private static (int pct, string reason, string tag) ComputePositionSizing(MetaSnapshot meta)
        {
            if (!meta.Loaded)
                return (100, "Pas de contexte _meta — sizing par défaut", "OK");

            double pct = 1.0;
            var reasons = new System.Collections.Generic.List<string>();

            // VIX régime
            if (meta.VixRegime == "extreme")  { pct *= 0.25; reasons.Add($"VIX EXTREME ({meta.Vix:F1})"); }
            else if (meta.VixRegime == "elevated") { pct *= 0.60; reasons.Add($"VIX elevated ({meta.Vix:F1})"); }

            // Macro events
            if (meta.MacroInBlackout)
            {
                pct = 0.0;
                reasons.Add("BLACKOUT macro EN COURS");
            }
            else if (meta.MacroMinutesToNext > 0 && meta.MacroMinutesToNext <= 30)
            {
                pct = 0.0;
                string ev = string.IsNullOrEmpty(meta.MacroNextEventTitle) ? "event macro" : meta.MacroNextEventTitle;
                reasons.Add($"{ev} dans {meta.MacroMinutesToNext}min");
            }
            else if (meta.MacroMinutesToNext > 0 && meta.MacroMinutesToNext <= 60)
            {
                pct *= 0.50;
                string ev = string.IsNullOrEmpty(meta.MacroNextEventTitle) ? "event macro" : meta.MacroNextEventTitle;
                reasons.Add($"{ev} dans {meta.MacroMinutesToNext}min");
            }

            // Data quality
            if (meta.DataQuality == "error")   { pct = 0.0; reasons.Add("Données pipeline EN ERREUR"); }
            else if (meta.DataQuality == "partial") { pct *= 0.70; reasons.Add("Données partielles"); }

            int finalPct = (int)Math.Round(Math.Max(0.0, Math.Min(1.0, pct)) * 100);
            string reason = reasons.Count > 0 ? string.Join(", ", reasons) : "Conditions normales";
            string tag = finalPct >= 80 ? "OK"
                       : finalPct >= 50 ? "PRUDENCE"
                       : finalPct > 0   ? "FORTE PRUDENCE"
                       :                  "FLAT";
            return (finalPct, reason, tag);
        }

        private static string SizingBar(int pct)
        {
            int filled = (int)Math.Round(pct / 20.0);
            if (filled < 0) filled = 0;
            if (filled > 5) filled = 5;
            return new string('●', filled) + new string('○', 5 - filled);
        }

        // ── Stats alertes (compteurs jour + 7j) ──────────────────────────────
        private void LoadAlertStats()
        {
            try
            {
                string dir = Path.GetDirectoryName(JsonPath) ?? "";
                string logPath = Path.Combine(dir, AlertLogFileName);
                if (!File.Exists(logPath)) return;

                DateTime today = DateTime.Today;
                DateTime weekCutoff = today.AddDays(-7);
                var fresh = new System.Collections.Generic.Dictionary<string, (int today, int week)>();

                foreach (var raw in File.ReadLines(logPath))
                {
                    string line = raw?.Trim() ?? "";
                    if (line.Length < 22) continue;
                    if (!DateTime.TryParseExact(line.Substring(0, 19), "yyyy-MM-dd HH:mm:ss",
                            System.Globalization.CultureInfo.InvariantCulture,
                            System.Globalization.DateTimeStyles.None, out var dt))
                        continue;
                    int b1 = line.IndexOf('[', 19);
                    int b2 = b1 >= 0 ? line.IndexOf(']', b1 + 1) : -1;
                    if (b1 < 0 || b2 < 0 || b2 <= b1 + 1) continue;
                    string key = line.Substring(b1 + 1, b2 - b1 - 1);
                    if (string.IsNullOrEmpty(key)) continue;

                    int isToday = dt >= today ? 1 : 0;
                    int isWeek  = dt >= weekCutoff ? 1 : 0;
                    if (!fresh.TryGetValue(key, out var cur)) cur = (0, 0);
                    fresh[key] = (cur.today + isToday, cur.week + isWeek);
                }

                lock (_alertStatsSync)
                {
                    _alertStats.Clear();
                    foreach (var kv in fresh) _alertStats[kv.Key] = kv.Value;
                }
            }
            catch { /* best-effort */ }
        }

        private string FormatAlertStats()
        {
            System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, (int today, int week)>> ordered;
            int totalToday = 0, totalWeek = 0;
            lock (_alertStatsSync)
            {
                if (_alertStats.Count == 0) return "  Aucune alerte enregistrée\n";
                foreach (var kv in _alertStats) { totalToday += kv.Value.today; totalWeek += kv.Value.week; }
                ordered = new System.Collections.Generic.List<System.Collections.Generic.KeyValuePair<string, (int, int)>>();
                foreach (var kv in _alertStats) ordered.Add(kv);
            }
            ordered.Sort((a, b) =>
            {
                int c = b.Value.today.CompareTo(a.Value.today);
                return c != 0 ? c : b.Value.week.CompareTo(a.Value.week);
            });

            var sb = new System.Text.StringBuilder();
            int shown = 0;
            foreach (var kv in ordered)
            {
                if (shown >= 6) break;
                sb.AppendLine($"  {kv.Key,-16} {kv.Value.today,2} j /{kv.Value.week,3} 7j");
                shown++;
            }
            sb.AppendLine($"  {"TOTAL",-16} {totalToday,2} j /{totalWeek,3} 7j");
            return sb.ToString();
        }

        // ── Panel ─────────────────────────────────────────────────────────────

        private void OpenPanel()
        {
            if (_panelOpen) return;
            var lv = _levels;

            var bgColor      = System.Windows.Media.Color.FromRgb(22, 27, 39);
            var bgDark       = System.Windows.Media.Color.FromRgb(13, 17, 23);
            var borderColor  = System.Windows.Media.Color.FromRgb(33, 41, 61);
            var textColor    = System.Windows.Media.Color.FromRgb(201, 209, 217);
            var textDimColor = System.Windows.Media.Color.FromRgb(139, 148, 158);
            var accentBlue   = System.Windows.Media.Color.FromRgb(79, 139, 209);

            _panelWindow = new Window
            {
                Title = "OFK ES GEX Levels", Width = 430,
                Height = 720, MinWidth = 380, MinHeight = 380,
                Topmost = true,
                ResizeMode = ResizeMode.CanResizeWithGrip,
                WindowStartupLocation = WindowStartupLocation.Manual,
                Left = 80, Top = 80,
                Background = new SolidColorBrush(bgColor),
                ShowInTaskbar = false,
                FontFamily = new System.Windows.Media.FontFamily("Segoe UI"),
                FontSize = 12,
            };

            var root  = new Border { Background = new SolidColorBrush(bgColor), BorderBrush = new SolidColorBrush(borderColor), BorderThickness = new Thickness(1) };
            var dock  = new DockPanel { LastChildFill = true };

            // Header (sticky top)
            var hdr = new Border { Background = new SolidColorBrush(bgDark), BorderBrush = new SolidColorBrush(borderColor), BorderThickness = new Thickness(0,0,0,1), Padding = new Thickness(12,8,12,8) };
            hdr.Child = new TextBlock { Text = "OFK ES GEX Levels", Foreground = new SolidColorBrush(accentBlue), FontSize = 13, FontWeight = FontWeights.SemiBold };
            DockPanel.SetDock(hdr, Dock.Top);
            dock.Children.Add(hdr);

            // Info text (scrollable, ajouté en LAST pour LastChildFill)
            var infoSec = new Border { Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(18,22,30)), Padding = new Thickness(12,10,12,10), BorderBrush = new SolidColorBrush(borderColor), BorderThickness = new Thickness(0,0,0,1) };
            _infoText = new TextBlock { FontFamily = new System.Windows.Media.FontFamily("Consolas"), FontSize = 11, Foreground = new SolidColorBrush(textColor), TextWrapping = TextWrapping.NoWrap, LineHeight = 18 };
            infoSec.Child = _infoText;

            // Boutons (sticky bottom)
            var btnSec = new Border { Padding = new Thickness(12,8,12,8), BorderBrush = new SolidColorBrush(borderColor), BorderThickness = new Thickness(0,1,0,0) };
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(8) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            _btnRefresh = new Button
            {
                Content = "▶  GEX LEVELS", Height = 32,
                Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(20,40,90)),
                Foreground = new SolidColorBrush(accentBlue),
                FontSize = 11, FontFamily = new System.Windows.Media.FontFamily("Segoe UI"),
                FontWeight = FontWeights.SemiBold,
                BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromRgb(79,139,209)),
                BorderThickness = new Thickness(1), Cursor = System.Windows.Input.Cursors.Hand,
                Template = CreateButtonTemplate(),
            };
            _btnRefresh.Click += (s, e) => RunScript();
            Grid.SetColumn(_btnRefresh, 0);
            grid.Children.Add(_btnRefresh);

            _btnBriefing = new Button
            {
                Content = "📄  Briefing", Height = 32,
                Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(20,55,40)),
                Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(63,185,80)),
                FontSize = 11, FontFamily = new System.Windows.Media.FontFamily("Segoe UI"),
                FontWeight = FontWeights.SemiBold,
                BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromRgb(63,185,80)),
                BorderThickness = new Thickness(1), Cursor = System.Windows.Input.Cursors.Hand,
                Template = CreateButtonTemplate(),
            };
            _btnBriefing.Click += (s, e) => OpenBriefing();
            Grid.SetColumn(_btnBriefing, 2);
            grid.Children.Add(_btnBriefing);

            btnSec.Child = grid;

            // Bouton Replay intraday (2e ligne, pleine largeur)
            var replaySec = new Border { Padding = new Thickness(12,0,12,8), BorderBrush = new SolidColorBrush(borderColor), BorderThickness = new Thickness(0,0,0,1) };
            _btnReplay = new Button
            {
                Content = "🎬  Replay intraday", Height = 32,
                Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(60,40,90)),
                Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(189,147,249)),
                FontSize = 11, FontFamily = new System.Windows.Media.FontFamily("Segoe UI"),
                FontWeight = FontWeights.SemiBold,
                BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromRgb(189,147,249)),
                BorderThickness = new Thickness(1), Cursor = System.Windows.Input.Cursors.Hand,
                Template = CreateButtonTemplate(),
            };
            _btnReplay.Click += (s, e) => OpenReplayWindow();
            replaySec.Child = _btnReplay;

            // Bouton Loop intraday (3e ligne, pleine largeur, toggle ON/OFF)
            var loopSec = new Border { Padding = new Thickness(12,0,12,8), BorderBrush = new SolidColorBrush(borderColor), BorderThickness = new Thickness(0,0,0,1) };
            _btnLoop = new Button
            {
                Height = 32,
                FontSize = 11,
                FontFamily = new System.Windows.Media.FontFamily("Segoe UI"),
                FontWeight = FontWeights.SemiBold,
                BorderThickness = new Thickness(1),
                Cursor = System.Windows.Input.Cursors.Hand,
                Template = CreateButtonTemplate(),
            };
            _btnLoop.Click += (s, e) => ToggleLoop();
            loopSec.Child = _btnLoop;
            UpdateLoopButton();

            // Status
            var statusSec = new Border { Background = new SolidColorBrush(bgDark), Padding = new Thickness(12,5,12,5) };
            _statusText = new TextBlock { FontFamily = new System.Windows.Media.FontFamily("Segoe UI"), FontSize = 10, Foreground = new SolidColorBrush(textDimColor), Text = lv.Loaded ? $"✅ JSON chargé — {lv.TradeDate}  (spot {lv.SpotLoaded:F0})" : "⚠ JSON non chargé — vérifier JSON Path" };
            statusSec.Child = _statusText;

            // Empiler en bas du DockPanel : ordre d'ajout = du bas vers le haut
            DockPanel.SetDock(statusSec, Dock.Bottom);  dock.Children.Add(statusSec);
            DockPanel.SetDock(loopSec,   Dock.Bottom);  dock.Children.Add(loopSec);
            DockPanel.SetDock(replaySec, Dock.Bottom);  dock.Children.Add(replaySec);
            DockPanel.SetDock(btnSec,    Dock.Bottom);  dock.Children.Add(btnSec);

            // ScrollViewer au milieu (LastChildFill = true → prend tout l'espace restant)
            var scroll = new ScrollViewer
            {
                Content = infoSec,
                VerticalScrollBarVisibility   = ScrollBarVisibility.Auto,
                HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
                PanningMode                   = PanningMode.VerticalOnly,
                Background                    = new SolidColorBrush(System.Windows.Media.Color.FromRgb(18,22,30)),
            };
            dock.Children.Add(scroll);

            root.Child = dock;
            _panelWindow.Content = root;
            _panelWindow.SourceInitialized += (s, e) => ApplyDarkTitleBar(_panelWindow);
            _panelWindow.Closed += (s, e) => { _panelOpen = false; _panelWindow = null; _infoText = null; _btnRefresh = null; _btnBriefing = null; _btnReplay = null; _btnLoop = null; _statusText = null; };
            UpdatePanelText();
            _panelWindow.Show();
            _panelOpen = true;
        }

        private void ClosePanel() { _panelWindow?.Close(); _panelOpen = false; }

        // ── Dark title bar (Windows 10 1809+) ─────────────────────────────────
        [DllImport("dwmapi.dll")]
        private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);
        private const int DWMWA_USE_IMMERSIVE_DARK_MODE = 20;          // Win10 1903+
        private const int DWMWA_USE_IMMERSIVE_DARK_MODE_LEGACY = 19;   // Win10 1809-1903

        private static void ApplyDarkTitleBar(Window w)
        {
            try
            {
                IntPtr hwnd = new WindowInteropHelper(w).Handle;
                if (hwnd == IntPtr.Zero) return;
                int useDark = 1;
                if (DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ref useDark, sizeof(int)) != 0)
                    DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_LEGACY, ref useDark, sizeof(int));
            }
            catch { /* DWM API not available — silent fallback */ }
        }

        private void UpdatePanelText()
        {
            if (_infoText == null) return;
            Application.Current?.Dispatcher?.BeginInvoke(new Action(() =>
            {
                if (_infoText == null) return;
                var lv = _levels;

                string gReg  = lv.GexRegime > 0 ? "POSITIF ● pinning" : lv.GexRegime < 0 ? "NEGATIF ● explosif" : "NEUTRE";
                string vReg  = lv.VexRegime > 0 ? "IV↓ = RALLY ▲"     : lv.VexRegime < 0 ? "IV↑ = SELLOFF ▼"   : "neutre";
                string dSide = lv.DexTotal  > 0 ? "longs" : "shorts";
                string pcrStr= lv.Pcr > 0 ? $"{lv.Pcr:F3}  ({(lv.Pcr > 1 ? "put-heavy" : "call-heavy")})" : "—";
                // Intraday (primaire scalping)
                string ivxIdStr  = lv.AtmIvIntraday > 0
                    ? $"{lv.AtmIvIntraday*100:F1}%  ({lv.AtmIvIntradayDte}d)"
                    : "—";
                string skewIdStr = lv.Skew25dIntraday != 0
                    ? $"{lv.Skew25dIntraday*100:+0.00;-0.00} vp  ({lv.Skew25dIntradayDte}d, {(lv.Skew25dIntraday > 0 ? "bearish" : "bullish")})"
                    : "—";
                string termIdStr = (!string.IsNullOrEmpty(lv.TermIntradayRegime) && lv.TermIntradayRegime != "unknown")
                    ? $"{lv.TermIntradayIvFront*100:F1}% ({lv.TermIntradayFrontDte}d) → {lv.TermIntradayIvBack*100:F1}% ({lv.TermIntradayBackDte}d) [{lv.TermIntradayRegime}, {lv.TermIntradaySlope*100:+0.00;-0.00} vp]"
                    : "—";
                // Structural (secondaire CME 49d)
                string ivxStrStr  = lv.AtmIvStructural > 0 ? $"{lv.AtmIvStructural*100:F1}%" : "—";
                string skewStrStr = lv.Skew25dStructural != 0
                    ? $"{lv.Skew25dStructural*100:+0.00;-0.00} vp"
                    : "—";
                string termStrStr = (lv.IvStructuralBack > 0 && !string.IsNullOrEmpty(lv.TermStructuralRegime) && lv.TermStructuralRegime != "unknown")
                    ? $"{lv.AtmIvStructural*100:F1}% → {lv.IvStructuralBack*100:F1}% ({lv.IvStructuralBackDte}d, {lv.TermStructuralRegime}, {lv.TermStructuralSlope*100:+0.00;-0.00} vp)"
                    : "—";
                string emStr = lv.ExpectedMovePts > 0 ? $"±{lv.ExpectedMovePts:F0} pts  [{lv.ExpectedMoveLow:F0} — {lv.ExpectedMoveHigh:F0}]" : "—";
                string oi1   = lv.TopOI1 > 0 ? $"  Top OI #1   {lv.TopOI1:F0}  (OI {lv.TopOI1Vol:N0})\n" : "";
                string oi2   = lv.TopOI2 > 0 ? $"  Top OI #2   {lv.TopOI2:F0}  (OI {lv.TopOI2Vol:N0})\n" : "";
                string oi3   = lv.TopOI3 > 0 ? $"  Top OI #3   {lv.TopOI3:F0}  (OI {lv.TopOI3Vol:N0})\n" : "";

                int idDte = lv.WallsIntradayMaxDte > 0 ? lv.WallsIntradayMaxDte : 7;
                string cwIdStr = lv.CallWallIntraday > 0 ? $"{lv.CallWallIntraday:F0}" : "—";
                string pwIdStr = lv.PutWallIntraday  > 0 ? $"{lv.PutWallIntraday:F0}" : "—";
                string ctStr   = lv.CTransIntraday   > 0 ? $"{lv.CTransIntraday:F0}"   : "—";
                string ptStr   = lv.PTransIntraday   > 0 ? $"{lv.PTransIntraday:F0}"   : "—";
                string transLine = (lv.CTransIntraday > 0 || lv.PTransIntraday > 0)
                    ? $"  cTrans      {ctStr}     pTrans    {ptStr}\n" : "";
                string dpStr   = lv.DexPlusIntraday  > 0 ? $"{lv.DexPlusIntraday:F0}"  : "—";
                string dmStr   = lv.DexMinusIntraday > 0 ? $"{lv.DexMinusIntraday:F0}" : "—";
                string dexLine = (lv.DexPlusIntraday > 0 || lv.DexMinusIntraday > 0)
                    ? $"  D+ DEX      {dpStr}     D- DEX    {dmStr}\n" : "";
                string oid1 = lv.TopOIIntraday1 > 0 ? $"  OI ID #1    {lv.TopOIIntraday1:F0}  (OI {lv.TopOIIntraday1Vol:N0})\n" : "";
                string oid2 = lv.TopOIIntraday2 > 0 ? $"  OI ID #2    {lv.TopOIIntraday2:F0}  (OI {lv.TopOIIntraday2Vol:N0})\n" : "";
                string oid3 = lv.TopOIIntraday3 > 0 ? $"  OI ID #3    {lv.TopOIIntraday3:F0}  (OI {lv.TopOIIntraday3Vol:N0})\n" : "";
                // IV Rank
                string ivrStr = "";
                if (lv.IvRankIntraday > 0 && (lv.IvRankIntradayStatus == "ok" || lv.IvRankIntradayStatus == "partial"))
                    ivrStr = $"  IVR         {lv.IvRankIntraday:F0}%  ({lv.IvRankIntradayStatus})\n";
                else if (!string.IsNullOrEmpty(lv.IvRankIntradayStatus))
                    ivrStr = $"  IVR         {lv.IvRankIntradayStatus} (hist insuffisant)\n";
                // 0DTE
                string zdLabel = lv.ZeroDTEDte == 0 ? "0DTE" : $"{lv.ZeroDTEDte}DTE";
                string mp0   = lv.MaxPain0DTE     > 0 ? $"  Max Pain    {lv.MaxPain0DTE:F0}  ({zdLabel})\n" : "";
                string pin0  = lv.PinStrike0DTE   > 0 ? $"  Pin Strike  {lv.PinStrike0DTE:F0}  ({zdLabel})\n" : "";
                string ch0   = lv.CharmMagnet0DTE > 0 ? $"  Charm Mag.  {lv.CharmMagnet0DTE:F0}  ({zdLabel})\n" : "";
                string zdSection = (mp0 + pin0 + ch0).Length > 0
                    ? $"━━ 0DTE (fin de session) ━━\n{mp0}{pin0}{ch0}  OI total {zdLabel}: {lv.ZeroDTEOITotal:N0}\n\n"
                    : "";

                var (sizingPct, sizingReason, sizingTag) = ComputePositionSizing(_meta);
                string sizingBar = SizingBar(sizingPct);
                string sizingLine = $"━━ POSITION SIZING [{sizingTag}] ━━\n  {sizingPct,3}%   {sizingBar}   {sizingReason}\n\n";

                string alertStatsLine = $"━━ STATS ALERTES (jour / 7j) ━━\n{FormatAlertStats()}\n";

                _infoText.Text =
                    $"═══ OPTIONS GREEKS ES  ({lv.TradeDate}) ═══\n\n" +
                    sizingLine +
                    alertStatsLine +
                    $"  GEX  {lv.GexTotal / 1e9:+0.000;-0.000}B   {gReg}\n" +
                    $"  VEX  {lv.VexTotal / 1e8:+0.00;-0.00}       {vReg}\n" +
                    $"  CEX  {lv.CexTotal / 1e6:+0.00;-0.00}M\n" +
                    $"  DEX  {lv.DexTotal / 1e10:+0.000;-0.000}   dealers {dSide}\n\n" +
                    $"  Gamma Flip  {lv.GammaFlip:F0}     Trigger  {lv.VolTrigger:F0}\n" +
                    $"  Risk Pivot  {lv.RiskPivot:F0}    V-Flip   {lv.VannaFlip:F0}\n" +
                    $"  Charm       {lv.CharmMagnet:F0}     Spot réf. {lv.SpotLoaded:F0}\n\n" +
                    $"  Max Pain    {lv.MaxPain:F0}\n" +
                    $"  Exp. Move   {emStr}\n" +
                    $"  PCR         {pcrStr}\n\n" +
                    $"━━ INTRADAY (scalping, 0-{idDte}d) ━━\n" +
                    $"  IVx         {ivxIdStr}\n" +
                    ivrStr +
                    $"  Skew 25Δ    {skewIdStr}\n" +
                    $"  Term IV     {termIdStr}\n" +
                    $"  Call Wall   {cwIdStr}     Put Wall  {pwIdStr}\n" +
                    transLine +
                    dexLine +
                    oid1 + oid2 + oid3 + "\n" +
                    zdSection +
                    $"━━ Structural (CME 49d, all-exp) ━━\n" +
                    $"  IVx         {ivxStrStr}\n" +
                    $"  Skew 25Δ    {skewStrStr}\n" +
                    $"  Term IV     {termStrStr}\n" +
                    $"  Call Wall   {lv.CallWall:F0}     Put Wall  {lv.PutWall:F0}\n" +
                    oi1 + oi2 + oi3;

                if (_statusText != null)
                    _statusText.Text = lv.Loaded
                        ? $"✅ JSON chargé — {lv.TradeDate}  (spot {lv.SpotLoaded:F0})"
                        : "⚠ JSON non chargé — vérifier JSON Path";
            }));
        }

        // ── RunScript ─────────────────────────────────────────────────────────

        private void RunScript()
        {
            if (_isRunning) return;
            if (!File.Exists(ScriptPath))
            {
                Application.Current?.Dispatcher?.Invoke(() => { if (_statusText != null) _statusText.Text = "❌ Script introuvable : " + ScriptPath; });
                return;
            }

            // Reload immédiat du JSON courant (au cas où il aurait été
            // mis à jour par un run externe — manuel ou via run_intraday_refresh).
            // Comme ça l'utilisateur voit les données fraîches dès le clic,
            // sans attendre la fin du nouveau run.
            LoadLevels();
            Application.Current?.Dispatcher?.Invoke(() => {
                UpdatePanelText();
                var lv = _levels;
                if (_statusText != null && lv.Loaded)
                    _statusText.Text = $"✅ JSON rechargé — {lv.TradeDate}";
            });
            try { RedrawChart(); } catch { }

            _isRunning = true;
            Application.Current?.Dispatcher?.Invoke(() =>
            {
                if (_btnRefresh  != null) { _btnRefresh.Content = "⏳ En cours…"; _btnRefresh.Background = new SolidColorBrush(System.Windows.Media.Color.FromArgb(220,80,60,0)); _btnRefresh.Foreground = System.Windows.Media.Brushes.Orange; _btnRefresh.IsEnabled = false; }
                if (_btnBriefing != null) _btnBriefing.IsEnabled = false;
                if (_statusText  != null) _statusText.Text = "⏳ run_morning_ES.py en cours (CME ES + CBOE SPY + Claude + PDF)…";
            });
            Task.Run(() =>
            {
                try
                {
                    var psi = new ProcessStartInfo
                    {
                        FileName         = OfkUtils.ResolveExe(PythonExePath),
                        Arguments        = "\"" + ScriptPath + "\" --ignore-holiday",
                        UseShellExecute  = false,
                        CreateNoWindow   = false,
                        WindowStyle      = ProcessWindowStyle.Normal,
                        WorkingDirectory = System.IO.Path.GetDirectoryName(ScriptPath) ?? @"C:\Users\steph\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline",
                    };
                    using var proc = Process.Start(psi);
                    bool exited = proc?.WaitForExit(300_000) ?? false;
                    int exitCode = exited ? (proc?.ExitCode ?? -1) : -99;
                    if (exitCode == 0) LoadLevels();
                    Application.Current?.Dispatcher?.Invoke(() =>
                    {
                        string msg = exitCode == 0 ? "✅ Données mises à jour" : $"⚠ Exit {exitCode}";
                        if (_btnRefresh  != null) { _btnRefresh.Content = "▶  GEX LEVELS"; _btnRefresh.Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(20,40,90)); _btnRefresh.Foreground = new SolidColorBrush(System.Windows.Media.Color.FromRgb(79,139,209)); _btnRefresh.IsEnabled = true; }
                        if (_btnBriefing != null) _btnBriefing.IsEnabled = true;
                        var lv = _levels;
                        if (_statusText != null) _statusText.Text = msg + (exitCode == 0 ? $"  —  {lv.TradeDate}" : "");
                        UpdatePanelText();
                    });
                    RedrawChart();
                }
                catch (Exception ex)
                {
                    Application.Current?.Dispatcher?.Invoke(() =>
                    {
                        if (_btnRefresh  != null) { _btnRefresh.Content = "▶  GEX LEVELS"; _btnRefresh.IsEnabled = true; }
                        if (_btnBriefing != null) _btnBriefing.IsEnabled = true;
                        if (_statusText  != null) _statusText.Text = "❌ " + ex.Message.Substring(0, Math.Min(60, ex.Message.Length));
                    });
                }
                finally { _isRunning = false; }
            });
        }

        // ── OpenBriefing ──────────────────────────────────────────────────────

        private void OpenBriefing()
        {
            try
            {
                if (!Directory.Exists(BriefingDir)) { if (_statusText != null) Application.Current?.Dispatcher?.Invoke(() => _statusText.Text = "❌ Dossier PDF introuvable : " + BriefingDir); return; }
                var pdfs = Directory.GetFiles(BriefingDir, "briefing_ES_*.pdf").OrderByDescending(f => f).ToArray();
                if (pdfs.Length == 0) { if (_statusText != null) Application.Current?.Dispatcher?.Invoke(() => _statusText.Text = "⚠ Aucun PDF trouvé"); return; }
                Process.Start(new ProcessStartInfo(pdfs[0]) { UseShellExecute = true });
                if (_statusText != null) Application.Current?.Dispatcher?.Invoke(() => _statusText.Text = "📄 " + Path.GetFileName(pdfs[0]));
            }
            catch (Exception ex) { if (_statusText != null) Application.Current?.Dispatcher?.Invoke(() => _statusText.Text = "❌ " + ex.Message.Substring(0, Math.Min(60, ex.Message.Length))); }
        }

        // ── Rendu chart ───────────────────────────────────────────────────────

        protected override void OnRender(RenderContext context, DrawingLayouts layout)
        {
            var lv = _levels;
            if (!lv.Loaded || ChartInfo == null) return;
            int chartW = ChartArea.Width;

            // Zone pinning
            if (ShowPinZone && lv.GexRegime > 0 && lv.CallWall > 0 && lv.PutWall > 0)
            {
                int yCw = (int)ChartInfo.GetYByPrice((decimal)lv.CallWall, false);
                int yPw = (int)ChartInfo.GetYByPrice((decimal)lv.PutWall,  false);
                if (yCw < yPw) context.FillRectangle(DrawingColor.FromArgb(PinZoneOpacity * 255 / 100, 0, 200, 0), new Rectangle(0, yCw, chartW, yPw - yCw));
            }

            // Bande Expected Move (TastyTrade-style si EM TT dispo dans le pipeline)
            if (ShowEMZone && lv.ExpectedMoveHigh > 0 && lv.ExpectedMoveLow > 0)
            {
                int yH = (int)ChartInfo.GetYByPrice((decimal)lv.ExpectedMoveHigh, false);
                int yL = (int)ChartInfo.GetYByPrice((decimal)lv.ExpectedMoveLow,  false);
                int alphaEM = Math.Max(2, Math.Min(30, EMBandOpacity)) * 255 / 100;
                if (yH < yL)
                    context.FillRectangle(
                        DrawingColor.FromArgb(alphaEM, EMBandColor.R, EMBandColor.G, EMBandColor.B),
                        new Rectangle(0, yH, chartW, yL - yH));
            }

            // ─── Zones Gamma (Phase 1, TanukiTrade-style) ──────────────────────
            // Bornes : Put Wall ID < pTrans < cTrans < Call Wall ID
            if (ShowGammaZones)
            {
                int alpha = Math.Max(2, Math.Min(40, GammaZoneOpacity)) * 255 / 100;
                double cw = lv.CallWallIntraday;
                double pw = lv.PutWallIntraday;
                double ct = lv.CTransIntraday;
                double pt = lv.PTransIntraday;
                int chartH = ChartArea.Height;

                int Clamp(double price)
                {
                    int y = (int)ChartInfo.GetYByPrice((decimal)price, false);
                    if (y < 0) y = 0;
                    if (y > chartH) y = chartH;
                    return y;
                }

                if (cw > 0)
                {
                    int yCw = Clamp(cw);
                    if (yCw > 0)
                        context.FillRectangle(
                            DrawingColor.FromArgb(alpha, ZoneSqueezeColor.R, ZoneSqueezeColor.G, ZoneSqueezeColor.B),
                            new Rectangle(0, 0, chartW, yCw));
                }

                if (cw > 0 && ct > 0 && ct < cw)
                {
                    int yCw = Clamp(cw);
                    int yCt = Clamp(ct);
                    if (yCt > yCw)
                        context.FillRectangle(
                            DrawingColor.FromArgb(alpha, ZonePositiveColor.R, ZonePositiveColor.G, ZonePositiveColor.B),
                            new Rectangle(0, yCw, chartW, yCt - yCw));
                }

                if (ct > 0 && pt > 0 && pt < ct)
                {
                    int yCt = Clamp(ct);
                    int yPt = Clamp(pt);
                    if (yPt > yCt)
                        context.FillRectangle(
                            DrawingColor.FromArgb(alpha, ZoneTransitionColor.R, ZoneTransitionColor.G, ZoneTransitionColor.B),
                            new Rectangle(0, yCt, chartW, yPt - yCt));
                }

                if (pw > 0 && pt > 0 && pw < pt)
                {
                    int yPt = Clamp(pt);
                    int yPw = Clamp(pw);
                    if (yPw > yPt)
                        context.FillRectangle(
                            DrawingColor.FromArgb(alpha, ZoneNegativeColor.R, ZoneNegativeColor.G, ZoneNegativeColor.B),
                            new Rectangle(0, yPt, chartW, yPw - yPt));
                }

                if (pw > 0)
                {
                    int yPw = Clamp(pw);
                    if (yPw < chartH)
                        context.FillRectangle(
                            DrawingColor.FromArgb(alpha, ZoneSqueezeColor.R, ZoneSqueezeColor.G, ZoneSqueezeColor.B),
                            new Rectangle(0, yPw, chartW, chartH - yPw));
                }
            }

            var penGF   = new RenderPen(GammaFlipColor,        LineWidth + 1);
            var penVT   = new RenderPen(VolTriggerColor,       LineWidth);
            var penCW   = new RenderPen(CallWallColor,         LineWidth);
            var penPW   = new RenderPen(PutWallColor,          LineWidth);
            var penRP   = new RenderPen(RiskPivotColor,        LineWidth);
            var penVF   = new RenderPen(VannaFlipColor,        1);
            var penCM   = new RenderPen(CharmMagnetColor,      1);
            var penMP   = new RenderPen(MaxPainColor,          LineWidth);
            var penEMH  = new RenderPen(ExpectedMoveHighColor, 1);
            var penEML  = new RenderPen(ExpectedMoveLowColor,  1);
            var penOI1  = new RenderPen(TopOI1Color,           1);
            var penOI2  = new RenderPen(TopOI2Color,           1);
            var penOI3  = new RenderPen(TopOI3Color,           1);
            var penCWid = new RenderPen(CallWallIntradayColor, LineWidth + 1);
            var penPWid = new RenderPen(PutWallIntradayColor,  LineWidth + 1);
            var penOIid1= new RenderPen(TopOIIntraday1Color,   2);
            var penOIid2= new RenderPen(TopOIIntraday2Color,   2);
            var penOIid3= new RenderPen(TopOIIntraday3Color,   2);

            DrawLevel(context, chartW, lv.GammaFlip,        ShowGammaFlip,        GammaFlipColor,        penGF,  10, 5, $"Gamma Flip  {lv.GammaFlip:F0}  [GEX {lv.GexTotal/1e9:+0.000;-0.000}B]");
            DrawLevel(context, chartW, lv.VolTrigger,       ShowVolTrigger,       VolTriggerColor,       penVT,  8,  4, $"Vol Trigger  {lv.VolTrigger:F0}");
            DrawLevel(context, chartW, lv.CallWall,         ShowCallWall,         CallWallColor,         penCW,  8,  4, $"Call Wall  {lv.CallWall:F0}  [GEX {lv.CallWallGex/1e9:+0.000;-0.000}B]");
            DrawLevel(context, chartW, lv.PutWall,          ShowPutWall,          PutWallColor,          penPW,  8,  4, $"Put Wall  {lv.PutWall:F0}  [GEX {lv.PutWallGex/1e9:+0.000;-0.000}B]");
            DrawLevel(context, chartW, lv.RiskPivot,        ShowRiskPivot,        RiskPivotColor,        penRP,  10, 5, $"Risk Pivot  {lv.RiskPivot:F0}");
            DrawLevel(context, chartW, lv.VannaFlip,        ShowVannaFlip,        VannaFlipColor,        penVF,  2,  4, $"Vanna Flip  {lv.VannaFlip:F0}  [VEX {lv.VexTotal/1e8:+0.00;-0.00}]");
            DrawLevel(context, chartW, lv.CharmMagnet,      ShowCharmMagnet,      CharmMagnetColor,      penCM,  2,  4, $"Charm  {lv.CharmMagnet:F0}");
            DrawLevel(context, chartW, lv.MaxPain,          ShowMaxPain,          MaxPainColor,          penMP,  6,  4, $"Max Pain  {lv.MaxPain:F0}");
            DrawLevel(context, chartW, lv.ExpectedMoveHigh, ShowExpectedMoveHigh, ExpectedMoveHighColor, penEMH, 4,  6, $"EM High  {lv.ExpectedMoveHigh:F0}");
            DrawLevel(context, chartW, lv.ExpectedMoveLow,  ShowExpectedMoveLow,  ExpectedMoveLowColor,  penEML, 4,  6, $"EM Low  {lv.ExpectedMoveLow:F0}");
            DrawLevel(context, chartW, lv.TopOI1,           ShowTopOI1,           TopOI1Color,           penOI1, 3,  6, $"OI #1  {lv.TopOI1:F0}  ({lv.TopOI1Vol:N0})");
            DrawLevel(context, chartW, lv.TopOI2,           ShowTopOI2,           TopOI2Color,           penOI2, 3,  6, $"OI #2  {lv.TopOI2:F0}  ({lv.TopOI2Vol:N0})");
            DrawLevel(context, chartW, lv.TopOI3,           ShowTopOI3,           TopOI3Color,           penOI3, 3,  6, $"OI #3  {lv.TopOI3:F0}  ({lv.TopOI3Vol:N0})");
            // Niveaux INTRADAY (CBOE 0-7 DTE — primaires scalping)
            string idTag = $" [0-{(lv.WallsIntradayMaxDte > 0 ? lv.WallsIntradayMaxDte : 7)}d]";
            DrawLevel(context, chartW, lv.CallWallIntraday, ShowCallWallIntraday, CallWallIntradayColor, penCWid, 9, 4, $"CW ID  {lv.CallWallIntraday:F0}  [GEX {lv.CallWallIntradayGex/1e9:+0.000;-0.000}B]" + idTag);
            DrawLevel(context, chartW, lv.PutWallIntraday,  ShowPutWallIntraday,  PutWallIntradayColor,  penPWid, 9, 4, $"PW ID  {lv.PutWallIntraday:F0}  [GEX {lv.PutWallIntradayGex/1e9:+0.000;-0.000}B]" + idTag);
            DrawLevel(context, chartW, lv.TopOIIntraday1,   ShowTopOIIntraday1,   TopOIIntraday1Color,   penOIid1, 3, 6, $"OI ID #1  {lv.TopOIIntraday1:F0}  ({lv.TopOIIntraday1Vol:N0})");
            DrawLevel(context, chartW, lv.TopOIIntraday2,   ShowTopOIIntraday2,   TopOIIntraday2Color,   penOIid2, 3, 6, $"OI ID #2  {lv.TopOIIntraday2:F0}  ({lv.TopOIIntraday2Vol:N0})");
            DrawLevel(context, chartW, lv.TopOIIntraday3,   ShowTopOIIntraday3,   TopOIIntraday3Color,   penOIid3, 3, 6, $"OI ID #3  {lv.TopOIIntraday3:F0}  ({lv.TopOIIntraday3Vol:N0})");
            // Transition levels cTrans/pTrans (Phase 3 — TanukiTrade-style)
            var penCT = new RenderPen(CTransIntradayColor, LineWidth);
            var penPT = new RenderPen(PTransIntradayColor, LineWidth);
            DrawLevel(context, chartW, lv.CTransIntraday,   ShowCTransIntraday,   CTransIntradayColor,   penCT, 3, 8, $"cTrans  {lv.CTransIntraday:F0}  [call dom.]" + idTag);
            DrawLevel(context, chartW, lv.PTransIntraday,   ShowPTransIntraday,   PTransIntradayColor,   penPT, 3, 8, $"pTrans  {lv.PTransIntraday:F0}  [put dom.]" + idTag);
            // DEX D+ / D- (Phase 4 — TanukiTrade-style, pression de hedging directionnelle)
            var penDp = new RenderPen(DexPlusIntradayColor,  LineWidth);
            var penDm = new RenderPen(DexMinusIntradayColor, LineWidth);
            DrawLevel(context, chartW, lv.DexPlusIntraday,  ShowDexPlusIntraday,  DexPlusIntradayColor,  penDp, 2, 5, $"D+  {lv.DexPlusIntraday:F0}  [DEX {lv.DexPlusIntradayDex/1e6:+0.00;-0.00}M]" + idTag);
            DrawLevel(context, chartW, lv.DexMinusIntraday, ShowDexMinusIntraday, DexMinusIntradayColor, penDm, 2, 5, $"D-  {lv.DexMinusIntraday:F0}  [DEX {lv.DexMinusIntradayDex/1e6:+0.00;-0.00}M]" + idTag);
            // Abs GEX Ab1/Ab2/Ab3 (Phase 5 — pin risk, gamma absolue concentrée)
            var penAb1 = new RenderPen(AbsGex1Color, 1);
            var penAb2 = new RenderPen(AbsGex2Color, 1);
            var penAb3 = new RenderPen(AbsGex3Color, 1);
            DrawLevel(context, chartW, lv.AbsGex1, ShowAbsGex1, AbsGex1Color, penAb1, 2, 8, $"Ab1  {lv.AbsGex1:F0}  [|GEX| {lv.AbsGex1Gex/1e9:+0.000;-0.000}B]" + idTag);
            DrawLevel(context, chartW, lv.AbsGex2, ShowAbsGex2, AbsGex2Color, penAb2, 2, 8, $"Ab2  {lv.AbsGex2:F0}  [|GEX| {lv.AbsGex2Gex/1e9:+0.000;-0.000}B]" + idTag);
            DrawLevel(context, chartW, lv.AbsGex3, ShowAbsGex3, AbsGex3Color, penAb3, 2, 8, $"Ab3  {lv.AbsGex3:F0}  [|GEX| {lv.AbsGex3Gex/1e9:+0.000;-0.000}B]" + idTag);
            // Extended walls (Phase 6 — TanukiTrade GEX7-10), couleur selon côté call/put
            DrawingColor extColor(string side) => side == "put" ? GexExtPutColor : GexExtCallColor;
            void DrawExt(int n, double price, bool show, double gex, string side)
            {
                var col = extColor(side);
                var pen = new RenderPen(col, 1);
                string sideTag = side == "put" ? "P" : "C";
                DrawLevel(context, chartW, price, show, col, pen, 2, 10,
                    $"GEX#{6+n}{sideTag}  {price:F0}  [{gex/1e9:+0.000;-0.000}B]" + idTag);
            }
            DrawExt(1, lv.GexExt1, ShowGexExt1, lv.GexExt1Gex, lv.GexExt1Side);
            DrawExt(2, lv.GexExt2, ShowGexExt2, lv.GexExt2Gex, lv.GexExt2Side);
            DrawExt(3, lv.GexExt3, ShowGexExt3, lv.GexExt3Gex, lv.GexExt3Side);
            DrawExt(4, lv.GexExt4, ShowGexExt4, lv.GexExt4Gex, lv.GexExt4Side);
            // Niveaux 0DTE (Phase C)
            var penMP0  = new RenderPen(MaxPain0DTEColor,     1);
            var penPin0 = new RenderPen(PinStrike0DTEColor,   LineWidth + 1);
            var penChM0 = new RenderPen(CharmMagnet0DTEColor, LineWidth);
            string zd = lv.ZeroDTEDte == 0 ? "0DTE" : $"{lv.ZeroDTEDte}DTE";
            DrawLevel(context, chartW, lv.MaxPain0DTE,     ShowMaxPain0DTE,     MaxPain0DTEColor,     penMP0,  6, 4, $"Max Pain {zd}  {lv.MaxPain0DTE:F0}");
            DrawLevel(context, chartW, lv.PinStrike0DTE,   ShowPinStrike0DTE,   PinStrike0DTEColor,   penPin0, 5, 3, $"Pin {zd}  {lv.PinStrike0DTE:F0}");
            DrawLevel(context, chartW, lv.CharmMagnet0DTE, ShowCharmMagnet0DTE, CharmMagnet0DTEColor, penChM0, 4, 3, $"Charm {zd}  {lv.CharmMagnet0DTE:F0}");

            // ─── Bannières alertes on-chart ────────────────────────────────
            if (EnableVisualBanners)
            {
                BannerEntry[] active;
                lock (_bannerSync)
                {
                    _banners.RemoveAll(b => (DateTime.Now - b.Time).TotalSeconds > BannerDurationSeconds);
                    active = _banners.ToArray();
                }
                if (active.Length > 0)
                {
                    var bFont = new RenderFont("Arial", 9);
                    int count = Math.Min(active.Length, MaxVisibleBanners);
                    int bH = 22, bGap = 3, bTop = 8, bRight = 10;

                    // Détection dynamique du bord droit utile :
                    // si le DOM trader est ouvert, ChartArea.Width inclut sa
                    // largeur. On utilise la position X de la dernière barre
                    // dessinée + une petite marge comme bord droit effectif —
                    // le DOM trader vit toujours après cette zone.
                    int rightEdge = chartW;
                    try
                    {
                        if (CurrentBar > 0)
                        {
                            int lastBarX = (int)ChartInfo.GetXByBar(CurrentBar - 1);
                            if (lastBarX > 0 && lastBarX + 20 < chartW)
                                rightEdge = lastBarX + 20;
                        }
                    }
                    catch { }

                    for (int i = 0; i < count; i++)
                    {
                        var entry = active[active.Length - 1 - i];
                        int remain = Math.Max(0, BannerDurationSeconds - (int)(DateTime.Now - entry.Time).TotalSeconds);
                        string txt = $"  {entry.Message}  ({remain}s)";
                        var ts = context.MeasureString(txt, bFont);
                        int bW = Math.Min((int)ts.Width + 20, (int)(rightEdge * 0.7));
                        int bx = rightEdge - bW - bRight;
                        int by = bTop + i * (bH + bGap);
                        float fade = Math.Min(1f, remain / 5f);
                        int bgA = (int)(215 * fade);
                        int fgA = (int)(240 * fade);
                        int strA = (int)(255 * fade);
                        context.FillRectangle(DrawingColor.FromArgb(bgA, 15, 15, 20), new Rectangle(bx, by, bW, bH));
                        context.FillRectangle(DrawingColor.FromArgb(strA, entry.Color.R, entry.Color.G, entry.Color.B), new Rectangle(bx, by, 4, bH));
                        context.DrawString(txt, bFont, DrawingColor.FromArgb(fgA, 220, 220, 230), bx + 8, by + 3);
                    }
                }
            }

            // ─── Overlay REPLAY (centré en haut du chart) ───────────────────
            if (_replayMode)
            {
                var rFont = new RenderFont("Arial Bold", 13);
                string rTxt = $"🎬  REPLAY  {_replayTimestamp:HH:mm}";
                var rs = context.MeasureString(rTxt, rFont);
                int rW = (int)rs.Width + 20;
                int rH = (int)rs.Height + 8;
                int rx = (chartW - rW) / 2;
                int ry = 8;
                context.FillRectangle(DrawingColor.FromArgb(220, 60, 40, 90), new Rectangle(rx, ry, rW, rH));
                context.FillRectangle(DrawingColor.FromArgb(255, 189, 147, 249), new Rectangle(rx, ry, rW, 2));
                context.DrawString(rTxt, rFont, DrawingColor.FromArgb(255, 230, 220, 250), rx + 10, ry + 4);
            }
        }

        // Font dynamique (LabelFontSize était hard-codé à 9 — bug fix)
        private RenderFont GetLabelFont() => new RenderFont("Arial", Math.Max(7, Math.Min(14, LabelFontSize)));

        private void DrawLevel(RenderContext ctx, int chartW, double price, bool show,
                                DrawingColor color, RenderPen pen, int dashLen, int gapLen, string label)
        {
            if (!show || price <= 0) return;
            int y = (int)ChartInfo.GetYByPrice((decimal)price, false);
            if (y < 0 || y > ChartArea.Height + 200) return;

            // Ligne (option : extension droite seulement, depuis la dernière barre)
            int xStart = 0;
            if (LineExtensionRightOnly && CurrentBar > 0)
            {
                int xLast = (int)ChartInfo.GetXByBar(CurrentBar - 1);
                xStart = Math.Max(0, xLast);
            }

            if (UseSolidLines)
            {
                ctx.DrawLine(pen, xStart, y, chartW, y);
            }
            else
            {
                int x = xStart; bool drawing = true;
                while (x < chartW)
                {
                    int end = Math.Min(x + (drawing ? dashLen : gapLen), chartW);
                    if (drawing) ctx.DrawLine(pen, x, y, end, y);
                    x = end; drawing = !drawing;
                }
            }

            // Label (option : on/off + position gauche/droite + opacité fond)
            if (!ShowLineLabels) return;
            var font = GetLabelFont();
            var ts = ctx.MeasureString(label, font);
            int lw = (int)ts.Width + 12, lh = (int)ts.Height + 4;
            int lx = LabelOnRight ? chartW - lw - 8 : 6;
            int ly = y - (int)ts.Height - 6;
            int bgAlpha = Math.Max(20, Math.Min(100, LabelBgOpacity)) * 255 / 100;
            ctx.FillRectangle(DrawingColor.FromArgb(bgAlpha, 10, 10, 10),               new Rectangle(lx-2, ly-1, lw, lh));
            ctx.FillRectangle(DrawingColor.FromArgb(220, color.R, color.G, color.B),    new Rectangle(lx-2, ly-1, 3,  lh));
            ctx.DrawString(label, font, DrawingColor.FromArgb(255, color.R, color.G, color.B), lx+4, ly+2);
        }

        private static System.Windows.Controls.ControlTemplate CreateButtonTemplate()
        {
            var t  = new System.Windows.Controls.ControlTemplate(typeof(Button));
            var b  = new System.Windows.FrameworkElementFactory(typeof(Border));
            b.SetBinding(Border.BackgroundProperty,    new System.Windows.Data.Binding("Background")    { RelativeSource = System.Windows.Data.RelativeSource.TemplatedParent });
            b.SetBinding(Border.BorderBrushProperty,   new System.Windows.Data.Binding("BorderBrush")   { RelativeSource = System.Windows.Data.RelativeSource.TemplatedParent });
            b.SetBinding(Border.BorderThicknessProperty,new System.Windows.Data.Binding("BorderThickness"){ RelativeSource = System.Windows.Data.RelativeSource.TemplatedParent });
            b.SetValue(Border.CornerRadiusProperty, new CornerRadius(3));
            var cp = new System.Windows.FrameworkElementFactory(typeof(ContentPresenter));
            cp.SetValue(ContentPresenter.HorizontalAlignmentProperty, HorizontalAlignment.Center);
            cp.SetValue(ContentPresenter.VerticalAlignmentProperty,   VerticalAlignment.Center);
            b.AppendChild(cp); t.VisualTree = b; return t;
        }

        public override void Dispose()
        {
            // Tuer le process loop intraday s'il tourne encore
            try
            {
                if (_loopProcess != null && !_loopProcess.HasExited)
                {
                    try { _loopProcess.Kill(entireProcessTree: true); } catch { }
                    _loopProcess.WaitForExit(1000);
                }
            }
            catch { }
            _loopProcess = null;
            _loopRunning = false;

            try { Application.Current?.Dispatcher?.Invoke(() => ClosePanel()); } catch { }
            base.Dispose();
        }

        // ── Loop intraday refresh : background process toggle ─────────────────
        private void ToggleLoop()
        {
            if (_loopRunning) StopLoop();
            else              StartLoop();
        }

        private void StartLoop()
        {
            if (_loopRunning) return;
            if (!File.Exists(IntradayRefreshScriptPath))
            {
                if (_statusText != null)
                    _statusText.Text = "❌ Script intraday introuvable : " + IntradayRefreshScriptPath;
                return;
            }
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName               = OfkUtils.ResolveExe(PythonExePath),
                    Arguments              = "\"" + IntradayRefreshScriptPath + "\" ES --loop",
                    UseShellExecute        = false,
                    CreateNoWindow         = true,
                    WindowStyle            = ProcessWindowStyle.Hidden,
                    WorkingDirectory       = System.IO.Path.GetDirectoryName(IntradayRefreshScriptPath)
                                             ?? @"C:\Users\steph\Documents\GitHub\OFK_Atas_GEX\OFK_GEX_Pipeline",
                    RedirectStandardOutput = true,
                    RedirectStandardError  = true,
                };
                // Force UTF-8 sur stdout/stderr de Python : sinon les caractères
                // box-drawing (─, ═, →) lèvent UnicodeEncodeError sur cp1252
                // (encoding par défaut quand stdout est piped sur Windows).
                psi.Environment["PYTHONIOENCODING"] = "utf-8";
                psi.Environment["PYTHONUTF8"]       = "1";
                _loopProcess = Process.Start(psi);
                if (_loopProcess == null)
                {
                    if (_statusText != null) _statusText.Text = "❌ Échec démarrage loop";
                    return;
                }
                // CRITICAL : consommer les streams en async pour ne pas bloquer
                // le process Python quand il print (buffer pipe ~4KB se remplit
                // sinon, le process se fige sur le 2-3e cycle).
                _loopProcess.OutputDataReceived += (s, e) => { /* discard */ };
                _loopProcess.ErrorDataReceived  += (s, e) => { /* discard */ };
                try { _loopProcess.BeginOutputReadLine(); } catch { }
                try { _loopProcess.BeginErrorReadLine();  } catch { }
                _loopRunning = true;
                _loopProcess.EnableRaisingEvents = true;
                _loopProcess.Exited += (s, e) =>
                {
                    _loopRunning = false;
                    _loopProcess = null;
                    Application.Current?.Dispatcher?.BeginInvoke(new Action(() =>
                    {
                        UpdateLoopButton();
                        if (_statusText != null) _statusText.Text = "⏹ Loop intraday s'est arrêté";
                    }));
                };
                UpdateLoopButton();
                if (_statusText != null)
                    _statusText.Text = $"🔄 Loop intraday ON  (PID {_loopProcess.Id})";
            }
            catch (Exception ex)
            {
                if (_statusText != null)
                    _statusText.Text = "❌ " + ex.Message.Substring(0, Math.Min(60, ex.Message.Length));
            }
        }

        private void StopLoop()
        {
            try
            {
                if (_loopProcess != null && !_loopProcess.HasExited)
                {
                    try { _loopProcess.Kill(entireProcessTree: true); } catch { }
                    _loopProcess.WaitForExit(2000);
                }
            }
            catch { }
            _loopProcess = null;
            _loopRunning = false;
            UpdateLoopButton();
            if (_statusText != null) _statusText.Text = "⏹ Loop intraday OFF";
        }

        private void UpdateLoopButton()
        {
            if (_btnLoop == null) return;
            Application.Current?.Dispatcher?.BeginInvoke(new Action(() =>
            {
                if (_btnLoop == null) return;
                if (_loopRunning)
                {
                    _btnLoop.Content     = "⏹  Loop intraday : ON";
                    _btnLoop.Background  = new SolidColorBrush(System.Windows.Media.Color.FromRgb(20, 70, 35));
                    _btnLoop.Foreground  = new SolidColorBrush(System.Windows.Media.Color.FromRgb(63, 185, 80));
                    _btnLoop.BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromRgb(63, 185, 80));
                }
                else
                {
                    _btnLoop.Content     = "▶  Loop intraday : OFF";
                    _btnLoop.Background  = new SolidColorBrush(System.Windows.Media.Color.FromRgb(35, 35, 45));
                    _btnLoop.Foreground  = new SolidColorBrush(System.Windows.Media.Color.FromRgb(150, 150, 160));
                    _btnLoop.BorderBrush = new SolidColorBrush(System.Windows.Media.Color.FromRgb(80, 80, 90));
                }
            }));
        }

        // ── Replay : ouverture de la fenêtre WPF ──────────────────────────────
        private void OpenReplayWindow()
        {
            if (_replayWindow != null) { try { _replayWindow.Activate(); } catch { } return; }
            var snaps = GexLoader.ListSnapshots(IntradayHistoryDir, "ES", DateTime.Today);
            if (snaps.Count == 0)
            {
                try {
                    MessageBox.Show(
                        "Aucun snapshot intraday trouvé pour aujourd'hui.\n\n" +
                        "Vérifie que run_intraday_refresh.py tourne et que le dossier est correct :\n" +
                        IntradayHistoryDir,
                        "Replay intraday", MessageBoxButton.OK, MessageBoxImage.Information);
                } catch { }
                return;
            }
            _replayWindow = new ReplayWindow(snaps, "ES",
                onSnapshotSelected: (path, ts) => LoadReplaySnapshot(path, ts),
                onExitReplay:       () => ExitReplayMode());
            _replayWindow.Closed += (s, e) => {
                _replayWindow = null;
                if (_replayMode) ExitReplayMode();
            };
            _replayWindow.Show();
        }

        // ── LoadLevels (délègue au shared loader) ─────────────────────────────
        private void LoadLevels()
        {
            if (_replayMode) return; // freeze pendant le replay
            var (gex, meta, ok) = GexLoader.Load(JsonPath, "es");
            if (!ok) { _levelsLoaded = false; return; }
            _levels       = gex;
            _meta         = meta;
            _loadedDate   = DateTime.Today.ToString("yyyy-MM-dd");
            _lastLoadTime = DateTime.Now;
            _levelsLoaded = true;
            LoadAlertStats();
        }

        // ── Replay intraday : chargement d'un snapshot historique ─────────────
        public void LoadReplaySnapshot(string snapshotPath, DateTime timestamp)
        {
            var (gex, meta, ok) = GexLoader.LoadSnapshotPath(snapshotPath, "es");
            if (!ok) return;
            _replayMode      = true;
            _replayTimestamp = timestamp;
            _levels          = gex;
            _meta            = meta;
            _levelsLoaded    = true;
            try { Application.Current?.Dispatcher?.BeginInvoke(new Action(() => UpdatePanelText())); } catch { }
            try { RedrawChart(); } catch { }
        }

        public void ExitReplayMode()
        {
            _replayMode      = false;
            _replayTimestamp = DateTime.MinValue;
            LoadLevels();
            try { Application.Current?.Dispatcher?.BeginInvoke(new Action(() => UpdatePanelText())); } catch { }
            try { RedrawChart(); } catch { }
        }

        public override string ToString() => "OFK ES GEX Levels";
    }
}
