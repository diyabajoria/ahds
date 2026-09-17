# Project review — reference summary

This file exists because `docs/mathematical_model.md`, `schedulers/hybrid.py`, and several other
files reference it directly. It's a condensed record of the project review document the simulator
was aligned to (`Hybrid Disk Scheduling for Mixed Multimedia and Database Workloads` — a
workload-classification-driven approach), kept here so the reasoning behind later implementation
choices doesn't go stale once the original document is no longer at hand.

## The review's core design (section 8 — Methodology & Pipeline)

A five-stage pipeline: **Data → PSI → Features → Model → Evaluate**.

1. **Data** — a synthetic multimedia streaming trace (sequential, deadline-tagged blocks) merged
   with a synthetic database trace (small, random OLTP-style reads/writes) on a shared timeline.
2. **PSI (Pattern & Stream Identification)** — every incoming request is inspected for raw
   behavioural signals: sequential vs. random, periodic vs. bursty, size, which stream it belongs to.
3. **Features** — request size (KB), inter-arrival time, LBA delta from the previous request, a
   derived sequential-vs-random flag, and short-term burstiness.
4. **Model** — a lightweight classifier (decision tree, benchmarked against an SVM baseline) maps
   the feature vector to **Multimedia** or **Database**.
5. **Evaluate** — classified, scheduled requests are run through a discrete-event simulator and
   compared against classical baselines (FCFS, SSTF, SCAN, LOOK, C-SCAN) and Linux-style Deadline
   scheduling, on: deadline-miss ratio, average response time, throughput, head movement, and Jain
   fairness — plus, specifically for the classifier itself, precision/recall/F1, and a
   **lead-time-before-degradation** metric (the load level at which the hybrid's advantage over the
   best static baseline starts shrinking).

## Section 8.4 — the hybrid scheduler's stated design

> "Multimedia-labelled requests go to a deadline/SCAN-style sub-queue... database-labelled requests
> go to an SSTF-style sub-queue with an ageing mechanism to prevent starvation. An arbitration layer
> then decides, request by request, which sub-queue gets access to the disk head next."

## Mapping onto this codebase

| Review concept | Implementation |
|---|---|
| PSI + Features + Model | `workloads/features.py` + `simulation/classifier_ml.py` (`POST /api/classifier/train`) |
| Deadline/SCAN sub-queue for multimedia | `schedulers/scan_edf.py`, used as HYBRID's RT sub-scheduler |
| SSTF-with-ageing sub-queue for database | `schedulers/sstf.py` + `simulation/aging.py`, used as HYBRID's BE sub-scheduler (see "Alignment note" in `docs/architecture.md` — this project originally used C-LOOK here; it was switched to match this review) |
| Arbitration layer | `schedulers/hybrid.py` — the round-budget + feedback-controller machinery (S11/S12 in `docs/mathematical_model.md`) |
| Linux-style Deadline baseline | `schedulers/deadline.py` (`SchedulerName.DEADLINE`) |
| Lead-time-before-degradation | `simulation/degradation.py` (`POST /api/experiment/degradation`) |
| Precision/Recall/F1 | `simulation/classifier_ml.py::ClassifierMetrics` |

The review's technical stack (Docker/Kubernetes/Prometheus/SimPy/scikit-learn) is broader than what
this codebase actually uses — the simulation engine here is a from-scratch discrete-event loop
(`simulation/engine.py`), not SimPy, and there is no Docker/K8s/Prometheus layer, since none of the
metrics or behaviour those would add (containerised deployment, live monitoring dashboards) are
things the test suite or the API surface actually exercises. scikit-learn was added specifically for
the classifier (`requirements.txt`).
