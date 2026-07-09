"""Domain context expansion — enriches queries with discipline vocabulary.

Ported from ~/.litellm/agency_preflight.py.
"""

from __future__ import annotations

_DOMAIN_EXPANSIONS: dict[str, list[str]] = {
    "conveyor": ["ci cd pipeline", "workflow automation", "task orchestration", "software delivery"],
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


def expand_query(query: str) -> str:
    """Expand domain-specific terms with discipline equivalents."""
    query_lower = query.lower()
    expansions: list[str] = []
    for term, disciplines in _DOMAIN_EXPANSIONS.items():
        if term in query_lower:
            expansions.extend(disciplines)
    if expansions:
        seen: set[str] = set()
        unique = [d for d in expansions if not (d in seen or seen.add(d))]
        return query + " [domain context: " + ", ".join(unique) + "]"
    return query
