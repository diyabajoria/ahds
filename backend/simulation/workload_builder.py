"""Assembles MULTIMEDIA + OLTP + OLAP requests into one workload from a
WorkloadConfig, using a single seeded Generator for full determinism (S16)."""
from __future__ import annotations
from typing import List, Tuple, Dict
import numpy as np

from models.request import Request
from models.workload import WorkloadConfig
from models.disk import DiskConfig
from workloads.multimedia import generate_multimedia
from workloads.oltp import generate_oltp
from workloads.olap import generate_olap


def build_workload(cfg: WorkloadConfig, disk: DiskConfig) -> Tuple[List[Request], Dict[str, float]]:
    rng = np.random.default_rng(cfg.seed)
    load_scale = cfg.load_intensity_pct / 50.0  # 50% load_intensity == the configured base rates

    mm_reqs, stream_periods = generate_multimedia(cfg.multimedia, disk, rng, id_start=0, load_scale=load_scale)
    oltp_reqs = generate_oltp(cfg.oltp, disk, rng, id_start=len(mm_reqs), load_scale=load_scale)
    olap_reqs = generate_olap(cfg.olap, disk, rng, id_start=len(mm_reqs) + len(oltp_reqs), load_scale=load_scale)

    all_reqs = mm_reqs + oltp_reqs + olap_reqs
    all_reqs.sort(key=lambda r: (r.arrival_time, r.id))
    return all_reqs, stream_periods
