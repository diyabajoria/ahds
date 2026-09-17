"""Multimedia stream workload generator.

Each stream has a bitrate, a fixed request_size, a derived period, and a
per-request deadline (arrival + deadline_slack_periods * period). Cylinder
walk is controlled by `sequentiality`: with that probability the next
request is cylinder+1, otherwise it jumps to a uniform-random cylinder.
"""
from __future__ import annotations
from typing import List, Tuple, Dict
import numpy as np

from models.request import Request, RequestType, Operation
from models.workload import MultimediaConfig
from models.disk import DiskConfig
from workloads.arrivals import generate_arrivals


def generate_multimedia(cfg: MultimediaConfig, disk: DiskConfig, rng: np.random.Generator,
                         id_start: int, n_requests_per_stream: int = 30,
                         load_scale: float = 1.0) -> Tuple[List[Request], Dict[str, float]]:
    requests: List[Request] = []
    stream_periods: Dict[str, float] = {}
    next_id = id_start

    for s in range(cfg.n_streams):
        stream_id = f"mm-{s}"
        period_ms = (cfg.request_size_bytes / cfg.bitrate_bytes_per_s) * 1000.0
        period_ms = period_ms / max(load_scale, 1e-6)
        stream_periods[stream_id] = period_ms

        rate_per_s = 1000.0 / period_ms
        arrivals = generate_arrivals(n_requests_per_stream, cfg.arrival_model, rate_per_s, rng)

        cylinder = int(rng.integers(0, disk.cylinders))
        for t in arrivals:
            if rng.random() < cfg.sequentiality:
                cylinder = min(cylinder + 1, disk.cylinders - 1)
            else:
                cylinder = int(rng.integers(0, disk.cylinders))

            deadline = t + cfg.deadline_slack_periods * period_ms
            requests.append(Request(
                id=next_id,
                type=RequestType.MULTIMEDIA,
                operation=Operation.READ,
                arrival_time=t,
                cylinder=cylinder,
                size_bytes=cfg.request_size_bytes,
                deadline=deadline,
                stream_id=stream_id,
                sequentiality=cfg.sequentiality,
            ))
            next_id += 1

    return requests, stream_periods
