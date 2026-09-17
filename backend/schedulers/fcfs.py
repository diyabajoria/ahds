from __future__ import annotations
from typing import List, Optional
from models.request import Request
from schedulers.base import Scheduler


class FCFS(Scheduler):
    name = "FCFS"

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        return min(pending, key=lambda r: (r.arrival_time, r.id))
