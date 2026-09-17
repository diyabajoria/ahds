from __future__ import annotations
from typing import List, Optional
from models.request import Request
from schedulers.base import Scheduler


class SSTF(Scheduler):
    """Shortest Seek Time First: always serve the pending request nearest to the head."""
    name = "SSTF"

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        return min(pending, key=lambda r: (abs(r.cylinder - head), r.arrival_time, r.id))
