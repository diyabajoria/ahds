"""Feature engineering for the workload classifier — spec section 8.3.

Turns each request's observable properties (nothing the classifier isn't
allowed to know: no peeking at the true label) into a numeric feature
vector:

- size_kb            — request size in KB (multimedia blocks: large/uniform; DB: small)
- inter_arrival_ms    — time since the previous request *on the same stream_id if any,
                        else the previous request overall* (steady for streaming, irregular for DB)
- lba_delta           — |cylinder - previous_request.cylinder| (small = sequential, large = random)
- sequential_flag     — 1.0 if lba_delta <= SEQ_THRESHOLD else 0.0 (derived from lba_delta)
- burstiness          — count of requests that arrived in the preceding BURST_WINDOW_MS
"""
from __future__ import annotations
from typing import List, Tuple
import numpy as np

from models.request import Request, RequestType

SEQ_THRESHOLD_CYLINDERS = 4
BURST_WINDOW_MS = 20.0

FEATURE_NAMES = ["size_kb", "inter_arrival_ms", "lba_delta", "sequential_flag", "burstiness"]


def extract_features(requests: List[Request]) -> Tuple[np.ndarray, np.ndarray]:
    """requests must be sorted by arrival_time. Returns (X, y) where y is
    1 for MULTIMEDIA and 0 for DATABASE (OLTP+OLAP merged, matching the
    review's two-class M vs D framing)."""
    ordered = sorted(requests, key=lambda r: (r.arrival_time, r.id))
    n = len(ordered)
    X = np.zeros((n, len(FEATURE_NAMES)), dtype=float)
    y = np.zeros(n, dtype=int)

    arrivals = [r.arrival_time for r in ordered]
    prev_cylinder = None
    prev_arrival = None

    for i, r in enumerate(ordered):
        size_kb = r.size_bytes / 1024.0
        inter_arrival = 0.0 if prev_arrival is None else max(0.0, r.arrival_time - prev_arrival)
        lba_delta = 0.0 if prev_cylinder is None else abs(r.cylinder - prev_cylinder)
        seq_flag = 1.0 if lba_delta <= SEQ_THRESHOLD_CYLINDERS else 0.0

        # burstiness: how many requests arrived in (arrival - BURST_WINDOW_MS, arrival]
        lo = r.arrival_time - BURST_WINDOW_MS
        # arrivals is sorted; count via searchsorted for O(log n) instead of a scan
        lo_idx = np.searchsorted(arrivals, lo, side="right")
        burstiness = float(i - lo_idx + 1)

        X[i] = [size_kb, inter_arrival, lba_delta, seq_flag, burstiness]
        y[i] = 1 if r.type == RequestType.MULTIMEDIA else 0

        prev_cylinder = r.cylinder
        prev_arrival = r.arrival_time

    return X, y
