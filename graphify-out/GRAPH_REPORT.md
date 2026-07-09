# Graph Report - .  (2026-07-08)

## Corpus Check
- Corpus is ~26,725 words - fits in a single context window. You may not need a graph.

## Summary
- 896 nodes · 2181 edges · 58 communities (34 shown, 24 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 193 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_CLI & Config Entry|CLI & Config Entry]]
- [[_COMMUNITY_Header Contract|Header Contract]]
- [[_COMMUNITY_Base Adapter Interface|Base Adapter Interface]]
- [[_COMMUNITY_Receipts & Telemetry|Receipts & Telemetry]]
- [[_COMMUNITY_Roster Sync|Roster Sync]]
- [[_COMMUNITY_Backend Registry|Backend Registry]]
- [[_COMMUNITY_Config Loader|Config Loader]]
- [[_COMMUNITY_Delegation Lifecycle|Delegation Lifecycle]]
- [[_COMMUNITY_Selector Pipeline|Selector Pipeline]]
- [[_COMMUNITY_Runtime Facade|Runtime Facade]]
- [[_COMMUNITY_HTTP Server Core|HTTP Server Core]]
- [[_COMMUNITY_HTTP Handlers|HTTP Handlers]]
- [[_COMMUNITY_Delegation Backends|Delegation Backends]]
- [[_COMMUNITY_Doctor Diagnostics|Doctor Diagnostics]]
- [[_COMMUNITY_Delegation Detection|Delegation Detection]]
- [[_COMMUNITY_Config Schema|Config Schema]]
- [[_COMMUNITY_Delegation Ledger|Delegation Ledger]]
- [[_COMMUNITY_Judge (LLM Scoring)|Judge (LLM Scoring)]]
- [[_COMMUNITY_Dependency Graph|Dependency Graph]]
- [[_COMMUNITY_Candidate Narrowing|Candidate Narrowing]]
- [[_COMMUNITY_LiteLLM Adapter|LiteLLM Adapter]]
- [[_COMMUNITY_Codex Adapter|Codex Adapter]]
- [[_COMMUNITY_Roster Quarantine|Roster Quarantine]]
- [[_COMMUNITY_Hermes Adapter|Hermes Adapter]]
- [[_COMMUNITY_Delegate Dispatch|Delegate Dispatch]]
- [[_COMMUNITY_Selector Cache|Selector Cache]]
- [[_COMMUNITY_Claude Adapter|Claude Adapter]]
- [[_COMMUNITY_OpenClaw Adapter|OpenClaw Adapter]]
- [[_COMMUNITY_Generic Adapter|Generic Adapter]]
- [[_COMMUNITY_Test Fixtures|Test Fixtures]]
- [[_COMMUNITY_Policy Loader|Policy Loader]]
- [[_COMMUNITY_Adapter Base Class|Adapter Base Class]]
- [[_COMMUNITY_Session Stickiness|Session Stickiness]]
- [[_COMMUNITY_ChunkHound Index|ChunkHound Index]]
- [[_COMMUNITY_README Concepts|README Concepts]]
- [[_COMMUNITY_Package Init|Package Init]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Default Roster|Default Roster]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Config Defaults|Config Defaults]]

## God Nodes (most connected - your core abstractions)
1. `Store` - 136 edges
2. `AgencyConfig` - 49 edges
3. `load_config()` - 45 edges
4. `BaseAdapter` - 42 edges
5. `DelegationLedger` - 33 edges
6. `int` - 31 edges
7. `Namespace` - 25 edges
8. `normalize_work_units()` - 23 edges
9. `delegate_with_lifecycle()` - 23 edges
10. `str` - 23 edges

## Surprising Connections (you probably didn't know these)
- `Path` --uses--> `Store`  [INFERRED]
  tests/test_http_server.py → agency_runtime/core/store/sqlite.py
- `str` --uses--> `Store`  [INFERRED]
  tests/test_http_server.py → agency_runtime/core/store/sqlite.py
- `int` --uses--> `Store`  [INFERRED]
  tests/test_http_server.py → agency_runtime/core/store/sqlite.py
- `test_normalize_string()` --calls--> `normalize_work_units()`  [EXTRACTED]
  tests/test_delegation.py → agency_runtime/core/delegation/lifecycle.py
- `test_normalize_list_of_strings()` --calls--> `normalize_work_units()`  [EXTRACTED]
  tests/test_delegation.py → agency_runtime/core/delegation/lifecycle.py

## Communities (58 total, 24 thin omitted)

### Community 0 - "CLI & Config Entry"
Cohesion: 0.06
Nodes (85): AgencyConfig, Any, Argparse command line interface for Agency Runtime.  Commands:     agency instal, int, str, Any, bool, float (+77 more)

### Community 1 - "Header Contract"
Cohesion: 0.08
Nodes (55): Any, bool, str, Any, bool, str, _clean(), _complexity_for_model_group() (+47 more)

### Community 2 - "Base Adapter Interface"
Cohesion: 0.08
Nodes (36): ABC, expose_model_telemetry(), get_delegate_backend(), is_available(), Base adapter interface — all adapters implement this contract., Apply header/finalization to the final visible reply., report_skills_loaded(), report_specialists_loaded() (+28 more)

### Community 3 - "Receipts & Telemetry"
Cohesion: 0.12
Nodes (34): Any, str, Any, int, str, Any, bool, str (+26 more)

### Community 4 - "Roster Sync"
Cohesion: 0.17
Nodes (35): Any, bool, Store, str, cmd_sync(), activate_snapshot(), _active_by_slug(), approve_snapshot() (+27 more)

### Community 5 - "Backend Registry"
Cohesion: 0.11
Nodes (24): bool, BackendRegistry, CommandBackend, DelegateBackend, Ordered registry of pluggable delegation backends., Register a backend and return it for decorator-style use., Return currently available backends in selection order., Select the first available backend, optionally constrained by name. (+16 more)

### Community 6 - "Config Loader"
Cohesion: 0.09
Nodes (29): bool, config_to_yaml(), load_config(), Load config with precedence: env > file > bundled defaults.      Args:         p, Serialize config back to YAML for display.      Args:         redact: If True, m, LiteLLM adapter — callback for LiteLLM proxy.  When LiteLLM is present, this ada, Tests for the centralized config system., config_to_yaml redacts api_key by default. (+21 more)

### Community 7 - "Delegation Lifecycle"
Cohesion: 0.17
Nodes (29): Any, bool, int, Path, str, aggregate_results(), _backend(), _branch_exists() (+21 more)

### Community 8 - "Selector Pipeline"
Cohesion: 0.16
Nodes (21): AgencyConfig, Any, bool, str, Agency Runtime Control Plane.  A portable control plane for specialist routing,, Codex adapter — first-class wrapper and delegation backend.  Works with or witho, Pre-call handler for LiteLLM proxy.          Runs the routing pipeline and retur, OpenClaw adapter — typed plugin hooks for OpenClaw runtime.  Uses api.on(...) ty (+13 more)

### Community 9 - "Runtime Facade"
Cohesion: 0.12
Nodes (15): AgencyRuntime, Any, int, str, Main entry point for the Agency Runtime Control Plane.      Usage:         runti, Route a user message to specialist agents., Route and return the preflight context string., Detect independent work units in a message. (+7 more)

### Community 10 - "HTTP Server Core"
Cohesion: 0.21
Nodes (13): Any, int, Path, str, BaseHTTPRequestHandler, AgencyHTTPHandler, main(), _normalise_path() (+5 more)

### Community 11 - "HTTP Handlers"
Cohesion: 0.13
Nodes (23): AgencyHTTPServer, Threaded HTTP server for Agency Runtime.      Each request is handled in its own, _get(), http_server(), _post(), int, Path, str (+15 more)

### Community 12 - "Delegation Backends"
Cohesion: 0.11
Nodes (16): Any, str, CodexExecBackend, HermesDelegateBackend, OpenClawSessionsBackend, Pluggable delegation backends for Agency Runtime.  Backends expose a small calla, OpenClaw session-spawn backend when an OpenClaw CLI is available., OpenAI Codex CLI backend using non-interactive exec mode. (+8 more)

### Community 13 - "Doctor Diagnostics"
Cohesion: 0.16
Nodes (22): AgencyConfig, Any, bool, float, int, str, AgencyConfig, CheckResult (+14 more)

### Community 14 - "Delegation Detection"
Cohesion: 0.11
Nodes (21): Any, str, str, detect_work_units(), Work unit decomposition — detect independent tasks for delegation.  Ported from, Detect independent work units in a user message.      Returns:         {, expand_query(), Domain context expansion — enriches queries with discipline vocabulary.  Ported (+13 more)

### Community 15 - "Config Schema"
Cohesion: 0.16
Nodes (20): Any, Path, str, AdapterEntryConfig, AdaptersConfig, _apply_env_overrides(), _build_adapter_entry(), _build_adapters() (+12 more)

### Community 16 - "Delegation Ledger"
Cohesion: 0.13
Nodes (15): Any, int, Store, str, DelegationLedgerEntry, entries(), from_store(), Auditable delegation ledger for Agency Runtime.  The ledger is the small contrac (+7 more)

### Community 17 - "Judge (LLM Scoring)"
Cohesion: 0.23
Nodes (20): AgencyConfig, Any, bool, float, int, str, bytes, JudgeConfig (+12 more)

### Community 18 - "Dependency Graph"
Cohesion: 0.14
Nodes (17): CompletedProcess, DelegationLedger, Record delegation lifecycle state and render the required JSON contract., build_dependency_graph(), DependencyGraph, Build dependency edges from sequencing language and same-file overlap., Directed dependency graph where edges point predecessor -> successor., Tests for delegation lifecycle — normalization, dependency graph, dispatch. (+9 more)

### Community 19 - "Candidate Narrowing"
Cohesion: 0.16
Nodes (18): Any, float, int, str, pre_narrow(), Token scoring utilities for candidate pre-narrowing.  Ported from ~/.litellm/age, Tokenize text for token-overlap scoring., Fast in-memory token-overlap score for candidate pre-narrowing. (+10 more)

### Community 20 - "LiteLLM Adapter"
Cohesion: 0.17
Nodes (11): AgencyConfig, Any, bool, Store, str, litellm_health_check(), LiteLLMAdapter, Check if LiteLLM gateway is reachable. (+3 more)

### Community 21 - "Codex Adapter"
Cohesion: 0.18
Nodes (9): Any, bool, Store, str, CodexAdapter, Run agency selector before launching codex., Codex CLI wrapper adapter., Check if codex CLI is installed. (+1 more)

### Community 22 - "Roster Quarantine"
Cohesion: 0.24
Nodes (16): Any, bool, int, Store, str, approve(), _connect(), _json_list() (+8 more)

### Community 23 - "Hermes Adapter"
Cohesion: 0.19
Nodes (9): Any, bool, int, str, HermesAdapter, Hermes Agent runtime adapter., Check if Hermes is the current host., Pre-LLM call handler for Hermes plugin system. (+1 more)

### Community 24 - "Delegate Dispatch"
Cohesion: 0.15
Nodes (15): DelegateFunc, get_delegate_func(), Return a delegate_func-compatible callable for lifecycle dispatch., Return a lifecycle-compatible delegate callable from a registry., delegate_with_lifecycle(), dispatch_work_units(), LifecycleResult, Dispatch topological batches with ThreadPoolExecutor. (+7 more)

### Community 25 - "Selector Cache"
Cohesion: 0.22
Nodes (14): Any, float, int, str, cache_get(), cache_key(), cache_put(), clear_cache() (+6 more)

### Community 26 - "Claude Adapter"
Cohesion: 0.19
Nodes (8): Any, bool, Store, str, ClaudeAdapter, Claude Code CLI wrapper adapter (optional)., Check if Claude Code CLI is installed., Execute a task via claude -p --output-format json.          Collects modelUsage/

### Community 27 - "OpenClaw Adapter"
Cohesion: 0.19
Nodes (8): Any, bool, str, OpenClawAdapter, OpenClaw/Nexus runtime adapter., Check if OpenClaw is running., Typed plugin hook: message received, run preflight., Typed plugin hook: apply header finalization before response sent.

### Community 28 - "Generic Adapter"
Cohesion: 0.22
Nodes (7): Any, bool, Store, str, GenericAdapter, Generic CLI wrapper adapter., Execute a task via a generic CLI command.

### Community 29 - "Test Fixtures"
Cohesion: 0.20
Nodes (10): Clear the cached config singleton (for tests)., reset_config_cache(), _clean_env(), Clear agency env vars before each test., _clean_env(), Tests for the doctor health diagnostics., Doctor fails when roster is empty., Report is JSON-serializable. (+2 more)

### Community 30 - "Policy Loader"
Cohesion: 0.25
Nodes (10): Any, Path, str, detect_actions(), load_policy(), Companion policy — deterministic action→agent mapping.  Ported from ~/.litellm/a, Resolve policy path from centralized config, env, or default., Load companion policy YAML, auto-reloading on file change. (+2 more)

### Community 31 - "Adapter Base Class"
Cohesion: 0.20
Nodes (6): BaseAdapter, Base class for host/runtime adapters.      Adapters are thin I/O shims. They tra, Store, Claude Code adapter — optional, skipped if not installed.  Two modes when availa, Generic adapter — wraps any agent CLI.  For runtimes that don't have a dedicated, Hermes adapter — plugin for Hermes Agent runtime.  When Hermes is the host, this

### Community 32 - "Session Stickiness"
Cohesion: 0.32
Nodes (6): Any, float, str, Session stickiness — reuse recent routing when token overlap is high.  Ported fr, session_check(), session_put()

### Community 34 - "README Concepts"
Cohesion: 0.67
Nodes (3): Architecture Overview, Key Design Principles, Install Profiles System

## Knowledge Gaps
- **20 isolated node(s):** `version`, `indexed_root_path`, `str`, `str`, `Any` (+15 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Base Adapter Interface` to `CLI & Config Entry`, `Header Contract`, `Roster Sync`, `Backend Registry`, `Config Loader`, `Selector Pipeline`, `Runtime Facade`, `HTTP Server Core`, `HTTP Handlers`, `Doctor Diagnostics`, `Delegation Ledger`, `Dependency Graph`, `LiteLLM Adapter`, `Codex Adapter`, `Roster Quarantine`, `Hermes Adapter`, `Claude Adapter`, `OpenClaw Adapter`, `Generic Adapter`, `Test Fixtures`, `Adapter Base Class`?**
  _High betweenness centrality (0.585) - this node is a cross-community bridge._
- **Why does `DelegationLedger` connect `Dependency Graph` to `Base Adapter Interface`, `Backend Registry`, `Delegation Lifecycle`, `Delegation Backends`, `Delegation Ledger`, `Delegate Dispatch`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `load_config()` connect `Config Loader` to `CLI & Config Entry`, `Base Adapter Interface`, `Selector Pipeline`, `HTTP Server Core`, `Doctor Diagnostics`, `Config Schema`, `Judge (LLM Scoring)`, `LiteLLM Adapter`, `Test Fixtures`, `Policy Loader`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 81 inferred relationships involving `Store` (e.g. with `Path` and `str`) actually correct?**
  _`Store` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `AgencyConfig` (e.g. with `str` and `AgencyConfig`) actually correct?**
  _`AgencyConfig` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `BaseAdapter` (e.g. with `ClaudeAdapter` and `OpenClawAdapter`) actually correct?**
  _`BaseAdapter` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `DelegationLedger` (e.g. with `FakeBackend` and `bool`) actually correct?**
  _`DelegationLedger` has 17 INFERRED edges - model-reasoned connections that need verification._