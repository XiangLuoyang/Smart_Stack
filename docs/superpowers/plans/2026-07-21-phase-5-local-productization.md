# Phase 5: Local Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the complete research workstation dependable for daily local use through reproducible setup, health visibility, structured logs, safe backup/restore, and documented recovery.

**Architecture:** Keep deployment single-machine and container-friendly. Validate configuration before starting mutable services, expose component health with explicit degraded states, write rotating structured logs, and use SQLite's online backup API plus checksums and manifests for recoverable local snapshots. Provide shell/PowerShell wrappers around the same Python maintenance commands.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, SQLite, APScheduler, Docker Compose, pytest, React 18, TypeScript 5, Vite, Bash, PowerShell.

## Global Constraints

- Local single-user only; no cloud sync, multi-tenancy, authentication server, telemetry, or broker connection.
- Preserve all prediction, research, order, trade, review, metric, and attachment history.
- A backup is valid only after SQLite integrity check, manifest generation, and SHA-256 verification.
- Restore never overwrites the active database without an automatically created pre-restore backup.
- Health states are `OK`, `DEGRADED`, or `FAILED`; stale/missing data is never reported as healthy.
- Secrets remain in local environment files and are never written to logs, exports, or health responses.

---

### Task 1: Validate local configuration before application startup

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/core/preflight.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_preflight.py`
- Create: `.env.example`

**Interfaces:**
- Consumes: environment variables and filesystem paths.
- Produces: `run_preflight(settings: Settings) -> PreflightReport`; startup aborts only on `FAILED` checks.

- [ ] **Step 1: Write required/degraded checks**

```python
def test_unwritable_data_dir_fails(settings, monkeypatch):
    monkeypatch.setattr(os, "access", lambda *_: False)
    report = run_preflight(settings)
    assert report.status == "FAILED"
    assert "DATA_DIR_NOT_WRITABLE" in report.codes

def test_missing_llm_key_is_degraded_not_failed(settings):
    settings.llm_api_key = None
    report = run_preflight(settings)
    assert report.status == "DEGRADED"
    assert "LLM_DISABLED" in report.codes
```

- [ ] **Step 2: Run preflight tests**

Run: `cd backend && python -m pytest tests/test_preflight.py -q`

Expected: FAIL because preflight does not exist.

- [ ] **Step 3: Implement typed configuration checks**

Validate Python version ≥3.12, data/log/backup directories, SQLite connectivity and migration head, unique production model, exactly one active account, quote interval exactly 15 seconds, positive fee rates, available disk ≥1 GB, and optional LLM configuration. Redact values whose names include `KEY`, `TOKEN`, `SECRET`, or `PASSWORD`. Run preflight before scheduler startup; raise with actionable codes on `FAILED`.

- [ ] **Step 4: Verify startup reports**

Run: `cd backend && python -m pytest tests/test_preflight.py -q`

Expected: PASS for OK, degraded LLM, bad migration, unwritable directory, and low-disk fixtures.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/core/preflight.py backend/app/main.py backend/tests/test_preflight.py .env.example
git commit -m "feat: validate local workstation startup"
```

### Task 2: Add structured rotating logs and task-run records

**Files:**
- Create: `backend/app/core/logging.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/jobs/daily_research.py`
- Modify: `backend/app/jobs/scheduler.py`
- Create: `backend/app/models/task_run.py`
- Create: `backend/app/models/local_preference.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/20260721_05_operations_health.py`
- Create: `backend/tests/test_task_logging.py`

**Interfaces:**
- Consumes: application/job events.
- Produces: JSON log lines; `TaskRun` rows containing run ID, task type, state, counts, timestamps, error summary, and retry number; a single `LocalPreference` row for non-secret user settings.

- [ ] **Step 1: Test correlation and secret redaction**

```python
def test_task_log_contains_run_id_and_no_secret(tmp_path, caplog):
    with task_run_context("DAILY_RESEARCH", "run-1"):
        logger.info("request", extra={"api_key": "secret-value", "symbol": "000001"})
    line = caplog.records[-1].message
    assert "run-1" in line
    assert "secret-value" not in line
```

- [ ] **Step 2: Run logging tests**

Run: `cd backend && python -m pytest tests/test_task_logging.py -q`

Expected: FAIL because logging context and task model are absent.

- [ ] **Step 3: Implement log and task lifecycle**

Write UTF-8 JSON logs to `data/logs/smart-stack.jsonl`, rotate at 10 MB with 10 files, and retain console output. Task helper inserts `RUNNING`, then `SUCCESS/PARTIAL/FAILED`, with count JSON and truncated sanitized error summary. Include run ID in service logs. Never log request headers, LLM keys, complete prompts, confirmation tokens, or database URLs. The same migration creates one `local_preferences` row with data-source priority JSON, fee rates, daily/monthly backup retention, LLM model/base URL, and update time; it never stores API keys.

- [ ] **Step 4: Upgrade and test**

Run: `cd backend && alembic upgrade head && python -m pytest tests/test_task_logging.py -q`

Expected: PASS and a failed test task leaves a `FAILED` row with a closed session.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/logging.py backend/app/main.py backend/app/jobs backend/app/models backend/migrations/versions/20260721_05_operations_health.py backend/tests/test_task_logging.py
git commit -m "feat: add structured local task logging"
```

### Task 3: Implement database and attachment backup with verification

**Files:**
- Create: `backend/app/maintenance/backup.py`
- Create: `backend/app/maintenance/__init__.py`
- Create: `backend/tests/test_backup.py`

**Interfaces:**
- Consumes: active SQLite path, attachments directory, backup directory.
- Produces: `create_backup(settings, reason) -> BackupManifest`; `verify_backup(path) -> VerificationResult`.

- [ ] **Step 1: Write consistent-backup tests**

```python
def test_backup_is_integrity_checked_and_manifested(settings, seeded_db):
    manifest = create_backup(settings, reason="MANUAL")
    assert manifest.database_sha256 == sha256_file(manifest.database_path)
    assert verify_backup(manifest.root).valid
    assert sqlite_integrity_check(manifest.database_path) == "ok"

def test_tampered_backup_fails_verification(settings, seeded_db):
    manifest = create_backup(settings, reason="MANUAL")
    manifest.database_path.write_bytes(b"tampered")
    assert verify_backup(manifest.root).code == "CHECKSUM_MISMATCH"
```

- [ ] **Step 2: Run backup tests**

Run: `cd backend && python -m pytest tests/test_backup.py -q`

Expected: FAIL because backup module is absent.

- [ ] **Step 3: Implement online backup and manifest**

Use `sqlite3.Connection.backup()` to copy a live database, then run `PRAGMA integrity_check` on the copy. Copy attachments preserving relative paths. Write `manifest.json` containing format version `1`, created time, app version, Alembic revision, reason, source paths, row counts for critical tables, and SHA-256 for every file. Write to a temporary sibling directory and atomically rename only after verification. Default retention is 30 daily and 12 monthly backups; delete only verified backups outside retention.

- [ ] **Step 4: Run backup tests**

Run: `cd backend && python -m pytest tests/test_backup.py -q`

Expected: PASS, including live-write simulation and tamper detection.

- [ ] **Step 5: Commit**

```bash
git add backend/app/maintenance backend/tests/test_backup.py
git commit -m "feat: create verified local backups"
```

### Task 4: Implement guarded restore and export

**Files:**
- Create: `backend/app/maintenance/restore.py`
- Create: `backend/app/maintenance/export.py`
- Create: `backend/tests/test_restore.py`
- Create: `backend/tests/test_export.py`

**Interfaces:**
- Consumes: verified backup directory or active database.
- Produces: `restore_backup(settings, backup_path, confirmation) -> RestoreResult`; ZIP research export without secrets.

- [ ] **Step 1: Write destructive-safety tests**

```python
def test_restore_requires_exact_confirmation(settings, valid_backup):
    with pytest.raises(ConfirmationError):
        restore_backup(settings, valid_backup, confirmation="yes")

def test_restore_creates_pre_restore_backup(settings, valid_backup):
    result = restore_backup(settings, valid_backup, confirmation="RESTORE smartstack.db")
    assert result.pre_restore_backup.exists()
    assert result.integrity_check == "ok"

def test_export_excludes_secrets(settings):
    archive = export_research_data(settings)
    assert ".env" not in zip_names(archive)
```

- [ ] **Step 2: Run restore/export tests**

Run: `cd backend && python -m pytest tests/test_restore.py tests/test_export.py -q`

Expected: FAIL because maintenance commands are absent.

- [ ] **Step 3: Implement guarded restore and portable export**

Restore requires stopped scheduler, exact database filename confirmation, valid manifest/checksums/integrity, compatible format version, and a successful automatic `PRE_RESTORE` backup. Restore into a temporary database, migrate to current head, integrity-check, then atomically replace the active file; preserve the failed target on error. Export CSV/JSON for predictions, screens, cases/events, orders/trades, reviews, and metrics plus attachments and a manifest; exclude `.env`, logs, confirmation tokens, and backup directories.

- [ ] **Step 4: Run recovery tests**

Run: `cd backend && python -m pytest tests/test_restore.py tests/test_export.py -q`

Expected: PASS; failed migration leaves the active database unchanged.

- [ ] **Step 5: Commit**

```bash
git add backend/app/maintenance/restore.py backend/app/maintenance/export.py backend/tests/test_restore.py backend/tests/test_export.py
git commit -m "feat: restore and export local research data"
```

### Task 5: Expose actionable component health and safe settings

**Files:**
- Create: `backend/app/services/health_service.py`
- Create: `backend/app/services/settings_service.py`
- Create: `backend/app/schemas/health.py`
- Create: `backend/app/schemas/settings.py`
- Create: `backend/app/api/settings.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_health_api.py`
- Create: `backend/tests/test_settings_api.py`

**Interfaces:**
- Consumes: preflight report, task runs, latest batch/run/quote/model, disk and backup state, and the singleton `LocalPreference`.
- Produces: `GET /api/health` with aggregate and component status; `GET /api/health/tasks`; `GET/PUT /api/settings` for whitelisted non-secret settings.

- [ ] **Step 1: Test stale data and redaction**

```python
def test_health_reports_stale_quote_as_degraded(client, stale_quote):
    body = client.get("/api/health").json()
    assert body["status"] == "DEGRADED"
    assert body["components"]["quotes"]["code"] == "STALE"
    assert "api_key" not in json.dumps(body).lower()

def test_settings_never_returns_or_accepts_api_key(client):
    assert "api_key" not in client.get("/api/settings").json()
    response = client.put("/api/settings", json={"llm_api_key": "secret"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run health tests**

Run: `cd backend && python -m pytest tests/test_health_api.py tests/test_settings_api.py -q`

Expected: FAIL against the current always-OK endpoint.

- [ ] **Step 3: Implement component rules**

Report database/migration, quotes, daily data batch, latest CSI 300 scan, production model, scheduler, settlement backlog, LLM, disk, and backup. Include status, code, message, checked time, last success time, and age seconds where relevant. Aggregate is `FAILED` if database/migration fails, otherwise `DEGRADED` if any component is not OK. The Docker healthcheck uses `/api/health/live` for process liveness; readiness uses `/api/health`. Settings accept only ordered sources from `AKSHARE/YFINANCE`, configured fee rates within documented ranges, backup retention of 7–365 daily and 1–60 monthly copies, and LLM model/base URL. The formal quote interval is displayed as locked at 15 seconds. API keys remain environment-only and the response exposes only `llm_key_configured: boolean`.

- [ ] **Step 4: Run health tests**

Run: `cd backend && python -m pytest tests/test_health_api.py tests/test_settings_api.py -q`

Expected: PASS for OK, stale, LLM-disabled, failed migration, and overdue settlement cases.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/health_service.py backend/app/services/settings_service.py backend/app/schemas/health.py backend/app/schemas/settings.py backend/app/api/settings.py backend/app/main.py backend/tests/test_health_api.py backend/tests/test_settings_api.py
git commit -m "feat: expose workstation health and settings"
```

### Task 6: Add local maintenance CLI and daily backup job

**Files:**
- Create: `backend/app/cli.py`
- Create: `backend/app/api/maintenance.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/jobs/scheduler.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/tests/test_cli.py`
- Create: `backend/tests/test_maintenance_api.py`

**Interfaces:**
- Consumes: preflight, backup, verify, restore, export, migration and task services.
- Produces: `python -m app.cli check|backup|verify|restore|export|migrate|run-daily|settle`; `POST /api/maintenance/backups`; `POST /api/maintenance/backups/verify`; `POST /api/maintenance/exports`.

- [ ] **Step 1: Test command exit codes**

```python
def test_check_exit_codes(cli_runner, healthy_settings, degraded_settings, failed_settings):
    assert cli_runner("check", healthy_settings).exit_code == 0
    assert cli_runner("check", degraded_settings).exit_code == 2
    assert cli_runner("check", failed_settings).exit_code == 1
```

- [ ] **Step 2: Run CLI tests**

Run: `cd backend && python -m pytest tests/test_cli.py -q`

Expected: FAIL because CLI is absent.

- [ ] **Step 3: Implement commands and schedule**

Use `argparse` with JSON output option. Restore requires `--confirm "RESTORE smartstack.db"`. Schedule a verified daily backup at 18:30 Asia/Shanghai after settlement/performance jobs; record it as a task run. CLI commands create and close their own sessions and return stable exit codes 0 OK, 1 FAILED, 2 DEGRADED. The local-only maintenance router exposes backup creation, verification by manifest ID, and export creation; validate requested paths against the configured backup directory and intentionally expose no restore endpoint.

- [ ] **Step 4: Run command and scheduler tests**

Run: `cd backend && python -m pytest tests/test_cli.py tests/test_maintenance_api.py tests/test_daily_research_job.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/cli.py backend/app/api/maintenance.py backend/app/main.py backend/app/jobs/scheduler.py backend/app/core/config.py backend/tests/test_cli.py backend/tests/test_maintenance_api.py
git commit -m "feat: add local maintenance commands"
```

### Task 7: Provide reproducible local and Docker startup

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/requirements.lock`
- Modify: `frontend/package-lock.json`
- Modify: `Dockerfile`
- Modify: `backend/Dockerfile`
- Modify: `frontend/Dockerfile`
- Modify: `docker-compose.yml`
- Rewrite: `start_workbench.sh`
- Rewrite: `start_workbench.bat`
- Create: `scripts/verify_install.sh`
- Create: `scripts/verify_install.ps1`

**Interfaces:**
- Consumes: supported Python/Node/Docker environments.
- Produces: repeatable dependency installation, migration, preflight, and startup.

- [ ] **Step 1: Pin and verify dependency inputs**

Generate `backend/requirements.lock` from `backend/requirements.txt` with hashes using Python 3.12 and `pip-tools`; install frontend with `npm ci`. Images use explicit Python 3.12 and Node 20 base tags, run as non-root users, and never bake `.env` into layers.

- [ ] **Step 2: Implement fail-fast start scripts**

Both scripts must check runtime versions, create directories, install only when lock hashes change, run `python -m app.cli migrate`, run `python -m app.cli check`, then start backend/frontend and print local URLs. Store PIDs under `data/run/`; handle Ctrl+C by terminating only those child PIDs.

- [ ] **Step 3: Harden Compose health and persistence**

Persist `data`, `attachments`, `backups`, and `logs`; use `/api/health/live` for container liveness and wait for backend readiness before frontend. Add `init: true`, bounded log rotation, and read-only root filesystems with explicit writable volumes where compatible.

- [ ] **Step 4: Verify both installation paths**

Run: `bash scripts/verify_install.sh`

Expected: creates a disposable data directory, migrates, starts services, receives 200 from liveness/readiness, runs backend tests and frontend build, then stops its own processes.

Run: `docker compose config && docker compose build`

Expected: Compose validates and both images build.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/requirements.lock frontend/package-lock.json Dockerfile backend/Dockerfile frontend/Dockerfile docker-compose.yml start_workbench.sh start_workbench.bat scripts
git commit -m "chore: make local startup reproducible"
```

### Task 8: Build settings and health UI

**Files:**
- Create: `frontend/src/pages/SettingsHealthPage.tsx`
- Create: `frontend/src/components/health/HealthSummary.tsx`
- Create: `frontend/src/components/health/TaskRunTable.tsx`
- Create: `frontend/src/components/health/BackupPanel.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Consumes: health/task APIs, `GET/PUT /api/settings`, and safe maintenance endpoints.
- Produces: local operational status UI, non-secret settings editor, and manual backup/export actions.

- [ ] **Step 1: Define health types**

```typescript
export type HealthStatus = "OK" | "DEGRADED" | "FAILED";
export interface ComponentHealth {
  status: HealthStatus;
  code: string;
  message: string;
  checked_at: string;
  last_success_at: string | null;
  age_seconds: number | null;
}
```

- [ ] **Step 2: Run frontend build after adding page import**

Run: `cd frontend && npm run build`

Expected: FAIL until types/components/API functions exist.

- [ ] **Step 3: Implement actionable local status**

Render aggregate status plus data, model, scheduler, review backlog, LLM, storage, and backup cards. Show last task runs and error summaries. Add validated editors for data-source priority, fees, backup retention, and LLM model/base URL; show the 15-second quote interval as locked and show only whether an LLM key exists. Provide “立即备份”“校验备份”“导出研究数据”; restore is intentionally CLI-only because it requires stopped services. Never display secrets or complete environment values.

- [ ] **Step 4: Build and verify degraded rendering**

Run: `cd frontend && npm run build`

Expected: build succeeds; mocked stale quote and disabled LLM show DEGRADED with correct guidance.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SettingsHealthPage.tsx frontend/src/components/health frontend/src/api/client.ts frontend/src/types/index.ts
git commit -m "feat: add local health and backup center"
```

### Task 9: Document and execute disaster-recovery acceptance

**Files:**
- Create: `docs/LOCAL_OPERATIONS.md`
- Create: `docs/DATA_RECOVERY.md`
- Create: `backend/tests/test_disaster_recovery_e2e.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: complete workstation and maintenance CLI.
- Produces: tested setup, daily-operation, backup, export, failure, and restore runbooks.

- [ ] **Step 1: Add recovery acceptance scenario**

```python
def test_disaster_recovery_preserves_research_history(settings, full_history):
    before = critical_table_checksums(settings.db_path)
    backup = create_backup(settings, "ACCEPTANCE")
    mutate_database(settings.db_path)
    restore_backup(settings, backup.root, "RESTORE smartstack.db")
    assert critical_table_checksums(settings.db_path) == before
```

- [ ] **Step 2: Write exact runbooks**

`LOCAL_OPERATIONS.md` covers install, configuration, start/stop, schedules, health codes, log locations, upgrades, and manual daily run. `DATA_RECOVERY.md` covers backup layout, verification, export, exact restore command, pre-restore backup, rollback after failed migration, and a quarterly recovery drill. Include Windows and macOS/Linux commands.

- [ ] **Step 3: Run the complete automated suite**

Run: `cd backend && python -m pytest tests -q && python -m app.cli check --json && cd ../frontend && npm run build`

Expected: tests/build pass and health returns OK or documented DEGRADED only for optional LLM/network data sources.

- [ ] **Step 4: Execute a disposable backup/restore drill**

Run: `cd backend && python -m pytest tests/test_disaster_recovery_e2e.py -q`

Expected: PASS with identical critical-table checksums before backup and after restore.

- [ ] **Step 5: Commit**

```bash
git add docs/LOCAL_OPERATIONS.md docs/DATA_RECOVERY.md backend/tests/test_disaster_recovery_e2e.py README.md
git commit -m "docs: add verified local operations runbook"
```
