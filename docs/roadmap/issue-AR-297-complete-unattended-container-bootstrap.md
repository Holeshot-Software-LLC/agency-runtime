---
title: "AR-297: Complete unattended container bootstrap"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-27
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
depends_on: [AR-300, AR-301, AR-302, AR-303, AR-304, AR-305, AR-306, AR-307, AR-308, AR-309, AR-310, AR-311, AR-313, AR-314, AR-315, AR-317, AR-318, AR-319, AR-320, AR-321, AR-322, AR-324]
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
