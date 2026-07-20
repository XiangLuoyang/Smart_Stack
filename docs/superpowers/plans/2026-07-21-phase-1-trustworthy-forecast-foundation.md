# Phase 1: Trustworthy Forecast Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, append-only 10-trading-day forecast pipeline for the CSI 300, including immutable inputs, model versions, complete rankings, and automatic maturity settlement.

**Architecture:** Replace the in-memory/JSON screener with SQLAlchemy-backed runs. Keep market-source adapters at the boundary, normalize and validate daily bars before assigning a batch ID, then make forecasting a deterministic pure engine whose inputs and model version are persisted. APScheduler only orchestrates application services and creates a fresh SQLAlchemy session per job.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite, pandas, NumPy, pytest, React 18, TypeScript 5, Ant Design, Zustand.

## Global Constraints

- Only China A-share cash equities: Shanghai/Shenzhen main board, ChiNext, and STAR Market.
- Local single-user operation with one simulated account; retain `account_id` in storage.
- Formal forecast horizon is exactly 10 trading days and is generated once after market close.
- Intraday quotes target a 15-second refresh and never overwrite a formal forecast.
- Predictions, universe membership, rankings, evidence, decisions, and reviews are append-only.
- No broker connection, automatic order placement, short selling, margin, futures, or options.
- LLM output is explanatory only and never contributes to numeric forecast scores.

---

### Task 1: Add schema migrations and a deterministic test database

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/db/base.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/20260721_01_forecast_foundation.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_migrations.py`

**Interfaces:**
- Consumes: `app.db.base.Base`, `Settings.sqlalchemy_url`.
- Produces: `alembic upgrade head`; `db_session` and `client` fixtures using one temporary SQLite database.

- [ ] **Step 1: Add a failing migration smoke test**

```python
# backend/tests/test_migrations.py
from sqlalchemy import inspect

def test_forecast_schema_exists(migrated_engine):
    tables = set(inspect(migrated_engine).get_table_names())
    assert {"market_data_batches", "daily_bars", "universe_snapshots", "trading_calendar", "model_versions",
            "screening_runs", "screening_candidates", "prediction_snapshots",
            "review_results"} <= tables
```

- [ ] **Step 2: Run the test and observe the missing fixture/schema**

Run: `cd backend && python -m pytest tests/test_migrations.py -q`

Expected: FAIL because `migrated_engine` and the forecast tables do not exist.

- [ ] **Step 3: Install Alembic and wire metadata into migrations**

Add `alembic>=1.13.0` to `backend/requirements.txt`. In `migrations/env.py`, import `Base` and `app.models`, set `target_metadata = Base.metadata`, and obtain the URL with `get_settings().sqlalchemy_url`. Change `init_db()` to run `alembic.command.upgrade(config, "head")`; do not call `Base.metadata.create_all()` in application startup.

The first revision must create the nine tables asserted above, including a unique session date in `trading_calendar` and named unique constraints for `(market_data_batch_id, symbol, date)` on immutable normalized `daily_bars`, `(business_date, source)` on batches, `(business_date, index_code)` on universe snapshots, `(name, version)` on models, `(business_date, model_version_id)` on screening runs, `(screening_run_id, symbol)` on candidates, and `(business_date, symbol, model_version_id, horizon_days)` on predictions.

- [ ] **Step 4: Add temporary-database fixtures and verify migration idempotency**

```python
@pytest.fixture
def migrated_engine(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DB_URL", url)
    get_settings.cache_clear()
    upgrade_database(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()
    get_settings.cache_clear()
```

Run twice: `cd backend && alembic upgrade head && alembic upgrade head`

Expected: both commands exit 0; the pytest smoke test passes.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/db/base.py backend/alembic.ini backend/migrations backend/tests/conftest.py backend/tests/test_migrations.py
git commit -m "chore: add versioned database migrations"
```

### Task 2: Persist and validate market-data batches and universe snapshots

**Files:**
- Create: `backend/app/models/forecast.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/engine/market_data_validation.py`
- Create: `backend/app/services/market_data_service.py`
- Create: `backend/tests/test_market_data_service.py`

**Interfaces:**
- Consumes: `MarketDataAdaptor.load_kline(symbol, start_date, end_date) -> tuple[pd.DataFrame, str]`.
- Produces: `MarketDataService.freeze_daily_batch(business_date: date, members: list[UniverseMemberInput]) -> FrozenMarketBatch`; `validate_daily_bars(df, as_of) -> ValidationResult`.

- [ ] **Step 1: Write validation and immutability tests**

```python
def test_rejects_future_bar():
    df = frame([("2026-07-21", 10.0), ("2026-07-22", 11.0)])
    result = validate_daily_bars(df, date(2026, 7, 21))
    assert not result.valid
    assert result.reason == "FUTURE_DATA"

def test_freeze_batch_is_idempotent(db_session, fake_source):
    svc = MarketDataService(db_session, fake_source)
    first = svc.freeze_daily_batch(date(2026, 7, 21), MEMBERS)
    second = svc.freeze_daily_batch(date(2026, 7, 21), MEMBERS)
    assert second.batch_id == first.batch_id
```

- [ ] **Step 2: Run tests and confirm missing modules**

Run: `cd backend && python -m pytest tests/test_market_data_service.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement normalized inputs and validation**

```python
@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str | None
    rows: int
    last_date: date | None

@dataclass(frozen=True)
class FrozenMarketBatch:
    batch_id: str
    universe_snapshot_id: str
    valid_symbols: tuple[str, ...]
    failures: dict[str, str]
```

Normalize columns to `date/open/high/low/close/volume/adj_factor`; reject duplicate dates, nonpositive OHLC, `high < low`, future rows, fewer than 120 rows, and latest bars older than the requested business date. Try configured sources in order, record every source attempt, and accept a fallback only when it passes the same validation; never merge two sources inside one symbol series. Store every accepted normalized row in immutable `DailyBar` records tied to the batch, plus chosen source, cutoff time, row count, SHA-256 checksum, validation status, and per-symbol failure JSON. Store all CSI 300 members in `UniverseSnapshot.members_json` before fetching bars. Forecast services must read `DailyBar` records by batch ID instead of re-fetching historical prices.

- [ ] **Step 4: Verify partial success and checksum stability**

Run: `cd backend && python -m pytest tests/test_market_data_service.py -q`

Expected: PASS, including one valid and one failed symbol in the same frozen batch.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models backend/app/engine/market_data_validation.py backend/app/services/market_data_service.py backend/tests/test_market_data_service.py
git commit -m "feat: freeze validated market data batches"
```

### Task 3: Implement model registry and the formal 10-day forecast contract

**Files:**
- Create: `backend/app/engine/forecasting.py`
- Create: `backend/app/services/forecast_service.py`
- Create: `backend/app/schemas/forecast.py`
- Create: `backend/tests/test_forecasting.py`
- Create: `backend/tests/test_forecast_service.py`

**Interfaces:**
- Consumes: validated adjusted daily bars and `ModelVersion.id`.
- Produces: `ForecastEngine.predict(frame: pd.DataFrame, benchmark: pd.DataFrame) -> ForecastOutput`; `ForecastService.create_formal_prediction(...) -> PredictionSnapshot`.

- [ ] **Step 1: Write tests for horizon, probability, and uniqueness**

```python
def test_baseline_forecast_contract(price_frame, benchmark_frame):
    out = ForecastEngine().predict(price_frame, benchmark_frame)
    assert out.horizon_days == 10
    assert abs(out.p_up + out.p_flat + out.p_down - 1.0) < 1e-9
    assert out.lower_return <= out.median_return <= out.upper_return

def test_formal_prediction_cannot_be_overwritten(db_session, frozen_batch, model):
    svc = ForecastService(db_session)
    first = svc.create_formal_prediction(frozen_batch, model, "000001")
    second = svc.create_formal_prediction(frozen_batch, model, "000001")
    assert first.id == second.id
```

- [ ] **Step 2: Run the tests to establish RED**

Run: `cd backend && python -m pytest tests/test_forecasting.py tests/test_forecast_service.py -q`

Expected: FAIL because the forecast interfaces are absent.

- [ ] **Step 3: Implement the deterministic baseline**

```python
@dataclass(frozen=True)
class ForecastOutput:
    horizon_days: int
    p_up: float
    p_flat: float
    p_down: float
    median_return: float
    lower_return: float
    upper_return: float
    expected_excess_return: float
    expected_mfe: float
    expected_mae: float
```

Use only rows at or before the batch cutoff. Build 10-day historical forward returns from adjusted closes, weight the latest 60 observations equally, define flat as `abs(return) <= 0.01`, use empirical 10th/50th/90th percentiles for the interval, and subtract the benchmark median for expected excess return. Persist model name `historical-10d-baseline`, semantic version `1.0.0`, feature version `daily-adjusted-v1`, parameters JSON, training cutoff, and code revision.

- [ ] **Step 4: Verify reproducibility**

Run: `cd backend && python -m pytest tests/test_forecasting.py tests/test_forecast_service.py -q`

Expected: PASS; two runs against the same batch and model return the same prediction ID and values.

- [ ] **Step 5: Commit**

```bash
git add backend/app/engine/forecasting.py backend/app/services/forecast_service.py backend/app/schemas/forecast.py backend/tests/test_forecasting.py backend/tests/test_forecast_service.py
git commit -m "feat: add immutable ten day forecast contract"
```

### Task 4: Replace the JSON screener with persistent complete rankings

**Files:**
- Rewrite: `backend/app/services/screener_service.py`
- Modify: `backend/app/api/screener.py`
- Create: `backend/app/schemas/screener.py`
- Create: `backend/tests/test_screener_service.py`
- Create: `backend/tests/test_screener_api.py`

**Interfaces:**
- Consumes: `MarketDataService.freeze_daily_batch`, `ForecastService.create_formal_prediction`.
- Produces: `ScreenerService.run(business_date: date, model_version_id: str) -> ScreeningRun`; `GET /api/screener/runs`; `GET /api/screener/runs/{run_id}`.

- [ ] **Step 1: Specify complete-ranking behavior**

```python
def test_scan_persists_successes_and_failures(db_session, pipeline):
    run = ScreenerService(db_session, pipeline).run(date(2026, 7, 21), "model-1")
    assert run.total_count == 3
    assert run.success_count == 2
    assert run.failure_count == 1
    rows = ScreenerService(db_session, pipeline).list_candidates(run.id)
    assert [r.rank for r in rows if r.status == "SUCCESS"] == [1, 2]
    assert next(r.failure_reason for r in rows if r.status == "FAILED") == "STALE_DATA"
```

- [ ] **Step 2: Run targeted tests**

Run: `cd backend && python -m pytest tests/test_screener_service.py tests/test_screener_api.py -q`

Expected: FAIL against the current singleton `ScreenerJob`.

- [ ] **Step 3: Implement database-backed runs**

Rank successful candidates by `expected_excess_return DESC`, then `median_return DESC`, then `symbol ASC`; assign stable ranks, retain every failed member with a reason, and set run state to `SUCCESS`, `PARTIAL`, or `FAILED`. Enforce idempotency with `(business_date, model_version_id)` and expose historical pagination rather than only the latest in-memory status.

- [ ] **Step 4: Verify API response contract**

Run: `cd backend && python -m pytest tests/test_screener_service.py tests/test_screener_api.py -q`

Expected: PASS; response includes `data_cutoff`, `model_version`, `total_count`, `success_count`, `failure_count`, full `candidates`, and derived `top10`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/screener_service.py backend/app/api/screener.py backend/app/schemas/screener.py backend/tests/test_screener_service.py backend/tests/test_screener_api.py
git commit -m "feat: persist CSI 300 screening history"
```

### Task 5: Settle matured forecasts using the trading calendar

**Files:**
- Create: `backend/app/engine/trading_calendar.py`
- Create: `backend/app/services/review_service.py`
- Create: `backend/app/schemas/review.py`
- Create: `backend/app/api/reviews.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_trading_calendar.py`
- Create: `backend/tests/test_review_service.py`
- Create: `backend/tests/test_review_api.py`

**Interfaces:**
- Consumes: `PredictionSnapshot`, adjusted daily bars for stock and CSI 300.
- Produces: `TradingCalendar.shift(start: date, sessions: int) -> date`; `ReviewService.settle_due(as_of: date) -> SettlementSummary`; `POST /api/reviews/settle`; `GET /api/reviews`.

- [ ] **Step 1: Write holiday and settlement metric tests**

```python
def test_shift_counts_sessions_not_calendar_days(calendar):
    assert calendar.shift(date(2026, 9, 25), 10) == date(2026, 10, 16)

def test_settlement_records_actuals(db_session, due_prediction, bars):
    result = ReviewService(db_session, bars).settle_due(date(2026, 8, 4))
    assert result.settled == 1
    review = db_session.scalar(select(ReviewResult))
    assert review.actual_return == pytest.approx(0.08)
    assert review.direction_correct is True
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `cd backend && python -m pytest tests/test_trading_calendar.py tests/test_review_service.py -q`

Expected: FAIL because calendar and settlement services are missing.

- [ ] **Step 3: Implement calendar and immutable automatic results**

Load sessions from AkShare into a cached `trading_calendar` table through the migration from Task 1. Calculate actual adjusted return, benchmark excess, signed error, interval coverage, MFE, and MAE from day 1 through day 10. Use a unique `prediction_snapshot_id`; if already settled, return it unchanged.

- [ ] **Step 4: Verify missing-price behavior**

Add an API test asserting `POST /api/reviews/settle` returns the settlement summary and `GET /api/reviews?state=DUE` returns matured predictions without user notes. Then run: `cd backend && python -m pytest tests/test_trading_calendar.py tests/test_review_service.py tests/test_review_api.py -q`

Expected: PASS; missing maturity price leaves the prediction `PENDING_DATA` and does not create zero-valued results.

- [ ] **Step 5: Commit**

```bash
git add backend/app/engine/trading_calendar.py backend/app/services/review_service.py backend/app/schemas/review.py backend/app/api/reviews.py backend/app/main.py backend/tests/test_trading_calendar.py backend/tests/test_review_service.py backend/tests/test_review_api.py
git commit -m "feat: settle ten day forecasts"
```

### Task 6: Schedule the daily pipeline safely

**Files:**
- Modify: `backend/app/jobs/scheduler.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/jobs/daily_research.py`
- Create: `backend/tests/test_daily_research_job.py`

**Interfaces:**
- Consumes: services from Tasks 2–5.
- Produces: `run_daily_research(business_date: date | None = None) -> DailyRunSummary`; `settle_matured_forecasts(as_of: date | None = None) -> SettlementSummary`.

- [ ] **Step 1: Test fresh-session and idempotent orchestration**

```python
def test_daily_job_uses_one_owned_session(session_factory, pipeline):
    summary = run_daily_research(date(2026, 7, 21), session_factory, pipeline)
    assert summary.screening_status == "SUCCESS"
    assert session_factory.opened == session_factory.closed == 1
```

- [ ] **Step 2: Run the test to establish RED**

Run: `cd backend && python -m pytest tests/test_daily_research_job.py -q`

Expected: FAIL because the orchestration module is missing.

- [ ] **Step 3: Implement job boundaries and schedule**

Create one session inside each job, commit through services, roll back on unhandled exceptions, close in `finally`, and never attach a session to the process-wide market-service singleton. Schedule quote refresh every 15 seconds during trading hours, formal daily research at `16:30 Asia/Shanghai`, and settlement at `17:00 Asia/Shanghai`; set `max_instances=1`, `coalesce=True`, and stable job IDs.

- [ ] **Step 4: Run scheduler/service tests**

Run: `cd backend && python -m pytest tests/test_daily_research_job.py tests/test_screener_service.py tests/test_review_service.py -q`

Expected: PASS with no cross-thread SQLite or shared-session errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/jobs backend/app/core/config.py backend/app/jobs/scheduler.py backend/tests/test_daily_research_job.py
git commit -m "feat: schedule reliable daily research pipeline"
```

### Task 7: Expose forecast history and rebuild the screener UI

**Files:**
- Create: `backend/app/api/forecasts.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_forecast_api.py`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Rewrite: `frontend/src/components/ScreenerPanel.tsx`
- Create: `frontend/src/components/ForecastCard.tsx`

**Interfaces:**
- Consumes: REST contracts from Tasks 3–5.
- Produces: `GET /api/forecasts/{symbol}` and a historical CSI 300 screen with explicit stale/failed/degraded states.

- [ ] **Step 1: Add backend API tests**

```python
def test_forecast_history_is_newest_first(client, seeded_predictions):
    response = client.get("/api/forecasts/000001")
    assert response.status_code == 200
    assert response.json()[0]["business_date"] == "2026-07-21"
    assert response.json()[0]["horizon_days"] == 10
```

- [ ] **Step 2: Run API test and TypeScript build**

Run: `cd backend && python -m pytest tests/test_forecast_api.py -q`

Expected: FAIL with 404.

- [ ] **Step 3: Implement typed API/UI contracts**

Define `ForecastSnapshot`, `ScreeningRun`, and `ScreeningCandidate` TypeScript interfaces matching Pydantic names exactly. `ScreenerPanel` must render business date, data cutoff, model/version, completion counts, full ranked table, a Top 10 filter, and failure reason tags. `ForecastCard` must display 10-day median/interval/probabilities/excess return without combining LLM text into the numeric score.

- [ ] **Step 4: Verify backend and frontend**

Run: `cd backend && python -m pytest tests/test_forecast_api.py tests/test_screener_api.py -q && cd ../frontend && npm run build`

Expected: pytest PASS and Vite build succeeds.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/forecasts.py backend/app/main.py backend/tests/test_forecast_api.py frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/components/ScreenerPanel.tsx frontend/src/components/ForecastCard.tsx
git commit -m "feat: show reproducible forecast history"
```

### Task 8: Phase-one end-to-end acceptance

**Files:**
- Create: `backend/tests/test_forecast_pipeline_e2e.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: all phase-one services and endpoints.
- Produces: one executable acceptance test proving freeze → screen → predict → mature → settle.

- [ ] **Step 1: Add the complete acceptance scenario**

```python
def test_forecast_pipeline_e2e(app_client, deterministic_market_source):
    run = app_client.post("/api/screener/runs", json={"business_date": "2026-07-21"}).json()
    assert run["success_count"] == 3
    prediction = run["top10"][0]["prediction"]
    assert prediction["horizon_days"] == 10
    settled = app_client.post("/api/reviews/settle", json={"as_of": "2026-08-04"}).json()
    assert settled["settled"] == 3
```

- [ ] **Step 2: Run the full backend suite**

Run: `cd backend && python -m pytest tests -q`

Expected: PASS.

- [ ] **Step 3: Update user-facing setup and forecast semantics**

Document `alembic upgrade head`, the 16:30 formal forecast schedule, the exact 10-session target, model/version fields, partial-screen semantics, and how to trigger a local manual scan without enabling automatic orders.

- [ ] **Step 4: Run final phase checks**

Run: `cd backend && python -m pytest tests -q && alembic check && cd ../frontend && npm run build`

Expected: all tests pass, Alembic reports no new upgrade operations, and frontend build succeeds.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_forecast_pipeline_e2e.py README.md
git commit -m "test: verify trustworthy forecast pipeline"
```
