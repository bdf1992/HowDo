"""One contract, written once as data, offered to two different hosts.

`jira_workflow.py` runs the same operation against the bare kernel. There the
path, the predicted shape, and the checks are Python objects: real, but stuck in
this process. Here they are a JSON document, so the obligations survive the trip
and a host that cannot meet them says so before anything runs.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import (
    AUTHORITY_READONLY,
    GateEvidence,
    Host,
    Paradigm,
    RequestContract,
    Unsupported,
    admit,
    bind,
    operate,
    settle,
)


# --- what ships between environments --------------------------------------

CONTRACT = json.dumps(
    {
        "version": 1,
        "name": "jira.add-status",
        "handle": "do work",
        "intent": "insert a status before an existing one",
        "target": "jira-workflow",
        "actor": "joint",
        "mutates": True,
        "crosses_boundary": True,
        "path": ["apply approved workflow change", "verify resulting statuses"],
        "accepts": {
            "fields": [
                {"name": "status", "type": "string", "description": "the status to insert"},
                {"name": "before", "type": "string", "description": "the status it precedes"},
            ],
            "closed": True,
        },
        "expects": {
            "fields": [{"name": "statuses", "type": "list", "of": "string"}],
            "closed": False,
        },
        "rules": [
            {
                "name": "approved",
                "description": "A human approved the workflow mutation",
                "kind": "precondition",
                "clause": {"key": "approved", "op": "eq", "value": True},
            },
            {
                "name": "has-done",
                "description": "The workflow retains a Done terminal state",
                "kind": "invariant",
                "clause": {"key": "statuses", "op": "contains", "value": "Done"},
            },
        ],
        "requires": ["jira.write"],
    }
)

contract = RequestContract.from_json(CONTRACT)
print("contract:", contract.name, "digest", contract.digest()[:12])
print("requires:", ", ".join(contract.requires))
print()


# --- the same contract, three hosts ----------------------------------------

hosts = [
    Host(name="workstation", capabilities=frozenset({"jira.write", "fs.write"})),
    Host(name="reviewer-sandbox", capabilities=frozenset({"jira.write"}),
         authority=AUTHORITY_READONLY),
    Host(name="docs-runner", capabilities=frozenset({"fs.write"})),
]

runnable = None
for host in hosts:
    bound = bind(contract, host)
    if isinstance(bound, Unsupported):
        print(f"{host.name:18} unsupported -- {bound.reason}")
    else:
        print(f"{host.name:18} bound")
        runnable = runnable or bound
print()

assert runnable is not None


# --- the loop, on the host that can actually run it ------------------------

world = {"approved": True, "statuses": ["Open", "In Progress", "Done"]}
paradigm = Paradigm(state={"map": {"statuses": list(world["statuses"])}, "rule": "approval first"})

resolution = runnable.resolve(
    paradigm,
    inputs={"status": "Ready for QA", "before": "Done"},
    expected={"statuses": ["Open", "In Progress", "Ready for QA", "Done"]},
)
print("inputs are declared, not smuggled:", dict(resolution.request.inputs))
print("gate rules travelled with the contract:", [c.name for c in resolution.checks])

admission = admit(
    resolution,
    paradigm,
    GateEvidence(state=dict(world), source="jira-workflow-readback"),
)
assert hasattr(admission, "admission_id"), admission


def executor(res):
    """Reads its arguments off the resolution rather than off this closure."""
    statuses = list(world["statuses"])
    statuses.insert(statuses.index(res.request.inputs["before"]), res.request.inputs["status"])
    world["statuses"] = statuses
    return {"claimed": "workflow updated"}


outcome = operate(admission, executor)
observation, residual = runnable.observe(
    outcome,
    lambda context: {"statuses": list(context.world["statuses"])},
    world=world,
    observer_name="jira-readback",
)
print("observed:", observation.observed)
print("residual:", residual.route, "matched=", residual.matched)

settlement = settle(
    paradigm,
    residual,
    accept=residual.matched,
    patch=lambda state: {**state, "map": {"statuses": list(observation.observed["statuses"])}},
    reason="verified against the declared shape",
)
print("revision:", paradigm.revision, "->", settlement.paradigm.revision)
print()


# --- what the shape check is for -------------------------------------------

_, bad_residual = runnable.observe(
    operate(
        admit(
            runnable.resolve(
                settlement.paradigm,
                inputs={"status": "Blocked", "before": "Done"},
                expected={"statuses": ["Open", "In Progress", "Blocked", "Ready for QA", "Done"]},
            ),
            settlement.paradigm,
            GateEvidence(state=dict(world), source="jira-workflow-readback"),
        ),
        lambda _res: {"claimed": "workflow updated"},
    ),
    # A host that answers with a summary string instead of the declared list.
    lambda context: {"statuses": ", ".join(context.world["statuses"])},
    world=world,
    observer_name="chatty-readback",
)
print("shape disagreement:", bad_residual.route)
print(bad_residual.note)
print("-> not a postcondition residual: nothing was actually compared.")
