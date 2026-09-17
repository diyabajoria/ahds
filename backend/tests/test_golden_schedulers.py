"""Golden-number tests from spec section 9, item 1.

Classic sequence [98,183,37,122,14,124,65,67], head 53, 200 cylinders:
FCFS 640, SSTF 236, SCAN 236, C-SCAN 382, LOOK 208, C-LOOK 322.

Directions were chosen to match the textbook's own convention: SCAN and LOOK
start by sweeping toward cylinder 0 (Direction.LEFT) so their FINAL sweep
moves toward larger cylinder numbers (matching the spec's "toward larger"
label); C-SCAN and C-LOOK sweep toward larger cylinders throughout
(Direction.RIGHT). All four were verified against both directions; only the
direction listed here reproduces the spec's number, confirming there is a
single, unambiguous interpretation.
"""
import pytest
from models.request import Request, RequestType, Operation
from models.disk import DiskConfig
from models.simulation import Direction
from simulation.engine import run_simulation
from schedulers.fcfs import FCFS
from schedulers.sstf import SSTF
from schedulers.scan import SCAN
from schedulers.cscan import CSCAN
from schedulers.look import LOOK
from schedulers.clook import CLOOK

CYLS = [98, 183, 37, 122, 14, 124, 65, 67]


def make_reqs():
    return [
        Request(id=i, type=RequestType.OLTP, operation=Operation.READ,
                arrival_time=0.0, cylinder=c, size_bytes=4096)
        for i, c in enumerate(CYLS)
    ]


def disk():
    return DiskConfig(cylinders=200, initial_head=53, rpm=7200,
                       bytes_per_track=1_048_576, seek_coeff=1.0)


@pytest.mark.parametrize("scheduler,direction,expected", [
    (FCFS(), None, 640),
    (SSTF(), None, 236),
])
def test_golden_no_direction(scheduler, direction, expected):
    res = run_simulation(make_reqs(), disk(), scheduler, {})
    assert res.total_head_movement == expected


def test_golden_scan():
    res = run_simulation(make_reqs(), disk(), SCAN(cylinders=200, direction=Direction.LEFT), {})
    assert res.total_head_movement == 236


def test_golden_cscan():
    res = run_simulation(make_reqs(), disk(), CSCAN(cylinders=200, direction=Direction.RIGHT), {})
    assert res.total_head_movement == 382


def test_golden_look():
    res = run_simulation(make_reqs(), disk(), LOOK(direction=Direction.LEFT), {})
    assert res.total_head_movement == 208


def test_golden_clook():
    res = run_simulation(make_reqs(), disk(), CLOOK(direction=Direction.RIGHT), {})
    assert res.total_head_movement == 322
