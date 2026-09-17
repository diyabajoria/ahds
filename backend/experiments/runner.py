"""Experiment runner: sweeps one or more parameters across one or more
schedulers, using a fresh identical (deep-copied) workload per configuration
value — S15: every scheduler in one comparison point sees byte-identical
input requests."""
from __future__ import annotations
from typing import List, Dict, Any

from models.simulation import ExperimentRequest
from simulation.workload_builder import build_workload
from simulation.orchestrator import run_one
from experiments.sweeps import build_sweep_configs


def run_experiment(req: ExperimentRequest) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    # Currently sweeps the FIRST parameter fully; additional params are held
    # at their base value. (A full Cartesian product across multiple swept
    # parameters is a straightforward extension left as future scope — see
    # docs/experiments.md — to keep run counts bounded for the API's
    # synchronous response model.)
    param = req.sweep[0]
    for value, cfg in build_sweep_configs(req.base, param):
        requests, stream_periods = build_workload(cfg.workload, cfg.disk)
        for sched_name in req.schedulers:
            run_cfg = cfg.model_copy(deep=True)
            run_cfg.scheduler = sched_name
            _, metrics, _ = run_one(run_cfg, requests=requests, stream_periods=stream_periods)
            rows.append({
                "sweep_param": param.name,
                "sweep_value": value,
                "scheduler": sched_name.value,
                "metrics": metrics,
            })
    return {"rows": rows, "sweep_param": param.name}
