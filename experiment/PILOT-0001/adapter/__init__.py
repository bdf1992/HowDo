"""PILOT-0001 environment-context adapter.

Outside the install payload by construction. See ``environment.py`` for the
declared dependency on ``howdo.context``.
"""

from .environment import (
    PILOT_ADMISSIBLE,
    FrozenContext,
    FrozenContextError,
    PilotAdmissibilityError,
    ReconReceipt,
    TrialClosure,
    assert_pilot_admissible,
    close_trial_context,
    complete_reconnaissance,
    describe_frozen,
    freeze_context,
    open_trial_context,
)

__all__ = [
    "PILOT_ADMISSIBLE",
    "FrozenContext",
    "FrozenContextError",
    "PilotAdmissibilityError",
    "ReconReceipt",
    "TrialClosure",
    "assert_pilot_admissible",
    "close_trial_context",
    "complete_reconnaissance",
    "describe_frozen",
    "freeze_context",
    "open_trial_context",
]
