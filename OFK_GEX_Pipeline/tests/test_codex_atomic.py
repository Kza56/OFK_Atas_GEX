"""Atomic publication and local-schema tests for the Codex adapter."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import codex_briefing as provider


def _briefing(**overrides: object) -> dict:
    value = {
        "date": "2026-08-24",
        "trade_date": "20260824",
        "generation_time": "09:00 ET",
        "spot_nq": 21000,
        "spot_es": None,
        "regime": {
            "gex_label": "positive",
            "total_gex_B": 2.0,
            "total_vex_B": 1.0,
            "ivx_intraday_pct": 16.0,
            "ivr_intraday_pct": None,
            "ivr_status": "insufficient",
            "skew_25d_intraday_vp": 2.0,
            "term_intraday_regime": "contango",
            "term_intraday_slope_vp": -0.5,
            "gamma_zone": "positive",
            "vol_implication": "Test volatility context.",
        },
        "bias": {
            "direction": "neutral",
            "conviction": "low",
            "reason": "Test bias context.",
        },
        "levels": [],
        "rth_plan": {
            "buy_zone": 20900,
            "sell_zone": 21100,
            "bullish_invalidation": 21200,
            "bearish_invalidation": 20800,
            "logic": "Test positive gamma zone plan.",
        },
        "risk_alerts": [],
        "meta_context": {
            "vix": 16.0,
            "vix_regime": "normal",
            "vix_term": "contango",
            "vix_dod_change": -0.2,
            "macro_in_blackout": False,
            "macro_next_event": None,
            "macro_minutes_to_next": -1,
            "data_quality": "ok",
            "interpretation": "Test market context.",
        },
        "one_line_summary": "test briefing",
    }
    value.update(overrides)
    return value


def _source(tmp_path: Path, symbol: str = "NQ") -> Path:
    path = tmp_path / f"full_levels_{symbol}.json"
    path.write_text(
        json.dumps(
            {
                "trade_date": "20260824",
                f"spot_{symbol.lower()}": 21000 if symbol == "NQ" else 5500,
                "total_gex": 2_000_000_000,
            }
        ),
        encoding="utf-8",
    )
    return path


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runner,
    **overrides: object,
) -> dict:
    monkeypatch.setattr(provider.shutil, "which", lambda _executable: "/opt/codex")
    arguments = {
        "full_json": _source(tmp_path),
        "briefing_json": tmp_path / "briefing_NQ.json",
        "raw_file": tmp_path / "briefing_NQ.raw.json",
        "prompt_file": tmp_path / "prompt_NQ.txt",
        "schema_file": provider.SCHEMA_FILE,
        "codex_command": "codex",
        "runner": runner,
        "archive_briefing": False,
    }
    arguments.update(overrides)
    return provider.run_symbol_briefing("NQ", **arguments)


def _temporary_artifacts(tmp_path: Path) -> list[Path]:
    return sorted(
        path
        for path in tmp_path.iterdir()
        if path.name.startswith(".") and path.suffix == ".tmp"
    )


def test_codex_uses_unique_adjacent_temps_and_atomic_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output_paths: list[Path] = []
    replacements: list[tuple[Path, Path]] = []
    fsync_calls: list[int] = []
    real_replace = provider.os.replace
    real_fsync = provider.os.fsync

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--output-last-message") + 1])
        output_paths.append(output)
        assert output.parent == tmp_path
        assert output not in {
            tmp_path / "briefing_NQ.json",
            tmp_path / "briefing_NQ.raw.json",
        }
        output.write_text(json.dumps(_briefing()), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def recording_replace(source, destination):
        replacements.append((Path(source), Path(destination)))
        return real_replace(source, destination)

    def recording_fsync(descriptor):
        fsync_calls.append(descriptor)
        return real_fsync(descriptor)

    monkeypatch.setattr(provider.os, "replace", recording_replace)
    monkeypatch.setattr(provider.os, "fsync", recording_fsync)

    first = _run(tmp_path, monkeypatch, fake_run)
    second = _run(tmp_path, monkeypatch, fake_run)

    assert first["_provider"]["status"] == "codex"
    assert second["_provider"]["status"] == "codex"
    assert len(output_paths) == 2
    assert output_paths[0] != output_paths[1]
    assert all(not output.exists() for output in output_paths)
    assert {destination for _, destination in replacements} >= {
        tmp_path / "briefing_NQ.json",
        tmp_path / "briefing_NQ.raw.json",
    }
    assert all(source.parent == destination.parent for source, destination in replacements)
    assert fsync_calls
    assert not (tmp_path / "prompt_NQ.txt").exists()
    assert _temporary_artifacts(tmp_path) == []


def test_schema_failure_preserves_previous_valid_briefing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    previous = _briefing(one_line_summary="last known good")
    briefing_path = tmp_path / "briefing_NQ.json"
    briefing_path.write_text(json.dumps(previous), encoding="utf-8")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--output-last-message") + 1])
        # The hand-written shape checks accept this list, while the local JSON
        # Schema correctly rejects its non-string item.
        output.write_text(json.dumps(_briefing(risk_alerts=[7])), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = _run(
        tmp_path,
        monkeypatch,
        fake_run,
        briefing_json=briefing_path,
    )

    assert result["_provider"]["status"] == "fallback"
    assert "schema validation" in result["_provider"]["error"]
    assert json.loads(briefing_path.read_text(encoding="utf-8")) == previous
    raw = json.loads((tmp_path / "briefing_NQ.raw.json").read_text(encoding="utf-8"))
    assert raw["status"] == "fallback"
    assert raw["briefing"]["_raw_full_levels"]["spot_nq"] == 21000
    assert _temporary_artifacts(tmp_path) == []


def test_failure_atomically_publishes_fallback_when_no_previous_briefing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(provider.shutil, "which", lambda _executable: None)

    result = provider.run_symbol_briefing(
        "ES",
        full_json=_source(tmp_path, "ES"),
        briefing_json=tmp_path / "briefing_ES.json",
        raw_file=tmp_path / "briefing_ES.raw.json",
        prompt_file=tmp_path / "prompt_ES.txt",
        schema_file=provider.SCHEMA_FILE,
        codex_command="codex",
        archive_briefing=False,
    )

    persisted = json.loads((tmp_path / "briefing_ES.json").read_text(encoding="utf-8"))
    assert result["_provider"]["status"] == "fallback"
    assert persisted == result
    assert persisted["_raw_full_levels"]["spot_es"] == 5500
    assert not (tmp_path / "prompt_ES.txt").exists()
    assert _temporary_artifacts(tmp_path) == []


def test_fail_fast_preserves_artifacts_and_cleans_temporary_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    briefing_path = tmp_path / "briefing_NQ.json"
    raw_path = tmp_path / "briefing_NQ.raw.json"
    previous = _briefing(one_line_summary="keep me")
    briefing_path.write_text(json.dumps(previous), encoding="utf-8")
    raw_path.write_text(json.dumps({"previous": True}), encoding="utf-8")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text("not json", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with pytest.raises(provider.BriefingUnavailable, match="invalid JSON"):
        _run(
            tmp_path,
            monkeypatch,
            fake_run,
            briefing_json=briefing_path,
            raw_file=raw_path,
            allow_fallback=False,
        )

    assert json.loads(briefing_path.read_text(encoding="utf-8")) == previous
    assert json.loads(raw_path.read_text(encoding="utf-8")) == {"previous": True}
    assert not (tmp_path / "prompt_NQ.txt").exists()
    assert _temporary_artifacts(tmp_path) == []


def test_atomic_writer_keeps_destination_if_serialization_fails(tmp_path: Path):
    destination = tmp_path / "briefing.json"
    destination.write_text('{"previous": true}\n', encoding="utf-8")

    with pytest.raises(TypeError):
        provider._write_json(destination, {"invalid": object()})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"previous": True}
    assert _temporary_artifacts(tmp_path) == []
