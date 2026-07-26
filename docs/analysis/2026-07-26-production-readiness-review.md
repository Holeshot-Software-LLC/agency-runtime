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

Agency Runtime is **not production-ready yet**. The architecture contains many
strong controls and the installed dashboard is visually polished, but fresh
dogfooding and independent layer traces reproduced ten P0/high-integrity
defects. The most consequential are model-accessible persistent mutation,
ambient credential inheritance, stale Store trust, broken MCP tools, a
contractor path that cannot hire its canonical gap, incomplete ZCode support,
process-local native-child correlation, and planned delegation that fails open
before side effects.

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

| ID | Finding | Reproduced impact | Owner |
|---|---|---|---|
| SEC-H1 | Model-facing MCP and restricted broker paths can perform persistent host/agent/runtime mutations using public static confirmation text. | A caller holding the model-facing capability can read generation and construct the published phrase; CAS prevents staleness, not confused-deputy authority. | [AR-128](../roadmap/issue-AR-128-seal-model-facing-control-authority.md) |
| SEC-H2 | Installer host commands inherit the complete parent environment. | A sentinel unrelated credential reached the third-party CLI environment. | [AR-129](../roadmap/issue-AR-129-isolate-subprocess-environments.md) |
| SEC-H3 | Positive Store path trust survives a permission-authority change. | Same inode/mtime returned trusted before and after authority loss; the authoritative checker ran only once. | [AR-130](../roadmap/issue-AR-130-revalidate-store-trust.md) |
| SEC-H4 | Agency-planned native children fail open when Store/correlation evidence is unavailable. | Valid planned-shaped labels for Claude, Codex, and ZCode returned pass-through, permitting side effects before terminal evidence rejection. | [AR-136](../roadmap/issue-AR-136-persist-native-child-correlation.md) |
| SEC-H5 | The model-callable in-app Browser can use the owner dashboard bearer and automate every persistent mutation modal. | Static phrases and CAS prove shape/freshness, not human presence; global, host, agent, config, roster, workforce, hiring, and trimming operations remain reachable. | [AR-143](../roadmap/issue-AR-143-require-operator-presence-for-controls.md) |
| SEC-H6 | A flat Windows SDDL regex can omit an outer conditional access-granting ACE. | Windows accepted and round-tripped a foreign full-control callback ACE containing nested text; directory and executable classifiers returned trusted before the complete-parser repair. | [AR-147](../roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md) |

### Medium

| ID | Finding | Owner |
|---|---|---|
| SEC-M1 | Delegated child PATH can retain dot, relative, repository, or unsafe caller entries even though the launcher itself is frozen. | [AR-129](../roadmap/issue-AR-129-isolate-subprocess-environments.md) |
| SEC-M2 | Restricted agent brokerage does not independently prove desired Store path or restart-required state. | [AR-128](../roadmap/issue-AR-128-seal-model-facing-control-authority.md) |
| SEC-M3 | One finalization request can partially commit evidence before a later conflict and accepts some coercible identity fields. | [AR-133](../roadmap/issue-AR-133-atomic-finalization-evidence.md) |
| SEC-M4 | Activation-consumption currentness accepted a table missing primary, unique, foreign-key, non-null, and value constraints. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |
| SEC-M5 | Workforce append-only and hiring-authority currentness accepted same-name no-op triggers. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |
| SEC-M6 | Schema normalization case-folded quoted literals and could hide semantic trigger drift. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |

### Low

| ID | Finding | Owner |
|---|---|---|
| SEC-L1 | Legacy boolean columns lack explicit zero/one constraints. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |
| SEC-L2 | Some REST fields fail as generic server errors instead of bounded typed client errors. | [AR-133](../roadmap/issue-AR-133-atomic-finalization-evidence.md) |
| SEC-L3 | MCP status exposes an unnecessary absolute database path. | [AR-131](../roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md) |
| SEC-L4 | A 64-character non-ASCII remediation HMAC raises instead of returning invalid authority. | [AR-148](../roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md) |

The dependency vulnerability scan could not be completed within the restricted
network/policy boundary. No claim of dependency-CVE cleanliness is made.

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
| Semantic retrieval, 10,000 agents | Initial 6-7.4 s cold / 199-414 ms warm / about 208 MiB; current 8,817.588 ms / 84.193 ms / 189.589 MiB | Warm scale and bounded memory improved; the fixed local tier gate passes |
| CLI startup | Packaged lazy-entrypoint control is 116.244 ms p50 / 129.574 ms p95; the separate `python -m` path fell from about 647 ms to 112 ms after it was routed through that dispatcher | Both version surfaces now avoid the full compatibility/evaluation import graph |
| Stable operational snapshot | 1,104.677 ms before the deeper slice; 663.671 ms after bounded fallback lookup and generation-proven reuse | About 40 percent faster, but 400-450 ms packaged-contractor reconciliation remains dominant |
| Finalize batch | Initially up to 256 independent transactions; now one prevalidated `BEGIN IMMEDIATE` transaction | Partial-write exposure is removed in focused transaction tests |

Safe improvements are coherent request reuse, one query vector, immutable
feature indexes keyed by exact roster revision, batched Store operations, and
deferred CLI imports. Positive authorization caching is explicitly excluded.
The bounded fallback lookup still uses the trusted Store connection, complete
active-definition join, and decoder; snapshot reuse requires an equal fresh
monotonic generation and recaptures after every change.

### Maintainability and compatibility

- `route_and_build_context` and `header.finalize` now have explicit deprecated
  compatibility wrappers with a declared no-removal-before-0.3.0 contract.
- Canonical identity, bounded-value, filesystem-trust, and executable helpers
  replace the reviewed duplicate implementations, with compatibility tests for
  `slug` versus `agent_slug` precedence.
- Several private wrappers are test-only/dead, while route, preflight, hook,
  and schema functions are large enough to conceal authority and transaction
  boundaries.
- Decomposition is useful only after P0 behavior is locked by regression tests;
  no large mechanical rewrite should share a commit with a security fix.

[AR-140](../roadmap/issue-AR-140-scale-routing-and-retrieval.md) owns measured
performance. [AR-141](../roadmap/issue-AR-141-restore-compatibility-consolidate-runtime.md)
owns compatibility and consolidation.

## Traceability review

| Layer | Verified chain | Confirmed defects |
|---|---|---|
| Browser controls -> JS | 134 controls resolved to handlers; section links work; no DOM-XSS primitive found; mobile layout has no overflow | ZCode missing from hard-coded Route Lab hosts; older reads can win; stale refreshes are silent; polling loses focus/open state; one accessible-name gap |
| JS -> dashboard HTTP | Shared authenticated JSON envelope, same-origin and response bounds are present | Workforce asks for 1,000 but server silently caps 200; filtered totals can be false; parallel responses can compose revisions |
| HTTP -> services | Route table and core destinations map correctly; mutation CAS and locked Store rechecks are strong | REST typing is inconsistent; no uniform safe request ID/latency/outcome; finalization batch is not atomic |
| MCP/CLI -> services | All twelve tool names have handlers; CLI parser/facade binding tests pass | Three valid tools are unreachable due missing `maxLength`; delegate bounds drift; host enum omits ZCode; finalize accepts spoofable host/requested-model labels; output contracts are untyped |
| Host install/hooks -> routing | Codex/Claude/other contract paths exist and focused tests pass | ZCode installs Claude files and cannot register; ZCode activation/lineage is broken; parent correlation is process-local; planned work fails open; failure hooks/observations are incomplete |
| Services -> Store | 118 public Store methods and 221 production calls showed no signature/arity mismatch | Trust cache stale; finalization partial commits; hiring outcome not projected |
| Store -> SQL/schema | Parameterized SQL and internal-only identifier interpolation were confirmed; integrity passed | ZCode excluded by host CHECK; currentness ignores a critical trigger/index; guarded-delete declaration is false; boolean checks incomplete |
| Return path -> UI/header | Durable model receipt wins and missing receipt renders unavailable rather than fabricated | Caller may spoof non-authoritative requested host/model label; collection truncation and stale UI can misrepresent state |

### ZCode concentration

ZCode is not a production-supported surface in the current build despite public
CLI/README claims. Its dedicated generator is unreachable, registration omits
it, native commands fall through to Claude, smoke fixtures miss it, activation
schema rejects it, post-tool parsing reads the wrong field, tool identity uses
Codex defaults, and active config registration is not inspected. AR-135 treats
this as one end-to-end parity correction rather than isolated patches.

### Instrumentation

Core trace/session/work-unit evidence is strong after persistence. The missing
piece is live boundary correlation: browser, HTTP, MCP, hook, and Store events
need one content-free request ID, bounded reason, outcome, duration, and exact
generation where relevant. Prompt content, tokens, credentials, SQL values, and
private paths must never be logged. AR-142 owns this work.

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

This table is the subagent-ready task artifact. A worker takes one AR item,
reads its issue and linked ADRs, adds focused regression tests first, implements
only that scope, runs proportionate checks, and returns exact evidence without
editing another worker's files.

| Wave | Task | Primary surface | Completion proof |
|---|---|---|---|
| 1 | [AR-128](../roadmap/issue-AR-128-seal-model-facing-control-authority.md) | MCP/broker/control authority | Model token cannot mutate; human UI/CLI still can |
| 1 | [AR-129](../roadmap/issue-AR-129-isolate-subprocess-environments.md) | Installer/delegation env | Sentinel credential and unsafe PATH probes denied |
| 1 | [AR-130](../roadmap/issue-AR-130-revalidate-store-trust.md) | Store filesystem trust | Same-identity permission transition fails closed |
| 1 | [AR-131](../roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md) | MCP schemas/CLI parity | Real protocol success and global schema meta-test |
| 1 | [AR-132](../roadmap/issue-AR-132-hire-deterministic-safe-gaps.md) | Workforce route/hiring | Full safe-gap route hires/restaffs with durable receipt |
| 1 | [AR-139](../roadmap/issue-AR-139-restore-release-asset-budget.md) | Release assets | Existing strict budget passes without limit change |
| 2 | [AR-133](../roadmap/issue-AR-133-atomic-finalization-evidence.md) | HTTP/MCP/Store | One all-or-nothing bounded transaction |
| 2 | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) | SQLite migration/currentness | Fresh/upgraded/tampered schema tests |
| 2 | [AR-135](../roadmap/issue-AR-135-complete-zcode-integration.md) | ZCode install/hooks/status | Fresh install through activation/lineage smoke |
| 2 | [AR-136](../roadmap/issue-AR-136-persist-native-child-correlation.md) | Hook subprocesses | Two-process correlation and outage denial |
| 2 | [AR-143](../roadmap/issue-AR-143-require-operator-presence-for-controls.md) | Dashboard/CLI control authority | Model-callable surfaces cannot mutate |
| 3 | [AR-137](../roadmap/issue-AR-137-complete-dashboard-collections.md) | Dashboard collections | 263/1,001 row exact paging/count tests |
| 3 | [AR-138](../roadmap/issue-AR-138-coherent-observable-dashboard-ui.md) | Dashboard async/a11y | Race, stale, focus, mobile, accessibility tests |
| 3 | [AR-142](../roadmap/issue-AR-142-instrument-runtime-boundaries.md) | Cross-layer telemetry | One redacted request trace across every boundary |
| 3 | [AR-144](../roadmap/issue-AR-144-restore-dashboard-ui-release-coverage.md) | Dashboard release tests | Exact fixed coverage floors pass with behavioral callbacks |
| 3 | [AR-145](../roadmap/issue-AR-145-restore-python-release-coverage.md) | Python release coverage | Exact fixed 97 percent gate and separate performance arm pass |
| 3 | [AR-146](../roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md) | Dashboard cursor chain | Generated cursor round-trips through handler and Store |
| 3 | [AR-147](../roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md) | Windows ACL trust | Native nested conditional grants fail every trust classifier closed |
| 3 | [AR-148](../roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md) | Remediation HMAC input | Malformed signatures return invalid authority without an exception |
| 4 | [AR-140](../roadmap/issue-AR-140-scale-routing-and-retrieval.md) | Routing/retrieval/startup | Correctness-preserving size-tiered performance gates |
| 4 | [AR-141](../roadmap/issue-AR-141-restore-compatibility-consolidate-runtime.md) | Compatibility/refactor | Deprecation and canonical-helper contract tests |
| 5 | [AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) | Product/host evaluation | Benchmark-valid complete corpus and installed apps |

## Production exit gate

Production and CEO-demo readiness require all P0 issues above closed locally,
the full repository and release checklist green, a fresh install from canonical
artifacts, truthful host maturity, installed MCP protocol smoke, dashboard
desktop/mobile/browser QA, contractor hiring and native-specialist dogfood,
and AR-125 outcome evidence. Normal-profile Codex trust and live canaries must
remain user-approved host actions; tracker creation/closure, push, PR, hosted
Actions, tags, publication, and release also remain outward actions requiring
explicit authorization.
