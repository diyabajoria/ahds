"""Aging — S13. Helpers for the BE starvation-prevention sub-queue.

Aged requests jump ahead of the normal C-LOOK order within the BE turn, and
may be dispatched even when the BE budget is exhausted, up to
max_aged_per_round times per round (the documented starvation escape hatch).
"""
from __future__ import annotations
from typing import List, Optional
from models.request import Request


def mark_aged(be_pending: List[Request], now: float, aging_threshold_ms: float) -> List[Request]:
    """Mutates request.aged in place; returns the aged ones, oldest arrival first.

    `be_pending` is always a filter of the engine's `pending` list, which the
    engine only ever appends to in ascending arrival_time order and never
    reorders (only removes from) — so it is already sorted ascending by
    arrival_time, and since age = now - arrival_time is therefore monotonically
    *decreasing* through the list at any fixed `now`, we can stop at the first
    non-aged request instead of scanning (and re-sorting) the entire
    potentially-huge backlog on every single dispatch decision. This was a
    real O(n) per call bottleneck under sustained overload (see
    docs/architecture.md's performance note) — profiling a 30k-request
    saturated HYBRID run showed this one function consuming ~45% of total
    runtime before this fix."""
    aged = []
    for r in be_pending:
        if (now - r.arrival_time) >= aging_threshold_ms:
            r.aged = True
            aged.append(r)
        else:
            break
    return aged


def oldest_aged(be_pending: List[Request], now: float, aging_threshold_ms: float) -> Optional[Request]:
    aged = mark_aged(be_pending, now, aging_threshold_ms)
    return aged[0] if aged else None
