---
title: "Use layered pinned supply-chain gates"
status: accepted
category: decisions
created: 2026-07-12
updated: 2026-07-13
tags: [security, supply-chain, ci, release]
related:
  - SECURITY.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-20-full-history-ledger-ci.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0037
type: decision
deciders: [maintainers]
---

# ADR-0037: Use layered pinned supply-chain gates

## Context

Agency Runtime installs plugins into credentialed agent hosts, launches native
commands, and persists local evidence. A compromised runtime dependency,
development tool, build backend, or CI action can therefore cross a more
sensitive boundary than an ordinary utility package. One scanner cannot cover
source flaws, dependency advisories, workflow injection, artifact omissions,
and mutable action tags at the same time.

The project also needs reproducible review evidence without forcing runtime
users to install a large security stack. Build and audit tooling belongs in
explicit optional dependency groups and CI, not the minimal runtime path.

## Decision

Use a layered release gate with these properties:

1. Keep the runtime dependency set minimal and version-bounded. Pin build,
   release, lint, coverage, and audit tools used by CI to reviewed versions.
2. Pin every third-party GitHub Action to an immutable commit SHA and disable
   checkout credential persistence unless a job explicitly requires it.
3. Run deterministic source hygiene and secret/path checks, Ruff, Bandit,
   runtime dependency auditing, offline workflow auditing, CodeQL for Python
   and JavaScript, and pull-request dependency review. Probe GitHub's
   dependency-diff capability first: use native review when available and the
   strict exact installed-runtime vulnerability audit when it is not, without
   silently enabling a potentially billable repository security product. Probe
   native CodeQL capability before registering its actions: initialize, analyze,
   and upload only where repository visibility and GitHub Code Security licensing
   permit them. Accept the unavailable path only for a private or internal
   repository whose HTTP 403 body exactly identifies Code Security as not
   enabled; authorization, rate-limit, malformed, not-found, and other ambiguous
   responses fail closed. For that recognized boundary, execute no CodeQL action
   or CLI, retain short-lived machine-readable evidence that analysis was not
   performed, and rely on the independently enforced Bandit, offline workflow,
   and exact installed-runtime vulnerability gates.
4. Verify wheel and source distributions structurally, compare shared payload
   hashes, install the built wheel in clean Windows and Linux environments, and
   keep publication or provenance claims separate until an authorized release
   actually produces them.
5. Let Dependabot propose reviewed upgrades with a cooldown; never replace
   immutable pins with moving major-version tags merely for convenience.

## Consequences

- Compromise or blind spots in one control are less likely to become the only
  release signal.
- CI configuration is itself audited and receives the same immutable-input
  discipline as product code.
- Private repositories without licensed dependency review retain an enforced
  vulnerability gate, while public or licensed repositories automatically use
  GitHub's base-versus-head dependency review.
- Public or licensed repositories automatically receive native CodeQL analysis
  and upload. Private or internal repositories with a positively identified
  missing entitlement record the capability boundary without implying that
  analysis ran or invoking an unlicensed analyzer; ambiguous probes fail.
- Tool upgrades become visible repository changes that require review and may
  briefly lag a release while compatibility is tested.
- Local contributors install more packages only when they request development,
  security, or release extras; production installations keep the small runtime
  dependency surface.
- Passing these gates reduces risk but does not prove absence of
  vulnerabilities or authorize a public release.

## Alternatives

- **Treat CodeQL as a universal mandatory gate.** Rejected because GitHub's
  action and CLI are not available for every private repository; initializing
  them without the required capability produces a configuration failure and
  would overstate the security evidence. Independent source, dependency, and
  workflow gates remain mandatory everywhere.
- **Use moving action tags and unpinned latest tools.** Rejected because the
  reviewed source can change without a repository diff and break
  reproducibility.
- **Vendor every tool and dependency.** Rejected because maintaining vendored
  security tooling would enlarge the trusted codebase and delay upstream fixes.
- **Add security tools to runtime dependencies.** Rejected because operators do
  not need scanners to run the control plane, and the extra packages would
  increase its attack and compatibility surface.
