"""Workload configuration models."""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class ArrivalModel(str, Enum):
    PERIODIC = "PERIODIC"
    POISSON = "POISSON"
    MANUAL = "MANUAL"


class MultimediaConfig(BaseModel):
    n_streams: int = 4
    bitrate_bytes_per_s: float = 500_000.0
    request_size_bytes: int = 8192
    deadline_slack_periods: float = 2.0
    sequentiality: float = 0.85   # P(next request is cylinder+1 vs a jump)
    arrival_model: ArrivalModel = ArrivalModel.PERIODIC

    @field_validator("n_streams")
    @classmethod
    def _n(cls, v):
        if v < 0:
            raise ValueError("n_streams must be >= 0")
        return v

    @field_validator("sequentiality")
    @classmethod
    def _seq(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("sequentiality must be in [0,1]")
        return v


class OLTPConfig(BaseModel):
    n_requests: int = 200
    min_size_bytes: int = 4096
    max_size_bytes: int = 16384
    zipf_s: float = 1.1
    read_ratio: float = 0.7
    arrival_rate_per_s: float = 50.0   # Poisson lambda
    arrival_model: ArrivalModel = ArrivalModel.POISSON

    @field_validator("read_ratio")
    @classmethod
    def _rr(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("read_ratio must be in [0,1]")
        return v

    @model_validator(mode="after")
    def _sizes(self):
        if self.min_size_bytes <= 0 or self.max_size_bytes < self.min_size_bytes:
            raise ValueError("invalid OLTP size range")
        return self


class OLAPConfig(BaseModel):
    n_scans: int = 10
    scan_length_cylinders: int = 40
    arrival_rate_per_s: float = 1.0
    arrival_model: ArrivalModel = ArrivalModel.POISSON

    @field_validator("scan_length_cylinders")
    @classmethod
    def _sl(cls, v):
        if v <= 0:
            raise ValueError("scan_length_cylinders must be > 0")
        return v


class WorkloadConfig(BaseModel):
    multimedia: MultimediaConfig = MultimediaConfig()
    oltp: OLTPConfig = OLTPConfig()
    olap: OLAPConfig = OLAPConfig()
    rt_be_mix: float = 0.5           # target fraction of bytes/requests that are RT (informational)
    load_intensity_pct: float = 50.0  # 10-100, scales arrival rates as a fraction of effective_BW
    seed: int = 42

    @field_validator("load_intensity_pct")
    @classmethod
    def _li(cls, v):
        if not (10.0 <= v <= 100.0):
            raise ValueError("load_intensity_pct must be in [10,100]")
        return v
