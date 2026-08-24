using System.ComponentModel;
using System.Drawing;
using ATAS.Indicators;
using OFT.Rendering.Context;
using OFT.Rendering.Tools;

namespace OFK_GEX.Probe;

/// <summary>
/// Deliberately small ATAS X compatibility probe.
///
/// This class verifies the minimum surface needed by the future Mac-native
/// indicator: an ATAS data series, OnCalculate, and ATAS custom drawing. It
/// intentionally contains no WPF windows, custom editors, process launching,
/// platform P/Invoke, or repository-specific JSON logic.
/// </summary>
[DisplayName("OFK ATAS X Compatibility Probe")]
public sealed class OFK_Atas_X_Probe : Indicator
{
    private readonly ValueDataSeries _probeSeries;

    public OFK_Atas_X_Probe() : base(true)
    {
        Panel = IndicatorDataProvider.NewPanel;
        DenyToChangePanel = true;
        EnableCustomDrawing = true;
        SubscribeToDrawingEvents(
            DrawingLayouts.Historical |
            DrawingLayouts.LatestBar |
            DrawingLayouts.Final);

        _probeSeries = (ValueDataSeries)DataSeries[0];
        _probeSeries.Name = "ATAS X probe";
        _probeSeries.Color = Color.LimeGreen;
        _probeSeries.Width = 2;
        _probeSeries.ShowZeroValue = false;
    }

    protected override void OnCalculate(int bar, decimal value)
    {
        // A deterministic non-zero value makes the probe visible in a new
        // panel without depending on the market data or repository JSON.
        _probeSeries[bar] = 1m;
    }

    protected override void OnRender(RenderContext context, DrawingLayouts layout)
    {
        var font = new RenderFont("Arial", 14);
        context.DrawString(
            "OFK ATAS X probe — loaded",
            font,
            Color.LimeGreen,
            8,
            8);
    }

    public override string ToString() => "OFK ATAS X Compatibility Probe";
}
