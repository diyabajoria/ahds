"""S15: the experiment/compare runner generates the workload once, then
passes a deepcopy to each scheduler — assert byte-identical input."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_compare_schedulers_see_identical_requests(monkeypatch):
    captured = []
    import simulation.orchestrator as orch
    real_run_one = orch.run_one

    def spy_run_one(cfg, requests=None, stream_periods=None):
        captured.append([r.to_dict() for r in requests])
        return real_run_one(cfg, requests=requests, stream_periods=stream_periods)

    monkeypatch.setattr(orch, "run_one", spy_run_one)
    monkeypatch.setattr("main.run_one", spy_run_one)

    body = {
        "schedulers": ["FCFS", "SSTF", "LOOK"],
        "workload": {"multimedia": {"n_streams": 1}, "oltp": {"n_requests": 20}, "olap": {"n_scans": 1}},
    }
    resp = client.post("/api/compare", json=body)
    assert resp.status_code == 200
    assert len(captured) == 3
    ids0 = [r["id"] for r in captured[0]]
    cyl0 = [r["cylinder"] for r in captured[0]]
    for snapshot in captured[1:]:
        assert [r["id"] for r in snapshot] == ids0
        assert [r["cylinder"] for r in snapshot] == cyl0
