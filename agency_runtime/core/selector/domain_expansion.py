"""Query expansion — adds domain context to improve specialist matching."""

from __future__ import annotations

import re
from functools import lru_cache

_DOMAIN_EXPANSIONS: dict[str, list[str]] = {
    "agency": [
        "multi-agent system",
        "agent orchestration",
        "specialist routing",
        "native delegation",
    ],
    "agent selection": [
        "specialist routing",
        "agent orchestration",
        "compatibility analysis",
    ],
    "response header": [
        "developer experience",
        "response telemetry",
    ],
    "dashboard": [
        "operations interface",
        "runtime controls",
    ],
    "conveyor": [
        "ci cd pipeline",
        "workflow automation",
        "task orchestration",
        "software delivery",
    ],
    "openclaw": ["multi-agent system", "ai agent orchestration", "distributed system"],
    "nexus": ["multi-agent system", "ai agent orchestration", "distributed system"],
    "mentor": ["ai agent", "system architecture", "code review"],
    "hermes": ["ai agent", "system architecture", "code review"],
    "litellm": ["api gateway", "model serving", "inference optimization", "python backend"],
    "ollama": ["model serving", "inference optimization", "local deployment"],
    "gateway": ["api gateway", "infrastructure", "backend architecture"],
    "systemd": ["devops", "infrastructure", "linux administration", "service management"],
    "vllm": ["model serving", "inference optimization", "gpu infrastructure"],
    "rocm": ["gpu infrastructure", "hardware optimization", "system performance"],
    "acp": ["ai agent", "inter-process communication", "system integration"],
    "telegram": ["messaging platform", "real-time communication", "bot development"],
    "discord": ["messaging platform", "real-time communication", "bot development"],
    "slack": ["messaging platform", "real-time communication", "bot development"],
    "warden": ["ai assistant", "system monitoring", "automation"],
    "scout": ["ai agent", "workbench", "code assistance"],
    "finance automation": ["financial analysis", "trading", "data visualization"],
}


@lru_cache(maxsize=len(_DOMAIN_EXPANSIONS))
def _domain_pattern(term: str) -> re.Pattern[str]:
    words = re.findall(r"[a-z0-9]+", term.lower())
    phrase = r"[^a-z0-9]+".join(re.escape(word) for word in words)
    return re.compile(rf"(?<![a-z0-9]){phrase}(?![a-z0-9])", re.IGNORECASE)


def expand_query(query: str) -> str:
    """Expand domain-specific terms with discipline equivalents."""
    expansions: list[str] = []
    for term, disciplines in _DOMAIN_EXPANSIONS.items():
        if _domain_pattern(term).search(query):
            expansions.extend(disciplines)
    if expansions:
        seen: set[str] = set()
        unique = [d for d in expansions if not (d in seen or seen.add(d))]
        return query + " [domain context: " + ", ".join(unique) + "]"
    return query
