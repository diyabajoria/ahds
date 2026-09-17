"""Disk configuration. Validated with Pydantic v2 — bad input is HTTP 422, never a 500."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, field_validator, model_validator


class SeekModel(str, Enum):
    LINEAR = "LINEAR"
    REALISTIC = "REALISTIC"


class DiskType(str, Enum):
    HDD = "HDD"
    SSD = "SSD"


class DiskConfig(BaseModel):
    disk_type: DiskType = DiskType.HDD
    cylinders: int = 500
    initial_head: int = 250
    rpm: float = 7200
    bytes_per_track: int = 1_048_576
    sector_size: int = 4096
    seek_model: SeekModel = SeekModel.LINEAR
    seek_coeff: float = 0.15          # ms per cylinder, LINEAR model
    seek_a: float = 1.5               # ms, fixed seek overhead, REALISTIC model
    seek_b: float = 0.6               # ms per sqrt(cylinder), REALISTIC model
    ssd_bandwidth: float = 2_000.0    # bytes per ms (~2 GB/s)

    @field_validator("cylinders")
    @classmethod
    def _cyl(cls, v):
        if v < 2:
            raise ValueError("cylinders must be >= 2")
        return v

    @field_validator("rpm")
    @classmethod
    def _rpm(cls, v):
        if v <= 0:
            raise ValueError("rpm must be > 0")
        return v

    @field_validator("bytes_per_track", "sector_size", "ssd_bandwidth")
    @classmethod
    def _pos(cls, v):
        if v <= 0:
            raise ValueError("must be > 0")
        return v

    @model_validator(mode="after")
    def _head_range(self):
        if not (0 <= self.initial_head < self.cylinders):
            raise ValueError(
                f"initial_head ({self.initial_head}) must be in [0, {self.cylinders})"
            )
        return self
