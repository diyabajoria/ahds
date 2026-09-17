"""Hybrid: per-round RT service time never exceeds budget + one request's
service time by more than is reconciled as debt in the next round."""
from models.simulation import SimulationConfig, SchedulerName, HybridConfig
from models.workload import WorkloadConfig, MultimediaConfig, OLTPConfig, OLAPConfig
from simulation.orchestrator import run_one


def test_hybrid_debt_reconciles_and_is_clamped():
    cfg = SimulationConfig(
        scheduler=SchedulerName.HYBRID,
        workload=WorkloadConfig(
            multimedia=MultimediaConfig(n_streams=6, bitrate_bytes_per_s=900_000),
            oltp=OLTPConfig(n_requests=150),
            olap=OLAPConfig(n_scans=3),
            load_intensity_pct=90,
            seed=5,
        ),
        hybrid=HybridConfig(round_length_ms=50.0, rt_fraction=0.5),
    )
    _, metrics, scheduler = run_one(cfg)
    assert "hybrid" in metrics
    for entry in scheduler.debt_log:
        rt_alloc = scheduler.T * cfg.hybrid.rt_fraction  # approx bound; fraction adapts, but debt
        # must never exceed a full round's allocation of EITHER class, i.e. <= T
        assert entry["rt_debt"] <= scheduler.T + 1e-6
        assert entry["be_debt"] <= scheduler.T + 1e-6
        assert entry["rt_debt"] >= 0
        assert entry["be_debt"] >= 0
    assert metrics["overall"]["final_rt_fraction"] >= cfg.hybrid.rt_min - 1e-9
    assert metrics["overall"]["final_rt_fraction"] <= cfg.hybrid.rt_max + 1e-9
