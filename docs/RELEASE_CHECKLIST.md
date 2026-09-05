---
title: "Release Checklist"
status: active
category: release
created: 2026-07-10
updated: 2026-08-13
tags: [release, verification]
related:
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - CHANGELOG.md
  - CONTRIBUTING.md
  - SECURITY.md
  - THIRD_PARTY_NOTICES.md
  - CODE_OF_CONDUCT.md
  - docs/THREAT_MODEL.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/decisions/0069-enforce-conflicts-before-prompt-composition.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
supersedes: []
superseded_by: null
---

# Release Checklist

This checklist gates a release; it is not evidence that a release has occurred.
Agency Runtime currently uses installation from this repository as its canonical
prerelease path. Choose and document any public package channel before publishing
or adding an index-install claim.

## 1. Scope and records

- [ ] The release scope maps to roadmap items and same-repository tracker issues.
- [ ] Every durable decision has an accepted ADR and registry row.
- [ ] Every substantive commit has its exact worklog row and reciprocal roadmap
      traceability.
- [ ] Tracker status matches local status, or an authorization-related mismatch
      is stated explicitly.
- [ ] `CHANGELOG.md` describes user-visible additions, changes, fixes, security
      changes, deprecations, and known limitations.
- [ ] The package version, release title, and proposed tag agree.
- [ ] `agency -V`, detailed installed identity, stable-release resolution, and
      the proposed tag all agree with the exact candidate commit. Update plans
      contain that full SHA rather than a mutable branch, tag, or `latest`.

## 2. Truthful support matrix

- [ ] README host claims separate contract and simulation coverage from live
      discovery, registration, enablement, loading, and canary evidence.
- [ ] The canonical AR-119 matrix records every Rule 1–8 cell as `proven` for
      Codex, Claude Code, ZCode, Hermes, and OpenClaw on the exact candidate;
      Rule 9 is then proven from that complete five-host set. An unavailable
      host remains `unproven` and cannot be waived, removed, or marked
      not-applicable while it is supported.
- [ ] Each of the five hosts has a current native Rule-4 canary in which the
      host starts the child and the host-authored artifact contains multiple
      compatible, inference-chosen card hashes before first child speech.
      Agency Store rows, model prose, registration, simulation, and generic
      child evidence cannot originate or substitute for that proof.
- [ ] The exact candidate repairs and then re-proves Codex Rule 4 in TUI,
      Desktop, and exec. The recorded 2026-08-11 result is negative on all three
      surfaces; it is a blocker, not evidence inherited by a later candidate.
- [ ] Every host called `runtime-verified` has a dated reproducible native
      canary on each operating system claimed by the release.
    - When claiming Agency-on/native-only comparison behavior, run both explicit
      host-canary modes against the same installed artifact. Require the global
      master state to match each mode, zero Agency evidence in native-only mode,
      no native-only attestation, and guaranteed restoration of Agency-on state.
- [ ] Codex, Claude Code, ZCode, Hermes, and OpenClaw install, disable, enable,
      rollback, preflight, evidence, and finalization paths have been exercised
      for the v1 matrix or clearly marked below that maturity.
- [ ] Codex generated-bundle smoke proves the expected 8 hook events,
      commands, and timeout schema; native inventory proves plugin registration
      and enablement. Exact existing-install refresh through
      `agency install --agent codex --no-dashboard` proves native registration,
      exact postconditions, and compensation behavior without an Agency-owned
      Windows Hello prompt. Installation reports `activation_required` until
      an operator reviews and trusts the hooks through `/hooks` and
      `agency install --agent codex --verify-activation` records a successful
      current-profile canary. Close terminal TUIs opened before the candidate
      refresh and approve from one fresh TUI. Before provider-backed work, the
      verifier must obtain a bounded read-only `hooks/list` result for the exact
      canary directory and prove the canonical eight Agency hooks occur exactly
      once, enabled and trusted. That verification omits the hook-trust bypass
      and must prove routing, specialist evidence, finalization, and the
      response header. Isolated canary bypasses remain package-only evidence
      and never establish normal-profile readiness.
    - For a dedicated unattended production container, require an exact
      `--config` bind and explicit host scope, owned system managed-hook
      policy with managed-only loading and all eight events, refusal of foreign
      policy, a normal-invocation no-bypass canary, and a persisted current
      attestation. Then prove a later ordinary Conveyor-equivalent invocation
      loads Agency without a trust prompt. Never apply this system-policy path
      to an attended or shared workstation.
- [ ] Windows npm command shims and POSIX executable launch are both verified.
- [ ] Ubuntu/WSL live evidence comes from a Linux environment with the project
      and test tooling installed; Windows-only evidence is not relabeled Linux.
- [ ] MCP initialization, tool discovery, bounded framing, errors, and at least
      one real stdio call pass from a packaged install.
- [ ] LiteLLM SDK registration and Proxy callback import are tested in supported
      LiteLLM versions, or the integration remains explicitly optional and
      contract-tested only.
- [ ] LiteLLM success, failure, retry, alias, router-group, provider, and actual
      model evidence reconcile without one terminal state suppressing another.
- [ ] OpenClaw rejects unaudited versions before mutation, applies final-only
      config transactionally, and produces a host-authored current-candidate
      child artifact containing the inference-chosen card hashes before first
      speech. Registration-only inspection and generated-plugin simulation are
      not promoted to live delivery proof.
- [ ] Dashboard, MCP, generated-host, and restricted-broker surfaces are
      read-only; every former mutation endpoint rejects both bearer roles before
      dispatch and the shipped browser contains no mutation client or control.
- [ ] The authenticated dashboard update banner remains copy-only, validates
      the update schema and official target URL, performs checks asynchronously,
      and cannot invoke pip, host refresh, service restart, trust, or release
      mutation. Hook and MCP hot paths perform no update discovery.
- [ ] Bare install auto-discovers every installed supported harness, selects the
      dashboard unless `--no-dashboard` is present, and reports each component
      independently. Harness trust remains native to the harness.
- [ ] Exact-config production-container install reaches a terminal result
      without human input for each claimed container host; the supplied config,
      native payload, Store binding, dashboard binding when selected, and
      activation evidence agree.
- [ ] Owner CLI and authenticated dashboard views expose complete current and
      historical workforce prompt definitions with immutable lineage, standing,
      version, content hash, source, relation, and truncation provenance. They
      state that stored definition is not host-delivery proof and never add
      prompt bodies to ordinary status or list output.
- [ ] Every other persistent CLI mutation remains unavailable unless it gains a
      separately valid authority and committing boundary.
- [ ] Deferred stdin/prompt input is ingested before verification. Secret
      payload binding is one-time and internal; neither a secret value nor a
      stable secret-dependent guessing oracle crosses the trusted boundary.
- [ ] Roster rollback and owned host uninstall prove they remain unavailable and
      make no change; no retired native helper is packaged as a workaround.
- [ ] Global and host status expose one committed generation across read-only
      CLI, dashboard, MCP, and generated host surfaces; the dormant Store
      mutation contract still proves stale-conflict, no-op, and single-increment
      invariants without exposing a positive unauthorized path.
- [ ] Generic CLI behavior is tested with an explicit argv command; an
      unconfigured backend remains unavailable.
- [ ] Agency never decides to spawn or supplies a child-execution plan. When the
      native host independently starts a child, that child receives the exact
      inference-chosen request-scoped card set through the host's official
      lifecycle. Multiple compatible cards are supported; parent specialists
      and the resident steward do not leak as ordinary worker prompts.
- [ ] Clean wheel and source-archive installs on Windows and Linux run the
      Agency runtime/dashboard recall regression against the complete roster:
      `multi-agent-systems-architect` is recalled for its exact contract,
      ambiguous input is labelled unresolved, and clinical, geography,
      translation, and generic operations specialists remain forbidden. This
      offline contract never claims to select or recommend a specialist.

Record dated live evidence in the release notes without committing secrets or
machine-specific credential paths.

## 3. Correctness and performance

Routine pull-request and push CI runs the named fast Python production spine
plus the automatic quality, UI, performance, portability, security, and
artifact gates. It deliberately does not run the complete warning-strict Python
corpus, four-shard Python coverage, or six-interpreter compatibility matrix.
The exhaustive jobs remain available as optional diagnostics only when an
authorized maintainer explicitly requests `workflow_dispatch`. Record their run
URL and outcome when used, but their absence is not itself a production or
release blocker. Base the verdict on the candidate's applicable fast checks,
artifact verification, installed smoke, live host/UI evidence, security status,
and explicitly listed limitations.

```bash
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests -q -W error -p no:cacheprovider -m performance
node --test --experimental-test-coverage --test-coverage-lines=95 --test-coverage-branches=90 --test-coverage-functions=96 tests/dashboard_ui.test.mjs
agency eval host-parity --json
agency eval routing --json --no-details
python -m agency_runtime.cli eval decision-conformance --repository . --json
agency eval full-roster --json --no-details
```

The routing report's `deterministic_candidate_recall_only` contract measures
the production shortlist, policy/delegation classification, and performance.
It does not prove specialist selection; provider-backed and exact live runtime
receipts own that evidence.

When independently collected paired observations exist, validate them
separately; this command does not create live-host evidence:

```bash
agency eval compare --input path/to/paired-observations.jsonl
```

- [ ] The named fast production spine and every focused changed-behavior test
      pass for the candidate.
- [ ] The exact candidate artifact passes independent verification, fresh
      installation smoke, and its applicable live host/UI demo checkpoint.
- [ ] If the owner requested optional exhaustive diagnostics, record their
      scope and outcome without promoting stale or failed evidence.
- [ ] The versioned routing report passes every checked-in threshold.
- [ ] Turn-classification tests cover all six exact kinds—`acknowledgement`,
      `conversation`, `control`, `continuation`, `new_intent`, and `revision`—
      against durable open/terminal state, unfinished work, pending questions or
      authorization, configuration/roster revisions, and retry evidence. Only a
      proven pure acknowledgement bypasses specialist consideration.
- [ ] The resident `agency-steward` contract remains compact, protected,
      parent-only, hash-bound, and restored once after compaction without
      accumulating complete prompt bodies. It cannot select or perform domain
      work; imported managers remain optional workers.
- [ ] For a novel-domain staffing need with zero relevant roster cards,
      inference declares the gap, hiring materializes and independently audits
      a narrow contractor, and the same inference-owned turn selects that
      contractor. Deterministic code may recall and validate but cannot select,
      replace, erase, or invent a specialist or contractor.
- [ ] No configured provider, provider exhaustion, or an invalid inference
      response means Agency supplies no specialist card or contractor; it
      records the exact cause and the native host proceeds as a generalist with
      a `Recruited via: none` header. Only a verifier's definite negative and
      the malformed-`Stop` forgery boundary may deliberately withhold.
- [ ] Rule 8 is live-proven on all five hosts: Agency unavailability never
      suppresses the host's natural response, and `agency evidence rejections`
      correctly separates a deliberate rejection from Agency being blind.
- [ ] Automatic contractor promotion is live-proven on the exact candidate:
      three independently accepted successes after the seven-day review window
      trigger promotion without an operator action, using producer and distinct
      verifier host artifacts. Missing host-backed acceptance leaves promotion
      dormant and blocks AR-119 and release completion.
- [ ] The exact candidate passes the unchanged 15,000 ms cold staffing gate;
      latency repair does not weaken inference-only selection, host-owned spawn,
      Rule-4 artifact authority, Rule-8 fail-open behavior, or promotion proof.
- [ ] `agency eval full-roster` proves every approved enabled routing card
      participates in lexical and semantic retrieval, candidate recall is
      `1.0`, identity-free target recall@10 is at least `0.99`, and the checked-in
      abstention, compatibility, isolation, and turn-state cases pass. Its
      report remains labelled offline, inference-free, contract-only, and
      incapable of establishing task quality or superiority.
- [ ] Every configured inference provider path is exercised. Selection-requiring
      turns cannot bypass inference through lexical confidence; chain exhaustion
      is visibly degraded, supplies no card, and cannot be reported as inferred.
- [ ] Compatible-set tests cover requirements, hard and soft conflicts,
      authority, context mode, independence, host, platform, tools, permissions,
      resource overlap, implementer/reviewer isolation, and calibrated no-match.
- [ ] Cache/stickiness tests prove roster, configuration, and policy isolation.
- [ ] Concurrent routing and evidence tests show no cross-request contamination.
- [ ] Native-child tests cover host-owned spawn origin, exact inference-decision
      binding, multiple compatible cards, child-identity correlation, duplicate
      lifecycle events, nested host-spawned children, and missing or malformed
      host artifacts without introducing an Agency scheduler or execution DAG.
- [ ] A real restricted-Windows canary proves root and nested Codex scratch,
      child `TEMP`/`TMP`, Store descendants, Git worktree creation, read-only Git
      cleanup, identity-swap rollback, and exact removal without repo fallback.
- [ ] Evidence tests reject failed, stale, ambiguous, and spoofed claims.
- [ ] Selection remains distinct from execution: inference chooses the card set,
      while only the native host chooses whether and how to spawn. A native
      child is counted as staffed only from its host-authored artifact containing
      exact card hashes before first speech; direct parent loads, unstaffed
      host continuations, and bounded retry exhaustion close without fabricated
      child delivery or delegation.
- [ ] Stop/finalization tests prove current-turn correlation, monotonic terminal
      closure, at most one strongly-preferred correction, revalidation on retry,
      fresh-turn recovery, and no terminal-trace reuse loop.
- [ ] Paired comparison input, when supplied, uses unique blinded run identities
      and matching requested/actual model plus LiteLLM router identities. Reports
      keep live-host, isolated, contract-only, and simulated evidence separate;
      directional eligibility is not published as a superiority conclusion.
- [ ] Measured runtime code reaches the configured coverage thresholds
      (95% lines / 90% branches / 96% functions for dashboard UI; when the
      optional exhaustive Python workflow is requested, its configured
      97-percent aggregate line-and-branch threshold); any unreachable
      platform-only exclusion is narrow, documented, and reviewed rather than
      hidden through a broad omit rule.

## 4. Security and privacy

```bash
python scripts/verify_release_hygiene.py
python -m bandit -q -r agency_runtime scripts -lll
python scripts/audit_runtime_dependencies.py
zizmor --pedantic --strict-collection --offline .
```

- [ ] No tracked secret, credential file, database, build output, generated host
      state, sibling path, or machine-specific absolute path is present.
- [ ] Dashboard tests enforce loopback binding, per-launch authentication,
      `Host`/origin checks, restrictive response headers, and fail-closed
      rejection of every former mutation for both bearer roles.
- [ ] Metadata-only capture and 30-day runtime retention remain the defaults.
- [ ] Opt-in content paths are bounded and redacted; limitations are documented.
- [ ] Native commands use argv execution, timeouts, bounded output, atomic
      Windows/Linux tree ownership, the exact Linux GO handoff, and validated
      terminal completion receipts from ADR-0073.
- [ ] Every upstream roster definition is accounted for as approved,
      quarantined, or retired with content hash and provenance. Deterministic and
      configured-inference audits, findings, active-basis checks, and lifecycle
      transitions are append-only; degraded or stale audit evidence cannot
      approve or activate a candidate.
- [ ] Nightly roster synchronization processes only new or content-changed
      definitions into quarantine under read-only repository permissions and
      never auto-activates, deletes, retires, or replaces an approved revision.
- [ ] Prompt-composition security tests reject instruction-priority escalation,
      unsafe authority, encoded/suspicious content, external dependencies,
      incompatible prompts, and full prompt bodies in inference requests or
      persisted routing receipts.
- [ ] Executable discovery rejects relative/current-directory search, freezes
      every launch-critical native, interpreter, and wrapper identity, and
      revalidates it immediately before process creation on Windows and POSIX.
- [ ] Restricted-Windows scratch validates effective-token logon identity,
      bounded unique host capability, owner-private ancestors, mutation access,
      protected child DACL, file identity, ambiguity failure, and link-safe
      cleanup without globally trusting arbitrary restricting SIDs.
- [ ] Restricted child processes independently reattest the exact randomized,
      thread-bound scratch allocation after `exec`; a parent process-local
      receipt, renamed allocation, mismatched host marker, or changed root/DACL
      is not accepted as authority.
- [ ] Persistent host and dashboard launchers bind interpreter plus package
      bootstrap lexical/resolved identity and content digest in managed
      manifests; inspection, registration, start, and restart reject drift.
- [ ] Master-control tests cover owner-private creation, strict bounded schema,
      generation conflicts, atomic replacement, missing/corrupt fail-enabled
      behavior, restricted Windows canonical reads, mutation-right probes, and
      authenticated dashboard brokering.
- [ ] Security reporting instructions and the current supported-version statement
      are accurate.
- [ ] The threat model covers current assets, trust boundaries, controls, and
      residual risks; CodeQL completes natively when repository visibility and
      licensing permit it, or a positively recognized private/internal
      missing-entitlement response produces machine-readable evidence that
      analysis was not performed while Bandit, offline workflow auditing, and
      the exact installed-runtime vulnerability audit pass. Ambiguous probe
      responses fail closed. Dependency review passes through native diff review
      or that exact runtime audit.
- [ ] GitHub Actions use immutable SHAs, least-privilege permissions, and no
      persisted checkout credentials without an explicit need.
- [ ] Release artifacts contain no retired Agency-owned Windows Hello helper,
      executable, or disguised PE payload. ADR-0219 retires its Authenticode,
      compiler/SDK redistribution and native-notice prerequisites; the original
      requirements remain in superseded ADR-0099 and historical AR-161.
- [ ] Signing keys and reusable credentials never enter the repository or
      ordinary CI artifacts. Current third-party notices and publication
      authorization cover the bytes actually distributed; helper retirement
      does not establish legal clearance for unrelated components.

## 5. Documentation integrity

```bash
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py --require-tracker
python scripts/verify_tracker.py
git diff --check
```

- [ ] Every maintained Markdown file has valid front matter.
- [ ] No intra-repository link dangles and no doc depends on a sibling repo.
- [ ] README CLI examples match `agency --help` and actual exit behavior.
- [ ] Host paths and maturity labels match the installer source and doctor output.
- [ ] Contribution, code-of-conduct, security, threat-model, changelog,
      troubleshooting, and release-checklist documents are linked from README
      and `AGENTS.md`.

## 6. Build and isolated install

The builder derives its wheel profile from the actual host: supported Windows
x64 emits one `win_amd64` wheel/source pair and other hosts emit one portable
wheel/source pair. Neither wheel profile admits executable or PE content.
Running these commands on one host does not create the complete release set.
The hosted merge gate must
prove byte-identical producer source distributions and shared wheel payloads,
assemble the two wheels plus one source distribution, and independently verify
all three. Current cross-OS evidence must identify an actual authorized producer
run; the 2026-09-05 backlog reconciliation claims no new hosted run or current
billing-state diagnosis. ADR-0219 retires the removed helper's signed-delivery
obligation, not cross-OS artifact proof or publication authorization.

From a clean checkout:

```bash
python -m pip install ".[dev,release,security]"
AGENCY_RELEASE_COMMIT="$(git rev-parse --verify 'HEAD^{commit}')"
AGENCY_DIST_DIR="${HOME}/.agency-runtime/release-artifacts/dist-${AGENCY_RELEASE_COMMIT}"
python -m scripts.build_distributions "${AGENCY_DIST_DIR}" --create-private-parent \
  --expected-commit "${AGENCY_RELEASE_COMMIT}"
python -m twine check --strict "${AGENCY_DIST_DIR}"/*
python -m scripts.verify_distribution "${AGENCY_DIST_DIR}" \
  --expected-commit "${AGENCY_RELEASE_COMMIT}"
```

In PowerShell, capture the same pre-build value and use an owner-private output
parent outside the checkout:

```powershell
$env:AGENCY_RELEASE_COMMIT = git rev-parse --verify "HEAD^{commit}"
$env:AGENCY_DIST_DIR = Join-Path $HOME `
  ".agency-runtime\release-artifacts\dist-$env:AGENCY_RELEASE_COMMIT"
python -m scripts.build_distributions $env:AGENCY_DIST_DIR `
  --create-private-parent --expected-commit $env:AGENCY_RELEASE_COMMIT
$artifacts = Get-ChildItem -LiteralPath $env:AGENCY_DIST_DIR -File |
  Select-Object -ExpandProperty FullName
python -m twine check --strict $artifacts
python -m scripts.verify_distribution $env:AGENCY_DIST_DIR `
  --expected-commit $env:AGENCY_RELEASE_COMMIT
```

Each producer builder requires an absent destination, validates or creates its
private parent, materializes the exact bounded release payload from reviewed Git
blobs, and publishes one profile-specific wheel plus one governed source
distribution only after a successful isolated build and pre-publication
checkout revalidation. The merge gate, not either producer, assembles and
uploads the verified three-artifact set. ADR-0219 retires AR-161's removed-helper
signing gate; existing publication and non-helper supply-chain controls remain.
This avoids trusting physical worktree
line endings or broadly inherited workspace ACLs while preserving the
independently implemented and invoked Twine and distribution-verifier gates.
Before publication, a bounded normalizer preserves every source-derived payload
byte, canonicalizes LF only for the shared finite generated-metadata allowlist,
rebuilds wheel `RECORD` from the normalized payload set, and rewrites
backend-created ZIP, gzip, tar, ownership, mode, and timestamp container metadata
to one Windows/Linux policy. It explicitly writes stored ZIP members and a
canonical RFC 1951 stored-block gzip stream, so output bytes do not depend on
host-zlib heuristics. Release-scoped Git inputs must all be regular non-executable
(`100644`) blobs, and archive regular files must remain non-executable.

Use a trusted release Python environment and output parent outside any
cross-account-writable checkout namespace. The builder freezes and revalidates
the interpreter before launch; an ordinary repository-local Windows virtual
environment or `dist` parent may be rejected when inherited ACLs permit another
account to replace the launcher or a newly created child.

- [ ] The portable and `win_amd64` wheels contain the complete shared package
      surface and neither contains an executable or structurally valid PE. The
      source distribution also contains
      governance docs, the threat model, release scripts, tests, and
      self-contained examples under one explicit no-universal-PE build policy.
- [ ] Artifact verification is pinned to the commit captured before build and
      proves HEAD did not change; wheel and sdist filenames, metadata, roots,
      version, dependencies, license, and every MANIFEST-governed committed
      byte match that reviewed commit exactly.
- [ ] The build source was materialized from canonical reviewed Git blobs, not
      line-ending-filtered working-tree bytes; unsafe paths, links, special
      entries, aliasing, size-bound violations, and partial output fail closed.
- [ ] On both hosted Ubuntu and Windows, the artifact job binds
      command-scoped `core.autocrlf=true` without persistent Git configuration,
      proves the fixed `LICENSE` source is physically CRLF while Git reports a
      clean exact reviewed `HEAD` with an LF blob, and only then invokes the
      canonical builder and independent verifier.
- [ ] The release input contains no executable Git entries; both the builder and
      independent verifier reject any release-scoped mode other than `100644`.
- [ ] Hosted Ubuntu and Windows producers each build and strictly verify one
      host-derived wheel/source pair. A dependent merge gate proves the two
      source distributions byte-identical and every shared wheel payload equal,
      assembles the portable wheel, Windows wheel, and one source distribution,
      and independently verifies that exact set. No partial set proceeds to
      install or publication.
- [ ] Archives contain only canonical portable regular-file payloads plus the
      explicit generated metadata allowlist, remain within member, size,
      aggregate, and compression-ratio limits, and pass strict singleton
      metadata, entry-point, WHEEL, and RECORD hash/size validation. Generated
      text uses canonical LF, `SOURCES.txt` has the backend's exact
      parent-directory/basename ordering and no-final-newline form, and
      core-metadata bodies decode as strict raw UTF-8.
- [ ] Each wheel has one contiguous ZIP layout with no prefix, gaps, orphan local
      records, comments, extras, directory entries, encryption, unsupported
      flags, data descriptors, compression, or trailing bytes; every stored
      member's physical size equals its payload size. The sdist has one bounded
      gzip member with the exact canonical RFC 1951 stored-block segmentation,
      only canonical bounded `mtime`/`path` PAX records, exact required parent
      directories, zero alignment padding, and one minimally padded tar end
      marker.
- [ ] ZIP creator/extractor versions, system, flags, attributes, method, and DOS
      time plus gzip and tar ownership, modes, and times match the single
      platform-independent container policy; wheel `METADATA` and sdist
      `PKG-INFO` agree semantically.
- [ ] Windows service contract tests prove current-user Task Scheduler
      registration, owned updates, rollback-on-failure, start/stop/restart,
      uninstall, readiness, persistent-launcher drift refusal, and
      `--no-dashboard` without touching a real task.
- [ ] Linux service contract tests prove `systemd --user` registration,
      hardening, manager-unavailable truth, start/stop/restart, uninstall,
      readiness, persistent-launcher drift refusal, and `--no-dashboard`
      without touching a real user manager.
- [ ] Dashboard configuration tests cover bounded redacted projections,
      local-only enforcement, owner writes, and broker rejection without state
      change. CLI and owner-dashboard write contracts remain typed, confirmed
      where required, and revision-checked without a human-presence ceremony.
- [ ] Dashboard live tests cover authenticated schema and metadata boundaries,
      stable revisions, one bounded activity read, stale-response cancellation,
      visibility lifecycle, terminal authentication, and capped retry behavior.
- [ ] Dashboard roster-operations tests cover bounded pagination and filters for
      division, capability, authority, host, platform, and tool; prompt-free
      routing contracts; conflict/requirement metadata; and bounded revision
      history without exporting specialist prompts.
- [ ] Dashboard review and inference tests cover immutable quarantine findings
      and status history, active-versus-candidate comparison, read-only audit
      status, ordered redacted provider projections, recent failure evidence, and
      requested/router/actual-provider/model separation. Remote freshness and
      provider readiness remain labelled non-probed unless separate live
      evidence exists.
- [ ] Dashboard master and host tests cover truthful enabled/disabled rendering,
      committed generations, live propagation, and the fresh-session A/B notice,
      while every mutation route rejects before dispatch with no state change.
- [ ] Restricted Windows CLI tests prove status brokerage only after an exact
      restricted-token Store refusal; endpoint/method pairs, complete host
      snapshots, master state, host identity, booleans, and generations are
      validated, and malformed or stale results fail without automatic retry.
- [ ] No brokered master, host, or agent mutation exists. Tests prove those
      endpoint/method pairs fail closed and cannot emit a success receipt.
- [ ] Restricted Windows agent tests prove list and exact lookup broker only the
      default installed identity through bounded revision-stable pages. Explicit
      config paths are not redirected, duplicate or inconsistent pages fail
      closed, and no toggle is proxied.
- [ ] Restricted Windows selector tests prove search, route, explain, and
      policy use one complete validated read-only catalog, while delegation,
      setup, arbitrary Store calls, and generic config mutation fail with
      controlled nonzero diagnostics before execution or evidence claims.
- [ ] Dashboard browser QA covers desktop and mobile layout, live status,
      chart summaries, keyboard naming, reduced motion, forced colors, no
      horizontal page overflow, and a clean console.
- [ ] Every dashboard asset is present in wheel and source artifacts, passes the
      static CSP/security scan, and stays within the documented asset budget.
- [ ] Fresh Python 3.10 environments on Windows install the `win_amd64` wheel,
      portable wheel, and source distribution separately, run `agency --help`,
      import package data, and pass the full packaged smoke procedure. Installer
      selection prefers the native wheel only on supported Windows x64.
- [ ] Ubuntu selects and installs the portable wheel, never receives the PE
      helper, and passes the isolated wheel/source-distribution procedures.
- [ ] `python -m pip check` passes for every applicable artifact/environment.
- [ ] Rebuilding from the same source does not depend on untracked local files.

## 7. Publish and post-publish

Publishing, pushing, tagging, issue closure, and release creation are
outward-facing actions and require explicit authorization.

- [ ] Obtain approval for the exact tag, artifacts, destination, and release
      notes.
- [ ] Tag the reviewed commit; do not move an existing public tag.
- [ ] Publish the complete paired-wheel and source artifact set produced by the
      verified workflow, not a local rebuild or partial upload.
- [ ] Verify hashes, metadata, install command, and CLI version from the public
      destination.
- [ ] Create release notes from `CHANGELOG.md` and include known support limits.
- [ ] Update tracker states only after the release outcome is confirmed.
- [ ] Start the next `Unreleased` changelog section.

## Current blockers

The dated checkpoints below are historical evidence, not current-candidate
release proof. References to helper signing describe the then-recorded gate;
ADR-0219 has retired that obligation. AR-160 owns the current paired no-helper
artifact contract, and AR-405 records two current Linux release-fixture failures.

The 2026-08-26 AR-297 unsigned Linux checkpoint built and independently
verified commit `987cee8ff01a4a16780eac15bb8120f828d4193d`. The portable wheel
SHA-256 is
`17a3bc0053a882b22ff72d8b3a2ebcd23ef602c2b5c034e7a05e8ae10ff929f1`
and the sdist SHA-256 is
`6551c43fc6fc7dfe7d8b9318e5b7605d1ecc8e214490eb7d0d2af001ffa9adb5`.
Build, strict Twine, and independent verification exit 0 only with the required
owner-private umask; the documented ambient-umask invocation exposes a
group-writable archive-permission failure. Clean Claude, Hermes, and OpenClaw
container registration passes, but Codex's managed canary exits at staffing
critique, all four later ordinary turns lack terminal Agency proof, and the
ordinary non-root systemd dashboard service fails closed under `PrivateTmp`
(AR-301). These results are local unsigned Linux evidence only; no checklist
box requiring cross-OS, signing, publication, or successful live host delivery
is satisfied by them.

The named repository gates subsequently pass from trusted owner-private Linux
execution: 858 fast-spine tests pass with 3 skips, dashboard UI passes 138,
routing passes every threshold, and decision conformance passes its baseline
with 160/160 mutations killed, zero survived/invalid, and source unchanged.
Fresh wheel and sdist installs each pass packaged import/data, 263-worker roster,
offline selection safety, eight-tool MCP, authenticated dashboard health,
deterministic smoke 8/8, CLI help/version, and `pip check`. Ambient umask 0002
and an interpreter below untrusted `/tmp` first fail closed; AR-302 retains that
local-repeatability defect. These local successes do not supply hosted Windows,
cross-producer parity, signing, or publication evidence.

The final owner-approved Hermes retry set native reasoning to `none` and
restricted auxiliary routing to free models. The ordinary command exited 0, but
Agency preflight recorded `workforce_inference_failed` and the turn guard
withheld Hermes's unverified draft. Trace
`20260826_143220_d88838:59ceb645-aba9-4910-9cb6-1f25d61efd89:2f835640`
has no Agency model receipt, route, specialist, delegation, finalization, or
attestation row. The final authenticated OpenClaw RPC and loaded-plugin checks
exit 0, while host status still reports absent canary attestations. All five
dedicated proof containers were then removed with exit 0, their final images and
host artifacts were retained, and the Linux-scoped release verdict remains
**NO-GO**.

The 2026-07-26 checkpoint passed the then-current ordinary warning-strict suite
(7,604 passed, 61 skipped, 1 expected failure), Python coverage at 97.08 percent,
the separate performance arm, dashboard coverage, routing, delegation,
full-roster, release-hygiene, Bandit, dependency, and offline-workflow gates.
That result remains historical context, not current-candidate proof. The earlier
2.166 ms cache arm and one non-reproduced lifecycle failure remain preserved as
failed evidence; neither an old exhaustive success nor the absence of a new
optional exhaustive run decides the current scoped verdict.

AR-197 retired the Agency-owned Windows Hello helper and its release surface.
Harness installation now uses native harness lifecycle and trust. Roster
rollback, owned host uninstall, dashboard/model-facing mutation, and generic
positive controls remain unavailable. The paired portable/`win_amd64` artifact
set must reject executable and disguised PE payloads in both profiles.

AR-119's canonical matrix currently records Claude Rule 4 as exact-candidate
unproven despite three prior-candidate live artifacts. Codex has a repaired
conditional plaintext source candidate with separate exact CLI `0.147.0` and
Desktop `0.147.0-alpha.6.6` profiles. Their supported ancestry passes scoped
local verification and independent adversarial review, while encrypted calls
remain unstaffed; all 65 observed Desktop calls were encrypted and unmarked.
Codex Rule 4 Implementation and Simulation are proven;
unobserved exec depth-two/deeper and exact-candidate Installed/Live state remain
unproven.
ZCode, Hermes, and OpenClaw remain unproven. That evidence is not release-ready.
AR-119 and AR-125 also still
require a benchmark-valid completed outcome corpus and current-artifact host/OS
evidence. The automatic three-success/seven-day contractor path remains dormant
without host-backed accepted outcomes and is on the release critical path.

AR-128 through AR-161 items with pending mappings require authorized
same-repository tracker synchronization.
Hosted Windows/Linux matrices, push, PR, tag, publication, and release remain
outward actions requiring explicit authorization. Historical PR #18 evidence
does not establish the current commit.
