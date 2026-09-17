# Running experiments

`POST /api/experiment/run` sweeps one parameter across one or more schedulers, using the **same**
generated workload at each sweep value for every scheduler in that comparison (S15).

## Request shape

```json
{
  "base": { "scheduler": "HYBRID", "disk": {...}, "workload": {...}, "hybrid": {...} },
  "sweep": [{ "name": "workload.load_intensity_pct", "start": 10, "end": 100, "step": 15 }],
  "schedulers": ["FCFS", "HYBRID"]
}
```

`name` is a dotted path into the base config, set with `setattr` on a deep copy per sweep value —
anything on `SimulationConfig` is fair game, e.g.:

- `workload.load_intensity_pct`
- `workload.multimedia.n_streams`
- `workload.oltp.n_requests`
- `hybrid.aging_threshold_ms`
- `hybrid.rt_fraction`
- `disk.rpm`

## Current scope

Only the **first** sweep parameter in the `sweep` list is actually expanded; a second/third entry
is accepted by the schema but held at its base value. A full Cartesian product across multiple
swept parameters was left out to keep a single synchronous API call bounded in run count and
response time — see `experiments/runner.py` for the exact note. Sweeping two parameters today means
two separate `/api/experiment/run` calls.

## Reading the output

Each row is one `(sweep_value, scheduler)` pair with the full metrics object attached — the same
shape `/api/simulate` returns per run. The Experiments page charts deadline miss ratio against the
swept parameter and offers a CSV export (`sweep_param, sweep_value, scheduler, miss_ratio, db_p95,
head_movement, utilization`).

## Why `load_intensity_pct` doesn't change request counts

Load intensity scales **arrival rate**, not the number of requests generated (stream/request counts
come from `n_streams` / `n_requests` / `n_scans`, independently). At 100% load the same number of
requests arrives in less wall-clock time, which is what actually stresses a scheduler — a workload
with more requests spread over more time isn't "more load" in the sense this project means it.
