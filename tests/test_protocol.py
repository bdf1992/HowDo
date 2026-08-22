"""Compatibility tests for the proposed protocol boundary (PROTOCOL.md).

These pin the *shape* of the public surface, not its behavior — behavior is
the rest of the suite's job. The policy under test: names and fields may be
added, never silently removed or renamed; vocabularies may grow, never shrink;
a serialized record with a version this host does not know is refused rather
than partially read.
"""

import dataclasses
import sys
import typing
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "plugin"
sys.path.insert(0, str(PAYLOAD / "runtime"))

import howdo  # noqa: E402
from howdo import (  # noqa: E402
    CONTRACT_VERSION,
    DOMAIN_VERSION,
    ContractError,
    DomainError,
    DomainHow,
    RequestContract,
    Shape,
    WorkedExample,
)
from howdo.context import ContextState  # noqa: E402
from howdo.core import Agency, Route  # noqa: E402

# The names PROTOCOL.md declares public. A removal or rename fails here; an
# addition passes, and belongs in PROTOCOL.md's next revision.
KERNEL_NAMES = {
    "Paradigm", "Request", "Check", "GateEvidence", "Resolution", "Fizzle",
    "Admission", "Outcome", "Observation", "ObservationContext", "Residual",
    "Settlement", "ExecutionError",
    "resolve", "admit", "operate", "observe", "settle",
}
CONTEXT_NAMES = {
    "ContextStatus", "ContextKindError", "ContextLockError",
    "PayloadContextError", "TemplateContextError",
    "inspect_context", "ensure_context", "complete_onboarding",
    "decline_onboarding", "defer_onboarding", "fork_context",
    "resolve_context_path", "default_store_path", "new_context_id",
    "payload_root", "is_plugin_payload", "is_shared",
}
CONTRACT_NAMES = {
    "RequestContract", "BoundContract", "Clause", "ContractError", "Field",
    "Host", "Rule", "Shape", "Unsupported", "bind", "CONTRACT_VERSION",
}
DOMAIN_NAMES = {
    "DomainHow", "DomainError", "IndexEntry", "Staleness", "WorkedExample",
    "issue", "issue_from_run", "ground", "revise", "load", "read_index",
    "reindex", "staleness", "DOMAIN_VERSION",
}

FIELDS = {
    "Paradigm": {"state", "revision", "paradigm_id"},
    "Request": {"handle", "intent", "target", "actor", "mutates",
                "crosses_boundary", "inputs"},
    "Check": {"name", "description", "predicate", "kind"},
    "GateEvidence": {"state", "source", "observed_at", "evidence_id"},
    "Resolution": {"request", "paradigm_id", "paradigm_revision",
                   "resolved_state", "path", "expected", "checks",
                   "resolution_id"},
    "Fizzle": {"resolution", "failed_checks", "reason", "route",
               "evidence_source"},
    "Admission": {"resolution", "passed_checks", "evidence_id",
                  "evidence_source", "evidence_observed_at", "admitted_at",
                  "admission_id", "consumed"},
    "Outcome": {"admission", "reported", "started_at", "finished_at", "error",
                "outcome_id"},
    "Observation": {"outcome_id", "observed", "observer_name", "observed_at",
                    "observation_id"},
    "Residual": {"resolution", "observation", "matched", "route", "expected",
                 "observed", "failed_invariants", "note", "residual_id"},
    "Settlement": {"residual", "accepted", "paradigm", "changed",
                   "changed_layers", "reason", "settlement_id"},
}

ROUTES = {"none", "precondition", "postcondition", "rendering",
          "hidden_postcondition", "invariant", "contract"}
AGENCIES = {"user", "assistant", "joint", "external", "unspecified"}
CONTEXT_STATES = {"missing", "template", "onboarding_required",
                  "reconnaissance_required", "ready", "deferred", "declined",
                  "fork_required", "expired", "invalid"}


def _harmless_contract(**overrides) -> RequestContract:
    kwargs = dict(
        name="probe.read",
        intent="read a value",
        path=("read",),
        mutates=False,
        crosses_boundary=False,
        accepts=Shape(),
        expects=Shape(),
    )
    kwargs.update(overrides)
    return RequestContract(**kwargs)


class ExportedSurfaceTests(unittest.TestCase):
    def test_public_names_are_exported_and_declared(self):
        declared = set(howdo.__all__)
        for group in (KERNEL_NAMES, CONTEXT_NAMES, CONTRACT_NAMES, DOMAIN_NAMES):
            for name in sorted(group):
                self.assertTrue(hasattr(howdo, name), f"howdo.{name} is gone")
                self.assertIn(name, declared, f"{name} missing from __all__")

    def test_protocol_objects_keep_their_fields(self):
        for cls_name, expected in FIELDS.items():
            actual = {f.name for f in dataclasses.fields(getattr(howdo, cls_name))}
            missing = expected - actual
            self.assertFalse(
                missing, f"{cls_name} lost protocol fields: {sorted(missing)}"
            )

    def test_vocabularies_may_grow_but_never_shrink(self):
        for alias, expected in (
            (Route, ROUTES), (Agency, AGENCIES), (ContextState, CONTEXT_STATES)
        ):
            actual = set(typing.get_args(alias))
            missing = expected - actual
            self.assertFalse(missing, f"vocabulary lost values: {sorted(missing)}")


class FormatVersionTests(unittest.TestCase):
    def test_each_persisted_artifact_carries_its_own_version(self):
        self.assertEqual(DOMAIN_VERSION, 1)
        self.assertEqual(CONTRACT_VERSION, 1)
        template = (PAYLOAD / "CONTEXT.template.md").read_text(encoding="utf-8")
        self.assertIn('howdo_context: "2"', template)

    def test_an_unknown_domain_how_version_is_refused_not_partially_read(self):
        with self.assertRaisesRegex(DomainError, "does not know"):
            DomainHow(
                concern="probe.read",
                map={"target": "a value"},
                contract=_harmless_contract(),
                example=WorkedExample(),
                version=DOMAIN_VERSION + 998,
            )

    def test_an_unknown_contract_version_is_refused_not_partially_read(self):
        data = _harmless_contract().as_dict()
        data["version"] = CONTRACT_VERSION + 998
        with self.assertRaises(ContractError):
            RequestContract.from_dict(data)

    def test_an_unknown_key_in_a_loaded_contract_is_refused_not_dropped(self):
        data = _harmless_contract().as_dict()
        data["telemetry"] = {"endpoint": "https://nowhere"}
        with self.assertRaises(ContractError):
            RequestContract.from_dict(data)


class DocumentTests(unittest.TestCase):
    def test_the_boundary_document_exists_and_names_this_suite(self):
        doc = (ROOT / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("tests/test_protocol.py", doc)
        # The open decision stays visibly open until somebody adopts it.
        self.assertIn("howdo_context", doc)


if __name__ == "__main__":
    unittest.main()
