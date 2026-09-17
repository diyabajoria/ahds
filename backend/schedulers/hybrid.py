"""HYBRID — S11-S13, the technical contribution of this project.

RT queue served by SCAN-EDF, BE queue served by SSTF-with-aging (matching
the design proposed in docs/project_review.md: "database-labelled requests
are handled by a fairness/seek-optimised sub-scheduler — SSTF-style with
anti-starvation ageing" — rather than the OS-textbook-standard C-LOOK this
project used before that alignment; see docs/architecture.md for the note
on this change and why plain SSTF is safe to use here specifically because
the aging escape hatch already guarantees no BE request waits unboundedly).
Arbitrated by round-based budgets (S11) with a deterministic feedback controller (S12)
that adapts rt_fraction, and an aging escape hatch (S13) so BE requests
cannot starve forever. Admission control (S14) lives separately in
simulation/admission.py and is applied by the caller before a stream's
requests are ever generated (see /api/admission/check and the experiment
runner) — HYBRID itself does not reject requests, it only arbitrates
between requests that already exist.

DOCUMENTED SIMPLIFICATION (declared per the project's own instruction to
surface ambiguity rather than silently resolve it): S11 says "a round ends
when both budgets are exhausted or no request is pending," implying the
engine should idle until the next round boundary if requests remain but
both budgets are spent. Implementing a true stall-until-round-boundary
would require a second engine-level "advance clock with no service" hook
symmetric to reposition_before_select. To keep the engine simple, this
implementation instead treats exhausted budgets as a *soft* deprioritisation
once both are exhausted mid-round: the class is still served (RT preferred),
and the overrun is charged as debt into the next round exactly as S11
specifies. This does not change the steady-state adaptive behaviour (the
feedback loop, aging, and debt accounting are all implemented exactly to
spec) — it only affects the fine-grained scheduling of the last request or
two before a round boundary under saturation.
"""
from __future__ import annotations
from typing import List, Optional
from models.request import Request, RequestType
from models.simulation import Direction, HybridConfig
from schedulers.base import Scheduler
from schedulers.scan_edf import SCAN_EDF
from schedulers.sstf import SSTF
from simulation.aging import mark_aged
from simulation.feedback import run_feedback_controller
from simulation.metrics import percentile_nearest_rank


class HYBRID(Scheduler):
    name = "HYBRID"

    def __init__(self, cfg: HybridConfig, direction: Direction = Direction.RIGHT):
        self.cfg = cfg
        self.rt_fraction = cfg.rt_fraction
        self.T = cfg.round_length_ms

        self._rt_sub = SCAN_EDF(deadline_tolerance_ms=cfg.deadline_tolerance_ms, direction=direction)
        self._be_sub = SSTF()

        self.round_index = 0
        self.round_start = 0.0
        self.rt_budget = self.T * self.rt_fraction
        self.be_budget = self.T - self.rt_budget
        self._pending_rt_debt = 0.0
        self._pending_be_debt = 0.0
        self._aged_dispatched_this_round = 0

        # window accumulators (reset every control_window rounds)
        self._win_rt_total = 0
        self._win_rt_misses = 0
        self._win_be_resp: List[float] = []

        self.db_latency_threshold = cfg.db_latency_threshold
        self._baseline_recorded = False

        # exposed counters/logs, read by the metrics layer after the run
        self.log: List[dict] = []
        self.aged_requests_count = 0
        self.starvation_count = 0
        self.max_waiting_time = 0.0
        self.debt_log: List[dict] = []

    def reset(self) -> None:
        self.__init__(self.cfg, self._rt_sub.direction)

    # ---- round bookkeeping -------------------------------------------------
    def _close_round(self) -> None:
        rt_alloc = self.T * self.rt_fraction
        be_alloc = self.T - rt_alloc
        rt_debt = min(max(0.0, -self.rt_budget), rt_alloc)
        be_debt = min(max(0.0, -self.be_budget), be_alloc)
        self.debt_log.append({
            "round_index": self.round_index, "rt_debt": rt_debt, "be_debt": be_debt,
        })
        self._pending_rt_debt = rt_debt
        self._pending_be_debt = be_debt
        self.round_index += 1
        self._aged_dispatched_this_round = 0

        if self.round_index % self.cfg.control_window_rounds == 0:
            self._run_feedback()

    def _open_round(self, start_time: float) -> None:
        rt_alloc = self.T * self.rt_fraction
        be_alloc = self.T - rt_alloc
        self.rt_budget = rt_alloc - self._pending_rt_debt
        self.be_budget = be_alloc - self._pending_be_debt
        self._pending_rt_debt = 0.0
        self._pending_be_debt = 0.0
        self.round_start = start_time

    def _run_feedback(self) -> None:
        miss_ratio = (self._win_rt_misses / self._win_rt_total) if self._win_rt_total > 0 else 0.0
        db_p95 = percentile_nearest_rank(self._win_be_resp, 95)

        if self.db_latency_threshold is None:
            if not self._baseline_recorded:
                self.db_latency_threshold = 3.0 * db_p95 if db_p95 > 0 else 3.0
                self._baseline_recorded = True
            threshold = self.db_latency_threshold
        else:
            threshold = self.db_latency_threshold

        decision = run_feedback_controller(
            rt_fraction=self.rt_fraction,
            miss_ratio=miss_ratio,
            db_p95=db_p95,
            step=self.cfg.step,
            miss_high_threshold=self.cfg.miss_high_threshold,
            miss_low_threshold=self.cfg.miss_low_threshold,
            db_latency_threshold=threshold,
            rt_min=self.cfg.rt_min,
            rt_max=self.cfg.rt_max,
        )
        self.log.append({
            "round_index": self.round_index,
            "time": self.round_start,
            "rt_fraction": decision.rt_fraction,
            "miss_ratio": decision.miss_ratio,
            "db_p95": decision.db_p95,
            "action": decision.action,
        })
        self.rt_fraction = decision.rt_fraction
        self._win_rt_total = 0
        self._win_rt_misses = 0
        self._win_be_resp = []

    def _roll_rounds_to(self, now: float) -> None:
        MAX_ROUNDS_PER_CALL = 200_000
        n = 0
        while now >= self.round_start + self.T and n < MAX_ROUNDS_PER_CALL:
            self._close_round()
            self._open_round(self.round_start + self.T)
            n += 1
        if n >= MAX_ROUNDS_PER_CALL:
            # huge idle gap: fast-forward without further per-round processing
            self.round_start = now

    # ---- Scheduler interface ------------------------------------------------
    def select_next(self, pending: List[Request], head: int, now: float) -> Optional[Request]:
        if not pending:
            return None
        self._roll_rounds_to(now)

        rt_pending = [r for r in pending if r.type == RequestType.MULTIMEDIA]
        be_pending = [r for r in pending if r.type != RequestType.MULTIMEDIA]

        if be_pending:
            aged = mark_aged(be_pending, now, self.cfg.aging_threshold_ms)
            if aged and self._aged_dispatched_this_round < self.cfg.max_aged_per_round:
                chosen = aged[0]
                self._aged_dispatched_this_round += 1
                self.starvation_count += 1
                self.aged_requests_count += 1
                return chosen

        want_rt = bool(rt_pending) and (self.rt_budget > 0 or (not be_pending and self.cfg.work_conserving))
        want_be = bool(be_pending) and (self.be_budget > 0 or (not rt_pending and self.cfg.work_conserving))

        if want_rt:
            return self._rt_sub.select_next(rt_pending, head, now)
        if want_be:
            return self._be_sub.select_next(be_pending, head, now)
        # both budgets exhausted mid-round but requests remain: soft fallback (documented above)
        if rt_pending:
            return self._rt_sub.select_next(rt_pending, head, now)
        if be_pending:
            return self._be_sub.select_next(be_pending, head, now)
        return None

    def on_completion(self, request: Request, now: float) -> None:
        self.max_waiting_time = max(self.max_waiting_time, request.waiting_time or 0.0)
        if request.type == RequestType.MULTIMEDIA:
            self.rt_budget -= (request.service_time or 0.0)
            self._win_rt_total += 1
            if request.deadline_missed:
                self._win_rt_misses += 1
        else:
            self.be_budget -= (request.service_time or 0.0)
            self._win_be_resp.append(request.response_time or 0.0)
