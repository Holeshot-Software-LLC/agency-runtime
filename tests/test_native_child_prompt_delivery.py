"""Hook-owned native-child prompt delivery envelope contracts."""

from __future__ import annotations

import base64
import json
import re
from hashlib import sha256

import pytest

from agency_runtime.core.native_child_prompt_delivery import (
    InferenceTeamCard,
    codex_opaque_child_message_ciphertext,
    inference_team_digest,
    is_codex_opaque_collaboration_message,
    parse_codex_native_child_execution_message,
    parse_inference_team_delivery,
    parse_jit_specialist_delivery,
    parse_native_child_prompt_delivery,
    render_codex_direct_native_child_prompt_delivery,
    render_codex_native_child_execution_message,
    render_codex_opaque_native_child_prompt_delivery,
    render_inference_team_context_segment,
    render_inference_team_delivery,
    render_jit_specialist_delivery,
    render_native_child_prompt_delivery,
)
from agency_runtime.core.unit_assignment import work_unit_goal_hash


def _render(*, task: str = "Review auth", prompt: str = "Exact specialist prompt") -> str:
    return render_native_child_prompt_delivery(
        task,
        prompt,
        host="codex",
        parent_session_id="session",
        parent_trace_id="trace",
        tool_use_id="call-1",
        work_unit_id="unit-auth",
        specialist_slug="code-reviewer",
        specialist_version="v1",
        specialist_prompt_hash=sha256(prompt.encode()).hexdigest(),
        activation_token="one-use-token",
    )


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _team_cards() -> tuple[InferenceTeamCard, InferenceTeamCard]:
    prompts = ("Review the authentication boundary.", "Verify the focused regression tests.")
    return (
        InferenceTeamCard("security-reviewer", "rev-security", _digest(prompts[0]), prompts[0]),
        InferenceTeamCard("test-engineer", "rev-tests", _digest(prompts[1]), prompts[1]),
    )


def _team_identity() -> dict[str, str]:
    return {
        "host": "claude",
        "parent_session_id": "session-parent",
        "parent_trace_id": "trace-parent",
        "launch_id": "tool-use-launch",
        "decision_id": "decision-inference-1",
        "provider_receipt_digest": _digest("provider-receipt"),
        "candidate_digest": _digest("runtime"),
        "install_id": "install-1",
        "bundle_digest": _digest("bundle"),
        "runtime_digest": _digest("runtime"),
        "issued_at": "2026-08-12T12:00:00Z",
        "expires_at": "2026-08-12T12:05:00Z",
        "nonce": "nonce-1",
        "binding_kind": "tool_use",
        "binding_id": "tool-use-launch",
    }


def _render_team(
    *,
    task: str = "Review this exact authentication change.",
    cards: tuple[InferenceTeamCard, ...] | None = None,
) -> str:
    return render_inference_team_delivery(
        task,
        cards or _team_cards(),
        **_team_identity(),
    )


def test_codex_opaque_collaboration_message_shape_is_exact() -> None:
    assert is_codex_opaque_collaboration_message("gAAAAA" + "opaque-host-ciphertext" * 2)
    assert not is_codex_opaque_collaboration_message("gAAAAAtoo-short")
    assert not is_codex_opaque_collaboration_message("gAAAAA" + "opaque-host-ciphertext" * 2 + "\n")
    assert not is_codex_opaque_collaboration_message(None)


def test_delivery_round_trip_preserves_original_task_and_exact_prompt() -> None:
    rendered = _render()

    parsed = parse_native_child_prompt_delivery(rendered)

    assert parsed is not None
    assert parsed.original_task == "Review auth"
    assert parsed.prompt_body == "Exact specialist prompt"
    assert parsed.host == "codex"
    assert parsed.parent_session_id == "session"
    assert parsed.parent_trace_id == "trace"
    assert parsed.tool_use_id == "call-1"
    assert parsed.work_unit_id == "unit-auth"
    assert parsed.specialist_slug == "code-reviewer"
    assert parsed.activation_token == "one-use-token"
    assert parsed.goal_hash == work_unit_goal_hash("Review auth")


def test_inference_team_round_trip_preserves_exact_order_and_all_bindings() -> None:
    task = "Review this exact authentication change."
    cards = _team_cards()
    rendered = _render_team(task=task, cards=cards)

    parsed = parse_inference_team_delivery(rendered)

    assert parsed is not None
    assert parsed.original_task == task
    assert parsed.host == "claude"
    assert parsed.parent_session_id == "session-parent"
    assert parsed.parent_trace_id == "trace-parent"
    assert parsed.launch_id == "tool-use-launch"
    assert parsed.decision_id == "decision-inference-1"
    assert parsed.provider_receipt_digest == _digest("provider-receipt")
    assert parsed.task_sha256 == _digest(task)
    assert parsed.candidate_digest == _digest("runtime")
    assert parsed.install_id == "install-1"
    assert parsed.bundle_digest == _digest("bundle")
    assert parsed.runtime_digest == _digest("runtime")
    assert parsed.issued_at == "2026-08-12T12:00:00Z"
    assert parsed.expires_at == "2026-08-12T12:05:00Z"
    assert parsed.nonce == "nonce-1"
    assert parsed.binding_kind == "tool_use"
    assert parsed.binding_id == "tool-use-launch"
    assert parsed.team_digest == inference_team_digest(cards)
    assert [card.specialist_slug for card in parsed.cards] == [
        "security-reviewer",
        "test-engineer",
    ]
    assert [card.prompt_body for card in parsed.cards] == [
        "Review the authentication boundary.",
        "Verify the focused regression tests.",
    ]
    assert inference_team_digest(tuple(reversed(cards))) != parsed.team_digest
    segment = render_inference_team_context_segment(task, cards, **_team_identity())
    assert rendered == task + segment


def test_inference_team_rejects_delivery_lifetime_over_the_shared_maximum() -> None:
    overlong_identity = {**_team_identity(), "expires_at": "2026-08-12T12:05:01Z"}
    with pytest.raises(ValueError, match="lifetime exceeds"):
        render_inference_team_delivery(
            "Review this exact authentication change.",
            _team_cards(),
            **overlong_identity,
        )

    rendered = _render_team()
    marker_pattern = re.compile(r"(<!-- agency-native-child-team:v6:)([A-Za-z0-9_-]+)( -->)")
    marker = marker_pattern.search(rendered)
    assert marker is not None
    encoded = marker.group(2)
    metadata = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    metadata["expires_at"] = "2026-08-12T12:05:01Z"
    overlong_metadata = (
        base64.urlsafe_b64encode(
            json.dumps(metadata, separators=(",", ":"), sort_keys=True).encode()
        )
        .decode()
        .rstrip("=")
    )
    tampered = rendered[: marker.start(2)] + overlong_metadata + rendered[marker.end(2) :]

    assert parse_inference_team_delivery(tampered) is None


def test_inference_team_rejects_candidate_runtime_identity_drift() -> None:
    drifted_identity = {**_team_identity(), "candidate_digest": _digest("stale-runtime")}

    with pytest.raises(ValueError, match="must match runtime_digest"):
        render_inference_team_delivery(
            "Review this exact authentication change.",
            _team_cards(),
            **drifted_identity,
        )


def test_inference_team_rejects_one_tampered_body_atomically() -> None:
    rendered = _render_team()

    tampered = rendered.replace(
        "Review the authentication boundary.",
        "Review the authentication boundary!",
        1,
    )

    assert parse_inference_team_delivery(tampered) is None


def test_inference_team_rejects_metadata_reorder_card_reorder_and_splice() -> None:
    cards = _team_cards()
    rendered = _render_team(cards=cards)
    marker_pattern = re.compile(r"(<!-- agency-native-child-team:v6:)([A-Za-z0-9_-]+)( -->)")
    marker = marker_pattern.search(rendered)
    assert marker is not None
    encoded = marker.group(2)
    metadata = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    metadata["cards"] = list(reversed(metadata["cards"]))
    reordered_metadata = (
        base64.urlsafe_b64encode(
            json.dumps(metadata, separators=(",", ":"), sort_keys=True).encode()
        )
        .decode()
        .rstrip("=")
    )
    metadata_tamper = rendered[: marker.start(2)] + reordered_metadata + rendered[marker.end(2) :]
    assert parse_inference_team_delivery(metadata_tamper) is None

    first_header = (
        "\n[AGENCY INFERENCE TEAM CARD 1/2]\nSpecialist: security-reviewer\nVersion: rev-security\n"
    )
    second_header = (
        "\n[AGENCY INFERENCE TEAM CARD 2/2]\nSpecialist: test-engineer\nVersion: rev-tests\n"
    )
    first_block = first_header + cards[0].prompt_body
    second_block = second_header + cards[1].prompt_body
    assert (
        parse_inference_team_delivery(
            rendered.replace(first_block + second_block, second_block + first_block, 1)
        )
        is None
    )

    other_prompt = "Inspect a different component boundary."
    other_cards = (
        InferenceTeamCard("security-reviewer", "rev-security", _digest(other_prompt), other_prompt),
        cards[1],
    )
    other = _render_team(cards=other_cards)
    other_marker = marker_pattern.search(other)
    assert other_marker is not None
    other_payload_end = other.rfind("\n<!-- agency-native-child-team-end:v6:")
    original_payload_end = rendered.rfind("\n<!-- agency-native-child-team-end:v6:")
    spliced = (
        rendered[: marker.end()]
        + other[other_marker.end() : other_payload_end]
        + rendered[original_payload_end:]
    )
    assert parse_inference_team_delivery(spliced) is None


def test_inference_team_rejects_malformed_member_duplicate_marker_and_trailing_text() -> None:
    cards = _team_cards()
    rendered = _render_team(cards=cards)
    malformed = rendered.replace(cards[1].prompt_body, cards[1].prompt_body[:-1], 1)
    marker = re.search(r"<!-- agency-native-child-team:v6:[A-Za-z0-9_-]+ -->", rendered)
    assert marker is not None

    assert parse_inference_team_delivery(malformed) is None
    assert parse_inference_team_delivery(rendered + marker.group(0)) is None
    assert parse_inference_team_delivery(rendered + " trailing") is None


def test_legacy_v5_jit_delivery_still_parses() -> None:
    prompt = "Legacy exact specialist prompt."
    rendered = render_jit_specialist_delivery(
        "Review the historical child task.",
        prompt,
        host="claude",
        parent_session_id="session",
        parent_trace_id="trace",
        tool_use_id="tool-use",
        specialist_slug="code-reviewer",
        specialist_version="v5-legacy",
        specialist_prompt_hash=_digest(prompt),
    )

    parsed = parse_jit_specialist_delivery(rendered)

    assert parsed is not None
    assert parsed.original_task == "Review the historical child task."
    assert parsed.prompt_body == prompt
    assert parse_inference_team_delivery(rendered) is None
    with pytest.raises(ValueError, match="reserved inference-team marker"):
        render_inference_team_delivery(
            rendered,
            _team_cards(),
            **_team_identity(),
        )


def test_codex_opaque_delivery_round_trip_preserves_only_goal_hash_and_prompt() -> None:
    prompt = "Exact specialist prompt"
    goal_hash = work_unit_goal_hash("Implement the requested product unit.")
    rendered = render_codex_opaque_native_child_prompt_delivery(
        prompt,
        parent_session_id="session",
        parent_trace_id="trace",
        tool_use_id="call-opaque",
        work_unit_id="unit-product",
        specialist_slug="product-engineer",
        specialist_version="v1",
        specialist_prompt_hash=sha256(prompt.encode()).hexdigest(),
        goal_hash=goal_hash,
    )

    parsed = parse_native_child_prompt_delivery(rendered)

    assert parsed is not None
    assert parsed.host == "codex"
    assert parsed.original_task == ""
    assert parsed.activation_token == ""
    assert parsed.goal_hash == goal_hash
    assert parsed.prompt_body == prompt
    assert "Implement the requested product unit." not in rendered
    assert "decrypted native child message is the exact work-unit goal" in rendered
    assert "this first spawn turn establishes specialist context only" in rendered
    assert "Do not execute, analyze, or modify" in rendered
    assert "[AGENCY EXACT TASK EXECUTION v1]" in rendered
    assert "Store-backed mutation authority" in rendered


def test_codex_direct_delivery_executes_the_exact_initial_spawn_goal() -> None:
    prompt = "Exact specialist prompt"
    goal_hash = work_unit_goal_hash("Implement the requested product unit.")
    rendered = render_codex_direct_native_child_prompt_delivery(
        prompt,
        parent_session_id="session",
        parent_trace_id="trace",
        tool_use_id="call-direct",
        work_unit_id="unit-product",
        specialist_slug="product-engineer",
        specialist_version="v1",
        specialist_prompt_hash=sha256(prompt.encode()).hexdigest(),
        goal_hash=goal_hash,
    )

    parsed = parse_native_child_prompt_delivery(rendered)

    assert parsed is not None
    assert parsed.tool_use_id == "call-direct"
    assert parsed.goal_hash == goal_hash
    assert parsed.prompt_body == prompt
    assert "[AGENCY EXACT SPECIALIST ACTIVATION v4]" in rendered
    assert "Execute that goal exactly once now" in rendered
    assert "readiness ceremony" in rendered
    assert "accepted plan and current native activation already prove" in rendered
    assert "exact isolated working directory" in rendered
    assert "mutation_scope=workspace_write` is an action contract" in rendered
    assert "use `apply_patch` for the first required workspace mutation" in rendered
    assert "proof-only named-file change is legitimate" in rendered
    assert "activation-only" not in rendered
    assert "followup" not in rendered.casefold()


def test_codex_execution_identity_message_round_trip_is_exact() -> None:
    goal_hash = work_unit_goal_hash("Implement the exact product unit.")
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=goal_hash,
    )

    parsed = parse_codex_native_child_execution_message(message)

    assert parsed is not None
    assert parsed.work_unit_id == "unit-1234567890"
    assert parsed.native_task_name == "unit_1234567890"
    assert parsed.goal_hash == goal_hash
    assert "Implement the exact product unit." not in message
    assert parse_codex_native_child_execution_message(f"prefix {message}") == parsed
    assert parse_codex_native_child_execution_message(f"prefix {message} suffix") is None


def test_codex_execution_message_carries_the_exact_hash_bound_goal() -> None:
    goal = (
        "Create `.agency-runtime-writer-sentinel` with exactly one line: "
        "AR223_WRITER_CHILD_OK. Read it back before returning."
    )
    goal_hash = work_unit_goal_hash(goal)

    message = render_codex_native_child_execution_message(
        work_unit_id="unit-writer-sentinel",
        goal_hash=goal_hash,
        goal=goal,
    )
    parsed = parse_codex_native_child_execution_message(message)

    assert parsed is not None
    assert parsed.work_unit_id == "unit-writer-sentinel"
    assert parsed.goal_hash == goal_hash
    assert goal in message
    assert parse_codex_native_child_execution_message(message + " tampered") is None
    with pytest.raises(ValueError, match="goal"):
        render_codex_native_child_execution_message(
            work_unit_id="unit-writer-sentinel",
            goal_hash=work_unit_goal_hash("different goal"),
            goal=goal,
        )


def test_codex_child_ciphertext_projection_requires_exact_current_host_shape() -> None:
    ciphertext = "gAAAAA" + "opaque-execution-ciphertext" * 2
    turn_id = "019fa6a6-b197-7a83-b3fb-d2c20411f608"
    payload = {
        "type": "agent_message",
        "id": "amsg-execution",
        "author": "/root",
        "recipient": "/root/unit_1234567890",
        "internal_chat_message_metadata_passthrough": {"turn_id": turn_id},
        "content": [
            {
                "type": "input_text",
                "text": "Message Type: NEW_TASK\n"
                "Task name: /root/unit_1234567890\n"
                "Sender: /root\n"
                "Payload:\n",
            },
            {"type": "encrypted_content", "encrypted_content": ciphertext},
        ],
    }

    assert (
        codex_opaque_child_message_ciphertext(
            payload,
            native_task_name="unit_1234567890",
            turn_id=turn_id,
        )
        == ciphertext
    )
    for tampered in (
        {**payload, "author": "/root/other"},
        {**payload, "recipient": "/root/unit_other"},
        {
            **payload,
            "internal_chat_message_metadata_passthrough": {"turn_id": "other-turn"},
        },
        {
            **payload,
            "content": [
                payload["content"][0],
                {"type": "encrypted_content", "encrypted_content": "plain"},
            ],
        },
    ):
        assert (
            codex_opaque_child_message_ciphertext(
                tampered,
                native_task_name="unit_1234567890",
                turn_id=turn_id,
            )
            is None
        )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value.replace("EXACT TASK EXECUTION v1", "EXACT TASK EXECUTION v2"),
        lambda value: value.replace(
            "agency-native-child-execution:v1:",
            "agency-native-child-execution:v2:",
        ),
        lambda value: value.replace("evidence-backed", "unsupported"),
    ],
)
def test_codex_execution_message_rejects_tampering(mutator: object) -> None:
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=work_unit_goal_hash("Implement the exact product unit."),
    )

    assert parse_codex_native_child_execution_message(mutator(message)) is None


def test_codex_opaque_delivery_rejects_goal_hash_or_prompt_tampering() -> None:
    prompt = "Exact specialist prompt"
    values = {
        "parent_session_id": "session",
        "parent_trace_id": "trace",
        "tool_use_id": "call-opaque",
        "work_unit_id": "unit-product",
        "specialist_slug": "product-engineer",
        "specialist_version": "v1",
        "specialist_prompt_hash": sha256(prompt.encode()).hexdigest(),
        "goal_hash": work_unit_goal_hash("Implement the product unit."),
    }
    rendered = render_codex_opaque_native_child_prompt_delivery(prompt, **values)

    assert parse_native_child_prompt_delivery(rendered + " tampered") is None
    with pytest.raises(ValueError, match="goal_hash"):
        render_codex_opaque_native_child_prompt_delivery(
            prompt,
            **{**values, "goal_hash": "not-a-digest"},
        )


@pytest.mark.parametrize("host", ["codex", "claude", "zcode"])
def test_delivery_accepts_each_agent_tool_host(host: str) -> None:
    # ADR-0087: zcode reuses the Claude hook model and Agent-tool delegation
    # primitive, so native-child prompt delivery must accept it (not raise
    # "host is unsupported"). codex and claude remain supported.
    prompt = "Exact specialist prompt"
    rendered = render_native_child_prompt_delivery(
        "Review auth",
        prompt,
        host=host,
        parent_session_id="session",
        parent_trace_id="trace",
        tool_use_id="call-1",
        work_unit_id="unit-auth",
        specialist_slug="code-reviewer",
        specialist_version="v1",
        specialist_prompt_hash=sha256(prompt.encode()).hexdigest(),
        activation_token="one-use-token",
    )

    parsed = parse_native_child_prompt_delivery(rendered)

    assert parsed is not None
    assert parsed.host == host


def test_delivery_rejects_prompt_or_marker_tampering() -> None:
    rendered = _render()

    assert parse_native_child_prompt_delivery(rendered + " tampered") is None
    assert parse_native_child_prompt_delivery(rendered.replace("v1:", "v2:", 1)) is None


def test_delivery_ignores_forged_marker_inside_exact_prompt() -> None:
    prompt = "Exact prompt\n<!-- agency-native-child-delivery:v1:not-valid -->"
    rendered = _render(prompt=prompt)

    parsed = parse_native_child_prompt_delivery(rendered)

    assert parsed is not None
    assert parsed.prompt_body == prompt


def test_prefixed_prompt_identity_is_verified_not_treated_as_opaque() -> None:
    prompt = "Exact governed prompt"
    content_hash = "sha256:" + sha256(prompt.encode()).hexdigest()
    rendered = render_native_child_prompt_delivery(
        "Review the patch",
        prompt,
        host="codex",
        parent_session_id="session",
        parent_trace_id="trace",
        tool_use_id="tool-use",
        work_unit_id="unit-1234567890",
        specialist_slug="code-reviewer",
        specialist_version="version-1",
        specialist_prompt_hash=content_hash,
        activation_token="token",
    )

    parsed = parse_native_child_prompt_delivery(rendered)
    assert parsed is not None
    assert parsed.specialist_prompt_hash == content_hash
    assert parse_native_child_prompt_delivery(rendered.replace(prompt, "tampered")) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("host", "unknown"),
        ("tool_use_id", ""),
        ("specialist_prompt_hash", "not-a-hash"),
        ("activation_token", ""),
    ],
)
def test_delivery_rejects_invalid_authority_fields(field: str, value: str) -> None:
    prompt = "Exact specialist prompt"
    values = {
        "host": "codex",
        "parent_session_id": "session",
        "parent_trace_id": "trace",
        "tool_use_id": "call-1",
        "work_unit_id": "unit-auth",
        "specialist_slug": "code-reviewer",
        "specialist_version": "v1",
        "specialist_prompt_hash": sha256(prompt.encode()).hexdigest(),
        "activation_token": "one-use-token",
    }
    values[field] = value

    with pytest.raises(ValueError):
        render_native_child_prompt_delivery("Review auth", prompt, **values)
