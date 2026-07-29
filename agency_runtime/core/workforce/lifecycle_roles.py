"""Typed lifecycle owners shared by recruitment and final staffing verification."""

from __future__ import annotations

import re
from typing import Any

_TOKENS = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)
_ALIASES = {
    "analyse": "analysis",
    "analyze": "analysis",
    "analyzed": "analysis",
    "analyzer": "analysis",
    "configure": "configuration",
    "configured": "configuration",
    "configuring": "configuration",
    "docs": "documentation",
    "document": "documentation",
    "documents": "documentation",
    "implement": "implementation",
    "implemented": "implementation",
    "implementing": "implementation",
    "install": "installation",
    "installable": "installation",
    "installed": "installation",
    "installer": "installation",
    "indexed": "index",
    "indexing": "index",
    "integrate": "integration",
    "integrated": "integration",
    "interpret": "analysis",
    "interpretation": "analysis",
    "observe": "observability",
    "package": "packaging",
    "packaged": "packaging",
    "packages": "packaging",
    "released": "release",
    "releasing": "release",
    "results": "result",
    "reviewed": "review",
    "reviewer": "review",
    "reviewing": "review",
    "secure": "security",
    "tests": "test",
    "testing": "test",
    "telemetry": "observability",
    "validate": "verification",
    "validated": "verification",
    "validation": "verification",
    "verified": "verification",
    "verifier": "verification",
    "verify": "verification",
}


def semantic_tokens(*values: str) -> frozenset[str]:
    """Normalize bounded routing text without letting filler words win ties."""

    return frozenset(
        _ALIASES.get(token, token)
        for value in values
        for token in _TOKENS.findall(value.casefold())
        if token not in _STOPWORDS
    )


def _evidence_anchors(unit: Any, tokens: frozenset[str]) -> tuple[str, ...]:
    if unit.lifecycle_phase == "release" or tokens & {"release", "installation"}:
        return ("cross-platform-release-verifier", "test-results-analyzer")
    if tokens & {"integration", "application", "authentication"}:
        return ("application-integration-verifier", "test-results-analyzer")
    if tokens & {"performance", "benchmark", "latency", "throughput"}:
        return ("performance-benchmarker", "test-results-analyzer")
    return ("test-results-analyzer",)


def _review_anchors(unit: Any, tokens: frozenset[str]) -> tuple[str, ...]:
    if "legal" in tokens and tokens & {"document", "documentation"}:
        return ("legal-document-review",)
    if "finance" in unit.domains and (
        "cfo" in tokens or {"chief", "financial", "officer"} <= tokens
    ):
        return ("chief-financial-officer",)
    if "accessibility" in unit.domains or tokens & {"accessibility", "wcag"}:
        return ("accessibility-auditor",)
    if "workforce-governance" in unit.domains and tokens & {
        "selection",
        "staffing",
        "workforce",
        "recruitment",
    }:
        return ("selection-safety-critic",)
    if unit.lifecycle_phase == "release":
        return ("cross-platform-release-verifier",)
    if "security" in unit.domains and tokens & {
        "exploit",
        "exploitability",
        "generated",
        "regression",
        "security",
        "vulnerability",
        "vulnerabilities",
    }:
        return ("ai-generated-code-security-auditor",)
    if "quality-assurance" in unit.domains and tokens & {
        "integration",
        "authentication",
        "data-flow",
    }:
        return ("application-integration-verifier",)
    if "software-engineering" in unit.domains or (
        "quality-assurance" in unit.domains and tokens & {"code", "implementation", "software"}
    ):
        return ("code-reviewer",)
    return ()


def _implementation_anchors(unit: Any, tokens: frozenset[str]) -> tuple[str, ...]:
    if "design" in unit.domains and tokens & {
        "delight",
        "microinteraction",
        "playful",
        "whimsy",
    }:
        return ("whimsy-injector",)
    if (
        "lsp" in tokens
        or {"language", "server", "index"} <= tokens
        or {
            "incremental",
            "index",
        }
        <= tokens
    ):
        return ("lsp-index-engineer",)
    result: list[str] = []
    stacks = set(unit.languages + unit.frameworks)
    if stacks & {"typescript", "javascript", "node"}:
        result.append("typescript-application-engineer")
    if "python" in stacks:
        result.append("python-application-engineer")
    if not result and tokens & {"frontend", "page", "ui", "web", "website"}:
        result.append("frontend-developer")
    if (
        tokens & {"installer", "installation", "packaging", "upgrade", "uninstall"}
        or {
            "linux",
            "windows",
        }
        <= tokens
    ):
        result.append("cross-platform-installer-engineer")
    if tokens & {"observability", "diagnostics", "health", "tracing"}:
        result.append("application-observability-engineer")
    if not result and tokens & {"backend", "service", "persistence", "api"}:
        result.append("backend-service-engineer")
    if not result:
        # A bounded implementation unit still needs an audited specialist when
        # no stack or product-specific owner can be proven. The minimum-change
        # role is the governed narrow fallback, not an untyped generic child.
        result.append("minimal-change-engineer")
    return tuple(dict.fromkeys(result))


def _discovery_anchors(unit: Any, tokens: frozenset[str]) -> tuple[str, ...]:
    if (
        tokens & {"postgres", "postgresql"}
        and "query" in tokens
        and tokens & {"performance", "plan", "slow"}
    ):
        return ("database-optimizer",)
    if "healthcare" in unit.domains and ("clinical" in tokens and tokens & {"evidence", "trial"}):
        return ("clinical-evidence-agent",)
    if "finance" in unit.domains and {"accounts", "payable"} <= tokens:
        return ("accounts-payable-agent",)
    if (
        "lsp" in tokens
        or {"language", "server", "index"} <= tokens
        or {"incremental", "index"} <= tokens
    ):
        return ("lsp-index-engineer",)
    if tokens & {"archaeology", "historical", "history", "legacy"}:
        return ("codebase-archaeologist",)
    if tokens & {
        "boundaries",
        "code",
        "codebase",
        "hook",
        "map",
        "path",
        "repository",
        "routing",
        "runtime",
        "structure",
        "trust",
    }:
        return ("codebase-onboarding-engineer",)
    if "software-engineering" in unit.domains:
        # A discovery unit that precedes repository implementation still needs
        # the audited codebase mapper even when the planner describes the
        # requested product artifact (for example, a local page) instead of
        # repeating the words codebase or repository in the outcome.
        return ("codebase-onboarding-engineer",)
    return ()


def _plan_anchors(unit: Any, tokens: frozenset[str]) -> tuple[str, ...]:
    if "design" in unit.domains and tokens & {"brand", "governance", "identity"}:
        return ("brand-guardian",)
    return ()


def role_anchors(unit: Any, *, request: str = "") -> tuple[str, ...]:
    """Return audited lifecycle owners for one typed work unit."""

    tokens = semantic_tokens(
        unit.outcome,
        *unit.domains,
        *unit.languages,
        *unit.frameworks,
        *unit.required_capabilities,
    )
    if unit.artifact_kind == "analysis" and unit.lifecycle_phase == "discovery":
        request_tokens = semantic_tokens(request)
        scoped_tokens = tokens
        database_query_request = bool(
            request_tokens & {"postgres", "postgresql"}
            and "query" in request_tokens
            and request_tokens & {"performance", "plan", "slow"}
        )
        runtime_routing_request = bool(
            request_tokens & {"hook", "routing", "runtime"}
            and request_tokens & {"diagnose", "diagnosis", "evidence", "integration", "trace"}
        )
        if (
            "finance" in unit.domains
            or database_query_request
            or runtime_routing_request
            or (
                tokens & {"cancellation", "incremental", "index", "symbol"}
                and ("lsp" in request_tokens or {"language", "server"} <= request_tokens)
            )
        ):
            scoped_tokens |= request_tokens
        return _discovery_anchors(unit, scoped_tokens)
    if unit.artifact_kind == "plan" and unit.lifecycle_phase == "planning":
        return _plan_anchors(unit, tokens)
    if unit.artifact_kind == "documentation":
        return ("technical-writer",)
    if unit.artifact_kind == "test-code" and unit.lifecycle_phase == "testing":
        return ("software-test-engineer",)
    if unit.artifact_kind == "test-evidence":
        return _evidence_anchors(unit, tokens)
    if unit.artifact_kind == "review-report":
        request_tokens = semantic_tokens(request) if "finance" in unit.domains else frozenset()
        return _review_anchors(unit, tokens | request_tokens)
    if unit.artifact_kind == "implementation-change":
        request_tokens = semantic_tokens(request)
        scoped_tokens = tokens
        if tokens & {"cancellation", "incremental", "index", "symbol"} and (
            "lsp" in request_tokens or {"language", "server"} <= request_tokens
        ):
            scoped_tokens |= request_tokens
        if tokens & {"installation", "packaging", "uninstall", "upgrade"}:
            scoped_tokens |= request_tokens & {
                "installation",
                "linux",
                "packaging",
                "uninstall",
                "upgrade",
                "windows",
            }
        return _implementation_anchors(unit, scoped_tokens)
    return ()


__all__ = ["role_anchors", "semantic_tokens"]
