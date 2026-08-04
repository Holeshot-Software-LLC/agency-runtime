---
title: "Deep audit findings 2026-07-25"
status: active
category: analysis
created: 2026-07-25
updated: 2026-07-25
tags: [analysis, security, optimization, traceability]
related: []
supersedes: []
superseded_by: null
---

# Deep Audit Findings — 2026-07-25

**Status:** working analysis document (untracked, not a governed record). Promote validated items to AR-NN issues.
**Sources:** 6 parallel read-only audits — Security, Optimization, Traceability L1 (UI→HTTP) / L2 (routes→store) / L3 (store→SQL) / L4 (schema).
**Headline:** The codebase is unusually well-hardened. **Zero Critical or High findings.** A handful of Mediums, many Low hardening items. Two coherent themes: (1) information leakage at boundaries, (2) observability / debuggability gaps.

## Severity rollup

| Area | Crit | High | Med | Low | Notes |
|---|---|---|---|---|---|
| Security | 0 | 0 | 1 | 4 | SEC-01 the one real fix |
| Optimization | — | — | — | 11 dead + 5 dup + 6 size + 9 perf | PERF-01/02 are the hook-latency wins |
| L1 UI→HTTP | 0 | 0 | 0 | 3 | clean |
| L2 routes→store | 0 | 0 | 1 | 5 | L2-05 real fix |
| L3 store→SQL | 0 | 0 | 1 | 9 | L3-09 instrumentation theme |
| L4 schema | 0 | 0 | 0 | 6 | FK CASCADE + CHECK hardening |

---

## THEMES (cross-cutting — these are the real takeaways)

### Theme A — Information leakage at boundaries
- **SEC-01** (`agency serve` prints bearer token to stdout, `server/http.py:954`) — diverges from dashboard service-mode discipline ("token never in logs"). **Real fix.**
- **L2-05** (`RuntimeControlSecurityError` message echoed to client as 400 body via `except (KeyError, ValueError, RuntimeError)`, `dashboard.py:1121`) — security-exception messages shouldn't reach clients. **Real fix.**

### Theme B — Observability / debuggability (3 layers independently flagging the same gap)
- **L1**: zero client-side logging; failed fetch only shows a 6s toast; no request IDs.
- **L2**: no per-request correlation IDs at the HTTP layer; rely on timestamp/path/CAS-token matching.
- **L3-09 (Medium)**: store layer has **zero** observability — no SQL trace callback, no slow-query timing, no logging, no error annotation of which query failed. `trace_id` is correctly persisted on every evidence table so *post-hoc* correlation works, but *live* slow calls are opaque.
- Combined recommendation: add per-request ID at HTTP layer + debug-gated SQL trace + slow-query timing emit.

### Theme C — Hook-path latency (30s-timeout-critical, NOT covered by the routing microbenchmark gate)
- **PERF-01 (highest leverage)**: `run_preflight` builds `_RouteRequest` twice per turn (once for `routing_context_fingerprint`, once inside `route()`). Full-catalog walk + canonicalize+sha256 over the roster × 2. On every fresh UserPromptSubmit.
- **PERF-02**: Stop path opens 5+ fresh SQLite connections per Stop event, each paying the trust-check (lstat, Windows DACL/SDDL probe) + connect + setup cost. 6 round-trips when one transaction would do.
- **PERF-05/06/08**: smaller hook-path wins (double `detect_fallback_companions`, double `affirmative_intent`, 4-query `find_authoritative_trace` loop).

---

## ALL FINDINGS — ordered by recommended priority for execution

> Each item: `ID | Sev | Effort | Depends on | File:line | One-line`. Effort: XS/S/M/L.

### Priority 1 — Real fixes (do first)
| ID | Sev | Effort | Deps | Where | What |
|---|---|---|---|---|---|
| SEC-01 | Medium | S | — | `server/http.py:954` | Don't print bearer token to stdout unless TTY (match dashboard service-mode discipline) |
| L2-05 | Medium | S | — | `server/dashboard.py:1121` | Catch `RuntimeControlSecurityError`/`RuntimeControlValidationError` separately; log full detail server-side, return generic message to client |
| PERF-01 | Med-perf | M | — | `core/preflight.py:1523` + `selector/pipeline.py:370` | Eliminate double `_RouteRequest` build per turn (thread pre-built request through `route()` or memoize). Highest hook-latency leverage |
| PERF-02 | Med-perf | S(trust-cache) / M-L(scope) | — | `core/store/sqlite.py:889` + Stop path | Cache `_storage_file_is_trusted` result for process lifetime keyed by `(path, ino, mtime_ns)`; optionally scope Stop-path store calls into one transaction |

### Priority 2 — Safety hardening (low risk, high value)
| ID | Sev | Effort | Deps | Where | What |
|---|---|---|---|---|---|
| SEC-02 | Low | S | — | `core/dashboard_runtime.py` | Regression test pinning broker-token allowlist against mutating routes |
| SEC-03 | Low | S | — | `core/delegation/lifecycle_git.py:429` | Comment the inverted-looking repo-boundary refusal + add guard test |
| SEC-05 | Low | S | — | `server/mcp.py:312` | Fail closed when a tool schema omits `maxLength` (prevent future unbounded input) |
| L4-04 | Low | M | — | `core/store/schema.py` (multiple FKs) | Add `ON DELETE CASCADE` to audit-only child tables; document `RUNTIME_DELETE_ORDER` as convention |
| L4-05 | Low | S | — | `schema.py:910, 1051-1052` | Add `CHECK (col IN (0,1))` to `agent_sources.enabled`, `agent_snapshots.{approved,activated}` |
| L2-06 | Low | S | — | `server/dashboard.py:1515` | Isolate per-host `inspect_host_status` failures so one bad record doesn't 400 the whole `/api/hosts` payload |
| L1-21 | Low | S | — | `dashboard/dashboard-actions.js:325` | Add abort guard to `selectWorker` GET (prevent double-click race) |

### Priority 3 — Observability theme (Theme B)
| ID | Sev | Effort | Deps | Where | What |
|---|---|---|---|---|---|
| L3-09 | Medium | M | — | store-wide | Debug-gated `set_trace_callback`; slow-query timing emit (>100ms); annotate store-method exceptions with offending SQL; expose `busy_timeout_hits` counter |
| L2-obs | Low | M | L3-09 | `server/dashboard.py` + `http.py` | Generate per-request UUID at `do_GET`/`do_POST` entry; include in `logger.exception`; propagate to client response header for end-to-end correlation |
| L1-obs | Low | M | L2-obs | dashboard JS | Optional structured client log + surface request IDs for failed fetches (beyond the 6s toast) |

### Priority 4 — Dead code removal (safe, quick)
| ID | Effort | Deps | Where | What |
|---|---|---|---|---|
| DEAD-06 | XS | — | `core/header/finalize.py:315` | Delete `finalize` alias + re-export (zero callers anywhere) |
| DEAD-07 | XS | — | `adapters/hooks.py:993` | Delete `_handle_claude_pre_tool_use` (one-line wrapper, test-only); port test to `_handle_native_child_pre_tool_use` |
| DEAD-08 | XS | — | `adapters/hooks.py:1561` | Delete `_is_authenticated_retry` method (test-only; live version in `openclaw/node_bridge.py:105`) |
| DEAD-09 | XS | — | `adapters/hooks.py:2049` | Delete `_record_finalization` method (production uses store's `record_finalization` via `header/finalize.py`) |
| DEAD-10 | XS | — | `adapters/hooks.py:1959` | Delete `_accept_exact_finalized_response` method (live version in `openclaw/node_bridge.py:251`); port tests to `_exact_terminal_finalization` |
| DEAD-11 | XS | — | `core/store/roster.py:1236` | Delete `count_active_roster` (test-only; use `count_enabled_roster(disabled_agents=())`) |
| DEAD-01 | S | — | `selector/pipeline.py:1305` | Delete `route_and_build_context`; port test to `route` + `build_routing_context` |
| DEAD-02 | S | — | `selector/pipeline.py:178` | Delete or formally deprecate `is_trivial` (compatibility alias, test-only) |
| DEAD-03 | XS | — | `selector/candidate_narrow.py:450` | Delete `pre_narrow_many` (test-only) |
| DEAD-04 | XS | — | `selector/candidate_narrow.py:305` | Keep `_clear_compiled_score_caches` as private test seam; document as test-only |
| DEAD-05 | XS | — | `selector/semantic_retrieval.py:445` | Wire `clear_semantic_retrieval_cache` into `evals/routing.py:99` for consistency, or delete |

### Priority 5 — Duplication consolidation (S-M each)
| ID | Effort | Deps | What |
|---|---|---|---|
| DUP-01 | XS | — | Collapse `preflight._coherent_workforce_snapshot` into canonical `routing_snapshot.bind_workforce_snapshot` (verify config identity first) |
| DUP-02 | S | — | Unify 5 `_slug`/`_agent_id` one-liners into `selector/_identity.py:agent_identity(agent)` (normalize slug-vs-agent_slug precedence) |
| DUP-03 | S | — | Consolidate `_bounded_unique_strings` (pipeline.py + preflight_recipe.py); reconcile whitespace-collapse behavior |
| DUP-04 | S | — | Have `_claude_post_tool_response` delegate to extended `_native_child_tool_identity` |
| DUP-05 | M | — | Collapse `_handle_{claude,codex}_subagent_{start,stop}` (4 methods) into 2 parameterized by host profile |

### Priority 6 — Structural decomposition (M each, lower urgency)
| ID | Effort | Where | What |
|---|---|---|---|
| SIZE-01 | M | `selector/pipeline.py:943` (281 LOC) | Split `route()` into `_route_workforce` + `_route_classic` + dispatch |
| SIZE-02 | M | `core/preflight.py:1348` (318 LOC) | Split `run_preflight` into lifecycle/prepare/commit helpers |
| SIZE-03 | M | `core/preflight.py:652` (226 LOC) | Split `_resolve_preflight_routing`; extract `_build_child_route_cache_key` |
| SIZE-04 | S | `adapters/hooks.py:840` (152 LOC) | Extract `_render_and_size_check` + `_prepare_activation` |
| SIZE-05 | M | `core/preflight.py:344` (148 LOC) | Extract `_validate_parent_unit_match` + shared routing-dict helper |
| SIZE-06 | M | `selector/judge.py:343` (177 LOC) | Lower priority; extract `_judge_without_inference` + `_judge_degraded_or_fallback` |

### Priority 7 — Smaller perf wins (S each)
| ID | Effort | Deps | What |
|---|---|---|---|
| PERF-03 | S | — | Batched `record_specialists_loaded` (currently N+1 up to 16) for MCP/tools path |
| PERF-04 | S | — | Single-query roster-entry fallback in `_selection_refs_for_recipe` (per-slug today) |
| PERF-05 | S | — | `detect_actions` returns fallback IDs; drop double call in `_route_signals` |
| PERF-06 | S | — | Skip redundant `affirmative_intent` in `query_judge` when pipeline pre-affirmed |
| PERF-07 | S | — | Reuse pre-narrowed candidates in `explain_route` (avoid double `pre_narrow`) |
| PERF-08 | S | — | Single `find_authoritative_trace(action=None)` across actions instead of 4 queries |
| PERF-09 | N/A | — | Documentation only: note ThreadPoolExecutor is for I/O overlap, not CPU (GIL) |

### Priority 8 — Minor / informational (likely won't fix)
| ID | Sev | Notes |
|---|---|---|
| SEC-04 | Low | `safe_load_bounded_json` redundant char-count pre-check — not a bypass, leave it |
| L1-01/03 | Low | `limit`/`vacuum`/`dry_run` server capabilities under-exposed in UI — by design |
| L1-07 | Low | `toggleAgent` "missing" revision fallback — dead but harmless |
| L2-01/02/03 | Low | workforce/hiring redundancy + prompt-bypass — intentional/compensated |
| L2-04 | Low | `list_workforce_workers(limit=1000)` count truncation — fix only if >1000 workers realistic |
| L2-07/08/09/10 | Low | non-atomic overview read / legacy explain divergence — acceptable |
| L3-01/02 | Low | missing composite indexes — only matters if join direction inverts |
| L3-03 | Low | skills_loaded no de-dup (audit-event design) — confirm intent |
| L3-04 | Low | missing `str()` coercion — defensive only |
| L3-05 | Low | ACL-repair on every read — cached, cheap |
| L3-06 | Low | `get_completion_evidence_snapshot` write-lock-for-read — intentional |
| L3-07 | Low | 41 COUNT(*) on /api/overview — only on manual load |
| L3-08 | Low | misleading dead base-DDL index — cosmetic |
| L3-10 | Low | host-canary autocommit — stylistic |
| L4-01/02/03/06/07/08/11/12/13/14 | Low | schema discipline notes — most are intentional/compensated |

### "Needs deeper review" (auditor couldn't fully verify — not findings)
- `process_argv.py` (1100+ lines, Windows launcher canonicalization) — threat model covers residual same-account race
- `windows_acl.py` / `windows_private_directory.py` (ctypes DACL/SID logic) — confirmed call-site discipline; exhaustive ctypes review out of scope
- `schema.py` migration steps (4600+ lines) — confirmed `ensure_column`/`DROP` interpolations use internal identifiers only
- Quarantined-prompt HMAC-escape path — no string-built SQL or unsafe deserialization found; full authority-flow trace out of scope

---

## CONFIRMED-SAFE (verified controls, not assumed)
Loopback-only HTTP binding + strict Host/Origin + bearer tokens + `compare_digest`; parameterized SQL everywhere (`nosec B608` only on internal-identifier interpolation); serialized ACL repair (AR-22 holds); fail-closed master switch with generation CAS; content-addressed single-use prompt delivery; shell-free delegation with executable resolution rejecting CWD/dot PATH; `hashlib.sha256`/`secrets`/`hmac`, no MD5/SHA1/eval/pickle. Schema: WAL + `synchronous=NORMAL` + `busy_timeout=5000` + `recursive_triggers=ON` + `foreign_keys=ON` + `secure_delete=ON`, all verified-on-connect. `trace_id` correlation end-to-end complete across all 11 evidence tables (indexed).

---

## RECOMMENDED EXECUTION PLAN

**Wave 1 — Real fixes (1 PR):** SEC-01, L2-05. Both Medium, both S effort, both boundary info-leak. Low risk, high signal.
**Wave 2 — Hook latency (1 PR):** PERF-01 + PERF-02 trust-cache. Biggest user-facing perf win, on the 30s-timeout path, ungated today.
**Wave 3 — Dead code sweep (1 PR):** DEAD-06/07/08/09/10/11 (the XS deletes) + DEAD-01/03. Mechanical, safe, shrinks the surface.
**Wave 4 — Safety hardening (1 PR):** SEC-02/03/05, L4-05, L2-06, L1-21. Regression tests + CHECK constraints + isolation guards.
**Wave 5 — Observability (1 PR, optional):** L3-09 + L2-obs. Theme B. Bigger but unblocks future debugging.
**Defer / batch:** DUP-*, SIZE-* (refactors — do when touching those files for other reasons), PERF-03/04/05/06/07/08 (small wins — fold into relevant PRs), L4-04 CASCADE (M, do with a schema migration).
