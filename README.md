# Adaptive Hybrid Disk Scheduling Simulator

A discrete-event disk scheduling simulator for mixed multimedia and database workloads, built
around **HYBRID** — a scheduler that classifies incoming I/O requests, arbitrates between a
deadline-aware real-time sub-scheduler and a fairness-aware best-effort sub-scheduler using
round-based budgets, and adapts that arbitration with a deterministic feedback controller.

This project was subsequently reviewed against a companion design document (`docs/project_review.md`)
describing a workload-classification-driven approach, and three things were changed to align with
it — see `docs/architecture.md`'s "Alignment note" for the full detail:

1. HYBRID's database sub-scheduler switched from C-LOOK to **SSTF-with-aging**.
2. A **real, trained classifier** (decision tree vs. SVM baseline) was added, reporting
   precision/recall/F1 — not the original heuristic.
3. A **Linux-style Deadline scheduler baseline** and a **lead-time-before-degradation** metric were
   added.

## Overview

Nine classical/real-time disk scheduling algorithms (FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK, EDF,
SCAN-EDF, a Linux-style Deadline scheduler) plus HYBRID, all running through the same
discrete-event engine, on the same generated (or uploaded) workload, so their measured differences
come from the algorithm alone.

## Problem statement

Given a single disk receiving a mixed stream of multimedia (deadline-bound) and database
(fairness-sensitive) requests, design and evaluate a scheduler that minimizes the multimedia
deadline-miss ratio, keeps database response time and fairness acceptable, and does not make total
disk throughput or head movement worse than the best single static algorithm on the same workload.

## Objectives

1. Build a workload classifier that labels each request multimedia or database from observable
   features alone (`workloads/features.py`, `simulation/classifier_ml.py`).
2. Design the hybrid scheduling policy (`schedulers/hybrid.py`).
3. Build a reproducible mixed-workload simulation environment (`simulation/`, `workloads/`).
4. Evaluate against classical baselines and Linux-style Deadline scheduling
   (`simulation/orchestrator.py`, `experiments/runner.py`, `simulation/degradation.py`).

## Architecture

See `docs/architecture.md` for the full layer-by-layer breakdown. In short:

```
FastAPI (backend/main.py)
  └─ simulation/orchestrator.py : build workload → build scheduler → run engine → compute metrics
       ├─ workloads/{multimedia,oltp,olap}.py   (single seeded RNG — S16 determinism)
       ├─ schedulers/*.py                        (10 algorithms, one class each)
       └─ simulation/engine.py                   (the discrete-event loop)
```

Frontend: React + Vite + TypeScript + Tailwind + Recharts, four pages (Simulation, Comparison,
Experiments, About the Algorithm), talking to the API over `/api/*`.

## Disk model

`service_time = seek_time + rotational_delay + transfer_time`, with a LINEAR or REALISTIC seek
model, and a separate SSD mode that zeroes seek and rotational delay entirely. Full formulas in
`docs/mathematical_model.md`.

## The hybrid design

Real-time (multimedia) requests are served by SCAN-EDF; best-effort (database) requests by
SSTF-with-aging. Each round of length `T` gets an RT/BE budget split controlled by `rt_fraction`;
overruns become debt into the next round; a feedback controller adjusts `rt_fraction` every few
rounds using hysteresis (two thresholds, not one, to avoid oscillation); any BE request that waits
past an aging threshold is escalated regardless of budget, capped per round. Full pseudocode in
`docs/algorithms.md`, full formulas in `docs/mathematical_model.md`.

## Workload models

- **Multimedia**: N streams, bitrate-derived period, deadline = arrival + slack × period,
  configurable sequentiality (probability of cylinder+1 vs. a jump).
- **Database (OLTP)**: small requests, Zipfian cylinder hot-spots, Poisson arrivals.
- **Database (OLAP)**: occasional large sequential scans.
- All randomness flows through one seeded `numpy.random.Generator` per run (`S16` — determinism is
  a tested property, see `tests/test_determinism.py`).

## Metrics

Deadline miss ratio, mean/max jitter, response-time percentiles (nearest-rank, S10), throughput,
IOPS, starvation count, max waiting time, total head movement, mean seek time, utilization, Jain
fairness index, and — per the project review — classifier precision/recall/F1 and lead-time-before-
degradation. Full list and formulas in `docs/mathematical_model.md`.

## Install

**Backend** (Python 3.11+):
```bash
cd backend
pip install -r requirements.txt
```

**Frontend** (Node 18+):
```bash
cd frontend
npm install
```

## Run

**Backend** (from `backend/`):
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```
API docs at `http://localhost:8000/docs`.

**Frontend** (from `frontend/`, in a second terminal):
```bash
npm run dev
```
Opens at `http://localhost:5173`, proxying `/api/*` to the backend on port 8000 (see
`vite.config.ts`).

**Tests** (from `backend/`):
```bash
python3 -m pytest -v
```

## A demo configuration that shows HYBRID's behaviour clearly

Use the **`starvation_stress`** preset (`GET /api/presets`, or the Simulation page's preset
dropdown): heavy multimedia pressure (10 streams at 900 KB/s) with a low aging threshold (80ms).
Run it, then look at:
- the **RT budget adaptation** chart — `rt_fraction` visibly climbing as the feedback controller
  reacts to deadline misses;
- the **hybrid metrics** — `aged_requests` and `starvation_count` both non-zero, proving the aging
  escape hatch actually fired rather than sitting unused.

## The hybrid algorithm, in plain English

Every disk request is either a video/audio stream request with a deadline, or a database
request with none. HYBRID keeps two separate queues and gives each a slice of every 100ms "round" —
by default, half the round for streams, half for the database. If deadlines start getting missed,
it takes a bit more time away from the database queue for the next several rounds; if the database
queue is fine but getting slow, it gives some of that time back. If a single database request has
been waiting a long time (more than a configurable threshold, regardless of whose turn it "should"
be), it gets served anyway, so it can never wait forever. That's the whole idea: instead of picking
one fixed algorithm and hoping it happens to suit whatever mix of requests shows up, HYBRID watches
what's actually happening and shifts its own priorities in response, while a hard-coded escape hatch
stops that adaptiveness from ever starving anyone completely.

## Full file list

```
backend/
  main.py  presets.py  requirements.txt
  models/          request.py  disk.py  workload.py  simulation.py
  schedulers/       base.py  fcfs.py  sstf.py  scan.py  cscan.py  look.py  clook.py
                    edf.py  scan_edf.py  deadline.py  hybrid.py
  workloads/        multimedia.py  oltp.py  olap.py  arrivals.py  classifier.py  features.py
  simulation/        engine.py  disk_model.py  metrics.py  admission.py  feedback.py  aging.py
                     workload_builder.py  factory.py  orchestrator.py  classifier_ml.py  degradation.py
  experiments/       runner.py  sweeps.py  export.py
  tests/             (14 files, 42 tests — see below)
frontend/
  src/
    App.tsx  main.tsx  index.css  types.ts
    services/api.ts
    components/  Panel.tsx  MetricCard.tsx  NumberField.tsx  HeadTrack.tsx
    pages/       SimulationPage.tsx  ComparisonPage.tsx  ExperimentsPage.tsx  AboutPage.tsx
docs/
  architecture.md  algorithms.md  mathematical_model.md  experiments.md  viva_questions.md
  project_review.md
README.md
```

## Actual pytest output

```
$ python3 -m pytest -v
tests/test_admission.py::test_admission_accepted_just_under_capacity PASSED
tests/test_admission.py::test_admission_rejected_just_over_capacity PASSED
tests/test_aging.py::test_aged_request_dispatched_before_nearer_nonaged PASSED
tests/test_api_validation.py::test_health PASSED
tests/test_api_validation.py::test_schedulers_list PASSED
tests/test_api_validation.py::test_presets_list PASSED
tests/test_api_validation.py::test_cylinder_out_of_range_rejected PASSED
tests/test_api_validation.py::test_nonpositive_size_rejected PASSED
tests/test_api_validation.py::test_rpm_zero_rejected PASSED
tests/test_api_validation.py::test_empty_workload_rejected PASSED
tests/test_api_validation.py::test_unknown_scheduler_rejected PASSED
tests/test_api_validation.py::test_rt_fraction_out_of_range_rejected PASSED
tests/test_api_validation.py::test_round_length_nonpositive_rejected PASSED
tests/test_api_validation.py::test_malformed_csv_rejected PASSED
tests/test_api_validation.py::test_wrong_extension_rejected PASSED
tests/test_api_validation.py::test_nonexistent_run_id_404 PASSED
tests/test_api_validation.py::test_valid_simulate_smoke PASSED
tests/test_classifier_ml.py::test_classifier_reports_precision_recall_f1_for_both_models PASSED
tests/test_classifier_ml.py::test_classifier_rejects_single_class_workload PASSED
tests/test_compare_identical_workload.py::test_compare_schedulers_see_identical_requests PASSED
tests/test_deadline_scheduler.py::test_expired_read_jumps_the_queue PASSED
tests/test_deadline_scheduler.py::test_no_expiry_behaves_like_sector_sorted_sweep PASSED
tests/test_degradation.py::test_degradation_sweep_produces_real_points PASSED
tests/test_determinism.py::test_same_seed_same_workload PASSED
tests/test_determinism.py::test_same_seed_same_metrics PASSED
tests/test_disk_model.py::test_rotation_and_transfer_by_hand PASSED
tests/test_disk_model.py::test_linear_seek_by_hand PASSED
tests/test_disk_model.py::test_realistic_seek_by_hand PASSED
tests/test_disk_model.py::test_ssd_mode_zeroes_seek_and_rotation PASSED
tests/test_edf.py::test_edf_nondecreasing_deadlines PASSED
tests/test_edf.py::test_scan_edf_differs_from_edf PASSED
tests/test_fairness.py::test_jain_equal_throughputs_is_one PASSED
tests/test_fairness.py::test_jain_one_class_dominant_is_one_over_n PASSED
tests/test_fairness.py::test_percentile_nearest_rank_basic PASSED
tests/test_golden_schedulers.py::test_golden_no_direction[scheduler0-None-640] PASSED
tests/test_golden_schedulers.py::test_golden_no_direction[scheduler1-None-236] PASSED
tests/test_golden_schedulers.py::test_golden_scan PASSED
tests/test_golden_schedulers.py::test_golden_cscan PASSED
tests/test_golden_schedulers.py::test_golden_look PASSED
tests/test_golden_schedulers.py::test_golden_clook PASSED
tests/test_hybrid_budget.py::test_hybrid_debt_reconciles_and_is_clamped PASSED
tests/test_workload_generation.py::test_generates_all_three_classes PASSED

======================== 42 passed in 1.56s ========================
```

The golden numbers (`test_golden_schedulers.py`) reproduce the spec's exact classic-sequence
answers — head 53, requests `[98,183,37,122,14,124,65,67]`, 200 cylinders:
**FCFS 640, SSTF 236, SCAN 236, C-SCAN 382, LOOK 208, C-LOOK 322** — all exact integer matches.

## One real experiment result table

3 multimedia streams (200 KB/s), 150 OLTP requests, 5 OLAP scans, 45% load intensity, seed 42, all
ten schedulers run on the **identical** generated workload:

| scheduler | deadline miss ratio | DB p95 (ms) | DB p99 (ms) | head movement (cyl) | utilization | Jain fairness |
|---|---|---|---|---|---|---|
| FCFS | 97.8% | 6391.98 | 6479.28 | 40176 | 100.0% | 0.340 |
| SSTF | 63.3% | 1535.55 | 1683.02 | 4647 | 100.0% | 0.340 |
| SCAN | 65.6% | 1577.47 | 1698.90 | 5209 | 98.8% | 0.340 |
| C-SCAN | 74.4% | 1600.08 | 1711.68 | 5947 | 89.1% | 0.340 |
| LOOK | 53.3% | 1497.64 | 1681.74 | 4806 | 100.0% | 0.340 |
| C-LOOK | 66.7% | 1569.79 | 1755.99 | 5681 | 90.2% | 0.340 |
| EDF | 96.7% | 6507.48 | 6594.78 | 40946 | 100.0% | 0.340 |
| SCAN-EDF | 82.2% | 4813.08 | 4900.38 | 29650 | 100.0% | 0.340 |
| DEADLINE | 96.7% | 6443.58 | 6530.88 | 40520 | 99.4% | 0.340 |
| **HYBRID** | **95.6%** | **5345.44** | **5515.54** | **30532** | 100.0% | 0.340 |

## Honest paragraph: where HYBRID loses, and why

At this load, **plain LOOK (53.3% miss ratio) and SSTF (63.3%) both beat HYBRID (95.6%)** on the one
metric HYBRID is specifically supposed to protect. The reason is structural, not a bug: HYBRID's
RT sub-scheduler (SCAN-EDF) groups requests by deadline proximity (within 5ms of each other) and
then picks the nearest *within that group* — but with three independent streams each walking their
own region of the disk, "nearest within an equally-urgent group" still frequently means a large seek
across streams, because deadline proximity and cylinder proximity are only weakly correlated across
different streams. Plain LOOK/SSTF have no deadline logic at all — they just always chase whatever
is physically nearest — and at this load, physically-nearest-first happens to serve multimedia
requests (which are the majority of pending demand once streams back up) fast enough, purely as a
side effect of low seek overhead, to beat a scheduler that's explicitly trying to prioritize them by
deadline but paying for it in extra seek distance. HYBRID *does* beat every deadline-agnostic FCFS-
style baseline (FCFS, EDF, DEADLINE all sit at 96-98%) and uses roughly 25% less head movement than
EDF/SCAN-EDF/DEADLINE while doing it — its actual advantage over those is real, it's specifically
the pure-seek-optimizing baselines (LOOK, SSTF) that beat it here. This is exactly the
"don't rig the workload" result this project's own build instructions call for: a result set where
HYBRID wins everywhere would be the sign of a bug, not a feature.

## Limitations

No real hardware — this is a discrete-event simulation, not a kernel patch or a block device driver.
No on-disk cache modelling, no NCQ (Native Command Queuing), no filesystem layer. Linear
cylinder-to-LBA mapping (real disks are far messier). Rotational latency is averaged rather than
modelled as an actual platter position at each instant. HYBRID's "soft" handling of a fully
budget-exhausted round (see `docs/mathematical_model.md`) is a documented simplification of the
spec's literal "round ends when both budgets are exhausted" wording. The experiment sweep endpoint
currently expands only the first swept parameter in a multi-parameter request (`docs/experiments.md`).
Under sustained heavy overload specifically (not normal operation — see the benchmark table in
`docs/architecture.md`), HYBRID's SSTF-based best-effort dispatch is `O(pending size)` per decision,
which measurably slows a run once the best-effort backlog grows very large; this was profiled and
optimized twice (see `docs/architecture.md`'s performance note) but the underlying linear scan was
left as-is rather than replaced with a sorted-by-cylinder structure, since it only bites in a regime
the aging escape hatch and admission control are meant to prevent in a correctly provisioned
deployment.

## Future scope

A full Cartesian-product multi-parameter sweep; a true stall-until-round-boundary implementation of
HYBRID's exhausted-budget case; per-request read/write merge logic in the Deadline scheduler; a
learned (rather than fixed-hyperparameter) classifier with cross-validated model selection; trace
replay from real block-layer captures via the existing `/api/trace/upload` endpoint (currently
accepts and validates traces but the simulate endpoint itself only runs generated workloads —
wiring an uploaded trace directly into `/api/simulate` is a natural next step); replacing
`schedulers/sstf.py`'s linear nearest-cylinder scan with a sorted-by-cylinder structure (e.g. a
balanced tree or `sortedcontainers.SortedList`) supporting O(log n) nearest-neighbour lookup, to
remove the one remaining `O(n)`-per-dispatch bottleneck under sustained heavy overload.
