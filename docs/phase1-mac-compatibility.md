# Phase 1 — Mac / ATAS X compatibility baseline

This phase establishes a small build-and-load probe before the GEX indicator is
refactored. The probe is intentionally independent of the Python pipeline and
does not read repository data.

## Recorded probe baseline

- Host: macOS 26.5, Apple Silicon arm64
- ATAS X: `8.0.14.647`
- .NET SDK: `10.0.203`
- ATAS X assemblies: `/Applications/ATAS X.app/Contents/MonoBundle`
- Python requirement: Python 3.10+ in an ignored `.venv`

## What is verified

- The local ATAS X assemblies can be referenced from macOS.
- The target runtime is `.NET 10` for the current ATAS X installation.
- The project targets `net10.0` with no Windows desktop targeting enabled.
- An `AnyCPU` custom indicator can derive from `ATAS.Indicators.Indicator`.
- A standard `ValueDataSeries` can be calculated and rendered.
- ATAS custom drawing (`RenderContext`, `RenderFont`, and `DrawingLayouts`)
  compiles against the installed ATAS X assemblies.
- The probe contains no WPF `Window`, custom WPF editor, Windows P/Invoke,
  process launching, hard-coded Windows path, or repository-specific logic.

## Build

From the repository root:

```bash
./scripts/build_atas_x_probe.sh
```

If ATAS X is installed elsewhere, point the script at its `MonoBundle` folder:

```bash
ATAS_X_PATH="/Applications/ATAS X.app/Contents/MonoBundle" \
  ./scripts/build_atas_x_probe.sh
```

The output is:

```text
OFK_ATAS_X_Probe/bin/Release/net10.0/OFK_Atas_X_Probe.dll
```

Build artifacts are ignored by Git. ATAS platform assemblies are referenced
from the local application and are not copied into the repository.

## Load test

1. Open ATAS X.
2. Open the Indicators window.
3. Choose **Add custom indicator** and select the probe DLL.
4. Add **OFK ATAS X Compatibility Probe** to a chart.
5. Confirm that the sub-panel shows a green histogram and the text
   `OFK ATAS X probe — loaded`.
6. Check ATAS X logs if the DLL is rejected:
   `~/Library/Application Support/ATAS/Logs`.

## Exit criteria

- [x] Probe builds as `net10.0` / `AnyCPU` with zero warnings and zero errors.
- [x] Probe builds again with `--no-restore` (offline repeatability).
- [x] The Python test suite passed in the recorded validation environment.
- [ ] Probe is added to a chart in ATAS X and visibly renders the green
  histogram and `OFK ATAS X probe — loaded` label.

Phase 1 is complete after the final manual load check. Only after that gate
should the GEX indicator be split into portable core logic and an ATAS X
adapter.

## Known scope boundary

This probe does not attempt to make the existing GEX indicator compatible. The
existing indicator still contains Windows-only WPF dashboard/replay code and
must remain untouched until the Phase 3/4 refactor.

The original `OFK_ATAS` project was also checked against the installed ATAS X
assemblies. Its normal configuration is Windows-only (`net10.0-windows`, WPF,
`x64`, and a `C:\Program Files...` hint path). With those settings it cannot
build on macOS. Redirecting the references to the ATAS X bundle and enabling a
diagnostic build gets as far as compilation, but stops on 14 color-type errors
(`System.Windows.Media.Color` versus the ATAS X drawing color type). This is
expected evidence for the later adapter refactor, not a Phase 1 probe failure.
