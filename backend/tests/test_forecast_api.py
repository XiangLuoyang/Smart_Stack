"""预测历史 API 测试:按业务日倒序返回。"""
from __future__ import annotations


def test_forecast_history_is_newest_first(client, seeded_predictions):
    response = client.get("/api/forecasts/000001")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["business_date"] == "2026-07-21"
    assert data[0]["horizon_days"] == 10
    assert data[1]["business_date"] == "2026-07-20"


def test_forecast_history_empty_for_unknown_symbol(client, seeded_predictions):
    response = client.get("/api/forecasts/999999")
    assert response.status_code == 200
    assert response.json() == []