---
title: "Changelog"
status: active
category: release
created: 2026-07-10
updated: 2026-07-21
tags: [release, changelog]
related:
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# Changelog

This project follows semantic versioning after the first published release.
Until then, changes accumulate under `Unreleased`; the package version remains
`0.1.0` and no public release or tag is claimed by this repository state.

Faithful commit history and reasoning-rich implementation notes remain in the
[worklog registry](docs/worklog/README.md). This file summarizes user-visible
changes rather than duplicating every commit.

## Unreleased

### Fixed

- Unsafe deterministic and inferred selection candidates now have to clear the
  configured confidence floor before caching, prompt hydration, or activation.
  Agency runtime/dashboard questions prefer the purpose-built multi-agent
  systems specialist, while ambiguous input abstains instead of accepting a
  weak semantic collision.
- Native-child delegation events now reconcile to the exact consumed activation
  receipt, so task labels cannot strand valid child evidence in a repeated Stop
  retry. Shared child routes also preserve multi-unit plans, zero-TTL
  singleflight results, complete parent correlation, and provider protocol
  settings across edits.
- Dashboard CLI-provider staging now removes stale HTTP credentials before
  validation.
- Companion-policy validation now uses the full active roster while selection
  still uses the host-eligible subset, preventing valid cross-platform agents
  from appearing missing on Windows or Linux routes.
- Corrected Codex activation guidance to use the terminal TUI hook-review
  surface, distinguish Codex Desktop connector setup, and expose the approval
  surface and launch command in structured installer evidence.

### Added

- Codex subscription providers can now choose a validated reasoning effort in
  both the CLI and dashboard. Account model discovery reports supported levels,
  and the isolated inference process receives the selected override without
  inheriting unrelated host configuration.
- A durable Agency-wide master switch shared by `agency on|off --global` and
  the authenticated dashboard. Host adapters and protocol surfaces consult it
  before Store creation, correlation, routing, prompt activation, delegation,
  model evidence, or finalization, enabling clean fresh-session A/B testing
  without unregistering integrations or erasing history.
- A compact, protected resident contract for `agents-orchestrator` and
  `chief-of-staff`, with explicit manager authority and an explainable no-match
  or justified-abstention fallback that does not append their complete upstream
  prompts on every turn.
- Reversible config-backed per-agent availability controls in the CLI and
  authenticated dashboard, with preserved roster history and protected default
  coordinators. Bounded exact-slug lookup keeps every governed agent reachable
  beyond the first dashboard page without raising response or DOM limits.
- Durable configuration identity shared by CLI and dashboard across reboots,
  with strict validation of the installed service manifest before it may select
  a non-default config path.
- A bounded dashboard evidence view for historical specialist activations,
  separated from current-turn state.
- Native, reversible host installation plans for Codex, Claude Code, Hermes,
  and OpenClaw, with explicit discovery-to-canary maturity.
- A dependency-light MCP stdio server and native Codex/Claude hook bridges.
- An optional, idempotent LiteLLM SDK callback and proxy callback object.
- A loopback-only authenticated operations dashboard with route inspection,
  evidence views, roster controls, host controls, and retention maintenance.
- Optional current-user dashboard services for Windows Task Scheduler and Linux
  `systemd --user`, installed by default with a mutation-free
  `agency install --no-dashboard` opt-out and explicit lifecycle commands.
- Structured dashboard configuration backed by the same typed, locked, atomic
  writer as CLI configuration, including ordered providers and write-only
  secrets.
- A responsive Signal Observatory with live bounded activity, accessible
  source-owned charts, animated event transitions, and reduced-motion and
  forced-colors support, plus a packaged first-party favicon that keeps browser
  console verification free of missing-asset noise.
- Prompt-free dashboard roster operations with division, capability, authority,
  host, platform, and tool filters; bounded contract/revision history; an
  immutable quarantine review queue; and an inference view that separates
  configured providers from persisted model evidence and recent failures.
- Versioned routing, policy, delegation, and 1,000-agent performance evaluation.
- A deterministic `agency eval full-roster` contract gate across every packaged
  approved agent, including identity-free probes, dual-retriever participation,
  hard negatives, abstention, compatibility, and state-aware turn cases. A
  separate `agency eval compare --input` validator pairs bounded independently
  collected native-only and Agency observations without claiming superiority.
- Content-addressed roster candidate audits, findings, lifecycle history, active-
  basis approval gates, delta-only upstream synchronization, and a read-only
  nightly review workflow that never auto-activates or deletes an agent.
- Exact-hash ingestion remediation with bounded offset rules, reviewed semantic
  projections, immutable runtime quarantine evidence, and HMAC-authenticated
  resolution authority. Unknown or ambiguous repairs stay queued, while raw
  unsigned resolution claims are reported as anomalies and cannot suppress work.
  Successful required-inference audits reconcile eligible repairs within the
  same ingestion instead of leaving stale pending queue entries.
- Governed bundled internationalization, payments and billing, and
  test-automation specialists plus an explicit generated availability registry
  for every companion-policy route.
- Windows and Ubuntu CI matrices plus isolated wheel smoke checks.
- Guided add/move/remove configuration for an authoritative four-entry provider
  chain, including authenticated Codex and Claude CLI judge transports.
- Persistent host-scoped soft controls shared by CLI, dashboard, MCP, and
  generated host command/skill surfaces, plus explicit `--native` lifecycle
  control.
- Generation-checked host soft controls whose committed revision is shared by
  CLI, dashboard, MCP, and generated host surfaces.
- A nonmutating host-canary readiness report and exact-confirmed, nonce-bound
  live workflow with content-free fingerprinted attestations.
- A self-contained threat model, release gate, code of conduct, issue
  templates, pinned dependency groups, CodeQL, capability-aware dependency
  review, Dependabot, and offline workflow auditing for open-source operation.
- Strict bounded JSON, YAML, and regular-file readers shared by configuration,
  protocols, native inventory, provider responses, roster ingress, and
  persisted projections.
- Capability-bound ephemeral scratch for restricted Codex processes on
  Windows, including nested workers, private child-process `TEMP`/`TMP`, and
  Git worktrees without falling back into a broadly writable repository.
- A global `agency --version` command backed by the installed package version.

### Changed

- Codex installation now remains `activation-required` after native
  registration until the user approves Agency hooks through `/hooks` and
  `agency install --agent codex --verify-activation` proves routing,
  finalization, and the response header in the normal profile without using
  Codex's hook-trust bypass.
- Release artifacts are now built from the canonical bounded regular-file payload
  in the reviewed Git commit instead of physical worktree bytes. This keeps clean
  Windows checkouts with line-ending filters from producing noncanonical wheels
  or source archives; unsafe sources and partial destinations fail closed while
  a bounded post-build pass preserves every source-derived payload byte,
  normalizes line endings only for an explicit generated-metadata allowlist,
  rebuilds wheel `RECORD` from those normalized bytes, and normalizes ZIP, gzip,
  tar, ownership, mode, and timestamp container metadata to one
  platform-independent policy. Canonical wheels use explicitly encoded stored
  ZIP members, and canonical source distributions use an owned RFC 1951
  stored-block gzip stream rather than host-zlib output, making the physical
  bytes stable across supported Python and operating-system runtimes. The
  independently implemented and invoked byte-strict distribution verifier now
  also holds stable artifact identities, enforces physical and manifest bounds,
  validates backend-source DEFLATE consumption, independently parses the
  canonical stored output, decodes core-metadata bodies from strict raw UTF-8
  bytes, checks wheel/sdist metadata parity, and rejects
  noncanonical ZIP, gzip, tar, comment, extra-field, PAX, padding, gap, and
  trailing-byte layouts.
- The warning-strict 100% line-and-branch gate now includes the canonical
  builder, bounded container normalizer, command-scoped clean-checkout probe,
  shared declarative release contract, trusted Git transport, and independent
  distribution verifier.
- Hosted Windows and Ubuntu builds now exchange their canonical wheel/source
  pairs through a dependent byte-parity gate; only the byte-matched Ubuntu pair
  proceeds to cross-platform installation smoke tests.
- Static security analysis now covers maintained release and governance scripts
  as well as the runtime package.
- Delegation suggestions now route each bounded work unit against the complete
  revision-stable approved and enabled roster, require configured inference for
  that semantic decision, and build the smallest sufficient compatible closure.
  No-match remains explicit; protected managers coordinate the parent and never
  masquerade as domain workers.
- Delegation DAG execution now releases a child as soon as all of that child's
  prerequisites succeed, while recursively skipping failed descendants and
  continuing independent branches without a topological-level barrier.
- Header, skill, specialist, delegation, and model evidence is correlated to the
  current turn trace while retaining session-level audit history; missing
  finalization correlation now fails closed.
- Canonical configuration, custom policy, and Linux dashboard-unit paths now
  require mutation-safe parent namespaces. Systemd manager-only runtime or
  credential variables block service mutation with names-only diagnostics.
- Dashboard host-toggle responses now use the service's bound master-control
  identity, including custom runtime-control homes.
- Delegation execution and Stop retries are reconciled against authoritative
  current-turn events, including public MCP and sanitized native tool names.
- Main-agent specialist instruction injection has an explicit count and total
  character budget so context pressure does not grow with session length.
- Turn classification and request fingerprints are durable across separate hook
  processes; terminal outcomes are monotonic and evidence writes cannot race a
  turn close.
- Preflight signal input, work-unit detection, suggestion persistence, and
  combined context are bounded before iteration or storage.
- Claude retry exhaustion terminates without another Stop loop. OpenClaw retries
  are revalidated and recorded within that host's bounded-revision contract,
  whose lack of a permanent deny result remains explicit.
- Hermes consumes one documented code-edit `pre_verify` continuation, then
  records exact retry exhaustion and relies on bounded safe output replacement
  for every turn that does not reach an authoritative accept.
- LiteLLM receipts separate the requested alias, router/model group, actual
  provider, and actual model using bounded StandardLoggingPayload evidence;
  request callbacks no longer close the surrounding Agency turn.
- Provider-qualified LiteLLM router aliases are reconciled as router evidence,
  never promoted to the actual model; without distinct deployment telemetry,
  the actual model remains explicitly unavailable. Unavailable and failed
  header states retain a verified LiteLLM router name.
- Long-lived LiteLLM callbacks with omitted configuration reload the
  Store-bound file-aware config for each event, so adapter enablement,
  disabled-agent, skipped-model, capture, and routing-policy changes apply
  without a worker restart. Explicit callback config remains immutable.
- Launch-critical executables, interpreters, wrappers, and service managers are
  rejected when their canonical parent namespace permits cross-account
  replacement, with trust rechecked immediately before process creation.
- Persistent dashboard and native-host launchers now bind the exact
  interpreter and package bootstrap content/identity in managed manifests;
  drift makes host maturity stale and blocks lifecycle execution until
  reinstall.
- Restricted Windows children independently reattest the exact thread-bound
  scratch allocation after process creation instead of inheriting a
  process-local parent authority claim.
- Linux dashboard unit writes and rollback honor `XDG_CONFIG_HOME` only through
  a real, owner-safe namespace that remains identity-stable for the transaction.
- Claude Code and Hermes registration now require an explicit native
  `enabled: true` proof; inventory presence with an omitted state remains
  unknown and cannot be promoted to registered or enabled.
- Canonical runtime configuration and companion-policy reads now reject
  cross-account-writable parent namespaces; restricted-host capability paths
  create missing private descendants through their attested boundary.
- The dashboard header and Route Lab remain neutral and disabled until an
  authoritative Agency master-state generation has loaded.
- `agency agents list --json` now returns `{config_path, agents}` so automation
  can verify which policy file supplied the activation view.
- A versioned state-aware classifier separates acknowledgement, conversation,
  control, continuation, new intent, and revision from specialist-selection and
  execution decisions. Only a proven pure acknowledgement may use the
  no-selection path, and exact runtime controls use their dedicated path.
  Selection is a plan: only isolated units the native host actually executes
  require exact one-use activation and a reciprocal native receipt.
- Compatible specialist sets now enforce requirements, conflicts, authority,
  context mode, independence, host, platform, tool, permission, and resource
  constraints before prompt hydration. Incompatible but useful roles become
  separate work units instead of competing prompts in one context.
- Every native child runs a bounded Agency preflight for its exact assignment;
  it receives only that unit's specialist capsule and correlation recipe, while
  native Codex, Claude Code, OpenClaw, or Hermes lifecycle remains authoritative.
- OpenClaw now enforces final-only delivery with synchronous full-payload seals
  and one-use outbound markers on its audited release line, instead of treating
  a bounded draft-revision request as permanent denial.
- Pull requests use GitHub's native dependency-diff review when the repository
  exposes that capability. The private-repository fallback installs the normal
  declared runtime dependencies plus pinned `pip-audit==2.10.1`, then enforces
  the exact installed-runtime vulnerability audit without installing unused
  security extras or requiring a billable security product.
- Native CodeQL analysis and upload run when repository visibility and GitHub
  Code Security licensing expose that capability. Private or internal
  repositories with a positively recognized Code Security-not-enabled response
  skip CodeQL initialization, publish short-lived machine-readable capability
  evidence that analysis was not performed, and continue to enforce Bandit,
  offline workflow auditing, and the exact installed-runtime vulnerability audit
  without executing an unlicensed analyzer. Ambiguous authorization, rate-limit,
  malformed, and not-found responses fail closed.
- Routing cache and session state now include roster, configuration, and policy
  fingerprints; zero-signal routing abstains.
- Agent availability reads use a file-identity-aware configuration cache, so an
  unchanged preflight parses policy once while external atomic edits invalidate
  on the next routing read.
- Provider fallthrough rejects semantically invalid results and reports
  cumulative decision latency.
- Delegation execution gates dependents on successful prerequisites and merges
  only successful predecessor work.
- Runtime storage defaults to metadata-only capture and a 30-day retention
  policy when the dashboard applies maintenance.
- Dashboard activity now uses a consolidated metadata-only live endpoint,
  visibility-aware single-flight polling, stable revisions, and capped retry
  backoff while keeping host discovery and configuration off the fast path.
- Dashboard unknown and no-host states are now explicit instead of implying a
  successful disabled or detected state; accessible contrast, focus, mobile
  navigation, reduced-motion, and forced-colors behavior share one reviewed
  visual contract.
- CLI secret updates now use standard input or a hidden prompt instead of
  process arguments, and configuration writes reject stale revisions and
  invalid schema before replacement.
- Companion-policy validation now covers action and division routes, skips
  inactive roster-gated specialists with a recorded reason, and exits nonzero
  for missing enabled or unclassified routes. Policy evaluation includes
  resolved-companion regression gates.
- Configured inference is mandatory for every specialist-selection decision.
  Exhausting the typed provider chain now records an explicit degraded result
  and cannot relabel deterministic retrieval as inferred; legacy judge and
  Ollama settings apply only when no typed chain exists, and deterministic
  routing remains an explicit no-provider mode.
- Codex and Claude canaries use isolated temporary plugin profiles and preserve
  real-profile native facts separately; only current-profile attestations can
  promote native inspection maturity.
- Oversized CLI, installer, dashboard-service, configuration, delegation,
  selector, LiteLLM, and SQLite facades are split into cohesive modules while
  preserving their public and monkeypatch compatibility surfaces.
- Dashboard activity omits discarded sensitive fields at query time and reads
  materialized snapshot summaries; the representative 1,000-row projection is
  about 3.4 times faster and large snapshot projection no longer reparses
  manifests on every request.

### Fixed

- Isolated Codex and Claude canaries now preserve the authoritative global
  Agency mode instead of defaulting a temporary home back to enabled. Explicit
  `agency` and `native-only` modes enforce opposite header/evidence contracts,
  reject control drift, and keep native-only observations out of Agency
  attestation history. Managed hook commands bind the canonical master-control
  identity explicitly, with authenticated dashboard recovery limited to
  positively identified restricted Windows hook processes.
- Custom companion-policy ownership on Windows now compares the owner's native
  binary SID with the effective TokenUser, accepting an SDDL alias only when it
  proves that exact identity. Package-owned launchers also configure standard
  streams as strict UTF-8 before CLI or host-protocol dispatch.
- Directory roster ingestion now binds every traversed directory to bounded,
  deterministic no-follow entry receipts, rejects links, reparse points, and
  special entries, and revalidates exact names and identities after all file
  reads under one source-wide budget. Add, remove, rename, and replacement races
  therefore fail closed without depending on directory timestamp behavior.
- Upgrades now refresh only immutable hash-proven legacy package starter rows
  to current audited bundled contracts, preserve custom and synced specialists,
  and report additions separately from migrations. Per-unit selection also
  filters write-intent candidates by reviewed mutation authority before
  inference, preventing a review-only specialist from receiving implementation
  or documentation changes.
- Dashboard service status and open recovery now validate the installed
  launcher identity before deciding whether a schema-v2 manifest is current,
  preventing healthy services from reporting a false repair recommendation.
- The restricted-Windows dashboard broker now reads its own authoritative
  master-control document through the strict owner-side boundary, preserving
  authenticated off/on control after the document is first materialized.
- Windows dashboard lifecycle transitions now wait a bounded time for the exact
  prior runtime generation to exit after Task Scheduler reports idle.
- Restricted host consumers now consult validated authenticated dashboard state
  when local master-file integrity cannot be proven, so a deliberate global off
  state bypasses routing and evidence work instead of silently failing enabled.

- Concurrent host-control writers no longer overwrite each other. SQLite
  compares the observed generation in the publishing transaction, increments
  only real transitions, preserves no-op generations, and returns explicit
  dashboard HTTP 409 or CLI/MCP conflicts for stale choices.
- Agency-off protocol and CLI surfaces bypass before schema, configuration,
  Store, routing, or delegation work while retaining only the explicit
  administrative status/control boundary.
- Restricted Windows `agency status` and host-scoped `agency on|off` now use
  the authenticated local dashboard only when the exact restricted-token Store
  boundary refuses access. Strict snapshot and mutation-receipt validation
  replaces the previous ACL traceback with truthful results or a sanitized
  nonzero diagnostic. Brokered master and host receipts must prove the exact
  requested state and legal no-op or single-increment generation; stale,
  opposite, jumping, or impossible effective states are never retried
  automatically.
- Restricted Windows agent list and toggle commands now broker only the default
  installed identity through compact bounded activation pages, one exact-agent
  lookup, and one revision-checked mutation. Bulk pages do not expose selector
  descriptions or taxonomy. Explicit config paths remain direct, and protected
  coordinators remain immutable.
- Restricted Windows search, route, explain, and policy commands execute the
  complete read-only operation inside the authenticated dashboard service and
  return bounded outputs tied to one config, Store, and roster snapshot. They do
  not export the full selector catalog. Delegation, setup, arbitrary Store calls,
  and generic configuration mutation are not proxied; expected permission
  failures return controlled nonzero diagnostics before execution or fabricated
  evidence.
- CLI route and explain diagnostics now bind the single exact verified enabled
  host installation when one is available. Candidate ranking and selected IDs
  therefore use the same host capability context instead of reporting an
  unrelated fallback from an unproven generic shell.
- Dashboard Store-bound responses carry the active and desired Store paths.
  Configuration drift that requires a service restart disables Store-backed
  reads and controls rather than silently mixing old SQLite state with new
  policy. Config-bound Store operations serialize against config writers, and
  agent-toggle preconditions are repeated inside the revision-checked writer
  transaction.
- Mixed numbered delegation input that includes dependency language now fails
  closed until those cross-unit edges can be represented, instead of silently
  dispatching an incorrect independent plan.
- The release toolchain pins the current stable `build==1.5.0` instead of the
  publisher-yanked 1.5.1 artifact.
- Concurrent SQLite initialization now distinguishes identity-stable transient
  sidecar trust-probe failures from replacement or persistently unsafe ACLs,
  preserving fail-closed storage checks without breaking safe WAL churn.
- Production canary, host parsing, and delegation-evaluation checks no longer
  depend on optimization-sensitive Python assertions; optimized interpreters
  retain the same fail-closed behavior.
- Windows delegated-process cleanup resolves `taskkill.exe` through the
  validated native system directory instead of CWD or `PATH` search.
- Windows dashboard task registration writes a BOM-bearing UTF-16 definition,
  accepts only Task Scheduler's allowlisted canonical default elisions, and
  reads native task XML through a bounded UTF-8/Base64 COM transport instead of
  the ambient console code page.
- Windows dashboard start and restart reject owned-but-drifted definitions and
  revalidate semantic equality immediately before any `/End` or `/Run` action.
  The trigger account is resolved from the process-token SID rather than
  mutable `USERNAME` or `USERDOMAIN` values.
- Expired preflight recovery now atomically removes every trace-scoped evidence
  record before returning the trace to service, and stale owners cannot mark the
  recovered turn ready or failed.
- Public evidence and finalization mutations accept only an active explicit
  preflight in `ready` state; evidence-only reservations and in-progress,
  terminal, missing, or mismatched correlation fail closed.
- Terminal traces cannot be reused by Stop feedback or response retries. A
  strongly preferred delegation receives at most one evidence-checked
  correction in the same external turn, then closes with truthful decline or
  retry-exhausted evidence instead of reopening a correlation loop.
- Generated Hermes plugins close only the exact interrupted or abandoned turn
  from `on_session_end`; session-only ambiguity closes nothing, and terminal
  outcomes remain immutable.
- Failed load/delegation events are no longer promoted to successful evidence.
- Delegation evidence correlates to stable work-unit identity.
- Final response evidence is reconciled against canonical state and rejects
  spoofed or stale claims.
- Delegation work-unit parsing no longer splits noun phrases at verb-shaped
  nouns such as “design,” while preserving explicit sequential boundaries.
- Existing schema-v16 stores now add and validate tombstone session/sequence
  identity before creating v17 indexes, then seal strict HMAC, counter,
  global-sequence, and turn-scoped evidence invariants through schema v19.
  Legacy trace barriers remain
  effective during in-place installation over durable profiles.
- Legacy activation and import-event tables now receive every current column,
  including deterministic positive event sequences, before any dependent index
  is created. Durable profiles upgrade transactionally instead of failing
  startup with a missing-column SQLite error.
- OpenAI-compatible URL joining, Anthropic Messages request handling, and
  model-specific request parameters are normalized.
- Windows command shims and test-home boundaries no longer assume POSIX launch
  behavior or real user directories.
- Inline sequencing language now produces the same dependency edge in route
  explanations and delegated execution, and the v1.1 policy corpus prevents
  generic design work from being mislabeled as UI while recognizing
  authentication and deployment intents.
- The installed dashboard now parses its shipped JavaScript, refreshes evidence
  after route tests, renders long Windows paths without page overflow, hides
  nonexistent host roots, and displays routing trace IDs.
- Destructive retention input is rejected instead of clamped, and stale host
  inspections cannot offer enable/disable actions or survive a successful
  native state change.
- Full dashboard refreshes are abortable and generation-checked so startup,
  background restoration, and configuration mutations cannot apply stale
  snapshots.
- Dashboard quick agent toggles retain the current redacted configuration
  revision outside the Settings view instead of submitting a missing CAS value.
- Routing-evaluation concurrency no longer depends on whether one CPU-bound
  narrowing call finishes inside a CPython thread-switch interval. Workers now
  synchronize from inside real narrowing progress, while a serialized
  narrowing regression still fails the overlap gate.
- Host adapters re-read persistent control at every boundary, trace correlation
  no longer falls back to a whole session, and native lifecycle success requires
  a proven inventory postcondition.
- Diagnostic route and explain surfaces no longer create orphaned evidence-only
  turns; explicit preflight is the sole owner of a durable turn lifecycle.
- Upgraded nonempty rosters repair missing protected fallback coordinators, while
  unchanged preflights avoid no-op serialized activation writes.
- Negated routing intent no longer leaks into policy, domain, token, or
  work-unit selection; explicit dependencies take precedence over incidental
  file overlap; output-format vocabulary no longer creates false graph edges.
- Nested roster snapshot diffs now materialize their real added, changed, and
  removed counts instead of reporting zero.
- Missing managed canary targets and empty file URLs no longer resolve
  implicitly to the current working directory.
- Routing cache hits compare detached mutation snapshots instead of rebuilding
  a 1,000-agent Python guard on every request, preserving nested-mutation
  invalidation while making the profiled hot path about ten times faster.
- An absent default companion-policy override no longer repeats an expensive
  Windows ACL walk on every routing cache hit; an override created later is
  still detected and validated on the next request.
- Current Codex plugin manifests declare their hook bundle with the host's
  supported command schema. The exact-confirmed Windows Codex 0.144.1
  isolated-profile canary now loads those hooks and produces a valid
  nonce-correlated six-line response header. Its explicit one-invocation trust
  bypass remains isolated and never promotes durable real-profile trust.
- Windows dashboard task inspection rejects DTD and entity declarations before
  parsing bounded XML.
- Windows drive-qualified and UNC executable paths remain absolute when payloads
  are generated on Linux, and platform-branch tests no longer mutate the shared
  process-wide `os.name` value.
- Rejected HTTP responses close their socket-backed bodies before the status
  exception is propagated, preventing repeated authentication failures from
  leaking connection resources.

### Security

- Managed persistent launchers are content-hashed and bound to lexical,
  resolved, metadata, ownership, and parent-namespace identities at install;
  inspection and lifecycle paths refuse drifted artifacts.
- Executable discovery ignores empty, dot, relative, and current-directory
  `PATH` entries; explicit commands must be absolute. Every launch-critical
  executable, interpreter, and wrapper is frozen to a canonical filesystem
  identity and revalidated immediately before process creation.
- Master-control state is bounded, schema-validated, owner-private, generation-
  checked, and atomically replaced. Missing or unverifiable state fails enabled;
  restricted Windows reads accept only the canonical path after proving stable
  real-file identities and no mutation rights.
- Scheduled-task ownership markers do not authorize execution: native Windows
  lifecycle actions additionally require a token-bound identity, a strict
  semantic definition match, and an exact pre-mutation requery.
- Dashboard requests require a per-launch bearer token, valid loopback host,
  same origin, JSON mutation bodies, and exact confirmation phrases.
- Background dashboard tokens rotate per start and live only in an owner-only
  runtime descriptor; service definitions, argv, logs, and status output remain
  credential-free.
- HTTP request bodies and subprocess output are bounded; server errors are
  sanitized; optional content capture applies defensive redaction.
- Credentialed provider requests reject redirects, remote model catalogs are
  byte/count/string/control bounded, subprocess overflow is discarded while
  both pipes continue draining, and Windows batch shims never receive
  user-controlled provider or delegation arguments.
- Host canaries isolate home/temp state, disable mutating MCP tools, bound and
  sanitize process output, omit prompt/output content from attestations, and
  never forward dashboard bearer tokens across redirects.
- Custom config/database paths no longer rewrite shared parent permissions.
  Config reads, locks, and replacements reject cross-account-writable parent
  namespaces while retaining safe read/traverse-only parents such as POSIX
  `0755`; the current-user config file is hardened before parsing. Database
  files and sidecars fail closed on Windows ACL errors, and database symlink or
  reparse-point paths are rejected before open.
- Present custom companion-policy files must be regular, single-link files
  owned by the current user, remain identity-stable across descriptor reads,
  and deny mutation to every other account. POSIX group/other read access may
  remain when write access is absent; Windows DACLs require the exact current
  owner and a mutation-safe access result. Cache hits revalidate this boundary.
- Distribution verification is bound to an immutable pre-build commit and its
  exact version, dependency, license, package, script, test, documentation, and
  example bytes. Portable archive names, regular member types, bounded reads,
  generated metadata, singleton headers, entry points, WHEEL tags, and RECORD
  hashes and sizes are validated before an artifact can be release evidence.
- Credentialed remote providers now require HTTPS except on literal loopback,
  reject ambiguous URL components, and validate the same rule across config,
  discovery, doctor, and runtime request paths.
- Delegation now minimizes inherited environment state, sends Codex/Claude
  tasks through standard input, redacts task content from every result surface,
  and contains descendants with atomic-at-creation Windows Job Objects or a
  dedicated Linux pidfd/subreaper supervisor that catches session-escaping
  double forks and cleans up when its launcher parent dies.
- Rejected JSON mutations drain bounded authenticated request bodies before
  responding, preventing intermittent Windows TCP resets from hiding the API
  error response.
- HTTP server tests now isolate configuration through pytest-managed temporary
  paths instead of leaking a POSIX-only global path across the Windows suite.
- Slotted Codex, Claude, and OpenClaw backends now call the shared parser
  explicitly, restoring structured delegation on Python 3.12 Linux; optional
  host capability tests no longer confuse an unusable WSL interop shim with a
  native executable.
- Protocol and configuration JSON rejects duplicate keys, non-finite numbers,
  oversized integers, excess bytes, deep nesting, and excess nodes; YAML also
  rejects aliases, merge keys, non-text keys, and shared containers.
- Delegated Git operations strip inherited Git configuration, disable hooks and
  fsmonitor, bound process output, and refuse executable filters, merge drivers,
  diff commands, and text converters before mutation.
- Windows owner-only permission setup detects restricted or indeterminate
  process tokens before changing a DACL, preventing a sandbox from locking
  itself out while preserving the fail-closed privacy contract.
- Existing exact owner-only Windows DACLs are verified and reused without a
  rewrite, including SQLite sidecars inherited from a recursively private
  parent; restricted tokens still fail before any required permission change.
- Roster downloads enforce one total deadline across slow reads; native canary
  credentials harden an empty destination before content exists; Git checkout
  hooks are suppressed; and strict finite JSON output is serialized before any
  protocol bytes are written.
- Agency evidence accepts only exact Agency and host-native tool identifiers;
  unrelated MCP namespaces cannot fabricate specialist, skill, or delegation
  records through a matching suffix.
- Turn correlation identifiers are printable, control-free, and bounded to 512
  UTF-8 bytes before public lookup or indexed persistence. OpenClaw bridge input
  is projected into a bounded envelope, and early child exit or oversized tool
  evidence cannot raise an unhandled standard-input error in the host process.
- Only the callback-owned Store ingress can persist authoritative LiteLLM
  provenance. Generic callers are downgraded, and receipt counts, provider
  identities, routing aliases, deployment names, and timestamps are normalized
  and bounded before they reach operator surfaces.
