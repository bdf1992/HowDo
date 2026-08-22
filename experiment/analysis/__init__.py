"""Committed analysis for the benchmark experiment.

Written and tested before any real trial exists. An analysis authored after the
data is visible is a choice made with the answer in view, and no amount of care
during the writing removes that.
"""

from .pilot0001 import (
    Outcome,
    PilotAnalysis,
    analyse,
    decide,
    per_task_rates,
    synthetic_trials,
)

__all__ = [
    "Outcome",
    "PilotAnalysis",
    "analyse",
    "decide",
    "per_task_rates",
    "synthetic_trials",
]
