from models.request import Request, RequestType, Operation
from models.disk import DiskConfig
from simulation.engine import run_simulation
from schedulers.edf import EDF
from schedulers.scan_edf import SCAN_EDF


def _req(i, cyl, deadline, arrival=0.0):
    return Request(id=i, type=RequestType.MULTIMEDIA, operation=Operation.READ,
                    arrival_time=arrival, cylinder=cyl, size_bytes=4096, deadline=deadline)


def test_edf_nondecreasing_deadlines():
    disk = DiskConfig(cylinders=200, initial_head=0)
    reqs = [_req(0, 150, 50), _req(1, 10, 10), _req(2, 90, 30), _req(3, 5, 20)]
    res = run_simulation(reqs, disk, EDF(), {})
    order = [r for r in res.requests]
    order.sort(key=lambda r: r.start_service_time)
    deadlines = [r.deadline for r in order]
    assert deadlines == sorted(deadlines)


def test_scan_edf_differs_from_edf():
    """Construct a case where two requests share (near-)identical deadlines but
    are far apart in cylinder space, while a third is close to the head.
    EDF (deadline only) and SCAN-EDF (deadline group -> nearest) must pick a
    different first request."""
    disk = DiskConfig(cylinders=200, initial_head=50)
    # two requests with the same deadline, one far, one is nearer to head
    reqs = [
        _req(0, 5, 100.0),     # far from head=50, earliest deadline set exactly equal
        _req(1, 51, 100.5),    # very close to head, deadline within 5ms tolerance of the earliest
    ]
    edf_first = EDF().select_next(reqs, head=50, now=0.0)
    scan_edf_first = SCAN_EDF(deadline_tolerance_ms=5.0).select_next(reqs, head=50, now=0.0)
    assert edf_first.id == 0          # EDF: strictly earliest deadline wins
    assert scan_edf_first.id == 1     # SCAN-EDF: within tolerance, nearest to head wins
    assert edf_first.id != scan_edf_first.id
