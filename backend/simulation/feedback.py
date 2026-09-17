"""Feedback controller — S12. Pure function, deterministic, no randomness.
Runs once per control_window rounds and adjusts rt_fraction with hysteresis
(two separate thresholds) so it doesn't oscillate on a single boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class FeedbackDecision:
    rt_fraction: float
    miss_ratio: float
    db_p95: float
    action: str  # "increase_rt" | "decrease_rt" | "unchanged"


def run_feedback_controller(
    rt_fraction: float,
    miss_ratio: float,
    db_p95: float,
    step: float,
    miss_high_threshold: float,
    miss_low_threshold: float,
    db_latency_threshold: float,
    rt_min: float,
    rt_max: float,
) -> FeedbackDecision:
    if miss_ratio > miss_high_threshold:
        new_fraction = rt_fraction + step
        action = "increase_rt"
    elif miss_ratio <= miss_low_threshold and db_p95 > db_latency_threshold:
        new_fraction = rt_fraction - step
        action = "decrease_rt"
    else:
        new_fraction = rt_fraction
        action = "unchanged"

    new_fraction = min(max(new_fraction, rt_min), rt_max)
    return FeedbackDecision(rt_fraction=new_fraction, miss_ratio=miss_ratio, db_p95=db_p95, action=action)
