---
title: "Release Checklist"
status: active
category: release
created: 2026-07-10
updated: 2026-07-20
tags: [release, verification]
related:
  - CHANGELOG.md
  - CONTRIBUTING.md
  - SECURITY.md
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
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
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
- [ ] Codex generated-bundle smoke proves the expected seven hook events,
      commands, and timeout schema; native inventory proves plugin registration
      and enablement. Installation reports `activation_required` until an
      operator reviews and trusts the hooks through `/hooks` and
      `agency install --agent codex --verify-activation` records a successful
      current-profile canary. That verification omits the hook-trust bypass and
      must prove routing, specialist evidence, finalization, and the response
      header. Isolated canary bypasses remain package-only evidence and never
      establish normal-profile readiness.
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
- [ ] Agent enable/disable works through CLI and dashboard against the same
      explicit, environment-selected, installed-service, or default config
      identity after restart; both protected coordinators remain enabled.
- [ ] `agency on|off --global` and the dashboard mutate one durable master
      generation; every host and protocol surface bypasses before Store or
      correlation when off, and fresh-session Agency-on / Agency-off canaries
      prove the intended A/B behavior without changing native registration.
- [ ] Host-scoped status exposes one committed generation across CLI,
      dashboard, MCP, and generated host commands; stale concurrent mutations
      conflict instead of overwriting, no-ops preserve the generation, and
      multi-host CLI failures retain every per-host result.
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

```bash
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests -q -W error -p no:cacheprovider -m "not performance" \
  --cov=agency_runtime \
  --cov=scripts.build_distributions \
  --cov=scripts.canonicalize_distributions \
  --cov=scripts.prove_autocrlf_checkout \
  --cov=scripts.release_contract \
  --cov=scripts.release_git \
  --cov=scripts.verify_distribution \
  --cov-branch --cov-report=term-missing --cov-fail-under=100
python -m pytest tests -q -W error -p no:cacheprovider -m performance
node --test --experimental-test-coverage --test-coverage-lines=100 --test-coverage-branches=100 --test-coverage-functions=100 tests/dashboard_ui.test.mjs
agency eval delegation --json
agency eval routing --json --no-details
agency eval full-roster --json --no-details
```

When independently collected paired observations exist, validate them
separately; this command does not create live-host evidence:

```bash
agency eval compare --input path/to/paired-observations.jsonl
```

- [ ] The complete suite passes on Ubuntu CI for Python 3.10 through 3.14 and on
      Windows CI at the 3.10 and 3.14 support endpoints; focused native Windows
      canonical-archive golden and atomic-process coverage also passes on Python
      3.11, 3.12, and 3.13.
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
- [ ] Measured runtime code reaches 100 percent line and branch coverage; any
      unreachable platform-only exclusion is narrow, documented, and reviewed
      rather than hidden through a broad omit rule.

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
      `Host`/origin checks, JSON mutations, exact confirmations, and restrictive
      response headers.
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

The builder requires an absent destination, validates or creates its private
parent, materializes the exact bounded release payload from reviewed Git blobs,
and publishes the wheel/source pair only after a successful isolated build and
pre-publication checkout revalidation. This avoids trusting physical worktree
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

- [ ] Wheel and source distribution contain every package module and asset; the
      source distribution also contains governance docs, the threat model,
      release scripts, tests, and self-contained examples.
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
- [ ] Hosted Ubuntu and Windows jobs each build and strictly verify the canonical
      wheel/source pair, then a dependent parity gate proves both filenames and
      artifact bytes are identical; only the reviewed Ubuntu pair proceeds as
      the install or publication candidate.
- [ ] Archives contain only canonical portable regular-file payloads plus the
      explicit generated metadata allowlist, remain within member, size,
      aggregate, and compression-ratio limits, and pass strict singleton
      metadata, entry-point, WHEEL, and RECORD hash/size validation. Generated
      text uses canonical LF, `SOURCES.txt` has the backend's exact
      parent-directory/basename ordering and no-final-newline form, and
      core-metadata bodies decode as strict raw UTF-8.
- [ ] The wheel has one contiguous ZIP layout with no prefix, gaps, orphan local
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
- [ ] Dashboard configuration tests cover typed writes, redaction, write-only
      secrets, optimistic-concurrency conflicts, local-only enforcement, and
      sensitive confirmation phrases through both CLI and API.
- [ ] Dashboard live tests cover authenticated schema and metadata boundaries,
      stable revisions, one bounded activity read, stale-response cancellation,
      visibility lifecycle, terminal authentication, and capped retry behavior.
- [ ] Dashboard roster-operations tests cover bounded pagination and filters for
      division, capability, authority, host, platform, and tool; prompt-free
      routing contracts; conflict/requirement metadata; and bounded revision
      history without exporting specialist prompts.
- [ ] Dashboard review and inference tests cover immutable quarantine findings
      and status history, active-versus-candidate comparison, audit-gated
      mutations, ordered provider configuration, recent failure evidence, and
      requested/router/actual-provider/model separation. Remote freshness and
      provider readiness remain labelled non-probed unless separate live
      evidence exists.
- [ ] Dashboard master-control tests cover enabled/disabled rendering,
      generation-checked mutation, exact confirmation, stale revisions, live
      propagation, and the fresh-session A/B notice.
- [ ] Dashboard host-control tests cover committed generations, atomic
      concurrent writers, HTTP 409 conflicts, no-op stability, counter
      exhaustion, refresh-and-retry behavior, and MCP/CLI parity.
- [ ] Restricted Windows CLI tests prove status and host soft control broker
      only an exact restricted-token Store refusal through the authenticated
      dashboard; endpoint/method pairs, complete host snapshots, master state,
      host identity, booleans, and generations are validated, and malformed,
      unavailable, or stale results return nonzero without automatic retry.
- [ ] Brokered master and host mutation receipts prove success, requested and
      effective state, changed truth, and the exact legal no-op or
      single-increment generation; opposite, jumping, overflowing, and
      impossible effective states fail without retry.
- [ ] Restricted Windows agent tests prove list and toggle broker only the
      default installed identity through bounded revision-stable pages, exact
      lookup, and one config-revision mutation. Explicit config paths are not
      redirected, duplicate or inconsistent pages fail closed, and protected
      coordinators remain immutable.
- [ ] Restricted Windows selector tests prove search, route, explain, and
      policy use one complete validated read-only catalog, while delegation,
      setup, arbitrary Store calls, and generic config mutation fail with
      controlled nonzero diagnostics before execution or evidence claims.
- [ ] Dashboard browser QA covers desktop and mobile layout, live controls,
      chart summaries, keyboard naming, reduced motion, forced colors, no
      horizontal page overflow, and a clean console.
- [ ] Every dashboard asset is present in wheel and source artifacts, passes the
      static CSP/security scan, and stays within the documented asset budget.
- [ ] Fresh Python 3.10 environments on Windows install the built wheel and
      source distribution separately, run `agency --help`, import package data,
      and pass the full packaged smoke procedure for each artifact.
- [ ] The same isolated wheel and source-distribution procedures pass on Ubuntu.
- [ ] `python -m pip check` passes for both artifacts in both environments.
- [ ] Rebuilding from the same source does not depend on untracked local files.

## 7. Publish and post-publish

Publishing, pushing, tagging, issue closure, and release creation are
outward-facing actions and require explicit authorization.

- [ ] Obtain approval for the exact tag, artifacts, destination, and release
      notes.
- [ ] Tag the reviewed commit; do not move an existing public tag.
- [ ] Publish the wheel and source artifact produced by the verified workflow,
      not a local rebuild.
- [ ] Verify hashes, metadata, install command, and CLI version from the public
      destination.
- [ ] Create release notes from `CHANGELOG.md` and include known support limits.
- [ ] Update tracker states only after the release outcome is confirmed.
- [ ] Start the next `Unreleased` changelog section.

## Current blockers

`AR-03` and `AR-04` are locally complete. The exact-confirmed Windows Codex
0.144.1 isolated-profile canary exited `0`, produced a valid six-line header,
and persisted one correlated routing/finalization attestation; isolated
conversation controls exercised disable and enable while ending enabled. The
canary used a one-invocation trust bypass and recorded no model receipt. It does
not establish durable real-profile trust, which remains an explicit `/hooks`
review and new-session step, and it does not establish Linux Codex maturity.

The source-readiness blockers are closed. Warning-strict coverage, security,
performance, dashboard, wheel/source, isolated Windows/WSL install, hosted
Python, dependency, artifact, and CodeQL capability workflows passed for the
reviewed head. CodeQL recorded unavailable native analysis and the compensating
source and dependency controls passed. Pull request #18 merged into `main`, the
required ledgers are reconciled, and the associated tracker items are closed.
Claude Code, Hermes, and OpenClaw were absent and remain contract-only. A public
tag and package publication remain separate authorization-gated actions.

The current review branch adds turn-scoped evidence and fallback coordination,
agent activation controls, reconciled LiteLLM router/model evidence, the durable
master switch, unit-aware event-driven delegation, executable identity
hardening, and the related storage and host boundary repairs. Those changes are
not part of the prior reviewed-head evidence above until the complete matrix,
artifact smoke, installed-host canary, tracker reconciliation, and merge gates
pass for the new commit.
