from models.workload import WorkloadConfig, MultimediaConfig, OLTPConfig, OLAPConfig
from models.disk import DiskConfig
from simulation.workload_builder import build_workload
from models.request import RequestType


def test_generates_all_three_classes():
    wcfg = WorkloadConfig(
        multimedia=MultimediaConfig(n_streams=2),
        oltp=OLTPConfig(n_requests=50),
        olap=OLAPConfig(n_scans=3, scan_length_cylinders=10),
        seed=1,
    )
    disk = DiskConfig()
    reqs, periods = build_workload(wcfg, disk)
    types = {r.type for r in reqs}
    assert types == {RequestType.MULTIMEDIA, RequestType.OLTP, RequestType.OLAP}
    assert len(periods) == 2
    # arrivals sorted non-decreasing
    times = [r.arrival_time for r in reqs]
    assert times == sorted(times)
    # all cylinders in range
    for r in reqs:
        assert 0 <= r.cylinder < disk.cylinders
