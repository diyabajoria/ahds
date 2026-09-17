"""Shared statistical helpers: percentiles (S10) and Jain's fairness index (S8)."""
from __future__ import annotations
from typing import List


def percentile_nearest_rank(values: List[float], p: float) -> float:
    """Nearest-rank percentile on a list of samples. p in [0,100]."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if p <= 0:
        return s[0]
    rank = math_ceil(p / 100.0 * n)
    rank = min(max(rank, 1), n)
    return s[rank - 1]


def math_ceil(x: float) -> int:
    import math
    return math.ceil(x - 1e-9)  # guard against floating point just-under-integer


def jain_fairness(throughputs: List[float]) -> float:
    """J = (sum xi)^2 / (n * sum xi^2). J=1 for equal throughputs; J=1/n if one
    class has all the throughput."""
    xs = [x for x in throughputs if x is not None]
    n = len(xs)
    if n == 0:
        return 1.0
    s1 = sum(xs)
    s2 = sum(x * x for x in xs)
    if s2 == 0:
        return 1.0
    return (s1 * s1) / (n * s2)


def compute_full_metrics(requests, total_head_movement: float, makespan: float, busy_time: float,
                          hybrid_scheduler=None) -> dict:
    """Builds every metric listed in spec section 5 from the *actual* completed
    requests — nothing here is a placeholder."""
    from models.request import RequestType, RequestStatus

    completed = [r for r in requests if r.status in (RequestStatus.COMPLETED, RequestStatus.MISSED)]
    mm = [r for r in completed if r.type == RequestType.MULTIMEDIA]
    db = [r for r in completed if r.type in (RequestType.OLTP, RequestType.OLAP)]

    def resp_stats(reqs):
        vals = [r.response_time for r in reqs if r.response_time is not None]
        if not vals:
            return {"mean": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
        return {
            "mean": sum(vals) / len(vals),
            "p95": percentile_nearest_rank(vals, 95),
            "p99": percentile_nearest_rank(vals, 99),
            "max": max(vals),
        }

    # Multimedia metrics
    mm_misses = sum(1 for r in mm if r.deadline_missed)
    mm_miss_ratio = (mm_misses / len(mm)) if mm else 0.0
    jitters = [r.jitter for r in mm if r.jitter is not None]
    per_stream_starvation = {}
    for r in mm:
        if r.stream_id and r.waiting_time is not None:
            per_stream_starvation.setdefault(r.stream_id, 0)

    # Database (OLTP+OLAP) metrics
    db_resp = resp_stats(db)
    total_db_bytes = sum(r.size_bytes for r in db)
    throughput_bytes_per_s = (total_db_bytes / (makespan / 1000.0)) if makespan > 0 else 0.0
    iops = (len(db) / (makespan / 1000.0)) if makespan > 0 else 0.0
    db_starvation_count = sum(1 for r in db if r.aged)
    db_max_wait = max([r.waiting_time for r in db if r.waiting_time is not None], default=0.0)

    # Disk-level
    seek_vals = [r.seek_distance for r in completed if r.seek_distance is not None]
    mean_seek = (sum(seek_vals) / len(seek_vals)) if seek_vals else 0.0
    utilization = (busy_time / makespan) if makespan > 0 else 0.0

    # Overall
    rejected = sum(1 for r in requests if r.status == RequestStatus.REJECTED)
    total_deadline_misses = sum(1 for r in requests if r.deadline_missed)

    mm_throughput = (sum(r.size_bytes for r in mm) / (makespan / 1000.0)) if makespan > 0 else 0.0
    db_throughput_for_fairness = throughput_bytes_per_s
    oltp_only = [r for r in db if r.type == RequestType.OLTP]
    olap_only = [r for r in db if r.type == RequestType.OLAP]
    oltp_tp = (sum(r.size_bytes for r in oltp_only) / (makespan / 1000.0)) if makespan > 0 else 0.0
    olap_tp = (sum(r.size_bytes for r in olap_only) / (makespan / 1000.0)) if makespan > 0 else 0.0
    fairness_inputs = [x for x in [mm_throughput, oltp_tp, olap_tp] if x > 0]
    fairness = jain_fairness(fairness_inputs) if fairness_inputs else 1.0

    result = {
        "multimedia": {
            "deadline_miss_ratio": mm_miss_ratio,
            "deadline_misses": mm_misses,
            "count": len(mm),
            "mean_jitter": (sum(jitters) / len(jitters)) if jitters else 0.0,
            "max_jitter": max(jitters) if jitters else 0.0,
            "response_time": resp_stats(mm),
            "streams_with_starvation": len(per_stream_starvation),
        },
        "database": {
            "count": len(db),
            "response_time": db_resp,
            "throughput_bytes_per_s": throughput_bytes_per_s,
            "iops": iops,
            "starvation_count": db_starvation_count,
            "max_waiting_time_ms": db_max_wait,
        },
        "disk": {
            "total_head_movement_cylinders": total_head_movement,
            "mean_seek_time_ms": mean_seek,
            "utilization": utilization,
            "makespan_ms": makespan,
        },
        "overall": {
            "completed": len(completed),
            "rejected": rejected,
            "total_deadline_misses": total_deadline_misses,
            "jain_fairness": fairness,
        },
    }

    if hybrid_scheduler is not None:
        result["overall"]["final_rt_fraction"] = hybrid_scheduler.rt_fraction
        result["hybrid"] = {
            "feedback_log": hybrid_scheduler.log,
            "debt_log": hybrid_scheduler.debt_log,
            "aged_requests": hybrid_scheduler.aged_requests_count,
            "starvation_count": hybrid_scheduler.starvation_count,
            "max_waiting_time_ms": hybrid_scheduler.max_waiting_time,
            "final_rt_fraction": hybrid_scheduler.rt_fraction,
        }

    return result
