# Agency Runtime Control Plane

A portable control plane for specialist routing, roster governance, delegation, and model/run observability.

Agency policy lives once. Runtime adapters only translate local events and capabilities.

## Quick Start

```bash
# Standard install (bundled roster, no network sync)
agency install --profile standard

# Doctor check
agency doctor

# Route a task to see which specialists match
agency route "review this pull request"

# Search the roster
agency search "code review"
```

## Install Profiles

| Profile | Network | Auto-sync | Auto-enable new agents |
|---|---|---|---|
| `local-only` | never | no | no |
| `standard` (default) | manual only | no | no |
| `power` | optional | optional | review required |
| `lucas` | yes | yes | policy-controlled |

## Architecture

```
                    +--------------------------------+
                    | Agency Runtime Control Plane   |
                    | Core + SQLite + CLI + API + MCP|
                    +----------------+---------------+
                                     |
        +----------------------------+-----------------------------+
        |                            |                             |
  Ingress adapters              Worker adapters              Roster manager
  - LiteLLM callback            - Hermes delegate_task        - download agents
  - Hermes plugin               - OpenClaw sessions_spawn     - quarantine
  - OpenClaw plugin             - Codex exec / ACP            - categorize
  - Codex wrapper               - Claude wrapper optional     - embed/index
  - generic CLI wrapper         - generic command runner      - snapshots
```

## Key Design Principles

- **LiteLLM is optional.** The control plane works with or without LiteLLM.
- **Roster sync is opt-in.** Standard installs never download remote agents.
- **Model truth is honest.** Never claim resolved model from requested alias alone.
- **Delegation is auditable.** Every delegation is recorded with concrete status.
- **SQLite is canonical.** No loose JSON for runtime state.

## License

MIT
