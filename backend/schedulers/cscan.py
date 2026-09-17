from __future__ import annotations
from typing import List, Optional
from models.request import Request
from schedulers.base import Scheduler
from models.simulation import Direction


class CSCAN(Scheduler):
    """Circular SCAN: always sweeps the same direction; on reaching the
    boundary it jumps directly back to the start of the sweep, charging that
    full jump distance, and continues — never reverses."""
    name = "CSCAN"

    def __init__(self, cylinders: int, direction: Direction = Direction.RIGHT):
        self.cylinders = cylinders
        self.direction = direction  # fixed for the whole run

    def reset(self) -> None:
        pass

    def _ahead(self, pending: List[Request], head: int) -> List[Request]:
        if self.direction == Direction.RIGHT:
            return [r for r in pending if r.cylinder >= head]
        return [r for r in pending if r.cylinder <= head]

    def reposition_before_select(self, pending: List[Request], head: int, now: float) -> Optional[int]:
        if not pending or self._ahead(pending, head):
            return None
        end = (self.cylinders - 1) if self.direction == Direction.RIGHT else 0
        start = 0 if self.direction == Direction.RIGHT else (self.cylinders - 1)
        if head != end:
            return end
        if head != start:
            return start
        return None

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        ahead = self._ahead(pending, head)
        if not ahead:
            return None
        return min(ahead, key=lambda r: (abs(r.cylinder - head), r.id))
