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
  - docs/worklog/2026-09-07-54bdff1f-governed-card-defaults.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-251
branch: codex/ar251-readonly-cards
evidence_commit: 54bdff1f2ac3044bb0931ca4202a2320059a6f47
minimum_ledger_commit: a6c34707ab4daf598f8bc7a4fa57ed421a0ea196
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/260
---

# AR-251 read-only CLI cards recovery capsule

## Checkpoint

Source `54bdff1f` and immediate ledger `a6c34707` freeze five read-only card
views with ADR-0154 automatic TTY defaults and explicit overrides. The initial
`a1d0c965` explicit-only default was corrected during review. No new ADR or
presentation-policy exception remains. Published through PR #753. The owner
ended test deferral for delivery; focused card tests now pass 61 cases after
correcting one test-only whole-card byte-limit assumption. Not accepted or done.

## Completed evidence

Source implements `roster list`, `policy`, `config show`, `config get`, and
`config provider list` cards using the existing renderer and `use_card_default`.
Non-TTY and explicit `--no-card` plain output remain unchanged; TTY defaults to
cards, and existing JSON branches take precedence over both default and explicit cards.
Config cards consume the original redacted display projection and preserve
explicit `--raw`; provider cards omit direct keys. Disabled roster filtering,
policy validation/exit codes, and empty/error paths remain in place.

Detail truncation points to `--no-card` or existing `--json` for complete output. New focused
regressions now pass. Parser golden artifact was mechanically refreshed
to `ca0221ef36d806dc4bf86dcf53136b7d5c3553e135c2eb284bac32b4a6ef9863`.

## Exact blocker

Installed CLI demonstration and isolated acceptance remain outstanding.
AR-251 remains `in_progress`; source tests are not native staffing proof.

## Same-task continuity

Owned runtime files are `cli/parser.py`, `cli/config_commands.py`, and
`cli/roster_commands.py`; tests are the parser golden and new read-only cards
module. Canonical AR-251, registry row, capsule index, changelog and worklog
carry the implementation boundary. Parent coordinates normal PR publication;
do not touch concurrent source or rewrite incoming history.

## Next bounded work package

Parent publishes the test-only correction in the final delivery branch and
demonstrates the exact installed candidate in isolated read-only fixtures.

## Verification

Focused card tests: 61 passed in 0.42 seconds after a test-only correction.
The earlier combined run had 1 failed, 371 passed and 1 skipped; its failure
compared UTF-8 card decoration plus content against a nonexistent whole-card
limit. The corrected assertion proves the actual bounded value/line. Runtime
renderer unchanged; no native or acceptance claim.

## Constraints

No new dependency, TTY policy outside ADR-0154, implicit raw output, mutating wizard,
upgrade control, roster-diff creation change, authenticated model discovery,
live-watch client, acceptance verdict, tracker closure, or done-state flip.
