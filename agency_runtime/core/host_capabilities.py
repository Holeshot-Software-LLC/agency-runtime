"""Canonical execution-host and tool-capability contracts.

An inference router is not an execution host.  This module is the single
operational vocabulary used to translate reviewed roster tool labels and the
capabilities proven by a native Agency adapter event.  Unknown labels remain
unknown: they are evidence for a fail-closed rejection, never an implicit new
capability.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Final

from agency_runtime.core.correlation import validate_correlation_id

EXECUTION_HOSTS: Final[tuple[str, ...]] = ("codex", "claude", "openclaw", "hermes")
INFERENCE_SURFACES: Final[tuple[str, ...]] = ("litellm",)
SUPPORTED_PLATFORMS: Final[tuple[str, ...]] = ("windows", "linux")
MAX_TOOL_CAPABILITIES: Final[int] = 64
MAX_CAPABILITY_EVIDENCE_ITEMS: Final[int] = 8
MAX_CAPABILITY_TOKEN_CHARS: Final[int] = 64
CAPABILITY_CONTRACT_VERSION: Final[str] = "1"
NATIVE_ADAPTER_RECEIPT_TTL_SECONDS: Final[int] = 60

_NATIVE_ADAPTER_RECEIPT_TTL_NS: Final[int] = NATIVE_ADAPTER_RECEIPT_TTL_SECONDS * 1_000_000_000
_CAPABILITY_ATTESTATION_KEY: Final[bytes] = secrets.token_bytes(32)

_TOKEN = re.compile(r"[a-z0-9][a-z0-9._+-]{0,63}\Z")
_RECEIPT_STATUSES = frozenset(
    {
        "native-contract-verified",
        "native-installation-verified",
        "native-evidence-unproven",
        "inference-only",
        "explicit-tools-without-execution-host",
        "unknown",
    }
)

_BASE_CANONICAL_TOOL_CAPABILITIES: Final[frozenset[str]] = frozenset(
    {
        "api-access",
        "browser-automation",
        "browser-interaction",
        "build-toolchain",
        "cloud-infrastructure",
        "code-execution",
        "data-analysis",
        "database-access",
        "device-testing",
        "document-access",
        "infrastructure-as-code",
        "media-processing",
        "model-runtime",
        "monitoring-observability",
        "native-delegation",
        "network-access",
        "package-management",
        "performance-profiling",
        "repository-read",
        "repository-write",
        "screenshot-capture",
        "security-analysis",
        "shell-execution",
        "source-control",
        "spreadsheet-access",
        "test-execution",
        "web-research",
    }
)

# Exact labels in the reviewed bundled roster.  Keeping this inventory local
# makes unknown future labels fail closed until the delta audit deliberately
# classifies them.  Labels covered by the alias groups below collapse to a
# shared operational capability; every other reviewed label remains its own
# exact capability and therefore cannot be accidentally satisfied by a broad
# host baseline.
_REVIEWED_TOOL_LABELS: Final[frozenset[str]] = frozenset(
    """
accessibility-tester accessibility-testing account-research accounting-data-reader aggregate-recruiting-analytics aggregate-workforce-data-reader
analytics-reader analytics-store api-client api-schema-validator apple-build-toolchain apple-platform-documentation
application-document-reader architecture-document-reader architecture-evidence artifact-reader artifact-validator asset-pipeline
assistive-technology-test-host ats-reader audio-evaluation-set audio-middleware audio-profiler audit-log-reader
authorized-cloud-test-environment authorized-crm-reader authorized-customer-data-reader authorized-market-data-reader authorized-product-analytics-reader authorized-test-environment
authorized-test-infrastructure axe backup-verifier benchmark-runner bim-toolchain blender
browser browser-test-runner budget-calculator build-toolchain cache-test-host calculation-tool
call-recording-reader ci-reader ci-runner claim-evidence-reader cloud-billing-data cloud-cli
cloud-or-local-model-runtime communication-context-reader communications-draft community-data-reader configuration-validator conflict-system-reader
contract-reader cost-model coverage-reader cpp-toolchain crm-reader cross-compiler
cross-platform-test-host cryptographic-test-tool csharp-toolchain current-cultural-research current-legal-research current-policy-research
current-regulation-research current-tax-research customer-record-reader dashboard dashboard-builder data-analysis-runtime
data-flow-reader data-runtime data-store database database-client database-reader
dataframe-runtime deal-document-reader delivery-audit-reader demo-environment desktop-test-host device-lab
device-test-host device-test-rig diff-tool document-reader document-runtime documentation-search
documentation-test-runner email-data-source email-platform-reader engineering-calculation-tool evaluation-dataset evaluation-runner
experiment-platform-reader experiment-runner feishu-sandbox ffmpeg file-read file-write
filesystem-editor filesystem-reader filesystem-search filings-reader financial-calculator financial-data-reader
financial-document-reader financial-modeling financial-record-reader fleet-sandbox fraud-case-reader game-engine
gdal-toolchain gdscript-or-dotnet-toolchain geospatial-data-reader geospatial-ml-toolchain gis-automation gis-desktop
gis-sdk gis-validator git git-history-reader godot-editor gpu-profiler
gpu-runtime graphics-debugger hardware-debugger healthcare-policy-reader hotline-lookup hr-policy-reader
identity-data-reader identity-system-reader identity-test-provider incident-data incident-timeline infrastructure-tooling
intake-form-reader jira k6 knowledge-base-reader language-server-runtime learning-content-tool
legal-billing-record-reader licensed-code-reference lighthouse link-validator loan-record-reader local-chain
locale-test-runtime market-data-reader market-research marketing-artifact-reader matching-evaluation media-generation
media-packager metrics-reader ml-runtime mobile-build-toolchain model-converter model-evaluation
model-evaluation-provider monitoring network network-client network-fault-injector network-lab
network-profiler network-simulator network-test-harness official-documentation-search official-employment-research official-ethics-research
official-france-research official-government-research official-immigration-research official-legal-research official-lending-research official-marketing-law-research
official-mcp-documentation official-payer-research official-procurement-research official-real-estate-research official-regulation-research official-school-research
official-solicitation-research official-trade-research operations-data-reader organizational-data-reader orgscript-cli oscal-validator
package-manager patient-record-reader payment-sandbox peer-reviewed-research performance-profiler photogrammetry-toolchain
pipeline-runner planning-data-reader playwright policy-reader portfolio-data-reader process-data-reader
product-analytics-reader program-data-reader property-policy-reader protocol-documentation prototype-runtime python
python-runtime realtime-test-harness recipient-directory-reader rendering-inspector rendering-profiler report-reader
repository repository-reader requirements-reader reservation-record-reader return-policy-reader roblox-studio
runtime-evidence safe-spreadsheet-reader salesforce-cli salesforce-documentation sandbox-environment scene-profiler
screen-reader screenshot-capture search-sandbox secure-data-reader secure-document-reader secure-evidence-reader
secure-health-record-reader security-analyzer security-document-reader security-documentation security-scanner service-client
service-management-data shell solidity-toolchain source-code-editor source-code-reader source-control
spatial-query speech-model-runtime spreadsheet sql statistical-runtime statistical-test-tool
store-console-evidence store-sandbox supply-chain-data-reader support-policy-reader survey-analysis sustainability-data-reader
synthetic-credentials target-build-toolchain target-gpu target-import-validator telemetry-store terraform
test-environment test-results-reader test-runner ticket-reader tracker-reader transaction-document-reader
transaction-record-reader translation-catalog translation-reference unity-editor unity-networking-packages unreal-editor
unreal-insights visionos-build-toolchain wasi-runtime wasm-toolchain web-3d-toolchain web-research
web-toolchain web-xr-toolchain wechat-devtools wechat-sandbox woocommerce-test-host workflow-platform-reader
xr-device-profiler
""".split()  # noqa: SIM905 - compact frozen audited vocabulary is easier to review
)


def _alias_map() -> dict[str, str]:
    groups = {
        "repository-read": {
            "repository-read",
            "repository",
            "repository-reader",
            "source",
            "source-code-reader",
            "file-read",
            "filesystem-reader",
            "filesystem-search",
            "artifact-reader",
            "architecture-document-reader",
            "requirements-reader",
        },
        "repository-write": {
            "repository-write",
            "file-write",
            "filesystem-editor",
            "source-code-editor",
        },
        "shell-execution": {"shell-execution", "shell"},
        "source-control": {"source-control", "git", "git-history-reader"},
        "code-execution": {
            "code-execution",
            "python",
            "python-runtime",
            "prototype-runtime",
        },
        "test-execution": {
            "test-execution",
            "test-runner",
            "benchmark-runner",
            "evaluation-runner",
            "experiment-runner",
            "documentation-test-runner",
        },
        "package-management": {"package-management", "package-manager"},
        "build-toolchain": {"build-toolchain"},
        "web-research": {
            "web-research",
            "documentation-search",
            "official-documentation-search",
            "market-research",
        },
        "browser-interaction": {"browser-interaction", "browser"},
        "browser-automation": {
            "browser-automation",
            "playwright",
            "browser-test-runner",
        },
        "screenshot-capture": {"screenshot-capture"},
        "network-access": {"network-access", "network", "network-client"},
        "api-access": {"api-access", "api-client", "service-client"},
        "database-access": {
            "database-access",
            "database",
            "database-client",
            "database-reader",
            "sql",
        },
        "data-analysis": {
            "data-analysis",
            "data-analysis-runtime",
            "dataframe-runtime",
            "statistical-runtime",
        },
        "spreadsheet-access": {
            "spreadsheet-access",
            "spreadsheet",
            "safe-spreadsheet-reader",
        },
        "document-access": {
            "document-access",
            "document-reader",
            "secure-document-reader",
        },
        "media-processing": {
            "media-processing",
            "media-generation",
            "media-packager",
            "ffmpeg",
        },
        "security-analysis": {
            "security-analysis",
            "security-analyzer",
            "security-scanner",
        },
        "cloud-infrastructure": {"cloud-infrastructure", "cloud-cli"},
        "infrastructure-as-code": {"infrastructure-as-code", "terraform"},
        "monitoring-observability": {
            "monitoring-observability",
            "monitoring",
            "metrics-reader",
            "telemetry-store",
        },
        "model-runtime": {
            "model-runtime",
            "ml-runtime",
            "gpu-runtime",
            "cloud-or-local-model-runtime",
        },
        "device-testing": {
            "device-testing",
            "device-lab",
            "device-test-host",
            "device-test-rig",
        },
        "performance-profiling": {
            "performance-profiling",
            "performance-profiler",
            "profiler",
        },
        "native-delegation": {"native-delegation"},
    }
    aliases: dict[str, str] = {}
    for canonical, values in groups.items():
        if canonical not in _BASE_CANONICAL_TOOL_CAPABILITIES:  # pragma: no cover
            raise RuntimeError(f"unknown canonical tool capability: {canonical}")
        for alias in values:
            previous = aliases.setdefault(alias, canonical)
            if previous != canonical:  # pragma: no cover
                raise RuntimeError(f"ambiguous tool capability alias: {alias}")
    for reviewed_label in _REVIEWED_TOOL_LABELS:
        aliases.setdefault(reviewed_label, reviewed_label)
    return aliases


TOOL_CAPABILITY_ALIASES: Final[Mapping[str, str]] = MappingProxyType(_alias_map())
CANONICAL_TOOL_CAPABILITIES: Final[frozenset[str]] = frozenset(
    _BASE_CANONICAL_TOOL_CAPABILITIES.union(TOOL_CAPABILITY_ALIASES.values())
)

_NATIVE_HOST_CAPABILITIES: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    dict.fromkeys(
        EXECUTION_HOSTS,
        (
            "code-execution",
            "native-delegation",
            "package-management",
            "repository-read",
            "repository-write",
            "shell-execution",
            "source-control",
            "test-execution",
        ),
    )
)


def _token(value: object) -> str:
    normalized = str(value or "").strip().casefold()
    return normalized if _TOKEN.fullmatch(normalized) else ""


def canonical_tool_capability(value: object) -> str | None:
    """Return one governed capability or ``None`` for an unknown label."""

    normalized = _token(value)
    return TOOL_CAPABILITY_ALIASES.get(normalized) if normalized else None


def canonicalize_tool_capabilities(
    values: Iterable[object] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return bounded canonical and unknown labels without guessing aliases."""

    canonical: set[str] = set()
    unknown: set[str] = set()
    if values is None:
        return (), ()
    for index, value in enumerate(values):
        if index >= MAX_TOOL_CAPABILITIES:
            unknown.add("capability-list-overflow")
            break
        normalized = _token(value)
        if not normalized:
            unknown.add("invalid-capability-label")
            continue
        resolved = canonical_tool_capability(normalized)
        if resolved is None:
            unknown.add(normalized)
        else:
            canonical.add(resolved)
    return tuple(sorted(canonical)), tuple(sorted(unknown))


def split_supported_surfaces(values: Iterable[object] | None) -> dict[str, tuple[str, ...]]:
    """Separate legacy roster host labels into execution and inference axes."""

    normalized = {_token(value) for value in values or ()}
    normalized.discard("")
    execution = tuple(host for host in EXECUTION_HOSTS if host in normalized)
    inference = tuple(surface for surface in INFERENCE_SURFACES if surface in normalized)
    known = set(execution).union(inference)
    return {
        "execution_hosts": execution,
        "inference_surfaces": inference,
        "unknown_surfaces": tuple(sorted(normalized.difference(known))),
    }


def execution_contract_projection(agent: Mapping[str, Any]) -> dict[str, list[str]]:
    """Derive operational axes from one reviewed roster contract.

    ``supported_platforms`` remains the tool-execution constraint.  A direct,
    tool-free adviser/planner/reviewer is explicitly portable for reasoning;
    this does not widen mutation or executable eligibility.
    """

    raw_tools = agent.get("required_tools")
    tools = raw_tools if isinstance(raw_tools, (list, tuple)) else ()
    required, unknown_tools = canonicalize_tool_capabilities(tools)
    raw_hosts = agent.get("supported_hosts")
    surfaces = split_supported_surfaces(raw_hosts if isinstance(raw_hosts, (list, tuple)) else ())
    raw_platforms = agent.get("supported_platforms")
    tool_platforms = tuple(
        platform
        for platform in SUPPORTED_PLATFORMS
        if platform in {_token(item) for item in raw_platforms or ()}
    )
    reasoning_portable = (
        not tools
        and str(agent.get("context_mode") or "").strip().casefold() == "direct_safe"
        and str(agent.get("authority") or "").strip().casefold() in {"advise", "plan", "review"}
    )
    reasoning_platforms = SUPPORTED_PLATFORMS if reasoning_portable else tool_platforms
    return {
        "required_capabilities": list(required),
        "unknown_required_tools": list(unknown_tools),
        "supported_execution_hosts": list(surfaces["execution_hosts"]),
        "supported_inference_surfaces": list(surfaces["inference_surfaces"]),
        "unknown_supported_surfaces": list(surfaces["unknown_surfaces"]),
        "supported_reasoning_platforms": list(reasoning_platforms),
        "supported_tool_platforms": list(tool_platforms),
    }


@dataclass(frozen=True, slots=True)
class HostCapabilityReceipt:
    """Bounded current-surface proof consumed by deterministic eligibility."""

    surface: str
    execution_host: str
    inference_surface: str
    platform: str
    status: str
    source: str
    capabilities: tuple[str, ...]
    unknown_tools: tuple[str, ...]
    evidence: tuple[str, ...]
    session_id: str = ""
    trace_id: str = ""
    observed_at: str = ""
    _attestation: str = field(default="", repr=False, compare=False)
    _expires_monotonic_ns: int = field(default=0, repr=False, compare=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": CAPABILITY_CONTRACT_VERSION,
            "surface": self.surface,
            "execution_host": self.execution_host,
            "inference_surface": self.inference_surface,
            "platform": self.platform,
            "status": self.status,
            "source": self.source,
            "capabilities": list(self.capabilities),
            "unknown_tools": list(self.unknown_tools),
            "evidence": list(self.evidence),
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "observed_at": self.observed_at,
        }


def _monotonic_ns() -> int:
    return time.monotonic_ns()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _optional_correlation(value: object, *, field_name: str) -> str:
    return validate_correlation_id(value, field=field_name, required=False)


def _attestation_payload(receipt: HostCapabilityReceipt) -> bytes:
    values = (
        receipt.surface,
        receipt.execution_host,
        receipt.platform,
        receipt.status,
        receipt.source,
        receipt.session_id,
        receipt.trace_id,
        receipt.observed_at,
        str(receipt._expires_monotonic_ns),
        *receipt.capabilities,
        "--unknown-tools--",
        *receipt.unknown_tools,
        "--evidence--",
        *receipt.evidence,
    )
    return "\0".join(values).encode("utf-8")


def _seal_native_receipt(receipt: HostCapabilityReceipt) -> HostCapabilityReceipt:
    signature = hmac.new(
        _CAPABILITY_ATTESTATION_KEY,
        _attestation_payload(receipt),
        hashlib.sha256,
    ).hexdigest()
    return replace(receipt, _attestation=signature)


def _unproven_native_receipt(
    surface: str,
    *,
    platform: str,
    session_id: str = "",
    trace_id: str = "",
    reason: str = "missing-native-adapter-receipt",
    unknown_tools: tuple[str, ...] = (),
) -> HostCapabilityReceipt:
    return HostCapabilityReceipt(
        surface=surface,
        execution_host="",
        inference_surface="",
        platform=platform,
        status="native-evidence-unproven",
        source="native-adapter-event",
        capabilities=(),
        unknown_tools=unknown_tools,
        evidence=(f"unproven:{reason}",),
        session_id=session_id,
        trace_id=trace_id,
    )


def _native_receipt_current(
    receipt: HostCapabilityReceipt,
    *,
    surface: str,
    platform: str,
    session_id: str,
    trace_id: str,
) -> tuple[bool, str]:
    if receipt.status != "native-contract-verified" or receipt.source != "native-adapter-event":
        return False, "not-native-adapter-attested"
    if receipt.surface != surface or receipt.execution_host != surface:
        return False, "host-mismatch"
    if receipt.platform != platform or platform not in SUPPORTED_PLATFORMS:
        return False, "platform-mismatch"
    if receipt.session_id != session_id or receipt.trace_id != trace_id:
        return False, "correlation-mismatch"
    if not receipt._attestation or receipt._expires_monotonic_ns <= 0:
        return False, "missing-attestation"
    expected = hmac.new(
        _CAPABILITY_ATTESTATION_KEY,
        _attestation_payload(receipt),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(receipt._attestation, expected):
        return False, "invalid-attestation"
    remaining = receipt._expires_monotonic_ns - _monotonic_ns()
    if remaining < 0 or remaining > _NATIVE_ADAPTER_RECEIPT_TTL_NS:
        return False, "stale-attestation"
    return True, ""


def _project_observed_at(value: object) -> str:
    observed_at = " ".join(str(value or "").split())
    if len(observed_at) > 64:
        raise ValueError("observed_at is oversized")
    if not observed_at:
        return ""
    parsed = datetime.fromisoformat(observed_at)
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return observed_at


def project_host_capability_receipt(value: object) -> dict[str, Any] | None:
    """Validate and bound an untrusted serialized capability receipt."""

    if not isinstance(value, Mapping) or value.get("contract_version") != (
        CAPABILITY_CONTRACT_VERSION
    ):
        return None
    surface = _token(value.get("surface")) or "unknown"
    execution_host = _token(value.get("execution_host"))
    inference_surface = _token(value.get("inference_surface"))
    platform = _token(value.get("platform")) or "unknown"
    status = _token(value.get("status"))
    source = _token(value.get("source"))
    raw_capabilities = value.get("capabilities")
    raw_unknown = value.get("unknown_tools")
    raw_evidence = value.get("evidence")
    try:
        session_id = _optional_correlation(value.get("session_id", ""), field_name="session_id")
        trace_id = _optional_correlation(value.get("trace_id", ""), field_name="trace_id")
        observed_at = _project_observed_at(value.get("observed_at"))
    except ValueError:
        return None
    if (
        execution_host not in {"", *EXECUTION_HOSTS}
        or inference_surface not in {"", *INFERENCE_SURFACES}
        or (execution_host and inference_surface)
        or platform not in {"unknown", *SUPPORTED_PLATFORMS}
        or status not in _RECEIPT_STATUSES
        or not source
        or not isinstance(raw_capabilities, list)
        or not isinstance(raw_unknown, list)
        or not isinstance(raw_evidence, list)
        or len(raw_capabilities) > MAX_TOOL_CAPABILITIES
        or len(raw_unknown) > MAX_TOOL_CAPABILITIES
        or len(raw_evidence) > MAX_CAPABILITY_EVIDENCE_ITEMS
        or bool(session_id) != bool(trace_id)
    ):
        return None
    capabilities = tuple(_token(item) for item in raw_capabilities)
    unknown_tools = tuple(_token(item) for item in raw_unknown)
    evidence = tuple(" ".join(str(item or "").split())[:256] for item in raw_evidence)
    if (
        any(item not in CANONICAL_TOOL_CAPABILITIES for item in capabilities)
        or any(not item for item in unknown_tools)
        or any(not item for item in evidence)
        or list(capabilities) != sorted(set(capabilities))
        or list(unknown_tools) != sorted(set(unknown_tools))
        or len(evidence) != len(set(evidence))
    ):
        return None
    if execution_host:
        expected_source = {
            "native-contract-verified": "native-adapter-event",
            "native-installation-verified": "native-installation-evidence",
        }.get(status)
        if surface != execution_host or source != expected_source:
            return None
        if status == "native-contract-verified" and not (session_id and trace_id and observed_at):
            return None
        if status == "native-installation-verified" and (session_id or trace_id or observed_at):
            return None
    elif inference_surface:
        if (
            surface != inference_surface
            or status != "inference-only"
            or source != "inference-adapter-event"
            or capabilities
        ):
            return None
    elif status not in {
        "unknown",
        "explicit-tools-without-execution-host",
        "native-evidence-unproven",
    }:
        return None
    elif status == "native-evidence-unproven":
        if source not in {"native-adapter-event", "native-installation-evidence"} or capabilities:
            return None
    elif source != "unproven-surface":
        return None
    return {
        "contract_version": CAPABILITY_CONTRACT_VERSION,
        "surface": surface,
        "execution_host": execution_host,
        "inference_surface": inference_surface,
        "platform": platform,
        "status": status,
        "source": source,
        "capabilities": list(capabilities),
        "unknown_tools": list(unknown_tools),
        "evidence": list(evidence),
        "session_id": session_id,
        "trace_id": trace_id,
        "observed_at": observed_at,
    }


def host_capability_receipt(
    surface: object,
    *,
    platform: object,
    available_tools: Iterable[object] | None = None,
    session_id: object = "",
    trace_id: object = "",
) -> HostCapabilityReceipt:
    """Describe a claimed surface without treating its name as execution proof."""

    normalized_surface = _token(surface) or "unknown"
    normalized_platform = _token(platform)
    if normalized_platform not in SUPPORTED_PLATFORMS:
        normalized_platform = "unknown"
    normalized_session = _optional_correlation(session_id, field_name="session_id")
    normalized_trace = _optional_correlation(trace_id, field_name="trace_id")
    if bool(normalized_session) != bool(normalized_trace):
        raise ValueError("session_id and trace_id must be supplied together")
    explicit, unknown = canonicalize_tool_capabilities(available_tools)
    if normalized_surface in EXECUTION_HOSTS:
        return _unproven_native_receipt(
            normalized_surface,
            platform=normalized_platform,
            session_id=normalized_session,
            trace_id=normalized_trace,
            reason=(
                "untrusted-explicit-tool-list" if explicit else "missing-native-adapter-receipt"
            ),
            unknown_tools=unknown,
        )
    if normalized_surface in INFERENCE_SURFACES:
        return HostCapabilityReceipt(
            surface=normalized_surface,
            execution_host="",
            inference_surface=normalized_surface,
            platform=normalized_platform,
            status="inference-only",
            source="inference-adapter-event",
            capabilities=(),
            unknown_tools=unknown,
            evidence=(f"inference-adapter-event:{normalized_surface}",),
            session_id=normalized_session,
            trace_id=normalized_trace,
        )
    status = "explicit-tools-without-execution-host" if explicit else "unknown"
    evidence = ("explicit-tool-list",) if explicit else ("execution-host-unproven",)
    return HostCapabilityReceipt(
        surface=normalized_surface,
        execution_host="",
        inference_surface="",
        platform=normalized_platform,
        status=status,
        source="unproven-surface",
        capabilities=explicit,
        unknown_tools=unknown,
        evidence=evidence,
        session_id=normalized_session,
        trace_id=normalized_trace,
    )


def native_adapter_capability_receipt(
    host: object,
    *,
    platform: object,
    session_id: object,
    trace_id: object,
    available_tools: Iterable[object] | None = None,
    restricted: bool = False,
) -> HostCapabilityReceipt:
    """Attest one fresh managed-adapter event for one exact turn correlation.

    The private process seal is deliberately not serialized. A transport caller
    can replay the public receipt for diagnostics, but cannot use it to authorize
    another route, correlation, platform, or process.
    """

    normalized_host = _token(host)
    if normalized_host not in EXECUTION_HOSTS:
        raise ValueError("native adapter receipt requires a supported execution host")
    normalized_platform = _token(platform)
    normalized_session = validate_correlation_id(session_id, field="session_id")
    normalized_trace = validate_correlation_id(trace_id, field="trace_id")
    if restricted is True:
        return _unproven_native_receipt(
            normalized_host,
            platform=(
                normalized_platform if normalized_platform in SUPPORTED_PLATFORMS else "unknown"
            ),
            session_id=normalized_session,
            trace_id=normalized_trace,
            reason="adapter-reported-restricted",
        )
    if normalized_platform not in SUPPORTED_PLATFORMS:
        return _unproven_native_receipt(
            normalized_host,
            platform="unknown",
            session_id=normalized_session,
            trace_id=normalized_trace,
            reason="platform-unproven",
        )
    explicit, unknown = canonicalize_tool_capabilities(available_tools)
    capabilities = tuple(sorted(set(_NATIVE_HOST_CAPABILITIES[normalized_host]).union(explicit)))
    now = _monotonic_ns()
    receipt = HostCapabilityReceipt(
        surface=normalized_host,
        execution_host=normalized_host,
        inference_surface="",
        platform=normalized_platform,
        status="native-contract-verified",
        source="native-adapter-event",
        capabilities=capabilities,
        unknown_tools=unknown,
        evidence=(
            f"native-adapter-event:{normalized_host}",
            f"managed-host-contract:{CAPABILITY_CONTRACT_VERSION}",
        ),
        session_id=normalized_session,
        trace_id=normalized_trace,
        observed_at=_utc_now(),
        _expires_monotonic_ns=now + _NATIVE_ADAPTER_RECEIPT_TTL_NS,
    )
    return _seal_native_receipt(receipt)


def diagnostic_installation_capability_receipt(
    value: object,
    *,
    surface: object,
    platform: object,
) -> HostCapabilityReceipt | None:
    """Rehydrate verified inventory evidence for non-executing diagnostics only."""

    projected = project_host_capability_receipt(value)
    normalized_surface = _token(surface)
    normalized_platform = _token(platform)
    if (
        projected is None
        or normalized_surface not in EXECUTION_HOSTS
        or normalized_platform not in SUPPORTED_PLATFORMS
        or projected["surface"] != normalized_surface
        or projected["execution_host"] != normalized_surface
        or projected["platform"] != normalized_platform
        or projected["status"] != "native-installation-verified"
        or projected["source"] != "native-installation-evidence"
    ):
        return None
    return HostCapabilityReceipt(
        surface=normalized_surface,
        execution_host=normalized_surface,
        inference_surface="",
        platform=normalized_platform,
        status="native-installation-verified",
        source="native-installation-evidence",
        capabilities=tuple(projected["capabilities"]),
        unknown_tools=tuple(projected["unknown_tools"]),
        evidence=tuple(projected["evidence"]),
    )


def current_host_capability_receipt(
    receipt: HostCapabilityReceipt | None,
    *,
    surface: object,
    platform: object,
    session_id: object,
    trace_id: object,
    allow_installation_diagnostic: bool = False,
) -> HostCapabilityReceipt:
    """Accept only a fresh opaque receipt bound to this exact route."""

    normalized_surface = _token(surface) or "unknown"
    normalized_platform = _token(platform)
    if normalized_platform not in SUPPORTED_PLATFORMS:
        normalized_platform = "unknown"
    normalized_session = validate_correlation_id(session_id, field="session_id")
    normalized_trace = validate_correlation_id(trace_id, field="trace_id")
    if normalized_surface not in EXECUTION_HOSTS:
        return host_capability_receipt(
            normalized_surface,
            platform=normalized_platform,
            session_id=normalized_session,
            trace_id=normalized_trace,
        )
    if (
        isinstance(receipt, HostCapabilityReceipt)
        and receipt.status == "native-evidence-unproven"
        and receipt.source == "native-adapter-event"
        and receipt.surface == normalized_surface
        and not receipt.execution_host
        and receipt.platform == normalized_platform
        and not receipt.capabilities
        and receipt.session_id == normalized_session
        and receipt.trace_id == normalized_trace
    ):
        return receipt
    if (
        allow_installation_diagnostic
        and isinstance(receipt, HostCapabilityReceipt)
        and receipt.status == "native-installation-verified"
        and receipt.source == "native-installation-evidence"
        and receipt.surface == normalized_surface
        and receipt.execution_host == normalized_surface
        and receipt.platform == normalized_platform
        and not receipt.session_id
        and not receipt.trace_id
        and not receipt.observed_at
    ):
        return receipt
    if isinstance(receipt, HostCapabilityReceipt):
        verified, reason = _native_receipt_current(
            receipt,
            surface=normalized_surface,
            platform=normalized_platform,
            session_id=normalized_session,
            trace_id=normalized_trace,
        )
        if verified:
            return receipt
    else:
        reason = "missing-native-adapter-receipt"
    return _unproven_native_receipt(
        normalized_surface,
        platform=normalized_platform,
        session_id=normalized_session,
        trace_id=normalized_trace,
        reason=reason,
    )


def host_capability_receipt_from_native_evidence(
    host: object,
    *,
    platform: object,
    native_record: Mapping[str, Any] | None,
) -> HostCapabilityReceipt:
    """Derive executable capabilities from bounded native inventory facts.

    Inventory evidence is stricter than a live adapter event: executable
    discovery, native registration, and native enablement must all be exactly
    true.  Missing and unknown fields produce an explicit unproven receipt.
    """

    normalized_host = _token(host) or "unknown"
    normalized_platform = _token(platform)
    if normalized_platform not in SUPPORTED_PLATFORMS:
        normalized_platform = "unknown"
    if normalized_host not in EXECUTION_HOSTS:
        return host_capability_receipt(
            normalized_host,
            platform=normalized_platform,
        )
    record_host = _token(native_record.get("host")) if isinstance(native_record, Mapping) else ""
    proofs = {
        "host_identity": record_host == normalized_host,
        "executable": bool(
            isinstance(native_record, Mapping)
            and native_record.get("executable_discovered") is True
        ),
        "registered": bool(
            isinstance(native_record, Mapping) and native_record.get("registered") is True
        ),
        "enabled": bool(
            isinstance(native_record, Mapping) and native_record.get("enabled") is True
        ),
        "managed_bundle": bool(
            isinstance(native_record, Mapping)
            and str(native_record.get("managed_plugin_version") or "").strip()
            and native_record.get("launcher_artifacts_current") is True
        ),
    }
    missing = tuple(sorted(name for name, proven in proofs.items() if not proven))
    if missing:
        return HostCapabilityReceipt(
            surface=normalized_host,
            execution_host="",
            inference_surface="",
            platform=normalized_platform,
            status="native-evidence-unproven",
            source="native-installation-evidence",
            capabilities=(),
            unknown_tools=(),
            evidence=tuple(f"unproven:{item}" for item in missing),
        )
    capabilities = _NATIVE_HOST_CAPABILITIES[normalized_host]
    return HostCapabilityReceipt(
        surface=normalized_host,
        execution_host=normalized_host,
        inference_surface="",
        platform=normalized_platform,
        status="native-installation-verified",
        source="native-installation-evidence",
        capabilities=capabilities,
        unknown_tools=(),
        evidence=(
            f"native-inventory-verified:{normalized_host}",
            f"managed-host-contract:{CAPABILITY_CONTRACT_VERSION}",
        ),
    )


__all__ = [
    "CANONICAL_TOOL_CAPABILITIES",
    "CAPABILITY_CONTRACT_VERSION",
    "EXECUTION_HOSTS",
    "INFERENCE_SURFACES",
    "MAX_CAPABILITY_EVIDENCE_ITEMS",
    "MAX_CAPABILITY_TOKEN_CHARS",
    "MAX_TOOL_CAPABILITIES",
    "NATIVE_ADAPTER_RECEIPT_TTL_SECONDS",
    "SUPPORTED_PLATFORMS",
    "TOOL_CAPABILITY_ALIASES",
    "HostCapabilityReceipt",
    "canonical_tool_capability",
    "canonicalize_tool_capabilities",
    "current_host_capability_receipt",
    "diagnostic_installation_capability_receipt",
    "execution_contract_projection",
    "host_capability_receipt",
    "host_capability_receipt_from_native_evidence",
    "native_adapter_capability_receipt",
    "project_host_capability_receipt",
    "split_supported_surfaces",
]
