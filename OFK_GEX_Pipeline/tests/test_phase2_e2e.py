"""Isolated Phase 2 fixture validation and PDF smoke tests."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


PIPELINE_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = PIPELINE_ROOT / "data" / "samples"
SCHEMA_FILE = PIPELINE_ROOT / "schemas" / "briefing.schema.json"


@pytest.mark.parametrize("symbol", ["NQ", "ES"])
def test_committed_symbol_samples_are_complete_and_schema_valid(symbol: str):
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    briefing = json.loads(
        (SAMPLES_DIR / f"briefing_{symbol}.json").read_text(encoding="utf-8")
    )
    full_levels = json.loads(
        (SAMPLES_DIR / f"full_levels_{symbol}.json").read_text(encoding="utf-8")
    )

    validator.validate(briefing)
    assert full_levels["trade_date"]
    assert isinstance(full_levels[f"spot_{symbol.lower()}"], (int, float))
    assert isinstance(full_levels["total_gex"], (int, float))


@pytest.mark.parametrize(
    ("symbol", "module_name", "builder_name"),
    [
        ("NQ", "generate_pdf_NQ", "build_pdf"),
        ("ES", "generate_pdf_ES", "build_pdf_ES"),
    ],
)
def test_pdf_generation_smoke_is_isolated(
    symbol: str,
    module_name: str,
    builder_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    pytest.importorskip("reportlab")
    module = importlib.import_module(module_name)
    output_dir = tmp_path / symbol
    output_dir.mkdir()
    monkeypatch.setattr(module, "OUTPUT_DIR", output_dir)
    briefing = json.loads(
        (SAMPLES_DIR / f"briefing_{symbol}.json").read_text(encoding="utf-8")
    )

    output = getattr(module, builder_name)(briefing)

    assert output.parent == output_dir
    assert output.stat().st_size > 1_000
    assert output.read_bytes().startswith(b"%PDF-")
