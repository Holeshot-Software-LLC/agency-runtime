---
title: "AR-404 final installed evaluation and stopping point"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-08
tags: [handoff, backlog, installation, live-evaluation]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-404-final-installed-evaluation-20260907.md
  - docs/roadmap/AR-404-next20-triage-20260907.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/worklog/2026-09-08-final-installed-evaluation.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/final-wrapup-20260907
evidence_commit: 4cbebf73df18545120348628afd6848b8e67e3ff
minimum_ledger_commit: bae369078646b2330f268ee0beddf13cca142504
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 final installed evaluation and stopping point

## Checkpoint

The owner superseded the midnight code-first extension: stop new backlog work,
merge completed slices, install all harnesses and evaluate. All three native
workers finished and stopped; no new backlog implementation is active.
Root owns final delivery records. All bounded native checks are terminal.
Stop after publishing the final evidence and exact merge ledger; no further
backlog work or live retry is active or scheduled.

Source is published on main at exact `4cbebf73` (PR762), including AR251/270/
280/284/287/312/369/371/411/412 and prior AR409/410. Five wrap-up PRs are
757,759,760,761,762. This is delivery, not whole-backlog completion.
Current inventory: 120 unfinished =48 mapped +72 legacy, not120 tracker issues.

## Completed evidence

Named production spine:1151 passed/3 skipped69.91s; dashboard224 passed.
Fallback focused161, timeout186/1skip, resident46, explicit-config48,
runtime-staleness39, card61, cache/Hermes56 pass at their recorded scopes.
One card-test-only assumption was corrected after the combined focused run;
no runtime byte changed. Routing gates pass. Decision-conformance first failed
at ambient-umask fixture setup; private-umask rerun reached its180s capture
bound with no verdict. Source unchanged; no owned evaluation child remains.

Exact-main portable wheel and sdist built, independently verified and Twine
checked. A fresh wheel install passed CLI/config/roster/MCP/dashboard smoke;
aggregate generated-hook smoke8/8 passed, including actual ZCode hook execution.
Owner CLI source is exact4cbebf73; all614 package files match the wheel.

Normal Codex/Claude/Hermes/ZCode installs succeeded. All four bind projection
`4d2934ddb59e70a94cab668077a84422a08cd1beb662adc2db578e39dd96e86b`.
OpenClaw staging published the same advisory pointer, but native install
refused because the gateway is live. The pointer is NOT registration proof.
Owner configuration and wrapper remain byte-identical; no service was restarted.

## Exact blocker

All-harness readiness is NOT proved. Codex's eight enabled hooks are untrusted;
activation returned codex_hook_trust_not_ready without invoking a model.
Claude returned all five header fields but was unstaffed, with one preflight
failure, no routing/specialist/finalization and delivery_marker_absent.
Hermes timed out at420s: cold embedding79.833s, invalid reranker response,
recruiter timeout120.180s, no header or specialist. Its own receipts prove
working provider stages; do not blame the parent's missing key for that result.

OpenClaw's existing gateway passed staffing-only: one accepted route/specialist,
five model receipts, actual five-field output and7050 model-only prompt chars.
It has no accepted finalization and its Agency run remains active; exact card
injection is not attested. Routing took288.389s in this concurrent/session-warm
check. This is not proof of candidate-native installation or a speedup.
ZCode has no native executable. OpenClaw restart consent was requested once,
with no answer; preserve the running service. No trust or credentials bypassed.

Current parent lacks LITELLM_API_KEY and runs old projection5059543ccea4.
A second normal Codex refresh returned already_current; disk reinstall cannot
retroactively staff this parent or grant normal native hook trust.

## Same-task continuity

Root delivery branch contains the exact source/ledger floor. Preserve all
unrelated worktree changes, especially the user Claude prefix worktree and
ignored main-checkout settings.local.json. Main is never committed directly.
At/below50% context, reuse this clean recovery pair and continue the same task.

## Next bounded work package

Paused until the owner explicitly requests continuation. Then prioritize one
fresh native staffed turn with exact injection and accepted finalization,
using existing AR119/409/410 and AR353 evidence. Keep Codex attended trust,
OpenClaw gateway restart consent and ZCode availability as separate prerequisites.
Do not begin a broad backlog wave, rerun stable failures or dispatch CI.

## Verification

Tests, installed-package smoke and native proof remain distinct. No exhaustive
corpus, coverage shards, compatibility matrix, hosted workflow or native Windows
run. Do not call provider-free candidate-recall performance staffing latency.
Do not mark unfinished acceptance or old native evidence as current success.

## Constraints

No trust bypass, credential-file fallback in product code, guessed header/model,
owner OpenClaw uninstall, shared gateway/dashboard restart without approval,
private transcript publication, unconditional acceptance or closure. Use existing
configured client authentication only; do not create or substitute credentials.
