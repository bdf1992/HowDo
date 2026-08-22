import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "plugin"
sys.path.insert(0, str(PAYLOAD / "runtime"))

from howdo import (
    Check,
    ExecutionError,
    Fizzle,
    GateEvidence,
    Paradigm,
    Request,
    admit,
    observe,
    operate,
    resolve,
    settle,
)


class RuntimeTests(unittest.TestCase):
    def consequential_resolution(self, paradigm, *, checks=None, expected=None):
        checks = checks or [
            Check("approved", "human approval", lambda s: s.get("approved") is True)
        ]
        return resolve(
            Request(handle="do work", intent="change x", mutates=True),
            paradigm,
            path=["change"],
            expected=expected or {"x": 2},
            checks=checks,
        )

    def test_consequential_request_requires_expectation(self):
        p = Paradigm(state={"map": {"x": 1}})
        r = Request(handle="do work", intent="change x", mutates=True)
        with self.assertRaises(ValueError):
            resolve(
                r,
                p,
                path=["change"],
                expected={},
                checks=[Check("approved", "approval", lambda _s: True)],
            )

    def test_consequential_request_requires_precondition(self):
        p = Paradigm(state={"map": {"x": 1}})
        r = Request(handle="do work", intent="change x", mutates=True, crosses_boundary=True)
        with self.assertRaisesRegex(ValueError, "at least one precondition"):
            resolve(r, p, path=["change"], expected={"_": None}, checks=[])

    def test_failed_precondition_fizzles_before_executor(self):
        p = Paradigm(state={"rule": "approval required"})
        resolution = self.consequential_resolution(p)
        result = admit(
            resolution,
            p,
            GateEvidence({"approved": False}, source="approval-api"),
        )
        self.assertIsInstance(result, Fizzle)
        self.assertEqual(result.failed_checks, ("approved",))
        self.assertEqual(result.route, "precondition")

    def test_gate_records_evidence_provenance(self):
        p = Paradigm(state={"map": {"x": 1}})
        resolution = self.consequential_resolution(p)
        evidence = GateEvidence({"approved": True}, source="jira-readback")
        admission = admit(resolution, p, evidence)
        self.assertEqual(admission.evidence_id, evidence.evidence_id)
        self.assertEqual(admission.evidence_source, "jira-readback")

    def test_gate_evidence_is_a_snapshot(self):
        p = Paradigm(state={"map": {"x": 1}})
        resolution = self.consequential_resolution(p)
        live = {"approved": True}
        evidence = GateEvidence(live, source="approval-api")
        live["approved"] = False
        admission = admit(resolution, p, evidence)
        self.assertFalse(isinstance(admission, Fizzle))

    def test_stale_resolution_fizzles_before_operation(self):
        p0 = Paradigm(state={"map": {"x": 1}})
        resolution = self.consequential_resolution(p0)
        p1 = Paradigm(state={"map": {"x": 9}}, revision=1, paradigm_id=p0.paradigm_id)
        result = admit(
            resolution,
            p1,
            GateEvidence({"approved": True}, source="current-world"),
        )
        self.assertIsInstance(result, Fizzle)
        self.assertIn("stale", result.reason)
        executed = False
        if not isinstance(result, Fizzle):
            operate(result, lambda _r: {"executed": True})
            executed = True
        self.assertFalse(executed)

    def test_invariant_failure_at_gate_routes_invariant(self):
        p = Paradigm(state={"map": {"x": 1}})
        checks = [
            Check("approved", "approval", lambda s: s.get("approved") is True),
            Check("positive", "x remains positive", lambda s: s.get("x", 0) > 0, kind="invariant"),
        ]
        resolution = self.consequential_resolution(p, checks=checks)
        result = admit(
            resolution,
            p,
            GateEvidence({"approved": True, "x": -1}, source="world"),
        )
        self.assertIsInstance(result, Fizzle)
        self.assertEqual(result.route, "invariant")
        self.assertEqual(result.failed_checks, ("positive",))

    def test_observer_is_not_handed_executor_report(self):
        world = {"x": 1}
        p = Paradigm(state={"map": {"x": 1}})
        resolution = self.consequential_resolution(p)
        admission = admit(
            resolution,
            p,
            GateEvidence({"approved": True}, source="approval-api"),
        )
        outcome = operate(admission, lambda _r: {"x": 2, "claimed": True})

        def independent_observer(context):
            self.assertEqual(context.expected_keys, ("x",))
            self.assertFalse(hasattr(context, "reported"))
            self.assertFalse(hasattr(context, "outcome"))
            return {"x": context.world["x"]}

        _obs, residual = observe(outcome, independent_observer, world=world)
        self.assertFalse(residual.matched)
        self.assertEqual(residual.route, "postcondition")

    def test_invariant_is_evaluated_after_operation(self):
        world = {"approved": True, "x": 1}
        p = Paradigm(state={"map": {"x": 1}})
        checks = [
            Check("approved", "approval", lambda s: s.get("approved") is True),
            Check("positive", "x remains positive", lambda s: s.get("x", 1) > 0, kind="invariant"),
        ]
        resolution = self.consequential_resolution(p, checks=checks, expected={"x": -5})
        admission = admit(
            resolution,
            p,
            GateEvidence(dict(world), source="world-before"),
        )

        def executor(_r):
            world["x"] = -5
            return {"claimed": "done"}

        outcome = operate(admission, executor)
        _obs, residual = observe(
            outcome,
            lambda context: {"x": context.world["x"]},
            world=world,
        )
        self.assertFalse(residual.matched)
        self.assertEqual(residual.route, "invariant")
        self.assertEqual(residual.failed_invariants, ("positive",))

    def test_observation_does_not_automatically_mutate_paradigm(self):
        world = {"x": 2}
        p = Paradigm(state={"map": {"x": 1}})
        resolution = self.consequential_resolution(p)
        admission = admit(
            resolution,
            p,
            GateEvidence({"approved": True}, source="approval-api"),
        )
        outcome = operate(admission, lambda _r: {"claimed": "done"})
        _obs, residual = observe(
            outcome,
            lambda context: {"x": context.world["x"]},
            world=world,
        )
        settlement = settle(p, residual, accept=True, patch=None)
        self.assertEqual(settlement.paradigm.revision, 0)
        self.assertFalse(settlement.changed)
        self.assertEqual(settlement.changed_layers, ())

    def test_settlement_updates_one_top_level_layer(self):
        world = {"x": 3}  # the operation overshot: a discrepancy the paradigm must absorb
        p = Paradigm(state={"map": {"x": 1}, "path": ["set"]})
        resolution = self.consequential_resolution(p)
        admission = admit(
            resolution,
            p,
            GateEvidence({"approved": True}, source="approval-api"),
        )
        outcome = operate(admission, lambda _r: {"claimed": "done"})
        _obs, residual = observe(
            outcome,
            lambda context: {"x": context.world["x"]},
            world=world,
        )

        self.assertFalse(residual.matched)

        def patch(state):
            state["map"]["x"] = 3
            return state

        settlement = settle(p, residual, accept=True, patch=patch)
        self.assertTrue(settlement.changed)
        self.assertEqual(settlement.changed_layers, ("map",))
        self.assertEqual(settlement.paradigm.revision, 1)
        self.assertEqual(settlement.paradigm.state["path"], ["set"])

    def test_settlement_refuses_multi_layer_rewrite_by_default(self):
        world = {"x": 3}
        p = Paradigm(state={"map": {"x": 1}, "path": ["set"], "receiver": {"mode": "guide"}})
        resolution = self.consequential_resolution(p)
        admission = admit(
            resolution,
            p,
            GateEvidence({"approved": True}, source="approval-api"),
        )
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(
            outcome,
            lambda context: {"x": context.world["x"]},
            world=world,
        )

        def hostile_patch(_state):
            return {"totally": "new"}

        with self.assertRaisesRegex(ValueError, "more than one top-level"):
            settle(p, residual, accept=True, patch=hostile_patch)

    def test_multi_layer_settlement_requires_explicit_override(self):
        world = {"x": 3}
        p = Paradigm(state={"map": {"x": 1}, "path": ["set"]})
        resolution = self.consequential_resolution(p)
        admission = admit(
            resolution,
            p,
            GateEvidence({"approved": True}, source="approval-api"),
        )
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(
            outcome,
            lambda context: {"x": context.world["x"]},
            world=world,
        )

        settlement = settle(
            p,
            residual,
            accept=True,
            patch=lambda _state: {"totally": "new"},
            allow_multi_layer=True,
            reason="explicit paradigm replacement",
        )
        self.assertTrue(settlement.changed)
        self.assertGreater(len(settlement.changed_layers), 1)

    def test_stale_residual_cannot_settle_new_revision(self):
        world = {"x": 2}
        p = Paradigm(state={"map": {"x": 1}})
        resolution = self.consequential_resolution(p)
        admission = admit(
            resolution,
            p,
            GateEvidence({"approved": True}, source="approval-api"),
        )
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(
            outcome,
            lambda context: {"x": context.world["x"]},
            world=world,
        )
        newer = Paradigm(state={"map": {"x": 3}}, revision=1, paradigm_id=p.paradigm_id)
        with self.assertRaises(ValueError):
            settle(newer, residual, accept=True, patch=lambda state: state)

    def test_actor_modifier_is_attributed_through_resolution(self):
        paradigm = Paradigm({"ready": True})
        request = Request(handle="how do", intent="ship together", actor="joint")
        resolution = resolve(
            request,
            paradigm,
            path=("plan",),
            expected={"done": True},
            checks=(Check("ready", "ready", lambda state: state["ready"]),),
        )
        self.assertEqual(resolution.request.actor, "joint")


if __name__ == "__main__":
    unittest.main()


class CoreHardeningTests(unittest.TestCase):
    def _admitted(self, expected=None, checks=None, state=None, evidence=None):
        p = Paradigm(state=state or {"map": {"x": 1}})
        r = Request(handle="do work", intent="set x to 2")
        resolution = resolve(
            r, p, path=["set"], expected=expected or {"x": 2},
            checks=checks or [Check("ok", "always", lambda s: True)],
        )
        return p, admit(resolution, p, GateEvidence(state=evidence or {}, source="test"))

    def test_request_is_consequential_by_default(self):
        p = Paradigm(state={})
        r = Request(handle="do work", intent="anything")
        self.assertTrue(r.mutates)
        with self.assertRaises(ValueError):
            resolve(r, p, path=["step"], expected={})

    def test_admission_is_single_use(self):
        p, admission = self._admitted()
        counter = {"n": 0}

        def ex(_r):
            counter["n"] += 1
            return {}

        operate(admission, ex)
        with self.assertRaises(ValueError):
            operate(admission, ex)
        self.assertEqual(counter["n"], 1)

    def test_check_that_raises_is_false_and_fizzles(self):
        p = Paradigm(state={})
        r = Request(handle="do work", intent="x")
        resolution = resolve(
            r, p, path=["s"], expected={"x": 1},
            checks=[Check("needs_key", "", lambda s: s["missing"] > 0)],
        )
        result = admit(resolution, p, GateEvidence(state={}, source="test"))
        self.assertIsInstance(result, Fizzle)
        self.assertEqual(result.failed_checks, ("needs_key",))

    def test_executor_failure_cannot_erase_the_admitted_attempt(self):
        world = {"x": 1}
        p, admission = self._admitted()

        def half_done_then_raise(_r):
            world["x"] = 2  # the boundary was crossed before the failure
            raise OSError("connection reset")

        with self.assertRaises(ExecutionError) as caught:
            operate(admission, half_done_then_raise)

        outcome = caught.exception.outcome
        self.assertEqual(outcome.admission.admission_id, admission.admission_id)
        self.assertIn("connection reset", outcome.error)
        self.assertEqual(dict(outcome.reported), {})
        self.assertIsInstance(caught.exception.__cause__, OSError)

    def test_admission_stays_single_use_after_executor_failure(self):
        p, admission = self._admitted()
        with self.assertRaises(ExecutionError):
            operate(admission, lambda _r: (_ for _ in ()).throw(RuntimeError("boom")))
        with self.assertRaisesRegex(ValueError, "already consumed"):
            operate(admission, lambda _r: {})

    def test_observation_runs_after_executor_failure(self):
        # The executor raised, but the world may have changed anyway; Look is
        # the arbiter, not the exception.
        world = {"x": 1}
        p, admission = self._admitted()

        def effect_then_raise(_r):
            world["x"] = 2
            raise RuntimeError("timeout waiting for confirmation")

        with self.assertRaises(ExecutionError) as caught:
            operate(admission, effect_then_raise)

        _obs, residual = observe(
            caught.exception.outcome,
            lambda context: {"x": context.world["x"]},
            world=world,
        )
        # The expected state {"x": 2} is observed despite the raise: the
        # exception was not proof that nothing happened.
        self.assertTrue(residual.matched)
        s = settle(p, residual, accept=True)
        self.assertTrue(s.accepted)
        self.assertFalse(s.changed)

    def test_matched_observation_cannot_license_state_rewrite(self):
        p, admission = self._admitted()
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(outcome, lambda c: {"x": 2}, world=None)
        self.assertTrue(residual.matched)
        self.assertEqual(residual.route, "none")
        with self.assertRaisesRegex(ValueError, "no discrepancy"):
            settle(p, residual, accept=True, patch=lambda st: {**st, "map": {"x": 2}})

    def test_matched_observation_settles_without_revision_churn(self):
        p, admission = self._admitted()
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(outcome, lambda c: {"x": 2}, world=None)
        s = settle(p, residual, accept=True)
        self.assertTrue(s.accepted)
        self.assertFalse(s.changed)
        self.assertEqual(s.paradigm.revision, p.revision)

    def test_unmatched_residual_still_earns_write_back(self):
        p, admission = self._admitted()
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(outcome, lambda c: {"x": 3}, world=None)
        self.assertFalse(residual.matched)
        s = settle(p, residual, accept=True, patch=lambda st: {**st, "map": {"x": 3}})
        self.assertTrue(s.changed)
        self.assertEqual(s.paradigm.revision, p.revision + 1)

    def test_paradigm_state_is_a_snapshot(self):
        # The revision asserts an identity for this exact state; a caller-held
        # nested mapping must not be able to change it retroactively.
        live = {"map": {"x": 1}}
        p = Paradigm(state=live)
        live["map"]["x"] = 999
        self.assertEqual(p.state["map"]["x"], 1)

    def test_state_mutated_behind_an_unchanged_revision_closes_the_gate(self):
        p = Paradigm(state={"map": {"x": 1}})
        r = Request(handle="do work", intent="set x to 2")
        resolution = resolve(
            r, p, path=["set"], expected={"x": 2},
            checks=[Check("ok", "always", lambda s: True)],
        )
        # The snapshot keeps the constructor's mapping out; the accessor is the
        # remaining route, and the gate has to catch it by value.
        p.state["map"]["x"] = 777  # mutate the nested mapping through the accessor
        result = admit(resolution, p, GateEvidence(state={}, source="test"))
        self.assertIsInstance(result, Fizzle)
        self.assertEqual(result.failed_checks, ("paradigm_state",))

    def test_state_mutated_behind_an_unchanged_revision_refuses_settlement(self):
        p, admission = self._admitted()
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(outcome, lambda c: {"x": 3}, world=None)
        self.assertFalse(residual.matched)
        p.state["map"]["x"] = 777
        with self.assertRaisesRegex(ValueError, "diverged"):
            settle(p, residual, accept=True, patch=lambda st: {**st, "map": {"x": 3}})

    def test_adding_a_none_valued_key_counts_as_a_changed_layer(self):
        p, admission = self._admitted()
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(outcome, lambda c: {"x": 3}, world=None)
        s = settle(p, residual, accept=True, patch=lambda st: {**st, "extra": None})
        self.assertEqual(s.changed_layers, ("extra",))
        self.assertTrue(s.changed)
        self.assertEqual(s.paradigm.revision, p.revision + 1)

    def test_removing_a_none_valued_key_counts_as_a_changed_layer(self):
        p, admission = self._admitted(state={"map": {"x": 1}, "extra": None})
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(outcome, lambda c: {"x": 3}, world=None)

        def drop_extra(st):
            st = dict(st)
            del st["extra"]
            return st

        s = settle(p, residual, accept=True, patch=drop_extra)
        self.assertEqual(s.changed_layers, ("extra",))
        self.assertTrue(s.changed)
        self.assertEqual(s.paradigm.revision, p.revision + 1)

    def test_settle_refuses_patch_after_invariant_residual(self):
        inv = Check("positive", "", lambda s: s["x"] > 0, kind="invariant")
        p, admission = self._admitted(
            expected={"y": 1},
            checks=[Check("ok", "", lambda s: True), inv],
            evidence={"x": 1},  # invariant must hold at the gate (fail-closed) before it can fail after
        )
        outcome = operate(admission, lambda _r: {})
        _obs, residual = observe(outcome, lambda c: {"y": 1, "x": -5}, world=None)
        self.assertEqual(residual.route, "invariant")
        with self.assertRaises(ValueError):
            settle(p, residual, accept=True, patch=lambda st: {**st, "map": {"x": -5}})
        # explicit override still works, and no-patch settlement is still allowed
        s = settle(p, residual, accept=True, patch=lambda st: {**st, "map": {"x": -5}}, allow_after_invariant=True)
        self.assertTrue(s.changed)
        s2 = settle(p, residual, accept=False)
        self.assertFalse(s2.changed)
