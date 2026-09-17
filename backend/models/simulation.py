"""Top-level simulation / hybrid / API request-response models."""
from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, field_validator, model_validator

from models.disk import DiskConfig
from models.workload import WorkloadConfig


class SchedulerName(str, Enum):
    FCFS = "FCFS"
    SSTF = "SSTF"
    SCAN = "SCAN"
    CSCAN = "CSCAN"
    LOOK = "LOOK"
    CLOOK = "CLOOK"
    EDF = "EDF"
    SCAN_EDF = "SCAN_EDF"
    DEADLINE = "DEADLINE"
    HYBRID = "HYBRID"


class Direction(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class HybridConfig(BaseModel):
    round_length_ms: float = 100.0
    rt_fraction: float = 0.5
    work_conserving: bool = True
    control_window_rounds: int = 5
    step: float = 0.05
    miss_high_threshold: float = 0.02
    miss_low_threshold: float = 0.0
    rt_min: float = 0.1
    rt_max: float = 0.9
    db_latency_threshold: Optional[float] = None  # None -> derive as 3x first-window p95
    aging_threshold_ms: float = 200.0
    max_aged_per_round: int = 1
    deadline_tolerance_ms: float = 5.0  # used by the RT (SCAN-EDF) sub-queue

    @field_validator("round_length_ms")
    @classmethod
    def _round(cls, v):
        if v <= 0:
            raise ValueError("round_length_ms must be > 0")
        return v

    @field_validator("rt_fraction")
    @classmethod
    def _rtf(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("rt_fraction must be in [0,1]")
        return v

    @field_validator("aging_threshold_ms")
    @classmethod
    def _age(cls, v):
        if v < 0:
            raise ValueError("aging_threshold_ms must be >= 0")
        return v

    @model_validator(mode="after")
    def _bounds(self):
        if not (0.0 <= self.rt_min < self.rt_max <= 1.0):
            raise ValueError("require 0 <= rt_min < rt_max <= 1")
        return self


class DeadlineSchedConfig(BaseModel):
    """Linux-style Deadline scheduler parameters (schedulers/deadline.py)."""
    read_expire_ms: float = 100.0
    write_expire_ms: float = 500.0

    @field_validator("read_expire_ms", "write_expire_ms")
    @classmethod
    def _pos(cls, v):
        if v <= 0:
            raise ValueError("expire times must be > 0")
        return v


class SimulationConfig(BaseModel):
    scheduler: SchedulerName
    disk: DiskConfig = DiskConfig()
    workload: WorkloadConfig = WorkloadConfig()
    hybrid: HybridConfig = HybridConfig()
    deadline_sched: DeadlineSchedConfig = DeadlineSchedConfig()
    direction: Direction = Direction.RIGHT  # initial sweep direction for SCAN/CSCAN/LOOK/CLOOK/SCAN-EDF/DEADLINE/Hybrid-BE
    stream_period_for_jitter: bool = True


class CompareRequest(BaseModel):
    schedulers: List[SchedulerName]
    disk: DiskConfig = DiskConfig()
    workload: WorkloadConfig = WorkloadConfig()
    hybrid: HybridConfig = HybridConfig()
    deadline_sched: DeadlineSchedConfig = DeadlineSchedConfig()
    direction: Direction = Direction.RIGHT

    @field_validator("schedulers")
    @classmethod
    def _nonempty(cls, v):
        if not v:
            raise ValueError("schedulers list must not be empty")
        return v


class SweepParam(BaseModel):
    name: str            # dotted path, e.g. "workload.load_intensity_pct"
    start: float
    end: float
    step: float

    @field_validator("step")
    @classmethod
    def _step(cls, v):
        if v == 0:
            raise ValueError("step must be nonzero")
        return v


class ExperimentRequest(BaseModel):
    base: SimulationConfig
    sweep: List[SweepParam]
    schedulers: List[SchedulerName]

    @field_validator("sweep")
    @classmethod
    def _nonempty(cls, v):
        if not v:
            raise ValueError("sweep list must not be empty")
        return v
