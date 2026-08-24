"""Codex-backed AI briefing provider for the OFK GEX pipeline.

This module is deliberately independent of the morning-runner scripts so the
provider can be introduced without changing the data-fetching stages.  It
invokes ``codex exec`` with an argument list (never through a shell), limits
the agent to the read-only sandbox, and asks Codex to validate its final
message against ``schemas/briefing.schema.json``.

When Codex is not installed, times out, exits unsuccessfully, or produces an
invalid response, :func:`run_briefing` returns a deterministic fallback
briefing.  The fallback includes the complete source ``full_levels`` object
under ``_raw_full_levels`` so a missing AI tool never discards market data.
Callers that need fail-fast behavior can pass ``allow_fallback=False`` and
handle :class:`BriefingUnavailable`.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import config as pipeline_config
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


SCHEMA_FILE = Path(__file__).with_name("schemas") / "briefing.schema.json"
DEFAULT_TIMEOUT_SECONDS = 180
REQUIRED_KEYS = (
    "date",
    "regime",
    "bias",
    "levels",
    "rth_plan",
    "risk_alerts",
    "meta_context",
    "one_line_summary",
)


class BriefingUnavailable(RuntimeError):
    """Raised when Codex cannot produce a valid briefing."""


def _command_parts(command: str | Path | Sequence[str]) -> list[str]:
    """Return an executable command prefix without invoking a shell."""
    if isinstance(command, (str, Path)):
        parts = shlex.split(str(command))
    else:
        parts = [str(part) for part in command]
    if not parts or not parts[0]:
        raise ValueError("CODEX_CMD must name an executable")
    return parts


def _executable_available(parts: Sequence[str]) -> bool:
    executable = parts[0]
    # ``which`` also handles PATH lookup, while an explicit path may include
    # spaces and must be tested as a path rather than passed as one string.
    if Path(executable).parent != Path("."):
        return Path(executable).is_file() and os.access(executable, os.X_OK)
    return shutil.which(executable) is not None


def build_codex_command(
    codex_command: str | Path | Sequence[str],
    *,
    schema_file: Path,
    output_file: Path,
) -> list[str]:
    """Build the portable, non-interactive Codex command.

    The final ``-`` tells ``codex exec`` to read the prompt from stdin.  The
    output file is populated by Codex's ``--output-last-message`` option.
    """
    return [
        *_command_parts(codex_command),
        "exec",
        "--sandbox",
        "read-only",
        "--output-schema",
        str(schema_file),
        "--output-last-message",
        str(output_file),
        "-",
    ]


def _strip_json_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1] if "\n" in value else ""
    if value.endswith("```"):
        value = value.rsplit("```", 1)[0]
    return value.strip()


def parse_briefing_json(text: str) -> dict[str, Any]:
    """Parse a Codex final message and reject non-briefing JSON."""
    raw = _strip_json_fence(text)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        # Be tolerant of an accidental short preamble while still requiring a
        # single JSON object.  Codex's output-schema normally makes this path
        # unnecessary, but it helps when users run an older CLI build.
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise BriefingUnavailable("Codex returned invalid JSON") from None
        try:
            value = json.loads(raw[start : end + 1])
        except json.JSONDecodeError as exc:
            raise BriefingUnavailable("Codex returned invalid JSON") from exc

    if not isinstance(value, dict):
        raise BriefingUnavailable("Codex briefing must be a JSON object")
    missing = [key for key in REQUIRED_KEYS if key not in value]
    if missing:
        raise BriefingUnavailable(
            "Codex briefing is missing required keys: " + ", ".join(missing)
        )
    if not isinstance(value["regime"], dict) or not isinstance(value["bias"], dict):
        raise BriefingUnavailable("Codex briefing regime and bias must be objects")
    if not isinstance(value["levels"], list) or not isinstance(value["risk_alerts"], list):
        raise BriefingUnavailable("Codex briefing levels and risk_alerts must be arrays")
    if not isinstance(value["rth_plan"], dict) or not isinstance(value["meta_context"], dict):
        raise BriefingUnavailable("Codex briefing rth_plan and meta_context must be objects")
    if not isinstance(value["one_line_summary"], str):
        raise BriefingUnavailable("Codex briefing one_line_summary must be text")
    return value


def _schema_validator(schema_file: Path) -> Draft202012Validator:
    """Load and check the local Draft 2020-12 briefing schema."""
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BriefingUnavailable(f"Briefing schema was not found: {schema_file}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise BriefingUnavailable(f"Briefing schema is unreadable: {schema_file}") from exc
    if not isinstance(schema, dict):
        raise BriefingUnavailable("Briefing schema must be a JSON object")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise BriefingUnavailable(f"Briefing schema is invalid: {exc.message}") from exc
    return Draft202012Validator(schema)


def _validate_briefing(
    briefing: Mapping[str, Any],
    validator: Draft202012Validator,
    *,
    source: str,
) -> None:
    """Reject a briefing that does not satisfy the checked local schema."""
    errors = sorted(
        validator.iter_errors(dict(briefing)),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if not errors:
        return
    error = errors[0]
    location = ".".join(str(part) for part in error.absolute_path) or "<root>"
    raise BriefingUnavailable(
        f"{source} failed briefing schema validation at {location}: {error.message}"
    )


def _read_source(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BriefingUnavailable(f"Source JSON is invalid: {path}") from exc
    if not isinstance(value, dict):
        raise BriefingUnavailable(f"Source JSON must be an object: {path}")
    return value


def _trade_date(source: Mapping[str, Any]) -> str:
    value = str(source.get("trade_date") or source.get("date") or "")
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value or date.today().isoformat()


def _number(source: Mapping[str, Any], *keys: str) -> float | int | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


def _fallback_briefing(symbol: str, source: Mapping[str, Any], error: str) -> dict[str, Any]:
    """Create a data-preserving briefing when no AI provider is available."""
    lower = symbol.lower()
    spot = _number(source, f"spot_{lower}", "spot", f"spot_{symbol}")
    gex = _number(source, "total_gex")
    vex = _number(source, "total_vex")
    gex_regime = source.get("gex_regime")
    if isinstance(gex_regime, str):
        regime_text = gex_regime.strip().lower()
        if regime_text in {"-1"} or any(
            word in regime_text for word in ("negative", "neg", "bear")
        ):
            gex_regime = -1
        elif regime_text in {"+1", "1"} or any(
            word in regime_text for word in ("positive", "pos", "bull")
        ):
            gex_regime = 1
        else:
            gex_regime = 1 if (gex or 0) >= 0 else -1
    elif not isinstance(gex_regime, (int, float)):
        gex_regime = 1 if (gex or 0) >= 0 else -1
    label = "positive" if gex_regime >= 0 else "negative"

    level_names = (
        "gamma_flip", "vol_trigger", "call_wall", "put_wall", "risk_pivot",
        "vanna_flip", "charm_magnet", "max_pain", "max_pain_0dte",
        "pin_strike_0dte", "c_trans_intraday", "p_trans_intraday",
    )
    levels: list[dict[str, Any]] = []
    for name in level_names:
        value = source.get(name)
        if value is None:
            value = source.get(f"{name}_{lower}")
        if isinstance(value, (int, float)):
            levels.append({
                "type": name,
                f"approx_price_{lower}": value,
                "dealer_behavior": "AI briefing unavailable; inspect raw GEX data.",
            })

    low = _number(source, f"range_bas_{lower}", "range_low", "expected_move_low")
    high = _number(source, f"range_haut_{lower}", "range_high", "expected_move_high")
    if low is None:
        low = _number(source, "put_wall", "gamma_flip", f"spot_{lower}")
    if high is None:
        high = _number(source, "call_wall", "gamma_flip", f"spot_{lower}")
    meta = source.get("_meta") or source.get("meta_context")
    if not isinstance(meta, dict):
        # The current merger stores these fields at the full-levels root;
        # accept that format as well as the nested format used by briefings.
        meta = {
            "vix": source.get("vix"),
            "vix_regime": source.get("vix_regime"),
            "vix_term": source.get("vix_term"),
            "vix_dod_change": source.get("vix_dod_change"),
            "macro_in_blackout": source.get("macro_in_blackout"),
            "macro_next_event": source.get("macro_next_event"),
            "macro_minutes_to_next": source.get("macro_minutes_to_next"),
            "data_quality": source.get("data_quality"),
        }
    meta = {
        "vix": meta.get("vix"),
        "vix_regime": meta.get("vix_regime", "unknown"),
        "vix_term": meta.get("vix_term", "unknown"),
        "vix_dod_change": meta.get("vix_dod_change"),
        "macro_in_blackout": bool(meta.get("macro_in_blackout", False)),
        "macro_next_event": meta.get("macro_next_event"),
        "macro_minutes_to_next": meta.get("macro_minutes_to_next", -1),
        "data_quality": meta.get("data_quality", "partial"),
        "interpretation": "AI briefing unavailable; use the raw source levels directly.",
    }
    return {
        "date": _trade_date(source),
        "trade_date": source.get("trade_date"),
        f"spot_{lower}": spot,
        "regime": {
            "gex_label": label,
            "total_gex_B": (gex / 1e9) if gex is not None else None,
            "total_vex_B": (vex / 1e9) if vex is not None else None,
            "gamma_zone": "unknown",
            "vol_implication": "AI briefing unavailable; inspect raw GEX and volatility data.",
        },
        "bias": {
            "direction": "neutral",
            "conviction": "low",
            "reason": "No Codex briefing was available; no directional bias inferred.",
        },
        "levels": levels,
        "rth_plan": {
            "buy_zone": low,
            "sell_zone": high,
            "bullish_invalidation": _number(
                source, "put_wall", f"put_wall_{lower}", "gamma_flip", f"gamma_flip_{lower}"
            ),
            "bearish_invalidation": _number(
                source, "call_wall", f"call_wall_{lower}", "gamma_flip", f"gamma_flip_{lower}"
            ),
            "logic": "Fallback only. Review the raw GEX levels before trading.",
        },
        "risk_alerts": [
            "AI briefing unavailable; this is a raw-data fallback, not a trade recommendation."
        ],
        "meta_context": meta,
        "one_line_summary": "AI briefing unavailable — review raw GEX levels before trading.",
        "_provider": {"name": "codex", "status": "fallback", "error": error},
        "_raw_full_levels": dict(source),
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Durably publish JSON with a same-directory atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.publish-",
            suffix=".tmp",
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _temporary_codex_output(raw_file: Path) -> Path:
    """Reserve a unique output-last-message path next to the raw artifact."""
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(raw_file.parent),
        prefix=f".{raw_file.name}.codex-",
        suffix=".tmp",
    )
    os.close(descriptor)
    return Path(temporary_name)


def _published_briefing_is_valid(
    path: Path,
    validator: Draft202012Validator,
) -> bool:
    """Return whether ``path`` contains a previously valid briefing."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return False
        parse_briefing_json(json.dumps(value))
        _validate_briefing(value, validator, source="Published briefing")
    except (OSError, json.JSONDecodeError, BriefingUnavailable):
        return False
    return True


def _archive_briefing(symbol: str, briefing: Mapping[str, Any]) -> None:
    try:
        history_dir = pipeline_config.HISTORY_DIR / "briefings"
        trade_date = str(briefing.get("trade_date") or "").replace("-", "")
        if trade_date and len(trade_date) == 8:
            history_dir.mkdir(parents=True, exist_ok=True)
            _write_json(history_dir / f"{symbol}_briefing_{trade_date}.json", briefing)
    except Exception:
        # Archiving is best effort and must never prevent the current briefing.
        pass


def _print_summary(symbol: str, briefing: Mapping[str, Any], output: Path) -> None:
    regime = briefing.get("regime") or {}
    bias = briefing.get("bias") or {}
    print(f"  {symbol} briefing: {(regime.get('gex_label') or '?').upper()} GEX / "
          f"{(bias.get('direction') or '?').upper()} bias")
    print(f"  Briefing -> {output}")


def _run_codex(
    *,
    command: list[str],
    prompt: str,
    cwd: Path,
    timeout: float,
    runner: Callable[..., Any],
) -> str:
    try:
        result = runner(
            command,
            input=prompt,
            capture_output=True,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise BriefingUnavailable("Codex executable was not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise BriefingUnavailable(f"Codex briefing timed out after {timeout:g}s") from exc
    except OSError as exc:
        raise BriefingUnavailable(f"Could not start Codex: {exc}") from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise BriefingUnavailable(
            f"Codex exited with status {result.returncode}"
            + (f": {details[-500:]}" if details else "")
        )
    return result.stdout or ""


def run_symbol_briefing(
    symbol: str,
    *,
    full_json: Path,
    briefing_json: Path,
    raw_file: Path,
    prompt_file: Path | None = None,
    codex_command: str | Path | Sequence[str] | None = None,
    timeout_seconds: float | None = None,
    schema_file: Path = SCHEMA_FILE,
    runner: Callable[..., Any] = subprocess.run,
    allow_fallback: bool = True,
    archive_briefing: bool = True,
) -> dict[str, Any]:
    """Generate and persist one symbol's briefing.

    ``allow_fallback`` defaults to ``True`` for unattended morning runs.  The
    source JSON remains available in the returned object and in the persisted
    fallback briefing under ``_raw_full_levels``.
    """
    symbol = symbol.upper()
    if symbol not in {"NQ", "ES"}:
        raise ValueError(f"Unsupported symbol: {symbol}")
    source = _read_source(full_json)
    command_setting = codex_command
    if command_setting is None:
        command_setting = getattr(
            pipeline_config, "CODEX_CMD", os.environ.get("CODEX_CMD", "codex")
        )
    timeout = timeout_seconds
    if timeout is None:
        timeout = float(getattr(
            pipeline_config,
            "CODEX_TIMEOUT_SECONDS",
            os.environ.get("CODEX_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        ))
    prompt = (
        f"Read {full_json.resolve()} and apply the analysis specification in "
        f"{(pipeline_config.SKILLS_DIR / f'gex_analyst_{symbol}.md').resolve()}. "
        "Return only the briefing JSON, with no markdown or explanation. "
        "Do not modify any files."
    )
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    codex_output: Path | None = None
    validator: Draft202012Validator | None = None
    published = False
    briefing: dict[str, Any]
    try:
        if prompt_file is not None:
            prompt_file.parent.mkdir(parents=True, exist_ok=True)
            prompt_file.write_text(prompt, encoding="utf-8")
        try:
            validator = _schema_validator(schema_file)
            parts = _command_parts(command_setting)
            if not _executable_available(parts):
                raise BriefingUnavailable(f"Codex executable is unavailable: {parts[0]}")

            # Codex never receives either stable artifact path. Its final
            # message is isolated until parsing and local validation succeed.
            codex_output = _temporary_codex_output(raw_file)
            command = build_codex_command(
                parts,
                schema_file=schema_file,
                output_file=codex_output,
            )
            stdout = _run_codex(
                command=command,
                prompt=prompt,
                cwd=pipeline_config.PIPELINE_ROOT,
                timeout=timeout,
                runner=runner,
            )
            file_output = codex_output.read_text(encoding="utf-8")
            output = file_output if file_output.strip() else stdout
            briefing = parse_briefing_json(output)
            _validate_briefing(briefing, validator, source="Codex briefing")
            briefing["_provider"] = {"name": "codex", "status": "codex"}
            _write_json(raw_file, briefing)
            _write_json(briefing_json, briefing)
            published = True
        except (BriefingUnavailable, ValueError) as exc:
            error = str(exc)
            if not allow_fallback:
                raise BriefingUnavailable(error) from exc
            briefing = _fallback_briefing(symbol, source, error)
            _write_json(
                raw_file,
                {"status": "fallback", "error": error, "briefing": briefing},
            )

            # A provider failure must not overwrite the last known-good
            # briefing. With no valid prior artifact, publish the validated
            # data-preserving fallback so unattended first runs remain usable.
            if validator is not None:
                _validate_briefing(briefing, validator, source="Fallback briefing")
                if not _published_briefing_is_valid(briefing_json, validator):
                    _write_json(briefing_json, briefing)
                    published = True
    finally:
        if codex_output is not None:
            codex_output.unlink(missing_ok=True)
        if prompt_file is not None:
            prompt_file.unlink(missing_ok=True)

    if archive_briefing and published:
        _archive_briefing(symbol, briefing)
    _print_summary(symbol, briefing, briefing_json)
    return briefing


def run_briefing(symbol: str) -> dict[str, Any]:
    """Stable public entry point using paths from :mod:`config`."""
    symbol = symbol.upper()
    if symbol == "NQ":
        return run_symbol_briefing(
            symbol,
            full_json=pipeline_config.NQ_FULL_JSON,
            briefing_json=pipeline_config.NQ_BRIEFING_JSON,
            raw_file=pipeline_config.NQ_BRIEFING_RAW,
            prompt_file=getattr(pipeline_config, "NQ_PROMPT_FILE", None),
        )
    if symbol == "ES":
        return run_symbol_briefing(
            symbol,
            full_json=pipeline_config.ES_FULL_JSON,
            briefing_json=pipeline_config.ES_BRIEFING_JSON,
            raw_file=pipeline_config.ES_BRIEFING_RAW,
            prompt_file=getattr(pipeline_config, "ES_PROMPT_FILE", None),
        )
    raise ValueError(f"Unsupported symbol: {symbol}")


def run_briefing_NQ() -> dict[str, Any]:
    return run_briefing("NQ")


def run_briefing_ES() -> dict[str, Any]:
    return run_briefing("ES")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate an OFK GEX Codex briefing")
    parser.add_argument("symbol", choices=("NQ", "ES"), nargs="?", default="NQ")
    args = parser.parse_args()
    run_briefing(args.symbol)
