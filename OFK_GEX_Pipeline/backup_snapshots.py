"""
backup_snapshots.py — Tarball horodaté du dossier history/ vers backups/.

Pourquoi : l'IVR (IV Rank) repose sur 252 jours d'historique. Si data/history/
est supprimé/corrompu, l'IVR redevient inutilisable pendant ~1 an. Ce script
crée un backup compressé chaque jour.

Politique de rétention :
- Garde les N derniers backups journaliers (défaut 30)
- Garde 1 backup par mois (premier du mois) indéfiniment si --keep-monthly

Usage CLI :
  py backup_snapshots.py                    # backup + cleanup avec défauts
  py backup_snapshots.py --retention 60     # garde 60 jours
  py backup_snapshots.py --no-monthly       # pas d'archivage mensuel
  py backup_snapshots.py --dry-run

Usage programmatique :
  from backup_snapshots import make_backup, cleanup_old_backups
  make_backup()
  cleanup_old_backups(retention_days=30, keep_monthly=True)

Intégré automatiquement dans run_morning_NQ/ES.py (1×/jour le matin).
"""
from __future__ import annotations

import argparse
import logging
import re
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import HISTORY_DIR, DATA_DIR

BACKUP_DIR: Path = DATA_DIR / "backups"
_NAME_PATTERN = re.compile(r"snapshots_(\d{8})_\d{6}\.tar\.gz")

log = logging.getLogger(__name__)


def make_backup() -> Optional[Path]:
    """Crée un tarball horodaté des snapshots actuels. Renvoie le path ou None."""
    if not HISTORY_DIR.exists() or not any(HISTORY_DIR.iterdir()):
        log.warning(f"history dir vide ou absent : {HISTORY_DIR}")
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = BACKUP_DIR / f"snapshots_{ts}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        tar.add(HISTORY_DIR, arcname="history")
    size_kb = out.stat().st_size / 1024
    log.info(f"backup → {out.name} ({size_kb:.1f} KB)")
    return out


def cleanup_old_backups(retention_days: int = 30,
                         keep_monthly: bool = True) -> int:
    """Supprime les backups journaliers > retention_days.
    Si keep_monthly, garde le plus ancien backup de chaque mois.

    Renvoie le nombre de fichiers supprimés.
    """
    if not BACKUP_DIR.exists():
        return 0
    cutoff = datetime.now().date() - timedelta(days=retention_days)
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
        # Récents → garde
        if d > cutoff:
            continue
        # Anchor mensuel → garde si pas encore vu pour ce (year, month)
        ym = (d.year, d.month)
        if keep_monthly and ym not in monthly_seen:
            monthly_seen.add(ym)
            continue
        log.info(f"  cleanup : suppression {bk.name}")
        try:
            bk.unlink()
            deleted += 1
        except OSError as e:
            log.warning(f"  cleanup échec {bk.name}: {e}")
    return deleted


def main():
    p = argparse.ArgumentParser(description="Backup snapshots history (Bloc 6)")
    p.add_argument("--retention", type=int, default=30,
                   help="jours de rétention pour backups journaliers (défaut 30)")
    p.add_argument("--no-monthly", action="store_true",
                   help="ne pas garder un backup par mois")
    p.add_argument("--dry-run", action="store_true",
                   help="affiche les actions sans rien modifier")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")

    if args.dry_run:
        log.info("=== DRY RUN ===")
        if HISTORY_DIR.exists():
            n = sum(1 for _ in HISTORY_DIR.iterdir())
            log.info(f"  history : {n} fichiers dans {HISTORY_DIR}")
        if BACKUP_DIR.exists():
            cutoff = datetime.now().date() - timedelta(days=args.retention)
            for bk in sorted(BACKUP_DIR.glob("snapshots_*.tar.gz")):
                m = _NAME_PATTERN.match(bk.name)
                if not m: continue
                d = datetime.strptime(m.group(1), "%Y%m%d").date()
                tag = "old" if d < cutoff else "recent"
                log.info(f"  [{tag}] {bk.name}")
        return

    out = make_backup()
    if out is None:
        log.warning("Aucun backup créé (history vide).")
        return
    deleted = cleanup_old_backups(retention_days=args.retention,
                                    keep_monthly=not args.no_monthly)
    log.info(f"Cleanup : {deleted} ancien(s) backup(s) supprimé(s).")


if __name__ == "__main__":
    main()
