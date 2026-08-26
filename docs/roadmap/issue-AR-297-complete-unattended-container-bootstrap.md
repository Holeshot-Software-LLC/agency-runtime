---
title: "AR-297: Complete unattended container bootstrap"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [installation, containers, codex, hooks, automation, configuration]
related:
  - README.md
  - CHANGELOG.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/roadmap/issue-AR-299-local-ollama-canary-child-judge.md
  - docs/roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md
  - docs/roadmap/issue-AR-301-private-systemd-dashboard-namespace.md
  - docs/roadmap/issue-AR-302-owner-private-local-verification.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - agency_runtime/cli/install_commands.py
  - agency_runtime/core/codex_managed_policy.py
  - agency_runtime/core/canary.py
  - tests/test_codex_managed_policy.py
  - tests/test_cli_coverage_complete_install.py
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-297
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
depends_on: [AR-300, AR-301, AR-302]
blocks: []
---

# AR-297: Complete unattended container bootstrap

## Problem

Production will dynamically create an OpenClaw, Claude Code, or Codex
container, install Agency Runtime, and let Conveyor invoke work. No person is
available after provisioning to settle hook trust or finish configuration.
The existing Codex `--autonomous --verify-activation` path uses a trust bypass
for one canary invocation only. It can prove that invocation, but it cannot
make the later ordinary Codex process started by Conveyor load Agency hooks.
Installation also lacks a first-class exact config argument, so image builders
must rely on ambient shell state.

## Current state

- Package acquisition and the Agency runtime-install transaction are separate;
  after the package exists, `agency install` owns roster, host, dashboard, and
  activation state.
- Attended Codex installation correctly leaves persistent trust to Codex, but
  that is not an unattended-container solution.
- The invocation-scoped autonomous bypass is useful diagnostic evidence and
  remains explicitly nonpersistent.
- Claude Code, OpenClaw, ZCode, and Hermes already use their native
  registration/enablement lifecycles without Agency inventing a trust store.
- Tracker issue [#335](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335)
  is linked and remains open with this in-progress record.

## Approach

Add `agency install --production-container --config <path>` as an explicit
dedicated-container transaction. Bind that exact validated config through the
Store, host payloads, and optional dashboard service. Require at least one
selected or detected host and fail before installation when the config or host
scope is missing.

For Codex, install the normal Agency plugin for skills and MCP, then install a
system `requirements.toml` that enables managed hooks, restricts hook loading
to managed sources, and references one Agency-owned absolute relay under the
managed directory. The relay binds the published private interpreter/runtime,
exact config, runtime control, and canonical eight events. Refuse any existing
system requirements or relay file that does not carry a valid Agency ownership
and payload digest; never merge or overwrite foreign enterprise policy.

After policy installation, run the existing current-profile Agency canary in
`managed_policy` mode through a normal Codex invocation with no hook-trust
bypass. Completion requires live hook/route/card/child/finalization proof and a
persisted current-profile attestation. A failed policy step or canary exits
nonzero while retaining bounded recovery evidence. Other selected hosts must
reach native registration completeness in production-container mode.

## Dependencies

- ADR-0173 owns the dedicated-container/system-policy boundary.
- ADR-0118 retains inference-only staffing authority; this installation change
  does not let Agency dispatch children.
- ADR-0156 retains host-written card-delivery proof.
- A live Codex canary still requires a working authenticated Codex provider and
  the configured Agency inference routes.

## Acceptance

- [x] `agency install` accepts and binds one explicit config path.
- [x] Production-container mode requires an explicit config and nonempty host
      scope and is incompatible with rollback and verification-only modes.
- [x] Codex system policy pins hooks on, loads only managed hooks, and installs
      all eight Agency events through an absolute managed relay.
- [x] Existing foreign requirements or relay files are refused without being
      overwritten.
- [x] The production Codex canary uses `trust_mode=managed_policy`, does not use
      `--dangerously-bypass-hook-trust`, and requires persistent attestation.
- [x] Prior Codex activation proof is invalidated before system-policy mutation;
      doctor, status, and dashboard inspection distinguish managed, attended,
      absent, drifted, and foreign-or-modified policy state.
- [x] Focused source tests cover policy generation, idempotence, refusal,
      parser closure, and fail-closed activation.
- [ ] A clean Linux Codex container proves the exact transaction, then a later
      ordinary Conveyor-equivalent Codex invocation loads Agency unattended.
- [ ] Clean Linux Claude Code, Hermes, and OpenClaw containers prove native
      registration, loading, and a bounded Agency turn without human input.
- [ ] Release-artifact and remaining release-checklist gates pass on the exact
      merge candidate.
- [x] Tracker issue #335 is linked and remains open while acceptance is pending.

## Verification evidence

Current source coverage parses the generated managed requirements as TOML,
checks all canonical hook events and immutable relay bindings, proves an
idempotent second install, and refuses both foreign system policy and a foreign
relay before preparing runtime artifacts. Read-only inspection parses the
owned TOML and relay without executing them, invalidates current proof on
policy drift, and projects managed authority through the CLI and dashboard.
Focused installer and canary tests prove the managed mode uses the normal
current-profile Codex argv, skips the non-managed plugin trust probe, records
no trust bypass, and fails before a canary when managed policy is refused.

The exact guided dashboard is 386,366 bytes. The audited 378 KiB ceiling leaves
706 bytes (0.18 percent) of headroom after the managed-policy and complete-prompt
projections; the release packaging gate passes at that bound.

On the installed Windows runtime, strict assurance and additive dense recall
validate structurally. Codex, Claude Code, ZCode, and the dashboard projection
are registered, enabled, and current with no runtime drift; OpenClaw and Hermes
are absent and were skipped. Deterministic installed smoke passes 8/8. The
install remains incomplete only because this attended workstation has not
granted Codex hook trust, while doctor additionally labels all three installed
harnesses cold. That is truthful attended-host degradation, not evidence for
or against the dedicated-container managed-policy path.

The exact installed dashboard, managed-policy module, and workforce Store
reader hash-match source. Repository verification passes 840 named fast-spine
tests with 20 skips, 138 dashboard UI tests, Ruff and documentation checks, all
routing thresholds, and the curated decision-conformance evaluator with a
passing baseline, every mutation killed, and source unchanged. The evaluator
must run through the development interpreter; the minimal consumer uv-tool
environment does not include the repository test dependency.

The required Linux container and post-install Conveyor-equivalent evidence are
intentionally still open. Windows source tests cannot establish Linux `/etc`
permissions, real Codex managed-policy loading, Claude/OpenClaw process state,
or release artifact portability.

The 2026-08-26 Linux preflight is isolated on
`codex/ar297-production-container-live-evidence` at clean merge candidate
`0a23983aa7b99ec27ef18b1a950f6a0327961f72`. The host is Ubuntu 24.04.4 LTS,
kernel 7.0.0-29, Python 3.12.3, Docker 29.7.2, and systemd 255. Exact harness
inventory is Codex 0.149.1 with ChatGPT auth, Claude Code 2.1.239 with first-party
subscription auth, Hermes 0.20.4, and OpenClaw 2026.7.1-2 with a reachable
systemd-user gateway. Local inference inventory found Ollama 0.30.0 and an
authenticated LiteLLM loopback gateway; no Jina route was configured or called.

The owner subsequently approved an all-free local text and child-judge
topology. A bounded synthetic planner A/B used Agency's exact compact planner
system prompt, response schema, semantic compiler, policy validator, and an
untrusted injection suffix with Ollama `think: false`. `qwen3.5:9b` returned six
units but failed semantic compilation (exit 1, 32,272 ms); the local
`qwen3-14b-abliterated:latest` returned six units, echoed no injection, and
passed every policy check (exit 0, 23,774 ms). Generation is therefore pinned
to the measured 14B model rather than selected from parameter count or prose.

The final owner-approved secret-indirected configuration outside the repository
has SHA-256
`cb569bf027133305df594d8ff029dffb8d38f545e960517d4431dfbf1b2bc2e1`.
It uses strict workforce assurance and independence, additive dense recall,
direct Ollama generation/critic/text-reranker profiles, unchanged LiteLLM
`qwen3-embedding` at exactly 4096 dimensions, and a no-thinking
`mistral-small3.2:24b` child judge pinned for every target harness. Direct
schema validation exits 0 and the file remains mode 0600 with no secret value.
The judge was acquired under the owner's explicit approval; local metadata
records digest `5a408ab55df5`, 24.0B parameters, Q4_K_M, 131,072-token context,
and Apache-2.0 licensing.

AR-299/ADR-0174 now admit only an already-declared, safe, available Ollama
profile into the existing exact-name/no-fallback canary projection. Thirteen
focused warning-strict tests pass; unsafe non-loopback HTTP still fails before
transport. Tracker creation remains prohibited by the active task, so AR-299
tracker parity is an explicit unresolved gate rather than an omitted record.

Bounded exact-route probes pass for every final route without Jina: generation
uses `qwen3-14b-abliterated:latest`; critic, text reranker, and child judge use
`mistral-small3.2:24b`; and the authenticated LiteLLM embedding alias resolves
to `qwen3-embedding` with two exact 4096-wide normalized vectors. Sanitized
requested/actual identities and schema checks are preserved in the private
evidence root.

The first clean Codex production-container transaction installed the native
bundle and current managed policy, then exited 1 before inference with
`live_attempted=false`: the canary reopened its Store at the absent default
config path and could not resolve the explicit config's local judge pin. AR-300
threads both exact identities across that internal boundary and passes 15
focused warning-strict regressions plus Ruff and formatting. No bypass or
default-path copy was used.

The rebuilt exact candidate is commit
`987cee8ff01a4a16780eac15bb8120f828d4193d`. Its wheel SHA-256 is
`17a3bc0053a882b22ff72d8b3a2ebcd23ef602c2b5c034e7a05e8ae10ff929f1`
and its sdist SHA-256 is
`6551c43fc6fc7dfe7d8b9318e5b7605d1ecc8e214490eb7d0d2af001ffa9adb5`;
build, strict Twine, and independent verification each exit 0 under owner-private
umask 0077. The documented build under ambient umask 0002 fails the independent
archive-permission contract and remains an explicit usability gate.

Clean production installs exit 0 for Claude Code, native-UID Hermes, and
OpenClaw. OpenClaw loads all 13 hooks. Two rebuilt Codex attempts reach the
exact managed canary but exit 1 at `staffing_critic_rejected` after the additive
embedding route reports invalid inputs. Store traces
`01a03e2b-01ba-7c02-962f-155b0fd8b3b8` and
`01a03e2c-f2cc-7f83-93f7-42bfae07df79` contain no route, specialist, child,
finalization, or attestation proof. This proves AR-300 crossed the prior config
boundary, but it does not satisfy AR-297's unattended Codex acceptance.

Later ordinary invocations also remain incomplete: Claude times out with Store
trace `5e7cea73-3db3-400b-b083-0a9687180693`; the first Hermes attempt rejects
Qwen 14B before inference because its declared context is below Hermes's 64K
minimum; and OpenClaw loads Agency but times out in `before_agent_run` with
trace `9b61694c-c562-498a-ab50-25aa2b5fcabd`. None of these partial states is
labelled a successful Agency turn.

The exact wheel and four native bundles are installed on the Linux host. Codex
correctly remains activation-required. The owner-scoped dashboard service rolls
back because systemd `PrivateTmp=true` remaps trusted root ancestors to UID
65534 and the configuration validator fails closed. AR-301 records that product
defect; foreground worker readiness does not substitute for service proof.

The approved Mistral Hermes compatibility attempt persisted model
`mistral-small3.2:24b` but retained the previously configured `medium` reasoning
level. Prompt SHA-256
`6b5c3c66979625bcc9b90a91978637ce15ca7fb3d3fa95da5b1df03c54c3b154`
created session `20260826_135649_5c52c9` and Store trace
`20260826_135649_5c52c9:5dc5c889-8e55-49d1-a67e-d790fbe89472:95f4cb56`.
Agency loaded unattended but terminalized preflight as
`workforce_inference_failed`; no Agency model receipt exists. Hermes then
exited 1 when Ollama rejected thinking for Mistral. Its native auxiliary chain
also warned about a paid OpenRouter default, received no paid response, and
fell back locally. At that checkpoint, the interview constraint required
explicit approval for `reasoning_effort=none` and `auxiliary.free_only=true`.

The owner then approved those two exact Hermes settings and one retry. The
2,811-byte native config, owned by UID/GID 10000, had SHA-256
`b2540d6e86de4705fe20903b693a14906c7810c7e2d179811964e0b12706b0d4`.
The same 246-byte prompt and hash created Hermes session
`20260826_143220_d88838` and Store trace
`20260826_143220_d88838:59ceb645-aba9-4910-9cb6-1f25d61efd89:2f835640`.
The ordinary process exited 0, but only because the turn guard replaced its
unverified draft with the terminal refusal. Store run
`ecdff898-6dc7-42c9-b0f9-db3447f46623` is `preflight_failed`; receipt
`ee306616-aa15-4262-b88f-b1e9818f0de0` records routing
`workforce_inference_failed`, `runtime_error`, and staffing
`inference_invalid`. The planner applied Qwen 14B, additive embedding rejected
invalid inputs, and both recruiter attempts returned an invalid candidate.
Only `runs` and `preflight_failure_receipts` contain correlated rows: there are
no Agency model, route, skill, specialist, delegation, finalization, or canary
attestation records.

Hermes itself completed two local Mistral API calls with reasoning-token count
zero, but its single `tool_search` found only the connected Agency source and it
never invoked the service. Its 1,367-byte draft SHA-256 is
`b4dfa808fd380fd99439f55417fcfa09635ccb4bffdde2148a93aff1f12794e9`;
the 16,912-byte native system prompt SHA-256 is
`e99111a2373e66b18fa7e3ecd1b4353105ed1cdd30bdd909476427ae8623855e`.
Agency correctly withheld that draft because turn-scoped finalization did not
accept it. No second request dump was created and no further retry was run.

Every named repository gate now has a successful exact run: documentation and
both Ruff checks exit 0; the trusted/private fast spine passes 858 with 3 skips;
dashboard UI passes 138; routing passes every threshold; decision conformance
passes its baseline and kills 160/160 mutations with source unchanged; and diff
checking exits 0. Initial runs from ambient umask 0002 and an interpreter below
untrusted `/tmp` remain preserved as environment failures. AR-302 records that
local repeatability defect rather than hiding it.

Fresh portable wheel and sdist environments each exit 0 for package import,
ten dashboard assets, 263-worker roster integrity, offline selection safety,
eight MCP tools, authenticated dashboard health, deterministic smoke 8/8,
`agency --version`/help, and `pip check`. Host status exits 0 with the four
recorded bundle digests and no runtime drift. OpenClaw's authenticated gateway
RPC probe now exits 0; this read-only health result does not replace its failed
ordinary Agency turn.

The final read-only host check again exits 0: OpenClaw's user service is active
with zero restarts, authenticated RPC is `admin_capable`, and Agency Preflight
0.1.0 is loaded. `agency status --json` reports every installed bundle current,
Codex activation-required, the other three runtime-unverified, and all canary
attestations absent. The foreign OpenClaw device-auth policy warning was observed
but not changed.

Final teardown resolved and removed only container IDs `2ad5e056c84c`
(Codex), `23d812c2bbf1` (Claude), `473cd5bd6059` (Hermes),
`ec5ea44a6f7a` (OpenClaw), and `c7a713bb3b06` (dashboard). `docker rm -f`
exited 0 for all five, the subsequent filtered container list was empty, and
all six final candidate images remain. The host install and OpenClaw service
remained healthy. The Linux-scoped verdict is **NO-GO**: artifact, install,
prompt-visibility, dashboard-authentication, and repository gates pass, but no
four-harness unattended Agency-turn matrix, Codex attestation, or non-root
dashboard-service proof exists.
