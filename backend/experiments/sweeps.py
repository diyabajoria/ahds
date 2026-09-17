"""Parameter sweep expansion: turns a SweepParam (dotted path + range) into a
list of (value, config) pairs by setting that field on a deep copy of the
base config."""
from __future__ import annotations
import copy
import numpy as np
from typing import List, Tuple

from models.simulation import SimulationConfig, SweepParam


def _set_dotted(obj, dotted: str, value):
    parts = dotted.split(".")
    target = obj
    for p in parts[:-1]:
        target = getattr(target, p)
    setattr(target, parts[-1], value)


def expand_sweep_values(param: SweepParam) -> List[float]:
    n_steps = int(round((param.end - param.start) / param.step)) + 1
    n_steps = max(n_steps, 1)
    return [round(param.start + i * param.step, 10) for i in range(n_steps)
            if (param.step > 0 and param.start + i * param.step <= param.end + 1e-9)
            or (param.step < 0 and param.start + i * param.step >= param.end - 1e-9)]


def build_sweep_configs(base: SimulationConfig, param: SweepParam) -> List[Tuple[float, SimulationConfig]]:
    out = []
    for v in expand_sweep_values(param):
        cfg = base.model_copy(deep=True)
        _set_dotted(cfg, param.name, v)
        out.append((v, cfg))
    return out
