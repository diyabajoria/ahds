"""Construct starvation for a BE (OLTP) request under heavy RT load and
assert the aging escape hatch dispatches it before a nearer non-aged one."""
from models.request import Request, RequestType, Operation
from models.disk import DiskConfig
from models.simulation import HybridConfig, Direction
from schedulers.hybrid import HYBRID


def test_aged_request_dispatched_before_nearer_nonaged():
    cfg = HybridConfig(round_length_ms=100.0, rt_fraction=0.5, aging_threshold_ms=50.0,
                        max_aged_per_round=1)
    sched = HYBRID(cfg, direction=Direction.RIGHT)

    old_far = Request(id=0, type=RequestType.OLTP, operation=Operation.READ,
                       arrival_time=0.0, cylinder=500, size_bytes=4096)   # arrived long ago, far from head
    new_near = Request(id=1, type=RequestType.OLTP, operation=Operation.READ,
                        arrival_time=90.0, cylinder=1, size_bytes=4096)   # just arrived, right next to head

    now = 100.0  # old_far has been waiting 100ms >= aging_threshold(50ms) -> aged
    chosen = sched.select_next([old_far, new_near], head=0, now=now)
    assert chosen.id == 0
    assert old_far.aged is True
