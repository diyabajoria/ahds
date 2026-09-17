"""Section 10: every listed bad-input case must return 422 (or a clean 4xx),
never a 500."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").status_code == 200


def test_schedulers_list():
    r = client.get("/api/schedulers")
    assert r.status_code == 200
    assert "HYBRID" in r.json()["schedulers"]


def test_presets_list():
    r = client.get("/api/presets")
    assert r.status_code == 200
    assert len(r.json()["presets"]) == 8


def test_cylinder_out_of_range_rejected():
    r = client.post("/api/simulate", json={
        "scheduler": "FCFS",
        "disk": {"cylinders": 200, "initial_head": 500},
    })
    assert r.status_code == 422


def test_nonpositive_size_rejected():
    r = client.post("/api/simulate", json={
        "scheduler": "FCFS",
        "workload": {"oltp": {"n_requests": 10, "min_size_bytes": -1, "max_size_bytes": 100}},
    })
    assert r.status_code == 422


def test_rpm_zero_rejected():
    r = client.post("/api/simulate", json={"scheduler": "FCFS", "disk": {"rpm": 0}})
    assert r.status_code == 422


def test_empty_workload_rejected():
    r = client.post("/api/simulate", json={
        "scheduler": "FCFS",
        "workload": {
            "multimedia": {"n_streams": 0}, "oltp": {"n_requests": 0}, "olap": {"n_scans": 0},
        },
    })
    assert r.status_code == 422


def test_unknown_scheduler_rejected():
    r = client.post("/api/simulate", json={"scheduler": "NOT_A_SCHEDULER"})
    assert r.status_code == 422


def test_rt_fraction_out_of_range_rejected():
    r = client.post("/api/simulate", json={"scheduler": "HYBRID", "hybrid": {"rt_fraction": 1.5}})
    assert r.status_code == 422


def test_round_length_nonpositive_rejected():
    r = client.post("/api/simulate", json={"scheduler": "HYBRID", "hybrid": {"round_length_ms": 0}})
    assert r.status_code == 422


def test_malformed_csv_rejected():
    r = client.post("/api/trace/upload", files={"file": ("bad.csv", b"not,the,right,columns\n1,2,3,4", "text/csv")})
    assert r.status_code == 422


def test_wrong_extension_rejected():
    r = client.post("/api/trace/upload", files={"file": ("bad.txt", b"hello", "text/plain")})
    assert r.status_code == 422


def test_nonexistent_run_id_404():
    r = client.get("/api/results/does-not-exist")
    assert r.status_code == 404


def test_valid_simulate_smoke():
    r = client.post("/api/simulate", json={
        "scheduler": "HYBRID",
        "workload": {"multimedia": {"n_streams": 2}, "oltp": {"n_requests": 30}, "olap": {"n_scans": 2}},
    })
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body and "metrics" in body and "timeline_sample" in body
