"""Publishing and subskill-index invariants.

The point of publishing is recurrence: a concern worked out once should be
invocable next week without re-deriving it. That only holds if the artifact
lands where a host looks, and if How Do can find out later what it already
built. These test both, plus the refusals that keep a catalogue honest.
"""

import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import (  # noqa: E402
    SCOPE_PERSONAL,
    SCOPE_PROJECT,
    SUBSKILLS_BASENAME,
    Clause,
    DomainHow,
    EmitError,
    Field,
    PublishError,
    RequestContract,
    Rule,
    STATUS_GROUNDED,
    Shape,
    WorkedExample,
    publish,
    published,
    render_reference,
    skills_root,
    subskills_path,
    workflows_root,
    write_reference,
)

CONTRACT = RequestContract(
    name="jira.add-status",
    intent="insert a status before an existing one",
    path=("apply approved workflow change", "verify resulting statuses"),
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


def a_how(**overrides) -> DomainHow:
    base = dict(
        concern="jira.workflow",
        map={"rule": "approval before mutation"},
        contract=CONTRACT,
        example=WorkedExample(
            inputs={"status": "Ready for QA"},
            expected={"statuses": ["Open", "Done"]},
            observed={"statuses": ["Open", "Done"]},
        ),
    )
    base.update(overrides)
    return DomainHow(**base)


def grounded(**overrides) -> DomainHow:
    return dataclasses.replace(
        a_how(**overrides),
        status=STATUS_GROUNDED,
        observed_against=0,
        grounded_by="jira-readback",
    )


class DestinationTests(unittest.TestCase):
    """The host's own documented layout, not a path a caller has to already know."""

    def test_project_scope_lands_under_dot_claude_in_the_repo(self):
        self.assertEqual(
            skills_root(SCOPE_PROJECT, project="/repo"), Path("/repo/.claude/skills")
        )
        self.assertEqual(
            workflows_root(SCOPE_PROJECT, project="/repo"), Path("/repo/.claude/workflows")
        )

    def test_personal_scope_honours_the_config_directory(self):
        env = {"CLAUDE_CONFIG_DIR": "/custom/cfg"}
        self.assertEqual(
            skills_root(SCOPE_PERSONAL, env=env), Path("/custom/cfg/skills")
        )
        self.assertEqual(
            workflows_root(SCOPE_PERSONAL, env=env), Path("/custom/cfg/workflows")
        )

    def test_an_unknown_scope_is_refused(self):
        with self.assertRaises(PublishError):
            skills_root("enterprise")

    def test_the_catalogue_lives_in_the_store_beside_the_context(self):
        path = subskills_path(env={"HOWDO_CONTEXT": "/somewhere/CONTEXT.md"})
        self.assertEqual(path, Path("/somewhere") / SUBSKILLS_BASENAME)


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "repo"

    def _publish(self, how=None, **kwargs):
        kwargs.setdefault("project", self.project)
        return publish(how or grounded(), **kwargs)

    def test_it_writes_where_a_host_actually_loads_from(self):
        results = {entry.kind: entry for entry in self._publish()}
        self.assertEqual(
            results["skill"].path,
            self.project / ".claude" / "skills" / "jira-workflow" / "SKILL.md",
        )
        self.assertEqual(
            results["workflow"].path,
            self.project / ".claude" / "workflows" / "jira-workflow.js",
        )

    def test_it_reports_the_command_that_reruns_the_work(self):
        """Recurrence is the point; a path nobody can invoke is not publishing."""
        for entry in self._publish():
            self.assertEqual(entry.command, "/jira-workflow")

    def test_an_untested_artifact_is_not_published(self):
        with self.assertRaises(EmitError):
            self._publish(a_how())

    def test_a_published_artifact_is_not_silently_replaced(self):
        self._publish()
        with self.assertRaises(PublishError):
            self._publish()
        self.assertEqual(len(self._publish(overwrite=True)), 2)

    def test_the_person_decides_who_can_reach_a_published_skill(self):
        """They worked the concern out. It is not the issuer's call to take."""
        (open_to_claude,) = self._publish(
            formats=("skill",), disable_model_invocation=False
        )
        self.assertNotIn(
            "disable-model-invocation", open_to_claude.path.read_text(encoding="utf-8")
        )
        self.assertTrue(open_to_claude.auto_invocable)
        self.assertEqual(open_to_claude.invocation_chosen_by, "user")

    def test_a_person_may_also_choose_to_close_a_harmless_one(self):
        """The choice runs both ways; consequences are a lean, not a rule."""
        how = dataclasses.replace(
            grounded(),
            contract=dataclasses.replace(
                CONTRACT, mutates=False, crosses_boundary=False, expects=Shape(), rules=()
            ),
        )
        (closed,) = self._publish(how, formats=("skill",), disable_model_invocation=True)
        self.assertIn("disable-model-invocation: true", closed.path.read_text(encoding="utf-8"))
        self.assertFalse(closed.auto_invocable)
        self.assertEqual(closed.invocation_chosen_by, "user")

    def test_an_unmade_choice_falls_back_and_says_that_it_did(self):
        """A default is a prompt to ask, not the person's answer."""
        (skill,) = self._publish(formats=("skill",))
        self.assertIn("disable-model-invocation: true", skill.path.read_text(encoding="utf-8"))
        self.assertFalse(skill.auto_invocable)
        self.assertEqual(skill.invocation_chosen_by, "default")

    def test_a_non_boolean_choice_is_refused_rather_than_coerced(self):
        with self.assertRaises(EmitError):
            self._publish(formats=("skill",), disable_model_invocation="yes")

    def test_publishing_into_a_skill_payload_is_refused(self):
        payload = Path(self.tmp.name) / "how-do"
        (payload / ".claude").mkdir(parents=True)
        (payload / "SKILL.md").write_text("---\nname: how-do\n---\n", encoding="utf-8")
        with self.assertRaises(PublishError):
            self._publish(project=payload)

    def test_an_unknown_format_is_refused(self):
        with self.assertRaises(PublishError):
            self._publish(formats=("plugin",))

    def test_formats_can_be_narrowed_to_one(self):
        self.assertEqual([e.kind for e in self._publish(formats=("workflow",))], ["workflow"])


class IndexTests(unittest.TestCase):
    """The catalogue is scanned from the destinations, never declared."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "repo"

    def test_it_finds_what_was_published(self):
        publish(grounded(), project=self.project)
        found = published(SCOPE_PROJECT, project=self.project)
        self.assertEqual({e.kind for e in found}, {"skill", "workflow"})
        self.assertEqual({e.concern for e in found}, {"jira.workflow"})

    def test_a_deleted_artifact_stops_being_listed(self):
        publish(grounded(), project=self.project)
        (self.project / ".claude" / "workflows" / "jira-workflow.js").unlink()
        found = published(SCOPE_PROJECT, project=self.project)
        self.assertEqual([e.kind for e in found], ["skill"])

    def test_somebody_elses_skill_is_not_catalogued_as_ours(self):
        publish(grounded(), project=self.project)
        other = self.project / ".claude" / "skills" / "deploy"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text(
            '---\nname: deploy\ndescription: "ship it"\n---\n\nbody\n', encoding="utf-8"
        )
        names = {e.name for e in published(SCOPE_PROJECT, project=self.project)}
        self.assertNotIn("deploy", names)

    def test_the_scan_reports_reachability_from_the_installed_file(self):
        """What governs is what is on disk, even if someone edited it after."""
        publish(grounded(), project=self.project, disable_model_invocation=False)
        (skill,) = [e for e in published(SCOPE_PROJECT, project=self.project) if e.kind == "skill"]
        self.assertTrue(skill.auto_invocable)
        self.assertEqual(skill.invocation_chosen_by, "observed")

    def test_the_catalogue_shows_who_can_reach_each_entry(self):
        publish(grounded(), project=self.project, disable_model_invocation=False)
        text = render_reference(published(SCOPE_PROJECT, project=self.project))
        self.assertIn("reachable by", text)
        self.assertIn("you or Claude", text)
        self.assertIn("a decision someone made, not a property of the work", text)

    def test_a_closed_skill_reads_as_yours_only(self):
        publish(grounded(), project=self.project, disable_model_invocation=True)
        text = render_reference(published(SCOPE_PROJECT, project=self.project))
        self.assertIn("you only", text)

    def test_an_empty_destination_indexes_to_nothing_rather_than_raising(self):
        self.assertEqual(published(SCOPE_PROJECT, project=self.project), ())

    def test_the_reference_names_the_command_and_the_status(self):
        publish(grounded(), project=self.project)
        text = render_reference(published(SCOPE_PROJECT, project=self.project))
        self.assertIn("`/jira-workflow`", text)
        self.assertIn("grounded", text)
        self.assertIn("jira.workflow", text)

    def test_an_empty_reference_says_so_rather_than_rendering_an_empty_table(self):
        self.assertIn("Nothing published yet", render_reference(()))

    def test_the_reference_warns_that_untested_entries_are_proposals(self):
        publish(grounded(), project=self.project)
        text = render_reference(published(SCOPE_PROJECT, project=self.project))
        self.assertIn("has not been confirmed by an observed", text)

    def test_the_reference_does_not_claim_how_do_runs_a_clock(self):
        """Recurrence is the host's scheduler; issuing and indexing is ours."""
        publish(grounded(), project=self.project)
        text = render_reference(published(SCOPE_PROJECT, project=self.project))
        self.assertIn("it does not run a clock", text)

    def test_it_writes_into_the_store_not_the_payload(self):
        publish(grounded(), project=self.project)
        store = Path(self.tmp.name) / "store" / "CONTEXT.md"
        target = write_reference(project=self.project, store=store)
        self.assertEqual(target, store.parent / SUBSKILLS_BASENAME)
        self.assertIn("/jira-workflow", target.read_text(encoding="utf-8"))

    def test_a_catalogue_aimed_inside_the_payload_is_refused(self):
        payload = Path(self.tmp.name) / "how-do"
        payload.mkdir()
        (payload / "SKILL.md").write_text("---\nname: how-do\n---\n", encoding="utf-8")
        with self.assertRaises(PublishError):
            write_reference(project=self.project, store=payload / "CONTEXT.md")


if __name__ == "__main__":
    unittest.main()
