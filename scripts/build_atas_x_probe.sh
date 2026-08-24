#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
probe_project="$repo_root/OFK_ATAS_X_Probe/OFK_Atas_X_Probe.csproj"
atas_x_path="${ATAS_X_PATH:-/Applications/ATAS X.app/Contents/MonoBundle}"

for assembly in ATAS.Indicators.dll ATAS.Types.dll ATAS.DataFeedsCore.dll OFT.Core.dll OFT.Rendering.dll OFT.Attributes.dll; do
  if [[ ! -f "$atas_x_path/$assembly" ]]; then
    echo "Missing ATAS X assembly: $atas_x_path/$assembly" >&2
    echo "Set ATAS_X_PATH to the ATAS X Contents/MonoBundle directory." >&2
    exit 1
  fi
done

dotnet build "$probe_project" \
  --configuration Release \
  --nologo \
  -p:PlatformTarget=AnyCPU \
  -p:ATASXPath="$atas_x_path"

echo
echo "Probe DLL: $repo_root/OFK_ATAS_X_Probe/bin/Release/net10.0/OFK_Atas_X_Probe.dll"
