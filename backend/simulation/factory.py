"""Builds a fresh Scheduler instance from a SchedulerName + config."""
from __future__ import annotations
from models.simulation import SchedulerName, Direction, HybridConfig
from schedulers.fcfs import FCFS
from schedulers.sstf import SSTF
from schedulers.scan import SCAN
from schedulers.cscan import CSCAN
from schedulers.look import LOOK
from schedulers.clook import CLOOK
from schedulers.edf import EDF
from schedulers.scan_edf import SCAN_EDF
from schedulers.deadline import DEADLINE
from schedulers.hybrid import HYBRID
from models.simulation import DeadlineSchedConfig


def build_scheduler(name: SchedulerName, cylinders: int, direction: Direction, hybrid_cfg: HybridConfig,
                     deadline_cfg: DeadlineSchedConfig = None):
    deadline_cfg = deadline_cfg or DeadlineSchedConfig()
    if name == SchedulerName.FCFS:
        return FCFS()
    if name == SchedulerName.SSTF:
        return SSTF()
    if name == SchedulerName.SCAN:
        return SCAN(cylinders=cylinders, direction=direction)
    if name == SchedulerName.CSCAN:
        return CSCAN(cylinders=cylinders, direction=direction)
    if name == SchedulerName.LOOK:
        return LOOK(direction=direction)
    if name == SchedulerName.CLOOK:
        return CLOOK(direction=direction)
    if name == SchedulerName.EDF:
        return EDF()
    if name == SchedulerName.SCAN_EDF:
        return SCAN_EDF(deadline_tolerance_ms=hybrid_cfg.deadline_tolerance_ms, direction=direction)
    if name == SchedulerName.DEADLINE:
        return DEADLINE(read_expire_ms=deadline_cfg.read_expire_ms,
                         write_expire_ms=deadline_cfg.write_expire_ms, direction=direction)
    if name == SchedulerName.HYBRID:
        return HYBRID(cfg=hybrid_cfg, direction=direction)
    raise ValueError(f"unknown scheduler: {name}")
