# Algorithms — pseudocode for all nine schedulers

All nine implement `select_next(pending, head, now) -> Request | None`. `pending` is only ever
requests that have already arrived — no scheduler ever sees the future.

## FCFS
```
return the pending request with the smallest arrival_time (ties broken by id)
```

## SSTF — Shortest Seek Time First
```
return the pending request with the smallest |cylinder - head|
```

## SCAN
```
state: direction (LEFT/RIGHT), persists across calls

reposition_before_select:
    if nothing pending in current direction:
        if head != disk boundary in current direction: return that boundary  # walk there first
        else: flip direction; return None

select_next:
    return nearest pending request "ahead" in current direction
```

## C-SCAN — circular SCAN
```
state: direction, FIXED for the whole run (never flips)

reposition_before_select:
    if nothing pending in current direction:
        if head != far boundary: return far boundary
        elif head != near boundary (start of sweep): return near boundary   # the "jump"
        else: return None

select_next:
    return nearest pending request "ahead" in current direction
```

## LOOK
```
state: direction, persists

select_next:
    if requests pending ahead: return nearest ahead
    else: flip direction; return nearest ahead in new direction (no boundary walk — LOOK
          reverses at the extreme PENDING request, not the disk edge)
```

## C-LOOK — circular LOOK
```
state: direction, FIXED for the whole run

reposition_before_select:
    if nothing pending ahead and head != nearest pending request on the other side:
        return that request's cylinder   # the jump — no disk-edge travel, unlike C-SCAN

select_next:
    return nearest pending request ahead
```

## EDF — Earliest Deadline First
```
if any pending request has a deadline:
    return the one with the smallest deadline (ties -> id)
else:
    return the pending request with the smallest arrival_time (FCFS among no-deadline requests)
```

## SCAN-EDF
```
if any pending request has a deadline:
    earliest = min(deadline) among deadlined pending requests
    group = all deadlined requests within deadline_tolerance_ms of `earliest`
    return, within `group`, the one nearest to head in the current sweep direction
else:
    FCFS among no-deadline requests
```

## HYBRID
```
roll forward any elapsed rounds (apply debt, open new round, run feedback controller every
    control_window_rounds rounds)

if any BE request has aged past aging_threshold_ms, and this round's aged-dispatch cap
    (max_aged_per_round) isn't yet spent:
        dispatch the oldest aged BE request, regardless of budget

else:
    want_rt = RT pending AND (rt_budget > 0 OR (no BE pending AND work_conserving))
    want_be = BE pending AND (be_budget > 0 OR (no RT pending AND work_conserving))
    if want_rt:  dispatch via SCAN-EDF over RT-pending
    elif want_be: dispatch via C-LOOK over BE-pending
    else: soft fallback — dispatch whichever class still has pending requests, RT preferred
          (see docs/mathematical_model.md for why this fallback exists)

on_completion(request):
    subtract request.service_time from its class's budget (may go negative -> becomes debt
        at the next round boundary)
    record it into the current control window's stats (RT completions/misses, or BE response
        time for the p95 the feedback controller reads)
```

## DEADLINE — Linux-style Deadline scheduler (baseline, added per the project review)
```
state: direction, FIXED for the whole run (sector-sorted sweep, like C-LOOK)
config: read_expire_ms, write_expire_ms

select_next:
    expired = pending requests where (now - arrival_time) >= expire_time_for(request.operation)
    if expired is non-empty: return the oldest one (by arrival_time)   # bounds worst-case latency
    else: return nearest pending request ahead in current direction    # sector-sorted throughput path

reposition_before_select:
    same jump-to-nearest-extreme-pending mechanism as C-LOOK, skipped whenever an expired
    request already exists (no point repositioning if we're about to jump to the expired one anyway)
```

Deliberately simpler than the four-queue real kernel implementation (no back/front-merge, no
`fifo_batch`) — see `schedulers/deadline.py` for the full rationale.
