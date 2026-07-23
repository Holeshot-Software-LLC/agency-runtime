---
title: "Repository Agent Instructions"
status: active
category: governance
created: 2026-07-10
updated: 2026-07-23
tags:
  - governance
  - documentation
related:
  - docs/roadmap/README.md
  - docs/worklog/README.md
  - docs/decisions/README.md
  - CONTRIBUTING.md
  - CODE_OF_CONDUCT.md
  - SECURITY.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
---

# Repository Agent Instructions

These instructions apply to the entire repository. Product behavior belongs in
the Python package; durable project context belongs in the documentation system
below.

## Documentation map

| Area | Canonical location | Purpose |
|---|---|---|
| Project overview | [README.md](README.md) | Installation, behavior, architecture, and public reference |
| Planning | [docs/roadmap/README.md](docs/roadmap/README.md) | Internal issue registry and tracker mapping |
| Context checkpoints | [docs/roadmap/handoffs/README.md](docs/roadmap/handoffs/README.md) | Bounded recovery capsules for long-running work |
| Change reasoning | [docs/worklog/README.md](docs/worklog/README.md) | Exact Git history index and reasoning-rich commit notes |
| Durable decisions | [docs/decisions/README.md](docs/decisions/README.md) | Canonical ADR registry and superseding chains |
| Contributor workflow | [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup, implementation boundaries, and validation |
| Security | [SECURITY.md](SECURITY.md) | Vulnerability reporting, threat boundaries, and hardening |
| Threat model | [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) | Assets, trust boundaries, enforced controls, and residual risks |
| Release history | [CHANGELOG.md](CHANGELOG.md) | User-visible unreleased and versioned changes |
| Operations help | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Host maturity, MCP, LiteLLM, dashboard, and platform diagnostics |
| Release gate | [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) | Support evidence, security, artifact, and publication checklist |

Each category owns its own `archive/` when retirement becomes necessary. Do not
create a global archive.

## Non-negotiable record discipline

The planning, tracker, Git, and decision records are one system. Do not complete
a change while knowingly leaving one of its required records behind.

### Features, enhancements, and bugs

Whenever a session surfaces a new feature, enhancement, or bug:

1. Allocate the next stable `AR-NN` internal ID. It never changes and never
   derives from a tracker-assigned number.
2. Create `docs/roadmap/issue-AR-NN-slug.md` with Problem, Current state,
   Approach, Dependencies, and Acceptance sections.
3. Add the item and its epic to `docs/roadmap/README.md`.
4. Create one same-repository tracker issue titled `[AR-NN] <title>` and label
   it `epic:<slug>`.
5. Write the tracker URL into the issue document and the registry mapping table.
6. Put governing decision paths in the issue document's `related` list and add
   the issue path back to each decision record.

Obtain any authorization required for an outward-facing tracker write. Lack of
authorization is a visible blocker to report, not permission to omit the local
record or pretend tracker parity.

### Commits and worklogs

Every substantive commit must have one exact row in
`docs/worklog/README.md`: short SHA, date, unmodified subject, related internal
issue, and an optional detail link. When a commit carries reasoning that its
subject cannot hold, add a detail file from `docs/worklog/TEMPLATE.md` covering
the approach, challenges, decisions or alternatives, and follow-ups. Include
the PR URL and related issues in its front matter.

Roadmap records link to implementation commits through the roadmap traceability
table. Decision records cite the relevant short SHAs and link back to both the
roadmap record and worklog registry through `related`.

A commit cannot contain its own SHA. Therefore the immediately following
ledger-maintenance commit records the preceding substantive commit. A commit
whose only purpose is updating `docs/worklog/**` and the reciprocal commit cell
in `docs/roadmap/README.md` must use the exact subject prefix `docs(worklog):`
and is exempt from requiring another row. No other paths are allowed in that
commit. Without this narrow exception, a clean repository would require an
infinite chain of self-recording commits.

Never rewrite a faithful historical subject to remove an old name or reference.
Preserve it exactly and add a provenance note if context is needed.

### Durable decisions

Every durable architectural, product, security, data-governance, or operating
decision requires:

1. The next file in the single `ADR-NNNN` number space under `docs/decisions/`.
2. Context, Decision, Consequences, and Alternatives sections.
3. A row in `docs/decisions/README.md`, grouped by area.
4. Reciprocal `supersedes` and `superseded_by` fields whenever a decision
   replaces another decision.

Weight changes detail, not numbering. Rejected, deprecated, and superseded
decisions remain in the canonical registry.

## Metadata and validation

Every maintained Markdown file starts with YAML front matter. Add missing
metadata with:

```bash
python scripts/docs_metadata.py
```

The writer skips any file that already starts with `---`. Before handoff, run:

```bash
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/ -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
git diff --check
```

After approved tracker creation, also run
`python scripts/verify_docs.py --require-tracker` and
`python scripts/verify_tracker.py`.

The strict tracker check fails when a locally complete item remains open. If
closure authorization is the only missing action, use
`python scripts/verify_tracker.py --allow-open-complete` for a read-only parity
audit; it still fails count, ID, URL, label, and all other state mismatches and
prints every authorization-pending closure as a warning. Release validation
remains strict.

For packaging or release-facing changes, also follow
[docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md). A deterministic host
contract is not a live runtime canary: keep discovery, registration, enablement,
loading, and canary claims separate in documentation and release evidence.

## Repository boundary

Documentation must be usable from this repository alone. Do not link to or
depend on sibling repositories, sibling filesystem paths, or external generated
indexes. Bring a small neutral example into this repository when documentation
needs one. Product and protocol names that describe actual supported behavior
may remain.

Do not alter faithful historical records merely to neutralize wording. Flag the
historical reference alongside the record instead.

## Context gates and clean checkpoints

Long-running work must not depend on one prompt retaining the entire execution
history. Every long-running roadmap item uses one active recovery capsule under
`docs/roadmap/handoffs/`. The capsule is a bounded current-state projection,
not a second roadmap or append-only transcript. `scripts/verify_docs.py`
enforces one active capsule per issue, required recovery sections, a maximum of
12 KiB and 180 lines, and the fixed 50-percent hard checkpoint and 65-percent
live-evaluation admission gates.

On Codex, run telemetry after bounded bootstrap, immediately before every live
evaluation, and at the end of every bounded package:

```bash
python scripts/context_handoff_status.py --json --threshold 50 --admission-threshold 65
```

The helper reads the newest cumulative token-count event. Normal Codex
compaction may not reset that cumulative value, so never wait or emit an empty
continuation hoping the percentage will rise.

Apply the gates as follows:

- At or above 65 percent remaining, a new expensive live evaluation may start.
- Below 65 percent, do not start any new expensive live evaluation. A
  conditional rerun or complete corpus is a separate evaluation and requires a
  fresh immediately-preceding telemetry check.
- At or below 50 percent, first finish the smallest safe in-progress slice,
  run proportionate checks, and create a clean durable substantive/ledger
  checkpoint. Then continue in the same task. Because this is below the
  65-percent gate, only non-live work may start until the current task again
  has an admissible reading.

At each hard checkpoint, update the canonical roadmap and active capsule with
exact evidence, unresolved gates, constraints, and one next bounded package,
then create the local recovery and ledger commits. Continue the current task
through normal Codex behavior, including compaction when it occurs.

The thresholds never authorize or require creating, forking, dispatching, or
waiting for another task. They also never require pausing or transferring a
persistent goal, recording a task owner, acknowledging a receiver, or stopping
for user action. Cross-task coordination is outside this context protocol.
A read-only preflight with no substantive delta never creates a telemetry note
or empty recovery/ledger pair; it reuses the existing checkpoint.

Codex Desktop does not inject its UI meter into the model prompt, so the helper
reads the active `CODEX_THREAD_ID` session record. If telemetry is unavailable,
use a conservative estimate. Preserve prior work and do not mark an umbrella
item complete until every acceptance gate has current evidence.
