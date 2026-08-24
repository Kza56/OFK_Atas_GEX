"""Focused tests for portable configuration environment overrides."""

import importlib

import pytest

import config


def _reload_config(monkeypatch, **values):
    """Reload config with only the requested environment overrides."""
    for name in (
        "CODEX_CMD",
        "CODEX_TIMEOUT_SECONDS",
        "GEX_DATA_DIR",
        "GEX_HISTORY_MAX_DAYS",
        "GEX_INTRADAY_HISTORY_MAX_DAYS",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, str(value))
    return importlib.reload(config)


def test_codex_defaults_are_portable(monkeypatch):
    loaded = _reload_config(monkeypatch)

    assert loaded.CODEX_CMD == "codex"
    assert loaded.CODEX_TIMEOUT_SECONDS == 180
    assert loaded.DATA_DIR == loaded.PIPELINE_ROOT / "data"


def test_codex_and_data_dir_overrides(monkeypatch, tmp_path):
    loaded = _reload_config(
        monkeypatch,
        CODEX_CMD="/opt/codex/bin/codex",
        CODEX_TIMEOUT_SECONDS=45,
        GEX_DATA_DIR=tmp_path,
    )

    assert loaded.CODEX_CMD == "/opt/codex/bin/codex"
    assert loaded.CODEX_TIMEOUT_SECONDS == 45
    assert loaded.DATA_DIR == tmp_path
    assert loaded.NQ_FULL_JSON == tmp_path / "full_levels_NQ.json"


def test_path_overrides_expand_user(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    loaded = _reload_config(monkeypatch, GEX_DATA_DIR="~/ofk-gex-data")

    assert loaded.DATA_DIR == tmp_path / "ofk-gex-data"
    assert loaded.ES_FULL_JSON == tmp_path / "ofk-gex-data" / "full_levels_ES.json"


@pytest.mark.parametrize("value", ["0", "-1", "not-a-number"])
def test_invalid_timeout_is_rejected(monkeypatch, value):
    with pytest.raises(ValueError, match="CODEX_TIMEOUT_SECONDS"):
        _reload_config(monkeypatch, CODEX_TIMEOUT_SECONDS=value)
