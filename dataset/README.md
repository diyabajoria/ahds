# Dataset — `disk_workload.csv`

## What this is

A fixed, 4,800-row CSV of disk I/O requests, generated once (seed = 7) and
frozen to disk so it can be inspected, reused, and demonstrated the same
way every time — instead of the simulator's usual behaviour of generating
a fresh workload from scratch on every run.

**This is a synthetic dataset, not a real-world trace, and this project
does not claim otherwise.** It is produced by calling the project's own
workload generators (`backend/workloads/multimedia.py`,
`backend/workloads/oltp.py`, `backend/workloads/olap.py`) through
`backend/simulation/workload_builder.py`, with a single fixed NumPy random
seed, and saving the result instead of discarding it. This is documented
here explicitly so nobody mistakes it for a captured real-world I/O trace.

## Why a dataset exists as a separate artifact

The simulator's normal mode of operation is: pick parameters → generate a
workload → run it → throw the workload away. For demonstrating the
project's **machine-learning workload classifier**
(`backend/simulation/classifier_ml.py`) specifically, it is more
convincing — and more standard academic practice — to have one fixed,
labeled dataset that can be shown, previewed, loaded, and reused across
multiple demonstrations, rather than a different set of random numbers
every time the "Generate" button is clicked.

## How it was generated

```
cd ahds/backend
python generate_dataset.py
```

Configuration used (see `backend/generate_dataset.py` for the exact code):

| Parameter | Value |
|---|---|
| Random seed | 7 |
| Disk | 500 cylinders (project default `DiskConfig`) |
| Multimedia streams | 20 streams × 30 requests/stream = 600 requests |
| OLTP requests | 3,200 requests (Zipfian hot-spot cylinders, Poisson arrivals) |
| OLAP scans | 25 scans × 40 cylinders/scan = 1,000 requests |
| **Total** | **4,800 requests** |

Because NumPy's `Generator` is fully deterministic for a fixed seed and a
fixed call order, re-running `generate_dataset.py` reproduces this exact
file. The script is part of the repository, not a one-off — this is a
generated-and-frozen dataset, not a hand-written one.

## Columns

| Column | Meaning |
|---|---|
| `timestamp` | Arrival time in milliseconds, simulation-relative (`0.0` = start) |
| `cylinder` | Disk cylinder / track number the request targets (`0`–`499`) |
| `size` | Request size in bytes |
| `operation` | `READ` or `WRITE` |
| `type` | Ground-truth workload class: `MULTIMEDIA`, `OLTP`, or `OLAP` (`OLTP`+`OLAP` are merged into the single `DATABASE` class at classifier-training time, matching the review's two-class M-vs-D framing) |
| `deadline` | Soft real-time deadline in ms, populated for `MULTIMEDIA` requests only (empty for `OLTP`/`OLAP`, which have none) |
| `stream_id` | Multimedia stream identifier (`mm-0` … `mm-19`), empty for `OLTP`/`OLAP` |

This is exactly the schema the backend's existing `POST /api/trace/upload`
endpoint already expected (`timestamp, cylinder, size, operation`
required; `type, deadline, stream_id` optional) — the dataset was built to
match the API the project already had, not the other way around.

## Class balance

| Type | Count | % |
|---|---:|---:|
| MULTIMEDIA | 600 | 12.5% |
| OLTP | 3,200 | 66.7% |
| OLAP | 1,000 | 20.8% |
| **DATABASE (OLTP+OLAP, classifier's negative class)** | **4,200** | **87.5%** |

This is an imbalanced two-class split (12.5% MULTIMEDIA vs 87.5%
DATABASE) by construction, since real mixed workloads are rarely
balanced 50/50 — the classifier's stratified train/test split
(`test_size=0.3`, `stratify=y`) accounts for this.

## How it's used in the project

- **API**: `GET /api/dataset/info` returns this table's numbers live from
  the file; `GET /api/dataset/preview` returns the first N rows;
  `POST /api/dataset/simulate` runs any scheduler against this exact
  dataset instead of a freshly generated workload;
  `POST /api/dataset/classifier/train` trains the Decision Tree / SVM
  classifier on this exact dataset instead of a fresh one.
- **Frontend**: the "Dataset" page shows the table above, a live preview
  of the CSV, and buttons to run a simulation or train the classifier
  against it.
- **Honesty note**: using a frozen dataset changes nothing about the
  underlying claim of the project — HYBRID is not asserted to be
  universally superior, and all metrics reported from this dataset are
  actual output of running the real simulator/classifier against these
  4,800 real (synthetic) rows, never invented numbers.
