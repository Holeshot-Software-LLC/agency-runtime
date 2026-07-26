---
title: "Broker restricted Windows agent controls through narrow dashboard operations"
status: superseded
category: decisions
created: 2026-07-16
updated: 2026-07-26
tags: [roster-governance, cli, dashboard, windows, security]
related:
  - docs/roadmap/issue-AR-75-broker-restricted-windows-agent-controls.md
  - docs/roadmap/issue-AR-76-restricted-windows-cli-read-and-fail-safe.md
  - docs/decisions/0046-config-backed-agent-activation-policy.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/decisions/0060-restricted-windows-cli-read-and-fail-safe.md
  - docs/decisions/0090-model-facing-control-paths-are-read-only.md
  - docs/roadmap/issue-AR-128-seal-model-facing-control-authority.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0090-model-facing-control-paths-are-read-only.md
id: ADR-0059
type: decision
deciders: [maintainers]
---

# ADR-0059: Broker restricted Windows agent controls through narrow dashboard operations

## Context

The reversible agent policy lives in typed configuration, while governed agent
definitions live in SQLite. A restricted Windows token may be able to read the
configuration yet correctly lack authority to repair the Store namespace. That
must not make the CLI crash when the installed normal-user dashboard already
owns both identities and exposes authenticated agent operations.

A generic config or Store proxy would be too broad. Silently redirecting an
explicit `--config` path would also mutate a different identity than the
operator named. Paginated roster data and a configuration revision can race if
the client does not bind every page and mutation to one coherent contract.

## Decision

Keep direct config and Store access as the primary CLI path. Only the exact
restricted-Windows-token refusal may broker default-identity agent operations.
An explicit `--config` path is never redirected and reports a controlled error
when direct access is unavailable.

Expose only three additional authenticated agent-control operations to this
private client: compact paginated activation read, exact-slug lookup, and agent
toggle. Bulk pages contain only canonical slug, name, division, enabled, and
protected state. Full selector metadata is not available in bulk; the lookup
returns at most one exact governed definition for the requested canonical slug.
Include the dashboard service's canonical configuration path and revision,
active and desired Store paths, restart-required state, and roster revision with
the responses. Do not expose arbitrary configuration mutation through this
broker.

For list, request bounded pages, require a stable path, revision, total count,
and strictly advancing canonical cursor, reject duplicate or non-canonical
slugs and malformed booleans, and cap the total materialized roster. For toggle,
look up exactly one slug and revision, then submit one request with the exact
confirmation phrase and that revision. Validate the returned slug, desired
state, changed flag, config path, revision, and effective disabled set. A 409 or
any mismatch is terminal; never refresh and retry automatically. Recheck Store
binding, roster membership, confirmation, and the effective disabled set inside
the config writer lock after revision validation. A desired Store path different
from the service's active Store is restart-required and refuses the operation.

## Consequences

- Restricted Codex can inspect and control optional specialists without Store
  ACL mutation authority.
- `agents-orchestrator` and `chief-of-staff` remain protected by the shared
  activation policy and dashboard handler.
- Normal shells stay service-independent and explicit configuration identities
  remain exact.
- Large rosters remain complete through compact pagination without sending
  routing descriptions or taxonomy for every specialist.
- This is not a precedent for generic roster administration, raw YAML writes,
  full-catalog export, or arbitrary Store calls. Read-only route, search, and
  policy brokerage is separately constrained by ADR-0060.

## Alternatives

- Relax Store ACLs for the restricted host. Rejected because agent inspection
  does not justify filesystem mutation authority.
- Proxy the entire configuration API. Rejected because the required operation
  is narrower and secrets must not cross this boundary.
- Redirect explicit `--config`. Rejected because it would violate the named
  configuration identity.
- Retry stale revisions automatically. Rejected because that can overwrite a
  deliberate concurrent operator choice.

## Provenance

`AR-75` records implementation and installed restricted-Codex verification.
The implementation commit will be linked through the roadmap and worklog after
it exists.
