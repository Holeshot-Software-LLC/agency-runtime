---
title: "AR-255: Make native child staffing inference-owned and host-proven"
status: open
category: roadmap
created: 2026-08-12
updated: 2026-08-16
tags: [routing, inference, native-child, codex, evidence, critical-path]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/codex_spawn_provenance.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/child_delivery_evidence.py
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-255
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-119, AR-180, AR-252, AR-253]
---

# AR-255: Make native child staffing inference-owned and host-proven

## Problem

The current JIT hook pre-narrows and compatibility-selects child cards in
deterministic local code, including a fail-open branch that can deliver every
candidate. That violates ADR-0118. Separately, the Codex canary can treat an
Agency-authored `specialist_load` row as card-delivery proof even though the
authoritative evidence contract requires an artifact written by the host.

The observed Codex Sol path exposes model-authored plaintext `task_name`, but
its `message` was encrypted and opaque to the hook. Codex 0.147 also has a
conditional plaintext path marked in the host response item, while that marker
is absent from the documented hook payload. Neither an unvalidated label nor a
plaintext-looking message is authority; the persisted exact host call must be.

## Current state

Runtime checkpoint `7e1b3603` makes inference the only native-child staffing
authority, preserves a valid multi-card result exactly, and fails open unstaffed
when inference is absent or invalid. It also collects Claude's canonical child
artifact inside an allocator-sealed disposable profile and current invocation
window, then passes a sealed one-use capability to canary evaluation. Store
rows, backend mappings, CLI input, caller-created roots, stale copies, and
replays cannot mint that capability.

Implementation and simulation are proven, not installed or live behavior. The
SafeClaude integration uses a test-managed install and fake process runner.
Claude's three prior-candidate artifacts remain historical context only.
Candidate `211563c7` correctly leaves unmarked calls unstaffed, preserves the
exact CLI `0.147.0` TUI/exec profiles, and adds a separate sealed Desktop
`0.147.0-alpha.6.6` profile for its observed root/depth-one/depth-two V2
ancestry. Scoped tests, mutations, authentic probes, and independent reattack
pass, so Codex Rule-4 Implementation and Simulation are proven. Exec depth-two/
deeper is unobserved and must remain fail open. Exact-install and live proof
remain open.

## Approach

Carry a validated inference decision to the native spawn boundary without
restoring Job B or allowing deterministic code to choose workers. Deterministic
logic may filter hard-ineligible cards, validate hashes and compatibility, and
reject invalid output; it may not rank or replace the inference result. If no
valid inference survives, deliver no card and emit an honest diagnostic.

Make the host-authored child artifact the sole green Rule-4 authority. Agency
Store rows may index or diagnose correlation but cannot prove delivery. For
Codex, accept a plaintext rewrite only after bounded canonical host-transcript
records match the exact session, turn, tool call, namespace, arguments,
current-call empty encrypted-argument marker, and any required cross-file causal
ancestry. Treat the documented transcript instability as versioned input and
fail open unstaffed on drift. AR-180 exact-installs and live-proves that channel
after source and adversarial simulation pass.
ADR-0159 governs this authorization boundary and its fail-open behavior.

## Dependencies

- ADR-0118 is the selection authority.
- `child_delivery_evidence.py` is the evidence-authority starting point.
- AR-209 is historical provenance for the retired plan-row transport and must
  not be restored as the fix.

## Checkpoint evidence

- Runtime `7e1b3603` and ledger `fb650b04` contain the implementation and its
  required traceability record.
- The final AR-255 focused package passed 229 tests with 1 skipped. The named
  fast Python production spine passed 673 with 6 skipped, dashboard UI passed
  134, and documentation validation passed for 685 Markdown files.
- Ruff lint and format, policy availability, worklog consistency, metadata, and
  `git diff --check` passed.
- Two independent adversarial passes found and drove fixes for Store-only proof,
  caller-selected roots, same-candidate replay, isolated install identity, and
  stale copied artifacts. The final reattack reported no unresolved Critical or
  High finding; its focused child-evidence suite passed 54 tests.
- Same-process private reflection and same-account transcript plus Store
  forgery remain the documented threat-model exclusion. No installed or live
  host layer advances from this checkpoint.
- The AR-180 read-only preflight identified exact Codex `0.147.0` and Desktop
  runtime `0.147.0-alpha.6.6` binaries, proved the current Sol/TUI spawn remained
  encrypted, and located a conditional host-marked plaintext path in the tagged
  `0.147.0` source. It did not run an Agency canary or change installation or
  trust state.
- Codex source `966845cc` and ledger `d9ee4a0a` add the sealed bounded scanner,
  double hook revalidation, and atomic replay guard. The 303-test focused slice,
  673-test fast spine with 6 skipped, 134 dashboard tests, Ruff, routing eval,
  and whitespace checks passed. Independent attack and the current-candidate
  mutation run remain open; Installed and Live layers do not advance.
- Independent attack found one Rule-4 completeness defect in nested rollout
  identity and one evidence-integrity defect in post-persistence drift cleanup.
  Repair `2fe5e9ec` and ledger `9eb6c683` address both with exact TUI/exec
  ancestry and transactional rollback. Its focused 206-test slice, Ruff, format,
  and whitespace checks pass.
- Hardening `e8b60f64` and ledger `4026ddd6` close the subsequent exact-schema,
  duplicate-identity, Store-projection, retry, and cleanup findings. The current
  342-test focused slice, 112/112 mutation run, 673-test fast spine with 6 skips,
  134 dashboard tests, routing gates, and independent review pass. Installed and
  Live layers remain unproven.
- Cross-file hardening `45b21cdc` and ledger `01730614` authenticate authentic
  one-record TUI ancestry across unique bounded canonical parent/root files.
  The census resolves 11/11 chains across depth-one sparse/inherited and depth-
  two sparse/inherited variants; the largest seals 48,678,898 external bytes and
  resolves in 3.809 seconds. The parent passed 365 focused tests, the 673-test
  fast spine with 6 skips, and 19/19 scoped mutations with a green baseline and
  unchanged source. The independent reviewer passed 200 tests, killed 19/19,
  and found no issue at any severity. The 134-test dashboard suite, routing,
  Ruff, format, and documentation/schema gates pass. The complete current
  decision-conformance evaluator exited zero in 883.1 seconds: baseline passed
  in 169,548 ms, all 131/131 mutations were killed, zero survived or were
  invalid, and `source_unchanged=true`. Installed and Live layers do not advance.
- Desktop hardening `211563c7` and ledger `ee8db873` add the sealed v3 profile
  pinned only to runtime `0.147.0-alpha.6.6`; the CLI profiles are unchanged.
  Desktop accepts one exact root and only 13 atomic observed depth-one/depth-two
  child tuples, rejecting eight tested unobserved cross-products. It requires
  V2 lineage, canonical owner files, both depth-two causal edges, adjacent direct event and
  output, sealed copied history/files/profile/currentness, the 64 MiB aggregate
  external bound, and the exact empty marker on the current call. Disabled
  guardians, greater depth, mixed profiles, and drift fail open unstaffed.
  Focused provenance/hook verification passed 288/288, focused plus the anchor
  passed 289/289, and the fast spine passed 673 with 6 skips. The Desktop
  baseline passed and killed 20/20 mutations with zero survived or invalid and
  `source_unchanged=true`; independent verification reproduced those results
  and found no issue at any severity. A content-safe authentic probe resolved
  52/52 V2 chains (47 depth one, 5 depth two), with maximum external ancestry
  32,650,955 bytes and maximum resolver time 2.765 seconds. All 65 observed
  Desktop calls were encrypted and unmarked, so State, Installed, and Live do
  not advance. For `211563c7`, dashboard UI passed 134/134, routing passed every
  threshold, and Ruff lint/format passed. The expanded decision-conformance
  evaluator remains pending; the 131/131 result above remains candidate-
  `45b21cdc` history.
- **2026-08-16, confirmed live cause of `native_child_inference_invalid`.** The
  first canary to complete on `980eb2d1b755` staffed the parent twice
  (`code-reviewer`, confidence 0.9 and 1.0) but failed every one of seven child
  routings, so no card ever reached a child and the collector reported
  `delivery_marker_absent`. **The children were not failing inference — they
  were abstaining, and the runtime records a sanctioned abstention as an invalid
  decision.** `build_judge_prompt` tells the model to "Select zero to 3
  specialists" and to "Return an empty selected_ids list when none fits";
  `validated_decision` accepts that empty answer, bounding only
  `len(selected) > max_sel`, and `applied_result` returns
  `status="applied"` carrying the model's own confidence; then
  `native_child_staffing` requires `1 <= len(selected)` and rejects the same
  answer as `native_child_inference_invalid`. Three layers, two contracts.
- **How the live rows prove it, without new instrumentation.** Every judge
  failure path hardcodes `confidence: 0.0`, and only `applied_result` preserves
  a model confidence, so the seven rows carrying **0.95, 0.95, 0.95, 0.95, 0.95,
  0.9 and 0.85** prove the judge returned `status="applied"` with
  `inference_mode="inferred"`. That excludes the status branch and the
  provider-receipt branch (distinct reason code), and `candidate_count: 33`
  excludes both early non-mapping branches, which record 0. Only the
  `selected_ids` check remains, and four of its five disjuncts — non-list,
  over-budget, unknown id, duplicate — are already enforced upstream by
  `validated_decision` over the same catalog using the same `agent_identity`
  function. The lower bound is the one disjunct nothing upstream enforces.
  Reproduced offline: an empty answer is the only case that the protocol accepts
  and staffing then rejects with the model's confidence intact.
- **Two projection fields are structurally constant on this path and must not be
  read as evidence.** `_unstaffed` always writes `selected_ids: []`, and the
  complete-universe judge always passes `top_score=0.0`. Neither reflects what
  the model returned. `candidate_count: 33` is the eligible catalog after
  host/platform/tool filtering, against 283 in the full roster; the gap is
  expected filtering, not a defect.
- **This is a behaviour contract, not an oversight.**
  `test_invalid_duplicate_unknown_and_over_budget_inference_is_rejected_whole`
  parameterises `[]` alongside duplicate, unknown, and over-budget answers, so
  changing it renegotiates a written test contract. It is also **not** the same
  fault as the parent-side ranking failure: the parent recruiter has legitimate
  abstention outcomes (`recruiter_abstained`, `no_safe_sufficient_team`), while
  the child path collapses abstention into "invalid".
- **Why the model declined, seven times out of seven: it was never shown a
  single specialist who could do the work.** Reproduced against the live
  283-agent roster at generation 289 with the child's own arguments
  (`host="claude"`, `platform="win32"`, `available_tools=None`,
  `capability_status=""`): `filter_eligible_catalog` returns **33 eligible and
  250 rejected, and every one of the 250 carries the same reason,
  `tool_capabilities_unproven:unknown`.** `code-reviewer` and
  `application-security-engineer` — the two the parent had just selected — are
  both in the rejected 250. What survives is the tool-free remainder:
  `anthropologist`, `book-co-author`, `brand-guardian`, `cartography-designer`,
  `game-designer`, `historian`, `level-designer`, `linkedin-content-creator`,
  `narratologist`, `personal-growth-mentor`, `resume-tailor`,
  `video-optimization-specialist`, `xr-interface-architect` and twenty more.
  Asked to staff a Python regression review from that set and told to return an
  empty list when none fits, the model returned an empty list. **The abstention
  was correct.** The defect is the universe it was given.
- **The two paths feed the same filter from different sources.**
  `selector/pipeline.py` calls `current_host_capability_receipt(...)` and passes
  `available_tools=capabilities.capabilities`, `inference_surface` and
  `capability_status` into `filter_eligible_catalog`;
  `adapters/base.py` builds that receipt with
  `native_adapter_capability_receipt(host, platform=..., session_id=...,
  trace_id=..., restricted=capabilities_restricted)`. The native-child call in
  `adapters/hooks.py` passes **none** of it, so `staff_native_child` defaults to
  `available_tools=None` and `capability_status=""`, which
  `filter_eligible_catalog` documents as "tool capability unproven" and fails
  closed on every tool-declaring specialist. One filter, two sources of truth.
- **Two hypotheses tested and refuted.** `_KNOWN_INFERENCE_SURFACES` is only
  `{"litellm"}`, so `host="claude"` is *not* reinterpreted as an inference
  surface and the execution host is not lost. And the identity functions agree:
  `judge._agent_id` delegates to the same `agent_identity` the staffing check
  uses, so a selected id can never be unknown to one layer and known to the
  other.
- **Shipped: abstention is recorded as abstention.** A solicited empty selection
  now returns `native_child_no_specialist_needed` with status
  `inference_abstained` and `inference_mode: "abstained"`, keeping the judge's
  real confidence and candidate count, and still failing open unstaffed;
  `preflight_routing_failure_reason` maps it to
  `substantive_specialist_unavailable`, beside the existing
  `child_budget_abstained` precedent. `[]` was removed from
  `test_invalid_duplicate_unknown_and_over_budget_inference_is_rejected_whole`
  and given its own test. **This changes the record, not the outcome** — the
  child still receives no card, so Rule 4 stays at zero until the catalog the
  child judge sees contains someone who can do the work.
- **Shipped: the child proves its capability instead of leaving it unknown.**
  When a caller supplies neither `available_tools` nor `capability_status`,
  `staff_native_child` now builds the same `native_adapter_capability_receipt`
  the parent adapter builds, and threads the result through both
  `filter_eligible_catalog` calls and the context fingerprint so the post-decision
  re-check cannot drift. The vision decides this: deterministic code may "enforce
  hard eligibility" but "may not make or erase the staffing decision", and
  **unproven is not hard-ineligible** — it removed 250 cards before inference ran,
  which is the "deterministic layer that ... changes what gets staffed ... even
  when the inference call still happens" the differentiator section forbids. It
  also made `candidate_scope="complete"` false in the runtime's own vocabulary.
  Measured on the live roster: the child universe goes **33 to 64 of 283**,
  `code-reviewer` becomes eligible, and every remaining rejection is genuine hard
  eligibility — `missing_capabilities:browser-interaction,web-research`,
  `unsupported_tool_platform:windows`, and
  `missing_capabilities:sandbox-environment,security-analysis`, which is why
  `application-security-engineer` stays out on this box.
- **The fence is unchanged for a caller that has proven the opposite.**
  Derivation runs only when nothing was supplied; an explicit
  `capability_status="unknown"` still hard-filters every tool-declaring card, and
  `restricted=True` yields an unproven receipt with no execution host, which the
  resolver refuses. A new `capabilities_restricted` parameter carries that
  through, defaulting closed to the adapter's own default. Both directions have
  tests. 367 tests pass across staffing, duplicate-launch, preflight bounds,
  mandatory inference, canary contract, store coverage, decision conformance,
  native-child adapter, Claude native-child hooks, adapter parity and host hooks.
- **The canary parent transcripts are gone.** Sessions `a7dcbfd4` and `42227b09`
  ran inside the ADR-0158 disposable profile and are absent from
  `~/.claude/projects`; a home-wide search found nothing. The exact child task
  strings are therefore unrecoverable, and only the seven `query_hash` values
  survive. Future runs need the abstention reason code above to be legible at
  all.

### First live host run of both repairs, and what is left (2026-08-16)

The `33ac14fcdac4` Claude canary is the first run where **parent staffing
succeeded on a host**, so the child path was reached for the first time. Both of
today's AR-255 repairs fired live, and both behaved as designed.

Parent, trace `9b7890ac`, routing `6f383f65`:

| field | value |
|---|---|
| status / source | `accepted` / `computed` |
| selected | `code-reviewer`, `senior-secops-engineer` |
| candidate count | 284 |
| recruiter latency | 124,165 ms |

Both cards were written to `specialists_loaded`, the receipt correlated, and
`isolated_plugin` came back `loaded: true, invoked: true`. Unmet prerequisites
dropped from three to two.

Child, routing `28cfc40b`, 5,611 ms:

~~~json
{"status": "inference_abstained", "native_child_reason": "native_child_no_specialist_needed",
 "candidate_count": 65, "inference_attempted": true, "selected_ids": []}
~~~

**The capability receipt worked.** The child universe is **65 of 284**, against
the 33 measured before the fix and the 64 predicted for the 283-contract roster.
**The abstention reason code worked**: the empty selection records as
`inference_abstained` with an honest reason, not as `native_child_inference_invalid`.

So the child was shown a universe including `code-reviewer` and judged that none
fit. The delegation is real and complete — `delegation_events` records
`backend: delegate_task`, `native_run_id: claude-agent:ae01af48c1d33466d`,
`error: "ok"` — but with `recommended_agent` and `retrieved_specialist_slug`
both empty, no activation receipt, and no parent scope. No cards, therefore
`delivery_marker_absent`, therefore Rule 4 stays at zero.
`native_child_delivery_verifications` still holds **zero rows, ever**.

**Rule 4 now blocks on one inference judgment, not on plumbing.** That is a
different problem from every prior blocker on this issue, and it is the first
time the question is "why did the judge decline" rather than "did the mechanism
run".

Two evidence gaps this run names, both worth closing before another run:

1. **The child decision records `candidate_count` but not which candidates.**
   Whether `code-reviewer` was in the 65 cannot be read from the receipt, only
   inferred from an offline roster computation. That is exactly the gap
   `ranked_agent_ids` closed for the parent, and it cost two days there.
2. **`source` still reads `native_child_inference_failure` on an honest
   abstention.** The status field was fixed today; this sibling label was not,
   and it re-creates the misreading the reason code exists to prevent.

Not a child problem, and tracked separately: the parent's finalization recorded
`response_invalid` with `missing: ["actual_model_selected", "recruited_via"]`.
The header shrank from five missing fields to two, and those two are parent
prose rather than staffing.

### Both gaps closed: the decline now names its own universe (2026-08-16)

`offered_agent_ids` and `offered_agent_digest` ship on the declining child
decision. The ids are the eligible universe **sorted and joined flat with `~`**,
the digest is sha256 over the complete set, and both cross the content-free
receipt boundary through the same allowlist the parent's evidence uses.

Four properties, each with a test rather than an assertion in prose:

- **Flat, not nested.** A list here is what pushed `ranked_agent_ids` past the
  reader's `maximum_depth=4` and bricked the live evidence store; a string is a
  leaf at any depth.
- **The digest covers the whole set, always.** When the ids exceed
  `MAX_RECORDED_OFFERED_AGENT_CHARS` (16,384) the ids are omitted and the digest
  stays, so a bounded record can never read as a smaller universe than the judge
  saw. A 284-slug roster is roughly 5 KB, so omission is not reachable today.
- **Slugs, not free text.** `_bounded_offered_agent_ids` fails the field closed
  on anything that is not an agent id, rather than passing an opaque string
  across the boundary.
- **The whole path, not just the projection.** The round-trip test writes through
  a real `Store` and reads back through `recent_runtime_activity` — the reader
  that failed last time while the writer's own projection was happy.

The sibling label is fixed too: a solicited decline now records
`source: "native_child_inference_abstained"` instead of
`native_child_inference_failure`. That required an addition to the source
allowlist in `store.queries.project_routing_decision`, because **an unlisted
source falls through to `"computed"`** — which would have labelled an inference
abstention as a deterministic decision, a worse lie than the one being fixed.
The failure-side helper picks the source from the status, so the two can no
longer disagree.

Also fixed in passing: `eligible_ids` was computed *after* the decline branches,
so what the judge was shown was only in scope for the paths that did not need
it. The invalid-selection path now carries it as well, since a selection naming
an agent outside the offered set is the one invalid response the offered set
explains directly.

### The judge was shown `code-reviewer` and declined (2026-08-16)

First live run of the instrument, on `95ceee1bcb81`, run `ea571f98`, child
decision `2403c5d8`:

| field | value |
|---|---|
| status / source | `inference_abstained` / `native_child_inference_abstained` |
| reason | `native_child_no_specialist_needed` |
| latency | 5,381 ms |
| offered | **66** of 285, digest `f34c49c2566f…` |

Self-consistent on its first live write: 66 ids recorded against
`candidate_count: 66`, sorted and unique, and the digest recomputes exactly. The
`native_child_inference_abstained` source survived the store's allowlist rather
than falling through to `computed`.

**`code-reviewer` was in the offered set.** So were `python-application-engineer`,
`software-test-engineer`, `test-results-analyzer`, `codebase-onboarding-engineer`,
`minimal-change-engineer`, `codebase-archaeologist` and
`ai-generated-code-security-auditor`. The judge saw them and returned an empty
list in 5.4 seconds.

**So the universe is not the blocker.** The parent selected `code-reviewer` for
the same turn from its own 285; the child was offered the same specialist and
declined it. Every prior explanation on this issue — unproven capability leaving
33 historians, an invalid model response, a plumbing fault — is now excluded by
evidence rather than by argument.

The 66 also confirm the capability filter is doing real work and doing it
correctly. `application-security-engineer` and `senior-secops-engineer` are
**absent** despite the parent selecting one of them, which matches the recorded
`missing_capabilities:sandbox-environment,security-analysis` rejection for this
box. Parent and child legitimately have different universes; that difference is
now visible rather than inferred.

**What this does not establish.** The receipt is content-free by design, so the
child's actual task is unknown. `native_child_no_specialist_needed` may well be
the *correct* answer for whatever the parent delegated — a child asked to read
one file and report back needs no specialist. The open question has therefore
moved from "was anyone capable offered" (answered: yes) to "what was the child
asked to do", and nothing in the current evidence answers it.

### The task shape, and why it is the ceiling for a content-free receipt

`task_chars` and `task_lines` now ship on every unstaffed child decision. They
separate a one-line errand, where `native_child_no_specialist_needed` is the
correct answer, from a substantial brief, where it is not.

Two richer instruments were considered and rejected on evidence, not taste:

- **The parent work unit the child descends from.** `staff_native_child` never
  receives one; its signature carries the task, correlation ids and host context
  and nothing else. That isolation is deliberate — the steward kernel states
  that any child the host spawns is staffed on its own. The `work_unit_id` on
  `delegation_events` (`unit-019efc1344`) is a **synthesised** id, not a link to
  a planner unit like `unit-python-text-normalization-strip-review`, so there is
  no parent-plan linkage to expose. Plumbing one in would change the boundary,
  not instrument it.
- **A typed characterisation of the child task.** The child path calls
  `query_judge` with `candidate_scope="complete"`, which skips retrieval
  entirely, so `affirmative_intent` never runs and no descriptors exist. Adding
  one would mean a second inference call on the child critical path, and the
  terms it produces are drawn from the task text — content, not shape.

So a structural count is the honest ceiling. **It is a weak signal and should not
be oversold**: it cannot distinguish a code review from a summary of the same
length, and nothing content-free can.

### The decline is consistent, and size does not explain it (2026-08-16)

A three-run series on `dc2513c58a8f`, every failure kept rather than retried so
the series measures a rate instead of producing a best-of. Run 3 hit the 420 s
deadline **after spawning six children**, so it contributed six independent
judge decisions rather than one.

| run | parent | header | child decisions | `task_chars` | offered |
|---|---|---|---|---|---|
| 1 | staffed `code-reviewer` | **valid** | 1 decline | 1,518 | 66 · `f34c49c2566f` |
| 2 | staffed 2 | missing 2 | 1 decline | 2,408 | 66 · `f34c49c2566f` |
| 3 | staffed 2, timed out | n/a | 6 declines + 1 provider failure | 541 – 2,013 | 66 then 67 |

**Ten child decisions across three projections; ten declines; zero staffed.**
`code-reviewer` was offered in every one. Assignments ranged from 541 characters
on one line to 2,408 characters over 17, and the answer never changed.

So both remaining explanations are excluded by evidence rather than argument:

- **Not intermittent.** Unlike parent staffing — which has now gone red, red,
  green, green, green, green — the child judge has never once staffed.
- **Not a trivial errand.** `task_chars` was built precisely to test whether
  `native_child_no_specialist_needed` might simply be correct. A 2,408-character,
  17-line brief is not an errand, and it drew the same answer as the 541-character
  one. Size does not separate the outcomes because there is only one outcome.

Three further facts this series produced, none of them sought:

1. **Rule 6 hiring is live and visible mid-run.** `request-intake-analyst` was
   minted during run 3, and the child universe grew **66 → 67 in flight**, with
   `offered_agent_digest` correctly changing from `f34c49c2566f` to
   `b5b83ecc699e`. The digest is doing exactly the job it was added for:
   distinguishing "the same universe" from "a universe that moved".
2. **A new canary limitation.** Run 3's collector returned
   `multiple_child_artifacts`. A parent that spawns six children cannot prove
   Rule 4 under the current collector, independent of any staffing question.
3. **Today's timeout fix proved itself on a real timeout.** Run 3 reported
   `status: timed_out`, `timed_out: true`, `failure_reason: claude_exec_timed_out`.
   Before this morning the same event would have published `"timed_out": false`
   beside exit code 124 and sent the next diagnosis after the wrong cause.

The provider failure in run 3 is also correct behaviour worth noting:
`native_child_inference_unavailable` carries **no** `offered_agent_digest`,
because it fails before a catalog exists. Absent, not an empty-set digest.

### The child is not evaluated the way the parent is (2026-08-16)

Owner observation, and the evidence supports it: parent and child reach their
staffing decisions through **different machinery**, and only the parent's
machinery staffs anyone.

| | parent | child |
|---|---|---|
| entry | `workforce/inference.py` | `selector/judge.py::query_judge` |
| intent | planner emits typed `WorkUnit`s | none — raw task text |
| requirements | six conjunctive axes per unit | none |
| candidates | typed shortlist annotated with `uncovered_requirements` and `execution_eligible` | complete universe, unannotated |
| decision | rank + classify required/acceptable/forbidden, then `_minimum_team_with_required` | one `selected_ids` list |
| on rejection | **funded repair loop**, retried with a repair message | none — one call, then abstain |
| critic | `workforce.recruiter.critic` route configured | none |
| observed latency | 119,128 – 124,165 ms | 5,381 – 8,071 ms |

The latency gap is the asymmetry made visible: two minutes of plan-plus-recruit-
plus-verify-plus-repair against a single five-second call.

One thing to be accurate about, having checked rather than assumed: the child's
candidate cards are **not** impoverished. `_CANDIDATE_TEXT_LIMITS` and
`_CANDIDATE_LIST_LIMITS` give each card capabilities (6 × 48), `preferred_when`
and `avoid_when` (3 × 72 each), task types, tool affinity, conflicts, requires
and evidence requirements. The child's disadvantage is not card content.

What the child lacks is everything *around* the call:

1. **No typed requirement to satisfy.** The parent's judge is asked to cover
   named axes; the child's is asked an open question about a block of text.
2. **A minimalism instruction beside a cheap escape.** The prompt says "Choose
   the smallest sufficient compatible set" and "Return an empty `selected_ids`
   list when none fits", with nothing pulling the other way. Zero is the
   smallest set, and abstaining is always defensible.
3. **No second chance.** A rejected recruiter proposal is repaired and retried;
   an abstaining child judge is final. The parent's own live runs needed two
   attempts, and the second is the one that succeeded.

That is a sufficient account of a 10-of-10 decline without needing the judge to
be wrong about any individual task. **The next change is architectural, not
another receipt field**: give the child the parent's pattern — a typed
characterisation to satisfy, and at minimum one funded repair before an
abstention becomes final. Whether the child gets a full planner or a smaller
typed intent step is the open design question.

**What would actually settle it** is already built and already owner-gated:
`observability.capture_content` requires a typed `ENABLE CONTENT CAPTURE`
confirmation in the dashboard and is currently `true` in `agency.yaml`. Wiring
the child assignment into that capture is the one change that answers "what was
the child asked" exactly. It is deliberately **not** taken here — starting to
record child task text is the owner's call, not a diagnostic convenience, and
the flag being on is not the same as the flag being pointed at this data.

## Acceptance

- [x] Every delivered specialist slug and version is an exact member of one
      validated inference decision; deterministic code never chooses a worker.
- [x] A valid compatible multi-card inference decision reaches the child intact;
      deterministic code does not truncate it to one card.
- [x] No provider or no valid inference yields no Agency-supplied specialist,
      card, activation, or hire and records one explicit failure reason; the
      native host remains free to proceed unstaffed.
- [x] Canary success requires a host-written child artifact containing the
      exact card hashes before the child's first speech; Store-only rows fail.
- [x] Spoofed, replayed, stale, encrypted-but-unbound, or Agency-authored
      evidence cannot produce a green result.
- [ ] The Codex channel binds the inference decision, parent/child correlation,
      card hashes, and install identity; focused spoof, replay, stale, and
      opaque-label adversarial tests pass.
- [ ] Claude's three prior-candidate artifacts remain valid historical
      evidence, an exact-candidate host artifact turns its installed/live
      layers green, and the current projection rejects Store-only claims.
