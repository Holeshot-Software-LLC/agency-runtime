---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-05
tags: [handoff, workforce, recall, staffing, hiring, install]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/roadmap/issue-AR-397-packaged-contracts-cannot-be-revised-in-place.md
  - docs/roadmap/issue-AR-398-a-gap-turn-that-outruns-its-lease-leaves-no-receipt.md
  - docs/roadmap/issue-AR-399-a-plan-object-followed-by-a-stray-brace-reads-as-prose.md
  - docs/roadmap/handoffs/issue-AR-400.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/decisions/0217-keep-subject-domains-out-of-execution-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: codex/ar400-delivery
evidence_commit: 1de05aead322dbbf359a0a5f3ab19dcbb7cdeff9
minimum_ledger_commit: df1ace064a67eff357d7f364fdb4cfc805207154
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

## Checkpoint

The formerly unpushed capsule commits 45b51a20/cbbd2cff are preserved and merged
through PR #669. Main is now 1de05aea. The current implementation and delivery
package is AR-400 through AR-403, with its active capsule linked above.
This refresh replaces the spent branch-only note and old installed-state claim;
historical implementation/evidence remains in the canonical issues and Git.

## Completed evidence

- Earlier PRs #657 through #664 delivered packaged-contract reconciliation,
  token-guarded lease closure/schema 49 and trailing-bracket parsing.
- The 15:00Z 1c1efa07 Codex proof and ordinary turn remain historical evidence,
  not proof of the newer runtime. That older ordinary turn took 96 s to route.
- Independent review at e6531004 reproduced compositional failures despite
  locally passing units: completed hires lost across empty gaps, provider
  deadlines restarted per stage, and subject domains mistaken for authority.
- PR #669 fixes those boundaries and adds private cross-process roster-vector
  reuse. Recruiter, strict critic, authority and hiring audits remain enabled.
- Named fast spine: 1004 passed, three skipped. JS: 138 passed. Routing passed.
  Conformance baseline passed and all 182 mutations were killed; final small
  launch-boundary changes separately passed 135 focused tests.
- Current live recall pair: 63.620 s cold / 283 embedding inputs; 8.804 s warm /
  one input. Fifteen of sixteen additions overlap; reranked lists differ.
  This is not total staffing latency or a live quality-equivalence proof.
- Installed non-editable VCS build 0.1.0+g1de05aead322, projection 349f1ae7fc74,
  from main 1de05aea. Dashboard restarted and reachable. PATH shim now uses
  that build; its old launcher is backed up beside the new venv.
- All-host deterministic smoke: eight passed, zero failed/skipped; five host
  parity cases passed.
- Claude isolated native-child canary passed at 16:51Z on projection 349f1ae7:
  code-reviewer delivered, header valid, no trust bypass, no persisted
  current-profile attestation. See AR-400-installed-delivery-20260905.md.

## Exact blocker

- Codex files are registered/enabled, but current-profile activation stopped
  before a model call: all eight changed hooks require attended trust in a
  fresh terminal TUI. The current long-lived process may retain its old kernel.
- OpenClaw's live gateway blocked native update; brief stop/restart consent was
  requested and is not assumed. Its current integration is not claimed updated.
- Hermes installed/enabled; ZCode's seven handlers installed/enabled. Neither
  exposes a proven bounded native-child noninteractive canary here; ZCode has
  no discovered CLI/version. Fresh ordinary sessions remain operator work.
- AR-393 criterion 5 still asks historical pre-fix receipts to name a condition.
  No receipt will be rewritten or acceptance wording weakened without a scoped
  owner decision. The four other criteria already have isolated verdicts.
- Missing AR-398/399 trackers and stale-open AR-397 are record debt identified
  before the owner's subsequent backlog-cleanup request, not runtime failures.

## Same-task continuity

Continue self-implementation in the AR-400 delivery worktree. Main is clean;
all subsequent code changes require their own branch, PR and verification.
Use the non-editable pinned binary outside source for installed probes. Local
development uses a separate editable venv and must never become a host launcher.
Live calls use existing configured credentials without printing or copying them
into repository evidence. Read operational store evidence from a read-only copy.

## Next bounded work package

1. Finish AR-400 through AR-403 isolated acceptance and merge delivery evidence.
2. Record an ordered backlog completion plan and reconcile evidenced tracker
   bookkeeping under the owner's cleanup request; keep unfinished items open.
3. Once available, verify attended Codex trust and consented OpenClaw install.
   Run fresh ordinary Hermes/ZCode sessions through their supported host UI.
4. AR-393 and AR-370 own remaining broader gap-account and cross-host proof;
   the successful isolated Claude canary does not close either umbrella.

## Verification

Current installed proof is repository-local:
docs/roadmap/acceptance/evidence/AR-400-installed-delivery-20260905.md.
Current recall reports:
docs/roadmap/acceptance/evidence/AR-403-recall-performance-20260905.json.
The old launch evidence at 15:00Z and old stuck-run counts are historical, not
re-measured current health. No exhaustive corpus, coverage shards, compatibility
matrix or remote exhaustive workflow was run for this delivery.

## Constraints

No direct main commits, native trust bypass, manual hook hashes, credential
creation, provider reconfiguration or silent historical-receipt rewriting.
Bounded packages, exact worklog ledgers and honest live/contract separation.
Acceptance verifier supplies judgments; the builder supplies evidence.
