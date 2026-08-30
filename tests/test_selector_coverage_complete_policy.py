"""Malformed-policy and reload-boundary contracts for companion routing."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import config as config_module
from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig
from agency_runtime.core.selector import pipeline, policy
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.stickiness import clear_session_routing


def test_policy_path_resolution_uses_config_and_propagates_config_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENCY_POLICY_PATH", raising=False)
    monkeypatch.setattr(
        config_module,
        "load_config",
        lambda: SimpleNamespace(companion_policy_path="~/custom-policy.yaml"),
    )
    assert policy._resolve_policy_path() == Path.home() / "custom-policy.yaml"

    monkeypatch.setattr(
        config_module,
        "load_config",
        lambda: (_ for _ in ()).throw(OSError("config unavailable")),
    )
    with pytest.raises(OSError, match="config unavailable"):
        policy._resolve_policy_path()


def test_relative_environment_policy_path_is_config_relative_and_cwd_stable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "configuration"
    config_dir.mkdir()
    config_path = config_dir / "agency.yaml"
    config_path.write_text("profile: standard\n", encoding="utf-8")
    other_cwd = tmp_path / "unrelated-working-directory"
    other_cwd.mkdir()
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AGENCY_POLICY_PATH", "policy/companions.yaml")

    expected = (config_dir / "policy" / "companions.yaml").resolve()
    first = policy._resolve_policy_path()
    assert config_module.load_config(reload=True).companion_policy_path == str(expected)
    monkeypatch.chdir(other_cwd)

    assert first == expected
    assert policy._resolve_policy_path() == expected


def test_route_request_uses_supplied_config_policy_not_process_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_policy = tmp_path / "custom" / "companions.yaml"
    global_policy = tmp_path / "global" / "companions.yaml"
    custom_policy.parent.mkdir()
    global_policy.parent.mkdir()

    def write_policy(path: Path, action: str, trigger: str, slug: str) -> None:
        path.write_text(
            "actions:\n"
            f"  {action}:\n"
            f"    triggers: [{trigger}]\n"
            "    always_include:\n"
            f"      - slug: {slug}\n"
            "    conditional: []\n",
            encoding="utf-8",
        )
        path.chmod(0o600)

    write_policy(custom_policy, "CUSTOM", "customneedle", "custom-agent")
    write_policy(global_policy, "GLOBAL", "globalneedle", "global-agent")
    monkeypatch.setenv("AGENCY_POLICY_PATH", str(global_policy))
    unrelated = tmp_path / "working-directory"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    request = pipeline._route_request(
        "session",
        "please handle customneedle",
        [{"slug": "custom-agent", "name": "Custom Agent"}],
        AgencyConfig(companion_policy_path=str(custom_policy.resolve())),
    )
    actions, companions = policy.detect_actions(
        request.user_message,
        request.policy,
        active_slugs=request.active_ids,
    )

    assert actions == ["CUSTOM"]
    assert companions == ["custom-agent"]


def test_bundled_policy_load_failure_is_cached_as_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(policy, "_BUNDLED_COMPANION_POLICY", None)
    monkeypatch.setattr(
        policy,
        "_read_bounded_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("bundle unavailable")),
    )

    assert policy._load_bundled_policy() == {}
    assert policy._load_bundled_policy() == {}


def test_missing_default_policy_never_reuses_prior_custom_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        "actions:\n"
        "  CUSTOM:\n"
        "    triggers: [customneedle]\n"
        "    always_include: []\n"
        "    conditional: []\n",
        encoding="utf-8",
    )
    custom.chmod(0o600)
    missing = tmp_path / "missing.yaml"
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_FILE_IDENTITY", None)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)
    monkeypatch.setattr(policy, "_POLICY_REQUEST_KEY", "")
    monkeypatch.setattr(policy, "_POLICY_CHECKED_AT", 0.0)
    monkeypatch.setattr(policy, "_resolve_policy_path", lambda: missing)

    assert "CUSTOM" in policy.load_policy(custom)["actions"]
    first = policy.load_policy()
    second = policy.load_policy()

    assert "CUSTOM" not in first.get("actions", {})
    assert policy.detect_fallback_companions(first) == [
        "agents-orchestrator",
        "chief-of-staff",
    ]
    assert second is first


@pytest.mark.parametrize("linked_component", ["file", "parent"])
def test_policy_loader_rejects_linked_path_components(
    tmp_path: Path,
    linked_component: str,
) -> None:
    destination = tmp_path / "destination"
    destination.mkdir()
    target = destination / "policy.yaml"
    target.write_text("actions: {}\n", encoding="utf-8")
    if linked_component == "file":
        candidate = tmp_path / "linked-policy.yaml"
        link = candidate
        link_target = target
        is_directory = False
    else:
        link = tmp_path / "linked-parent"
        candidate = link / "policy.yaml"
        link_target = destination
        is_directory = True
    try:
        link.symlink_to(link_target, target_is_directory=is_directory)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(policy.PolicyIdentityError, match="symlink or reparse point"):
        policy.load_policy(candidate)


def test_policy_loader_rejects_file_swapped_to_link_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "policy.yaml"
    candidate.write_text("actions: {}\n", encoding="utf-8")
    candidate.chmod(0o600)
    target = tmp_path / "redirected.yaml"
    target.write_text("actions:\n  REDIRECTED: {}\n", encoding="utf-8")
    original_read = policy._read_bounded_policy

    def swap_then_read(path: Path, **kwargs: object) -> object:
        candidate.unlink()
        try:
            candidate.symlink_to(target)
        except OSError as exc:
            pytest.skip(f"symlink creation unavailable: {exc}")
        return original_read(path, **kwargs)

    monkeypatch.setattr(policy, "_read_bounded_policy", swap_then_read)
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_FILE_IDENTITY", None)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)

    with pytest.raises(policy.PolicyIdentityError, match="symlink or reparse point"):
        policy.load_policy(candidate)


def test_concurrent_route_and_explain_keep_distinct_policy_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def write_policy(path: Path, action: str, trigger: str, slug: str) -> None:
        path.write_text(
            "actions:\n"
            f"  {action}:\n"
            f"    triggers: [{trigger}]\n"
            "    always_include:\n"
            f"      - slug: {slug}\n"
            "    conditional: []\n",
            encoding="utf-8",
        )
        path.chmod(0o600)

    route_path = tmp_path / "route.yaml"
    explain_path = tmp_path / "explain.yaml"
    write_policy(route_path, "ROUTE_A", "alpha-policy", "agent-a")
    write_policy(explain_path, "ROUTE_B", "beta-policy", "agent-b")
    route_config = AgencyConfig(
        companion_policy_path=str(route_path),
        judge=JudgeConfig(model="", confidence_bypass_threshold=999.0),
        ollama=OllamaConfig(enabled=False),
        providers=(),
    )
    explain_config = AgencyConfig(
        companion_policy_path=str(explain_path),
        judge=JudgeConfig(model="", confidence_bypass_threshold=999.0),
        ollama=OllamaConfig(enabled=False),
        providers=(),
    )
    original_read = policy._read_bounded_policy
    activity_lock = threading.Lock()
    active_reads = 0
    maximum_active_reads = 0

    def delayed_read(path: Path, **kwargs: object) -> object:
        nonlocal active_reads, maximum_active_reads
        with activity_lock:
            active_reads += 1
            maximum_active_reads = max(maximum_active_reads, active_reads)
        try:
            time.sleep(0.03)
            return original_read(path, **kwargs)
        finally:
            with activity_lock:
                active_reads -= 1

    monkeypatch.setattr(policy, "_read_bounded_policy", delayed_read)
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_FILE_IDENTITY", None)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)
    monkeypatch.setattr(policy, "_POLICY_REQUEST_KEY", "")
    monkeypatch.setattr(policy, "_POLICY_CHECKED_AT", 0.0)
    clear_cache()
    clear_session_routing()
    start = threading.Barrier(3)
    results: dict[str, list[str]] = {}
    errors: list[BaseException] = []

    def route_worker() -> None:
        try:
            start.wait()
            routed = pipeline.route(
                "concurrent-route",
                "alpha-policy request",
                [{"slug": "agent-a", "name": "Agent A"}],
                config=route_config,
            )
            results["route"] = list(routed["selected_ids"])
        except BaseException as exc:  # captured for assertion in the parent thread
            errors.append(exc)

    def explain_worker() -> None:
        try:
            start.wait()
            receipt = explain_route(
                "concurrent-explain",
                "beta-policy request",
                [{"slug": "agent-b", "name": "Agent B"}],
                config=explain_config,
            )
            results["explain"] = [item["slug"] for item in receipt["selected"]]
        except BaseException as exc:  # captured for assertion in the parent thread
            errors.append(exc)

    threads = [threading.Thread(target=route_worker), threading.Thread(target=explain_worker)]
    for thread in threads:
        thread.start()
    start.wait()
    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert errors == []
    assert results == {"route": ["agent-a"], "explain": ["agent-b"]}
    assert maximum_active_reads == 1


def test_trigger_and_condition_matching_rejects_nonlexical_inputs() -> None:
    policy._compiled_trigger.cache_clear()
    assert policy._compiled_trigger("_fallback_") is None
    assert policy._compiled_trigger("***") is None
    assert policy._matches("code review", 7) is False
    assert policy._matches_condition("code review", ["code"]) is False


def test_multiword_condition_requires_more_than_one_generic_token() -> None:
    assert policy._matches_condition("test agent selection live", "test result analysis") is False
    assert policy._matches_condition("analyze the test results", "test result analysis") is True
    assert policy._matches_condition("authentication failed", "authentication") is True


def test_policy_reload_reuses_unchanged_file_and_retains_last_good_same_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "policy.yaml"
    path.write_text("actions:\n  FIRST:\n    triggers: [alpha]\n", encoding="utf-8")
    path.chmod(0o600)
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_MTIME", 0.0)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)
    monkeypatch.setattr(policy, "_POLICY_REQUEST_KEY", "")
    monkeypatch.setattr(policy, "_POLICY_CHECKED_AT", 0.0)

    first = policy.load_policy(path)
    second = policy.load_policy(path)
    assert first is second
    assert set(second["actions"]) == {"FIRST"}

    monkeypatch.setattr(policy, "_POLICY_MTIME", -1)
    monkeypatch.setattr(
        policy,
        "_read_bounded_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid update")),
    )
    retained = policy.load_policy(path)
    assert retained is first


def test_policy_route_validation_reports_every_malformed_division_shape() -> None:
    routes, errors = policy._policy_routes(
        {
            "actions": {},
            "division_anchors": {
                "not-a-mapping": [],
                "bad-anchor": {"anchor": " ", "conditional": "not-a-list"},
                "entries": {
                    "conditional": [
                        "incomplete",
                        {"slug": "", "when": "condition"},
                        {"slug": "valid", "when": ""},
                        ("tuple-specialist", "tuple condition"),
                    ]
                },
            },
        }
    )

    assert {route["slug"] for route in routes} == {"valid", "tuple-specialist"}
    assert "division_anchors.not-a-mapping must be a mapping" in errors
    assert "division_anchors.bad-anchor.anchor must be a non-empty string" in errors
    assert "division_anchors.bad-anchor.conditional must be a list" in errors
    assert any("must contain a slug and condition" in error for error in errors)
    assert any(".slug must be a non-empty string" in error for error in errors)
    assert any(".when must be a non-empty string" in error for error in errors)


def test_slug_and_availability_validation_rejects_adversarial_registry_shapes() -> None:
    errors: list[str] = []
    assert policy._slug_list("not-a-list", path="items", errors=errors) == []
    assert policy._slug_list(["same", "same", 7], path="items", errors=errors) == [
        "same",
        "same",
    ]
    assert "items must be a list" in errors
    assert "items[2] must be a non-empty string" in errors
    assert "items must not contain duplicate slugs" in errors

    invalid_mapping = policy.validate_policy(
        {"actions": {}, "specialist_availability": "invalid"},
        [],
    )
    assert "specialist_availability must be a mapping" in invalid_mapping["errors"]

    invalid_gated = policy.validate_policy(
        {
            "actions": {},
            "specialist_availability": {
                "schema_version": 2,
                "enabled": [],
                "roster_gated": "invalid",
            },
        },
        [],
    )
    assert "specialist_availability.schema_version must be 1" in invalid_gated["errors"]
    assert "specialist_availability.roster_gated must be a mapping" in invalid_gated["errors"]

    conflicting = policy.validate_policy(
        {
            "actions": {
                "ACTION": {
                    "always_include": [{"slug": "route"}],
                    "conditional": [],
                }
            },
            "specialist_availability": {
                "schema_version": 1,
                "enabled": ["route", "both", "extra"],
                "roster_gated": {
                    "reason": "requires activation",
                    "slugs": ["both"],
                },
            },
        },
        ["route"],
    )
    assert any("both enabled and roster-gated: both" in item for item in conflicting["errors"])
    assert any(
        "availability declares unreferenced specialists: both, extra" in item
        for item in conflicting["errors"]
    )


def test_invalid_companion_identity_is_never_appended() -> None:
    companions: list[str] = []
    policy._append_eligible_companion(companions, None, None)
    policy._append_eligible_companion(companions, "", None)
    assert companions == []


def test_nonmatching_division_condition_is_not_promoted() -> None:
    actions, companions = policy.detect_actions(
        "optimize the database",
        {
            "actions": {
                "OTHER": {
                    "triggers": ["unrelated"],
                    "always_include": [],
                    "conditional": [],
                }
            },
            "division_anchors": {
                "data": {
                    "keywords": ["database"],
                    "anchor": "database-anchor",
                    "conditional": [{"slug": "security-reviewer", "when": "security audit"}],
                }
            },
        },
    )

    assert actions == []
    assert companions == ["database-anchor"]
