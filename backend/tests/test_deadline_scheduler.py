"""Linux-style Deadline scheduler: expired requests must jump the sector-sorted
queue; otherwise it behaves like C-LOOK."""
from models.request import Request, RequestType, Operation
from models.disk import DiskConfig
from models.simulation import Direction
from schedulers.deadline import DEADLINE


def _req(i, cyl, arrival, op=Operation.READ):
    return Request(id=i, type=RequestType.OLTP, operation=op, arrival_time=arrival,
                    cylinder=cyl, size_bytes=4096)


def test_expired_read_jumps_the_queue():
    sched = DEADLINE(read_expire_ms=50.0, write_expire_ms=500.0, direction=Direction.RIGHT)
    old_far = _req(0, 400, arrival=0.0)     # will have waited 100ms -> expired (>= 50ms)
    new_near = _req(1, 10, arrival=95.0)    # just arrived, very close to head
    chosen = sched.select_next([old_far, new_near], head=5, now=100.0)
    assert chosen.id == 0


def test_no_expiry_behaves_like_sector_sorted_sweep():
    sched = DEADLINE(read_expire_ms=1000.0, write_expire_ms=5000.0, direction=Direction.RIGHT)
    near = _req(0, 10, arrival=0.0)
    far = _req(1, 400, arrival=0.0)
    chosen = sched.select_next([near, far], head=5, now=1.0)
    assert chosen.id == 0  # nearest ahead, nothing expired
