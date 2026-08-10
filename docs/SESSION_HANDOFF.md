---
title: "Session handoff — rule 4 evidence"
status: active
category: documentation
created: 2026-08-10
updated: 2026-08-10
tags: []
related: []
supersedes: []
superseded_by: null
---
# Session handoff — rule 4 evidence

Durable engineering state for picking this work up cold. Machine-specific setup (host CLI
locations, permissions, auth state) is deliberately **not** here — it is operator-local and lives in
the working handoff outside the repo.

## Where the product stands

Agency reads what was just asked, pulls the right specialist card(s) from the roster, and hands
them to whoever is about to do the work — the generalist, or any sub-agent the harness spawned on
its own initiative. The specialist works inside the existing conversation. Agency never decides to
spawn; that is the harness's call.

**Rule 4 — "harness-spawned children get cards, plural" — is the one open rule, and it is the
differentiator.** A dynamic specialist system that also covers the harness's own sub-agents is the
novel claim. As of this handoff it is *built and instrumented but never once observed working in
production*.

| layer | what it proves | state |
|---|---|---|
| L1 | the JIT staffing path works against the real Store and roster | done — 21 tests |
| L3 | the child *received* the card, per the host's own artifacts | **done — this handoff** |
| L2 | a real harness spawning a real child, end to end | not yet run |

## What shipped here

- **`core/child_delivery_evidence.py`** — reads the transcript the *host* wrote for a child and
  reports which cards provably arrived. A `specialists_loaded` row proves only that Agency *tried*,
  because the same code under test writes it; the host's own artifact is the only independent
  evidence. Pure read: no writes, no network, no Store, so it needs no rewritable launch seam.
- **`core/host_wiring_drift.py`** — compares what a host actually invokes against what the
  installer staged. Exits non-zero on drift, so it gates a live observation.
- **`core/bounded_io.py::read_bounded_regular_file_prefix`** — the existing reader rejects a file
  larger than its limit, which is right for whole-file trust and wrong for a multi-MB transcript
  read only for its opening records.
- **Claude plugin version is now derived from bundle content** (`0.1.0+claude.<digest>`), mirroring
  `render_codex_plugin_version`, which Codex always had. A pinned version made both
  `plugin install` and `plugin update` no-op against a changed bundle.
- **CLI provider failures now say why.** Resolution failures were all reported as "executable not
  found", including executables that were found and *refused*.

CLI surface: `agency evidence children [--host claude|codex]`, `agency evidence wiring`.

## Two rules the design depends on

**A card counts only if it reached the child before the child first spoke.** A marker later in a
transcript is the child *reading about* Agency — grep output, a file it opened. In this repository
that false positive is not hypothetical. `tests/test_child_delivery_evidence.py` names it.

**Independence comes from cross-checking two writers.** The envelope's `parent_session_id` is
written by Agency; the parent id in the transcript is written by the host. Nothing coordinates them,
so their agreement is the evidence.

## Verifying it

```bash
uv run --no-sync agency evidence wiring          # exit 1 = you are about to observe the wrong code
uv run --no-sync agency evidence children --host claude
```

First scan across 1,225 real child artifacts found **17 provable deliveries** (6 Claude sub-agent
transcripts, 11 Codex child rollouts), every one hash-verified and correlated — but all of them
legacy envelopes from the deleted planned-delegation path. **Zero JIT deliveries have ever been
observed.** That is an empty data window rather than evidence the path is broken: Agency has been
off since the JIT path shipped.

## Artifact locations

| host | child artifact | child identity |
|---|---|---|
| claude | `<claude-config>/projects/<slug>/<parent-session>/subagents/**/agent-<id>.jsonl` | record 0, `type=user`, `isSidechain=true` |
| codex | `<codex-home>/sessions/YYYY/MM/DD/rollout-*-<thread>.jsonl` | record 0 `session_meta` with `source.subagent.thread_spawn` |

Claude writes each sub-agent its own file — that is what makes the Claude side cheap. Both hosts'
directories pass the storage-trust checks unchanged.

## Known open

- **L2 has never been run.** It needs a host with working inference and granted hook trust, and a
  session started *after* the install — hooks pin their runtime at session start.
- **`host_wiring_drift` covers Claude only.** Its staged and cached paths are measured facts;
  guessing another host's path would produce a confident "wired" from a file that does not exist.
  Each further host is one table entry once its path is observed.
- **`child_delivery_evidence` covers Claude and Codex only.** A pure read path is the only rule-4
  evidence obtainable on hosts with no rewritable launch seam, so extending it is the point.
- **Contractors have no review/revoke CLI** — `agency contractor` is `list`/`show` only.

## Test baseline

Diff the failure-ID **set**, never the count. At the time of writing: **131 failed / 8441 passed**,
unchanged as a set across this work.

```bash
uv run pytest -q -p no:randomly --ignore=tests/test_platform_wheel.py -rf --tb=no
```

`--ignore=tests/test_platform_wheel.py` is required; it fails to collect and aborts the run.
Several tests read repo files from disk, so use a separate worktree for a concurrent run rather
than editing mid-run. After deleting any public-ish symbol, run `pytest --collect-only -q` first —
a module-scope import of a deleted symbol aborts the whole suite with no failure list.
