"""The discrete-event simulation engine — S1-S3, S6-S7.

The engine owns the clock, the pending queue, and all metric bookkeeping.
Schedulers only choose which request to serve next. This file never
hardcodes a metric: every number below is derived from requests actually
run through compute_service_time.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from models.disk import DiskConfig, DiskType
from models.request import Request, RequestStatus
from schedulers.base import Scheduler
from simulation.disk_model import compute_service_time, seek_time_ms


@dataclass
class TimelineEvent:
    time: float
    head: int
    request_id: Optional[int]
    event_type: str  # "reposition" | "service"


@dataclass
class EngineResult:
    requests: List[Request]
    timeline: List[TimelineEvent]
    total_head_movement: float
    makespan: float
    busy_time: float
    first_arrival: float
    last_completion: float


def run_simulation(
    requests: List[Request],
    disk: DiskConfig,
    scheduler: Scheduler,
    stream_periods: Optional[Dict[str, float]] = None,
) -> EngineResult:
    stream_periods = stream_periods or {}
    scheduler.reset()

    all_reqs = sorted(requests, key=lambda r: (r.arrival_time, r.id))
    pending: List[Request] = []
    arrival_ptr = 0
    n_total = len(all_reqs)

    clock = 0.0
    head = disk.initial_head
    total_head_movement = 0.0
    busy_time = 0.0
    timeline: List[TimelineEvent] = []
    last_completion_by_stream: Dict[str, float] = {}

    if all_reqs:
        first_arrival = all_reqs[0].arrival_time
        clock = first_arrival
    else:
        first_arrival = 0.0

    def pull_arrivals():
        # all_reqs is sorted by arrival_time, so a single advancing pointer
        # (rather than rescanning the whole remaining list every call) keeps
        # this O(1) amortized instead of O(n) per call.
        nonlocal arrival_ptr
        while arrival_ptr < n_total and all_reqs[arrival_ptr].arrival_time <= clock:
            pending.append(all_reqs[arrival_ptr])
            arrival_ptr += 1

    pull_arrivals()
    last_completion = clock
    guard = 0
    GUARD_MAX = 5_000_000

    while arrival_ptr < n_total or pending:
        guard += 1
        if guard > GUARD_MAX:
            raise RuntimeError("engine safety guard tripped — possible infinite loop")

        if not pending:
            # S3: idle -> jump the clock forward to the next arrival
            clock = all_reqs[arrival_ptr].arrival_time
            pull_arrivals()
            continue

        # reposition loop (SCAN boundary walk, C-SCAN/C-LOOK jump) — pure seek, no service
        while True:
            target = scheduler.reposition_before_select(pending, head, clock)
            if target is None:
                break
            distance = abs(head - target)
            cost = 0.0 if disk.disk_type == DiskType.SSD else seek_time_ms(distance, disk)
            clock += cost
            total_head_movement += distance
            head = target
            timeline.append(TimelineEvent(time=clock, head=head, request_id=None, event_type="reposition"))
            pull_arrivals()

        req = scheduler.select_next(pending, head, clock)
        if req is None:
            # nothing selectable even though pending is non-empty (shouldn't
            # normally happen) — avoid a stall by forcing idle-jump if possible
            if arrival_ptr < n_total:
                clock = all_reqs[arrival_ptr].arrival_time
                pull_arrivals()
                continue
            break

        pending.remove(req)
        breakdown = compute_service_time(head, req.cylinder, req.size_bytes, disk)

        req.start_service_time = clock
        req.waiting_time = clock - req.arrival_time
        req.seek_distance = breakdown.seek_distance
        clock += breakdown.service_time
        req.service_time = breakdown.service_time
        req.completion_time = clock
        req.response_time = req.completion_time - req.arrival_time
        req.status = RequestStatus.COMPLETED

        total_head_movement += breakdown.seek_distance
        busy_time += breakdown.service_time
        head = req.cylinder

        if req.deadline is not None and req.completion_time > req.deadline:
            req.deadline_missed = True
            req.status = RequestStatus.MISSED

        if req.stream_id:
            period = stream_periods.get(req.stream_id)
            prev = last_completion_by_stream.get(req.stream_id)
            if prev is not None and period is not None:
                req.jitter = abs((req.completion_time - prev) - period)
            last_completion_by_stream[req.stream_id] = req.completion_time

        scheduler.on_completion(req, clock)
        timeline.append(TimelineEvent(time=clock, head=head, request_id=req.id, event_type="service"))
        last_completion = clock

        pull_arrivals()

    makespan = (last_completion - first_arrival) if all_reqs else 0.0
    return EngineResult(
        requests=all_reqs,
        timeline=timeline,
        total_head_movement=total_head_movement,
        makespan=makespan,
        busy_time=busy_time,
        first_arrival=first_arrival,
        last_completion=last_completion,
    )
