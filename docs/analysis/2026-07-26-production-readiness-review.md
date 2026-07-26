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

### Medium

| ID | Finding | Owner |
|---|---|---|
| SEC-M1 | Delegated child PATH can retain dot, relative, repository, or unsafe caller entries even though the launcher itself is frozen. | [AR-129](../roadmap/issue-AR-129-isolate-subprocess-environments.md) |
| SEC-M2 | Restricted agent brokerage does not independently prove desired Store path or restart-required state. | [AR-128](../roadmap/issue-AR-128-seal-model-facing-control-authority.md) |
| SEC-M3 | One finalization request can partially commit evidence before a later conflict and accepts some coercible identity fields. | [AR-133](../roadmap/issue-AR-133-atomic-finalization-evidence.md) |

### Low

| ID | Finding | Owner |
|---|---|---|
| SEC-L1 | Legacy boolean columns lack explicit zero/one constraints and schema currentness omits critical object SQL. | [AR-134](../roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md) |
| SEC-L2 | Some REST fields fail as generic server errors instead of bounded typed client errors. | [AR-133](../roadmap/issue-AR-133-atomic-finalization-evidence.md) |
| SEC-L3 | MCP status exposes an unnecessary absolute database path. | [AR-131](../roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md) |

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

## Optimization review

### Measured performance

| Path | Evidence | Interpretation |
|---|---|---|
| Cached routing microbenchmark | p95 samples `2.193-3.579 ms` against a `2.0 ms` ceiling; 5/5 failed | Real narrow-gate regression; correctness and uncached <20 ms still passed |
| Full local route | about 653 ms cold, 87-121 ms warm; internal route 53-57 ms | Warm end-to-end work remains materially larger than the microbenchmark |
| Semantic retrieval, 263 agents | about 121-134 ms cold, 3.7-4.7 ms warm | Current bundled scale is usable but cold initialization is visible |
| Semantic retrieval, 10,000 agents | about 6-7.4 s cold, 199-414 ms warm, about 208 MiB peak | Current algorithm does not scale to large catalogs |
| CLI startup | about 840 ms | Heavy import/startup path is visible for hook-oriented commands |
| Finalize batch | up to 256 independent connections/transactions | Latency and partial-write risk share one root cause |

Safe improvements are coherent request reuse, one query vector, immutable
feature indexes keyed by exact roster revision, batched Store operations, and
deferred CLI imports. Positive authorization caching is explicitly excluded.

### Maintainability and compatibility

- `route_and_build_context` and `header.finalize` were removed as unused inside
  this repository without a deprecation window or declared breaking release.
- POSIX trust checks, path/JSON helpers, bounded-string helpers, and agent
  identity extraction are duplicated; `slug` versus `agent_slug` precedence is
  not consistent.
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

The UI looks good enough for a demo visually: consistent dark design, working
navigation, readable cards, responsive 375 px layout, and clean browser console.
It is **not yet production-truthful** because complete-workforce views hide at
least 63 bundled records, failures can leave stale panels without a marker,
polling disrupts keyboard state, and ZCode is missing from one hard-coded host
surface. Preserve the design; repair completeness, coherence, accessibility,
and support diagnostics through AR-137 and AR-138.

## Requested deeper-review areas

These remain residual-review notes, not invented findings:

- `process_argv.py`: shell-free canonicalization and call discipline were
  traced; no new bypass was reproduced. The documented same-account race
  remains residual risk.
- `windows_acl.py` / `windows_private_directory.py`: call sites and native
  identity checks were traced; no ctypes defect was confirmed. Exhaustive
  Windows ABI verification still needs the hosted Windows security gate.
- `schema.py`: dynamic currentness and host-domain defects were reproduced and
  promoted to AR-134. All reviewed string-built DDL identifiers remain internal
  constants; no injection path was found.
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
