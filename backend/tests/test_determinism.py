"""Same seed + same config => byte-identical request lists and metrics (S16)."""
from models.workload import WorkloadConfig
from models.disk import DiskConfig
from simulation.workload_builder import build_workload
from models.simulation import SimulationConfig, SchedulerName
from simulation.orchestrator import run_one


def test_same_seed_same_workload():
    wcfg = WorkloadConfig(seed=123)
    disk = DiskConfig()
    reqs1, periods1 = build_workload(wcfg, disk)
    reqs2, periods2 = build_workload(wcfg, disk)
    assert len(reqs1) == len(reqs2)
    for a, b in zip(reqs1, reqs2):
        assert a.to_dict() == b.to_dict()
    assert periods1 == periods2


def test_same_seed_same_metrics():
    cfg = SimulationConfig(scheduler=SchedulerName.SSTF, workload=WorkloadConfig(seed=7))
    _, m1, _ = run_one(cfg)
    _, m2, _ = run_one(cfg)
    assert m1 == m2
