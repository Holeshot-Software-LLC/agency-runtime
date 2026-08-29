---
title: "AR-297: Complete unattended container bootstrap"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-29
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
  - docs/roadmap/issue-AR-303-bound-full-roster-embedding-requests.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/issue-AR-305-normalize-planner-novelty-absence.md
  - docs/roadmap/issue-AR-306-bind-strict-critic-semantics.md
  - docs/roadmap/issue-AR-307-project-canary-inference-credentials.md
  - docs/roadmap/issue-AR-308-bind-activation-canary-delegation.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-310-require-managed-codex-canary-store.md
  - docs/roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - docs/roadmap/issue-AR-316-size-ollama-selector-judge-context.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
  - docs/roadmap/issue-AR-318-bound-codex-activation-child-wait.md
  - docs/roadmap/issue-AR-319-honor-pinned-canary-judge-timeout.md
  - docs/roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md
  - docs/roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/roadmap/issue-AR-328-seal-hermes-install-tree.md
  - docs/roadmap/issue-AR-329-freeze-codex-inspector-bootstrap-as-persistent-input.md
  - docs/roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
  - docs/decisions/0178-project-config-declared-credentials-into-tool-reduced-canaries.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - docs/decisions/0182-bound-codex-activation-child-wait.md
  - docs/decisions/0183-honor-pinned-canary-judge-timeout.md
  - docs/decisions/0184-bound-codex-wait-to-full-child-staffing.md
  - docs/decisions/0185-enforce-child-judge-schema-at-litellm-alias.md
  - docs/decisions/0186-bind-codex-child-session-with-canary-request-digest.md
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - docs/decisions/0191-seal-managed-hermes-python-bundles.md
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
depends_on: [AR-300, AR-301, AR-302, AR-303, AR-304, AR-305, AR-306, AR-307, AR-308, AR-309, AR-310, AR-311, AR-313, AR-314, AR-315, AR-317, AR-318, AR-319, AR-320, AR-321, AR-322, AR-324, AR-325, AR-326, AR-327, AR-328, AR-329, AR-330]
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
- [x] A clean Linux Codex container proves the exact transaction, then a later
      ordinary Conveyor-equivalent Codex invocation loads Agency unattended.
- [x] Clean Linux Claude Code, Hermes, and OpenClaw containers prove native
      registration, loading, and a bounded Agency turn without human input.
- [x] Release-artifact and remaining Linux release-checklist gates pass on the exact
      merge candidate.
- [x] Tracker issue #335 is linked; its authorization-pending closure remains
      separate from the completed Linux evidence scope.

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

The next bounded recovery implements AR-303 and AR-304 before repeating any
container matrix. Full-roster recall now prevalidates the logical input set and
may use at most two ordered scalar-safe embedding calls; partial failure or
model/dimension drift is atomic and uncached. Recruiter and critic contract
failures now retain only closed runtime-owned subreasons. The focused
warning-strict set passes 129 tests. Private trace
`ae75a071-1bc2-444c-821a-f616dfd1402a` crossed the former 4,096-dimensional
scalar rejection and then failed at LiteLLM authentication because the direct
process lacked the config-declared `LITELLM_API_KEY`. Both recruiter attempts
persisted `recruiter_candidate_score_invalid` without provider prose. Its
mode-0600 summary and Store SHA-256 values are
`f2c434d9486528b5808b4d263b3609c2ef446c0325527fbe628d84a20202542d`
and `8910f9167ac5ca731ff44d5b0498dad9977562fa9712ccc5cfc1dce6003dced2`.
An ephemeral one-input check using the existing protected LiteLLM service
credential then applied in 3,818 ms at exactly 4,096 dimensions. The corrected
full preflight awaits the mandatory clean telemetry checkpoint; no secret was
persisted and no container was created.

After clean checkpoint `14a4346c` / `3841fcce`, authenticated trace
`7a45e47a-4fb1-4f19-b712-acd24743f910` received HTTP 200 but failed closed on
the bounded JSON structural-node limit. A direct 244-row reproduction proved
that 999,424 vector scalars fit the scalar cap while response row/container
nodes exceed the separate one-million-node parser cap. AR-303 now reserves
those nodes and limits a 4,096-dimensional call to 243 rows; the exact
regression is 243+21 and 139 focused warning-strict tests pass. The preserved
summary and Store hashes are
`31f8c8ad731a5e1f84bfd9037dd5a5457d386e4b213ec636b5d5c63227d8b326`
and `72b33ee665806d9c8b055379cd98a28441903250ef67d403b8a60ee9273355bd`.
No post-correction live call ran before the required recovery checkpoint.

After checkpoint `dbd3eda9` / `95c323eb`, node-bounded trace
`d055d5b4-4bb9-4f6a-993c-5364b27c9e2b` applied both exact
`qwen3-embedding` batches and exact Mistral reranking. Qwen recruitment then
failed with `recruiter_candidate_positive_evidence_invalid` followed by
`recruiter_candidate_score_invalid`. Its summary and Store hashes are
`ab15602d81642a384741c97e78d874cf5569816728579b13adc12ec4f5e934df`
and `accbf41b7991de4c5daaad79232feac11dd542bf53ad2dc54cd3d67d81fac4f9`.
AR-304 now states the exact score and evidence-code formats in both recruiter
systems and appends the matching closed correction to bounded repair feedback;
no model choice or validation rule changed.

After clean checkpoint `5acfbf41` / `8eb54c96`, the single prompt-corrected
private preflight ran at 9.2 percent telemetry and exited 2 after 232,336 ms.
Session `ar297-direct-3efe9f90-9f57-458d-8ef0-a20d972ae03b`, trace
`e10388cf-492c-403c-b2e4-f24cf4df78da`, and Store run
`4bdcfa5a-1d4c-44bf-adef-cc13c4ec5499` correlate one `preflight_failed` turn.
The exact two-batch `qwen3-embedding` route and Mistral reranker applied. The
first Qwen recruiter response was rejected with closed diagnosis
`staff_without_safe_team` after ranking only `uswds-developer`; its repair was
schema-valid and applied, but abstained. Routing therefore remained
`no_specialist_fail_open` with `no_safe_sufficient_team` and
`recruiter_abstained`, while hiring retained `hiring_status_abstained` and
`hiring_inference_failed`.

Only `runs` and `preflight_failure_receipts` have correlated rows. The sole
loaded identity is the resident `agency-steward`; no target specialist was
selected, so the complete 2,659-byte Accessibility Auditor prompt at SHA-256
`c3cfc0981cb980d700ee6b115c3669f5533108598419ca83f26bd5f30e185848`
was not present in the 1,311-byte workforce context. The mode-0600 7,376-byte
summary SHA-256 is
`601dbcc9e6335962e3b5ce087110f5882fea528e34992bac7adb10e2181d7566`;
the mode-0600 3,936,256-byte Store SHA-256 is
`ce9aa8685fe6643688112d01202688eeffd4eb5b8cb9642a734746445b0a8627`.
The run reused the existing service credential only in process memory, retained
no secret, made no Jina call, and was the package's final model attempt.

The owner-approved one-variable Mistral recruiter A/B changed only
`workforce.recruiter` from `local-generation` to `local-critic`; its mode-0600
3,638-byte config SHA-256 is
`87551b5bc936a41742d6846523377e3cf869d8e5c2ce2e4941c447848e125628`.
It exited 2 after 296,074 ms. Session
`ar297-direct-48045cad-ba8d-42b4-b372-075105116b51`, trace
`d276a583-e632-49af-b80f-7bece3b34b90`, and run
`4d0c87fc-e85a-4e4b-865a-474b9886cb93` correlate the failure. Mistral ranked
`accessibility-auditor`, `section-508-accessibility-specialist`, then
`uswds-developer`, but deterministic sufficiency still rejected the team on
the capability axis. The mode-0600 summary and Store hashes are
`8b71384383212e99a3f902065344cfd4e48e73e72b53085edf0cc9085263a3a7` and
`994893bb05270087deb2eae3030e76791d1e7ab032fe79c4823b7e07572425fa`.

AR-305 then reproduced the exact planner boundary in one diagnostic call.
Qwen returned `novel_capability: "false"`; compilation converted that absence
sentinel into the sole uncovered requirement `capability:false`. Its 4,148-byte
mode-0600 diagnostic SHA-256 is
`8c7a2c5c0941ad56fb69f6363662bba8e472449ca82e1c73b9c6a837ad4bf137`.
The bounded candidate canonicalizes stringified absence without weakening real
novel-gap or unknown-domain validation. Planning/inference/selection tests pass
158 with one skip, and changed-file static gates pass. A post-fix live turn has
not yet run at this checkpoint.

The clean post-AR-305 preflight exited 2 after 110,442 ms, but it advanced the
boundary: Qwen planning, both `qwen3-embedding` batches, Mistral reranking, the
Mistral recruiter, and the Mistral critic all applied. Session
`ar297-direct-2776dc3d-9ca1-4f2c-9b96-28fb05a21a49`, trace
`bbf187df-29ab-495a-acb0-7f60885a8b7e`, and run
`be80eeee-c874-454d-bd74-b800e0ec32a8` correlate the remaining
`staffing_critic_rejected` failure. Its 6,815-byte summary SHA-256 is
`a4ca68e121e5ba1db3f9dade51da2556ad194c62f1c663eaf5e86734d132371a`;
the 3,936,256-byte Store is
`7b679a1de05dc49455f577ab44c4ecd521b8580e31a8e38d59f1b5f4795fb346`.

The non-activating strict-pipeline diagnostic exited 2 after 131,589 ms. It
proves the compiled unit requires only `analysis` and `audit`; Mistral selected
only `accessibility-auditor` at confidence 1.0 and margin 0.1, retained the
Section 508 specialist as runner-up, and forbade the USWDS implementer. The
hard verifier accepted that team, but the critic returned
`unsupported-confidence` and `unsafe-composition`. The mode-0600 8,603-byte
artifact SHA-256 is
`c2dbfa542123917bbbd75971ed33aff21be6b95d2a6c538f2261a774911bbba2`.
AR-306 now supplies the previously absent exact thresholds, pre-execution scope,
and selected-only composition contract while retaining independent veto
authority. Focused tests remain 158 passed and one skipped; a live confirmation
has not yet run.

The first AR-306 live confirmation exited 2 after 123,381 ms. Session
`ar297-direct-634be4cb-022f-4aba-91ad-7b1f8dcbc26b`, trace
`a60ed00e-4f08-4a84-8135-8bbc1a2a4f1b`, and run
`e499ad35-f2dc-4a4d-bb76-56f9b23e980d` show every stage through recruiter
applied. Both critic attempts changed from veto to approval but incorrectly
returned reason codes; both failed closed with the precise runtime diagnostic
`critic_approval_reasons_present`. The 7,441-byte summary and 3,936,256-byte
Store SHA-256 values are
`c89620c2983489f118173612d97f01b05662f73be788a204998c2583a6d8722e` and
`7d911ec3faff8e9198a1ddfa791649b124b396b36997c8f3c499daab0a3efe75`.
AR-306 now makes the conditional empty-on-approval/nonempty-on-rejection rule
explicit without weakening the parser or accepting the malformed response.

Final direct trace `f8af12a9-2747-489d-879a-4a8417d1ef35` is accepted at clean
source ledger `eb9da40f4e5662b4671885da004bf93289f8fdeb`. Session
`ar297-direct-50344949-2206-4286-8dc8-d73bf640399f` and run
`61c2b08b-b32c-4493-89b1-777d5efde4f9` correlate five successful model
receipts, one accepted routing decision, and one Accessibility Auditor load;
there is no preflight failure. The 123,320-ms strict/additive turn selects only
`accessibility-auditor` at confidence 1.0, with typed requirements `analysis`
and `audit`. Its exact 2,659-byte governed prompt is present verbatim in the
5,373-byte context at SHA-256
`c3cfc0981cb980d700ee6b115c3669f5533108598419ca83f26bd5f30e185848`.
The mode-0600 4,066-byte summary SHA-256 is
`e608576c0444071e08cc2ac297d7b72ae432c709a831e83035abc1aac7cb8576`;
the mode-0600 3,952,640-byte Store is
`c0cb4beb2d165f8d8f63da3269bf21427e1cf543ce9d18388142aa45606de8be`.
Jina remained absent and the existing LiteLLM credential remained in memory.
This closes the direct specialist-selection and complete-prompt gate without
claiming native harness delivery or container acceptance.

Every named repository gate now has a successful exact run: documentation and
both Ruff checks exit 0; the trusted/private fast spine passes 858 with 3 skips;
dashboard UI passes 138; routing passes every threshold; decision conformance
passes its baseline and kills 160/160 mutations with source unchanged; and diff
checking exits 0. Initial runs from ambient umask 0002 and an interpreter below
untrusted `/tmp` remain preserved as environment failures. AR-302 records that
local repeatability defect rather than hiding it.

The final capture also preserves fail-closed interpreter diagnostics. An
unbound fixture-interpreter run exited 1 with 787 passed, 3 skipped, and 71
trust failures against a group-writable uv base interpreter. Binding the private
cached Python 3.13 reduced that to exit 1 with 856 passed, 3 skipped, and 2
failures because that build lacks Linux `pidfd_open` and
`pidfd_send_signal`; the same two focused containment tests then pass under
OS-owned `/usr/bin/python3`. The complete OS-owned Linux fast spine exits 0
with 858 passed and 3 skipped. Conversely, the first conformance attempt under
isolated `/usr/bin/python3` exited 1 before baseline because that interpreter's
isolated environment lacks pytest; the final private-venv evaluator exits 0,
kills all 160 mutations, and reports source unchanged.

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

The fresh exact candidate is ledger
`2aa0b5a9c00763972ebea740cfe69aa6d2b4544b`. Under caller umask 0002, build,
strict Twine, and independent verification exit 0 for wheel
`912220eb8b9db12c68f38b3a49735ed56d1a99b477e455220bb2d3a96d3740a2`
and sdist
`b3a35227b05ff75d2b1ee1a58c88d0c180d904148dc95aa070991d07ce163c7c`.
The exact named fast spine exits 0 with 859 passed and 3 skipped; all remaining
listed repository gates also exit 0, including 160/160 decision-conformance
mutations killed with source unchanged.

The exact wheel is installed on the Linux host in the owner-private
`2aa0b5a9...` venv and `pip check` exits 0. All four native bundles were
refreshed; the attended combined command exits 1 solely because Codex correctly
remains activation-required. The ordinary non-root dashboard service now
installs and starts with exit 0, is active/running with zero restarts, rejects
unauthenticated health with 401, and returns authenticated 200/no-store health
and worker detail. The browser renders all 2,659 bytes of the Accessibility
Auditor prompt at SHA-256
`c3cfc0981cb980d700ee6b115c3669f5533108598419ca83f26bd5f30e185848`;
stored definition remains explicitly distinct from runtime delivery.

Five fresh image builds bind the exact candidate and wheel hash. Their image
IDs are `d3a2e3bd...49e546` (Codex), `eb720746...fda24d` (Claude),
`6262bad6...be1443` (Hermes), `2bf86f32...ccea47` (OpenClaw base), and
`967c229c...f11ca` (OpenClaw systemd). Fresh clean-state production transactions
exit 0 for Claude, native-UID Hermes, and OpenClaw. Their installed bundle
digests are `8bcaebb9...ef4f6c`, `1e41599f...073f9d`, and
`a9bd648f...3b1732`; OpenClaw loads all 13 required hooks. No ordinary turn is
claimed yet.

The first clean Codex production transaction installs current managed-only
policy with all eight events and no trust bypass, but exits 1 after its live
canary. Session `01a03f2e-593d-7861-bd79-3ab68ca5a92f`, trace
`01a03f2e-5948-7bc1-83d1-15d7d331ca95`, and Store hash
`aabc7fa82eb1d66de637d67657b8c43031881cbf5433f6efea94ff1be4d9beb3`
correlate one run and one `workforce_inference_failed` receipt. Planning,
Mistral recruiting, and Mistral criticism apply, while additive recall records
`embedding_provider_failed`; there are no model, route, specialist, child,
finalization, or attestation rows. The caller had the LiteLLM credential only
in process memory. This failure remains a blocker and is not an activation
claim.

AR-307 isolates that failure without another model call. A secret-safe probe
inside the same Codex container records the declared credential present in the
installer environment and absent from the general safe CLI projection, while
printing no value. The bounded candidate now derives credential-shaped names
from the exact config, projects only matching process-local values after the
native/control environment is complete, and rejects collisions, canary-control
names, malformed values, NULs, duplicates, and oversize before launch. The
global CLI allowlist remains unchanged. Focused warning-strict slices pass 90
and 118 tests; changed-file Ruff, formatting, metadata, policy availability,
worklog, documentation, and diff checks exit 0. No post-fix model call has run.

The post-AR-307 exact candidate is substantive `a13e3cf8` plus ledger
`c5279762`. Caller-umask-0002 build, strict Twine, and independent verification
all exit 0 for the mode-0644 wheel at SHA-256
`6677c9227a9ef6af5aa9e241e1799011cfa98333765699b97abef3a2b0ba90f5`
(9,242,783 bytes) and sdist at
`326f0907be2a603116fb76a19d8ecd0d8cf3d53cf9e412f4579650592253bf3b`
(25,386,943 bytes). Five rebuilt image IDs begin `f50d8eef` (Codex),
`5e482815` (Claude), `ba3551bc` (Hermes), `28d1f07b` (OpenClaw base), and
`9d45c40d` (OpenClaw systemd); every label binds ledger `c5279762` and wheel
`6677c922...90f5`. Four new containers pass the pre-install absence contract;
its mode-0600 receipt hashes to `dedaabba...1491fd82f`.

Two unchanged, no-bypass Codex transactions then exit 1 after real local
inference. Sessions `01a03f4e-27e6-7772-942f-f121ac9c487f` and
`01a03f52-6822-72e3-9c46-d8a7dfc05e7b` correlate traces
`01a03f4e-27f3-7e52-a19e-705f7531a614` and
`01a03f52-6885-73d2-8b73-66b4c274a06e`. Both prove current managed-only
policy, all eight owned events, `managed_policy` trust, and no bypass. Qwen
planning applies after one semantic repair; LiteLLM embedding applies with the
requested/actual `qwen3-embedding`; and Mistral recruiting plus criticism
apply. Both terminate `workforce_inference_failed` before a route, specialist,
child, finalization, or attestation exists. The first complete install JSON
hashes to `53ecfca5...e767152`; the unchanged retry hashes to
`d0efdf28...20837d`. AR-307 is therefore live-proven while Codex activation
remains honestly blocked by the separate strict staffing outcome.

Clean exact-source production installs exit 0 for Claude Code and native UID
10000 Hermes with bundle digests `702a880f...e970724` and
`eda2cb87...31e9858`. OpenClaw's first mutation exits 1 because the pristine
host had no `agents.defaults` policy; Agency correctly refuses to invent it.
After applying the already approved container-local native profile using only
`LITELLM_API_KEY` and `OPENCLAW_GATEWAY_TOKEN` SecretRefs, its mode-0600
`openclaw.json` hashes to `7d567996...cc8060`. The retry exits 0 with bundle
`e0cd11d0...07e598`, runtime-verified loading, and all 13 hooks registered.
No ordinary post-install harness turn is claimed at this checkpoint.

A content-safe ordinary `agency route` diagnostic for the canary text exits 0
outside the restricted activation environment. It records exact 4,096-wide
embedding and all requested/actual models, but Qwen initially rejects false
novelty and its repaired plan misclassifies the read-only review as a
workspace-write implementation. Because the closed-world activation
projection was intentionally absent, that diagnostic is model-quality
evidence only and is not canary, host delivery, or activation proof.

The rebuilt exact `1f32915d` candidate passes all named repository gates and
produces independently verified wheel `a81338f5...ca78` plus sdist
`22e4286f...a15a`. Its one clean no-bypass Codex 0.149.1 transaction crosses
AR-308: accepted `delivery=delegate` selects and loads `code-reviewer`, then
executes one direct native child and one completed wait. The transaction still
exits 1 because the V2 child rollout redacts pre-speech card delivery and the
parent never receives Agency's post-wait header snapshot, so its stale
`delegated: none` response is rejected and no attestation persists. AR-309
owns that later proof boundary; Store rows and model prose are not promoted
into host-artifact authority.

The bounded supported-`multi_agent` comparison cannot replace V2. Although it
records the same accepted `delivery=delegate` route, its injected host context
contains no concrete delegation-plan row, so session
`01a03f94-156b-75f1-9022-ea7cef6ace55` truthfully spawns no child. The retained
stdout, stderr, Store, and parent-rollout SHAs are `356d36d1...bc6`,
`dc6b6525...f5a`, `bb518e7c...20d`, and `95329525...a3`. AR-309 therefore
keeps the V2 execution surface and repairs its exact fail-closed evidence
boundary.

The first rebuilt AR-309 candidate at ledger `fd163da2` produces verified
wheel `2d78f9c...16ab5` and Codex image `9afefdb2...39442`. Fresh container
`570506ea...39b9` passes absence at `eee05217...68a0`, but both its exact
install and bounded diagnostic stop before Codex execution: JSON SHAs are
`64b021ce...1b54` and `d55536f7...2845`, stderr is empty, no rollout or Store
run exists, and private debug SHA `a2821a18...ba65` proves the sealed collector
refused a backend lacking `require_existing_store`. AR-310's managed-only
one-line call-contract repair passes 268 warning-strict focused tests; a fresh
rebuild and no-bypass live transaction remain required.

The rebuilt exact `c60678ef` candidate produces independently verified wheel
`3c8eb01b...09c4e`, sdist `8b8db82c...39131`, and Codex image
`49493058...c9a5c`. Fresh container `30b2b90c...be88` passes absence at
`a5c70707...28b0d`. Its no-bypass install exits 1 with empty stderr and JSON
SHA `a58dae29...4ad7`, but now reaches session `01a03fe6-c434-7432-a7ef-8d5535109e8c`:
the exact route, fixed delegate unit, and one `code-reviewer` load persist.
Canonical parent rollout `fe8aedb9...2d6` proves the only spawn uses invalid
`task_name=code-reviewer` because no concrete delegation-plan row was injected;
the host rejects it before child creation. AR-311's canary-only
`code_reviewer` plan repair passes 545 focused warning-strict tests. Rebuilt
live attestation remains required.

Exact post-AR-311 candidate `49bf11902af5eca7fae528edf75374e73f747933`
was built under caller umask 0002. Build, strict Twine, and independent
verification exit 0 for mode-0644 wheel
`d9c77acfb03577e15e87b4a292776a4fd090c38c655c836fadd4ec3578d860b6`
(9,295,276 bytes) and sdist
`9c74f940713d7a12ce055c4c3d5e350b345003385fb2065b806252344c348ed0`
(25,509,833 bytes). Codex image
`2aed0f4936f53f8247f8b9ec62a4e9488c48a3e1eeca91bf68445800833a276b`
and fresh container `c22a08de...1767d3` bind that wheel. The final absence
receipt exits 0 at SHA-256 `2444f2c4...06a8c`; no Agency target existed before
installation.

The exact no-bypass production install exits 1 with empty stderr and a
mode-0600 21,339-byte JSON at SHA-256 `a28b8b9e...fac87`. Managed-only policy,
all eight events, and `trust_bypass_used=false` remain current. Session
`01a04003-649c-7193-af0e-76cfde91fd20`, trace
`01a04003-64a8-7ef3-8087-9a0f3ca8d7d7`, query
`7a92318a...b046`, and route `b29473bb-5622-471d-a308-fa492cc4c18d`
prove the accepted fixed `code-reviewer` delegate plan. AR-311 is live-proven:
Codex creates child `01a04005-8353-7f42-9020-3453eed3b5b0`, its native worker
run exits 0 on fixed unit `unit-05d45f7553`, and the canonical parent/child
rollouts hash to `8b93d005...1b668` and `6e18884f...f73a0`.

The child still receives only the 563-byte identity context, not the v6 team,
because Codex 0.149.1 reports the omitted optional role as built-in `default`
while preserving `task_name=code_reviewer` as its path. The evidence readers
also reject Codex's normal mode-0755 date directories as non-private before
parsing. Consequently there are zero native child staffing decisions,
deliveries, activation grants, or consumptions. Finalization
`1b1a8833-0bc5-4dba-91be-31da5bafc219` is `response_invalid` with missing
`evidence_verification`. AR-313 and AR-314 own the two bounded compatibility
repairs; 586 focused warning-strict tests plus two artifact-parent tests pass.

The same fresh image also exposes AR-312: the README's pre-install
`agency config validate` form has no explicit config argument and exits 1
against the absent default Store. Its stdout is SHA-256
`c462b0f5...52b7`; the exact config is later accepted by the production
transaction, so AR-312 is recorded without expanding this live package.

After clean AR-313/AR-314 recovery pair `0accd39e` / `84dd879e`, the first
artifact command used an incorrect expanded commit and the immutable-source
guard exited 1 before creating output. The group-writable worktree venv then
failed the executable-namespace guard and lacked Twine. Both diagnostics are
retained. The established owner-private release interpreter produced the exact
candidate successfully under caller umask 0002: build, strict Twine, and
independent verification exit 0 for mode-0644 wheel
`61dbb8c621cbc6229532f30216dab4bf2a5693cf96ad2b084080cb85a07c950b`
(9,298,676 bytes) and sdist
`3845d6e076a60d0da1d3c0578da65a9639e0d0756ba323956fb21d536808329c`
(25,540,553 bytes). Image `12534257...647291` and fresh container
`22ce57f2...e93bff` bind that exact wheel; absence exits 0 at receipt SHA-256
`ae43bf47...ae4bc`.

The first exact `84dd879e` no-bypass install exits 1 after 145 seconds with
empty stderr and a mode-0600 21,016-byte JSON at SHA-256
`b138e5f6...e6800`. It does not reach AR-313/AR-314: session
`01a0402b-2183-77e2-bd3d-998a74504989`, trace
`01a0402b-218f-7ce3-8649-b7943c62395f`, and query
`fc016fdf...891a` terminate `preflight_failed` before any route, load, child,
finalization, or attestation. Qwen planning applies after one semantic repair;
exact `qwen3-embedding` applies; Mistral recruiting applies after one rejected
unsafe-team proposal but then abstains with `no_safe_sufficient_team` and
`recruiter_abstained`. Store `ff60c8c3...a5bc1` and canonical parent rollout
`032f2ee6...7c4d` are retained mode 0600. Because identical config accepted on
the prior transaction, one fresh unchanged retry followed without changing a
model, thinking level, route, or policy choice.

Retry R2 uses fresh container `537744e9...09476`; absence exits 0 at receipt
SHA-256 `0161a419...05fd`. Its no-bypass exact install exits 1 with empty stderr
and a mode-0600 21,349-byte JSON at SHA-256 `aba8cf2d...5089`. Session
`01a04030-ba19-71c2-94fe-f821351a825f`, trace
`01a04030-ba32-7902-a09f-22dc2a32fa3e`, query
`3337f391...5c56`, and accepted route
`3bac13eb-34f4-4d8a-9973-2170c0f8366e` create child
`01a04033-0c92-7f91-a9cf-fc89c5a99148`. Its fixed worker unit exits 0, but
the child again receives only the 563-byte identity message. There are zero
native child routes, deliveries, grants, or consumptions; finalization
`a065ac2c-b1be-4057-83b2-a6bd3c6f51e9` rejects missing
`evidence_verification`. Store, parent rollout, and child rollout hashes are
`9209d92e...c177`, `bf356b10...e309`, and `e9d3c8f8...6cf93`.

AR-315 isolates the exact pre-staffing rejection. The current-profile backend
sets canary mode but omits the owner-home capability that the immutable
managed-install identity reader requires in every canary. Against the installed
private runtime, the no-capability diagnostic resolves no identity; adding
only `/root` as the explicit native-install home resolves a current identity
whose candidate and running digests match. Both exit 0 with empty stderr;
their mode-0600 stdout hashes are `550b2048...e3fff` and
`1fccf6f2...ee60`. The bounded source repair projects that existing owner-home
authority across the subprocess boundary without changing the config or trust
mode. Seven focused and 559 broader warning-strict tests, Ruff, and all 869
documentation checks pass at exit 0; a rebuilt live proof follows a clean
recovery checkpoint.

Exact ledger `3e42598d` produces mode-0644 wheel `0bb18a70...d983` and sdist
`73d8c201...ae55`; build, strict Twine, and independent verification each exit
0. Image `6fbbdbd5...696c` binds the wheel, and fresh C1/C2 absence receipts
`575a1fe3...090`/`abf3d278...8a4b` both exit 0. C1 exits 1 before routing after
two semantically invalid Qwen planner responses; receipt, Store, and parent
rollout hash to `86983408...0fc0`, `765c26a6...d307`, and
`f8ec06fb...fb24`.

C2 reaches accepted route `9f377961-6ced-428d-b1f6-17382b37fb2d`, creates
child `01a04053-b0fc-76a1-8a38-b88b68040455`, and completes fixed unit
`unit-05d45f7553` at exit 0. AR-315 is live-proven: native-child decision
`1d351ac6-cc63-4799-a263-cc3960c63082` can exist only after the immutable
install identity and stable routing-state checks, and it evaluates all 59
eligible cards. The requested free Mistral child judge fails unavailable after
26,341 ms, so only the 563-byte identity is delivered. The outer 180-second
canary expires five seconds after child completion, without a finalization or
attestation. Receipt/Store/parent/child hashes are `e043a745...ead5`,
`7e8a6f9f...9706`, `d74fa302...43a4`, and `a54138e7...0c53`. The next bounded
step diagnoses that exact child-judge route, then retries a fresh unchanged
container with the supported 600-second activation timeout.

AR-316 records the completed route diagnosis: the selector protocol hardcodes
`num_ctx=8192`, so Ollama truncates C2's 19,520-token complete catalog to 8,191
despite the installed model's 131,072-token capability. The same-model,
same-endpoint 32,768-token repair is waiting for the required operator approval;
no judge-route parameter has been changed.

AR-317 replaces that direct route for this Linux candidate without modifying
the retained diagnosis. The operator selected stable LiteLLM aliases for every
Agency inference stage, Mistral for `task-agency-router`, and disabled thinking
for Qwen generation after the installed abliterated build rejected `medium`.
The new mode-0600 exact config has SHA-256 `a4e213d6...97348`; product
schema/load and authenticated six-deployment validation exit 0 at
`fb8d3384...f680f`, with direct Ollama disabled and no secret value or Jina.
Agency critic, text-reranker, child-judge, and exact 4,096-dimensional embedding
probes exit 0. A no-thinking synthetic planner probe returns a valid six-unit
shape but exits 1 for `plan_missing_codebase_discovery`; the next exact Codex
canary must prove its bounded repair before the remaining harness installs.

Exact ledger `8d33694c9895f9da30ef560206efa1206893c78f` now produces a
mode-0644 portable wheel `3b5fa8f9...466dd` (9,299,617 bytes) and source
archive `67ef88f3...0f8f2` (25,601,998 bytes). Canonical build, strict Twine,
and independent verification each exit 0; manifest `7b4098b9...18dc8` records
their complete hashes, modes, ownership, and sizes. Separately built Codex,
Claude, Hermes, and OpenClaw images bind that same exact commit and wheel; their
IDs are `fe5df2d0...6de3`, `e365adc1...74fa`, `34af3456...1c3c`, and
`8375ab36...a800`, with version/label receipt `794d67f3...143a` at exit 0.
OpenClaw 2026.7.1-2 truthfully rejected the former Node 22.22.0 base at exit 1
(`c6f9a003...0b07b`); its retained failed tag was replaced as candidate by the
verified Node 24.15.0 image without changing Agency or the OpenClaw version.

The first exact `8d33694c` no-bypass Codex install reaches accepted route
`d1a4e01f...7565` and child `01a04100...e872`, but exits 1 at receipt
`2942f5ee...935b`. The child authors its terminal message 224 ms before the
single 60-second wait returns `timed_out=true`; the parent correctly refuses a
delivery, header, accepted finalization, or attestation. Store and parent/child
rollouts hash to `3f3f5d84...397e`, `ec0c7859...d523`, and
`fc2c7681...d8f9`. AR-318 owns the bounded one-wait timing repair.

AR-318 now binds one shared 120,000-ms wait into the exact Codex developer
instruction and persisted-rollout validator while retaining one spawn, one
wait, no retry, and the 600-second outer ceiling. The stale 60,000-ms shape is
regression-rejected; Ruff and 309 focused warning-strict tests pass at exit 0.
Exact ledger `c6b7d92d3e66d25e3f108265852f8ad7092710a0` then produces
mode-0644 wheel `704e78a9...79a8` (9,299,940 bytes) and sdist
`69ee572e...552f` (25,612,238 bytes); manifest `c4b99600...557c` records full
hashes and metadata. Build, strict Twine, and independent verifier stdout hashes
are `a7e70dcf...2c7d7`, `6bd77304...354d`, and `70e8a13e...b73f`; all exit 0.
Codex, Claude, Hermes, OpenClaw systemd, and dashboard images bind the exact
wheel with IDs `c14c26b5...73879`, `40f3c505...c900c`, `6e7d7617...1c943`,
`b9add4fc...e7288`, and `a3d2619c...7fa49`. Version/label receipt
`676b83dd...5c2b` exits 0. A fresh clean Codex transaction remains required.

Fresh `c6b7d92d` absence passes at `802e7f60...617c`; exact install
`d61d1574...d23f` exits 1 after accepted route `97e2084b...f386`. The parent
emits one 120,000-ms wait, child `01a0411a...8103` completes, and the wait
returns `timed_out=false`. Its pinned `local-child-judge` nevertheless records
`native_child_inference_unavailable` at 60,091 ms because the 120-second
profile remains capped by the legacy 60-second aggregate judge budget. Only
the 563-byte identity reaches the child, so strict projection admits no v6
delivery, header, finalization, or attestation. Store and parent/child rollouts
hash to `c16b99c1...1438`, `e63a6865...1b8e`, and `7a25e86f...c879`. AR-319
owns the bounded pinned-timeout repair.

AR-319 now projects that pinned provider's validated timeout into the
canary-only aggregate budget and permits the existing 120-second profile
maximum through the selector's internal ceiling. Ruff and 222 affected
warning-strict tests pass; a rebuilt fresh Codex transaction remains required.

Exact ledger `89a56901edb121b32255fbac8f2e58666a9c5d03` canonical build, strict
Twine, and independent verification exit 0. Mode-0644 wheel
`486b04ba...75de` is 9,300,384 bytes and sdist `d08d2ffc...56a2` is 25,622,478
bytes; manifest `4904e1cd...5321` records full metadata. Two earlier retained
pre-build attempts exit 1 without artifacts: worktree-Python trust rejection
`382ab257...b1e0` and system-Python missing-build rejection
`2d7234be...dc85`. Codex, Claude, Hermes, OpenClaw systemd, and dashboard image
IDs are `7765d320...b545`, `222a78c7...cdb2`, `896c03d1...0766`,
`24736e64...1f3d`, and `4c0182f3...88e1`; exact version/label verification
`5edc4c29...395c` exits 0. Fresh clean Codex runtime proof remains required.

Fresh container `f72c1b51...0555` passes exact absence at `a56ac1c5...d994`;
install `96e4d746...73cf` exits 1. The parent accepts `code-reviewer`, spawns
child `01a04131...7490`, and waits once for 120,000 ms. Owner journal
`a32aa50c...edc2` proves the initial child judge and its funded abstention
repair both succeed untruncated in 62,057.76 and 62,870.53 ms. Their combined
125 seconds exceeds the parent wait; identity arrives only after timeout and
the child is interrupted without v6 delivery. Store and parent/child rollouts
hash to `d8755fd9...2f72`, `00d8e1d5...8076`, and `e978545c...d00a`. AR-320
owns the full-path bound; no model or route change is required.

AR-320 now derives one 300,000-ms wait from both 120,000-ms judge ceilings and
a 60,000-ms completion margin while preserving the 600-second outer bound,
one spawn, one wait, and no retry. Ruff and 418 affected warning-strict tests
pass. Exact ledger `c1cf1793db1bc98589ca958a553c502a0126c637` now produces
mode-0644 wheel `8766b539...99d7` (9,300,725 bytes) and sdist
`5dbd6edc...bf68a` (25,642,963 bytes). Canonical build, strict Twine, and the
independent verifier exit 0; manifest `a04282e6...adade` records full metadata.
Codex, Claude, Hermes, OpenClaw systemd, and dashboard images bind the exact
wheel with IDs `c735534e...bd3f`, `93ab0881...acc3`, `e8819230...94ef`,
`5355886a...ca94`, and `fc23a724...666f`; version/label verification
`2f9dadb5...a449` exits 0. A fresh clean Codex transaction remains required.

Fresh exact-candidate container `agency-ar297-codex-c1cf1793` passes absence at
`7d08f8c1...c341`; its one no-bypass install receipt `04f8c2df...7ad` exits 1.
The parent accepts `code-reviewer`, spawns one child, waits once for 300,000 ms,
and receives `timed_out=false`, live-proving AR-320's full-path timing repair.
The current Mistral child judge then abstains on both the initial and funded
repair calls over all 59 eligible cards, so route `fcdf4396...9447` truthfully
records `native_child_abstention_confirmed` and withholds v6 delivery. Store and
parent/child rollouts hash to `9ed3c3f5...b103`, `539b0263...6890`, and
`a1d474ca...e1e8`. An authenticated LiteLLM diagnostic rules out the existing
abliterated Qwen 14B model: its unconstrained response is prose truncated at
256 tokens (`d34221cc...af9c`), while constrained JSON confidently selects the
wrong `ai-evaluation-engineer` card (`697d9cd9...1ac0`). AR-321 owns selection
and promotion of a reliable free LiteLLM child-judge alias before the next
fresh Codex install.

AR-321's authenticated exact-prompt screen rejects preinstalled Qwen 3.5 9B,
Qwen3 Coder 30B-A3B, Dolphin/Mistral 24B, and Qwen 3.5 2B for over-selection,
wrong-card selection, or repeated abstention; all four temporary aliases were
removed with retained receipts. The owner-approved official Apache-2.0
Ministral 3 14B Q4_K_M download exits 0 at `1ae8154b...cf1e`; local metadata
`6321d22e...f2c` proves 13.9B parameters and 262,144-token context. Its plain
JSON probe returns explanation objects at `84a4b980...b8d1`; an exact-schema
alias returns valid strings but over-selects two cards at `aa8917b2...6cef`.
Both temporary aliases are removed, the downloaded free model remains locally
installed, and stable Agency routes remain unchanged. AR-321 continues with a
smaller official structured-output candidate. Official Apache-2.0 Granite 4.2
8B acquisition subsequently exits 0 at `1c990f61...c7ed`; metadata
`8d44fb7b...b81c` proves 8.8B/Q4_K_M and 131,072-token context. Its sole
temporary schema-constrained LiteLLM deployment `e791c3f0...9fc9` is ready for
the next exact probe; the stable child-judge alias remains unchanged.

Granite 4.2 8B subsequently abstains on both exact selector calls at
`b797bbf8...d4f8` and `9c842512...937b`; its temporary alias is removed. The
official Apache-2.0 Qwen 2.5 14B download exits 0 at `e3793ca3...b203`, model
receipt `20b2d98b...360b` proves 14.8B/Q4_K_M and 32,768-token context, and sole
schema-constrained temporary LiteLLM deployment `96ee8dc1...f9f0` is ready.

Qwen 2.5 returns valid JSON but selects `python-application-engineer` at
`35f1030d...5e8e`, so its alias is removed. Official free Llama 3.1 8B
acquisition/model receipts `16e64126...2137` and `048e80f2...e20f` pass,
proving 8.0B/Q4_K_M and 131,072-token context. Sole temporary schema deployment
`fa9bc0d1...331e` is ready while the stable Agency route remains unchanged.

Llama returns valid JSON but selects `ai-evaluation-engineer` at
`e39a84bd...8274`, so its alias is removed. AR-321 next isolates the existing
Mistral Small 3.2 24B model behind temporary no-fallback exact-schema alias
`28a681dc...7a91`; create receipt `d364b366...e485` passes without changing
the stable `task-agency-child-judge` route.

Schema-bound Mistral selects sole `code-reviewer` on the initial form at
`76d2cd38...d1a0` but abstains on repair at `98ead20c...c791`; its probe alias
is removed without promotion. Official Apache-2.0 GPT-OSS 20B acquisition and
model receipts `1e030701...7cee`/`7b701cde...c3d0` pass, proving
20.9B/MXFP4 and 131,072-token context. Sole temporary schema deployment
`9a85ecdf...a219` is ready while the stable Agency route remains unchanged.

GPT-OSS with thinking disabled returns empty content at `91daeed4...2367`, so
that invalid temporary alias is removed. Replacement deployment
`25f90630...45d1` keeps the exact schema, 32,768 context, and zero retries while
using GPT-OSS's lowest supported reasoning effort; secret-safe create receipt
`17fdcd76...8b6f` passes without changing the stable Agency route.

Low-reasoning GPT-OSS again returns empty at `b5bad7af...0500`, so its alias is
removed. A fresh-name schema-bound Mistral deployment `4527083a...1ff6` passes
create receipt `a53f4249...c78c` for an uncached repeat. Promotion now requires
repeated sole-card initial success; repair may safely abstain but may not
misroute, matching the real funded path rather than forcing a false selection.

Fresh-name repeat `cea48a7d...ae89` matches the first schema-Mistral result:
sole `code-reviewer`, confidence 0.8, and 20,037 prompt tokens. Stable
deployment `0f0b1b59...a7d1` keeps the free Mistral backend while adding the
exact output schema, 32,768 context, thinking off, 120-second timeout, zero
retries, and no fallback. Snapshot `03cf8292...9baa` and promotion
`7af0aa02...aa45` are secret-safe; the Agency config remains byte-identical.

Stable literal-alias proof `54a773f7...00d3` exits 0 and selects sole
`code-reviewer`; post-promotion deployment snapshot `de042cbe...6c0a` proves
the exact Mistral/schema/context/timeout contract, and temporary alias deletion
leaves zero deployments at `74a870bc...95da`. Fresh container
`agency-ar297-codex-c1cf1793-j2` passes corrected absence
`3e80348e...1178`; its one no-bypass install `d08883a7...7623` reaches accepted
route `6ca7be2e...0da7`, spawns child `01a04187...ac7e`, waits once for 300
seconds, and receives child exit 0 with `timed_out=false`.

The child nevertheless receives only generic identity context. Parent/child
rollouts `16f4d5e2...2934`/`910538f1...6953` and Store
`d3471c9a...e2af` prove no native parent scope, captured assignment, delivery
verification, or native plan. Official Codex `rust-v0.149.1` source confirms
`SubagentStart` identifies the child session, not the parent. AR-322 source
checkpoint `a5c1ad53` binds that child to the unique nonce-request digest; 99
focused warning-strict tests pass. Exact artifacts and fresh live proof must be
rebuilt from this checkpoint before any Codex success claim.

Clean ledger `c7f35dd541560a8a4e2420c62ee4a43fdd932cb5` now passes canonical
build, strict Twine, and independent verification. Mode-0644 wheel
`23036c74...d68d` is 9,305,733 bytes and sdist `09b85884...1a3b` is
25,694,168 bytes; manifest receipt `bb9b8fb8...09a6` records both. Codex,
Claude, Hermes, OpenClaw systemd, and dashboard image IDs are
`c56df293...26fa0`, `3b0b0b98...21cdc`, `626bf282...bac3e`,
`f2d35ea8...aa83b`, and `9d3eb4c2...c1507`; exact label and packaged-version
verification `f1808c22...64674` exits 0. A fresh clean Codex transaction is the
next live gate.

That transaction at `c7f35dd5` confirms the request digest and parent route but
again gives the successful child only generic identity. AR-324 source checkpoint
`66b889a2` replaces ambient digest inheritance with the exact bounded,
owner-trusted Codex `0.149.1` child `session_meta` lineage. Focused tests pass
137/137 and the expanded canary/artifact/security set passes 259/259.

Clean ledger `9e8fa342` then produces wheel `0d3c4948...dd4a`, sdist
`e443491e...fc66`, manifest `02bd1e04...b327`, and verified Codex, Claude,
Hermes, OpenClaw systemd, and dashboard images `eb4d9305...17e7`,
`c5ac6f52...c6d6`, `f7c7f279...0874`, `a3597cf8...94bf`, and
`041b92bd...9007`. Fresh exact Codex install `7197d5ff...a62` exits 1 after
accepted route `25e06734...7484`, one spawn, one 300-second wait, and child
`01a041d3...b1d2` exit 0 without timeout. Parent/child rollouts and Store hash
to `f83e31f3...02fc`, `b4215dc8...0394`, and `56518a59...53b0`; the child
still receives generic identity and finalization rejects missing
`evidence_verification`.

The exact supported source and retained rollout isolate the fault: Codex puts
the root parent in `SubagentStart.session_id` and the spawned child in
`agent_id`, while ADR-0187 incorrectly required equality. ADR-0188 supersedes
that contract at source checkpoint `34f41532`. The regression fails before and
passes after requiring hook parent/child to agree independently with the
rollout parent/child; focused warning-strict sets pass 192/192 and 258/258 with
two expected skips. Clean recovery and worklog ledgers `7f760a59` and
`c3493337` record that repair.

Exact clean ledger `c34933377f7fb16431120f21d487bfbc9910cd55` passes the
canonical build, strict Twine check, independent verifier, and artifact
manifest at exit 0. Its mode-0644 wheel `3ee91ef7...6626` is 9,317,437 bytes
and sdist `5a762480...9455` is 25,765,853 bytes; manifest
`7fa7d2c1...3bfd` records both. Exact Codex, Claude, Hermes, OpenClaw systemd,
and dashboard image IDs are `2d0b6555...0272`, `c731f8c8...ba8`,
`56645dba...dae8`, `f87f2ab8...218`, and `951618f1...66a`; packaged-version,
commit, wheel, and label verification `884a225f...821` exits 0.

Fresh container `agency-ar297-codex-c3493337` passes preinstall absence at
`a88f8e7d...deb`; its only no-bypass production install receipt
`0ef4c8bb...d46` exits 1 after accepted parent route
`41ac6703-bd29-490c-88d3-b7d9b9aefb38`, one child spawn, one 300-second wait,
and child `01a041eb-27a6-7f22-851e-ff23455f1128` exit 0 without timeout. The
separate-ID host-lineage join now succeeds: the Store contains one native
worker run for that exact child. Parent/child rollouts and Store hash to
`2b0acaec...a11`, `3d0ef98d...d3c`, and `4842b81d...9c9`.

The newly admitted restricted staffing call reaches the authenticated free
`local-child-judge` LiteLLM route over all 59 cards, then fails closed after
62,139 ms with `native_child_compatibility_mutated`, confidence 0.8, and no
persisted selected identifiers. Sanitized correlation receipt
`50bd2770...a0b6` exits 0 and also distinguishes the expected earlier opaque
inter-agent diagnostic. Because exact v6 delivery, consumption, header,
finalization, and attestation remain absent, AR-321 continues to own reliable
free child-judge selection before another fresh Codex transaction.

LiteLLM spend log `chatcmpl-f7ce0722-fdd8-4168-a29f-059c29905990` identifies
the exact stable-alias call as 19,526 prompt plus 26 completion tokens; its
database response projection is empty and the original short-lived Redis body
expired. One bounded repeat of the byte-identical 59-card prompt through the
unchanged stable alias recovers the cached 26-token body exactly:
`code-reviewer` plus `software-test-engineer`, confidence 0.8, content
`8f9a361c...d155`. Owner-private receipt `6df05ca7...884` exits 0. This proves
semantic over-selection rather than lineage, transport, schema, or parser
failure. ADR-0185 forbids deterministic filtering of the larger team; the next
bounded package tests the same approved free backend under a deterministic
temporary LiteLLM deployment while leaving the stable alias unchanged.

That deterministic avenue is now closed. Three fresh temporary aliases retain
the approved backend, exact schema, 32,768 context, thinking off, 120-second
timeouts, and zero retries while adding `temperature=0`; create receipts
`b00a4c04...f430`, `f5880647...d454`, and `23ad4d61...afb3` pass. Agency's
selector request already carries temperature 0, and nine unique successful
LiteLLM request IDs across body/header no-cache diagnostics all reproduce the
same two-card response `8f9a361c...d155`. Spend correlation
`5baea1c2...a7b1` records the distinct requests. All three aliases are removed
at `a30c4b0d...9200`, `9638bf09...557`, and `18b39cbe...932e`; the stable
deployment projection remains byte-identical at `18dd1bdd...18b3`. The next
bounded option is an inference-owned compatibility-repair call through the
same route; a different model or thinking choice still requires owner input.

The first inference-owned compatibility-repair probe remains fail-closed but
does not advance the canary. Through the unchanged stable alias it evaluates
the complete 59-card universe with 20,146 prompt tokens and returns an empty
exact-schema selection at confidence 0.8; owner-private receipt
`2642ac10...0b1e` exits 0. The next bounded probe supplies only the model's own
prior selected IDs and the closed `separate_context_pairs` diagnostic so the
same inference authority can reassess its answer. It still permits abstention
and does not filter, force, add, or remove a specialist in deterministic code.

The closed-diagnostic repair also fails to advance: it supplies the judge only
its own prior IDs and the exact separate-context finding, then Mistral repeats
`code-reviewer` plus `software-test-engineer` byte-for-byte after 19,637 prompt
tokens. Owner-private receipt `29a0045c...f034` exits 0. Temperature and both
inference-owned repair forms are therefore closed without a product mutation.
Filtering, schema max-one, or deterministic role selection remain prohibited
by ADR-0118/ADR-0185. The next viable gate is an owner-selected different free
local child model behind temporary authenticated LiteLLM aliases; this host has
46 GiB RAM, 35 GiB swap, and 331 GiB free disk, with no detected GPU.

The owner-approved `gemma3:27b` trial is also closed. Pull stream
`bfe27b67...f53e` exits 0; metadata `70b7267c...1ead` proves local digest
`a418f5838eaf`, Gemma 3, 27.4B/Q4_K_M, and 131,072-token native context.
Temporary deployment receipt `30805cfe...39c2` proves one authenticated
exact-schema alias with 32,768 context, thinking off, 120-second timeouts, and
zero retries. Its uncached 59-card call `e53e906f...b31c` selects sole
`ai-evaluation-engineer` at confidence 0.9 instead of required
`code-reviewer`, so no repair or promotion is admissible. Deletion receipt
`ec9514af...75c0` leaves zero temporary deployments; the stable child-judge
projection remains byte-identical at `18dd1bdd...18b3`. A new owner-selected
free model is required before another exact Codex transaction.

The subsequent owner-approved `qwen3:32b` candidate clears the bounded model
gate. Pull stream `eea2379c...c4a0` exits 0; metadata `0f040ecb...63fc`
proves digest `030ee887880f`, dense Qwen 3 32.8B/Q4_K_M, and 40,960-token
native context. Two fresh exact-schema temporary aliases retain 32,768 context,
thinking off, 120-second timeouts, and zero retries at `2e458fb9...4bff` and
`c7242824...9cd3`. Initial probes `275b1a2b...81f3` and
`574468ce...f138` each select sole `code-reviewer` at confidence 0.9; funded
repair `7ef675c5...e9e0` returns the same sole card with zero reasoning bytes.
Spend correlation `5163ff8e...61f6` proves three distinct successful LiteLLM
request IDs, exact Qwen backend/deployments, and no response-cache hit. Both
temporary aliases are removed at `298e202b...eb2a` and `7dad190b...673f`.
Stable pre-promotion receipt `16b48f2c...ad40` still hashes to the byte-identical
Mistral projection `18dd1bdd...18b3`; Qwen promotion is the next bounded gate.

Stable Qwen promotion now passes without changing the Agency config or alias
identity. Update receipt `6e19008f...1750` preserves deployment
`0f0b1b59...a7d1`, records prior projection `18dd1bdd...18b3`, and binds
`ollama/qwen3:32b` at new projection `a8dcd172...744a3`. Strict review catches
the legacy update endpoint's stale informational Mistral key. Partial metadata
repair `e1cba9f6...e841` changes only base/key/tier to exact free Qwen values;
executable params remain byte-identical at `47c257af...ee11`. Final validation
`42921a7e...867c` exits 0 over the mode-0600 config and all six deployments,
including exact Qwen backend/metadata/ID/schema, disabled thinking, 32,768
context, zero retries, 4,096-dimensional embedding, and unchanged remaining
routes. A literal stable-alias probe precedes the new exact Codex transaction.

That literal stable-alias gate passes. Exact-config receipt `b686ab4b...9abe`
exits 0 through `task-agency-child-judge`, selects sole `code-reviewer` at
confidence 0.9, and records the same schema-valid 54-byte content with zero
reasoning. Spend correlation `d7183bb5...2f07` binds request
`chatcmpl-b1fe24cc-c39b-4c39-b99a-f37fc212e7b9` to
`ollama/qwen3:32b`, stable deployment `0f0b1b59...a7d1`, successful status,
and no response-cache hit. A new exact Codex container is now the live gate.

The first new container preflight exits 1 only because its `docker run` omitted
the required instance-level candidate/proof labels; content-free receipt
`0cdc5547...ed1` still proves every Agency target absent. That clean setup-only
container is removed at `d0308c3e...4b84` without an install attempt. Separately
named `agency-ar297-codex-c3493337-qwen2` binds the exact verified image and
both instance labels; injection passes and absence receipt `eb44d7ee...fc7e1`
exits 0 with exact image/candidate/config, Codex 0.149.1, mode-0600 auth, and all
Agency targets absent.

That container's one no-bypass production install now exits 1 at finalization,
not at selection, delivery, or child execution. Exact absence SHA-256 is
`eb44d7eefef2e18daf408cf70da02d8f87155aa69b1a325b53f67b7601afc7e1`;
the 27,042-byte mode-0600 install JSON hashes to
`c56eb749f236f63b0b87a3439b9f58eb2aa8a2a0078d0a2253168ce334bc3c44`.
Parent `01a04311-f671-7e70-b8cc-accd93ef10a4`, trace
`01a04311-f6a8-73a2-8318-3cb72700b7ed`, accepted route
`8a7b167a-cda0-421e-a5e4-8e0a06e2cee4`, and child
`01a04313-bcd6-79b1-b304-f37769d1872e` agree. The promoted free Qwen alias
selects sole `code-reviewer` at confidence 0.9; the complete 2,379-character
card with prompt hash
`e409b2c8b42430b9e69b1e0a93a42e8b790e6ae86c1a3e3e31c03ea0ed9820bd`
is host-verified by native delivery decision
`native-child-b2c5e574580f1be4788de94e30699684`. The child exits 0, the one
300-second wait reports completed without timeout, and no activation bypass is
used. This clears the AR-321 model gate and live-proves AR-324's separate-ID
lineage and full v6 prompt delivery.

Parent rollout SHA-256 is
`fb580c43c012081c707df4e760c6b77567e3444cbe173f92f7ce171d8c87a383`;
child rollout is
`c60cc6a65a3a90e80f99939a93ba102fbb5187c05b0b111a2d8078459db2d079`;
Store is
`3e41479f4f8cffa924a60a990a0b2e3f08c4438734b28b793da8e1a67f4148a6`.
Finalization `eaea50d9-c0e8-4d70-a744-a5e10faa3833` rejects only
`evidence_verification`. AR-325 isolates two callback-order defects: the exact
managed encrypted spawn also appended ordinary failure route
`6b6ec8ec-ecff-40ab-8c47-b227906ddfba`, and post-tool-first ordering left
synthetic delegation `1fd541cd-1e02-45ee-9976-efdcabac041d` on opaque-message
unit `unit-a6211f69b1` while the real child completed unbound on fixed unit
`unit-05d45f7553`.

The regression-first AR-325 source repair keeps ordinary opaque spawns
diagnostic, recognizes only the exact managed ciphertext/task/response shape,
retains the fixed-unit dispatch when `PostToolUse` arrives first, and atomically
promotes or merges it when the validated real child arrives. The opposite
callback order can now claim after an already-observed terminal child. Five
targeted warning-strict cases, 149 focused hook/Store/header/parity tests, and
17 decision-conformance unit tests pass; both new curated mutations are killed
with source unchanged. Their retained stdout SHA-256 values are
`394d9276...1c4d`, `74a9f4f9...4141`, and `ea4477e5...3695`; every command
exits 0 with empty stderr. A separate 145-test security/atomicity slice also
exits 0 at stdout `ae7689e3...7a84` with empty stderr. A fresh exact build and
clean Codex install remain required before accepted finalization or attestation
may be claimed.

Clean ledger `19e0210bd5c5b3949dc4206b7cc8ca9244c9a144` now produces wheel
`81d0bba7...43c1` (9,335,316 bytes) and sdist `c8891af1...01dd`
(25,837,538 bytes). Build, strict Twine, verifier, manifest, all six image
builds, and image verification exit 0; manifest and image receipt hash to
`4a63946a...5330` and `81f1eed2...95ec`. Codex/Claude/Hermes/OpenClaw/dashboard
images are `30ffdb63...9819`, `fe59a43f...2f8d`, `f9a8d750...a92a`,
`6e0f9958...4b29`, and `11f0a9a9...126b`.

Fresh absence `dd5b6e71...c301` exits 0. The sole no-bypass install
`4c3e1e1b...c97e` exits 1 only at attestation: finalization
`d5b3d58f-c94d-418f-b857-9a4c07de928c` accepts with `missing=[]`; parent
`01a0435e...ac6f`, trace `01a0435e...aeb0`, child `01a0435f...02ac`, native
decision `native-child-98105e66...a7a6`, complete v6 prompt
`e409b2c8...20bd`, verified delivery, exit-0 child, valid header, and one
completed wait agree. Parent/child/Store hashes are `5cea5e66...3e22`,
`1518a498...ecd1`, and `ceb65010...2fc8`; SQLite quick-check passes. AR-326
records the remaining lifecycle bug: after Codex returns, the bounded backend
collector asks a live-only parent resolver and receives `verification_refused`
despite the exact accepted terminal graph. Diagnostic `89fafc05...5b02`
isolates that lookup failure without changing the proof Store.

The regression-first AR-326 repair leaves hook-side parent resolution live-only
and gives only the post-return backend collector an exclusive accepted-terminal
mode. It requires one completed Codex run, one bound `accept/completed`
finalization with `missing=[]`, canonical non-pending metadata, and the existing
session, trace, route, delivery, and artifact agreement. The affected suite
passes 203 tests at `4e76af29...a318`; the named fast spine passes 860 tests with
3 skips at `8cda02e1...4312`; and complete decision conformance kills 165/165
mutations with source unchanged at `891defed...ab8`. All three exit 0 with empty
stderr. Retained exit-1 receipts prove the earlier protected UV Python lacked
Linux `pidfd_open` and the canonical system binary lacked pytest; neither run
changed source. A new exact build and fresh one-install Codex proof remain
required, so the prior failed attestation is not relabelled.

Clean AR-326 ledger `4b443be2f11045814250ab455d829800634c3909` now
produces wheel `aaf9b461...1f7d` (9,341,603 bytes) and sdist
`869b2842...545f` (25,888,743 bytes). Build, strict Twine, independent verifier,
all six image builds, and final image verification exit 0; manifest and image
receipts are `c8fdc3f6...9c9e` and `f91c05d1...adde`. Codex, Claude, Hermes,
OpenClaw systemd, and dashboard image IDs begin `1c4fea8a`, `a4dae27b`,
`e4cef33c`, `073a9d01`, and `9f484583`. The first generic OpenClaw build used
Node 22.22.0 and was independently refused; both images remain explicitly
tagged `node22-failed`, while the Node 24.15.0 rebuild passes.

New Codex container `cf983a11...79b1` is bound to the exact candidate/image and
is the thirtieth retained AR-297 proof container. Private input receipt
`018f6d4f...494f` and fresh absence `0a7d2818...50cb` prove mode-0600 auth and
config, exact config SHA `a4e213d6...7348`, Codex 0.149.1, and no pre-existing
Agency runtime, Codex config, system requirements, or managed relay. No install
has yet run in that container; its sole no-bypass install is the next live gate.

That first new container's sole install hashes to `40c1c188...7f5a` and exits 1
because the omitted CLI override left the activation window at its 180-second
default. Codex exits 124 just after dispatch: parent `01a043a2...0011`, trace
`01a043a2...ca32`, accepted sole `code-reviewer`, pending synthetic worker
`task:code_reviewer`, and two rollout hashes `586e8285...3de2` and
`fba3e1f9...35e9` are retained. No native child route, delivery, finalization,
or attestation exists, so the run never reaches AR-326's terminal collector.
The copied Store hashes to `e7bc0f97...9c55`, passes quick-check, closes the run
as `canary_failed`, and correlates at content-free receipt `5f76b443...6eaa`.
The container will not be reinstalled.

Second exact container `9806a82a...2a2b` passes private input and fresh absence
at `018f6d4f...494f` and `1849d13e...a74c`. Its sole no-bypass install uses
the proven `--activation-timeout 300`; Codex exits 0 without timing out and
proves one native route/delivery, complete prompt hash `e409b2c8...20bd`, an
exit-0 child, and accepted finalization `38c5914f...465c` with `missing=[]`.
Install receipt `ca1a6d2f...fcc1` exits 1 only because attestation is absent.
Store `6730ee75...3195` and parent/child rollouts `aeda3b86...fa59` and
`ee5d577e...005d` are retained.

Content-free replay diagnostic `dcc4d23a...23b6` proves AR-326's terminal
lookup succeeds and every persisted receipt field agrees except
`artifact_digest`. The live receipt hashes to `91bd1c0d...21ac`, exactly the
completed rollout's first 84,598 bytes and 16 complete JSONL records; Codex then
appends a seventeenth `task_complete` record, producing `ee5d577e...005d`.
AR-327 and ADR-0190 own an exact receipt-bound append-only prefix replay; no
second install will run in Qwen2.

The AR-327 regression-first candidate now reparses only the unique complete
JSONL prefix bound by the immutable receipt. The affected suite passes 211
tests with three known AR-323 schema-literal cases deselected, 17 conformance
tests pass, and both new mutations are killed with source unchanged. Exact
artifacts and one new clean Codex proof remain pending.

Committed-source replay against the exact retained Qwen2 Store and rollout
exits 0 at `f98bb268...7cb3`; both the read-only receipt projection and full
restricted verifier return staffed `verified_existing_receipt`. This is source
validation only: the failed installed candidate is not relabelled or mutated.

Clean AR-327 ledger `7dbd0cbc5cbc77e46fc795568bb63ddcf5e3ee6f` now
produces wheel `e117b362...fc03d` (9,344,796 bytes) and sdist
`ac30feb0...9fb6c` (25,929,703 bytes). Canonical build, strict Twine,
independent distribution verification, artifact manifest, all six image
builds, and final image verification exit 0. Manifest and image receipt hash to
`780512b2...b7876` and `00fcf8e6...5f76`. Codex, Claude, Hermes, OpenClaw
systemd, and dashboard image IDs are `206e94c4...a5b2e`,
`237c788d...d7e40`, `7869a7a3...121b8`, `91c3a5bc...0fde`, and
`1b0653a5...cb87`. One new clean Codex container, fresh absence, and its sole
300-second no-bypass install are the next live gate.

Exact Codex container `2ec2180b...17bb` passes fresh absence at
`e857f524...d9bd` against image `206e94c4...a5b2e`, candidate `7dbd0cbc`,
config `a4e213d6...7348`, private auth, Codex 0.149.1, and no pre-existing
Agency target. Its sole 300-second no-bypass production install exits 0 at
`54572077...ac82` with `complete=true`, managed-only eight-event policy, one
native route/delivery, one exit-0 child, one completed wait, accepted
finalization `56de0046...e30b` with `missing=[]`, valid response header, and
persisted current-profile attestation `ded810a5...6e66`.

Parent `01a043dc...1bff`, trace `01a043dc...d2c3`, child
`01a043de...206b`, native decision `native-child-7738d04b...c06f`, complete
2,379-character prompt `e409b2c8...20bd`, and delivery prefix
`ef67633a...0b0c` agree. Store correlation `ef8304ef...e30c` exits 0 with
SQLite `quick_check=ok`; Store and parent/child rollouts hash to
`7e767300...27b1`, `b3fc13a8...9274`, and `f7633d02...5e88`. Later read-only
status `e4755e50...66a3` exits 0 and reports `runtime-verified`, verified
attestation, current launcher artifacts, and current managed policy. AR-327's
exact rebuilt live gate is closed; ordinary post-install Codex loading remains
part of the four-harness unattended-process row.

The first exact Claude setup-only container exited 1 before invoking Agency
because its entrypoint tried to copy credentials before creating
`/root/.claude`; retained state and log receipts hash to
`2d2e7c80...1f9e` and `5eea0608...eff`. Replacement container
`d33914d6...9991` uses the same exact image, passes fresh absence at
`f95648d6...9919`, and records exit-0 dry-run `67f5125e...7467` followed by
one exit-0 production install `798da70f...5afa`. It registers and enables
bundle `ea4e9444...783f`; status, plugin, and marketplace receipts hash to
`bb4a673e...36fb`, `4003d55e...4f67`, and `c88bbcde...644f`. Its Store
`6d9568d0...4dc2` passes SQLite quick-check and contains no ordinary run.

Exact Hermes container `9d5cfe07...ccf0` proves the native UID/GID 10000
boundary. Absence `c90213d8...175c`, dry-run `f9c06879...9c59`, and the sole
install `d2d7ce1b...5ae1` all exit 0. Bundle `d7a3a3a7...3a33` is registered
and enabled; status and native plugin receipts hash to `5cd0d280...f88` and
`25d6f66f...36a`. Store `45f89485...887b3` passes quick-check with no
ordinary run, while native manifest and current launcher hash to
`e2b48933...1e7d` and `74da0cde...c6a`.

Exact OpenClaw systemd container `512df094...1fff` brings its root user manager
to `running` at receipt `2524b552...26a`. Fresh absence `534327ca...74a` and
dry-run `193e891f...6444` exit 0. The dry run creates only the empty Agency
ephemeral directory and no native plugin; that bounded diagnostic is retained
at `9108c029...8db0` rather than hidden. The sole production install
`9a0f49b5...1b7a` exits 0 with `complete=true`, runtime-verified bundle
`4d9afa0b...d79`, and all 13 hooks loaded at `bfa7557a...b3f7`. Store
`c53dc2a9...01b6` passes quick-check with zero runs; its count receipt, native
manifest, and launcher hash to `762636c2...2cd3`, `bcfdc272...380e`, and
`08a672a5...4c2`.

The first mode-0600 native profile used `task-agency-generator`, which the
authenticated pre-turn inventory `7163aa90...911a` proves does not exist; the
actual approved alias is `task-agency-generation`. This did not affect Agency
installation because no native model turn ran, but the earlier sanitized
receipts are retained as a configuration failure rather than promoted. Before
any ordinary model call, correction `65ceab8f...d161` exited 0. Current native
config SHA `88409233...e909` and sanitized receipt `2180a4dc...23e8` now prove
provider `openai-completions` at the loopback LiteLLM endpoint, exactly alias
`task-agency-generation`, and environment SecretRefs for both credentials.

The separate exact production-install row is therefore closed for Codex,
Claude Code, native-UID Hermes, and OpenClaw systemd. Registration, enablement,
runtime loading, and later ordinary turns remain distinct: row 6 must still
prove unattended Agency loading and a bounded ordinary process in all four.

Before the first later ordinary Hermes turn, authenticated alias creation
`d23cb3f6...f6c84` and sanitized native-state receipt
`517a40d3...0a51` bound stable alias `task-agency-hermes` to the approved free
Mistral Small 3.2 24B backend, loopback LiteLLM endpoint, truthful 65,536-token
context, disabled thinking, and an environment key reference. The mode-0600
native config itself hashes to `c4bcf36a...68549`; no secret value is retained.

The first normal UID-10000 `hermes chat -q` process used the same 397-byte task
`fb36e4a...26235`, no bypass/ignore/safe flags, a four-turn ceiling, and
process-memory credential injection. The native process exits 0 at
`bde29436...120`, but Agency correctly replaces its draft with the fail-closed
response at `cef7b4ec...f849`. Store `01ca5974...b14` passes quick-check and
correlation `6011ee8b...a5fd` proves accepted route
`section-508-accessibility-specialist`, six alias-only model receipts, and one
`response_invalid` finalization missing the governed header fields. Native
state `a71855e7...524e` passes quick-check; receipt `87866dee...c7e9` proves the
exact 3,227-byte card `589a6e0c...303e` appears once in the 7,321-byte API user
content. That establishes full workforce-prompt visibility, not successful
completion: the raw 178-byte model response serialized a `clarify` JSON object
as text, made zero native tool calls, and did not invoke `agency_finalize`.

Hermes plugin doctor `5de107fb...c496` independently reports one registered
Agency tool and eight hooks, while tool inventory `ef80af98...c1a5` shows the
Agency toolset enabled. Mistral template receipt `706c4d11...98c8` contains
native tool-call branches. The remaining mismatch was the AR-297-owned alias's
LiteLLM `ollama/` text transport, which cannot preserve that native tool-call
envelope unless JSON format is separately forced. It was removed at
`958a2d6c...8c40` and recreated at `584558db...639` as the same alias, backend,
endpoint, context, and thinking setting using `ollama_chat/` with truthful
function-calling metadata; deployment `4089bb62...f0fe` is the sole current
deployment. No new model choice was made. The corrected ordinary Hermes retry
ran through the same normal UID-10000 process and again exited natively 0. Its
stdout, stderr, and exit receipts hash to `a94a1e6c...8a68`,
`988c3550...2bfb`, and `bde29436...120`; the stdout warning
`Unknown toolsets: agency-runtime` precedes Agency's fail-closed replacement.

R2 Store `5c95a565...cdd4` and native state `a937c8f9...b1f7` both pass
SQLite quick-check. Correlation receipt `2ebc93fd...712e` binds run
`6223f95c...55d3`, trace `20260827_164059_043752:3e23ee93-931c-4523-a3a8-`
`e8dfbb8da4f6:ff1a5de7`, accepted routing to the same specialist, all five
Agency inference routes, and terminal `response_invalid` finalization
`d4960cf6...f2eb`. Native receipt `a2a44504...761b` exits 0 and proves the
same 397-byte task plus one exact 3,227-byte card occurrence in the 7,321-byte
API content. The assistant returned 842 bytes at `c97fa7fa...fb19` with
`finish_reason=stop`, made zero tool calls, and requested access instead of
invoking `agency_finalize`.

The corrected chat transport therefore rules out the original serialization
mismatch but does not close ordinary Hermes. Runtime inspection finds the
dynamically registered `agency_finalize` in registry toolset
`agency-runtime`, while the actual 21-tool model definition omits it and the
plugin manifest declares no `provides_tools`. The next bounded package must
isolate that registration-to-model-definition gap before another live call;
the first two failures remain retained evidence rather than being retried away.

R3 removed task incompleteness as an alternative explanation without changing
the model or configuration. The exact 684-byte self-contained HTML-review task
hashes to `7411494b...49de` on both host and container, prohibits external
access and follow-up questions, and runs through the same ordinary UID-10000
process. Native stdout/stderr/exit hash to `a94a1e6c...8a68`,
`9e844172...fff1`, and `bde29436...120`; the process again exits 0 only because
Agency replaces its draft with the fail-closed response.

R3 Agency Store `80942b3b...3944` and native state `00211b3c...b1c` pass
quick-check. Correlation `6d1d3f52...8a29` binds accepted routing to the same
specialist, all five Agency inference routes, run `299f0edf...39dc`, and
`response_invalid` finalization `e98c98df...4d8c` missing only
`actual_model_selected`. Native receipt `f3b89dac...cf92` exits 0 and proves
one exact 3,227-byte card occurrence in the 7,608-byte API content. Mistral
returned a complete 3,627-byte report at `62b553e6...5fd0`, copied the initial
header snapshot, and still made zero tool calls despite receiving the exact
direct-or-`tool_call` finalizer instruction once.

Offline native inspection confirms the host bridge itself is usable: the raw
tool list contains `agency_finalize`, the model-visible list replaces it with
`tool_search`, `tool_describe`, and `tool_call`, the embedded catalog lists the
finalizer, and `tool_describe` returns its required `draft_text` schema. Three
bounded attempts therefore establish that the approved Mistral Hermes route is
not reliable enough for the governed finalization contract. Selecting another
Hermes model/alias target requires the mandated owner interview before R4.

The first later ordinary Claude process is retained as a bounded negative, not
retried away. R1 started the installed `SessionStart` and `UserPromptSubmit`
hooks but omitted process-memory LiteLLM authentication and then found that its
copied first-party OAuth session had expired. Native stdout
`94a376d5...8d2d` and Store receipt `b5006ee0...cdd4` preserve that boundary.
For R2, the current credential was restored from the same approved read-only
host bind and the LiteLLM key existed only in the child process. The ordinary
Claude 2.1.239 command used `dontAsk`, no model override, no activation bypass,
and the exact 683-byte task `abfcd7ee...3408`.

R2 native stream `13864e9a...de92`, Store correlation
`ef24801d...b6fb`, and content-minimized receipt `c5c3b811...b54f` prove
session `29700000-0000-4000-8000-000000000002`, accepted routing to
`section-508-accessibility-specialist`, all five configured alias-only Agency
receipts, and one exact 3,227-byte card `589a6e0c...303e` in the 6,511-byte
additional context. Claude then failed its own provider turn because the
unchanged `claude.ai` OAuth session was expired and could not refresh. The
Store therefore truthfully ends the run with no terminal finalization. A third
unchanged draw is prohibited; the same-method credential needs operator
refresh before Claude can complete.

OpenClaw's pre-turn plugin list `fba378be...935c` reports
`agency-preflight` enabled and loaded, and doctor `9d8ec6e3...b4e6` reports no
plugin issue. The later ordinary embedded process used the corrected native
`litellm/task-agency-generation` alias, disabled thinking, both credentials in
process memory, no model override, and no bypass. It exited 0 after 187,420 ms;
stdout/stderr/exit hash to `909bbfe0...c73`, `78390e2d...81c4`, and
`bde29436...120`.

OpenClaw native receipt `0e4ecc3d...c53` binds session
`29700000-0000-4000-8000-000000000101`, run
`851c3ad2...9ec8`, quick-checked native state `f6d6c301...acb`, and trajectory
`260c58b2...225`. Its 7,591-byte submitted prompt contains the exact 683-byte
task and one exact 3,227-byte card, with 35 native tool definitions. All five
Agency alias receipts succeed and Store correlation `6bf28dbe...367b` binds
the accepted route. The approved 14B abliterated native generation route then
returned exactly two bytes, `{}`, at `44136fa3...aff8`; Agency correctly
recorded `response_invalid` rather than promoting native exit 0. A replacement
OpenClaw alias/model is an owner-interview choice before R2.

The first later ordinary Codex process used Codex 0.149.1 with ChatGPT auth, no
model override, the read-only sandbox, an empty dedicated Git worktree, and no
approval, sandbox, or hook-trust bypass. Native stdout/stderr/exit hash to
`f87b33ca...c864`, `6c69d1ab...9566`, and `bde29436...120`; the unrelated
remote Cloudflare MCP auth diagnostic did not stop the turn. Parent
`01a04449...241e` and child `01a0444b...5c86` both completed natively.

Codex native receipt `a18f2b10...71ed` proves the exact 2,659-byte
`accessibility-auditor` card `c3cfc098...5848` occurs once in both parent
`0eeaa6b9...07a0` and child `bfd567d7...fa99` rollouts. Store correlation
`06dcfe2f...e3e` passes quick-check, binds the parent route and all five Agency
aliases, and records finalization `a6bf6ed1...d499`. Codex chose an opaque
collaboration child despite the self-contained task; Agency therefore withheld
the otherwise complete 3,337-byte report because only `evidence_verification`
was missing. A direct-only, no-delegation R2 is the next live step and requires
no model or auth change.

End-of-package telemetry `63bf6e3a...beda` reports 45.6 percent remaining and
requires this clean substantive/ledger checkpoint before the next live call.

After clean ledger `b66bb020`, Codex R2 used the exact retained 824-byte
direct-only task `3ef304e5...dd3`, the same ChatGPT auth and default model,
read-only sandbox, managed policy, and process-memory LiteLLM credential. It
made no tool or collaboration call. Native stdout/stderr/exit hash to
`69f672c2...2874`, `5079dcb4...365f`, and `bde29436...120`; the only stderr
line is the same unrelated optional Cloudflare MCP OAuth diagnostic.

Native receipt `53598f2a...5fd5` binds sole thread
`01a04454...fb65`, one 4,547-byte response `43b2e44c...0b32`, no child, and
one exact 2,659-byte `accessibility-auditor` card in rollout
`693e9dfe...4cd9`. Store correlation `b269dc11...478d` passes quick-check and
binds trace `01a04454...12f6`, one accepted route, all four used alias-only
receipts, and finalization `f7937fc5...46e6` with `action=accept`,
`terminal_status=completed`, and `missing=[]`. Later ordinary Codex loading is
therefore complete; Claude, Hermes, and OpenClaw remain open independently.

The exact wheel is now also installed on the Linux host in owner-private venv
`~/.agency-runtime/release-venvs/ar297-7dbd0cbc`. Venv creation, wheel install,
and `pip check` exit 0; the wheel remains `e117b362...fc03d`, and receipt
manifest `4b48dcc8...7e6b` binds the retained host evidence. A process-injected
LiteLLM key was first rejected from dashboard planning as non-durable, and the
live OpenClaw gateway independently blocked mutation. After a native exit-0
gateway stop, the no-secret exact dry run exited 0. The single attended
`install --config ... --all --json` receipt `00d51490...b559` then exited 1
solely because refreshed Codex correctly remained `activation_required` with
no bypass; Hermes, OpenClaw, Claude, and the dashboard all completed.

Installed bundle digests are `04fdaf88...3195` (Hermes),
`c7f12929...cc00` (OpenClaw), `b82c0201...eb41` (Codex), and
`05be2f52...b8a6` (Claude). OpenClaw's native restart exited 0 and its second
deep RPC status `78bab6d1...34a1` exited 0 with active/running state, no version
drift, and a clean config audit. Independent packaged-context attestation
`ec2f8fdd...9292` exits 0 and binds the candidate venv to immutable runtime
`dbf1581f...f301`; the first checkout-contaminated probe is retained as the
expected exit-1 negative rather than relabelled.

The user-scoped systemd dashboard unit and manifest hash to
`459e035c...e5a0` and `0cc62bc...735b`. It is enabled, active/running, has zero
automatic restarts, and preserves `UMask=0077`, `NoNewPrivileges=yes`,
`PrivateTmp=no`, owner runtime-directory mode 0700, loopback address families,
the exact immutable runtime, and config `a4e213d6...7348`; contract receipt
`b3ffa572...f888` exits 0. An Agency-owned restart `b72f17e7...94d8` exits 0
and rotates the mode-0600 descriptor from fingerprint `e9c82e0b...e2fe` to
`7e536f42...f6d4`.

Post-restart HTTP proof `358ab92e...d94f` exits 0: unauthenticated health is
401/no-store, authenticated health and workforce detail are 200/no-store, and
the exact stored `accessibility-auditor` prompt is untruncated at 2,659 bytes
and `c3cfc098...5848`, byte-identical to the installed asset. Headless browser
proof `7b22dd85...c483` likewise exits 0 with 19 authenticated 200 responses,
no console/page/request failures, immediate token-fragment removal, and the
complete prompt visible in the DOM; screenshot `222d5109...b5ac` retains the
expanded owner view without a token. No dashboard inference was invoked or
claimed: the service process deliberately has no transient `LITELLM_API_KEY`,
so this bounded proof covers authenticated operations and prompt visibility.
The exact host-install/dashboard row is complete; ordinary Claude, Hermes, and
OpenClaw turns, final named gates, and teardown remain.
Checkpoint metadata, policy-availability, worklog-index, documentation, and
diff checks all exit 0; their output hashes are `6f128b54...899c`, the empty
SHA, `244c6d18...fa7a`, `45466cc3...8ba`, and the empty SHA respectively.

A later normal current-profile Codex activation verifier used the exact host
bundle and process-memory LiteLLM credential with no bypass. Receipt
`933bc916...bb4` exits 1 before model invocation because the attended trust
inspection reports all eight hook events unobserved; it leaves configuration,
runtime controls, roster, dashboard, adapter, and trust store untouched. This
retained limitation does not replace the completed dedicated-container Codex
proof or reopen the exact host/dashboard installation row.

Every named repository gate now passes on the committed tree. Metadata checks
912 Markdown documents (`c5f34de1...8b7f`); policy availability is empty-output
clean; worklog currentness (`25ea7b84...ef96`) and documentation validation
(`cfaaa7c5...3444`) pass. Ruff lint (`82b3e6a6...4f18`) and format
(`82826f75...0f1`) pass. The named warning-strict Python spine passes 860 tests
with 3 skips (`25cc4f01...4cb`), dashboard UI passes 138/138
(`2eb1981a...3ef9`), and routing 1.4.0 passes (`eeb12164...10d4`). Decision
conformance's protected, `umask 077` repository run passes its baseline and
kills 167/167 mutations with zero survived/invalid and source unchanged
(`9a45044f...0a71`); the prior no-pytest and ambient-`0002` private-boundary
failures remain retained at `1fe3f42b...f88d` and `4dd2f8f3...da6b` rather
than relabelled. Final diff output is empty. Every successful gate has exact
exit 0 receipt SHA `bde29436...120`.

The next ordinary-process preflight found the host's existing same-method
`claude.ai` OAuth session refreshed and logged in. The exact Claude R2 proof
container's read-only host bind differed from its stale internal credential;
an owner-private copy refresh exited 0 without printing credential bytes, and
sanitized native status `ca740051...3af1` now reports first-party
`authMethod=claude.ai` and `loggedIn=true`. No auth method or model changed.

That sanitized status was only local credential-presence metadata, not a
successful provider exchange. After clean checkpoint `606ce9e5` / `0ac06c11`,
the materially refreshed credential justified one R3 rather than an unchanged
retry. Immediately preceding telemetry `85b38b88...6620` reported 24.5 percent
remaining and a clean required checkpoint. The normal Claude 2.1.239 process
again used `dontAsk`, no model override, no activation bypass, the exact
684-byte task `7411494b...49de`, and sole native session
`29700000-0000-4000-8000-000000000003`.

R3 native stdout and exit hash to `456775a6...e4b3` and
`85acfd2e...5409`; the process exits 1. Content-minimized native receipt
`a712f945...ba82` nevertheless exits 0 and proves both Agency hooks completed,
the exact 3,227-byte prompt `589a6e0c...303e` occurs once in the 6,511-byte
additional context, and the exact task occurs twice in the owner-private native
session `55eab009...0ffb`. Store correlation `ea44335e...71b7` passes
quick-check and binds run `b0b4866b...0115`, trace
`8d976302...e9aa`, accepted routing to
`section-508-accessibility-specialist`, all five alias-only Agency receipts,
and one specialist load. No terminal finalization exists because Claude's
provider response again reports `authentication_failed`: the OAuth session is
expired and could not be refreshed. No unchanged R4 is admissible; a genuine
first-party `claude.ai` re-login is the remaining Claude operator gate.
Package-end telemetry `b755a171...193c` reports 56.9 percent remaining and
permits normal same-task continuation after this recovery pair.

Authenticated LiteLLM inventory `73551634...0551` shows exactly the seven
current `task-agency-*` aliases. Sanitized snapshots retain sole deployments
for the Qwen 3 32B child judge (`54a2c740...d9ee`), rejected Mistral Hermes
route (`ebc865a0...1ad`), and 14B generation route (`86751a87...2d6`). Local
model inventory `e48128f2...40b0` confirms `qwen3:32b` remains resident, but no
Hermes or OpenClaw alias/model change was made without the owner interview.
Pre-final Docker inventory `6d0c7888...81f7` exits 0 and binds exactly 36
AR-297-labelled containers: 35 running and one exited.

The owner then approved the exact remaining harness route and same-method
Claude.ai login: already-resident free
`qwen3-coder-30b-a3b-128k-rocm:latest` behind stable aliases
`task-agency-hermes` and `task-agency-openclaw`, authenticated loopback
LiteLLM with `ollama_chat`, 65,536 configured context, thinking disabled,
tool calling enabled, and all other aliases unchanged. No-mutation plan
`94827ae4...a5a7` exits 0 and binds native model metadata with tools,
completion, Q4_K_M 30.5B, and truthful 262,144 maximum context.

The first two bounded mutations are retained exact rollback negatives.
LiteLLM returned HTTP 200 while `/model/update` changed Hermes transport
parameters but preserved stale Mistral `model_info`; the independent exact
projection rejected it. Receipts `202e0f47...f143` and
`e95f446b...75e2` prove the new OpenClaw alias was deleted, Hermes was restored,
and all unrelated aliases stayed unchanged. The corrected delete/recreate
transaction `d69aa6b...af4d` exits 0. Independent verification
`a1e2381d...a5dd` exits 0 with exactly eight `task-agency-*` aliases, sole
approved Hermes/OpenClaw deployment IDs, exact 65,536/no-thinking/tool
metadata, candidate context/capabilities, and no model invocation; the six
unrelated alias projection remains `1e3c1db5...7f08` before and after.

OpenClaw's owner-approved native transition `e97e02e2...deba` exits 0 and
changes only its primary plus provider model ID/name from
`task-agency-generation` to isolated `task-agency-openclaw`. Config SHA changes
from `88409233...e909` to `7b8fd421...6c26`; credential SecretRefs, empty
fallbacks, Agency plugin, and every unrelated field remain exact. Independent
receipt `a141d193...e1ce` and native schema validation
`275572d1...cfef` exit 0. A later user-service start attempt exits 5 at
`5d96cc23...fc13` because this proof container has no gateway unit; no unit was
created or changed, and the required ordinary proof uses OpenClaw's embedded
process as R1 did.

Immediately preceding live-probe telemetry `e9b158b2...2f40` reports 17.4
percent remaining and requires this clean recovery pair before any approved
Qwen model invocation.

After clean checkpoint `abb79e1f` / `94d25bb4`, fresh telemetry
`85b85aa4...b668` reported 82.4 percent remaining. Authenticated, no-cache
tool smoke `2b25ad2a...d1f15` exits 0 through loopback LiteLLM: both
`task-agency-hermes` and `task-agency-openclaw` return HTTP 200, their exact
deployment IDs, no fallback, no text, and exactly one `agency_finalize` call
with byte-identical arguments. The receipt retains no response content.

The following normal UID-10000 Hermes R4 used the unchanged 684-byte task,
four-turn ceiling, disabled thinking, and no bypass flags. Native stdout,
stderr, and exit hash to `a94a1e6c...8a68`, `ae72e6e4...dad1f`, and
`bde29436...120`; session `20260827_192506_ed39a0` made three API calls and
five native tool calls. Native receipt `c484e1bb...8fb1` proves the exact
3,227-byte specialist card occurs once and both SQLite copies pass
quick-check. Store receipt `d38412bb...5fbe` binds accepted selection and load
of `section-508-accessibility-specialist` plus every Agency inference alias.
Qwen used four `tool_describe` calls and one `tool_search`, but Hermes's default
progressive disclosure withheld the plugin finalizer from the direct tool
array; no `agency_finalize` call occurred and Agency correctly retained
`response_invalid`. R4 therefore rejects a remaining model-format explanation
but does not close the Hermes ordinary-turn gate.

The bounded native repair changes only this AR-297-owned Hermes config's
`tools.tool_search.enabled` value to `off`, making its sole plugin finalizer
eagerly visible without disabling Agency policy, using an activation bypass,
or changing a model, endpoint, credential reference, thinking level, or
foreign policy. The native transition `717d7279...a362` exits 0 and changes
config SHA from `c4bcf36a...68549` to `80813e3d...36b3`, preserving mode 0600
and UID/GID 10000. The first evidence helper `a46a312a...a42d` exits 1 because
it checked the wrong native provider key (`base_url` rather than `api`);
corrected independent verifier `da5a737e...94ea` exits 0, proves that sole
exact delta and no inline secret, and invokes no model. Pre-R5 telemetry
`5f738310...ee5f` reports 39.9 percent remaining, so no R5 invocation is
admissible until this clean recovery pair exists. The approved official
Claude.ai login is open at its first-party browser callback but is not yet
claimed complete.

After clean checkpoint `e23f45c6` / `f45ad0ab`, immediately preceding
telemetry `8ba51fdd...0336` permitted R5 under the existing checkpoint. Native
R5 receipt `275e7154...116b` and Store correlation `9fa22217...7e03` prove
session `20260827_193602_81f0fd`, accepted routing and exact specialist load,
one exact card, all five Agency inference aliases, and exactly one native
`agency_finalize` call. Finalization `940b9180...4f91` commits `missing=[]`,
`status=completed`, and accepted response hash `fe57dceb...4fde`.

R5 still does not close Hermes: its follow-up model text hashes to
`25c20313...9341` rather than the accepted tool result. The output hook
correctly returns the same bounded block `a94a1e6c...8a68`; stderr and native
exit are `8afe29cc...0707` and `bde29436...120`. This isolates exact replay
after successful finalization, not routing, prompt visibility, tool exposure,
or Store acceptance. AR-288 is reopened locally; no tracker was created.

The regression-first repair retains failing receipt `cad6beee...d937`, teaches
default Hermes tool-search discovery, and replays only a bounded, one-shot,
trace-scoped cached tool result that a separate bridge call matches to the
authoritative completed Store hash. It never accepts the rewritten model text,
does not change native config or request another model pass, and preserves
disabled/unavailable/rejected behavior. Completion, parity, installer, and
smoke suites pass 236 tests at `68ade380...3ffc`. Exact artifacts, clean
installs, named gates, and a default-config live turn must be refreshed from
the eventual substantive commit before any Linux GO.

Substantive Hermes repair `5d478c3323a255c6eea6f856b6db294d7402c0b0`
and clean ledger candidate `e17e5221657ec90df8092879cf9d5c79d65ecb50`
now produce exact wheel `8b35c8f6...d897` and sdist `7e9f7ad6...9287`.
Canonical build, strict Twine, independent distribution verification, six
image builds, and independent label/version verification all exit 0; artifact
manifest and image receipts hash to `3ae9f798...86b6` and
`e3e6302d...f947`.

Four new actual-install witnesses independently prove pre-install absence and
complete once from exact images. Codex receipt `c41e8eae...0039` binds bundle
`9bcb81e6...454e`, managed policy with no activation bypass, one verified
native child, a valid exact header, `missing=[]`, and current-profile
attestation; independent Store receipt `1ca3bf03...cf6` passes quick-check.
Claude receipt `1917bec2...575` binds registered/enabled bundle
`7ffd1c4c...c53`. UID-10000 Hermes R2 receipt `5c3b902b...838` binds exact
default `task-agency-hermes` configuration and bundle `06c68be0...b4e`; native
doctor passes with one tool and eight hooks. OpenClaw R2 receipt
`df4601f0...b12` binds the sole LiteLLM provider/primary
`task-agency-openclaw`, empty fallbacks, SecretRefs, systemd user-manager
contract, bundle `25ad98ae...34cb`, and runtime-loaded 13-hook plugin. All four
installed Stores pass quick-check. Diagnostic Hermes R1 and OpenClaw dry-run
witnesses remain labelled for final teardown; 42 AR-297 containers now exist.
Package-end telemetry `4e0e2fb9...f1fce` reports 21.4 percent remaining and
requires this clean recovery pair before any next live process.

The fresh default-config Hermes ordinary process now closes AR-288 and its
current AR-297 matrix cell. Immediately preceding telemetry used the clean
`aa834796` / `5b29da9b` checkpoint. UID-10000 session
`20260827_201909_a6a13c` used the exact 684-byte task `7411494b...49de`,
default progressive tool disclosure, stable LiteLLM alias
`task-agency-hermes`, disabled thinking, and no bypass. Native stdout/stderr
and exit hash to `69affec8...d98`, `55098ee0...e4e`, and
`bde29436...120`; stderr contains only Hermes's deprecated
`TERMINAL_CWD` warning.

Native state receipt `f33f7457...100` proves one exact 3,227-byte
`section-508-accessibility-specialist` card in the 7,729-byte API content,
four API calls, two progressive `tool_search` calls, exactly one
`agency_finalize`, and one mandatory follow-up. Store correlation
`f2516e6a...d3e` passes quick-check, binds completed trace
`20260827_201909_a6a13c:35d9bbf4-282c-4759-8e4c-1453a70daf91:fb8114f4`,
accepted selection/load, all five required Agency alias groups, and terminal
acceptance with `missing=[]`. The accepted finalizer result and exact visible
response both hash to `ad8a06d3...eeaa`; the model follow-up instead hashes to
`473a37ba...d3e`, proving trace-scoped replay—not model coincidence—delivered
the authoritative text. Independent receipt `3c40a9bf...8959` exits 0 and
also proves both SQLite copies healthy and post-install/post-live native config
byte-identical at `2552f21c...e680`. Codex, Claude, and OpenClaw current-candidate
ordinary cells remain independently open.

The fresh exact Codex container now also passes its later ordinary cell. Two
pre-model setup receipts remain as honest negatives: native stderr
`d2cbaf84...38f3` records the initially absent work directory and
`dd701e71...324d` records the empty directory before Git initialization. Both
fail before hook or model work. After creating the same empty dedicated Git
repository used by the prior control, telemetry `149b846c...6749` (receipt path
`codex-ordinary-r3-prelive-context.json`) confirmed the clean `2ae22537`
checkpoint and admitted the changed-condition R3.

Normal Codex 0.149.1 session `01a044ee-8605-7301-adfd-6474eb422291`
then exited 0 with default ChatGPT model, `approval_policy=never`, read-only
sandbox, exact 824-byte direct-only task `3ef304e5...dd3`, no tool or
collaboration call, and no child. Native stream, rollout, and receipt hash to
`a204142a...7ad1`, `a6754b55...4164`, and `8355a9a6...7590`; the rollout
contains one exact 2,659-byte `accessibility-auditor` card
`c3cfc098...5848`.

Store correlation `7e39f736...d921` passes quick-check and binds trace
`01a044ee-86ba-7ee3-ae93-3f976bc4da77`, accepted selection/load, four
successful alias-only generation/embedding/critic receipts, and completed
finalization `a6e3bd79...7e35` with `missing=[]`. Its accepted response hash
`31f67a63...8302` exactly matches the sole 4,461-byte native answer.
Independent verifier `2ae0bdde...4a79` exits 0, rechecks all correlations, and
proves the mode-0600 exact config, managed requirements, and relay hashes remain
unchanged on image `28c3fd34...8797`. Package telemetry `ca37511b...1ba0`
reports 35.0 percent and requires this recovery pair before OpenClaw.

The fresh exact OpenClaw systemd container also passes its bounded later
ordinary loading cell. Immediately preceding telemetry receipt
`13a15d89...1bc5` used the clean `65ef42f2` / `58bf9ca7` checkpoint. Normal
embedded session `29700000-0000-4000-8000-000000000201` invoked the exact
683-byte task `abfcd7ee...3408` with thinking off and sole native provider/model
`litellm/task-agency-openclaw`; no model override, fallback, activation bypass,
or configuration mutation occurred. Native stdout/stderr/exit hash to
`0663ad32...f0d0`, `dafd580e...2b96`, and `bde29436...120` after 235,821 ms.

Independent native receipt `bb90b2fc...9841` exits 0 and binds run
`8fb5e4cc-6263-4dc7-8338-d9dce3e08877`, one exact 2,659-byte
`accessibility-auditor` card `c3cfc098...5848` in the 6,936-byte compiled
prompt, 35 native tools, and one 3,784-byte nonempty response
`9005a854...610f`. Native session and trajectory hashes are
`e0ce63a5...8ad0` and `5de86189...dcf9`; the native state SQLite quick-check
passes at `1ea2b5cf...ca73`. Store backup `7be84928...47c3` passes quick-check
and correlation receipt `1a4a1a4f...a2f5` binds accepted selection and load of
`accessibility-auditor` plus all five required alias-only Agency inference
receipts.

The Store run truthfully remains active without a terminal finalization: this
ordinary embedded command requested no channel delivery, and OpenClaw invokes
its authoritative `reply_payload_sending` full-envelope gate only for an
outbound channel payload. The shipped production package omits its private
synthetic QA channel. This is therefore a bounded unattended Agency-loading
PASS, not a channel-delivery claim; weakening the final-only boundary,
installing a test-only transport, or silently choosing an external channel was
rejected. Exact native config validation still exits 0. The OpenClaw matrix
cell closes while its non-delivery limitation remains explicit.

The exact Linux-host Hermes load then exposed AR-328: Python wrote an
unmanifested `__pycache__/__init__.cpython-311.pyc` into the otherwise exact
managed plugin tree. Deleting it once would not survive restart. The bounded
repair manifests a POSIX cache guard, seals only that namespace to 0500/0400,
records and strictly validates its policy, and leaves the owner-private plugin
root movable for upgrade, rollback, and uninstall. Regression-first failure
`751276ea...e3a` exits 1; the repaired broader installer surface passes 359
tests with 2 skips at `981fbbc8...ddd0`, while focused Ruff and docs pass. This
source change supersedes `e17e5221` as the final candidate, so exact artifacts,
images, four clean installs, and their later-process evidence must be rebuilt.

Clean ledger `e0b0b25c30083b09743fe1a04f2a0ad4cdf4e533` produces wheel
`75d63ff9...3762` (9,351,340 bytes) and sdist `2b1ae7ec...79d9`
(26,052,593 bytes). Canonical build, strict Twine, independent distribution
verification, the artifact manifest, and all six final image builds exit 0.
The first independent image run exits 1 because it detects an accidental Node
22 OpenClaw base; that receipt is retained. Rebuilding only the OpenClaw pair
with the established Node 24.15 pin makes the final verifier pass at
`07f372e3...eb9a`. Codex, Claude, Hermes, OpenClaw systemd, and dashboard image
IDs begin `c8e7a265`, `93eb1f9e`, `3a4cac26`, `c3d712ec`, and `4d2ccddc`.

Final candidate setup then proves Codex, Claude, and UID-10000 Hermes remain
absent after successful dry-runs. OpenClaw's dry-run exits 0 but strict receipt
`8ffcb927...af70` detects its empty runtime-home namespace, so that container
is retained as a diagnostic rather than cleaned and reused. A second untouched
OpenClaw container passes absence at `5feaa49c...2cdd`.

Claude, Hermes, and OpenClaw R2 installs exit 0 at `579d65c8...a0e9`,
`4d04f360...02d8`, and `4debebf3...c748`; their exact bundle digests are
`b2151080...b119`, `eab39058...c15e`, and `c7a68bb8...8f90`. All three Stores
pass quick-check. OpenClaw's root user manager, exact sole
`task-agency-openclaw` route, SecretRefs, empty fallbacks, and 13-hook runtime
pass independently. After native Hermes doctor, strict receipt
`d7bc15f0...d8f8` proves the exact 0700 root, 0500 guard, 0400 marker, policy,
and zero `.pyc` entries. Telemetry `5af0422f...082c` reports 26.1 percent and
forces this clean recovery pair before the final Codex live install.

After clean recovery `d2ae9b57` / `6781c59b`, telemetry immediately precedes
the sole final Codex transaction. Exact install receipt `ce370bc8...1330`
exits 0 with bundle `96b44257...7785`, one completed host-created child, one
native delivery, one accepted finalization, `missing=[]`, persisted
current-profile attestation, managed trust, and no activation bypass. Store
correlation `d9469980...d5b9`, artifact backup `8831ece2...3940`, and status
`e1c700b5...fd1f` independently pass. All four exact final-candidate install
rows are now closed; their later ordinary unattended rows remain separate.

The final `e0b0b25c` Codex and Hermes containers now pass their later ordinary
unattended rows. Codex pre-live telemetry `0092ba2f...722d` precedes normal
0.149.1 session `01a04546-933a-7c61-93a8-fb6129ffe24d`; native stdout,
stderr, and exit hash to `ded07214...80e1`, `2f47dea9...0a07`, and
`bde29436...0120`. Independent receipt `8b372e4c...2423` exits 0 and binds
trace `01a04546-9377-7a73-9f23-2d44e09beac8`, the exact 824-byte task, one
exact 2,659-byte `accessibility-auditor` card, no child or collaboration call,
read-only sandbox, `approval_policy=never`, accepted selection/load, four
successful alias-only generation/embedding/critic receipts, completed
finalization, and `missing=[]`. The sole 5,523-byte native response exactly
matches the Store response hash; config, hook, requirements, image, and mode
checks remain exact. Native and Store source receipts are
`a4033406...fb67` and `eebb3782...f6dc`.

Hermes pre-live telemetry `1a48fef3...c23e` precedes normal UID-10000 session
`20260827_221502_139df0`; native stdout, stderr, and exit hash to
`6da1a595...a71`, `e2173f25...42d`, and `bde29436...0120`. The first native
summary intentionally retains exit 1 because its helper defaulted to a
different historical task digest; corrected explicit-task receipt
`d8e9eab7...9fe3` exits 0. Independent verification `9ee57328...f2f7` binds
trace `20260827_221502_139df0:e0f86b7b-0295-445d-a6bf-f21309621df7:0cfa5f1f`,
the exact 684-byte task, one exact 3,227-byte
`section-508-accessibility-specialist` card, one `tool_search`, exactly one
`agency_finalize`, accepted selection/load, all five required alias groups,
completed finalization, and `missing=[]`. The accepted finalizer and visible
response both hash to `5d3f0b59...563d`, distinct from the mandatory model
follow-up `444f5bbf...da8e`, proving authoritative replay. Both Stores pass
quick-check and native config remains byte-identical at `2552f21c...e680`.
OpenClaw telemetry `197e4afa...0922` reports 48.1 percent, requiring this clean
checkpoint before its live invocation; OpenClaw and Claude ordinary rows remain
open.

After clean checkpoint `14cab69b` / `9a87eb57`, fresh telemetry
`45d11f26...b17f` immediately precedes the final OpenClaw ordinary process.
Normal embedded session `29700000-0000-4000-8000-000000000301` exits 0;
native stdout, stderr, and exit hash to `c20a26f2...f1a`,
`25f89ac5...d1c4`, and `bde29436...0120`. Native receipt
`d29ed865...756f` proves the sole `litellm/task-agency-openclaw` host route,
thinking off, one exact 683-byte task, one exact 2,659-byte
`accessibility-auditor` card in the 6,936-byte compiled prompt, 35 native tools,
successful non-timeout termination, healthy state SQLite, and one nonempty
3,993-byte response `73f1216e...cc7d`.

Store receipt `a38c5a82...9de2` passes quick-check and binds trace
`399a365a-482e-4155-8410-ac1e6ddfb87a`, accepted specialist selection/load,
and five successful alias-only Agency inference receipts across generation,
embedding, reranker, and critic groups. The run truthfully remains active with
no terminal finalization because the embedded invocation has no outbound
delivery channel; no boundary was weakened and no synthetic or external
channel was installed. The obsolete generation-alias sanitizer is retained as
exit 1 at `92a9f1c0...cb81`; the current exact alias verifier exits 0 at
`d521f10b...65ba` and proves post-live config byte-identical at
`c6632a1f...67b4`, with sole provider, empty fallbacks, SecretRefs, and plugin
unchanged. Independent final receipt `3c300451...5a02` exits 0. Package
telemetry `5bf27f4d...b073` reports 25.4 percent and requires this recovery
pair. Only Claude remains open in the four-harness ordinary matrix.

The final Linux host refresh uses the exact `e0b0b25c` wheel
`75d63ff9...3762` and mode-0600 exact config `a4e213d6...97348`. The first
read-only attestation correctly rejects the pre-AR-328 Hermes tree. After a
safe OpenClaw gateway stop, ready dry-run `34cd4a78...4e9d` exits 0 and the
bounded live transaction `68822689...33af` exits 1 only because attended Codex
activation remains a truthful host limitation; Hermes, OpenClaw, Claude, and
the dashboard complete. OpenClaw is restarted and its deep RPC receipt
`561de9bd...df54` exits 0. Independent attestation `64564e4a...bc24` exits 0
and binds every host bundle to private runtime `d054649e...d3d7`, with the
systemd-user dashboard active, enabled, and at zero restarts.

Authenticated HTTP proof `26923d58...bb2` and browser proof
`65162e02...e32c` exit 0. They distinguish 401 from authenticated 200, require
`no-store`, remove the bearer fragment, and render the exact untruncated
2,659-byte `accessibility-auditor` prompt `c3cfc098...5848`; screenshot
`222d5109...b5ac` is retained. Final named gates all exit 0: metadata and docs
validate 916 Markdown files; worklog indexes 1,328 commits; Ruff checks 696
files; the named Python spine passes 860 with 3 skips; dashboard UI passes
138; routing 1.4.0 passes every threshold; and decision conformance starts
green and kills 167/167 mutations with source unchanged. The exact gate
receipts are indexed by `f9e37789...4618`; the initial policy checker without
`PYTHONPATH` and decision evaluator without private umask are retained as
environmental negative receipts before their passing reruns.

The operator completed Claude's first-party subscription login, and the
credential was copied mode 0600 into only the already-installed final Claude
proof container. The first authenticated invocation is retained as a bounded
negative: its `/tmp` Store location correctly failed the product trust
boundary before a valid Agency load. Corrected ordinary Claude Code 2.1.239
session `29700000-0000-4000-8000-000000000303` uses `dontAsk`, no model
override, no activation bypass, and an owner-private Store directory. Native
stdout, stderr, and exit hash to `fed6961c...d406`, `e3b0c442...b855`, and
`bde29436...0120`; the exact 3,227-byte
`section-508-accessibility-specialist` card hashes to `589a6e0c...303e`.
Independent verifier `7c4968e8...4dee` exits 0 and binds trace
`21e96faa-84bb-40cc-a398-0df067f636d4`, one completed run, one accepted route,
one specialist load, five successful receipts across the exact generation,
embedding, reranker, and critic LiteLLM aliases, terminal acceptance with
`missing=[]`, and native/Store response hash `74da8abb...9cb`. Post-live config
remains exact at `a4e213d6...97348`; evidence manifest
`7fdd19af...7378` and package telemetry `1841465e...11be` both exit 0. The
four-harness later-ordinary matrix is therefore complete; teardown and final
record audit remain.

Final teardown first resolves exactly 47 unique full container IDs and
independently binds every name and `dev.agency-runtime.proof=AR-297` label at
receipt `d089a235...c6af`. Removal returns the same ordered 47-ID set, empty
stderr, and exit 0; both filtered post-removal inventories are empty.
Independent completion receipt `40fa5062...1dc4` exits 0. No image is removed:
the five retained candidate images remain bound to exact commit `e0b0b25c` and
wheel `75d63ff9...3762` at `5c998f61...e276`. Post-teardown host attestation
`64564e4a...bc24`, authenticated dashboard proof `26923d58...bb2`, and
OpenClaw deep status `33f99caf...86e0` all exit 0; the dashboard remains exact
and OpenClaw remains running with healthy authenticated RPC. Teardown manifest
`3fb64c9a...d009` and telemetry `f91b2bc3...1dea` exit 0.

Independent final audit `3c82c16d...cd79` exits 0 and returns Linux-scoped
**GO**. It revalidates exact source/artifacts/config, mode 0600, no Jina,
LiteLLM loopback-only inference, all four ordinary receipts, all named gate
exits and their manifest, exact host/dashboard/OpenClaw health, five retained
images, and zero labelled container survivors. Cross-OS artifacts, signing,
tracker writes or closure, push/PR/merge/tag/publication/release, and the
optional exhaustive hosted workflow were not performed and are not Linux-only
GO gates.

The final read-only tracker audit exits 1 with stderr
`413c8a3a...1600`: it reports pre-existing repository-wide missing remote
issues and unrelated state/URL/label mismatches, but no AR-297 identity, URL,
or label mismatch. Repairing that external governance debt requires tracker
writes that were not authorized and remains explicitly outside this Linux GO.

During authorized publication, PR #337's first CI run `33137554337` passed
static quality, documentation, dashboard UI, performance, dependency audit,
three Windows portability jobs, and the Windows unsigned distribution job.
The Ubuntu unsigned distribution job `98743288010` exited 1 only after its
installed wheel report and CLI help checks passed: AR-328's correct Hermes
0500/0400 cache guard blocked removal of smoke's disposable home. The bounded
repair reopens only that exact generated guard in smoke's `finally` path; the
existing full isolation regression now passes, both focused smoke suites pass
37 tests, and production guard validation remains unchanged. A fresh hosted
run and final merge-state audit remain the next publication gates.

At clean ledger head `6e78b14636fb682f9b0b4f7fa400fb5a51eed38f`,
canonical build, strict Twine, and independent portable-distribution
verification exit 0. The wheel hashes to `cf32f861...b2a7` and the sdist to
`1b40ca8f...e228`. Separate owner-private installations of each artifact pass
all eight deterministic smoke checks with no cleanup error and exit 0. The
artifacts, two copied-interpreter environments, and isolated homes remain under
`~/.agency-runtime-ci/ar297-pr337-6e78b146/` for review.

Fresh hosted CI run `33139352190` on exact reviewed head `3a9a09c2` completes
with 16 successful checks, three intentional exhaustive-integration skips,
zero failures, and zero pending checks. Ubuntu and Windows unsigned review
distributions pass in 1m24s and 3m27s; all three Windows portability jobs,
aggregate automatic gates, and platform-honest artifact assembly pass.
Dependency review run `33139352171` and CodeQL run `33139352213` pass, including
both language analyses and the aggregate CodeQL result. PR #337 was mergeable
and clean, then merged without bypass at `2026-08-28T03:55:35Z` as
`591aad207eadfe36671d374ff2b488d8bbd6a6a5`. Its parents are original
`origin/main` `0a23983a` and exact reviewed head `3a9a09c2`; the post-fetch
ancestry check exits 0. Tracker #335 remains open, and no tag, signing, release,
or tracker closure was performed.

The owner subsequently extended the accepted container scope to an exact
ordinary-process proof on this existing Linux host. AR-329 repair `aead84d0`
corrects the Codex inspector's non-executable-bootstrap classification without
weakening its artifact guard; 127 focused warning-strict tests pass. Clean
ledger `b25951ba` produces wheel/sdist `5f2c9b5d...4e33`/`24875bca...eff7`,
with canonical build, strict Twine, and independent verification exits 0.
Host refresh `10c50ca...82fb` installs all four exact bundles and the active
dashboard. OpenClaw returns to healthy authenticated RPC on port 18789. Codex
reports the refreshed inventory exactly as eight `modified` hooks with none
missing, making one fresh attended trust grant the explicit operator gate.

The owner completed that trust grant. Exact no-bypass verifier
`ef88754e...f2a4` then passes all 8/8 trust checks and launches Codex 0.150.1,
but exits 1 because child `01a048b6...1301` receives only the generic identity.
Parent/child rollouts `7a966722...3a9`/`8aa757e2...8f75` and Store
`eafa2c87...56f` isolate the missing boundary: the strict hook lineage reader
still admits only the 0.149.1 implicit-role/UTC-filename shape. The bounded
AR-330 follow-up adds the exact 0.150.1 `Code Reviewer` top-level/nested role
shape plus Codex's host-local filename spelling, while preserving exact
0.149.1 and fail-closed drift behavior. The real retained child now resolves
its exact parent and 103 focused warning-strict tests pass; rebuild, fresh
trust, and live staffing verification remain pending.

Clean ledger `33d9503bc5b7ec711466232e5606d82c4eb32966` now produces
portable wheel `141b1c07...e87f9` and sdist `4fa78570...385f`; canonical
build, strict Twine, independent distribution verification, an isolated
Python 3.12 wheel install, and `pip check` all exit 0. The owner-private
candidate venv is `~/.agency-runtime/release-venvs/ar297-33d9503b`; the
installed immutable runtime hashes to `59c12970...dcf2`. Exact config remains
mode 0600 at `a4e213d6...7348`, with strict assurance, additive recall, only
LiteLLM aliases, and no Jina route.

The bounded host transaction installs fresh Hermes, OpenClaw, Codex, and
Claude bundles `90ea1533...e2a2`, `87c5a833...0955`,
`bf284699...9d20d`, and `ab1fd64d...a7b9`. Receipt
`d68c4641...21ad` exits 1 only for the attended Codex trust gate and the
deliberately non-durable process-local LiteLLM credential at the dashboard
service boundary; all four host filesystem/native transactions complete.
A credential-free idempotent Hermes/dashboard transaction
`a3ddb605...7684` exits 0 and starts the candidate dashboard. OpenClaw's
supported stop/install/start sequence retains its immediate not-ready status
as a bounded negative; second deep authenticated RPC receipt
`3d782263...c0ac` exits 0 with active/running state, zero restarts, clean
config audit, and no version drift.

After the fresh attended eight-hook grant, immediately-preceding telemetry
reported 57.8 percent remaining. Exact no-bypass activation receipt
`eca6fcb4...647c` exits 0 for Codex 0.150.1 and persists current-profile proof
`93e3c88d...7635` at trace
`01a048d3-5687-7c11-a0a9-b1f3abbb7402`. It binds accepted selection/load of
`code-reviewer`, one real child, native delivery, four successful alias-only
generation/embedding/critic receipts, and completed finalization
`aae6686c...4392` with `missing=[]`; no activation bypass, adapter mutation,
or configuration mutation occurs. Parent/child rollouts hash to
`299542c3...7158` and `a8525798...c707`. Private Store backup
`cbaec4a8...01f8` passes quick-check, and sanitized correlation receipt
`0fe1ac45...a34b` binds the exact run, route, specialist, model receipts, and
accepted response hash. The AR-330 live gate is closed; fresh ordinary
Codex/Claude/Hermes/OpenClaw proofs, authenticated dashboard proof, named
repository gates, final record audit, and authorized merge remain.

The first fresh later-ordinary host row passes on the same candidate. Normal
Codex 0.150.1 session `01a048dd-10f0-77e2-94bd-d5e4c4572a4f` runs the exact
824-byte direct-only task `3ef304e5...2dd3` under the user's unmodified
`gpt-5.6-sol` model choice, `approval_policy=never`, and read-only sandbox; it
makes no tool or collaboration call and exits 0. Native receipt
`f4b845c8...7a82` proves one exact 2,659-byte `accessibility-auditor` card
`c3cfc098...5848` in rollout `793448db...52d2`. Private Store
`30f63fcf...6526` passes quick-check, and correlation `ecdc4998...22ec`
binds trace `01a048dd-1171-7872-8125-00637de78618`, accepted selection/load,
four successful alias-only generation/embedding/critic receipts, and
finalization `8b42648c...4792` with `missing=[]`. The sole native response and
Store response both hash to `572926de...0355`. Independent host verifier
`db8f6780...e2f3` exits 0 and rechecks the exact bundle, immutable runtime,
mode-0600 config, prompt, rollout, Store, and response equality. Claude,
Hermes, and OpenClaw ordinary rows remain.

Fresh ordinary Claude Code also passes on the exact candidate. Session
`29700000-0000-4000-8000-000000000403` uses the existing first-party
subscription login, normal default model, `dontAsk`, no bypass, and exact
683-byte task `abfcd7ee...3408`; native stdout/stderr/exit hash to
`38cd1ba7...3d03`, the empty SHA, and `bde29436...0120`. Native receipt
`c0800570...b370` proves one exact 3,227-byte
`section-508-accessibility-specialist` card `589a6e0c...303e`, no tool use,
and successful completion. Store `0319318c...29d1` passes quick-check;
correlation `15e99b7c...7c6b` binds trace
`58b2d963-c7bd-4653-b100-9e7045ef86a5`, accepted selection/load, all five
generation/embedding/reranker/critic alias receipts, and finalization
`45913401...640d` with `missing=[]`. Native and Store response hash is
`b4cd2225...8016`. Independent verifier `ed965d7c...8ca9` exits 0 with all
19 checks true and no secret disclosure. Hermes and OpenClaw ordinary rows
remain.

The first fresh ordinary host Hermes attempt is retained as a fail-closed
negative, not a completed matrix row. Normal Hermes 0.20.4 session
`20260828_110948_f9349a` uses the unchanged `task-agency-hermes` LiteLLM
alias, ordinary current-profile configuration, exact 684-byte task
`7411494b...49de`, and no model, thinking, toolset, or bypass override. Native
stdout/stderr/exit hash to `0f1d55ef...a801`, `e79cc69f...c6ef`, and
`bde29436...0120`; the process exits 0 only because Agency replaces the
unverified draft with its bounded block.

Native state `1b0dbc22...f173` and Store `ae80fe76...1bd3` both pass SQLite
quick-check. Offline inspection proves the selected 2,659-byte
`accessibility-auditor` card `c3cfc098...5848` occurs exactly once in the
12,397-byte first API payload. Correlation `5c85c67a...f2bf` binds accepted
selection/load, all five required Agency alias groups including the reranker,
and terminal finalization `8dfef4b6...a17` with
`missing=[actual_model_selected]`. Hermes made six progressive tool searches
but did not perform the explicitly instructed `agency_finalize` search or
call; it then made one prompt-prohibited terminal call. Plugin doctor still
proves one registered tool and eight hooks. This isolates nondeterministic
model compliance after successful routing and prompt visibility; no product
wiring defect, new model choice, configuration mutation, or AR item is claimed.

One unchanged, clean-checkpointed R2 confirms that the current host failure is
reproducible and is not admissible for another unchanged retry. Immediately
preceding telemetry `97092734...e3b` records the clean `3982e05c` /
`b81d154c` recovery pair and 40.2 percent remaining. Normal session
`20260828_112338_b056ed` again uses the exact task, stable Hermes alias,
current profile, and no model, reasoning, toolset, or bypass override. Native
stdout/exit are byte-identical to R1 at `0f1d55ef...a801` /
`bde29436...0120`; stderr `c77a80b2...0a70` contains only the session ID.

Native receipt `712a0dc8...ce28` proves one exact 3,227-byte
`section-508-accessibility-specialist` card in the 13,052-byte first API
payload, ten API calls, nine tool calls, and a 3,747-byte final draft. Despite
the task's self-contained/no-external-access constraint, the model made four
generic searches, one schema description, two GitHub searches, and two
terminal calls; it never searched for or called `agency_finalize`. Store
receipt `eee92f9b...5a89` passes quick-check and binds accepted selection/load,
all five Agency alias groups, and fail-closed finalization
`7f3d1839...2f86`. A second host-created trace remains `in_progress` after CLI
close and must expire or close before a final Store-cleanliness claim. The next
attempt must materially narrow the supported Hermes tool surface rather than
change the model or overwrite persistent user policy.

The least-privilege host R3 closes the fresh Hermes matrix cell without a
model or persistent-policy change. Supported ordinary CLI invocation manifest
`e6182cae...35a7` pins only toolset `agency-runtime` and a four-turn ceiling;
it retains the same `task-agency-hermes` alias, current profile, credential
reference, and persistent config `0ef96df3...ee74`. The bounded 818-byte task
`f1d1963e...b038` explicitly permits only the local Agency finalizer and caps
the report below its native transport budget. Pre-live telemetry
`0347535c...8c16` follows clean recovery `2c52e99a` / `a0cdea6f`.

Session `20260828_113341_bbcb27` exits 0 with native stdout/stderr/exit
`67fbb7cb...1871`, `218e0296...777f`, and `bde29436...0120`. Correct online
state backup `cb86b49e...1624` passes quick-check; the rejected pre-WAL copy
and its failed helper outputs were removed. Native receipt
`d466fbb3...cdb8` proves one exact 2,659-byte `accessibility-auditor` card in
the 12,531-byte API payload, three API calls, and exact tool sequence
`tool_search` then `agency_finalize`. No GitHub, terminal, browser, file, or
other non-Agency tool is present or called.

Store `4ded5b87...e551` passes quick-check, and correlation
`82409a45...d632` binds accepted selection/load, generation, additive
embedding, critic, and host-alias receipts, plus terminal finalization
`a424f727...fab76` with `missing=[]`. The exact accepted 2,646-byte response
and visible output both hash to `d44c75bb...2f2b`; R1/R2 independently retain
the configured reranker application. Supported lifecycle replay
`32adcb5c...486a` closes R2's expired interrupted trace without changing its
negative result. Independent verifier `f64738b9...8ce9` exits 0. The fresh
Hermes row is complete at this explicit Conveyor-style least-privilege scope.

Fresh ordinary OpenClaw now closes the fourth host harness cell. The first
fresh invocation fails before model work at exit 1 because the machine's
additive native model allow-lists predate and reject the already approved
`litellm/task-agency-openclaw` alias; stdout is empty and stderr/exit hash to
`fa87265e...5523` / `85acfd2e...5409`. No configuration or session artifact is
created. Transaction receipt `831edb7a...dd2f` then adds only empty alias
entries to the global and `openclaw` allow-lists. The native config changes
from `3480c474...588ff` to `5a864f4e...ddfb6` at mode 0600 with all unrelated
foreign policy, credentials, providers, fallbacks, gateway, and plugin fields
unchanged; native validation exits 0.

Immediately preceding telemetry `f104b10f...4b451` reports 51.9 percent and a
clean `01598467` / `313ad7cd` recovery pair. Supported embedded OpenClaw
2026.7.1-2 session `29700000-0000-4000-8000-000000000505` uses agent
`openclaw`, the approved LiteLLM alias, thinking off, no delivery, and the
exact 684-byte task `7411494b...49de`. It exits 0 after 234,660 ms; native
stdout/stderr/exit hash to `661198c2...6b8b`, `aac406a2...b7d3`, and
`bde29436...0120`. Corrected native receipt `1ac86bca...10fa` proves the full
task file and its 683-byte message body, one exact 2,659-byte
`accessibility-auditor` card, sole `litellm` provider and
`task-agency-openclaw` model, thinking off, successful session end, healthy
native SQLite, and a nonempty 3,239-byte response `c519f1ab...ddcf`. The first
helper receipt remains retained at exit 1 because it expected the historical
trimmed final prompt rather than this version's exact final newline.

Store backup `97602525...f56a` passes quick-check. Correlation
`84d672a6...afbf` binds trace `64adf094-cec5-4ac3-bbf1-f56200e5135b`,
accepted selection/load, exact task fingerprint, and five successful
generation/embedding/reranker/critic alias receipts. As in the isolated proof,
the no-delivery embedded process has an active run and no terminal finalizer;
that limitation is explicit rather than promoted to delivery evidence.
Independent verifier `61fd0b83...7fe7` exits 0. After the additive config is
loaded by the existing user-scoped systemd service, authenticated RPC receipt
`a144aab9...172` exits 0 with operator role, loopback port 18789, zero restart
count, no extra service, and no plugin drift. Package-end telemetry
`d02d00d7...d6d9` reports 42.5 percent and requires this clean recovery pair
before the authenticated dashboard proof.

The exact candidate dashboard closes the final live host surface. Immediately
preceding HTTP/browser telemetry `dee39489...d0f5` / `9ee71f18...0a14` sees
the clean `6d8c97d0` / `c5c6cfd9` recovery pair. Authenticated HTTP receipt
`b16121ba...c59c` exits 0 with all 21 checks true: the mode-0600 descriptor PID
matches systemd, unauthenticated health is 401, authenticated health/workforce
are 200 with `no-store`, and the complete 2,659-byte prompt
`c3cfc098...5848` is untruncated and byte-identical to the exact installed
asset. No bearer token is disclosed.

Browser receipt `abd3c832...c2f8` exits 0 with all 13 checks true under
Playwright 1.60.0 and Chromium 148.0.7778.96. It removes the token fragment,
selects `accessibility-auditor`, visibly expands the complete governed prompt,
observes 19 authenticated API 200 responses, and records zero console, page,
or request failures. Owner-private screenshot `222d5109...b5ac` is 166,535
bytes at mode 0600 and was visually inspected. Independent verifier
`de359741...7ea` exits 0 and binds runtime `59c12970...dcf2`, systemd PID
687930 with zero restarts, port 7810, both proofs, exact prompt, and screenshot.
Package-end telemetry `ece5d47f...7f4d` reports 32.1 percent and requires this
clean recovery pair before final repository gates.

Every named repository gate now passes against clean source commit
`33d9503b`. Metadata and documentation checks validate 921 Markdown files;
Ruff lint and the 696-file format check pass; the named fast production spine
passes 861 tests with 3 skips; all 138 dashboard UI tests pass; routing schema
1.4.0 passes; and decision conformance has a green baseline with all 167
curated mutations killed, zero survivors, and unchanged source. Every accepted
exit is 0. Owner-private manifest `ef8d8abc...1b09` binds the exact commands,
stdout/stderr/exit hashes, and the rejected environment preflights. The final
decision run uses a private prepared CI interpreter and strict `0077` process
umask so its disposable checkouts satisfy the existing private-path policy; it
does not bypass or mutate Agency policy. The explicitly optional exhaustive
corpus, four-shard coverage, and six-interpreter workflow were not dispatched.

The final read-only record audit leaves source unchanged and isolates inherited
repository-wide tracker debt rather than an AR-297 mismatch. Tracker-required
documentation and tracker-parity stderr hash to `769fb577...6056` and
`e98fd0e5...64a7`; both exit 1 because older roadmap items lack tracker URLs or
have state/label drift. AR-297 and tracker #335 appear in neither mismatch list.
No tracker, closure, tag, signature, release, or publication mutation was made.

PR #339 then merged the complete product package to `origin/main` as
`dc8bbde6a884f72614dae32585e488ce4997b9ac`. A clean checkout built wheel
`c3f3cd0d...675c` and sdist `dc57fa54...5325`; build `a7e70dcf...c7d7`, strict
Twine `e2527bd9...a8a3`, and independent distribution verification
`70e8a13e...73f` all exit 0. The exact wheel was installed into fresh venv
`~/.agency-runtime/release-venvs/ar297-main-dc8bbde6`, with no external Agency
version pin. Hermes/dashboard `cea01073...5a2`, Claude `097450fa...f66`,
OpenClaw install `75be0172...a20`, and Codex install `19820581...24c` all exit
0. OpenClaw's supported stop/install/start sequence and authenticated deep RPC
`48b73bba...393b` pass without replacing foreign policy.

The owner completed Codex TUI hook trust. The default 180-second verifier then
timed out safely without persisting an attestation; its materially changed,
previously proven 300-second retry exits 0 at `d90cfcd1...c47`, with managed
trust, canary pass, trace `01a04952-fea8-7362-8593-08e24ab4045f`, proof digest
`641cc99d...d18`, and bundle `cecc8993...ab3b`. Exact runtime attestation
`93a25ad5...c25` exits 0 with all 18 checks true for runtime
`2dd04fdc...9987` and Hermes/OpenClaw/Codex/Claude bundles
`b03b47fe...e9b`, `1f88f2ef...2c8`, `cecc8993...ab3b`, and
`5d178603...136`. The installer record binds the exact wheel URL; its PEP 610
record does not include the optional archive hash, so the canonical builder
and independent verifier separately bind the wheel SHA.

Final status `7cc9023f...f512` exits 0, and authenticated dashboard proof
`96d1a058...a515` exits 0 with unauthenticated 401, authenticated health and
workforce 200 plus `no-store`, PID 1134253 on port 7810, and the full untruncated
2,659-byte accessibility-auditor prompt `c3cfc098...5848`. No secret is
printed or persisted. This closes the clean-main build and machine-install
package. The remaining owner-requested work is an interactive read-only test
in each harness followed by the Linux-scoped verdict; tracker #335 remains open
and no release, tag, signature, publication, or tracker mutation is authorized.

The first owner-observed Codex test then revealed an ordinary-terminal
credential projection gap hidden by the earlier proof environment. The
`UserPromptSubmit` hook visibly loaded the resident-steward frame, and Codex
produced the requested three bullets, but Stop rejected publication with
`AGENCY TURN TERMINAL`. Store trace `01a04996-795a-7473-9919-a75e3ca3c151`
is `preflight_failed`: `task-agency-generation` has
`provider_no_valid_response`. The LiteLLM service log binds the request to HTTP
401 `No api key passed in`; LiteLLM, Ollama, the dashboard, and OpenClaw remain
running. This is not a model or endpoint failure and the rejected answer is not
promoted to a passing manual cell.

The existing exact config references `LITELLM_API_KEY`, but a fresh ordinary
terminal does not inherit that variable. Using the owner's prior authorization
to obtain the key from mode-0600 `~/.openclaw/.env`, the supported write-only
`agency config set ... --stdin` interface replaces all eight LiteLLM credential
references in a copied config without printing the value. The old config stays
untouched. Receipt `530b7837...1e5e` records 16 zero-exit operations and creates
mode-0600 exact config `ar297-litellm-df75e01d31dd8ebc.yaml`, SHA
`df75e01d31dd8ebc668c3f4127d70a0af14e1e63cf600a9a03e6a01884540922`.
Validation no longer reports provider authentication unavailable; exit 2 is
limited to the four truthful cold-inventory loading warnings.

Codex/dashboard reinstall stdout `9824fbf2...4c58` installs bundle
`40b3693c...e340` and moves the healthy dashboard to the new exact config. The
overall exit is 1 only because changing the bundle invalidates prior attended
Codex hook trust. No bypass is used. The current bounded exit is
`waiting_for_operator`: close the old Codex TUI, trust all eight hooks in a
fresh terminal, and repeat the manual prompt as a new turn before testing the
other three harnesses.

Fresh trust succeeds, but two subsequent owner-observed turns still fail
closed before selection. Trace `01a049a6-1623-7972-aebf-47a048cedb07` rejects
the initial Qwen plan as semantically invalid and its repair for a forward
dependency. Trace `01a049ab-dbc2-7fa1-87d8-87ed63e89f76` rejects the initial
plan as semantically invalid and its repair for missing implementation, test
implementation, and test-evidence review on the explicitly read-only copy
task. Neither trace has routing, specialist loading, model receipts, or final
acceptance, so both visible Codex drafts remain rejected rather than evidence.

An isolated Store replay of the exact prompt on current
`task-agency-generation` does pass once: database `63e5d86a...37a9` records an
accepted `accessibility-auditor`, four successful LiteLLM receipts, and full
5,858-byte context `f1182d56...646a`. Because one isolated success does not
erase two real failures, a second isolated config changes only the generation
profile to already-approved LiteLLM alias `task-agency-router`, whose local
backend is free `mistral-small3.2:24b`. Config `741cf7cd...fe97` and Store
`193cd280...ae5a` produce the same accepted specialist and byte-identical
context with no failure. No stable alias or installed bundle is changed by the
A/B. The next bounded exit is `waiting_for_operator` for the generation model
choice: retain measured-but-unreliable Qwen 14B or remap the stable
`task-agency-generation` alias to the slower structured Mistral 24B.

The owner rejected Mistral's general-use latency and approved subscription
model trials through the existing LiteLLM gateway. Exact-prompt Luna-light
config `3f2144b3...c1df` exits 0 in 96.72 seconds: Store
`9c303400...ca81` records accepted `accessibility-auditor`, all five required
generation/embedding/reranker/critic receipts, and the byte-identical complete
5,858-byte context `f1182d56...646a`. Terra was not called on this first pass.
The first stable-alias transaction `c0bf514f...9f5` is a retained HTTP 422
negative for invalid metadata tier and proves rollback to Qwen. Corrected
transaction `3e6b3491...d4c` exits 0 and preserves deployment
`df8ebd8f...3a51` and alias `task-agency-generation` while selecting
`chatgpt/gpt-5.6-luna` at low reasoning. No host config or bundle changes.

A harder planner-only probe shows why one simple pass is insufficient. Stable
Luna returns in 13,689 ms but exits 1 solely for
`plan_missing_codebase_discovery`; receipt `aab403bd...6270`. Temporary
Terra-light config `37436635...d733` runs the identical request in 13,047 ms,
exits 0, emits six units, echoes no injection, and has zero policy violations;
receipt `65427d17...36b`. Stable production remains Luna pending the completed
quality/latency comparison.

Latency profile `437b7ce3...9b83` isolates the 96.72-second result: Luna
completes near six seconds, two 4,096-dimension Qwen3 embedding batches finish
near 40/45 seconds, and three Mistral structured stages finish near 55/90/97
seconds. Ollama reports Mistral at 19 GB GPU residency and the embedding model
at 4.7 GB on disk; alternating them causes cold-load churn. The embedding
catalog cache is process-local, so ordinary per-hook processes cannot rely on
a previous turn warming it. Multiple-minute preflight is explicitly not an
acceptable general-use result.

The owner approved the next bounded performance screen without weakening
strict assurance or additive dense recall: Terra-light generation; Qwen3
embedding at 1,024 dimensions; local Qwen 14B abliterated versus Qwen 3.5 9B
for independent critic/text-reranker; unchanged free Qwen 3 32B child judge;
and configured GLM 4.7 Flash/FlashX and GLM 5 Turbo candidates. GLM routes are
HTTPS Z.AI deployments, not local Ollama weights. GPT-5.3-Codex-Spark is also
approved for consideration through subscription auth at low/medium reasoning,
but the gateway currently has no Spark deployment; official/current local
metadata marks it Pro research-preview with a separate limit. Target the full
preflight at no more than 20 seconds warm and 30 seconds cold; promote only a
repeatedly passing exact configuration, then resume one-at-a-time manual host
tests.

The owner then broadened the screen: keep embeddings local, but subscription
routes may replace every other local stage when repeated evidence proves both
lower latency and accepted quality. All such routes still remain behind
LiteLLM aliases and strict provider/model independence remains enabled. Bounded
Z.AI deployments set zero retries and a 25-second internal timeout; an external
30-second ceiling prevents the gateway's global retry policy from recreating a
multi-minute wait. GLM 5.2 with thinking disabled produces no response before
operator termination at 46.32 seconds (`44876a0a...752` / exit 143). GLM 5.3
low returns HTTP 200 in 23.01 seconds but fails the strict structured boundary
(`b5cdd83a...ee5` / exit 1). GLM 5 Turbo with thinking disabled returns six
units in 21.88 seconds but fails semantic validation (`463703e6...288` / exit
1). Their temporary aliases are deleted by receipts `f228ab49...0c6`,
`e90cc768...faf`, and `745087c8...d01`.

GLM 5.3 Flash low is the sole passing GLM planner: config
`11bdde01...6da5` yields six policy-clean units in 21,727 ms / 21.84 seconds,
exit 0 and response `cdcca1ff...ae9d`; its temporary alias remains only for the
next independent verifier comparison. Subscription Sol-light also passes the
identical hard planner with six units and no policy violations in 12,864 ms /
12.98 seconds; config/response are `8c71e965...d8c2` /
`f1710b0a...ec6`. Sol and Terra are therefore effectively tied on one sample,
with Sol only 0.18 seconds faster in wall time; repeated runs, not that
noise-sized difference, must select the planner.

Temporary subscription Spark aliases then establish a materially different
latency tier. Low reasoning passes the identical six-unit hard planner with no
violations in 2,593 ms / 2.70 seconds (`ce3a5eff...ed6`, exit 0); medium also
passes in 2,920 ms / 3.03 seconds (`64ed8fa6...ce2`, exit 0). Exact config
`a330c1a8...419` assigns Spark-low to planning, recruitment, and text
reranking, Sol-light to independent critic/review, and the existing local
embedding alias at the approved 1,024 dimensions. Its cold and immediately
repeated runs time out at the external 60/45-second ceilings (`9928ea39...836`
for both exits). Gateway chronology isolates one local embedding request at
about 34--37 seconds even while the 8B embedding model is GPU-resident; Spark
stages remain approximately 2--6 seconds. Dimension truncation reduces result
width and batching but does not reduce the 8B model's forward-pass cost.

The owner requests production aliases with a measured best primary and an
ordered second-best fallback from a different provider so Spark quota
exhaustion fails over unattended. LiteLLM's deployment `order` control is the
selected mechanism: order 1 is always tried before order 2, 429 places the
failed deployment on cooldown, and per-deployment zero retries prevents
multi-minute same-provider loops. The exact matrix and forced-failure proof
remain pending. Embeddings stay local; the next owner choice is whether to
download and test the official 639-MB `qwen3-embedding:0.6b` artifact at its
native 1,024 dimensions in place of the current 8B model.

The owner approves that exact model/dimension. Pull exits 0 in 6.85 seconds
(`8f42d4d6...d359`); `ollama show` receipt `3b8529fe...504e` confirms Qwen3,
595.78M parameters, 32,768 context, 1,024 embedding length, and Q8_0.
Temporary LiteLLM alias receipt `ba21d61a...f94b` exits 0 with backend
`ollama/qwen3-embedding:0.6b`, `keep_alive=-1`, zero retries, 30-second
timeout, embedding mode, and output vector size 1,024. Direct dimension and
latency validation is the next bounded live evaluation.

Cold direct probe config `782ba725...490e` then embeds 27 catalog-style inputs
as exactly 27 uniform 1,024-value vectors in 2,148 ms / 2.26 seconds, exit 0;
receipt `e861bd5d...ff0b`. This is more than fifteen times faster than the
resident 8B model on the comparable batch. The bounded package now proceeds
to an explicitly unloaded full cold hook, an immediate warm hook, and ordered
cross-provider primary-failure proof.

The unloaded full hook returns at process level in 7.79 seconds, but strict
Store inspection rejects the result: both Spark planner attempts are
`plan_response_semantic_invalid`, the run is `preflight_failed`, and no model,
routing, or specialist receipt is accepted. Stdout/Store are
`67133d17...2cb`/`d1562321...c09`; this is a fast negative, not a cold pass.
The gateway cost logger also fails to persist most Spark spend rows. A
deduplicated journal audit exits 0 at `e307f2e5...784d` and proves 12 distinct
Spark completions from 15:31:01 through 15:46:39 EDT. The retained first audit
exits 1 because it counts the logger and duplicated exception line separately.

The owner rejects Spark after it consumes about half of its separate five-hour
subscription budget. Transaction `75855980...6bc` restores stable
`task-agency-generation` to local `ollama/qwen3-14b-abliterated`; deletion
receipts `bfb54a1f...86ae` and `b412d6cf...4851` remove the temporary low and
medium Spark aliases. All eight stable Agency aliases again resolve locally.
No later benchmark may include Spark.

The owner authorizes a broader per-stage benchmark across non-Spark OpenAI
subscription models, MiniMax M2.7/M2.7-highspeed/M3, Z.AI, and warm local
models. Every provider-supported reasoning level, including off/unset where
available, must be evaluated for latency, deterministic/semantic quality, and
a combined score. The retained call ledger must distinguish attempted,
completed, cached, retried, and rejected requests. The final technical report
must rank each unique Agency text-stage contract; embeddings remain a separate
local dimension/latency/recall measurement because reasoning level does not
apply.

The frozen pre-live manifest `62f8bec4...c6fd` contains 67 exact model/mode
candidates: 30 non-Spark OpenAI subscription routes, four MiniMax routes, 15
Z.AI routes, and 18 local Ollama routes. Nine production contracts produce 603
one-shot screen cells, 18 accounted local warm-ups, and at most 18 top-two
confirmations, for a hard maximum of 639 model calls with zero retries. The
secret-safe alias manager and stage harness are `65c80909...4a38` and
`226f4532...b4e8`; fixture/schema validation and authenticated alias preflight
`21700339...d176` pass without a model call, and no temporary benchmark alias
exists. Schema/semantic/injection eligibility is a hard gate before the
60-percent-quality/40-percent-latency combined score; every promoted fallback
must come from a different provider.

The non-Spark OpenAI block completes all 270 frozen cells exactly once. Ledger
`a0c3f787...85e2` records 238 structured completions, 197 strictly eligible
responses, and 32 bounded transport/JSON failures across all 30 candidates and
nine stages. GPT-5-nano accounts for nine immediate failures and is unusable
through this subscription gateway; the remaining failures are retained
48-second ceilings on heavier reasoning/stage combinations. Terra-low first
meets the practical stage envelope with 100-point planner/recruiter/critic/
reranker/judge/security results and 19.878/25.480-second hiring/safety outputs;
Terra-ultra is the only OpenAI candidate to score 100 on all nine single-screen
fixtures, at 24.435/24.744 seconds on the two full-contract stages. Mini-low is
faster on those full contracts at 16.104/18.282 seconds but fails planner
semantics. The first alias body was rejected before inference because `tier`
must be `paid`, not `subscription`; its sanitized HTTP-422 receipt is retained,
manager `8d7d884a...4d92` fixes that metadata field, and every later create/
delete passes. Post-block inspection reports zero temporary benchmark aliases.

MiniMax completes all 36 frozen cells exactly once. Cumulative ledger
`5f93b3a3...7747` adds 32 structured completions, 19 strict eligibilities, and
four bounded failures across all four official model/mode candidates. M2.7 and
M2.7-highspeed both fail planner and the hiring/security contract gates while
passing the compact recruiter, critic, reranker, and judge fixtures; the
highspeed route is slower on this workload. M3-off passes the 4.267-second
planner but fails critic and hiring. M3-adaptive is the MiniMax compact-stage
leader with 7.179-second planning, 1.535-second recruitment, 2.512-second
critique, 1.405-second reranking, and 0.818-second judging, all at 100 points;
it remains ineligible for both full hiring-contract stages. Every MiniMax alias
is removed after its nine-cell slice.

Z.AI completes all 135 frozen cells exactly once. Cumulative ledger
`636a1dec...5bf5` adds 100 structured completions, 73 strict eligibilities, and
35 bounded transport/JSON failures across 15 documented input-mode candidates.
Regular GLM-5.3 passes compact stages but not planner or full hiring generation;
the Flash variants are slower and no more reliable. GLM-5.2 `low` and `medium`
(both effective `high`) produce the best Z.AI planners at 17.044/17.657 seconds,
but every 5.2 input fails the full hiring generator. GLM-5-Turbo off is
inconsistent and on is slow at 32.780/32.862 seconds for planning/recruitment;
neither is eligible on hiring. Z.AI therefore contributes only compact-stage
fallback candidates, subject to cross-provider combined ranking. Every alias is
deleted after its nine-cell slice.

Local Ollama completes all 162 frozen cells and all 18 accounted warm-ups
exactly once. Cumulative ledger `336fdf67...fcc1` records 78 structured
completions, 24 strict eligibilities, and 84 bounded transport/JSON failures;
seven warm-ups pass and 11 fail. Qwen3 Coder 30B is the strongest local route:
it scores 100 on planner/recruiter/critic/reranker/judge, reaches 17.125 seconds
on planning and 0.892--4.334 seconds on the compact stages, but misses the full
hiring and repair gold gates at 80. Mistral 24B passes recruiter and judge but
takes 20.416/3.970 seconds; all GPT-OSS 20B reasoning modes fail the strict
structured path. The completed screen is therefore 603/603 cells, 448
structured and 313 eligible. Post-block inspection returns HTTP 200 with zero
temporary benchmark aliases; the only cleanup warning names an already-absent
OpenAI alias after its prior successful delete and does not leave live state.

The exact 18-call confirmation budget completes with 18 structured responses
and 12 strict eligibilities, bringing the retained ledger to its hard maximum
of 639 paired starts/finishes at `2080c834...d56`. Replay audit
`1823c21b...19e` revalidates all 466 saved response hashes and decision scores;
rankings/plan/results are `ebd3f4fb...cee6`, `311ab6c0...2d9`, and
`f6c92e4b...189a`. Five stage pairs repeat with different providers:
recruiter M3-adaptive/Luna-low, critic local Qwen 3.5 2B-off/Terra-medium,
reranker and judge M3-adaptive/local Qwen3 Coder 30B-off, and security review
GPT-5.4-mini-low/local Qwen3 Coder 30B-off. Planner M3-off/GPT-5.5-high both
regress to 82.5; GPT-5.4-mini-low repeats hiring generation and safety repair
but neither cross-provider probe qualifies; Terra-ultra regresses to 85 on the
hiring critic and its local probe also fails. Therefore five pairs are
promotable, while planner, hiring generator fallback, hiring critic, and safety
repair fallback remain unresolved. HTTP-200 inspection again finds zero
temporary aliases.

The decision report is retained as mode-0600 host artifact `report.html` at
`97ec909e...62d0`; its canonical input/data/SQL/builder hashes are
`feddf5ca...1c50`, `7ccd70e7...39f4`, `b966fe7c...dc3d`, and
`76e2ec0e...9b5`. The packaged delivery receipt passes validation, packaging,
four-chart extraction, 1,440/390-pixel browser verification, exact rendered
counts, and keyboard source-dialog interaction in 7.694 seconds. Readiness
receipt `3ba71f8e...9322` independently checks 18 manifest blocks, nine stages,
18 confirmations, 313 eligible rankings, nine different-provider selections,
and a clear sensitive-pattern scan. It admits only the five repeated pairs and
marks the complete LiteLLM configuration not ready; stable routing is therefore
unchanged until the four unresolved contracts have repeated eligible evidence.
The one-use report reader correction was authorized, embedded only in the
self-contained report, and the installed plugin source/reader were restored to
their exact original `2f989ae1...ed4` / `6c5ed0d3...e7b5` hashes.

Response-level failure audit isolates four prompt-contract defects without
weakening any gate: planner confirmations omit the literal repository/code/path
tokens used by the deterministic discovery veto; every approving hiring critic
except one adds explanatory reason codes instead of the required empty array;
the best local hiring generator and repair fallback emits `null` for the
required string `coherent_amendment_target`; and MiniMax safety repair quotes an
untrusted suffix while explaining that it ignored it. Production prompts now
state those exact closed-output requirements. Ruff 0.16.5 check/format and 160
focused intent, hiring, contract, and decision-conformance tests exit 0. No
model was called and no stable alias changed; a separately authorized maximum
of 24 zero-retry remediation calls is still required before configuration.

The owner then authorizes exactly 24 zero-retry remediation calls: 16 mandatory
repetitions and at most eight predeclared stage reserves, with Spark and Jina
excluded. Separate mode-0600 manifest/runner `f7477f43...9e3` /
`de72a5ae...68d` preserve the original 639-call ledger and refuse reserve work
unless a required stage still lacks a cross-provider pair. Ledger
`deedc130...a1` contains exactly 24 unique starts and 24 matching finishes,
zero retries, 20 valid alias receipts, 16 saved responses, and eight
transport/JSON failures. Authenticated final inspection returns HTTP 200 with
zero temporary aliases; no stable route or exact config changes.

The repaired planner primary GPT-5.5-high passes twice at quality 100 in
10,883/11,961 ms. MiniMax M3-off fails JSON twice, while the local 30B reserve
times out once at 48,137 ms and passes once at 19,440 ms, so planner still has
no repeatable fallback. Hiring critic is the only newly complete pair:
GPT-5.4-mini-low passes twice at 2,165/2,004 ms and local Qwen 3.5 2B-off passes
twice at 10,218 ms cold / 2,297 ms warm; MiniMax M3-adaptive varies one pass to
one rejection. GPT-5.4-mini-low also passes hiring generation twice at
17,203/17,961 ms and safety repair twice at 16,169/17,634 ms. Their fallbacks
do not qualify: local Qwen3 Coder 30B reaches the 48-second limit on all four
full-contract calls; GLM-5 Turbo generator returns one schema-invalid score-80
response then one transport/JSON failure; MiniMax safety repair scores 85 twice
but reproduces untrusted source text. Replay analyzer/results
`0a4e92b7...1212` / `ce7704a5...b455` recheck all prompt, system, schema, saved
response, decision, and score hashes.

The refreshed mode-0600 technical report `c608309f...68b6` preserves all 313
screen rankings, four chart IDs, and three table IDs; it adds all 24 remediation
calls and raises readiness from five to six of nine pairs. Canonical
input/data/SQL/notes/builder hashes are `0ef0ff5f...ab52`,
`362dd71f...387`, `1b2e80c0...e9eb`, `290de5c3...49f`, and
`1c8d81c9...2303`. Validation `0fa79f4c...68a8` passes packaging, chart
extraction, 1,440/390-pixel browser checks, and keyboard source interaction in
2.882 seconds; its analytical verdict is share-with-caveats because planner,
hiring generation, and safety repair still lack repeatable cross-provider
fallbacks. The temporary known top-bar correction used exact patched hashes
`426377da...6c1` / `112e8616...e78`; plugin source/reader are restored exactly
to `2f989ae1...ed4` / `6c5ed0d3...e7b5`, generated dependencies and failure
screenshots are removed, and the complete LiteLLM config remains blocked.

The next prompt-only repair makes the hiring response shape literal: exactly
five top-level keys, `schema_version` only under `contract`, every declared
array kept as an array, all required strings nonempty, and nonempty bounded
tools for hire/amend. Safety repair now forbids reproducing any verbatim
`original_hiring_input` text anywhere, including evaluation scenarios and
rationales, and requires neutral labels without source markers. Source/test
hashes are `38f51f01...276f` / `c14db2f49...0836`. Ruff 0.15.20 check and
format exit 0; the focused dynamic-hiring, contract, selection-safety, and
decision-conformance suite exits 0 with 137 passed and one intentional skip.
No model or stable alias is called. The owner separately authorizes the next
six zero-retry calls: two repetitions each for MiniMax M3-adaptive planner,
local Llama 3.1 8B hiring generator, and MiniMax M3-off safety repair.

That exact follow-up manifest/runner `ba2ecb0d...6207a` / `c385a11a...b855`
executes all six calls with no retry. Planner M3-adaptive produces one
transport/JSON failure at 6,693 ms and one score-15 schema failure at 2,918 ms
whose sole top-level defect is an invented `additionalProperties` key. Local
Llama 3.1 8B hiring generation reaches the 48-second ceiling twice at
48,130/48,135 ms. M3-off safety repair passes once at quality 100 in 11,315 ms
and returns a schema-, semantic-, and gold-valid score-85 response in 18,811 ms
that still reproduces the untrusted marker in `avoided_scenarios[0]` and the
hard-negative rationale. No route repeats and readiness stays six of nine.

Ledger/analyzer/results `02154df0...c2f2` / `2a228291...fdde` /
`249ce089...95cc` prove exactly six starts/finishes, zero retries, three saved
response replays, and six valid create/delete receipts. Authenticated final
LiteLLM inspection returns HTTP 200 with zero temporary aliases. Stable routes
remain unchanged; the six-call grant is exhausted.

The final follow-up technical report `8fd5667f...a587` now reconciles 669 total
calls, 48 post-screen calls, 25 strict-eligible post-screen results, all 313
original eligible ranking rows, and the unchanged six-of-nine decision.
Artifact/data/SQL/notes/builder hashes are `1327b9fa...b381`,
`71fd4bcd...a66e`, `26fff5be...01a4`, `cbe98456...bb66`, and
`43fea685...8682`. Validation `ce57492e...572c` passes the 21-block/four-chart/
three-table package, desktop/mobile checks, keyboard source interaction, exact
arithmetic, sensitive-pattern scan, and share-with-caveats analytical review in
2.912 seconds. The same known top-bar correction produces patched hashes
`426377da...6c1` / `112e8616...e78`; plugin source, reader, compressed parts,
dependency absence, and failure-screen absence are restored exactly. The
general asset normalizer rejects an unrelated development redirect, while the
scoped portable-reader normalization and delivery pass.

The next no-call repair addresses the exact follow-up failures. The planner
system now requires exactly `request_summary` and `units` and forbids emitting
schema keywords such as `additionalProperties`. Safety repair no longer
receives the raw request, free-text work-unit fields, or full worker prose; a
new deterministic projection supplies only bounded identifiers, enums,
booleans, counts, typed coverage, and four worker execution facts. Existing
schema, semantic, injection, validation, and independent security-review gates
remain unchanged. Intent/hiring source hashes are `2f01bd74...8fb4` /
`a7dba727...0b12`; test hashes are `d9482a7c...4b64` / `db27aaf9...10a5`.
Ruff 0.15.20 check/format and 188 focused tests exit 0 with one intentional
skip. No model or stable route is called.

The evidence-driven next candidate set is Z.AI GLM-5.2-low planner (the fastest
non-OpenAI strict screen pass at 17,044 ms), GLM-5-Turbo-on hiring generation
(previously one score-80 shape failure before the explicit array/tool repair),
and MiniMax M3-off safety repair against the new content-free prompt. Each needs
two zero-retry repetitions under a new explicit six-call owner cap.

The owner authorizes that exact six-call route-closure plan and grants broader
in-scope YOLO authority through 11:00 AM local time. Manifest/runner
`a32cc7a5...a9e6` / `dd2d3a9b...ecdd` execute exactly six starts and finishes
with no retry. Z.AI GLM-5.2-low planner fails at the transport/JSON boundary
twice in 24,498/26,249 ms. GLM-5-Turbo-on hiring generation passes once at
quality 100 in 39,310 ms, then scores 80 in 29,477 ms because it collapses
`execution_profile.working_principles` from an array to a string. MiniMax
M3-off safety repair scores 56.25 twice: injection safety passes, but it emits
only `action` and `contract`, omits the three other required top-level fields,
and adds an empty second tool. The 31 ms second safety result is a cached
identical-prompt response and is not independent evidence.

Ledger/analyzer/results `2dca9647...977a` / `5ade50b5...950f` /
`19565ac0...0472` replay all four saved responses, prove six valid create/delete
receipts, and finish authenticated HTTP 200 inspection with zero temporary
aliases. No pair is added, readiness remains six of nine, and stable routing is
unchanged. The next bounded remedy must add a changing evaluation nonce to the
content-free safety fixture, reinforce the exact five-key/array syntax, and
prewarm the previously cold-sensitive local Qwen3 Coder planner before two
strict repetitions rather than extend its production timeout.

The next prompt-only repair makes that shape executable: one-item working
principles use a literal JSON array example, every array element must be
nonempty, and safety repair must derive and return all five top-level records
even with projected context. A one-based `repair_turn` cache-busting ordinal is
added to each bounded safety replacement attempt and explicitly carries no
instruction authority. Hiring source/test hashes are `863df134...a8d8` /
`852fd91a...d0d6`; Ruff check/format and the same 188-test focused set pass with
one intentional skip. No model or stable alias is called.

The owner-authorized hot-closure manifest/runner `af666f79...25bf` /
`4e93e10f...0756` then consume exactly seven zero-retry calls. The full local
Qwen3 Coder planner prewarm and both measured hot calls all reach the unchanged
48-second boundary (48,136/48,139/48,090 ms), so that route is rejected for
reliable general use. Z.AI GLM-5-Turbo-on hiring generation also reaches the
boundary twice (48,126/48,076 ms) without a returned object. MiniMax M3-off
safety repair returns two independent score-100 objects in 28,261/6,053 ms;
both are schema-, semantic-, gold-, and injection-valid and have distinct
response hashes `cae75d76...5e9b` / `9371d74d...e0ed`. That route now supplies
the different-provider fallback for the already repeated OpenAI safety route,
raising readiness to seven of nine pairs.

Ledger/analyzer/results `c375dd21...89d2` / `c3628fc4...8b7d` /
`e8d48a2c...959c` replay both saved responses and validate all seven starts and
finishes, zero retries, nine valid alias receipts, the exact stable config hash
`df75e01d...0922`, and final authenticated LiteLLM HTTP 200 with zero temporary
benchmark aliases. Stable routing is unchanged. The next bounded candidate set
is two current-fixture repetitions each of MiniMax M3-off and GPT-5.5-high for
planner, plus GPT-5.4-mini-low and MiniMax M3-off for hiring generation. This
eight-call package tests both required providers for each remaining stage.

Final-pairs manifest/runner `bda0e8a2...c69b` / `df856b65...9e7b` execute that
exact eight-call plan with no retry. GPT-5.5-high planner repeats at quality 100
in 9,913/10,414 ms, and GPT-5.4-mini-low generation repeats at quality 100 in
17,690/19,201 ms, confirming both current-fixture OpenAI primaries. MiniMax
M3-off is not yet repeatable: planner scores 85 then 100 in 4,579/9,536 ms, with
the first otherwise-valid response reproducing the untrusted phrase in
`request_summary`; generation has one transport/JSON failure at 18,420 ms then
one score-100 result at 21,249 ms.

Ledger/analyzer/results `ae9c30e3...edbd` / `32b974a2...324f` /
`33256428...7400` replay seven saved responses, validate exactly eight starts
and finishes, zero retries, nine valid receipts, stable config
`df75e01d...0922`, and authenticated HTTP 200 with zero temporary aliases.
Readiness remains seven of nine because both cross-provider fallbacks still
need two clean repetitions. The next bounded repair forbids quoting, describing,
or paraphrasing ignored prompt-injection text in planner outputs, followed by
two MiniMax M3-off planner and two generation measurements.

That no-call planner repair is now implemented. The intent system instructs the
model never to quote, describe, paraphrase, or mention ignored injection text
or injected worker names in any output field and to summarize only authorized
work. Intent source/test hashes are `07fdffdc...2dfa` / `09b238ef...461c`;
Ruff 0.16.5 check/format and the same 188-test focused set exit 0 with one
intentional skip. Stable routing and model-call accounting remain unchanged.

MiniMax fallback manifest/runner `172ba9ac...5fc5` / `00edb012...a670`
execute exactly four zero-retry calls after that repair. Planner now repeats at
quality 100 in 8,261/3,838 ms with distinct response hashes, closing its
different-provider pair. Hiring generation scores 63.75 in 7,666 ms then 100
in 29,544 ms. The failed object remains safe and semantically near-complete but
collapses `contract.relationships` to an empty string and emits only
`disabled_covering_workers` inside `gap_evidence` instead of the required full
seven-key record.

Ledger/analyzer/results `5106e992...1ee7` / `aad39222...5ec8` /
`c8f79895...d90b` replay all four responses, validate four starts and finishes,
zero retries, three valid alias receipts, stable config `df75e01d...0922`, and
authenticated HTTP 200 with zero temporary aliases. Readiness is eight of nine;
only the MiniMax generation fallback remains. The next no-call repair pins
`relationships` as an array and the literal complete `gap_evidence` key set
before two final bounded MiniMax generation measurements.

The final no-call shape repair now requires `gap_evidence` to contain exactly
all seven schema keys and requires `contract.relationships` to remain a JSON
array, using the literal empty form when no edge is needed. Hiring source/test
hashes are `81b5cb9e...a525` / `6e6dd0f3...e2a1`; Ruff 0.16.5 check/format and
the 188-test focused set exit 0 with one intentional skip. No model or stable
alias is called.

Generator-close manifest/runner `5312ecb2...44ba` / `84bf953f...b345`
execute exactly two zero-retry MiniMax calls in 7,633/7,625 ms, scoring 65/80.
Both preserve the repaired full gap record and relationships array and satisfy
all semantic/gold checks. One contract exceeds the four-host bound by adding an
invented host; the other adds undeclared `contract.host_constraints`. The first
also repeats an injection marker, so neither is eligible.

Ledger/analyzer/results `c6d9b26d...57a2` / `a32e9c12...554c` /
`3f862167...b56e` replay both responses, validate two starts and finishes, zero
retries, three valid receipts, exact config `df75e01d...0922`, and authenticated
HTTP 200 with zero temporary aliases. Readiness remains eight of nine. The next
bounded repair forbids undeclared contract fields and requires hosts/platforms
to copy only supplied work-unit values before another exact two-call proof.

That no-call repair now forbids undeclared contract fields such as
`host_constraints`, caps `contract.hosts` at four unique nonempty identifiers,
and forbids reproducing injection text even inside evaluation scenarios and
rationales. Hiring source/test hashes are `6e70bfa9...f269` /
`8048bee0...20e7`; Ruff 0.16.5 check/format and the 188-test focused set exit 0
with one intentional skip. No model or stable alias is called.

Generator-final manifest/runner `bec6e696...f960` / `5383729d...a47e` execute
two more zero-retry MiniMax calls in 8,359/12,637 ms. Both are now schema-valid,
semantically complete, and pass every gold check at score 85; their sole
remaining failure is reproducing the raw request's injection markers inside
negative safety examples despite the explicit non-echo instruction.

Ledger/analyzer/results `ca43701b...66fa` / `71d36193...5a18` /
`cf3a3c38...2f6e` replay both responses and validate two starts and finishes,
zero retries, three valid receipts, stable config `df75e01d...0922`, and final
authenticated HTTP 200 with zero temporary aliases. Readiness remains eight of
nine. Since prompt-only non-echo wording has reached full structural quality
but not marker safety, the next bounded repair removes the raw request from the
initial hiring-generator projection and supplies only the governed work unit,
verified gap, and workforce facts already sufficient to design the role.

The initial hiring projection now implements that boundary: raw request text is
replaced by a one-way `request_hash` carrying no instruction authority, while
the governed work unit, verified gap, and complete workforce remain available.
The same content-free object flows into a bounded critic repair. Hiring
source/test hashes are `e69a0624...7956` / `efec54af...b1a4`; Ruff 0.16.5
check/format and the 188-test focused set exit 0 with one intentional skip. No
model or stable alias is called.

Content-free manifest/runner `e3ddc1ba...f4a4` / `5e973a33...b8ed` then execute
two zero-retry MiniMax M3-off generation calls. The raw request is provably
absent. The first returns `{"action":"none"}` in 966 ms and scores 15; the
second returns a complete injection-safe score-100 contract in 10,336 ms. The
distinct nonces and response hashes disprove an identical-prompt replay, but
the route is still not repeatable.

Ledger/analyzer/results `038c5195...853c` / `306c8b80...7773` /
`c2a7f326...4e03` replay both responses, validate two starts and finishes, zero
retries, three valid receipts, stable config `df75e01d...0922`, and final HTTP
200 with zero temporary aliases. Readiness remains eight of nine. Because the
remaining failure is an isolated invalid enum rather than a stable prompt-shape
defect, the next bounded package compares two fresh M3-off calls with two
M3-adaptive calls on the exact content-free fixture without changing product
code.

MiniMax comparison manifest/runner `95b546c5...f445` / `9cd28015...c04d`
execute exactly four zero-retry calls on that same content-free fixture. M3-off
returns one score-100 contract in 13,347 ms then one transport/JSON failure in
9,901 ms. M3-adaptive returns one score-80 schema failure in 22,007 ms then one
transport/JSON failure in 14,922 ms. Neither route is repeatable.

Ledger/analyzer/results `b339c776...4995` / `d7c2326b...fb2c` /
`c4ca7581...6143` replay both saved responses, validate four starts and finishes,
zero retries, six valid receipts, stable config `df75e01d...0922`, and final
authenticated HTTP 200 with zero temporary aliases. Readiness remains eight of
nine and MiniMax is rejected as the generation fallback. The next bounded
package tests two Z.AI GLM-5-Turbo-off and two GLM-5-Turbo-on calls against the
exact content-free fixture; those are the only non-OpenAI routes that previously
returned semantically complete generator contracts.

Z.AI comparison manifest/runner `0f6bdd40...541f` / `3e01d850...727e`
execute exactly four zero-retry content-free calls. GLM-5-Turbo-off reaches the
unchanged 48-second boundary twice at 48,137/48,075 ms; Turbo-on does the same
at 48,065/48,035 ms. No response object returns, so both routes are rejected.

Ledger/analyzer/results `a28bfd31...9709` / `5eb629c0...aee3` /
`d95cf6da...bb3f` validate four starts and finishes, zero retries, six valid
receipts, stable config `df75e01d...0922`, and final authenticated HTTP 200 with
zero temporary aliases. Readiness remains eight of nine. The next bounded
package prewarms then measures two calls each for local Qwen3 Coder 30B and
Llama 3.1 8B against the shorter content-free fixture; both previously returned
semantically complete score-80 generator contracts before the shape repairs.

Local comparison manifest/runner `b4e41e99...bb48` / `b7543b0b...62cb`
execute exactly six zero-retry calls: one counted warmup and two measured calls
per model. Qwen3 Coder 30B warms in 21,882 ms, then returns two distinct,
schema-, semantic-, gold-, and injection-valid score-100 generator contracts in
21,483/16,928 ms. It closes the ninth different-provider pair within the 20s
warm target on the second sustained call. Llama 3.1 8B warms in 5,850 ms but
scores 47.5 twice in 18,741/15,477 ms and is rejected.

Ledger/analyzer/results `857ea7f3...7799` / `e6af98fd...2e39` /
`055044a5...b793` replay four measured responses, validate six starts and
finishes, both warmups, zero retries, six valid receipts, exact stable config
`df75e01d...0922`, and authenticated HTTP 200 with zero temporary aliases. The
matrix is now nine of nine. Stable routes remain unchanged pending one atomic
exact-config update and forced-failure proof.

Live route inspection then found that the declared
`workforce.hiring.safety_repair` route was not consumed: the bounded repair
loop silently reused the hiring-generator providers and duplicated the first
unsafe security-review attempt in its durable sequence. The narrow runtime
repair resolves that exact route per harness, uses the resolved repair model as
the creator identity for the following isolated review, and retains each
attempt once. Ruff check/format, `git diff --check`, and the five focused
hiring/decision suites pass with 189 tests and one intentional skip. The
nine-stage LiteLLM projection can now bind every measured stage before live
fallback proof.

The host's shared LiteLLM 1.94 gateway retains a foreign/global three-retry
policy, so Agency now sends the supported per-request
`x-litellm-num-retries: 0` override on every LiteLLM structured call. This
leaves global policy untouched while permitting the gateway's separate
order-based fallback path to advance from order 1 to order 2. The exact header
regression, all 68 roster/provider adapter tests, Ruff check/format, and
`git diff --check` pass. A broader 161-pass diagnostic exposed two existing
live-operator-state-coupled preflight expectations; the scoped adapter suite is
green and the required named spine remains reserved for the post-install gate.

The additive production projection begins under manifest/runner/ledger
`354fdeff...585d` / `b9e70c15...a442` / `82491c19...669b`. Planner,
recruiter, and critic each prove the real order-2 fallback after one disposable
order-1 loopback failure (`x-litellm-attempted-fallbacks=1`), then the exact
order-1 primary with zero fallbacks; all six accepted calls are HTTP 200,
quality 100, and deployment-UUID reconciled. Recruiter's first MiniMax primary
attempt transiently used its healthy OpenAI fallback, then the next ordinary
call proved the MiniMax UUID at quality 100, demonstrating the desired
unattended behavior without a retry.

The first cold Qwen Coder reranker fallback reached its 45-second deployment
ceiling. Reconfiguration adds `keep_alive=-1`; the immediate 45-ms retry is a
bounded negative because LiteLLM correctly retains that exact deployment UUID
in cooldown. At the clean checkpoint, planner/recruiter/critic each have their
two final deployments, reranker has only its exact resident order-2 fallback,
all other new aliases remain absent, and no disposable failure deployment
survives. Resume after cooldown with the retained runner; do not recreate or
delete the three proven aliases.

Cooldown resume succeeds for the resident reranker in 3,836 ms, then its
forced fallback and MiniMax primary pass in 1,288/3,538 ms. Child judge,
hiring generator, hiring critic, and security review also pass both forced
fallback and normal primary with deployment UUIDs reconciled, zero retries,
and quality 92.5--100. Ledger `784181c9...8c5a` therefore closes eight aliases.
Safety repair alone returns an immediate MiniMax transport 408 after the
disposable primary failure; it remains unreferenced with the exact order-2
fallback plus disposable order-1 deployment. Resume after its 60-second
cooldown; all eight proven aliases already contain their final two deployments.
