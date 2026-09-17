"""OLAP workload: occasional large sequential scans, low arrival rate."""
from __future__ import annotations
from typing import List
import numpy as np

from models.request import Request, RequestType, Operation
from models.workload import OLAPConfig
from models.disk import DiskConfig
from workloads.arrivals import generate_arrivals


def generate_olap(cfg: OLAPConfig, disk: DiskConfig, rng: np.random.Generator, id_start: int,
                   load_scale: float = 1.0) -> List[Request]:
    scan_arrivals = generate_arrivals(cfg.n_scans, cfg.arrival_model, cfg.arrival_rate_per_s * load_scale, rng)

    requests: List[Request] = []
    next_id = id_start
    scan_bytes = disk.bytes_per_track  # one "chunk" per cylinder step in the scan

    for scan_idx, t0 in enumerate(scan_arrivals):
        start_cyl = int(rng.integers(0, max(1, disk.cylinders - cfg.scan_length_cylinders)))
        # a scan is a burst of sequential reads, 1ms apart in arrival (they queue up)
        for k in range(cfg.scan_length_cylinders):
            requests.append(Request(
                id=next_id,
                type=RequestType.OLAP,
                operation=Operation.READ,
                arrival_time=float(t0) + k * 0.5,
                cylinder=min(start_cyl + k, disk.cylinders - 1),
                size_bytes=scan_bytes,
            ))
            next_id += 1
    return requests
