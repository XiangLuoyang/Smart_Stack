"""数据库迁移冒烟测试:确认预测基座 schema 已建立。"""
from sqlalchemy import inspect


def test_forecast_schema_exists(migrated_engine):
    tables = set(inspect(migrated_engine).get_table_names())
    assert {
        "market_data_batches",
        "daily_bars",
        "universe_snapshots",
        "trading_calendar",
        "model_versions",
        "screening_runs",
        "screening_candidates",
        "prediction_snapshots",
        "review_results",
    } <= tables