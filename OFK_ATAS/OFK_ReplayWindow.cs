// ============================================================================
//  OFK_ReplayWindow.cs — Fenêtre WPF pour replay intraday GEX
//
//  Affiche un slider permettant de naviguer dans les snapshots intraday
//  horodatés (générés par run_intraday_refresh.py toutes les 5 min).
//  À chaque changement de position, charge le snapshot correspondant
//  via le callback onSnapshotSelected, qui met à jour les niveaux de
//  l'indicateur GEX_Levels.
//
//  Bouton "Live" : sort du mode replay et reprend le live (last full_levels).
// ============================================================================
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;

namespace OFK_GEX
{
    public class ReplayWindow : Window
    {
        private readonly List<GexLoader.SnapshotInfo> _snapshots;
        private readonly string _symbol;
        private readonly Action<string, DateTime> _onSnapshotSelected;
        private readonly Action _onExitReplay;

        private Slider    _slider      = null!;
        private TextBlock _tsLabel     = null!;
        private TextBlock _rangeLabel  = null!;
        private TextBlock _statusLabel = null!;
        private Button    _btnLive     = null!;
        private Button    _btnPrev     = null!;
        private Button    _btnNext     = null!;

        public ReplayWindow(List<GexLoader.SnapshotInfo> snapshots, string symbol,
                            Action<string, DateTime> onSnapshotSelected,
                            Action onExitReplay)
        {
            _snapshots          = snapshots ?? new List<GexLoader.SnapshotInfo>();
            _symbol             = (symbol ?? "NQ").ToUpperInvariant();
            _onSnapshotSelected = onSnapshotSelected;
            _onExitReplay       = onExitReplay;
            BuildUI();
            // Sélection initiale = dernier snapshot (le plus récent)
            if (_snapshots.Count > 0)
            {
                _slider.Value = _snapshots.Count - 1;
                ApplyCurrentSelection();
            }
        }

        private void BuildUI()
        {
            Title  = $"Replay {_symbol} — {_snapshots.Count} snapshots";
            Width  = 620;
            Height = 240;
            Background = new SolidColorBrush(Color.FromRgb(13, 17, 23));
            ResizeMode = ResizeMode.CanResize;
            MinWidth   = 480; MinHeight = 200;
            Topmost    = false;
            ShowInTaskbar = true;
            FontFamily = new FontFamily("Segoe UI");
            SourceInitialized += (s, e) => ApplyDarkTitleBar(this);

            var bgColor      = Color.FromRgb(22, 27, 39);
            var bgDark       = Color.FromRgb(13, 17, 23);
            var borderColor  = Color.FromRgb(33, 41, 61);
            var textColor    = Color.FromRgb(201, 209, 217);
            var textDimColor = Color.FromRgb(139, 148, 158);
            var accentPurple = Color.FromRgb(189, 147, 249);
            var accentRed    = Color.FromRgb(239, 83, 80);

            var root = new Border { Background = new SolidColorBrush(bgColor) };
            var outer = new StackPanel { Orientation = Orientation.Vertical };

            // Header
            var hdr = new Border
            {
                Background = new SolidColorBrush(bgDark),
                Padding = new Thickness(12, 8, 12, 8),
                BorderBrush = new SolidColorBrush(borderColor),
                BorderThickness = new Thickness(0, 0, 0, 1)
            };
            hdr.Child = new TextBlock
            {
                Text = $"🎬  Replay intraday {_symbol}",
                Foreground = new SolidColorBrush(accentPurple),
                FontSize = 13,
                FontWeight = FontWeights.SemiBold
            };
            outer.Children.Add(hdr);

            // Timestamp en gros
            var tsSec = new Border { Padding = new Thickness(12, 12, 12, 4) };
            _tsLabel = new TextBlock
            {
                Text = "—",
                FontFamily = new FontFamily("Consolas"),
                FontSize = 28,
                FontWeight = FontWeights.Bold,
                Foreground = new SolidColorBrush(textColor),
                HorizontalAlignment = HorizontalAlignment.Center
            };
            tsSec.Child = _tsLabel;
            outer.Children.Add(tsSec);

            // Range labels
            var rangeSec = new Border { Padding = new Thickness(12, 0, 12, 6) };
            var rangeGrid = new Grid();
            rangeGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            rangeGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            var rangeLeft = new TextBlock
            {
                Text = _snapshots.Count > 0 ? _snapshots[0].Timestamp.ToString("HH:mm") : "—",
                Foreground = new SolidColorBrush(textDimColor),
                FontSize = 10,
                HorizontalAlignment = HorizontalAlignment.Left
            };
            var rangeRight = new TextBlock
            {
                Text = _snapshots.Count > 0 ? _snapshots[_snapshots.Count - 1].Timestamp.ToString("HH:mm") : "—",
                Foreground = new SolidColorBrush(textDimColor),
                FontSize = 10,
                HorizontalAlignment = HorizontalAlignment.Right
            };
            Grid.SetColumn(rangeLeft, 0);
            Grid.SetColumn(rangeRight, 1);
            rangeGrid.Children.Add(rangeLeft);
            rangeGrid.Children.Add(rangeRight);
            rangeSec.Child = rangeGrid;
            outer.Children.Add(rangeSec);

            // Slider
            var sliderSec = new Border { Padding = new Thickness(12, 0, 12, 8) };
            _slider = new Slider
            {
                Minimum = 0,
                Maximum = Math.Max(0, _snapshots.Count - 1),
                Value = 0,
                TickFrequency = 1,
                IsSnapToTickEnabled = true,
                SmallChange = 1,
                LargeChange = 5,
                Foreground = new SolidColorBrush(accentPurple),
                Background = new SolidColorBrush(borderColor),
            };
            _slider.ValueChanged += (s, e) => ApplyCurrentSelection();
            _slider.PreviewKeyDown += (s, e) =>
            {
                if (e.Key == Key.Left)  { _slider.Value = Math.Max(_slider.Minimum, _slider.Value - 1); e.Handled = true; }
                if (e.Key == Key.Right) { _slider.Value = Math.Min(_slider.Maximum, _slider.Value + 1); e.Handled = true; }
            };
            sliderSec.Child = _slider;
            outer.Children.Add(sliderSec);

            // Boutons (Prev / Live / Next)
            var btnSec = new Border
            {
                Padding = new Thickness(12, 6, 12, 8),
                BorderBrush = new SolidColorBrush(borderColor),
                BorderThickness = new Thickness(0, 1, 0, 1)
            };
            var btnGrid = new Grid();
            btnGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            btnGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(8) });
            btnGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.5, GridUnitType.Star) });
            btnGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(8) });
            btnGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            _btnPrev = MakeButton("◀  Prev", Color.FromRgb(40, 50, 70), accentPurple);
            _btnPrev.Click += (s, e) => { if (_slider.Value > _slider.Minimum) _slider.Value--; };
            Grid.SetColumn(_btnPrev, 0);
            btnGrid.Children.Add(_btnPrev);

            _btnLive = MakeButton("▶  Reprendre LIVE", Color.FromRgb(60, 20, 30), accentRed);
            _btnLive.Click += (s, e) =>
            {
                try { _onExitReplay?.Invoke(); } catch { }
                Close();
            };
            Grid.SetColumn(_btnLive, 2);
            btnGrid.Children.Add(_btnLive);

            _btnNext = MakeButton("Next  ▶", Color.FromRgb(40, 50, 70), accentPurple);
            _btnNext.Click += (s, e) => { if (_slider.Value < _slider.Maximum) _slider.Value++; };
            Grid.SetColumn(_btnNext, 4);
            btnGrid.Children.Add(_btnNext);

            btnSec.Child = btnGrid;
            outer.Children.Add(btnSec);

            // Status / range label
            var statusSec = new Border { Background = new SolidColorBrush(bgDark), Padding = new Thickness(12, 5, 12, 6) };
            _rangeLabel = new TextBlock
            {
                Text = $"{_snapshots.Count} snapshots — flèches ←/→ pour naviguer",
                Foreground = new SolidColorBrush(textDimColor),
                FontSize = 10
            };
            statusSec.Child = _rangeLabel;
            outer.Children.Add(statusSec);

            _statusLabel = new TextBlock
            {
                Text = "",
                Foreground = new SolidColorBrush(textDimColor),
                FontSize = 9,
                Margin = new Thickness(12, 4, 12, 4)
            };
            outer.Children.Add(_statusLabel);

            root.Child = outer;
            Content = root;
        }

        private Button MakeButton(string text, Color bg, Color fg)
        {
            return new Button
            {
                Content = text,
                Height = 30,
                Background = new SolidColorBrush(bg),
                Foreground = new SolidColorBrush(fg),
                FontSize = 11,
                FontWeight = FontWeights.SemiBold,
                BorderBrush = new SolidColorBrush(fg),
                BorderThickness = new Thickness(1),
                Cursor = Cursors.Hand
            };
        }

        private void ApplyCurrentSelection()
        {
            int idx = (int)Math.Round(_slider.Value);
            if (idx < 0 || idx >= _snapshots.Count) return;
            var snap = _snapshots[idx];
            _tsLabel.Text = snap.Timestamp.ToString("HH:mm");
            _statusLabel.Text = $"snapshot {idx + 1}/{_snapshots.Count}  •  {System.IO.Path.GetFileName(snap.Path)}";
            try { _onSnapshotSelected?.Invoke(snap.Path, snap.Timestamp); } catch { }
        }

        // ── Dark title bar (Windows 10 1809+) ─────────────────────────────────
        [DllImport("dwmapi.dll")]
        private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);
        private const int DWMWA_USE_IMMERSIVE_DARK_MODE        = 20;
        private const int DWMWA_USE_IMMERSIVE_DARK_MODE_LEGACY = 19;

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
            catch { }
        }
    }
}
