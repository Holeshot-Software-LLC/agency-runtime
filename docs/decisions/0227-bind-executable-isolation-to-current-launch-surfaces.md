---
title: "Bind legacy executable-isolation acceptance to current launch surfaces"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [security, executables, acceptance, governance]
related:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0227
type: decision
deciders: [maintainers]
---

# ADR-0227: Bind executable-isolation acceptance to current launch surfaces

## Context

AR-164's fifth criterion still names direct Codex execution and a command
delegation backend. Job B deliberately removed those Agency-owned worker
surfaces in fb34191f9380cdeab2895878e5a933c2cda35608. AR-236 records the merged
retirement; North Star R5 retains native-host ownership of spawning/execution.
The Git helper and bounded process primitive survived because other legitimate
product operations use them. Current CLI-provider inspection/inference is not
restoration of an Agency-owned worker dispatcher.

The ancestor discovery and final lexical/resolved executable checks remain
implemented and relevant. An obsolete component name must neither require
restoring deleted behavior nor justify removing the security boundary.

## Decision

Explicitly reconcile only criterion 5 to:

> Current CLI-provider, installer, dashboard, and smoke launch paths use the
> shared contract; retired Agency-owned execution backends remain absent.

Preserve the original wording in AR-164 and its Git history. Criteria 1–4 and
6–7 are unchanged. Retain inert marker-derived ancestors, initial Git discovery
protection, explicit/resolver/link rejection, safe external PATH discovery,
identity freezing, namespace checks and immediate pre-spawn revalidation.

Keep the Windows test scope accurate: portable Windows spelling/PATHEXT
simulations exercise the shared algorithm on Linux. They are not native Windows
filesystem, PowerShell, ACL or host-activation evidence. Native platform
qualification and AR-187's attended refresh remain separate retained work;
nothing here changes those acceptance requirements or authorizes Windows work.

No production implementation changes are required by this reconciliation.
Isolated checks must judge the revised current criterion against a frozen
candidate. The builder cannot mark it satisfied based on removed code.

## Consequences

Evidence candidate 083ae8b5 records 38 discovery, 129 current-launch and 24
surviving Git/process passes with their exact Windows limitations. All seven
current criteria await isolated checks; no product bytes were changed.

- The current entry points retain the original security obligation.
- No removed host-execution backend or worker scheduler is restored.
- Historical acceptance text remains auditable, without claiming every original
  component still exists.
- Native Windows and normal-session activation limits remain explicit.
- ADR-0055 remains accepted and unchanged in substance; this decision narrows
  obsolete record terminology, not executable trust.

## Alternatives

- Restore the deleted backends to satisfy their old names: rejected because
  native hosts own worker execution.
- Retire all of AR-164: rejected because ancestor PATH poisoning remains relevant.
- Quietly treat removed components as passing: rejected because it conceals
  the changed product surface.
- Require an exhaustive cross-platform release run for this record: rejected
  because it is not one of the seven scoped criteria; do not confuse local
  algorithm evidence with native platform certification.
