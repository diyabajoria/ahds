from __future__ import annotations
from typing import List, Optional
from models.request import Request
from schedulers.base import Scheduler
from models.simulation import Direction


class SCAN(Scheduler):
    """Sweeps to the physical disk boundary before reversing — the boundary
    travel is charged as head movement even when nothing is pending there."""
    name = "SCAN"

    def __init__(self, cylinders: int, direction: Direction = Direction.RIGHT):
        self.cylinders = cylinders
        self.initial_direction = direction
        self.direction = direction

    def reset(self) -> None:
        self.direction = self.initial_direction

    def _ahead(self, pending: List[Request], head: int) -> List[Request]:
        if self.direction == Direction.RIGHT:
            return [r for r in pending if r.cylinder >= head]
        return [r for r in pending if r.cylinder <= head]

    def reposition_before_select(self, pending: List[Request], head: int, now: float) -> Optional[int]:
        if not pending or self._ahead(pending, head):
            return None
        boundary = (self.cylinders - 1) if self.direction == Direction.RIGHT else 0
        if head != boundary:
            return boundary
        # at the boundary, nothing pending further this way: reverse.
        self.direction = Direction.LEFT if self.direction == Direction.RIGHT else Direction.RIGHT
        return None

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        ahead = self._ahead(pending, head)
        if not ahead:
            return None  # reposition_before_select will have flipped direction; engine re-asks
        return min(ahead, key=lambda r: (abs(r.cylinder - head), r.id))
