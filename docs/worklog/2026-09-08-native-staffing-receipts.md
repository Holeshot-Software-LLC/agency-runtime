---
title: "AR-414: Verify native staffing and distinguish the handoff veto"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [staffing, headers, native-evidence]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/roadmap/handoffs/issue-AR-414.md
  - docs/worklog/2026-09-08-recruiter-fallback-recovery.md
  - docs/decisions/0239-render-failed-turn-diagnostics-without-acceptance.md
supersedes: []
superseded_by: null
type: worklog
commit: 389be187013d143305810f898a7a09a477690bba
short: 389be187
date: 2026-09-08
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/785
related_issues:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
---

# AR-414: Verify native staffing and distinguish the handoff veto

## Purpose

Continue from clean synchronized main ed9d5aa9. Distinguish the exact historical
critic veto from the repaired recruiter transport failure and verify an ordinary
native response against its stored finalization. No production or owner
configuration change is justified by the retained failure codes alone.

## Historical failure

Session `01a07211-50c1-7772-9cc2-15b6e1b3fffc`, trace
`01a081fe-0037-7e20-919c-97b7a2063e1b`, received the exact request
`give me a handoff for a new session to continue`.
Receipt `ba132c4d-0c8a-432e-a5c5-b5aa7b243814` records subject classification
rejected in 2.464s, then successful planner 6.591s, embedding 2.076s,
reranker 8.524s, recruiter 3.527s and critic 3.899s. The critic's valid verdict
vetoed staffing with `wrong-neighbor-selection`. There is no HTTP404 or
recruiter-shape failure in this receipt. Subject failure is nonfatal here:
`infer_work_subject_hints` returns empty hints and planning proceeds.

The read-only failed-header renderer reproduces steward-only loading, no
delegation or skills, no observed model, and the exact subject/critic reason
codes. The run remains `preflight_failed`; no terminal acceptance was written.
Neither the original proposed team nor the critic's disputed alternative is
retained in this content-free failure receipt. Its semantic judgment cannot be
reconstructed from its reason code.

## Fresh native evidence

The live MCP process runs projection `f72f24a788ca`, matching the published
Codex pointer. The installed inspector reports all eight hooks enabled and
trusted, zero modified/untrusted/missing. Source-environment inspection first
reported `worker_projection_unavailable`; that is inspector availability, not
untrusted hooks. No host restart, reinstall or trust write was performed here.

The current continuation session also has fresh uncached accepted staffing in
149.564s, after bounded planner and recruiter repairs. Its final response is
not yet evidence at this checkpoint. The separate ordinary native demonstration
below has already reached terminal acceptance.

Native session `01a08208-d73f-7010-9ff0-f4977c68fce6`, trace
`01a08208-d781-7bc3-bcf9-ac208f407496`, reviewed the supplied average function:
`def average(values): return sum(values) // len(values)`. The request required
fractional arithmetic means, ValueError on empty input, examples `[2, 7]` and
`[]`, and prohibited repository inspection/modification. No specialist identity
or artificial staffing instruction was supplied. Ordinary `codex exec` used
persisted owner configuration and hook trust; no bypass or model override.

Uncached inference selected `code-reviewer` and `test-results-analyzer`; both
load rows and the native injected capsule agree. Staffing took 64.007s and the
whole command 79.296s. The response's five fields report steward plus those two
cards, delegation none, skills none, the observed critic wrapper alias, and
recruitment via inference. The review correctly identifies floor division and
the empty-input exception. It truthfully reports static analysis only.

The native Stop hook recorded `action=accept`, `terminal_status=completed`,
no missing fields, finalization `64955a45-d8c5-4447-a227-096b6f9bf42c`.
Exact final-output SHA-256 equals the Store response hash:
`a4d57963b8a7abae2448f00df93dce3607c4b4189c7406c2b0cca574a7df8f37`.
This is ordinary installed native evidence, not an installed-provider replay or
canary attestation. It does not establish a latency improvement.

## Handoff recurrence

One resume of that native session used the exact historical handoff wording.
Trace `01a0820a-fc29-74c0-8063-d53748450a7f` again ended `preflight_failed`:
receipt `1817b8a3-338b-4f7c-bc94-33ee0d15ef02` records successful subject,
planner, recall, recruiter and critic calls, followed by the same semantic veto.
Whole command 65.692s. The native failure response carries truthful steward-only
headers and delivers a bounded handoff without claiming staffing acceptance.
This reproduces the rejection class in different preceding context; it is not
an exact replay of the historical proposal. The native failure has no accepted
finalization event. Its body correctly preserves the earlier review-only scope.

One instrumented call to the unmodified installed `plan_and_staff_workforce`,
using the same handoff wording, recorded newly inferred planner/recruiter/critic
packets in private temporary files. It accepted in19.557s. Inference selected
`technical-writer` for handoff authoring and `reality-checker` for independent
review; the critic returned approved true with no rejection codes. The complete
eligible authoring set also included `project-delivery-response-documentation-specialist`
and `finance-snapshot-json-documentation-verifier`. No specialist was selected,
substituted or replayed by the operator. The normal call budget and strict
validator remained intact. This was a fresh standalone request without the
native session's preceding context, not a reconstruction of either failed team.

The captured successful proposal cannot adjudicate either failed proposal. It
shows that the wording is not deterministically rejected, not that the semantic
veto is fixed or erroneous. No provider, critic, validator, retry limit or owner
configuration is changed. Further useful diagnosis needs a failing proposal and
its actual critic packet captured together; another uncaptured successful
repeat would add no causal evidence.

## Verification

Focused failure/inference/subject/finalization tests: 189 passed. Named Python
production spine: 1151 passed, 3 skipped, 75.76s. UI: 224 passed. Ruff check and
format: 778 files pass. Metadata/docs: 1325 documents. Strict tracker: 406 items.
Routing gates pass. Frozen-source decision-conformance passes all188mutations,
zero survived/invalid, source_unchanged=true. Two earlier baseline attempts were
runner-environment failures: resolving a symlinked venv lost pytest, then the
copied-interpreter run rejected directories made under the inherited permissive
umask. The successful run used the existing copied interpreter with pytest and
umask077; no runtime trust check was weakened. Documentation edits are outside
this gate's declared source scope. Use the repository's CLI entrypoint with that
interpreter and `PYTHONPATH=.`; the system Python and bare Ruff executable were
not sufficient in this session.
No exhaustive corpus, coverage shards, compatibility matrix or Windows work.

## Decisions and follow-ups

Preserve strict validators, critic independence and inference-owned selection.
A valid veto is not a transport fault and a repeat cannot be declared erroneous
without inspecting its proposal. Keep AR-414 and AR-415 open; no isolated
acceptance verdicts or closure are claimed. The bounded native demonstration is
complete: current-process integration, injected cards, exact truthful header,
and terminal acceptance have evidence. Handoff-veto correctness remains unknown.
The next diagnostic package must capture a failing plan/proposal/critic packet
together under the same native context, and fix only a demonstrated defect.
The authoritative receipt must remain immutable; do not load the rejected team
or recast an approved standalone sample as a repaired native handoff.
