---
title: "Threat Model"
status: active
category: security
created: 2026-07-12
updated: 2026-07-20
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
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0054-unit-aware-assignment-and-event-driven-dag.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/decisions/0056-capability-bound-restricted-windows-scratch.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/decisions/0067-require-configured-inference-for-selection.md
  - docs/decisions/0068-select-compatible-specialist-closures-per-unit.md
  - docs/decisions/0069-enforce-conflicts-before-prompt-composition.md
  - docs/decisions/0070-run-child-specific-agency-activation.md
  - docs/decisions/0071-bound-native-delegation-correction.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
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
| Agency-wide master state | Read before other runtime work; owner-private, bounded, generation-checked, atomically published, and impossible to turn off through deletion, corruption, or an unproven restricted-token read. |
| Host-scoped soft controls | Durable, generation-checked, atomically published, and resistant to stale dashboard, CLI, MCP, or host-command writers. |
| Agent activation policy | Bound to one canonical config and roster revision; protected coordinators remain enabled, and optional-agent changes are reversible without deleting governed definitions or history. |
| Resident manager binding | Compact, versioned, parent-only, and current-turn bound; complete upstream manager prompts do not accumulate in long-running conversations or enter children as worker directives. |
| Roster governance | Every upstream definition is content-addressed and accounted for as active, quarantined, or retired; audit findings and lifecycle transitions remain append-only and cannot be bypassed by a newer download. Every quarantine creates a source-bound, non-executable remediation attempt. Only exact registered rules may propose a repair; unknowns remain queued, and semantic audit plus explicit approval remain mandatory before activation. A resolution becomes authoritative only after keyed verification of its exact durable dependency closure; raw or ambiguous claims never suppress pending work. CLI/dashboard projections expose hashes, rule disposition, next action, and anomaly counts without raw prompt content. Runtime quarantine may retain bounded raw source evidence, while the packaged bundle retains hashes, receipts, findings, and approved rewritten artifacts instead of corrupt raw prompts. |
| Routing and composition plans | Bound to the exact classifier, configuration, roster, candidate, compatibility, and inference revisions; no conflicting or ineligible prompt is hydrated merely because it scored highly. |
| Routing and delegation evidence | Correlated to canonical trace, turn, work-unit, and outcome records; model-authored claims are not authoritative. |
| Specialist activation capabilities | Single-use, exact-version and work-unit scoped, stored only as digests, and recorded as retrieval rather than proof that a named specialist executed. |
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
- An upstream specialist definition may contain instruction-priority escalation,
  unsafe mutation authority, encoded payloads, hidden external dependencies, or
  conflicting directives intended to cross a worker or manager boundary.
- A configured inference provider may fail, return malformed or adversarial
  rankings, or falsely imply that a requested router alias is the model that
  actually served the request.
- A hostile repository or delegated command may attempt shell injection,
  credential inheritance, output flooding, path traversal, symlink races, or
  descendant-process escape.
- Another local account may try to read custom configuration, SQLite files,
  sidecars, dashboard descriptors, master-control state, backups, or temporary
  canary homes, or replace a control path to suppress enforcement.
- A hostile repository may put a familiar executable in its working directory
  or a relative `PATH` entry, then replace a validated launcher before process
  creation.
- A compromised package or GitHub Action may enter through development,
  release, or CI dependencies.
- Crashes and concurrent requests may cause partial writes, stale decisions,
  resource exhaustion, or evidence from one session to contaminate another.

## Enforced controls

| Boundary | Controls |
|---|---|
| Dashboard and HTTP | Literal loopback binding; strict `Host` and same-origin checks; per-process bearer token; no permissive CORS; JSON-only mutations; exact confirmations; canonical exact-slug lookup and cursor validation; prompt-free bounded roster operations/revision history, immutable review projections, and credential-free inference projections; remote freshness and provider health remain explicitly non-probed unless separate evidence exists; CSP, COOP, and CORP headers; canonical content length; rejected transfer encoding; body, context, worker, response-page, DOM, and socket-deadline limits. |
| Agency-wide master control | Canonical per-user `control.json` checked before Store or correlation; strict bounded schema; owner-private real parent chain; monotonic compare-and-swap generation; owner-private lock and exclusive temporary file; durable atomic replacement and verified postcondition; missing or invalid state fails enabled. A restricted Windows reader is canonical-path-only and requires stable identities plus negative proof for every mutation right; an authenticated loopback dashboard may broker writes. |
| Host-scoped soft control | Canonical SQLite row per host; absent state is enabled at generation zero; status projects the committed generation; every public mutation compares one observed generation under `BEGIN IMMEDIATE`; real transitions increment exactly once; no-ops preserve revision; stale, malformed, and exhausted generations fail closed; dashboard conflicts return HTTP 409 and multi-host CLI results preserve partial failure. Direct Store access remains primary; only an exact restricted-Windows-token refusal may use the owner-private authenticated dashboard descriptor to broker one complete validated host snapshot or one generation-checked mutation. Missing, duplicate, malformed, mismatched, unauthenticated, unavailable, and stale broker results fail closed without retry; native lifecycle is never proxied. |
| Files and SQLite | Owner-only file mode or Windows DACL enforcement; real parent chains that exclude cross-account substitution; canonical config and custom policy namespaces are checked before cache use and after reads; a present custom policy must be a current-user-owned regular single-link file whose descriptor and path identity remain stable, with no POSIX group/other mutation or Windows non-owner mutation access. A textual Windows SDDL owner alias is accepted only when native binary-SID comparison proves exact equivalence to the effective TokenUser. Config parents may retain safe read/traverse-only access while database parents remain private for sidecars; POSIX default-ACL rejection; symlink, reparse-point, hard-link, and SQLite-sidecar rejection; no-follow reads where available; bounded reads; stable identity checks; locked atomic replacement with exact rollback receipts; config-bound Store mutations and complete routing snapshots serialize against configuration writers, with mutation preconditions repeated inside the writer lock after revision validation; SQLite transactions, foreign keys, uniqueness constraints, and read-only diagnostics. |
| Providers, configuration, and roster ingress | Credentialed remote providers require HTTPS; embedded credentials and ambiguous URL components are rejected; credentialed requests do not follow redirects; response bytes, models, identifiers, per-operation timeouts, total roster-fetch deadlines, and candidate counts are bounded. JSON and YAML boundaries reject duplicate keys, aliases, merge keys, non-finite numbers, excessive depth, and excessive node counts. Local directory ingestion rejects links, reparse points, and special entries; records exact basename bytes and stable identities for the manifest root and every traversed directory; enforces one source-wide entry budget; and revalidates every receipt after file reads. Every imported definition enters a content-addressed candidate revision. Deterministic and configured-inference audit results, findings, active-basis identity, and lifecycle transitions are append-only. A missing, invalid, degraded, stale-basis, or failing required audit cannot approve or activate a candidate; nightly delta synchronization never auto-activates, deletes, or replaces the last approved revision. |
| Selection and prompt composition | Turn intent, expertise selection, and execution topology are separate decisions. Hard host, platform, tool, permission, activation, and policy filters run before inference. Configured inference is mandatory for selection-requiring turns and exhausts its bounded declared chain before entering an explicit degraded state; deterministic candidates are never relabeled as inferred. Inference receives bounded structured cards, never full prompt bodies. Compatible-set construction enforces `requires`, `conflicts_with`, authority, context mode, independence, and resource constraints before hydration. One directive specialist per worker is the default; implementers and independent reviewers remain isolated. The resident managers remain parent-only and cannot become domain workers. |
| Restricted Windows CLI brokerage | Direct owner-private access remains primary. Only an exact restricted-token refusal may use the owner-private authenticated dashboard for bounded master, host, or agent operations. Bulk roster pages expose only compact activation state; one exact-agent lookup supports one revision-checked toggle. Route, search, explain, and policy execute server-side over full routing metadata and return bounded projections instead of exporting the selector catalog. Every Store-backed response binds one canonical config path/revision, active Store path, and roster revision; a different desired Store path is restart-required and fails closed. Control receipts must prove success, requested and effective states, changed truth, and the deterministic no-op or single-increment generation. Explicit config identities are never redirected; delegation, setup, arbitrary Store calls, and generic configuration mutation are never proxied. Missing, stale, malformed, mismatched, oversized, unavailable, or conflicting evidence fails closed without retry. |
| Native processes and delegation | Argument arrays without a shell; absolute-only executable discovery that ignores empty, dot, relative, and current-directory `PATH` entries; canonical regular targets outside the target repository; Windows link/reparse rejection and POSIX launcher-symlink canonicalization; every executable or wrapper artifact occurs at one exact ordered argv position, with the first identity covering `argv[0]`; frozen ephemeral or persistent identities cover those same paths and are revalidated immediately before process creation; minimal allowlisted environment; task content through standard input when supported; bounded output and time; kill-on-close Windows Job membership assigned atomically through `STARTUPINFOEX` at process creation, or a dedicated non-dumpable Linux subreaper with a pre-opened `/proc` children descriptor and pidfd signaling. Before `exec`, the Linux target enters a separate session, arms parent-death signaling, and inherits a `no_new_privs` seccomp policy denying supervisor-targeted signals, queued signals, pidfd acquisition, resource-limit changes, scheduler and affinity mutations, priority changes, and I/O-priority changes while retaining normal own-child operations. A private policy acknowledgement precedes external `READY`, but target code remains blocked until the parent durably owns containment state and every I/O worker, then sends exact `GO\n` plus EOF as a one-way commit. Exact cancellation prevents pre-commit execution; ambiguous post-commit interruption drains the full tree before propagation. Exactly one final `COMPLETE` after descendant drain and resource close is required. Missing, malformed, duplicate, out-of-order, or truncated receipts and unavailable strong-containment primitives fail closed; bounded versioned unit-aware specialist assignment; validated dependency DAG; stable event-driven ready queue; strict failure-gated successors; mutating Git operations suppress hooks, inherited Git configuration, fsmonitor, executable filters, merge drivers, text converters, and pathspec magic; merge only after proven success. Restricted Codex Windows scratch requires a file-ID-bound host capability under the owner-private visualization namespace, an authoritative effective-token logon SID, protected child DACLs, and link-safe identity-bound cleanup. Process-local authority never crosses `exec`: every child independently reattests only its exact randomized thread-bound allocation against the canonical host marker, root/parent identity, DACL, and mutation access; ambiguous roots and repository fallbacks fail closed. |
| Evidence and finalization | Fresh printable trace and session IDs bounded to 512 UTF-8 bytes before lookup or indexed persistence; privacy-safe request fingerprints and durable typed turn classifications; explicit work-unit identity; exact Agency and host-native tool allowlists rather than namespace-suffix trust; duplicate and missing results fail; bounded work-unit extraction. Selection is a plan, not load evidence. Each isolated unit the native host actually starts requires a digest-only single-use capability bound to its ready-recipe slug, version, hash, and work unit; completion separately correlates retrieval with a generic native worker or tool-run receipt and never treats unauthenticated MCP access as named-specialist execution. Declined, skipped, or retry-exhausted units close with explicit nonexecution evidence rather than a fabricated activation; a host-merged unit is recorded as skipped with a bounded merge reason. Disabling an optional agent invalidates replay, preparation, consumption, and affected ready-turn completion; oversized exact prompts fail before selection or activation; mutation and terminal close transactions are mutually exclusive; terminal outcomes are monotonic and cannot be reopened by Stop feedback; one corrective pass is the maximum; protocol input and output remain strict finite JSON; success is recorded only after verified outcomes; LiteLLM provenance is granted only by the callback-owned Store ingress; final headers reconcile against canonical SQLite evidence and reject spoofed or ambiguous fallbacks. |
| Installation and canaries | Canonical bundle digest and exact managed-tree comparison; unexpected files force replacement; owner-private staging; backups and rollback; native inventory postconditions; interpreter plus package-bootstrap lexical/resolved metadata and content identities persisted in the managed install manifest; launcher drift or unproven identity makes maturity stale and blocks registration; Windows permission setup rejects restricted or indeterminate tokens before DACL mutation; scheduled-task definitions use BOM-bearing UTF-16 input, token-SID-bound identity, bounded Base64/UTF-8 COM inspection, strict schema normalization, semantic execution checks, and exact pre-mutation requery; isolated canary homes receive an owner-only directory policy before credentials exist; bounded link-resistant authentication copy hardens the empty destination before writing; nonce-bound proof; attestations bind to host, OS, version, capability, installation, and current launcher identity. |
| Dashboard service registration | Systemd unit operations are bound to one frozen mutation-safe XDG root across planning, reads, writes, unlink, and rollback; Task Scheduler remains token-SID-bound. The ownership manifest binds exact interpreter and package bootstrap metadata/content identity; inspection, start, and restart revalidate both and reject drift. Installer-process and systemd-manager environment inputs are checked separately, and only matching variable names may enter diagnostics. Normal Linux retains `PrivateTmp`; positively identified WSL omits only that directive because its mount namespace rewrites ancestor identities, while namespace validation and all other unit controls remain mandatory. |
| Owned child processes | Shell-free bounded argv and I/O; atomic-at-creation Windows Job Objects or a dedicated Linux pidfd/subreaper supervisor that also contains session-escaping descendants and handles launcher parent death; Linux supervisor isolation from inherited target signal, pidfd, resource-limit, scheduler, affinity, priority, I/O-priority, ptrace, and proc-memory paths; policy readiness followed by an exact parent-owned GO commit only after durable lifecycle and I/O ownership; post-drain terminal completion receipts; deterministic timeout and interruption cleanup; Windows system helpers resolve through validated allowlisted native paths rather than CWD or `PATH`. |
| Privacy | Metadata-only default; bounded defensive redaction; secrets remain write-only in dashboard and CLI projections; finite retention; logs sanitize control characters and content-bearing failures. |
| Supply chain | Minimal runtime dependency; pinned build, audit, and workflow tools; immutable GitHub Action SHAs; identity-frozen hostile-config-free Git transport; full reviewed commit and clean-checkout identity before and after construction; bounded non-executable regular source paths materialized from independently rehashed canonical Git blobs rather than checkout-filtered bytes; private environment-reduced temp-first build whose bounded normalizer preserves every source-derived payload byte, canonicalizes LF only for a finite shared generated-metadata allowlist, rebuilds wheel `RECORD`, explicitly encodes byte-deterministic stored ZIP members and an RFC 1951 stored-block gzip stream, and applies one tar ownership, mode, and timestamp policy without host-zlib output; contained descendant cleanup and atomic no-clobber wheel/source-pair publication; hosted Windows and Linux construction/verification; wheel/sdist names, roots, version, dependencies, license, and committed MANIFEST-governed bytes checked independently and exactly; contiguous single-container ZIP/gzip/tar layouts with no prefixes, gaps, orphan records, noncanonical stored blocks, unapproved comments/extras/PAX keys, nonzero alignment padding, concatenated streams, or noncanonical trailing data; portable regular archive members with path-component, count, size, aggregate, and compression bounds; strict raw-UTF-8 generated metadata, wheel/sdist metadata parity, singleton headers, entry points, WHEEL tags, and RECORD hashes/sizes; exact installed-runtime vulnerability audit; Bandit; capability-gated native CodeQL analysis and upload where repository visibility and licensing permit it; machine-readable non-analysis evidence only for a recognized private/internal missing-entitlement response, with ambiguous probes failing closed; native dependency-diff review when GitHub exposes it; offline workflow security linting; no credential persistence in checkout steps. |

## Residual risk and non-goals

- Administrator, root, debugger, or same-account memory access can defeat local
  process secrecy. Agency Runtime is not a sandbox against its owner.
- Linux owned-process controls prevent the identity-approved target and its
  inherited descendants from using the guarded signal, pidfd, resource-limit,
  scheduler, affinity, priority, I/O-priority, ptrace, or proc-memory interfaces
  against their non-dumpable supervisor. They do not isolate a separately
  cooperating same-account process that already holds an applicable capability
  or ask the kernel to survive administrator/root action. Abnormal supervisor
  loss is detected by the missing terminal receipt and cannot be reported as
  success.
- Executable identity revalidation narrows repository and cross-account
  substitution, but portable Python does not provide one open handle that the
  operating system must execute. A same-account actor can still race the final
  revalidation and kernel open and is inside the stated local-user boundary.
- Capability-bound Windows scratch is ephemeral to one logon and host
  namespace. It prevents cross-account fallback and detects identity changes,
  but it is not isolation between hostile processes sharing the same trusted
  operating-system account and logon; that requires a separate broker/token.
- The master switch takes effect at runtime boundaries, not retroactively inside
  a model context. A clean Agency-on versus Agency-off comparison requires a
  fresh host session after each switch change.
- Specialist activation tokens are scoped bearer capabilities, not
  cryptographic process-identity attestations. MCP transport does not prove the
  caller is the child, so a compromised parent can consume a token and then
  launch a same-labeled worker; the receipt proves exact prompt retrieval for the
  correlated work unit and a native execution, not prompt delivery to, or
  consumption by, that child.
  Forged host-native evidence also remains outside this local protocol boundary.
  Current MCP-backed workers retain generic delegated attribution even when a
  concrete child worker ID is visible.
- Defensive redaction cannot recognize every secret or personal identifier.
  Do not enable content capture for data that must never be stored.
- The dashboard is not a remote, multi-user, or reverse-proxied control plane.
- Approved roster prompts and external model responses remain untrusted
  instructions. Deterministic and inference-assisted audit, quarantine, and
  review reduce risk but do not prove intent or make an approved prompt safe for
  authority it was not granted.
- A remediation queue receipt proves only that bounded rules were attempted
  against one exact source hash. It is not evidence that a repair is correct or
  executable, and it never substitutes for semantic review or activation
  approval.
- A remediation resolution event is likewise not authority by itself. Only an
  HMAC-verified marker with the exact queue, scan seal, selected provenance,
  candidate, audit, download, source, and transformation edges may move an item
  to history. Missing or mutated edges reopen the queue, and unsigned duplicates
  remain visible as quarantined anomalies.
- A configured inference result is advisory routing evidence, not proof of task
  fitness, task quality, or model identity. Only response telemetry can
  reconcile the actual provider/model; a LiteLLM router or requested alias
  remains a separate field.
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
- Full-roster and paired-comparison reports preserve their own evidence labels.
  Contract-only retrieval coverage and directional-claim eligibility do not
  establish superiority over a native host or another router.
- OpenClaw's finalize hook can request only a bounded revision and then permits
  the natural answer; it exposes no permanent deny result. Agency Runtime
  revalidates the retry and places a synchronous, payload-bound grant in
  `reply_payload_sending`; `message_sending` consumes its one-use dispatch seal.
  This closes the audited agent-reply paths, including audio-only delivery, but
  runtime inspection proves registration rather than delivery behavior. An
  unregistered hook, a future host path that bypasses modifying hooks, or a
  trusted same-process plugin at the same terminal priority remains outside the
  seal. OpenClaw support is therefore restricted to audited stable `2026.7.x`
  patches at or above `2026.7.1`, with live maturity tracked separately.
- Hermes `pre_verify` runs only on code-edit turns and exposes no permanent
  deny result. Agency Runtime spends one nudge and then uses its
  `transform_llm_output` replacement on every registered-plugin turn, so an
  unverified draft is not returned even when correlation or storage fails.
  Missing or disabled plugin registration remains outside Runtime's control,
  and a persistence failure deliberately leaves the correlated turn open.
- A public package signature, provenance attestation, and tagged release do not
  exist until the publication checklist records them; source state alone must
  not claim those guarantees.

## Verification

The release gate in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) is the
executable companion to this model. At minimum, run the warning-strict tests,
routing and full-roster contract evaluations, Ruff, Bandit, pip-audit, zizmor,
documentation validators,
artifact parity checks, and both Windows and Linux portability suites. A new
trust boundary or residual risk requires this document and the governing ADR to
change in the same review.
