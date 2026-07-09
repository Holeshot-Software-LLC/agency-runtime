# Agency Runtime Handoff — 2026-07-09

This file is a detailed restart packet for continuing work on `agency-runtime` in a new session. It captures the repository, architecture, user requirements, completed work, verification evidence, known caveats, and the next likely tasks.

## TL;DR

Agency Runtime is Lucas's portable AI-agent control plane. It should be installable into different AI agent hosts (Hermes, OpenClaw/Nexus, Codex, Claude Code, etc.) and provide:

1. Specialist routing from a local roster.
2. Multi-provider judge fallback independent of LiteLLM.
3. Actual-model receipts from API responses, not stale LiteLLM SpendLogs.
4. Six-line Agency observability headers.
5. One-command install into every detected agent host, or one-command install into a specific host.
6. Toggle on/off from the command line now, with a future goal of chat slash commands such as `/agency on` and `/agency off`.
7. Public-ready docs/branding so a future user can point an agent at the repo and ask it to install.

Current repo is pushed here:

- Org repo: `https://github.com/Holeshot-Software-LLC/agency-runtime`
- Local path: `/home/holeshot/agency-runtime`
- Branch: `main`
- Remote: `origin https://github.com/Holeshot-Software-LLC/agency-runtime.git`
- Current pushed head before this handoff file: `a7bba3a feat: one-command install, on/off toggle, comprehensive README`

## User Expectations / Requirements

Lucas's requirements from this session:

### Portability

- Agency Runtime must be a portable package, not a pile of live-only Hermes patches.
- It must work on systems that do not have LiteLLM.
- If LiteLLM is configured but unhealthy, Agency Runtime must fall back to non-LiteLLM providers.
- If Ollama is not installed, it must support direct provider auth paths such as OpenAI API key, Anthropic API key, OpenAI-compatible gateways, etc.
- It should eventually support OAuth/CLI-backed flows where practical, especially Claude/Codex-style auth.

### Configuration

- Everything controlling the plugin should be config-first in `~/.agency-runtime/agency.yaml`.
- Do not rely primarily on system environment variables.
- Env vars are allowed as overrides or deployment conveniences, but config is the single source of truth.
- API keys can be stored directly in `agency.yaml`; the file should be `0600`.
- Configure should be robust like OpenClaw configure: detect what exists, ask or infer provider priority, write a usable fallback chain, and validate.

### Install

Lucas explicitly asked for:

```text
One command. Finds every agent on your machine. Installs for each.
or,
one command, for the particular agent you are installing into: openclaw, hermes, claude, codex, etc.
```

Implemented command shape:

```bash
agency install --all
agency install --agent hermes
agency install --agent openclaw
agency install --agent codex
agency install --agent claude
agency install
```

Desired chat/slash shape for host agents:

```text
/agency on
/agency off
```

Current CLI toggle shape:

```bash
agency on --agent hermes
agency off --agent hermes
agency on --agent codex
agency off --agent codex
```

Important: chat slash command integration is not yet implemented; only CLI toggles exist.

### Documentation / Branding

Lucas wants this public one day. README must be detailed and marketable:

- Explain what Agency Runtime does.
- Explain how it helps.
- Include detailed install instructions.
- Include examples.
- Include architecture/background.
- Be clear enough that a user can point an agent at the repo and ask it to install.
- Use MIT license because `https://github.com/msitarzewski/agency-agents` is MIT and this package uses/works with that ecosystem.

## Repository Status

### Package metadata

`pyproject.toml` currently says:

```toml
[project]
name = "agency-runtime"
version = "0.1.0"
description = "Portable Agency Runtime Control Plane — specialist routing, roster governance, delegation, and model/run observability."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
license-files = ["LICENSE"]
authors = [{name = "Holeshot Software"}]
dependencies = ["pyyaml>=6.0"]

[project.scripts]
agency = "agency_runtime.cli.main:main"
```

### License

`LICENSE` exists and is MIT:

```text
MIT License
Copyright (c) 2026 Holeshot Software
```

### Tests

Latest full suite before this handoff:

```bash
cd /home/holeshot/agency-runtime && python3 -m pytest tests/ -q
# 104 passed in ~12s
```

### Important commits

```text
a7bba3a feat: one-command install, on/off toggle, comprehensive README
dc0be8d feat: multi-provider fallback chain with config-first auth
c2d1274 fix: pre_llm_call always injects routing, pre_verify enforces specialist loading
3b39f58 config-first secrets, doctor auth, packaging hardening, portability fixes
2434f30 Wire portable agency_runtime into live Hermes plugin (Step 2-3 cutover)
886d6cf Fix: post_tool_call hook captures specialist loads, not just skills
cfc7d38 Fix dynamic model resolution: capture actual model from response, not SpendLogs
5eb4de1 Add complexity tier to model header + fix post_api_request race condition
```

## Key Files

### Core config

- `agency_runtime/core/config.py`
- `agency_runtime/core/config_defaults.yaml`

Important types:

- `ProviderEntry`
- `JudgeConfig`
- `OllamaConfig`
- `AgencyConfig`
- `AdapterEntryConfig`

Important config facts:

- `AgencyConfig.providers` is a tuple of `ProviderEntry`.
- `ProviderEntry` supports `name`, `type`, `model`, `base_url`, `api_key`, `api_key_env`, `ollama_mode`, `timeout`.
- `ProviderEntry.resolve_api_key()` prefers direct `api_key`, then env var.
- `ProviderEntry.auth_method()` reports `api_key`, `env_key`, `oauth`, or `none`.
- `ProviderEntry.is_available()` treats Ollama as available with model+base_url and no key; other providers require model + resolved key.
- `_apply_env_overrides()` must preserve `cfg.providers`; this was a bug and is fixed.
- `config_to_yaml()` redacts `api_key` values when `redact=True`.

### Provider detection / configure

- `agency_runtime/core/detect.py`
- `agency_runtime/cli/main.py` (`cmd_configure`)

Current detection creates a `providers` list from detected:

1. LiteLLM
2. OpenAI API key
3. Anthropic API key
4. Ollama

Caveat: The configure wizard is improved but not truly OpenClaw-grade yet. It still needs a deeper interactive fallback-priority editor and first-class OAuth/CLI auth detection.

### Judge fallback chain

- `agency_runtime/core/selector/judge.py`

Current fallback order:

1. Each provider in `cfg.providers` (first success wins).
2. Legacy `cfg.judge` config for backward compatibility.
3. `cfg.ollama` fallback if enabled.
4. Token-only fallback (no LLM needed, always produces routing candidates).

Important design: Agency Runtime must never hard-require LiteLLM. LiteLLM is just one provider type in the chain.

### Host installer / toggles

- `agency_runtime/core/installer.py`
- `agency_runtime/cli/main.py`

Implemented host detection targets:

```python
HOSTS = {
    "hermes": {
        "plugin_dir": "~/.hermes-nexus/plugins/agency-preflight",
        "detect_paths": ["~/.hermes-nexus", "~/.hermes-nexus/plugins"],
        "detect_binary": "hermes",
    },
    "openclaw": {
        "plugin_dir": "~/.openclaw/agency-preflight",
        "detect_paths": ["~/.openclaw"],
        "detect_binary": None,
    },
    "codex": {
        "plugin_dir": "~/.codex/agency-preflight",
        "detect_paths": ["~/.codex"],
        "detect_binary": "codex",
    },
    "claude": {
        "plugin_dir": "~/.claude/agency-preflight",
        "detect_paths": ["~/.claude"],
        "detect_binary": "claude",
    },
}
```

Current installer functions:

- `detect_installed_agents()`
- `install_agent_adapter(host, cfg=None)`
- `toggle_agency(host, enabled)`
- `seed_starter_roster(store)`

Current command behavior tested live:

```bash
agency install --all
# Detected: hermes, openclaw, codex
# Wrote plugin files for all three.

agency off --agent codex
agency on --agent codex
# Renamed __init__.py <-> __init__.py.disabled successfully.
```

Caveat: Current generated plugin template assumes all hosts have Hermes-like hook registration (`register(ctx)` with `pre_llm_call`, `pre_verify`, `post_tool_call`, `post_api_request`, `transform_llm_output`). That is accurate for Hermes and intended for OpenClaw parity, but Codex/Claude may not actually load that plugin path or hook API yet. Treat Codex/Claude generated plugins as scaffolds until host-specific integration is verified.

### Hermes adapter

- `agency_runtime/adapters/hermes/plugin.py`

Important fixed bugs:

1. `pre_llm_call_handler` must always run routing and inject context for non-trivial messages. It must not skip routing just because LiteLLM is healthy.
2. `pre_verify_handler` must reject `Agency/Agencies loaded: none` on non-trivial work when no specialists were actually loaded.
3. `post_tool_call_handler` tracks `skill_view`, `agency_agents_load`, `agency_agents_inspect`, `agency_agents_delegate`, and some `delegate_task` metadata.
4. `post_api_request_handler` reads the resolved model from the response body (`response["model"]` / `response_model`) rather than querying LiteLLM SpendLogs.

### Store

- `agency_runtime/core/store/sqlite.py`

Important fix: `Store.__init__` expands `~` in `db_path`. Before the fix it could create a literal `~/.agency-runtime/agency.db` directory.

### README

- `README.md`

Current README has:

- Market positioning.
- Why this exists.
- Quick start.
- Install modes.
- Enable/disable.
- Configuration reference.
- Provider chain explanation.
- Architecture tree.
- CLI reference.
- Python API examples.
- MIT/license note.

Caveat: README uses `pip install agency-runtime`, but the package may not yet be published to PyPI. Until published, public install instructions need either:

```bash
pip install git+https://github.com/Holeshot-Software-LLC/agency-runtime.git
```

or a release/publish step. If making public before PyPI publication, adjust README accordingly.

## Current Live Local Config

Local config path:

```bash
/home/holeshot/.agency-runtime/agency.yaml
```

It was updated this session to include a provider chain roughly:

1. `litellm` using `task-agency-router` at `http://127.0.0.1:4000` with direct `api_key` stored in config.
2. `ollama` using local model `qwen3-coder-30b-a3b-128k-rocm` at `http://127.0.0.1:11434`.

Do not paste or expose the real API key. The config should be mode `0600`.

Latest doctor after provider-chain config:

```text
✅ provider_litellm: litellm: litellm model=task-agency-router auth=api_key
✅ provider_ollama: ollama: ollama model=qwen3-coder-30b-a3b-128k-rocm auth=none
✅ provider_chain: Fallback chain (2 available): litellm → ollama
Result: ✅ HEALTHY — all checks passed
```

## Skill Library / Operational Context

Relevant skill:

- `agency-specialist-routing`

That skill has been updated repeatedly during this work. It now documents:

- Clean-slate Agency Runtime cutover.
- Portable package is live system.
- No compat shims.
- Config-first secret management.
- LiteLLM independence.
- Provider fallback chain.
- Specialist loading enforcement.
- The recurring failure pattern where agents write `loaded: none` even when routing exists.

Important behavioral rule for future sessions:

- For any non-trivial turn, actually load an Agency specialist (`agency_agents_search` then `agency_agents_load`) before working.
- Do not write `Agency/Agencies loaded: none` unless the turn is genuinely trivial.

Relevant coding workflow skills that must be considered for future code changes:

- `final-state-cleanup`
- `production-hardening`

## Completed Work This Session

### 1. Packaging and portability hardening

Implemented/fixed:

- MIT `LICENSE`.
- `pyproject.toml` uses SPDX-style `license = "MIT"`.
- `package-data` includes `core/config_defaults.yaml` in wheel.
- `.gitignore` added for build/cache artifacts.
- Fresh wheel build worked.
- Fresh venv smoke passed.
- `agency doctor` passed.

### 2. Config-first secrets

Implemented/fixed:

- `AdapterEntryConfig.api_key` direct field.
- `AdapterEntryConfig.resolve_api_key()`.
- `JudgeConfig.resolve_api_key()` direct key first, env var second.
- `config_to_yaml()` redacts direct keys.
- `_normalize_enabled()` handles YAML booleans (`true`/`false`) correctly.
- Doctor uses authenticated provider checks where needed.
- Local config migrated from env-var-only to direct key in `agency.yaml`.

### 3. LiteLLM-independent routing

Implemented/fixed:

- `pre_llm_call_handler` always injects routing context for non-trivial turns.
- Judge fallback does not assume LiteLLM; provider chain works without it.
- Token-only fallback remains final always-available route.

### 4. Multi-provider fallback chain

Implemented/fixed:

- `ProviderEntry` config model.
- `AgencyConfig.providers` list.
- YAML parser for providers.
- `judge.py` tries each provider in order.
- Backward compatibility with legacy `judge` config.
- Doctor reports provider chain.
- Detection/configure generates provider list from detected LiteLLM/OpenAI/Anthropic/Ollama.
- Tests increased from 98 to 104.

### 5. Repo creation and push

Important correction: the repo was first created under the personal account `holeshotclaw/agency-runtime`, but Lucas expected the org.

Correct repo now:

```text
https://github.com/Holeshot-Software-LLC/agency-runtime
```

Local remote is set to the org repo.

The personal repo deletion attempt failed because the GitHub token lacks `delete_repo` scope:

```text
HTTP 403: Must have admin rights to Repository.
This API operation needs the "delete_repo" scope.
```

Next session can either ignore the personal repo or ask Lucas to grant/delete it manually if needed.

### 6. Install/toggle and README

Implemented/fixed:

- `agency install --all`
- `agency install --agent <hermes|openclaw|codex|claude>`
- `agency install` for standalone roster seeding.
- `agency on --agent <host>`
- `agency off --agent <host>`
- `agency_runtime/core/installer.py`
- Comprehensive README.

Live smoke:

```bash
agency install --all
# Detected 3 host(s): hermes, openclaw, codex
# Wrote plugin files for all three.

agency off --agent codex
agency on --agent codex
# Passed.
```

## Known Caveats / Remaining Work

### Highest priority: host-specific install truth

The installer currently writes plugin scaffolds for Codex and Claude, but actual Codex/Claude plugin loading has not been proven. Before public release:

1. Verify whether Codex supports loading a plugin from `~/.codex/agency-preflight/__init__.py`.
2. Verify whether Claude Code supports loading a plugin from `~/.claude/agency-preflight/__init__.py`.
3. If not, replace the scaffolds with the real integration mechanism:
   - wrapper command,
   - ACP integration,
   - config injection,
   - MCP server,
   - shell hook,
   - or documented unsupported status.
4. Update README to distinguish `verified`, `experimental`, and `planned` hosts.

Do not market Codex/Claude as fully integrated until that is actually verified.

### Slash command support

Lucas wants:

```text
/agency on
/agency off
```

Current implementation is CLI only:

```bash
agency on --agent hermes
agency off --agent hermes
```

Need to implement slash-command/chat-command handling in supported hosts. Likely route:

- Hermes plugin intercepts user message `/agency on` or `/agency off`.
- Plugin calls `toggle_agency(host, enabled)` or toggles runtime flag.
- But beware: if `/agency off` disables the plugin by renaming itself, the active process may keep it imported until restart. Need a runtime enabled flag in config/store or host hook short-circuit, not just file rename, for immediate effect.
- File rename is still useful for restart-persistent disable.

Recommended design:

1. Add `runtime.enabled_by_host.<host>` or `adapters.<host>.enabled` control in config/store.
2. `pre_llm_call_handler` checks host enabled state and returns `None` if disabled.
3. Slash command updates that state and returns a confirmation.
4. CLI `agency on/off` can use the same state plus optional plugin file rename.

### Configure wizard needs robust fallback priority editor

Current detection writes a provider list, but the wizard should become more like OpenClaw configure:

- Show detected providers.
- Ask the user to order fallback priority.
- Support direct API key storage in config.
- Support env var references.
- Support custom OpenAI-compatible endpoints.
- Support LiteLLM model group selection.
- Support Ollama model selection.
- Detect Claude/Codex CLI/OAuth where possible.
- Validate each provider in order and show failures clearly.
- Write config with `0600` permissions.
- Print exact next commands.

### OAuth / CLI providers

`ProviderEntry.type = "cli"` and `auth_method() == "oauth"` exist conceptually, but actual Claude OAuth / OpenAI OAuth / Codex CLI calls are not implemented as judge providers.

Need to decide whether provider chain should call:

- direct HTTP APIs only,
- CLI wrappers,
- LiteLLM as the OAuth bridge,
- Codex/Claude ACP transports,
- or MCP/server sidecars.

Do not claim OAuth support publicly until implemented and tested.

### Public install instructions

README says:

```bash
pip install agency-runtime
```

If package is not on PyPI yet, change public quickstart to:

```bash
pip install git+https://github.com/Holeshot-Software-LLC/agency-runtime.git
```

or publish to PyPI first.

### Tests needed

Add tests for:

- `installer.detect_installed_agents()` using temp HOME / monkeypatch for paths/binaries.
- `install_agent_adapter()` writes expected plugin content.
- `toggle_agency()` renames active/disabled files safely.
- `agency install --all` CLI with mocked detection.
- `agency on/off` CLI with mocked host detection.
- Provider fallback order with one failing fake HTTP provider and one succeeding fake provider.
- Doctor provider chain output for available/unavailable providers.
- Slash command support once implemented.

### Docs needed

README is much better, but public release needs additional files:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `docs/install.md`
- `docs/configuration.md`
- `docs/host-integrations.md`
- `docs/provider-fallbacks.md`
- `docs/architecture.md`
- `docs/troubleshooting.md`

### Branding / market polish

Lucas asked for marketable branding. Current README is functional but could be more visually branded.

Possible branding direction:

- Tagline: "The control plane for specialist AI agents."
- Promise: "Route, verify, and audit every agent turn."
- Key differentiators:
  - portable across hosts,
  - provider independent,
  - actual model receipts,
  - specialist roster governance,
  - audit headers.

Need a logo/banner later.

## Commands to Run When Picking Back Up

```bash
cd /home/holeshot/agency-runtime

git status --short
git remote -v
git log --oneline -12

python3 -m pytest tests/ -q
agency doctor
agency install --all
agency off --agent codex
agency on --agent codex
```

If changing installer behavior, run a temp-home smoke instead of mutating live config where possible:

```bash
TMP_HOME=$(mktemp -d)
HOME="$TMP_HOME" python3 -m agency_runtime.cli.main configure --non-interactive --profile local-only --force
HOME="$TMP_HOME" python3 -m agency_runtime.cli.main install --all
HOME="$TMP_HOME" python3 -m agency_runtime.cli.main doctor
```

Need to create fake host dirs in `TMP_HOME` for installer tests.

## Suggested Next Work Plan

1. **Add installer tests.** Current installer was live-smoked but not covered by tests.
2. **Clarify host support matrix.** Verify Codex/Claude actual integration or mark as experimental.
3. **Implement runtime `/agency on` and `/agency off`.** Use config/store flag for immediate process-level disable; file rename alone only affects restart.
4. **Improve configure wizard.** Add provider priority editor and custom endpoint flow.
5. **Fix README install claim if not on PyPI.** Use GitHub install until publish.
6. **Add public-release docs.** CONTRIBUTING, SECURITY, CHANGELOG, docs/ pages.
7. **Run final cleanup/hardening.** Remove any unverified claims before making public.

## Critical Pitfalls To Avoid

- Do not reintroduce SpendLog queries for actual model resolution. Use API response body.
- Do not make LiteLLM required. It is optional.
- Do not claim Codex/Claude integration is fully working until real host loading is verified.
- Do not put secrets in README, commits, logs, or final messages.
- Do not write `Agency/Agencies loaded: none` on non-trivial turns; load a specialist.
- Do not preserve compatibility shims. The portable package is the live system.
- Do not downgrade planner/fallback model aliases to plain model strings without debugging the configured alias/tag path.

## Current Final-State Contract

The intended final state for the project is:

- A pip-installable package named `agency-runtime`.
- Config-first control via `~/.agency-runtime/agency.yaml`.
- Provider-independent judge fallback chain.
- SQLite store for roster, receipts, skills, specialists, delegation events.
- Thin host adapters that import from the installed package.
- One-command install into all detected hosts.
- One-command install into one selected host.
- On/off toggles from CLI now; slash-command toggles later.
- Public-ready README and MIT license.
- Tests proving config/provider/install behavior.

## Last Known Verification

Before this handoff file:

```text
104 passed in 12.08s
agency install --all: detected hermes, openclaw, codex; wrote plugin files
agency off --agent codex: passed
agency on --agent codex: passed
origin push: main -> Holeshot-Software-LLC/agency-runtime
```

After creating this handoff file, rerun tests and commit/push the file.
