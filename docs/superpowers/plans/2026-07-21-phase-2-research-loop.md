# Phase 2: Research Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn forecasts into durable research cases with frozen snapshots, append-only evidence and decisions, a focused single-stock workspace, and a 10-day review queue.

**Architecture:** Add a research aggregate rooted at `ResearchCase`. The case freezes references and user inputs at creation; evidence, decision changes, and review notes are separate immutable events. Read services compose forecasts, indicators, risk, LLM reports, and prior cases without letting an unavailable LLM block the workflow.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite, pytest, React 18, TypeScript 5, Ant Design, Zustand, React Markdown.

## Global Constraints

- Only China A-share cash equities: Shanghai/Shenzhen main board, ChiNext, and STAR Market.
- Formal forecast horizon is exactly 10 trading days.
- Formal forecasts and initial research snapshots are immutable; changes are append-only events.
- Quantitative forecast, technical indicators, risk metrics, and LLM interpretation remain visually and semantically separate.
- LLM failure never blocks forecast viewing, case creation, evidence, decisions, or review.
- The user manually authors every decision; no generated analysis can place an order.

---

### Task 1: Add research-case, evidence, and decision event schema

**Files:**
- Create: `backend/app/models/research.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/20260721_02_research_loop.py`
- Create: `backend/tests/test_research_models.py`

**Interfaces:**
- Consumes: `PredictionSnapshot.id`, optional `ScreeningCandidate.id`.
- Produces: `ResearchCase`, `EvidenceEntry`, `DecisionEntry`, `ReviewNote` ORM models.

- [ ] **Step 1: Write schema invariants**

```python
def test_case_requires_initial_decision(db_session, prediction):
    case = ResearchCase(symbol="000001", prediction_snapshot_id=prediction.id)
    db_session.add(case)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_events_are_ordered_by_created_at(db_session, research_case):
    db_session.add_all([
        EvidenceEntry(research_case_id=research_case.id, stance="SUPPORT", category="EARNINGS",
            content="盈利上修", source_label="USER", observed_date=date(2026, 7, 21)),
        EvidenceEntry(research_case_id=research_case.id, stance="OPPOSE", category="VALUATION",
            content="估值过高", source_label="USER", observed_date=date(2026, 7, 22)),
    ])
    db_session.commit()
    assert [e.stance for e in research_case.evidence_entries] == ["SUPPORT", "OPPOSE"]
```

- [ ] **Step 2: Run migration/model tests**

Run: `cd backend && python -m pytest tests/test_research_models.py -q`

Expected: FAIL because research models do not exist.

- [ ] **Step 3: Implement schema and constraints**

`ResearchCase` stores symbol, prediction ID, candidate ID, status (`ACTIVE/CLOSED`), initial direction (`BULLISH/NEUTRAL/BEARISH`), thesis, expected return lower/upper, strongest counterargument, invalidation condition, planned entry/target/stop, confidence 1–5, frozen analysis JSON, and timestamps. `EvidenceEntry` stores stance (`SUPPORT/OPPOSE/NEUTRAL`), category, content, source label/URL, observed date, and creator. `DecisionEntry` stores direction, action (`WATCH/PLAN_BUY/HOLD/PLAN_SELL/EXIT/NO_ACTION`), rationale, confidence, and superseded decision ID. `ReviewNote` stores attribution and error tags JSON. Foreign keys use `RESTRICT`; there is no update endpoint for event content.

- [ ] **Step 4: Upgrade and verify**

Run: `cd backend && alembic upgrade head && python -m pytest tests/test_research_models.py -q`

Expected: migration succeeds and tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models backend/migrations/versions/20260721_02_research_loop.py backend/tests/test_research_models.py
git commit -m "feat: add append only research records"
```

### Task 2: Implement research-case creation and event services

**Files:**
- Create: `backend/app/services/research_service.py`
- Create: `backend/app/schemas/research.py`
- Create: `backend/tests/test_research_service.py`

**Interfaces:**
- Consumes: `ForecastService.get(prediction_id)`, `SignalService.get_all_sources(symbol)`, indicator/risk calculators.
- Produces: `ResearchService.create_case(CaseCreate) -> ResearchCase`; `append_evidence`; `append_decision`; `close_case`.

- [ ] **Step 1: Write freeze and append-only tests**

```python
def test_create_case_freezes_current_analysis(db_session, prediction, analysis_reader):
    case = ResearchService(db_session, analysis_reader).create_case(CaseCreate(
        prediction_snapshot_id=prediction.id, direction="BULLISH", thesis="需求改善",
        expected_return_lower=0.03, expected_return_upper=0.12,
        counterargument="价格已反映", invalidation_condition="跌破20日低点",
        planned_entry=10, target_price=11.2, stop_price=9.4, confidence=4))
    analysis_reader.payload["technical"]["rsi"] = 99
    assert json.loads(case.frozen_analysis_json)["technical"]["rsi"] != 99

def test_append_decision_preserves_prior_record(db_session, research_case):
    service = ResearchService(db_session)
    old = service.append_decision(research_case.id, DecisionCreate(direction="BULLISH", action="WATCH", rationale="等待", confidence=3))
    new = service.append_decision(research_case.id, DecisionCreate(direction="NEUTRAL", action="NO_ACTION", rationale="逻辑减弱", confidence=2))
    assert old.id != new.id and new.supersedes_id == old.id
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `cd backend && python -m pytest tests/test_research_service.py -q`

Expected: FAIL because service and schemas are absent.

- [ ] **Step 3: Implement transactional aggregate operations**

Validate direction, price ordering (`stop < entry < target` for bullish cases), confidence 1–5, and expected-return range. Serialize the analysis snapshot with sorted JSON keys. Every append method inserts a new row; only `ResearchCase.status` and `closed_at` may update. Reject appends to a closed case with domain code `CASE_CLOSED`.

- [ ] **Step 4: Run service tests**

Run: `cd backend && python -m pytest tests/test_research_service.py -q`

Expected: PASS, including rollback when initial decision insertion fails.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/research_service.py backend/app/schemas/research.py backend/tests/test_research_service.py
git commit -m "feat: manage immutable research cases"
```

### Task 3: Build the single-stock research read model

**Files:**
- Create: `backend/app/services/stock_research_service.py`
- Create: `backend/app/schemas/stock_research.py`
- Create: `backend/tests/test_stock_research_service.py`

**Interfaces:**
- Consumes: latest/formal forecast, `MarketService.get_kline`, technical/risk engines, signals, prior cases.
- Produces: `StockResearchService.get(symbol: str, as_of: date | None) -> StockResearchView`.

- [ ] **Step 1: Specify separated sections and degraded LLM state**

```python
def test_stock_research_keeps_sections_separate(service):
    view = service.get("000001")
    assert view.forecast.horizon_days == 10
    assert view.technical.rsi == 52.0
    assert view.risk.annualized_volatility > 0
    assert view.llm.status == "UNAVAILABLE"
    assert view.llm.report_markdown is None
```

- [ ] **Step 2: Run the focused test**

Run: `cd backend && python -m pytest tests/test_stock_research_service.py -q`

Expected: FAIL because the read model is missing.

- [ ] **Step 3: Implement composition without a blended score**

Return `{symbol, as_of, data_cutoff, quote, kline, forecast, technical, risk, llm, historical_forecasts, active_cases, closed_cases}`. Use explicit section statuses `READY/STALE/UNAVAILABLE/DEGRADED`; do not map missing values to zero. Include the exact model version and source timestamps.

- [ ] **Step 4: Verify LLM independence**

Run: `cd backend && python -m pytest tests/test_stock_research_service.py -q`

Expected: PASS when LLM raises, while quantitative sections remain `READY`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/stock_research_service.py backend/app/schemas/stock_research.py backend/tests/test_stock_research_service.py
git commit -m "feat: compose single stock research view"
```

### Task 4: Expose research REST endpoints

**Files:**
- Create: `backend/app/api/research.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_research_api.py`

**Interfaces:**
- Consumes: `ResearchService`, `StockResearchService`.
- Produces: `GET /api/research/stocks/{symbol}`; CRUD-like append endpoints under `/api/research/cases` with no destructive update/delete.

- [ ] **Step 1: Add endpoint contract tests**

```python
def test_case_api_is_append_only(client, prediction):
    created = client.post("/api/research/cases", json=case_payload(prediction.id))
    assert created.status_code == 201
    case_id = created.json()["id"]
    assert client.patch(f"/api/research/cases/{case_id}", json={"thesis": "改写"}).status_code == 405
    event = client.post(f"/api/research/cases/{case_id}/evidence", json={
        "stance": "OPPOSE", "category": "VALUATION", "content": "估值升至历史90分位",
        "source_label": "个人观察", "observed_date": "2026-07-22"})
    assert event.status_code == 201
```

- [ ] **Step 2: Run API tests**

Run: `cd backend && python -m pytest tests/test_research_api.py -q`

Expected: FAIL with 404.

- [ ] **Step 3: Implement endpoints and error mapping**

Add list filters for status, symbol, created date, and review state. Map `CASE_NOT_FOUND` to 404, validation errors to 422, and `CASE_CLOSED` to 409. Provide only `POST /evidence`, `POST /decisions`, and `POST /close`; intentionally omit PATCH and DELETE.

- [ ] **Step 4: Verify OpenAPI and test suite**

Run: `cd backend && python -m pytest tests/test_research_api.py -q`

Expected: PASS; `/openapi.json` contains no mutation route capable of overwriting event content.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/research.py backend/app/main.py backend/tests/test_research_api.py
git commit -m "feat: expose append only research api"
```

### Task 5: Reorient navigation around discovery, research, decisions, and learning

**Files:**
- Rewrite: `frontend/src/App.tsx`
- Create: `frontend/src/components/AppNavigation.tsx`
- Create: `frontend/src/pages/TodayPage.tsx`
- Create: `frontend/src/pages/ScreenerPage.tsx`
- Create: `frontend/src/pages/StockResearchPage.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

**Interfaces:**
- Consumes: phase-one screener/forecast APIs and Task 4 stock research endpoint.
- Produces: route state type `WorkspacePage = "today" | "screener" | "stock" | "cases" | "reviews" | "performance" | "operations" | "settings"`.

- [ ] **Step 1: Define typed navigation state**

```typescript
export type WorkspacePage =
  | "today" | "screener" | "stock" | "cases"
  | "reviews" | "performance" | "operations" | "settings";

export interface NavigationState {
  page: WorkspacePage;
  symbol?: string;
  caseId?: string;
}
```

- [ ] **Step 2: Run the TypeScript build before implementation**

Run: `cd frontend && npm run build`

Expected: FAIL after importing the not-yet-created navigation/page modules.

- [ ] **Step 3: Implement research-first shell**

The default page is `today`; primary navigation order is 今日、沪深300、单股研究、研究案例、复盘、模型表现. Put 模拟操作 and 设置 after a divider. `TodayPage` shows latest scan state and Top 10, active cases, forecasts due within three sessions, overdue reviews, today's simulated operations, and basic data/model status; unavailable later-phase fields render as “尚未启用” rather than zero. `ScreenerPage` opens `StockResearchPage` with the selected symbol. Keep existing K-line, order, and position components available but remove them from the default three-column shell.

- [ ] **Step 4: Verify frontend build**

Run: `cd frontend && npm run build`

Expected: TypeScript and Vite build succeed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/AppNavigation.tsx frontend/src/pages frontend/src/index.css frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: make research the primary workspace"
```

### Task 6: Add case creation, timeline, and decision UI

**Files:**
- Create: `frontend/src/pages/ResearchCasesPage.tsx`
- Create: `frontend/src/components/research/CreateCaseDrawer.tsx`
- Create: `frontend/src/components/research/CaseTimeline.tsx`
- Create: `frontend/src/components/research/EvidenceForm.tsx`
- Create: `frontend/src/components/research/DecisionForm.tsx`
- Modify: `frontend/src/pages/StockResearchPage.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Consumes: Task 4 endpoints.
- Produces: `createResearchCase`, `appendEvidence`, `appendDecision`, `closeResearchCase`; case timeline UI.

- [ ] **Step 1: Add exact client payload types**

```typescript
export interface CaseCreate {
  prediction_snapshot_id: string;
  direction: "BULLISH" | "NEUTRAL" | "BEARISH";
  thesis: string;
  expected_return_lower: number;
  expected_return_upper: number;
  counterargument: string;
  invalidation_condition: string;
  planned_entry: number | null;
  target_price: number | null;
  stop_price: number | null;
  confidence: 1 | 2 | 3 | 4 | 5;
}
```

- [ ] **Step 2: Run build to expose missing UI modules**

Run: `cd frontend && npm run build`

Expected: FAIL until components and API functions are implemented.

- [ ] **Step 3: Implement forms and immutable timeline**

Require all initial-case fields from the design. Render forecast snapshot, initial thesis, evidence, and decision changes in ascending time order with creator/source labels. Offer “追加证据”“更新判断”“结束案例”; never render edit/delete controls for past items. Validate bullish price order client-side while relying on server validation as authority.

- [ ] **Step 4: Build and manually exercise**

Run: `cd frontend && npm run build`

Expected: build succeeds; with the backend running, a case can be created from a stock page and two events appear without replacing the initial snapshot.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ResearchCasesPage.tsx frontend/src/pages/StockResearchPage.tsx frontend/src/components/research frontend/src/api/client.ts frontend/src/types/index.ts
git commit -m "feat: add research case timeline"
```

### Task 7: Build the maturity review queue and user review flow

**Files:**
- Modify: `backend/app/services/review_service.py`
- Modify: `backend/app/api/reviews.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_review_api.py`
- Create: `frontend/src/pages/ReviewCenterPage.tsx`
- Create: `frontend/src/components/research/ReviewForm.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Consumes: phase-one `ReviewResult`, phase-two `ResearchCase` and `ReviewNote`.
- Produces: `GET /api/reviews?state=DUE|COMPLETED`; `POST /api/reviews/{prediction_id}/notes`.

- [ ] **Step 1: Test automatic facts versus user attribution**

```python
def test_review_note_does_not_modify_market_result(client, settled_review):
    before = client.get(f"/api/reviews/{settled_review.prediction_snapshot_id}").json()
    response = client.post(f"/api/reviews/{settled_review.prediction_snapshot_id}/notes", json={
        "attribution": "方向正确但进场过早", "error_tags": ["EARLY_ENTRY"],
        "discipline_followed": False})
    after = client.get(f"/api/reviews/{settled_review.prediction_snapshot_id}").json()
    assert response.status_code == 201
    assert after["actual_return"] == before["actual_return"]
```

- [ ] **Step 2: Run backend review tests**

Run: `cd backend && python -m pytest tests/test_review_api.py -q`

Expected: FAIL because review endpoints are absent.

- [ ] **Step 3: Implement review query and append endpoint**

Return actual return, error, coverage, excess, MFE/MAE, linked cases, latest decision, and existing notes. Accept fixed tags `MODEL_DIRECTION`, `MODEL_MAGNITUDE`, `THESIS`, `TIMING`, `EARLY_ENTRY`, `LATE_ENTRY`, `EARLY_EXIT`, `LATE_EXIT`, `DISCIPLINE`, and `DATA_QUALITY`. Notes append; they never update automatic results.

- [ ] **Step 4: Implement Review Center and verify both stacks**

Show tabs 待复盘/已完成, due date, prediction-versus-actual comparison, linked case timeline, required attribution, multi-select tags, and discipline status.

Run: `cd backend && python -m pytest tests/test_review_api.py -q && cd ../frontend && npm run build`

Expected: tests pass and frontend builds.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/review_service.py backend/app/api/reviews.py backend/app/main.py backend/tests/test_review_api.py frontend/src/pages/ReviewCenterPage.tsx frontend/src/components/research/ReviewForm.tsx frontend/src/api/client.ts frontend/src/types/index.ts
git commit -m "feat: add ten day review workflow"
```

### Task 8: Phase-two research-loop acceptance

**Files:**
- Create: `backend/tests/test_research_loop_e2e.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: all phase-two endpoints.
- Produces: acceptance proof for screen → stock research → case → evidence → decision → settlement → review.

- [ ] **Step 1: Add complete API scenario**

```python
def test_research_loop_e2e(client, seeded_screening_run):
    stock = client.get("/api/research/stocks/000001").json()
    case = client.post("/api/research/cases", json=case_payload(stock["forecast"]["id"])).json()
    client.post(f"/api/research/cases/{case['id']}/evidence", json=evidence_payload())
    client.post(f"/api/research/cases/{case['id']}/decisions", json=decision_payload())
    client.post("/api/reviews/settle", json={"as_of": "2026-08-04"})
    note = client.post(f"/api/reviews/{stock['forecast']['id']}/notes", json=review_payload())
    assert note.status_code == 201
```

- [ ] **Step 2: Run all tests**

Run: `cd backend && python -m pytest tests -q`

Expected: PASS.

- [ ] **Step 3: Document the daily research workflow**

Update README with the exact user flow, append-only semantics, LLM-degraded behavior, and review tag definitions.

- [ ] **Step 4: Run phase acceptance commands**

Run: `cd backend && python -m pytest tests -q && cd ../frontend && npm run build`

Expected: backend and frontend checks pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_research_loop_e2e.py README.md
git commit -m "test: verify end to end research loop"
```
