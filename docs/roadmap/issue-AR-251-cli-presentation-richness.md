---
title: "AR-251: CLI presentation richness (sub-issue 10 of AR-236)"
status: in_progress
category: roadmap
created: 2026-08-04
updated: 2026-09-07
tags: [cli, dashboard, parity, presentation, card, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/decisions/0154-plain-text-cli-cards-over-rich-dependency.md
  - agency_runtime/cli/_render.py
  - agency_runtime/cli/workforce_commands.py
  - agency_runtime/cli/parser.py
  - agency_runtime/cli/config_commands.py
  - agency_runtime/cli/roster_commands.py
  - tests/test_cli_readonly_cards.py
  - docs/roadmap/handoffs/issue-AR-251.md
  - docs/worklog/2026-09-07-a1d0c965-readonly-cli-cards.md
  - docs/worklog/2026-09-07-54bdff1f-governed-card-defaults.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-251
priority: p2
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/260"
depends_on: []
blocks: []
---

# AR-251: CLI presentation richness (sub-issue 10 of AR-236)

## Problem

The CLI output is tab-separated text. The dashboard renders cards with
grouped metadata. The user asked for the CLI to be "pretty too."

## Current state

- AR-237 introduced `agency_runtime/cli/_render.py` with a plain-text card
  layout (dividers, tab-aligned fields, sections) and a `--card` flag for
  hiring commands.
- ADR-0154 records the decision to use plain-text cards over a `rich`
  dependency (zero-dependency install property).
- September 7 source `54bdff1f`, immediate ledger `a6c34707`, adds the five
  read-only views below, correcting initial `a1d0c965` to follow ADR-0154's
  automatic TTY behavior. This is a branch source checkpoint, not
  installed delivery or verified acceptance. Tests are written but unrun at
  the owner's code-first/defer-tests-and-CI direction; status stays
  `in_progress`, with the original checkbox states preserved.

| Command | Card projection | Compatibility boundary |
|---|---|---|
| `agency roster list --card` | One card per enabled row | Same enabled filter; non-TTY/`--no-card` tab-separated output unchanged |
| `agency policy --card` | Summary, action and division cards | Existing validation/exit code; `--json` wins unchanged |
| `agency config show --card` | One card per top-level display section | Uses existing redacted YAML projection; `--raw` only when explicitly requested |
| `agency config get KEY --card` | One existing redacted display value | Same missing-key error/exit and explicit `--raw` behavior |
| `agency config provider list --card` | Ordered public provider fields | Existing direct-key omission; `--json` wins unchanged |

All five views use the existing `use_card_default` policy: automatic cards on a
TTY, plain output otherwise, explicit `--card`/`--no-card` overrides, and JSON
precedence where supported. Existing hiring/workforce behavior is unchanged.
The first source checkpoint's explicit-only default was corrected during review;
it is historical, not a new ADR exception. Card fields visibly ellipsize;
bounded detail sections report truncation and point to `--no-card` or existing
`--json` for complete output. No presentation
dependency, color system, live-watch client, wizard, mutation command,
authenticated model discovery, or extra owner-state read was introduced.

## Approach

The earlier slice added `workforce list`; hiring already had cards from AR-237.
The current slice extends exactly the five read-only views above, reusing
`_render.py` and the existing public/redacted data paths. Broad parity remains
AR-236; upgrade controls remain AR-250, not implicit work in this slice.

## Dependencies

- Existing ADR-0154 plain-text renderer and unchanged output/redaction contracts.
- Parent-coordinated source review/publication; no new tracker or authority policy.

## Verification boundary

`tests/test_cli_readonly_cards.py` covers parser overrides and mutation refusal,
automatic TTY cards, non-TTY/explicit plain bytes, JSON precedence, enabled-roster filtering, config
scalar/nested redaction and explicit raw output, empty/error paths, policy
validation, and truncation disclosure. These regressions have **not run**.
The existing whole-parser golden was mechanically regenerated to
`ca0221ef36d806dc4bf86dcf53136b7d5c3553e135c2eb284bac32b4a6ef9863`,
without executing test functions. Formatting and `git diff --check` are artifact
maintenance, not a passing test result. No CI, acceptance verifier, live CLI,
host canary, provider call, or installation was run for this source package.

## Acceptance

- [x] ADR-0154 records the plain-text card decision.
- [x] `workforce list --card` renders one card per worker.
- [ ] Extending `--card` to remaining commands (roster, policy, config) is
      an incremental follow-up; the rendering infrastructure is in place.
