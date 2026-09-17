# Viva questions

## Core scheduling theory

**1. Why not just use EDF for everything?**
EDF ignores seek cost entirely — it will happily jerk the head across the whole disk to chase the
two nearest deadlines even when a same-urgency request sits right next to the head. It also has no
concept of a non-deadlined workload at all: left with OLTP/OLAP traffic mixed in, plain EDF would
starve it indefinitely, since anything without a deadline is only served once nothing deadlined is
pending.

**2. What does SCAN-EDF add over EDF?**
Within the set of requests that are equally urgent (deadlines within `deadline_tolerance_ms` of the
earliest pending one), it picks the nearest to the head instead of an arbitrary one. Two requests
with deadlines 100.0ms and 100.5ms are, for practical purposes, equally urgent — EDF would still
pick whichever has the numerically smaller deadline even if it's across the disk.

**3. Why is service non-preemptive?**
A real disk head can't abandon an in-flight seek or a rotation partway through — there's no
hardware equivalent of a context switch mid-transfer. Modelling it as preemptible would understate
real scheduling cost.

**4. Why does the feedback controller need hysteresis (two thresholds), not one?**
A single threshold sitting right at the boundary between "increase" and "decrease" conditions would
flip `rt_fraction` back and forth every control window as the metric oscillates around that one
value. Two separate thresholds (`miss_high_threshold` to raise, `miss_low_threshold` to allow a
decrease) create a dead zone in between where the controller holds steady.

**5. Why can aging violate the round budget?**
Aging exists specifically to rescue a request that budget-based arbitration has already failed to
serve for a full aging window — if it were still bound by the exhausted budget, it would never
actually get dispatched, defeating the point. It's capped at `max_aged_per_round` so this escape
hatch can't itself swallow an entire round.

**6. Why does everything collapse toward the same performance on SSDs?**
Every seek-optimising scheduler (SCAN, C-SCAN, LOOK, C-LOOK) exists purely to minimize physical
head travel. An SSD has no head — seek time and rotational delay are both zero. The orderings still
differ, but since the thing being optimised no longer costs anything, their measured performance
converges.

**7. What's the difference between SCAN and LOOK?**
SCAN always travels to the physical boundary of the disk before reversing, even if no request is
waiting there. LOOK reverses as soon as there's no pending request further in the current
direction — it "looks" ahead rather than blindly sweeping to the edge.

**8. What's the difference between LOOK and C-LOOK?**
LOOK reverses direction at the extreme pending request. C-LOOK never reverses — it always sweeps
one direction, and on reaching the extreme pending request, jumps directly to the nearest pending
request on the other side and keeps sweeping the same way. This is the "circular" idea — the disk
is treated as if cylinder 0 were adjacent to the last cylinder.

**9. Why would C-SCAN/C-LOOK ever be preferred over SCAN/LOOK if they involve extra jump distance?**
They give more uniform wait times: SCAN/LOOK's request density right near a reversal point gets
served twice in quick succession (once on each pass), while density near the *other* end waits a
full sweep. C-SCAN/C-LOOK trade that unevenness for extra raw head travel.

**10. Why is SSTF not simply "the best" scheduler despite usually having low head movement?**
It can starve a request that happens to sit far from the head if closer requests keep arriving —
there's no fairness or deadline awareness in "always pick nearest."

## HYBRID design

**11. Walk through what happens to a real-time request from arrival to completion under HYBRID.**
It arrives, enters the RT-pending set. At the next scheduling decision, if RT has budget (or BE has
no work and `work_conserving` is on), HYBRID hands the RT-pending set to its internal SCAN-EDF
sub-scheduler, which picks the request based on deadline grouping and head proximity. Once
serviced, `on_completion` subtracts its service time from the RT budget and records whether it hit
its deadline into the current control window's stats.

**12. What happens if RT budget goes negative mid-round?**
It's allowed to (service is non-preemptive, so an in-progress request can't be interrupted when the
budget runs dry mid-service). At round close, the negative amount becomes debt, clamped to at most
one full round's allocation, and is subtracted from that class's budget in the *next* round.

**13. Why clamp debt to one round's allocation?**
Otherwise a single very long request could create debt that takes multiple future rounds to repay,
effectively locking a class out for an extended stretch — the clamp bounds how much of a future
round any one overrun can consume.

**14. What is `work_conserving` actually for?**
Without it, a class with budget but no pending work would simply waste that budget while the other
class might have a backlog. With it on, the class with no eligible work yields its slot to the
other class instead of idling the disk.

**15. How does the admission controller decide whether to accept a new multimedia stream?**
It estimates the disk's effective bandwidth per request (accounting for the average seek + rotation
+ transfer overhead, not just raw transfer rate), takes `rt_max` of that as the reservable pool, and
checks whether the new stream's bitrate plus everything already reserved still fits.

**16. Why is only `rt_max` of effective bandwidth reservable, not all of it?**
Reserving 100% for RT streams would leave nothing to guarantee for best-effort traffic even in the
average case — `rt_max` is the same ceiling the feedback controller itself is not allowed to exceed
when raising `rt_fraction`.

## Metrics

**17. Why Jain's fairness index specifically?**
It's bounded in [1/n, 1] regardless of the number of classes, scale-independent (doubling every
class's throughput doesn't change J), and has an intuitive worst case (one class gets everything ->
J = 1/n) and best case (equal throughput -> J = 1) that are easy to sanity-check in a test.

**18. Why nearest-rank percentiles rather than linear interpolation?**
Nearest-rank always returns an actual observed sample rather than an interpolated value between two
samples — for a metric like "p99 response time," reporting a value nobody actually experienced can
be misleading in a systems context.

**19. Why is a "MISSED" request still serviced rather than dropped?**
This is a soft real-time system by design (S6) — a late multimedia frame is still worth decoding
late rather than not at all, unlike a hard real-time system where a miss might mean discarding the
work entirely.

**20. Why track both `waiting_time` and `response_time` separately?**
`waiting_time` isolates queueing delay (arrival to start of service); `response_time` is the
end-to-end experience (arrival to completion). A scheduler could have low waiting time but high
response time if it dispatches quickly but the service itself (large sequential transfer) is slow —
the two numbers separate scheduling quality from raw disk throughput.

## Workload modelling

**21. Why Zipfian cylinder hot-spots for OLTP?**
Real transactional workloads are rarely uniform across storage — a small number of "hot" rows/pages
get disproportionately more access. Zipf's law is the standard model for that kind of skew.

**22. Why does OLAP model scans as bursts of adjacent-cylinder requests rather than one big request?**
It mirrors how a real sequential scan actually issues I/O — many smaller reads/writes to
consecutive blocks — which is also what lets the scheduler's ordering logic (which operates on
individual requests) actually have something to reorder within a scan.

**23. What does `sequentiality` control in the multimedia generator?**
The probability that the next request in a stream targets the very next cylinder versus jumping to
a uniformly random one — modelling how contiguous a stream's on-disk layout is.

**24. Why is the heuristic classifier explicitly *not* called machine learning?**
It's a fixed set of if/else rules on size, deadline presence, and similar features — calling it "AI"
or "ML" would overstate what it does and make its accuracy (reported via an explicit confusion
matrix) misleading to interpret.

## Engineering / determinism

**25. How is full determinism (same seed -> identical output) actually guaranteed?**
Every random draw across every workload generator flows through one `numpy.random.Generator`
created once per run, seeded from the config — no code path anywhere calls the global `random`
module or bare `np.random.*` functions, which would silently reintroduce hidden global state.

**26. How is it verified that every scheduler in a comparison saw the exact same input requests?**
`/api/compare` and the experiment runner generate the workload list once, then pass a `deepcopy` of
it into each scheduler's run. A test spies on the orchestrator and asserts the request id/cylinder
sequence is byte-identical across all schedulers in one comparison call.

**27. Why deepcopy rather than just regenerating with the same seed for each scheduler?**
Deepcopy is strictly stronger — it removes any possibility that a generator implementation detail
(e.g. an accidental shared mutable default) causes two "identical seed" runs to diverge; the actual
runtime engine also mutates request objects in place (setting completion time, status, etc.), so
each scheduler run needs its own independent copy regardless.

**28. What was the actual performance bug found in this project, and how was it caught?**
The engine originally rebuilt its "not yet arrived" list by scanning the full remaining list on
every simulation step, making the whole run O(n²). On a ~95,600-request HYBRID benchmark this took
176 seconds. It was caught by literally running the 100k-request benchmark called for in the spec,
not by code review — replacing it with a single advancing index pointer (since arrivals are
pre-sorted) fixed it.

**29. Why is the frontend never allowed to drive the simulation itself?**
The spec requires the server to run the full simulation to completion first, returning a
downsampled timeline (≤2000 points) for the browser to animate. If the browser tried to compute
each step live, a 100k-request run would freeze the tab; the animation is a replay of already-computed
results, not a live computation.

**30. Why cap the in-memory result store at 50 runs with LRU eviction rather than a database?**
The spec explicitly calls for no database — JSON config in, CSV/JSON export out — and a 50-entry
LRU cache is enough to support "go back and compare a couple of recent runs" without unbounded
memory growth across a long session.

**31. What happens to a scheduler if `select_next` returns `None` while requests are still pending?**
The engine treats it as a stall-avoidance case: if there are still unarrived requests, it jumps the
clock forward to the next arrival and retries; otherwise it breaks out of the loop rather than
spinning forever. In practice, none of the nine implemented schedulers ever legitimately return
`None` with non-empty pending input — every `select_next` either returns a request or is guaranteed
non-empty input by its caller.

**32. Why does `HybridConfig` validate `rt_min < rt_max` at the Pydantic layer instead of at runtime in the scheduler?**
Catching an invalid configuration at the API boundary (422, before any simulation work starts) is
strictly better than discovering it mid-run — it's also what keeps `/api/simulate` from ever
returning a 500 on a structurally invalid request.

## Added per the project review alignment

**33. Why switch HYBRID's database sub-scheduler from C-LOOK to SSTF?**
The project review's stated design explicitly calls for "an SSTF-style sub-queue with an ageing
mechanism to prevent starvation" for the database class. Plain SSTF alone is starvation-prone (it
will happily ignore a far request forever if closer ones keep arriving), but HYBRID's aging escape
hatch (S13) already guarantees no BE request waits past `aging_threshold_ms` regardless of which
base policy sits underneath it — which is exactly what makes it safe to use the simpler, more
seek-greedy SSTF here instead of C-LOOK.

**34. Why is the classifier a real decision tree now instead of a heuristic?**
The project review's Objective 1 and its Expected Outcome table explicitly call for a trained model
reporting precision/recall/F1 — a fixed if/else heuristic has no notion of a train/test split or a
confusion matrix to report, so it can't produce those numbers meaningfully. The original heuristic
is kept in the codebase for comparison but is no longer what the primary `/api/classifier/train`
endpoint uses.

**35. Why compare the decision tree against an SVM specifically, rather than some other baseline?**
That's the specific baseline the review's methodology names. An SVM (with standardised features) is
also a reasonable choice methodologically: it's a fundamentally different kind of decision boundary
(a fitted hyperplane/kernel surface vs. a decision tree's axis-aligned splits), so if both reach
similar precision/recall it's evidence the classes are genuinely well-separated by the chosen
features, not an artifact of one particular model family.

**36. Why does the classifier only ever see two classes (Multimedia vs Database) when the engine
tracks three request types (Multimedia, OLTP, OLAP)?**
The review's problem statement defines exactly two classes, M and D — OLTP and OLAP are merged into
"Database" for the classifier's label, even though the scheduling engine underneath still treats
them as separate request types for metrics purposes (throughput, IOPS, etc. are still reported per
type).

**37. What does "lead-time-before-degradation" actually tell you that a single load-test doesn't?**
A single load point can't distinguish "HYBRID is always better" from "HYBRID is better only in a
specific load range." Sweeping load and tracking where HYBRID's advantage over the best static
baseline stops improving (or starts shrinking) gives a concrete, defensible answer to "up to what
load is this design actually worth deploying" — useful for capacity planning, which is exactly the
motivation the review gives for including it.

**38. The Linux Deadline scheduler here is simplified — what's missing compared to the real kernel
implementation, and does it matter for this comparison?**
Real Linux tracks four queues (two sector-sorted, two FIFO, one per read/write) with request
merging (`front_merge`/`back_merge`) and a `fifo_batch` size limiting how many requests get pulled
from the sorted queue before rechecking expiry. This implementation keeps the two properties that
matter for the comparison this project makes — location-aware throughput via a sector-sorted sweep,
and a hard bound on worst-case latency via per-operation expiry — while dropping the merge logic,
since this simulator's request model doesn't represent physically adjacent I/Os as mergeable in the
first place.
