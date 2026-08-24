"""Focused tests for the portable Codex briefing provider."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

import codex_briefing as provider


def _briefing(symbol: str = "NQ") -> dict[str, Any]:
    lower = symbol.lower()
    return {
        "date": "2026-08-24",
        "trade_date": "20260824",
        f"spot_{lower}": 21000 if symbol == "NQ" else 5700,
        "regime": {"gex_label": "positive"},
        "bias": {"direction": "neutral"},
        "levels": [],
        "rth_plan": {},
        "risk_alerts": [],
        "meta_context": {},
        "one_line_summary": f"{symbol} test briefing",
    }


def _source(symbol: str) -> dict[str, Any]:
    lower = symbol.lower()
    return {
        "trade_date": "20260824",
        f"spot_{lower}": 21000 if symbol == "NQ" else 5700,
        "total_gex": 2_000_000_000,
        "gamma_flip": 20900 if symbol == "NQ" else 5675,
    }


def _output_runner(
    payload: str | dict[str, Any],
    *,
    returncode: int = 0,
    stderr: str = "",
    captured: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload)

    def fake_run(command, **kwargs):
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(text, encoding="utf-8")
        if captured is not None:
            captured.update(command=command, kwargs=kwargs, output=output)
        return SimpleNamespace(returncode=returncode, stdout="", stderr=stderr)

    return fake_run


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    symbol: str = "NQ",
    runner: Callable[..., Any] | None = None,
    codex_command: str | list[str] = "codex",
    allow_fallback: bool = True,
) -> tuple[dict[str, Any], Path, Path]:
    source_path = tmp_path / f"full_levels_{symbol}.json"
    source_path.write_text(json.dumps(_source(symbol)), encoding="utf-8")
    briefing_path = tmp_path / f"briefing_{symbol}.json"
    raw_path = tmp_path / f"raw_{symbol}.json"
    monkeypatch.setattr(provider.pipeline_config, "HISTORY_DIR", tmp_path / "history")
    monkeypatch.setattr(provider.pipeline_config, "PIPELINE_ROOT", tmp_path)
    if runner is not None:
        monkeypatch.setattr(
            provider.shutil, "which", lambda executable: "/usr/local/bin/codex"
        )

    result = provider.run_symbol_briefing(
        symbol,
        full_json=source_path,
        briefing_json=briefing_path,
        raw_file=raw_path,
        prompt_file=tmp_path / f"prompt_{symbol}.txt",
        schema_file=provider.SCHEMA_FILE,
        codex_command=codex_command,
        timeout_seconds=2,
        runner=runner or subprocess.run,
        allow_fallback=allow_fallback,
        archive_briefing=False,
    )
    return result, briefing_path, raw_path


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
    result = provider.parse_briefing_json(
        "```json\n" + json.dumps(_briefing()) + "\n```"
    )
    assert result["bias"]["direction"] == "neutral"


def test_parse_briefing_json_rejects_missing_required_key():
    value = _briefing()
    del value["rth_plan"]
    with pytest.raises(provider.BriefingUnavailable, match="rth_plan"):
        provider.parse_briefing_json(json.dumps(value))


@pytest.mark.parametrize("symbol", ["NQ", "ES"])
def test_run_symbol_briefing_generates_and_publishes_both_symbols(
    symbol: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    captured: dict[str, Any] = {}
    result, briefing_path, raw_path = _run(
        tmp_path,
        monkeypatch,
        symbol=symbol,
        runner=_output_runner(_briefing(symbol), captured=captured),
    )

    assert result["_provider"]["status"] == "codex"
    assert json.loads(briefing_path.read_text(encoding="utf-8"))[
        "one_line_summary"
    ] == f"{symbol} test briefing"
    assert captured["command"][1:5] == [
        "exec", "--sandbox", "read-only", "--output-schema"
    ]
    assert captured["kwargs"]["input"].startswith("Read ")
    assert "shell" not in captured["kwargs"]
    assert captured["output"] != briefing_path
    assert not captured["output"].exists()
    assert not (tmp_path / f"prompt_{symbol}.txt").exists()
    assert raw_path.exists()


def test_malformed_json_through_provider_flow_uses_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    captured: dict[str, Any] = {}
    result, briefing_path, raw_path = _run(
        tmp_path,
        monkeypatch,
        runner=_output_runner("not valid JSON", captured=captured),
    )

    assert result["_provider"]["status"] == "fallback"
    assert "invalid JSON" in result["_provider"]["error"]
    assert json.loads(briefing_path.read_text(encoding="utf-8"))[
        "_provider"
    ]["status"] == "fallback"
    assert json.loads(raw_path.read_text(encoding="utf-8"))["status"] == "fallback"
    assert not captured["output"].exists()


def test_schema_invalid_wrong_field_type_uses_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    invalid = _briefing()
    invalid["risk_alerts"] = [42]

    result, _, _ = _run(
        tmp_path,
        monkeypatch,
        runner=_output_runner(invalid),
    )

    assert result["_provider"]["status"] == "fallback"
    assert result["_raw_full_levels"] == _source("NQ")


def test_nonzero_authentication_failure_uses_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    result, _, _ = _run(
        tmp_path,
        monkeypatch,
        runner=_output_runner(
            "",
            returncode=1,
            stderr="authentication required: run codex login",
        ),
    )

    assert result["_provider"]["status"] == "fallback"
    assert "status 1" in result["_provider"]["error"]
    assert "authentication required" in result["_provider"]["error"]


def test_process_start_network_oserror_uses_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def unavailable(*args, **kwargs):
        raise OSError("network is unavailable")

    result, _, _ = _run(tmp_path, monkeypatch, runner=unavailable)

    assert result["_provider"]["status"] == "fallback"
    assert "Could not start Codex" in result["_provider"]["error"]
    assert "network is unavailable" in result["_provider"]["error"]


def test_timeout_uses_fallback_and_preserves_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    result, _, _ = _run(tmp_path, monkeypatch, symbol="ES", runner=timeout)

    assert result["_provider"]["status"] == "fallback"
    assert "timed out after 2s" in result["_provider"]["error"]
    assert result["_raw_full_levels"] == _source("ES")


def test_missing_executable_uses_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(provider.shutil, "which", lambda executable: None)

    result, _, _ = _run(tmp_path, monkeypatch)

    assert result["_provider"]["status"] == "fallback"
    assert "executable is unavailable" in result["_provider"]["error"]


def test_explicitly_disabled_codex_keeps_market_data_usable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    result, briefing_path, _ = _run(
        tmp_path, monkeypatch, codex_command=[]
    )

    assert result["_provider"]["status"] == "fallback"
    assert result["_raw_full_levels"] == _source("NQ")
    assert briefing_path.exists()


def test_allow_fallback_false_raises_without_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_path = tmp_path / "full_levels_NQ.json"
    source_path.write_text(json.dumps(_source("NQ")), encoding="utf-8")
    briefing_path = tmp_path / "briefing_NQ.json"
    monkeypatch.setattr(provider.shutil, "which", lambda executable: None)
    monkeypatch.setattr(provider.pipeline_config, "HISTORY_DIR", tmp_path / "history")
    monkeypatch.setattr(provider.pipeline_config, "PIPELINE_ROOT", tmp_path)

    with pytest.raises(provider.BriefingUnavailable, match="unavailable"):
        provider.run_symbol_briefing(
            "NQ",
            full_json=source_path,
            briefing_json=briefing_path,
            raw_file=tmp_path / "raw_NQ.json",
            prompt_file=tmp_path / "prompt_NQ.txt",
            schema_file=provider.SCHEMA_FILE,
            codex_command="codex",
            allow_fallback=False,
            archive_briefing=False,
        )

    assert not briefing_path.exists()
    assert not (tmp_path / "prompt_NQ.txt").exists()


def test_provider_failure_preserves_previous_valid_briefing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    previous = _briefing()
    previous["one_line_summary"] = "last known valid briefing"
    briefing_path = tmp_path / "briefing_NQ.json"
    briefing_path.write_text(json.dumps(previous), encoding="utf-8")
    captured: dict[str, Any] = {}

    result, published_path, raw_path = _run(
        tmp_path,
        monkeypatch,
        runner=_output_runner("{malformed", captured=captured),
    )

    assert result["_provider"]["status"] == "fallback"
    assert published_path == briefing_path
    assert json.loads(briefing_path.read_text(encoding="utf-8")) == previous
    assert json.loads(raw_path.read_text(encoding="utf-8"))["status"] == "fallback"
    assert not captured["output"].exists()


def test_fallback_interprets_textual_negative_regime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = _source("NQ")
    source["gex_regime"] = "negative_gamma"
    source_path = tmp_path / "full_levels_NQ.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    monkeypatch.setattr(provider.shutil, "which", lambda executable: None)
    monkeypatch.setattr(provider.pipeline_config, "HISTORY_DIR", tmp_path / "history")
    monkeypatch.setattr(provider.pipeline_config, "PIPELINE_ROOT", tmp_path)

    result = provider.run_symbol_briefing(
        "NQ",
        full_json=source_path,
        briefing_json=tmp_path / "briefing.json",
        raw_file=tmp_path / "raw.txt",
        schema_file=provider.SCHEMA_FILE,
        codex_command="codex",
        archive_briefing=False,
    )

    assert result["regime"]["gex_label"] == "negative"
