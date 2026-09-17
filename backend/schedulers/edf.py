from __future__ import annotations
from typing import List, Optional
from models.request import Request
from schedulers.base import Scheduler


class EDF(Scheduler):
    """Earliest Deadline First. Requests with no deadline are only served
    when nothing with a deadline is pending, and are then served FCFS among
    themselves."""
    name = "EDF"

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        deadlined = [r for r in pending if r.deadline is not None]
        if deadlined:
            return min(deadlined, key=lambda r: (r.deadline, r.id))
        return min(pending, key=lambda r: (r.arrival_time, r.id))
