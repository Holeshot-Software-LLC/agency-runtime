"""Pure contract tests for one-use native-child specialist activation."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256

import pytest

from agency_runtime.core import native_child_activation as contract_module
from agency_runtime.core.native_child_activation import (
    MAX_NATIVE_CHILD_ACTIVATION_BYTES,
    MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS,
    MAX_NATIVE_CHILD_EVIDENCE_REQUIREMENTS,
    MAX_NATIVE_CHILD_PATH_PREFIXES,
    MAX_NATIVE_CHILD_TIMESTAMP,
    NATIVE_CHILD_ACTIVATION_LEGACY_VERSION,
    NativeChildActivationGrant,
    build_native_child_activation_grant,
    build_native_child_activation_receipt,
    build_native_child_evidence_contract,
    build_native_child_mutation_scope,
    build_native_child_run_identity,
    build_native_child_specialist_identity,
    build_native_child_worker_binding,
    canonical_native_child_host,
    deserialize_native_child_activation_grant,
    deserialize_native_child_activation_receipt,
    serialize_native_child_activation_grant,
    serialize_native_child_activation_receipt,
    validate_native_child_activation_grant,
    validate_native_child_activation_receipt,
    validate_native_child_evidence_contract,
    validate_native_child_mutation_scope,
    validate_native_child_run_identity,
    validate_native_child_specialist_identity,
    validate_native_child_work_unit_id,
    validate_native_child_worker_binding,
)

_HASH = sha256(b"security-reviewer prompt v1").hexdigest()
_OTHER_HASH = sha256(b"senior-developer prompt v2").hexdigest()


def _specialist(
    *,
    slug: str = "security-reviewer",
    version: str = "source-revision-1",
    content_hash: str = _HASH,
):
    return build_native_child_specialist_identity(
        slug=slug,
        version=version,
        content_hash=content_hash,
    )


def _scope(*, mode: str = "workspace_write", paths: object = ("agency_runtime/core",)):
    return build_native_child_mutation_scope(mode=mode, path_prefixes=paths)


def _evidence(
    *,
    contract_id: str = "code-change-v1",
    requirements: object = ("diff", "tests"),
):
    return build_native_child_evidence_contract(
        contract_id=contract_id,
        requirements=requirements,
    )


def _grant_arguments() -> dict[str, object]:
    return {
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
        "work_unit_id": "unit-0123456789",
        "host": "codex",
        "specialist": _specialist(),
        "mutation_scope": _scope(),
        "evidence_contract": _evidence(),
        "issued_at": 1_000,
        "expires_at": 1_600,
    }


def _grant(**overrides: object) -> NativeChildActivationGrant:
    arguments = _grant_arguments()
    arguments.update(overrides)
    return build_native_child_activation_grant(**arguments)


def _run():
    return build_native_child_run_identity(
        worker_kind="native-subagent",
        worker_id="worker-7",
        native_run_id="codex:run-42",
    )


def test_grant_is_immutable_canonical_content_free_and_deterministic() -> None:
    grant = _grant()
    repeated = _grant()
    payload = serialize_native_child_activation_grant(grant)

    assert grant == repeated
    assert grant.grant_id == repeated.grant_id
    assert grant.grant_id.startswith("ncg-")
    assert grant.use_limit == 1
    assert grant.consumption_key == grant.grant_id
    assert payload == json.dumps(
        grant.as_dict(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    assert deserialize_native_child_activation_grant(payload) == grant
    assert validate_native_child_activation_grant(grant.as_dict()) == grant
    assert "security-reviewer prompt v1" not in payload
    assert "activation_token" not in payload
    assert "user_message" not in payload
    assert len(payload.encode()) <= MAX_NATIVE_CHILD_ACTIVATION_BYTES
    with pytest.raises(FrozenInstanceError):
        grant.host = "claude"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("parent_session_id", "other-session"),
        ("parent_trace_id", "other-trace"),
        ("work_unit_id", "unit-abcdef1234"),
        ("host", "claude"),
        (
            "specialist",
            build_native_child_specialist_identity(
                slug="senior-developer",
                version="source-revision-1",
                content_hash=_OTHER_HASH,
            ),
        ),
        (
            "mutation_scope",
            build_native_child_mutation_scope(
                mode="workspace_write",
                path_prefixes=("tests",),
            ),
        ),
        (
            "evidence_contract",
            build_native_child_evidence_contract(
                contract_id="review-v1",
                requirements=("review",),
            ),
        ),
        (
            "worker_binding",
            build_native_child_worker_binding(
                mode="prebound",
                worker_kind="native-subagent",
                worker_id="worker-7",
            ),
        ),
        ("issued_at", 1_001),
        ("expires_at", 1_601),
    ],
)
def test_grant_id_binds_every_authority_and_correlation_field(
    field: str,
    replacement: object,
) -> None:
    assert _grant().grant_id != _grant(**{field: replacement}).grant_id


@pytest.mark.parametrize("host", [" CLAUDE ", "CODEX", "hermes", "openclaw"])
def test_supported_hosts_are_canonicalized(host: str) -> None:
    assert canonical_native_child_host(host) == host.strip().casefold()


@pytest.mark.parametrize("host", ["", "litellm", "unknown", "other", 42])
def test_unsupported_or_non_text_hosts_are_rejected(host: object) -> None:
    with pytest.raises(ValueError):
        canonical_native_child_host(host)


@pytest.mark.parametrize(
    "work_unit_id",
    [
        "unit-0123456789",
        "specialist:security-reviewer",
        "native/task-1",
        "review_unit@2",
    ],
)
def test_stable_content_free_work_unit_forms_are_supported(work_unit_id: str) -> None:
    assert validate_native_child_work_unit_id(work_unit_id) == work_unit_id


@pytest.mark.parametrize(
    "work_unit_id",
    ["", "contains spaces", "../escape", "-leading", "x" * 161, None],
)
def test_unstable_work_unit_forms_are_rejected(work_unit_id: object) -> None:
    with pytest.raises(ValueError):
        validate_native_child_work_unit_id(work_unit_id)


@pytest.mark.parametrize("slug", ["agents-orchestrator", "chief-of-staff"])
def test_resident_managers_cannot_be_selected_as_child_specialists(slug: str) -> None:
    with pytest.raises(ValueError, match="resident managers"):
        _specialist(slug=slug)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("slug", "bad slug"),
        ("version", ""),
        ("version", 7),
        ("version", "free form prompt text"),
        ("content_hash", "not-a-hash"),
        ("content_hash", True),
    ],
)
def test_specialist_identity_requires_exact_bounded_immutable_fields(
    field: str,
    value: object,
) -> None:
    values: dict[str, object] = {
        "slug": "security-reviewer",
        "version": "source-revision-1",
        "content_hash": _HASH,
    }
    values[field] = value
    with pytest.raises(ValueError):
        build_native_child_specialist_identity(**values)


def test_specialist_identity_rejects_lists_and_extra_fields() -> None:
    with pytest.raises(ValueError, match="must be an object"):
        validate_native_child_specialist_identity([_specialist().as_dict()])
    invalid = {**_specialist().as_dict(), "prompt": "do not persist me"}
    with pytest.raises(ValueError, match="invalid fields"):
        validate_native_child_specialist_identity(invalid)


def test_mutation_scope_is_portable_sorted_and_exact() -> None:
    write_scope = build_native_child_mutation_scope(
        mode=" WORKSPACE_WRITE ",
        path_prefixes=("tests", "agency_runtime/core", "."),
    )
    read_scope = build_native_child_mutation_scope(mode="read_only")

    assert write_scope.path_prefixes == (".", "agency_runtime/core", "tests")
    assert validate_native_child_mutation_scope(write_scope.as_dict()) == write_scope
    assert read_scope.as_dict() == {"mode": "read_only", "path_prefixes": []}


@pytest.mark.parametrize(
    ("mode", "paths"),
    [
        ("read_only", ("tests",)),
        ("workspace_write", ()),
        ("external_write", ("tests",)),
        ("workspace_write", ("/absolute",)),
        ("workspace_write", (r"windows\path",)),
        ("workspace_write", ("C:/drive",)),
        ("workspace_write", ("a//b",)),
        ("workspace_write", ("a/../b",)),
        ("workspace_write", ("tests", "tests")),
        ("workspace_write", tuple(f"path-{index}" for index in range(17))),
        ("workspace_write", "tests"),
    ],
)
def test_mutation_scope_rejects_ambiguous_or_overbroad_shapes(
    mode: str,
    paths: object,
) -> None:
    with pytest.raises(ValueError):
        build_native_child_mutation_scope(mode=mode, path_prefixes=paths)


def test_mutation_scope_rejects_extra_fields() -> None:
    with pytest.raises(ValueError, match="invalid fields"):
        validate_native_child_mutation_scope(
            {
                "mode": "read_only",
                "path_prefixes": [],
                "shell_command": "rm -rf",
            }
        )


def test_evidence_contract_is_sorted_versioned_and_content_free() -> None:
    contract = build_native_child_evidence_contract(
        contract_id=" Code-Change-V1 ",
        requirements=("tests", "diff", "security.review"),
    )

    assert contract.contract_id == "code-change-v1"
    assert contract.requirements == ("diff", "security.review", "tests")
    assert validate_native_child_evidence_contract(contract.as_dict()) == contract


@pytest.mark.parametrize(
    ("contract_id", "requirements"),
    [
        ("", ()),
        ("bad contract", ()),
        ("code-v1", ("bad requirement",)),
        ("code-v1", ("tests", "tests")),
        (
            "code-v1",
            tuple(
                f"requirement-{index}"
                for index in range(MAX_NATIVE_CHILD_EVIDENCE_REQUIREMENTS + 1)
            ),
        ),
        ("code-v1", "tests"),
    ],
)
def test_evidence_contract_rejects_unbounded_or_free_form_values(
    contract_id: str,
    requirements: object,
) -> None:
    with pytest.raises(ValueError):
        build_native_child_evidence_contract(
            contract_id=contract_id,
            requirements=requirements,
        )


def test_grant_rejects_invalid_lifetime_and_exact_shape() -> None:
    with pytest.raises(ValueError, match="greater"):
        _grant(expires_at=1_000)
    with pytest.raises(ValueError, match="lifetime"):
        _grant(expires_at=1_000 + MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS + 1)
    with pytest.raises(ValueError, match="issued_at"):
        _grant(issued_at=True)
    with pytest.raises(ValueError, match="expires_at"):
        _grant(expires_at=MAX_NATIVE_CHILD_TIMESTAMP + 1)

    invalid = {**_grant().as_dict(), "prompt": "hidden specialist body"}
    with pytest.raises(ValueError, match="invalid fields"):
        validate_native_child_activation_grant(invalid)
    invalid = {**_grant().as_dict(), "use_limit": 2}
    with pytest.raises(ValueError, match="one-use"):
        validate_native_child_activation_grant(invalid)


def test_grant_validation_detects_any_capsule_or_id_tampering() -> None:
    grant = _grant()
    tampered = grant.as_dict()
    tampered["work_unit_id"] = "unit-abcdef1234"
    with pytest.raises(ValueError, match="grant_id"):
        validate_native_child_activation_grant(tampered)

    malformed = grant.as_dict()
    malformed["grant_id"] = "ncr-" + "0" * 32
    with pytest.raises(ValueError, match="grant_id"):
        validate_native_child_activation_grant(malformed)


def test_grant_deserializer_rejects_noncanonical_duplicate_and_oversized_json() -> None:
    payload = serialize_native_child_activation_grant(_grant())
    with pytest.raises(ValueError, match="not canonical"):
        deserialize_native_child_activation_grant(payload + " ")
    duplicate = payload.replace(
        '"expires_at":1600',
        '"expires_at":1600,"expires_at":1600',
    )
    with pytest.raises(ValueError, match="duplicate"):
        deserialize_native_child_activation_grant(duplicate)
    with pytest.raises(ValueError, match="byte limit"):
        deserialize_native_child_activation_grant("x" * (MAX_NATIVE_CHILD_ACTIVATION_BYTES + 1))
    with pytest.raises(ValueError, match="contain an object"):
        deserialize_native_child_activation_grant("[]")
    with pytest.raises(ValueError, match="must be a string"):
        deserialize_native_child_activation_grant({})


def test_run_identity_is_host_neutral_exact_and_content_free() -> None:
    child_run = _run()

    assert child_run.as_dict() == {
        "worker_kind": "native-subagent",
        "worker_id": "worker-7",
        "native_run_id": "codex:run-42",
    }
    assert validate_native_child_run_identity(child_run.as_dict()) == child_run
    with pytest.raises(ValueError, match="invalid fields"):
        validate_native_child_run_identity({**child_run.as_dict(), "host": "codex"})


def test_worker_binding_is_explicit_exact_and_authenticated_by_grant_id() -> None:
    late = build_native_child_worker_binding(
        mode="late_bound",
        worker_kind="generic-worker",
    )
    prebound = build_native_child_worker_binding(
        mode="prebound",
        worker_kind="generic-worker",
        worker_id="worker-7",
    )

    assert late.as_dict() == {
        "mode": "late_bound",
        "worker_kind": "generic-worker",
        "worker_id": "",
    }
    assert validate_native_child_worker_binding(prebound.as_dict()) == prebound
    assert _grant(worker_binding=late).grant_id != _grant(worker_binding=prebound).grant_id
    with pytest.raises(ValueError, match="cannot name"):
        build_native_child_worker_binding(
            mode="late_bound",
            worker_kind="generic-worker",
            worker_id="worker-7",
        )
    with pytest.raises(ValueError, match="worker_id"):
        build_native_child_worker_binding(
            mode="prebound",
            worker_kind="generic-worker",
        )


@pytest.mark.parametrize(
    ("mode", "worker_kind", "worker_id"),
    [
        (7, "generic-worker", ""),
        ("unknown", "generic-worker", ""),
        ("late_bound", "bad kind", ""),
        ("late_bound", "generic-worker", 7),
        ("prebound", "generic-worker", "../worker"),
    ],
)
def test_worker_binding_rejects_ambiguous_or_unsafe_shapes(
    mode: object,
    worker_kind: object,
    worker_id: object,
) -> None:
    with pytest.raises(ValueError):
        build_native_child_worker_binding(
            mode=mode,
            worker_kind=worker_kind,
            worker_id=worker_id,
        )
    with pytest.raises(ValueError, match="invalid fields"):
        validate_native_child_worker_binding(
            {
                "mode": "late_bound",
                "worker_kind": "generic-worker",
                "worker_id": "",
                "native_run_id": "run-1",
            }
        )


def test_version_specific_grant_shapes_fail_closed() -> None:
    late = build_native_child_worker_binding(
        mode="late_bound",
        worker_kind="generic-worker",
    )
    with pytest.raises(ValueError, match="v1"):
        _grant(
            version=NATIVE_CHILD_ACTIVATION_LEGACY_VERSION,
            worker_binding=late,
        )
    with pytest.raises(ValueError, match="must be an object"):
        validate_native_child_activation_grant([])
    with pytest.raises(RuntimeError, match="no worker binding"):
        replace(_grant(), worker_binding=None).as_dict()


def test_legacy_v1_grant_and_receipt_remain_canonical_and_readable() -> None:
    grant = _grant(
        version=NATIVE_CHILD_ACTIVATION_LEGACY_VERSION,
        worker_binding=None,
    )
    grant_payload = serialize_native_child_activation_grant(grant)
    receipt = build_native_child_activation_receipt(
        grant,
        child_run=_run(),
        consumed_at=1_001,
    )
    receipt_payload = serialize_native_child_activation_receipt(receipt, grant=grant)

    assert grant.version == receipt.version == NATIVE_CHILD_ACTIVATION_LEGACY_VERSION
    assert grant.worker_binding is None
    assert "worker_binding" not in grant_payload
    assert deserialize_native_child_activation_grant(grant_payload) == grant
    assert deserialize_native_child_activation_receipt(receipt_payload, grant=grant) == receipt
    mismatched_receipt = {
        **build_native_child_activation_receipt(
            _grant(),
            child_run=_run(),
            consumed_at=1_001,
        ).as_dict(),
        "version": NATIVE_CHILD_ACTIVATION_LEGACY_VERSION,
    }
    with pytest.raises(ValueError, match="does not match its grant"):
        validate_native_child_activation_receipt(mismatched_receipt, grant=_grant())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("worker_kind", ""),
        ("worker_kind", "contains spaces"),
        ("worker_id", "../worker"),
        ("native_run_id", "x" * 257),
        ("native_run_id", None),
    ],
)
def test_run_identity_rejects_missing_or_unsafe_identifiers(
    field: str,
    value: object,
) -> None:
    values: dict[str, object] = {
        "worker_kind": "native-subagent",
        "worker_id": "worker-7",
        "native_run_id": "codex:run-42",
    }
    values[field] = value
    with pytest.raises(ValueError):
        build_native_child_run_identity(**values)


def test_receipt_is_canonical_append_only_projection_bound_to_exact_grant() -> None:
    grant = _grant()
    receipt = build_native_child_activation_receipt(
        grant,
        child_run=_run(),
        consumed_at=1_001,
    )
    payload = serialize_native_child_activation_receipt(receipt, grant=grant)

    assert receipt.status == "consumed"
    assert receipt.grant_id == grant.grant_id
    assert receipt.consumption_key == grant.consumption_key
    assert receipt.receipt_id.startswith("ncr-")
    assert receipt.specialist == grant.specialist
    assert validate_native_child_activation_receipt(receipt.as_dict(), grant=grant) == receipt
    assert deserialize_native_child_activation_receipt(payload, grant=grant) == receipt
    assert "prompt" not in payload
    assert "token" not in payload
    with pytest.raises(FrozenInstanceError):
        receipt.consumed_at = 1_002  # type: ignore[misc]


@pytest.mark.parametrize("consumed_at", [999, 1_601, True, -1])
def test_receipt_consumption_time_must_be_inside_grant_lifetime(
    consumed_at: object,
) -> None:
    with pytest.raises(ValueError):
        build_native_child_activation_receipt(
            _grant(),
            child_run=_run(),
            consumed_at=consumed_at,
        )


def test_receipt_rejects_different_grant_and_projection_tampering() -> None:
    grant = _grant()
    receipt = build_native_child_activation_receipt(
        grant,
        child_run=_run(),
        consumed_at=1_001,
    )

    with pytest.raises(ValueError, match="does not match"):
        validate_native_child_activation_receipt(
            receipt,
            grant=_grant(parent_trace_id="different-trace"),
        )

    invalid_status = {**receipt.as_dict(), "status": "completed"}
    with pytest.raises(ValueError, match="status"):
        validate_native_child_activation_receipt(invalid_status, grant=grant)

    invalid_run = receipt.as_dict()
    invalid_run["child_run"] = {
        **receipt.child_run.as_dict(),
        "native_run_id": "codex:run-99",
    }
    with pytest.raises(ValueError, match="receipt_id"):
        validate_native_child_activation_receipt(invalid_run, grant=grant)

    invalid_specialist = receipt.as_dict()
    invalid_specialist["specialist"] = _specialist(
        slug="senior-developer",
        content_hash=_OTHER_HASH,
    ).as_dict()
    with pytest.raises(ValueError, match="specialist does not match"):
        validate_native_child_activation_receipt(invalid_specialist, grant=grant)


def test_receipt_deserializer_rejects_noncanonical_and_extra_fields() -> None:
    grant = _grant()
    receipt = build_native_child_activation_receipt(
        grant,
        child_run=_run(),
        consumed_at=1_001,
    )
    payload = serialize_native_child_activation_receipt(receipt, grant=grant)

    with pytest.raises(ValueError, match="not canonical"):
        deserialize_native_child_activation_receipt(payload + "\n", grant=grant)
    invalid = {**receipt.as_dict(), "output": "arbitrary child response"}
    with pytest.raises(ValueError, match="invalid fields"):
        validate_native_child_activation_receipt(invalid, grant=grant)


def test_contract_limits_are_deliberately_small_and_positive() -> None:
    assert MAX_NATIVE_CHILD_PATH_PREFIXES == 16
    assert MAX_NATIVE_CHILD_EVIDENCE_REQUIREMENTS == 16
    assert MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS == 3_600


def test_low_level_type_unicode_version_and_json_failures_are_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="printable"):
        canonical_native_child_host("co\ndex")
    with pytest.raises(ValueError, match="valid UTF-8"):
        canonical_native_child_host("co\ud800dex")
    with pytest.raises(ValueError, match="mode must be a string"):
        build_native_child_mutation_scope(mode=1)

    invalid_grant_version = {**_grant().as_dict(), "version": True}
    with pytest.raises(ValueError, match="version"):
        validate_native_child_activation_grant(invalid_grant_version)

    grant = _grant()
    receipt = build_native_child_activation_receipt(
        grant,
        child_run=_run(),
        consumed_at=1_001,
    )
    invalid_receipt_version = {**receipt.as_dict(), "version": 99}
    with pytest.raises(ValueError, match="version"):
        validate_native_child_activation_receipt(invalid_receipt_version, grant=grant)
    invalid_receipt_specialist = {**receipt.as_dict(), "specialist": []}
    with pytest.raises(ValueError, match="specialist is invalid"):
        validate_native_child_activation_receipt(invalid_receipt_specialist, grant=grant)

    with pytest.raises(ValueError, match="non-finite"):
        deserialize_native_child_activation_grant('{"issued_at":NaN}')
    with pytest.raises(ValueError, match="valid UTF-8"):
        deserialize_native_child_activation_grant("\ud800")
    with pytest.raises(ValueError, match="JSON is invalid"):
        deserialize_native_child_activation_grant("{")

    monkeypatch.setattr(contract_module, "MAX_NATIVE_CHILD_ACTIVATION_BYTES", 1)
    with pytest.raises(RuntimeError, match="serialization budget"):
        serialize_native_child_activation_grant(grant)
