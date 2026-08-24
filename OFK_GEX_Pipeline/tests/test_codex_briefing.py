"""Focused tests for the portable Codex briefing provider."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import codex_briefing as provider


def _briefing() -> dict:
    return {
        "date": "2026-08-24",
        "regime": {"gex_label": "positive"},
        "bias": {"direction": "neutral"},
        "levels": [],
        "rth_plan": {},
        "risk_alerts": [],
        "meta_context": {},
        "one_line_summary": "test",
    }


def test_build_codex_command_is_shell_free(tmp_path: Path):
    command = provider.build_codex_command(
        "codex",
        schema_file=tmp_path / "briefing.schema.json",
        output_file=tmp_path / "raw.txt",
    )

    assert command == [
        "codex", "exec", "--sandbox", "read-only", "--output-schema",
        str(tmp_path / "briefing.schema.json"), "--output-last-message",
        str(tmp_path / "raw.txt"), "-",
    ]
    assert "shell" not in command


def test_parse_briefing_json_accepts_markdown_fence():
    result = provider.parse_briefing_json("```json\n" + json.dumps(_briefing()) + "\n```")
    assert result["bias"]["direction"] == "neutral"


def test_parse_briefing_json_rejects_missing_required_key():
    value = _briefing()
    del value["rth_plan"]
    with pytest.raises(provider.BriefingUnavailable, match="rth_plan"):
        provider.parse_briefing_json(json.dumps(value))


def test_run_symbol_briefing_uses_codex_output_and_persists(tmp_path: Path, monkeypatch):
    source_path = tmp_path / "full_levels_NQ.json"
    source_path.write_text(json.dumps({"trade_date": "20260824", "spot_nq": 21000}), encoding="utf-8")
    briefing_path = tmp_path / "briefing_NQ.json"
    raw_path = tmp_path / "raw.txt"
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("{}", encoding="utf-8")
    captured = {}

    monkeypatch.setattr(provider.shutil, "which", lambda executable: "/usr/local/bin/codex")

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(_briefing()), encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = provider.run_symbol_briefing(
        "NQ",
        full_json=source_path,
        briefing_json=briefing_path,
        raw_file=raw_path,
        schema_file=schema_path,
        codex_command="codex",
        runner=fake_run,
    )

    assert result["_provider"]["status"] == "codex"
    assert json.loads(briefing_path.read_text())["one_line_summary"] == "test"
    assert captured["command"][1:5] == ["exec", "--sandbox", "read-only", "--output-schema"]
    assert captured["kwargs"]["input"].startswith("Read ")
    assert "shell" not in captured["kwargs"]


def test_run_symbol_briefing_falls_back_when_codex_missing(tmp_path: Path, monkeypatch):
    source = {"trade_date": "20260824", "spot_nq": 21000, "total_gex": 2_000_000_000, "gamma_flip": 20900}
    source_path = tmp_path / "full_levels_NQ.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    monkeypatch.setattr(provider.shutil, "which", lambda executable: None)

    result = provider.run_symbol_briefing(
        "NQ",
        full_json=source_path,
        briefing_json=tmp_path / "briefing.json",
        raw_file=tmp_path / "raw.txt",
        schema_file=tmp_path / "schema.json",
        codex_command="codex",
    )

    assert result["_provider"]["status"] == "fallback"
    assert result["_raw_full_levels"] == source
    assert result["bias"]["direction"] == "neutral"
    raw = json.loads((tmp_path / "raw.txt").read_text())
    assert raw["status"] == "fallback"


def test_fallback_interprets_textual_negative_regime(tmp_path: Path, monkeypatch):
    source = {
        "trade_date": "20260824",
        "spot_nq": 21000,
        "total_gex": 2_000_000_000,
        "gex_regime": "negative_gamma",
    }
    source_path = tmp_path / "full_levels_NQ.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    monkeypatch.setattr(provider.shutil, "which", lambda executable: None)

    result = provider.run_symbol_briefing(
        "NQ",
        full_json=source_path,
        briefing_json=tmp_path / "briefing.json",
        raw_file=tmp_path / "raw.txt",
        schema_file=tmp_path / "schema.json",
        codex_command="codex",
    )

    assert result["regime"]["gex_label"] == "negative"


def test_run_symbol_briefing_falls_back_on_timeout(tmp_path: Path, monkeypatch):
    source_path = tmp_path / "full_levels_ES.json"
    source_path.write_text(json.dumps({"trade_date": "20260824", "spot_es": 5000}), encoding="utf-8")
    monkeypatch.setattr(provider.shutil, "which", lambda executable: "/usr/local/bin/codex")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(kwargs.get("timeout", 1), args[0])

    result = provider.run_symbol_briefing(
        "ES",
        full_json=source_path,
        briefing_json=tmp_path / "briefing.json",
        raw_file=tmp_path / "raw.txt",
        schema_file=tmp_path / "schema.json",
        codex_command="codex",
        timeout_seconds=2,
        runner=timeout,
    )

    assert result["_provider"]["status"] == "fallback"
    assert "timed out" in result["_provider"]["error"]
