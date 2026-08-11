# CLI re-scope: the keep-list, derived from the founding vision

Date: 2026-08-11. Companion to the dashboard re-scope (Codex, separate worktree).

Lucas's rule for this pass: **if it is not part of the vision it needs to go.** The default
for a surface with no vision justification is removal, not a refactor. This document records
the keep-list, what fell outside it, and — importantly — the two things that *looked* like
they fell outside and did not.

The vision is the memory `agency-runtime-founding-vision`, confirmed 2026-08-07 and sharpened
2026-08-11. Rule numbers below refer to it.

## Method

Every top-level command was tested against one question: **which numbered rule does this
serve?** Not "is it used", not "does it have tests", not "does it still work" — the vision
memory is explicit that reachability is the wrong instrument, because the code is full of
dead bodies that still run.

A command that serves no rule is deleted even if it works. A command that serves a rule under
a misleading name is renamed, not deleted.

## Keep — with the rule each one serves

| Command | Rule |
| --- | --- |
| `install`, `uninstall`, `upgrade`, `version`, `sync`, `source` | 9 — parity is the claim; these put one runtime on five hosts |
| `on`, `off`, `status`, `doctor`, `host-canary` | 8 — "if it can't help, get out of the way" needs a switch and a readiness check |
| `configure`, `config *` | 1 — inference-based selection requires a reachable inference endpoint |
| `roster *`, `agents *`, `search`, `workforce *` | the ~280-card cabinet rule 1 selects from |
| `contractor *`, `hiring *` | 6 — mint a card, interview it for safety, file it in the pool |
| `workforce duplicates`, `consolidate`, `merge`, `amend` | "contractors must dedupe" (refinement, 2026-08-07) |
| `policy` | 3 — multiple cards are allowed *when they don't conflict*; this is the conflict declaration |
| `route`, `explain` | 1 — a selection nobody can audit is not a selection anyone can trust |
| `evidence children` | **4** — the only proof of the differentiator: that harness-spawned children got cards |
| `evidence rejections` | 8 — named verbatim in the sharpened rule |
| `evidence intent` | "selection comes from INTENT, not keywords" (2026-08-08) |
| `evidence latency` | 8 — "complements and never blocks" is a number, not an intention |
| `evidence wiring` | 9 — proves each host invokes the projection the installer staged |
| `mcp`, `hook` | the two ways a card actually reaches a host |
| `db stats`, `db trim` | retention for a content-free evidence store |
| `eval *` | not product surface, but the evidence AR-119's claims are met |

## Removed

**`agency delegate`** — the last live surface of Job B. It selected a backend
(`CodexExecBackend`, `ClaudeExecBackend`, `HermesDelegateBackend`, `OpenClawAgentBackend`,
`GenericCLIBackend`), spawned it, and waited for a result. Rule 5 is one sentence: *Agency
never decides to spawn.* The 2026-08-09 deletion removed Job B from the hook path — planning,
one-use tokens, receipts, denial — and this survived it because nothing in that pass walked
the CLI. Deleting it took `cli/delegation_commands.py` with it.

**`agency run`** — "Run an arbitrary command", a passthrough to `subprocess`. No vision anchor
at all. It is also an arbitrary-execution surface on a binary that gets installed into five
agent hosts, which is a reason to want it gone independent of scope.

**`agency codex exec`** — proxied `codex exec <args>`. A per-host branch with no host-parity
twin, which rule 9 calls a smell to justify; the justification was that it is `agency run` with
a hardcoded prefix.

## Kept after a second look — the two near-misses

**`agency eval delegation` is not Job B.** The name says delegation; the suite exercises all
five adapters recording the same evidence for an identical turn — skills loaded, specialists
loaded, a delegation *the host itself chose to make*, and a model receipt. That is rule 9
(parity) and rule 5 done correctly (the host spawns, Agency observes). It never spawns
anything. Renamed to **`agency eval host-parity`** (`core/evals/host_parity.py`) so the surface
stops reading as the thing it is the opposite of.

**`core/delegation/` is not deletable as a package.** `run_bounded_process` is the installer's,
the canary's, and the codex hook-trust inspector's subprocess primitive; `events.suggested_delegations`
is on the live hook path; `native_labels` is used by child-prompt delivery; `lifecycle_git.run_git`
is used by the update service. The package name is a historical accident, not a statement of
what is in it.

## Deliberately deferred

**The Job B machinery still exported from `core/delegation/__init__.py`** — `delegate_with_lifecycle`,
`dispatch_work_units`, `provision_worktrees`, `cleanup_worktrees`, `DependencyGraph`, `WorkUnit`,
`DelegationLedger` (~3,400 lines across `lifecycle*.py`). With `agency delegate` gone, the only
remaining consumers are `core/evals/routing.py` and `server/dashboard.py`.

This was not touched in this pass for one reason: **`server/dashboard.py:1197` imports
`delegation.lifecycle`, and Codex is editing the dashboard in a worktree right now.** Pruning it
here would collide head-on. It is the natural next package once the dashboard re-scope lands, and
it should be judged by the same question — a worker pool with git worktrees is Job B whether or
not a CLI command points at it.

## Judgment calls left open

- **`agency serve`** — an HTTP JSON control plane (`/preflight`, `/explain`, `/finalize`,
  `/status`, `/roster`, `/search`). No host consumes it; cards reach hosts via hooks and MCP.
  It shares infrastructure with the dashboard, so it belongs to the dashboard decision, not this one.
- **`agency smoke`** — deterministic local checks. Overlaps `doctor` + `host-canary` +
  `evidence wiring`. A dev tool, not a product surface; harmless, but it is the kind of thing
  that accretes.
- **`agency hook` accepts only `codex`, `claude`, `zcode`** (`cli/parser.py`). Hermes and
  OpenClaw cannot be hooked from the CLI at all. Under rule 9 that is a parity gap, not a
  trade-off — noted here because the re-scope surfaced it, not because this pass fixed it.

## Effect

Command paths in the golden parser manifest: 109 → 106. Three top-level commands and one
subcommand removed, one subcommand renamed. `agency_runtime/cli/` lost 420 lines
(`delegation_commands.py`); the test suite lost ~500 lines covering it.
