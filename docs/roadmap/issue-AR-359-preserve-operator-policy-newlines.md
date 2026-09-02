---
title: "AR-359: config set --stdin flattens operator_policy newlines"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-02
tags: [cli, config, operator-policy]
related:
  - docs/roadmap/issue-AR-355-working-agreements-resident-manager.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-359
priority: p3
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/429
depends_on: []
blocks: []
---

# AR-359: config set --stdin flattens operator_policy newlines

## Problem

`agency config set operator_policy --stdin` parses the piped text as a
YAML scalar, folding the operator's line breaks into spaces. Measured
2026-09-01 setting the owner's five working agreements: a five-line
numbered list was stored and injected as one long line. The
operator-policy module explicitly preserves `\n` because "line
structure is how it stays readable inside the injected block" —
the ingestion path defeats the design.

## Current state

Content survives (numbering keeps it parseable) but formatting the
owner wrote is lost; live capsules show the flattened form.

## Approach

Treat `--stdin` input for string-typed keys as a literal string, not a
YAML document (or wrap it as a YAML literal block before parsing).
Re-set the live installation's policy with its line breaks once fixed.

## Implementation (2026-09-02)

`agency config set <key> --stdin` keeps the piped bytes as one literal
string for every text-valued set path instead of loading them as a YAML
document: `TEXT_SET_PATHS` in `agency_runtime/core/configuration_patch.py`
is a projection of `_SET_VALIDATORS` (every path whose validator accepts
nothing but text, `operator_policy` included), exposed as
`is_text_set_path`; `_literal_stdin_text` in
`agency_runtime/cli/config_commands.py` drops only the single trailing
newline a heredoc or `echo` appends, and the key's own validator still
applies its normalization (`operator_policy` keeps `\n` and `\t`). Every
other path still needs YAML to be typed and keeps the parser. README's
`--stdin` note records the exception. Tests:
`tests/test_cli_config_security.py` and
`tests/test_cli_coverage_complete_config.py` (a five-line policy round-trips
with five lines; a non-text key still parses YAML; the text-path table names
only text-only validators).

## Dependencies

- None.

## Acceptance

- [x] `config set <string-key> --stdin` stores the piped bytes'
      line structure verbatim (modulo the module's own control-char
      normalization), covered by a regression test —
      `test_config_set_stdin_keeps_line_structure_for_text_keys`,
      `test_config_set_stdin_still_parses_yaml_for_non_text_keys`,
      `test_config_set_stdin_is_literal_for_text_keys_and_yaml_otherwise`,
      and `test_text_set_paths_name_only_text_validators`.
- [ ] This installation's operator policy is re-set with its five
      lines intact and verified in a live capsule (the integrator's deploy
      step; the flattened policy is still live until then).
