# Architecture

## Layers

```
FastAPI (main.py)
   │  validates SimulationConfig / CompareRequest / ExperimentRequest (Pydantic v2)
   ▼
simulation/orchestrator.py  — one call: build workload → build scheduler → run engine → compute metrics
   │
   ├── simulation/workload_builder.py → workloads/{multimedia,oltp,olap}.py  (single seeded RNG)
   ├── simulation/factory.py          → schedulers/*.py                     (one class per algorithm)
   ├── simulation/engine.py           — owns the clock, the pending queue, all head-movement bookkeeping
   └── simulation/metrics.py          — turns completed requests into the numbers in section 5 of the spec
```

The engine never asks a scheduler to compute a metric, and no scheduler ever touches the clock —
that separation is what makes the golden-number tests possible: swap the scheduler, get a different
number, from the same engine.

## The Scheduler interface

```python
class Scheduler(ABC):
    def select_next(self, pending, head, now) -> Request | None: ...
    def reposition_before_select(self, pending, head, now) -> int | None: ...   # optional
    def on_completion(self, request, now) -> None: ...                          # optional
    def reset(self) -> None: ...                                                # optional
```

`select_next` is the only required method — a scheduler that just answers "which of these pending
requests do I serve next" is a complete, correct scheduler (FCFS, SSTF, EDF are exactly this).

Two optional hooks exist because a handful of algorithms need more:

- **`reposition_before_select`** — SCAN needs to walk all the way to the physical disk boundary
  before reversing, even when nothing is pending there; C-SCAN and C-LOOK need to jump back to the
  start of the sweep. Returning a cylinder tells the engine "move the head here first, as a pure
  seek with no data transfer, then ask me again." The engine loops on this until it gets `None`.
  Plain FCFS/SSTF/EDF never override it.
- **`on_completion`** — only `HYBRID` overrides this. Everything else is memoryless between calls;
  HYBRID needs to observe every completion to run its round/debt/feedback bookkeeping.

## Discrete-event engine (`simulation/engine.py`)

The loop, each iteration:

1. Pull any requests whose `arrival_time <= clock` into `pending` (via an advancing index pointer
   over the arrival-sorted request list — not a full rescan, which is what made the first version of
   this engine `O(n²)` on a 100k-request run; see the Performance note below).
2. If nothing is pending, jump the clock to the next arrival (S3).
3. Otherwise, loop on `reposition_before_select` until it returns `None` (SCAN-family boundary
   walks / jumps), pulling any new arrivals after each move.
4. Call `select_next`, compute the real service-time breakdown via `disk_model.py`, advance the
   clock, update the request's runtime fields, mark it completed or missed, call `on_completion`.

## Performance note

An early version of the engine rebuilt the "not yet arrived" list by scanning it in full on every
loop iteration — `O(n)` per step, `O(n²)` overall. On a 95,600-request HYBRID run this took **176
seconds**. Replacing the rescan with a single advancing index pointer over the (already
arrival-sorted) request list brought this down by roughly two orders of magnitude.

Two further bottlenecks were found by profiling (`cProfile`) the same benchmark, both fixed:

- **`simulation/aging.py::mark_aged`** rescanned and re-sorted the *entire* best-effort pending
  list on every single dispatch decision. Since the engine only ever appends to `pending` in
  ascending arrival order and never reorders it (only removes from it), the aged prefix can be
  found by a simple early-breaking linear scan instead — no full rescan, no sort.
- **`models/request.py::Request`** is a `@dataclass` with the default field-wise `__eq__`, which
  made `list.remove(req)` in the engine's hot loop do an expensive multi-field comparison against
  every candidate until it found a match. `Request` now sets `eq=False` (identity-based equality),
  since nothing in this codebase ever needs value-equality between two `Request` instances —
  every removal is always by the exact object reference just selected.

Net effect on the same 95,600-request HYBRID benchmark (20 streams, 90% load — a deliberately
adversarial, heavily RT-saturated case where the best-effort queue backs up substantially):
**176s → 31s (arrival-pointer fix) → 22.6s (aging fix) → 15.9s (equality fix)**.

At a realistic, non-saturated load (60% load intensity, ~93,300 requests), every scheduler —
including HYBRID — completes in **under 4 seconds**:

| scheduler | requests | time |
|---|---|---|
| FCFS | 93,300 | 3.49s |
| SSTF | 93,300 | 1.90s |
| SCAN | 93,300 | 2.06s |
| LOOK | 93,300 | 1.82s |
| HYBRID | 93,300 | 3.67s |

The remaining bottleneck under sustained overload is `schedulers/sstf.py`'s `min()` scan over the
current best-effort pending list, which is `O(pending size)` per dispatch — algorithmically
unavoidable without a sorted-by-cylinder structure (e.g. a balanced tree keyed by cylinder,
supporting O(log n) nearest-neighbour lookup) in place of a plain list. That refactor was left as
documented future scope (see the README) rather than done under this project's time budget, since
it only matters in the specific regime where a class's queue is allowed to grow very large — which
is itself a symptom the aging escape hatch and admission control exist to prevent from happening in
a correctly provisioned deployment.

## API result store

`main.py` keeps an in-memory `OrderedDict` of up to 50 runs, evicted LRU. `/api/simulate` stores the
full per-request results; `/api/results/{run_id}` returns just the metrics (the large per-request
list is only served via `/csv` or `/json`, or the first page via `requests_page` in the original
`/api/simulate` response) — this is what keeps `/api/results/{run_id}` cheap even for a 100k-request
run.

## Frontend

React + Vite + TypeScript + Tailwind + Recharts, four pages (`src/pages/`), talking to the FastAPI
backend over `/api/*` (proxied in dev by `vite.config.ts`). The Simulation page animates the
downsampled `timeline_sample` the API returns (≤2000 points) — the frontend never drives the
simulation itself, only replays what the server already computed, per the spec's performance
separation.

## Alignment note — changes made after the project review

After an initial build, the project was reviewed against a separate project-review document
(`docs/project_review.md`) describing a workload-classification-driven approach. Three changes were
made to align with it:

1. **HYBRID's database sub-scheduler switched from C-LOOK to SSTF-with-aging.** The original build
   used C-LOOK (the OS-textbook-standard circular-sweep policy) for best-effort dispatch. The review
   explicitly specifies "an SSTF-style sub-queue with an ageing mechanism to prevent starvation" —
   so `schedulers/hybrid.py` now uses `schedulers/sstf.py` for its BE sub-policy. This is safe
   specifically *because* the aging escape hatch (S13) already guarantees no BE request waits
   unboundedly — plain SSTF without that safety net would be starvation-prone under sustained RT
   pressure, which is exactly the failure mode aging exists to prevent.
2. **A real (non-heuristic) classifier was added** — `workloads/features.py` +
   `simulation/classifier_ml.py` — training a decision tree (benchmarked against an SVM baseline)
   on observable request features, reporting precision/recall/F1 and a confusion matrix. The
   original `workloads/classifier.py` heuristic is kept for comparison but is no longer the primary
   classification mechanism exposed via the API.
3. **A Linux-style Deadline scheduler baseline was added** (`schedulers/deadline.py`,
   `SchedulerName.DEADLINE`) and a **lead-time-before-degradation** metric
   (`simulation/degradation.py`, `POST /api/experiment/degradation`), both named explicitly in the
   review's Objective 4 and Expected Outcome sections.

One consequence worth stating honestly (per this project's own "don't hide losses" instruction, item
8 of the build order): with HYBRID's default parameters, the default multimedia workload (6 streams
at 500 KB/s) already oversaturates the RT round budget even at 20% load intensity — `rt_debt` hits
its clamp within the first few rounds and stays there. In that regime, plain SSTF's unconstrained
"always nearest" dispatch outperforms HYBRID's deadline-miss ratio, because SCAN-EDF's tight
deadline-tolerance grouping (5ms default) forces it to jump between widely separated streams' own
cylinder walks under multi-stream contention, burning more of the RT budget on seeks per request
than SSTF ever does chasing pure proximity. This is a genuine result, not a bug — see the "honest
paragraph" in the README's final deliverable section.
