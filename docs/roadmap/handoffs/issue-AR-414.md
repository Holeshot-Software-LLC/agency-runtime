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
branch: codex/ar414-installed-evidence-20260908
evidence_commit: 992d148d8ae60e82dc5856de1af4df2c1a4c015c
minimum_ledger_commit: 3b240fd636c9aced07079f24e012870b48eff78e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/773
---

# AR-414 staffing and failure-header checkpoint

## Checkpoint

Header repair merged PR774/905d37b8; private follow-up owns planner instructions
and evidence. Phase implementing; native package waiting_for_operator after
install changed the eight hook hashes. No worker or native child is active.

## Completed evidence

Actual installed SQLite/MCP returns a truthful failed header and leaves the run
failed. Real IDs are supplied beside initial header values. Synthetic timeout
fixture is not native activation. Header fast spine1151/3skip, UI224,
focused117/1skip and112, decision conformance188/188 pass.
Canonical992d148d artifact independently verified;614installed files match.

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
probe still uses a wrapper; stock installed follow-up remains to be recorded.

## Same-task continuity

Worktree branch contains the initial implementation and merge ledger. Read the
linked worklog for exact artifact IDs and probe scopes. Keep all unrelated
worktrees intact. Continue from a clean substantive/ledger pair at the50% gate.

## Next bounded work package

Finish, verify, merge and install the planner instruction follow-up. Record the
final bundle and one stock installed staffing call. Then await owner /hooks
approval; run normal activation plus ordinary native turn only after that.
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
