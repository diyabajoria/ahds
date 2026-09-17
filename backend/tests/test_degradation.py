"""Lead-time-before-degradation: shape/sanity checks — every point must carry
real, non-placeholder numbers from an actual run."""
from models.simulation import SimulationConfig, SchedulerName
from models.workload import WorkloadConfig, MultimediaConfig, OLTPConfig, OLAPConfig
from simulation.degradation import compute_lead_time_before_degradation


def test_degradation_sweep_produces_real_points():
    base = SimulationConfig(
        scheduler=SchedulerName.HYBRID,
        workload=WorkloadConfig(multimedia=MultimediaConfig(n_streams=3), oltp=OLTPConfig(n_requests=80),
                                 olap=OLAPConfig(n_scans=3), seed=2),
    )
    result = compute_lead_time_before_degradation(
        base, [SchedulerName.SSTF, SchedulerName.SCAN], load_start=20, load_end=60, load_step=20,
    )
    assert len(result.points) == 3
    for p in result.points:
        assert 0.0 <= p.hybrid_miss_ratio <= 1.0
        assert 0.0 <= p.best_baseline_miss_ratio <= 1.0
        assert p.best_baseline in ("SSTF", "SCAN")
    assert isinstance(result.note, str) and len(result.note) > 0
