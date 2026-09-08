---
title: "AR-414 staffing and failure-header checkpoint"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [handoff, staffing, headers]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/worklog/2026-09-08-failed-headers-and-planner.md
  - docs/decisions/0239-render-failed-turn-diagnostics-without-acceptance.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-414
branch: codex/ar414-final-checkpoint-20260908
evidence_commit: 6786aaa242c69810b25baaa12b4090e24c0cd2a5
minimum_ledger_commit: 51851f640fd4f23c9695a7e23c39cc6d9da93a25
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/773
---

# AR-414 staffing and failure-header checkpoint

## Checkpoint

Header repair merged PR774/905d37b8; planner instructions merged PR775/975ce7b4.
Both are installed. Phase waiting_for_operator after install changed the eight
hook hashes. No worker or native child is active.

## Completed evidence

Actual installed SQLite/MCP returns a truthful failed header and leaves the run
failed. Real IDs are supplied beside initial header values. Synthetic timeout
fixture is not native activation. Header fast spine1151/3skip, UI224,
focused117/1skip and112, decision conformance188/188 pass.
Final canonical6786aaa2 artifact independently verified;614installed files match.
Wheel843b117756bb6991b24f2c9a2551468c2c44785ebea52a2b4aa09d1f9cdca190;
bundle dc60673491f287f7eae05e2602fae25c02bbbaee4a24b9b1df5d14d9e1527fac;
plugin0.1.0+codex.6c3ad021798c. Final planner/header focused176pass;
final production spine1151pass,3skip. Actual final installed MCP diagnostic passes.

Gateway correction retained on the existing Agency planner GLM deployment:
order0 instead of2; extra_body.reasoning_effort low instead of empty. No other
parameter, secret or service changed. The OpenAI-compatible adapter drops the
top-level reasoning parameter; current GLM accepts low/high/max, not medium.
Candidate explicit empty-string novelty instructions yield accepted staffing
25.078seconds, with all planner/recruiter/critic checks intact. Warm sample only.

## Exact blocker

Fresh inspection after install:8modified hooks,0trusted. Previous old bundle
was genuinely trusted. New ordinary run has0Agency rows and0header fields.
No more native retries before fresh approval; no bypass. Candidate instruction
probe accepted25.078seconds with a wrapper. A final stock installed call on a
fresh fractional-mean input took48.626seconds: subject3818ms, planner10925ms,
embedding2859ms and reranker6213ms applied; recruiter13178/11456ms replies both
failed validation, second recruiter_response_shape_invalid. No accepted stock
staffing or native execution is claimed. Planner latency is not whole-turn latency.

## Same-task continuity

Worktree branch contains the initial implementation and merge ledger. Read the
linked worklog for exact artifact IDs and probe scopes. Keep all unrelated
worktrees intact. Continue from a clean substantive/ledger pair at the50% gate.

## Next bounded work package

Await owner /hooks approval in a fresh Codex process for the exact final bundle.
Then run normal activation plus an ordinary native turn with no overrides.
The remaining staffing repair is the recorded recruiter response-shape boundary;
inspect it before another paid full-path run, without weaker validation or a
hand-picked specialist. Trust approval alone does not fix that recruiter failure.
Never mark AR414 or AR404 done on the synthetic or wrapped probe alone.

## Verification

Focused planner/header tests and named fast spine; docs metadata, worklog,
policy, strict tracker, Ruff and diff gates. Canonical artifact verification,
installed byte identity, actual MCP and one real provider staffing call.
Precede live calls with context telemetry. No exhaustive suite or Windows run.

## Constraints

No manual specialist choice, relaxed validator, false acceptance, credential
replacement, trust bypass, OpenClaw restart, or unrelated backlog wave. Preserve
failed-run immutability and exact correlation. Reversal of the gateway change
is order2 and empty extra_body on the same deployment only.
