import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import (  # noqa: E402
    PayloadContextError,
    defer_onboarding,
    default_store_path,
    is_shared,
    TemplateContextError,
    fork_context,
    complete_onboarding,
    decline_onboarding,
    ensure_context,
    inspect_context,
    payload_root,
    resolve_context_path,
)

SHIPPED_TEMPLATE = ROOT / "CONTEXT.template.md"

EVIDENCE = {
    "calibration_domain": "distributed queues; runs incident review",
    "representation_observation": "diagram before terminology landed for relational systems",
    "landed_example": "state diagram then one worked failure, then names",
    "rejected_example": "definitions-first prose; reader could not locate the failure",
}


def make_payload(root: Path) -> Path:
    """Build a directory that looks like an installed skill payload."""
    payload = root / "skills" / "how-do"
    (payload / "runtime" / "howdo").mkdir(parents=True)
    (payload / "SKILL.md").write_text("# How Do\n", encoding="utf-8")
    (payload / "CONTEXT.template.md").write_text(
        SHIPPED_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return payload


def stray_instance(payload: Path) -> Path:
    """A real (non-template) context mistakenly placed inside the payload."""
    text = SHIPPED_TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("template: true\n", "")
    text = text.replace("context_file: CONTEXT.template.md", "context_file: CONTEXT.md")
    text = text.replace("context_id: template", "context_id: pending")
    path = payload / "CONTEXT.md"
    path.write_text(text, encoding="utf-8")
    return path


class PayloadBoundaryTests(unittest.TestCase):
    def test_payload_is_detected_from_the_skill_file_it_ships(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            self.assertEqual(payload_root(payload / "CONTEXT.template.md"), payload)
            self.assertEqual(payload_root(payload / "runtime" / "howdo"), payload)

    def test_store_outside_the_payload_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_payload(Path(tmp))
            store = Path(tmp) / "home" / ".howdo" / "CONTEXT.md"
            store.parent.mkdir(parents=True)
            store.write_text(SHIPPED_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertIsNone(payload_root(store))

    def test_completion_refuses_to_settle_inside_the_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            stray = stray_instance(payload)
            with self.assertRaises(PayloadContextError):
                complete_onboarding(stray, **EVIDENCE)
            # The refusal must leave the file untouched.
            self.assertEqual(inspect_context(stray).state, "onboarding_required")

    def test_decline_refuses_to_settle_inside_the_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            with self.assertRaises(PayloadContextError):
                decline_onboarding(stray_instance(payload))

    def test_payload_settlement_requires_an_explicit_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            settled = complete_onboarding(
                stray_instance(payload), allow_payload=True, **EVIDENCE
            )
            self.assertEqual(inspect_context(settled).state, "ready")


class StoreResolutionTests(unittest.TestCase):
    def test_explicit_selection_wins_over_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            chosen = Path(tmp) / "chosen" / "CONTEXT.md"
            resolved = resolve_context_path(
                chosen, env={"HOWDO_CONTEXT": str(Path(tmp) / "env" / "CONTEXT.md")}
            )
            self.assertEqual(resolved, chosen)

    def test_environment_wins_over_home_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            configured = Path(tmp) / "env" / "CONTEXT.md"
            resolved = resolve_context_path(
                env={"HOWDO_CONTEXT": str(configured)}, home=Path(tmp) / "home"
            )
            self.assertEqual(resolved, configured)

    def test_default_store_is_user_scoped_and_keeps_the_canonical_basename(self):
        """The default is per-platform, so the assertion pins one.

        Passing no ``platform=`` made this agree with whichever host ran it:
        green on Linux CI, red on Windows against correct behaviour.
        """
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "profile"
            roaming = Path(tmp) / "Roaming"
            cases = (
                (
                    "windows, APPDATA set",
                    "win32",
                    {"APPDATA": str(roaming)},
                    roaming / "howdo" / "CONTEXT.md",
                ),
                (
                    "windows, APPDATA unset",
                    "win32",
                    {},
                    home / "AppData" / "Roaming" / "howdo" / "CONTEXT.md",
                ),
                ("posix", "linux", {}, home / ".howdo" / "CONTEXT.md"),
            )
            for label, platform, env, expected in cases:
                with self.subTest(platform=label):
                    resolved = resolve_context_path(
                        env=env, home=home, platform=platform
                    )
                    self.assertEqual(resolved, expected)
                    # A different basename reads as a fork to inspect_context.
                    self.assertEqual(resolved.name, "CONTEXT.md")


class EnsureContextTests(unittest.TestCase):
    def test_first_run_instantiates_the_store_and_requires_onboarding(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            status = ensure_context(
                template=payload / "CONTEXT.template.md", env={}, home=Path(tmp) / "home"
            )
            self.assertEqual(status.state, "onboarding_required")
            self.assertTrue(status.path.exists())
            self.assertIsNone(payload_root(status.path))

    def test_reinstall_never_clobbers_a_settled_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            home = Path(tmp) / "home"
            first = ensure_context(template=payload / "CONTEXT.template.md", env={}, home=home)
            complete_onboarding(first.path, **EVIDENCE)
            settled_id = inspect_context(first.path).metadata["context_id"]

            # Payload is replaced wholesale, exactly as an update would do.
            (payload / "CONTEXT.template.md").write_text(
                SHIPPED_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            second = ensure_context(template=payload / "CONTEXT.template.md", env={}, home=home)

            self.assertEqual(second.state, "ready")
            self.assertEqual(second.metadata["context_id"], settled_id)

    def test_instantiated_store_is_settleable_where_the_payload_copy_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            status = ensure_context(
                template=payload / "CONTEXT.template.md", env={}, home=Path(tmp) / "home"
            )
            complete_onboarding(status.path, **EVIDENCE)
            self.assertEqual(inspect_context(status.path).state, "ready")


class TemplateTypeTests(unittest.TestCase):
    def test_instantiation_strips_the_template_marker_and_opens_a_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            status = ensure_context(
                template=payload / "CONTEXT.template.md", env={}, home=Path(tmp) / "home"
            )
            text = status.path.read_text(encoding="utf-8")
            self.assertNotIn("template: true", text)
            self.assertEqual(status.metadata["context_file"], "CONTEXT.md")
            self.assertEqual(status.metadata["context_id"], "pending")
            # The template itself is unchanged and still a template.
            self.assertEqual(
                inspect_context(payload / "CONTEXT.template.md").state, "template"
            )

    def test_template_cannot_be_forked_because_it_has_no_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            with self.assertRaises(TemplateContextError):
                fork_context(payload / "CONTEXT.template.md", Path(tmp) / "CONTEXT.code.md")


class DeferralTest(unittest.TestCase):
    """"Not now" is a postponement, not a refusal. Conflating them costs a calibration."""

    def _fresh(self, tmp) -> Path:
        return ensure_context(template=SHIPPED_TEMPLATE, env={}, home=Path(tmp) / "home").path

    def test_defer_is_its_own_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fresh(tmp)
            defer_onboarding(p)
            status = inspect_context(p)
            self.assertEqual(status.state, "deferred")
            self.assertNotEqual(status.state, "declined")

    def test_deferral_opens_a_lineage_it_can_settle_into_later(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fresh(tmp)
            defer_onboarding(p)
            deferred_id = inspect_context(p).metadata["context_id"]
            self.assertNotIn(deferred_id, {None, "", "pending"})
            complete_onboarding(p, **EVIDENCE)
            self.assertEqual(inspect_context(p).state, "ready")
            self.assertEqual(inspect_context(p).metadata["context_id"], deferred_id)

    def test_deferring_twice_does_not_churn_the_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fresh(tmp)
            defer_onboarding(p)
            first = inspect_context(p).metadata["context_id"]
            defer_onboarding(p)
            self.assertEqual(inspect_context(p).metadata["context_id"], first)

    def test_a_deferral_can_still_become_a_decline(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fresh(tmp)
            defer_onboarding(p)
            decline_onboarding(p)
            self.assertEqual(inspect_context(p).state, "declined")

    def test_a_decline_is_final_and_cannot_be_reopened_by_deferring(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fresh(tmp)
            decline_onboarding(p)
            with self.assertRaises(ValueError):
                defer_onboarding(p)

    def test_ready_context_has_nothing_to_defer(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fresh(tmp)
            complete_onboarding(p, **EVIDENCE)
            with self.assertRaises(ValueError):
                defer_onboarding(p)

    def test_deferral_is_refused_inside_the_payload_like_any_settlement(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "skills" / "how-do"
            payload.mkdir(parents=True)
            (payload / "SKILL.md").write_text("---\nname: how-do\n---\n", encoding="utf-8")
            status = ensure_context(payload / "CONTEXT.md", template=SHIPPED_TEMPLATE)
            with self.assertRaises(PayloadContextError):
                defer_onboarding(status.path)


class TemplateProseTest(unittest.TestCase):
    """The template must describe itself; the store it produces must not."""

    def test_shipped_template_still_declares_itself(self):
        text = SHIPPED_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("template-only:start", text)
        self.assertIn("template-only:end", text)
        self.assertIn("not a context", text)

    def test_instance_drops_the_template_only_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = ensure_context(
                template=SHIPPED_TEMPLATE, env={}, home=Path(tmp) / "home"
            )
            text = status.path.read_text(encoding="utf-8")
            self.assertNotIn("template-only", text)
            self.assertNotIn("shipped template", text.lower())
            # The instance must never repeat the template's claim about itself:
            # a store whose body says it cannot be settled contradicts the
            # frontmatter that just asked for onboarding.
            self.assertNotIn("cannot be settled", text)
            self.assertNotIn("Do not settle this file", text)
            self.assertTrue(text.split("---", 2)[2].lstrip().startswith("# How Do Context"))

    def test_instance_keeps_every_required_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = ensure_context(
                template=SHIPPED_TEMPLATE, env={}, home=Path(tmp) / "home"
            )
            text = status.path.read_text(encoding="utf-8")
            for heading in (
                "Calibration domains",
                "Representation observations",
                "Structures that landed",
                "Structures that did not land",
                "Interaction observations",
                "LongHow settlements",
            ):
                self.assertIn(f"## {heading}", text)
            self.assertEqual(status.state, "onboarding_required")

    def test_settled_instance_carries_no_template_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = ensure_context(
                template=SHIPPED_TEMPLATE, env={}, home=Path(tmp) / "home"
            )
            complete_onboarding(status.path, **EVIDENCE)
            text = status.path.read_text(encoding="utf-8")
            self.assertEqual(inspect_context(status.path).state, "ready")
            self.assertNotIn("template", text.lower().split("## calibration")[0])


class PlatformStoreTest(unittest.TestCase):
    """The store belongs where the platform already keeps per-user state."""

    def test_windows_default_is_appdata(self):
        with tempfile.TemporaryDirectory() as tmp:
            roaming = Path(tmp) / "Roaming"
            resolved = default_store_path(
                env={"APPDATA": str(roaming)}, home=Path(tmp) / "profile", platform="win32"
            )
            self.assertEqual(resolved, roaming / "howdo" / "CONTEXT.md")

    def test_windows_falls_back_to_profile_when_appdata_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "profile"
            resolved = default_store_path(env={}, home=home, platform="win32")
            self.assertEqual(
                resolved, home / "AppData" / "Roaming" / "howdo" / "CONTEXT.md"
            )

    def test_posix_default_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolved = default_store_path(env={}, home=Path(tmp), platform="linux")
            self.assertEqual(resolved, Path(tmp) / ".howdo" / "CONTEXT.md")

    def test_resolution_ignores_what_is_already_on_disk(self):
        """Same config, same path — resolution is not steered by stray files."""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "profile"
            stray = home / ".howdo" / "CONTEXT.md"
            stray.parent.mkdir(parents=True)
            stray.write_text("settled", encoding="utf-8")
            roaming = Path(tmp) / "Roaming"
            resolved = default_store_path(
                env={"APPDATA": str(roaming)}, home=home, platform="win32"
            )
            self.assertEqual(resolved, roaming / "howdo" / "CONTEXT.md")

    def test_env_override_still_outranks_the_platform_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            chosen = Path(tmp) / "elsewhere" / "CONTEXT.md"
            resolved = resolve_context_path(
                env={"HOWDO_CONTEXT": str(chosen), "APPDATA": str(Path(tmp) / "Roaming")},
                home=Path(tmp),
                platform="win32",
            )
            self.assertEqual(resolved, chosen)


class SharedScopeTest(unittest.TestCase):
    """Generic, install-wide context is available but never the default."""

    def _payload(self, tmp: Path) -> Path:
        payload = tmp / "skills" / "how-do"
        payload.mkdir(parents=True)
        (payload / "SKILL.md").write_text("---\nname: how-do\n---\n", encoding="utf-8")
        return payload

    def test_default_scope_is_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = ensure_context(
                template=SHIPPED_TEMPLATE, env={}, home=Path(tmp) / "home"
            )
            self.assertFalse(is_shared(status.metadata))
            self.assertEqual(status.metadata.get("scope"), "user")

    def test_unmarked_payload_context_is_still_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._payload(Path(tmp))
            status = ensure_context(payload / "CONTEXT.md", template=SHIPPED_TEMPLATE)
            self.assertIsNotNone(payload_root(status.path))
            with self.assertRaises(PayloadContextError):
                complete_onboarding(status.path, **EVIDENCE)
            with self.assertRaises(PayloadContextError):
                decline_onboarding(status.path)

    def test_shared_payload_context_may_settle(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._payload(Path(tmp))
            status = ensure_context(
                payload / "CONTEXT.md", template=SHIPPED_TEMPLATE, scope="shared"
            )
            self.assertTrue(is_shared(status.metadata))
            complete_onboarding(status.path, **EVIDENCE)
            self.assertEqual(inspect_context(status.path).state, "ready")

    def test_scope_absence_reads_as_user(self):
        """A store written before the key existed is per-person, not generic."""
        self.assertFalse(is_shared({}))
        self.assertFalse(is_shared({"scope": ""}))
        self.assertTrue(is_shared({"scope": "SHARED"}))


if __name__ == "__main__":
    unittest.main()
