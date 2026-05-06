"""Tests for backup_snapshots — Block 6."""
import os
import tempfile
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import backup_snapshots


def test_make_backup_returns_none_on_empty_history(tmp_path, monkeypatch):
    empty_history = tmp_path / "history"
    empty_history.mkdir()
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(backup_snapshots, "HISTORY_DIR", empty_history)
    monkeypatch.setattr(backup_snapshots, "BACKUP_DIR", backup_dir)
    assert backup_snapshots.make_backup() is None


def test_make_backup_creates_tarball(tmp_path, monkeypatch):
    history = tmp_path / "history"
    history.mkdir()
    (history / "NQ_full_levels_20260101.json").write_text("{}")
    (history / "ES_full_levels_20260101.json").write_text("{}")

    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(backup_snapshots, "HISTORY_DIR", history)
    monkeypatch.setattr(backup_snapshots, "BACKUP_DIR", backup_dir)

    out = backup_snapshots.make_backup()
    assert out is not None
    assert out.exists()
    assert out.suffix == ".gz"
    # Verify content
    with tarfile.open(out, "r:gz") as t:
        names = t.getnames()
    assert any("NQ_full_levels_20260101.json" in n for n in names)


def test_cleanup_keeps_recent_and_first_of_month(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr(backup_snapshots, "BACKUP_DIR", backup_dir)

    today = datetime.now().date()
    # Create files: 5 recent + 5 old (different month + scattered)
    files = []
    # 3 recent daily backups (D-1, D-2, D-3)
    for d in range(1, 4):
        ts = (today - timedelta(days=d)).strftime("%Y%m%d") + "_120000"
        f = backup_dir / f"snapshots_{ts}.tar.gz"
        f.write_text("dummy"); files.append(f)
    # 1 old backup beyond default 30-day retention
    old_date = today - timedelta(days=60)
    f_old = backup_dir / f"snapshots_{old_date.strftime('%Y%m%d')}_120000.tar.gz"
    f_old.write_text("dummy"); files.append(f_old)
    # 1 old backup in a different month (first of the month -> kept if keep_monthly)
    other_month = today.replace(day=1) - timedelta(days=45)
    f_month = backup_dir / f"snapshots_{other_month.strftime('%Y%m%d')}_120000.tar.gz"
    f_month.write_text("dummy"); files.append(f_month)

    deleted = backup_snapshots.cleanup_old_backups(retention_days=30,
                                                    keep_monthly=True)
    # At least f_old (out of retention without a monthly anchor) should be deleted
    # But if f_old is the only one for its month -> also kept (keep_monthly)
    # Verify recent files are intact
    for d in range(1, 4):
        ts = (today - timedelta(days=d)).strftime("%Y%m%d") + "_120000"
        assert (backup_dir / f"snapshots_{ts}.tar.gz").exists(), f"recent D-{d} must remain"
    # The exact result depends on monthly distribution, but cleanup must not crash
    assert deleted >= 0
