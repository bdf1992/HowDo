"""Domain-how issuer and index invariants.

The artifact `SKILL.md` always promised and never wrote. The promises worth
breaking a build over are the ones the prose could only assert: an artifact is
issued from a run rather than an intention, it stays untested until a matching
run grounds it, an edit cannot inherit the grounding its predecessor earned, and
the index is a view over the files rather than a second source of truth.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import (  # noqa: E402
    STATUS_GROUNDED,
    STATUS_UNTESTED,
    Clause,
    DomainError,
    DomainHow,
    Field,
    GateEvidence,
    Host,
    Paradigm,
    RequestContract,
    Rule,
    Shape,
    WorkedExample,
    admit,
    bind,
    ground,
    issue,
    issue_from_run,
    load,
    operate,
    read_index,
    reindex,
    resolve_domain_root,
    revise,
    staleness,
)


def a_contract(**overrides) -> RequestContract:
    kwargs = dict(
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
        ),
        requires=("jira.write",),
    )
    kwargs.update(overrides)
    return RequestContract(**kwargs)


A_MAP = {"statuses": ["Open", "Done"], "rule": "approval before mutation"}


def a_run(world=None, *, paradigm=None):
    """One complete HowDo, returning what an artifact would be issued from."""

    world = world if world is not None else {"approved": True, "statuses": ["Open", "Done"]}
    paradigm = paradigm or Paradigm(state={"map": dict(A_MAP)})
    bound = bind(a_contract(), Host("local", capabilities=frozenset({"jira.write"})))
    resolution = bound.resolve(
        paradigm,
        inputs={"status": "Ready for QA", "before": "Done"},
        expected={"statuses": ["Open", "Ready for QA", "Done"]},
    )
    admission = admit(resolution, paradigm, GateEvidence(state=dict(world), source="readback"))
    outcome = operate(admission, lambda _r: {"claimed": "updated"})
    observed = {"statuses": ["Open", "Ready for QA", "Done"]}
    _observation, residual = bound.observe(
        outcome, lambda ctx: dict(ctx.world), world=observed, observer_name="jira-readback"
    )
    return paradigm, resolution, residual


def a_how(**overrides) -> DomainHow:
    _paradigm, resolution, residual = a_run()
    how = issue_from_run(
        resolution, residual, concern="jira.workflow", contract=a_contract(), map=dict(A_MAP)
    )
    return how if not overrides else DomainHow(**{**how.__dict__, **overrides})


class IssuedFromARunTests(unittest.TestCase):
    """An artifact issued from an intention has no evidence in it."""

    def test_the_example_is_the_run_that_happened(self):
        _paradigm, resolution, residual = a_run()
        how = issue_from_run(
            resolution, residual, concern="jira.workflow", contract=a_contract(), map=dict(A_MAP)
        )
        self.assertEqual(how.example.inputs, dict(resolution.request.inputs))
        self.assertEqual(how.example.observed, dict(residual.observed))

    def test_a_residual_from_another_run_cannot_supply_the_example(self):
        _p1, resolution, _r1 = a_run()
        _p2, _r2, residual = a_run()
        with self.assertRaises(DomainError):
            issue_from_run(
                resolution, residual, concern="jira.workflow", contract=a_contract(), map=A_MAP
            )

    def test_a_contract_describing_another_route_is_refused(self):
        _paradigm, resolution, residual = a_run()
        with self.assertRaises(DomainError):
            issue_from_run(
                resolution,
                residual,
                concern="jira.workflow",
                contract=a_contract(path=("some other route",)),
                map=A_MAP,
            )

    def test_an_artifact_carries_the_map_its_path_is_navigable_in(self):
        _paradigm, resolution, residual = a_run()
        with self.assertRaises(DomainError):
            issue_from_run(
                resolution, residual, concern="jira.workflow", contract=a_contract(), map={}
            )

    def test_it_exposes_the_workflow_and_the_capabilities_it_needs(self):
        how = a_how()
        self.assertEqual(how.path, a_contract().path)
        self.assertEqual(how.requires, ("jira.write",))


class GroundingTests(unittest.TestCase):
    """`SKILL.md`: never promote an untested exemplar because it sounded plausible."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "domains"
        self.addCleanup(self.tmp.cleanup)

    def test_a_freshly_issued_artifact_is_untested(self):
        how = a_how()
        self.assertEqual(how.status, STATUS_UNTESTED)
        self.assertIsNone(how.observed_against)

    def test_a_matching_run_grounds_it(self):
        issue(a_how(), root=self.root)
        _paradigm, _resolution, residual = a_run()
        promoted = ground("jira.workflow", residual, root=self.root)
        self.assertEqual(promoted.status, STATUS_GROUNDED)
        self.assertEqual(promoted.observed_against, 0)
        self.assertEqual(load("jira.workflow", root=self.root).status, STATUS_GROUNDED)

    def test_a_run_that_did_not_match_cannot_ground_it(self):
        issue(a_how(), root=self.root)
        paradigm = Paradigm(state={"map": dict(A_MAP)})
        bound = bind(a_contract(), Host("local", capabilities=frozenset({"jira.write"})))
        resolution = bound.resolve(
            paradigm,
            inputs={"status": "Ready for QA", "before": "Done"},
            expected={"statuses": ["Open", "Ready for QA", "Done"]},
        )
        admission = admit(
            resolution,
            paradigm,
            GateEvidence(state={"approved": True, "statuses": ["Open", "Done"]}, source="readback"),
        )
        outcome = operate(admission, lambda _r: {"claimed": "updated"})
        _obs, residual = bound.observe(
            outcome,
            lambda ctx: dict(ctx.world),
            world={"statuses": ["Open", "Done"]},  # the change never landed
            observer_name="jira-readback",
        )
        with self.assertRaises(DomainError):
            ground("jira.workflow", residual, root=self.root)

    def test_a_grounded_status_cannot_be_declared_without_an_observation(self):
        with self.assertRaises(DomainError):
            a_how(status=STATUS_GROUNDED, observed_against=None)

    def test_an_untested_artifact_cannot_claim_an_observation(self):
        with self.assertRaises(DomainError):
            a_how(status=STATUS_UNTESTED, observed_against=3)

    def test_a_revision_drops_the_grounding_its_predecessor_earned(self):
        issue(a_how(), root=self.root)
        _p, _r, residual = a_run()
        grounded = ground("jira.workflow", residual, root=self.root)
        self.assertTrue(grounded.grounded)

        edited = a_how(map={**A_MAP, "rule": "approval is now optional"})
        superseded = revise(edited, grounded)
        self.assertEqual(superseded.revision, grounded.revision + 1)
        self.assertEqual(superseded.status, STATUS_UNTESTED)
        self.assertIsNone(superseded.observed_against)

    def test_an_unchanged_revision_is_not_a_new_one(self):
        how = a_how()
        self.assertIs(revise(a_how(), how), how)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "domains"
        self.addCleanup(self.tmp.cleanup)

    def test_artifacts_live_beside_the_context_not_inside_the_payload(self):
        root = resolve_domain_root(env={"HOWDO_CONTEXT": "/somewhere/CONTEXT.md"})
        self.assertEqual(root, Path("/somewhere/domains"))

    def test_issuing_into_the_skill_payload_is_refused(self):
        payload = Path(self.tmp.name) / "how-do"
        payload.mkdir()
        (payload / "SKILL.md").write_text("---\nname: how-do\n---\n", encoding="utf-8")
        with self.assertRaises(DomainError):
            issue(a_how(), root=payload / "domains")

    def test_a_silent_overwrite_of_different_content_is_refused(self):
        issue(a_how(), root=self.root)
        edited = a_how(map={**A_MAP, "rule": "changed"})
        with self.assertRaises(DomainError):
            issue(edited, root=self.root)

    def test_reissuing_identical_content_is_a_no_op(self):
        first = issue(a_how(), root=self.root)
        self.assertEqual(issue(a_how(), root=self.root), first)

    def test_a_file_edited_outside_the_issuer_is_refused_on_load(self):
        target = issue(a_how(), root=self.root)
        data = json.loads(target.read_text(encoding="utf-8"))
        data["map"]["rule"] = "quietly rewritten"
        target.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(DomainError):
            load("jira.workflow", root=self.root)

    def test_casing_cannot_fork_one_concern_into_two(self):
        with self.assertRaises(DomainError):
            a_how(concern="Jira.Workflow")


class IndexTests(unittest.TestCase):
    """The index is a projection over the files, never a second authority."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "domains"
        self.addCleanup(self.tmp.cleanup)

    def test_it_catalogues_the_workflow_and_the_capabilities(self):
        issue(a_how(), root=self.root)
        (entry,) = read_index(root=self.root)
        self.assertEqual(entry.concern, "jira.workflow")
        self.assertEqual(entry.path, a_contract().path)
        self.assertEqual(entry.requires, ("jira.write",))
        self.assertEqual(entry.status, STATUS_UNTESTED)

    def test_a_deleted_index_is_a_rebuild_not_a_loss(self):
        issue(a_how(), root=self.root)
        (self.root / "index.json").unlink()
        self.assertEqual(len(read_index(root=self.root)), 1)

    def test_a_corrupt_index_is_a_rebuild_not_a_loss(self):
        issue(a_how(), root=self.root)
        (self.root / "index.json").write_text("{ not json", encoding="utf-8")
        self.assertEqual(len(read_index(root=self.root)), 1)

    def test_one_unreadable_artifact_does_not_cost_the_whole_index(self):
        issue(a_how(), root=self.root)
        (self.root / "broken.json").write_text("{ not json", encoding="utf-8")
        entries = read_index(root=self.root)
        self.assertEqual(len(entries), 1)
        view = json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(view["unreadable"], ["broken.json"])

    def test_untested_artifacts_can_be_kept_out_of_a_decision(self):
        issue(a_how(), root=self.root)
        self.assertEqual(read_index(root=self.root, status=STATUS_GROUNDED), ())
        _p, _r, residual = a_run()
        ground("jira.workflow", residual, root=self.root)
        self.assertEqual(len(read_index(root=self.root, status=STATUS_GROUNDED)), 1)

    def test_a_host_can_see_only_what_it_could_run(self):
        issue(a_how(), root=self.root)
        self.assertEqual(read_index(root=self.root, requires=()), ())
        self.assertEqual(len(read_index(root=self.root, requires=("jira.write",))), 1)

    def test_an_empty_store_indexes_to_nothing_rather_than_raising(self):
        self.assertEqual(read_index(root=self.root / "never-created"), ())


class StalenessTests(unittest.TestCase):
    """admit() fizzles a stale resolution; that protection ends where storage begins."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "domains"
        self.addCleanup(self.tmp.cleanup)

    def test_an_untested_artifact_has_nothing_to_be_stale_against(self):
        report = staleness(a_how(), Paradigm(state={"map": A_MAP}, revision=9))
        self.assertFalse(report.stale)
        self.assertIn("untested", report.reason)

    def test_a_drifted_paradigm_makes_a_grounded_artifact_stale(self):
        issue(a_how(), root=self.root)
        _p, _r, residual = a_run()
        grounded = ground("jira.workflow", residual, root=self.root)
        report = staleness(grounded, Paradigm(state={"map": A_MAP}, revision=40))
        self.assertTrue(report.stale)
        self.assertEqual(report.observed_against, 0)
        self.assertEqual(report.current_revision, 40)

    def test_an_artifact_observed_against_the_current_revision_is_not_stale(self):
        issue(a_how(), root=self.root)
        _p, _r, residual = a_run()
        grounded = ground("jira.workflow", residual, root=self.root)
        self.assertFalse(staleness(grounded, Paradigm(state={"map": A_MAP})).stale)


if __name__ == "__main__":
    unittest.main()
