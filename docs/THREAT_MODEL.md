---
title: "Threat Model"
status: active
category: security
created: 2026-07-12
updated: 2026-07-28
tags: [security, architecture, privacy, supply-chain]
related:
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
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
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/decisions/0071-bound-native-delegation-correction.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
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
| Persistent mutation authority | Granted to a normal owner CLI invocation or the owner dashboard bearer. Exact confirmation text, revision and generation compare-and-swap, immutable preparation, ownership checks, locks, rollback, and postconditions remain transaction-safety controls. Hook, MCP, broker, generated-host, and restricted brokerage identities remain read-only and do not inherit owner authority. |
| Agent activation policy | Bound to one canonical config and roster revision; protected coordinators remain enabled, and optional-agent changes are reversible without deleting governed definitions or history. |
| Resident manager binding | Compact, versioned, parent-only, and current-turn bound; complete upstream manager prompts do not accumulate in long-running conversations or enter children as worker directives. |
| Roster governance | Every upstream definition is content-addressed and accounted for as active, quarantined, or retired; audit findings and lifecycle transitions remain append-only and cannot be bypassed by a newer download. Every quarantine creates a source-bound, non-executable remediation attempt. Only exact registered rules may propose a repair; unknowns remain queued, and semantic audit plus explicit approval remain mandatory before activation. A resolution becomes authoritative only after keyed verification of its exact durable dependency closure; raw or ambiguous claims never suppress pending work. CLI/dashboard projections expose hashes, rule disposition, next action, and anomaly counts without raw prompt content. Runtime quarantine may retain bounded raw source evidence, while the packaged bundle retains hashes, receipts, findings, and approved rewritten artifacts instead of corrupt raw prompts. |
| Routing and composition plans | Bound to the exact classifier, configuration, roster, candidate, compatibility, and inference revisions; no conflicting or ineligible prompt is hydrated merely because it scored highly. |
| Routing and delegation evidence | Correlated to canonical trace, turn, work-unit, and outcome records; model-authored claims are not authoritative. |
| Specialist activation capabilities | Single-use, exact-version and work-unit scoped, stored only as digests, and recorded as retrieval rather than proof that a named specialist executed. |
| Managed host plugins | Exactly match the canonical generated bundle, install reversibly, retire only under exact ownership and native-detachment proof, and never claim native state without a postcondition. |
| Native release delivery | Portable and Windows wheels contain no Agency-owned executable; archive verification rejects executable names and structurally valid PE payloads under any filename. |
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
- A hostile repository may put a familiar executable in its working directory,
  a sibling directory reachable from a nested working directory, or a relative
  `PATH` entry, then replace a validated launcher before process creation.
- A compromised package or GitHub Action may enter through development,
  release, or CI dependencies.
- A package index, cache, release worker, or compromised signing boundary may
  substitute the wrong platform variant, a partial release set, an unsigned or
  wrong-publisher helper, or signed bytes that do not map to the reviewed
  unsigned build.
- Crashes and concurrent requests may cause partial writes, stale decisions,
  resource exhaustion, or evidence from one session to contaminate another.

## Enforced controls

| Boundary | Controls |
|---|---|
| Dashboard and HTTP | Literal loopback binding; strict `Host` and same-origin checks; separate per-process owner and broker bearers; the owner bearer may use the bounded configuration/control endpoints while the broker remains restricted to the exact read/computation allowlist; no permissive CORS; canonical exact-slug lookup and cursor validation; prompt-free bounded roster operations/revision history, immutable review projections, and credential-free inference projections; remote freshness and provider health remain explicitly non-probed unless separate evidence exists; CSP, COOP, and CORP headers; canonical content length; rejected transfer encoding; body, context, worker, response-page, DOM, and socket-deadline limits. The automatically supplied owner bearer is request isolation, not proof that a human is present. |
| Agency-wide master control | Canonical per-user `control.json` checked before Store, input parsing, or correlation; strict bounded schema; owner-private real parent chain; monotonic compare-and-swap generation; owner-private lock and exclusive temporary file; durable atomic replacement and verified postcondition; missing or invalid state fails enabled. Generated Codex and Claude hooks bind an absolute canonical control identity in their owner-managed manifests. The strict owner-private reader remains primary, including for a UAC-filtered owner token. Only after a strict security refusal may a positively identified restricted Windows caller use the stable-identity reader with negative proof for every mutation right, then recover the complete validated bound master document through the authenticated loopback dashboard. Invalid identities and unavailable or malformed brokerage fail enabled. |
| Host-scoped soft control | Canonical SQLite row per host; absent state is enabled at generation zero; status projects the committed generation; owner CLI and owner-dashboard mutations compare the observed generation under `BEGIN IMMEDIATE`, increment real transitions exactly once, and preserve no-op revisions. MCP, generated-host, broker, and restricted-Windows brokerage remain read-only; native lifecycle is never proxied through those identities. |
| Native lifecycle authority | Bare install auto-discovers installed supported harnesses and uses each harness's native registration, enablement, and trust lifecycle. Agency ships no independent Windows Hello verifier and exports no reusable authorization result. Exact install namespaces are closed-world parsed and serialize host work on the owner-private lifecycle lock. Owner CLI installation, rollback, native enable/disable, uninstall, roster rollback, configuration, and service operations retain their operation-specific preparation and postconditions without a second presence ceremony. MCP, hooks, broker, generated-host, and restricted brokerage paths remain read-only for persistent mutations. Codex activation verification is evidence-producing and cannot silently claim trust, loading, routing, specialist activation, or delegation. |
| Native release construction | Portable and Windows wheels contain the same reviewed Python package payload and differ only in required wheel metadata. Every `.exe` name and bounded structurally valid PE payload is rejected, including PE bytes hidden under a data filename. Like artifacts remain canonical and deterministic; missing, duplicate, cross-contaminated, cross-commit, or metadata-divergent sets fail. |
| Files and SQLite | Owner-only file mode or Windows DACL enforcement; real parent chains that exclude cross-account substitution; canonical config and custom policy namespaces are checked before cache use and after reads; a present custom policy must be a current-user-owned regular single-link file whose descriptor and path identity remain stable, with no POSIX group/other mutation or Windows non-owner mutation access. Windows SDDL trust checks consume the complete DACL with balanced, quote-aware ACE parsing, reject unknown or malformed shapes, and classify conditional grants at their maximum stated rights. A textual Windows SDDL owner alias is accepted only when native binary-SID comparison proves exact equivalence to the effective TokenUser. Config parents may retain safe read/traverse-only access while database parents remain private for sidecars; POSIX default-ACL rejection; symlink, reparse-point, hard-link, and SQLite-sidecar rejection; no-follow reads where available; bounded reads; stable identity checks; locked atomic replacement with exact rollback receipts; config-bound Store mutations and complete routing snapshots serialize against configuration writers, with mutation preconditions repeated inside the writer lock after revision validation; exact normalized DDL currentness preserves quoted literal bytes and covers security-critical constraints, indexes, and triggers; malformed HMAC text fails closed before constant-time comparison; SQLite transactions, foreign keys, uniqueness constraints, and read-only diagnostics. |
| Providers, configuration, and roster ingress | Credentialed remote providers require HTTPS; embedded credentials and ambiguous URL components are rejected; credentialed requests do not follow redirects; response bytes, models, identifiers, per-operation timeouts, total roster-fetch deadlines, and candidate counts are bounded. JSON and YAML boundaries reject duplicate keys, aliases, merge keys, non-finite numbers, excessive depth, and excessive node counts. Local directory ingestion rejects links, reparse points, and special entries; records exact basename bytes and stable identities for the manifest root and every traversed directory; enforces one source-wide entry budget; and revalidates every receipt after file reads. Every imported definition enters a content-addressed candidate revision. Deterministic and configured-inference audit results, findings, active-basis identity, and lifecycle transitions are append-only. A missing, invalid, degraded, stale-basis, or failing required audit cannot approve or activate a candidate; nightly delta synchronization never auto-activates, deletes, or replaces the last approved revision. |
| Selection and prompt composition | Turn intent, expertise selection, and execution topology are separate decisions. Hard host, platform, tool, permission, activation, and policy filters run before inference. Configured inference is mandatory for selection-requiring turns and exhausts its bounded declared chain before entering an explicit degraded state; deterministic candidates are never relabeled as inferred. Inference receives bounded structured cards, never full prompt bodies. Compatible-set construction enforces `requires`, `conflicts_with`, authority, context mode, independence, and resource constraints before hydration. One directive specialist per worker is the default; implementers and independent reviewers remain isolated. The resident managers remain parent-only and cannot become domain workers. |
| Restricted Windows CLI brokerage | Direct owner-private access remains primary. Only an exact restricted-token refusal may use the owner-private authenticated dashboard for bounded master, host, agent, roster, route, search, explain, and policy reads/computations. Bulk roster pages expose compact activation state and one exact-agent lookup remains read-only. Every Store-backed response binds one canonical config path/revision, active and desired Store paths, `store_restart_required=false`, and roster revision. Explicit config identities are never redirected; control mutation, delegation, setup, arbitrary Store calls, and generic configuration mutation are never proxied. Missing, stale, malformed, mismatched, oversized, unavailable, or conflicting evidence fails closed without retry. |
| Native processes and delegation | Argument arrays without a shell; absolute-only executable discovery that ignores empty, dot, relative, and current-directory `PATH` entries; inert repository-marker discovery before the first Git call excludes every containing repository ancestor from both search and final lexical/resolved candidate acceptance; repository-independent host lifecycle commands prepare and execute from one owner-private working directory while retaining every ambient marker-derived repository boundary; canonical regular targets outside the target repository; Windows link/reparse rejection and POSIX launcher-symlink canonicalization; every executable or wrapper artifact occurs at one exact ordered argv position, with the first identity covering `argv[0]`; frozen ephemeral or persistent identities cover those same paths and are revalidated immediately before process creation; minimal allowlisted environment; task content through standard input when supported; bounded output and time; kill-on-close Windows Job membership assigned atomically through `STARTUPINFOEX` at process creation, or a dedicated non-dumpable Linux subreaper with a pre-opened `/proc` children descriptor and pidfd signaling. Before `exec`, the Linux target enters a separate session, arms parent-death signaling, and inherits a `no_new_privs` seccomp policy denying supervisor-targeted signals, queued signals, pidfd acquisition, resource-limit changes, scheduler and affinity mutations, priority changes, and I/O-priority changes while retaining normal own-child operations. A private policy acknowledgement precedes external `READY`, but target code remains blocked until the parent durably owns containment state and every I/O worker, then sends exact `GO\n` plus EOF as a one-way commit. Exact cancellation prevents pre-commit execution; ambiguous post-commit interruption drains the full tree before propagation. Exactly one final `COMPLETE` after descendant drain and resource close is required. Missing, malformed, duplicate, out-of-order, or truncated receipts and unavailable strong-containment primitives fail closed; bounded versioned unit-aware specialist assignment; validated dependency DAG; stable event-driven ready queue; strict failure-gated successors; mutating Git operations suppress hooks, inherited Git configuration, fsmonitor, executable filters, merge drivers, text converters, and pathspec magic; merge only after proven success. Restricted Codex Windows scratch requires a file-ID-bound host capability under the owner-private visualization namespace, an authoritative effective-token logon SID, protected child DACLs, and link-safe identity-bound cleanup. Process-local authority never crosses `exec`: every child independently reattests only its exact randomized thread-bound allocation against the canonical host marker, root/parent identity, DACL, and mutation access; ambiguous roots and repository fallbacks fail closed. |
| Evidence and finalization | Fresh printable trace and session IDs bounded to 512 UTF-8 bytes before lookup or indexed persistence; privacy-safe request fingerprints and durable typed turn classifications; explicit work-unit identity; exact Agency and host-native tool allowlists rather than namespace-suffix trust; duplicate and missing results fail; bounded work-unit extraction. Selection is a plan, not load evidence. Each isolated unit the native host actually starts requires a digest-only single-use capability bound to its ready-recipe slug, version, hash, and work unit; completion separately correlates retrieval with a generic native worker or tool-run receipt and never treats unauthenticated MCP access as named-specialist execution. Declined, skipped, or retry-exhausted units close with explicit nonexecution evidence rather than a fabricated activation; a host-merged unit is recorded as skipped with a bounded merge reason. Disabling an optional agent invalidates replay, preparation, consumption, and affected ready-turn completion; oversized exact prompts fail before selection or activation; mutation and terminal close transactions are mutually exclusive; terminal outcomes are monotonic and cannot be reopened by Stop feedback; one corrective pass is the maximum; protocol input and output remain strict finite JSON; success is recorded only after verified outcomes; LiteLLM provenance is granted only by the callback-owned Store ingress; final headers reconcile against canonical SQLite evidence and reject spoofed or ambiguous fallbacks. |
| Installation and canaries | Canonical bundle digest and exact managed-tree comparison; unexpected files force replacement; owner-private staging; backups and rollback; native inventory postconditions; interpreter plus package-bootstrap lexical/resolved metadata and content identities persisted in the managed install manifest; launcher drift or unproven identity makes maturity stale and blocks registration; Windows permission setup rejects restricted or indeterminate tokens before DACL mutation; scheduled-task definitions use BOM-bearing UTF-16 input, token-SID-bound identity, bounded Base64/UTF-8 COM inspection, strict schema normalization, semantic execution checks, and exact pre-mutation requery; isolated canary homes receive an owner-only directory policy before credentials exist; bounded link-resistant authentication copy hardens the empty destination before writing; nonce-bound proof; attestations bind to host, OS, version, capability, installation, and current launcher identity. Before a current-profile Codex canary invokes a model, a strongly contained, bounded read-only app-server exchange selects only `agency-preflight@agency-runtime`, requires the canonical eight events exactly once with valid current hashes, and requires each to be enabled and `trusted`; warnings, errors, missing or duplicate events, unknown shapes or statuses, timeouts, disabled, untrusted, or modified entries fail closed. Only sanitized counts, event names, statuses, and current hashes survive; command strings, source paths, unrelated hooks, and raw process output do not. The exact nonce-bound parent task and canonical direct child goal are distinct: routing and replay persist the direct child goal while the general native-child goal-hash equality guard remains unchanged. A proven owned-process timeout projects only a fixed allowlisted reason, never raw output. Current-profile activation verification then uses initial inspection, exactly one canary, and final inspection; success requires the fresh invocation's persisted proof digest, trace, scope, and installation identity to match final inventory, so an older attestation cannot rescue a failed or malformed attempt. Codex product trials write one canonical trusted-project entry only inside the disposable profile, retain the workspace-write sandbox with no added directory, correlate the exact executed prompt to the activation snapshot, and require a bounded prompt-derived sentinel written by that invocation before grading. Persistent profile configuration is excluded; preexisting, missing, mismatched, linked, oversized, or uncleanable proof fails closed. |
| Host integration uninstall | A write-free outer SHA-256 plan digest binds the selector, canonical hosts, target, install identity, nested authority binding, status, and exact native command sequence. The nested binding covers target/parent/runtime/retention identities, plugin version, the full prepared platform/launcher projection and every executable or wrapper artifact identity that can participate in process creation, allowlisted host-profile environment, and applicable plugin, marketplace, gateway, or ZCode facts. Native provenance uses a closed set of documented path aliases; invalid, relative, or conflicting aliases fail even when one alias is correct. A separate aggregate native binding covers the operation UUID, canonical host transitions, outer plan hash, hash of each per-host binding and exact retained destination, and fixed `runtime-data-and-marketplaces.v1` preservation and `retained-owned-bundles.v1` recovery policies. Generic mutating install, rollback, native enable/disable toggle, prepared Codex refresh, and uninstall serialize on one owner-private host-integrations lock; uninstall re-plans and revalidates its full binding under that lock. Only bounded schema-2 Agency ownership with an exact file/directory set, real regular entries, stable identity, and no links or reparse points may proceed. Installed plugin and observed marketplace sources must bind to the managed source, but a mismatched marketplace blocks without granting deletion authority; OpenClaw must be proven stopped; ZCode removes only exact owned handlers after two unchanged-byte checks under the Agency lifecycle lock. Native detachment is proven before the unchanged tree is atomically retained at `backups/<host>/uninstall-<operation_uuid>`; recovery names that exact tree with `--backup`. Hermes may retain only its exact disabled Agency inventory row as the proven detachment state. On Windows, final ownership validation, rename, destination proof, and bounded restoration follow the exact source directory through one open handle, closing the pathname-swap window. A bounded owner-private journal records intent only after native Windows authority and locked revalidation but before the first host mutation, then records each host outcome without native output or configuration content; denial writes no journal, and a failure reports every later host as `not_attempted`. Codex/Claude marketplace registrations remain user configuration and marketplace-only residue cannot select `--all` unless a future install ledger proves exclusive creation ownership. Unknown, drifted, partial, or changed state fails nonzero with files retained. Package, Agency Runtime configuration, Store, roster, evidence, backups, dashboard service, unrelated host configuration, and marketplace registrations are never removed; no purge or dashboard/model-facing uninstall endpoint exists. External same-account ZCode writers do not honor Agency's lock, so a write in the final read-to-replace interval remains a residual lost-update race; the two byte checks are not filesystem compare-and-swap, and external ZCode configuration must stop before applying uninstall. |
| Host integration recovery rendering | Every successful uninstall names the exact operation-bound retained tree with `--backup`. POSIX uses shell-safe joining. Windows output targets an attended PowerShell session, starts with the `&` call operator, single-quotes every argument, and doubles embedded quotes; path spaces and metacharacters therefore remain literal instead of becoming shell syntax. |
| Dashboard service registration | Systemd unit operations are bound to one frozen mutation-safe XDG root across planning, reads, writes, unlink, and rollback; Task Scheduler remains token-SID-bound. The ownership manifest binds exact interpreter and package bootstrap metadata/content identity; inspection, start, and restart revalidate both and reject drift. Installer-process and systemd-manager environment inputs are checked separately, and only matching variable names may enter diagnostics. Normal Linux retains `PrivateTmp`; positively identified WSL omits only that directive because its mount namespace rewrites ancestor identities, while namespace validation and all other unit controls remain mandatory. |
| Owned child processes | Shell-free bounded argv and I/O; atomic-at-creation Windows Job Objects or a dedicated Linux pidfd/subreaper supervisor that also contains session-escaping descendants and handles launcher parent death; Linux supervisor isolation from inherited target signal, pidfd, resource-limit, scheduler, affinity, priority, I/O-priority, ptrace, and proc-memory paths; policy readiness followed by an exact parent-owned GO commit only after durable lifecycle and I/O ownership; post-drain terminal completion receipts; deterministic timeout and interruption cleanup; Windows system helpers resolve through validated allowlisted native paths rather than CWD or `PATH`. |
| Privacy | Metadata-only default; bounded defensive redaction; secrets remain write-only in dashboard and CLI projections; finite retention; logs sanitize control characters and content-bearing failures. |
| Update discovery | Closed-world release/main/version/ref selectors resolve to one full commit through configured GitHub CLI access or fixed-origin redirect-free public HTTPS under one total timeout and response budget. The CLI child receives only an allowlisted environment; unrelated secrets do not cross the process boundary. Official repository URLs, semantic tags, refs, full SHAs, text controls, and target shapes are validated before an owner-private atomic cache write and revalidated on every read. Concurrent refreshes merge under a process lock. Only semantic release ordering produces automatic notices; a different mutable branch/ref is not called newer. Dashboard and startup projections are read-only, hooks/MCP perform no update I/O, and attended plans pin the exact SHA while executing no pip, host, trust, service, or release mutation. |
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
  Codex MultiAgentV2 also flattens the native tool namespace and name before
  command-hook delivery. Agency accepts only the exact current flattened name,
  exact persisted task label and goal, and bounded matching result path, then
  atomically claims the sole unconsumed child start created after that grant.
  Codex does not expose the spawning tool-use ID on `SubagentStart`, so this is
  temporal/cardinality correlation rather than cryptographic process identity;
  hostile same-account host/plugin code remains inside this residual boundary.
  Every accepted Codex spawn spelling requires a unique unclaimed lifecycle
  row. Bounded JSON decoding preserves whether the response supplied a child
  identity so it must match that lifecycle on first use and replay; V2 also
  requires a rooted AgentPath. Idempotent replay requires the exact consumed
  token digest and tool-use ID.
  Forged host-native evidence also remains outside this local protocol boundary.
  Current MCP-backed workers retain generic delegated attribution even when a
  concrete child worker ID is visible.
- Defensive redaction cannot recognize every secret or personal identifier.
  Do not enable content capture for data that must never be stored.
- The dashboard is not a remote, multi-user, or reverse-proxied control plane.
- Update metadata and its private cache can be unavailable or stale within the
  documented TTL. Resolution proves the selected official commit identity, not
  that an unsigned prerelease is safe, signed, published, newer than a diverged
  checkout, or authorized for installation. An attended printed command is not
  execution, activation, or release evidence.
- The owner dashboard bearer is not proof of human presence when a model can
  control that browser session; possession deliberately conveys the same local
  owner authority as a normal CLI invocation. A caller that should remain
  read-only must receive only the broker, hook, MCP, generated-host, or
  restricted brokerage surface. The Codex install path still does not prove
  hooks loaded in a new host process; activation requires separate runtime
  evidence.
- Host-integration uninstall does not prove already-running host processes have
  unloaded previously loaded Agency code; affected hosts require a fresh
  session. It deliberately retains the retired bundle and all existing backups,
  so it does not reclaim all disk space or erase historical runtime data.
- The host-integrations lock serializes Agency writers but cannot exclude an
  external same-account ZCode config writer. A write between Agency's final
  unchanged-byte read and atomic replacement can still be lost; the checks are
  not filesystem compare-and-swap, so external ZCode configuration must stop
  during uninstall.
- The packaged Windows verifier is reviewed and identity-pinned but unsigned.
  ADR-0098's source implementation now derives portable and `win_amd64`
  producer profiles and independently verifies their merged three-artifact
  unsigned review set; the portable wheel retains audit source/provenance/
  and excludes every bounded structurally valid PE. Hosted Windows/Linux
  producer and merge proof remains open under AR-160 because repository Actions
  billing is disabled. The retired helper has no signing or attended-presence
  release gate.
- Native lifecycle coordination assumes the local operating-system account,
  installed package, and Python interpreter are trusted. Same-account code
  replacement, monkeypatching or private reflection, debugger/memory access,
  and raw SQLite writes can bypass Python-level control flow. Stronger
  same-account isolation requires signed/package policy or a separate broker
  and token boundary.
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
- A product-trial sentinel proves one exact write inside the bound workspace
  under the evaluated invocation. It does not exhaustively prove the native
  host's sandbox implementation or absence of every write the host itself may
  perform in operating-system-managed temporary locations.
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
per-variant artifact-set parity and signature checks, and both Windows and Linux
portability suites. A new
trust boundary or residual risk requires this document and the governing ADR to
change in the same review.
