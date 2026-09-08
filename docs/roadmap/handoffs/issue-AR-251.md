---
title: "AR-251 read-only CLI cards recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, cli, presentation]
related:
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
  - docs/decisions/0154-plain-text-cli-cards-over-rich-dependency.md
  - docs/worklog/2026-09-07-a1d0c965-readonly-cli-cards.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-251
branch: codex/ar251-readonly-cards
evidence_commit: a1d0c965edc8bfb503646dbe318462740911c3d0
minimum_ledger_commit: 869203544685b85877c246e16c47f104b1e068a0
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/260
---

# AR-251 read-only CLI cards recovery capsule

## Checkpoint

Source `a1d0c965` and immediate ledger `86920354` freeze five explicit
read-only card views. Branch-only, verification pending; not accepted,
installed, or done. Current main AR-410/411 source and faithful merge ledgers
were fast-forwarded through `c050be37` before this checkpoint.

## Completed evidence

Source implements `roster list`, `policy`, `config show`, `config get`, and
`config provider list` cards using the existing renderer. Default plain/TTY
output paths remain unchanged; existing JSON branches take precedence.
Config cards consume the original redacted display projection and preserve
explicit `--raw`; provider cards omit direct keys. Disabled roster filtering,
policy validation/exit codes, and empty/error paths remain in place.

Detail truncation is disclosed with a complete-output alternative. New focused
regressions are written but unrun. Parser golden artifact mechanically refreshed
to `281fdc085e51900d93fef7210e104920314831cd0d59e0c59d134246b1f73f3e`.

## Exact blocker

Owner explicitly deferred tests and CI in favor of code implementation.
No acceptance, installed CLI demonstration, or live harness proof exists for
this candidate. AR-251 remains `in_progress`; do not infer satisfaction from
the written tests, formatting, parser-golden regeneration, or source review.

## Same-task continuity

Owned runtime files are `cli/parser.py`, `cli/config_commands.py`, and
`cli/roster_commands.py`; tests are the parser golden and new read-only cards
module. Canonical AR-251, registry row, capsule index, changelog and worklog
carry the implementation boundary. Parent coordinates normal PR publication;
do not touch concurrent source or rewrite incoming history.

## Next bounded work package

Finish parent-coordinated source review and publication with verification
explicitly deferred. Only after the owner resumes verification, run focused
card/parser/config-redaction/policy regressions and demonstrate the exact
installed candidate in isolated read-only fixtures. No broad suite or native
staffing run is needed to implement these presentation flags.

## Verification

Formatting, mechanical parser artifact regeneration, source inspection, and
diff hygiene only. No tests, CI, acceptance models, native calls, providers,
owner configuration reads, installation, or dashboard/service mutation.

## Constraints

No new dependency, automatic TTY change, implicit raw output, mutating wizard,
upgrade control, roster-diff creation change, authenticated model discovery,
live-watch client, acceptance verdict, tracker closure, or done-state flip.
