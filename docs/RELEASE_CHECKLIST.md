---
title: "Release Checklist"
status: active
category: release
created: 2026-07-10
updated: 2026-07-29
tags: [release, verification]
related:
  - CHANGELOG.md
  - CONTRIBUTING.md
  - SECURITY.md
  - THIRD_PARTY_NOTICES.md
  - CODE_OF_CONDUCT.md
  - docs/THREAT_MODEL.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0054-unit-aware-assignment-and-event-driven-dag.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
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
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
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

- [ ] README host claims separate deterministic contract coverage from live
      discovery, registration, enablement, loading, and canary evidence.
- [ ] Every host called `runtime-verified` has a dated reproducible native
      canary on each operating system claimed by the release.
    - When claiming Agency-on/native-only comparison behavior, run both explicit
      host-canary modes against the same installed artifact. Require the global
      master state to match each mode, zero Agency evidence in native-only mode,
      no native-only attestation, and guaranteed restoration of Agency-on state.
- [ ] Codex, Claude Code, Hermes, and OpenClaw install, disable, enable, rollback,
      preflight, evidence, and finalization paths have been exercised for the v1
      matrix or clearly marked below that maturity.
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
      config transactionally, and proves exact-payload one-use dispatch sealing
      in the generated-plugin harness. Registration-only inspection is not
      promoted to live delivery proof.
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
- [ ] Each native child receives a fresh bounded Agency preflight for its exact
      assignment through the host's official lifecycle. Parent specialists and
      resident managers do not leak into children as ordinary worker prompts,
      and absent live hosts remain labelled contract-only.
- [ ] Clean wheel and source-archive installs on Windows and Linux run the
      Agency runtime/dashboard selection regression against the complete roster:
      `multi-agent-systems-architect` is the only result, ambiguous input
      abstains, and clinical, geography, translation, and generic operations
      specialists remain forbidden.

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
agency eval delegation --json
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
agency eval full-roster --json --no-details
```

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
- [ ] The resident `agents-orchestrator` and `chief-of-staff` contract remains
      compact, protected, parent-only, hash-bound, and restored once after
      compaction without accumulating complete prompt bodies.
- [ ] `agency eval full-roster` proves every approved enabled routing card
      participates in lexical and semantic retrieval, candidate recall is
      `1.0`, identity-free target recall@10 is at least `0.99`, and the checked-in
      abstention, compatibility, isolation, and turn-state cases pass. Its
      report remains labelled offline, inference-free, contract-only, and
      incapable of establishing task quality or superiority.
- [ ] Every configured inference provider path is exercised. Selection-requiring
      turns cannot bypass inference through lexical confidence; chain exhaustion
      is visibly degraded and cannot be reported as inferred. No-provider
      deterministic mode remains explicitly distinguishable.
- [ ] Compatible-set tests cover requirements, hard and soft conflicts,
      authority, context mode, independence, host, platform, tools, permissions,
      resource overlap, implementer/reviewer isolation, and calibrated no-match.
- [ ] Cache/stickiness tests prove roster, configuration, and policy isolation.
- [ ] Concurrent routing and evidence tests show no cross-request contamination.
- [ ] Delegation DAG tests cover failed prerequisites, missing results, duplicate
      work units, unit-specific specialist assignment, immediate successor
      release, independent concurrency, recursive failure skips, and successful
      worktree merging.
- [ ] A real restricted-Windows canary proves root and nested Codex scratch,
      child `TEMP`/`TMP`, Store descendants, Git worktree creation, read-only Git
      cleanup, identity-swap rollback, and exact removal without repo fallback.
- [ ] Evidence tests reject failed, stale, ambiguous, and spoofed claims.
- [ ] Selection remains distinct from execution: only native-started isolated
      units require exact one-use activation plus reciprocal worker/run evidence;
      direct loads, explicit declines, skips (including a bounded reason for a
      host-merged unit), and bounded retry exhaustion close without fabricated
      activation or delegation.
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
- [ ] The deterministic unsigned native helper is rebuilt and independently
      verified before signing; release provenance separately binds the signed
      SHA-256, approved publisher certificate identity and chain, RFC 3161
      timestamp, policy, and exact unsigned review digest.
- [ ] Independent Windows Authenticode verification uses the default
      authentication policy and rejects a missing signature, warning, wrong
      publisher, invalid chain, altered bytes, absent/invalid timestamp, or
      unresolved revocation state when policy requires it. Signing keys and
      reusable credentials never enter the repository or ordinary CI artifacts.
- [ ] `THIRD_PARTY_NOTICES.md` and the release artifacts include the exact local
      C++/WinRT MIT and Microsoft STL Apache-2.0 WITH LLVM-exception/NOTICE
      texts from their immutable official source revisions.
- [ ] The owner and an authorized legal reviewer record the exact Visual Studio
      edition/build-operator entitlement, MSVC and Windows SDK terms and redist
      list, `/MT` static CRT/runtime disposition, upstream notices, publisher
      identity, and final channel approval. Source-license provenance alone is
      not legal clearance.

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
wheel/source pair whose wheel excludes only the PE. Running these commands on
one host does not create the complete unsigned review set. The hosted merge gate must
prove byte-identical producer source distributions and shared wheel payloads,
assemble the two wheels plus one source distribution, and independently verify
all three. Hosted cross-OS proof remains pending while repository Actions
billing is disabled. AR-161 separately requires an approved signed delivery
payload and legal disposition before publication.

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
uploads the verified unsigned review three-artifact set. AR-161's protected
signing and delivery gate must produce the final release candidate separately.
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

Normal-profile Codex readiness still requires user-owned terminal-TUI `/hooks`
review and a new session. AR-119 and AR-125 still require a benchmark-valid
completed outcome corpus and current-artifact host/OS evidence; absent Claude
Code, Hermes, OpenClaw, ZCode, and Linux canaries remain contract-only.

AR-128 through AR-161 items with pending mappings require authorized
same-repository tracker synchronization.
Hosted Windows/Linux matrices, push, PR, tag, publication, and release remain
outward actions requiring explicit authorization. Historical PR #18 evidence
does not establish the current commit.
