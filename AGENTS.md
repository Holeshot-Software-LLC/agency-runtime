---
title: "Repository Agent Instructions"
status: active
category: governance
created: 2026-07-10
updated: 2026-07-22
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

## Autonomous context handoff

Long-running work must not depend on one chat retaining the entire execution
history. On Codex, check the active thread's local telemetry at the start and
end of every bounded package:

```bash
python scripts/context_handoff_status.py --json --threshold 50
```

At or before half of the active context remains, or earlier when compaction
risk becomes apparent, the active agent must autonomously:

1. Finish the smallest safe in-progress slice and run its proportionate local
   checks.
2. Update the canonical roadmap issue with completed evidence, unresolved
   gates, constraints, and one bounded next work package.
3. Create a local recovery commit and its required worklog ledger commit. Do
   not push merely to create a handoff.
4. Dispatch a fresh Codex task with the exact branch, commits, canonical issue,
   next package, verification commands, and prohibited actions.
5. Wait until the receiving task acknowledges ownership or reports a concrete
   blocker before ending the current task.

Codex Desktop does not inject its UI meter into the model prompt, so the helper
reads the active `CODEX_THREAD_ID` token-count event from the local session log.
If telemetry is unavailable on another host, use a conservative estimate. A
compaction event, an unusually large diff, or declining ability to retain
acceptance criteria triggers the same process. The receiving task must read
this file, the canonical roadmap issue, and the live tracker issue before
editing. It must preserve the prior task's work and must not mark the umbrella
goal complete until every acceptance gate has current evidence.
