---
title: "Agency Runtime"
status: active
category: overview
created: 2026-07-08
updated: 2026-08-12
tags: [agents, routing, delegation, dashboard]
related:
  - CONTRIBUTING.md
  - SECURITY.md
  - THIRD_PARTY_NOTICES.md
  - docs/TROUBLESHOOTING.md
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/decisions/0136-bind-opaque-codex-execution-by-ciphertext-identity.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
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

For each request, Agency Runtime uses inference to decompose the staffing need
and identify the expertise an exacting owner would want from an unlimited
specialist pool. It then selects faithful audited specialists or, for a real
gap, designs, audits, and hires a narrow contractor. This is a staffing
decision, not an execution plan: the native host alone decides whether to
spawn children, what they do, and how it completes the request. When a host
does start a child, Agency's supported integrations are designed to attach
request-scoped specialist cards and correlate the host's own evidence. Only a
host-written artifact containing the exact delivered card hashes before the
child's first speech proves that delivery. The cards leave the active context
with the request, so your main agent stays small.

> **Doctrine note (2026-08-05).** Earlier revisions treated any near-match as
> a mandatory gap and let deterministic coverage checks veto inference-chosen
> teams. In practice that made refusal the default outcome: the models picked
> the right specialists and the machinery abstained. The doctrine is now
> staff-first — deterministic verification annotates the receipt (coverage
> limits, missing independent assurance) instead of vetoing a staffed team,
> and only the safety screens (injection, authority escalation, high-risk
> hiring approval) hard-block.

**You get:**

- 🔭 **Inference-owned staffing** — inference decomposes the ask into bounded
  staffing needs, defines the ideal expertise from an open-ended role pool, and
  then either reuses a faithful roster match or declares a real gap. It does
  not tell the host what child tasks to create or in which order to run them.
- 🚨 **Fails honestly, never locks you out** — deterministic code can recall and
  validate candidates, but it never chooses a specialist. A substantive turn
  without a valid inference decision selects nobody, reports the exact cause
  (recruiter abstention, safety rejection, provider failure), and lets the host
  answer as a generalist with a `Recruited via: none` header rather than
  blocking you out of the agent.
- 🧬 **Request-scoped specialist cards** — when a supported host starts a
  child, Agency can bind audited specialist cards to that host-owned child for
  the request and record the resulting host-written evidence.
- 🧑‍💼 **Hires contractors on real gaps** — if no specialist fits, Agency
  compiles, audits, and admits a least-privilege task specialist in the same
  turn; it does not stretch a near-match into a generalist.
- 📊 **Local dashboard + CLI** — staffing decisions, model receipts,
  workforce lifecycle, bounded delegation-event rows, and owner controls.
- 🪟 **Windows and Linux**, five native hosts.

> Agency Runtime is prerelease software. Install it from this repository; no
> public package release is claimed yet.

> **Nine-rule completion is not claimed.** The current matrix records Rule 1
> negative on Claude, Codex, and ZCode because the JIT path can still alter the
> inference choice; Rule 8 source-negative on Hermes and OpenClaw; and the
> mixed Rule-4 state shown below. AR-255 and the other P0 matrix repairs must
> land before these intended behaviors become a cross-host product claim.

---

## 🎯 Why

A single generalist agent can't be the best at everything, but loading every
specialist's full prompt into every turn balloons context and degrades the
model. Agency Runtime is the middle path: a **company** of narrow audited
specialists that your main agent recruits per turn.

- **Per-turn ideal-specialist selection** from an open-ended inference pool;
  the enabled roster is a reusable cache, not the limit of available expertise.
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

Imagine your main agent can staff from an unlimited catalog of possible roles,
with 263 audited specialists already on payroll.

1. You ask the main agent for something.
2. Agency classifies the turn — new task, follow-up, approval, control command,
   or ordinary conversation.
3. It builds a bounded **staffing decomposition**: the intended outcome,
   artifact, lifecycle, domain, stack, capabilities, and authority needed for
   the request. This identifies expertise; it is not a plan telling the host
   which children to start or how to execute them.
4. It **recalls** a bounded, coverage-first sample of enabled specialists that
   could plausibly fit (typed contract fields: artifact, lifecycle, domain,
   stack, capability, authority — up to 24 candidates per staffing need, including
   untyped wildcard workers). Recall lists unapproved workers with their
   ineligibility flagged; approval is hard-enforced later, at verification,
   where an unapproved worker can never execute.
5. The **recruiter** uses inference to staff faithful roster specialists —
   staff-first: imperfect typed coverage annotates the receipt rather than
   blocking the pick. A gap is declared only when no supplied specialist is
   semantically appropriate, and a gap hires. If inference is unavailable or
   invalid, the turn fails open: no specialist is selected, the exact cause is
   reported, and the host can answer as a generalist with a `Recruited via:
   none` header.
6. Compatibility rules keep conflicting specialists and unsafe authority or
   context combinations out of the same staffing set.
7. The **host owns execution**. It may use its native child mechanism or
   continue without spawning; Agency neither requires dispatch nor blocks the
   parent waiting for it. For a host-started child, supported integrations bind
   the request's specialist card(s) and correlate the child identity.
8. Agency records the staffing decision and model evidence; child-start and
   card-delivery proof come from host-written events, not from a planned
   delegation claim.
9. The response shows that evidence in a compact header. On the next request,
   specialists return to the pool.

One compact Agency-native `agency-steward` stays resident to bind outcome,
scope, and evidence. It is infrastructure, not a worker: it cannot select,
execute, review, or answer substantive work. Imported `agents-orchestrator` and
`chief-of-staff` remain ordinary optional roster specialists selected only when
their audited activation contracts fit.

```mermaid
flowchart LR
    U["Your request"] --> T["Classify turn"]
    T --> P["Infer staffing decomposition"]
    P --> I["Infer ideal expertise from open-ended pool"]
    I --> R["Recall typed roster matches"]
    R --> D{"Inference decision valid?"}
    D -- yes --> RC["Accept faithful match / declare gap"]
    D -- no --> DF["Fail open: generalist + Recruited via: none"]
    RC --> G{"Real gap?"}
    G -- yes --> H["Hire contractor"]
    G -- no --> V["Validate staffing set"]
    H --> V
    V --> C["Create request-scoped specialist cards"]
    C --> E["Host chooses execution and writes child evidence"]
    E --> HDR["Response header (Recruited via: ...)"]
    HDR --> POOL["Specialists return to the pool"]
```

---

## 🔌 Supported hosts

| Host | Integration | Host-native child primitive | Rule-4 exact-candidate state |
|---|---|---|---|
| **Codex** | Hooks + MCP + controls | `spawn_agent` | **negative in source, installed/live unproven**: the current adapter cannot carry cards through the encrypted context channel; prior-candidate TUI, Desktop, and exec children received no card |
| **Claude Code** | Hooks + MCP + controls | `Agent` | **unproven**: three host-authored prior-candidate artifacts contain cards before speech, but none binds the exact candidate |
| **ZCode** | Hooks + controls | `Agent` (Claude-like) | **unproven** |
| **Hermes** | Python plugin + MCP | `delegate_task` | **unproven** |
| **OpenClaw** | JavaScript plugin | `sessions_spawn` | **unproven** |

Contract and simulation coverage is not live completion evidence. The
[AR-119 rule/host matrix](docs/roadmap/AR-119-rule-host-evidence-matrix.md) is
the sole current completion projection and requires the same behavior on all
five hosts. A copied plugin directory, an Agency Store row, or an unavailable
host never becomes proof. Run `agency doctor --json` to inspect local install
and verification state without promoting it to a live-delivery claim.

> **ZCode note:** ZCode reuses the Claude hook model and `Agent` tool for
> host-owned child work. It does not emit `SubagentStart`/`SubagentStop`, so the
> child-identity and stop evidence available on Claude/Codex is not available
> there. That limits what Agency can prove; it does not authorize Agency to
> schedule or dispatch a child.

---

## 🧬 How request-scoped specialist cards reach host-started children

Your host keeps its own scheduler. Agency does not produce a child-execution
plan, ask the host to dispatch one, or wait for a dispatch before allowing the
parent to continue. It supplies a staffing decision for the request. If the
host independently starts a child, a supported integration may attach one or
more exact-version specialist cards to that host-owned child.

For hook hosts (Codex, Claude Code, ZCode), the integration observes the host's
native child-tool lifecycle and binds the card only when its own correlation
checks succeed. For MCP/plugin hosts (Hermes, OpenClaw), the host bridge frames
the cards and emits native-child lifecycle events. The card is request-scoped:
it is not a standing worker prompt, a child-task instruction, or permission for
Agency to run a second dispatch.

```mermaid
sequenceDiagram
    participant Host
    participant Agency
    participant Store as Evidence store
    participant Child as Host-started child
    Host->>Agency: request reaches preflight
    Agency->>Store: record staffing decision and card identity
    Host->>Host: choose whether and how to execute
    opt Host starts a child and correlation succeeds
        Host->>Agency: native child lifecycle event
        Agency->>Child: request-scoped specialist card(s)
        Host->>Host: write child artifact with exact card hashes
        Agency->>Store: index the observed host artifact
    end
    Host->>Agency: natural response / finalization evidence
```

Only host-written, correlated artifacts establish that a child was staffed.
An Agency staffing decision, a selected roster card, or a generic child event
alone is not proof of execution. If evidence is missing or cannot be correlated,
Agency reports that limitation rather than inventing a dispatch or a successful
specialist run.

---

## 🧑‍💼 Recruiter, gaps, and contractor hiring

Selection is inference-owned; host execution is not:

1. **Decompose for staffing** — one compact inference call describes the typed
   staffing needs for the ask (outcome, artifact, lifecycle, domain, stack,
   capabilities, authority). It does not create a host execution sequence.
2. **Define the ideal** — inference asks who an exacting owner would want for
   each staffing need if the possible-role pool were unlimited. The parent model is
   structurally excluded (it has no roster identity a nomination can name);
   the recruiter and critic are instructed never to stretch a generalist into
   the role, though that half is a prompt rule, not a deterministic gate.
3. **Recall** — deterministic typed recall returns a bounded, coverage-first
   sample of plausibly relevant audited workers without ranking or choosing
   them; an empty result remains valid.
4. **Recruit** — the recruiter explicitly decides `staff` or `gap` per staffing
   need and
   classifies only faithful roster candidates as `required`, `acceptable`, or
   `forbidden`. Staff-first: any faithful candidate staffs; a gap is reserved
   for genuinely missing specialties and may contain no roster candidate at
   all.
5. **Verify** — deterministic code validates eligibility, composition, coverage,
   and budget around the model's decision. Hard failures (ineligible workers,
   empty teams, forbidden conflicts, budget) abstain; advisory findings such as
   missing independent assurance are recorded on the accepted receipt instead
   of vetoing the staffed team. A contradictory `staff` or `gap` result gets
   one bounded inference repair; code does not silently reverse it.
6. **Gap → hire** — only an explicit gap with verifier-confirmed safe no-team
   evidence enters independent whole-workforce contractor analysis. Declined
   analysis does not consume the task's applied-hire allowance.

### Contractor hiring (`hire_contractor_for_gap`)

A declared gap is a contractor specification. Agency:

- **Compiles** a structured contract through a fixed, security-reviewed prompt
  template (never an unrestricted model-written system prompt).
- **Criticizes** it with an independent hiring-critic inference pass. If that
  critic rejects a deterministically valid proposal and at least two calls
  remain in the hiring budget, one complete inference-authored replacement
  runs with a fresh independent critique; a second rejection remains terminal.
- **Risk-tiers** it deterministically: injection / policy-override pattern
  screens, invisible and bidirectional Unicode rejection, denial-aware
  high-risk domain markers (legal, medical, financial, destructive, approval,
  credential, offensive security, exfiltration), and conflict / duplicate
  checks. The isolated inference security reviewer remains the safety gate on
  contract content.
- **Admits** the worker as a least-privilege, visibly-marked probationary
  contractor tied to the agency origin (`origin="agency"`,
  `employment="contractor"`), with immutable identity and request-scoped
  admission evidence.
- **Keeps roles narrow** — ordinary task staffing creates the exact missing
  specialist instead of expanding a near-match into a broad generalist.
- A contract asserting an owner-gated high-risk domain class is persisted as a
  high-tier case that stops before registration: no worker exists until an
  explicit `agency hiring approve` (or the dashboard approval) records the
  owner's decision. Externally mutating scope alone stays reviewer-gated
  (AR-238) rather than owner-gated.

Contractors follow the **same audited, versioned, composition-bound path** as
employees. **Promotion to employee happens two ways.** The owner can promote
any active contractor at any time through the CLI or dashboard transition
action, informed by the surfaced promotion-readiness projection. Separately, a
policy-based automatic promotion fires after
`workforce.auto_promote_successes` (default 3) assignments whose acceptance
was independently verified by a different worker in the same turn; it is
suppressed during the `workforce.contractor_review_days` review window (default
7 days) and disabled entirely with `auto_promote_successes: 0`. Every promotion
— automatic or operator — is recorded as a worker event with its actor and
evidence. This automatic path is an AR-119 P0 closure gate. Live native-child
outcomes do not yet record verified-acceptance evidence, so automatic promotion
stays dormant until
[AR-252](docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md)
lands.

---

## 🧪 What gets routed for an ask

Inference reads the **intent** of the ask together with the repository's
**detected stacks**: a bounded, deterministic marker-file scan of the turn's
working directory (`pyproject.toml`, `package.json`/`tsconfig.json`,
`go.mod`, `composer.json` dependencies, ...) is surfaced to the planner and
recruiter as context evidence. The same phrasing can route to a different
specialist depending on that repository context, and a single ask often
decomposes into a multi-specialist team. *(Representative — actual picks
depend on the detected stacks, the model's reading of intent, and the live
roster.)*

**Same ask, different specialists by context:**

| Ask (with detected stacks) | Recruited via | Specialist |
|---|---|---|
| "fix the auth bug" — in a Python repo | inference | `python-application-engineer` |
| "fix the auth bug" — in a TypeScript repo | inference | `typescript-application-engineer` |
| "fix the auth bug" — in a Go repo | inference | `go-application-engineer` |

Stack detection is evidence, not a selector: deterministic code reports what
the repository proves, and inference still owns the pick.

**One ask → a governed multi-specialist staffing set:**

| Ask | Recruited via | Staffing view — not a host execution sequence |
|---|---|---|
| "Review this code for correctness and security" | inference | `code-reviewer` + `ai-generated-code-security-auditor` |
| "Design a Git branching strategy" | inference | `git-workflow-master` plus any independently selected supporting expertise |
| "Build a FluxUI dashboard" | inference | `senior-developer` (owns FluxUI/Livewire/Laravel) |
| "Investigate and contain this production incident" | inference | incident-analysis, recovery-planning, and operations expertise as justified by the ask |

**No provider configured, or no valid inference response?** Agency selects no
specialist, reports the exact cause, and lets the host answer as a generalist
with a `Recruited via: none` header. Deterministic recall may build the
candidate shortlist and deterministic verification may reject unsafe model
output, but neither is allowed to recommend a team. You are never locked out of
the agent by a staffing failure.

Try it yourself on your own repo:

```bash
agency route "review this authentication design and propose tests"
agency explain "review this authentication design and propose tests"
```

---

## 🤖 Configure inference

Agency requires a working provider for every substantive specialist-selection
turn. Configure and validate one before expecting routing or hiring.

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

If the configured chain is unavailable or invalid, Agency reports a terminal
selection failure rather than pretending deterministic candidates were
model-selected.

**Per-stage profiles and per-harness routing.** Named `inference.profiles`
assign a model and thinking level to each selection stage, across every
provider kind: LiteLLM routers and API-key endpoints (`adapter: litellm`,
`anthropic`, `openai-compatible`, `ollama`) and OAuth subscriptions through
`adapter: cli` with `transport: codex` or `transport: claude` (codex forwards
`thinking_level` as its reasoning effort; the claude CLI has no per-call
thinking control, so a configured level is recorded as unsupported).
`inference.harnesses.<host>` sections scope a `default_profile` and `routes`
to the harness that owns the turn, so one installation staffs from a
different subscription per host — e.g. Claude turns on an Anthropic
subscription, Codex turns on an OpenAI subscription:

```yaml
inference:
  profiles:
    claude-haiku: {adapter: cli, transport: claude, model: haiku, timeout_ms: 120000}
    claude-sonnet: {adapter: cli, transport: claude, model: sonnet, timeout_ms: 120000}
    codex-fast: {adapter: cli, transport: codex, model: gpt-5.6-luna, thinking_level: low, timeout_ms: 120000}
  harnesses:
    claude:
      default_profile: claude-haiku
      routes:
        workforce.recruiter: claude-sonnet
        workforce.recruiter.critic: claude-sonnet
    codex:
      default_profile: codex-fast
```

Precedence: harness routes → harness default → global routes → global default
→ the legacy provider chain. `AGENCY_INFERENCE_HARNESS` naming a configured
section overrides harness selection for terminal testing.

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
agency install --dry-run
agency doctor
```

Inspect the exact installed build and resolve an update target without changing
the environment:

```bash
agency -V                                      # fast package version
agency version --json                         # source/VCS commit + install kind
agency upgrade check --channel release        # latest stable release
agency upgrade check --channel main --refresh # current development head
agency upgrade --version 0.2.0                 # exact release plan
agency upgrade --ref <full-commit-sha>         # exact ref plan
```

The repository currently has no published stable release, so the release check
truthfully reports unavailable. Private-repository checks use your configured
GitHub CLI authentication when present; Agency neither stores nor returns that
credential. `--cached` performs no remote access, and
`AGENCY_UPDATE_NOTICES=0` disables interactive cache notices.

`agency upgrade` is deliberately a planner, not a self-modifying installer. It
resolves the selector to one full immutable commit and prints an exact usable
package-install command plus the Codex-refresh command for review in an
owner-controlled terminal; it reports
`mutation_performed=false` and executes neither displayed mutation. The
authenticated dashboard checks stale release/main metadata in the background
and exposes the same fixed copy-only attended command. It cannot install
packages, refresh Codex, restart itself, or bypass native harness trust. See
[ADR-0107](docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md).

The plan uses the current interpreter only after proving the Agency package and
regular `pip` entry point are inside that exact private, non-repository
environment and a bounded isolated `pip --version` probe succeeds. A uv-managed
Agency tool normally omits pip, so Agency instead requires the bounded uv
receipt to identify this exact tool environment and a non-repository `uv`
executable. Bounded `uv tool dir --no-config` probes must then prove that uv's
default tool and executable directories own the current prefix and receipt
entry point. Target-changing uv/XDG environment overrides fail closed. The
planner then emits `uv tool install --force --refresh --no-config` against the
same commit-pinned source. Run the displayed commands unchanged in the same
owner-controlled environment; regenerate the plan after any environment
change. Windows displays are inert PowerShell invocations, and POSIX uv
entrypoint symlinks must resolve inside the exact tool prefix. If neither
installer can be proven usable, planning fails closed rather than printing a
command that cannot run.

Bare `agency install` installs the applicable suite: it initializes Agency's
core state, discovers every installed supported harness on the current OS,
installs or refreshes those integrations, and selects the dashboard service.
`--agent <host>` narrows harness scope, `--no-dashboard` excludes the dashboard,
and `--all` remains a compatible explicit spelling of automatic discovery.
Each component reports independently, so dashboard failure does not erase a
successful harness result and one harness failure does not suppress later
selected harnesses. Use `--dry-run --json` for the complete write-free plan.

Harness registration, enablement, and trust use each harness's native lifecycle;
Agency no longer ships or invokes its own Windows Hello verifier. Normal owner
CLI commands and the automatically authenticated owner dashboard share the same
configuration and control authority. Hook, MCP, and broker credentials remain
read-only. See
[ADR-0117](docs/decisions/0117-unify-owner-control-authority.md).

For Codex, installation also adds one bounded Agency-managed block to the
active global `~/.codex/AGENTS.override.md` when that file is nonempty, or to
`~/.codex/AGENTS.md` otherwise. It supplies the host integration's specialist
card and evidence-correlation guidance; it does not ask Codex to decompose a
request into child work, schedule children, or dispatch an inference-authored
plan. It never selects or names a specialist, never changes repository
`AGENTS.md` files, preserves all owner content outside its markers, and is
idempotent. Codex uninstall removes only that managed block. See
[ADR-0138](docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md).

Release artifacts remain canonical and reject executable names or structurally
valid PE payloads under disguised names. The Windows and portable wheel profiles
contain the same Python package payload; platform metadata remains explicit.
Install from this repository only as prerelease source; no signed public
artifact exists.

**Codex** normally requires you to approve command hooks. Agency installs the
plugin, reports registration, trust mode, and activation separately, and gives
the exact next step. To refresh an existing managed Codex adapter from this
source in attended mode, first run:

```bash
agency install --agent codex --no-dashboard
```

That transaction deliberately does not claim activation. Close every Codex
terminal TUI opened before the install or refresh, then run `codex` in a fresh
terminal. Choose **Trust all and continue** when the startup review lists all
eight Agency events, or run `/hooks` inside that fresh terminal TUI. Start a new
session so the settled plugin can load, then run:

```bash
agency install --agent codex --verify-activation
```

Verification first asks Codex for the read-only hook inventory. In attended
mode it starts the bounded model-backed canary only when the exact eight Agency
hooks are enabled and trusted; missing, changed, or unsettled trust fails
quickly without using provider quota.

For an owner-controlled fresh container or other disposable environment, use
the explicit autonomous mode after configuring inference through the same CLI
surface:

```bash
agency install --autonomous --verify-activation --json
```

Autonomous mode may use the harness's supported noninteractive hook-trust bypass
for that exact invocation. It records `trust_mode=autonomous_bypass` and never
claims the hooks were trusted. Both modes must still prove hook start, route,
correlated specialist-card delivery, host-native child lifecycle, and finalization before
reporting runtime readiness.

The intended post-gate install and rollback commands include ZCode:

```bash
agency install --agent zcode
agency install --agent codex --rollback
```

The dashboard is selected by default as a per-user service (no admin access).
`agency install --no-dashboard` omits it. Managed files and backups live under
`~/.agency-runtime/`.

Remove only Agency's native host integrations with a reviewed two-step plan:

```bash
agency uninstall --all --dry-run --json
agency uninstall --all --confirm-plan <plan_digest> --json

# Or scope both calls to one host:
agency uninstall --agent codex --dry-run --json
agency uninstall --agent codex --confirm-plan <plan_digest> --json
```

Application recomputes the exact plan, so a changed selector, host, managed tree
or parent, install identity, prepared launcher or any executable/wrapper
artifact in its process chain, host profile environment, native plugin or
marketplace source, gateway/ZCode state, or command plan invalidates the digest.
Native provenance accepts only documented path aliases; an invalid, relative,
or conflicting alias blocks even if another alias points at the
managed target. A mutating uninstall applies the exact two-step dry-run ->
confirm-plan digest: the plan is recomputed and re-digested at apply time, so a
changed selector, host, managed tree, ownership, or binding invalidates the
digest and makes no host change. Only a strict ownership-proven adapter tree is
moved after native detachment is proven,
to the exact destination
`~/.agency-runtime/backups/<host>/uninstall-<operation_uuid>`. Windows follows
the validated directory through an open handle during rename, so a pathname
swap cannot redirect retirement. Restore that exact bundle with the result's
`agency install --rollback --agent <host> --backup <retained_path>` command.
On Windows, copy the reported command exactly: it starts with PowerShell's `&`
and single-quotes every argument so path metacharacters remain literal.
There is no purge option: the Python package, Agency Runtime configuration,
Store, roster, evidence, existing backups, and dashboard service are preserved.
Exact plugin registration or Agency-owned
ZCode handlers necessarily change; unrelated host configuration is preserved.
This command does not call the dashboard-service uninstaller. Codex and Claude
marketplace registrations are also retained as user configuration unless a
future install ledger proves Agency created an exact entry exclusively;
marketplace-only residue does not select a host under `--all`, while an
ambiguous or mismatched marketplace blocks an otherwise selected integration
without being removed. The dashboard may copy the write-free preview command,
but it has no uninstall mutation endpoint. Hermes may retain its exact Agency
inventory row in a proven disabled state; that is its detachment contract, not a
claim that the row was deleted. ZCode performs two unchanged-byte checks before
atomic replacement under the Agency lock, but an external same-account ZCode
writer can still race between the final read and replacement; this is not
claimed as filesystem compare-and-swap. Restart affected hosts before treating
Agency as unloaded from already-running sessions. See
[AR-189](docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md) and
[ADR-0108](docs/decisions/0108-retire-only-owned-host-integrations.md).

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

`agency eval routing` is an offline deterministic candidate-recall, policy,
delegation, and performance gate. Its candidate IDs are shortlist evidence for
inference, not selected or recommended specialists. Substantive specialist
selection requires a valid configured inference decision and runtime receipt.

From a development checkout with the dev dependencies installed, prove that
the focused suite rejects Agency's curated decision regressions:

```bash
agency eval decision-conformance --repository . --json
```

The command first proves the named baseline tests are green, then applies each
mutation to a fresh owner-private disposable copy. It never changes or restores
the requested checkout. Only the expected ordinary pytest failure kills a
mutation; a timeout, stale anchor, collection error, unrelated failure, or
survivor fails the command. The curated manifest includes online inference
ownership, ranking order, explicit staff/gap decisions, truthful hire-budget
accounting, contractor projection, amendment identity and bounded additivity,
and content-free diagnostic decisions.

Inspect the persistent host and global states without changing them:

```bash
agency status --agent codex
agency status
agency off --agent codex --dry-run --json
```

Owner CLI and dashboard controls use the same validated writers, exact
confirmations, revision or generation checks, dry runs, ownership checks, and
postconditions. Those are transaction-safety controls, not a human-presence
ceremony. Hook, MCP, and broker identities remain read-only.
The Agency-native `agency-steward` is the protected parent-only evidence kernel.
It is not listed as a selectable worker; imported managers remain ordinary,
reversible roster specialists.

---

## 📊 Operations dashboard

The optional local dashboard is selected by default during installation and can
be excluded with `--no-dashboard`. It shows staffing decisions, provider and
model receipts, host compatibility/status, roster and workforce evidence,
bounded delegation-event rows, routing latency, specialist-selection
frequency, recent turns, cached/background update status, and the supported
owner configuration and runtime controls available in the browser. Its
Evidence view keeps three authorities separate: host-written artifacts can
prove card delivery, Store statuses can show Rule-8 exceptions without proving
what a host did, and trusted staged/cache files can show measured wiring drift
without a live canary. It is an observatory and owner control plane, not a
child-execution scheduler. Delegation-event rows may include legacy or
recommendation-only records; the dashboard shows an observed child only when
execution correlation exists, and no such row proves specialist-card delivery.

`agency dashboard service open` is an owner convenience operation: it ensures
an Agency-owned service is installed and running before opening its loopback
page. Authentication is automatic through a per-launch bearer that is removed
from browser history; it is request isolation, not a login or proof of human
presence. Broker credentials remain read-only. See
[ADR-0117](docs/decisions/0117-unify-owner-control-authority.md).

---

## 🔍 Response header

Every Agency response starts with an evidence header — a truth-receipt, not
marketing:

```text
Agency/Agencies loaded: agency-steward, code-reviewer
Agency/Agencies delegated: code-reviewer via generic-worker/spawn_agent
Skills loaded: none
Actual Model selected: parent task: host-selected (not observable to Agency); workforce inference: gpt-5.6-luna -> codex/gpt-5.6-luna; specialist: launch model not evidenced by this receipt
Recruited via: inference
```

The canonical header is exactly these five machine-stamped lines (AR-224
removed the earlier model-authored `Why` / `How it shaped outcome` lines from
the contract). The **`Recruited via`** value is stamped from the durable
routing receipt — `inference`, an inference-backed `cached` decision,
`deterministic` for turns that need no specialist selection (exact control
commands, plain conversation), or `none` on a staffing failure — and can never
be model-authored. The header is a compact projection of correlated Store
evidence, not independent proof. A missing, malformed, corrected, or
evidence-mismatched header makes the turn fail; successful product evidence
requires correction count zero.

`Agency/Agencies delegated` is a historical, host-observed native-child event
projection. It does not mean Agency instructed the host to dispatch a child or
prove that a selected card was delivered; those claims require the separately
correlated host artifact.

Agency constructs that header before the first visible response. Native Codex
receives exact Store-backed snapshots at preflight and after recorded tool or
wait evidence. Hermes and OpenClaw call the local `agency.finalize` tool once
immediately before their natural final response and emit its returned text
unchanged. An invalid natural response is terminal: Agency does not ask the
model to repair the header or count a repaired response as success.

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
- A nightly workflow quarantines and audits upstream deltas and publishes review
  evidence. It does not yet update normalized contracts, confusion groups, and
  ingestion evaluations end to end; AR-120 remains open for that completion.
- Enrichment (`scripts/enrich_workforce_contracts.py`) regenerates typed
  `stacks` and user-facing `scope_qualifiers` for the roster so the
  deterministic verifier scores real stack coverage; `domains` come from a
  read-time contract overlay rather than the enrichment script.

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

Deterministic plugin smoke (no live model calls):

```bash
agency smoke --agent codex --json
agency smoke --all --json
```

Live host canaries print their exact confirmation phrase on the readiness
report and run only when you pass it back:

```bash
agency host-canary claude
agency host-canary claude --execute --confirm "RUN LIVE claude CANARY"
```

Claude canaries always run in a disposable isolated profile;
`--profile-scope current-profile` and `agency install --agent codex
--verify-activation` are Codex-only surfaces.

---

## 🧯 Troubleshooting & development

- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — host maturity, MCP,
  LiteLLM, dashboard, and platform diagnostics.
- [CONTRIBUTING.md](CONTRIBUTING.md) — setup, implementation boundaries,
  validation.
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) — release gates.

## License

[MIT](LICENSE). Roster specialists are sourced under MIT from the upstream
specialist-pool project. Native Windows source provenance, C++/WinRT MIT text,
Microsoft STL Apache-2.0 WITH LLVM-exception text and NOTICE, and the unresolved
MSVC/Windows SDK/static-runtime legal gate are recorded in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
