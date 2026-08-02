---
title: "AR-223: Prove Codex child task execution"
status: in_progress
category: roadmap
created: 2026-08-01
updated: 2026-08-02
tags: [bug, product, codex, delegation, execution, evidence]
related:
  - README.md
  - agency_runtime/core/native_child_prompt_delivery.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/product_host.py
  - tests/test_native_child_prompt_delivery.py
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
  - docs/decisions/0139-make-codex-execution-turns-self-contained.md
  - docs/decisions/0140-use-codex-stable-multi-agent-feature.md
  - docs/decisions/0141-admit-writer-proof-only-through-agency-plans.md
  - docs/decisions/0142-require-terminal-product-child-before-next-unit.md
  - docs/decisions/0143-execute-codex-specialists-in-the-initial-spawn-turn.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/decisions/0145-place-exact-codex-execution-after-specialist-expertise.md
  - docs/decisions/0146-preserve-content-free-codex-child-tool-outcomes.md
  - docs/decisions/0147-persist-codex-child-tool-evidence-on-worker-receipts.md
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

Exact installed `eb8e077` now consumes and passes its sole autonomous-bypass
activation. Session `019fc073-ad61-7f60-b187-974936bb4c33`, trace
`019fc073-b8fd-7e70-9a55-2ae74ba8adb1`, run
`1602cd81-bc40-469a-8386-008077c2a0a1`, native run
`codex-agent:019fc074-d7b4-71e1-8425-b21a855ba8ee`, delegation
`9351fffd-5015-4b18-bc51-b2bdc0103b83`, and finalization
`1be22617-6bab-4089-83fb-bd4ea4104c55` prove one accepted inferred
`code-reviewer` plan, one spawn, one execution follow-up, two completed waits,
one consumed grant, one specialist load, and one completed worker. The first
header is valid, correction count is zero, the bypass changes no persistent
profile state, and the product slot remains unconsumed.

Product trial `ar223-eb8e077-readme-01` is consumed and fails after 698.421
seconds. Session `019fc07a-7f12-7423-8098-2f093898b361`, trace
`019fc07a-7f90-7d41-afb3-663fb9c1a903`, run
`21c91eda-a403-44a7-ac49-6e1e0d1ebdc0`, route
`67300d45-cf3c-46d6-8d4e-25afaf60d725`, and finalization
`76d583c5-fea3-4279-a1d8-63a7e5964811` prove a high-confidence, nine-unit
inferred plan across `codebase-onboarding-engineer`,
`python-cli-architecture-specialist`, `python-application-engineer`,
`software-test-engineer`, `technical-writer`, `code-reviewer`, and
`test-results-analyzer`. All nine delegations complete, all seven specialists
load, all nine workers exit zero, the parent completes, and exactly one
finalization is accepted; the first header is valid and correction count is
zero. Existing contractors fill architecture, implementation, and test roles;
no new hire is attempted.

The trial's sole proof failure is `workspace_write_not_proven`. The plan
correctly marks implementation unit `unit-e3a6637a0c`, test unit
`unit-8e8634aa31`, and documentation unit `unit-f027038a2b` as
`workspace_write`, but their worker records contain no stdout or stderr and the
exact trial workspace remains empty. The expected proof file is missing, so
artifact and check validation are correctly skipped. This consumed trial must
not be rerun. The remaining defect is now below inference, plan delivery, and
child lifecycle: Codex writer children did not realize their declared
workspace-write capability.

The first bounded diagnosis found no Agency denial of child workspace tools.
Codex child turns inherit the parent sandbox policy; the failed native control
was not self-contained because its sentinel path and content existed only in
parent instructions. The product execution follow-up had the same defect: it
carried a goal hash and told the child to recover the actual goal from its
activation turn. Hash identity proved the message but did not make the later
turn independently actionable.

The local repair makes every execution follow-up contain the exact hash-bound
goal in the current turn. Plan context still compresses repeated request text
through one shared prefix and per-row suffix, then uses the same reconstructed
goal for spawn and execution. Fifty-four focused protocol tests and 110 broader
Codex lifecycle/product-host tests pass; targeted Ruff lint and format pass.
Live writer-child proof remains pending and no new immutable build has been
spent.

Fresh native control `ar223-native-writer-self-contained-01` is consumed and
fails before child activation. The isolated Codex backend completes in 42.4
seconds with exit code 0 under `autonomous_bypass`, but its collaboration
projection records zero spawns, zero follow-ups, one wait, and zero unexpected
items. The exact workspace is empty and `.ar223-native-child-control` is
absent. The self-contained child block therefore never reached a child; this
run neither proves nor disproves child workspace-write. Do not rerun it. The
next boundary is the missing parent spawn, not another execution-envelope or
artifact repair.

Direct Codex app child control `ar223-direct-native-child-01` then succeeds in
a fresh workspace. The child creates and reads back exact 29-byte sentinel
`.ar223-direct-native-child`; its content is `AR223_DIRECT_NATIVE_CHILD_OK`
plus one LF and its SHA-256 is
`15afa0a7dfc371b1982dae6c0dcb50d5f9146c8ef296a9dd0e68bf1770a0148c`.
This proves the current host can give a native child workspace-write authority
and that the child can use it. The remaining failure is parent launch policy.

Installed Codex 0.146.0 exposes `multi_agent` as stable and enabled while the
failed harness forces disabled-by-default `multi_agent_v2`. The public manual
documents the stable feature and direct-request behavior, not V2. ADR-0140
switches activation and product backends to explicit stable `multi_agent`,
retains `agents.enabled=true`, and forbids V2 in focused tests. Thirty-eight
focused host/product/decision tests and targeted Ruff checks pass. No stable-
surface harness sentinel, build, or product trial has yet been spent.

Retained stable-feature control
`ar223-native-writer-stable-multi-agent-01` disproves that hypothesis. It
completes in 33.7 seconds under autonomous bypass but again records zero
spawns, zero follow-ups, one completed wait with zero receivers, and zero
unexpected items. Its parent falsely reports a read-only child failure even
though no child launched and the backend passed `workspace-write`; the exact
workspace remains empty.

ADR-0141 supersedes the stable-feature detour and restores the existing V2
contract before any build. The generic controls omit the accepted Agency plan
and installed global delegation request, so they cannot gate the README path.
The consumed real product trial already proves nine Agency parent spawns; the
direct app child proves exact workspace-write. The next admissible proof is one
accepted Agency writer row using the new self-contained follow-up.

Exact candidate `ae322ec` passes the named local gate: 657 Python production
tests with 6 skips, 110 dashboard tests, every routing threshold, and all 91
decision mutations with zero survivors or invalid results. Its independently
verified wheel installs the default discovered suite. Codex autonomous
activation passes with one inferred and loaded `code-reviewer`, one native
worker, one accepted finalization, zero corrections, and no persistent trust
change. ZCode is registered and enabled; the dashboard is active and reachable.

Writer sentinel `ar223-agency-writer-ae322ec-01` is retained but invalid as a
product verdict: the harness stated the correct 23-byte length but the wrong
SHA-256. The correct hash for `AR223_AGENCY_WRITER_OK` plus LF is
`767303371a040770ecccc894befc37191c57af167b1dce19ed569b5d20c3e5eb`.
No retry is allowed on that build.

The invalid run still exposes an independent terminal-order defect. Its
accepted five-row plan dispatches four specialist children, including
`minimal-change-engineer` with `mutation_scope=workspace_write`, but advances
while every prior worker has `ended_at = null`; unit five remains suggested at
the 300-second deadline and the proof file is absent. ADR-0142 now requires the
parent to distinguish commentary wakes from terminal completion, permits up to
three bounded execution waits, and forbids launching the next row before the
exact prior child is terminal.

The focused implementation and mutation slice passes 42 tests and kills both
new decision mutations with zero survivors or invalid results. The second and
final review pass covers 164 surrounding Codex activation, product-host,
child-execution, and hook tests with warning-strict execution. Targeted Ruff,
format, documentation, and diff checks pass. Clean recovery head `a5b9d4b`
then passes the complete named gate: the Python spine reports 657 passes and 6
skips, dashboard UI reports 110 passes, every routing threshold passes, and
decision conformance kills 93 of 93 mutations with zero survivors or invalid
results and unchanged source.

Exact clean recovery head `bffd2c8f172ea774353158d10ad615a89c3d0095`
then builds and installs as a wheel with SHA-256
`1bf175f209969d773c4725a34ec70c6dace932b28304113a78d31eaf2e227aae`.
Default autonomous installation discovers only Codex and ZCode, installs both
plus the dashboard, and passes Codex activation. Activation session
`019fc10f-f69d-7311-900e-12b13afd41b1` and trace
`019fc110-02e5-7c10-a464-2f1bd571a992` prove one inferred and loaded
`code-reviewer`, one completed native worker, one accepted finalization, a
valid first header, zero corrections, and trust bypass without persistent
profile change. ZCode is registered and enabled; the dashboard is active and
reachable.

Corrected writer sentinel `ar223-agency-writer-bffd2c8-01` is consumed and
terminal `NO-GO`. Session `019fc112-9e30-7a10-a0bb-dba51de4b4bb`, trace
`019fc112-9eca-7bf1-b1cd-889bf37422ad`, route
`55f9ebef-2ca4-4dba-8d30-911ee97d4742`, run
`f43fc4d9-9997-4069-9ba3-d771fb0c7afe`, and finalization
`2a336e1c-3e75-4d12-8edc-7279afdd8eac` retain the exact result. Inference
expands the explicitly indivisible request into four units and selects
`minimal-change-engineer`, `software-test-engineer`, `code-reviewer`, and
`test-results-analyzer`. The parent launches only the first specialist. Its
activation and execution waits both reach terminal completion, the worker
exits zero, and the rollout has zero corrections or unexpected items. The
parent then truthfully finalizes `delegation_declined` because the other three
accepted rows did not execute. The exact workspace remains empty and both
`writer-result.txt` and the workspace-write proof are absent.

The retained failure narrows the product defect past scheduler timing. Agency
itself tells a newly spawned Codex specialist to perform no work in its first
native turn, then relies on an encrypted `followup_task` turn for execution.
The direct current-host control already proves a self-contained first-turn
child can write exact bytes. The two-turn activation ceremony is therefore no
longer justified by the product outcome and is the next bounded boundary to
remove; the accepted specialist should execute its exact spawn goal in the
first turn and the parent should wait for that same terminal child before any
later row.

ADR-0143 now removes that ceremony for current Codex execution. The initial
spawn carries the exact persisted goal and direct specialist context; the child
executes in that one turn, and the parent performs only bounded terminal waits.
Strict rollout evidence binds the exact parent spawn ciphertext to the child's
byte-identical `NEW_TASK`, lineage, single turn, and final response. The Store
claims direct execution only after `PostToolUse` records the exact delegation,
recovering the consumed spawn receipt when Codex omits the callback tool ID.
Historical two-turn evidence remains readable but is no longer emitted.

The changed-surface warning-strict suite passes 181 tests across child
execution, prompt delivery, unit-aware delegation, product hosting, Codex
activation, native child hooks, and decision conformance. The first full
decision-conformance run passes every baseline and kills 94 of 97 mutations;
its three survivors are exactly two obsolete mutations from superseded
ADR-0137 plus one redundant parent-session check. Removing the obsolete checks
and moving the identity mutation to the shared verifier passes the focused
manifest, execution, and isolated mutation checks. The final full rerun passes
its baseline and kills all 95 current mutations with zero survivors or invalid
results and unchanged source. The named Python spine passes 657 tests with 6
skips; all 110 dashboard tests, every routing threshold, repository-wide Ruff,
formatting, documentation, metadata, policy, worklog, and diff checks pass.

Clean head `b6bcdfb5b7c121863bea8e29f3d60b139a6a24ed` builds canonically
from a detached checkout. Its independently verified Windows wheel has SHA-256
`3f9c8c0ddd7fd59daa48b0f6edb7af8824a22133988a87d486aa714f51229f28`.
The exact wheel installs, and bare autonomous installation refreshes Codex and
ZCode plus an active reachable dashboard. ZCode is registered and enabled.

The consumed Codex activation is terminal `NO-GO`. Session
`019fc17d-8a96-7171-a384-225f1debf56f`, trace
`019fc17d-96fa-7052-afa8-87b92e46e357`, route
`08860e5b-b0c7-44c5-940b-dc47e4b70959`, run
`9966776d-9d8c-4f81-a767-e1df6e409da3`, finalization
`72b11aa9-52e8-4b25-9119-04e2a95ca29e`, and worker
`019fc17e-a7b5-7f32-9c48-469054dde329` retain the exact boundary. The run
proves inferred and loaded `code-reviewer`, one direct spawn, zero follow-ups,
one completed wait, a valid first header, zero corrections, and an accepted
finalization. Verification nevertheless fails because the exact spawn's
one-use Store execution dispatch receipt is absent, leaving the delegation and
worker lifecycle open. Store timestamps and the retained rollout prove that
current Codex emitted the parent spawn result before the real child start and
activation consumption. ADR-0144 therefore claims the exact dispatch at
whichever callback is second and has both the recorded delegation and real
activated identity. The live-order regression, reverse-order compatibility,
37-test activation file, and 52 execution/lifecycle tests pass.
The complete named local gate passes: repository Ruff and formatting, 657
Python tests with 6 platform skips, 110 dashboard tests, every routing
threshold, documentation and diff checks, and a full decision-conformance
baseline that kills all 96 mutations with zero survivors or invalid results
and leaves source unchanged.

Clean checkpoint `d4c65a7b01f851cf2a4a1393ec227f7e53f0487c` builds
canonically from a detached checkout. Its verified Windows wheel has SHA-256
`581263464509639f9ca4efd7e9b8aff29e755af68e0da428c4cf9d7fd1e41075`.
The exact wheel installs and the default autonomous suite refreshes Codex and
ZCode plus an active reachable dashboard.

Its one permitted Codex activation is terminal `NO-GO` before specialist
selection. Session `019fc1a8-1217-70a0-83ca-bae1f67e008e`, trace
`019fc1a8-1c0c-7193-861b-0d72f14b7fdc`, run
`c53d8e06-abcf-45eb-8bd5-d714e70b2106`, and preflight failure
`7dfa8d89-95eb-4e9f-91c3-3d693c6b7d48` prove the planner received no valid
response from configured `codex-subscription` inference for
`gpt-5.6-luna`. The turn records no route, plan, delegation, activation,
worker, header, spawn, or correction. Trust bypass was used without a
persistent profile change. This attempt did not exercise ADR-0144 and cannot
prove or disprove the callback-order repair; exact `d4c65a7` must not be
retried and no writer sentinel ran.

A bounded 2026-08-02 09:01 UTC diagnostic does not retry that activation. It
uses the installed `d4c65a7` runtime, configured `codex-subscription` provider,
and exact production planner schema. Account-aware discovery reports
`gpt-5.6-luna` visible; the CLI returns `thread.started`, `turn.started`,
`item.completed`, and `turn.completed` with exit zero in 23.3 seconds, and the
runtime parses the required plan object. The earlier content-free failure is
therefore not reproducible and remains unclassified rather than being assigned
to recruiter acceptance without evidence. A fresh exact candidate, not a retry
of `d4c65a7`, may proceed to the activation gate.

Clean checkpoint `4d14b99ccbcfd3a78fcb3c867c16654ab85ded1f` builds
canonically from a detached checkout. Strict metadata and independent
distribution verification pass; the installed Windows wheel has SHA-256
`ad2bddce9bdd2f253ae3b2b15f44c70d4a481442af994269cf2fc0463334ff69`.
The default autonomous suite installs Codex and ZCode plus an active reachable
dashboard. Its one permitted activation passes: session
`019fc1be-ef9a-7392-8eab-ecb196c40eb5`, trace
`019fc1be-fbbf-70c3-b299-e47e16b19010`, route
`5b98f0a9-6697-40ae-be20-4f074824196b`, run
`5793dda3-452e-4ea7-af5a-0393bea227d6`, finalization
`c83b9b4b-8985-4b89-ba66-714e774aafc3`, and native worker
`codex-agent:019fc1bf-f590-70f3-a8dd-55fbfb2f8fdd` prove one inferred, loaded,
and delegated `code-reviewer`; one spawn, no follow-up, one wait; the exact
ADR-0144 execution dispatch receipt; terminal exit zero; accepted finalization;
a valid first header; and zero corrections. Autonomous trust bypass changes no
persistent profile state. This admits one Agency-owned writer sentinel against
the same installed build; it does not yet prove workspace mutation or the full
README product story.

The one admitted `4d14b99` Agency writer sentinel is now consumed and terminal
`NO-GO`. Workspace `ar223-agency-writer-4d14b99-01` remains empty and the
evaluator correctly fails `route_ambiguous`, the missing Codex collaboration
projection, and `workspace_write_not_proven`, with a valid first header and zero
corrections. The product run is `89adc572-3fcd-485b-ba32-e67c71feeb27`; its
current route `d710224d-b064-467b-bade-06a5caf01c4f`, session
`019fc1c5-9657-7df0-a3f6-26e99c60fdb4`, trace
`019fc1c5-96ce-70a2-a3cb-cfdec12416c8`, and finalization
`32fb5ef7-a624-40c7-8328-faf5b328204e` retain the exact boundary.

The failure proves two first-class defects. The product evaluator asks the
Store for a route using only host and executed-prompt hash. That hash also
matches historical route `55f9ebef-2ca4-4dba-8d30-911ee97d4742`, so the
supposedly exact lookup sees two routes and rejects the current one as
ambiguous instead of binding the Codex result's exact session. Independently,
inference ignored the explicit one-indivisible-unit constraint and authored
five units for onboarding, implementation, testing, review, and test evidence.
Only `codebase-onboarding-engineer` ran and exited zero; the remaining four
delegations stayed suggested, finalization truthfully recorded
`delegation_declined`, and no writer artifact was created. The next candidate
must repair exact session binding and inference-owned indivisible topology
before any further build or live attempt.

The bounded repair now binds the native Codex `thread.started` identity into
the product result, requires that session at the product evaluator, and filters
both ready-route and failed-preflight Store resolution by session as well as
host and prompt hash. A regression records two routes for the same prompt and
proves the historical lookup remains ambiguous while the current-session lookup
resolves exactly. Separately, the planner recognizes an explicit one
indivisible work-unit plus no-split constraint, presents inference with an
exactly-one-unit schema and explicit topology fact, and updates the inference
system contract to fold requested verification into that unit. It does not name
or select a worker. The focused planner, Store, product-host, Codex-projection,
and decision-manifest slice passes 127 warning-strict tests; Ruff passes the
changed surface. Clean repair commit
`10c047f2b18caf8b95fc74de5dd40a15a469d211` then passes the complete named
local gate. The Python production spine reports 657 passes and 6 platform
skips; dashboard UI reports 110/110; all routing thresholds pass; metadata,
policy, worklog, 635-document validation, repository-wide Ruff and formatting,
and diff checks pass. Decision conformance passes its 173.661-second baseline
and kills all 97 mutations with zero survivors or invalid results, unchanged
source, and 831.4 seconds total command time. This is local source evidence;
one immutable build, install, and live writer sentinel remain pending.

Clean checkpoint `93e465a9a42fbf8c73de44b8d56bcbd30c54e455` builds
canonically from a detached checkout. Strict Twine metadata and independent
distribution verification pass; the installed Windows wheel has SHA-256
`6426f2e1e061a5b34f80aece547a0468e75f26a1d4a3667d2529dfa87df70d50`.
The default autonomous suite installs Codex and ZCode plus an active reachable
dashboard. Its one permitted activation passes: session
`019fc1f7-00aa-72b3-9005-2cf180485a8d`, trace
`019fc1f7-0c2c-7593-a44c-eb2d2394047a`, route
`0d018c1d-86a9-49f9-a446-944da5ab1775`, run
`46ef75fb-b233-445e-9d79-0ab2abb6ae67`, finalization
`3f983200-0b34-484d-93d9-d399ac46812f`, and native worker
`codex-agent:019fc1f8-0ae2-7263-a6ea-f051c16e0e97` prove one inferred,
loaded, and delegated `code-reviewer`; one spawn, no follow-up, one wait; an
exact execution dispatch; terminal exit zero; accepted finalization; a valid
first header; and zero corrections. Autonomous trust bypass changes no
persistent profile state. This admits one fresh Agency writer sentinel only.

That one `93e465a` writer sentinel is now consumed and terminal `NO-GO`.
Session `019fc1fb-9f81-7cd2-9de2-927b68fe12f1`, trace
`019fc1fb-a004-7b42-a36e-8ba4beec5667`, run
`de09a39d-8d10-42d8-a442-77db2f244840`, and preflight failure
`e72322b5-96b7-4e26-a093-fd685856357a` retain the exact result. Both planner
attempts used `codex-subscription/gpt-5.6-luna` and were rejected as
`provider_response_contract_invalid`; no route, unit, specialist, delegation,
or worker exists. The header is absent, correction count is zero, and the exact
workspace is empty. Exact session reconciliation now works: the evaluator
resolves this run's `preflight_failed` snapshot instead of the older same-prompt
routes. The remaining defect is planner acceptance of the explicit one-unit
contract, not product evidence correlation. This build must not be retried.

A single bounded direct-planner diagnostic against that exact installed wheel
and those exact product and executed prompt hashes reproduces the rejection
without retrying the product. Luna returns one transport-schema-valid
`implementation-change` unit under `maxItems: 1`; the semantic policy rejects
it only for missing separate test implementation, independent review, and test
evidence units. The runtime had therefore made its own repair impossible: the
inference contract required one indivisible unit while the deterministic
completeness policy required at least four.

Commit `73f9989` carries the explicit indivisible fact through both semantic
policy checks, so user-owned one-unit topology suppresses only decomposition
requirements. External-write authorization remains enforced. A full-path
regression deliberately includes code-mutation tokens and proves the accepted
one-unit plan still comes from inference. The focused workforce, intent,
routing, and product-host slice passes 141 warning-strict tests; changed-file
Ruff lint and formatting pass. Clean head
`0f40e8e8b0fe5894845bf2293d791bcab55a5908` passes the complete named gate:
657 Python tests pass with 6 platform skips, dashboard UI passes 110/110, every
routing threshold passes, metadata, policy, worklog, 635-document validation,
repository-wide Ruff and formatting, and diff checks pass. Decision conformance
passes its 173.614-second baseline and kills all 97 mutations with zero invalid
results, unchanged source, and 859.9 seconds total command time. One fresh
immutable build may now proceed; no new live evidence has been consumed.

Clean candidate `d610630d4b3f8d04fc7cb2d0fc08fe6e19e44bbc` builds
canonically from a detached checkout and passes strict Twine metadata plus the
independent distribution verifier. Its Windows wheel SHA-256 is
`7f18ddaab3fc7859e45e794edc9582420847d3bfc73ddf1b32bb6a8c476d9f5d`;
the source distribution SHA-256 is
`42614e526e0190ec26d16d440a12fdcdb4835bc7580c655a924a634f315190a8`.
The global uv tool now points directly to that exact local wheel. No activation
or writer evidence has been spent for this candidate.

That candidate's single autonomous activation now passes. Session
`019fc228-8701-7c63-8e71-0b700f7893a9`, trace
`019fc228-93b9-73e2-b07e-2dde182d3e6d`, route
`0dd11929-7673-4f7b-8b5e-4e00918b72d2`, run
`f1a1f8d0-ef60-4a28-b852-215f249c5c26`, finalization
`a216da1f-9819-4772-a04e-a015d329490c`, delegation
`afbf90c8-a605-4b4d-a233-b53f239541e2`, and native worker
`codex-agent:019fc229-71ca-70d2-a184-dda5064f98ed` retain the exact proof.
Inference selects, loads, and delegates `code-reviewer`; the parent records one
spawn, no follow-up, and one wait; Store records the exact execution dispatch,
terminal exit zero, and accepted finalization. The first header validates with
no missing fields, one terminal finalization yields correction count zero, and
the rollout contains no correction hook prompt. Codex and ZCode install, the
dashboard is active and reachable, autonomous trust bypass changes no persistent
profile state, and the one writer sentinel is now admitted.

That one `d610630` writer sentinel is consumed and terminal `NO-GO` after
67.406 seconds. Session `019fc230-7a55-7263-b135-0051a291ea8b`, trace
`019fc230-7ac7-7732-a4b7-037faea8d61b`, run
`0ba1b3b8-dd4e-4687-a790-10dd5f9f87e5`, and preflight failure
`f2902d64-1730-4ee2-a300-1ea2a1102866` retain the exact boundary. The planner
applies one inference-authored unit, but both recruiter responses are rejected
because the staffing verifier reports `independent_assurance_missing`. No
route, specialist launch, header, or workspace artifact exists; correction
count is zero and the workspace is empty. The remaining contradiction is
exact: the runtime honors the explicit indivisible topology in planning, then
requires a separate downstream assurance unit during staffing. This build must
not be retried.

The bounded repair carries that same explicit topology into the recruiter
contract and staffing verifier. Only a genuinely one-unit plan skips the
otherwise mandatory downstream independent-assurance unit; composition,
eligibility, evidence, budgets, mutation scope, and every ordinary assurance
check remain enforced. A full-path regression accepts one inference-authored
implementation unit and one inference-selected filesystem specialist without a
repair call. The focused workforce, routing, hiring, staffing, and product-host
slice passes 189 tests with one platform skip; changed-file Ruff lint and
formatting pass. The one named gate remains before a new immutable build.

Clean executable and test head `62b7f3e` passes the complete named gate.
Metadata, policy, worklog, and 635-document validation pass; repository-wide
Ruff lint and formatting cover 609 files; the Python production spine reports
657 passes and 6 expected platform skips; dashboard UI reports 110/110; and
every routing threshold passes. Decision conformance passes its 182.490-second
baseline and kills all 97 mutations with zero survivors or invalid results,
unchanged source, and 891.8 seconds total command time. One new immutable build
may now proceed; no new live evidence was consumed by the gate.

Exact candidate `7f0479fd25010ca5a7a3bd00fb41d8d0e1da78d3` builds
canonically, passes strict Twine metadata and independent distribution
verification, and installs from a Windows wheel with SHA-256
`e42ff9fa2d460cde6d2163f539c5b44c531e82433f08a4fe711e02fd3f9186ef`.
Its one autonomous activation passes: session
`019fc253-aedf-7822-9744-7911d5b37901`, trace
`019fc253-bb0a-7f01-8927-ff2f945c76d2`, route
`28683bc3-bb63-40f0-ba1f-1d5c06f9777f`, run
`c73394ca-6e2a-47ef-ab68-6a243b636253`, finalization
`a6a83fe7-7a52-4cb2-91ea-776f75c19f9e`, delegation
`0bdb5869-7048-4a94-8069-2919fb3ee42a`, and native worker
`codex-agent:019fc254-88cb-77a1-b441-8dc88143879a` retain the exact proof.
Inference selects, loads, and delegates `code-reviewer`; the worker terminates
successfully, finalization is accepted, the first header is valid, correction
count is zero, and autonomous trust bypass changes no persistent profile state.
Codex and ZCode install and the dashboard is active and reachable. The one
writer sentinel is admitted and unspent.

That one `7f0479f` writer sentinel is now consumed and terminal `NO-GO` after
93.844 seconds. Session `019fc257-a0aa-7471-a8ea-0a9fae0e2dcd`, trace
`019fc257-a116-74c1-977c-3c7181a0977a`, route
`15739f24-8dec-49f4-8c9b-57601103dd56`, run
`76cf2936-69db-49d1-ae70-920c91570ec5`, finalization
`120d7ea3-2a8c-4931-87dc-4c2177076797`, delegation
`80b72766-b091-4dd4-8d4c-0ec9d42cfc67`, and native child
`019fc258-730c-7c30-bc22-d5067dce1428` retain the exact boundary. Inference
selects, loads, and delegates `minimal-change-engineer` for one
`workspace_write` unit; the parent records one spawn and one wait; the child
terminates with exit code zero; and finalization is accepted. The first header
is valid and correction count is zero. The workspace nevertheless remains
empty, so `workspace_write_not_proven` is the sole product failure. This build
must not be retried. Per the bounded delivery contract, no further repair loop
starts without a new owner go-ahead.

The bounded post-failure diagnosis separates current product projection from
the activation-canary verifier: the product projector already permits and
counts child tools, so its tool-free activation helper is not the writer cause.
The exact specialist contract instead requires tool availability to be proven
before use, while the direct child delivery did not state that the accepted
plan and current native activation were that proof or that relative paths
resolve against the exact isolated workspace. The focused repair carries those
two already-verified facts into both direct specialist context and the product
developer contract, keeps inference authoritative and the parent non-working,
and tells the child to report a prerequisite only after an actual tool denial.
The focused native-delivery, product-host, and Codex activation slice passes 84
warning-strict tests; scoped Ruff lint, formatting, and diff checks pass. No new
immutable build or live product evidence has been consumed.

Clean head `be1ca0e69652645f4bf5be7a48a81de47a869821` passes the complete
named local gate: metadata, policy, worklog, 635-document validation,
repository-wide Ruff lint and formatting, 657 Python passes with 6 platform
skips, 110 dashboard passes, every routing threshold, and a 196.478-second
decision-conformance baseline followed by 97/97 killed mutations with unchanged
source. The detached canonical build passes strict Twine metadata and independent
distribution verification. Its Windows wheel SHA-256 is
`c707342bfb4392d89ae5f07d202cd7a0e73d1a7dfc52304c5d16e2b53ad9f519`;
the source distribution SHA-256 is
`451c8a4286f1167d5f29788c3a415c47f979305b6172f038369b274e46a69dd1`.

The exact wheel installs and bare autonomous installation refreshes only Codex,
ZCode, and the reachable dashboard. Its one activation passes: session
`019fc29f-f8da-7360-8a1c-38cbe9a2f9fa`, trace
`019fc2a0-0584-7f71-a1eb-a54ed8ebf098`, delegation
`e5ab2e88-be0f-44b6-93e5-9f088825dd85`, finalization
`7a8426af-7ea4-4d4b-b290-9def315ce92c`, and native worker
`codex-agent:019fc2a0-f083-7712-a042-f70fed29bef8` prove one inferred,
loaded, and delegated `code-reviewer`, terminal exit-zero execution, accepted
finalization, a valid first header, zero corrections, autonomous trust bypass,
and no persistent profile change.

Its one writer sentinel `ar223-agency-writer-be1ca0e-01` is consumed and
terminal `NO-GO` after 78.672 seconds. Prompt hash
`sha256:1a02a85f8d35af52f983b4c3886c0aa5470b7613aa2bd2b9045261b719c66729`,
session `019fc2a3-1b73-7162-a10b-ab2b891a7876`, trace
`019fc2a3-1be8-7481-b08f-df6801a08964`, route
`5cec6a14-9cdc-4564-8e60-3a9d5d9f831a`, run
`00ffae19-8b6c-4217-846d-a7dc2fc4dfb1`, delegation
`1e26fd70-d29a-448a-baf6-3ebb28723afb`, finalization
`5699518a-3c18-42bf-8965-f1bcbedd5d97`, and native child
`codex-agent:019fc2a3-c2c3-7b32-b16e-f2dbb27d97ed` retain the exact failure.
Inference selects, loads, and delegates `minimal-change-engineer` for one
`workspace_write` unit; one spawn and one wait complete with exit code zero;
finalization is accepted; the first header is valid; and correction count is
zero. Independent inspection proves the isolated workspace has zero entries and
no `writer-result.txt`, leaving `workspace_write_not_proven` as the sole product
failure. The explicit tool/workspace-proof hypothesis is therefore falsified.
This build must not be retried, and header/dashboard/report work remains
deferred behind actual delegated workspace execution.

The retained direct control and the failed Agency trial use the same
`fork_turns=none` launch. The direct child immediately invokes `apply_patch`,
records a successful workspace-local `patch_apply_end`, verifies the bytes, and
finishes; the Agency child records zero tool calls. Current Codex 0.146.0 source
also confirms that a `SubagentStop` `decision:block` result supplies a native
continuation prompt. The first exact defect is therefore Agency's completion
boundary: it accepted lifecycle, delivery, and a nonblank final response as
`ok` without requiring any mutation receipt for a `workspace_write` row.

The bounded repair makes the exact write contract actionable and fail-closed.
The Codex v3 child context and product prompt require `apply_patch` for the
first product proof mutation and explicitly admit a proof-only named-file unit
without generic root-cause, test, or refactor expansion. `SubagentStop` now
requires one successful `patch_apply_end` whose every changed path resolves
inside the exact child workspace before recording a write child as `ok`. A
first missing receipt produces one native execution continuation; a repeated
miss terminates instead of looping. Parent-`Stop` reconciliation applies the
same receipt requirement and cannot backfill a false success. Ninety-seven
focused child-delivery, product-host, activation, and execution tests pass with
warning-strict Pytest; targeted Ruff lint/format and `git diff --check` pass.
Clean ledger head `d5a4e3190a49b94b47620a98c4c313a0f1518d04` passes the
complete named gate: metadata, policy, worklog, 635-document validation,
repository-wide Ruff lint and formatting, 657 Python passes with 6 platform
skips, 110 dashboard passes, every routing threshold, and 98/98 killed
decision mutations with unchanged source. Its detached canonical build passes
strict Twine metadata and independent distribution verification. Windows wheel
SHA-256 is
`c00a2317ea7db20512701602a7920216a824b8bdab9166eacfe8bb7e76dfa0f2`;
source SHA-256 is
`a58c47522306900189db5760a07dc199f61536336816e4529207804e01772d9f`.

The exact wheel installs and bare autonomous installation refreshes only Codex,
ZCode, and the reachable dashboard. Its one activation passes with session
`019fc2ef-4dbf-7a93-961d-8af333446b0c`, trace
`019fc2ef-5984-7103-bf17-8c51acf3927e`, and native worker
`codex-agent:019fc2f0-4b31-71f1-beb9-ce135020b0d7`; trust bypass is proven and
the persistent profile is unchanged.

Writer sentinel `ar223-agency-writer-d5a4e31-01` is consumed and terminal
`NO-GO` after 85.844 seconds. Prompt hash
`sha256:1a02a85f8d35af52f983b4c3886c0aa5470b7613aa2bd2b9045261b719c66729`,
session `019fc2f2-63f6-7a62-af0b-bdd4dbe9124e`, trace
`019fc2f2-6465-7df0-a093-621733808dab`, route
`4956e672-f132-49f2-9583-fa106d6a7890`, run
`7b18905e-0621-497e-9f8c-7ec79486420b`, delegation
`d69e1e22-bc7d-4a57-b094-dc093a2060e7`, finalization
`72a85da5-2e31-49ef-ab13-2f178bedebdb`, and native child
`codex-agent:019fc2f3-1864-7840-b5d2-84edf35dd077` retain the exact failure.
Inference selects, loads, and delegates `minimal-change-engineer` for one
`workspace_write` row; the product projection records one spawn, one wait, one
completed child, zero failed children, zero unexpected items, a valid first
header, and zero corrections. Receipt enforcement correctly leaves the Store
worker unended and the delegation incomplete after no patch receipt, but the
parent still records `accept/completed` with no missing rows. Independent
inspection finds zero workspace entries. The remaining AR-223 defect is now
only the parent-finalization boundary: it must reject an accepted
`workspace_write` row whose receipt-gated worker/delegation is incomplete.
Do not retry `d5a4e31`.

The bounded parent-finalization repair now validates the current v14 unit plan
before any terminal acceptance. Every `workspace_write` work unit must map
one-to-one to a delegation whose status is `completed` and whose
`completed_at` receipt is present. Missing, merely delegated, timestamp-free,
duplicate, malformed, or untrusted evidence returns
`delegation_execution` instead of reaching `accept/completed`; the existing
terminal policy records that outcome as `delegation_declined`. Read-only and
legacy plans are unchanged. The exact regression plus its terminal-action
control pass, and 264 adjacent completion-policy, hook, child, activation, and
product-host tests pass with one platform skip. The new decision mutation has
one exact source anchor. No new immutable build or live trial has been consumed.

Clean ledger head `c8a0577cd60124eb8e29199c214bbeec81677349`
passes the complete named local gate: metadata, policy, worklog,
635-document validation, repository-wide Ruff lint and formatting, 657 Python
passes with 6 platform skips, 110 dashboard passes, every routing correctness
threshold, and 99/99 killed decision mutations with unchanged source. The first
routing invocation had one transient 10,000-agent warm p95 of 377.314 ms; the
single bounded classification rerun passed at 84.435 ms, consistent with the
immediately preceding clean gate's 41.543 ms rather than a correctness change.
The detached canonical build passes strict Twine metadata and independent
distribution verification. Windows wheel SHA-256 is
`f09e0c179a71f69c0c0ad07e0cfeb1fa1827a5c9e015364f33bb1c95c2fdadc1`;
source SHA-256 is
`f39e04851f86ed79fdeb227c9d97f04b65760356159cbf5baaedd85315dc5458`.

The exact wheel installs and bare autonomous installation refreshes only Codex,
ZCode, and the reachable dashboard. Activation session
`019fc32f-95d8-74d3-90f8-ff8b570df2b9`, trace
`019fc32f-9efe-75a1-bd3a-7fa370adb701`, delegation
`a61cc962-ba57-4003-a834-96affb35b2d7`, finalization
`13841b28-dac1-489f-a2ec-3d6fb63a17a2`, and native worker
`codex-agent:019fc330-525f-7b20-b337-f87b7b6ef063` prove inferred and loaded
`code-reviewer`, a completed timestamped delegation, terminal exit-zero worker,
accepted finalization, autonomous trust bypass, and no persistent profile
change.

Writer sentinel `ar223-agency-writer-c8a0577-01` is consumed and terminal
`NO-GO` for the README writer outcome, but `PASS` for the scoped
parent-finalization defect. Prompt hash
`sha256:1a02a85f8d35af52f983b4c3886c0aa5470b7613aa2bd2b9045261b719c66729`,
session `019fc331-f432-71e1-b473-ce62d345171b`, trace
`019fc331-f4ad-73f3-ad67-f25092b925cd`, route
`73333330-dd5d-475d-8c61-96fdf7138565`, run
`c1c9475a-358d-4755-a665-3be459ce409a`, delegation
`c23a05b3-1eff-475c-b7f4-c1a3f9000cda`, finalization
`067e1925-23db-45d2-92a8-280115e72779`, and native child
`codex-agent:019fc332-93f4-7c31-af81-742bcce29385` retain the exact outcome.
Inference selected and loaded `minimal-change-engineer` for one
`workspace_write` row, but the worker remained unended and its delegation
remained `delegated` with no `completed_at`. The new guard therefore recorded
`delegation_declined` with missing `delegation_execution`; the run ended in the
same state. Independent inspection finds zero workspace entries and no
`writer-result.txt`. The preceding `d5a4e31` candidate had accepted this same
incomplete shape as `accept/completed`, so the controlled before/after proves
the requested bug is fixed. Do not retry `c8a0577`. Actual delegated workspace
execution remains the next separate AR-223 product gap.

The next bounded diagnosis compares that failed Agency child with the retained
direct native control. Both use current Codex encrypted task transport and an
inherited writable workspace, but only Agency injects its direct-child context.
The v3 renderer put the exact execution instruction before the immutable
`minimal-change-engineer` prompt, leaving the specialist's generic refusal of
arbitrary text and root-cause/test requirements as the newest instructions.
ADR-0145 replaces that envelope with v4: the independently hash-verified
specialist body remains unchanged, while a byte-exact, fail-closed execution
suffix follows it and requires `apply_patch` for `workspace_write`. Exact
implementation `c6c02d0` and ledger `cd142c4` pass 103 focused tests plus the
complete named gate: 636-document validation, repository-wide Ruff/format, 657
Python passes with 6 skips, 110 dashboard passes, every routing threshold, and
100/100 killed decision mutations with a green baseline and unchanged source.

Exact clean candidate `4c57507` builds and independently verifies. Wheel
SHA-256 is `01eb373868156423031e12c5bce13a54787c4bb2c7ccbca6fb0e9a0a404e4230`;
source SHA-256 is
`fab10f3a2769d921175c422757ec524cbfa4e092a7a83744659e4cb95037a4d3`.
Autonomous suite refresh installs Codex, ZCode, and the reachable dashboard;
Codex activation passes with trust bypass and no persistent profile change.
Its one writer trial `ar223-agency-writer-4c57507-01` is consumed and terminal
`NO-GO`. Inference selected and loaded `minimal-change-engineer`; the child now
records one tool call, one completed child, a valid first header, and zero
corrections, improving the preceding zero-tool behavior. It still produced no
successful patch receipt or file. Delegation remained incomplete, the worker
remained unended, and finalization truthfully recorded `delegation_declined`
with missing `delegation_execution`. Do not retry `4c57507`.

The bounded retained-evidence audit found no authoritative record of that one
tool's type or outcome. The Store preserves launch, activation consumption, and
execution dispatch but no worker end, exit code, stdout, stderr, or tool
receipt; the surviving parent rollouts do not contain the child identity, and
the isolated child profile no longer exists. Historical reconstruction is
therefore unavailable rather than inferred.

ADR-0146 implementation `3cc852f` upgrades the product collaboration projection
to v2. Each exact child and the aggregate now retain only fixed counts for call
kind, the safe `exec` / `apply_patch` / `shell_command` / `other` classes, call
status, output receipt, and patch success/failure/unknown. No argument, path,
file content, output, error, task, or response content is retained. Sixty-five
focused tests pass, and the new isolated decision mutation passes its baseline,
is killed once, and leaves source unchanged. No product trial was run in this
diagnostic slice.

The next bounded repair closes the remaining diagnostic durability gap before
another immutable trial. Schema v44 attaches the validated content-free child
tool projection to the exact Codex `worker_runs` receipt with immutable,
byte-identical replay semantics. The activation snapshot exposes each receipt
as `recorded`, `missing`, or `invalid`; product admission requires the Store
counts to equal the corresponding rollout projection. Missing or failed writes
remain fixed unit-scoped failures instead of collapsing into an opaque
reconciliation exception. One new decision mutation removes the Store write.
The focused lifecycle, product-host, schema, activation, and conformance suite
passes 128 tests with warning-strict execution; repository-wide Ruff lint,
format, and diff checks pass. No candidate was built and no live evidence was
consumed in this implementation slice.

## Approach

1. Freeze child completion as lifecycle evidence only; never treat it alone as
   proof that the assigned work unit executed.
2. Put exact plan-execution authorization at both current Codex boundaries: the
   installed global guidance requests delegation only for an accepted inferred
   plan, while the existing marker-scoped developer protocol schedules it.
   Neither boundary may name or select a worker before inference. Bind the
   initial spawn to the exact child, native task name, work-unit ID, decoded
   goal hash, exact self-contained goal, and accepted row; do not send an
   execution follow-up.
3. Require a causal terminal child completion after that initial delivery. Reject
   missing, duplicate, reordered, cross-child, malformed, or unbounded task
   messages without retaining task or response content.
4. Preserve one-at-a-time dependency scheduling, the non-working parent,
   turn-scoped specialist authority, and the first workspace-write sentinel.
5. Prove one installed, accepted-plan Agency writer sentinel before any full
   product trial. Require the exact lifecycle, file bytes, first header, and
   zero corrections in the same run.

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
- [x] The actionable delivery contains the exact hash-bound goal in its own
  turn and its later completion is proven causally against the exact unit ID,
  task name, child identity, and goal hash; all malformed variants fail closed.
- [ ] One isolated self-contained writer child creates and reads back its exact
  sentinel before a new immutable build is produced.
- [x] One direct current-host native child creates and reads back exact bytes,
  independently proving inherited workspace-write capability.
- [ ] One accepted Agency plan row launches its selected writer, delivers the
  self-contained execution turn, and creates exact retained file proof.
- [x] A Codex `workspace_write` row cannot record success without a successful
  workspace-local patch receipt; one bounded native correction is permitted
  and a repeated missing receipt terminates without a loop.
- [x] Parent finalization rejects a current `workspace_write` row whose exact
  delegation lacks terminal completed evidence instead of recording
  `accept/completed`.
- [x] Product scheduling cannot advance from a nonterminal commentary wake;
  bounded repeated waits remain causally and content-freely verifiable.
- [x] Current Codex execution uses one initial specialist turn and no execution
  follow-up; exact spawn/child ciphertext, lineage, completion, and final-answer
  variants fail closed in focused tests.
- [ ] Read-only children and the parent cannot mutate the workspace; the first
  workspace-write child creates the exact proof before any other mutation.
- [x] Focused checks, bounded review, and the complete named local gate pass for
  the first-turn and callback-order implementation.
- [x] The generated Codex `UserPromptSubmit` handler keeps the complete bounded
  inferred plan inline instead of spilling it outside the parent's allowed
  tool boundary.
- [ ] One new exact build passes autonomous activation and one fresh product
  trial with real specialist-created artifacts, independent checks, a valid
  first header, and zero corrections.
