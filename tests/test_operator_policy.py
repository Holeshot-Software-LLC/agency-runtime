"""Operator house rules: bounded, attested, subordinate, and actually delivered."""

from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path

import pytest

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.configuration_patch import _set_validator
from agency_runtime.core.configuration_schema import validate_config_document
from agency_runtime.core.operator_policy import (
    EMPTY_OPERATOR_POLICY_REFERENCE,
    MAX_OPERATOR_POLICY_CHARS,
    MAX_OPERATOR_POLICY_LINES,
    OPERATOR_POLICY_FOOTER,
    OPERATOR_POLICY_HEADER,
    OperatorPolicyError,
    normalized_operator_policy,
    operator_policy_reference,
    render_operator_policy,
)
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_KERNEL,
    RESIDENT_MANAGER_KERNEL_REFERENCE,
)
from agency_runtime.core.store.sqlite import Store

POLICY = "Never commit to main.\nUse a worktree, a branch, and a PR."


# ── normalization ──────────────────────────────────────────────


def test_absent_policy_is_empty_rather_than_a_block() -> None:
    for value in (None, "", "   ", "\n\n\t\n"):
        assert normalized_operator_policy(value) == ""
        assert render_operator_policy(normalized_operator_policy(value)) == ""


def test_normalization_never_rewrites_what_the_operator_wrote() -> None:
    """An operator has to be able to read their policy back out unchanged."""

    assert normalized_operator_policy("  Never commit to main.  ") == "Never commit to main."
    assert normalized_operator_policy("a\r\nb\rc") == "a\nb\nc"
    # Trailing spaces are invisible but change the hash; an unedited policy must
    # not look edited in evidence.
    assert normalized_operator_policy("a   \nb\t \n") == "a\nb"
    # Structure survives: this is prose, and line breaks are how it stays readable.
    assert normalized_operator_policy("one\n\ntwo") == "one\n\ntwo"
    assert normalized_operator_policy("tab\there") == "tab\there"


def test_control_characters_that_would_corrupt_the_block_are_stripped() -> None:
    assert normalized_operator_policy("safe\x00\x07text") == "safetext"
    assert normalized_operator_policy("esc\x1b[31mred") == "esc[31mred"


def test_non_text_policy_is_refused() -> None:
    for value in (42, ["a"], {"a": 1}, True):
        with pytest.raises(OperatorPolicyError, match="must be text"):
            normalized_operator_policy(value)


# ── budget ─────────────────────────────────────────────────────


def test_over_budget_policy_is_rejected_and_never_silently_truncated() -> None:
    """Truncation would inject something the operator did not write."""

    oversized = "x" * (MAX_OPERATOR_POLICY_CHARS + 1)
    with pytest.raises(OperatorPolicyError) as excinfo:
        normalized_operator_policy(oversized)
    assert str(MAX_OPERATOR_POLICY_CHARS) in str(excinfo.value)

    at_budget = "x" * MAX_OPERATOR_POLICY_CHARS
    assert normalized_operator_policy(at_budget) == at_budget


def test_line_budget_is_enforced_independently_of_the_character_budget() -> None:
    many_short_lines = "\n".join("x" for _ in range(MAX_OPERATOR_POLICY_LINES + 1))
    assert len(many_short_lines) < MAX_OPERATOR_POLICY_CHARS
    with pytest.raises(OperatorPolicyError, match="lines"):
        normalized_operator_policy(many_short_lines)


# ── rendering and attestation ──────────────────────────────────


def test_rendered_block_names_its_source_and_states_its_precedence() -> None:
    rendered = render_operator_policy(normalized_operator_policy(POLICY))
    assert rendered.startswith(OPERATOR_POLICY_HEADER)
    assert rendered.endswith(OPERATOR_POLICY_FOOTER)
    assert POLICY in rendered
    # Rule 8 has to be legible to the model reading the block, not just to us.
    assert "never withhold your answer" in OPERATOR_POLICY_FOOTER


def test_policy_is_attested_separately_from_agencys_own_contract() -> None:
    """Two blocks, two hashes — evidence can answer who asserted what."""

    reference = operator_policy_reference(normalized_operator_policy(POLICY))
    assert len(reference.content_hash) == 64
    assert reference.content_hash != RESIDENT_MANAGER_KERNEL_REFERENCE.content_hash
    assert reference.char_count == len(render_operator_policy(POLICY))
    assert reference.as_dict()["content_hash"] == reference.content_hash


def test_absent_policy_attests_to_nothing_rather_than_to_an_empty_string_hash() -> None:
    assert operator_policy_reference("") == EMPTY_OPERATOR_POLICY_REFERENCE
    assert EMPTY_OPERATOR_POLICY_REFERENCE.content_hash == ""


def test_equivalent_policies_hash_equal_and_edits_change_the_hash() -> None:
    a = operator_policy_reference(normalized_operator_policy("Never commit to main.  "))
    b = operator_policy_reference(normalized_operator_policy("Never commit to main."))
    c = operator_policy_reference(normalized_operator_policy("Never commit to trunk."))
    assert a == b
    assert a.content_hash != c.content_hash


# ── the four declaration sites ─────────────────────────────────


def test_every_configuration_path_accepts_operator_policy_identically() -> None:
    """The recurring break: one field spelled in several places, updated in some.

    `operator_policy` has to survive the dataclass default, the document
    validator, the `agency config set` validator, and a serialize/parse round
    trip. Each of those is a separate allowlist, and a field missing from any one
    of them is accepted by one path and rejected by another.
    """

    assert AgencyConfig().operator_policy == ""

    validated = validate_config_document({"operator_policy": f"  {POLICY}  "})
    assert validated["operator_policy"] == POLICY

    assert _set_validator("operator_policy", POLICY) == POLICY

    import yaml

    from agency_runtime.core.config import _dict_to_config, config_to_yaml

    rendered = config_to_yaml(dataclasses.replace(AgencyConfig(), operator_policy=POLICY))
    assert _dict_to_config(yaml.safe_load(rendered)).operator_policy == POLICY


def test_over_budget_policy_is_refused_by_both_validators_not_just_one() -> None:
    oversized = "x" * (MAX_OPERATOR_POLICY_CHARS + 1)
    with pytest.raises(ValueError, match=str(MAX_OPERATOR_POLICY_CHARS)):
        validate_config_document({"operator_policy": oversized})
    with pytest.raises(ValueError, match=str(MAX_OPERATOR_POLICY_CHARS)):
        _set_validator("operator_policy", oversized)


# ── end to end ─────────────────────────────────────────────────


def _context_for(policy: str) -> str:
    from agency_runtime.adapters.hermes.plugin import HermesAdapter

    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "operator-policy.db")
        config = dataclasses.replace(AgencyConfig(), operator_policy=policy)
        result = HermesAdapter(store=store).build_preflight_context(
            "operator-policy-session",
            "agency status",
            config=config,
        )
        assert result is not None
        return str(result["context"])


def test_configured_policy_reaches_the_turn_after_agencys_own_frame() -> None:
    """The point of the feature: set it once, and every turn carries it."""

    context = _context_for(POLICY)
    assert POLICY in context
    assert OPERATOR_POLICY_HEADER in context
    # Agency's contract comes first, so a budget cut takes the operator's text.
    assert context.startswith(RESIDENT_MANAGER_KERNEL)
    assert context.index(RESIDENT_MANAGER_KERNEL) < context.index(OPERATOR_POLICY_HEADER)


def test_unset_policy_adds_nothing_at_all_to_a_turn() -> None:
    """Agency ships no opinion about anyone's conventions."""

    context = _context_for("")
    assert OPERATOR_POLICY_HEADER not in context
    assert OPERATOR_POLICY_FOOTER not in context


# ── a bad policy must never take a host down ───────────────────


def test_loading_an_over_budget_policy_drops_it_instead_of_failing_the_turn() -> None:
    """Rule 8, applied to Agency's own configuration.

    The strict normalizer belongs where an operator is making a change and can act
    on the error. A config file already on disk is read on every turn on every
    host, so raising there turns one over-long house rule into a total outage --
    Agency withholding turns because Agency is misconfigured. A house rule that
    does not fit is not a reason to stop answering.
    """

    import yaml

    from agency_runtime.core.config import _dict_to_config

    oversized = "x" * (MAX_OPERATOR_POLICY_CHARS + 1)
    config = _dict_to_config(yaml.safe_load("operator_policy: '" + oversized + "'"))

    assert config.operator_policy == ""
    assert str(MAX_OPERATOR_POLICY_CHARS) in config.operator_policy_error


def test_a_dropped_policy_is_reported_rather_than_vanishing() -> None:
    """Dropping quietly is right for the turn and wrong for the operator."""

    from agency_runtime.core.doctor import _config_checks

    healthy = dataclasses.replace(AgencyConfig(), operator_policy=POLICY)
    names = {check.name: check for check in _config_checks(healthy)}
    assert names["operator_policy"].status == "pass"

    broken = dataclasses.replace(
        AgencyConfig(), operator_policy="", operator_policy_error="too long"
    )
    reported = {check.name: check for check in _config_checks(broken)}
    assert reported["operator_policy"].status == "warn"
    assert "not being applied" in reported["operator_policy"].message

    silent = {check.name for check in _config_checks(AgencyConfig())}
    assert "operator_policy" not in silent


def test_the_change_that_makes_a_turn_impossible_is_still_refused_up_front() -> None:
    """Leniency is only for load. The paths an operator drives stay strict."""

    oversized = "x" * (MAX_OPERATOR_POLICY_CHARS + 1)
    with pytest.raises(ValueError):
        validate_config_document({"operator_policy": oversized})
    with pytest.raises(ValueError):
        _set_validator("operator_policy", oversized)


# ── the fleet cases ────────────────────────────────────────────


def test_install_refuses_house_rules_it_would_never_apply() -> None:
    """Strict where the config is chosen, lenient where it is merely read.

    Nobody need be watching. Install's exit code is what a provisioning step
    reads, so refusing turns a silently dropped guardrail into a container that
    visibly fails to provision. Every later read stays lenient so a running
    container never stops answering over a typo.
    """

    import argparse

    from agency_runtime.cli.install_commands import DEFAULT_DEPENDENCIES, _operator_policy_refusal

    del argparse
    emitted: list[object] = []
    dependencies = dataclasses.replace(DEFAULT_DEPENDENCIES, emit_json=emitted.append)

    healthy = dataclasses.replace(AgencyConfig(), operator_policy=POLICY)
    assert _operator_policy_refusal(healthy, json_mode=True, dependencies=dependencies) is None
    assert emitted == []

    broken = dataclasses.replace(AgencyConfig(), operator_policy_error="policy is 3000 characters")
    assert _operator_policy_refusal(broken, json_mode=True, dependencies=dependencies) == 2
    assert emitted and "3000 characters" in str(emitted[0])


def test_footer_closes_the_ship_it_loophole_for_an_unattended_agent() -> None:
    """An agent told to "ship it" must not reason its way past a house rule.

    The earlier wording said a rule conflicting with the request loses, which is
    fine with a human in the loop and wrong on a conveyor: almost no house rule
    actually blocks a goal, it constrains the method. "Never commit to main" does
    not stop you shipping, it changes how you ship.
    """

    footer = OPERATOR_POLICY_FOOTER
    assert "constraints on HOW you do the work, not on whether" in footer
    assert "Satisfy the request within them" in footer
    # Rule 8 survives the hardening -- guidance strength is not turn withholding.
    assert "never withhold your answer" in footer
    # And an impossible rule is reported rather than silently skipped.
    assert "state which rule you could not honor and why" in footer
    assert "inconvenient, slower, or because the request sounds urgent" in footer
