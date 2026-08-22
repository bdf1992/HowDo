"""Request-contract invariants.

Each test is named for the promise whose breaking it would report. The subject
is portability: a contract has to state the same obligations after it leaves the
process that wrote it, and a host has to be able to refuse it before anything
runs.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import (  # noqa: E402
    AUTHORITY_READONLY,
    AUTHORITY_WRITABLE,
    BoundContract,
    Check,
    Clause,
    ContractError,
    Field,
    GateEvidence,
    Host,
    Paradigm,
    RequestContract,
    Rule,
    Shape,
    Unsupported,
    admit,
    bind,
    observe,
    operate,
    settle,
)


def a_contract(**overrides) -> RequestContract:
    """The worked example from the repo, stated as data instead of closures."""

    kwargs = dict(
        name="jira.add-status",
        intent="add Ready for QA before Done",
        target="jira-workflow",
        path=("apply approved workflow change", "verify resulting statuses"),
        mutates=True,
        crosses_boundary=True,
        accepts=Shape(
            fields=(
                Field("status", type="string", description="the status to insert"),
                Field("before", type="string", description="the status it precedes"),
            )
        ),
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
    kwargs.update(overrides)
    return RequestContract(**kwargs)


def a_host(**overrides) -> Host:
    kwargs = dict(
        name="local", capabilities=frozenset({"jira.write"}), authority=AUTHORITY_WRITABLE
    )
    kwargs.update(overrides)
    return Host(**kwargs)


def a_paradigm() -> Paradigm:
    return Paradigm(state={"map": {"statuses": ["Open", "Done"]}, "path": ["apply", "verify"]})


class PortabilityTests(unittest.TestCase):
    """A contract that only means something in the process that built it is not one."""

    def test_a_contract_round_trips_through_json_unchanged(self):
        original = a_contract()
        restored = RequestContract.from_json(original.to_json())
        self.assertEqual(original, restored)
        self.assertEqual(original.digest(), restored.digest())

    def test_the_digest_commits_to_rule_order(self):
        """Order is cheap to record and impossible to recover after the fact."""
        original = a_contract()
        swapped = a_contract(rules=tuple(reversed(original.rules)))
        self.assertNotEqual(original.digest(), swapped.digest())

    def test_the_digest_commits_to_the_canonicalization_version(self):
        """Without it a historical digest cannot be told from a re-serialized one."""
        self.assertIn(b'"version":1', a_contract().canonical_bytes())

    def test_a_contract_from_a_future_version_is_refused_not_guessed_at(self):
        data = a_contract().as_dict()
        data["version"] = 99
        with self.assertRaises(ContractError):
            RequestContract.from_dict(data)

    def test_unknown_keys_are_refused_rather_than_dropped(self):
        """A key nobody reads means one thing in the file and another in the host."""
        data = a_contract().as_dict()
        data["retries"] = 3
        with self.assertRaises(ContractError):
            RequestContract.from_dict(data)

    def test_a_clause_operand_that_cannot_serialize_is_refused(self):
        with self.assertRaises(ContractError):
            Clause(key="approved", op="eq", value=object())

    def test_an_unknown_operator_is_refused_at_load(self):
        with self.assertRaises(ContractError):
            Clause.from_dict({"key": "x", "op": "matches_regex", "value": "^a"})

    def test_an_operator_that_reads_no_value_refuses_one(self):
        """A silently ignored operand looks load-bearing to the next reader."""
        with self.assertRaises(ContractError):
            Clause(key="x", op="present", value=True)


class ContractStatementTests(unittest.TestCase):
    """What a contract must say before it is allowed to travel."""

    def test_a_consequential_contract_must_declare_its_result_shape(self):
        with self.assertRaises(ContractError):
            a_contract(expects=Shape())

    def test_a_consequential_contract_must_carry_its_own_precondition(self):
        """A gate the host happens to supply does not travel with the contract."""
        invariant_only = (a_contract().rules[1],)
        with self.assertRaises(ContractError):
            a_contract(rules=invariant_only)

    def test_an_observation_only_contract_needs_neither(self):
        contract = a_contract(
            mutates=False, crosses_boundary=False, expects=Shape(), rules=(), requires=()
        )
        self.assertFalse(contract.consequential)

    def test_a_contract_declares_the_path_it_follows(self):
        with self.assertRaises(ContractError):
            a_contract(path=())

    def test_duplicate_rule_names_are_refused(self):
        rule = a_contract().rules[0]
        with self.assertRaises(ContractError):
            a_contract(rules=(rule, rule))


class ShapeTests(unittest.TestCase):
    """The shape check exists to catch disagreement, so it must not be lenient."""

    def test_a_boolean_does_not_satisfy_an_integer_field(self):
        """bool subclasses int in Python; a flag is not a count."""
        shape = Shape(fields=(Field("attempts", type="integer"),))
        self.assertTrue(shape.violations({"attempts": True}))
        self.assertFalse(shape.violations({"attempts": 3}))

    def test_element_types_are_checked(self):
        shape = Shape(fields=(Field("statuses", type="list", of="string"),))
        self.assertFalse(shape.violations({"statuses": ["Open", "Done"]}))
        self.assertTrue(shape.violations({"statuses": ["Open", 7]}))

    def test_an_optional_field_may_be_absent_but_not_wrong(self):
        shape = Shape(fields=(Field("note", type="string", required=False),))
        self.assertFalse(shape.violations({}))
        self.assertTrue(shape.violations({"note": 7}))

    def test_a_closed_shape_refuses_undeclared_keys(self):
        shape = Shape(fields=(Field("statuses", type="list"),), closed=True)
        self.assertFalse(shape.violations({"statuses": []}))
        self.assertTrue(shape.violations({"statuses": [], "debug": 1}))

    def test_an_open_shape_allows_extra_keys(self):
        shape = Shape(fields=(Field("statuses", type="list"),))
        self.assertFalse(shape.violations({"statuses": [], "debug": 1}))

    def test_duplicate_keys_are_refused(self):
        with self.assertRaises(ContractError):
            Shape(fields=(Field("x"), Field("x")))


class ClauseTests(unittest.TestCase):
    """A portable predicate must behave like Check.evaluate: fail closed."""

    def test_a_clause_that_raises_fails_closed(self):
        self.assertFalse(Clause(key="n", op="gt", value=1).evaluate({"n": "not a number"}))

    def test_a_missing_key_is_absent_rather_than_an_error(self):
        self.assertTrue(Clause(key="n", op="absent").evaluate({}))
        self.assertFalse(Clause(key="n", op="present").evaluate({}))
        self.assertFalse(Clause(key="n", op="eq", value=1).evaluate({}))

    def test_a_dotted_key_reaches_into_nested_state(self):
        state = {"map": {"statuses": ["Open", "Done"]}}
        self.assertTrue(Clause(key="map.statuses", op="contains", value="Done").evaluate(state))
        self.assertFalse(Clause(key="map.missing", op="present").evaluate(state))


class BindingTests(unittest.TestCase):
    """Loadability is a result you can read, not a failure you hit mid-operation."""

    def test_a_host_missing_a_capability_is_unsupported_before_anything_resolves(self):
        outcome = bind(a_contract(), a_host(capabilities=frozenset()))
        self.assertIsInstance(outcome, Unsupported)
        self.assertEqual(outcome.missing_capabilities, ("jira.write",))

    def test_a_consequential_contract_is_unsupported_on_a_readonly_host(self):
        outcome = bind(a_contract(), a_host(authority=AUTHORITY_READONLY))
        self.assertIsInstance(outcome, Unsupported)
        self.assertIn(AUTHORITY_READONLY, outcome.reason)

    def test_an_observation_only_contract_binds_to_a_readonly_host(self):
        contract = a_contract(
            mutates=False, crosses_boundary=False, expects=Shape(), rules=(), requires=()
        )
        self.assertIsInstance(bind(contract, a_host(authority=AUTHORITY_READONLY)), BoundContract)

    def test_one_contract_binds_into_two_different_hosts(self):
        """The portability claim, end to end: same bytes, same digest, two hosts."""
        shipped = a_contract().to_json()
        first = RequestContract.from_json(shipped)
        second = RequestContract.from_json(shipped)
        self.assertEqual(first.digest(), second.digest())
        self.assertIsInstance(bind(first, a_host(name="local")), BoundContract)
        self.assertIsInstance(
            bind(second, a_host(name="ci", capabilities=frozenset({"jira.write", "fs.write"}))),
            BoundContract,
        )


class ResolutionTests(unittest.TestCase):
    """The declared I/O is checked at the door, not after the operation ran."""

    def _bound(self, **overrides) -> BoundContract:
        bound = bind(a_contract(**overrides), a_host())
        self.assertIsInstance(bound, BoundContract)
        return bound

    def test_inputs_that_violate_the_accepted_shape_are_refused(self):
        with self.assertRaises(ContractError):
            self._bound().resolve(
                a_paradigm(),
                inputs={"status": "Ready for QA"},  # `before` is declared and required
                expected={"statuses": ["Open", "Done"]},
            )

    def test_expected_that_violates_the_promised_shape_is_refused(self):
        with self.assertRaises(ContractError):
            self._bound().resolve(
                a_paradigm(),
                inputs={"status": "Ready for QA", "before": "Done"},
                expected={"statuses": "Done"},
            )

    def test_declared_inputs_reach_the_executor_instead_of_a_closure(self):
        resolution = self._bound().resolve(
            a_paradigm(),
            inputs={"status": "Ready for QA", "before": "Done"},
            expected={"statuses": ["Open", "Ready for QA", "Done"]},
        )
        self.assertEqual(resolution.request.inputs["status"], "Ready for QA")

    def test_request_inputs_are_snapshotted_against_later_mutation(self):
        inputs = {"status": "Ready for QA", "before": "Done"}
        resolution = self._bound().resolve(
            a_paradigm(), inputs=inputs, expected={"statuses": ["Open", "Done"]}
        )
        inputs["status"] = "tampered"
        self.assertEqual(resolution.request.inputs["status"], "Ready for QA")

    def test_host_supplied_checks_add_to_the_contracts_rules_and_cannot_replace_them(self):
        extra = Check(name="local-only", description="host check", predicate=lambda state: True)
        resolution = self._bound().resolve(
            a_paradigm(),
            inputs={"status": "Ready for QA", "before": "Done"},
            expected={"statuses": ["Open", "Done"]},
            checks=(extra,),
        )
        names = [check.name for check in resolution.checks]
        self.assertEqual(names, ["approved", "has-done", "local-only"])

    def test_a_compiled_rule_closes_the_gate_exactly_as_a_python_check_would(self):
        paradigm = a_paradigm()
        resolution = self._bound().resolve(
            paradigm,
            inputs={"status": "Ready for QA", "before": "Done"},
            expected={"statuses": ["Open", "Ready for QA", "Done"]},
        )
        fizzle = admit(
            resolution,
            paradigm,
            GateEvidence(state={"approved": False, "statuses": ["Open", "Done"]}, source="readback"),
        )
        self.assertEqual(fizzle.route, "precondition")
        self.assertIn("approved", fizzle.failed_checks)


class ObservationRoutingTests(unittest.TestCase):
    """A result that cannot be compared is not a result that came out wrong."""

    def _run(self, observed, *, expected=("Open", "Ready for QA", "Done")):
        paradigm = a_paradigm()
        bound = bind(a_contract(), a_host())
        resolution = bound.resolve(
            paradigm,
            inputs={"status": "Ready for QA", "before": "Done"},
            expected={"statuses": list(expected)},
        )
        admission = admit(
            resolution,
            paradigm,
            GateEvidence(state={"approved": True, "statuses": ["Open", "Done"]}, source="readback"),
        )
        outcome = operate(admission, lambda _resolution: {"claimed": "updated"})
        return paradigm, bound.observe(
            outcome, lambda context: dict(context.world), world=observed, observer_name="readback"
        )

    def test_a_shape_mismatch_routes_to_contract_not_postcondition(self):
        _paradigm, (_observation, residual) = self._run({"statuses": "Done"})
        self.assertEqual(residual.route, "contract")
        self.assertFalse(residual.matched)
        self.assertIn("shape residual", residual.note)

    def test_a_conforming_but_wrong_result_still_routes_to_postcondition(self):
        _paradigm, (_observation, residual) = self._run({"statuses": ["Open", "Done"]})
        self.assertEqual(residual.route, "postcondition")

    def test_an_invariant_residual_outranks_a_shape_residual(self):
        """The paradigm is already unsafe to continue under; settle must keep refusing."""
        _paradigm, (_observation, residual) = self._run({"statuses": "Open"})
        self.assertEqual(residual.route, "invariant")
        self.assertIn("has-done", residual.failed_invariants)

    def test_a_missing_declared_key_is_a_shape_residual_even_when_values_agree(self):
        contract = a_contract(
            expects=Shape(
                fields=(
                    Field("statuses", type="list", of="string"),
                    Field("revision", type="integer"),
                )
            )
        )
        paradigm = a_paradigm()
        bound = bind(contract, a_host())
        resolution = bound.resolve(
            paradigm,
            inputs={"status": "Ready for QA", "before": "Done"},
            expected={"statuses": ["Open", "Done"], "revision": 2},
        )
        admission = admit(
            resolution,
            paradigm,
            GateEvidence(state={"approved": True, "statuses": ["Open", "Done"]}, source="readback"),
        )
        outcome = operate(admission, lambda _resolution: {"claimed": "updated"})
        _observation, residual = bound.observe(
            outcome,
            lambda context: {"statuses": list(context.world["statuses"])},
            world={"statuses": ["Open", "Done"]},
            observer_name="readback",
        )
        self.assertEqual(residual.route, "contract")

    def test_a_matching_run_settles_normally(self):
        paradigm, (_observation, residual) = self._run(
            {"statuses": ["Open", "Ready for QA", "Done"]}
        )
        self.assertTrue(residual.matched)
        self.assertEqual(residual.route, "none")
        settlement = settle(
            paradigm,
            residual,
            accept=True,
            patch=lambda state: {**state, "map": {"statuses": list(residual.observed["statuses"])}},
            reason="verified",
        )
        self.assertTrue(settlement.changed)
        self.assertEqual(settlement.changed_layers, ("map",))


if __name__ == "__main__":
    unittest.main()
