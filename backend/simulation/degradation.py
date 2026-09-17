"""Lead-time-before-degradation — the review's Expected Outcome metric,
Section 10: "the load level (requests/second) at which the hybrid
scheduler's advantage over the best static baseline starts to shrink."

Implementation: sweep workload.load_intensity_pct, and at each load level
compute a single composite "advantage" score for HYBRID versus whichever
static baseline scores best at that load — advantage is defined as the
baseline's deadline-miss ratio minus HYBRID's (positive = HYBRID better).
The lead time is the load value at the last point where this advantage was
still non-decreasing relative to the previous point; past that point it is
shrinking. If it never shrinks across the swept range, that is reported
explicitly rather than guessed at — this is exactly the kind of "must not
just assert no exception" number the project's test suite (S9) insists on
for every metric.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from models.simulation import SimulationConfig, SchedulerName
from simulation.workload_builder import build_workload
from simulation.orchestrator import run_one


@dataclass
class DegradationPoint:
    load_pct: float
    hybrid_miss_ratio: float
    best_baseline: str
    best_baseline_miss_ratio: float
    advantage: float  # baseline_miss_ratio - hybrid_miss_ratio; positive = hybrid better


@dataclass
class DegradationResult:
    points: List[DegradationPoint]
    lead_time_load_pct: Optional[float]  # None if advantage never shrinks in the swept range
    note: str


def compute_lead_time_before_degradation(
    base: SimulationConfig,
    baseline_schedulers: List[SchedulerName],
    load_start: float = 20.0,
    load_end: float = 100.0,
    load_step: float = 10.0,
) -> DegradationResult:
    points: List[DegradationPoint] = []
    load = load_start
    while load <= load_end + 1e-9:
        cfg = base.model_copy(deep=True)
        cfg.workload.load_intensity_pct = load
        requests, stream_periods = build_workload(cfg.workload, cfg.disk)

        hybrid_cfg = cfg.model_copy(deep=True)
        hybrid_cfg.scheduler = SchedulerName.HYBRID
        _, hybrid_metrics, _ = run_one(hybrid_cfg, requests=requests, stream_periods=stream_periods)
        hybrid_miss = hybrid_metrics["multimedia"]["deadline_miss_ratio"]

        best_name, best_miss = None, None
        for sname in baseline_schedulers:
            base_cfg = cfg.model_copy(deep=True)
            base_cfg.scheduler = sname
            _, m, _ = run_one(base_cfg, requests=requests, stream_periods=stream_periods)
            miss = m["multimedia"]["deadline_miss_ratio"]
            if best_miss is None or miss < best_miss:
                best_miss, best_name = miss, sname.value

        points.append(DegradationPoint(
            load_pct=load, hybrid_miss_ratio=hybrid_miss,
            best_baseline=best_name, best_baseline_miss_ratio=best_miss,
            advantage=best_miss - hybrid_miss,
        ))
        load += load_step

    lead_time = None
    note = "advantage did not shrink anywhere in the swept load range"
    for i in range(1, len(points)):
        if points[i].advantage < points[i - 1].advantage - 1e-9:
            lead_time = points[i - 1].load_pct
            note = f"HYBRID's advantage over the best static baseline starts shrinking after {lead_time}% load"
            break

    return DegradationResult(points=points, lead_time_load_pct=lead_time, note=note)
