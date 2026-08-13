---
title: "AR-258: Reconcile the installed projection before any host proof"
status: open
category: roadmap
created: 2026-08-13
updated: 2026-08-13
tags: [install, hosts, evidence, windows, critical-path]
related:
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - agency_runtime/core/store/schema.py
  - agency_runtime/core/installer_native.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-258
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-258: Reconcile the installed projection before any host proof

## Problem

Simulation parity is complete on all five hosts, and no further AR-119 cell can
move without a host artifact bound to the exact candidate. Every remaining cell
is an Installed or Live layer. The installed projection on the evidence machine
cannot produce one: it is staged from two trees that are behind `origin/main`,
fronted by a command-line build that cannot open the Store at all.

This issue scopes that reconciliation. It performs no install action. Every
figure below was measured read-only on 2026-08-13.

## Measured state

**The installed CLI cannot read the Store.** `agency` resolves to the uv tool
at `~/.local/bin/agency`, reports version `0.1.0`, and every Store-backed
command exits with `Agency Runtime database schema is newer than this runtime
(45 > 44)`. Its `agency_runtime/adapters/hooks.py` in the uv tool tree is dated
2026-08-08.

**Three trees own the installed hooks.** The per-host launcher pointers under
`~/.agency-runtime/launchers/` disagree:

| host | staged from | runtime digest | position vs `origin/main` |
|---|---|---|---|
| claude, codex | `C:\Workspaces\Holeshot Software\agency-runtime` | `bb45af11…` | 34 behind, 0 ahead |
| zcode | `C:\Workspaces\Holeshot Software\agency-runtime-jobb2` | `3dd9daf6…` | 42 behind, 0 ahead |
| — | `.codex/worktrees/56b7/agency-runtime` (AR-119) | not installed | 0 behind, 69 ahead |

The session that produced this document was itself running hooks from
`runtime-sha256-bb45af11…`, the 34-behind tree. `~/.claude/plugins/cache/`
additionally holds several `agency-preflight` builds, each pinning a different
runtime digest.

**The master switch is off**, `generation 55`, `source cli`, since
`2026-08-11T22:43:58Z`.

## The constraint that decides the rest

`SCHEMA_VERSION` is **45 on the AR-119 branch and 44 everywhere else** —
`origin/main`, the primary checkout, and `agency-runtime-jobb2` all declare 44.
The shared Store at `~/.agency-runtime/agency.db` has already been migrated to
45 by running branch code against it.

Schema migration is forward-only, so this door has already been walked through.
Installing from `origin/main` or either stale tree would not repair anything: it
would reproduce exactly the error the installed CLI gives today, on every host
instead of only at the command line.

Two further facts bear on the choice and correct an earlier assumption. The Rule
8 fail-open repair **is** on `origin/main` — it is not branch-only, and is not an
argument for the branch. But the AR-119 branch carries roughly 11,300 lines of
runtime change that `origin/main` does not, including the whole native-child
staffing service, the Codex spawn-provenance attestor, and the schema-45
migration itself.

Together these make the choice close to forced, and it is worth stating plainly:
**the matrix requires an Installed or Live artifact bound to the exact candidate
commit.** The candidate is on the branch. An install from `origin/main` could not
bind to it even if the Store allowed it. The genuine decision left to the owner
is therefore not *which tree*, but *whether to merge the branch to `main` first*
so that the code the machine runs is also the code the project ships.

## Decision required before any step below

1. **Merge first, then install from `main`.** The installed code is the shipped
   code, the two stale trees can be refreshed from `main` and stop diverging,
   and the candidate commit for the matrix becomes a `main` commit. Costs a
   review of a 69-commit branch.
2. **Install from the AR-119 branch as it stands.** Unblocks the Installed
   layers immediately and binds artifacts to the current candidate, at the cost
   of the machine running an unmerged branch until the merge happens.

Both need explicit authorization. No install, trust action, or switch change is
taken without it.

## Sequence once a tree is chosen

Ordered, and the order matters: the CLI refresh must precede switching Agency on,
because the Store is already at 45 and an older runtime can never read it.

1. `agency install --agent <host> --dry-run` — documented write-free; read the
   planned roster and host wiring before anything is written.
2. Refresh the uv tool from the chosen tree. A plain `uv tool install --force .`
   silently reuses a cached build, because the version stays `0.1.0`; it reports
   success and leaves the old files in place. Use
   `uv tool install --force --no-cache --reinstall .`
3. Verify the refresh actually happened before trusting it — compare size and
   mtime of the tool's `agency_runtime/adapters/hooks.py` against the repo's.
   Skipping this is why a previous install reported success while `hooks.json`
   kept its old `runtime-sha256-…` pin: the pointer is written by the same stale
   build that generates the hooks, so the two always agree and the SessionStart
   drift warning can never fire.
4. Confirm `agency --version` and a Store-backed command such as `agency status`
   both succeed. If the schema error persists, stop — nothing downstream is
   meaningful.
5. Install per host, one at a time rather than `--all`, so a failure is
   attributable: `agency install --agent claude`, then `codex`, `zcode`, and the
   two remote hosts only on the box that has them.
6. Codex hook trust needs interactive TUI approval; `--verify-activation`
   verifies an already-installed adapter without reinstalling or bypassing
   trust.
7. Turn the master switch on **last**, once every host reads a current
   projection.
8. Start a fresh session per host. Hooks only reload in a new session, so no
   currently open session changes mid-flight and none of the above is visible
   until then.

## Traps already paid for

- **PATH precedence.** Relocating the CLI to `C:\agency-cli` resolved the
  AppData ACE that blocked executables, but npm still wins on PATH order; unless
  the chosen location is prepended, every host reads `native unverified`.
- **The uv cache.** See step 2. This has produced a false clean install twice.
- **Baseline runs rewrite the pointer.** Running the test suite calls
  `record_installed_runtime` and repoints `~/.agency-runtime/launchers/current.json`
  at whichever worktree ran it. It is advisory and cannot redirect a hook, but it
  has generated a false "reinstall first" warning twice. Do not run a suite
  between the install and its verification.

## Verification

- `agency status --json` — one `source_root` for every host, matching the chosen
  tree, and `global: on` only after step 7.
- `agency smoke --agent <host> --json` per host.
- A fresh session per host, confirming no SessionStart drift warning.
- `agency install --agent codex --verify-activation` for the Codex trust path.
- Live Claude proof stays behind `agency host-canary claude --execute --confirm`
  in an isolated profile only, under separate authorization.

## What this unlocks, and what it does not

It unlocks the Installed layer for eight rules across the hosts present on this
machine, and it is the precondition for every Live layer. It does not move Rule
5 Implementation, which needs a source formulation separating starting an agent
from running a tool, and it does not by itself produce any Live artifact: those
need host-written evidence bound to the candidate.

## Rollback

`agency install --rollback --agent <host>` restores the latest retained backup,
and `--backup` selects a specific one. Because hooks reload only in a fresh
session, a rollback is effective for every session started after it and no
in-flight session is disturbed. The Store schema is the exception: it is
forward-only and cannot be rolled back, which is why the CLI refresh is a repair
rather than a risk.

## Acceptance

- [ ] Owner chooses merge-first or install-from-branch, explicitly.
- [ ] One tree owns every per-host launcher pointer.
- [ ] The installed CLI opens the Store and reports a version matching the
      chosen tree.
- [ ] Every host reports a current projection with no drift warning in a fresh
      session.
- [ ] The master switch is on, and its generation is recorded.
- [ ] Tracker creation remains authorization-pending and is not represented as
      present.
