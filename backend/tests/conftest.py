"""pytest 共享 fixture。"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from pathlib import Path

# 让 backend/app 和根目录 src 都能被导入
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# 测试用临时 SQLite
os.environ["DB_PATH"] = str(PROJECT_ROOT / "data" / "test_smartstack.db")

import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base, upgrade_database


@pytest.fixture
def db_session():
    """每个测试用独立的内存 SQLite。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def migrated_engine(tmp_path, monkeypatch):
    """在临时 SQLite 文件上运行 Alembic 迁移,返回已迁移的引擎。"""
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    monkeypatch.setenv("DB_URL", url)
    get_settings.cache_clear()
    upgrade_database(url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    try:
        yield engine
    finally:
        engine.dispose()
        get_settings.cache_clear()


@pytest.fixture
def client(db_session):
    """绑定测试会话的 FastAPI TestClient(跳过 lifespan,避免启动调度器)。"""
    from fastapi.testclient import TestClient

    from app.api.deps import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------- 筛选管线 fake ----------------


class FakeScreeningPipeline:
    """可控筛选管线:返回预设的冻结批次与预测快照。"""

    def __init__(self, batch_id, model_id, predictions, failures):
        self.batch_id = batch_id
        self.model_id = model_id
        self._predictions = predictions
        self._failures = failures

    def freeze(self, business_date):
        from app.services.market_data_service import FrozenMarketBatch

        return FrozenMarketBatch(
            batch_id=self.batch_id,
            universe_snapshot_id="",
            valid_symbols=tuple(self._predictions.keys()),
            failures=dict(self._failures),
        )

    def predict(self, frozen, model_version_id, symbol):
        return self._predictions[symbol]


def _make_prediction(db, batch_id, model_id, symbol, excess):
    from app.models.forecast import PredictionSnapshot

    pred = PredictionSnapshot(
        business_date=date(2026, 7, 21),
        symbol=symbol,
        model_version_id=model_id,
        market_data_batch_id=batch_id,
        horizon_days=10,
        p_up=0.4,
        p_flat=0.2,
        p_down=0.4,
        median_return=0.01,
        lower_return=-0.03,
        upper_return=0.05,
        expected_excess_return=excess,
        expected_mfe=0.04,
        expected_mae=-0.02,
        state="PENDING",
    )
    db.add(pred)
    db.flush()
    return pred


@pytest.fixture
def screening_pipeline(db_session):
    """构造一个批次 + 模型 + 2 个成功预测 + 1 个 STALE_DATA 失败。"""
    from app.models.forecast import MarketDataBatch, ModelVersion

    batch = MarketDataBatch(
        business_date=date(2026, 7, 21),
        source="fake",
        cutoff_time=datetime(2026, 7, 21, 15, 0),
        status="SUCCESS",
        row_count=260,
        checksum="0" * 64,
        failures_json="{}",
        universe_snapshot_id=None,
    )
    db_session.add(batch)
    db_session.flush()

    model = ModelVersion(name="historical-10d-baseline", version="1.0.0")
    db_session.add(model)
    db_session.flush()

    pred1 = _make_prediction(db_session, batch.id, model.id, "000001", excess=0.05)
    pred2 = _make_prediction(db_session, batch.id, model.id, "600000", excess=0.02)
    db_session.commit()

    return FakeScreeningPipeline(
        batch_id=batch.id,
        model_id=model.id,
        predictions={"000001": pred1, "600000": pred2},
        failures={"000002": "STALE_DATA"},
    )


@pytest.fixture
def seeded_run(db_session, screening_pipeline):
    from app.services.screener_service import ScreenerService

    return ScreenerService(db_session, screening_pipeline).run(
        date(2026, 7, 21), screening_pipeline.model_id
    )