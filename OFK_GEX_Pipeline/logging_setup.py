"""
logging_setup.py — Rotated file logging for the GEX pipeline.

Console (stderr) + rotated file `data/logs/pipeline.log`:
- 10 MB max per file
- 5 backups kept (pipeline.log.1 to .5)
- Detailed format (timestamp, level, module, message)

Usage:
  from logging_setup import setup_logging
  setup_logging()  # once at the start of the script
  log = logging.getLogger(__name__)
  log.info("...")

Env overrides:
  GEX_LOG_LEVEL : DEBUG|INFO|WARNING|ERROR (default INFO)
  GEX_LOG_FILE  : override path for pipeline.log
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_INITIALIZED = False


def setup_logging(level: str | None = None, log_file: Path | None = None) -> None:
    """Configure root logger: console + RotatingFileHandler. Idempotent."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    level_str = (level or os.environ.get("GEX_LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_str, logging.INFO)

    # Default path: DATA_DIR/logs/pipeline.log
    if log_file is None:
        log_env = os.environ.get("GEX_LOG_FILE")
        if log_env:
            log_file = Path(log_env)
        else:
            from config import DATA_DIR
            log_file = DATA_DIR / "logs" / "pipeline.log"

    log_file.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(log_level)
    # Avoid duplicates if setup_logging is called multiple times
    for h in list(root.handlers):
        root.removeHandler(h)

    # Console (stderr)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(ch)

    # Rotated file: 10 MB, 5 backups
    fh = RotatingFileHandler(
        str(log_file),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(log_level)
    fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(fh)

    _INITIALIZED = True
    logging.getLogger(__name__).info(
        f"logging initialized (level={level_str}, file={log_file})"
    )
