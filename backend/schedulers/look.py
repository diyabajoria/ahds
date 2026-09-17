from __future__ import annotations
from typing import List, Optional
from models.request import Request
from schedulers.base import Scheduler
from models.simulation import Direction


class LOOK(Scheduler):
    """Like SCAN but reverses at the extreme pending request rather than the
    physical disk boundary — no wasted travel."""
    name = "LOOK"

    def __init__(self, direction: Direction = Direction.RIGHT):
        self.initial_direction = direction
        self.direction = direction

    def reset(self) -> None:
        self.direction = self.initial_direction

    def _ahead(self, pending: List[Request], head: int) -> List[Request]:
        if self.direction == Direction.RIGHT:
            return [r for r in pending if r.cylinder >= head]
        return [r for r in pending if r.cylinder <= head]

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        ahead = self._ahead(pending, head)
        if ahead:
            return min(ahead, key=lambda r: (abs(r.cylinder - head), r.id))
        self.direction = Direction.LEFT if self.direction == Direction.RIGHT else Direction.RIGHT
        ahead2 = self._ahead(pending, head)
        if ahead2:
            return min(ahead2, key=lambda r: (abs(r.cylinder - head), r.id))
        return None
