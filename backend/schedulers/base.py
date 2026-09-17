"""Every scheduler implements this interface.

The engine owns the clock, the queue and the metrics. Schedulers own only the
selection policy.

select_next(pending, head, now) -> Request | None
    Given currently-pending (already-arrived) requests, pick the next one to
    service, or None if nothing is pending.

reposition_before_select(pending, head, now) -> int | None
    Optional. Some policies (SCAN, C-SCAN, C-LOOK) sometimes need the head to
    travel to a cylinder that carries no request of its own — SCAN walks all
    the way to the disk boundary before reversing; C-SCAN/C-LOOK jump back to
    the start of the sweep. Returning a cylinder tells the engine "move the
    head there first, as a pure seek with no data transfer, then ask me
    again" (the engine loops on this until it returns None). Default: no-op.

on_completion(request, now) -> None
    Optional hook, called right after a request completes. Only HYBRID uses
    this, to run its round/feedback/aging bookkeeping. Default: no-op.

reset() -> None
    Optional: clear internal state (direction, round counters, ...) between
    runs of the same scheduler instance. Default: no-op.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

from models.request import Request


class Scheduler(ABC):
    name: str = "BASE"

    @abstractmethod
    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        ...

    def reposition_before_select(self, pending: List[Request], head: int, now: float) -> Optional[int]:
        return None

    def on_completion(self, request: Request, now: float) -> None:
        return None

    def reset(self) -> None:
        return None
