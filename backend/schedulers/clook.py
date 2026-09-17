from __future__ import annotations
from typing import List, Optional
from models.request import Request
from schedulers.base import Scheduler
from models.simulation import Direction


class CLOOK(Scheduler):
    """Circular LOOK: sweeps one direction; when nothing pending remains
    ahead, jumps directly to the nearest extreme pending request on the other
    side and continues in the same direction — never reverses."""
    name = "CLOOK"

    def __init__(self, direction: Direction = Direction.RIGHT):
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
        target = min(pending, key=lambda r: r.cylinder).cylinder if self.direction == Direction.RIGHT \
            else max(pending, key=lambda r: r.cylinder).cylinder
        if head != target:
            return target
        return None

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        ahead = self._ahead(pending, head)
        if not ahead:
            return None
        return min(ahead, key=lambda r: (abs(r.cylinder - head), r.id))
