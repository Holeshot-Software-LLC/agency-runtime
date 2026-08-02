---
title: "AR-223: Prove Codex child task execution"
status: in_progress
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, codex, delegation, execution, evidence]
related:
  - README.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/product_host.py
  - tests/test_product_host.py
  - tests/test_codex_activation_canary.py
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
  - docs/decisions/0136-bind-opaque-codex-execution-by-ciphertext-identity.md
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-223
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/228
depends_on: [AR-221]
blocks: [AR-203, AR-204]
---

# AR-223: Prove Codex child task execution

## Problem

Exact merged build `43870c8b3052c1b274de396576a399b2cb542e61`
passes autonomous Codex activation with one inferred specialist, one real native
child, a valid first header, and zero corrections. Its one governed product
trial also accepts eight inference-authored units, applies one new live
contractor hire, launches eight distinct native children, projects every
current Codex wait, preserves every verified mutation scope, and accepts the
Store finalization.

The isolated product workspace nevertheless remains empty. The exact
`python-application-engineer` child goal contains the expected product request,
workspace-write proof path and token, `mutation_scope=workspace_write`, and a
hash matching the persisted plan. Codex records the child as completed even
though it does not create the mandatory first-write sentinel or any application
artifact. A native child completion therefore proves that a turn ended, not
that the spawn message became an actionable task.

## Current state

Trial `ar221-43870c8-readme-01` is consumed and terminal `NO-GO`. Session
`019fbe61-6267-7581-ada8-44d157c989e4`, trace
`019fbe61-62eb-7193-8ffd-e6f702c5271e`, run
`8c16f792-6941-4e54-b41b-ee4594976953`, route
`8d0ea8e3-9aef-40dd-9c1c-3a657510393c`, and finalization
`469f75a4-c422-4893-8a8d-ae0c604014ca` retain the exact Store boundary.
Correction count is zero and the first header is valid.

The inferred roster uses seven unique specialist identities across eight
units: `codebase-onboarding-engineer`, newly hired
`python-cli-architecture-specialist`, `python-application-engineer`,
`software-test-engineer`, `technical-writer`, `code-reviewer` twice, and
`test-results-analyzer`. The hiring case
`69bc7370-6763-4f41-966b-0b4af5215b54` is applied. All eight native child runs
have exit code zero, while the product report fails only
`workspace_write_not_proven` with `proof_file_missing`; independent validation
is correctly skipped because no artifacts exist.

The parent rollout contains eight spawns, eight waits, eight completed
children, zero failed children, zero timed-out waits, and zero unexpected
items. It records twenty-nine child tool calls but no content-bearing child
result. The current projector promotes every terminal child turn to a passed
worker outcome. Codex CLI 0.146.0 source defines `followup_task` as an explicit
turn-triggering message to an existing child, while the initial V2 spawn path
delivers an inter-agent communication that can be acknowledged without work.

The bounded local repair now separates those two lifecycle facts. Every
accepted Codex row stages an exact goal-hash-bound execution envelope, uses the
canonical `spawn_agent` → `wait_agent` → `followup_task` → `wait_agent`
sequence, claims the follow-up once in schema v43, and accepts a worker only
when its own bounded child rollout proves that exact envelope inside the second
terminal turn. The first readiness completion remains non-terminal for worker
evidence. Two bounded review passes have no unresolved High or Critical
finding. Three terminal focused slices pass 106, 176, and 36 tests respectively
(318 total) with warning-strict execution; the earlier combined invocation hit
its 304-second command timeout and is deliberately not counted. The named
Python production spine passes 656 tests with 6 skipped, dashboard UI passes
110 tests, documentation and Ruff gates pass, routing passes every threshold,
and decision conformance kills 84 of 84 mutations with zero survivors or
invalid results and unchanged source. Immutable-build live proof remains
pending. PR 229 merged exact
`ba76ce798b19b2e5306ef2d3ee09424c4246d07e`; the immutable upgrade planner
installed that exact VCS revision. Bare full-suite installation then refreshed
Codex and ZCode and restarted the dashboard: the dashboard is active and
reachable, ZCode is registered and enabled, and Codex is registered with the
expected `activation_required` state.

Its one autonomous activation canary is consumed and terminal `NO-GO`.
Session `019fbf1b-e062-7533-aaaa-bdde81cc2bae`, trace
`019fbf1b-f4a4-7d03-882e-25c90df4dadd`, run
`a94a6f82-561b-4784-8775-0a7e889ce2dd`, route
`94072e54-72b4-41de-b453-34b7d6141012`, and finalization
`37773104-d977-45da-af20-65db1d8c65ef` retain the exact boundary. Inference
selects `code-reviewer`, and the parent records one spawn, one completed
activation wait, and one `followup_task`. Agency's own `PreToolUse` hook rejects
that generated follow-up before the Store execution claim; therefore no second
wait or execution turn exists, the header is absent, and collaboration reports
`parent_wait_ambiguous`. Correction count is zero and persistent trust remains
unchanged. No product trial was launched.

The first failure reproduction showed that current Codex exposes the
`followup_task` message to `PreToolUse` and the parent rollout as a 760-character
`gAAAA...` ciphertext while the receiving child model acts on the decrypted
task. That repair bound the opaque parent call to the unique activated canonical
child path and one-use Store claim, but its projector fixtures incorrectly
represented the persisted child input as plaintext. Exact local head `4daf82a`
passes 143 focused hook, Store,
activation, and product tests; the named Python spine passes 656 with 6 skipped;
dashboard UI passes 110; documentation validates 625 files; Ruff, format, diff,
and every routing threshold pass. Decision conformance passes its 209.170-second
baseline and kills 84 of 84 mutations with zero invalid results and unchanged
source in 857.9 seconds. PR 230 merged that repair as exact
`a2d1a7c88f04956be0915c4b9acc4a21c5baf28c`. The immutable upgrade installed
that exact VCS commit, and `direct_url.json` independently reports the same
requested revision and commit ID. A subsequent full-suite refresh reports the
dashboard installed, active, and reachable; ZCode registered, enabled, and
complete; and the Codex bundle registered and byte-current. The install exits
partial only because Codex correctly remains `activation_required` until its
live canary runs.

That one activation is now consumed and terminal `NO-GO`. Session
`019fbf55-a690-7c20-804c-543def40a117`, trace
`019fbf55-b2dd-7602-90d7-7712854c752f`, run
`9d482344-0d67-42fc-8e49-52263b648a8b`, route
`3528a1c0-eaf9-4a4f-aed3-86a8a7eec27b`, finalization
`632849e2-5c42-4fa9-b58a-8773e75f96c4`, and child
`019fbf56-82e2-77d1-925a-43c5fcd19cbf` retain the exact boundary. Inference
selects `code-reviewer`; the parent records one spawn, two completed waits, one
accepted opaque follow-up, and one Store execution dispatch; the child completes
its second turn with the expected review response; and Store finalization is
accepted. Correction count is zero and persistent trust is unchanged.

Current Codex also persists the child's incoming execution message as a
760-character ciphertext with an empty visible payload. The model executes the
decrypted task, but the projector cannot reconstruct the exact envelope from
the persisted child rollout, so it reports `native_collaboration_topology_invalid`
and withholds the header. No product trial ran.

The focused repair now uses the host evidence that actually exists: the parent
follow-up and child second-turn `NEW_TASK` record carry one byte-equal
ciphertext. It cross-checks that transient value with the Store tool-use claim,
parent and child session lineage, canonical native task path, and exact causal
turns, then projects only the already verified activation work-unit and goal
hash. It never retains the ciphertext. The already-consumed live rollout now
projects one spawn, one follow-up, two waits, zero unexpected items, and exact
`unit-05d45f7553` execution identity. Focused warning-strict checks pass 59
direct projection tests and 220 surrounding hook, lifecycle, product, Claude,
and activation tests. Two bounded reviews have no unresolved High or Critical
finding. The final focused set passes 72 tests; both new decision mutations are
killed. The named Python spine passes 656 tests with 6 skipped, dashboard UI
passes 110, 627 Markdown files validate, repo-wide Ruff lint and format pass,
routing passes every threshold, and decision conformance kills 86 of 86
mutations with zero survivors or invalid results and unchanged source after a
163.196-second baseline and 759.4 seconds total. PR 231 merges exact
`5ff4a08e587ce47d46c96b878ed0191712906059`; the global uv tool's
`direct_url.json` independently reports that exact requested revision and
commit ID. Bare `agency install` auto-detects Codex and ZCode, refreshes both,
and installs and restarts a reachable dashboard. Codex is registered with the
exact byte-current bundle and remains `activation_required`; ZCode is
registered and enabled.

The one `5ff4a08` activation is now consumed and terminal `NO-GO`. Session
`019fbf98-e5d8-77e3-9faf-0b9d36eeffb5`, trace
`019fbf98-f1f4-77e3-82c5-8b7a065657cb`, run
`76cb3c09-e9af-4549-bdef-7ecb43a7a31f`, route
`0cec20a3-11a0-4a8d-8a5b-d7732649d3ee`, finalization
`8457f9c2-69dd-4d4b-8254-466f0b49bdda`, and child
`019fbf99-d680-7541-b951-00b6bd432b38` retain the boundary. Inference selects
`code-reviewer`; both waits, the exact opaque follow-up, the child's second
execution turn, accepted finalization, valid first response, and zero
corrections all pass. Autonomous trust bypass is proven and persistent trust is
unchanged. The exact child transcript also passes the new ciphertext projector.

The sole failure is `worker_runs.ended_at = null`. Current Codex emits
`SubagentStop` after the activation-only turn but does not emit it again after a
`followup_task` turn. Both this run and the prior `a2d1a7c` run retain that same
open-worker state; the tests incorrectly invoked a synthetic second
`SubagentStop`. No product trial ran.

The bounded lifecycle repair now reconciles at the parent `Stop`, whose common
hook payload carries the exact parent transcript path. It accepts only the
claimed worker whose bounded child rollout resolves back to that parent and
proves two turns, the exact execution delivery before one nonempty turn-bound
assistant final response, and a matching terminal completion. The activation
stop remains non-terminal, no second stop is fabricated, and the atomic Store
end transition records success only after all causal evidence passes. Focused
projection and activation checks pass 44 cases; the named fast gate and one new
immutable-build live trial remain pending.

The exact local projector also replays the consumed `5ff4a08` parent rollout
`019fbf98-e5d8-77e3-9faf-0b9d36eeffb5` and child
`019fbf99-d680-7541-b951-00b6bd432b38` as
`completion_observed=True`. That read-only reprojection proves the repair
matches the real host shape without mutating or reinterpreting the terminal
failed trial. Two bounded review passes are complete. They tightened causal
ordering so the exact execution input must occur inside the second turn and
before its final response, and they require child lineage even for any future
plaintext-capable projection.

Exact reviewed commit `62ea12a` now passes the complete named local gate. The
Python production spine reports 656 passes and 6 skips; dashboard UI reports
110 passes; documentation validates 628 files; repo-wide Ruff lint and format
pass; routing passes every threshold. Decision conformance passes its
248.747-second baseline and kills all 90 mutations with zero survivors or
invalid results, unchanged source, and 938.2 seconds total command time. Four
new mutations independently prove the parent-`Stop` call, final-response
requirement, execution-before-response order, and execution-inside-second-turn
boundary. Publication and install evidence follow below; the one fresh
activation remains.

[PR 232](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/232)
has no review threads, comments, or reviews and merges the exact locally green
tree as `b2be07758737b8e89a98aa0b0e03cecd6eb68c83`. The global uv tool's
`direct_url.json` independently reports that exact requested revision and
commit ID. Bare full-suite install refreshes Codex to bundle digest
`e314ab3c4c8488a09e127928afda957bdd534e874ebfa26a2117f7f39a1cef0c`,
registers and enables ZCode, and installs and restarts an active reachable
dashboard. Its partial result is solely Codex `activation_required`; the one
fresh autonomous activation remains unspent.

The one `b2be077` activation is now consumed and passes. Session
`019fbfd8-bb78-7683-9d6e-2a4c2d7f4b60`, trace
`019fbfd8-c7ec-77b0-aaac-9111ad12dd18`, run
`ee965317-6bf8-41a9-8ee1-0b29d2462e96`, route
`fe21a189-35fa-4599-b214-d9210f776994`, finalization
`3fc23768-c5ac-4126-bcae-61eb0a17e98d`, delegation
`8b17ef05-3cd3-4e4d-ba30-3a1cfd6706a6`, and child
`019fbfd9-8678-7ec0-a4a7-beb1265ff15b` retain the exact proof. Inference
selects and loads `code-reviewer`; one spawn, one follow-up, and two waits have
no unexpected items. The Store records the exact execution dispatch and closes
the worker with `ended_at`, exit code zero, completed delegation, and accepted
finalization. The first header is valid with zero corrections. Autonomous trust
bypass is proven, persistent profile state is unchanged, and install reports
`complete: true`.

The one `b2be077` product trial `ar223-b2be077-readme-01` is now consumed and
fails at the parent launch boundary. Session
`019fbfdf-0069-7f73-a2fc-9879f8336ab3`, trace
`019fbfdf-00fa-76c2-983b-24d40ef327a5`, run
`c77ede95-d8da-446e-8503-f4b19dc8b0d6`, route
`37d9b5bc-2610-4ebe-b5dd-616c0036bcc0`, and finalization
`3b0bed95-5875-4437-b350-41aa88436b13` retain the exact failure. Inference
accepts an eight-unit team of onboarding, Python CLI architecture,
implementation, testing, documentation, code review, test analysis, and
application-security specialists. The Codex parent then emits zero spawns,
follow-ups, waits, specialist loads, or workers; the isolated workspace stays
empty. The evaluator correctly reports `codex_parent_spawn_missing` and
`workspace_write_not_proven`, with no final header and zero corrections. The
trial is terminal and must not be rerun.

ADR-0126 placed exact product-delegation authority in Codex developer
instructions after an older host rejected hook context alone. Current Codex
delegates when the user asks or applicable `AGENTS.md` or skill instructions
request it. Hook output is extra developer context. A real broad-skill probe
adds a parent shell read and still reports `Skills loaded: none`, so that path
would be both invalid in the product harness and untraceable. The bounded repair
instead installs a marked global `AGENTS.md` or active override block that
requests exact inference-owned delegation; the product wrapper remains an
ordinary user request and projects the same canonical block.

The bounded implementation now installs one marked block in the active Codex
global guidance file, creates a missing fresh-container profile safely, exposes
the write in dry-run output, projects the exact renderer into the isolated
product profile, restores it on rollback, and removes only its own markers on
uninstall. It preserves owner content and rejects malformed, linked, non-UTF-8,
or oversized guidance. The broader focused run passes 248 tests; the final
targeted rerun passes 21; repository Ruff checks pass; documentation validation
covers 629 files; and the new decision mutation is killed 1/1. Two review passes
are closed. This focused evidence did not yet prove the named gate or a newly
installed live build.

Clean recovery head `9f391b8` closes the complete named local gate. Metadata,
policy, worklog, and 629-document validation pass; Ruff checks and formatting
cover 609 files; the Python production spine passes 657 tests with 6 skipped;
the dashboard passes 110/110; every routing threshold passes; and full decision
conformance passes with all 91 mutations killed, zero survived or invalid
results, and the source checkout unchanged. This remains local-build evidence,
not installed runtime or product proof.

PR 233 merges exact `8097e7708a52956862746ea3aa5b2fecbe7031ed`. The global
uv `direct_url.json` receipt and `agency version --json` both name that exact
revision. Bare suite installation refreshes Codex with bundle digest
`a9aa4f7e5bee9ddc575d7358e3d6e5e8f1cbb5bd71884d033d53a216d9278b83`,
registers and enables ZCode, and installs an active reachable dashboard. The
installed `C:\Users\lucas\.codex\AGENTS.md` is byte-equal to the canonical
1,123-byte renderer and contains exactly one begin and one end marker. Codex
registration succeeds and truthfully remains `activation-required`; this
installation consumes neither the activation nor product live-evidence slot.

The exact installed build consumes one autonomous-bypass activation and exits
zero. Session `019fc036-6716-76a1-a39e-8bf44a0ba502`, trace
`019fc036-733e-7653-9d49-28683b815d4e`, and native run
`codex-agent:019fc037-8811-78e0-94b9-2e167c75aa4a` prove the accepted inferred
`code-reviewer` route, one plan, one spawn, one execution follow-up, two waits,
one specialist load, a completed exit-zero worker, and an accepted
finalization. The first header is valid, correction count and unexpected-item
count are both zero, trust bypass is used, and the persistent profile is
unchanged. The fresh product slot remains unconsumed.

Product trial `ar223-8097e77-readme-01` is now consumed and fails after 104.094
seconds. Session `019fc03e-1ce0-7b01-ad08-3b80c65c2ec2`, trace
`019fc03e-1d71-7be0-aa0f-918623d2014e`, run
`c100183d-6b38-45db-adc8-fb4258c432fe`, route
`52f57ced-a4e2-4b6d-9f5a-9d3be4c9c6d6`, and finalization
`bd418651-542f-42db-a0a0-7e4c4b35ce82` prove an accepted 11-unit inferred plan
across `codebase-onboarding-engineer`, `python-cli-architecture-specialist`,
`python-application-engineer`, `software-test-engineer`, `code-reviewer`,
`test-results-analyzer`, and `technical-writer`. The parent rollout is observed
but makes zero spawns, follow-ups, or waits; no specialist loads, activation
receipts, or workers exist; the workspace remains empty; and no header is
produced. The terminal reasons are `codex_parent_spawn_missing` and
`workspace_write_not_proven`; correction count is zero. This build and trial
must not be rerun.

The missing edge is now isolated to current Codex's command-hook spill policy,
not inference or global-guidance loading. Codex defaults `additionalContext` to
an approximate 2,500-token model-visible threshold and spills larger output to
disk. The one-row activation plan fits; the product's 11-row exact plan does
not. Because the parent is collaboration-only, it cannot read the spill path
and must not reconstruct missing rows. The bounded repair sets the supported
`additionalContextLimit: 0` only on Codex `UserPromptSubmit`; Agency's existing
32,000-character context ceiling remains enforced. Bundle generation and smoke
validation bind the field. The focused installer, adapter-parity, and smoke set
passes 200 tests; targeted Ruff lint and format checks pass.

Clean recovery head `7327483` closes the complete named local gate for this
repair. Metadata, policy, worklog, and 629-document validation pass; Ruff lint
and format cover 609 files; the Python production spine passes 657 tests with 6
skipped; the dashboard passes 110/110; every routing threshold passes; decision
conformance kills every registered mutation with zero survived or invalid
results; and the source checkout remains unchanged. The next boundary is one
new immutable build, one autonomous activation, and one fresh product trial.

PR 234 merges that clean head as exact
`eb8e07770bf2b1d29933ff7730f09115928e4b1a`. The uv receipt and
`agency version --json` match the merge. Bare installation discovers only
Codex and ZCode, registers and enables both, and leaves the owned dashboard
installed, active, current, and reachable. The installed Codex manifest places
`additionalContextLimit: 0` on its sole nested `UserPromptSubmit` command
handler and on no other event. Codex remains truthfully `activation-required`;
neither the activation nor product slot has been consumed.

## Approach

1. Freeze child completion as lifecycle evidence only; never treat it alone as
   proof that the assigned work unit executed.
2. Put exact plan-execution authorization at both current Codex boundaries: the
   installed global guidance requests delegation only for an accepted inferred
   plan, while the existing marker-scoped developer protocol schedules it.
   Neither boundary may name or select a worker before inference. Bind each
   actionable delivery to the exact spawned child, native task name, work-unit
   ID, decoded goal hash, and accepted row.
3. Require a causal terminal child completion after that delivery. Reject
   missing, duplicate, reordered, cross-child, malformed, or unbounded task
   messages without retaining task or response content.
4. Preserve one-at-a-time dependency scheduling, the non-working parent,
   turn-scoped specialist authority, and the first workspace-write sentinel.
5. Run at most two reviews and the named local fast gate, then spend one fresh
   immutable-build activation and at most one product trial.

## Dependencies

AR-221 proves that current waits, exact goal delivery, verified mutation scope,
and workspace proof obligations reach every child. AR-219 owns exact multi-unit
topology evidence. ADR-0116 requires a real delegated workspace write,
ADR-0124 grades the inferred unit graph, and ADR-0128 binds opaque launches to
accepted plan authority.

## Acceptance

- [x] A terminal spawn turn is lifecycle evidence only and cannot by itself
  produce a passed worker outcome.
- [x] Every accepted plan row receives exactly one actionable native task on
  its exact spawned child, with no retry or duplicate execution path.
- [x] The actionable delivery and its later completion are proven causally and
  content-free against the exact unit ID, task name, child identity, and goal
  hash; all malformed variants fail closed.
- [ ] Read-only children and the parent cannot mutate the workspace; the first
  workspace-write child creates the exact proof before any other mutation.
- [x] Focused checks, bounded review, and the complete named local gate pass on
  clean recovery head `7327483`.
- [x] The generated Codex `UserPromptSubmit` handler keeps the complete bounded
  inferred plan inline instead of spilling it outside the parent's allowed
  tool boundary.
- [ ] One new exact build passes autonomous activation and one fresh product
  trial with real specialist-created artifacts, independent checks, a valid
  first header, and zero corrections.
