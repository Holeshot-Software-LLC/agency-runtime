---
title: "AR-203: Prove product-canary workspace writes and exact activation"
status: in_progress
category: roadmap
created: 2026-07-30
updated: 2026-07-31
tags: [evaluation, codex, activation, sandbox, evidence, regression]
related:
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/handoffs/issue-AR-203.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-203
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/183
depends_on: [AR-201]
blocks: [AR-200]
---

# AR-203: Prove product-canary workspace writes and exact activation

## Problem

The AR-201 product trial exposed two independent harness defects. First,
`execute_product_host` collected the legacy recent-activity summary and passed
it to the Codex proof evaluator, which now requires
`agency.canary-activation-evidence.v1`. The evaluator therefore reported
`exact Codex activation evidence contract was not available` even though a
direct post-trial Store query returned that exact schema with `proven: true`.

Second, the fresh isolated Codex response reported that application work was
blocked by a read-only workspace policy despite the product command requesting
`--sandbox workspace-write`. The trial created no files. The isolated profile
does not inherit the current profile's trusted-project entries, and existing
tests assert only the requested CLI flag, not the effective model-facing write
contract.

The terminal AR-203 trial exposed an earlier activation boundary as well. The
ordinary product backend still launched Codex with `--ephemeral` and without
`multi_agent_v2` or `agents.enabled=true`, even though the installation
activation canary had already removed ephemeral mode and enabled both native
agent controls. The product hook child also did not require the pre-existing
evidence Store, and its result projection could not distinguish a hook that
never started from one that accepted an event and then failed.

## Current state

The Codex process completed with exit zero and the isolated Agency plugin was
registered and enabled. It emitted one route, three correlated model receipts,
and two finalization rows. The exact Store snapshot resolves the trial trace,
but the product report used the incompatible summary projection. Collaboration
projection also observed eight non-allowlisted command/MCP items and no Agency
spawn/wait chain because staffing abstained.

The product backend now writes one exact trusted-project entry into only the
private temporary Codex home and verifies a hash-only attestation for that
canonical workspace. It retains the workspace-write sandbox with no added write
directory or general sandbox bypass. The same model invocation must create a
fixed, prompt-bound sentinel; missing or unproven write evidence skips product
grading, and a preexisting sentinel is rejected.

Codex Agency mode now queries the exact activation snapshot using the hash of
the wrapped prompt actually sent to the host while retaining the canonical
product prompt hash separately. Focused review passes 85 tests. The two new
product decision mutations are killed inside the 13/13 decision-conformance
gate with zero survivors or invalid results. The named fast production spine
passes 675 tests with 6 skipped, the dashboard UI passes 109 tests, and routing
evaluation 1.3.0 passes every configured gate.

PR 184 merged normally as exact main revision
`dbd5502847b822825c7f3b99a18662949c98de0b`; exact build
`0.1.0+gdbd5502847b8` is installed and refreshed for Codex and ZCode only.
Hosted GitHub jobs did not execute repository steps because account billing or
spending-limit enforcement refused each job.

The one authorized final trial, `ar203-dbd5502-ordinary-01`, is terminal
`NO-GO`. Codex completed with host exit zero in 87.813 seconds and returned a
nonempty response, while the product command correctly exited one. The exact
isolated-workspace trust projection was proven without changing the persistent
profile, but the model-written sentinel was absent, so effective
workspace-write was not proven and product grading was skipped. The exact
activation query returned `route_not_found`; all route, run, load, delegation,
receipt, and finalization cardinalities were zero. The final response had no
Agency header. Correction count was exactly zero, but that narrow result cannot
compensate for a missing header and absent activation evidence.

The orchestration process itself required elevated authority to create the
`C:/tmp` trial directory before the restricted Codex run. That is concrete
evidence of a workspace capability mismatch and is the first next diagnostic,
but this trial does not prove it caused the separate missing Agency route.

The current bounded repair removes `--ephemeral` from product execution,
enables Codex multi-agent V2 and the agents capability, requires the exact
existing Store in the isolated hook process, and records only allowlisted
content-free accepted/completed/failed hook-stage counts. Ordinary product
trials still do not opt into the activation canary's single-child rollout
topology because the product goal requires multiple independent work units.
Codex delegation context now requires `fork_turns=none` so each child receives
only the exact hook-injected specialist context instead of inheriting the
parent's full history. The new and directly affected tests pass 26 focused
cases. Decision conformance passes its baseline and kills all 19 curated
mutations with zero survivors or invalid results. Two bounded review passes
found and repaired Windows CRLF hook-marker parsing, added real handler-failure
stage coverage, and corrected a stale multi-unit assertion that had accepted an
unevidenced model line. The complete changed-component suite passes 200 tests
under warning-strict mode.

The exact post-review tree is demo-ready locally. The named fast Python spine
passes 675 tests with 6 skipped, the dashboard UI passes 109 tests, and routing
evaluation 1.3.0 passes every gate with routing p95 4.710 ms and cache-hit p95
1.448 ms. A fresh decision-conformance run on the same tree again kills 19/19
mutations with zero survivors or invalid results. Documentation validation
passes 551 files, and Ruff check plus format validation pass all 603 Python
inputs. The dashboard UI's restricted first attempt stopped at the outer
sandbox's expected `spawn EPERM`; the authorized normal-owner rerun passed.

PR 186 merged that exact repair as
`830b878859318bc1288858ba65ba580bd98bf53e`. The immutable upgrade planner
resolved that full revision, and exact build `0.1.0+g830b87885931` is installed
for Codex and ZCode only. After the owner trusted the refreshed hooks and
restarted Codex, trial `ar203-830b878-ordinary-02` proved the hook and route
start: one route, one run, three model receipts, two finalizations, and nine
typed work units were persisted under trace
`019fb417-f166-7461-a1db-e53ee0007045`.

The trial is terminal `NO-GO`. The planner response was applied, the recruiter
response was rejected as `provider_response_contract_invalid`, and its bounded
repair ended `provider_no_valid_response`. Routing therefore degraded and
abstained with `workforce_inference_failed`; no specialist, hiring case, load,
delegation, or worker run followed. The seven-field header was structurally
present only after one correction, which independently fails the zero-correction
gate. Isolated workspace trust was proven without changing the persistent
profile, but the proof file was missing, the workspace stayed empty, and product
validation correctly skipped as `workspace_write_not_proven`.

The first source repair is now implemented without restoring deterministic
selection. The bounded repair receives a distinct high-priority system contract
that requests every listed failed row and explicitly omits retained rows. The
durable route now projects only allowlisted planned-unit and invariant-code
pairs, so a repeated rejection will expose the exact safe boundary rather than
only `provider_response_contract_invalid`. Two review passes are complete. The
changed boundary passes 107 tests with 1 skipped, and decision conformance kills
21/21 mutations with zero survivors or invalid results and unchanged source.
The named fast Python spine passes 675 tests with 6 skipped, dashboard UI passes
109 tests, routing evaluation 1.3.0 passes every gate, documentation validation
passes 551 files, and Ruff checks all 603 Python inputs.

PR 187 merged that first recruiter repair as exact main revision
`26a3911e371e42bc004faabaa2fd0b802bf50fdd`, and immutable upgrade installed
exact build `0.1.0+g26a3911e371e`. Codex and ZCode were refreshed. The owner
expanded this README-story proof to include the dashboard; its current-user
service is installed, owned, enabled, active, manifest-current, and reachable.
Opening the authenticated page remains an attended action because automated
execution could not satisfy the non-exporting OS operator-presence verifier.

Codex activation verification then stopped before model use: all eight managed
events are present and enabled, but all eight hashes are `modified`, with zero
trusted and zero managed by the settled trust record. No trust bypass was used,
no attestation was written, and no model invocation was attempted. Because the
post-merge Codex review found two valid P1 source defects, this build is
invalidated before asking the owner to retrust it.

The valid review fixes now enforce the recorded ordered failed-unit tuple
before any accumulator mutation and hash sensitive planner-derived unit IDs in
durable receipts. The third P1, alleging broken ledger ancestry, is disproven
by merge `26a3911` preserving branch head `d01338d` and substantive commit
`d470993`. The post-review boundary passes 108 tests with 1 skipped, and
decision conformance kills 23/23 mutations with zero survivors or invalid
results and unchanged source. Its named fast gate passes 675 Python tests with
6 skipped, 109 dashboard UI tests, routing evaluation 1.3.0 with every gate
green, documentation validation for 552 files, and Ruff check plus format
validation for all 603 Python inputs. Local commit `b45bd28` freezes that
reviewed tree. [PR 188](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/188)
merged it with commit-preserving ancestry as exact main revision
`5e3fab622b75f257e0ab4b74f1cc2c6d43b1d748`; its only Codex review P1 named
an unreachable synthetic commit and was disproven by the remote graph plus the
GitHub commit API.

Exact build `0.1.0+g5e3fab622b75` is now installed. Codex refresh install ID
is `a352175a-b4e9-456e-973c-90e76ddb77da`; ZCode is registered; the dashboard
is owned, active, manifest-current, drift-free, and reachable. Codex activation
preflight observed all eight expected events enabled but all eight hashes
`modified`, with zero trusted and zero managed. It persisted no attestation
and attempted no model call.

The delivery outcome is frozen as "README's main story works in reality" for
the ordinary Codex path on this machine. Each package stops at its first
terminal failure or 45 minutes, permits one live trial per exact build, and
produces a durable evidence checkpoint before any repair. A second failure at
the same causal boundary stops for owner direction instead of looping.

[PR 191](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/191)
merged the complete README-story source package as exact revision
`cc322381ec932452f0575445dc174510e4caad6f`. Exact build
`0.1.0+gcc322381ec93` is installed. Current-profile activation then proved a
real `code-reviewer` route with one grant, consumption, specialist load, native
spawn/wait, completed delegation, worker run, accepted finalization, and zero
response corrections under trace `019fb676-df24-72c1-bf3e-af3a23222ff8`.

The one product trial for that exact build,
`ar205-cc32238-readme-01`, is terminal `NO-GO`. It ended after 49.327 seconds
with CLI exit one and an empty workspace. Exact session evidence proves the
hook ran and reached `preflight_failed`, but the product projection mislabeled
that boundary as `route_not_found`. A bounded direct replay then identified the
first causal defect: planner instructions omitted deterministic assurance
requirements that the validator later vetoed, and recruiter inference lacked
the exact typed uncovered-requirement evidence needed to distinguish a safe
team from a roster gap.

The current source candidate repairs those contracts without synthesizing a
plan or selecting a worker deterministically. A real provider replay now
accepts a nine-unit inference-authored plan and a nine-assignment specialist
team spanning discovery, paired Python/TypeScript implementation, test
authorship, correctness, security and accessibility review, documentation and
documentation review, and independent test evidence. This is routing-boundary
proof only. The named fast spine passes 636 tests with 6 intentional skips,
dashboard UI passes 110 tests, routing evaluation 1.4.0 passes every gate,
decision conformance kills 44/44 mutations, documentation validates 571 files,
and Ruff checks all 602 Python inputs. The next exact merged build still needs
one fresh product trial to prove delegation, workspace write, artifacts, and
zero corrections together.

[PR 192](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/192)
is the reviewed merge candidate. Its first Codex review found three valid
contract leaks: planner parsing ignored a configured work-unit limit below 16,
release evidence could satisfy the wrong requested operation or negated prose,
and documentation normalization removed explicitly requested communication
capability. The bounded repairs now pass 79 planner/intent tests plus 115
routing, selection, hiring, and decision-conformance tests with one intentional
skip. A second review pass, exact merge/install, and the one fresh product
trial remain.

## Approach

1. For Codex Agency product trials, read the exact activation snapshot by host
   and prompt hash, matching the ordinary activation canary proof contract.
2. Keep legacy recent-activity summaries only for modes and hosts whose proof
   contract expects them.
3. Bind any isolated trusted-project configuration to the one existing empty
   trial directory and the private temporary Codex home; never mutate the
   owner's persistent trust configuration.
4. Add a host-level write probe whose success is attributable to the same
   effective Codex workspace policy, and fail before product grading when that
   contract is not proven.
5. Add regressions that fail under the current summary mismatch and under an
   isolated read-only profile.
6. Preserve product safety: no general sandbox bypass and no write authority
   outside the confirmed trial directory.
7. Persist the ordinary Codex parent turn and explicitly enable native
   multi-agent V2 plus the agents capability.
8. Require hook children to open the exact existing Agency Store and expose
   only bounded, allowlisted hook-stage counts in product evidence.
9. Keep multi-unit product evidence separate from the activation canary's
   deliberately single-child rollout parser, and isolate each Codex specialist
   child with `fork_turns=none`.
10. Repair only the recruiter response acceptance and bounded-repair contract
    proven by the exact live trace; keep online selection inference-owned.
11. Require the replacement trial to accept a real specialist team for the
    fixed robust prompt, or record a defensible gap and an actual hiring
    decision; never manufacture hiring merely to satisfy the demo.
12. Resolve valid merged-PR review findings before retrust: enforce exact repair
    IDs before mutation and sanitize sensitive planned-unit identities in
    durable evidence.

## Dependencies

ADR-0077 owns behavioral activation proof. ADR-0112 owns exact staged evidence
and accepted finalization. AR-201 supplies the exact terminal trace that
demonstrates both mismatches.

## Acceptance

- [x] Codex Agency product evaluation reads
  `agency.canary-activation-evidence.v1` for the exact prompt hash and never
  reports that schema unavailable when the Store returns it.
- [ ] The isolated Codex profile proves effective workspace-write authority for
  the exact empty trial directory without changing persistent user trust.
- [x] The product backend retains sandboxing and cannot write outside the trial
  directory.
- [x] A failed write proof stops before grading and is reported separately from
  workforce selection or product-quality failures.
- [x] Focused tests fail against both current defects and pass after repair.
- [x] Ordinary Codex product execution persists the parent turn, enables native
  multi-agent V2 and agents, and does not impose the single-child activation
  rollout topology.
- [x] Product hook execution requires the exact existing Store and projects
  bounded hook-stage evidence without retaining hook input or raw stderr.
- [x] Codex specialist launch instructions require `fork_turns=none` and the
  exact persisted native task name.
- [x] PR 186 is merged and its exact revision is installed for Codex and ZCode
  only without selecting the dashboard.
- [x] The exact installed trial starts the hook and route, persists nine typed
  work units, and distinguishes recruiter contract failure from activation,
  hiring, delegation, and workspace-write evidence.
- [x] The recruiter repair uses a non-contradictory partial-row system contract,
  and durable rejection evidence is bounded to allowlisted unit/invariant pairs.
- [x] PR 187 merged and exact build `0.1.0+g26a3911e371e` was installed before
  review invalidated it for live use.
- [x] The post-review repair passes 108 focused tests with 1 skipped and kills
  23/23 decision-conformance mutations.
- [x] The post-review repair passes the named fast gate.
- [x] The post-review repair merges and is exact-installed for Codex, ZCode,
  and the dashboard.
- [x] The dashboard service is installed and locally reachable.
- [ ] An attended browser opens and renders the authenticated dashboard page.
- [x] Exact installed activation passes through attended trust or the supported
  one-invocation bypass, with bypassed evidence never mislabeled trusted.
- [x] Recruiter response acceptance or bounded repair produces a defensible
  inferred staffing plan for the fixed README-story prompt.
- [ ] The replacement trial selects and launches at least one specialist/team,
  or records a defensible gap plus an actual hiring decision.
- [ ] The next ordinary canary reports exact activation evidence and can create
  required artifacts when workforce execution reaches the parent model.
