"""One-call orchestration: build workload -> build scheduler -> run engine ->
compute metrics. Used directly by the API and by the experiment runner."""
from __future__ import annotations
import copy
from typing import List

from models.simulation import SimulationConfig
from schedulers.hybrid import HYBRID
from simulation.workload_builder import build_workload
from simulation.engine import run_simulation
from simulation.factory import build_scheduler
from simulation.metrics import compute_full_metrics


def run_one(cfg: SimulationConfig, requests=None, stream_periods=None):
    if requests is None:
        requests, stream_periods = build_workload(cfg.workload, cfg.disk)
    else:
        requests = copy.deepcopy(requests)
        stream_periods = stream_periods or {}

    scheduler = build_scheduler(cfg.scheduler, cfg.disk.cylinders, cfg.direction, cfg.hybrid, cfg.deadline_sched)
    engine_result = run_simulation(requests, cfg.disk, scheduler, stream_periods)

    hybrid_sched = scheduler if isinstance(scheduler, HYBRID) else None
    metrics = compute_full_metrics(
        engine_result.requests,
        engine_result.total_head_movement,
        engine_result.makespan,
        engine_result.busy_time,
        hybrid_scheduler=hybrid_sched,
    )
    return engine_result, metrics, scheduler
