"""预检与备份测试。"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.preflight import run_preflight
from app.services.backup_service import BackupService


class TestPreflight:
    def test_ok_with_key(self, tmp_path):
        report = run_preflight(data_dir=str(tmp_path), llm_api_key="test-key")
        assert report.status == "OK"

    def test_missing_llm_key_degraded(self, tmp_path):
        report = run_preflight(data_dir=str(tmp_path), llm_api_key=None)
        assert report.status == "DEGRADED"
        assert "LLM_DISABLED" in report.codes

    def test_unwritable_dir_fails(self, tmp_path):
        target = tmp_path / "locked"
        target.mkdir()
        with patch("os.access", return_value=False):
            report = run_preflight(data_dir=str(target), llm_api_key="k")
        assert report.status == "FAILED"
        assert "DATA_DIR_NOT_WRITABLE" in report.codes


class TestBackup:
    def test_create_and_list(self, tmp_path):
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.commit()
        conn.close()

        backup_dir = tmp_path / "backups"
        svc = BackupService(str(db_file), str(backup_dir))
        manifest = svc.create_backup()
        assert manifest["integrity"] == "ok"
        assert manifest["sha256"]
        assert len(svc.list_backups()) == 1

    def test_restore_creates_pre_restore_backup(self, tmp_path):
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()

        backup_dir = tmp_path / "backups"
        svc = BackupService(str(db_file), str(backup_dir))
        manifest = svc.create_backup()
        time.sleep(1.1)  # ensure different timestamp
        result = svc.restore(manifest["file"])
        assert result["restored_from"] == manifest["file"]
        assert len(svc.list_backups()) == 2