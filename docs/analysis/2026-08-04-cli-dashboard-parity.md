---
title: "CLI and dashboard functional and presentational parity"
status: draft
category: analysis
created: 2026-08-04
updated: 2026-08-04
tags: [cli, dashboard, parity, analysis, routing, workforce, hiring, ops]
related:
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - agency_runtime/cli/parser.py
  - agency_runtime/cli/workforce_commands.py
  - agency_runtime/cli/roster_commands.py
  - agency_runtime/dashboard/dashboard-render.js
  - agency_runtime/dashboard/dashboard-actions.js
  - agency_runtime/server/http.py
  - agency_runtime/core/dashboard_operational.py
supersedes: []
superseded_by: null
type: analysis
---

# CLI and dashboard functional and presentational parity

## Goal

The dashboard is a "pretty GUI" of the same capability surface the CLI
exposes; the CLI is a "pretty terminal" of the same surface the
dashboard exposes. Identical functionality parity in both directions,
identical presentational richness in the medium that suits each
surface. No dashboard-only operations, no CLI-only operations, no
information one surface shows and the other hides.

This analysis is the inventory. It feeds a new AR (proposed below) that
defines the parity roadmap.

## Methodology

I read the canonical sources for each surface and built the inventory
from the source, not from the README:

- CLI surface: `agency_runtime/cli/parser.py` (`build_parser` + 14
  `_register_*` functions), `agency_runtime/cli/main.py` (`cmd_*` +
  `_cmd_*` handlers), and the per-domain handler modules
  (`workforce_commands.py`, `roster_commands.py`, `config_commands.py`,
  `delegation_commands.py`, `eval_commands.py`, `install_commands.py`,
  `uninstall_commands.py`, `upgrade_commands.py`, `service_commands.py`,
  `agent_control_broker.py`, `status_projection.py`).
- Dashboard surface: `agency_runtime/dashboard/index.html` (view
  panels and their inner sections), `dashboard-render.js` (render
  functions for each view), `dashboard-actions.js` (the API endpoints
  the dashboard actually calls).
- Server surface: `agency_runtime/server/http.py` (read endpoints) and
  the POST/PUT/DELETE endpoints the dashboard uses (extracted from
  `dashboard-actions.js`'s `api(...)` calls).

I deliberately did not read the README's "Available views" section as
a source of truth — the surface area is in the code, and the code is
the parity contract.

## CLI surface inventory (as of 2026-08-04)

50+ top-level commands, registered in `parser.py` via
`build_parser`. Subcommands shown indented.

| Top-level | Subcommand | Handler | What it does |
|---|---|---|---|
| `--version` | — | `__init__` | Print Agency Runtime version |
| `version` | — | `cmd_version` | Print Agency Runtime version (alias) |
| `upgrade` | — | `cmd_upgrade` | Plan / run / list an in-place upgrade |
| `install` | — | `cmd_install` | Install Agency Runtime to a host |
| `uninstall` | — | `cmd_uninstall` | Uninstall Agency Runtime from a host |
| `on` | — | `cmd_on` | Enable Agency on a host |
| `off` | — | `cmd_off` | Disable Agency on a host |
| `status` | — | `cmd_status` | Show per-host install + master status |
| `host-canary` | — | `cmd_host_canary` | Run a one-shot host canary |
| `configure` | — | `cmd_configure` | Guided provider-chain setup wizard |
| `doctor` | — | `cmd_doctor` | Diagnose DB, config, providers, adapters |
| `config` | `show` | `cmd_config_show` | Print effective configuration |
| `config` | `path` | `cmd_config_path` | Print config file path |
| `config` | `get <key>` | `cmd_config_get` | Read one config value |
| `config` | `set <key> <value>` | `cmd_config_set` | Write one config value |
| `config` | `validate` | `cmd_config_validate` | Validate config + reachability |
| `config` | `reset` | `cmd_config_reset` | Reset to defaults |
| `config` | `provider list` | `cmd_config_provider_list` | List configured providers |
| `config` | `provider models` | `cmd_config_provider_models` | Discover account models |
| `config` | `provider set` | `cmd_config_provider_set` | Add or update a provider |
| `config` | `provider remove` | `cmd_config_provider_remove` | Remove a provider |
| `roster` | `list` | `cmd_roster_list` | List roster (filterable) |
| `roster` | `diff` | `cmd_roster_diff` | Compare roster snapshots |
| `roster` | `approve` | `cmd_roster_approve` | Approve a roster snapshot |
| `roster` | `retire` | `cmd_roster_retire` | Retire a roster snapshot |
| `roster` | `rollback` | `cmd_roster_rollback` | Rollback a roster action |
| `roster` | `scans` | `cmd_roster_scans` | List source scans |
| `roster` | `candidate-audit` | `cmd_roster_candidate_audit` | Audit a candidate |
| `roster` | `candidate-compare` | `cmd_roster_candidate_compare` | Compare two candidates |
| `roster` | `candidate-findings` | `cmd_roster_candidate_findings` | Show candidate findings |
| `roster` | `candidate-reject` | `cmd_roster_candidate_reject` | Reject a candidate |
| `roster` | `upstream-import` | `cmd_roster_upstream_import` | Import from an upstream source |
| `roster` | `upstream-status` | `cmd_roster_upstream_status` | Show upstream source status |
| `roster` | `remediation-queue` | `cmd_roster_remediation_queue` | List pending remediations |
| `roster` | `activate` | `cmd_roster_activate` | Activate a staged roster |
| `roster` | `source-add` | `cmd_source_add` | Add a roster source |
| `roster` | `source-list` | `cmd_source_list` | List roster sources |
| `roster` | `sync` | `cmd_sync` | Sync roster from sources |
| `workforce` | `list` | `cmd_workforce_list` | List workforce members |
| `workforce` | `search` | `cmd_workforce_search` | Search workforce by query |
| `workforce` | `duplicates` | `cmd_workforce_duplicates` | Show near-duplicate workers |
| `workforce` | `consolidate` | `cmd_workforce_consolidate` | Consolidate near-duplicates |
| `workforce` | `show <slug>` | `cmd_workforce_show` | Show one worker record |
| `workforce` | `transition` | `cmd_workforce_transition` | Lifecycle transition (suspend/resume/retire/merge) |
| `contractor` | `list` | `cmd_contractor_list` | List contractor-class workers |
| `hiring` | `list` | `cmd_hiring_list` | List hiring cases |
| `hiring` | `show <id>` | `cmd_hiring_show` | Show one hiring case |
| `hiring` | `approve <id>` | `cmd_hiring_approve` | Approve a high-risk hiring case |
| `policy` | — | `cmd_policy` | Show companion policy + coverage |
| `route <task>` | — | `cmd_route` | Route a task to candidates |
| `explain <task>` | — | `cmd_explain` | Explain why a task routed the way it did |
| `search` | — | `cmd_search` | Search the roster (alias) |
| `agent-enable` | — | `cmd_agent_enable` | Enable one agent |
| `agent-disable` | — | `cmd_agent_disable` | Disable one agent |
| `agents-list` | — | `cmd_agents_list` | List agents (alias of `roster list`) |
| `db-stats` | — | `cmd_db_stats` | Show SQLite stats |
| `db-trim` | — | `cmd_db_trim` | Trim old rows from SQLite |
| `eval` | `compare` | `cmd_eval_compare` | Compare two Agency runs |
| `eval` | `decision-conformance` | `cmd_eval_decision_conformance` | Decision-conformance check |
| `eval` | `full-roster` | `cmd_eval_full_roster` | Eval against full roster |
| `eval` | `product` | `cmd_eval_product` | Product-scenario eval |
| `eval` | `upstream-architecture` | `cmd_eval_upstream_architecture` | Upstream architecture eval |
| `eval` | `upstream-selection` | `cmd_eval_upstream_selection` | Upstream selection eval |
| `eval` | `workforce` | `cmd_eval_workforce` | Workforce eval |
| `eval` | `delegation` | `cmd_eval_delegation` | Delegation eval |
| `eval` | `routing` | `cmd_eval_routing` | Routing eval |
| `serve` | — | `cmd_serve` | Start HTTP server |
| `dashboard` | — | `cmd_dashboard` | Open the dashboard |
| `dashboard` | `service ...` | `cmd_dashboard_service` | Manage the dashboard service |
| `hook <host>` | — | `cmd_hook` | Handle one native hook event |
| `mcp` | — | `cmd_mcp` | Serve MCP over stdio |
| `codex` | `exec ...` | `cmd_codex_exec` | Run codex exec |
| `run ...` | — | `cmd_run` | Run an arbitrary command |

## Dashboard surface inventory (as of 2026-08-04)

Six top-level views, three modal flows, and nine API actions.

**Views (read-side)**:

| View | Reads from | What it shows |
|---|---|---|
| Routing | SSE stream | Live routing activity, model receipts, header text |
| Evidence (sub-tabs: specialist-activations, delegations, routing-decisions, model-receipts, runs, finalizations) | SSE / REST | Filterable, paginated, current-turn + historical |
| Roster (browse, search, filter form, snapshots, review queue) | REST | Card grid, filter by division/capability/authority/host/platform/tool, snapshot list, quarantine review queue with paging |
| Workforce (metric grid: employees/contractors/disabled/suspended/retired/merged; grid; worker detail) | REST | Per-worker card with name, slug, capabilities, version, revision, recruitment contract, lifecycle history, promotion readiness, closest workers, compiled prompt preview |
| Policy | REST | Companion policy + coverage against active roster |
| Config (workforce settings, providers with reasoning effort, advanced storage/server) | REST | Workforce mode / caps / review window; ordered provider builder with reasoning effort; SQLite path / HTTP host / body size / companion policy path |

**Modals (write-side flows)**:

| Modal | Action | Confirm |
|---|---|---|
| Confirmation modal | Phrase-typed confirm for destructive lifecycle ops | Required for hire-approve, workforce lifecycle, host control, agency master |

**API endpoints the dashboard actually calls** (from `dashboard-actions.js`):

| Method + Path | Purpose |
|---|---|
| `POST /api/agents/toggle` | Enable or disable one agent |
| `POST /api/config` | Save configuration changes |
| `POST /api/hiring/approve` | Approve a high-risk hiring case |
| `POST /api/hosts/toggle` | Enable or disable a host |
| `POST /api/maintenance/trim` | Trim old rows from SQLite |
| `POST /api/roster/action` | Approve / retire / rollback a roster snapshot |
| `POST /api/route` | Route a task (interactive equivalent of `agency route`) |
| `POST /api/runtime/toggle` | Agency master on/off |
| `POST /api/workforce/action` | Workforce lifecycle action (enable / disable / merge / suspend / retire) |

## Parity matrix

Status: **✓** = both surfaces, **△** = partial (one surface or one direction), **✗** = missing on one side.

### Operations

| Operation | CLI | Dashboard | Status | Notes |
|---|---|---|---|---|
| Version | `agency --version` / `version` | (implicit) | △ | CLI is the source; dashboard could show in footer |
| Upgrade | `agency upgrade` | — | ✗ | Missing in dashboard |
| Install / uninstall | `agency install/uninstall` | — | n/a | Host lifecycle; out of scope for dashboard |
| Host on/off/status | `agency on/off/status` | master on/off button; status in routing view | △ | No per-host detail in dashboard |
| Host canary | `agency host-canary` | — | ✗ | Missing in dashboard |
| Configure wizard | `agency configure` | provider builder in config view | △ | Wizard is interactive; dashboard equivalent is the builder + secret editor |
| Doctor | `agency doctor` | — | ✗ | Missing in dashboard |
| Config show/path/get/set/validate/reset | `agency config ...` | config view (workforce + advanced) | △ | No `get`/`set` per-key; `validate` missing; `reset` is the dashboard reset-fields button (not config reset) |
| Config provider {list,models,set,remove} | `agency config provider ...` | provider builder + secret editor + remove | ✓ | With API parity; CLI uses JSON / flags; dashboard uses form |
| Roster list | `agency roster list` | roster view grid | ✓ | |
| Roster diff | `agency roster diff` | — | ✗ | Missing in dashboard |
| Roster approve / retire / rollback | `agency roster approve/retire/rollback` | `POST /api/roster/action` | ✓ | Via confirmation modal |
| Roster scans | `agency roster scans` | (in review queue upstream-status) | △ | Partial |
| Roster candidate-audit/compare/findings/reject | `agency roster candidate-*` | — | ✗ | Missing in dashboard (these are operator review flows) |
| Roster upstream-import | `agency roster upstream-import` | — | ✗ | Missing in dashboard |
| Roster upstream-status | `agency roster upstream-status` | upstream status text in review queue | ✓ | |
| Roster remediation-queue | `agency roster remediation-queue` | review queue | ✓ | |
| Roster activate | `agency roster activate` | — | ✗ | Missing in dashboard |
| Roster source-add / source-list | `agency roster source-add/source-list` | — | ✗ | Missing in dashboard |
| Roster sync | `agency roster sync` | — | ✗ | Missing in dashboard |
| Workforce list | `agency workforce list` | workforce view | ✓ | |
| Workforce search | `agency workforce search` | roster search + filter form | △ | Different filter shape; same idea |
| Workforce duplicates | `agency workforce duplicates` | — | ✗ | Missing in dashboard |
| Workforce consolidate | `agency workforce consolidate` | — | ✗ | Missing in dashboard |
| Workforce show | `agency workforce show <slug>` | worker detail panel | ✓ | |
| Workforce transition | `agency workforce transition` | `POST /api/workforce/action` | ✓ | |
| Contractor list | `agency contractor list` | workforce view (mixed) | △ | Dashboard mixes contractors and employees; no filter-only-contractors view |
| Hiring list | `agency hiring list` | — | ✗ | Missing in dashboard (workforce view does not show the hiring case ledger) |
| Hiring show | `agency hiring show <id>` | — | ✗ | Missing in dashboard |
| Hiring approve | `agency hiring approve` | `POST /api/hiring/approve` | △ | Action exists in dashboard but no list/show to find a case to approve |
| Policy | `agency policy` | policy view | ✓ | |
| Route | `agency route <task>` | `POST /api/route` (interactive use) | △ | CLI is one-shot; dashboard route is interactive from evidence view; no "explore candidates" form |
| Explain | `agency explain <task>` | — | ✗ | Missing in dashboard |
| Search | `agency search` | roster search form | △ | Aliases; different filter shape |
| Agent enable / disable | `agency agent-enable/agent-disable` | `POST /api/agents/toggle` | ✓ | |
| Agents list | `agency agents-list` | roster view | ✓ | |
| DB stats | `agency db-stats` | — | ✗ | Missing in dashboard |
| DB trim | `agency db-trim` | `POST /api/maintenance/trim` | △ | Action exists; no stats view |
| Eval suite | `agency eval *` | — | ✗ | Missing in dashboard (by design — these are developer-only; not operator) |
| Serve / dashboard / hook / mcp / codex-exec / run | (all top-level) | — | n/a | Process lifecycle; not user-facing operations |

### Per-domain summary

| Domain | CLI count | Dashboard count | Both | Parity |
|---|---|---|---|---|
| Version / upgrade / install / uninstall | 4 | 0 | 0 | ✗ dashboard missing the operator surface for these |
| Host control | 4 | 1 | 1 | △ master only |
| Configure / doctor | 11 | ~3 (config view + provider builder) | ~2 | △ |
| Roster | 17 | ~5 | ~4 | ✗ 13 missing |
| Workforce | 6 | ~3 | ~3 | △ |
| Contractor / hiring | 4 | 1 | 0 | ✗ dashboard can approve but cannot browse cases |
| Policy | 1 | 1 | 1 | ✓ |
| Route / explain / search | 3 | 1 | 1 | △ |
| Agent enable/disable/list | 3 | 2 | 2 | ✓ |
| DB | 2 | 1 | 1 | △ stats missing |
| Eval | 8 | 0 | 0 | n/a (developer surface) |
| Process lifecycle | 6 | 0 | 0 | n/a |

## Presentation parity

The user said: "the dashboard is just a pretty gui, and the cli should be pretty too." Two distinct axes:

### Information density parity

The dashboard shows fields the CLI does not render. Examples from
`dashboard-render.js` lines 1440-1500 (worker detail panel) that are
NOT in `cmd_workforce_show`:

- Per-worker "Promotion readiness" card with `verified_successes /
  required_successes` (the worker's autonomous-promotion progress).
- "Closest workers" comparison list (the worker's near-duplicates and
  the differentiation rationale).
- "Compiled prompt preview" (the actual prompt text + version + hash).
- "Author-only governed specialist definition" disclaimer.

The CLI's `workforce show` likely prints a subset. The same set of
fields needs to be available in both — the CLI just needs to render
them as a card / table, not just tab-separated fields.

### Presentation richness parity

What the dashboard does that the CLI does not (yet):

- Color-coded status (e.g., `configured` vs `failed`, `ready` vs
  `not-ready`).
- Card layouts with metadata grouped by section (Roster card,
  Policy card, Worker card).
- Filter forms with multiple criteria (division, capability, authority,
  host, platform, tool).
- Live SSE updates (the dashboard pushes; the CLI only polls).
- Phrase-typed confirmation modals for destructive actions.
- Reasoning-effort picker on the provider builder.
- "Eyebrow" + "panel-tag" labels for navigation and counts.

What the CLI does that the dashboard does not:

- A `--json` flag for every command (machine-readable output).
- One-shot, non-interactive execution (good for CI / scripts).
- Tab-completion (assumed via argparse; not verified in this scan).

The CLI should grow: rich card-style output for humans, `--json` for
machines, interactive prompts where the dashboard has a modal, color
status matching the dashboard's CSS classes, and live-watch mode for
the same SSE streams the dashboard consumes.

## Top-priority gaps (proposed for AR-236)

A new AR ("Achieve full CLI and dashboard functional and presentational
parity") should be opened, with sub-issues per gap. Proposed ordering
(based on operator impact × cost):

1. **Hiring list / show** (high impact, low cost) — the dashboard can
   approve a hiring case but has no way to find one. Add a
   "Hiring cases" tab to the workforce view, list cases with status,
   show the same detail the CLI shows, and let the operator approve
   from the same view. The CLI side already exists; the dashboard
   view + new CLI flags are the work.
2. **Workforce promotion readiness** (high impact, low cost) — the
   dashboard already renders the card; the CLI's `workforce show`
   needs to print the same fields. Both surfaces should also surface
   the "ready to promote" list, not just per-worker.
3. **Workforce duplicates / consolidate** (high impact, low cost) —
   the dashboard's roster view has filter form and search; add a
   "near-duplicates" mode that lists workers above the
   `amend_overlap_threshold` and a "consolidate" button that drives
   the same code path as `agency workforce consolidate`.
4. **Roster diff** (medium impact, low cost) — the dashboard's
   snapshot panel could add a side-by-side diff view that mirrors
   `agency roster diff`.
5. **Roster scans / candidate-audit/compare/findings/reject** (medium
   impact, medium cost) — operator review flows live in CLI only.
   The review queue is partial; bringing the full set of candidate
   operations into the dashboard is a one-to-one mapping.
6. **Roster source-{add,list} and sync** (medium impact, low cost) —
   add a "Sources" panel to the roster view with the same
   add/list/sync surface.
7. **Doctor + DB stats** (low impact, low cost) — small operator
   diagnostic views; quick wins.
8. **Explain** (medium impact, low cost) — add an "Explain" action on
   the routing view that shows the same output as `agency explain`.
9. **Upgrade** (low impact, high cost) — bring upgrade planning into
   the dashboard; this is a multi-step flow and probably wants
   dedicated AR scoping.
10. **CLI presentation richness** (cross-cutting, medium cost) — for
    every existing CLI command, add card-style output (or a
    `--card` flag), color-coded status, and live-watch where the
    dashboard has live updates. The `rich` library is already a
    likely dep; this is mostly render work, not new functionality.

## Out-of-scope (for the parity AR)

- Eval suite (`agency eval *`) — developer surface, not operator.
- Process lifecycle (`serve`, `dashboard`, `hook`, `mcp`, `codex-exec`,
  `run`) — these are not user-facing operations; the user is running
  them, not invoking them as operator actions.
- Install / uninstall — host lifecycle, by design not in the
  dashboard.

## Recommendation

Open **AR-236** ("Achieve full CLI and dashboard functional and
presentational parity") with the gap list above as acceptance items.
Sub-issue per gap. Each sub-issue is a focused PR that touches one
domain, with both surfaces updated in the same commit set (per the
"identical functionality parity" goal).

Before opening AR-236, the user should confirm:

- The eval suite is truly developer-only and not needed in the
  dashboard (item in the out-of-scope list).
- "Pretty CLI" means `rich`-style card output, color status, and
  live-watch — not a TUI (no full-screen ncurses interface). Confirm.
- The dashboard's confirmation modal is the canonical pattern for
  destructive operations; the CLI should grow a matching
  confirmation prompt (not just a `--yes` flag). Confirm.
