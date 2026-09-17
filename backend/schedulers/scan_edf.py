from __future__ import annotations
from typing import List, Optional
from models.request import Request
from schedulers.base import Scheduler
from models.simulation import Direction


class SCAN_EDF(Scheduler):
    """Groups pending requests whose deadline falls within
    `deadline_tolerance_ms` of the earliest pending deadline, then within
    that group picks the one closest to the head in the current sweep
    direction. This lets it save seek distance among requests that are
    equally urgent, which plain EDF cannot do. Requests with no deadline are
    only served once nothing with a deadline is pending."""
    name = "SCAN_EDF"

    def __init__(self, deadline_tolerance_ms: float = 5.0, direction: Direction = Direction.RIGHT):
        self.deadline_tolerance_ms = deadline_tolerance_ms
        self.direction = direction

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        deadlined = [r for r in pending if r.deadline is not None]
        if not deadlined:
            return min(pending, key=lambda r: (r.arrival_time, r.id))

        earliest = min(r.deadline for r in deadlined)
        group = [r for r in deadlined if r.deadline - earliest <= self.deadline_tolerance_ms]

        def dist_in_direction(r: Request) -> tuple:
            d = abs(r.cylinder - head)
            ahead = (r.cylinder >= head) if self.direction == Direction.RIGHT else (r.cylinder <= head)
            return (0 if ahead else 1, d, r.id)

        return min(group, key=dist_in_direction)
