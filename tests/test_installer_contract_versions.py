"""The one place a canary proof-contract version literal is asserted.

Handoff §8 entry 5: e48f7f8f reverted CODEX_ACTIVATION_CANARY_PROOF_CONTRACT from
v2 to v1 while resolving conflict markers, and nothing caught it because eight
test sites carried their own copy of the literal instead of importing the
constant. Those copies now import it, so a silent revert shows up here and only
here.
"""

from __future__ import annotations

from pathlib import Path

from agency_runtime.core.installer_contracts import (
    CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
    CODEX_AUTOMATION_CANARY_PROOF_CONTRACT,
    CODEX_CANARY_PROOF_CONTRACTS,
)


def test_codex_canary_proof_contract_versions_are_exact() -> None:
    # v4 requires a verified host-written child artifact. v3 trusted the Store
    # specialist-load row, which Agency itself writes, so it is intentionally stale.
    assert CODEX_ACTIVATION_CANARY_PROOF_CONTRACT == "agency.codex-activation-canary.v4"
    assert CODEX_AUTOMATION_CANARY_PROOF_CONTRACT == "agency.codex-automation-canary.v1"
    assert {
        CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
        CODEX_AUTOMATION_CANARY_PROOF_CONTRACT,
    } == CODEX_CANARY_PROOF_CONTRACTS


def test_no_other_site_hardcodes_a_canary_proof_contract_literal() -> None:
    """Keep the literal in exactly one place -- the defect §8 entry 5 records."""

    root = Path(__file__).resolve().parent.parent
    owner = root / "agency_runtime" / "core" / "installer_contracts.py"
    offenders: list[str] = []
    for path in list((root / "agency_runtime").rglob("*.py")) + list(
        (root / "tests").rglob("*.py")
    ):
        if path == owner or path == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "agency.codex-activation-canary.v" in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == [], (
        "import CODEX_ACTIVATION_CANARY_PROOF_CONTRACT instead of copying its value: "
        + ", ".join(offenders)
    )
