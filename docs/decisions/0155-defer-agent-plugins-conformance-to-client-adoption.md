---
title: "Defer Agent Plugins conformance to client adoption"
status: accepted
category: decisions
created: 2026-08-06
updated: 2026-08-06
deciders: [lkrammes]
tags:
  - packaging
  - interoperability
  - hosts
  - standards
related:
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0005-portable-core-thin-host-adapters.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - agency_runtime/core/installer_payload_manifests.py
supersedes: []
superseded_by: null
id: ADR-0155
type: decision
---

# ADR-0155: Defer Agent Plugins conformance to client adoption

## Context

The Agent Plugins Specification 1.0.0 (`agent-plugins.org`) defines a
vendor-neutral portable plugin package: a required root `plugin.json` with a
closed schema, skills discovered at `skills/*/SKILL.md`, MCP servers at a root
`mcp.json`, plugin-root path containment, and `${PLUGIN_ROOT}` / `${PLUGIN_DATA}`
expansion in stdio server `args`, `env`, and `cwd`. Its Technical Steering
Committee is drawn from Amazon, Cursor, Microsoft, OpenAI, and Vercel.

Three properties of that specification decide this record.

1. **The format covers two component types.** §7 defines exactly skills and
   MCP servers. Hooks, agents, commands, rules, and LSP servers are named and
   deliberately excluded until their formats converge.
2. **Extension namespaces are client-owned.** §3 defines an extension namespace
   as a client-owned identifier and §8 directs a *client* to base it on a domain
   it controls, with the client defining the contents and behavior of its own
   namespace. In the host direction Agency is a plugin, not a client: it cannot
   mint a namespace for its own hook payload, because a client reads only the
   namespace it owns.
3. **The trust surface is deferred.** `FUTURE_CONSIDERATIONS.md` defers the
   permission model, sandboxing, provenance verification and signing, secret
   handling, enterprise policy, and audit-event schemas.

Measured against the bundles built in
[`installer_payload_manifests.py`](../../agency_runtime/core/installer_payload_manifests.py),
the Claude payload has five members. `skills/agency/SKILL.md` and the MCP
configuration fall inside the v1 format. `hooks/hooks.json`,
`.claude-plugin/plugin.json`, and `marketplace.json` do not — and
`hooks/hooks.json` carries the specialist binding chain that the product exists
to provide.

No supported host reads a root `plugin.json` today. Claude Code loads
`.claude-plugin/plugin.json`; Anthropic holds no TSC seat. No supported host has
published an extension-namespace directory contract.

## Decision

Do not restructure host bundles for Agent Plugins v1 conformance. Continue
packaging each host integration in its native format per ADR-0024, and do not
emit a root `plugin.json` or `mcp.json` until a supported host reads them.

Rationale:

1. **The format standardizes the least load-bearing members.** The
   `PreToolUse` bind → one-use activation receipt → `SubagentStart` injection
   chain is outside v1 by construction, as is the specialist roster. Conformance
   would portablize the control skill and the MCP entry and leave the product
   surface exactly where it is.
2. **Hooks have no lawful portable location.** Because namespaces are
   client-owned and none has been published, there is no directory Agency is
   permitted to write hooks into that any host would read. `hooks/hooks.json` at
   the plugin root is not a deferral; it is the only location that loads.
3. **Emitting unread files is not free here.** `render_codex_plugin_version`
   derives the Codex plugin version from a content fingerprint of the component
   files, install and uninstall plans are recomputed and re-digested at apply
   time, and ownership proofs and smoke assertions key off exact managed file
   sets. Two inert manifests churn a version, invalidate digests, and require
   test updates across five hosts for no reader.
4. **There is no runtime saving.** The specification standardizes packaging, not
   delegation primitives or hook vocabulary. The five host adapters differ on
   `Agent` / `spawn_agent` / `delegate_task` / `sessions_spawn` and on their
   event models; `agency_runtime/adapters/` is unaffected either way.

**Reopen this record when both conditions hold:** a supported host discovers a
root `plugin.json`, *and* that same host publishes the contract for its
extension-namespace directory. The first condition alone is insufficient — a
portable manifest that cannot carry hooks does not package this product.

## Consequences

- Host bundles keep their native manifests and gain no new members. ADR-0024
  continues to govern packaging.
- `PLUGIN_ID` is `agency-preflight`, which already satisfies the §5.5 name
  constraints (lowercase alphanumeric, hyphens, alphanumeric first and last
  character, no repeated separators). No name migration is owed when the trigger
  fires.
- The control skill and MCP configuration are the portable-shaped members. Keep
  host-specific fields out of them so that a future portable emitter is additive
  rather than a rewrite.
- Agency continues to ignore `${PLUGIN_DATA}`. Cross-host state stays under one
  root at `~/.agency-runtime/`; a per-plugin-instance data directory runs against
  that and nothing in the specification requires using it.
- One finding is recorded independently of adoption: §7.2.1 treats bare-name
  `PATH` resolution of an MCP `command` as client-defined behavior that
  conformant plugins must not depend on, reserving deterministic execution for
  bundled plugin-relative commands. Agency's MCP server resolves through the
  installed package entry point rather than a bundled executable. This is worth
  confirming against the launcher identity rules in ADR-0055 and ADR-0040 on its
  own merits, because it is the same exposure that appears in PATH-less service
  contexts.
- The specification's *client* role remains the more interesting direction. If
  third-party specialist rosters were distributed as Agent Plugins packages,
  Agency would be the client under §3, would legitimately own a reverse-domain
  namespace, and would define the contents of its own agents directory. That is
  roster work under the existing quarantine and approval gate (ADR-0013,
  ADR-0066), not packaging work, and the specification supplies no provenance or
  signature verification to lean on.

## Alternatives

- **Emit a portable `plugin.json` and `mcp.json` alongside the native
  manifests.** Rejected: nothing reads them, while they churn the Codex
  content-derived version, invalidate install and uninstall plan digests, and
  force test updates across five hosts for no behavior change.
- **Restructure to the portable layout with hooks under a Holeshot-owned
  namespace.** Rejected as a misreading of §8: extension namespaces belong to
  clients, no host would read `com.holeshotsoftware.agency/hooks/`, and moving
  hooks out of the plugin root breaks the loading path every supported host
  actually uses.
- **Adopt `${PLUGIN_DATA}` as the state convention.** Rejected: per-plugin
  instance directories conflict with the single cross-host state root, and the
  specification does not require a plugin to use the variable.
- **Join the specification effort to argue for hooks in v2.** Not rejected, but
  out of scope for a packaging decision. Recorded here as the reason the trigger
  condition is worth watching rather than forgetting.
