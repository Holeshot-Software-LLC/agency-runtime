---
title: "Authenticate Codex plaintext spawns from host transcripts"
status: accepted
category: decisions
created: 2026-08-12
updated: 2026-08-13
tags: [codex, native-child, hooks, transcripts, security, evidence]
related:
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/THREAT_MODEL.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/codex_spawn_provenance.py
  - agency_runtime/core/store/maintenance.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0159
type: decision
deciders: [lkrammes]
---

# ADR-0159: Authenticate Codex plaintext spawns from host transcripts

## Context

Codex CLI `0.147.0` and Desktop runtime `0.147.0-alpha.6.6` support two
MultiAgentV2 delivery modes. A collaboration function call whose host response
item contains explicit `encrypted_function_args: []` is delivered as plaintext;
a call without that exact marker remains encrypted. The current Sol/TUI
observation and all 65 observed Desktop calls used the encrypted path.

Codex `PreToolUse` exposes the transcript path, session, turn, tool-call ID, and
parsed arguments and can replace local function-tool arguments. It does not
expose the plaintext marker or internal tool-call source. Trusting
`tool_input.message`, `task_name`, a model slug, or ciphertext appearance would
therefore let model-authored input impersonate host-authorized plaintext.

The host records the complete function-call response item before queuing tool
execution, so the parent transcript is the available pre-dispatch source for
the missing provenance. Codex documents that transcript format as unstable.
Any parser is consequently a version-pinned compatibility boundary, not a
generic JSONL trust grant.

## Decision

Agency may rewrite a Codex native-child `spawn_agent` message only after a
sealed in-process v3 attestation proves one exact host-persisted plaintext call.
The attestation seals one atomic `profile_id` chosen only from exact transcript
metadata. The existing CLI TUI/exec profiles remain pinned to `0.147.0`; a
separate Desktop profile is pinned only to `0.147.0-alpha.6.6`. Every unknown
version, mixed profile, or schema fails open unstaffed.

The attestor accepts only the canonical active transcript beneath the private
Codex sessions root. It rejects relative or caller-selected roots, links,
Windows reparse points, hard links, mutable non-owner access, replacement,
truncation, oversized input, duplicate keys, and unstable descriptor/path
identity. A purpose-built bounded streaming scanner must support observed large
rollout lines without loading the transcript as one object.

The transcript filename supplies the concrete UUIDv7 thread identity while the
hook's session ID supplies the shared UUIDv7 root identity. The canonical path
uses padded date components, and turn IDs accept only the observed non-nil RFC
UUIDv4/UUIDv7 domain. Exact CLI `0.147.0` ancestry may be fully materialized in
one rollout or use the authentic one-record TUI fork form. For that cross-file
form, Agency resolves each declared parent/root UUID only in its canonical UTC
date directory plus the immediately adjacent UTC dates, requires one unique
canonical filename without recursive search, and validates each file's own
recorded UTC offset independently. Every external descriptor, complete scanned
prefix, metadata record, causal record, and identity join is sealed and later
revalidated; all external ancestry together is capped at 64 MiB.

The Desktop profile accepts only root plus observed depth-one and depth-two V2
structured-child ancestry under exact `vscode`/`legacy`/`Codex Desktop`
lineage. Disabled guardians, `subagent.other`, greater depth, and mixed CLI/
Desktop metadata are rejected. The first metadata record owns a canonical file;
later exact-known Desktop metadata can corroborate history but never become
authority, and every consumed copy, record, prefix, file, and profile is sealed.
Root dynamic tools and the exact two/three-key Git families are independently
required. Each child's dynamic-tools presence, Git-branch presence, inheritance,
leading-prefix count, causal fork form, filename residual, and parent inheritance
must match one of 13 observed atomic tuples. Eight tested but unobserved cross-
products are deliberately outside the allowlist.

An accepted CLI cross-file edge requires the exact parent `spawn_agent` call
and its exact adjacent `SubAgentActivity(started)` completion record. A Desktop
edge requires the exact adjacent call, direct started event, and compact
`function_call_output`, including exact IDs, path, fork semantics, and temporal
ordering. Every supported depth-two form proves both root-to-parent and parent-
to-child edges. Ancestor causal calls accept only the observed ordinary
response-item schema or that exact schema plus `encrypted_function_args: []`;
this optional historical marker does not authorize the current rewrite. The
current authorization call still requires
exactly one `response_item.function_call` using namespace `collaboration`, name
`spawn_agent`, the hook's turn and call IDs, arguments exactly equal to the
complete hook input, and `encrypted_function_args` present as exactly an empty
list. Null, missing, nonempty, ambiguous, stale, completed, replayed, or
unsupported ancestry is unstaffed. V1 receives no implicit exception. Exec
depth-two/deeper remains unsupported until it receives a separate observed
exact-schema decision.

Attestation returns only sealed, content-free identities and digests. Agency
revalidates the exact file and records during delivery validation and as the
last guarded action inside the successful route's `BEGIN IMMEDIATE` transaction.
Failure rolls the route back before any staffed output can be returned. The same
transaction rejects a second delivery for the same host, parent session, parent
trace, and launch ID so concurrent hooks cannot obtain two rewrites.

This attestation authorizes only the pre-spawn rewrite. It cannot prove that the
child received or used the cards. ADR-0156 remains the sole Rule-4 authority: a
green result still requires the host-authored child artifact with every exact
inference-selected card hash before first child speech. Installed and Live
claims additionally bind the exact Codex executable and Agency candidate.

## Consequences

- Current encrypted Sol calls continue unstaffed without blocking native host
  execution.
- A marked plaintext call can use the existing inference-owned multi-card
  staffing path without trusting a model-authored label or message.
- Codex transcript or version drift becomes an explicit compatibility failure
  and requires a reviewed capability update. The exact CLI `0.147.0` profiles
  remain unchanged; Desktop alpha uses its own exact profile rather than a
  widened CLI predicate. Exec depth-two/deeper remains outside both profiles.
- The new scanner and one-use transaction need focused spoof, replay, path,
  schema, size, concurrency, and TOCTOU tests before installation.
- Source and simulation can advance independently; neither changes an Installed
  or Live matrix layer.

## Alternatives

- **Trust a plaintext-looking hook message.** Rejected because the hook does not
  expose whether the host selected plaintext delivery.
- **Use `task_name`, model slug, or message shape as authority.** Rejected
  because those values are model-authored or merely heuristic.
- **Inject cards at `SubagentStart`.** Rejected because that event does not bind
  its context to the exact authenticated parent spawn call.
- **Treat the transcript as a generic stable interface.** Rejected because the
  host documents it as unstable; exact version and schema pinning are required.
- **Wait indefinitely for a richer upstream hook field.** Rejected as the only
  path because the exact host already persists sufficient bounded provenance;
  a future direct marker may supersede this compatibility adapter.

## Provenance

The 2026-08-12 AR-180 read-only preflight identified Codex CLI `0.147.0`,
Desktop runtime `0.147.0-alpha.6.6`, the conditional marker contract, and one
current encrypted Sol/TUI spawn. It ran no Agency canary and changed no install
or trust state.

Candidate `966845cc` first implemented this boundary; adversarial review found
incomplete nested-thread ancestry and a post-persistence final-validation gap.
Repair `2fe5e9ec` separates root and thread identity across observed TUI/exec
lineages, seals each ancestry record, and moves final validation before commit.
Hardening `e8b60f64` pins the exact inner and outer response schema, canonical
paths and UUID domains, duplicate item identity, exact persisted success
projection, and retry-safe post-commit cleanup. Its 112-mutation verifier, named
fast spine, and independent adversarial review pass.

Candidate `45b21cdc` and ledger `01730614` added the v2 cross-file attestation for
authentic one-record TUI forks. The observed census resolved 11/11 canonical
chains: one depth-one sparse, seven depth-one inherited, one depth-two sparse,
and two depth-two inherited. The largest accepted sample sealed 48,678,898
external bytes and resolved in 3.809 seconds. The parent checkpoint passed 365
focused warning-strict tests and the 673-test fast spine with 6 skips. Its
scoped mutation run killed 19/19 mutations with a green baseline and
`source_unchanged=true`; an independent reviewer passed 200 tests, killed the
same 19/19 mutations, and reported no finding at any severity. These results
advanced only Codex Rule-4 Implementation and Simulation. The 134-test dashboard
suite, routing evaluation, Ruff, format, and documentation/schema gates passed
for that candidate. Its complete decision-conformance evaluator exited zero in
883.1 seconds: the baseline passed in 169,548 ms, all 131/131 mutations were
killed, zero survived or were invalid, and `source_unchanged=true`.

Candidate `211563c7` and ledger `ee8db873` add the sealed v3 Desktop profile.
Focused provenance/hook verification passed 288/288, the focused-plus-anchor
gate passed 289/289, and the named fast spine passed 673 with 6 skips. The scoped
Desktop baseline passed and killed 20/20 mutations with zero survived or invalid
and `source_unchanged=true`; an independent run reproduced those results and
reported no finding at any severity. A content-safe probe resolved all 52
authentic V2 Desktop chains (47 depth one, 5 depth two), with a maximum
32,650,955 external bytes and 2.765 seconds. All 65 observed Desktop calls were
encrypted and unmarked, so these results advance only Codex Rule-4
Implementation and Simulation. For `211563c7`, the dashboard UI suite passed
134/134, routing passed every threshold, and Ruff lint/format passed. The
expanded decision-conformance evaluator remains pending; the prior 131/131
result remains candidate-`45b21cdc` history. Exec depth-two/deeper ancestry and
all Installed and Live proof remain unproven.
