---
title: "Package the audited upstream roster and synchronize quarantined deltas"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-27
tags: [roster, upstream, audit, quarantine, supply-chain]
related:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md
  - docs/roadmap/issue-AR-97-reconcile-required-inference-remediation.md
  - docs/roadmap/issue-AR-163-reopen-stale-remediation-authority.md
  - docs/roadmap/issue-AR-83-manifest-roster-import.md
  - docs/roadmap/issue-AR-106-portable-windows-policy-and-posix-simulations.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0063-import-external-rosters-through-declared-manifests.md
  - docs/worklog/README.md
supersedes: [docs/decisions/0063-import-external-rosters-through-declared-manifests.md]
superseded_by: null
id: ADR-0066
type: decision
deciders: [maintainers]
---

# ADR-0066: Package the audited upstream roster and synchronize quarantined deltas

## Context

Generic manifest ingress is a necessary trust boundary, but Agency's product
contract also requires the complete vetted upstream specialist roster to be available
without a sibling checkout or network call. The earlier decision rejected
packaging a named upstream entirely, which would leave normal installations with
an incomplete employee pool and make routing depend on operator assembly.

## Decision

Keep the generic declared-manifest quarantine boundary, and additionally govern
one official upstream roster as a pinned, audited, self-contained distribution
input. Every source definition has an explicit approved, quarantined, or retired
outcome. Package only approved, rewritten Agency-owned routing contracts and
bounded prompt artifacts; preserve source identity, revision, content hash,
license provenance, audit revision, and superseding history.

Nightly synchronization compares pinned source identities and content hashes.
Only new or changed definitions enter quarantine. The previously approved
version remains active while deterministic security checks, optional
inference-assisted semantic review, contract regeneration, and active-roster
conflict analysis run. A failed, unavailable, or degraded required audit never
activates a candidate. Activation is a generation-checked review action, and an
upstream deletion never silently removes an active version.

Every rejected definition enters a reusable immutable remediation queue during
ingestion. Its receipt binds the original source hash, rules attempted,
matched/no-match disposition, optional deterministic proposal hash, and next
review action. CLI and dashboard projections omit source prompt bodies. Only an
exact registered hash-bound rule may create an automatic proposal, and that
proposal remains quarantined and non-executable until a governed semantic
projection, deterministic and configured inference audits, conflict checks, and
explicit approval succeed. Unknown or ambiguous repairs are never guessed.

Do not treat the presence of a resolution event as authority. After complete
semantic validation, mint a keyed authority receipt bound to one queue and an
exact durable dependency closure. Bind source scans with a full normalized scan
seal and bind the selected entry and provenance explicitly. Any dependency
mutation or missing child edge invalidates the marker and reopens the queue.
Unsigned, malformed, and duplicate resolution events remain quarantined audit
claims and are surfaced as anomalies.

Normal routing reads the verified installed bundle and canonical Store. It never
depends on a sibling repository or live upstream availability. The CLI,
dashboard, and bounded CI job expose source status, import dry runs, findings,
candidate comparison, approval, rejection, and activation history.

## Consequences

- A fresh installation can consider the complete approved roster.
- Upstream changes cannot replace active instructions before review.
- Generic third-party manifest import remains available through the same
  quarantine controls.
- Repository size grows with the governed contracts and prompts, but build-time
  reproducibility and runtime independence improve.
- Audit failures are durable findings, not silently omitted agents.
- Remediation is a reusable ingestion state machine, not a silent text rewrite;
  queueing or proposing a repair grants no activation authority.
- SQLite maintenance or forged duplicate rows cannot reorder resolution
  authority because causal order uses an immutable event sequence and only the
  verifier-held HMAC marker can suppress pending work.

## Alternatives

- Retain only generic operator-selected imports. Rejected because the standard
  installation would not provide the promised complete roster.
- Download the roster at runtime. Rejected because selection would gain a
  mutable network and supply-chain dependency.
- Auto-activate hash changes after deterministic scanning. Rejected because
  semantic authority and cross-agent conflicts require review.
