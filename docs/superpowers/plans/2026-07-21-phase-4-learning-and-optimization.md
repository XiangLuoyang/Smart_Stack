# Phase 4: Learning and Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure model, CSI 300 Top 10, personal judgment, and execution performance separately, then govern model promotion with reproducible walk-forward evidence.

**Architecture:** Compute versioned metric batches from immutable predictions, reviews, decisions, and trades. Pure metric functions produce transparent values; aggregation services persist dimensions and sample counts. Training experiments remain challengers until a deterministic promotion gate compares them with the production baseline over untouched time windows.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite, pandas, NumPy, scikit-learn, pytest, React 18, TypeScript 5, Ant Design Charts or existing lightweight chart primitives.

## Global Constraints

- Evaluate only matured formal 10-trading-day predictions; never recompute historical prediction inputs.
- Report sample count and date range beside every metric.
- Keep model outcome, screening outcome, user judgment, and execution outcome separate.
- Use time-ordered walk-forward splits; never randomly shuffle financial time series.
- New models do not replace the production model unless they pass all recorded promotion gates.
- Industry and market-regime slices are diagnostic; they cannot hide poor aggregate results.

---

### Task 1: Add versioned performance metric schema

**Files:**
- Create: `backend/app/models/performance.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/20260721_04_performance_metrics.py`
- Create: `backend/tests/test_performance_models.py`

**Interfaces:**
- Consumes: model version, screening run, prediction, case, review, and trade IDs.
- Produces: `MetricBatch`, `PerformanceMetric`, `MarketRegimeSnapshot`, `ModelEvaluationRun`, `ModelPromotionDecision`.

- [ ] **Step 1: Test version and dimension uniqueness**

```python
def test_metric_identity_is_versioned(db_session, metric_batch):
    metric = PerformanceMetric(batch_id=metric_batch.id, scope="MODEL", scope_id="m1",
        metric_name="direction_accuracy", dimension_key="ALL", value=0.6,
        sample_count=100, period_start=date(2025,1,1), period_end=date(2026,1,1))
    db_session.add(metric); db_session.commit()
    db_session.add(copy.copy(metric))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Step 2: Run model tests**

Run: `cd backend && python -m pytest tests/test_performance_models.py -q`

Expected: FAIL because performance tables are absent.

- [ ] **Step 3: Implement schema**

`MetricBatch` stores calculation version, cutoff, source row counts, status, and checksum. `PerformanceMetric` stores scope (`MODEL/SCREEN/USER/EXECUTION`), scope ID, name, dimension key/value, numeric value, numerator, denominator, sample count, period, and JSON metadata. `MarketRegimeSnapshot` stores date, benchmark trend, realized volatility bucket, and regime label. `ModelEvaluationRun` stores candidate/baseline IDs, folds JSON, and metrics JSON. `ModelPromotionDecision` stores evaluation run ID, candidate/baseline IDs, gate decisions JSON, approved boolean, creator, and immutable creation time; promotion references this stable ID.

- [ ] **Step 4: Upgrade and verify**

Run: `cd backend && alembic upgrade head && python -m pytest tests/test_performance_models.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models backend/migrations/versions/20260721_04_performance_metrics.py backend/tests/test_performance_models.py
git commit -m "feat: add versioned performance metrics"
```

### Task 2: Implement transparent model and ranking metrics

**Files:**
- Create: `backend/app/engine/performance_metrics.py`
- Create: `backend/tests/test_performance_metrics.py`

**Interfaces:**
- Consumes: aligned arrays of predictions, actuals, intervals, ranks, benchmark returns.
- Produces: `direction_accuracy`, `mae`, `rmse`, `interval_coverage`, `spearman_rank`, `top_n_return`, `top_n_excess_return`.

- [ ] **Step 1: Write exact numerical tests**

```python
def test_model_metrics_known_values():
    out = model_metrics(pred=[.10, -.05, .02], actual=[.08, .01, -.01],
        lower=[0, -.10, -.02], upper=[.15, 0, .05])
    assert out.direction_accuracy == pytest.approx(1/3)
    assert out.mae == pytest.approx((.02 + .06 + .03) / 3)
    assert out.interval_coverage == pytest.approx(2/3)

def test_top10_is_equal_weighted():
    out = ranking_metrics(ranks=[1,2,11], actual=[.10,.00,.50], benchmark=.02, top_n=10)
    assert out.top_n_return == pytest.approx(.05)
    assert out.top_n_excess_return == pytest.approx(.03)
```

- [ ] **Step 2: Run metric tests**

Run: `cd backend && python -m pytest tests/test_performance_metrics.py -q`

Expected: FAIL because functions are missing.

- [ ] **Step 3: Implement pure functions with missing-data rules**

Return dataclasses containing value and sample count. Drop a row only from metrics whose required values are missing; never coerce missing to zero. Direction uses the same ±1% flat band as the forecast contract. Spearman returns `None` below five observations or for constant ranks/returns. Top N is equal-weighted by formal rank and uses the same-period CSI 300 return.

- [ ] **Step 4: Run metric tests**

Run: `cd backend && python -m pytest tests/test_performance_metrics.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/engine/performance_metrics.py backend/tests/test_performance_metrics.py
git commit -m "feat: calculate model and ranking performance"
```

### Task 3: Calculate user judgment and execution increment separately

**Files:**
- Create: `backend/app/engine/decision_metrics.py`
- Create: `backend/tests/test_decision_metrics.py`

**Interfaces:**
- Consumes: formal prediction, initial/latest user decision before cutoff, actual result, execution attribution.
- Produces: `DecisionMetricSet` and `ExecutionMetricSet`.

- [ ] **Step 1: Specify counterfactual comparisons**

```python
def test_user_override_increment():
    out = decision_metrics(model_direction="UP", user_direction="NEUTRAL", actual_direction="DOWN")
    assert out.model_correct is False
    assert out.user_correct is True
    assert out.user_increment == 1

def test_no_operation_is_not_zero_return():
    out = execution_metrics(planned=True, operated=False, trades=[])
    assert out.operated is False
    assert out.realized_return is None
```

- [ ] **Step 2: Run decision metric tests**

Run: `cd backend && python -m pytest tests/test_decision_metrics.py -q`

Expected: FAIL because the engine is missing.

- [ ] **Step 3: Implement unambiguous attribution**

Map bullish/neutral/bearish to the same return bands. User increment is `user_correct - model_correct`, calculated only when a decision existed before the prediction matured. Execution metrics include operated rate, entry/exit slippage, fees as percentage of notional, plan adherence, and realized return; no-operation and open positions remain null where outcome is unknowable.

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_decision_metrics.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/engine/decision_metrics.py backend/tests/test_decision_metrics.py
git commit -m "feat: separate judgment and execution metrics"
```

### Task 4: Classify market regimes and aggregate metric batches

**Files:**
- Create: `backend/app/engine/market_regime.py`
- Create: `backend/app/services/performance_service.py`
- Create: `backend/tests/test_market_regime.py`
- Create: `backend/tests/test_performance_service.py`

**Interfaces:**
- Consumes: CSI 300 adjusted closes and all settled observations up to cutoff.
- Produces: `classify_regime(frame, on_date) -> MarketRegime`; `PerformanceService.rebuild(cutoff) -> MetricBatch`.

- [ ] **Step 1: Test regime and idempotent batch behavior**

```python
def test_regime_uses_only_past_data(benchmark_frame):
    first = classify_regime(benchmark_frame.loc[:"2026-07-21"], date(2026,7,21))
    changed_future = benchmark_frame.copy(); changed_future.loc["2026-07-22":, "close"] *= 10
    assert classify_regime(changed_future, date(2026,7,21)) == first

def test_rebuild_same_cutoff_returns_same_batch(service):
    assert service.rebuild(date(2026,7,21)).id == service.rebuild(date(2026,7,21)).id
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/test_market_regime.py tests/test_performance_service.py -q`

Expected: FAIL because services are absent.

- [ ] **Step 3: Implement regime and dimensions**

Trend is `BULL/BEAR/SIDEWAYS` from close versus 60-day moving average with a ±2% neutral band. Volatility is `LOW/MEDIUM/HIGH` from trailing 20-day annualized volatility thresholds `<15%`, `15–25%`, `>25%`; combine to a stable label. Aggregate ALL, model version, industry, regime, calendar year, and rolling 12-month dimensions. Persist null metrics with sample count rather than inventing zero.

- [ ] **Step 4: Verify deterministic rebuild**

Run: `cd backend && python -m pytest tests/test_market_regime.py tests/test_performance_service.py -q`

Expected: PASS and a repeated cutoff produces the same checksum.

- [ ] **Step 5: Commit**

```bash
git add backend/app/engine/market_regime.py backend/app/services/performance_service.py backend/tests/test_market_regime.py backend/tests/test_performance_service.py
git commit -m "feat: aggregate performance by market regime"
```

### Task 5: Add leakage-safe walk-forward evaluation

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/engine/walk_forward.py`
- Create: `backend/app/services/model_evaluation_service.py`
- Create: `backend/tests/test_walk_forward.py`
- Create: `backend/tests/test_model_evaluation_service.py`

**Interfaces:**
- Consumes: feature rows containing `as_of_date`, target availability date, symbol, features, and 10-day target.
- Produces: `build_folds(rows, train_sessions, validation_sessions, embargo_sessions) -> list[Fold]`; immutable evaluation run.

- [ ] **Step 1: Write leakage tests**

```python
def test_fold_enforces_target_availability_and_embargo(rows):
    folds = build_folds(rows, train_sessions=504, validation_sessions=63, embargo_sessions=10)
    for fold in folds:
        assert max(r.target_available_date for r in fold.train) < min(r.as_of_date for r in fold.validation)

def test_rows_are_never_randomly_shuffled(rows):
    folds = build_folds(list(reversed(rows)), 504, 63, 10)
    assert all(f.train == sorted(f.train, key=lambda r: r.as_of_date) for f in folds)
```

- [ ] **Step 2: Run walk-forward tests**

Run: `cd backend && python -m pytest tests/test_walk_forward.py tests/test_model_evaluation_service.py -q`

Expected: FAIL because evaluator is absent.

- [ ] **Step 3: Implement fold generation and challenger evaluation**

Add `scikit-learn>=1.4.0` to backend requirements. Use expanding training windows, 63-session validation windows, and a 10-session embargo. Fit preprocessing inside each fold only. Start with regularized linear regression and logistic direction classifier as challengers; store feature names, scalers, parameters, fold dates, predictions, and metrics. Reserve the latest 126 sessions as the final untouched test window.

- [ ] **Step 4: Verify reproducibility**

Run: `cd backend && python -m pytest tests/test_walk_forward.py tests/test_model_evaluation_service.py -q`

Expected: PASS; fixed input and random seed produce byte-identical metrics JSON.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/engine/walk_forward.py backend/app/services/model_evaluation_service.py backend/tests/test_walk_forward.py backend/tests/test_model_evaluation_service.py
git commit -m "feat: add leakage safe model evaluation"
```

### Task 6: Enforce recorded model-promotion gates

**Files:**
- Create: `backend/app/services/model_registry_service.py`
- Create: `backend/tests/test_model_promotion.py`

**Interfaces:**
- Consumes: completed baseline/challenger `ModelEvaluationRun` on the same folds.
- Produces: `evaluate_promotion(candidate_id, baseline_id) -> PromotionDecision`; `promote(decision_id) -> ModelVersion`.

- [ ] **Step 1: Define promotion gate tests**

```python
def test_candidate_fails_when_top10_gain_is_sector_concentrated(service, concentrated_run):
    decision = service.evaluate_promotion(concentrated_run.candidate_id, concentrated_run.baseline_id)
    assert not decision.approved
    assert "SECTOR_CONCENTRATION" in decision.failed_gates

def test_only_approved_decision_can_promote(service, rejected_decision):
    with pytest.raises(DomainError, match="PROMOTION_NOT_APPROVED"):
        service.promote(rejected_decision.id)
```

- [ ] **Step 2: Run gate tests**

Run: `cd backend && python -m pytest tests/test_model_promotion.py -q`

Expected: FAIL because registry service is absent.

- [ ] **Step 3: Implement exact gates**

Require final-test MAE no worse than baseline, direction accuracy at least baseline + 2 percentage points, Spearman no worse than baseline, Top 10 excess at least baseline + 1 percentage point annualized, improvement in at least three regime labels, no industry contributing over 40% of excess P&L, complete reproducibility metadata, and at least 252 matured predictions. Store every pass/fail and supporting number. Promotion creates a new `PRODUCTION` model version and retires the prior production version; it never edits historical predictions.

- [ ] **Step 4: Run promotion tests**

Run: `cd backend && python -m pytest tests/test_model_promotion.py -q`

Expected: PASS for approved, rejected, and insufficient-sample cases.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/model_registry_service.py backend/tests/test_model_promotion.py
git commit -m "feat: govern forecast model promotion"
```

### Task 7: Expose performance and model-evaluation APIs

**Files:**
- Create: `backend/app/schemas/performance.py`
- Create: `backend/app/api/performance.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_performance_api.py`

**Interfaces:**
- Consumes: `PerformanceService`, model registry/evaluation services.
- Produces: `GET /api/performance/summary`; `/series`; `/dimensions`; `/models`; `/evaluations/{id}`.

- [ ] **Step 1: Test metric metadata visibility**

```python
def test_summary_includes_samples_and_period(client, metric_batch):
    item = client.get("/api/performance/summary", params={"scope":"MODEL"}).json()[0]
    assert {"value", "sample_count", "period_start", "period_end", "calculation_version"} <= item.keys()
```

- [ ] **Step 2: Run API tests**

Run: `cd backend && python -m pytest tests/test_performance_api.py -q`

Expected: FAIL with 404.

- [ ] **Step 3: Implement filterable read endpoints**

Validate scopes/metric names/dimensions against enums, support model version, industry, regime, and date filters, and return the latest completed metric batch by default. Evaluation endpoints expose fold boundaries and gate evidence. Promotion remains an explicit POST requiring the stored approved decision ID.

- [ ] **Step 4: Run API tests**

Run: `cd backend && python -m pytest tests/test_performance_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/performance.py backend/app/api/performance.py backend/app/main.py backend/tests/test_performance_api.py
git commit -m "feat: expose learning and model metrics"
```

### Task 8: Build the performance dashboard and phase acceptance

**Files:**
- Create: `frontend/src/pages/PerformancePage.tsx`
- Create: `frontend/src/components/performance/MetricCard.tsx`
- Create: `frontend/src/components/performance/PerformanceSeries.tsx`
- Create: `frontend/src/components/performance/DimensionTable.tsx`
- Create: `frontend/src/components/performance/ModelComparison.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `backend/tests/test_learning_loop_e2e.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 7 endpoints.
- Produces: model/screen/user/execution dashboard and end-to-end metric rebuild proof.

- [ ] **Step 1: Define the frontend metric contract**

```typescript
export interface PerformanceMetric {
  scope: "MODEL" | "SCREEN" | "USER" | "EXECUTION";
  metric_name: string;
  dimension_key: string;
  dimension_value: string;
  value: number | null;
  sample_count: number;
  period_start: string;
  period_end: string;
  calculation_version: string;
}
```

- [ ] **Step 2: Add an end-to-end rebuild test**

```python
def test_learning_loop_e2e(client, matured_research_history):
    rebuilt = client.post("/api/performance/rebuild", json={"cutoff":"2026-07-21"})
    assert rebuilt.status_code == 201
    scopes = {x["scope"] for x in client.get("/api/performance/summary").json()}
    assert scopes == {"MODEL", "SCREEN", "USER", "EXECUTION"}
```

- [ ] **Step 3: Implement dashboard with honest denominators**

Create four separate sections. Every card shows value, sample count, and date range; charts expose model version changes. Add filters for period/model/industry/regime and an error-tag table. `ModelComparison` shows fold metrics and gate decisions but offers promotion only for an already approved stored decision.

- [ ] **Step 4: Run final phase checks**

Run: `cd backend && python -m pytest tests -q && cd ../frontend && npm run build`

Expected: all tests and build pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PerformancePage.tsx frontend/src/components/performance frontend/src/api/client.ts frontend/src/types/index.ts backend/tests/test_learning_loop_e2e.py README.md
git commit -m "feat: add research performance dashboard"
```
