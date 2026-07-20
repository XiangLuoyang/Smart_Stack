# Phase 3: Reliable Simulated Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed reliable, manually confirmed A-share paper operations into research cases while preserving cash, holdings, and execution attribution.

**Architecture:** Introduce a two-step preview/confirm command with an expiring idempotency token. Maintain explicit cash and position reservations for pending orders, derive sellable quantity from settlement lots for T+1, and apply order, trade, cash, lot, and reservation changes in one SQLite transaction. Every order is linked to a research case and fresh quote snapshot.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite WAL, pytest, React 18, TypeScript 5, Ant Design, Zustand.

## Global Constraints

- One local simulated account; keep `account_id` fields but expose no multi-account UI.
- Every simulated order requires explicit user confirmation; forecasts, screeners, schedulers, and LLMs cannot call confirmation.
- A-share long-only cash rules: 100-share board lots for buys, T+1 sellability, suspension and daily price-limit checks, configurable fees.
- Intraday quote freshness target is 15 seconds; stale or missing quotes cannot produce silent fills.
- No real broker API, no short selling, no margin, no auto stop-loss order generation.
- Every operation must link to an active research case and retain decision/quote context.

---

### Task 1: Add reservation, settlement-lot, and research linkage schema

**Files:**
- Modify: `backend/app/models/account.py`
- Modify: `backend/app/models/position.py`
- Modify: `backend/app/models/order.py`
- Modify: `backend/app/models/trade.py`
- Create: `backend/app/models/settlement_lot.py`
- Create: `backend/app/models/order_reservation.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/20260721_03_reliable_operations.py`
- Create: `backend/tests/test_operation_models.py`

**Interfaces:**
- Consumes: `ResearchCase.id`, existing account/order/trade schema.
- Produces: `Account.reserved_cash`; `Position.reserved_qty`; `SettlementLot`; `OrderReservation`; `Order.research_case_id`, `decision_entry_id`, `quote_snapshot_id`, `idempotency_key`, `confirmed_at`.

- [ ] **Step 1: Write migration invariants**

```python
def test_operation_schema_has_reservations(migrated_engine):
    account_cols = {c["name"] for c in inspect(migrated_engine).get_columns("accounts")}
    order_cols = {c["name"] for c in inspect(migrated_engine).get_columns("orders")}
    assert "reserved_cash" in account_cols
    assert {"research_case_id", "decision_entry_id", "quote_snapshot_id",
            "idempotency_key", "confirmed_at"} <= order_cols
```

- [ ] **Step 2: Run migration test**

Run: `cd backend && python -m pytest tests/test_operation_models.py -q`

Expected: FAIL because fields/tables are absent.

- [ ] **Step 3: Implement schema with financial invariants**

Use numeric columns with four decimal places for money and integer share quantities. `SettlementLot` stores trade ID, acquired date, total quantity, remaining quantity, and `sellable_on`. `OrderReservation` has exactly one of `cash_amount` or `qty`; its state is `ACTIVE/RELEASED/CONSUMED`. Add unique constraints for `orders.idempotency_key` and one active reservation per order. Backfill existing rows with zero reservations and nullable research linkage; require linkage for all newly confirmed orders in the service.

- [ ] **Step 4: Upgrade and verify**

Run: `cd backend && alembic upgrade head && python -m pytest tests/test_operation_models.py -q`

Expected: PASS and existing account/order rows remain readable.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models backend/migrations/versions/20260721_03_reliable_operations.py backend/tests/test_operation_models.py
git commit -m "feat: add paper operation ledger primitives"
```

### Task 2: Encode A-share execution rules as pure functions

**Files:**
- Create: `backend/app/engine/ashare_rules.py`
- Modify: `backend/app/engine/matching.py`
- Create: `backend/tests/test_ashare_rules.py`
- Modify: `backend/tests/test_matching.py`

**Interfaces:**
- Consumes: symbol, board, ST status, previous close, quote timestamp, order side/type/quantity/price.
- Produces: `validate_order_rules(OrderIntent, InstrumentState, now) -> RuleDecision`; price-time matching result.

- [ ] **Step 1: Add boundary tests**

```python
@pytest.mark.parametrize("symbol,limit_pct", [("600000", .10), ("300001", .20), ("688001", .20)])
def test_board_price_limits(symbol, limit_pct):
    state = InstrumentState(symbol=symbol, prev_close=10, is_st=False, suspended=False)
    assert price_limits(state) == (round(10 * (1-limit_pct), 2), round(10 * (1+limit_pct), 2))

def test_buy_requires_board_lot():
    decision = validate_order_rules(intent(qty=150, side="BUY"), normal_state(), NOW)
    assert decision.code == "INVALID_BOARD_LOT"

def test_stale_quote_is_rejected():
    decision = validate_order_rules(intent(), normal_state(quote_ts=NOW-timedelta(seconds=31)), NOW)
    assert decision.code == "STALE_QUOTE"
```

- [ ] **Step 2: Run rule tests**

Run: `cd backend && python -m pytest tests/test_ashare_rules.py tests/test_matching.py -q`

Expected: FAIL because rule types/functions are absent.

- [ ] **Step 3: Implement deterministic rules**

```python
@dataclass(frozen=True)
class RuleDecision:
    allowed: bool
    code: str
    message: str
    lower_limit: Decimal | None = None
    upper_limit: Decimal | None = None
```

Reject unsupported symbols, buys not divisible by 100, sells above sellable quantity, suspended securities, prices outside daily limits, quotes older than configured 30 seconds, nonpositive prices/quantities, and missing previous close. Apply 5% limits to ST securities, 10% to normal main-board securities, and 20% to ChiNext/STAR; reject instruments flagged as newly listed or price-limit-exempt until trustworthy instrument metadata explicitly supplies their rule. Permit odd-lot sell only when closing the full remaining position. Market simulation fills at current quote; limit simulation fills at the better of current quote and limit, never at a worse price than the user specified.

- [ ] **Step 4: Run pure engine tests**

Run: `cd backend && python -m pytest tests/test_ashare_rules.py tests/test_matching.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/engine/ashare_rules.py backend/app/engine/matching.py backend/tests/test_ashare_rules.py backend/tests/test_matching.py
git commit -m "feat: enforce A share paper execution rules"
```

### Task 3: Implement cash/quantity reservations and T+1 lots

**Files:**
- Modify: `backend/app/services/position_service.py`
- Create: `backend/app/services/reservation_service.py`
- Create: `backend/app/services/settlement_service.py`
- Create: `backend/tests/test_reservation_service.py`
- Create: `backend/tests/test_settlement_service.py`

**Interfaces:**
- Consumes: accepted pending order and fee estimate.
- Produces: `reserve_for_order(order, estimated_price) -> OrderReservation`; `release(order_id)`; `consume(order_id)`; `sellable_qty(account_id, symbol, on_date) -> int`.

- [ ] **Step 1: Write reservation and T+1 tests**

```python
def test_pending_buy_reserves_principal_and_max_fee(db_session, account, order):
    reservation = ReservationService(db_session).reserve_for_order(order, Decimal("10.00"))
    assert reservation.cash_amount == Decimal("1005.00")
    assert account.cash - account.reserved_cash == Decimal("998995.00")

def test_today_buy_not_sellable(db_session, filled_buy):
    svc = SettlementService(db_session, calendar)
    assert svc.sellable_qty(filled_buy.account_id, filled_buy.symbol, filled_buy.filled_at.date()) == 0
    assert svc.sellable_qty(filled_buy.account_id, filled_buy.symbol, calendar.shift(filled_buy.filled_at.date(), 1)) == 100
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `cd backend && python -m pytest tests/test_reservation_service.py tests/test_settlement_service.py -q`

Expected: FAIL because services are missing.

- [ ] **Step 3: Implement transactional reservation rules**

Available cash is `cash - reserved_cash`; available shares are matured lot remainder minus active sell reservations. Pending buys reserve limit notional plus worst-case configured fees; pending sells reserve quantity. Cancel/reject releases once; fill consumes once. Buying creates a lot sellable on the next trading session. Selling consumes oldest sellable lots first and updates aggregate position quantity in the same transaction.

- [ ] **Step 4: Verify double-release and oversubscription protection**

Run: `cd backend && python -m pytest tests/test_reservation_service.py tests/test_settlement_service.py -q`

Expected: PASS, including two competing orders where only the first can reserve the same funds/shares.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/position_service.py backend/app/services/reservation_service.py backend/app/services/settlement_service.py backend/tests/test_reservation_service.py backend/tests/test_settlement_service.py
git commit -m "feat: reserve paper cash and T plus one lots"
```

### Task 4: Add explicit preview and confirmation commands

**Files:**
- Rewrite: `backend/app/services/order_service.py`
- Create: `backend/app/models/order_preview.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/20260721_03b_order_previews.py`
- Modify: `backend/app/schemas/order.py`
- Create: `backend/tests/test_order_confirmation.py`

**Interfaces:**
- Consumes: active research case, latest decision, fresh quote, rule engine, reservation service.
- Produces: `preview(OrderPreviewRequest) -> OrderPreview`; `confirm(preview_id, confirmation_token, idempotency_key) -> PlaceOrderResult`.

- [ ] **Step 1: Specify manual-confirmation guarantees**

```python
def test_preview_does_not_create_order(db_session, service, request):
    preview = service.preview(request)
    assert preview.confirmation_token
    assert db_session.scalar(select(func.count(Order.id))) == 0

def test_confirm_is_idempotent(service, preview):
    first = service.confirm(preview.id, preview.confirmation_token, "ui-123")
    second = service.confirm(preview.id, preview.confirmation_token, "ui-123")
    assert second.order.id == first.order.id

def test_expired_preview_cannot_confirm(service, expired_preview):
    with pytest.raises(DomainError, match="PREVIEW_EXPIRED"):
        service.confirm(expired_preview.id, expired_preview.confirmation_token, "ui-124")
```

- [ ] **Step 2: Run confirmation tests**

Run: `cd backend && python -m pytest tests/test_order_confirmation.py -q`

Expected: FAIL against the current one-step `place()` method.

- [ ] **Step 3: Implement preview/confirm transaction**

Create and apply the `order_previews` migration. Preview expires after 60 seconds and stores case ID, decision ID, intent, quote snapshot ID/time, fee estimate, limit bounds, and a random hashed token. Confirm re-reads case state, quote freshness, funds/shares, and rules; inserts order and reservation, attempts immediate matching, and applies trade/cash/lot changes atomically. Remove direct public use of `OrderService.place`; scheduler may only call `scan_pending_orders`.

- [ ] **Step 4: Run confirmation and existing order tests**

Run: `cd backend && alembic upgrade head && python -m pytest tests/test_order_confirmation.py tests/test_order_service.py -q`

Expected: PASS after adapting existing tests to preview then confirm.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/order_service.py backend/app/models/order_preview.py backend/app/models/__init__.py backend/migrations/versions/20260721_03b_order_previews.py backend/app/schemas/order.py backend/tests/test_order_confirmation.py backend/tests/test_order_service.py
git commit -m "feat: require manual paper order confirmation"
```

### Task 5: Harden SQLite transaction and pending-order scanning

**Files:**
- Modify: `backend/app/db/base.py`
- Modify: `backend/app/jobs/scheduler.py`
- Modify: `backend/app/services/order_service.py`
- Create: `backend/tests/test_order_concurrency.py`

**Interfaces:**
- Consumes: `SessionLocal`, pending orders, fresh quote map.
- Produces: serialized write transactions with bounded busy timeout; `scan_pending_orders(quotes) -> ScanSummary`.

- [ ] **Step 1: Write concurrency recovery test**

```python
def test_two_confirms_cannot_overspend(file_db, account, previews):
    results = run_in_two_threads(lambda p: confirm_in_new_session(p), previews)
    assert sum(r.accepted for r in results) == 1
    refreshed = load_account(file_db, account.id)
    assert refreshed.cash >= 0 and refreshed.reserved_cash >= 0
```

- [ ] **Step 2: Run against file-backed SQLite**

Run: `cd backend && python -m pytest tests/test_order_concurrency.py -q`

Expected: FAIL by oversubscription or `database is locked` before hardening.

- [ ] **Step 3: Configure and serialize writes**

Enable SQLite WAL, foreign keys, and a 5000 ms busy timeout on connect. Begin financial commands with `BEGIN IMMEDIATE`; catch lock timeout and return domain code `LEDGER_BUSY` without partial writes. The scanner processes one order per short transaction in stable creation order, skips stale quotes, and returns counts for filled, pending, stale, and failed.

- [ ] **Step 4: Run concurrency suite repeatedly**

Run: `cd backend && python -m pytest tests/test_order_concurrency.py -q --count=10`

Expected: all repetitions pass; install `pytest-repeat>=0.9.3` in test dependencies if the environment lacks `--count`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/base.py backend/app/jobs/scheduler.py backend/app/services/order_service.py backend/requirements.txt backend/tests/test_order_concurrency.py
git commit -m "fix: make paper ledger writes atomic"
```

### Task 6: Expose single-account operation APIs

**Files:**
- Modify: `backend/app/api/orders.py`
- Modify: `backend/app/api/accounts.py`
- Create: `backend/app/services/bootstrap_service.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_operations_api.py`

**Interfaces:**
- Consumes: preview/confirm services and account overview.
- Produces: `POST /api/orders/preview`; `POST /api/orders/confirm`; single `GET /api/account`; orders/trades with case attribution.

- [ ] **Step 1: Add API contract tests**

```python
def test_operation_requires_case_and_two_calls(client, active_case):
    preview = client.post("/api/orders/preview", json=order_payload(active_case.id))
    assert preview.status_code == 200
    assert client.get("/api/orders").json() == []
    confirmed = client.post("/api/orders/confirm", json={
        "preview_id": preview.json()["id"],
        "confirmation_token": preview.json()["confirmation_token"],
        "idempotency_key": "browser-command-1"})
    assert confirmed.status_code == 201
    assert confirmed.json()["order"]["research_case_id"] == active_case.id
```

- [ ] **Step 2: Run API tests**

Run: `cd backend && python -m pytest tests/test_operations_api.py -q`

Expected: FAIL until routes are changed.

- [ ] **Step 3: Implement single-account bootstrap and routes**

At startup, create exactly one account named `个人模拟账户` with configured initial cash only when no account exists; if multiple legacy accounts exist, expose a health warning and require a one-time selection migration, not silent deletion. Remove account creation/switching from the normal UI API. Return available/reserved cash and total/sellable/reserved quantity.

- [ ] **Step 4: Run API tests**

Run: `cd backend && python -m pytest tests/test_operations_api.py -q`

Expected: PASS; old direct `POST /api/orders` returns 410 with migration guidance.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/orders.py backend/app/api/accounts.py backend/app/services/bootstrap_service.py backend/app/main.py backend/tests/test_operations_api.py
git commit -m "feat: expose confirmed single account operations"
```

### Task 7: Build the research-linked operation interface

**Files:**
- Create: `frontend/src/pages/OperationsPage.tsx`
- Create: `frontend/src/components/operations/OrderPreviewDrawer.tsx`
- Create: `frontend/src/components/operations/ConfirmationPanel.tsx`
- Create: `frontend/src/components/operations/OperationHistory.tsx`
- Modify: `frontend/src/pages/ResearchCasesPage.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/stores/useStore.ts`

**Interfaces:**
- Consumes: Task 6 APIs.
- Produces: `previewOrder(payload)`, `confirmOrder(payload)`, operation history filters by case/symbol/status.

- [ ] **Step 1: Define preview and confirmation types**

```typescript
export interface OrderPreview {
  id: string;
  research_case_id: string;
  decision_entry_id: string;
  symbol: string;
  side: Side;
  qty: number;
  order_type: OrderType;
  requested_price: number | null;
  quote_price: number;
  quote_ts: string;
  estimated_fees: number;
  estimated_cash_effect: number;
  expires_at: string;
  confirmation_token: string;
}
```

- [ ] **Step 2: Run frontend build with new imports**

Run: `cd frontend && npm run build`

Expected: FAIL until the operation components and client calls exist.

- [ ] **Step 3: Implement explicit confirmation UX**

Only active case pages show “发起模拟操作”. Step one collects side/type/quantity/price; step two displays case thesis, latest decision, quote time/age, price limits, fee estimate, available cash/sellable shares, and a distinct “确认提交模拟委托” button. Disable it on expiry/stale quote and require a new preview. Generate one UUID idempotency key per confirm click and reuse it on network retry.

- [ ] **Step 4: Build and manually verify**

Run: `cd frontend && npm run build`

Expected: build succeeds; preview alone creates no order, double-click confirm creates one order, and history links back to the case.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/OperationsPage.tsx frontend/src/pages/ResearchCasesPage.tsx frontend/src/components/operations frontend/src/api/client.ts frontend/src/types/index.ts frontend/src/stores/useStore.ts
git commit -m "feat: add confirmed research linked operations ui"
```

### Task 8: Attribute execution outcomes and verify the ledger end to end

**Files:**
- Create: `backend/app/services/execution_review_service.py`
- Modify: `backend/app/services/review_service.py`
- Create: `backend/tests/test_execution_attribution.py`
- Create: `backend/tests/test_operations_e2e.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: case plan prices, confirmed orders, trades, market path, review result.
- Produces: `ExecutionAttribution` with planned-vs-filled price, missed operation, timing, fees, discipline flags.

- [ ] **Step 1: Write attribution and ledger acceptance tests**

```python
def test_execution_attribution_separates_model_and_fill(case, prediction, trade):
    result = ExecutionReviewService().calculate(case, prediction, [trade])
    assert result.model_return == prediction.median_return
    assert result.entry_slippage == pytest.approx((trade.price-case.planned_entry)/case.planned_entry)

def test_full_order_cycle_balances_ledger(client, active_case):
    buy = preview_and_confirm(client, active_case.id, "BUY", 100)
    assert buy["order"]["status"] == "FILLED"
    account = client.get("/api/account").json()
    assert account["cash"] + account["reserved_cash"] >= 0
    assert account["positions"][0]["sellable_qty"] == 0
```

- [ ] **Step 2: Run targeted tests**

Run: `cd backend && python -m pytest tests/test_execution_attribution.py tests/test_operations_e2e.py -q`

Expected: FAIL until attribution service is implemented.

- [ ] **Step 3: Implement attribution and documentation**

Calculate entry/exit slippage against case plan, total fees, holding sessions, whether invalidation/target was crossed, whether user operated, and discipline deviations. Add the result to review reads without altering automatic forecast outcomes. Document preview expiry, T+1, price limits, reservations, stale quote behavior, and recovery from `LEDGER_BUSY`.

- [ ] **Step 4: Run full phase checks**

Run: `cd backend && python -m pytest tests -q && cd ../frontend && npm run build`

Expected: all checks pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/execution_review_service.py backend/app/services/review_service.py backend/tests/test_execution_attribution.py backend/tests/test_operations_e2e.py README.md
git commit -m "test: verify reliable simulated operation ledger"
```
