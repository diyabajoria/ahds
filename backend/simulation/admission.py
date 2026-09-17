"""Admission control — S14.

Effective bandwidth accounts for per-request overhead (seek + rotation), not
just raw transfer rate. Only the RT share (rt_max) of effective bandwidth is
reservable for real-time streams.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List

from models.disk import DiskConfig
from simulation.disk_model import seek_time_ms, rotational_delay_ms, transfer_time_ms


@dataclass
class AdmissionResult:
    accepted: bool
    requested_bw: float
    reserved_before: float
    reserved_after: float
    usable_bw: float
    effective_bw: float
    reason: str


def estimate_avg_seek_ms(disk: DiskConfig) -> float:
    """Expected distance between two uniform-random cylinders is cylinders/3."""
    mean_distance = disk.cylinders / 3.0
    return seek_time_ms(mean_distance, disk)


def effective_bandwidth_bytes_per_ms(disk: DiskConfig, avg_request_bytes: float) -> float:
    avg_seek = estimate_avg_seek_ms(disk)
    rot = rotational_delay_ms(disk)
    xfer = transfer_time_ms(avg_request_bytes, disk)
    avg_request_ms = avg_seek + rot + xfer
    if avg_request_ms <= 0:
        return float("inf")
    return avg_request_bytes / avg_request_ms


def check_admission(
    disk: DiskConfig,
    avg_request_bytes: float,
    rt_max: float,
    reserved_bitrates: List[float],
    new_bitrate: float,
) -> AdmissionResult:
    effective_bw = effective_bandwidth_bytes_per_ms(disk, avg_request_bytes)
    usable_bw = effective_bw * rt_max
    reserved_before = sum(reserved_bitrates)
    reserved_after = reserved_before + new_bitrate
    accepted = reserved_after <= usable_bw
    reason = (
        f"reserved {reserved_after:.2f} B/ms <= usable {usable_bw:.2f} B/ms"
        if accepted
        else f"reserved {reserved_after:.2f} B/ms exceeds usable {usable_bw:.2f} B/ms"
    )
    return AdmissionResult(
        accepted=accepted,
        requested_bw=new_bitrate,
        reserved_before=reserved_before,
        reserved_after=reserved_after if accepted else reserved_before,
        usable_bw=usable_bw,
        effective_bw=effective_bw,
        reason=reason,
    )
