"""筛选 API 测试:历史运行列表与完整排名详情。"""
from __future__ import annotations


def test_get_run_returns_full_contract(client, seeded_run):
    resp = client.get(f"/api/screener/runs/{seeded_run.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 3
    assert data["success_count"] == 2
    assert data["failure_count"] == 1
    assert data["status"] == "PARTIAL"
    assert len(data["candidates"]) == 3
    assert len(data["top10"]) == 2
    assert data["candidates"][0]["rank"] == 1
    assert data["model_version"] == "historical-10d-baseline@1.0.0"
    assert data["data_cutoff"] is not None


def test_list_runs(client, seeded_run):
    resp = client.get("/api/screener/runs")
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) >= 1
    assert runs[0]["id"] == seeded_run.id


def test_get_run_not_found(client):
    resp = client.get("/api/screener/runs/nonexistent")
    assert resp.status_code == 404