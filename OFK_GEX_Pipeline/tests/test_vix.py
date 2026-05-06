"""Tests for VIX classification — Block 1."""
from vix_fetcher import _classify_regime, _classify_term


def test_regime_low():
    assert _classify_regime(10) == "low"
    assert _classify_regime(13.99) == "low"


def test_regime_normal():
    assert _classify_regime(14) == "normal"
    assert _classify_regime(17) == "normal"
    assert _classify_regime(19.99) == "normal"


def test_regime_elevated():
    assert _classify_regime(20) == "elevated"
    assert _classify_regime(25) == "elevated"
    assert _classify_regime(27.99) == "elevated"


def test_regime_extreme():
    assert _classify_regime(28) == "extreme"
    assert _classify_regime(50) == "extreme"


def test_regime_unknown_invalid():
    assert _classify_regime(0) == "unknown"
    assert _classify_regime(-1) == "unknown"


def test_term_backwardation_when_vix9d_above():
    # VIX9D > VIX + 0.5 -> backwardation (short-term stress)
    assert _classify_term(vix=15, vix9d=16) == "backwardation"
    assert _classify_term(vix=20, vix9d=22) == "backwardation"


def test_term_contango_when_vix9d_below():
    assert _classify_term(vix=15, vix9d=13) == "contango"


def test_term_flat_when_close():
    assert _classify_term(vix=15, vix9d=15) == "flat"
    assert _classify_term(vix=15, vix9d=15.3) == "flat"   # < 0.5 diff
    assert _classify_term(vix=15, vix9d=14.8) == "flat"   # < 0.5 diff


def test_term_unknown_invalid():
    assert _classify_term(vix=0, vix9d=15) == "unknown"
    assert _classify_term(vix=15, vix9d=0) == "unknown"
