"""Arrival-time generators. All randomness flows through the single
numpy.random.Generator passed in — never global `random` or `np.random.*`
(S16). Same seed + same config => byte-identical results."""
from __future__ import annotations
from typing import List
import numpy as np

from models.workload import ArrivalModel


def generate_arrivals(n: int, model: ArrivalModel, rate_per_s: float, rng: np.random.Generator) -> List[float]:
    """Returns n arrival times in milliseconds, sorted ascending, starting near 0."""
    if n <= 0:
        return []
    if model == ArrivalModel.PERIODIC:
        period_ms = 1000.0 / rate_per_s if rate_per_s > 0 else 1000.0
        return [i * period_ms for i in range(n)]
    if model == ArrivalModel.POISSON:
        lam_per_ms = rate_per_s / 1000.0 if rate_per_s > 0 else 0.001
        inter = rng.exponential(1.0 / lam_per_ms, size=n)
        return list(np.cumsum(inter))
    # MANUAL falls back to evenly spaced arrivals; the caller is expected to
    # override via a trace upload in that case.
    period_ms = 1000.0 / rate_per_s if rate_per_s > 0 else 1000.0
    return [i * period_ms for i in range(n)]
