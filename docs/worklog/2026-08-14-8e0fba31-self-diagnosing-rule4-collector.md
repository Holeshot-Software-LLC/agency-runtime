---
title: "Worklog detail: make the Rule 4 collector name the stage that refused"
status: active
category: worklog
created: 2026-08-14
updated: 2026-08-14
tags: [rule4, canary, child-delivery, evidence, diagnosis]
related:
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
supersedes: []
superseded_by: null
type: worklog
commit: 8e0fba3118765fcb29dacecaaf5c4bd1d5147ad7
short: 8e0fba31
date: 2026-08-14
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
---

# Worklog detail: make the Rule 4 collector name the stage that refused

## Purpose

Two live Claude canary runs on 2026-08-14 failed with one line —
`verified host-authored Claude child card delivery was not proven` — and
diagnosing them took a day. `_collect_private_host_child_delivery` answered
eighteen materially different conditions with a bare `None`: a host that spawned
no child, a host that spawned four, a child that received no card, a child that
received a v5 card, an ACL refusal, a stale artifact, and a Store rejection all
looked identical from outside.

That silence is what let the day be spent theorising about a staffing outage
that had been retired on purpose, so the instrument came before more evidence
gathering.

## Approach

`_collect_private_host_child_delivery` now returns `HostChildCollection`, a
frozen pair of the sealed proof and a reason drawn from the closed
`HOST_CHILD_COLLECTION_REASONS` vocabulary. `__post_init__` refuses a reason
outside the vocabulary and refuses a reason that disagrees with the proof, so
`collected` and "there is a proof" cannot drift apart.

The long body was split into three readers that each answer one question and
name their own refusal: `_collected_host_root`, `_sole_window_artifact`, and
`_readable_v6_delivery`. Two distinctions were added deliberately rather than
inherited from the old control flow:

- `artifact_not_trusted` versus `delivery_marker_absent`. The old code called
  `child_delivery_evidence` and could not tell an ACL refusal from a child that
  simply carried no card. Those have opposite fixes.
- `legacy_delivery_not_authoritative` versus `delivery_marker_absent`. A v5
  envelope means a card *was* delivered by an older runtime. Reporting it as "no
  marker" sends the next reader hunting a staffing outage that is not there —
  the exact trap this repository fell into a day earlier.

The canary backend stamps `host_child_collection_reason` onto its record, and
the Rule 4 failure line quotes it, so the reason reaches
`unmet_prerequisites` where an operator actually reads it.

**The gate itself is unchanged.** `multiple_child_artifacts` still refuses:
"the artifact this invocation wrote" has no single answer when a host fans a
task out to four children, and relaxing that binding is a threat-model change,
not a refactor. The change is only that a fan-out no longer reads the same as a
host that spawned nothing.

## Challenges encountered

Two hypotheses were tested and disproven before the real localisation, and both
are recorded because each was plausible enough to build on.

**`--setting-sources=` suppresses the plugin's hooks.** The canary passes it to
keep the owner's settings out of the disposable profile. Tested against a fresh
home with `--plugin-dir`: empty sources, default sources, and
`--setting-sources=user` — **all three produced zero Agency markers.** Not the
cause.

**The plugin is available but not enabled.** The real profile enables Agency
through `~/.claude/settings.json` (`enabledPlugins` plus
`extraKnownMarketplaces`), and the canary's fresh home has no settings file at
all. Tested with those keys present, then again with the real profile's
`installed_plugins.json` and `known_marketplaces.json` copied in — **both
produced zero markers.** Also not the cause.

Six combinations, no activation — which left the isolated profile itself as the
remaining suspect, and that framing was also wrong.

**The control settles it, and it supersedes both hypotheses above.** Running
`claude -p` against the *real* profile — the same `~/.claude` whose hooks fire
for an interactive session, no `CLAUDE_CONFIG_DIR` override — produced a
sub-agent child with no Agency marker, no AGENCY text anywhere in the parent
transcript, and zero Agency rows: `runs: 0`, `routing: 0`,
`preflight_failure_receipts: 0`. The hook did not decline; **it never ran**.
Repeated with every inherited `CLAUDE_CODE_*` variable stripped, including
`CLAUDE_CODE_CHILD_SESSION` — a fair confound for any measurement taken from
inside a Claude Code session, and worth testing rather than assuming — with the
same result.

Eight runs, two profiles, zero markers, while interactive sessions on the same
machine staff normally at confidence 1.0. **`claude -p` does not run the Agency
plugin's hooks, and the profile was never the variable.** The Claude canary is
built on `-p`, so it cannot produce Rule 4 Live evidence in its present shape.
That is structural, not a configuration defect.

A third finding fell out of reading `evidence_summary` while chasing the above:
`routing` and `loaded_specialists` are filtered by the canary's own query hash,
but `counts.specialists` is unfiltered and `counts.runs` is filtered only by
host and status. On a workstation whose own Claude session writes the same
store, those two counts absorb activity that was never the canary's. An earlier
matrix paragraph quoted `specialists: 6` and `runs: 2` as canary measurements;
they are upper bounds, and the matrix now says so.

## Decisions and alternatives

**Rejected: relaxing `candidate_count == 1` to "exactly one artifact verifies".**
Tempting, because a live run produced four children and the collector refused
all of them. But the single-artifact rule is what binds the proof to this
invocation unambiguously in a namespace that was empty beforehand. Loosening it
is a threat-model decision for the owner, not a side effect of adding
diagnostics. Recorded in the matrix instead.

**Rejected: carrying the verification reason through verbatim.** Reasons travel
into evidence, so an unbounded string is a liability. Four verification reasons
that already name their own stage are promoted by whitelist; everything else
collapses to `verification_refused`.

**Rejected: writing the reason only into the log.** The reason is exactly what a
future reader needs and a log line is not durable evidence, so it goes into the
canary record and the operator-facing failure list.

## Verification

- `tests/test_child_delivery_evidence.py`, `tests/test_rule4_card_delivery_end_to_end.py`,
  `tests/test_host_canary.py` — all pass. Four new tests cover the closed
  vocabulary, the fan-out case, the no-card case, and the v5 case; a fifth
  covers the failure line quoting the reason and ignoring an unusable one.
- `tests/test_child_delivery_evidence.py` joins CI's AR-119 matrix-evidence
  step, and the matrix cites it, which `tests/test_release_packaging.py`
  enforces in both directions.
- Two live isolated-profile Claude canary runs after the change both report
  `host_child_collection_reason: delivery_marker_absent` and the failure line
  `verified host-authored Claude child card delivery was not proven
  (delivery_marker_absent)`.
- `verify_docs.py` (687 files), `docs_metadata.py --check`,
  `update_policy_availability.py --check`, `ruff check`, `ruff format --check`,
  `node --test tests/dashboard_ui.test.mjs`, `agency eval routing`,
  `agency eval spawn-authority`, and the full matrix-evidence list.

## Follow-ups

- **`claude -p` runs no Agency hooks**, so the canary's whole surface cannot
  produce Rule 4 Live evidence
  ([AR-119](../roadmap/issue-AR-119-inference-first-workforce.md)). Either
  headless mode is made to run hooks, or Rule 4 is collected from an
  interactive surface. This is now the top Rule 4 blocker, and it is a design
  question rather than a bug to chase.
- **No v6 envelope has ever been written on the evidence workstation** — 63
  child artifacts, 3 v5, 7 v1, 0 v6. The installed launcher does carry the v6
  renderer, so one child spawned from an *interactive* session would settle
  whether delivery works at all today. That needs the owner's hands.
- The AR-252 envelope collector is unstarted, and its fourth constraint — the
  verdict must bind a transcript digest no verifier child can read — is recorded
  in [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md)
  and should be settled before the build.
