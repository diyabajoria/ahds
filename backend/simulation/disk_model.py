"""Disk service-time arithmetic. S4 and S5 of the spec, implemented exactly.

seek_time        = f(|head - target_cylinder|)
rotational_delay = 0.5 * (60000 / RPM)
transfer_time    = (size_bytes / bytes_per_track) * (60000 / RPM)
service_time     = seek_time + rotational_delay + transfer_time

SSD mode: seek = 0, rotational_delay = 0, transfer_time = size_bytes / ssd_bandwidth_bytes_per_ms.
"""
from __future__ import annotations
import math
from dataclasses import dataclass

from models.disk import DiskConfig, DiskType, SeekModel


@dataclass
class ServiceTimeBreakdown:
    seek_time: float
    rotational_delay: float
    transfer_time: float
    service_time: float
    seek_distance: float


def seek_time_ms(distance: float, disk: DiskConfig) -> float:
    if distance == 0:
        return 0.0
    if disk.seek_model == SeekModel.LINEAR:
        return disk.seek_coeff * distance
    # REALISTIC: a + b*sqrt(d), seek = 0 when d == 0 (handled above)
    return disk.seek_a + disk.seek_b * math.sqrt(distance)


def rotational_delay_ms(disk: DiskConfig) -> float:
    return 0.5 * (60_000.0 / disk.rpm)


def transfer_time_ms(size_bytes: int, disk: DiskConfig) -> float:
    return (size_bytes / disk.bytes_per_track) * (60_000.0 / disk.rpm)


def compute_service_time(head: int, target_cylinder: int, size_bytes: int, disk: DiskConfig) -> ServiceTimeBreakdown:
    distance = abs(head - target_cylinder)
    if disk.disk_type == DiskType.SSD:
        seek = 0.0
        rot = 0.0
        xfer = size_bytes / disk.ssd_bandwidth
        return ServiceTimeBreakdown(seek, rot, xfer, seek + rot + xfer, distance)

    seek = seek_time_ms(distance, disk)
    rot = rotational_delay_ms(disk)
    xfer = transfer_time_ms(size_bytes, disk)
    return ServiceTimeBreakdown(seek, rot, xfer, seek + rot + xfer, distance)
