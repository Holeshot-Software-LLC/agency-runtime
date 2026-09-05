---
title: "AR-404 first evidence-led backlog dispositions"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, review, evidence, supersession]
related:
  - docs/roadmap/issue-AR-139-restore-release-asset-budget.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-backlog-inventory-20260905.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - docs/roadmap/acceptance/issue-AR-285.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: roadmap
evidence_commit: 6edfa6d8b5cb34155a249ae37896e7de2013768b
---

# AR-404 first evidence-led backlog dispositions

This is a reviewed delta, not a replacement for the canonical registry or the
frozen 155-item inventory. Starting state: 151 unfinished baseline records plus
AR-404 after the four review fixes. The owner requested cleanup of already-done,
contradictory and no-longer-wanted work. Original criteria and historical
receipts are preserved; supersession is not a successful acceptance verdict.

## First bounded batch

| Issue | Disposition | Evidence and retained responsibility |
|---|---|---|
| [AR-132](issue-AR-132-hire-deterministic-safe-gaps.md) | Retire original policy; wont_do | AR-235 replaces hard caps with autonomous/amend-first hiring; ADR-0118 requires inference-owned choices. Safe gaps and durable outcomes remain AR-235/393; AR-400 fixes progress across empty gaps. Stable execution of an accepted plan is not prohibited. |
| [AR-167](issue-AR-167-normalize-windows-release-source-modes.md) | Retire helper-specific delivery; wont_do | AR-197 removed the helper. The special source-tar executable allowance must not return. General path/handle-mode tests remain; AR-160 owns current cross-OS artifact proof. |
| [AR-169](issue-AR-169-exclude-native-pe-from-portable-wheel.md) | Retire conflicting PE split; wont_do | The original Windows-wheel criterion requires the helper. Both current profiles set includes_native_executable=false. ADR-0219 retains paired artifacts and no-PE verification. |
| [AR-267](issue-AR-267-accept-openclaw-numeric-package-revision.md) | Retire old release-line contract; wont_do | Owner-approved 2a5d52cd (AR-347 worklog) moved the minimum to 2026.8.2. tests/test_native_installer.py accepts 2026.8.2-1 and intentionally rejects 2026.7.1-2. Numeric revision parsing remains implemented. |
| [AR-285](issue-AR-285-accept-openclaw-stopped-gateway-status.md) | Retain in_progress: three satisfied, two absent criteria | Current regression and negative cases pass. The isolated verifier requires actual trusted-runner wiring citations and a successful changed-precondition dry-run receipt; historical real-install records do not supply the latter. The two unchecked criteria and full verdicts are retained. No live gateway mutation was performed. |
| [AR-160](issue-AR-160-publish-platform-honest-native-release-artifacts.md) | Reconcile, retain in_progress | Replace the removed-helper acceptance with the existing no-PE paired-artifact contract. Historical checks move intact to their own section. Windows/Linux producer evidence remains required for release; no new evidence is claimed. |

Four baseline records are retired in this checkpoint: 147 remain unfinished,
plus AR-404 and newly filed AR-405 (149 total unfinished current records).
AR-285 is not counted closed: its isolated verdicts do not permit completion.
Pre-tracker exemptions are retained; retiring an old unmapped item does not
create a new external tracker or silently claim external parity.

## Current historical-record reconciliation

The separate count audit at e4255836 found 43 actual open trackers plus 104
unfinished pre-tracker local records, not 147 demonstrated current bugs. These
rows apply the owner's instruction to judge old agent-authored requirements
against current product intent, without changing the frozen baseline inventory.

| Issue | Disposition | Current evidence and retained responsibility |
|---|---|---|
| [AR-139](issue-AR-139-restore-release-asset-budget.md) | Retired, wont_do | Its fixed 263,168-byte ceiling was superseded by AR-295's explicit required-UI audit, then 3023f0557's AR-297/298 audit. Current ten assets total 386,366 bytes, below the strict 378 KiB ceiling; the current resource test passes (1 test, 0.17s). No UI removal, floor change, or new artifact/Windows proof is claimed. |
| [AR-149](issue-AR-149-fresh-dashboard-request-ids.md) | Done; existing fix accepted | Four real HTTP regressions, 180 dashboard/disconnect tests and eight boundary/Store tests pass. All four isolated criteria are satisfied. The first absent 2/3 verdicts remain in f2e41b89; a targeted recheck followed the addition of actual ContextVar and Store source excerpts. No product criterion or implementation changed to obtain closure. |
| [AR-152](issue-AR-152-bound-dashboard-live-listeners.md) | Done; existing repair verified | Four isolated criteria satisfied at 12a62393. The unchanged 50-render soak and teardown cases pass. AR-406/ADR-0220 explicitly correct the coverage denominator to all seven product modules, retaining the 95/86/93 floors; no listener design or behavioral test was changed. |
| [AR-406](issue-AR-406-restore-dashboard-function-coverage.md) | Done; measurement contract corrected | Three isolated criteria satisfied at d109b094. The initial mixed-scope 91.12 function score counted fixture callbacks; the exact production-wide configured gate passes 138 unchanged cases at 96.92/86.62/95.71. Both local/CI exact-command regressions pass in 163 workflow tests; fresh spine 1030 pass/three skips. Initial absent baseline-comparison verdict retained, then supplied exact equal Git objects. |
| [AR-148](issue-AR-148-fail-malformed-remediation-signatures-closed.md), [AR-323](issue-AR-323-remove-stale-ledger-schema-literals.md) | Done; existing signature fix verified and stale schema tests corrected | The signature guard was already implemented. Three known ledger cases and seven migration/credential cases failed only on copied schema-46 literals. Those output assertions now use canonical SCHEMA_VERSION, retaining legacy 44/45 inputs and every behavioral guard. All 401 selected tests and fresh 1030-test spine pass; three existing spine skips. Eight isolated criteria satisfied. No production or schema change. AR-347's existing AR-323 tracker exemption supersedes its old future-tracker clause. |
| [AR-348](issue-AR-348-enforce-strict-independence-in-production.md) | Done locally; real runtime defect repaired | ADR-0221 guards actual resolved creator/reviewer chains, including legacy, harness, fallback and safety-repair paths. Both unchanged criteria satisfied at c9b678a5; 413 focused passes/one skip, 1075 spine passes/three skips, 138 UI passes, routing pass, 184/184 mutation kills and source unchanged. PR #687 and installed delivery pending; no five-host live or latency claim. |

After retiring AR-139 and completing AR-148/149/152/323/406, local unfinished
records total 142: 43 mapped plus 99 legacy. PR #684 merged at 853de310 and
external #682 closed as completed on 2026-09-05 at 21:35:56 UTC. Read-back
confirms closure; refreshed tracker enumeration confirms 43 actual open issues.
Closing an unmapped historical record cannot decrease the owner's tracker-open
count. Five completions and one retirement are published in PRs #683/#684.

AR-348's accepted repair reduces the local unfinished queue to 141 (42 mapped
plus 99 legacy). Its tracker #406 remains open until PR #687 merges; remote
enumeration therefore remains 43 at this pre-publication checkpoint.

## Earlier candidate review and subsequent disposition

This table retains the original findings; the publication column identifies
items subsequently completed. Only unfinished rows are future work.

| Issue or family | Finding | Next bounded outcome |
|---|---|---|
| [AR-271](issue-AR-271-accept-stopped-openclaw-uninstall-status.md) | The original review found a real install/uninstall classifier gap. | Subsequently done via PR #679 at 5434836e: shared classifier, three satisfied isolated criteria, 248 focused passes/two Windows skips, exact installed smoke recorded below. No longer an open candidate. |
| [AR-337](issue-AR-337-run-harness-battery-on-version-change.md) | Much is implemented, but all checkboxes are not proof. BATTERY_HOSTS excludes ZCode and tests explicitly reject it, while acceptance says each supported harness. | Resolve and record the supported-battery versus supported-host scope, then verify the service, drift and receipt contract. Do not claim five-host battery parity. |
| [AR-298](issue-AR-298-expose-complete-workforce-prompts.md) | Implemented Store/CLI/dashboard inspection and historical installed visual evidence; no isolated acceptance record. | Bind the nine criteria to exact current source/test and appropriately scoped visual evidence; close only after isolated verification. |
| [AR-336](issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md) | Historical ordinary-route evidence exists, but a later owner-approved description-evaluation addition is outside its four checked criteria. Current configuration cannot be inferred from August receipts. | Reconcile that scope with AR-253/370/374, identify a fixed qualification corpus and retained receipts. |
| [AR-348](issue-AR-348-enforce-strict-independence-in-production.md), [AR-349](issue-AR-349-persist-rejected-hiring-cases.md) | Real defects reproduced by the preceding review; not obsolete record debt. | AR-348 is now accepted; its PR #687 and installed delivery remain pending. AR-349's rejected repair-exhaustion persistence remains a separate fix. |
| [AR-350](issue-AR-350-risk-classifier-verdict-vs-hint.md) | Explicit product/authority choice, not a safe automatic closure. | Keep owner-approval gates until their authority is explicitly resolved; align the hint contract and marker count afterward. |
| [AR-351](issue-AR-351-close-sibling-axis-empty-declarations.md) | Its domain-axis rejection conflicts with AR-402/ADR-0217's descriptive-domain semantics; the stack wildcard and lifecycle questions are separate. | Reconcile only the obsolete domain clause, then reproduce stack/lifecycle boundaries before deciding their remaining hardening. |
| [AR-174](issue-AR-174-short-circuit-docs-only-ci.md), [AR-177](issue-AR-177-make-exhaustive-python-ci-manual.md) | Implemented contract tests coexist with explicit missing hosted measurement. | Distinguish deployment/measurement debt from code work; do not dispatch an exhaustive workflow or manufacture an old receipt during cleanup. |
| [AR-359](issue-AR-359-preserve-operator-policy-newlines.md) | Code is implemented; one requirement rewrites the owner's exact policy. | Obtain the exact approved text or explicitly retire that operator-specific step. Do not invent policy text. |
| [AR-393](issue-AR-393-declared-gaps-leave-no-hiring-account.md) | Four satisfied verdicts; one contradicted criterion demands causality from historical empty receipts. | Preserve the receipts and explicitly reconcile prospective accounting versus impossible retroactive reconstruction. |
| [AR-405](issue-AR-405-make-directory-identity-regressions-portable.md) (new, outside baseline) | The original wider run returned 443 passed, two skipped, two failed: real Linux directories lack the Windows attributes assumed by two tests. | Subsequently done via PR #678: portable synthetic/native observations separated, three satisfied isolated criteria and 452 wider passes/three skips. Original red evidence retained; no native Windows pass claimed. |

## Next packages

Finish AR-348's PR #687 publication and exact installed smoke, then handle
AR-349's rejected-hire persistence separately. AR-348 implements actual resolved
chains, not its old declared-profile-only suggestion; strict=false warnings and
inference-owned choices are preserved. AR-298 remains an implemented inspection
candidate awaiting isolated verification. Leave Windows work to the owner and
preserve operator authority boundaries.

### Prior delivery checkpoints

Installed-delivery checkpoint: PR #679 merged at 5434836e; that exact immutable
package is installed with the prior launcher/environment retained. All eight
deterministic smoke checks passed, including five host contracts. Native
refresh remains partial (Codex attended trust, OpenClaw live-gateway consent);
Claude/Hermes/ZCode registered and enabled. The installed-delivery evidence
records the managed dashboard restart and Claude package permission repair.
No new live-session pass, credential change or OpenClaw lifecycle action is
claimed. The 147 unfinished count is unchanged by delivery bookkeeping.

Second bounded fix: AR-271 is implemented and accepted through PR #679.
Install and uninstall share the bounded stopped-state classifier. The red
regression yielded seven failures/fifteen passes; the final focused suite has
248 passes/two native Windows skips. The named spine has 1030 passes/three
skips, UI 138, isolated acceptance three satisfied, and protected conformance
182/182 kills with source unchanged. No real gateway was stopped or uninstalled.
Current unfinished count is 147: 146 baseline records plus AR-404.

Earlier continuation after the first record batch: AR-405 is implemented and accepted
through PR #678. The build-test file returns 100 passed/one native-only skip;
the wider seven files return 452 passed/three skips. Three isolated criteria
are satisfied. Protected conformance passes baseline plus 182 mutation kills;
the initial ambient-umask private-boundary failure is retained in its evidence.
No production identity code changed. Current unfinished count is 148: the same
147 baseline records plus AR-404. AR-271 is the next runtime package; the
first-batch table above remains a historical disposition checkpoint.

Verification checkpoint: 1004 named-spine tests pass (three skips), 138 UI tests
pass, and 207 documentation/acceptance/tracker/distribution-verifier tests pass.
The 181 focused installer checks and wider two-failure result are separate.
Claude acceptance verification recorded no judgments because its executable
parent namespace failed trust. The supported Codex excerpt-only verifier then
satisfied three criteria and reported two absent; no second judgment pass was
used to seek a green result. Decision conformance passes with source unchanged.
No runtime/test source, host permissions or trust settings changed in this batch.

1. Deliver this record batch through PR #676 and its exact worklog. AR-285 stays
   open for the two precisely named evidence gaps; do not repeat successful
   checks or run a live service interruption to force closure.
2. Verify implemented inspection/observability items such as AR-298, and resolve
   small scope contradictions before creating new implementation work.
3. Deliver the genuine AR-271 and AR-348/349 safety fixes in separate bounded
   packages, with regression-first evidence and no unnecessary host mutation.
4. Keep staffing quality/latency and five-host live evidence under AR-253 and
   AR-119. They are observable product outcomes, not consequences of a shorter
   backlog. The remaining inventory has not been fully semantically audited.
