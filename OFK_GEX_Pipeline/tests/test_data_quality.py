"""Tests compute_data_quality() — Bloc 7."""
from config import compute_data_quality, JSON_SCHEMA_VERSION


def test_schema_version_is_string():
    assert isinstance(JSON_SCHEMA_VERSION, str)
    assert "." in JSON_SCHEMA_VERSION


def test_quality_error_on_empty():
    assert compute_data_quality({}) == "error"
    assert compute_data_quality(None) == "error"


def test_quality_error_when_no_source():
    assert compute_data_quality({"some_other_field": 42}) == "error"


def test_quality_partial_when_only_cme():
    assert compute_data_quality({"total_gex": 1e9}) == "partial"


def test_quality_partial_when_only_cboe():
    assert compute_data_quality({"atm_iv_intraday": 0.18}) == "partial"


def test_quality_partial_when_cme_cboe_no_vix():
    assert compute_data_quality({
        "total_gex": 1e9,
        "atm_iv_intraday": 0.18,
    }) == "partial"


def test_quality_ok_when_all_three_sources():
    assert compute_data_quality({
        "total_gex": 1e9,
        "atm_iv_intraday": 0.18,
        "vix": 14.5,
    }) == "ok"


def test_quality_ignores_zero_values():
    # vix=0 → considéré comme absent
    assert compute_data_quality({
        "total_gex": 1e9,
        "atm_iv_intraday": 0.18,
        "vix": 0,
    }) == "partial"
