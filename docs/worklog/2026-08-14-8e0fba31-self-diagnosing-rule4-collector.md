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
suspect. Running `claude -p` against the *real* profile ruled that out too: no
marker, no AGENCY text in the parent transcript, `runs: 0`, `routing: 0`,
`receipts: 0`. Repeated with every inherited `CLAUDE_CODE_*` variable stripped,
including `CLAUDE_CODE_CHILD_SESSION` — a fair confound for any measurement
taken from inside a Claude Code session — with the same result. Nine runs, two
profiles, zero markers.

**That was then read as "the hook never runs under `-p`", which was wrong, and
the error is worth naming precisely: zero Agency rows is equally what a hook
that never started and a hook that started and failed open both produce.**
Agency fails open by design, so absence of its evidence cannot distinguish the
two. The next probe supplied a *trivial* hook with an observable side effect
through `--settings`: it fired on all five of `SessionStart`,
`UserPromptSubmit`, `PreToolUse`, `SubagentStart` and `Stop`. Hooks run fine.

Wrapping Agency's own hook command in a shim that logs stdin, stdout, stderr and
exit code then gave the real answer on the first run, identically on every
event:

~~~text
RuntimeError: Agency Runtime database schema is newer than this runtime (46 > 45)
agency hook claude: RuntimeError; host operation continues
~~~

**The break is this commit's own.** The live store is at schema 46, this
checkout is at 46, and the pinned launcher every hook executes is at 45. The
AR-252 work raised `SCHEMA_VERSION`, and running checkout-local CLI commands
(`agency host-canary`, `agency eval …`) against the real
`~/.agency-runtime/agency.db` migrated it past what the installed launcher
accepts. `Store.__init__` refuses, the boundary fails open, the host proceeds
uncarded — and `Stop` fails *closed*, returning the "could not verify or persist
the turn-scoped evidence contract" block that interrupted the operator's own
session.

The evidence store stops dead at `2026-08-14T23:15:24Z`: newest `runs`,
`routing_decisions`, `preflight_failure_receipts` and `specialists_loaded` rows
all share that boundary. **Every zero-marker measurement after it — both canary
runs and all nine host probes — describes this break and says nothing about
`-p`, profiles, or card delivery.**

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
- `verify_docs.py` (688 files), `docs_metadata.py --check`,
  `update_policy_availability.py --check`, `ruff check`, `ruff format --check`,
  `node --test tests/dashboard_ui.test.mjs`, `agency eval routing`,
  `agency eval spawn-authority`, and the full matrix-evidence list (670 passed).
- `tests/test_doctor.py` gains two cases for the drift that hid this: a store
  ahead of the runtime now fails the `db_schema` check with the reinstall
  remedy, and a store behind it warns. Previously the check only asserted that a
  version row existed, which is why it showed a green `Schema version: 46` while
  that same runtime was refusing that same store.

## Follow-ups

- **The evidence workstation needs a reinstall** so the launcher its hooks run
  matches the store this work migrated. Until then every hook fails open and no
  Rule 4 measurement on that machine means anything
  ([AR-119](../roadmap/issue-AR-119-inference-first-workforce.md)). Installing
  needs the owner's authorization.
- **A schema bump is not a local change** when a checkout shares its store with
  an installed runtime: it disables staffing machine-wide until the launcher is
  refreshed. Worth sequencing deliberately, and arguably worth a guard that
  refuses to migrate a store an older installed launcher still points at.
- **No v6 envelope has ever been written on the evidence workstation** — 63
  child artifacts, 3 v5, 7 v1, 0 v6, and zero
  `native_child_delivery_verifications` rows. That census stands; the reason
  does not follow from it. One child spawned from a repaired runtime settles
  whether v6 delivery works at all today.
- The AR-252 envelope collector is unstarted, and its fourth constraint — the
  verdict must bind a transcript digest no verifier child can read — is recorded
  in [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md)
  and should be settled before the build.
