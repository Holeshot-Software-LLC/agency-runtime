---
title: "Agency Runtime"
status: active
category: overview
created: 2026-07-08
updated: 2026-07-24
tags: [agents, routing, delegation, dashboard]
related:
  - CONTRIBUTING.md
  - SECURITY.md
  - docs/TROUBLESHOOTING.md
supersedes: []
superseded_by: null
---

<p align="center">
  <img src="docs/assets/agency-runtime-icon.svg" alt="Agency Runtime" width="120" height="120"/>
</p>

<h1 align="center">Agency Runtime</h1>

<p align="center">Give your coding agent a bench of 263 audited specialists — without bloating every conversation into a giant prompt.</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"/></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue.svg"/>
  <img alt="Specialists" src="https://img.shields.io/badge/specialists-263-6366f1.svg"/>
  <img alt="Hosts" src="https://img.shields.io/badge/hosts-5-38bdf8.svg"/>
  <img alt="Status: prerelease" src="https://img.shields.io/badge/status-prerelease-orange.svg"/>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-windows%20%7C%20linux-lightgrey.svg"/>
</p>

For each request, Agency Runtime understands the work, searches an audited
roster of specialists, and gives your host (Codex, Claude Code, ZCode, Hermes,
or OpenClaw) a focused delegation plan. The chosen specialist's instructions
apply to that turn or child task and then leave the active context — your main
agent stays small.

**You get:**

- 🔭 **Inference-first selection** — when a provider is configured, an intent
  planner decomposes the ask and a recruiter picks the best eligible specialist
  per work unit (or declares a real gap and hires a contractor).
- 🧮 **Works offline too** — no provider? Agency falls back to a deterministic
  typed-recall floor (a best typed-guess), stamped so it's never mistaken for an
  inference pick. Configure a provider for intent-aware selection.
- 🧬 **Specialists bind into subagents** — when your host spins up a child, the
  exact audited specialist is injected for that one task with a one-use
  activation receipt.
- 🧑‍💼 **Hires contractors on real gaps** — if no specialist fits, Agency
  compiles, audits, and admits a least-privilege contractor in the same turn.
- 📊 **Local dashboard + CLI** — live routing activity, model receipts,
  workforce lifecycle, and on/off controls.
- 🪟 **Windows and Linux**, five native hosts.

> Agency Runtime is prerelease software. Install it from this repository; no
> public package release is claimed yet.

---

## 🎯 Why

A single generalist agent can't be the best at everything, but loading every
specialist's full prompt into every turn balloons context and degrades the
model. Agency Runtime is the middle path: a **company** of narrow audited
specialists that your main agent recruits per turn.

- **Per-turn best-specialist selection** across the whole enabled roster, not a
  fixed prompt.
- **Inference reads intent** — it picks the specialist for *this* ask (e.g. a
  Git-workflow specialist for "design a branching strategy") that keyword
  matching could never find.
- **Gaps hire contractors in-turn** — a real uncovered capability compiles and
  admits a governed contractor immediately.
- **Stays small** — specialist instructions are turn-/task-scoped and return to
  the pool; they don't accumulate in your main agent's context.
- **Honest evidence** — every response carries a stamped header showing what
  loaded, what model ran, and **how the specialist was recruited**.
- **Proves its value** — release requires measured Agency-on vs Agency-off
  outcome lift on the same host and model (tracked, not yet claimed).

---

## 🧒 How it works (ELI5)

Imagine your main agent has a company directory of 263 specialists.

1. You ask the main agent for something.
2. Agency classifies the turn — new task, follow-up, approval, control command,
   or ordinary conversation.
3. It **plans** the work into typed units (no agent names yet).
4. It **recalls** every approved, enabled specialist that could plausibly fit
   (typed contract fields: artifact, lifecycle, domain, stack, capability,
   authority).
5. The **recruiter** (inference, when configured) picks the best eligible
   specialist per unit — or declares a real gap. Offline, a deterministic
   typed-recall floor makes a best typed-guess.
6. If two specialists would conflict, Agency separates their work instead of
   putting both in one prompt.
7. Small focused work loads into the current turn; larger or independent work is
   delegated through the host's native subagent mechanism with the exact
   specialist bound in.
8. Agency records what really loaded, delegated, and the model evidence.
9. The response shows that evidence in a compact header. On the next request,
   specialists return to the pool.

A small permanent coordination pair (Agents Orchestrator + Chief of Staff) stays
resident. They do not replace domain specialists.

```mermaid
flowchart LR
    U["Your request"] --> T["Classify turn"]
    T --> P["Plan typed work units"]
    P --> R["Recall typed specialists"]
    R --> D{"Inference configured?"}
    D -- yes --> RC["Recruiter picks best / declares gap"]
    D -- no --> DF["Deterministic typed-recall floor"]
    RC --> G{"Real gap?"}
    G -- yes --> H["Hire contractor"]
    G -- no --> V["Verify team"]
    DF --> V
    H --> V
    V --> L["Load focused help"]
    V --> ND["Delegate via native subagent (exact specialist bound)"]
    L --> E["Record evidence"]
    ND --> E
    E --> HDR["Response header (Recruited via: ...)"]
    HDR --> POOL["Specialists return to the pool"]
```

---

## 🔌 Supported hosts

| Host | Integration | Native delegation primitive | Specialist injection | Canary |
|---|---|---|---|---|
| **Codex** | Hooks + MCP + controls | `spawn_agent` | Hook envelope (PreToolUse bind → one-use receipt) | ✅ |
| **Claude Code** | Hooks + MCP + controls | `Agent` | Hook envelope (PreToolUse bind → one-use receipt) | ✅ |
| **ZCode** | Hooks + controls | `Agent` (Claude-like) | Hook envelope (PreToolUse bind → one-use receipt) | planned |
| **Hermes** | Python plugin + MCP | `delegate_task` | MCP-plugin context framing | ✅ |
| **OpenClaw** | JavaScript plugin | `sessions_spawn` | MCP-plugin context framing | ✅ |

All hosts have deterministic Windows and Linux contract coverage. **Live status
is reported separately** — a copied plugin directory is never proof a host loaded
it. Run `agency doctor --json` to see what is installed and verified.

> **ZCode note:** ZCode reuses the Claude hook model and `Agent`-tool primitive,
> so it's first-class for main-session routing. ZCode **native children are
> host-limited**: ZCode does not emit `SubagentStart`/`SubagentStop`, so governed
> native-child self-routing can't fire for ZCode children yet (tracked, gated on
> host support). Main-session specialist binding works.

---

## 🧬 How a specialist gets into a subagent

Your host keeps its own scheduler. Agency doesn't replace it — it binds the exact
audited specialist into the child for that one task. There are two mechanisms:

### Hook hosts (Codex, Claude Code, ZCode)

When the host invokes its native delegation tool (`spawn_agent` / `Agent`), a
`PreToolUse` hook resolves the one persisted assignment for that child, verifies
the goal matches the plan, and injects the specialist's exact versioned prompt as
an `[AGENCY EXACT SPECIALIST ACTIVATION v1]` envelope into the child's task
input. After the host proves it executed the launch, a `PostToolUse` hook
**consumes the one-use activation receipt** — it can't be replayed. Payloads are
byte-budgeted (64 KiB) and never silently truncated.

```mermaid
sequenceDiagram
    participant Host
    participant Hook as Agency PreToolUse hook
    participant Store as Evidence store
    participant Child as Native child
    Host->>Hook: invoke spawn_agent / Agent (goal)
    Hook->>Store: resolve one persisted assignment
    Store-->>Hook: exact specialist + version
    Hook-->>Host: allow + rewritten input (specialist envelope)
    Host->>Child: launch with specialist prompt bound
    Child-->>Host: result
    Host->>Hook: PostToolUse (launch evidence)
    Hook->>Store: consume one-use receipt
```

### MCP-plugin hosts (Hermes, OpenClaw)

These hosts deliver the specialist as prompt-context framing through a subprocess
backend (`delegate_task` / `sessions_spawn`), and record child lifecycle via
explicit `native_child_started` / `native_child_ended` bridge actions.

---

## 🧑‍💼 Recruiter, gaps, and contractor hiring

When a provider is configured, selection is inference-first:

1. **Plan** — one compact inference call decomposes the ask into typed work units
   (outcome, artifact, lifecycle, domain, stack, capabilities, authority,
   dependencies).
2. **Recall** — deterministic, zero-false-negative typed recall reduces the whole
   workforce to the plausibly-relevant specialists.
3. **Recruit** — the recruiter (one bounded inference call over the recall
   shortlist) nominates the best eligible specialist per unit — `required`,
   `acceptable`, or `forbidden` — or declares a real gap.
4. **Verify** — deterministic code validates eligibility, composition, coverage,
   and budget around the model's trusted nomination.
5. **Gap → hire** — if no specialist covers a unit, Agency hires a contractor.

### Contractor hiring (`hire_contractor_for_gap`)

A declared gap is a contractor specification. Agency:

- **Compiles** a structured contract through a fixed, security-reviewed prompt
  template (never an unrestricted model-written system prompt).
- **Criticizes** it with an independent hiring-critic inference pass.
- **Risk-tiers** it and runs deterministic Unicode / injection / exfiltration /
  authority / tool / conflict / duplicate checks.
- **Admits** the worker as a least-privilege, visibly-marked probationary
  contractor tied to the agency origin (`origin="agency"`,
  `employment="contractor"`), with a one-use activation receipt.
- High-risk domains still require explicit human approval.

Contractors follow the **same audited, versioned, composition-bound path** as
employees. **Promotion to employee is human-controlled** — an operator must act,
and only after independently-verified successful assignments.

---

## 🧪 What gets routed for an ask

Agency reads the **intent** of the ask and the **detected stack/domain** to
pick specialists — it doesn't keyword-match. The same phrasing routes to a
different specialist depending on the repository context, and a single ask often
decomposes into a multi-specialist team. *(Representative — actual picks depend
on the detected stack and the live roster.)*

**Same ask, different specialists by context:**

| Ask (with context) | Recruited via | Specialist |
|---|---|---|
| "fix the auth bug" — in a Python repo | inference | `python-application-engineer` |
| "fix the auth bug" — in a TypeScript repo | inference | `typescript-application-engineer` |
| "fix the auth bug" — in a Go repo | inference | `go-application-engineer` |

The router reads the repository's stacks, not the literal words.

**One ask → a governed multi-specialist team (sequential units):**

| Ask | Recruited via | Team decomposition |
|---|---|---|
| "Review this code for correctness and security" | inference | `code-reviewer` + `ai-generated-code-security-auditor` |
| "Design a Git branching strategy" | inference | discovery → design → implement → review → test, incl. `git-workflow-master` |
| "Build a FluxUI dashboard" | inference | `senior-developer` (owns FluxUI/Livewire/Laravel) |
| "Investigate and contain this production incident" | inference | discovery → analysis → recovery plan → operations |

**No provider configured?** Agency falls back to a deterministic typed-recall
floor (stamped `Recruited via: deterministic`) — a best typed-guess specialist
rather than nothing. Configure a provider for the intent-aware picks above.

Try it yourself on your own repo:

```bash
agency route "review this authentication design and propose tests"
agency explain "review this authentication design and propose tests"
```

---

## 🤖 Configure inference

Agency works without a provider (deterministic typed-recall floor). Configure one
for intent-aware selection.

```bash
agency configure          # guided setup
agency config show
agency config validate
```

**Ways to configure inference:**

- **Codex CLI / subscription reuse** — reuse an authenticated Codex session;
  exposes the account-visible model and reasoning levels (`low` is usually
  enough for the compact plan and reduces latency).
- **OpenAI-compatible endpoint** — any local or remote OpenAI-compatible API
  (e.g. `http://127.0.0.1:1234/v1`).
- **LiteLLM router** — enter the router/model-group alias exactly (e.g.
  `task-agency-router`).
- **Ordered fallback chain** — providers tried in order; the first healthy one
  serves the turn.

```yaml
providers:
  - name: codex-cli
    type: cli
    transport: codex
    model: ""
    reasoning_effort: low
    timeout: 60
  - name: local-compatible
    type: openai-compatible
    model: local-model
    base_url: http://127.0.0.1:1234/v1
    timeout: 15
```

```bash
agency config provider set codex-subscription --type cli --transport codex --model gpt-5.6-luna --reasoning-effort low --timeout 60
agency config provider set office-router --type litellm --model task-agency-router --base-url http://127.0.0.1:4000/v1
agency config set judge.model qwen3.5:2b
agency config set delegation.child_inference_budget 4
```

If a configured chain is unavailable, Agency reports selection is degraded
rather than pretending deterministic candidates were model-selected.

Default files: config `~/.agency-runtime/agency.yaml`, database
`~/.agency-runtime/agency.db`, global switch `~/.agency-runtime/run/control.json`.
Use `AGENCY_CONFIG_PATH` / `AGENCY_DB_PATH` to relocate.

---

## 📦 Install

Python 3.10+.

```bash
git clone https://github.com/Holeshot-Software-LLC/agency-runtime.git
cd agency-runtime
python -m pip install .

agency --version
agency install --all --dry-run
agency doctor
```

This unreleased source currently keeps every persistent setup and control
mutation fail-closed because its production OS-backed operator-presence verifier
has not been implemented. Dry runs, status, diagnostics, routing, and the
read-only dashboard remain available; positive `configure`, `install`, service,
host, agent, and retention mutations return a controlled unavailable result.
Do not substitute a static confirmation, bearer token, environment variable, or
model-callable credential for genuine operator presence. See
[AR-143](docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md).

After that release blocker is implemented, the installer will discover
supported hosts and register only the ones it can identify. It does not restart
a host automatically.

**Codex** will also require you to approve command hooks: Agency installs the plugin,
reports `activation_required`, and gives the exact next step. Run `codex`,
choose **Trust all and continue** at the startup hook review (or `/hooks` inside
the terminal UI and trust the Agency events), then:

```bash
agency install --agent codex --verify-activation
```

The intended post-gate install and rollback commands include ZCode:

```bash
agency install --agent zcode
agency install --agent codex --rollback
```

When positive installation is enabled, the dashboard installs by default as a
per-user service (no admin access). `agency install --all --no-dashboard` omits
it. Managed files and backups live under `~/.agency-runtime/`.

---

## 🛠 Everyday commands

```bash
agency status                 # system + host status
agency doctor --json          # what's installed and verified
agency smoke --all --json     # canary readiness check (see 🩺 below)
agency agents list            # roster
agency roster list

agency search "incident response"
agency route "review this authentication design"
agency explain "review this authentication design" --session-id demo
agency eval routing --json --no-details
```

Inspect the persistent host and global states without changing them:

```bash
agency status --agent codex
agency status
agency off --agent codex --dry-run --json
```

The data contracts retain reversible host, global, and per-agent controls, but
positive CLI mutations remain unavailable until AR-143 has a production
operator-presence backend. The dashboard and every model-facing surface are
read-only. `agents-orchestrator` and `chief-of-staff` remain the protected
coordination pair.

---

## 📊 Operations dashboard

The optional local dashboard shows live routing, delegation, provider health,
model receipts, host status, roster and workforce evidence, and recent turns.
It is a local-only, bounded, read-only observability surface; every former
mutation endpoint rejects both owner and broker bearers. See
[ADR-0096](docs/decisions/0096-require-operator-presence-for-persistent-controls.md).

---

## 🔍 Response header

Every Agency response starts with an evidence header — a truth-receipt, not
marketing:

```text
Agency/Agencies loaded: code-reviewer
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: gpt-5.6-luna -> codex/gpt-5.6-luna
Recruited via: inference
Why: Security review requested for auth code
How it shaped outcome: Loaded code review + security auditor
```

The **`Recruited via`** line is machine-stamped (`inference`, `deterministic`,
`cached`, or `none`) — distinct from the model-authored `Why`. It tells you at a
glance how the specialist was actually selected, including when the offline
typed-recall floor fired.

---

## 📂 Roster & the upstream project

Agency Runtime ships a **263-specialist audited roster** sourced from an
upstream open-source specialist-pool project (MIT, pinned revision). Credit and
thanks to that project — the audited pool of specialists is the upstream asset
worth borrowing. (Provenance — repository, exact revision, and license — is
recorded in the bundled roster manifest and in [LICENSE](LICENSE).)

- The roster is the community-sync asset, **not** a selector. Agency Runtime uses
  its own inference-first router; it does not vendor the upstream selector.
- Pull in deltas: `agency source add <path> --name ...` then
  `agency roster upstream import --source-revision <rev>`. **Import only
  quarantines the delta** — it never approves or activates.
- New agents become selectable only after a separate **audit → approval →
  activation** step, so nothing enters the live roster unreviewed.
- A nightly workflow runs the upstream delta audit and publishes review evidence.
- Enrichment (`scripts/enrich_workforce_contracts.py`) regenerates typed
  `stacks`/`domains` and user-facing `scope_qualifiers` for the roster so the
  deterministic verifier scores real stack coverage.

---

## 🔐 Privacy and security

Agency runs locally; the dashboard is local-only. Specialist prompts are
turn-/task-scoped and don't accumulate. See
[SECURITY.md](SECURITY.md) and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for
vulnerability reporting, trust boundaries, and enforced controls.

---

## 🩺 Canaries

A **canary** is an isolated, non-mutating readiness smoke that proves the
*installed* runtime actually fires end-to-end on a real host. Tests run in pytest
with stubs; a canary catches what tests can't — a broken hook registration, a
wrong config path, or a provider that times out. It refuses to claim success
without explicit confirmation before any live backend call.

```bash
agency smoke --agent codex --json
agency smoke --all --json
```

---

## 🧯 Troubleshooting & development

- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — host maturity, MCP,
  LiteLLM, dashboard, and platform diagnostics.
- [CONTRIBUTING.md](CONTRIBUTING.md) — setup, implementation boundaries,
  validation.
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) — release gates.

## License

[MIT](LICENSE) — roster specialists sourced under MIT from the upstream
specialist-pool project.
