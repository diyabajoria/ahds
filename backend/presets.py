"""GET /api/presets — the demo buttons for the viva. Each is a fully
specified SimulationConfig plus a one-line description of what it's meant to
demonstrate."""
from __future__ import annotations
from models.simulation import SimulationConfig, SchedulerName, Direction, HybridConfig
from models.disk import DiskConfig, DiskType
from models.workload import WorkloadConfig, MultimediaConfig, OLTPConfig, OLAPConfig


def _cfg(**kw) -> SimulationConfig:
    return SimulationConfig(**kw)


PRESETS = {
    "video_streaming": {
        "description": "Multimedia-dominated load: shows deadline misses piling up under a plain "
                        "throughput scheduler (SSTF/LOOK) and HYBRID protecting them instead.",
        "config": _cfg(
            scheduler=SchedulerName.HYBRID,
            workload=WorkloadConfig(
                multimedia=MultimediaConfig(n_streams=8, bitrate_bytes_per_s=750_000),
                oltp=OLTPConfig(n_requests=80),
                olap=OLAPConfig(n_scans=2),
                load_intensity_pct=70,
            ),
        ),
    },
    "oltp_heavy": {
        "description": "Small, bursty, hot-spotted OLTP traffic dominates — good for comparing "
                        "SSTF/C-LOOK head-movement efficiency against FCFS.",
        "config": _cfg(
            scheduler=SchedulerName.HYBRID,
            workload=WorkloadConfig(
                multimedia=MultimediaConfig(n_streams=1),
                oltp=OLTPConfig(n_requests=400, zipf_s=1.3),
                olap=OLAPConfig(n_scans=1),
                load_intensity_pct=80,
            ),
        ),
    },
    "olap_heavy": {
        "description": "Large sequential scans dominate — shows why C-LOOK/SCAN beat SSTF once "
                        "requests are big and sequential rather than small and scattered.",
        "config": _cfg(
            scheduler=SchedulerName.HYBRID,
            workload=WorkloadConfig(
                multimedia=MultimediaConfig(n_streams=1),
                oltp=OLTPConfig(n_requests=40),
                olap=OLAPConfig(n_scans=15, scan_length_cylinders=60),
                load_intensity_pct=60,
            ),
        ),
    },
    "balanced_50_50": {
        "description": "Even RT:BE mix at moderate load — the baseline case for the comparison "
                        "trade-off chart.",
        "config": _cfg(
            scheduler=SchedulerName.HYBRID,
            workload=WorkloadConfig(load_intensity_pct=50),
        ),
    },
    "overloaded_disk": {
        "description": "Load intensity pushed to 100% — every scheduler degrades; shows HYBRID's "
                        "feedback controller reacting under saturation, and that it is NOT immune "
                        "to overload.",
        "config": _cfg(
            scheduler=SchedulerName.HYBRID,
            workload=WorkloadConfig(
                multimedia=MultimediaConfig(n_streams=10),
                oltp=OLTPConfig(n_requests=500),
                olap=OLAPConfig(n_scans=10),
                load_intensity_pct=100,
            ),
        ),
    },
    "deadline_stress": {
        "description": "Tight deadline slack on multimedia streams — stresses EDF/SCAN-EDF/HYBRID "
                        "against baselines that ignore deadlines entirely.",
        "config": _cfg(
            scheduler=SchedulerName.HYBRID,
            workload=WorkloadConfig(
                multimedia=MultimediaConfig(n_streams=6, deadline_slack_periods=1.1),
                oltp=OLTPConfig(n_requests=150),
                load_intensity_pct=75,
            ),
        ),
    },
    "starvation_stress": {
        "description": "Heavy RT pressure with a low aging threshold — demonstrates HYBRID's aging "
                        "escape hatch rescuing BE requests that would otherwise starve.",
        "config": _cfg(
            scheduler=SchedulerName.HYBRID,
            workload=WorkloadConfig(
                multimedia=MultimediaConfig(n_streams=10, bitrate_bytes_per_s=900_000),
                oltp=OLTPConfig(n_requests=200),
                load_intensity_pct=85,
            ),
            hybrid=HybridConfig(rt_fraction=0.8, aging_threshold_ms=80, rt_max=0.85),
        ),
    },
    "hdd_vs_ssd": {
        "description": "Same workload and scheduler, SSD disk model — shows seek-optimising "
                        "schedulers converging in performance once seek cost is gone.",
        "config": _cfg(
            scheduler=SchedulerName.HYBRID,
            disk=DiskConfig(disk_type=DiskType.SSD),
            workload=WorkloadConfig(load_intensity_pct=60),
        ),
    },
}


def list_presets():
    return [
        {"key": k, "description": v["description"], "config": v["config"].model_dump()}
        for k, v in PRESETS.items()
    ]


def get_preset(key: str) -> SimulationConfig:
    if key not in PRESETS:
        raise KeyError(key)
    return PRESETS[key]["config"]
