<div align="center">

# Agency Runtime

**A portable control plane that routes AI agent tasks to the right specialist, tracks which model actually ran, and makes every decision auditable.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 104](https://img.shields.io/badge/tests-104%20passed-brightgreen.svg)](#testing)

</div>

---

## Why This Exists

Every AI agent framework has the same problem: **you build an agent, it works great in the demo, then you realize it has no idea which specialist to call for a given task, it can't tell you which model actually ran, and there's no audit trail for what happened.**

Agency Runtime solves this with three core capabilities:

1. **Specialist Routing** — An 8-layer pipeline (token pre-narrowing → LLM judge → session stickiness → cache) matches tasks to the right specialist from your roster. Works with any LLM provider.

2. **Model Receipts** — After every LLM call, captures the *actual model that ran* (not the alias you requested), the provider, latency, and status. Stored in SQLite for audit.

3. **Observability Headers** — Every response starts with a six-line header showing which specialists were loaded, which were delegated, which skills were used, and which model resolved — making agent behavior transparent and debuggable.

## What It Does

```
User asks: "Review this PR for security issues"

Agency Runtime:
  1. Routes → security-architect (confidence: 0.92, source: llm)
  2. Agent loads security-architect specialist context
  3. LLM call runs → response["model"] = "claude-3-5-sonnet" (not the alias)
  4. Response header records everything:

     Agency/Agencies loaded: security-architect
     Agency/Agencies delegated: none
     Skills loaded: github-code-review
     Actual Model selected: [implementation] task-implementation -> anthropic/claude-3-5-sonnet
     Why: Security review requires architectural threat modeling
     How it shaped outcome: Specialist context identified injection risks in auth middleware
```

## Quick Start

### Prerequisites

- Python 3.10+
- At least one LLM provider: [Ollama](https://ollama.ai) (free/local), OpenAI API key, Anthropic API key, or a LiteLLM proxy

### Install

```bash
pip install agency-runtime
```

### One-Command Setup

```bash
# Configure + seed roster + wire into every AI agent on your machine
agency configure
agency install --all
```

That's it. Agency Runtime auto-detects your LLM providers, writes `~/.agency-runtime/agency.yaml`, and wires plugin files into every supported agent host it finds.

## Installation Modes

### Mode 1: Auto-Detect (Recommended)

```bash
agency install --all
```

Scans your machine for installed agent hosts (Hermes, OpenClaw, Codex, Claude Code) and wires Agency Runtime into each one:

```
🔍 Detected 3 agent host(s): hermes, openclaw, codex
✅ hermes: wired → ~/.hermes-nexus/plugins/agency-preflight/__init__.py
✅ openclaw: wired → ~/.openclaw/agency-preflight/__init__.py
✅ codex: wired → ~/.codex/agency-preflight/__init__.py
```

### Mode 2: Specific Agent

```bash
agency install --agent hermes
```

Wires into a single host. Useful if you only want routing for one agent.

### Mode 3: Standalone (No Host Integration)

```bash
agency install
```

Seeds the starter roster and configures the judge model, but doesn't wire into any host. Use Agency Runtime as a library or via the CLI (`agency route`, `agency search`).

## Enable / Disable

Toggle Agency Runtime on or off for any host without uninstalling:

```bash
# Disable for a specific host
agency off --agent hermes

# Re-enable
agency on --agent hermes

# If only one host is detected, agent is auto-selected
agency off
agency on
```

When disabled, the plugin file is renamed to `__init__.py.disabled` — the host simply doesn't load it. No data is lost.

## Configuration

### Guided Wizard

```bash
agency configure
```

Auto-detects your providers and walks you through setup. For non-interactive use:

```bash
agency configure --non-interactive --profile local-only --force
```

### Config File: `~/.agency-runtime/agency.yaml`

```yaml
# ── Provider Fallback Chain ──────────────────────────────
# The judge tries each provider in order until one succeeds.
# Types: litellm, openai-compatible, anthropic, ollama, cli
# Auth: api_key (stored directly, file is 0600), api_key_env, or none

providers:
  # Option A: LiteLLM proxy (handles multiple backends)
  - name: litellm
    type: litellm
    model: task-general          # Your LiteLLM model group
    base_url: http://127.0.0.1:4000
    api_key: sk-litellm-...      # Stored directly (file is 0600)

  # Option B: Direct OpenAI API
  - name: openai
    type: openai-compatible
    model: gpt-4o-mini
    base_url: https://api.openai.com/v1
    api_key_env: OPENAI_API_KEY  # Read from environment

  # Option C: Anthropic API
  - name: anthropic
    type: anthropic
    model: claude-3-5-sonnet-20241022
    base_url: https://api.anthropic.com/v1
    api_key_env: ANTHROPIC_API_KEY

  # Option D: Local Ollama (free, no API key)
  - name: ollama
    type: ollama
    model: qwen3.5:2b
    base_url: http://127.0.0.1:11434
    ollama_mode: true

# ── Judge Settings ───────────────────────────────────────
judge:
  model: task-agency-router      # Model for specialist routing
  base_url: http://127.0.0.1:4000
  api_key: sk-...
  timeout: 15
  max_selected: 3                # Max specialists per task
  confidence_bypass_threshold: 15.0  # Skip LLM if token score is high enough

# ── Ollama Fallback ──────────────────────────────────────
# Used when no providers in the chain succeed
ollama:
  enabled: true
  base_url: http://127.0.0.1:11434
  model: qwen3.5:2b

# ── Selector Tuning ──────────────────────────────────────
selector:
  min_confidence: 0.4           # Minimum confidence to suggest a specialist
  max_user_msg_len: 4000        # Truncate long messages before routing
  trivial_msg_threshold: 12     # Messages shorter than this skip routing

# ── Storage ──────────────────────────────────────────────
store:
  db_path: ~/.agency-runtime/agency.db  # SQLite: roster, receipts, events
```

### Environment Variable Overrides

All config values can be overridden via environment variables (highest precedence):

| Variable | Overrides |
|----------|-----------|
| `AGENCY_CONFIG_PATH` | Config file location |
| `AGENCY_DB_PATH` | SQLite database path |
| `AGENCY_JUDGE_MODEL` | Judge model name |
| `AGENCY_JUDGE_BASE_URL` | Judge endpoint URL |
| `AGENCY_JUDGE_API_KEY` | Judge API key |
| `AGENCY_JUDGE_TIMEOUT` | Judge timeout (seconds) |
| `AGENCY_MAX_SELECTED` | Max specialists per task |
| `AGENCY_BYPASS_THRESHOLD` | Confidence bypass threshold |
| `OLLAMA_BASE_URL` | Ollama endpoint |
| `LITELLM_API_KEY` | LiteLLM proxy key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |

### Profiles

```bash
agency configure --profile local-only   # Ollama only, no network, no auto-sync
agency configure --profile standard     # Default: uses detected providers
agency configure --profile power        # All features, auto-sync, network
```

## Supported Agent Hosts

| Host | Status | Plugin Path |
|------|--------|-------------|
| **Hermes Agent** | ✅ Full support | `~/.hermes-nexus/plugins/agency-preflight/` |
| **OpenClaw / Nexus** | ✅ Full support | `~/.openclaw/agency-preflight/` |
| **Codex** | ✅ Plugin generated | `~/.codex/agency-preflight/` |
| **Claude Code** | ✅ Plugin generated | `~/.claude/agency-preflight/` |

Each host gets a thin plugin file that imports from the installed `agency_runtime` package. No vendoring, no duplication — one package, many hosts.

## How Routing Works

The routing pipeline runs 8 layers, fastest-exit-first:

```
User Message
     │
     ▼
Layer 0: Companion Policy ──── Deterministic action→agent mapping (<1ms)
     │                        e.g. "code review" → code-reviewer
     ▼
Layer 1: Domain Expansion ──── "conveyor" → ci cd pipeline, gitops
     │
     ▼
Layer 2: LRU Cache ─────────── Content-hash + TTL (skip everything if hit)
     │
     ▼
Layer 3: Session Stickiness ── Reuse last routing for similar messages
     │
     ▼
Layer 4: Confidence Bypass ─── Skip LLM if token score ≥ threshold
     │
     ▼
Layer 5: Token Pre-Narrow ──── Narrow 238 agents → top 20 by token score
     │
     ▼
Layer 6: LLM Judge ─────────── Ask judge model to pick best specialists
     │                        Falls back through provider chain on failure
     ▼
Layer 7: Union ─────────────── Merge companion + semantic results
     │
     ▼
Routing Result: { selected_ids, confidence, latency_ms, status }
```

### Provider Fallback Chain

When the LLM judge is called, it tries providers in order:

```
1. providers[0] (e.g. LiteLLM)  ── fails ──▶
2. providers[1] (e.g. OpenAI)   ── fails ──▶
3. providers[2] (e.g. Anthropic) ── fails ──▶
4. providers[3] (e.g. Ollama)   ── fails ──▶
5. Legacy judge config           ── fails ──▶
6. Ollama fallback               ── fails ──▶
7. Token-only (no LLM needed)    ──────────▶  Always succeeds
```

**Agency Runtime always produces a result.** Even with no LLM providers configured, it falls back to token-based scoring.

## CLI Reference

```bash
# Setup
agency configure                    # Guided setup wizard
agency install [--all|--agent NAME] # Install + wire into host(s)
agency on [--agent NAME]            # Enable for a host
agency off [--agent NAME]           # Disable for a host
agency doctor                       # Health check

# Config
agency config show                  # Display effective config (redacted)
agency config show --raw            # Show secrets (use with caution)
agency config set judge.model X     # Set a config value
agency config validate              # Validate config + reachability
agency config path                  # Print config file location

# Roster
agency roster list                  # List active roster
agency search "security"            # Search roster by keyword
agency route "review this PR"       # Route a task to agents
agency sync                         # Download agents from sources
agency source add <url>             # Add a roster source

# Server
agency serve                        # Start HTTP API server
```

## Observability Header

Every response from an agent with Agency Runtime enabled begins with:

```
Agency/Agencies loaded: security-architect, code-reviewer
Agency/Agencies delegated: security-architect via delegate_task
Skills loaded: github-code-review
Actual Model selected: [implementation] task-implementation -> anthropic/claude-3-5-sonnet
Why: Security review requires threat modeling expertise
How it shaped outcome: Identified injection vectors in auth middleware
```

This makes agent behavior transparent: you can always see which specialists were consulted, which model actually ran, and why the routing decision was made.

### Model Receipts

The `Actual Model selected` line is populated from the **actual API response body**, not the requested alias. LiteLLM's complexity router and fallback chains can resolve a request for `task-implementation` to `gpt-4o`, `claude-3-5-sonnet`, or `qwen3-coder` depending on availability — Agency Runtime captures what *actually* happened.

Receipts are stored in SQLite:

```sql
SELECT requested_model, resolved_model, resolved_provider, latency_ms, status
FROM model_receipts
WHERE session_id = '...'
ORDER BY started_at DESC;
```

## Architecture

```
agency_runtime/
├── core/
│   ├── config.py              # agency.yaml loader, ProviderEntry, env overrides
│   ├── config_defaults.yaml   # Bundled defaults
│   ├── detect.py              # Auto-detect LiteLLM, OpenAI, Anthropic, Ollama
│   ├── doctor.py              # 15+ health checks
│   ├── installer.py           # Host detection, plugin wiring, on/off toggle
│   ├── store/
│   │   └── sqlite.py          # Canonical store: roster, receipts, events, skills
│   ├── selector/
│   │   ├── pipeline.py        # 8-layer routing pipeline
│   │   ├── judge.py           # Multi-provider LLM judge with fallback chain
│   │   ├── candidate_narrow.py # Token pre-narrowing (238 → 20)
│   │   ├── cache.py           # Content-hash LRU cache
│   │   ├── stickiness.py      # Session reuse
│   │   └── policy.py          # Companion policy (deterministic action→agent)
│   ├── header/
│   │   ├── contract.py        # Six-line header validation + auto-fill
│   │   └── finalize.py        # Response finalization gate
│   ├── receipts/
│   │   ├── normalize.py       # Receipt normalization (host + LiteLLM)
│   │   ├── host.py            # Host-side receipt capture
│   │   └── litellm.py         # LiteLLM response extraction
│   └── delegation/
│       ├── lifecycle.py       # Worktree-isolated delegation engine
│       ├── backends.py        # delegate_task, delegate_async backends
│       └── ledger.py          # Delegation event ledger
├── adapters/
│   ├── base.py                # BaseAdapter (thin I/O shim contract)
│   ├── hermes/plugin.py       # Hermes Agent adapter
│   ├── openclaw/plugin.py     # OpenClaw/Nexus adapter
│   ├── litellm/callback.py    # LiteLLM callback adapter
│   ├── codex/wrapper.py       # Codex adapter
│   └── generic/wrapper.py     # Generic OpenAI-compatible adapter
├── cli/
│   └── main.py                # `agency` CLI
└── server/
    ├── http.py                # REST API
    └── mcp.py                 # MCP server
```

## Adding Agents to Your Roster

### From Agency-Agents (open source)

```bash
agency source add https://github.com/msitarzewski/agency-agents
agency sync
agency roster approve
agency roster activate
```

### Custom Agents

Add agents directly to the SQLite store via the CLI or Python API:

```python
from agency_runtime.core.store.sqlite import Store

store = Store()
store.activate_agent({
    "slug": "my-specialist",
    "name": "My Specialist",
    "description": "Expert at X, Y, Z",
    "division": "engineering",
    "source": "custom",
    "categories": "code,review,testing",
})
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_config.py -v
```

104 tests covering: config parsing, provider fallback, header validation, roster operations, routing pipeline, delegation lifecycle, doctor checks, and HTTP server.

## Python API

```python
from agency_runtime.core.selector.pipeline import route

# Route a task to specialists
result = route(
    session_id="my-session",
    user_message="Review this PR for security issues",
)
print(result["selected_ids"])    # ["security-architect", "code-reviewer"]
print(result["confidence"])     # 0.92
print(result["status"])         # "applied"
```

## Requirements

- Python 3.10+
- `pyyaml`, `requests` (or `urllib` from stdlib)
- SQLite3 (stdlib)
- Optional: [Ollama](https://ollama.ai) for free local inference

## License

MIT — see [LICENSE](LICENSE). Compatible with [agency-agents](https://github.com/msitarzewski/agency-agents) (also MIT).

## Contributing

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Ensure `python -m pytest tests/ -v` passes
5. Submit a pull request

## Related Projects

- [agency-agents](https://github.com/msitarzewski/agency-agents) — Open-source specialist agent roster (MIT)
- [LiteLLM](https://github.com/BerriAI/litellm) — Multi-provider LLM proxy
- [Ollama](https://ollama.ai) — Local LLM inference
