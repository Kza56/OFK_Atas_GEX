"""
backup_snapshots.py — Timestamped tarball of the history/ folder into backups/.

Why: IVR (IV Rank) relies on 252 days of history. If data/history/ is
deleted/corrupted, IVR becomes unusable for ~1 year. This script creates a
compressed backup each day.

Retention policy:
- Keep the last N daily backups (default 30)
- Keep 1 backup per month (first of the month) indefinitely if --keep-monthly

CLI usage:
  python3 backup_snapshots.py                    # backup + cleanup with defaults
  python3 backup_snapshots.py --retention 60     # keep 60 days
  python3 backup_snapshots.py --no-monthly       # no monthly archiving
  python3 backup_snapshots.py --dry-run

Programmatic usage:
  from backup_snapshots import make_backup, cleanup_old_backups
  make_backup()
  cleanup_old_backups(retention_days=30, keep_monthly=True)

Integrated automatically in run_morning_NQ/ES.py (1×/day in the morning).
"""
from __future__ import annotations

import argparse
import logging
import re
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from config import HISTORY_DIR, DATA_DIR

BACKUP_DIR: Path = DATA_DIR / "backups"
_NAME_PATTERN = re.compile(r"snapshots_(\d{8})_\d{6}\.tar\.gz")

log = logging.getLogger(__name__)


def make_backup() -> Optional[Path]:
    """Create a timestamped tarball of current snapshots. Returns the path or None."""
    if not HISTORY_DIR.exists() or not any(HISTORY_DIR.iterdir()):
        log.warning(f"history dir empty or missing: {HISTORY_DIR}")
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts  = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = BACKUP_DIR / f"snapshots_{ts}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        tar.add(HISTORY_DIR, arcname="history")
    size_kb = out.stat().st_size / 1024
    log.info(f"backup → {out.name} ({size_kb:.1f} KB)")
    return out


def cleanup_old_backups(retention_days: int = 30,
                         keep_monthly: bool = True) -> int:
    """Remove daily backups older than retention_days.
    If keep_monthly, keep the oldest backup of each month.

    Returns the number of files removed.
    """
    if not BACKUP_DIR.exists():
        return 0
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=retention_days)
    backups = sorted(BACKUP_DIR.glob("snapshots_*.tar.gz"))
    monthly_seen = set()
    deleted = 0
    for bk in backups:
        m = _NAME_PATTERN.match(bk.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y%m%d").date()
        except ValueError:
            continue
        # Recent → keep
        if d > cutoff:
            continue
        # Monthly anchor → keep if not yet seen for this (year, month)
        ym = (d.year, d.month)
        if keep_monthly and ym not in monthly_seen:
            monthly_seen.add(ym)
            continue
        log.info(f"  cleanup: deleting {bk.name}")
        try:
            bk.unlink()
            deleted += 1
        except OSError as e:
            log.warning(f"  cleanup failed {bk.name}: {e}")
    return deleted


def main():
    p = argparse.ArgumentParser(description="Backup snapshots history (Block 6)")
    p.add_argument("--retention", type=int, default=30,
                   help="retention days for daily backups (default 30)")
    p.add_argument("--no-monthly", action="store_true",
                   help="do not keep one backup per month")
    p.add_argument("--dry-run", action="store_true",
                   help="show actions without modifying anything")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")

    if args.dry_run:
        log.info("=== DRY RUN ===")
        if HISTORY_DIR.exists():
            n = sum(1 for _ in HISTORY_DIR.iterdir())
            log.info(f"  history: {n} files in {HISTORY_DIR}")
        if BACKUP_DIR.exists():
            cutoff = datetime.now(timezone.utc).date() - timedelta(days=args.retention)
            for bk in sorted(BACKUP_DIR.glob("snapshots_*.tar.gz")):
                m = _NAME_PATTERN.match(bk.name)
                if not m: continue
                d = datetime.strptime(m.group(1), "%Y%m%d").date()
                tag = "old" if d < cutoff else "recent"
                log.info(f"  [{tag}] {bk.name}")
        return

    out = make_backup()
    if out is None:
        log.warning("No backup created (history empty).")
        return
    deleted = cleanup_old_backups(retention_days=args.retention,
                                    keep_monthly=not args.no_monthly)
    log.info(f"Cleanup: {deleted} old backup(s) removed.")


if __name__ == "__main__":
    main()
