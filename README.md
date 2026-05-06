# OFK_Atas_GEX

ATAS indicators and Python pipeline for trading the E-mini Nasdaq-100 (NQ) and E-mini S&P 500 (ES) futures using options-derived levels (GEX, DEX, walls, gamma flip, pin strikes) and AI-generated daily briefings.

## What it does

- **Python pipeline** scrapes CME and CBOE option chains, computes Greeks Exposure levels (GEX, VEX, DEX, CEX), enriches with VIX and macro context, and writes a JSON file every 5 minutes during RTH.
- **ATAS indicators (C#)** read the JSON and draw the levels live on NQ/ES charts, with an on-chart context score, a floating panel, an intraday replay, and 12 alert types.
- **AI briefing** uses Claude to generate a daily JSON briefing with regime analysis, RTH plan (buy/sell zones, invalidations), and risk alerts. Rendered as a dark-theme A4 PDF.

## Quick install

**Required path**: extract the repository into `C:\OFK_Atas_GEX\` (root of the C: drive).
The ATAS indicator default settings are pre-configured for this location. Installing elsewhere requires manual editing of indicator parameters in ATAS.

```powershell
# 1. Build the indicators
cd C:\OFK_Atas_GEX\OFK_ATAS
dotnet build OFK_Atas_GEX.csproj -c Release

# 2. Copy the DLL to ATAS
Copy-Item "bin\Release\net10.0-windows\OFK_Atas_GEX.dll" "$env:APPDATA\ATAS\Indicators\" -Force

# 3. Install Python dependencies
cd C:\OFK_Atas_GEX\OFK_GEX_Pipeline
pip install -r requirements.txt
playwright install chromium

# 4. Restart ATAS — indicators appear under "OFK Suite"
```

## Daily usage

```powershell
cd C:\OFK_Atas_GEX\OFK_GEX_Pipeline

# Morning run (~08:30 ET): full pipeline + AI briefing + PDF
python run_morning_NQ.py
python run_morning_ES.py

# Intraday refresh every 5 minutes during RTH (09:30-16:00 ET)
python run_intraday_refresh.py NQ --loop --interval 300
```

The ATAS indicators auto-reload the JSON every 5 minutes by default.

## Documentation

- **[OFK_ATAS/README.md](OFK_ATAS/README.md)** — ATAS indicators reference
- **[OFK_GEX_Pipeline/README.md](OFK_GEX_Pipeline/README.md)** — Python pipeline reference
- **[OFK_GEX_Pipeline/GUIDE_GEX_LEVELS.md](OFK_GEX_Pipeline/GUIDE_GEX_LEVELS.md)** — Plain-English guide to reading the levels (the most important doc for traders)
- **[docs/integration_handoff/](docs/integration_handoff/)** — Integration contract for external consumers (7 documents)

## Requirements

- Windows 10 / 11
- ATAS 1.5+ with .NET 10 SDK installed
- Python 3.10+
- Claude Code CLI (`npm i -g @anthropic-ai/claude-code`) for AI briefings

## License

MIT — see [LICENSE](LICENSE).
