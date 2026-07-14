---
title: "Threat Model"
status: active
category: security
created: 2026-07-12
updated: 2026-07-13
tags: [security, architecture, privacy, supply-chain]
related:
  - SECURITY.md
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0038-refuse-executable-git-configuration-during-delegation.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
---

# Threat model

This model covers the local Agency Runtime process, generated host plugins,
SQLite evidence, configuration, delegated commands, provider and roster
network requests, MCP, the loopback dashboard, and the release supply chain.
It assumes the operating-system account and Python interpreter are trusted.

## Assets and security properties

| Asset | Required property |
|---|---|
| Host and provider credentials | Never persist in logs, evidence, URLs, service definitions, or child environments outside the selected integration. |
| Dashboard authority | Remains process-scoped, high entropy, loopback-only, origin-bound, and absent from server logs and command arguments. |
| Configuration and SQLite state | Owner-private, atomically written, link-safe, bounded, and internally consistent. |
| Routing and delegation evidence | Correlated to canonical trace, turn, work-unit, and outcome records; model-authored claims are not authoritative. |
| Managed host plugins | Exactly match the canonical generated bundle, install reversibly, and never claim native state without a postcondition. |
| User and roster content | Metadata-only by default; any opted-in content is bounded, redacted defensively, and retained for a finite period. |

## Trust boundaries and plausible attackers

- A malicious webpage may attempt loopback CSRF, DNS rebinding, token reuse, or
  cross-origin reads against the dashboard.
- A compromised model, tool result, host hook, or MCP client may forge headers,
  replay stale IDs, inject control characters, overrun protocol frames, or
  claim work that did not complete.
- A provider, roster source, proxy, or redirect target may return oversized,
  malformed, credential-harvesting, or adversarial content.
- A hostile repository or delegated command may attempt shell injection,
  credential inheritance, output flooding, path traversal, symlink races, or
  descendant-process escape.
- Another local account may try to read custom configuration, SQLite files,
  sidecars, dashboard descriptors, backups, or temporary canary homes.
- A compromised package or GitHub Action may enter through development,
  release, or CI dependencies.
- Crashes and concurrent requests may cause partial writes, stale decisions,
  resource exhaustion, or evidence from one session to contaminate another.

## Enforced controls

| Boundary | Controls |
|---|---|
| Dashboard and HTTP | Literal loopback binding; strict `Host` and same-origin checks; per-process bearer token; no permissive CORS; JSON-only mutations; exact confirmations; CSP, COOP, and CORP headers; canonical content length; rejected transfer encoding; body, context, worker, and socket-deadline limits. |
| Files and SQLite | Owner-only mode or Windows DACL enforcement; symlink, reparse-point, and SQLite-sidecar rejection; no-follow reads where available; bounded reads; locked atomic replacement; transactions, foreign keys, uniqueness constraints, and read-only diagnostics. |
| Providers, configuration, and roster ingress | Credentialed remote providers require HTTPS; embedded credentials and ambiguous URL components are rejected; credentialed requests do not follow redirects; response bytes, models, identifiers, per-operation timeouts, total roster-fetch deadlines, and candidate counts are bounded. JSON and YAML boundaries reject duplicate keys, aliases, merge keys, non-finite numbers, excessive depth, and excessive node counts. Roster activation remains quarantined and approval-gated. |
| Native processes and delegation | Argument arrays without a shell; validated executable selection; minimal allowlisted environment; task content through standard input when supported; bounded output and time; Windows Job Objects or POSIX process groups; dependency DAG validation; failure-gated successors; mutating Git operations suppress hooks, inherited Git configuration, fsmonitor, executable filters, merge drivers, and text converters; merge only after proven success. |
| Evidence and finalization | Fresh trace and decision IDs; explicit work-unit identity; duplicate and missing results fail; protocol input and output remain strict finite JSON; success is recorded only after verified outcomes; final headers reconcile against canonical SQLite evidence and reject spoofed or ambiguous fallbacks. |
| Installation and canaries | Canonical bundle digest and exact managed-tree comparison; unexpected files force replacement; owner-private staging; backups and rollback; native inventory postconditions; Windows permission setup rejects restricted or indeterminate tokens before DACL mutation; isolated canary homes receive an owner-only directory policy before credentials exist; bounded link-resistant authentication copy hardens the empty destination before writing; nonce-bound proof; attestations bind to host, OS, version, capability, and installation identity. |
| Privacy | Metadata-only default; bounded defensive redaction; secrets remain write-only in dashboard and CLI projections; finite retention; logs sanitize control characters and content-bearing failures. |
| Supply chain | Minimal runtime dependency; pinned build, audit, and workflow tools; immutable GitHub Action SHAs; wheel/sdist parity checks; exact installed-runtime vulnerability audit; Bandit; capability-gated native CodeQL analysis and upload where repository visibility and licensing permit it; machine-readable non-analysis evidence only for a recognized private/internal missing-entitlement response, with ambiguous probes failing closed; native dependency-diff review when GitHub exposes it; offline workflow security linting; no credential persistence in checkout steps. |

## Residual risk and non-goals

- Administrator, root, debugger, or same-account memory access can defeat local
  process secrecy. Agency Runtime is not a sandbox against its owner.
- Defensive redaction cannot recognize every secret or personal identifier.
  Do not enable content capture for data that must never be stored.
- The dashboard is not a remote, multi-user, or reverse-proxied control plane.
- Approved roster prompts and external model responses remain untrusted
  instructions. Quarantine and review reduce risk but do not prove intent.
- An operator who explicitly permits private or loopback roster sources can
  expose local services to that fetch. DNS can also change between validation
  and connection, and environment proxies remain part of the remote-source
  trust boundary; redirects, credentials, response shape, and size still fail
  closed.
- Portable Python cannot prove the absence of every exotic hard-link or
  filesystem race on every supported volume. Sensitive paths are revalidated
  around open/read/replace operations, but high-assurance deployments should
  also use an owner-private local filesystem.
- Live host maturity is established separately for each host and operating
  system. Deterministic contracts do not substitute for an absent native host.
- A public package signature, provenance attestation, and tagged release do not
  exist until the publication checklist records them; source state alone must
  not claim those guarantees.

## Verification

The release gate in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) is the
executable companion to this model. At minimum, run the warning-strict tests,
routing evaluation, Ruff, Bandit, pip-audit, zizmor, documentation validators,
artifact parity checks, and both Windows and Linux portability suites. A new
trust boundary or residual risk requires this document and the governing ADR to
change in the same review.
