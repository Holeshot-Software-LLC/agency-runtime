---
title: "Production-readiness review 2026-07-26"
status: active
category: analysis
created: 2026-07-26
updated: 2026-07-26
tags: [production-readiness, security, optimization, traceability, ui, dogfood]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-128-seal-model-facing-control-authority.md
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
  - docs/roadmap/issue-AR-130-revalidate-store-trust.md
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/issue-AR-132-hire-deterministic-safe-gaps.md
  - docs/roadmap/issue-AR-133-atomic-finalization-evidence.md
  - docs/roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-136-persist-native-child-correlation.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/issue-AR-139-restore-release-asset-budget.md
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/issue-AR-141-restore-compatibility-consolidate-runtime.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-144-restore-dashboard-ui-release-coverage.md
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md
  - docs/roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
supersedes: []
superseded_by: null
---

# Production-readiness review 2026-07-26

## Executive verdict

Agency Runtime is **not production-ready yet**, but the reason is now narrow and
explicit. The initial dogfood and independent layer traces reproduced ten
P0/high-integrity defects; every one has a local fail-closed repair and focused
evidence. A final independent pass then found six UI-to-Store defects under
AR-149 through AR-154; their implementation is in the final validation cycle.
The decisive remaining product blocker is AR-143: there is no production
OS-backed, non-exporting operator-presence verifier, so positive persistent
setup and control mutations intentionally remain unavailable. Hosted, tracker,
normal-profile trust, and benchmark-valid outcome evidence are separate open
release gates.

This is not a conclusion drawn from the earlier untracked
`2026-07-25-deep-audit-findings.md` draft. That draft remains preserved as a
working artifact and is not authoritative. In particular, its proposed positive
Store-trust cache is contradicted by the new same-inode permission-transition
reproduction and must not be implemented.

## What was actually exercised

- Fetched and fast-forward checked `main`; local source matched
  `origin/main` at `5001d78` before audit checkpoint commits.
- Removed/reinstalled the managed Codex integration from the current source.
  The installer preserved nine contractors, wrote an owner backup, registered
  and enabled Codex, and started the authenticated loopback dashboard.
- Ran `agency doctor --json --verbose`: configuration, SQLite integrity,
  schema 35, the 272-agent operational roster, and the Codex subscription judge
  passed. Overall remained degraded only because normal-profile Codex hook
  trust requires the supported terminal-TUI user approval.
- Exercised the authenticated installed dashboard on desktop and 375 px mobile:
  no console errors, no page overflow, working section navigation, truthful
  Codex activation-required state, and truthful ZCode staged-not-registered
  state.
- Replayed a safe installed Routing Lab task after telemetry. It produced a
  typed three-unit plan and the canonical no-safe-team reasons, but selected no
  specialist and hired no contractor. Direct code reproduction located the
  reason allowlist defect.
- Traced UI controls through browser JavaScript, dashboard/HTTP, core services,
  MCP/CLI, host hooks, Store methods, SQL, and schema. Store analysis mapped
  118 public methods to 221 production call sites without an arity/signature
  mismatch; the confirmed failures are semantic/authority/transaction defects.
- Ran focused suites and direct adversarial probes. Notable results: UI Node
  tests 97 passed; dashboard Python tests 145 passed and 3 skipped; host
  contracts 71 passed and 1 skipped; MCP-focused collection exposed 3 failures;
  release packaging passed 14 and failed the exact asset ceiling; Store trust
  and schema-currentness probes reproduced their defects.

## Security review

The review assumed a junior implementation and treated the threat model's
compromised model, tool result, hook, MCP client, hostile repository, and
cross-account actors as real.

### Critical

No Critical finding was confirmed.

### High

| ID | Initial finding and reproduced impact | Current status | Owner |
|---|---|---|---|
| SEC-H1 | Model-facing MCP and restricted broker paths could mutate with public confirmation text; CAS proved freshness, not authority. | **Repaired:** MCP, broker, generated-host, and dashboard paths are read-only and former endpoints reject before dispatch. | [AR-128](../roadmap/issue-AR-128-seal-model-facing-control-authority.md) |
| SEC-H2 | Installer host commands inherited the complete parent environment; an unrelated sentinel credential reached a third-party CLI. | **Repaired:** delegated and installer launches use bounded allowlisted environments. | [AR-129](../roadmap/issue-AR-129-isolate-subprocess-environments.md) |
| SEC-H3 | Positive Store path trust survived a same-identity permission-authority change. | **Repaired:** authoritative boundaries revalidate trust; no positive authority cache remains. | [AR-130](../roadmap/issue-AR-130-revalidate-store-trust.md) |
| SEC-H4 | Planned native children passed through when Store/correlation evidence was unavailable. | **Repaired:** durable expiring one-use scopes fail planned work closed before side effects. | [AR-136](../roadmap/issue-AR-136-persist-native-child-correlation.md) |
| SEC-H5 | Browser automation could use the owner bearer and static modal text for persistent mutation. | **Mitigated/fail-closed:** dashboard mutation is removed and CLI mutation rejects; production remains blocked until a real OS-presence backend exists. | [AR-143](../roadmap/issue-AR-143-require-operator-presence-for-controls.md) |
| SEC-H6 | A flat Windows SDDL regex omitted an outer conditional access-granting ACE and misclassified trust. | **Repaired:** balanced quote-aware parsing consumes the complete DACL and rejects malformed/unknown shapes. | [AR-147](../roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md) |

### Medium

| ID | Initial finding | Current status | Owner |
|---|---|---|---|
| SEC-M1 | Delegated child PATH retained unsafe caller entries. | **Repaired:** PATH and environment are reconstructed from the bounded launch contract. | [AR-129](../roadmap/issue-AR-129-isolate-subprocess-environments.md) |
| SEC-M2 | Restricted brokerage did not prove desired Store path/restart state. | **Repaired:** every Store response binds active, desired, and restart truth. | [AR-128](../roadmap/issue-AR-128-seal-model-facing-control-authority.md) |
| SEC-M3 | Finalization could partially commit and coerce identity fields. | **Repaired:** one prevalidated bounded transaction commits all-or-nothing with strict identities. | [AR-133](../roadmap/issue-AR-133-atomic-finalization-evidence.md) |
| SEC-M4 | Activation-consumption currentness accepted weakened constraints. | **Repaired:** exact normalized DDL covers security-critical table constraints. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |
| SEC-M5 | Workforce/hiring currentness accepted same-name no-op triggers. | **Repaired:** exact authority objects and triggers are compared. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |
| SEC-M6 | Schema normalization case-folded quoted literals. | **Repaired:** quoted literal bytes retain semantic case. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |

### Low

| ID | Initial finding | Current status | Owner |
|---|---|---|---|
| SEC-L1 | Legacy boolean columns lacked explicit zero/one constraints. | **Repaired** by exact schema currentness. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |
| SEC-L2 | Some REST fields surfaced generic server errors. | **Repaired** with strict bounded request typing. | [AR-133](../roadmap/issue-AR-133-atomic-finalization-evidence.md) |
| SEC-L3 | MCP status exposed an unnecessary absolute database path. | **Repaired** by the bounded public projection. | [AR-131](../roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md) |
| SEC-L4 | Non-ASCII remediation HMAC text raised instead of returning invalid authority. | **Repaired:** malformed text fails closed without exception. | [AR-148](../roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md) |

The final local dependency audit completed against the declared runtime
dependency set and reported no known vulnerabilities. This is point-in-time
local evidence, not a substitute for hosted dependency review.

### Remediation checkpoint

The first bounded implementation package is locally green but does not change
the production verdict. MCP and restricted broker paths are read-only; every
MCP string is bounded; subprocess environments are least-privilege; Store trust
is revalidated; schema 36 enforces currentness/retention/boolean/ZCode
invariants; canonical staffing gaps can hire deterministically; and packaged
dashboard assets are 17 bytes below the unchanged ceiling.

Independent checkpoint verification passed 785 Python tests with 9 skips, 97
dashboard interaction tests, and full Ruff/format/diff checks. AR-128 remains
open because SEC-H5 was reproduced after its initial slice. Fresh installation,
installed dogfood, the full release gate, and every later wave remain required.

The second local remediation package now implements atomic finalization,
schema-37 durable native-child scope, exact ZCode source integration, complete
paginated dashboard contracts, coherent last-good UI refresh, safe request
correlation across dashboard/HTTP/MCP/hooks/Store, truthful hiring outcomes,
revision-aware retrieval, a lightweight CLI entrypoint, restored compatibility
wrappers, and a fail-closed CLI operator-presence gate. Independent split
verification passed 110 authority tests, 167 native-hook/ZCode tests, 147
transaction/observability/protocol tests with 8 skips, 137 dashboard server
tests with 3 skips, 82 browser interaction tests, and 101 distribution/release
tests. One attempted combined arm timed out at five minutes and is not counted;
its exact components passed when isolated.

The first complete integrated Python run after the hard checkpoint did not
pass: 7,486 passed, 61 skipped, 1 expected failure, and 34 failed in 43m39s.
The failures span stale authority expectations and genuine cross-suite
regressions in dashboard, host/control, schema/HTTP, and routing performance.
The failed expectations were reconciled to the current fail-closed authority
and schema contracts. The run also exposed and repaired three production
defects: ZCode was absent from the interactive configuration wizard, dashboard
disconnect handling assumed request headers existed and classified expected
client disconnects as server faults, and cached routing repeated a full-roster
mutation comparison already proven by eligibility filtering. The unchanged
routing gate then produced five deterministic final-source cache-hit p95
controls of `1.345`, `1.448`, `1.318`, `1.442`, and `1.745 ms`. The exact
12-module integrated reproducer now passes 424 tests in 70.71 seconds.

The second complete Python run improved to 7,521 passed, 61 skipped, 1
expected failure, and 1 failed in 43m27s. Its sole failure was a legacy test
fixture whose injected adapter namespace omitted the new canonical ZCode
field; production failed visibly instead of silently dropping the host. The
fixture now models all five hosts and both wizard modules pass 36 tests. The
third complete run from the clean repair checkpoint is green: 7,522 passed,
61 skipped, and 1 expected failure in 42m43s. This supersedes neither failed
run as history; it is the first complete integrated pass for the current
source.

The exact branch-aware release-coverage arm then exposed four additional test
contract failures and failed the fixed aggregate floor at 96.66 percent: 7,515
passed, 61 skipped, 3 performance tests deliberately deselected, and 1 expected
failure in 57m35s. AR-145 preserves that failed evidence. Coverage scheduling
made a threaded observation race and cold-bootstrap fixture deterministic, and
an accuracy test accidentally ran new wall-clock benchmarks under
instrumentation. Focused repairs now pass 33 integrated tests. Matched
authority/persistence coverage adds 177 statements and closes 38 partial
branches across finalization, maintenance, observed SQLite, and MCP; the
dashboard package adds 87 statements. The exact aggregate rerun remains
required and no threshold or exclusion changed.

The production verdict remains negative for one decisive reason: there is no
production OS-backed, non-exporting operator-presence verifier. Dashboard and
model-facing surfaces are read-only, while real persistent CLI mutations now
fail closed. Fresh reinstall from this source, installed host canaries, and
normal-profile Codex trust therefore cannot be completed autonomously without
weakening the security decision. AR-143 remains open.

## Optimization review

### Measured performance

| Path | Evidence | Interpretation |
|---|---|---|
| Cached routing microbenchmark | Initial p95 samples `2.193-3.579 ms` failed; the first remediation passed five controls at `1.531-1.795 ms`, but a mixed arm later exposed `2.103 ms`; after eliminating one redundant mutation-proof scan, five unchanged final-source controls were `1.318-1.745 ms` and the exact 12-module reproducer passed 424 tests | The fixed local 2.0 ms gate is restored with integrated headroom and no threshold change; supported-runner evidence remains outstanding |
| Full local route | about 653 ms cold, 87-121 ms warm; internal route 53-57 ms | Warm end-to-end work remains materially larger than the microbenchmark |
| Semantic retrieval, 263 agents | Initial 121-134 ms cold / 3.7-4.7 ms warm; current fixed control 316.006 ms cold / 2.031 ms warm p95 / 6.922 MiB | Revision-aware indexes pass the declared local tier budget |
| Semantic retrieval, 10,000 agents | Initial 6-7.4 s cold / 199-414 ms warm / about 208 MiB; a later unchanged arm failed at 181.144 ms and its rerun passed at 127.495 ms; immutable sparse-map scoring now measures 7,839.770 ms cold / 53.825 ms warm p95 / 167.817 MiB | The exact selection hash is unchanged; scoring probes the 49-dimension query rather than about 109 dimensions per eligible agent, restoring material scheduling headroom without changing the gate |
| CLI startup | Packaged lazy-entrypoint control is 116.244 ms p50 / 129.574 ms p95; the separate `python -m` path fell from about 647 ms to 112 ms after it was routed through that dispatcher | Both version surfaces now avoid the full compatibility/evaluation import graph |
| Stable operational snapshot | 1,104.677 ms before the deeper slice; 663.671 ms after bounded fallback lookup and generation-proven reuse; final paired warm control 539.410 ms legacy versus 408.184 ms with one contractor snapshot | The contractor batch removes eight trusted SQLite opens and reduces the final paired median by 24.328 percent; hosted/cross-platform evidence remains outstanding |
| Finalize batch | Initially up to 256 independent transactions; now one prevalidated `BEGIN IMMEDIATE` transaction | Partial-write exposure is removed in focused transaction tests |

Safe improvements are coherent request reuse, one query vector, immutable
feature indexes keyed by exact roster revision, batched Store operations, and
deferred CLI imports. Positive authorization caching is explicitly excluded.
The bounded fallback lookup still uses the trusted Store connection, complete
active-definition join, and decoder; snapshot reuse requires an equal fresh
monotonic generation and recaptures after every change.
Profiling the 10,000-agent warm path attributed 92.6 percent of its time to
cosine scoring and about 412,060 sparse probes per call. Immutable compiled
maps reduce this to the smaller-vector probe set; score comparison had maximum
delta 0.0 and the selected-result hash is unchanged.

### Maintainability and compatibility

- `route_and_build_context` and `header.finalize` now have explicit deprecated
  compatibility wrappers with a declared no-removal-before-0.3.0 contract.
- Canonical identity, bounded-value, filesystem-trust, and executable helpers
  replace the reviewed duplicate implementations, with compatibility tests for
  `slug` versus `agent_slug` precedence.
- A repository-wide static reachability audit proved seven private inference
  helpers and their closed dependency chain unreachable from production,
  exports, dynamic dispatch, and string entrypoints. Removing that island
  deletes 590 production lines while adding one replacement line; the ported public-plan suite passes 52 tests
  with one skip and one expected failure.
- Route, preflight, hook, and schema functions remain large enough to conceal
  authority and transaction boundaries.
- Decomposition is useful only after P0 behavior is locked by regression tests;
  no large mechanical rewrite should share a commit with a security fix.

[AR-140](../roadmap/issue-AR-140-scale-routing-and-retrieval.md) owns measured
performance. [AR-141](../roadmap/issue-AR-141-restore-compatibility-consolidate-runtime.md)
owns compatibility and consolidation.

## Traceability review

| Layer | Verified chain | Finding disposition |
|---|---|---|
| Browser controls -> JS | Every shipped control resolves to a handler; section links, inert text, focus, mobile, reduced-motion, and forced-colors contracts are covered. | Initial ZCode/race/stale/focus/name defects were repaired under AR-135/138. Final cross-scope commit, ambiguous-host, listener-retention, and malformed-page defects are repaired under AR-150/151/152/154 and await the final aggregate rerun. |
| JS -> dashboard HTTP | One authenticated same-origin bounded envelope, complete paging, exact totals, revisions, and read-only authority are explicit. | Initial caps/revision composition were repaired under AR-137/146. Route Lab now rejects duplicate/oversized inventories before POST under AR-151. |
| HTTP -> services | Route destinations, strict request typing, atomic finalization, and content-free boundary envelopes map correctly. | AR-149 fixes per-connection request-ID reuse and pre-dispatch error correlation; final integrated evidence is pending. |
| MCP/CLI -> services | Every registered tool has a bounded schema and handler; CLI facade/host bindings include ZCode and model-facing mutations are absent. | Initial unreachable-tool, bound, enum, spoofable-label, and output defects were repaired under AR-131/133/135. |
| Host install/hooks -> routing | All five source adapters have exact generators, events, correlation recipes, and deterministic contract tests. | Initial ZCode, process-local correlation, planned-work pass-through, and missing failure observation defects were repaired under AR-135/136/142; installed-host proof remains blocked/gated. |
| Services -> Store | Public method/call-site arity remains clean; trust, finalization, hiring, and request observations bind authoritative state. | AR-153 fixes worker-detail filtering after limit and unbounded lineage; arrays now carry exact total/truncation metadata. |
| Store -> SQL/schema | SQL remains parameterized with internal-only identifier interpolation; exact DDL covers host, trigger, index, boolean, and HMAC authority. | Initial schema/currentness defects were repaired under AR-134/148; no injection path was reproduced. |
| Return path -> UI/header | Authoritative durable evidence wins; unavailable remains explicit; collection/page and worker-detail truth are bounded. | Initial spoofing/truncation/stale defects were repaired; AR-150/153/154 close the final overwrite/count/page gaps. |

### ZCode concentration

The initial build did not support ZCode despite public CLI/README claims: its
generator was unreachable, registration omitted it, commands fell through to
Claude, fixtures missed it, schema rejected it, and parsing/identity were wrong.
AR-135 repairs the complete seven-event source chain and its integrated tests.
ZCode remains contract-tested, not installed or live-canary verified.

### Instrumentation

Core trace/session/work-unit evidence and browser/HTTP/MCP/hook/Store boundary
envelopes now carry one content-free request ID, bounded reason, outcome,
duration, and exact generation where relevant. AR-149 closes the final
HTTP/1.1 keep-alive and pre-dispatch error gap. Prompt content, tokens,
credentials, SQL values, and private paths remain excluded.

## UI verdict

The visual design remains demo-quality: consistent dark design, working
navigation, readable cards, responsive narrow layout, and a clean browser
console in the pre-remediation installed smoke. Current source now declares
collection truncation and exact totals, drains complete control collections,
uses one coherent control revision, retains last-good state with an explicit
stale marker and request ID, preserves keyboard interaction state, and includes
ZCode in runtime host presentation. The initial 82-test run exposed a genuine
release-gate hole: function coverage was 92.95 percent against the fixed 96
percent floor. AR-144 adds behavioral callback coverage; the exact command now
passes all 84 tests at 97.13 percent lines, 91.28 percent branches, and 96.32
percent functions without changing thresholds or production code. This is
source-level evidence, not a fresh installed-browser claim; post-install
desktop/mobile and accessibility QA remains an AR-138 exit gate.

The collection trace found a separate production defect: a literal
backslash-Z regex suffix rejected every opaque cursor generated by the
dashboard. AR-146 corrects the end anchor. The focused server suite passes 29
tests and 12 existing cursor/activity regressions pass, including a full
handler-to-Store keyset round-trip.

## Requested deeper-review areas

These remain residual-review notes, not invented findings:

- `process_argv.py`: shell-free canonicalization and call discipline were
  traced; no new bypass was reproduced. The documented same-account race
  remains residual risk.
- `windows_acl.py` / `windows_private_directory.py`: deeper review confirmed a
  high-severity parser omission, now owned by AR-147. A native-valid nested
  conditional grant bypassed both directory and executable trust classifiers;
  complete balanced parsing now fails the reproduction closed. Exhaustive
  hosted Windows security verification remains required.
- `schema.py`: deeper review reproduced weakened-table, same-name no-op
  trigger, and quoted-literal normalization defects under AR-134. Exact DDL
  comparison now covers those boundaries; reviewed interpolated identifiers
  remain internal constants and no injection path was found.
- Quarantined-prompt HMAC escape: no unsafe deserialization or string-built SQL
  was found and no authority bypass was reproduced. Full end-to-end adversarial
  roster lifecycle remains part of AR-125 evidence.

## Execution queue

This remains the subagent-ready task artifact. Workers take one open proof below,
read the linked issue/ADRs, preserve failed evidence, and return exact local,
installed, or hosted scope without promoting contract tests to live proof.

| State | Tasks | Remaining proof |
|---|---|---|
| Locally repaired | [AR-128](../roadmap/issue-AR-128-seal-model-facing-control-authority.md) through [AR-139](../roadmap/issue-AR-139-restore-release-asset-budget.md), excluding AR-143 | Final current-commit aggregate/artifact checks; install-dependent issues remain blocked from positive canary proof. |
| Locally measured | [AR-140](../roadmap/issue-AR-140-scale-routing-and-retrieval.md) | Local correctness/performance and the packaged-contractor batch are green; supported-runner evidence and further end-to-end profiling remain. |
| Partially complete | [AR-141](../roadmap/issue-AR-141-restore-compatibility-consolidate-runtime.md) | Compatibility and a dead island with 590 deletions/one replacement line are repaired; independently reviewed large-function/helper consolidation remains. |
| Locally repaired | [AR-142](../roadmap/issue-AR-142-instrument-runtime-boundaries.md), [AR-144](../roadmap/issue-AR-144-restore-dashboard-ui-release-coverage.md), [AR-146](../roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md), [AR-147](../roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md), [AR-148](../roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md) | Final current-commit aggregate and artifact checks. |
| Final validation | [AR-145](../roadmap/issue-AR-145-restore-python-release-coverage.md), [AR-149](../roadmap/issue-AR-149-fresh-dashboard-request-ids.md) through [AR-154](../roadmap/issue-AR-154-fail-malformed-initial-pages-closed.md) | Exact Python coverage/performance/full-suite rerun plus focused cross-layer and browser/artifact QA. |
| Product blocker | [AR-143](../roadmap/issue-AR-143-require-operator-presence-for-controls.md) | Implement and human-canary a real OS-backed, non-exporting, single-use presence verifier. |
| Outcome evidence | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) | Benchmark-valid completed corpus and current-artifact host/OS outcomes; malformed/timed-out arms stay invalid. |
| Administrative/host | AR-128 through AR-154 tracker rows, normal-profile Codex trust, hosted matrices, absent-host canaries | Explicit user/outward authorization and real installed environments. |

## Production exit gate

Production and CEO-demo readiness require all P0 issues above closed locally,
the full repository and release checklist green, a fresh install from canonical
artifacts, truthful host maturity, installed MCP protocol smoke, dashboard
desktop/mobile/browser QA, contractor hiring and native-specialist dogfood,
and AR-125 outcome evidence. Normal-profile Codex trust and live canaries must
remain user-approved host actions; tracker creation/closure, push, PR, hosted
Actions, tags, publication, and release also remain outward actions requiring
explicit authorization.
