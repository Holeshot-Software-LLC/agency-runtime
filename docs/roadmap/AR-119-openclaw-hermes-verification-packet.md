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

## 3. What the claude host taught us, 2026-08-17/18 — read before running anything

Every item below cost real time on claude. They are host-agnostic unless
stated, and each one produced a reading that looked like a product failure and
was not.

### 3.1 Four ways to get a confident wrong answer

- **An unrun hook and a fail-open hook are indistinguishable from outside.**
  Zero Agency rows proves neither. If you suspect the hook is not running, wrap
  its command in a shim that logs stdin/stdout/stderr/exit — that gave the root
  cause on the first run after two days of theorising.
- **A store newer than the launcher disables every hook on the machine** and
  reads exactly like a delivery failure. Before believing any measurement:
  `agency doctor` must show the store's schema equal to the runtime's. Run it
  first, every time.
- **`python -m agency_runtime...` imports from the current directory first**,
  and `PYTHONPATH` cannot override it. An eval "against the installed tree" that
  did not assert `agency_runtime.__file__` may have measured a checkout. Prefer
  running through the installed launcher's own `_bootstrap.py` under `-I -S`,
  which removes CWD, user site and PYTHONPATH by construction.
- **A gate or canary judged by a piped exit code is not judged.** Appending
  `; echo EXIT=$?` makes a failure look like success. Read the tool's own
  summary line or report file.

### 3.2 Reading child evidence without fooling yourself

- **`counts.specialists` and `counts.runs` in a canary record are not
  canary-scoped.** On a workstation whose own sessions write to the same store,
  both absorb unrelated activity. Only `routing` (filtered by the canary's query
  hash) and `loaded_specialists` are the canary's own.
- **`agency evidence child-launches` does not support these hosts.**
  `default_child_artifact_root` raises for anything but claude and codex, so do
  not expect a per-launch outcome report here; use the store directly and the
  bridge-level evidence named in section 2.
- **A child artifact is not a faithful copy of the assignment.** Measured on
  claude: a 3,184-character launch input appears in the child's first record as
  867 characters. Any join that hashes the child's copy will miss. Agency hashes
  what the *parent* recorded.
- **An assignment may legitimately quote a delivery marker.** A review task that
  discusses `[AGENCY INFERENCE TEAM v6]` contains that string; treating the
  mention as a delivery truncates the assignment and produces a hash matching
  nothing. Strip only when an envelope actually decodes.
- **Three join keys exist and they are complementary**, so try all three before
  concluding a launch has no record: the delivered envelope's `decision_id`, the
  assignment SHA-256 against `routing_decisions.query_hash`, and the recomputed
  `context_fingerprint`. Each resolved launches the others missed.

### 3.3 What Rule 4 verification actually requires — expect this

`agency evidence children` will report a delivered, correlated, pre-speech v6
envelope as **`verified_delivery: false`** with reason
`host_hook_output_origin_not_proven`. That is not a defect and not a failed run.
The verification input is the **one-use verified-delivery capability**, which
only the canary's in-lifetime private-lease collector may consume (ADR-0158); a
read-only projection cannot supply it and must not consume it.

**So Rule 4 Live can only be proven inside a canary run on these hosts too.**
Plan for that: the canary is the vehicle, and a passing `evidence children`
read is not a substitute. The same seal is what blocks AR-252's pairing
collector, which is why both wait on one owner decision.

### 3.4 Measurement discipline that survived contact

- **Serialize canary runs.** Concurrent runs contend on the same inference
  providers and depress the very rate being measured.
- **Keep every failure.** Retry-until-green converts a rate into a best-of. Over
  three series on claude, nine runs produced one usable answer; the eight
  failures are what made the ninth readable.
- **Back off, do not grind.** Two consecutive provider-stage kills earns a
  30-minute pause; three failing series spaced over six hours is
  `blocked-on-provider`, and grinding past that produces false confidence.
- **Expect provider flakiness to dominate.** On claude it roved across planner,
  recruiter and child stages, interleaved with clean draws minutes apart on
  identical code. A single failed run says nothing about the path.
- **Sessions started before an install keep the old launcher.** The cure is a
  restart, never another install.

### 3.5 The findings that are already settled — do not re-derive them

- Recruiter ranking order, candidate eligibility, requirement coverage, the
  child's candidate universe, and child task size have each been refuted as the
  cause of staffing failures. The overnight brief's REFUTED list stands.
- The child judge, given a pure small unit over the complete universe with the
  owner's small-unit policy live in the prompt, **abstained** (first-pass,
  repair unconfirmed). If these hosts staff that same unit, that is a
  cross-host difference worth reporting immediately.

## 4. Read this before installing: what these hosts will and will not produce

Source audit, 2026-08-18, adversarially reviewed and independently
re-verified against the cited lines. These hosts are not installed here, so
everything below is a **source claim**, not a measurement — but the claims are
about code that exists, and each one is checkable without either host.

### 4.1 The headline: there is no Rule 4 verification route for these hosts today

Installing openclaw or hermes right now would **not** produce Rule 4 evidence.
Not "might fail" — there is no path:

- **No artifact reader.** `default_child_artifact_root` handles claude and
  codex and raises `ValueError("child delivery evidence host is unsupported")`
  for anything else (`agency_runtime/core/child_delivery_evidence.py:1248`).
  `child_delivery_evidence(..., host="openclaw")` raises, and a test pins that
  as deliberate (`tests/test_child_delivery_evidence.py:1414-1418`).
- **No canary.** `SAFE_CANARY_HOSTS = frozenset({"codex", "claude"})`
  (`agency_runtime/core/canary.py:82`), enforced in `canary_backends.py` and
  `canary_proof.py`; neither file mentions hermes or openclaw at all.
- **Delivery is in-process only.** Neither bridge writes a child transcript to
  disk; hermes returns the context segment as JSON on stdout
  (`adapters/hermes/bridge.py:406-412`) and openclaw returns a dict serialized
  in `main` (`adapters/openclaw/node_bridge.py:1320-1327`). The host plugin
  injects it into the child prompt in memory. **There is no host-written
  artifact to read**, which is what ADR-0156 requires as the origin authority.

**So sequence the work accordingly**: installing these hosts proves R2, R3, R7
and lifecycle behaviour, and cannot prove R4 until a reader or a canary backend
exists for them. Do not read a missing R4 result as a delivery failure.

**The encouraging half:** everything *below* the missing reader is already
host-agnostic. The delivery-verification tables accept all five hosts
(`core/store/schema.py:730, 810, 868`), `_record_native_child_delivery_verification`
accepts any execution host (`core/store/evidence.py:2044-2046`), and the exact
matcher already handles their binding kind — `binding_kind == "child_id"`
(`child_delivery_evidence.py:689-691`). What is missing is the artifact reader,
the root resolver, and the canary host gate. That is a bounded build, not an
architecture change.

### 4.2 The silent hole is worse here than on claude

On claude, five paths attempt a receipt through `_record_native_child_unstaffed`
(`adapters/hooks.py:1138, 1180, 1199, 1263, 1315`). **The shared adapter path
these hosts use calls nothing**: `record_native_child_staffing_failure` is
referenced only from `adapters/hooks.py:984-987`, never from
`adapters/base.py` — verified by repo-wide grep.

Every early return on their child boundary is bare (`adapters/base.py`):
runtime disabled (`:829-830`), host-not-matched **or partial correlation**
(`:845-846`), an exception around `staff_native_child` (debug log only,
`:866-872`), and unstaffed (`:873-874`). A real child launch arriving with one
to three of the four required identities produces **no trace of any kind**.

Two host-specific consequences worth watching for on first install:

- **hermes may silently reclassify a child as a user turn.** Native-child
  fields are forwarded only when `parent_session_id and parent_trace_id` are
  both present (`adapters/hermes/bridge.py:398`). Without them the child falls
  through to the ordinary `run_preflight` path as though a person had typed it.
  That is a misclassification, not merely a missing receipt, and openclaw does
  not share it — openclaw always passes all four, possibly empty
  (`node_bridge.py:1306-1319`).
- **openclaw can skip `record_native_child_started`.** When `work_unit_id or
  goal` is truthy it calls the post-tool-call handler and returns early
  (`node_bridge.py:1204-1215`), bypassing the recorder at `:1216`; hermes does
  both (`bridge.py:461-489`).

**A structural limit that applies to every host, including claude.** Adding the
recorder to `base.py` would not close the parent-correlation case:
`record_native_child_staffing_failure` itself returns `""` when the parent
scope is not current (`native_child_staffing.py:598-604`), and `_record_decision`
re-checks the same gate (`:524-530`). `routing_decisions` is bound to an open
parent run, so *"a child launch that cannot be correlated to a live parent" is
unrecordable in that table by construction*. Closing it needs a different lane
— which is exactly the schema decision already queued, and this audit is the
argument for taking it.

### 4.3 Which join keys will work here

Of the three keys that work on claude, only two survive, and the strongest one
changes:

- **v6 envelope `decision_id` — unavailable.** The decision id *is* sealed into
  the rendered segment and does reach the child's context
  (`native_child_staffing.py:1370-1386`), but with no artifact there is no
  left-hand side to join from.
- **`sha256(assignment)` against `query_hash` — works, and is the strongest
  available join here.** `query_hash` is set to `task_sha256` for both staffed
  and unstaffed decisions (`native_child_staffing.py:455-456, 606, 899`).
  Anyone holding the child's exact plaintext assignment can join. Note nothing
  in these paths persists that plaintext except the opt-in capture lane.
- **Recomputed `context_fingerprint` — works, same as claude**, with the same
  caveat that applied and failed rows use *different* fingerprint schemas
  (`:204-230` versus `:489-506`), so recompute the right one.

Store-side only: an applied decision carries `native_child_delivery.launch_id`
with `binding_kind: "child_id"` (`native_child_decision.py:246-248`). But
`bind_native_child_launch` is hard-restricted to claude and zcode
(`base.py:679-707`), so these hosts get no explicit launch-binding row.

### 4.4 The one thing only an install can settle

Whether real Hermes and real OpenClaw actually populate `parent_session_id`,
`parent_trace_id`, `workerId` and `nativeRunId` on a child launch. That payload
contract (`hermes/bridge.py:394-404`, `openclaw/node_bridge.py:1313-1316`) is
exercised only by this repository's own tests, never against a live host. It
decides how often the silent paths above actually fire in production.

**So the first thing to capture on install is not a Rule 4 attempt — it is the
raw child-launch payload.** Log what the host sends before Agency interprets
it. If all four identities are present, the silent paths are theoretical and
the remaining work is the missing reader. If they are not, that is the first
real defect these hosts expose, and it was predicted from source.

**A caution about the existing tests.** `tests/test_native_child_host_boundary_staffing.py`
drives the real bridges but stubs `staff_native_child`, and at `:166-217` it
asserts that a partially-correlated child gets **nothing** — the current tests
codify the silence as intended behaviour. Do not read those passing tests as
evidence that non-delivery is impossible; they assert the opposite.

## 5. What to send back

For each host: the ≥3 canary JSON reports, the recorded commit `C` and
per-host `runtime_digest`, the host artifact paths (or copies) supporting
each claimed cell, and the store row ids (`routing_decisions`,
`specialists_loaded`, `agent_hiring_cases`,
`native_child_delivery_verifications`) per claim. Every cell then updates the
matrix under its named proof authority with candidate identity, artifact,
observation date, and limitation — cells this packet cannot reach stay
`unproven`, and saying so is the correct result.
