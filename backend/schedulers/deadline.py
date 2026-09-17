"""Linux-style Deadline I/O scheduler — added as a baseline per the review's
Objective 4 ("compare against ... Linux-style Deadline scheduling").

Real Linux's deadline scheduler keeps a sector-sorted queue (serviced in
sweep order, like C-LOOK) plus a per-operation FIFO expiry queue — reads get
a short expiry, writes a longer one, since read latency is user-visible more
often. Whenever the request at the head of the expiry FIFO has actually
expired, it jumps ahead of the sector-sorted order to bound worst-case
latency; otherwise it services from the sector-sorted queue exactly like
C-LOOK.

This is deliberately simpler than the four-queue real kernel implementation
(no per-op back-merge/front-merge, no fifo_batch) but preserves the property
that actually matters for this comparison: it is location-aware for
throughput AND still bounds worst-case per-request latency, unlike plain
C-LOOK — which is exactly the axis the review's comparison table cares
about ("Not aware of request origin beyond read/write" vs the classical
algorithms' "No" on starvation bounding).
"""
from __future__ import annotations
from typing import List, Optional
from models.request import Request, Operation
from schedulers.base import Scheduler
from models.simulation import Direction


class DEADLINE(Scheduler):
    name = "DEADLINE"

    def __init__(self, read_expire_ms: float = 100.0, write_expire_ms: float = 500.0,
                 direction: Direction = Direction.RIGHT):
        self.read_expire_ms = read_expire_ms
        self.write_expire_ms = write_expire_ms
        self.direction = direction  # fixed, C-LOOK-style circular sweep

    def reset(self) -> None:
        pass

    def _expire_for(self, r: Request) -> float:
        return self.read_expire_ms if r.operation == Operation.READ else self.write_expire_ms

    def _expired(self, pending: List[Request], now: float) -> Optional[Request]:
        candidates = [r for r in pending if (now - r.arrival_time) >= self._expire_for(r)]
        if not candidates:
            return None
        return min(candidates, key=lambda r: (r.arrival_time, r.id))

    def _ahead(self, pending: List[Request], head: int) -> List[Request]:
        if self.direction == Direction.RIGHT:
            return [r for r in pending if r.cylinder >= head]
        return [r for r in pending if r.cylinder <= head]

    def reposition_before_select(self, pending: List[Request], head: int, now: float) -> Optional[int]:
        if not pending or self._expired(pending, now) or self._ahead(pending, head):
            return None
        target = min(pending, key=lambda r: r.cylinder).cylinder if self.direction == Direction.RIGHT \
            else max(pending, key=lambda r: r.cylinder).cylinder
        if head != target:
            return target
        return None

    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        expired = self._expired(pending, now)
        if expired is not None:
            return expired
        ahead = self._ahead(pending, head)
        if not ahead:
            return None
        return min(ahead, key=lambda r: (abs(r.cylinder - head), r.id))
