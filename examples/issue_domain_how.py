"""The full arc: run a HowDo, issue what it learned, index it, ground it.

`jira_workflow.py` runs the bare kernel. `portable_contract.py` makes the
request's I/O portable. This one closes the loop: the run leaves an artifact
behind, so the next person working the same concern starts from evidence instead
of from scratch.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import (
    Clause,
    Field,
    GateEvidence,
    Host,
    Paradigm,
    RequestContract,
    Rule,
    Shape,
    admit,
    bind,
    ground,
    issue,
    issue_from_run,
    load,
    operate,
    read_index,
    staleness,
)

CONTRACT = RequestContract(
    name="jira.add-status",
    intent="insert a status before an existing one",
    target="jira-workflow",
    path=("apply approved workflow change", "verify resulting statuses"),
    accepts=Shape(fields=(Field("status", type="string"), Field("before", type="string"))),
    expects=Shape(fields=(Field("statuses", type="list", of="string"),)),
    rules=(
        Rule(
            name="approved",
            description="A human approved the workflow mutation",
            clause=Clause(key="approved", op="eq", value=True),
        ),
        Rule(
            name="has-done",
            description="The workflow retains a Done terminal state",
            clause=Clause(key="statuses", op="contains", value="Done"),
            kind="invariant",
        ),
    ),
    requires=("jira.write",),
)

world = {"approved": True, "statuses": ["Open", "In Progress", "Done"]}
paradigm = Paradigm(state={"map": {"statuses": list(world["statuses"])}})

# --- one ordinary run ------------------------------------------------------

bound = bind(CONTRACT, Host("workstation", capabilities=frozenset({"jira.write"})))
resolution = bound.resolve(
    paradigm,
    inputs={"status": "Ready for QA", "before": "Done"},
    expected={"statuses": ["Open", "In Progress", "Ready for QA", "Done"]},
)
admission = admit(resolution, paradigm, GateEvidence(state=dict(world), source="jira-readback"))


def executor(res):
    statuses = list(world["statuses"])
    statuses.insert(statuses.index(res.request.inputs["before"]), res.request.inputs["status"])
    world["statuses"] = statuses
    return {"claimed": "workflow updated"}


outcome = operate(admission, executor)
_observation, residual = bound.observe(
    outcome,
    lambda context: {"statuses": list(context.world["statuses"])},
    world=world,
    observer_name="jira-readback",
)
print("run:", residual.route, "matched =", residual.matched)
print()

# --- what the run leaves behind -------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    store = Path(tmp) / "domains"

    how = issue_from_run(
        resolution,
        residual,
        concern="jira.workflow",
        contract=CONTRACT,
        map={"statuses": list(world["statuses"]), "rule": "approval before mutation"},
    )
    path = issue(how, root=store)
    print("issued:", path.name, "revision", how.revision, "--", how.status)
    print("  the example is the run, not an illustration:", how.example.inputs)
    print()

    print("index:")
    for entry in read_index(root=store):
        print(f"  {entry.concern:16} r{entry.revision}  {entry.status:9} needs {entry.requires}")
        print(f"  {'':16} workflow: {' -> '.join(entry.path)}")
    print()

    # Untested is not a decision you want to build on.
    print("grounded only:", read_index(root=store, status="grounded"))
    print("what a host without jira.write may run:", read_index(root=store, requires=()))
    print()

    promoted = ground("jira.workflow", residual, root=store)
    print("grounded by:", promoted.grounded_by, "at revision", promoted.observed_against)
    print("grounded only:", [e.concern for e in read_index(root=store, status="grounded")])
    print()

    # The kernel fizzles a stale resolution. Storage is where that stops.
    drifted = Paradigm(state=paradigm.state, revision=40)
    report = staleness(load("jira.workflow", root=store), drifted)
    print("staleness:", report.stale)
    print(" ", report.reason)
