# Mathematical Model

Every formula below is implemented exactly as written, in the file named next to it.
Symbols in `code font` match variable names in the code.

## Symbol table

| Symbol | Meaning | Unit |
|---|---|---|
| `head` | current head position | cylinder |
| `d` | seek distance = \|head − target\| | cylinders |
| `RPM` | disk rotation speed | revolutions/min |
| `bytes_per_track` | track capacity | bytes |
| `size_bytes` | request payload size | bytes |
| `T` | HYBRID round length | ms |
| `rt_fraction` | share of `T` reserved for RT | [0,1] |

## S4 — Service time (`simulation/disk_model.py`)

```
seek_time        = f(d)
rotational_delay = 0.5 * (60000 / RPM)
transfer_time     = (size_bytes / bytes_per_track) * (60000 / RPM)
service_time      = seek_time + rotational_delay + transfer_time
```

Seek models:
- **LINEAR**: `seek_time = seek_coeff * d`
- **REALISTIC**: `seek_time = seek_a + seek_b * sqrt(d)`, and `seek_time = 0` when `d == 0` in both.

## S5 — SSD mode

```
seek_time = 0
rotational_delay = 0
transfer_time = size_bytes / ssd_bandwidth_bytes_per_ms
```

All schedulers still run and produce an ordering; head movement is still computed and shown in the
UI, but labelled not-applicable to timing, since a real SSD has no head to move.

## S7 — Jitter (per multimedia stream)

```
jitter_k = |(completion_time_k − completion_time_{k−1}) − stream_period|
```

The first request of a stream has no jitter (its `jitter` field is `None`, not 0 — 0 would falsely
claim a measurement of "no jitter" rather than "no prior request to compare against").

## S8 — Jain fairness index (`simulation/metrics.py :: jain_fairness`)

```
J = (Σ xᵢ)² / (n · Σ xᵢ²)
```

`xᵢ` is the achieved throughput (bytes/ms) of workload class *i*, over the classes actually present
in the run (MULTIMEDIA, OLTP, OLAP treated as up to three classes). `J = 1` when all classes get
equal throughput; `J = 1/n` when one class gets everything.

## S9 — Utilization

```
utilization = busy_time / makespan
makespan    = last_completion_time − first_arrival_time
```

## S10 — Percentiles (`simulation/metrics.py :: percentile_nearest_rank`)

Nearest-rank method on the sorted sample list:

```
rank = ceil(p/100 * n),  clamped to [1, n]
percentile = sorted_values[rank - 1]
```

`response_time = completion_time − arrival_time` and `waiting_time = start_service_time −
arrival_time` are used consistently everywhere in the codebase — never redefined per chart.

## S11 — Hybrid round budgets (`schedulers/hybrid.py`)

```
rt_budget_ms = T * rt_fraction
be_budget_ms = T − rt_budget_ms
```

A request is only dispatched from a class while that class's budget > 0 (subject to the
work-conservation and aging overrides below). Because service is non-preemptive, a dispatched
request may run past its class's remaining budget — the overrun becomes **debt**:

```
debt_class = min(max(0, −budget_class_at_round_end), T * fraction_class)   # clamped to one round's allocation
next_round_budget_class = T * fraction_class − debt_class
```

**Work conservation** (`work_conserving`, default `true`): if one class has no eligible pending
requests, the other class may consume budget beyond its own allocation.

**Documented simplification** — the spec's literal text ("a round ends when both budgets are
exhausted or no request is pending") implies the engine should idle until the round boundary if
both budgets are spent but requests remain. This implementation instead treats that state as a
*soft* deprioritisation: the class is still served (RT preferred), and the overrun is still charged
as debt exactly as above. This was a deliberate scope cut to avoid a second engine-level "advance
clock with no service" hook symmetric to the SCAN-family's `reposition_before_select`; it changes
only the scheduling of the last request or two before a round boundary under saturation, not the
steady-state adaptive behaviour.

## S12 — Feedback controller (`simulation/feedback.py`)

Runs once every `control_window_rounds` rounds (default 5), deterministic, no randomness:

```
miss_ratio = misses_in_window / RT_completions_in_window     (0 if no RT completions)
db_p95     = p95 of BE response times in window

if miss_ratio > miss_high_threshold:                    rt_fraction += step
elif miss_ratio <= miss_low_threshold and db_p95 > db_latency_threshold:  rt_fraction -= step
else:                                                    unchanged

rt_fraction = clamp(rt_fraction, rt_min, rt_max)
```

Defaults: `step=0.05`, `miss_high_threshold=0.02`, `miss_low_threshold=0.0`, `rt_min=0.1`,
`rt_max=0.9`. `db_latency_threshold` defaults to `3 × db_p95` measured in the **first** control
window (recorded once as a baseline, never re-derived). The two separate thresholds (rather than
one) are what prevent oscillation — see `docs/viva_questions.md`.

## S13 — Aging (`simulation/aging.py`)

```
age = now − arrival_time
if age >= aging_threshold_ms: request.aged = True
```

Aged BE requests are served before the normal C-LOOK order within the BE turn, oldest arrival
first, and may be dispatched even when the BE budget is exhausted — up to `max_aged_per_round`
(default 1) per round. This is the deliberate starvation escape hatch: it necessarily lets a BE
request violate the round's budget by design, which is why it's capped per round rather than
unconditional.

## S14 — Admission control (`simulation/admission.py`)

```
avg_seek_ms  = f(cylinders / 3)                      # expected distance between 2 uniform cylinders
avg_request_ms = avg_seek_ms + rotational_delay + (avg_request_bytes / bytes_per_track) * rotation_ms
effective_BW = avg_request_bytes / avg_request_ms      # bytes per ms
usable_BW    = effective_BW * rt_max                    # only the RT share is reservable

ACCEPT a new stream of `bitrate` iff:  Σ reserved + bitrate <= usable_BW
```

Both the requested and the usable bandwidth are returned in the API response so the reason for a
rejection is never opaque.

## S8/S15/S16 cross-references

- Jain fairness inputs in `compute_full_metrics` are per-class **achieved** throughput
  (`bytes serviced / makespan`), not nominal/configured bitrate — an idle or starved class shows up
  as low fairness even if its nominal share was generous.
- S15 (identical workload across schedulers in one comparison) is enforced by generating the
  request list once in `/api/compare` and `/api/experiment/run`, then `deepcopy`-ing it into
  `run_one()` for every scheduler — see `tests/test_compare_identical_workload.py`.
- S16 (determinism) is enforced by routing every random draw through one
  `numpy.random.Generator(seed)` created in `simulation/workload_builder.py::build_workload` — see
  `tests/test_determinism.py`.

## Added per the project review — classifier and DEADLINE scheduler

### Features (`workloads/features.py`)

```
size_kb           = size_bytes / 1024
inter_arrival_ms  = max(0, arrival_time_i - arrival_time_{i-1})     # over the full arrival-sorted sequence
lba_delta         = |cylinder_i - cylinder_{i-1}|
sequential_flag   = 1 if lba_delta <= SEQ_THRESHOLD_CYLINDERS (4) else 0
burstiness        = count of requests with arrival_time in (arrival_time_i - 20ms, arrival_time_i]
```

### Classifier evaluation (`simulation/classifier_ml.py`)

A `DecisionTreeClassifier(max_depth=6)` and an `SVC(kernel="rbf")` (features standardised first) are
trained on an identical stratified 70/30 train/test split of the same feature matrix, and each is
scored with:

```
precision, recall, f1 = precision_recall_fscore_support(y_test, y_pred, pos_label=MULTIMEDIA)
confusion_matrix = [[TN, FP], [FN, TP]]   # label 1 = MULTIMEDIA, label 0 = DATABASE (OLTP+OLAP merged)
```

### Linux-style Deadline scheduler (`schedulers/deadline.py`)

```
expired(request) = (now - request.arrival_time) >= (read_expire_ms if READ else write_expire_ms)
```
Serves the oldest expired request if any exist; otherwise falls back to a C-LOOK-style
sector-sorted sweep. Defaults: `read_expire_ms=100`, `write_expire_ms=500` (scaled down from real
Linux's 500ms/5000ms defaults to match this simulator's much shorter workload timescales).

### Lead-time-before-degradation (`simulation/degradation.py`)

```
advantage(load) = best_static_baseline_miss_ratio(load) - hybrid_miss_ratio(load)
lead_time = the load value at the last point where advantage(load) was still >= advantage(previous load)
```
Reported as `None` with an explanatory note if the advantage never shrinks across the swept range —
this value is never guessed at or interpolated; it is read directly off points that were each a
full, real simulation run.
