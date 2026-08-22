"""Emitter invariants: a rendered artifact has to be loadable, and honest.

Two specifications constrain the output, so most of these are conformance tests
against them rather than taste. The rest guard the one thing emission can get
wrong on its own: shipping an unconfirmed artifact as though it were settled.
"""

import dataclasses
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import (  # noqa: E402
    MAX_COMPATIBILITY,
    MAX_DESCRIPTION,
    MAX_NAME,
    SPEC_FIELDS,
    TARGET_CLAUDE_CODE,
    TARGET_SPEC,
    Clause,
    DomainHow,
    EmitError,
    Field,
    RequestContract,
    Rule,
    Shape,
    STATUS_GROUNDED,
    Shape,
    WorkedExample,
    render_skill,
    render_workflow,
    skill_name,
    write_skill,
    write_workflow,
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


def a_how(**overrides) -> DomainHow:
    base = dict(
        concern="jira.workflow",
        map={"statuses": ["Open", "Done"], "rule": "approval before mutation"},
        contract=CONTRACT,
        example=WorkedExample(
            inputs={"status": "Ready for QA", "before": "Done"},
            expected={"statuses": ["Open", "Ready for QA", "Done"]},
            observed={"statuses": ["Open", "Ready for QA", "Done"]},
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


class UntestedTests(unittest.TestCase):
    """A SKILL.md on disk pre-loads every later session. Untested must not ship quietly."""

    def test_an_untested_artifact_is_not_emitted_as_a_skill(self):
        with self.assertRaises(EmitError):
            render_skill(a_how())

    def test_an_untested_artifact_is_not_emitted_as_a_workflow(self):
        with self.assertRaises(EmitError):
            render_workflow(a_how())

    def test_the_override_stamps_the_output_it_produces(self):
        """Review is a reason to render one; mistaking it for ground is not."""
        self.assertIn("**Untested.**", render_skill(a_how(), allow_untested=True).body)
        self.assertIn("UNTESTED", render_workflow(a_how(), allow_untested=True).source)

    def test_a_grounded_artifact_states_what_grounding_did_and_did_not_prove(self):
        body = render_skill(grounded()).body
        self.assertIn("observed to match", body)
        self.assertIn("not a claim that this is the best route", body)


class SkillSpecificationTests(unittest.TestCase):
    """Agent Skills constraints. A skill that violates one is not loadable at all."""

    def test_the_name_is_lowercase_hyphenated_and_within_the_cap(self):
        bundle = render_skill(grounded())
        self.assertEqual(bundle.name, "jira-workflow")
        self.assertRegex(bundle.name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(bundle.name), MAX_NAME)

    def test_a_concern_that_cannot_project_to_a_legal_name_is_refused(self):
        with self.assertRaises(EmitError):
            skill_name("-")
        with self.assertRaises(EmitError):
            skill_name("x" * (MAX_NAME + 1))

    def test_dots_and_underscores_project_to_hyphens_without_doubling(self):
        self.assertEqual(skill_name("a.b_c--d"), "a-b-c-d")

    def test_the_description_states_what_and_when_within_the_cap(self):
        bundle = render_skill(grounded())
        self.assertLessEqual(len(bundle.description), MAX_DESCRIPTION)
        self.assertIn("Use when", bundle.description)
        self.assertIn(CONTRACT.intent, bundle.description)

    def test_the_description_does_not_make_the_skill_ambient(self):
        """This repo learned the lesson once already; a generated one inherits it."""
        description = render_skill(grounded()).description
        self.assertIn("not a general-purpose helper", description)
        self.assertIn("not by itself a reason to load it", description)

    def test_frontmatter_carries_no_angle_brackets(self):
        """They can inject instructions into a system prompt."""
        how = grounded()
        how = dataclasses.replace(
            how,
            contract=dataclasses.replace(
                CONTRACT, intent="insert a <script>alert(1)</script> status"
            ),
        )
        bundle = render_skill(how)
        frontmatter = bundle.body.split("---")[1]
        self.assertNotIn("<", frontmatter)
        self.assertNotIn(">", frontmatter)

    def test_the_directory_name_equals_the_skill_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = write_skill(grounded(), tmp)
            self.assertEqual(target.name, "SKILL.md")
            self.assertEqual(target.parent.name, render_skill(grounded()).name)

    def test_an_existing_skill_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_skill(grounded(), tmp)
            with self.assertRaises(EmitError):
                write_skill(grounded(), tmp)
            self.assertTrue(write_skill(grounded(), tmp, overwrite=True).is_file())


def _frontmatter(body: str) -> str:
    return body.split("---")[1]


def _top_level_keys(body: str) -> set:
    return {
        line.split(":", 1)[0]
        for line in _frontmatter(body).strip().splitlines()
        if line and not line.startswith((" ", "\t"))
    }


class FrontmatterTargetTests(unittest.TestCase):
    """Two accepted field sets, and an unknown key is a hard error on one of them.

    Outside Claude Code -- claude.ai upload, the Skills API, package_skill.py --
    a field the spec does not list fails packaging outright rather than being
    ignored, so the default target cannot emit one.
    """

    def test_the_spec_target_emits_only_the_six_accepted_fields(self):
        body = render_skill(grounded(), license="MIT").body
        self.assertTrue(_top_level_keys(body) <= set(SPEC_FIELDS), _top_level_keys(body))

    def test_the_spec_target_is_the_default(self):
        self.assertEqual(
            render_skill(grounded()).body, render_skill(grounded(), target=TARGET_SPEC).body
        )

    def test_an_unknown_target_is_refused(self):
        with self.assertRaises(EmitError):
            render_skill(grounded(), target="anthropic-api")

    def test_a_consequential_artifact_is_not_left_auto_invocable_for_claude_code(self):
        """The documented case for the field: a workflow with side effects."""
        self.assertTrue(CONTRACT.consequential)
        body = render_skill(grounded(), target=TARGET_CLAUDE_CODE).body
        self.assertIn("disable-model-invocation: true", _frontmatter(body))

    def test_an_observation_only_artifact_stays_invocable(self):
        how = dataclasses.replace(
            grounded(),
            contract=dataclasses.replace(
                CONTRACT, mutates=False, crosses_boundary=False, expects=Shape(), rules=()
            ),
        )
        body = render_skill(how, target=TARGET_CLAUDE_CODE).body
        self.assertNotIn("disable-model-invocation", _frontmatter(body))

    def test_the_spec_target_says_in_prose_what_it_cannot_say_in_frontmatter(self):
        body = render_skill(grounded()).body
        self.assertNotIn("disable-model-invocation", _frontmatter(body))
        self.assertIn("Invoke this deliberately.", body)


class SpecFieldTests(unittest.TestCase):
    """license and compatibility are spec fields; both were being left on the floor."""

    def test_a_licence_is_emitted_only_when_the_caller_supplies_one(self):
        """The issuer knows how the artifact was made, not what covers its content."""
        self.assertNotIn("license:", _frontmatter(render_skill(grounded()).body))
        self.assertIn('license: "MIT"', _frontmatter(render_skill(grounded(), license="MIT").body))

    def test_required_capabilities_become_the_compatibility_statement(self):
        body = render_skill(grounded()).body
        # Quoted, because the value itself contains ": ".
        self.assertIn('compatibility: "Requires a host offering: jira.write."', body)

    def test_an_artifact_needing_nothing_declares_no_compatibility(self):
        how = dataclasses.replace(
            grounded(), contract=dataclasses.replace(CONTRACT, requires=())
        )
        self.assertNotIn("compatibility:", _frontmatter(render_skill(how).body))

    def test_values_carrying_a_colon_are_quoted_rather_than_emitted_plain(self):
        """A plain YAML scalar may not contain ": ", and the description always does."""
        front = _frontmatter(render_skill(grounded()).body)
        for line in front.strip().splitlines():
            if line.startswith(("description:", "compatibility:", "license:")):
                value = line.split(":", 1)[1].strip()
                self.assertTrue(value.startswith('"') and value.endswith('"'), line)

    def test_a_compatibility_line_over_the_cap_is_refused(self):
        how = dataclasses.replace(
            grounded(),
            contract=dataclasses.replace(
                CONTRACT, requires=tuple(f"cap-{i:03d}-{'x' * 20}" for i in range(20))
            ),
        )
        with self.assertRaises(EmitError):
            render_skill(how)
        self.assertEqual(MAX_COMPATIBILITY, 500)


@unittest.skipIf(__import__("importlib").util.find_spec("yaml") is None, "pyyaml absent")
class FrontmatterParsesTests(unittest.TestCase):
    """Frontmatter a YAML parser rejects makes the skill unloadable."""

    def _parse(self, body: str):
        import yaml

        return yaml.safe_load(_frontmatter(body))

    def test_both_targets_parse_as_yaml(self):
        for target in (TARGET_SPEC, TARGET_CLAUDE_CODE):
            with self.subTest(target=target):
                data = self._parse(render_skill(grounded(), target=target).body)
                self.assertEqual(data["name"], "jira-workflow")
                self.assertIsInstance(data["metadata"], dict)

    def test_a_colon_in_an_intent_does_not_break_the_description(self):
        """`description: a: b` is a YAML error, not a description."""
        how = dataclasses.replace(
            grounded(),
            contract=dataclasses.replace(CONTRACT, intent="do this: then that"),
        )
        data = self._parse(render_skill(how).body)
        self.assertIn("do this", data["description"])


class SkillBodyTests(unittest.TestCase):
    """The body has to carry the artifact, not a summary of it."""

    def test_it_carries_the_map_workflow_gate_and_invariants(self):
        body = render_skill(grounded()).body
        self.assertIn("approval before mutation", body)
        for step in CONTRACT.path:
            self.assertIn(step, body)
        self.assertIn("A human approved the workflow mutation", body)
        self.assertIn("The workflow retains a Done terminal state", body)

    def test_it_renders_clauses_in_the_portable_form_not_pythons(self):
        self.assertIn("approved eq true", render_skill(grounded()).body)

    def test_it_carries_the_worked_example_from_the_run(self):
        self.assertIn("Ready for QA", render_skill(grounded()).body)

    def test_it_keeps_looks_discipline_rather_than_trusting_a_report(self):
        body = render_skill(grounded()).body
        self.assertIn("report that the step ran is not evidence", body)

    def test_it_names_the_capabilities_the_concern_needs(self):
        self.assertIn("`jira.write`", render_skill(grounded()).body)


@unittest.skipIf(shutil.which("node") is None, "node is not available")
class WorkflowParsesTests(unittest.TestCase):
    """Generated code that does not parse is worthless, so check it with a parser."""

    def _check(self, source: str) -> subprocess.CompletedProcess:
        # The runtime wraps the body, which is why top-level `return` is legal
        # there. Wrap it the same way before handing it to node.
        wrapped = "(async () => {\n" + source.replace("export const meta", "const meta", 1) + "\n})()"
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write(wrapped)
            path = handle.name
        self.addCleanup(Path(path).unlink)
        return subprocess.run(["node", "--check", path], capture_output=True, text=True)

    def test_the_generated_script_is_valid_javascript(self):
        result = self._check(render_workflow(grounded()).source)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_it_survives_content_that_would_break_naive_interpolation(self):
        how = dataclasses.replace(
            grounded(),
            map={"note": 'quotes " and ` and ${injected} and \\ backslash'},
        )
        result = self._check(render_workflow(how).source)
        self.assertEqual(result.returncode, 0, result.stderr)


class WorkflowShapeTests(unittest.TestCase):
    """Dynamic-workflow constraints, and the loop the script is supposed to be."""

    def test_meta_declares_the_name_the_command_will_have(self):
        script = render_workflow(grounded())
        self.assertEqual(script.name, "jira-workflow")
        self.assertIn('name: "jira-workflow"', script.source)

    def test_meta_phases_match_the_phase_calls(self):
        source = render_workflow(grounded()).source
        declared = set(re.findall(r"\{ title: '([^']+)'", source))
        called = set(re.findall(r"phase\('([^']+)'\)", source))
        self.assertEqual(declared, called)

    def test_it_loads_no_modules(self):
        """A script containing import() fails before the run starts."""
        source = render_workflow(grounded()).source
        self.assertNotIn("import(", source)
        self.assertNotIn("\nimport ", source)
        self.assertNotIn("require(", source)

    def test_the_gate_runs_before_anything_acts(self):
        source = render_workflow(grounded()).source
        self.assertLess(source.index("phase('Check')"), source.index("phase('Do')"))
        self.assertLess(source.index("phase('Do')"), source.index("phase('Look')"))

    def test_a_closed_gate_fizzles_instead_of_proceeding(self):
        source = render_workflow(grounded()).source
        self.assertIn("gate closed", source)
        self.assertIn("fizzled: true", source)

    def test_the_observer_is_told_not_to_read_back_the_executor_report(self):
        """The kernel enforces this structurally; a generated script can only say it."""
        source = render_workflow(grounded()).source
        self.assertIn("Do NOT read back what the previous agents reported", source)

    def test_an_existing_workflow_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(write_workflow(grounded(), tmp).name, "jira-workflow.js")
            with self.assertRaises(EmitError):
                write_workflow(grounded(), tmp)
            self.assertTrue(write_workflow(grounded(), tmp, overwrite=True).is_file())


if __name__ == "__main__":
    unittest.main()
