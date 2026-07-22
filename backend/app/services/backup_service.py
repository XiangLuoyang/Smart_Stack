"""本地备份服务:SQLite online backup + SHA-256 校验。"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class BackupService:
    def __init__(self, db_path: str, backup_dir: str):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> dict:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"smartstack_{ts}.db"

        src = sqlite3.connect(str(self.db_path))
        dst = sqlite3.connect(str(backup_file))
        src.backup(dst)
        dst.close()
        src.close()

        integrity = self._integrity_check(backup_file)
        checksum = self._sha256(backup_file)

        manifest = {
            "file": backup_file.name,
            "created_at": ts,
            "sha256": checksum,
            "integrity": integrity,
            "size_bytes": backup_file.stat().st_size,
        }
        manifest_path = self.backup_dir / f"smartstack_{ts}.manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return manifest

    def restore(self, backup_file: str) -> dict:
        backup_path = self.backup_dir / backup_file
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_file}")

        pre_restore = self.create_backup()

        shutil.copy2(str(backup_path), str(self.db_path))
        return {"restored_from": backup_file, "pre_restore_backup": pre_restore["file"]}

    def list_backups(self) -> list[dict]:
        manifests = sorted(self.backup_dir.glob("*.manifest.json"), reverse=True)
        results = []
        for m in manifests:
            try:
                results.append(json.loads(m.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def _integrity_check(self, db_file: Path) -> str:
        try:
            conn = sqlite3.connect(str(db_file))
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            return result[0] if result else "unknown"
        except Exception:
            return "error"

    def _sha256(self, file: Path) -> str:
        h = hashlib.sha256()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()