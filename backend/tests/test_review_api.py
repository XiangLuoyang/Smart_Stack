"""结算 API 测试:触发结算与到期预测查询。"""
from __future__ import annotations


def test_settle_endpoint_returns_summary(client, due_prediction, bars):
    from app.api.reviews import get_bar_source
    from app.main import app

    app.dependency_overrides[get_bar_source] = lambda: bars
    try:
        resp = client.post("/api/reviews/settle", json={"as_of": "2026-08-04"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["settled"] == 1
        assert data["pending_data"] == 0
        assert data["as_of"] == "2026-08-04"
    finally:
        app.dependency_overrides.pop(get_bar_source, None)


def test_list_reviews_due(client, due_prediction, bars):
    resp = client.get("/api/reviews", params={"state": "DUE", "as_of": "2026-08-04"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "000001"
    assert data[0]["state"] == "PENDING"