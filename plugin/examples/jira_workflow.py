"""Tiny example: change a Jira-like workflow only after approval, then verify it."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import Check, GateEvidence, Paradigm, Request, admit, observe, operate, resolve, settle


world = {
    "approved": True,
    "statuses": ["Open", "In Progress", "Done"],
}

paradigm = Paradigm(
    state={
        "map": {"statuses": list(world["statuses"])},
        "path": ["inspect", "propose", "approve", "apply", "verify"],
        "rule": "workflow mutation requires explicit approval",
    }
)

request = Request(
    handle="do work",
    intent="add Ready for QA before Done",
    target="jira-workflow",
    mutates=True,
    crosses_boundary=True,
)

resolution = resolve(
    request,
    paradigm,
    path=["apply approved workflow change", "verify resulting statuses"],
    expected={"statuses": ["Open", "In Progress", "Ready for QA", "Done"]},
    checks=[
        Check(
            name="approved",
            description="A human approved the workflow mutation",
            predicate=lambda state: state.get("approved") is True,
        ),
        Check(
            name="has-done",
            description="The workflow retains a Done terminal state",
            predicate=lambda state: "Done" in state.get("statuses", []),
            kind="invariant",
        ),
    ],
)

evidence = GateEvidence(
    state={"approved": world["approved"], "statuses": list(world["statuses"])},
    source="jira-workflow-readback",
)
admission = admit(resolution, paradigm, evidence)
if not hasattr(admission, "admission_id"):
    print("FIZZLE", admission.route, admission.reason, admission.failed_checks)
    raise SystemExit(1)


def executor(_resolution):
    world["statuses"] = ["Open", "In Progress", "Ready for QA", "Done"]
    return {"claimed": "workflow updated"}


outcome = operate(admission, executor)
observation, residual = observe(
    outcome,
    lambda context: {"statuses": list(context.world["statuses"])},
    world=world,
    observer_name="jira-readback",
)


def patch(state):
    state["map"]["statuses"] = list(world["statuses"])
    return state


settlement = settle(
    paradigm,
    residual,
    accept=True,
    patch=patch,
    reason="verified workflow now contains Ready for QA",
)

print("gate:", "open", "via", admission.evidence_source)
print("executor report:", outcome.reported)
print("observed:", observation.observed)
print("residual:", residual.route, "matched=", residual.matched)
print("revision:", paradigm.revision, "->", settlement.paradigm.revision)
print("changed layers:", settlement.changed_layers)
print("saved map:", settlement.paradigm.state["map"])
