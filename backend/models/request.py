"""Request model — the atomic unit moving through the simulator.

Config fields are set at generation time. Runtime fields are filled in by the
engine as the request moves through QUEUED -> RUNNING -> COMPLETED/MISSED/REJECTED.
Nothing here computes anything; this is pure data.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RequestType(str, Enum):
    MULTIMEDIA = "MULTIMEDIA"
    OLTP = "OLTP"
    OLAP = "OLAP"


class Operation(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class RequestStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    MISSED = "MISSED"      # completed but past deadline (soft real-time -> still serviced)
    REJECTED = "REJECTED"  # admission control rejected the whole stream before any request existed


@dataclass(eq=False)
class Request:
    """eq=False deliberately: identity-based equality/hash (the dataclass
    default field-wise __eq__ compares every attribute and made
    list.remove() a measured bottleneck under heavy load — see
    docs/architecture.md's performance note). Nothing in this codebase ever
    needs value equality between two Request instances; every simulation
    always removes a request by the exact object reference it just
    selected."""
    id: int
    type: RequestType
    operation: Operation
    arrival_time: float
    cylinder: int
    size_bytes: int
    priority: int = 0
    deadline: Optional[float] = None
    stream_id: Optional[str] = None
    sequentiality: float = 0.0

    # runtime fields, filled in by the engine
    start_service_time: Optional[float] = None
    completion_time: Optional[float] = None
    waiting_time: Optional[float] = None
    response_time: Optional[float] = None
    service_time: Optional[float] = None
    seek_distance: Optional[float] = None
    deadline_missed: bool = False
    jitter: Optional[float] = None
    status: RequestStatus = RequestStatus.QUEUED
    aged: bool = False

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            d[k] = v.value if isinstance(v, Enum) else v
        return d
