---
title: "Owner-run verification packet for openclaw and hermes"
status: active
category: roadmap
created: 2026-08-16
updated: 2026-08-16
tags: [roadmap, verification, hosts, openclaw, hermes, AR-119]
related:
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-overnight-report.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# Owner-run verification packet for openclaw and hermes

openclaw and hermes are not installed on the evidence workstation and the owner
has directed that they not be installed there. Their Installed and Live matrix
cells therefore **cannot move from this machine**, and nothing in this packet
is evidence — it is the runnable recipe for producing that evidence on a box
that has the hosts. It was written without either host present; if a step does
not match the host's actual surface, that mismatch is a finding to record, not
to paper over.

## 0. Bind the runtime first, or nothing below is comparable

1. On the target box, from a **clean checkout of main** at a recorded commit
   `C` (record it):

   ~~~text
   python -m agency_runtime.cli install --agent openclaw
   python -m agency_runtime.cli install --agent hermes
   ~~~

   The packaged `agency.exe` refuses schema-46 stores (pinned at 45); always
   install with the checkout CLI.
2. Read `~/.agency-runtime/launchers/current-<host>.json` and record
   `runtime_digest` per host. Both hosts must pin the **same digest**, and it
   must be the digest a clean-tree install from `C` produces (AR-258's
   one-digest property). The workstation's reference point tonight:
   commit `c6df1449` → `16f1e720f15d…`; after the AR-255 P2 merge the digest
   changes — use the digest your own install produces from your `C`, and
   record `C` next to every result.
3. `agency doctor`: store schema must equal the runtime `SCHEMA_VERSION`
   (46). A store ahead of the launcher fails every hook open and reads
   exactly like a delivery failure — do not measure through it.
4. Sessions opened before the install keep the old launcher. Fresh sessions
   only; a restart, never a reinstall, is the cure.

## 1. The measurement vehicle

The host canary encodes each host's collection logic; readiness first, then an
explicitly confirmed live run:

~~~text
python -m agency_runtime.cli host-canary openclaw --timeout 420
python -m agency_runtime.cli host-canary openclaw --execute \
    --profile-scope isolated-profile --confirm "RUN LIVE openclaw CANARY" \
    --timeout 420 --output openclaw-run1.json
~~~

(Substitute `hermes` verbatim. The confirm phrase is printed by the readiness
report as `execute_confirmation`; use exactly what it prints.)

Series discipline, non-negotiable: **at least 3 runs per host**, keep every
failure, never retry-until-green, and compare decisions-to-declines rather
than runs-to-runs. Parent staffing on claude measured red/green across
otherwise identical runs; one run proves nothing on any host.

## 2. Acceptance conditions per run

A run supports a matrix cell only when the host artifact supports it
(ADR-0156); Agency Store rows correlate but never originate a claim.

- `trust_bypass_used` must be `false` and `trust_mode` `attended`; a
  bypass-derived result must be labeled as such and satisfies no
  attended-trust criterion.
- Parent-side (R2/R3): the report's `evidence` block shows
  `expected_specialist_selected: true`, `expected_specialist_loaded: true`,
  `receipt_proven: true`, and the host's own turn artifact carries the
  delivered capsule (all selected cards, whole instruction bodies) **before
  the turn's first assistant output**. Two or more compatible cards in one
  turn is the R3 shape; the claude parent recruiter regularly selects
  `code-reviewer + application-security-engineer` for the canary prompt.
- Child-side (R1/R4): `host_child_collection_reason` must be absent (a named
  refusal such as `delivery_marker_absent` is the honest negative), the child
  artifact must carry the v6 team envelope with exact card hashes pre-first-
  speech, and `native_child_delivery_verifications` must gain a row joined to
  the staffing decision. Note: as of tonight the child judge has declined
  every native-child staffing decision on claude (15 of 15 non-staffed
  including 13 abstentions); AR-255 P2 (one funded repair call) merges
  tonight — measure on a build that includes it and read the abstention
  reason codes (`native_child_abstention_confirmed` vs
  `native_child_no_specialist_needed`) to know which path you observed.
- R6: if the run's request falls outside the roster, expect
  `agent_hiring_cases` status `applied`, critic approved on a different
  provider than the creator, an `origin='agency'` contractor row, and the new
  card dealt into the same turn's capsule in the host artifact. Known caveat:
  passing security reviews are currently recorded `verdict: "unsafe"` by a
  stale heuristic (`hiring.py:2091`); read the reasons list, not the verdict
  string, until that fix lands.
- R7: two consecutive turns in one session — the card held in turn N's
  artifact, absent in turn N+1 with the expiry announced there, and
  `specialists_loaded.expired_at` set to turn N's end.
- R8: any turn where Agency failed open (for example a routing failure
  receipt) while the host still answered, shown in the host's own artifact:
  user record, no specialist capsule, assistant output after it. Routing
  failures occur organically; none needs to be fabricated.

## 3. What to send back

For each host: the ≥3 canary JSON reports, the recorded commit `C` and
per-host `runtime_digest`, the host artifact paths (or copies) supporting
each claimed cell, and the store row ids (`routing_decisions`,
`specialists_loaded`, `agent_hiring_cases`,
`native_child_delivery_verifications`) per claim. Every cell then updates the
matrix under its named proof authority with candidate identity, artifact,
observation date, and limitation — cells this packet cannot reach stay
`unproven`, and saying so is the correct result.
