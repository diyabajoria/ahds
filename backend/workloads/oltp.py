"""OLTP workload: small requests, Zipfian cylinder hot-spots, Poisson arrivals."""
from __future__ import annotations
from typing import List
import numpy as np

from models.request import Request, RequestType, Operation
from models.workload import OLTPConfig
from models.disk import DiskConfig
from workloads.arrivals import generate_arrivals


def generate_oltp(cfg: OLTPConfig, disk: DiskConfig, rng: np.random.Generator, id_start: int,
                   load_scale: float = 1.0) -> List[Request]:
    n = cfg.n_requests
    arrivals = generate_arrivals(n, cfg.arrival_model, cfg.arrival_rate_per_s * load_scale, rng)

    # Zipfian hot-spot cylinders: sample a small set of hot cylinders, then
    # assign each request to a rank drawn from a Zipf distribution over them.
    n_hotspots = max(1, min(20, disk.cylinders // 10))
    hotspots = rng.choice(disk.cylinders, size=n_hotspots, replace=False)

    ranks = rng.zipf(cfg.zipf_s, size=n)
    ranks = np.clip(ranks, 1, n_hotspots)

    sizes = rng.integers(cfg.min_size_bytes, cfg.max_size_bytes + 1, size=n)
    is_read = rng.random(n) < cfg.read_ratio

    requests: List[Request] = []
    for i in range(n):
        cylinder = int(hotspots[ranks[i] - 1])
        # small jitter around the hotspot so it's not literally always the same cylinder
        jitter = int(rng.integers(-3, 4))
        cylinder = int(np.clip(cylinder + jitter, 0, disk.cylinders - 1))
        requests.append(Request(
            id=id_start + i,
            type=RequestType.OLTP,
            operation=Operation.READ if is_read[i] else Operation.WRITE,
            arrival_time=float(arrivals[i]),
            cylinder=cylinder,
            size_bytes=int(sizes[i]),
        ))
    return requests
